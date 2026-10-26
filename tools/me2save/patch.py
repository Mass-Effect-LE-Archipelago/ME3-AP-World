"""Apply plot edits to a COPY of an ME2 LE save and re-seal its checksum.

Never modifies the input file and refuses to overwrite an existing output.
Edits are in place: bool words and int slots must already exist in the table.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import struct

from checksum import seal, verify
from layout import PlotTableSpan, get_bool, get_int, parse


@dataclass(frozen=True)
class Edit:
    table: str   # "me2" or "me1"
    kind: str    # "bool" or "int"
    index: int
    value: int


def apply(save: bytes, edits: list[Edit]) -> bytes:
    if not verify(save):
        raise ValueError("input checksum does not verify")
    layout = parse(save)
    body = bytearray(save[:layout.body_end])
    for edit in edits:
        table: PlotTableSpan = layout.plot if edit.table == "me2" else layout.me1_plot
        if edit.kind == "bool":
            word, bit = divmod(edit.index, 32)
            if word >= table.bool_words or edit.value not in (0, 1):
                raise ValueError(f"bool edit out of range: {edit}")
            offset = table.bool_words_offset + 4 * word
            current = struct.unpack_from("<I", body, offset)[0]
            struct.pack_into("<I", body, offset, current | 1 << bit if edit.value else current & ~(1 << bit))
        elif edit.kind == "player":  # index 0 = origin, 1 = notoriety (u8 enum)
            if edit.index not in (0, 1) or not 1 <= edit.value <= 3:
                raise ValueError(f"player edit out of range: {edit}")
            body[layout.origin_offset if edit.index == 0 else layout.notoriety_offset] = edit.value
        elif edit.kind == "int":
            if edit.index >= table.ints:
                raise ValueError(f"int edit out of range: {edit}")
            struct.pack_into("<i", body, table.ints_offset + 4 * edit.index, edit.value)
        else:
            raise ValueError(f"unknown edit kind: {edit}")
    result = seal(bytes(body))
    check = parse(result)
    for edit in edits:
        table = check.plot if edit.table == "me2" else check.me1_plot
        if edit.kind == "player":
            read = result[check.origin_offset if edit.index == 0 else check.notoriety_offset]
        else:
            read = get_bool(result, table, edit.index) if edit.kind == "bool" else get_int(result, table, edit.index)
        if int(read) != edit.value:
            raise ValueError(f"readback mismatch: {edit}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("edits", type=Path, help="JSON list of {table, kind, index, value}")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists; never overwrite a save")
    source = args.input.read_bytes()
    edits = [Edit(**item) for item in json.loads(args.edits.read_text(encoding="utf-8"))]
    result = apply(source, edits)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as stream:
        stream.write(result)
    print(json.dumps({"input_sha256": hashlib.sha256(source).hexdigest(),
                      "output": str(args.output), "output_sha256": hashlib.sha256(result).hexdigest(),
                      "edits": len(edits)}, indent=2))


if __name__ == "__main__":
    main()

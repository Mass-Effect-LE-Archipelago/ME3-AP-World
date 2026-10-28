"""Walk an ME2 LE (version 30) .pcsav and locate its plot tables.

Written for this project from the field order documented by Trilogy Save Editor
(KarlitosVII/trilogy-save-editor, CeCILL; read as a format reference, no code copied).
Encoding: little-endian; bool = u32 0/1; enum = u8; Vec/map = u32 count; string =
i32 length (negative = UTF-16 code units) including a trailing NUL; Guid = 16 bytes.

Only offsets are recorded. Editing plot bools never changes the file size, so a
patch rewrites words in place and re-seals the checksum (checksum.py).
"""
from __future__ import annotations

from dataclasses import dataclass
import struct


class SaveFormatError(ValueError):
    pass


class Reader:
    def __init__(self, data: bytes):
        self.data, self.pos = data, 0

    def take(self, size: int) -> bytes:
        if size < 0 or self.pos + size > len(self.data):
            raise SaveFormatError(f"read past end at {self.pos}")
        chunk = self.data[self.pos:self.pos + size]
        self.pos += size
        return chunk

    def i32(self) -> int: return struct.unpack("<i", self.take(4))[0]
    def u32(self) -> int: return struct.unpack("<I", self.take(4))[0]
    def f32(self) -> float: return struct.unpack("<f", self.take(4))[0]
    def u8(self) -> int: return self.take(1)[0]

    def boolean(self) -> bool:
        value = self.u32()
        if value not in (0, 1):
            raise SaveFormatError(f"bad bool {value} at {self.pos - 4}")
        return bool(value)

    def string(self) -> str:
        length = self.i32()
        if length == 0:
            return ""
        raw = self.take(-2 * length) if length < 0 else self.take(length)
        text = raw.decode("utf-16-le" if length < 0 else "cp1252")
        if not text.endswith("\0"):
            raise SaveFormatError(f"unterminated string before {self.pos}")
        return text[:-1]

    def count(self, limit: int = 1_000_000) -> int:
        value = self.u32()
        if value > limit:
            raise SaveFormatError(f"implausible count {value} at {self.pos - 4}")
        return value

    def many(self, item) -> list:
        return [item() for _ in range(self.count())]


@dataclass(frozen=True)
class PlotTableSpan:
    bool_words_offset: int  # first u32 of the bool bitfield words
    bool_words: int
    ints_offset: int
    ints: int
    floats_offset: int
    floats: int


@dataclass(frozen=True)
class Layout:
    version: int
    base_level: str
    end_game_state: int  # 0 not finished, 1 died, 2 lived
    first_name: str
    is_female: bool
    origin_offset: int      # Player.origin u8 (1 spacer, 2 colonist, 3 earthborn)
    notoriety_offset: int   # Player.notoriety u8 (1 survivor, 2 war hero, 3 ruthless)
    plot: PlotTableSpan      # ME2 plot table
    me1_plot: PlotTableSpan  # inherited ME1 plot table
    body_end: int            # offset of the trailing checksum


def _weapon_loadout(r: Reader) -> None:
    for _ in range(6):
        r.string()


def _power(r: Reader) -> None:
    r.string(); r.f32(); r.string(); r.i32()


def _head_morph(r: Reader) -> None:
    r.string()
    r.many(r.string)
    for _ in range(r.count()):
        r.string(); r.f32()
    for _ in range(r.count()):
        r.string(); r.take(12)
    for _ in range(4):
        r.take(12 * r.count())
    for _ in range(r.count()):
        r.string(); r.f32()
    for _ in range(r.count()):
        r.string(); r.take(16)
    for _ in range(r.count()):
        r.string(); r.string()


def _plot_table(r: Reader) -> PlotTableSpan:
    words = r.count(); bools = r.pos; r.take(4 * words)
    ints_count = r.count(); ints = r.pos; r.take(4 * ints_count)
    floats_count = r.count(); floats = r.pos; r.take(4 * floats_count)
    return PlotTableSpan(bools, words, ints, ints_count, floats, floats_count)


def parse(data: bytes) -> Layout:
    r = Reader(data)
    version = r.i32()
    if version != 30:
        raise SaveFormatError(f"expected ME2 LE save version 30, found {version}")
    r.string(); r.f32(); r.i32()
    base_level = r.string()
    r.u8()
    end_game_state = r.u32()
    if end_game_state > 2:
        raise SaveFormatError("bad end game state")
    r.take(16); r.take(12); r.take(12); r.i32()                      # timestamp, location, rotation, tip
    r.many(lambda: (r.string(), r.boolean(), r.boolean()))           # levels
    r.many(lambda: (r.string(), r.boolean()))                         # streaming states
    r.many(lambda: (r.take(16), r.boolean()))                         # kismet records
    r.many(lambda: (r.take(16), r.u8(), r.u8()))                      # doors
    r.many(lambda: r.take(16))                                        # pawns
    # Player
    is_female = r.boolean(); r.string(); r.i32(); r.f32()
    first_name = r.string(); r.i32()
    origin_offset = r.pos; r.u8(); notoriety_offset = r.pos; r.u8(); r.i32()
    r.string(); r.string(); r.string()
    r.u8(); r.take(4 * 13)                                            # appearance ids
    if r.boolean():
        _head_morph(r)
    r.many(lambda: _power(r))
    r.many(lambda: (r.string(), r.i32(), r.i32(), r.boolean(), r.boolean(), r.string()))
    _weapon_loadout(r)
    r.many(lambda: (r.string(), r.i32()))                             # hotkeys
    r.take(4 * 7); r.f32()                                            # credits..probes, fuel
    r.string(); r.i32()                                               # face code, class name ref
    r.take(4 * 7)                                                     # ME1 import bonus (LE only)
    r.many(lambda: (r.string(), r.many(lambda: _power(r)), r.i32(), r.i32(), _weapon_loadout(r), r.string()))
    plot = _plot_table(r)
    r.i32(); r.many(lambda: (r.i32(), r.boolean(), r.many(r.i32))); r.many(r.i32)        # journal
    r.many(lambda: r.many(lambda: (r.i32(), r.boolean()))); r.many(r.i32)                 # codex
    me1_plot = _plot_table(r)
    r.many(lambda: (r.i32(), r.boolean(), r.take(8 * r.count())))     # galaxy map planets
    r.many(lambda: (r.i32(), r.string()))                             # dependent DLC
    if r.pos != len(data) - 4:
        raise SaveFormatError(f"layout ended at {r.pos}, expected {len(data) - 4}")
    return Layout(version, base_level, end_game_state, first_name, is_female, origin_offset, notoriety_offset,
                  plot, me1_plot, r.pos)


def get_bool(data: bytes, table: PlotTableSpan, index: int) -> bool:
    word, bit = divmod(index, 32)
    if word >= table.bool_words:
        return False
    return bool(struct.unpack_from("<I", data, table.bool_words_offset + 4 * word)[0] >> bit & 1)


def get_int(data: bytes, table: PlotTableSpan, index: int) -> int:
    return struct.unpack_from("<i", data, table.ints_offset + 4 * index)[0] if index < table.ints else 0

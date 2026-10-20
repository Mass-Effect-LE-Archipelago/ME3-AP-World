"""Read-only LE3 snapshot/diff helper; uses only Python's standard library."""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import json
import os
from pathlib import Path

PIPE = r"\\.\pipe\LE3APBridge"


def parse_assets(reply: str) -> dict[str, int]:
    parts = reply.split()
    if not parts:
        raise ValueError("Empty asset reply")
    result = {}
    for part in parts[1:]:
        key, value = part.split(":")
        if key in result:
            raise ValueError("Duplicate asset ID in snapshot")
        result[key] = int(value)
    if int(parts[0]) != len(result):
        raise ValueError("Asset count mismatch")
    return result


class Connection:
    def __enter__(self):
        if os.name != "nt":
            raise RuntimeError("The game bridge requires Windows")
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.WaitNamedPipeW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD]
        kernel.WaitNamedPipeW.restype = wintypes.BOOL
        kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                      ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.SetNamedPipeHandleState.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p, ctypes.c_void_p]
        kernel.SetNamedPipeHandleState.restype = wintypes.BOOL
        kernel.ReadFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
        kernel.ReadFile.restype = wintypes.BOOL
        kernel.WriteFile.argtypes = kernel.ReadFile.argtypes
        kernel.WriteFile.restype = wintypes.BOOL
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.restype = wintypes.BOOL
        if not kernel.WaitNamedPipeW(PIPE, 1000):
            raise RuntimeError("LE3APBridge pipe is unavailable; no game connection was made")
        self.kernel = kernel
        self.handle = kernel.CreateFileW(PIPE, 0xC0000000, 0, None, 3, 0, None)
        if self.handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        mode = wintypes.DWORD(2)
        if not kernel.SetNamedPipeHandleState(self.handle, ctypes.byref(mode), None, None):
            kernel.CloseHandle(self.handle)
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            if self.request("HELLO 1") != "1 LE3 readonly":
                raise RuntimeError("Unexpected game/protocol handshake")
        except BaseException:
            kernel.CloseHandle(self.handle)
            raise
        return self

    def __exit__(self, *_):
        self.kernel.CloseHandle(self.handle)

    def request(self, text: str) -> str:
        encoded = text.encode("ascii")
        sent, size = wintypes.DWORD(), wintypes.DWORD()
        if not self.kernel.WriteFile(self.handle, encoded, len(encoded), ctypes.byref(sent), None):
            raise ctypes.WinError(ctypes.get_last_error())
        if sent.value != len(encoded):
            raise RuntimeError("Short pipe write")
        buffer = ctypes.create_string_buffer(65536)
        if not self.kernel.ReadFile(self.handle, buffer, len(buffer), ctypes.byref(size), None):
            raise ctypes.WinError(ctypes.get_last_error())
        reply = buffer.raw[:size.value].decode("utf-8")
        if reply == "OK":
            return ""
        if not reply.startswith("OK "):
            raise RuntimeError(reply)
        return reply[3:]


def read_plots(connection, operation: str, indices: list[int]) -> dict[str, int]:
    result = {}
    for start in range(0, len(indices), 64):
        batch = indices[start:start + 64]
        values = [int(value) for value in connection.request(operation + " " + " ".join(map(str, batch))).split()]
        if len(values) != len(batch):
            raise ValueError("Plot batch count mismatch")
        result.update((str(key), value) for key, value in zip(batch, values))
    return result


def snapshot(connection, bools: list[int], ints: list[int]) -> dict:
    started = datetime.now(timezone.utc).isoformat()
    current_map = connection.request("MAP")
    version = connection.request("VER")
    capabilities = connection.request("CAPS").split()
    plot_info = connection.request("PLOTINFO") if "PLOTINFO" in capabilities and (bools or ints) else None
    result = {"schema": 1, "game": "LE3", "bridge_version": version,
              "started_utc": started, "map": current_map,
              "bools": read_plots(connection, "GETBS", bools),
              "ints": read_plots(connection, "GETIS", ints),
              "gaw": parse_assets(connection.request("GAW"))}
    used, expected_total = [], None
    while expected_total is None or len(used) < expected_total:
        parts = connection.request(f"USES {len(used)} 128").split()
        total = int(parts[0])
        if expected_total is not None and total != expected_total:
            raise RuntimeError("Used-object list changed during snapshot; retry while idle")
        expected_total = total
        page = parts[1:]
        for guid in page:
            fields = guid.split(":")
            if len(fields) != 4:
                raise ValueError("Malformed use-module GUID")
            for field in fields:
                int(field)
        if len(page) != min(128, total - len(used)):
            raise ValueError("Used-object page count mismatch")
        used.extend(page)
    if len(set(used)) != len(used):
        raise ValueError("Duplicate use-module GUID")
    result["used_guids"] = used
    if plot_info is not None:
        result["plot_info_before"] = plot_info
        result["plot_info_after"] = connection.request("PLOTINFO")
    if connection.request("MAP") != current_map:
        raise RuntimeError("Map changed during snapshot; retry while idle")
    result["finished_utc"] = datetime.now(timezone.utc).isoformat()
    return result


def difference(before: dict, after: dict) -> dict:
    if before.get("game") != "LE3" or after.get("game") != "LE3" or before.get("schema") != 1 or after.get("schema") != 1:
        raise ValueError("Expected LE3 schema 1 snapshots")
    return {"before_map": before["map"], "after_map": after["map"],
            **{family: {key: {"before": before[family].get(key), "after": after[family].get(key)}
                        for key in before[family].keys() | after[family].keys()
                        if before[family].get(key) != after[family].get(key)} for family in ("bools", "ints", "gaw")},
            "used_guids_added": sorted(set(after["used_guids"]) - set(before["used_guids"])),
            "used_guids_removed": sorted(set(before["used_guids"]) - set(after["used_guids"]))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    take = sub.add_parser("snapshot")
    take.add_argument("output", type=Path)
    take.add_argument("--bool", type=int, nargs="*", default=[], dest="bools")
    take.add_argument("--int", type=int, nargs="*", default=[], dest="ints")
    take.add_argument("--bool-range", type=int, nargs=2, metavar=("START", "STOP"))
    take.add_argument("--catalog-plots", action="store_true",
                      help="Include every experimental location plot predicate and ending candidate")
    diff = sub.add_parser("diff")
    diff.add_argument("before", type=Path)
    diff.add_argument("after", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "diff":
            result = difference(json.loads(args.before.read_text()), json.loads(args.after.read_text()))
            print(json.dumps(result, indent=2))
            return
        indices = set(args.bools)
        integer_indices = set(args.ints)
        if args.catalog_plots:
            catalog = Path(__file__).resolve().parents[2] / "world/mass_effect_le3/locations.json"
            for row in json.loads(catalog.read_text(encoding="utf-8")):
                detector = row["detector"]
                if detector["kind"] == "bool":
                    indices.add(detector["index"])
                elif detector["kind"] == "int_positive":
                    integer_indices.add(detector["index"])
            indices.add(22426)  # Final-decision candidate; runtime evidence still required.
        if args.bool_range:
            first, stop = args.bool_range
            if not 0 <= first < stop <= 65536:
                parser.error("bool range must satisfy 0 <= START < STOP <= 65536")
            indices.update(range(first, stop))
        if any(not 0 <= value <= 65535 for value in indices | integer_indices):
            parser.error("plot indices must be between 0 and 65535")
        with Connection() as connection:
            result = snapshot(connection, sorted(indices), sorted(integer_indices))
        # Exclusive create protects earlier observations from accidental overwrite.
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")
        print(f"Saved read-only snapshot: {args.output.resolve()}")
    except (OSError, RuntimeError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()

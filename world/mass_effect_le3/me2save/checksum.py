"""ME2 LE .pcsav checksum: CRC-32/BZIP2 of every byte before the trailing 4-byte little-endian value.

Identified 2026-10-24 by matching all owner-supplied ME2 LE saves (see research/me2_save_format.md).
"""
from __future__ import annotations

import struct

_TABLE = []
for _i in range(256):
    _c = _i << 24
    for _ in range(8):
        _c = ((_c << 1) ^ 0x04C11DB7) & 0xFFFFFFFF if _c & 0x80000000 else (_c << 1) & 0xFFFFFFFF
    _TABLE.append(_c)


def crc32_bzip2(data: bytes) -> int:
    crc = 0xFFFFFFFF
    for byte in data:
        crc = _TABLE[((crc >> 24) ^ byte) & 0xFF] ^ ((crc << 8) & 0xFFFFFFFF)
    return crc ^ 0xFFFFFFFF


def verify(save: bytes) -> bool:
    return len(save) > 4 and struct.unpack_from("<I", save, len(save) - 4)[0] == crc32_bzip2(save[:-4])


def seal(body: bytes) -> bytes:
    """Return body plus its checksum; body must not already carry one."""
    return body + struct.pack("<I", crc32_bzip2(body))

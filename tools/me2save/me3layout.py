"""Read-only walker for ME3 LE (version 59) .pcsav files: plot table and player variables.

Field order from Trilogy Save Editor's mass_effect_3 module (format reference only).
Used to diff saves, e.g. the state Earth leaves behind; never writes ME3 saves.
"""
from __future__ import annotations

from dataclasses import dataclass
import struct

from layout import Reader, SaveFormatError, _head_morph, _weapon_loadout


@dataclass(frozen=True)
class Me3Plot:
    base_level: str
    bools: frozenset[int]          # set indices
    ints: dict[int, int]           # sparse map
    floats: dict[int, float]
    me1_bools: frozenset[int]
    player_variables: dict[str, int]


def _power(r: Reader) -> None:
    r.string(); r.f32(); r.take(24); r.string(); r.i32()


def _weapon(r: Reader) -> None:
    r.string(); r.i32(); r.i32(); r.boolean(); r.boolean(); r.string(); r.string()


def _weapon_mod(r: Reader) -> None:
    r.string(); r.many(r.string)


def _bits(r: Reader) -> frozenset[int]:
    words = [r.u32() for _ in range(r.count())]
    return frozenset(32 * w + b for w, word in enumerate(words) for b in range(32) if word >> b & 1)


def parse(data: bytes) -> Me3Plot:
    r = Reader(data)
    if r.i32() != 59:
        raise SaveFormatError("expected ME3 save version 59")
    r.string(); r.f32(); r.i32()
    base_level = r.string(); r.string()
    r.u8(); r.u32()
    r.take(16); r.take(12); r.take(12); r.i32()
    r.many(lambda: (r.string(), r.boolean(), r.boolean()))
    r.many(lambda: (r.string(), r.boolean()))
    r.many(lambda: (r.take(16), r.boolean()))
    r.many(lambda: (r.take(16), r.u8(), r.u8()))
    r.many(lambda: (r.take(16), r.u8(), r.u8()))                      # placeables
    r.many(lambda: r.take(16))
    # Player
    r.boolean(); r.string(); r.boolean(); r.boolean(); r.boolean(); r.i32(); r.f32()
    r.string(); r.i32(); r.u8(); r.u8(); r.i32()
    r.string(); r.string(); r.string()
    r.u8(); r.take(4 * 13)
    if r.boolean():
        _head_morph(r)
    r.i32()                                                            # emissive id
    r.many(lambda: _power(r))
    for _ in range(r.count()):
        r.i32(); r.i32()                                               # war assets
    r.many(lambda: _weapon(r))
    r.many(lambda: _weapon_mod(r))
    _weapon_loadout(r); r.string(); r.string()
    r.many(r.i32)
    r.many(lambda: (r.string(), r.string()))
    r.f32(); r.take(4 * 7); r.f32(); r.i32()                           # health, credits..probes, fuel, grenades
    r.string(); r.i32(); r.take(16)
    r.many(lambda: (r.string(), r.many(lambda: _power(r)), r.i32(), r.i32(), _weapon_loadout(r), r.string(),
                    r.many(lambda: _weapon_mod(r)), r.i32(), r.many(lambda: _weapon(r))))
    bools = _bits(r)
    ints = {r.i32(): r.i32() for _ in range(r.count())}
    floats = {r.i32(): r.f32() for _ in range(r.count())}
    r.i32(); r.many(lambda: (r.i32(), r.boolean(), r.i32(), r.many(r.i32))); r.many(r.i32)
    r.many(lambda: r.many(lambda: (r.i32(), r.boolean()))); r.many(r.i32)
    me1_bools = _bits(r); r.take(4 * r.count()); r.take(4 * r.count())
    variables = {}
    for _ in range(r.count()):
        key = r.string(); variables[key] = r.i32()
    r.many(lambda: (r.i32(), r.boolean(), r.take(8 * r.count()), r.boolean()))
    r.many(lambda: (r.i32(), r.f32(), r.boolean()))
    r.many(lambda: (r.i32(), r.string(), r.string()))
    r.many(lambda: (r.string(), r.i32(), r.i32(), r.many(r.string)))
    r.many(lambda: r.take(16))
    r.u8()
    r.many(lambda: (r.string(), r.take(12), r.i32(), r.string(), r.u8()))
    r.i32()
    if r.pos != len(data) - 4:
        raise SaveFormatError(f"ME3 layout ended at {r.pos}, expected {len(data) - 4}")
    return Me3Plot(base_level, bools, ints, floats, me1_bools, variables)

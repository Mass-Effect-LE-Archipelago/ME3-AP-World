"""Source-mapped history readback; not yet a complete career initializer.

Mirrors BioGlobalVariableTable.MajorPlot_* readers in vanilla SFXGame.pcc.
These report current plot state, which later ME3 events may change. They cannot
reconstruct a complete immutable imported profile from an arbitrary old save.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


# All indices below are cross-checked against config aliases, the plot database,
# and each decompiled reader by tools/verify_history_mapping.py.
READER_PLOTS = {
    "MajorPlot_ME1_RachniiQueenSaved": ((12587,), ()),
    "MajorPlot_ME1_VirmireSurvivor_IsAsh": ((13827,), ()),
    "MajorPlot_ME1_WrexStatus": ((13942, 13028, 13029, 15543), ()),
    "MajorPlot_ME1_SavedTheCouncil": ((13001,), ()),
    "MajorPlot_ME2_DestroyedMaelonsData": ((2677,), ()),
    "MajorPlot_ME2_SavedMaelonsData": ((2676,), ()),
    "MajorPlot_ME2_HerteticsStatus": ((757, 759), ()),
    "MajorPlot_ME2_CollectorBaseStatus": ((1832, 1831), ()),
    "MajorPlot_ME2_NumberOfSuicideMissionSurvivors":
        ((33, 34, 42, 39, 44, 37, 40, 35, 38, 43, 41, 36), ()),
    "MajorPolt_ME1_Romance": ((14281, 13960, 14169), (10017, 10015, 10016)),
    "MajorPlot_ME2_Romance": ((), (266, 270, 267, 271, 213, 272)),
}
ME1_ROMANCES = (("ashley", 14281, 10017), ("kaidan", 13960, 10015), ("liara", 14169, 10016))
ME2_ROMANCES = (("miranda", 266), ("garrus", 270), ("jacob", 267),
                ("thane", 271), ("jack", 213), ("tali", 272))
SURVIVORS = {"miranda": 33, "jacob": 34, "grunt": 42, "thane": 39, "zaeed": 44,
             "kasumi": 37, "tali": 40, "jack": 35, "garrus": 38, "samara_or_morinth": 43,
             "mordin": 41, "legion": 36}

# The only write bundle currently backed by a complete vanilla setter.
# SetPlotChoices explicitly clears both opposite outcomes and party flags.
VIRMIRE_BUNDLES = {
    "ashley": {13827: True, 13828: False, 13940: True, 13939: False},
    "kaidan": {13827: False, 13828: True, 13940: False, 13939: True},
}


def readback_indices() -> tuple[frozenset[int], frozenset[int]]:
    """Include complementary diagnostics, not just flags used by vanilla getters."""
    bools = {index for b, _ in READER_PLOTS.values() for index in b}
    ints = {index for _, i in READER_PLOTS.values() for index in i}
    bools.update((12588, 13002, 13828, 13940, 13939))
    return frozenset(bools), frozenset(ints)


@dataclass(frozen=True)
class HistoryReadback:
    values: dict
    warnings: tuple[str, ...]


def inspect_history_snapshot(snapshot: dict) -> HistoryReadback:
    """Decode the read-only probe's schema, without coercing malformed values."""
    if snapshot.get("game") != "LE3" or type(snapshot.get("schema")) is not int or snapshot["schema"] != 1:
        raise ValueError("Expected an LE3 schema 1 snapshot")
    b, i = readback_indices()
    bools, ints = {}, {}
    for family, indices, target in (("bools", b, bools), ("ints", i, ints)):
        source = snapshot.get(family)
        if not isinstance(source, dict): raise ValueError(f"Missing {family} snapshot mapping")
        for index in indices:
            if str(index) not in source: continue  # inspect_history reports all missing indices.
            value = source[str(index)]
            if type(value) is not int or (family == "bools" and value not in (0, 1)):
                raise ValueError(f"Invalid {family} snapshot value at {index}")
            target[index] = bool(value) if family == "bools" else value
    return inspect_history(bools, ints)


def inspect_history(bools: Mapping[int, bool], ints: Mapping[int, int]) -> HistoryReadback:
    """Reproduce native getter precedence while reporting ambiguous combinations.

    Require every requested read. Missing transport results must not masquerade
    as a valid default history. Warnings are diagnostics, not profile validation:
    later campaign changes can legitimately alter party membership.
    """
    required_bools, required_ints = readback_indices()
    missing_bools, missing_ints = required_bools - bools.keys(), required_ints - ints.keys()
    if missing_bools or missing_ints:
        raise ValueError(f"Incomplete history snapshot: bools={sorted(missing_bools)}, ints={sorted(missing_ints)}")
    if any(type(bools[i]) is not bool for i in required_bools):
        raise ValueError("History bool reads must be booleans")
    if any(type(ints[i]) is not int or not -(2**31) <= ints[i] < 2**31 for i in required_ints):
        raise ValueError("History int reads must be signed 32-bit integers")
    warnings = []
    for name, first, second, exclusive_required in (
        ("me1.rachni", 12587, 12588, True), ("me1.council", 13001, 13002, True),
        ("me1.virmire_survivor", 13827, 13828, True),
        ("me2.maelon_data", 2676, 2677, False),
        ("me2.heretics", 757, 759, False), ("me2.collector_base", 1831, 1832, True),
    ):
        if bools[first] and bools[second]: warnings.append(f"{name}: both outcomes set")
        if exclusive_required and not (bools[first] or bools[second]):
            warnings.append(f"{name}: neither outcome set; native fallback is not proof of history")
    survivor = "ashley" if bools[13827] else "kaidan"
    if any(bools[index] != expected for index, expected in VIRMIRE_BUNDLES[survivor].items()):
        warnings.append("me1.virmire_survivor: rescue/party bundle differs from fresh-career setter")
    wrex_dead = any(bools[i] for i in (13028, 13029, 15543))
    if bools[13942] and wrex_dead: warnings.append("me1.wrex: in-party and death flags both set")
    me1_romances = [name for name, flag, count in ME1_ROMANCES if bools[flag] and ints[count] >= 4]
    me2_romances = [name for name, relationship in ME2_ROMANCES if ints[relationship] == 5]
    if len(me1_romances) > 1: warnings.append("me1.romance: multiple recognized partners; native priority used")
    if len(me2_romances) > 1: warnings.append("me2.romance: multiple recognized partners; native priority used")
    alive = tuple(name for name, index in SURVIVORS.items() if bools[index])
    values = {
        "me1.rachni_queen_saved": bools[12587],
        "me1.virmire_survivor": survivor,
        "me1.wrex": "alive" if bools[13942] else "dead" if wrex_dead else "ignored",
        "me1.council_saved": bools[13001],
        "me1.romance": me1_romances[0] if me1_romances else "none",
        "me2.maelon_data_saved": bools[2676],
        "me2.maelon_data_destroyed": bools[2677],
        "me2.heretics": "rewritten" if bools[759] else "destroyed" if bools[757] else "not_completed",
        # Native defaults to irradiated/preserved even when both flags are false.
        "me2.collector_base": "preserved" if bools[1832] or not bools[1831] else "destroyed",
        "me2.romance": me2_romances[0] if me2_romances else "none",
        "me2.squad_survivor_count": len(alive),
        "me2.squad_present": alive,
    }
    return HistoryReadback(values, tuple(warnings))

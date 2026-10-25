"""Translate a resolved history profile into ME2 LE import-save plot edits.

Decision D3: seed history reaches ME3 through its own ME2 import path. ME3 copies
ME2 plot indices unchanged and the inherited ME1 table at +10000 (proven live,
research/me2_save_format.md). ME2 also keeps its own copies of several ME1
outcomes; both copies are written so ME2-side and ME1-side readers agree.

Indices come from Trilogy Save Editor's ME1/ME2 plot databases. Each family is
tagged "reader" (checked offline against the ME3 MajorPlot reader model) or
"database" (labels only; needs a live import before it is trusted).
"""
from __future__ import annotations

from typing import Iterable, Mapping

Edit = tuple[str, str, int, int]  # (table "me1"/"me2", kind "bool"/"int", index, value)

VERIFICATION = {
    "me1.virmire_survivor": "live", "me2.collector_base": "live",
    "me1.wrex": "reader", "me1.rachni": "reader", "me1.council": "reader", "me1.romance": "reader",
    "me2.heretics": "reader", "me2.maelon_data": "reader", "me2.romance": "reader",
    "me2.squad": "reader",
    "me1.human_councilor": "database", "me2.liara_relationship": "database",
    "me2.crew_rescue": "database", "shepard": "database",
}
UNSUPPORTED = {
    # Morinth needs Samara's death and the whole recruitment swap; not derivable
    # from a Samara template by flag edits alone.
    ("me2.mystic_identity", "morinth"),
}

SQUAD_FLAGS = {  # in party, loyal, dead, selectable, specialized
    "miranda": (33, 177, 195, 207, 219), "jacob": (34, 178, 196, 208, 220),
    "jack": (35, 179, 197, 209, 221), "legion": (36, 180, 198, 210, 222),
    "kasumi": (37, 182, 199, 211, 223), "garrus": (38, 183, 200, 212, 224),
    "thane": (39, 185, 201, 213, 225), "tali": (40, 186, 202, 214, 226),
    "mordin": (41, 188, 203, 215, 227), "grunt": (42, 189, 204, 216, 228),
    "mystic": (43, 191, 205, 217, 229), "zaeed": (44, 192, 206, 218, 230),
}
# ME1 romance: active flag, cancelled flag, progress int (ME3 recognizes >= 4).
ME1_ROMANCE = {"ashley": (4281, 4282, 17), "kaidan": (3960, 3961, 15), "liara": (4169, 4686, 16)}
ME1_ROMANCE_ME2_COPY = {"ashley": 1528, "kaidan": 1529, "liara": 1530}
ME1_ROMANCE_SEX = {"ashley": "male", "kaidan": "female", "liara": None}
# ME2 romance: progress int (5 = romance, ME3 recognizes exactly 5), "had sex" flag.
ME2_ROMANCE = {"miranda": (266, 5209), "garrus": (270, 5207), "jacob": (267, 3892),
               "thane": (271, 5206), "jack": (213, 5208), "tali": (272, 3926)}
ME2_ROMANCE_SEX = {"miranda": "male", "jack": "male", "tali": "male",
                   "garrus": "female", "jacob": "female", "thane": "female"}
ORIGIN = {"spacer": (1, 1533), "colonist": (2, 1535), "earthborn": (3, 1534)}
NOTORIETY = {"sole_survivor": (1, 1537), "war_hero": (2, 1538), "ruthless": (3, 1539)}


def _bools(table: str, values: Mapping[int, bool]) -> list[Edit]:
    return [(table, "bool", index, int(value)) for index, value in values.items()]


def plot_edits(choices: Mapping[str, str | bool], *, is_female: bool,
               current_int: callable) -> list[Edit]:
    """Edits that make a template save express `choices` completely.

    `current_int(table, index)` reads the template so romance progress for
    non-partners can be capped below the recognition threshold, not zeroed.
    Raises ValueError for combinations the template or mapping cannot express.
    """
    for key, value in choices.items():
        if (key, value) in UNSUPPORTED:
            raise ValueError(f"{key}={value} cannot be generated from this template yet")
    sex = "female" if is_female else "male"
    edits: list[Edit] = []

    survivor = choices["me1.virmire_survivor"]
    ash = survivor == "ashley"
    edits += _bools("me1", {3827: ash, 3828: not ash, 3940: ash, 3939: not ash})
    edits += _bools("me2", {1541: ash, 1540: not ash})

    wrex = choices["me1.wrex"]
    edits += _bools("me1", {3942: wrex == "alive", 3021: wrex != "alive",
                            3029: wrex == "dead", 3028: False, 5543: False})
    edits += _bools("me2", {3753: wrex != "never_recruited", 3752: wrex != "alive", 1862: False})

    rachni = choices["me1.rachni"] == "saved"
    edits += _bools("me1", {2587: rachni, 2588: not rachni})
    edits += _bools("me2", {3151: rachni})

    council = choices["me1.council"] == "saved"
    edits += _bools("me1", {3001: council, 3002: not council})
    edits += _bools("me2", {1554: council, 1553: not council})

    anderson = choices["me1.human_councilor"] == "anderson"
    edits += _bools("me1", {5435: anderson, 5434: not anderson})
    edits += _bools("me2", {1556: anderson, 1555: not anderson})

    partner = choices["me1.romance"]
    if partner != "none" and ME1_ROMANCE_SEX[partner] not in (None, sex):
        raise ValueError(f"me1.romance={partner} is not available to a {sex} Shepard")
    for name, (active, cancelled, progress) in ME1_ROMANCE.items():
        chosen = name == partner
        edits += _bools("me1", {active: True, cancelled: False} if chosen else {active: False})
        edits.append(("me1", "int", progress, max(current_int("me1", progress), 4) if chosen
                      else min(current_int("me1", progress), 3)))
        edits += _bools("me2", {ME1_ROMANCE_ME2_COPY[name]: chosen})
    edits += _bools("me1", {6528: partner != "none"})
    edits += _bools("me2", {1926: partner == "none"})

    edits += _bools("me2", {1831: choices["me2.collector_base"] == "destroyed",
                            1832: choices["me2.collector_base"] == "preserved"})

    heretics = choices["me2.heretics"]
    if heretics == "not_completed" and choices["me2.squad.legion.loyal"]:
        raise ValueError("me2.heretics=not_completed contradicts a loyal Legion")
    edits += _bools("me2", {757: heretics == "destroyed", 759: heretics == "rewritten"})

    maelon = choices["me2.maelon_data"]
    if maelon == "not_completed" and choices["me2.squad.mordin.loyal"]:
        raise ValueError("me2.maelon_data=not_completed contradicts a loyal Mordin")
    edits += _bools("me2", {2676: maelon == "saved", 2677: maelon == "destroyed"})

    alive = 0
    for member, (party, loyal, dead, selectable, specialized) in SQUAD_FLAGS.items():
        recruited = choices[f"me2.squad.{member}.recruited"]
        survived = recruited and choices[f"me2.squad.{member}.survived"]
        alive += survived
        edits += _bools("me2", {party: survived, loyal: recruited and choices[f"me2.squad.{member}.loyal"],
                                dead: recruited and not survived})
        if not survived:  # Living members keep the template's selectable/specialized state.
            edits += _bools("me2", {selectable: False, specialized: False})
    if alive < 2:
        raise ValueError("Shepard survives the Suicide Mission only with at least two squad survivors")

    me2_partner = choices["me2.romance"]
    if me2_partner != "none":
        if ME2_ROMANCE_SEX[me2_partner] != sex:
            raise ValueError(f"me2.romance={me2_partner} is not available to a {sex} Shepard")
    for name, (progress, consummated) in ME2_ROMANCE.items():
        chosen = name == me2_partner
        current = current_int("me2", progress)
        edits.append(("me2", "int", progress, 5 if chosen else (4 if current == 5 else current)))
        edits += _bools("me2", {consummated: chosen})

    liara = choices["me2.liara_relationship"]
    edits += _bools("me2", {6927: liara == "continued", 6924: liara == "ended"})

    crew = choices["me2.crew_rescue"]
    edits += _bools("me2", {3351: crew == "all_saved", 3629: crew != "all_saved"})
    edits += [("me2", "int", 166, {"all_saved": 0, "half_saved": 2, "doctor_only": 4}[crew])]

    origin, origin_flag = ORIGIN[choices["shepard.origin"]]
    edits.append(("me1", "int", 1, origin))
    edits += _bools("me2", {flag: flag == origin_flag for _, flag in ORIGIN.values()})
    notoriety, notoriety_flag = NOTORIETY[choices["shepard.service_history"]]
    edits.append(("me1", "int", 2, notoriety))
    edits += _bools("me2", {flag: flag == notoriety_flag for _, flag in NOTORIETY.values()})

    return _deduplicate(edits)


def _deduplicate(edits: Iterable[Edit]) -> list[Edit]:
    final: dict[tuple[str, str, int], int] = {}
    for table, kind, index, value in edits:
        key = (table, kind, index)
        if key in final and final[key] != value:
            raise ValueError(f"Conflicting edits for {key}")
        final[key] = value
    return [(table, kind, index, value) for (table, kind, index), value in final.items()]


def me3_import_view(read_bool: callable, read_int: callable, bools: Iterable[int], ints: Iterable[int]) -> dict:
    """Snapshot of what ME3 would read after import (ME2 as-is, ME1 at +10000)."""
    def source(index: int) -> tuple[str, int]:
        return ("me1", index - 10000) if index >= 10000 else ("me2", index)
    return {"game": "LE3", "schema": 1,
            "bools": {str(i): int(read_bool(*source(i))) for i in bools},
            "ints": {str(i): read_int(*source(i)) for i in ints}}

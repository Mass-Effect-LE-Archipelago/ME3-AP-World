"""Stable source IDs shared by the generator and game client.

The source manifest includes explicit evidence/availability limitations. Its ID
ledger is append-only; detector and availability fixes never renumber checks.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from importlib.resources import files

GAME_NAME = "Mass Effect Legendary Edition 3"
ITEM_BASE = 0x4D330000
INTEL = "Crucible Intel"
CREDITS = "Credits (1000)"
VICTORY = "Reapers Defeated"
ITEM_NAME_TO_ID = {INTEL: ITEM_BASE, CREDITS: ITEM_BASE + 0x40}
DLC = frozenset({"From Ashes", "Leviathan", "Omega", "Citadel"})
FINAL_REGIONS = frozenset({"Cerberus Headquarters", "Earth Finale"})
GOAL_PLOT_BOOL = 22426  # End002: Made_Final_Decision; runtime observation pending.
SCHEMA_VERSION = 1
HISTORY = {"preset": "maximum_content", "version": 1, "implemented_in_game": False}


@dataclass(frozen=True)
class LocationData:
    key: str
    name: str
    id: int
    region: str
    category: str
    dlc: str
    detector: dict
    progression_safe: bool
    evidence: str
    source: str
    notes: str


_manifest_text = files(__package__).joinpath("locations.json").read_text(encoding="utf-8")
MANIFEST_HASH = hashlib.sha256(_manifest_text.encode("utf-8")).hexdigest()
LOCATIONS = tuple(LocationData(**entry) for entry in json.loads(_manifest_text))
BY_ID = {entry.id: entry for entry in LOCATIONS}
BY_KEY = {entry.key: entry for entry in LOCATIONS}
LOCATION_NAME_TO_ID = {entry.name: entry.id for entry in LOCATIONS}
LOCATION_NAME_GROUPS = {category: {entry.name for entry in LOCATIONS if entry.category == category}
                        for category in sorted({entry.category for entry in LOCATIONS})}
if len(BY_ID) != len(LOCATIONS) or len(BY_KEY) != len(LOCATIONS) or len(LOCATION_NAME_TO_ID) != len(LOCATIONS):
    raise ValueError("Duplicate ME3 source identity, AP ID or location name")

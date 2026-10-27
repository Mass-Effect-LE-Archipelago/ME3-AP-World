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
# Loadout weapons in bridge Weapons.hpp order (append-only; the index is the native WEAPON id).
WEAPON_CLASSES = (
    "AssaultRifle_Avenger", "AssaultRifle_Argus", "AssaultRifle_Cobra", "AssaultRifle_Collector",
    "AssaultRifle_Falcon", "AssaultRifle_Geth", "AssaultRifle_Mattock", "AssaultRifle_Reckoning",
    "AssaultRifle_Revenant", "AssaultRifle_Saber", "AssaultRifle_Valkyrie", "AssaultRifle_Vindicator",
    "SMG_Shuriken", "SMG_Hornet", "SMG_Hurricane", "SMG_Locust", "SMG_Tempest",
    "Pistol_Predator", "Pistol_Carnifex", "Pistol_Eagle", "Pistol_Ivory", "Pistol_Phalanx", "Pistol_Scorpion",
    "Pistol_Talon", "Pistol_Thor",
    "Shotgun_Katana", "Shotgun_Claymore", "Shotgun_Crusader", "Shotgun_Disciple", "Shotgun_Eviscerator",
    "Shotgun_Geth", "Shotgun_Graal", "Shotgun_Raider", "Shotgun_Scimitar", "Shotgun_Striker",
    "SniperRifle_Mantis", "SniperRifle_BlackWidow", "SniperRifle_Incisor", "SniperRifle_Indra",
    "SniperRifle_Javelin", "SniperRifle_Raptor", "SniperRifle_Valiant", "SniperRifle_Viper", "SniperRifle_Widow",
)
_KINDS = {"AssaultRifle": "Assault Rifle", "SMG": "SMG", "Pistol": "Pistol", "Shotgun": "Shotgun",
          "SniperRifle": "Sniper Rifle"}
WEAPON_ITEMS = tuple(f"{cls.split('_', 1)[1]} ({_KINDS[cls.split('_', 1)[0]]})" for cls in WEAPON_CLASSES)
WEAPON_ITEM_BASE = ITEM_BASE + 0x100
STARTING_WEAPON = WEAPON_ITEMS[WEAPON_CLASSES.index("Pistol_Predator")]   # D5: the career starts with the Predator
ITEM_NAME_TO_ID.update({name: WEAPON_ITEM_BASE + index for index, name in enumerate(WEAPON_ITEMS)})
WEAPON_ID_TO_NATIVE = {WEAPON_ITEM_BASE + index: index for index in range(len(WEAPON_ITEMS))}
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

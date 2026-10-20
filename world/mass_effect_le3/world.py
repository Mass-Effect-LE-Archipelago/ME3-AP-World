from __future__ import annotations

import logging

from BaseClasses import Item, ItemClassification, Location, LocationProgressType, Region, Tutorial
from worlds.AutoWorld import WebWorld, World

from . import data
from .options import MassEffectLE3Options


class ME3Item(Item):
    game = data.GAME_NAME


class ME3Location(Location):
    game = data.GAME_NAME


class ME3WebWorld(WebWorld):
    tutorials = [Tutorial("Multiworld Setup Guide", "Experimental LE3 integration setup and current limitations.",
                          "English", "setup_en.md", "setup/en", ["APWorldMaker"])]


def included(options: MassEffectLE3Options, entry: data.LocationData) -> bool:
    if entry.dlc and entry.dlc not in options.enabled_dlc.value:
        return False
    switch = {"objectives": "objective_checks", "credits": "credit_checks", "supplies": "supply_checks",
              "armor": "armor_checks", "mods": "mod_checks", "weapons": "weapon_checks", "exploration": "exploration_checks"}
    return bool(getattr(options, switch[entry.category])) if entry.category in switch else True


class MassEffectLE3World(World):
    """An experimental ME3 Legendary Edition integration with source-specific pickups and war-effort recoveries.

    Generation and client foundations are implemented. Native history, reward
    transactions and finale enforcement are not ready for a playable release.
    """
    game = data.GAME_NAME
    hidden = True
    web = ME3WebWorld()
    options_dataclass = MassEffectLE3Options
    options: MassEffectLE3Options
    item_name_to_id = data.ITEM_NAME_TO_ID
    location_name_to_id = data.LOCATION_NAME_TO_ID
    location_name_groups = data.LOCATION_NAME_GROUPS
    origin_region_name = "Campaign"

    def generate_early(self) -> None:
        self.selected = tuple(entry for entry in data.LOCATIONS if included(self.options, entry))
        safe_slots = sum(entry.progression_safe and entry.region not in data.FINAL_REGIONS for entry in self.selected)
        capacity = max(1, safe_slots - 4)
        self.intel_total = min(self.options.crucible_intel_total.value, capacity)
        self.intel_required = min(self.options.crucible_intel_required.value, self.intel_total)
        if self.intel_total != self.options.crucible_intel_total.value or self.intel_required != self.options.crucible_intel_required.value:
            logging.warning("%s: LE3 intel pool/requirement adjusted to %s/%s for the selected safe locations",
                            self.player_name, self.intel_total, self.intel_required)

    def create_regions(self) -> None:
        hub = Region("Campaign", self.player, self.multiworld)
        self.multiworld.regions.append(hub)
        names = sorted({entry.region for entry in self.selected} | {"Earth Finale"})
        regions = {name: Region(name, self.player, self.multiworld) for name in names}
        self.multiworld.regions.extend(regions.values())
        for name, region in regions.items():
            # Native story ordering has no AP-item prerequisite. These edges mean
            # eventually reachable through vanilla play; they do not skip missions.
            gate = (lambda state: state.has(data.INTEL, self.player, self.intel_required)) if name in data.FINAL_REGIONS else None
            hub.connect(region, f"Campaign -> {name}", gate)
        for entry in self.selected:
            location = ME3Location(self.player, entry.name, entry.id, regions[entry.region])
            if not entry.progression_safe or entry.region in data.FINAL_REGIONS:
                location.progress_type = LocationProgressType.EXCLUDED
            regions[entry.region].locations.append(location)
        goal = ME3Location(self.player, "Defeat the Reapers", None, regions["Earth Finale"])
        goal.place_locked_item(ME3Item(data.VICTORY, ItemClassification.progression, None, self.player))
        regions["Earth Finale"].locations.append(goal)

    def create_item(self, name: str) -> ME3Item:
        classification = ItemClassification.progression_skip_balancing if name == data.INTEL else ItemClassification.filler
        return ME3Item(name, classification, data.ITEM_NAME_TO_ID[name], self.player)

    def create_items(self) -> None:
        self.multiworld.itempool.extend(self.create_item(data.INTEL) for _ in range(self.intel_total))
        self.multiworld.itempool.extend(self.create_item(data.CREDITS) for _ in range(len(self.selected) - self.intel_total))

    def get_filler_item_name(self) -> str:
        return data.CREDITS

    def set_rules(self) -> None:
        self.multiworld.completion_condition[self.player] = lambda state: state.has(data.VICTORY, self.player)

    def fill_slot_data(self) -> dict:
        return {"slot_data_version": data.SCHEMA_VERSION, "client_protocol": 1, "manifest_hash": data.MANIFEST_HASH,
                "implementation_status": "experimental_not_playable", "history": data.HISTORY.copy(),
                "crucible_intel_total": self.intel_total, "crucible_intel_required": self.intel_required,
                "enabled_dlc": sorted(self.options.enabled_dlc.value),
                "locations": [entry.id for entry in self.selected],
                "goal": {"kind": "bool", "index": data.GOAL_PLOT_BOOL},
                "native_requirements": ["save_identity", "indexed_delivery", "finale_gate", "history_initialization"]}

from __future__ import annotations

import logging

from BaseClasses import Item, ItemClassification, Location, LocationProgressType, Region, Tutorial
from worlds.AutoWorld import WebWorld, World

from . import data
from .options import MassEffectLE3Options, option_groups, options_presets


class ME3Item(Item):
    game = data.GAME_NAME


class ME3Location(Location):
    game = data.GAME_NAME


class ME3WebWorld(WebWorld):
    tutorials = [Tutorial("Multiworld Setup Guide", "Installing and playing Mass Effect Legendary Edition 3 with Archipelago.",
                          "English", "setup_en.md", "setup/en", ["APWorldMaker"])]
    option_groups = option_groups
    options_presets = options_presets


def included(options: MassEffectLE3Options, entry: data.LocationData) -> bool:
    if entry.region in data.SKIPPED_REGIONS:
        return False
    if entry.dlc and entry.dlc not in options.enabled_dlc.value:
        return False
    switch = {"objectives": "objective_checks", "credits": "credit_checks", "supplies": "supply_checks",
              "armor": "armor_checks", "mods": "mod_checks", "weapons": "weapon_checks", "exploration": "exploration_checks",
              "codex": "codex_checks"}
    if entry.category == "war_assets":
        return entry.detector["count"] <= options.war_asset_checks.value
    return bool(getattr(options, switch[entry.category])) if entry.category in switch else True


class MassEffectLE3World(World):
    """Mass Effect 3 Legendary Edition: gather Crucible Intel from across the multiworld to reach Cronos Station and
    Earth. Pickups, mission objectives, codex pages and war-asset recoveries are checks; weapons are items."""
    game = data.GAME_NAME
    web = ME3WebWorld()
    options_dataclass = MassEffectLE3Options
    options: MassEffectLE3Options
    item_name_to_id = data.ITEM_NAME_TO_ID
    location_name_to_id = data.LOCATION_NAME_TO_ID
    location_name_groups = data.LOCATION_NAME_GROUPS
    origin_region_name = "Campaign"

    def safe(self, entry: data.LocationData) -> bool:
        """May hold progression. With salvage on, a pickup on a mission you can't replay can still be bought back."""
        if entry.region in data.FINAL_REGIONS:
            return False
        return entry.progression_safe or bool(self.options.salvage and entry.region in data.SALVAGE_MISSIONS
                                              and entry.category in data.PICKUP_CATEGORIES)

    def generate_early(self) -> None:
        self.selected = tuple(entry for entry in data.LOCATIONS if included(self.options, entry))
        regions = {entry.region for entry in self.selected}
        # Access items for the side missions this slot has; with the option off they are precollected (always open).
        self.mission_keys = [name for name in data.MISSION_KEY_ITEMS if data.MISSION_KEY_REGION[name] in regions]
        safe_slots = sum(self.safe(entry) for entry in self.selected)
        capacity = max(1, safe_slots - 4 - (len(self.mission_keys) if self.options.mission_access else 0))
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
            keys = tuple(k for k in data.REGION_REQUIRES.get(name, ()) if k in self.mission_keys)
            if keys:
                intel = self.intel_required if name in data.FINAL_REGIONS else 0
                gate = lambda state, keys=keys, intel=intel: (state.has_all(keys, self.player)
                                                              and state.has(data.INTEL, self.player, intel))
            hub.connect(region, f"Campaign -> {name}", gate)
        for entry in self.selected:
            location = ME3Location(self.player, entry.name, entry.id, regions[entry.region])
            if not self.safe(entry):
                location.progress_type = LocationProgressType.EXCLUDED
            regions[entry.region].locations.append(location)
        goal = ME3Location(self.player, "Defeat the Reapers", None, regions["Earth Finale"])
        goal.place_locked_item(ME3Item(data.VICTORY, ItemClassification.progression, None, self.player))
        regions["Earth Finale"].locations.append(goal)

    def create_item(self, name: str) -> ME3Item:
        classification = (ItemClassification.progression_skip_balancing if name == data.INTEL
                           else ItemClassification.filler)
        # Weapons stay filler: most locations are excluded (conservative missable audit), and a weapon is never
        # required, so it may be placed anywhere. Only ~11 non-excluded slots would remain after intel otherwise.
        if name in data.MISSION_KEY_REGION:
            classification = ItemClassification.progression
        return ME3Item(name, classification, data.ITEM_NAME_TO_ID[name], self.player)

    def create_items(self) -> None:
        self.multiworld.itempool.extend(self.create_item(data.INTEL) for _ in range(self.intel_total))
        keys = self.mission_keys if self.options.mission_access else []
        for name in self.mission_keys:
            if not self.options.mission_access:
                self.multiworld.push_precollected(self.create_item(name))
        self.multiworld.itempool.extend(self.create_item(name) for name in keys)
        weapons = []
        if self.options.weapon_items:
            self.multiworld.push_precollected(self.create_item(data.STARTING_WEAPON))
            # Weapons replace credit filler only while slots remain; never displace intel.
            room = len(self.selected) - self.intel_total - len(keys)
            weapons = [name for name in data.WEAPON_ITEMS if name != data.STARTING_WEAPON][:room]
        self.multiworld.itempool.extend(self.create_item(name) for name in weapons)
        self.multiworld.itempool.extend(self.create_item(data.CREDITS)
                                        for _ in range(len(self.selected) - self.intel_total - len(keys) - len(weapons)))

    def get_filler_item_name(self) -> str:
        return data.CREDITS

    def set_rules(self) -> None:
        self.multiworld.completion_condition[self.player] = lambda state: state.has(data.VICTORY, self.player)

    def fill_slot_data(self) -> dict:
        return {"slot_data_version": data.SCHEMA_VERSION, "client_protocol": 1, "manifest_hash": data.MANIFEST_HASH,
                "implementation_status": "beta", "history": data.HISTORY.copy(),
                "crucible_intel_total": self.intel_total, "crucible_intel_required": self.intel_required,
                "weapon_items": bool(self.options.weapon_items),
                "mission_access": bool(self.options.mission_access),
                "salvage": bool(self.options.salvage), "salvage_price": self.options.salvage_price.value,
                "enabled_dlc": sorted(self.options.enabled_dlc.value),
                "locations": [entry.id for entry in self.selected],
                "goal": {"kind": "bool", "index": data.GOAL_PLOT_BOOL},
                "native_requirements": ["save_identity", "indexed_delivery", "finale_gate", "history_initialization"]}

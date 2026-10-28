from dataclasses import dataclass

from Options import Choice, DefaultOnToggle, OptionGroup, OptionSet, PerGameCommonOptions, Range, Toggle
from .data import DLC


class CrucibleIntelTotal(Range):
    """Number of Crucible Intel items in the pool. Clamped to safe placement capacity when needed."""
    display_name = "Crucible Intel Total"
    range_start = 1
    range_end = 24
    default = 16


class CrucibleIntelRequired(Range):
    """Intel needed before the final assault. Clamped to the actual pool total."""
    display_name = "Crucible Intel Required"
    range_start = 1
    range_end = 24
    default = 12


class ObjectiveChecks(DefaultOnToggle):
    """Include the named Mars objective completion checks currently mapped in the source catalog."""
    display_name = "Objective Checks"


class CreditChecks(DefaultOnToggle):
    """Include fixed credit-cache source interactions. Filler-only pending the missable/deadline audit."""
    display_name = "Credit Cache Checks"


class SupplyChecks(DefaultOnToggle):
    """Include fixed supply/medical interactions. Vanilla full-inventory behavior still requires testing."""
    display_name = "Supply Checks"


class ArmorChecks(DefaultOnToggle):
    """Include placed armor source interactions. Filler-only pending availability validation."""
    display_name = "Armor Pickup Checks"


class ModChecks(DefaultOnToggle):
    """Include placed weapon-mod interactions. Filler-only pending availability validation."""
    display_name = "Weapon Mod Checks"


class WeaponChecks(Toggle):
    """Include cataloged weapon source interactions, including heavy/special weapons. Experimental and filler-only."""
    display_name = "Weapon Pickup Checks"


class WeaponItems(DefaultOnToggle):
    """D5: start with only the M3 Predator; every other loadout weapon is an item in the pool."""
    display_name = "Weapons as Items"


class ExplorationChecks(DefaultOnToggle):
    """Include the 76 named galaxy-map recoveries. Recovery and subsequent quest delivery are distinct actions."""
    display_name = "Exploration Recovery Checks"


class CodexChecks(DefaultOnToggle):
    """Include codex pages as checks: each page a conversation or mission unlocks after the start (variants of one
    page are one check). Some come from optional conversations, so codex checks never hold progression items."""
    display_name = "Codex Checks"


class Salvage(DefaultOnToggle):
    """Missed-checks salvage: once you've been on a mission that can't be replayed, the Normandy's store terminal sells
    "<mission> Salvage". Each purchase sends one check you left behind on that mission."""
    display_name = "Salvage"


class SalvagePrice(Choice):
    """Credits per salvaged check."""
    display_name = "Salvage Price per Check"
    option_free = 0
    option_500 = 1
    option_1000 = 2
    option_2500 = 3
    option_5000 = 4
    default = 2


class EnabledDLC(OptionSet):
    """Include mapped pickup sources in the selected official DLC campaigns."""
    display_name = "Enabled DLC"
    valid_keys = DLC
    default = DLC


@dataclass
class MassEffectLE3Options(PerGameCommonOptions):
    crucible_intel_total: CrucibleIntelTotal
    crucible_intel_required: CrucibleIntelRequired
    objective_checks: ObjectiveChecks
    credit_checks: CreditChecks
    supply_checks: SupplyChecks
    armor_checks: ArmorChecks
    mod_checks: ModChecks
    weapon_checks: WeaponChecks
    exploration_checks: ExplorationChecks
    codex_checks: CodexChecks
    salvage: Salvage
    salvage_price: SalvagePrice
    weapon_items: WeaponItems
    enabled_dlc: EnabledDLC


option_groups = [
    OptionGroup("Goal", [CrucibleIntelTotal, CrucibleIntelRequired]),
    OptionGroup("Checks", [ObjectiveChecks, CreditChecks, SupplyChecks, ArmorChecks, ModChecks, WeaponChecks,
                           ExplorationChecks, CodexChecks]),
    OptionGroup("Items", [WeaponItems]),
    OptionGroup("Salvage", [Salvage, SalvagePrice]),
    OptionGroup("DLC", [EnabledDLC]),
]

options_presets = {
    "Story Focus": {"crucible_intel_total": 10, "crucible_intel_required": 8, "credit_checks": False,
                    "supply_checks": False, "exploration_checks": False, "codex_checks": False},
    "Completionist": {"weapon_checks": True, "salvage_price": "500"},
    "Everything": {"crucible_intel_total": 24, "crucible_intel_required": 20, "weapon_checks": True},
}

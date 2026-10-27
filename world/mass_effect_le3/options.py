from dataclasses import dataclass

from Options import DefaultOnToggle, OptionSet, PerGameCommonOptions, Range, Toggle
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
    weapon_items: WeaponItems
    enabled_dlc: EnabledDLC

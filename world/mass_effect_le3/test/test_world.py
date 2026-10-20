import unittest

from BaseClasses import LocationProgressType
from Fill import distribute_items_restrictive
from test.general import gen_steps, setup_multiworld

from .. import data
from ..world import MassEffectLE3World


class TestWorldGeneration(unittest.TestCase):
    def test_default_and_maximum_categories(self):
        for options, count in (({}, 502), ({"weapon_checks": True}, 527)):
            with self.subTest(options=options):
                world = setup_multiworld(MassEffectLE3World, gen_steps, 17, options)
                self.assertEqual(len(world.get_unfilled_locations()), count)
                self.assertEqual(len(world.itempool), count)
                self.assertEqual(len(world.worlds[1].fill_slot_data()["locations"]), count)

    def test_intel_opens_both_finale_regions(self):
        world = setup_multiworld(MassEffectLE3World, gen_steps, 1)
        required = world.worlds[1].intel_required
        for _ in range(required - 1):
            world.state.collect(world.worlds[1].create_item(data.INTEL))
        for name in data.FINAL_REGIONS:
            self.assertFalse(world.get_region(name, 1).can_reach(world.state))
        world.state.collect(world.worlds[1].create_item(data.INTEL))
        for name in data.FINAL_REGIONS:
            self.assertTrue(world.get_region(name, 1).can_reach(world.state))

    def test_missables_are_excluded_from_progression(self):
        world = setup_multiworld(MassEffectLE3World, gen_steps, 5, {"weapon_checks": True})
        for entry in data.LOCATIONS:
            if not entry.progression_safe or entry.region in data.FINAL_REGIONS:
                self.assertEqual(world.get_location(entry.name, 1).progress_type, LocationProgressType.EXCLUDED)

    def test_option_boundaries_fill_and_reach_goal(self):
        minimal = {key: False for key in ("objective_checks", "credit_checks", "supply_checks", "armor_checks", "mod_checks", "weapon_checks", "exploration_checks")}
        minimal["enabled_dlc"] = []
        option_sets = [{}, {"weapon_checks": True}, minimal,
                       {"crucible_intel_total": 1, "crucible_intel_required": 24},
                       {"crucible_intel_total": 24, "crucible_intel_required": 24, "enabled_dlc": []}]
        for options in option_sets:
            for seed in range(20):
                with self.subTest(options=options, seed=seed):
                    world = setup_multiworld(MassEffectLE3World, gen_steps, seed, options)
                    distribute_items_restrictive(world)
                    self.assertFalse(world.get_unfilled_locations())
                    self.assertTrue(world.can_beat_game(world.state))
                    self.assertLessEqual(world.worlds[1].intel_required, world.worlds[1].intel_total)
                    for location in world.get_filled_locations():
                        if location.address and location.progress_type == LocationProgressType.EXCLUDED:
                            self.assertFalse(location.item.advancement)

    def test_two_player_fill(self):
        world = setup_multiworld([MassEffectLE3World, MassEffectLE3World], gen_steps, 23,
                                 [{}, {"weapon_checks": True, "enabled_dlc": []}])
        distribute_items_restrictive(world)
        self.assertFalse(world.get_unfilled_locations())
        self.assertTrue(world.can_beat_game(world.state))

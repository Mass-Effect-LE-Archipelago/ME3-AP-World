import itertools
import unittest

from ..client_core import history_digest
from ..history import inspect_history, readback_indices
from ..history_profile import (SQUAD, compile_history_preview,
                               parse_resolved_history, resolve_history)


class TestHistoryProfile(unittest.TestCase):
    def test_preset_resolves_all_facts_without_sharing_mutable_state(self):
        first = resolve_history()
        self.assertEqual(len(first.choices), 51)
        choices = first.to_slot_data()["choices"]
        for member in SQUAD:
            for fact in ("recruited", "survived", "loyal"):
                self.assertIs(choices[f"me2.squad.{member}.{fact}"], True)
        choices["me1.wrex"] = "dead"
        self.assertEqual(resolve_history(), first)
        self.assertEqual(parse_resolved_history(first.to_slot_data()), first)

    def test_contradictory_recruitment_facts_are_rejected_without_correction(self):
        for member in SQUAD:
            with self.subTest(member=member):
                with self.assertRaisesRegex(ValueError, "recruitment"):
                    resolve_history(overrides={f"me2.squad.{member}.recruited": False})
        with self.assertRaisesRegex(ValueError, "Mystic identity"):
            resolve_history(overrides={"me2.mystic_identity": "none"})
        member = {f"me2.squad.mystic.{fact}": False for fact in ("recruited", "survived", "loyal")}
        profile = resolve_history(overrides={**member, "me2.mystic_identity": "none"})
        self.assertEqual(dict(profile.choices)["me2.mystic_identity"], "none")

    def test_past_romance_and_loyalty_survive_partner_death(self):
        overrides = {"me2.romance": "thane", "me2.squad.thane.survived": False}
        profile = resolve_history(overrides=overrides)
        self.assertEqual(profile.preset, "custom")
        choices = dict(profile.choices)
        self.assertEqual(choices["me2.romance"], "thane")
        self.assertIs(choices["me2.squad.thane.loyal"], True)
        self.assertIs(choices["me2.squad.thane.survived"], False)
        plan = compile_history_preview(profile)
        self.assertEqual(plan["unmapped_choices"]["me2.romance"], "thane")
        self.assertIs(plan["unmapped_choices"]["me2.squad.thane.survived"], False)
        self.assertFalse(plan["executable"])
        overrides.update({"me2.squad.thane.recruited": False, "me2.squad.thane.loyal": False})
        with self.assertRaisesRegex(ValueError, "past romance"):
            resolve_history(overrides=overrides)

    def test_invalid_options_and_incomplete_saved_profiles_fail(self):
        for overrides in ({"typo": True}, {"me1.romance": ["liara"]},
                          {"me2.squad.thane.survived": 1}, {"me1.wrex": "random"}):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                resolve_history(overrides=overrides)
        profile = resolve_history().to_slot_data()
        del profile["choices"]["me1.romance"]
        with self.assertRaisesRegex(ValueError, "missing"):
            parse_resolved_history(profile)
        for invalid in (True, 2, "1"):
            profile = resolve_history().to_slot_data()
            profile["version"] = invalid
            with self.assertRaisesRegex(ValueError, "version"): parse_resolved_history(profile)
        profile = resolve_history().to_slot_data()
        profile["choices"]["me1.wrex"] = "dead"
        with self.assertRaisesRegex(ValueError, "labeled custom"): parse_resolved_history(profile)

    def test_bundle_composition_matches_native_major_readers(self):
        # Check all mapped ME1 combinations plus the Collector Base choice,
        # including romance alternatives being cleared before the chosen setter.
        dimensions = {
            "me1.romance": ("none", "ashley", "kaidan", "liara"),
            "me1.virmire_survivor": ("ashley", "kaidan"),
            "me1.wrex": ("alive", "dead"), "me1.rachni": ("saved", "killed"),
            "me1.council": ("saved", "sacrificed"),
            "me1.human_councilor": ("anderson", "udina"),
            "me2.collector_base": ("destroyed", "preserved"),
        }
        for combination in itertools.product(*dimensions.values()):
            requested = dict(zip(dimensions, combination))
            # This exercises source composition, not full native story legality.
            plan = compile_history_preview(resolve_history(overrides=requested))
            self.assertFalse(plan["executable"])
            self.assertEqual(plan["actions"][0]["transition"], 5600)
            self.assertNotIn(5915, [a["transition"] for a in plan["actions"]])
            b, i = readback_indices()
            bools, ints = dict.fromkeys(b, False), dict.fromkeys(i, 0)
            for key, value in plan["expected_direct_targets"]["bools"].items(): bools[int(key)] = value
            for key, value in plan["expected_direct_targets"]["ints"].items(): ints[int(key)] = value
            result = inspect_history(bools, ints).values
            for key in ("me1.romance", "me1.virmire_survivor", "me1.wrex", "me2.collector_base"):
                self.assertEqual(result[key], requested[key])
            self.assertEqual(result["me1.council_saved"], requested["me1.council"] == "saved")
            self.assertEqual(result["me1.rachni_queen_saved"], requested["me1.rachni"] == "saved")

    def test_substates_and_unmapped_choices_are_retained(self):
        plan = compile_history_preview(resolve_history(overrides={"me1.wrex": "never_recruited"}))
        self.assertEqual(plan["unmapped_choices"]["me1.wrex"], "never_recruited")
        substate = next(e for a in plan["actions"] for e in a["elements"] if e["Type"] == 8)
        self.assertIn("ParentIndex", substate)
        self.assertIn("SiblingIndices", substate)
        self.assertEqual(plan["required_map"], "PlotManagerAutoDLC_CON_DH1.StateTransitionMap")
        self.assertFalse(plan["profile"]["implemented_in_game"])
        self.assertEqual(set(dict(resolve_history().choices)) - set(plan["unmapped_choices"]),
                         {a["decision"] for a in plan["actions"] if a["decision"] != "me1.romance.clear"}
                         | {"me1.romance"})

    def test_full_resolved_profile_is_bound_by_existing_history_digest(self):
        first = resolve_history(overrides={"me2.squad.thane.survived": False}).to_slot_data()
        second = resolve_history(overrides={"me2.squad.thane.survived": True}).to_slot_data()
        self.assertNotEqual(history_digest(first), history_digest(second))
        reversed_choices = {**first, "choices": dict(reversed(list(first["choices"].items())))}
        self.assertEqual(history_digest(first), history_digest(reversed_choices))

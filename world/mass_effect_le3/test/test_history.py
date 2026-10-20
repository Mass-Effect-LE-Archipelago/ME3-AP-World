import unittest

from ..history import (ME1_ROMANCES, ME2_ROMANCES, SURVIVORS, VIRMIRE_BUNDLES,
                       inspect_history, inspect_history_snapshot, readback_indices)


class TestHistoryReadback(unittest.TestCase):
    def setUp(self):
        b, i = readback_indices()
        self.bools, self.ints = dict.fromkeys(b, False), dict.fromkeys(i, 0)
        self.bools.update(VIRMIRE_BUNDLES["ashley"])
        self.bools.update({12587: True, 13001: True, 1831: True})

    def read(self):
        return inspect_history(self.bools, self.ints)

    def test_complete_complementary_virmire_bundles(self):
        for survivor, bundle in VIRMIRE_BUNDLES.items():
            with self.subTest(survivor=survivor):
                self.bools.update(bundle)
                self.assertEqual(self.read().values["me1.virmire_survivor"], survivor)
                self.assertFalse(self.read().warnings)
        self.bools[13940] = True
        self.assertTrue(any("rescue/party" in w for w in self.read().warnings))

    def test_me1_romance_requires_flag_and_dialogue_threshold(self):
        for partner, flag, count in ME1_ROMANCES:
            for active, dialogue, expected in ((False, 4, "none"), (True, 3, "none"),
                                               (True, 4, partner), (True, 5, partner)):
                with self.subTest(partner=partner, active=active, dialogue=dialogue):
                    self.bools[flag], self.ints[count] = active, dialogue
                    self.assertEqual(self.read().values["me1.romance"], expected)
            self.bools[flag], self.ints[count] = False, 0

    def test_me2_romance_uses_exact_state_and_retains_native_priority(self):
        for partner, index in ME2_ROMANCES:
            for state in (0, 4, 5, 6):
                self.ints[index] = state
                self.assertEqual(self.read().values["me2.romance"], partner if state == 5 else "none")
            self.ints[index] = 0
        for _, index in ME2_ROMANCES: self.ints[index] = 5
        result = self.read()
        self.assertEqual(result.values["me2.romance"], "miranda")
        self.assertTrue(any("multiple recognized" in w for w in result.warnings))
        # A dead partner does not erase the native reader's relationship result.
        self.bools[SURVIVORS["miranda"]] = False
        self.assertEqual(self.read().values["me2.romance"], "miranda")

    def test_wrex_native_precedence_and_ignored_state(self):
        self.assertEqual(self.read().values["me1.wrex"], "ignored")
        for index in (13028, 13029, 15543):
            self.bools[index] = True
            self.assertEqual(self.read().values["me1.wrex"], "dead")
            self.bools[index] = False
        self.bools.update({13942: True, 13029: True})
        result = self.read()
        self.assertEqual(result.values["me1.wrex"], "alive")
        self.assertTrue(any("death flags" in w for w in result.warnings))

    def test_unset_and_contradictory_outcomes_are_diagnosed(self):
        self.bools.update({12587: False, 13002: True, 2676: True, 2677: True,
                           757: True, 759: True, 1831: False})
        result = self.read()
        self.assertFalse(result.values["me1.rachni_queen_saved"])
        self.assertTrue(result.values["me2.maelon_data_saved"])
        self.assertTrue(result.values["me2.maelon_data_destroyed"])
        self.assertEqual(result.values["me2.heretics"], "rewritten")
        self.assertEqual(result.values["me2.collector_base"], "preserved")
        self.assertEqual(len(result.warnings), 5)
        self.bools.update({1831: True, 1832: True})
        self.assertEqual(self.read().values["me2.collector_base"], "preserved")

    def test_survivor_count_uses_all_twelve_slots(self):
        for count, (partner, index) in enumerate(SURVIVORS.items(), 1):
            self.bools[index] = True
            result = self.read()
            self.assertEqual(result.values["me2.squad_survivor_count"], count)
            self.assertIn(partner, result.values["me2.squad_present"])

    def test_missing_or_malformed_reads_never_become_default_history(self):
        b, i = self.bools.copy(), self.ints.copy()
        del b[13827]
        with self.assertRaisesRegex(ValueError, "Incomplete"): inspect_history(b, i)
        b = self.bools.copy()
        del i[266]
        with self.assertRaisesRegex(ValueError, "Incomplete"): inspect_history(b, i)
        for invalid in (1, "false", None):
            b[13827] = invalid
            with self.assertRaisesRegex(ValueError, "booleans"): inspect_history(b, self.ints)
        for invalid in (True, 2**31, "5", None):
            i = self.ints.copy()
            i[266] = invalid
            with self.assertRaisesRegex(ValueError, "32-bit"): inspect_history(self.bools, i)

    def test_snapshot_adapter_requires_complete_native_integer_reads(self):
        snapshot = {"schema": 1, "game": "LE3",
                    "bools": {str(k): int(v) for k, v in self.bools.items()},
                    "ints": {str(k): v for k, v in self.ints.items()}}
        self.assertEqual(inspect_history_snapshot(snapshot), self.read())
        for invalid in ("1", 2, True, None):
            snapshot["bools"]["13827"] = invalid
            with self.assertRaisesRegex(ValueError, "Invalid bools"): inspect_history_snapshot(snapshot)
        snapshot["bools"]["13827"] = 1
        del snapshot["ints"]["266"]
        with self.assertRaisesRegex(ValueError, "Incomplete"): inspect_history_snapshot(snapshot)
        snapshot["game"] = "LE2"
        with self.assertRaisesRegex(ValueError, "LE3 schema"): inspect_history_snapshot(snapshot)

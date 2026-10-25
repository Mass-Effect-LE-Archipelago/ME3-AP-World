"""Offline ME2 save tests against the owner-supplied saves (skipped if absent)."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from checksum import verify  # noqa: E402
from layout import get_bool, parse  # noqa: E402
from patch import Edit, apply  # noqa: E402

SAVES = sorted((Path(__file__).resolve().parents[2] / "ME2 Saves").glob("*/*.pcsav"))
ENDGAME = next((path for path in SAVES if path.name == "Save_0050.pcsav"), None)


@unittest.skipUnless(SAVES, "owner-supplied ME2 saves not present")
class Me2SaveTests(unittest.TestCase):
    def test_every_supplied_save_verifies_and_parses_to_its_checksum(self):
        for path in SAVES:
            data = path.read_bytes()
            self.assertTrue(verify(data), path.name)
            self.assertEqual(parse(data).body_end, len(data) - 4, path.name)

    @unittest.skipUnless(ENDGAME, "Save_0050 not present")
    def test_collector_base_flip_round_trips(self):
        data = ENDGAME.read_bytes()
        layout = parse(data)
        self.assertEqual(layout.end_game_state, 2)
        self.assertTrue(get_bool(data, layout.plot, 1831))
        edited = apply(data, [Edit("me2", "bool", 1831, 0), Edit("me2", "bool", 1832, 1)])
        self.assertEqual(len(edited), len(data))
        self.assertTrue(verify(edited))
        changed = [i for i, (a, b) in enumerate(zip(data, edited)) if a != b]
        word = layout.plot.bool_words_offset + 4 * (1831 // 32)
        self.assertTrue(all(word <= i < word + 4 or i >= len(data) - 4 for i in changed))

    @unittest.skipUnless(ENDGAME, "Save_0050 not present")
    def test_out_of_range_edits_refused(self):
        data = ENDGAME.read_bytes()
        with self.assertRaises(ValueError):
            apply(data, [Edit("me2", "bool", 10 ** 7, 1)])
        with self.assertRaises(ValueError):
            apply(data[:-1] + b"\0", [])


@unittest.skipUnless(ENDGAME, "Save_0050 not present")
class GeneratedHistoryTests(unittest.TestCase):
    """Generated saves must satisfy the ME3 reader model for every reader fact."""

    @classmethod
    def setUpClass(cls):
        import generate_import_save as generator
        cls.generator = generator
        cls.profile = generator._load("history_profile")
        cls.template = ENDGAME.read_bytes()

    def generate(self, **overrides):
        resolved = self.profile.resolve_history("maximum_content", overrides)
        return self.generator.generate(self.template, dict(resolved.choices))

    def test_default_profile_and_many_variants_read_back(self):
        import random
        rng = random.Random(1)
        self.generate()
        options = {"me1.virmire_survivor": ("ashley", "kaidan"), "me1.wrex": ("alive", "dead", "never_recruited"),
                   "me1.rachni": ("saved", "killed"), "me1.council": ("saved", "sacrificed"),
                   "me1.human_councilor": ("anderson", "udina"), "me1.romance": ("none", "ashley", "liara"),
                   "me2.collector_base": ("destroyed", "preserved"), "me2.romance": ("none", "miranda", "jack", "tali"),
                   "me2.crew_rescue": ("all_saved", "half_saved", "doctor_only"),
                   "me2.liara_relationship": ("not_set", "continued", "ended"),
                   "shepard.origin": ("spacer", "colonist", "earthborn"),
                   "shepard.service_history": ("sole_survivor", "war_hero", "ruthless")}
        for _ in range(200):
            overrides = {key: rng.choice(values) for key, values in options.items()}
            for member in ("thane", "kasumi", "zaeed", "legion", "grunt"):
                state = rng.choice(("alive", "dead", "missing"))
                overrides[f"me2.squad.{member}.recruited"] = state != "missing"
                overrides[f"me2.squad.{member}.survived"] = state == "alive"
                overrides[f"me2.squad.{member}.loyal"] = state != "missing" and rng.random() < 0.5
            overrides["me2.heretics"] = rng.choice(("destroyed", "rewritten")) if overrides["me2.squad.legion.loyal"] \
                else rng.choice(("destroyed", "rewritten", "not_completed"))
            _, report = self.generate(**overrides)
            self.assertGreater(report["edits"], 50)

    def test_template_cannot_express_wrong_sex_romance_or_morinth(self):
        with self.assertRaisesRegex(ValueError, "not available"):
            self.generate(**{"me1.romance": "kaidan"})
        with self.assertRaisesRegex(ValueError, "not available"):
            self.generate(**{"me2.romance": "garrus"})
        with self.assertRaisesRegex(ValueError, "cannot be generated"):
            self.generate(**{"me2.mystic_identity": "morinth"})

    def test_too_few_survivors_refused(self):
        dead = {f"me2.squad.{m}.survived": False for m in
                ("miranda", "jacob", "garrus", "mordin", "grunt", "jack", "thane", "tali", "legion", "mystic", "kasumi")}
        with self.assertRaisesRegex(ValueError, "two squad survivors"):
            self.generate(**dead)


if __name__ == "__main__":
    unittest.main()

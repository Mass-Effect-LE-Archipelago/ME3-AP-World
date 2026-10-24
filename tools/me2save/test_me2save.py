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


if __name__ == "__main__":
    unittest.main()

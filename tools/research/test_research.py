"""Focused parser and source-identity checks; no live-game claims."""
from __future__ import annotations

import csv
from pathlib import Path
import unittest

from tools.research.le3_config_catalog import parse_value
from tools.le3apbridge.probe import difference, parse_assets, snapshot

ROOT = Path(__file__).resolve().parents[2]


class ResearchTests(unittest.TestCase):
    def test_nested_unreal_structs(self):
        self.assertEqual(parse_value('(ModTargets[0]=(TargetID=6,Value=-20),Names=("a,b","c"),Ready=True)'),
                         {"ModTargets[0]": {"TargetID": 6, "Value": -20}, "Names": ["a,b", "c"], "Ready": True})

    def test_bad_structs_are_rejected(self):
        for text in ('(A=1,A=2)', '(A=(1,2)', '(A=1,orphan)', '(A="unterminated)'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_value(text)

    def test_zero_strength_asset_identity_is_retained(self):
        self.assertEqual(parse_assets('2 7:0 3:90'), {"7": 0, "3": 90})
        for text in ('', '2 7:0', '2 7:0 7:1'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_assets(text)

    def test_snapshot_batches_and_tracks_signed_guid(self):
        class Fake:
            def request(self, text):
                if text == 'MAP': return 'BioP_ProMar'
                if text == 'GAW': return '1 7:0'
                if text == 'USES 0 128': return '1 -1:2:3:-4'
                if text.startswith('GETBS '): return ' '.join('1' for _ in text.split()[1:])
                if text.startswith('GETIS '): return '9'
                raise AssertionError(text)
        state = snapshot(Fake(), list(range(130)), [1])
        self.assertEqual(len(state['bools']), 130)
        self.assertEqual(state['used_guids'], ['-1:2:3:-4'])
        after = {**state, 'gaw': {'7': 0, '8': 50}, 'used_guids': ['-1:2:3:-4', '1:2:3:4']}
        changed = difference(state, after)
        self.assertEqual(changed['gaw'], {'8': {'before': None, 'after': 50}})
        self.assertEqual(changed['used_guids_added'], ['1:2:3:4'])

    def test_unlandable_planet_is_not_excluded_from_recovery(self):
        with (ROOT / 'research/le3_exploration_sources.csv').open(encoding='utf-8') as stream:
            rows = list(csv.DictReader(stream))
        bres = next(row for row in rows if row['asset_name'] == 'GAWAsset_SynDiamondHeatSinks')
        self.assertIn('"PlanetLandCondition": 635', bres['explicit_conditions'])
        self.assertEqual(bres['static_disabled'], 'False')
        unnamed = [row for row in rows if not row['asset_name']]
        self.assertTrue(unnamed)
        self.assertTrue(all(row['static_disabled'] == 'True' for row in unnamed))


if __name__ == '__main__':
    unittest.main()

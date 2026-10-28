import unittest

from ..client_core import IdentityMismatch, UnsupportedFeature, synchronize, seed_identity, history_digest
from ..live_bridge import LivePipeBridge
from .. import data


class FakePipe:
    """Native 0.2.2 delivery-dev protocol fake; does not claim engine behavior."""
    def __init__(self):
        self.identity = self.history = None
        self.cursor = self.required = self.intel = 0
        self.credits, self.weapons, self.used, self.gaw, self.bools = 0, set(), [], [], {}
        self.caps = "delivery_dev DEV_SESSION DEV_BIND DEV_TXN DEV_GATE LANDING_GATE WEAPONS GETBS GETIS USES GAW"

    def __enter__(self): return self
    def __exit__(self, *_): pass

    def request(self, text):
        w = text.split()
        if w[0] == "CAPS": return self.caps
        if w[0] == "DEV_SESSION":
            return "1 research_only unbound 0" if self.identity is None else \
                f"1 research_only {self.identity} {self.history} {self.cursor}"
        if w[0] == "DEV_BIND":
            self.identity, self.history = w[1], w[2]
            self.required = int(w[4]) if len(w) == 5 else 0
            return "bound research_only"
        if w[0] == "DEV_GATE":
            state = "unbound" if self.identity is None else ("closed" if self.intel < self.required else "open")
            return f"{self.required} {self.intel} {state}"
        if w[0] == "DEV_TXN":
            assert w[1:3] == [self.identity, self.history]
            index = int(w[3])
            if index < self.cursor: return f"{self.cursor} 0 done"
            assert index == self.cursor
            if w[4] == "INTEL": self.intel += 1
            if w[4] == "CREDITS": self.credits += int(w[5])
            if w[4] == "WEAPON": self.weapons.add(int(w[5]))
            self.cursor += 1
            return f"{self.cursor} 0 applied"
        if w[0] == "GETBS": return " ".join(str(int(self.bools.get(int(i), False))) for i in w[1:])
        if w[0] == "GETIS": return " ".join("0" for _ in w[1:])
        if w[0] == "USES":
            start = int(w[1]); return " ".join([str(len(self.used))] + self.used[start:start + int(w[2])])
        if w[0] == "GAW": return " ".join([str(len(self.gaw))] + self.gaw)
        raise AssertionError(text)


class LiveBridgeTests(unittest.TestCase):
    def setUp(self):
        self.pipe = FakePipe()
        self.identity = seed_identity("seed", 0, 1)
        self.history = history_digest(data.HISTORY)

    def bridge(self, allow_bind=True, required=2):
        return LivePipeBridge(self.identity, self.history, required, allow_bind=allow_bind, connect=lambda: self.pipe)

    def test_binds_delivers_and_reports_checks(self):
        guid_entry = next(e for e in data.LOCATIONS if e.detector["kind"] == "use_guid")
        gaw_entry = next(e for e in data.LOCATIONS if e.detector["kind"] == "gaw_asset")
        self.pipe.used = [guid_entry.detector["guid"]]
        self.pipe.gaw = [f"{gaw_entry.detector['asset_id']}:0"]
        items = [data.ITEM_NAME_TO_ID[data.STARTING_WEAPON], data.ITEM_NAME_TO_ID[data.INTEL],
                 data.ITEM_NAME_TO_ID[data.CREDITS], data.ITEM_NAME_TO_ID[data.INTEL]]
        result = synchronize(self.bridge(), self.identity, data.HISTORY, {guid_entry.id, gaw_entry.id}, items, 2)
        self.assertEqual((self.pipe.identity, self.pipe.history, self.pipe.required), (self.identity, self.history, 2))
        self.assertEqual((self.pipe.cursor, self.pipe.intel, self.pipe.credits, self.pipe.weapons), (4, 2, 1000, {17}))
        self.assertEqual(result.locations, {guid_entry.id, gaw_entry.id})
        again = synchronize(self.bridge(allow_bind=False), self.identity, data.HISTORY, {guid_entry.id}, items, 2)
        self.assertEqual((again.received_index, self.pipe.cursor), (4, 4))

    def test_unlinked_career_needs_explicit_bind(self):
        with self.assertRaises(IdentityMismatch):
            synchronize(self.bridge(allow_bind=False), self.identity, data.HISTORY, set(), [], 2)
        self.assertIsNone(self.pipe.identity)

    def test_foreign_career_and_old_bridge_refused(self):
        self.pipe.identity, self.pipe.history = "a" * 64, self.history
        with self.assertRaises(IdentityMismatch):
            synchronize(self.bridge(), self.identity, data.HISTORY, set(), [], 2)
        self.assertEqual(self.pipe.cursor, 0)
        old = FakePipe(); old.caps = "delivery_dev DEV_SESSION DEV_BIND DEV_TXN"
        self.pipe = old
        with self.assertRaises(UnsupportedFeature):
            synchronize(self.bridge(), self.identity, data.HISTORY, set(), [], 2)

    def test_earth_prologue_never_selected(self):
        self.assertTrue(any(e.region in data.SKIPPED_REGIONS for e in data.LOCATIONS))


if __name__ == "__main__":
    unittest.main()

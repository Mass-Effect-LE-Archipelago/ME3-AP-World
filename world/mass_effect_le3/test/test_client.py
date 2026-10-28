import unittest
from types import SimpleNamespace

from .. import data
from ..client_core import (GameSnapshot, IdentityMismatch, SaveSession, history_digest, observed_locations,
                           seed_identity, synchronize)


class FakeBridge:
    def __init__(self):
        self.identity = seed_identity("test-seed", 0, 1)
        self.history = history_digest(data.HISTORY)
        self.index = 0
        self.credits = 0
        self.gate = False
        self.lost_reply = False
        self.state = GameSnapshot()

    def session(self):
        return SaveSession(self.identity, self.index, self.history)

    def deliver(self, index, operation, amount):
        if index < self.index:
            return self.index
        if index != self.index:
            raise ValueError("gap")
        if operation == "CREDITS":
            self.credits += amount
        elif operation != "COUNTER":
            raise ValueError(operation)
        self.index += 1
        if self.lost_reply:
            self.lost_reply = False
            raise OSError("lost reply after native commit")
        return self.index

    def set_finale_gate(self, opened):
        self.gate = opened

    def snapshot(self, bool_indices, int_indices):
        return self.state


class TestClientCore(unittest.TestCase):
    def test_custom_history_choices_are_part_of_save_identity(self):
        first = {"preset": "custom", "version": 1,
                 "choices": {"me1.virmire_survivor": "ashley", "me2.romance": "none"}}
        second = {**first, "choices": {**first["choices"], "me1.virmire_survivor": "kaidan"}}
        self.assertNotEqual(history_digest(first), history_digest(second))
        bridge = FakeBridge()
        bridge.history = history_digest(first)
        with self.assertRaises(IdentityMismatch):
            synchronize(bridge, bridge.identity, second, set(), [data.ITEM_NAME_TO_ID[data.CREDITS]], 1)
        self.assertEqual((bridge.index, bridge.credits), (0, 0))

    def test_history_digest_is_stable_across_editor_order_and_support_metadata(self):
        first = {"preset": "custom", "version": 1, "choices": {"a": "one", "b": "two"},
                 "implemented_in_game": False}
        second = {"version": 1, "preset": "custom", "choices": {"b": "two", "a": "one"},
                  "implemented_in_game": True}
        self.assertEqual(history_digest(first), history_digest(second))
        with self.assertRaises(ValueError): history_digest({**first, "choices": ["unresolved", "options"]})

    def sync(self, bridge, items, required=1, locations=None):
        return synchronize(bridge, seed_identity("test-seed", 0, 1), data.HISTORY,
                           set() if locations is None else locations, items, required)

    def test_source_detection_and_enabled_filter(self):
        use = next(entry for entry in data.LOCATIONS if entry.detector["kind"] == "use_guid")
        recovery = next(entry for entry in data.LOCATIONS if entry.detector["kind"] == "gaw_asset")
        state = GameSnapshot(used_guids=frozenset({use.detector["guid"]}), gaw_assets=frozenset({recovery.detector["asset_id"]}))
        self.assertEqual(observed_locations(state, {use.id}), {use.id})
        self.assertEqual(observed_locations(state, {use.id, recovery.id}), {use.id, recovery.id})
        self.assertFalse(observed_locations(GameSnapshot(), {use.id, recovery.id}))
        rannoch = data.BY_ID[data.LOCATION_NAME_TO_ID["Codex: The Battle of Rannoch"]]
        self.assertEqual(observed_locations(GameSnapshot(bools={rannoch.detector["indices"][-1]: True}), {rannoch.id}), {rannoch.id})
        self.assertFalse(observed_locations(GameSnapshot(bools={rannoch.detector["indices"][0]: False}), {rannoch.id}))

    def test_mismatched_seed_blocks_reads_and_grants(self):
        bridge = FakeBridge()
        bridge.identity = seed_identity("different-seed", 0, 1)
        with self.assertRaises(IdentityMismatch):
            self.sync(bridge, [data.ITEM_NAME_TO_ID[data.CREDITS]])
        self.assertEqual((bridge.index, bridge.credits), (0, 0))

    def test_mismatched_history_blocks_grants(self):
        bridge = FakeBridge()
        bridge.history = "wrong"
        with self.assertRaises(IdentityMismatch):
            self.sync(bridge, [data.ITEM_NAME_TO_ID[data.CREDITS]])
        self.assertEqual(bridge.index, 0)

    def test_lost_reply_does_not_duplicate_credit_grant(self):
        bridge = FakeBridge()
        bridge.lost_reply = True
        items = [data.ITEM_NAME_TO_ID[data.CREDITS], data.ITEM_NAME_TO_ID[data.INTEL]]
        with self.assertRaises(OSError):
            self.sync(bridge, items)
        result = self.sync(bridge, items)
        self.assertEqual((bridge.credits, result.received_index), (1000, 2))
        self.assertTrue(bridge.gate)

    def test_old_save_replays_only_missing_items(self):
        bridge = FakeBridge()
        items = [data.ITEM_NAME_TO_ID[data.CREDITS], data.ITEM_NAME_TO_ID[data.INTEL]]
        self.sync(bridge, items)
        bridge.index, bridge.credits = 1, 1000
        self.sync(bridge, items)
        self.assertEqual((bridge.credits, bridge.index), (1000, 2))
        bridge.index, bridge.credits = 0, 0
        self.sync(bridge, items)
        self.assertEqual((bridge.credits, bridge.index), (1000, 2))

    def test_unknown_items_are_not_consumed(self):
        bridge = FakeBridge()
        with self.assertRaises(ValueError):
            self.sync(bridge, [data.ITEM_NAME_TO_ID[data.CREDITS], 1])
        self.assertEqual((bridge.credits, bridge.index), (0, 0))

    def test_goal_requires_committed_intel_and_game_completion(self):
        bridge = FakeBridge()
        bridge.state = GameSnapshot(bools={data.GOAL_PLOT_BOOL: True})
        self.assertFalse(self.sync(bridge, []).goal)
        self.assertTrue(self.sync(bridge, [data.ITEM_NAME_TO_ID[data.INTEL]]).goal)

    def test_slot_and_seed_identity_are_distinct(self):
        self.assertNotEqual(seed_identity("a", 0, 1), seed_identity("a", 0, 2))
        self.assertNotEqual(seed_identity("a", 0, 1), seed_identity("b", 0, 1))


class TestNetworkContext(unittest.IsolatedAsyncioTestCase):
    async def test_check_reporting_retries_on_reconnect(self):
        from ..client import ME3Context
        bridge = FakeBridge()
        entry = next(row for row in data.LOCATIONS if row.detector == {"kind": "bool", "index": 18075})
        bridge.state = GameSnapshot(bools={18075: True})
        ctx = ME3Context(bridge=bridge)
        ctx.slot, ctx.team, ctx.server = 1, 0, object()
        ctx.server_locations = {entry.id}
        ctx.items_received = [SimpleNamespace(item=data.ITEM_NAME_TO_ID[data.INTEL])]
        ctx.on_package("RoomInfo", {"seed_name": "test-seed"})
        config = {"slot_data_version": data.SCHEMA_VERSION, "manifest_hash": data.MANIFEST_HASH,
                  "history": data.HISTORY, "locations": [entry.id], "crucible_intel_required": 1}
        ctx.on_package("Connected", {"slot_data": config})
        messages = []
        async def send(payload): messages.extend(payload)
        ctx.send_msgs = send
        await ctx.poll_game()
        await ctx.poll_game()
        self.assertEqual(messages, [{"cmd": "LocationChecks", "locations": [entry.id]}])
        # No server ACK was received. Reconnection must resend the observation.
        ctx.on_package("Connected", {"slot_data": config})
        await ctx.poll_game()
        self.assertEqual(len(messages), 2)

    async def test_research_bridge_never_reports_unbound_checks(self):
        from ..client import ME3Context
        from ..client_core import UnsupportedFeature
        ctx = ME3Context()
        ctx.slot, ctx.team, ctx.server = 1, 0, object()
        ctx.room_seed_name = "test-seed"
        ctx.slot_config = {"history": data.HISTORY, "locations": [], "crucible_intel_required": 1}
        with self.assertRaises(UnsupportedFeature):
            await ctx.poll_game()

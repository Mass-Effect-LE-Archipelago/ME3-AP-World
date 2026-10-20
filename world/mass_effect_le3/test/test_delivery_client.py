import unittest
from types import SimpleNamespace

from .. import data
from ..client_core import BridgeError, IdentityMismatch, UnsupportedFeature, seed_identity
from ..delivery_client import RESEARCH_HISTORY, parse_session, synchronize_research_delivery


class FakeWire:
    """Native protocol fake; integration assertions do not claim engine behavior."""
    def __init__(self, bound=True):
        self.identity = seed_identity("test-seed", 0, 1) if bound else None
        self.history = RESEARCH_HISTORY if bound else None
        self.cursor = self.credits = 0
        self.calls = []
        self.lose_reply = False
        self.readonly = False

    def __enter__(self): return self
    def __exit__(self, *_): pass
    def request(self, text):
        self.calls.append(text)
        words = text.split()
        if words[0] == "CAPS":
            return "readonly DEV_SESSION" if self.readonly else "delivery_dev DEV_SESSION DEV_BIND DEV_TXN"
        if words[0] == "DEV_SESSION":
            if self.identity is None: return "1 research_only unbound 0"
            return f"1 research_only {self.identity} {self.history} {self.cursor}"
        if words[0] == "DEV_BIND":
            if self.identity is not None: raise BridgeError("ERR bound")
            self.identity, self.history = words[1:3]
            return "bound research_only"
        if words[0] == "DEV_TXN":
            if words[1:3] != [self.identity, self.history]: raise BridgeError("ERR identity")
            index = int(words[3])
            if index < self.cursor: return f"{self.cursor} 0 done"
            if index > self.cursor: raise BridgeError(f"ERR gap {self.cursor}")
            delta = int(words[5]) if words[4] == "CREDITS" else 0
            self.credits += delta
            self.cursor += 1
            if self.lose_reply:
                self.lose_reply = False
                raise OSError("Reply lost after commit")
            return f"{self.cursor} {delta} applied"
        raise AssertionError(f"Unexpected native operation: {text}")


class TestResearchDelivery(unittest.TestCase):
    def sync(self, wire, items, **kwargs):
        return synchronize_research_delivery(seed_identity("test-seed", 0, 1), items,
                                             connect=lambda: wire, **kwargs)

    def test_captured_native_session_decodes_full_digests(self):
        # Real 2026-10-15 credit-test reply; preserves leading/high-bit words.
        text = ("1 research_only 491883538a2bbf973ffe4f5c5f15ff7d8fd7247f183225348040a41c325f6b61 "
                "9bfcd8ee209c2ca23a58958f5faa782b33184997ed25e0eee7a102f03f014c5e 1")
        result = parse_session(text)
        self.assertEqual(result.cursor, 1)
        self.assertEqual(result.history, RESEARCH_HISTORY)
        self.assertTrue(result.identity.startswith("49188353"))

    def test_receive_retry_and_old_save_replay(self):
        wire = FakeWire()
        items = [data.ITEM_NAME_TO_ID[data.CREDITS], data.ITEM_NAME_TO_ID[data.INTEL]]
        self.assertEqual(self.sync(wire, items), 2)
        self.assertEqual(self.sync(wire, items), 2)
        self.assertEqual((wire.credits, wire.cursor), (1000, 2))
        wire.credits = wire.cursor = 0
        self.assertEqual(self.sync(wire, items), 2)
        self.assertEqual((wire.credits, wire.cursor), (1000, 2))

    def test_lost_reply_resumes_from_native_cursor(self):
        wire = FakeWire()
        wire.lose_reply = True
        items = [data.ITEM_NAME_TO_ID[data.CREDITS], data.ITEM_NAME_TO_ID[data.INTEL]]
        with self.assertRaises(OSError): self.sync(wire, items)
        self.assertEqual(self.sync(wire, items), 2)
        self.assertEqual(wire.credits, 1000)

    def test_binding_requires_explicit_opt_in(self):
        wire = FakeWire(bound=False)
        with self.assertRaises(IdentityMismatch): self.sync(wire, [])
        self.assertIsNone(wire.identity)
        self.assertEqual(self.sync(wire, [], allow_bind=True), 0)
        self.assertEqual(wire.identity, seed_identity("test-seed", 0, 1))

    def test_wrong_slot_history_and_ahead_cursor_refused(self):
        for field, value in (("identity", seed_identity("test-seed", 0, 2)), ("history", "f" * 64)):
            wire = FakeWire()
            setattr(wire, field, value)
            with self.assertRaises(IdentityMismatch): self.sync(wire, [data.ITEM_NAME_TO_ID[data.CREDITS]])
            self.assertFalse(any(c.startswith("DEV_TXN") or c.startswith("DEV_BIND") for c in wire.calls))
        wire = FakeWire()
        wire.cursor = 2
        with self.assertRaises(BridgeError): self.sync(wire, [data.ITEM_NAME_TO_ID[data.CREDITS]])

    def test_unknown_item_refused_before_binding(self):
        wire = FakeWire(bound=False)
        with self.assertRaises(ValueError):
            self.sync(wire, [data.ITEM_NAME_TO_ID[data.CREDITS], -1], allow_bind=True)
        self.assertEqual(wire.calls, [])

    def test_readonly_bridge_and_malformed_session_refused(self):
        wire = FakeWire()
        wire.readonly = True
        with self.assertRaises(UnsupportedFeature): self.sync(wire, [])
        self.assertEqual(wire.calls, ["CAPS"])
        for text in ("1 production unbound 0", "1 research_only unbound 1",
                     "1 research_only " + "0" * 64 + " " + RESEARCH_HISTORY + " 0",
                     "1 research_only " + "f" * 64 + " " + RESEARCH_HISTORY + " -1"):
            with self.assertRaises(BridgeError): parse_session(text)

    def test_save_change_after_delivery_rejected(self):
        wire = FakeWire()
        original = wire.request
        reads = 0
        def switched(command):
            nonlocal reads
            if command == "DEV_SESSION":
                reads += 1
                if reads == 2: wire.identity = seed_identity("another-seed", 0, 1)
            return original(command)
        wire.request = switched
        with self.assertRaises(IdentityMismatch): self.sync(wire, [data.ITEM_NAME_TO_ID[data.CREDITS]])


class TestDeliveryOnlyNetworkClient(unittest.IsolatedAsyncioTestCase):
    async def test_real_context_receives_without_reporting_checks_or_goal(self):
        from ..client import ME3Context
        wire = FakeWire()
        ctx = ME3Context(delivery_test=True, delivery_connect=lambda: wire)
        ctx.slot, ctx.team, ctx.server = 1, 0, object()
        ctx.room_seed_name = "test-seed"
        ctx.server_locations = {data.LOCATIONS[0].id}
        ctx.slot_config = {"locations": list(ctx.server_locations)}
        ctx.items_received = [SimpleNamespace(item=data.ITEM_NAME_TO_ID[data.CREDITS]),
                              SimpleNamespace(item=data.ITEM_NAME_TO_ID[data.INTEL])]
        messages = []
        async def send(payload): messages.extend(payload)
        ctx.send_msgs = send
        await ctx.poll_game()
        await ctx.poll_game()
        self.assertEqual((ctx.delivery_cursor, wire.credits), (2, 1000))
        self.assertEqual(messages, [])
        self.assertFalse(ctx.finished_game)
        self.assertTrue(all(c.split()[0] in {"CAPS", "DEV_SESSION", "DEV_TXN"} for c in wire.calls))

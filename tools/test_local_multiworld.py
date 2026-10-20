"""Exercise the real AP server/client on loopback with an explicit fake game bridge.

This is a network integration test, not an in-game test. Run with local socket
access; the restricted Windows sandbox can block asyncio's socketpair setup.
"""
import asyncio
import functools
import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
os.environ["AP_TEST_WORLDS"] = "mass_effect_le3"
os.environ["SKIP_REQUIREMENTS_UPDATE"] = "1"
sys.path.insert(0, str(ROOT / "Archipelago-main"))
import websockets
from CommonClient import server_loop
from MultiServer import Context, server
from worlds.mass_effect_le3 import data
from worlds.mass_effect_le3.client import ME3Context
from worlds.mass_effect_le3.client_core import GameSnapshot, SaveSession, history_digest, seed_identity


class FakeGameBridge:
    def __init__(self, seed):
        self.identity = seed_identity(seed, 0, 1)
        self.index = 0
        self.credits = 0
        self.gate = False
        self.state = GameSnapshot()

    def session(self):
        return SaveSession(self.identity, self.index, history_digest(data.HISTORY))

    def deliver(self, index, operation, amount):
        assert index == self.index
        if operation == "CREDITS": self.credits += amount
        elif operation != "COUNTER": raise AssertionError(operation)
        self.index += 1
        return self.index

    def set_finale_gate(self, opened): self.gate = opened
    def snapshot(self, bools, ints): return self.state


async def until(predicate):
    async with asyncio.timeout(8):
        while not predicate():
            await asyncio.sleep(0.02)


async def main():
    seed_file = next((ROOT / "build/development_seed").glob("*.zip"))
    host = Context("127.0.0.1", 0, None, None, 1, 10, False)
    host.load(str(seed_file))
    async with websockets.serve(functools.partial(server, ctx=host), "127.0.0.1", 0) as listener:
        port = listener.sockets[0].getsockname()[1]
        bridge = FakeGameBridge(host.seed_name)
        ctx = ME3Context(f"127.0.0.1:{port}", bridge=bridge)
        ctx.auth = "ME3Developer"
        ctx.server_task = asyncio.create_task(server_loop(ctx))
        try:
            await until(lambda: ctx.slot_config is not None)
            selected = set(ctx.slot_config["locations"])
            pickup = next(entry for entry in data.LOCATIONS if entry.id in selected and entry.detector["kind"] == "use_guid")
            bridge.state = GameSnapshot(used_guids=frozenset({pickup.detector["guid"]}))
            await ctx.poll_game()
            await until(lambda: pickup.id in host.location_checks[(0, 1)] and len(ctx.items_received) == 1)
            await ctx.poll_game()
            await ctx.poll_game()
            assert bridge.index == 1 and bridge.credits == 1000
            assert not bridge.gate
            assert ctx.room_seed_name == host.seed_name
            result = {"server": "real Archipelago loopback", "game_bridge": "fake; no in-game claim",
                      "connected_slot": ctx.slot, "reported_location": pickup.id,
                      "received_index": bridge.index, "credits_granted": bridge.credits,
                      "finale_gate": bridge.gate}
            (ROOT / "research/le3_local_multiworld_receipt.json").write_text(json.dumps(result, indent=2) + "\n")
            print(json.dumps(result, indent=2))
        finally:
            ctx.exit_event.set()
            await ctx.shutdown()


if __name__ == "__main__":
    asyncio.run(main())

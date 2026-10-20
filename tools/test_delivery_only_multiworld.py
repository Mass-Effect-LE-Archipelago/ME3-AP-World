"""Real localhost AP packets -> development client -> explicit fake native protocol.

No game is contacted, and no check/goal packets should be sent.
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
from MultiServer import Context, server, send_items_to, send_new_items
from NetUtils import NetworkItem
from worlds.mass_effect_le3 import data
from worlds.mass_effect_le3.client import ME3Context
from worlds.mass_effect_le3.client_core import seed_identity
from worlds.mass_effect_le3.test.test_delivery_client import FakeWire


async def until(predicate):
    async with asyncio.timeout(8):
        while not predicate(): await asyncio.sleep(0.02)


async def main():
    host = Context("127.0.0.1", 0, None, None, 1, 10, False)
    host.load(str(next((ROOT / "build/development_seed").glob("*.zip"))))
    wire = FakeWire(bound=False)
    async with websockets.serve(functools.partial(server, ctx=host), "127.0.0.1", 0) as listener:
        port = listener.sockets[0].getsockname()[1]
        ctx = ME3Context(f"127.0.0.1:{port}", delivery_test=True, bind_research_save=True,
                         delivery_connect=lambda: wire)
        ctx.auth = "ME3Developer"
        ctx.server_task = asyncio.create_task(server_loop(ctx))
        try:
            await until(lambda: ctx.slot_config is not None)
            await ctx.poll_game()
            assert wire.identity == seed_identity(host.seed_name, 0, 1)
            send_items_to(host, 0, 1, NetworkItem(data.ITEM_NAME_TO_ID[data.CREDITS], -1, 0),
                          NetworkItem(data.ITEM_NAME_TO_ID[data.INTEL], -1, 0))
            send_new_items(host)
            await until(lambda: len(ctx.items_received) == 2)
            await ctx.poll_game()
            await ctx.poll_game()
            assert (wire.credits, wire.cursor) == (1000, 2)
            assert not host.location_checks[(0, 1)] and not ctx.finished_game
            assert all(command.split()[0] in {"CAPS", "DEV_SESSION", "DEV_BIND", "DEV_TXN"} for command in wire.calls)
            receipt = {"server": "real Archipelago loopback", "native_bridge": "fake protocol; no in-game claim",
                       "received_items": len(ctx.items_received), "native_cursor": wire.cursor,
                       "credits": wire.credits, "location_checks": 0, "client_goal_sent": False,
                       "research_binding_matches_room_seed": True}
            (ROOT / "research/le3_delivery_only_multiworld_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
            print(json.dumps(receipt, indent=2))
        finally:
            ctx.exit_event.set()
            await ctx.shutdown()


if __name__ == "__main__": asyncio.run(main())

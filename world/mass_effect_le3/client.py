"""AP client foundation and opt-in, receive-only native delivery testing."""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import logging

from CommonClient import CommonContext, get_base_parser, gui_enabled, handle_url_arg, server_loop
from NetUtils import ClientStatus
import Utils

from . import data
from .client_core import BridgeError, UnsupportedFeature, seed_identity, synchronize
from .client_core import history_digest
from .delivery_client import PipeConnection, synchronize_research_delivery
from .live_bridge import LivePipeBridge

logger = logging.getLogger("ME3Client")


class ResearchBridge:
    """Blocks normal campaigns until initialized history and real gating exist.

    The explicit receive-only test mode uses the development native contract.
    It must not imply a maximum-content history or report campaign checks.
    """
    def session(self):
        raise UnsupportedFeature("The native bridge supports research delivery tests; normal play still needs "
                                 "initialized Shepard history and a real finale gate. Checks and rewards remain disabled here.")


class ME3Context(CommonContext):
    game = data.GAME_NAME
    items_handling = 0b111

    def __init__(self, server_address=None, password=None, bridge=None, *, delivery_test=False,
                 bind_research_save=False, delivery_connect=PipeConnection, live_dev=False, bind_new_career=False):
        self.live_dev = live_dev
        self.bind_new_career = bind_new_career
        self.delivery_test = delivery_test
        self.bind_research_save = bind_research_save
        self.delivery_connect = delivery_connect
        self.delivery_cursor = None
        self.bridge = bridge or ResearchBridge()
        self.slot_config = None
        self.room_seed_name = None
        self.reported = set()
        self._state = None
        super().__init__(server_address, password)

    async def server_auth(self, password_requested=False):
        if password_requested and not self.password:
            await super().server_auth(password_requested)
        await self.get_username()
        await self.send_connect()

    def on_package(self, cmd: str, args: dict) -> None:
        if cmd == "RoomInfo":
            self.room_seed_name = args.get("seed_name")
        if cmd == "Connected":
            config = args.get("slot_data", {})
            if config.get("slot_data_version") != data.SCHEMA_VERSION or config.get("manifest_hash") != data.MANIFEST_HASH:
                self.slot_config = None
                logger.error("Unsupported ME3 slot data or a different source manifest; use the matching apworld")
                return
            self.slot_config = config
            # Server checked state is authoritative; a failed/uncertain send is
            # retried after reconnect rather than suppressed by a local ledger.
            self.reported = set(self.checked_locations)
            self._state = None

    async def poll_game(self):
        actual_seed = self.room_seed_name or getattr(self, "server_seed_name", None)
        if not self.slot_config or self.slot is None or self.team is None or not actual_seed:
            return
        if self.server is None:
            return
        identity = seed_identity(actual_seed, self.team, self.slot)
        config = self.slot_config
        selected = set(config["locations"])
        if selected != set(self.server_locations):
            raise BridgeError("Server location list differs from the ME3 slot manifest")
        if self.delivery_test:
            self.delivery_cursor = await asyncio.to_thread(synchronize_research_delivery, identity,
                [item.item for item in self.items_received], allow_bind=self.bind_research_save,
                connect=self.delivery_connect)
            return  # Explicitly NO source reads, LocationChecks, goal or gate operation.
        bridge = self.bridge
        if self.live_dev:
            bridge = LivePipeBridge(identity, history_digest(config["history"]), config["crucible_intel_required"],
                                    allow_bind=self.bind_new_career, connect=self.delivery_connect)
        result = await asyncio.to_thread(synchronize, bridge, identity, config["history"], selected,
                                         [item.item for item in self.items_received], config["crucible_intel_required"])
        new = set(result.locations) - self.checked_locations - self.reported
        if new:
            await self.send_msgs([{"cmd": "LocationChecks", "locations": sorted(new)}])
            self.reported.update(new)
        if result.goal and not self.finished_game:
            await self.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}])
            self.finished_game = True

    async def bridge_loop(self):
        while not self.exit_event.is_set():
            try:
                await self.poll_game()
                message = ("Waiting for a server slot" if not self.slot_config else
                           f"Research delivery cursor {self.delivery_cursor}; check/goal reporting disabled"
                           if self.delivery_test else "Synchronized")
            except (BridgeError, OSError, ValueError, KeyError) as error:
                message = str(error)
            if message != self._state:
                logger.info(message)
                self._state = message
            await asyncio.sleep(2)


async def _main(args: argparse.Namespace):
    ctx = ME3Context(args.connect, args.password, delivery_test=args.delivery_test,
                     bind_research_save=args.bind_research_save, live_dev=args.live_dev,
                     bind_new_career=args.bind_new_career)
    if args.live_dev:
        logger.warning("LIVE DEVELOPMENT RUN: items, checks and goal are live on the linked career (bridge 0.2.2 delivery-dev)")
    if args.delivery_test:
        logger.warning("RESEARCH DELIVERY ONLY: no Shepard preset initialization, mission unlocks, checks or goal reporting")
    ctx.auth = args.name
    ctx.server_task = asyncio.create_task(server_loop(ctx), name="AP server")
    bridge_task = asyncio.create_task(ctx.bridge_loop(), name="ME3 bridge")
    if gui_enabled and not getattr(args, "nogui", False):
        ctx.run_gui()
    ctx.run_cli()
    try:
        await ctx.exit_event.wait()
    finally:
        bridge_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await bridge_task
        await ctx.shutdown()


def launch(*launch_args: str):
    parser = get_base_parser(description="Mass Effect Legendary Edition 3 experimental AP client")
    parser.add_argument("--name", help="Archipelago slot name")
    parser.add_argument("--delivery-test", action="store_true", help="Receive items through the development bridge; never report checks/goals")
    parser.add_argument("--bind-research-save", action="store_true", help="Explicitly allow binding an unbound disposable save in delivery-test mode")
    parser.add_argument("--live-dev", action="store_true",
                        help="First live run: deliver items and report checks/goal through the delivery-dev bridge")
    parser.add_argument("--bind-new-career", action="store_true",
                        help="With --live-dev: link an unlinked career (the imported seed save) to this slot")
    parser.add_argument("url", nargs="?")
    args = handle_url_arg(parser.parse_args(launch_args or None), parser)
    if args.bind_research_save and not args.delivery_test:
        parser.error("--bind-research-save requires --delivery-test")
    if args.bind_new_career and not args.live_dev:
        parser.error("--bind-new-career requires --live-dev")
    if args.live_dev and args.delivery_test:
        parser.error("--live-dev and --delivery-test are separate modes")
    Utils.init_logging("ME3Client", exception_logger="Client")
    asyncio.run(_main(args))


if __name__ == "__main__":
    launch()

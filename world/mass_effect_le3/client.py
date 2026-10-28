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
            if self.live_dev:
                asyncio.create_task(self.prepare_import_save(config["history"]))
            # Server checked state is authoritative; a failed/uncertain send is
            # retried after reconnect rather than suppressed by a local ledger.
            self.reported = set(self.checked_locations)
            self._state = None

    async def prepare_import_save(self, history: dict) -> None:
        """Write this slot's ME2 import save (once per history) as a new ME2 career for the ME3 creator to import."""
        from .me2save.import_save import ensure_import_career
        try:
            path, created = await asyncio.to_thread(ensure_import_career, history, history_digest(history))
        except Exception as error:  # a missing/unreadable ME2 save must not stop the client
            logger.warning(f"Could not write the ME2 import save: {error}. Finish ME2 LE once (or copy any finished ME2 "
                           "save into your ME2 save folder) and reconnect.")
            return
        career = path.parent.name
        logger.info(f"ME2 import career for this seed: '{career}'{' (just created)' if created else ''}. "
                    "For a new run: ME3 > New Career > Import ME2 Career > that career.")

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
                                         [item.item for item in self.items_received], config["crucible_intel_required"],
                                         frozenset(self.checked_locations | self.reported),
                                         config.get("salvage_price") if config.get("salvage") else None)
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
                     bind_research_save=args.bind_research_save, live_dev=not args.delivery_test,
                     bind_new_career=args.bind_new_career)
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
    parser = get_base_parser(description="Mass Effect Legendary Edition 3 Archipelago client")
    parser.add_argument("--name", help="Archipelago slot name")
    parser.add_argument("--delivery-test", action="store_true", help="Receive items through the development bridge; never report checks/goals")
    parser.add_argument("--bind-research-save", action="store_true", help="Explicitly allow binding an unbound disposable save in delivery-test mode")
    parser.add_argument("--live-dev", action="store_true", help="Accepted for older shortcuts; live play is the default")
    parser.add_argument("--bind-new-career", action="store_true",
                        help="Also link an unlinked career the mod did not mark (development only)")
    parser.add_argument("url", nargs="?")
    args = handle_url_arg(parser.parse_args(launch_args or None), parser)
    if args.bind_research_save and not args.delivery_test:
        parser.error("--bind-research-save requires --delivery-test")
    if args.live_dev and args.delivery_test:
        parser.error("--live-dev and --delivery-test are separate modes")
    Utils.init_logging("ME3Client", exception_logger="Client")
    asyncio.run(_main(args))


if __name__ == "__main__":
    launch()

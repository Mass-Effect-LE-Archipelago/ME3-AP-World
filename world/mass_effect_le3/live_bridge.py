"""Live ItemBridge over the native pipe (first live run 2026-10-27; default client mode since 0.1.0).

Implements client_core.ItemBridge with the 0.2.2 delivery-development contract:
DEV_SESSION/DEV_BIND/DEV_TXN/DEV_GATE plus the read commands. A career is bound only
when it is unbound AND the mod's open start marked it (or binding was explicitly forced); it is bound to the seed identity
and the slot's resolved history digest, with the slot's intel requirement for the
Cronos Station/Earth landing gate. A career bound to anything else is refused.
"""
from __future__ import annotations

import re
from typing import Callable

from . import data
from .client_core import BridgeError, GameSnapshot, IdentityMismatch, SaveSession, UnsupportedFeature
from .delivery_client import PipeConnection

HEX = re.compile(r"[0-9a-f]{64}")
AP_CAREER_BOOL = 26085  # set by the mod's open start (le3mod ApCareerBool)
NEEDED = {"delivery_dev", "DEV_SESSION", "DEV_BIND", "DEV_TXN", "DEV_GATE", "LANDING_GATE", "WEAPONS",
          "GETBS", "GETIS", "USES", "GAW", "SALVAGE"}


class LivePipeBridge:
    def __init__(self, identity: str, history: str, intel_required: int, *, allow_bind: bool,
                 connect: Callable = PipeConnection):
        if not HEX.fullmatch(identity) or not HEX.fullmatch(history):
            raise ValueError("Identity and history must be 64 lowercase hex characters")
        self.identity, self.history, self.intel_required = identity, history, intel_required
        self.allow_bind, self.connect = allow_bind, connect

    def _session(self, pipe) -> tuple[str | None, str | None, int]:
        fields = pipe.request("DEV_SESSION").split()
        if fields[:3] == ["1", "research_only", "unbound"]:
            return None, None, 0
        if len(fields) != 5 or not HEX.fullmatch(fields[2]) or not HEX.fullmatch(fields[3]):
            raise BridgeError("Malformed native session")
        return fields[2], fields[3], int(fields[4])

    def session(self) -> SaveSession:
        with self.connect() as pipe:
            missing = NEEDED - set(pipe.request("CAPS").split())
            if missing:
                raise UnsupportedFeature(f"Installed bridge lacks {sorted(missing)}; install bridge 0.2.2 delivery-dev")
            identity, history, cursor = self._session(pipe)
            if identity is None:
                # Only careers the mod's open start marked (plot bool AP_CAREER_BOOL) are linked, unless forced.
                marked = pipe.request(f"GETBS {AP_CAREER_BOOL}").split() == ["1"]
                if not (marked or self.allow_bind):
                    raise IdentityMismatch("This career wasn't started with the Archipelago mod. Start a New Career in ME3 and "
                                           "import the Archipelago ME2 save the client created")
                pipe.request(f"DEV_BIND {self.identity} {self.history} RESEARCH_ONLY {self.intel_required}")
                identity, history, cursor = self._session(pipe)
            gate = pipe.request("DEV_GATE").split()
            if identity == self.identity and history == self.history and int(gate[0]) != self.intel_required:
                raise BridgeError(f"Career's intel requirement {gate[0]} differs from this slot's {self.intel_required}")
            return SaveSession(identity, cursor, history)

    def deliver(self, index: int, operation: str, amount: int) -> int:
        command = f"DEV_TXN {self.identity} {self.history} {index} {'INTEL' if operation == 'COUNTER' else operation}"
        if operation in ("CREDITS", "WEAPON"):
            command += f" {amount}"
        with self.connect() as pipe:
            fields = pipe.request(command).split()
        if len(fields) != 3 or fields[2] not in ("applied", "done"):
            raise BridgeError(f"Unexpected delivery reply: {' '.join(fields)}")
        return int(fields[0])

    def set_finale_gate(self, opened: bool) -> None:
        # The native gate reads the career's own intel count; nothing to send. Cross-check it.
        with self.connect() as pipe:
            required, received, state = pipe.request("DEV_GATE").split()
        if (state == "open") != opened:
            raise BridgeError(f"Native gate is {state} ({received}/{required}) but the server says opened={opened}")

    def salvage(self, tier: int, caps: list[int]) -> list[int]:
        """Publish salvage caps/tier and take the missions bought since the last call (one game-thread step)."""
        if not 0 <= tier < len(data.SALVAGE_PRICES) or len(caps) != len(data.SALVAGE_MISSIONS):
            raise ValueError("Invalid salvage request")
        with self.connect() as pipe:
            fields = pipe.request(f"DEV_SALVAGE {self.identity} {self.history} {tier} {' '.join(map(str, caps))}").split()
        if not fields or fields[0] != "bought" or any(not f.isdigit() or int(f) >= len(caps) for f in fields[1:]):
            raise BridgeError(f"Unexpected salvage reply: {' '.join(fields)}")
        return [int(f) for f in fields[1:]]

    def snapshot(self, bool_indices: set[int], int_indices: set[int]) -> GameSnapshot:
        with self.connect() as pipe:
            def batched(op: str, indices: list[int]) -> dict[int, int]:
                out = {}
                for start in range(0, len(indices), 64):
                    batch = indices[start:start + 64]
                    values = [int(v) for v in pipe.request(f"{op} {' '.join(map(str, batch))}").split()]
                    if len(values) != len(batch):
                        raise BridgeError("Plot batch count mismatch")
                    out.update(zip(batch, values))
                return out
            bools = {k: bool(v) for k, v in batched("GETBS", sorted(bool_indices)).items()}
            ints = batched("GETIS", sorted(int_indices))
            used, total = [], None
            while total is None or len(used) < total:
                parts = pipe.request(f"USES {len(used)} 128").split()
                if total is not None and int(parts[0]) != total:
                    raise BridgeError("Used-object list changed during a read; retrying")
                total = int(parts[0])
                if not parts[1:] and len(used) < total:
                    raise BridgeError("Used-object page was empty")
                used.extend(parts[1:])
            gaw = pipe.request("GAW").split()
            assets = {int(entry.split(":")[0]) for entry in gaw[1:]}
        return GameSnapshot(bools, ints, frozenset(used), frozenset(assets))

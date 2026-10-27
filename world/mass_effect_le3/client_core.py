"""Transport-independent source detection and save-bound synchronization."""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from typing import Protocol, Sequence

from . import data


class BridgeError(RuntimeError):
    pass


class UnsupportedFeature(BridgeError):
    pass


class IdentityMismatch(BridgeError):
    pass


@dataclass(frozen=True)
class GameSnapshot:
    bools: dict[int, bool] = field(default_factory=dict)
    ints: dict[int, int] = field(default_factory=dict)
    used_guids: frozenset[str] = frozenset()
    gaw_assets: frozenset[int] = frozenset()


@dataclass(frozen=True)
class SaveSession:
    identity: str
    received_index: int
    history_digest: str


class ItemBridge(Protocol):
    def session(self) -> SaveSession: ...
    def deliver(self, index: int, operation: str, amount: int) -> int: ...
    def set_finale_gate(self, opened: bool) -> None: ...
    def snapshot(self, bool_indices: set[int], int_indices: set[int]) -> GameSnapshot: ...


def seed_identity(seed_name: str, team: int, slot: int) -> str:
    if not seed_name or team < 0 or slot <= 0:
        raise ValueError("A server seed name and a valid team/slot are required")
    payload = json.dumps([seed_name, team, slot], separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def history_digest(history: dict) -> str:
    payload = {"preset": history["preset"], "version": history["version"]}
    if "choices" in history:
        if not isinstance(history["choices"], dict):
            raise ValueError("Resolved history choices must be a mapping")
        payload["choices"] = history["choices"]
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def observed_locations(snapshot: GameSnapshot, enabled_ids: set[int]) -> set[int]:
    if enabled_ids - data.BY_ID.keys():
        raise ValueError("Slot contains unknown LE3 location IDs")
    checked = set()
    for location_id in enabled_ids:
        detector = data.BY_ID[location_id].detector
        kind = detector["kind"]
        if kind == "use_guid":
            complete = detector["guid"] in snapshot.used_guids
        elif kind == "gaw_asset":
            complete = detector["asset_id"] in snapshot.gaw_assets
        elif kind == "bool":
            complete = snapshot.bools.get(detector["index"], False)
        elif kind == "int_positive":
            complete = snapshot.ints.get(detector["index"], 0) > 0
        else:
            raise ValueError(f"Unsupported detector {kind}")
        if complete:
            checked.add(location_id)
    return checked


def item_operation(item_id: int) -> tuple[str, int]:
    if item_id == data.ITEM_NAME_TO_ID[data.INTEL]:
        return "COUNTER", 0
    if item_id == data.ITEM_NAME_TO_ID[data.CREDITS]:
        return "CREDITS", 1000
    if item_id in data.WEAPON_ID_TO_NATIVE:
        return "WEAPON", data.WEAPON_ID_TO_NATIVE[item_id]
    raise ValueError(f"Unsupported ME3 item ID {item_id}; it was not consumed")


@dataclass(frozen=True)
class SyncResult:
    locations: frozenset[int]
    goal: bool
    received_index: int
    intel_count: int


def synchronize(bridge: ItemBridge, identity: str, history: dict, enabled_ids: set[int],
                received_item_ids: Sequence[int], intel_required: int) -> SyncResult:
    # Refuse a mismatched/unsupported save before any writes OR location reports.
    session = bridge.session()
    if session.identity != identity:
        raise IdentityMismatch("Loaded career belongs to another seed or slot")
    if session.history_digest != history_digest(history):
        raise IdentityMismatch("Loaded career does not match this slot's Shepard history")
    if not 0 <= session.received_index <= len(received_item_ids):
        raise BridgeError("Save received index does not match the server item list")
    if intel_required < 1 or enabled_ids - data.BY_ID.keys():
        raise ValueError("Invalid slot goal or location list")
    operations = [item_operation(item_id) for item_id in received_item_ids]
    index = session.received_index
    while index < len(operations):
        operation, amount = operations[index]
        committed = bridge.deliver(index, operation, amount)
        if committed != index + 1:
            raise BridgeError("Native item transaction returned an invalid committed index")
        index = committed
    intel = sum(item_id == data.ITEM_NAME_TO_ID[data.INTEL] for item_id in received_item_ids[:index])
    ready = intel >= intel_required
    bridge.set_finale_gate(ready)
    bools, ints = {data.GOAL_PLOT_BOOL}, set()
    for location_id in enabled_ids:
        detector = data.BY_ID[location_id].detector
        if detector["kind"] == "bool": bools.add(detector["index"])
        if detector["kind"] == "int_positive": ints.add(detector["index"])
    state = bridge.snapshot(bools, ints)
    return SyncResult(frozenset(observed_locations(state, enabled_ids)),
                      ready and state.bools.get(data.GOAL_PLOT_BOOL, False), index, intel)

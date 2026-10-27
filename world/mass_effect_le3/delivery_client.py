"""Opt-in AP-to-native research delivery. Never evaluates checks or goals."""
from __future__ import annotations

from dataclasses import dataclass
import ctypes
from ctypes import wintypes
import hashlib
import os
import re
from typing import Callable, Sequence

from .client_core import BridgeError, IdentityMismatch, UnsupportedFeature, item_operation

RESEARCH_HISTORY = hashlib.sha256(b"research_existing_save_v1_NOT_maximum_content").hexdigest()
HEX = re.compile(r"[0-9a-fA-F]{64}\Z")


class PipeConnection:
    """One local message-mode connection. Instantiate inside the polling worker."""
    def __enter__(self):
        if os.name != "nt": raise UnsupportedFeature("Native ME3 delivery requires Windows")
        api = ctypes.WinDLL("kernel32", use_last_error=True)
        api.WaitNamedPipeW.argtypes, api.WaitNamedPipeW.restype = [wintypes.LPCWSTR, wintypes.DWORD], wintypes.BOOL
        api.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                                   wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        api.CreateFileW.restype = wintypes.HANDLE
        api.SetNamedPipeHandleState.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p, ctypes.c_void_p]
        api.SetNamedPipeHandleState.restype = wintypes.BOOL
        api.ReadFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
        api.ReadFile.restype = wintypes.BOOL
        api.WriteFile.argtypes, api.WriteFile.restype = api.ReadFile.argtypes, wintypes.BOOL
        api.CloseHandle.argtypes, api.CloseHandle.restype = [wintypes.HANDLE], wintypes.BOOL
        name = r"\\.\pipe\LE3APBridge"
        if not api.WaitNamedPipeW(name, 1000): raise BridgeError("ME3 bridge is unavailable; load the research test save")
        self.api = api
        self.handle = api.CreateFileW(name, 0xC0000000, 0, None, 3, 0, None)
        if self.handle == ctypes.c_void_p(-1).value: raise ctypes.WinError(ctypes.get_last_error())
        try:
            mode = wintypes.DWORD(2)
            if not api.SetNamedPipeHandleState(self.handle, ctypes.byref(mode), None, None):
                raise ctypes.WinError(ctypes.get_last_error())
            if self.request("HELLO 1") != "1 LE3 readonly": raise BridgeError("Unexpected LE3 bridge handshake")
        except BaseException:
            api.CloseHandle(self.handle)
            raise
        return self

    def __exit__(self, *_): self.api.CloseHandle(self.handle)

    def request(self, command: str) -> str:
        encoded = command.encode("ascii")
        if not encoded or len(encoded) > 4096: raise BridgeError("Invalid native request length")
        sent, size = wintypes.DWORD(), wintypes.DWORD()
        if not self.api.WriteFile(self.handle, encoded, len(encoded), ctypes.byref(sent), None):
            raise ctypes.WinError(ctypes.get_last_error())
        if sent.value != len(encoded): raise BridgeError("Short native pipe write")
        buffer = ctypes.create_string_buffer(65536)
        if not self.api.ReadFile(self.handle, buffer, len(buffer), ctypes.byref(size), None):
            raise ctypes.WinError(ctypes.get_last_error())
        reply = buffer.raw[:size.value].decode("utf-8")
        if reply == "OK": return ""
        if not reply.startswith("OK "): raise BridgeError(reply)
        return reply[3:]


@dataclass(frozen=True)
class ResearchSession:
    identity: str | None
    history: str | None
    cursor: int


def parse_session(reply: str) -> ResearchSession:
    fields = reply.split()
    if fields == ["1", "research_only", "unbound", "0"]: return ResearchSession(None, None, 0)
    if (len(fields) != 5 or fields[:2] != ["1", "research_only"]
            or not HEX.fullmatch(fields[2]) or not HEX.fullmatch(fields[3])
            or int(fields[2], 16) == 0 or int(fields[3], 16) == 0):
        raise BridgeError("Unsupported or malformed native research session")
    try: cursor = int(fields[4])
    except ValueError as error: raise BridgeError("Invalid native delivery cursor") from error
    if not 0 <= cursor <= 1000000: raise BridgeError("Native delivery cursor out of range")
    return ResearchSession(fields[2].lower(), fields[3].lower(), cursor)


def synchronize_research_delivery(identity: str, received_ids: Sequence[int], *, allow_bind: bool = False,
                                  connect: Callable = PipeConnection) -> int:
    """Receive-only development mode. Does not initialize history or unlock anything."""
    if not HEX.fullmatch(identity) or int(identity, 16) == 0: raise ValueError("Invalid research seed identity")
    identity = identity.lower()
    # Refuse unsupported items BEFORE any binding or partial delivery.
    operations = [item_operation(item_id) for item_id in received_ids]
    with connect() as pipe:
        capabilities = set(pipe.request("CAPS").split())
        if not {"delivery_dev", "DEV_SESSION", "DEV_TXN"} <= capabilities:
            raise UnsupportedFeature("Install the explicit delivery-development bridge to receive test items")
        # Refuse before any binding or partial delivery.
        if any(operation == "WEAPON" for operation, _ in operations) and "WEAPONS" not in capabilities:
            raise UnsupportedFeature("Installed bridge cannot deliver weapons; install bridge 0.2.2 or newer")
        session = parse_session(pipe.request("DEV_SESSION"))
        if session.identity is None:
            if not allow_bind:
                raise IdentityMismatch("Research save is unbound; binding requires --bind-research-save")
            if "DEV_BIND" not in capabilities: raise UnsupportedFeature("Native bridge cannot bind a research save")
            pipe.request(f"DEV_BIND {identity} {RESEARCH_HISTORY} RESEARCH_ONLY")
            session = parse_session(pipe.request("DEV_SESSION"))
        if session.identity != identity or session.history != RESEARCH_HISTORY:
            raise IdentityMismatch("Research save belongs to another seed/slot or history; never rebind it")
        if session.cursor > len(operations): raise BridgeError("Save cursor is ahead of the server's received list")
        # Gate-capable bridges count Crucible Intel natively; older ones only advance the cursor.
        if "LANDING_GATE" in capabilities:
            operations = [("INTEL", 0) if operation == "COUNTER" else (operation, amount) for operation, amount in operations]
        cursor = session.cursor
        while cursor < len(operations):
            operation, amount = operations[cursor]
            command = f"DEV_TXN {identity} {RESEARCH_HISTORY} {cursor} {operation}"
            if operation in ("CREDITS", "WEAPON"): command += f" {amount}"
            granted_limit = amount if operation == "CREDITS" else 0  # WEAPON's amount is a weapon id, not credits
            fields = pipe.request(command).split()
            try:
                if (len(fields) != 3 or int(fields[0]) != cursor + 1 or fields[2] not in ("applied", "done")
                        or not 0 <= int(fields[1]) <= granted_limit or (fields[2] == "done" and fields[1] != "0")):
                    raise ValueError("Unexpected delivery acknowledgement")
            except ValueError as error: raise BridgeError("Malformed native delivery acknowledgement; resync before retry") from error
            cursor += 1
        final = parse_session(pipe.request("DEV_SESSION"))
        if final != ResearchSession(identity, RESEARCH_HISTORY, cursor):
            raise IdentityMismatch("Loaded research save changed during synchronization")
        return cursor

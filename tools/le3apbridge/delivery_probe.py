"""Explicit developer-only delivery spike; never connects to an AP server."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from probe import Connection, snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("inspect", "bind-test-save", "credits", "counter"))
    parser.add_argument("output", type=Path, help="New receipt path; existing files are not overwritten")
    parser.add_argument("--seed", default="ME3 native delivery development test 1")
    parser.add_argument("--team", type=int, default=0)
    parser.add_argument("--slot", type=int, default=1)
    parser.add_argument("--index", type=int, help="Explicit item index; never auto-advances across retries")
    parser.add_argument("--amount", type=int, default=1000)
    args = parser.parse_args()
    if args.output.exists(): parser.error("Receipt already exists")
    if args.action in ("credits", "counter") and (args.index is None or not 0 <= args.index < 1000000):
        parser.error("Delivery requires an explicit --index 0..999999")
    if not 1 <= args.amount <= 1000000: parser.error("Amount must be 1..1000000")
    if not args.seed or args.team < 0 or args.slot < 1: parser.error("A nonempty seed and valid team/slot are required")
    identity = hashlib.sha256(json.dumps([args.seed, args.team, args.slot],
        separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    history = hashlib.sha256(b"research_existing_save_v1_NOT_maximum_content").hexdigest()
    result = {"utc": datetime.now(timezone.utc).isoformat(), "action": args.action,
              "research_only": True, "server_contacted": False, "identity": identity, "history": history}
    with Connection() as connection:
        capabilities = connection.request("CAPS").split()
        if "DEV_SESSION" not in capabilities: raise RuntimeError("Installed bridge has no delivery-development interface")
        result["version"] = connection.request("VER")
        result["session_before"] = connection.request("DEV_SESSION")
        result["wallet_before"] = list(map(int, connection.request("DEV_WALLET").split()))
        if args.action != "inspect" and "DEV_BIND" not in capabilities:
            raise RuntimeError("Installed research build has delivery writes disabled")
        if args.action == "bind-test-save":
            reference = Path(__file__).resolve().parents[2] / "research/live_earth_reloaded_01.json"
            expected = json.loads(reference.read_text())
            observed = snapshot(connection, [], [])
            if (observed["map"].lower() != expected["map"].lower()
                    or not set(expected["used_guids"]) <= set(observed["used_guids"])):
                raise RuntimeError("Loaded gameplay does not match the witnessed Earth pickup test save; no binding performed")
            result["test_save_markers_matched"] = True
            result["reply"] = connection.request(f"DEV_BIND {identity} {history} RESEARCH_ONLY")
        if args.action in ("credits", "counter"):
            before = snapshot(connection, [], [])
            operation = f"CREDITS {args.amount}" if args.action == "credits" else "COUNTER"
            command = f"DEV_TXN {identity} {history} {args.index} {operation}"
            result["first_reply"] = connection.request(command)
            result["wallet_after_first"] = list(map(int, connection.request("DEV_WALLET").split()))
            result["retry_reply"] = connection.request(command)
            result["wallet_after_retry"] = list(map(int, connection.request("DEV_WALLET").split()))
            result["retry_balance_unchanged"] = result["wallet_after_first"] == result["wallet_after_retry"]
            result["actual_credit_delta"] = result["wallet_after_first"][0] - result["wallet_before"][0]
            after = snapshot(connection, [], [])
            result["used_guids_before"] = before["used_guids"]
            result["used_guids_after"] = after["used_guids"]
            result["gaw_unchanged"] = before["gaw"] == after["gaw"]
            result["source_guids_unchanged"] = before["used_guids"] == after["used_guids"]
            first_fields, retry_fields = result["first_reply"].split(), result["retry_reply"].split()
            result["cursor_reply_valid"] = (len(first_fields) == 3 and len(retry_fields) == 3
                and int(first_fields[0]) >= args.index + 1 and first_fields[0] == retry_fields[0]
                and first_fields[2] in ("applied", "done") and retry_fields[1:] == ["0", "done"])
            result["grant_delta_valid"] = result["actual_credit_delta"] == int(first_fields[1])
        result["session_after"] = connection.request("DEV_SESSION")
        result["wallet_after"] = list(map(int, connection.request("DEV_WALLET").split()))
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2); stream.write("\n")
    print(json.dumps(result, indent=2))
    if any(result.get(key) is False for key in ("retry_balance_unchanged", "source_guids_unchanged", "cursor_reply_valid", "grant_delta_valid")):
        raise RuntimeError("Delivery invariant failed; receipt retained")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError) as error:
        raise SystemExit(str(error)) from None

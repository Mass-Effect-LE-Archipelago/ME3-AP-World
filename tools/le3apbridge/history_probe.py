"""Read-only vanilla history summary; never initializes or binds a career."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys

from probe import Connection, snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New receipt path; never overwrite earlier evidence")
    parser.add_argument("--from-snapshot", type=Path, help="Offline analysis of an existing complete LE3 snapshot")
    args = parser.parse_args()
    if args.output.exists(): parser.error("Receipt already exists")
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location("le3_history", root / "world/mass_effect_le3/history.py")
    history = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = history
    spec.loader.exec_module(history)
    if args.from_snapshot:
        observed = json.loads(args.from_snapshot.read_text(encoding="utf-8"))
    else:
        bools, ints = history.readback_indices()
        with Connection() as connection:
            observed = snapshot(connection, sorted(bools), sorted(ints))
    decoded = history.inspect_history_snapshot(observed)
    receipt = {"schema": 1, "utc": datetime.now(timezone.utc).isoformat(),
               "read_only": True, "server_contacted": False, "history_initialized": False,
               "scope": "current_native_major_plot_readers_not_complete_imported_profile",
               "input_snapshot": str(args.from_snapshot.resolve()) if args.from_snapshot else None,
               "live_game_contacted": args.from_snapshot is None,
               "snapshot": observed, "recognized": decoded.values, "warnings": decoded.warnings}
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"receipt": str(args.output.resolve()), "recognized": decoded.values,
                      "warnings": decoded.warnings}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError) as error:
        raise SystemExit(str(error)) from None

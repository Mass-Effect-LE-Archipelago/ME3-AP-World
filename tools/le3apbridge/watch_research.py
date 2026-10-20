"""Bounded read-only gameplay capture. Saves changed states, never sends AP checks."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from probe import Connection, snapshot, difference

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New directory; existing observations are never overwritten")
    parser.add_argument("--seconds", type=int, default=180)
    parser.add_argument("--interval", type=float, default=5)
    parser.add_argument("--plot-prefix", default="LE3.End_Game.")
    args = parser.parse_args()
    if not 1 <= args.seconds <= 3600 or not 1 <= args.interval <= 60:
        parser.error("seconds must be 1..3600; interval must be 1..60")
    bools, ints = {22426}, set()
    for row in json.loads((ROOT / "world/mass_effect_le3/locations.json").read_text()):
        detector = row["detector"]
        if detector["kind"] == "bool": bools.add(detector["index"])
        elif detector["kind"] == "int_positive": ints.add(detector["index"])
    plot_names = {}
    with (ROOT / "research/le3_plot_inventory.csv").open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if not row["path"].startswith(args.plot_prefix): continue
            if row["family"] not in ("bools", "ints"): continue
            index = int(row["plot_id"])
            (bools if row["family"] == "bools" else ints).add(index)
            plot_names[f"{row['family']}:{index}"] = row["path"]
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "session.json").write_text(json.dumps({
        "started_utc": datetime.now(timezone.utc).isoformat(), "seconds": args.seconds,
        "interval": args.interval, "read_only": True, "plot_names": plot_names,
        "bools": sorted(bools), "ints": sorted(ints)}, indent=2) + "\n")
    deadline, previous, sequence, errors = time.monotonic() + args.seconds, None, 0, 0
    while time.monotonic() < deadline:
        try:
            with Connection() as connection:
                state = snapshot(connection, sorted(bools), sorted(ints))
            delta = difference(previous, state) if previous else None
            changed = previous is None or delta["before_map"] != delta["after_map"] or any(
                delta[key] for key in ("bools", "ints", "gaw", "used_guids_added", "used_guids_removed"))
            if changed:
                sequence += 1
                (args.output / f"state_{sequence:04d}.json").write_text(json.dumps(state, indent=2) + "\n")
                if delta:
                    (args.output / f"delta_{sequence:04d}.json").write_text(json.dumps(delta, indent=2) + "\n")
                print(json.dumps({"state": sequence, "map": state["map"], "used_guids": len(state["used_guids"]),
                    "changed_bools": delta["bools"] if delta else {},
                    "changed_ints": delta["ints"] if delta else {},
                    "changed_gaw": delta["gaw"] if delta else {}}), flush=True)
                previous = state
        except (OSError, RuntimeError, ValueError) as error:
            errors += 1
            with (args.output / "errors.jsonl").open("a") as stream:
                stream.write(json.dumps({"utc": datetime.now(timezone.utc).isoformat(), "error": str(error)}) + "\n")
            print(json.dumps({"transient_read_error": str(error)}), flush=True)
        time.sleep(min(args.interval, max(0, deadline - time.monotonic())))
    (args.output / "completed.json").write_text(json.dumps({"finished_utc": datetime.now(timezone.utc).isoformat(),
        "changed_states_saved": sequence, "read_errors": errors}, indent=2) + "\n")
    print(f"Capture complete: {sequence} changed states, {errors} read errors", flush=True)


if __name__ == "__main__":
    main()

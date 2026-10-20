"""Read the career-trace observer ring and summarize new-career ordering.

Read-only: sends only HELLO/VER/CAPS/CAREER_TRACE, which the bridge answers on
the pipe thread without HUD dispatch. Never initializes history or binds a save.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

METHODS = {0: "none", 1: "FinalCommit", 2: "SetPlotChoices", 3: "CreateCareer",
           4: "SetNewGamePlotStates", 5: "UpdatePlayerSaveRecord"}
ROUTES = {0: "event", 1: "internal", 2: "call_function"}
TABLES = {0: "unavailable", 1: "world_accessor", 2: "default_context", 3: "instance_context"}
# Bit order matches CareerTrace::Plots.
PLOTS = (13827, 13828, 13940, 13939)
FIELDS = ("sequence", "invocation", "thread", "route", "method", "leaving",
          "depth", "origin", "table", "valid", "values")


def parse_page(reply: str) -> dict:
    """Parse an `OK 1 career_trace_readonly mask oldest latest count records...` reply."""
    parts = reply.split()
    if len(parts) < 7 or parts[:3] != ["OK", "1", "career_trace_readonly"]:
        raise ValueError(f"Unexpected career trace reply: {reply[:80]}")
    mask, oldest, latest, count = (int(value) for value in parts[3:7])
    raw = parts[7:]
    if len(raw) != count:
        raise ValueError("Career trace record count mismatch")
    records = []
    for item in raw:
        values = item.split(":")
        if len(values) != len(FIELDS):
            raise ValueError("Malformed career trace record")
        record = dict(zip(FIELDS, (int(value) for value in values)))
        if record["method"] not in METHODS or record["route"] not in ROUTES or record["table"] not in TABLES:
            raise ValueError("Unknown career trace enum value")
        records.append(record)
    if [r["sequence"] for r in records] != sorted({r["sequence"] for r in records}):
        raise ValueError("Career trace sequences are not strictly increasing")
    return {"target_mask": mask, "oldest": oldest, "latest": latest, "records": records}


def read_all(request, after: int = 0) -> dict:
    """Page from `after` to the latest record; report any ring overwrite gap."""
    records, mask, gap = [], 0, None
    oldest = latest = 0
    while True:
        page = parse_page("OK " + request(f"CAREER_TRACE {after} 64"))
        mask, oldest, latest = page["target_mask"], page["oldest"], page["latest"]
        if page["records"] and page["records"][0]["sequence"] != after + 1 and gap is None:
            gap = {"expected": after + 1, "first_available": page["records"][0]["sequence"]}
        records.extend(page["records"])
        if not page["records"]:
            break
        after = page["records"][-1]["sequence"]
    return {"target_mask": mask, "oldest": oldest, "latest": latest, "gap": gap, "records": records}


def plots(record: dict) -> dict[str, bool | None]:
    return {str(index): (bool(record["values"] >> bit & 1) if record["valid"] >> bit & 1 else None)
            for bit, index in enumerate(PLOTS)}


def analyze(trace: dict) -> dict:
    """Describe each outermost FinalCommit and whether the candidate seam was observed.

    One script call can appear through several routes (event/call_function and
    internal); `routes` lists them so a later executor can pick exactly one.
    """
    records = trace["records"]
    commits, findings = [], []
    previews = [r for r in records if r["method"] == 4 and r["table"] == 3 and not r["leaving"]]
    open_commit = None
    for record in records:
        name = METHODS[record["method"]]
        if record["method"] == 1 and not record["leaving"] and record["depth"] == 1 and open_commit is None:
            open_commit = {"thread": record["thread"], "origin": record["origin"], "events": [], "complete": False}
        if open_commit is None or record["thread"] != open_commit["thread"]:
            continue
        open_commit["events"].append({"sequence": record["sequence"], "invocation": record["invocation"],
                                      "method": name, "route": ROUTES[record["route"]],
                                      "phase": "leave" if record["leaving"] else "enter",
                                      "table": TABLES[record["table"]], "plots": plots(record)})
        if record["method"] == 1 and record["leaving"] and record["depth"] == 1:
            open_commit["complete"] = True
            commits.append(open_commit)
            open_commit = None
    if open_commit:
        commits.append(open_commit)
    for commit in commits:
        order = []
        for event in commit["events"]:
            key = (event["method"], event["phase"])
            if not order or order[-1] != key:
                order.append(key)
        commit["order"] = [f"{method}:{phase}" for method, phase in order]
        commit["routes"] = sorted({f"{e['method']}:{e['route']}" for e in commit["events"]})
        choices_left = [i for i, key in enumerate(order) if key == ("SetPlotChoices", "leave")]
        saved = [i for i, key in enumerate(order) if key == ("UpdatePlayerSaveRecord", "enter")]
        commit["seam_observed"] = bool(choices_left and saved and choices_left[-1] < saved[0])
        after_choices = [e for e in commit["events"] if e["method"] == "SetPlotChoices" and e["phase"] == "leave"]
        commit["virmire_after_plot_choices"] = after_choices[-1]["plots"] if after_choices else None
        if not commit["complete"]:
            findings.append("FinalCommit has not returned; trace may still be in progress")
    if trace.get("gap"):
        findings.append("Ring buffer overwrote records before they were read")
    if trace["target_mask"] != 31:
        findings.append(f"Not every target function resolved (mask {trace['target_mask']})")
    return {"commits": commits, "preview_tables_initialized": len(previews), "findings": findings}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New receipt path; never overwrite earlier evidence")
    parser.add_argument("--after", type=int, default=0, help="Only read records after this sequence")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Receipt already exists")
    from probe import Connection
    with Connection() as connection:
        version = connection.request("VER")
        if "career-trace" not in version or "CAREER_TRACE" not in connection.request("CAPS").split():
            raise RuntimeError(f"Installed bridge is not the career-trace profile ({version})")
        trace = read_all(connection.request, args.after)
    receipt = {"schema": 1, "utc": datetime.now(timezone.utc).isoformat(), "read_only": True,
               "history_initialized": False, "server_contacted": False, "bridge_version": version,
               "trace": trace, "analysis": analyze(trace)}
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    summary = receipt["analysis"]
    print(json.dumps({"receipt": str(args.output.resolve()), "records": len(trace["records"]),
                      "commits": [{k: c[k] for k in ("origin", "complete", "seam_observed", "order",
                                                     "virmire_after_plot_choices")} for c in summary["commits"]],
                      "findings": summary["findings"]}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError) as error:
        raise SystemExit(str(error)) from None

"""Inventory the local LEX LE3 plot DB without executing or modifying game files.

Run from the project root: python tools/research/le3_plot_inventory.py
Outputs are research candidates, never an approved AP location list.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]


def load_database(dll: Path) -> tuple[dict, bytes]:
    data = dll.read_bytes()
    offset = 0
    # Managed embedded resources contain several complete ZIP archives. Locate
    # their end records; ZipFile accounts for the preceding PE bytes itself.
    while (offset := data.find(b"PK\x05\x06", offset)) >= 0:
        try:
            with zipfile.ZipFile(io.BytesIO(data[:offset + 22])) as archive:
                if "le3.json" in archive.namelist():
                    raw = archive.read("le3.json")
                    return json.loads(raw), raw
        except zipfile.BadZipFile:
            pass
        offset += 4
    raise ValueError(f"No embedded le3.json archive in {dll}")


def inventory(database: dict) -> list[dict]:
    # LEX uses strings for organizational IDs and integers for leaf IDs.
    elements = {int(e["elementid"]): e for entries in database.values() for e in entries}

    def full_path(element: dict) -> str:
        labels, seen = [], set()
        while element is not None:
            key = int(element["elementid"])
            if key in seen:
                raise ValueError(f"Cycle in plot ancestry: {key}")
            seen.add(key)
            labels.append(element["label"])
            element = elements.get(int(element.get("parentelementid", 0)))
        return ".".join(reversed(labels))

    rows = []
    for family in ("bools", "ints", "floats"):
        for element in database[family]:
            path = full_path(element)
            legacy = any(x in path.split(".") for x in ("ME1_Plots_for_ME3", "ME2_Plots_for_ME3"))
            tags = []
            if not legacy:
                patterns = {
                    "journal": r"\.(?:Side_Journals|Critpath_Journals)\.",
                    "fetch_quest": r"\.New_Fetch_Quests\.",
                    "codex": r"codex",
                    "text_messages": r"\.ME3_Texts\.",
                    "war_asset_related": r"GAW|War_Asset|Readiness|Military_Strength",
                    "intel": r"\.Intel_Rewards\.",
                    "store": r"\.Stores\.",
                    "pickup_hint": r"Treasure|Credit|Loot|Medigel|Medi_Gel|Salvage|Pickup|Picked_Up|Cache",
                    "collectible": r"\.Cabin\.|Model_Ships|Dogtag|Dog_Tag|Hamster|Fish|Space_Chess",
                    "completion_hint": r"Complete|Finished|Resolved",
                    "combat_simulator": r"\.CmbtSim\.",
                    "social": r"\.RP_Plots\.|\.Apartment\.|\.Light_Characters\.",
                }
                tags = [name for name, regex in patterns.items() if re.search(regex, path, re.I)]
            rows.append({
                "family": family, "plot_id": element["plotid"], "element_id": element["elementid"],
                "path": path, "legacy_import": legacy,
                "review_hint": bool(re.search(r"deprecated|deleted|debug|test_|unused", path, re.I)),
                "candidate_tags": ";".join(tags), "status": "DB_ONLY",
            })
    return rows


def main() -> None:
    dll = ROOT / "Legendary Explorer/LegendaryExplorerCore.dll"
    database, raw = load_database(dll)
    rows = inventory(database)
    output = ROOT / "research"
    output.mkdir(exist_ok=True)
    with (output / "le3_plot_inventory.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    candidates = [row for row in rows if row["candidate_tags"]]
    with (output / "le3_check_candidates.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(candidates)
    summary = {
        "source": str(dll.relative_to(ROOT)),
        "dll_sha256": hashlib.sha256(dll.read_bytes()).hexdigest(),
        "le3_json_sha256": hashlib.sha256(raw).hexdigest(),
        "database_counts": {key: len(value) for key, value in database.items()},
        "state_rows": len(rows),
        "legacy_import_rows": sum(row["legacy_import"] for row in rows),
        "nonlegacy_state_rows": sum(not row["legacy_import"] for row in rows),
        "candidate_rows": len(candidates),
        "overlapping_candidate_tags": dict(Counter(tag for row in candidates for tag in row["candidate_tags"].split(";"))),
        "me2_bool_range_collisions": [row for row in rows if row["family"] == "bools" and 21000 <= row["plot_id"] <= 21999],
        "warning": "Heuristic discovery only. Counts overlap and include branches, dead content and non-check states. No runtime verification.",
    }
    (output / "le3_plot_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in summary.items() if key != "me2_bool_range_collisions"}, indent=2))
    print("ME2 bool-range collisions:", len(summary["me2_bool_range_collisions"]))


if __name__ == "__main__":
    main()

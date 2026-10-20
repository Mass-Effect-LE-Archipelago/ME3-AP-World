"""Join LE3 config, map, mount, English name and plot evidence.

This produces source candidates, not Archipelago locations. Run after the probe
and config/plot inventory tools; see README.md for the full pipeline.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research"
sys.path.insert(0, str(ROOT))
from tools.research.le3_plot_inventory import load_database


def json_lines(name: str) -> list[dict]:
    return [json.loads(line) for line in (OUT / name).read_text(encoding="utf-8-sig").splitlines()]


def relative(source: str) -> str:
    path = Path(source)
    return path.resolve().relative_to(ROOT).as_posix()


def priority(source: str, mounts: dict[str, int]) -> int:
    parts = relative(source).split("/")
    return mounts[parts[parts.index("DLC") + 1]] if "DLC" in parts else 0


def write_csv(name: str, rows: list[dict]) -> None:
    with (OUT / name).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    mounts = {Path(row["source"]).parent.parent.name: row["priority"] for row in json_lines("le3_mounts.jsonl")}
    texts = defaultdict(list)
    for row in json_lines("le3_catalog_strings.jsonl"):
        if row["text"]:
            texts[row["id"]].append(row)

    def name(ref: int) -> str:
        values = texts.get(ref, [])
        if not values:
            return ""
        top = max(priority(row["source"], mounts) for row in values)
        options = {row["text"] for row in values if priority(row["source"], mounts) == top}
        # TLKs include gender variants; preserve any differences explicitly.
        return " / ".join(sorted(options))

    plots = list(csv.DictReader((OUT / "le3_plot_inventory.csv").open(encoding="utf-8")))
    bools = {int(row["plot_id"]): row["path"] for row in plots if row["family"] == "bools"}
    declarations = json.loads((OUT / "le3_config_declarations.json").read_text(encoding="utf-8"))["declarations"]
    assets = [row for row in declarations if row["property"] == "allassets"]
    asset_by_name = {row["data"]["AssetName"].casefold(): row["data"] for row in assets}
    asset_by_id = {row["data"]["ID"]: row["data"] for row in assets}
    if len(asset_by_id) != len(assets) or len(asset_by_name) != len(assets):
        raise ValueError("Duplicate asset declarations need explicit config merge resolution")
    modifiers, asset_rows = [], []
    for row in assets:
        data = row["data"]
        states = [value for key, value in data.items() if key.startswith("UnlockPlotStates") and value]
        targets = [value for key, value in data.items() if key.startswith("ModTargets")]
        for target in targets:
            modifiers.append({"modifier_id": data["ID"], "modifier_name": data["AssetName"],
                "target_id": target["TargetID"], "target_name": asset_by_id.get(target["TargetID"], {}).get("AssetName", ""),
                "value": target["Value"], "source": row["source"], "status": "CONFIG_ONLY"})
        asset_rows.append({"candidate_key": f"gaw:{data['ID']}", "asset_id": data["ID"],
            "asset_name": data["AssetName"], "display_name": name(data.get("GUIName", 0)),
            "type": data.get("Type", "").casefold(), "exploration": data.get("bIsExploration", False),
            "emitted_bools": ";".join(str(value) for value in states),
            "emitted_bool_paths": ";".join(bools.get(value, f"UNRESOLVED:{value}") for value in states),
            "modifier_values": ";".join(str(target["Value"]) for target in targets),
            "source": row["source"], "status": "CONFIG_ONLY"})
    objects = json_lines("le3_map_objects.jsonl")
    map_sources = {row["source"] for row in objects}
    top = max(priority(source, mounts) for source in map_sources)
    winners = [source for source in map_sources if priority(source, mounts) == top]
    if len(winners) != 1:
        raise ValueError(f"Cannot resolve map package winner: {winners}")
    winner = winners[0]
    selected = {row["object_path"]: row for row in objects if row["source"] == winner}
    recoveries = []
    plot_db, _ = load_database(ROOT / "Legendary Explorer/LegendaryExplorerCore.dll")
    false_conditions = {entry["plotid"] for entry in plot_db["conditionals"] if entry.get("code", "").strip().casefold() == "false"}
    for row in selected.values():
        if row["class_name"] != "SFXPlanetFeatureGAWAsset":
            continue
        asset_name = row["properties"].get("AssetName", "")
        asset = asset_by_name.get(asset_name.casefold(), {})
        parent = row["object_path"].rsplit(".", 1)[0]
        ancestors = []
        while parent in selected:
            ancestors.append(selected[parent])
            parent = parent.rsplit(".", 1)[0]
        labels = {ancestor["class_name"]: name(ancestor["properties"].get("DisplayName", 0)) for ancestor in ancestors}
        conditions = {ancestor["object_path"]: {key: value for key, value in ancestor["properties"].items()
                      if key in ("VisibleConditional", "VisibleParameter", "UsableConditional", "UsableParameter", "PlanetLandCondition")}
                      for ancestor in [row] + ancestors}
        recoveries.append({"candidate_key": f"map:{Path(winner).stem}:{row['object_path']}",
            "cluster": labels.get("SFXCluster", ""), "system": labels.get("SFXSystem", ""),
            "planet": labels.get("BioPlanet", ""), "feature": name(row["properties"].get("DisplayName", 0)),
            "asset_name": asset_name, "asset_id": asset.get("ID", ""),
            "asset_type": asset.get("Type", ""), "exploration": asset.get("bIsExploration", ""),
            "source": relative(winner), "export": row["export"], "object_path": row["object_path"],
            "explicit_conditions": json.dumps(conditions, sort_keys=True),
            "static_disabled": any(value in false_conditions for fields in conditions.values()
                                   for key, value in fields.items() if key in ("VisibleConditional", "UsableConditional")),
            "status": "PACKAGE_AND_CONFIG" if asset else "UNRESOLVED_ASSET"})
    write_csv("le3_gaw_candidates.csv", asset_rows)
    write_csv("le3_gaw_modifiers.csv", modifiers)
    write_csv("le3_exploration_sources.csv", recoveries)
    summary = {"asset_candidates": len(asset_rows), "modifier_target_edges": len(modifiers),
        "negative_modifier_edges": sum(row["value"] < 0 for row in modifiers),
        "unresolved_modifier_targets": sum(not row["target_name"] for row in modifiers),
        "assets_with_nonzero_emitted_bools": sum(bool(row["emitted_bools"]) for row in asset_rows),
        "assets_with_resolved_names": sum(bool(row["display_name"]) for row in asset_rows),
        "winning_local_map": relative(winner), "winning_map_priority": top,
        "exploration_source_candidates": len(recoveries),
        "unique_exploration_asset_names": len({row["asset_name"].casefold() for row in recoveries}),
        "unresolved_exploration_assets": sum(row["status"] == "UNRESOLVED_ASSET" for row in recoveries),
        "named_resolved_exploration_candidates": sum(bool(row["asset_name"]) and row["status"] == "PACKAGE_AND_CONFIG" and not row["static_disabled"] for row in recoveries),
        "exploration_types": dict(Counter(row["asset_type"] for row in recoveries)),
        "warning": "Local official-backup mount precedence only. No runtime evidence; conditions, defaults and mutually exclusive content remain to trace."}
    (OUT / "le3_source_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

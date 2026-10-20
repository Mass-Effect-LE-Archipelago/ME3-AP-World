"""Resolve local package override versions and catalog reward source objects."""
from __future__ import annotations

from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.research.le3_source_catalog import OUT, json_lines, priority, relative, write_csv


def main() -> None:
    objects = json_lines("le3_reward_sources.jsonl")
    mounts = {Path(row["source"]).parent.parent.name: row["priority"] for row in json_lines("le3_mounts.jsonl")}
    candidates = defaultdict(set)
    for row in objects:
        candidates[Path(row["source"]).name.casefold()].add(row["source"])
    winners = {}
    for filename, sources in candidates.items():
        top = max(priority(source, mounts) for source in sources)
        chosen = [source for source in sources if priority(source, mounts) == top]
        if len(chosen) != 1:
            raise ValueError(f"Unresolved mount tie for {filename}")
        winners[filename] = chosen[0]
    # A higher-mounted copy can contain no matching reward objects. It still
    # overrides the original; therefore inspect all PCC names, not just hits.
    for path in (ROOT / "ME3LE Backup/BioGame").rglob("*.pcc"):
        key = path.name.casefold()
        if key in winners and priority(str(path), mounts) > priority(winners[key], mounts):
            winners[key] = str(path)
    selected = [row for row in objects if relative(row["source"]).casefold() == relative(winners[Path(row["source"]).name.casefold()]).casefold()]
    uses, awards, xp = [], [], []
    for row in selected:
        props, cls = row["properties"], row["class_name"]
        origin = {"source": relative(row["source"]), "export": row["export"], "object_path": row["object_path"]}
        if "UseModule" in cls:
            guid = props.get("UseModuleGUID", {})
            valid = len(guid) == 4 and all(isinstance(guid.get(key), int) and guid[key] != 0 for key in "ABCD")
            key = ":".join(str(guid[key]) for key in "ABCD") if valid else ""
            uses.append({**origin, "candidate_key": "use:" + key if key else "", "guid": key,
                "class_name": cls, "explicit_reward_type": props.get("TreasureType", "<inherited>"),
                "weapon_class": json.dumps(props.get("WeaponClass", {})),
                "weapon_mod_class": json.dumps(props.get("WeaponModClass", {})),
                "armor": json.dumps(props.get("ArmorPiece", "")),
                "world_instance": row["object_path"].casefold().startswith("theworld.persistentlevel."),
                "status": "SAVED_GUID_CANDIDATE" if valid else "GUID_NEEDS_DEFAULT_TRACE"})
        elif cls.startswith("SFXSeqAct_AwardGAWAsset"):
            awards.append({**origin, "class_name": cls, "asset_name": props.get("AssetName", ""),
                           "explicit_id": props.get("Id", ""), "status": "SEQUENCE_NEEDS_FLOW_TRACE"})
        elif cls.startswith("BioSeqAct_GiveMissionXP"):
            xp.append({**origin, "reward_amount": props.get("RewardAmount", "<inherited>"),
                "objective_strref": props.get("ObjectiveStringRef", ""), "combat_token": props.get("CombatToken", ""),
                "combat_experience": props.get("bCombatExperience", "<inherited>"),
                "status": "SEQUENCE_NEEDS_FLOW_TRACE"})
    write_csv("le3_saved_pickup_sources.csv", uses)
    write_csv("le3_gaw_award_sources.csv", awards)
    write_csv("le3_objective_reward_sources.csv", xp)
    guids = Counter(row["guid"] for row in uses if row["guid"] and row["world_instance"])
    summary = {"raw_reward_objects": len(objects), "mounted_reward_objects": len(selected),
        "mounted_counts": dict(Counter(row["class_name"] for row in selected)),
        "use_module_sources": len(uses), "distinct_world_use_guids": len(guids),
        "shared_guid_groups": sum(value > 1 for value in guids.values()),
        "use_modules_without_explicit_valid_guid": sum(not row["guid"] for row in uses),
        "gaw_award_nodes": len(awards), "objective_xp_nodes": len(xp),
        "warning": "These are mounted source candidates. Inherited defaults, reachability, GUID persistence, successful-use semantics and sequence flow require validation; do not sum into a check count."}
    (OUT / "le3_reward_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

"""Turn the read-only LEX coalesced extraction into research catalogs.

Input: research/le3_config_sections.jsonl (Le3Probe --config).
No mount precedence or runtime reachability is inferred from declarations.
"""
from __future__ import annotations

from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]


def split_outer(text: str, separator: str) -> list[str]:
    """Split only outside Unreal's nested parentheses and quoted strings."""
    result, start, depth, quoted, escaped = [], 0, 0, False, False
    for index, char in enumerate(text):
        if escaped:
            escaped = False
        elif quoted and char == "\\":
            escaped = True
        elif char == '"':
            quoted = not quoted
        elif not quoted:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth < 0:
                    raise ValueError("Unbalanced parentheses")
            elif char == separator and depth == 0:
                result.append(text[start:index].strip())
                start = index + 1
    if quoted or depth:
        raise ValueError("Unterminated quoted string or parentheses")
    result.append(text[start:].strip())
    return result


def parse_value(text: str):
    text = text.strip()
    if text.startswith("(") and text.endswith(")"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        parts = split_outer(inner, ",")
        fields = [split_outer(part, "=") for part in parts]
        if all(len(field) == 2 for field in fields):
            result = {}
            for key, value in fields:
                if key in result:
                    raise ValueError(f"Duplicate struct field {key}")
                result[key] = parse_value(value)
            return result
        if any(len(field) != 1 for field in fields):
            raise ValueError(f"Mixed struct and array: {text}")
        return [parse_value(part) for part in parts]
    if text.startswith('"'):
        if not text.endswith('"'):
            raise ValueError("Unterminated string")
        return re.sub(r'\\(["\\])', r'\1', text[1:-1])
    if text.lower() in ("true", "false"):
        return text.lower() == "true"
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    if re.fullmatch(r"-?\d+\.\d+", text):
        return float(text)
    return text


def csv_write(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"No rows for {path}")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    output = ROOT / "research"
    sections = [json.loads(line) for line in (output / "le3_config_sections.jsonl").read_text(encoding="utf-8-sig").splitlines()]
    declarations, hashes = [], {}
    for section in sections:
        source = Path(section["source"])
        if not source.is_absolute():
            source = ROOT / source
        source = source.resolve()
        relative = source.relative_to(ROOT).as_posix()
        hashes[relative] = hashlib.sha256(source.read_bytes()).hexdigest()
        xml = ET.fromstring(section["section"])
        for prop in xml.findall("Property"):
            values = list(prop.findall("Value")) or [prop]
            for ordinal, value in enumerate(values):
                declarations.append({
                    "source": relative, "ini": section["file"], "section": xml.attrib["name"],
                    "property": prop.attrib["name"], "ordinal": ordinal,
                    "config_action": int(value.attrib["type"]),
                    "data": parse_value(value.text or ""),
                })
    (output / "le3_config_declarations.json").write_text(json.dumps({
        "source_sha256": hashes, "declarations": declarations,
        "status": "CONFIG_ONLY", "mount_resolution": "not performed",
    }, indent=2) + "\n", encoding="utf-8")
    assets, levels, treasure = [], [], []
    for declaration in declarations:
        prop, data = declaration["property"], declaration["data"]
        provenance = {key: declaration[key] for key in ("source", "config_action", "ordinal")}
        if prop == "allassets":
            assets.append({**provenance, "asset_id": data["ID"], "asset_name": data["AssetName"],
                "type": data.get("Type", ""), "subtype": data.get("SubType", ""),
                "starting_strength": data.get("StartingStrength", ""),
                "name_strref": data.get("GUIName", ""),
                "exploration": data.get("bIsExploration", False),
                "unlock_states_raw": json.dumps({k: v for k, v in data.items() if k.startswith("UnlockPlotStates")}),
                "modifier_targets_raw": json.dumps({k: v for k, v in data.items() if k.startswith("ModTargets")}),
                "description": data.get("DebugConditionalDescription", ""), "status": "CONFIG_ONLY"})
        elif prop == "leveltreasure":
            levels.append({**provenance, "level": data["Level"], "level_enum": data.get("LevelEnum", ""),
                "plot_id": data.get("PlotId", ""), "xp": data.get("XP", 0),
                "credits": data.get("Credits", 0), "alliance_credits": data.get("AllianceCredits", 0),
                "status": "CONFIG_ONLY"})
            for field in ("Treasure", "ConditionalGAWAssets", "UndetectableGAWAssets"):
                seen = Counter()
                for index, item in enumerate(data.get(field, [])):
                    if not isinstance(item, str):
                        raise ValueError(f"Unexpected treasure value: {item}")
                    seen[item.casefold()] += 1
                    treasure.append({**provenance, "level": data["Level"], "kind": field,
                        "entry": index, "reward": item, "casefold_occurrence": seen[item.casefold()],
                        "status": "CONFIG_ONLY"})
    csv_write(output / "le3_gaw_assets.csv", assets)
    csv_write(output / "le3_level_rewards.csv", levels)
    csv_write(output / "le3_treasure_entries.csv", treasure)
    summary = {
        "source_count": len(hashes), "declaration_count": len(declarations),
        "asset_declarations": len(assets), "distinct_asset_ids": len({row["asset_id"] for row in assets}),
        "asset_types": dict(Counter(row["type"] for row in assets)),
        "modifier_declarations": sum(row["modifier_targets_raw"] != "{}" for row in assets),
        "exploration_asset_declarations": sum(row["exploration"] for row in assets),
        "level_reward_declarations": len(levels), "treasure_entry_declarations": len(treasure),
        "treasure_entries_by_kind": dict(Counter(row["kind"] for row in treasure)),
        "casefold_duplicate_entries_in_same_list": sum(row["casefold_occurrence"] > 1 for row in treasure),
        "warning": "Definitions are not checks. Mount precedence, source interactions, unlock semantics and reachability remain to verify.",
    }
    (output / "le3_config_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

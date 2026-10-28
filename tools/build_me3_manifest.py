"""Build the source-backed LE3 manifest; preserve every assigned location ID/name."""
from __future__ import annotations

from collections import Counter
import csv
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "world/mass_effect_le3/locations.json"
RESEARCH = ROOT / "research"
BASE = 0x4D331000
REGIONS = {
    "proear": ("Earth Prologue", ""), "promar": ("Mars", ""),
    "krogar": ("Palaven", ""), "kro001": ("Sur'Kesh", ""), "kro002": ("Tuchanka", ""),
    "kron7a": ("Tuchanka: Turian Platoon", ""), "kron7b": ("Tuchanka: Bomb", ""),
    "krogru": ("Attican Traverse", ""), "omgjck": ("Grissom Academy", ""),
    "cat001": ("Eden Prime", "From Ashes"), "cat002": ("Thessia", ""),
    "cat003": ("Citadel Coup", ""), "cat004": ("Cerberus Headquarters", ""),
    "gth001": ("Geth Dreadnought", ""), "gth002": ("Rannoch", ""),
    "gthn7a": ("Rannoch: Admiral Koris", ""), "gthleg": ("Rannoch: Fighter Squadrons", ""),
    "cerjcb": ("Ex-Cerberus Scientists", ""), "cermir": ("Sanctuary", ""),
    "citsam": ("Ardat-Yakshi Monastery", ""), "end001": ("Earth Finale", ""),
    "mpcer": ("N7: Cerberus Lab", ""), "mpnov": ("N7: Cerberus Fighter Base", ""),
    "mprctr": ("N7: Fuel Reactors", ""), "mpdish": ("N7: Communication Hub", ""),
    "spdish": ("N7: Communication Hub", ""), "mpslum": ("N7: Cerberus Abductions", ""),
    "mptowr": ("N7: Cerberus Attack", ""),
    **{f"lev{i:03}": ("Leviathan", "Leviathan") for i in range(1, 5)},
    **{key: ("Omega", "Omega") for key in ("omg001", "omg02a", "omg003", "omg004")},
    **{f"cit{i:03}": ("Citadel DLC", "Citadel") for i in range(1, 5)},
}


def rows(name: str) -> list[dict]:
    with (ROOT / "research" / name).open(encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def words(value: str) -> str:
    value = re.sub(r"^\d+", "", value).replace("_", " ").strip()
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value).strip()


def candidates() -> list[dict]:
    result = []
    for source in sorted(rows("le3_saved_pickup_sources.csv"), key=lambda row: row["candidate_key"]):
        if not source["guid"] or source["world_instance"] != "True":
            continue
        stem = Path(source["source"]).stem
        pieces = stem.split("_")
        key = pieces[1].casefold()
        if key not in REGIONS:
            raise ValueError(f"Unmapped pickup mission {stem}")
        region, dlc = REGIONS[key]
        cls = source["class_name"]
        if "WeaponMod" in cls:
            category, detail = "mods", json.loads(source["weapon_mod_class"]).get("path", "").split(".")[-1].removeprefix("SFXWeaponMod_")
        elif "Armor" in cls:
            category, detail = "armor", json.loads(source["armor"]).removeprefix("ArmorTreasure_")
        elif "Weapon" in cls:
            category, detail = "weapons", json.loads(source["weapon_class"]).get("path", "").split(".")[-1].removeprefix("SFXWeapon_")
        elif source["explicit_reward_type"] == "CREDITS_TREASURE":
            category, detail = "credits", "Credit Cache"
        else:
            category, detail = "supplies", "Supply Cache"
        area = words("_".join(pieces[2:])) or "Mission Area"
        result.append({"key": source["candidate_key"], "name": f"{region}: {area} - {words(detail) or category.title()}",
            "region": region, "category": category, "dlc": dlc,
            "detector": {"kind": "use_guid", "guid": source["guid"]},
            "progression_safe": False, "evidence": "PACKAGE_AND_SCRIPT", "source": source["source"],
            "notes": "Availability and full-inventory behavior require runtime validation; filler-only."})
    for source in rows("le3_exploration_sources.csv"):
        if not source["asset_name"] or source["static_disabled"] == "True":
            continue
        result.append({"key": "explore:" + source["asset_name"].casefold(),
            "name": f"{source['cluster']}: {source['system']} / {source['planet']} - {source['feature']}",
            "region": "Galaxy Exploration", "category": "exploration", "dlc": "",
            "detector": {"kind": "gaw_asset", "asset_id": int(source["asset_id"])},
            "progression_safe": False, "evidence": "PACKAGE_AND_CONFIG", "source": source["source"],
            "notes": "Recovery only; does not create a second asset-recruitment check. Filler-only until deadline audit."})
    # The dedicated completion flags are DB-backed candidates; all remain runtime-unverified.
    story = [
        ("Earth Prologue", "Priority: Earth - Escape", "bool", 18075, True),
        ("Mars", "Priority: Mars - Complete", "bool", 20552, True),
        ("Palaven", "Priority: Palaven - Complete", "int_positive", 10213, True),
        ("Sur'Kesh", "Priority: Sur'Kesh - Complete", "int_positive", 10178, True),
        ("Tuchanka", "Priority: Tuchanka - Complete", "int_positive", 10179, True),
        ("Citadel Coup", "Priority: Citadel II - Complete", "bool", 19453, True),
        ("Geth Dreadnought", "Priority: Geth Dreadnought - Complete", "int_positive", 10172, True),
        ("Rannoch", "Priority: Rannoch - Complete", "int_positive", 10173, True),
        ("Thessia", "Priority: Thessia - Complete", "int_positive", 10184, True),
        ("Sanctuary", "Priority: Horizon - Complete", "int_positive", 10188, True),
        ("Cerberus Headquarters", "Priority: Cerberus Headquarters - Complete", "int_positive", 10185, False),
    ]
    for region, name, kind, plot, safe in story:
        result.append({"key": f"story:{kind}:{plot}", "name": name, "region": region, "category": "story", "dlc": "",
            "detector": {"kind": kind, "index": plot}, "progression_safe": safe,
            "evidence": "DB_ONLY", "source": "LEX le3.json", "notes": "Completion predicate requires in-game observation."})
    # Individually named Mars objective completion states. Started/active and branch flags are omitted.
    for source in rows("le3_plot_inventory.csv"):
        if source["family"] != "bools" or not source["path"].startswith("LE3.Prologue.ProMar.Objectives.") or not source["path"].endswith("_Complete"):
            continue
        title = words(source["path"].split(".")[-1].removesuffix("_Complete"))
        result.append({"key": "objective:bool:" + source["plot_id"], "name": f"Mars: Objective - {title}", "region": "Mars",
            "category": "objectives", "dlc": "", "detector": {"kind": "bool", "index": int(source["plot_id"])},
            "progression_safe": True, "evidence": "DB_ONLY", "source": source["path"],
            "notes": "Named completion state; mandatory-path status and persistence require runtime validation."})
    result.extend(codex())
    return result


CODEX_DLC = {"DLC_EXP_Pack001": ("Leviathan", "Leviathan"), "DLC_EXP_Pack002": ("Omega", "Omega"),
             "DLC_HEN_PR": ("Eden Prime", "From Ashes")}
# Where a page's setter lives decides its region; the Normandy and the Citadel hub come first (always revisitable).
CODEX_HUBS = {"nor": "Normandy", "cithub": "Citadel", "omg000": "Omega", "omghub": "Omega"}


def codex() -> list[dict]:
    """Codex pages a vanilla conversation or Kismet transition grants (research/le3_codex_setters.tsv, from le3mod
    boolsetters over every runtime-winning package; page ids from the BioCodexMaps, titles from the INT TLKs).
    Pages with the same title are one check (any variant bool). Pages only the skipped Earth prologue grants are left
    out. Codex pages can come from optional conversations, so they never hold progression."""
    pages = {row[0]: row for row in (line.rstrip("\n").split("\t") for line in (RESEARCH / "le3_codex_pages.tsv").open(encoding="utf-8"))}
    titles = dict(line.rstrip("\n").split("\t", 1) for line in (RESEARCH / "le3_codex_titles.tsv").open(encoding="utf-8"))
    codes: dict[str, set[str]] = {}
    for source in csv.DictReader((RESEARCH / "le3_codex_setters.tsv").open(encoding="utf-8"), delimiter="\t"):
        code = re.match(r"(?:BioD_|BioP_|BioA_)?([A-Za-z0-9]+)_", source["package"]).group(1).lower()
        codes.setdefault(source["bool"], set()).add(code)
    grouped: dict[str, dict] = {}
    for page, found in sorted(codes.items(), key=lambda item: int(item[0])):
        found = found - {"proear"}
        if not found:
            continue
        dlc_folder = pages[page][3] if len(pages[page]) > 3 else ""
        if dlc_folder:
            region, dlc = CODEX_DLC[dlc_folder]
        else:
            hub = next((CODEX_HUBS[code] for code in CODEX_HUBS if code in found), None)
            region, dlc = hub or REGIONS[min(found)][0], "" if hub else REGIONS[min(found)][1]
        title = titles[pages[page][1]].strip('"')
        entry = grouped.setdefault(title, {"key": f"codex:{page}", "name": f"Codex: {title}", "region": region,
            "category": "codex", "dlc": dlc, "detector": {"kind": "bool_any", "indices": []}, "progression_safe": False,
            "evidence": "PACKAGE_AND_DB", "source": "research/le3_codex_setters.tsv",
            "notes": "Codex page plot bool(s); granted by " + ", ".join(sorted(found)) + ". Needs a live false-before/true-after check."})
        entry["detector"]["indices"].append(int(page))
    return list(grouped.values())


def main() -> None:
    found = candidates()
    existing = json.loads(DEST.read_text(encoding="utf-8")) if DEST.exists() else []
    old = {row["key"]: row for row in existing}
    if len(old) != len(existing) or len({row["key"] for row in found}) != len(found):
        raise ValueError("Duplicate source key")
    missing = old.keys() - {row["key"] for row in found}
    if missing:
        raise ValueError(f"Existing IDs require explicit retirement rather than deletion: {missing}")
    next_id = max((row["id"] for row in existing), default=BASE - 1) + 1
    used_names = {row["name"] for row in existing}
    for row in sorted(found, key=lambda value: value["key"]):
        if row["key"] in old:
            row["id"], row["name"] = old[row["key"]]["id"], old[row["key"]]["name"]
        else:
            proposed = row["name"]
            suffix = 2
            while row["name"] in used_names:
                row["name"] = f"{proposed} {suffix}"
                suffix += 1
            row["id"] = next_id
            next_id += 1
        used_names.add(row["name"])
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(json.dumps(sorted(found, key=lambda row: row["id"]), indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(found)} stable source locations: {dict(Counter(row['category'] for row in found))}")


if __name__ == "__main__":
    main()

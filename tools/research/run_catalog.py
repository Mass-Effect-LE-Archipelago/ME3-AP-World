"""Rebuild the LE3 offline catalogs from the supplied backup and LEX libraries."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research"
PROBE = ROOT / "tools/research/Le3Probe"
REWARD_PATTERN = r"^(SFXSeqAct_AwardGAWAsset(_Silent)?|SFXSeqAct_AwardTreasure|SFXSeqAct_GiveWeapon|SFXTreasureNode|BioSeqAct_GiveMissionXP.*|SFX(Treasure|Weapon|WeaponMod|Armor)UseModule(_BonusWeapon)?|SFXSeqAct_AwardGAWAssetsForLevel)$"


def probe(output: str, *arguments: str, log: str | None = None) -> None:
    with (OUT / output).open("w", encoding="utf-8") as stream:
        if log:
            with (OUT / log).open("w", encoding="utf-8") as errors:
                subprocess.run(["dotnet", "run", "--no-build", "--project", str(PROBE), "--", *arguments],
                               cwd=ROOT, stdout=stream, stderr=errors, check=True)
        else:
            subprocess.run(["dotnet", "run", "--no-build", "--project", str(PROBE), "--", *arguments],
                           cwd=ROOT, stdout=stream, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-reward-scan", action="store_true", help="reuse the existing reward scan; do not use after changing the backup")
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    subprocess.run(["dotnet", "build", str(PROBE), "--verbosity", "quiet"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "tools/research/le3_plot_inventory.py"], cwd=ROOT, check=True)
    game = ROOT / "ME3LE Backup/BioGame"
    configs = [game / "CookedPCConsole/Coalesced.bin", *sorted((game / "DLC").rglob("Default_*.bin"))]
    probe("le3_config_sections.jsonl", "--config", *map(str, configs))
    subprocess.run([sys.executable, "tools/research/le3_config_catalog.py"], cwd=ROOT, check=True)
    probe("le3_mounts.jsonl", "--mounts", str(game / "DLC"))
    maps = sorted(game.rglob("BioD_Nor_203aGalaxyMap.pcc"))
    probe("le3_map_objects.jsonl", "--objects", r"^(SFXPlanetFeatureGAWAsset|SFXCluster|SFXSystem|BioPlanet)$", *map(str, maps))
    declarations = json.loads((OUT / "le3_config_declarations.json").read_text())["declarations"]
    refs = {row["data"]["GUIName"] for row in declarations if row["property"] == "allassets" and "GUIName" in row["data"]}
    for line in (OUT / "le3_map_objects.jsonl").read_text().splitlines():
        value = json.loads(line)["properties"].get("DisplayName")
        if isinstance(value, int):
            refs.add(value)
    refs_path = OUT / "le3_catalog_name_refs.json"
    refs_path.write_text(json.dumps(sorted(refs)), encoding="utf-8")
    tlks = sorted(path for path in game.rglob("*_INT.tlk") if "_Test_" not in path.name)
    probe("le3_catalog_strings.jsonl", "--strings", str(refs_path), *map(str, tlks))
    subprocess.run([sys.executable, "tools/research/le3_source_catalog.py"], cwd=ROOT, check=True)
    if not args.skip_reward_scan:
        probe("le3_reward_sources.jsonl", "--scan-objects", REWARD_PATTERN, str(game), log="le3_reward_scan.log")
    elif not (OUT / "le3_reward_sources.jsonl").is_file():
        parser.error("no existing reward scan to reuse")
    subprocess.run([sys.executable, "tools/research/le3_reward_catalog.py"], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()

"""Cross-check history reader/setter indices against extracted vanilla sources."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def load_history():
    spec = importlib.util.spec_from_file_location("le3_history", ROOT / "world/mass_effect_le3/history.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def verify():
    history = load_history()
    config_path = ROOT / "research/le3_history_config.jsonl"
    script_path = ROOT / "research/le3_history_callers.jsonl"
    database_path = ROOT / "research/le3_plot_inventory.csv"
    aliases = {}
    for line in config_path.read_text(encoding="utf-8").splitlines():
        section = ET.fromstring(json.loads(line)["section"])
        if section.attrib["name"].lower() == "sfxgame.bioglobalvariabletable":
            for prop in section.findall("Property"):
                if prop.text and prop.text.strip().isdigit():
                    aliases[prop.attrib["name"].lower()] = int(prop.text)
    functions = {row["function"]: row for line in script_path.read_text(encoding="utf-8").splitlines()
                 if (row := json.loads(line))}
    with database_path.open(encoding="utf-8", newline="") as stream:
        database = {(row["family"], int(row["plot_id"])): row["path"] for row in csv.DictReader(stream)}

    def resolve(alias, family):
        index = aliases[alias.lower()]
        db_path = database[(family, index)]
        # ME3__X and ME2__X alias prefixes denote the game using the plot, not
        # database roots; all reader references here use ME3__<path>.
        expected_path = "le3." + alias.split("__", 1)[1].replace("__", ".").lower()
        if db_path.lower() != expected_path:
            raise ValueError(f"Config/database disagreement: {alias}={index}: {db_path}")
        return index

    readers = []
    for name, expected in history.READER_PLOTS.items():
        row = functions["BioGlobalVariableTable." + name]
        text = row["text"]
        actual = tuple(tuple(resolve(alias, family) for alias in re.findall(rf"Get{kind}\((\w+)\)", text))
                       for kind, family in (("Bool", "bools"), ("Int", "ints")))
        if actual != expected:
            raise ValueError(f"Reader index/order disagreement: {name}: {actual} != {expected}")
        readers.append({"function": row["function"], "export": row["export"],
                        "bools": actual[0], "ints": actual[1]})
    me1 = functions["BioGlobalVariableTable.MajorPolt_ME1_Romance"]["text"]
    me2 = functions["BioGlobalVariableTable.MajorPlot_ME2_Romance"]["text"]
    if re.findall(r"GetInt\(\w+\)\s*>=\s*(\d+)", me1) != ["4"] * 3:
        raise ValueError("ME1 romance recognition threshold changed")
    if re.findall(r"GetInt\(\w+\)\s*==\s*(\d+)", me2) != ["5"] * 6:
        raise ValueError("ME2 romance recognition state changed")
    setter = functions["BioSFHandler_NewCharacter.SetPlotChoices"]
    for choice, enum in (("ashley", "KaidenDies"), ("kaidan", "AshleyDies")):
        match = re.search(rf"case EPlotChoice\.EPlotChoice_{enum}:(.*?)break;", setter["text"], re.S)
        if not match: raise ValueError(f"Missing native Virmire case {enum}")
        actual = {resolve(alias, "bools"): value == "TRUE" for alias, value in
                  re.findall(r"SetBool\(Class'BioGlobalVariableTable'\.default\.(\w+), (TRUE|FALSE)\)", match[1])}
        if actual != history.VIRMIRE_BUNDLES[choice]:
            raise ValueError(f"Virmire setter disagreement: {choice}")
    b, i = history.readback_indices()
    if any(("bools", index) not in database for index in b) or any(("ints", index) not in database for index in i):
        raise ValueError("Unmapped diagnostic index")
    return {"schema": 1, "status": "offline_source_mapping_verified_not_runtime_initialization",
            "readers": readers, "virmire_setter_export": setter["export"],
            "required_bool_count": len(b), "required_int_count": len(i),
            "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in (config_path, script_path, database_path,
                                        ROOT / "world/mass_effect_le3/history.py")}}


if __name__ == "__main__":
    result = verify()
    output = ROOT / "research/le3_history_mapping_validation.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Verified {len(result['readers'])} vanilla readers and both Virmire setter branches; "
          f"{result['required_bool_count']} bools, {result['required_int_count']} ints.\n{output}")

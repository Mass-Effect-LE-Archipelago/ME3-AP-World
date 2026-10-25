"""Generate an ME2 LE import save that expresses a resolved history profile.

Reads a template end-game save (never modified), applies history_save.plot_edits,
re-seals the checksum, verifies the ME3 reader model against the profile and
writes a NEW file. Optionally installs it as a new ME2 career folder.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from layout import get_bool, get_int, parse  # noqa: E402
from patch import Edit, apply  # noqa: E402


def _load(name: str):
    path = ROOT / "world/mass_effect_le3" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"le3_{name}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


history = _load("history")
history_save = _load("history_save")

# ME3 reader values that a resolved profile fully determines.
READER_EXPECTATIONS = {
    "me1.virmire_survivor": lambda c: c["me1.virmire_survivor"],
    "me1.wrex": lambda c: {"never_recruited": "ignored"}.get(c["me1.wrex"], c["me1.wrex"]),
    "me1.rachni_queen_saved": lambda c: c["me1.rachni"] == "saved",
    "me1.council_saved": lambda c: c["me1.council"] == "saved",
    "me1.romance": lambda c: c["me1.romance"],
    "me2.maelon_data_saved": lambda c: c["me2.maelon_data"] == "saved",
    "me2.maelon_data_destroyed": lambda c: c["me2.maelon_data"] == "destroyed",
    "me2.heretics": lambda c: c["me2.heretics"],
    "me2.collector_base": lambda c: c["me2.collector_base"],
    "me2.romance": lambda c: c["me2.romance"],
    "me2.squad_survivor_count": lambda c: sum(
        c[f"me2.squad.{m}.recruited"] and c[f"me2.squad.{m}.survived"] for m in history_save.SQUAD_FLAGS),
}


def generate(template: bytes, choices: dict) -> tuple[bytes, dict]:
    layout = parse(template)
    if layout.end_game_state != 2:
        raise ValueError("Template must be an ME2 end-game save with Shepard alive")
    tables = {"me2": layout.plot, "me1": layout.me1_plot}
    edits = history_save.plot_edits(
        choices, is_female=layout.is_female,
        current_int=lambda table, index: get_int(template, tables[table], index))
    result = apply(template, [Edit(*edit) for edit in edits])
    check = parse(result)
    tables = {"me2": check.plot, "me1": check.me1_plot}
    bools, ints = history.readback_indices()
    view = history_save.me3_import_view(lambda t, i: get_bool(result, tables[t], i),
                                        lambda t, i: get_int(result, tables[t], i), bools, ints)
    readback = history.inspect_history_snapshot(view)
    mismatches = {key: (readback.values[key], expect(choices)) for key, expect in READER_EXPECTATIONS.items()
                  if readback.values[key] != expect(choices)}
    if mismatches or readback.warnings:
        raise ValueError(f"ME3 reader model disagrees with the profile: {mismatches} {readback.warnings}")
    return result, {"edits": len(edits), "me3_reader_values": readback.values}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("template", type=Path)
    parser.add_argument("profile", type=Path, help="Resolved profile JSON (preset/version/choices)")
    parser.add_argument("output", type=Path)
    parser.add_argument("--install-career", type=Path, metavar="ME2_SAVE_DIR",
                        help="Also copy into a new career folder under this ME2 save directory")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists; never overwrite a save")
    profile_module = _load("history_profile")
    profile = profile_module.parse_resolved_history(json.loads(args.profile.read_text(encoding="utf-8")))
    template = args.template.read_bytes()
    result, report = generate(template, dict(profile.choices))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as stream:
        stream.write(result)
    report.update(template_sha256=hashlib.sha256(template).hexdigest(),
                  output=str(args.output), output_sha256=hashlib.sha256(result).hexdigest())
    if args.install_career:
        digest = hashlib.sha256(result).hexdigest()[:7]
        # Mirror the template career's "<name>_<nn>_<class>_" prefix; the pattern was accepted by ME3 in test 01.
        prefix = "_".join(args.template.resolve().parent.name.split("_")[:3])
        folder = args.install_career / f"{prefix}_{datetime.now():%d%m%y}_{digest}"
        folder.mkdir()  # refuses an existing career folder
        with (folder / "Save_0001.pcsav").open("xb") as stream:
            stream.write(result)
        report["installed"] = str(folder / "Save_0001.pcsav")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

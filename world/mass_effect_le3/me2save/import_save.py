"""Write the ME2 import save that carries a slot's history (D3), as a new ME2 career the ME3 creator can import.

The template is one of the player's own ME2 LE end-game saves (Shepard alive), never modified: the choices are applied
to a copy, the checksum is re-sealed and the ME3 reader model must read the history back before anything is written.
One career per history: its folder ends in the history digest, so a second call finds it instead of writing again.
"""
from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path

from .. import history, history_save
from .layout import SaveFormatError, get_bool, get_int, parse
from .patch import Edit, apply

# ME3 reader values that a resolved profile fully determines (same table as tools/me2save/generate_import_save.py).
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


def default_save_root() -> Path:
    return Path(os.path.expanduser("~")) / "Documents" / "BioWare" / "Mass Effect Legendary Edition" / "Save" / "ME2"


def generate(template: bytes, choices: dict) -> bytes:
    layout = parse(template)
    if layout.end_game_state != 2:
        raise SaveFormatError("Template must be an ME2 end-game save with Shepard alive")
    tables = {"me2": layout.plot, "me1": layout.me1_plot}
    edits = history_save.plot_edits(choices, is_female=layout.is_female,
                                    current_int=lambda table, index: get_int(template, tables[table], index))
    result = apply(template, [Edit(*edit) for edit in edits])
    check = parse(result)
    tables = {"me2": check.plot, "me1": check.me1_plot}
    bools, ints = history.readback_indices()
    view = history_save.me3_import_view(lambda t, i: get_bool(result, tables[t], i),
                                        lambda t, i: get_int(result, tables[t], i), bools, ints)
    readback = history.inspect_history_snapshot(view)
    mismatches = {key: readback.values[key] for key, expect in READER_EXPECTATIONS.items()
                  if readback.values[key] != expect(choices)}
    if mismatches or readback.warnings:
        raise SaveFormatError(f"ME3 reader model disagrees with the history: {mismatches} {readback.warnings}")
    return result


def find_template(root: Path, skip_suffix: str) -> Path | None:
    """Newest ME2 save that is an end-game save with Shepard alive (our own generated careers are skipped)."""
    candidates = sorted((p for p in root.glob("*/*.pcsav") if not p.parent.name.endswith(skip_suffix)),
                        key=lambda p: p.stat().st_mtime, reverse=True)
    for path in candidates:
        try:
            if parse(path.read_bytes()).end_game_state == 2:
                return path
        except (SaveFormatError, OSError, ValueError):
            continue
    return None


def ensure_import_career(history_data: dict, digest: str, root: Path | None = None) -> tuple[Path, bool]:
    """Return (career save, created). Raises FileNotFoundError when no usable ME2 save exists."""
    root = root or default_save_root()
    suffix = "_" + digest[:7]  # 7 hex characters, the same shape as the game's own career ids
    existing = sorted(root.glob(f"*{suffix}/Save_0001.pcsav"))
    if existing:
        return existing[0], False
    template = find_template(root, suffix)
    if template is None:
        raise FileNotFoundError(f"No finished ME2 LE save (Shepard alive) under {root}")
    result = generate(template.read_bytes(), dict(history_data["choices"]))
    # ME3 lists ME2 careers by folder; mirror the template's "<name>_<nn>_<class>" prefix (accepted by ME3 in test 01).
    prefix = "_".join(template.parent.name.split("_")[:3])
    folder = root / f"{prefix}_{datetime.now():%d%m%y}{suffix}"
    folder.mkdir()  # never reuses or overwrites a career folder
    with (folder / "Save_0001.pcsav").open("xb") as stream:
        stream.write(result)
    return folder / "Save_0001.pcsav", True

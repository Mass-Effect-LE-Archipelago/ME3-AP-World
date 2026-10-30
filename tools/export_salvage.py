"""Write tools/le3mod/salvage.json and mission_keys.json (native slot order) from the world's data.py tables."""
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
tree = ast.parse((ROOT / "world/mass_effect_le3/data.py").read_text(encoding="utf-8"))


def table(name):
    return next(ast.literal_eval(node.value) for node in tree.body
                if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == name for t in node.targets))


missions = table("SALVAGE_MISSIONS")
(ROOT / "tools/le3mod/salvage.json").write_text(json.dumps(list(missions), indent=1) + "\n", encoding="utf-8")
keys = [{"region": r, "map": m, "done_int": d, "extra": x} for r, m, d, x in table("MISSION_KEYS")]
(ROOT / "tools/le3mod/mission_keys.json").write_text(json.dumps(keys, indent=1) + "\n", encoding="utf-8")
print(f"{len(missions)} salvage missions, {len(keys)} mission keys")

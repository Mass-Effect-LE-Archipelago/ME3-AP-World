"""Write tools/le3mod/salvage.json (salvage mission names, native slot order) from the world's data.SALVAGE_MISSIONS."""
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
tree = ast.parse((ROOT / "world/mass_effect_le3/data.py").read_text(encoding="utf-8"))
missions = next(ast.literal_eval(node.value) for node in tree.body
                if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "SALVAGE_MISSIONS" for t in node.targets))
(ROOT / "tools/le3mod/salvage.json").write_text(json.dumps(list(missions), indent=1) + "\n", encoding="utf-8")
print(f"{len(missions)} salvage missions")

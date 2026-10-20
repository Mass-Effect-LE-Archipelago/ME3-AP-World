"""Compile an offline Shepard history preview; never contacts the game or AP."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New preview JSON; existing artifacts are never overwritten")
    parser.add_argument("--input", type=Path, help="JSON preset/choice overrides, or a complete versioned profile")
    args = parser.parse_args()
    if args.output.exists(): parser.error("Preview already exists")
    spec = importlib.util.spec_from_file_location("le3_history_profile", ROOT / "world/mass_effect_le3/history_profile.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    request = json.loads(args.input.read_text(encoding="utf-8")) if args.input else {}
    if not isinstance(request, dict): parser.error("Expected a JSON object")
    if "version" in request:
        profile = module.parse_resolved_history(request)
    else:
        if request.keys() - {"preset", "choices"}: parser.error("Unknown history request fields")
        profile = module.resolve_history(request.get("preset", "maximum_content"), request.get("choices", {}))
    bundles = json.loads((ROOT / "world/mass_effect_le3/history_bundles.json").read_text(encoding="utf-8"))
    result = module.compile_history_preview(profile, bundles=bundles)
    payload = profile.to_slot_data()
    payload.pop("implemented_in_game")
    result.update({"history_digest": hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                                              allow_nan=False).encode()).hexdigest(),
                   "game_contacted": False, "server_contacted": False})
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(f"Resolved {len(profile.choices)} history facts; "
          f"{len(profile.choices) - len(result['unmapped_choices'])} source mappings, "
          f"{len(result['unmapped_choices'])} unmapped. Native execution is unavailable.\n{args.output.resolve()}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError) as error:
        raise SystemExit(str(error)) from None

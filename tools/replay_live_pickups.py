"""Replay actual gameplay snapshots through the packaged AP source detector.

Offline verification only: does not connect to a game or Archipelago server.
"""
import json
import os
from pathlib import Path
import sys
import unittest  # Activates the supplied AP checkout's focused import filter.

ROOT = Path(__file__).resolve().parents[1]
os.environ["AP_TEST_WORLDS"] = "apquest"
os.environ["SKIP_REQUIREMENTS_UPDATE"] = "1"
sys.path.insert(0, str(ROOT / "Archipelago-main"))
import worlds
worlds.__path__.insert(0, str(ROOT / "build/mass_effect_le3.apworld"))
from worlds.mass_effect_le3 import data
from worlds.mass_effect_le3.client_core import GameSnapshot, observed_locations


def load(name):
    raw = json.loads((ROOT / "research" / name).read_text())
    return GameSnapshot({int(k): bool(v) for k, v in raw["bools"].items()},
                        {int(k): int(v) for k, v in raw["ints"].items()},
                        frozenset(raw["used_guids"]), frozenset(map(int, raw["gaw"])))


assert ".apworld" in sys.modules["worlds.mass_effect_le3.client_core"].__file__
enabled = set(data.BY_ID)
before = observed_locations(load("live_baseline_01.json"), enabled)
after = observed_locations(load("live_earth_after_pickups_01.json"), enabled)
expected = {1295192584, 1295192353}  # Witnessed rooftop medkit and AA-gun Cain.
assert after - before == expected, (after - before, expected)
assert not before - after, "An earlier observed predicate disappeared"
reloaded = observed_locations(load("live_earth_reloaded_01.json"), enabled)
assert expected <= reloaded, "Pickup records did not survive the reported save/reload"
assert reloaded == after, "Observed selected locations changed across the idle reload"
receipt = {"verification": "actual snapshots replayed through packaged source detector",
           "server_contacted": False, "items_delivered": False,
           "save_reload_verified": True, "fresh_process_reload_verified": False,
           "newly_observed_ids": sorted(after - before),
           "newly_observed_names": [data.BY_ID[k].name for k in sorted(after - before)]}
(ROOT / "research/le3_live_detector_replay.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt, indent=2))

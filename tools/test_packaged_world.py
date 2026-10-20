"""Smoke-test the built AP archive itself, including its JSON resources."""
import os
from pathlib import Path
import sys
import unittest  # Enables the local AP_TEST_WORLDS import filter.

ROOT = Path(__file__).resolve().parents[1]
os.environ["AP_TEST_WORLDS"] = "apquest"
os.environ["SKIP_REQUIREMENTS_UPDATE"] = "1"
sys.path.insert(0, str(ROOT / "Archipelago-main"))
import worlds

# Test loading from the ZIP rather than accidentally reusing the synced folder.
archive = ROOT / "build/mass_effect_le3.apworld"
worlds.__path__.insert(0, str(archive))
from worlds.mass_effect_le3 import MassEffectLE3World
from worlds.mass_effect_le3 import data
from worlds.mass_effect_le3.history_profile import compile_history_preview, resolve_history
from test.general import gen_steps, setup_multiworld
from Fill import distribute_items_restrictive

assert ".apworld" in sys.modules["worlds.mass_effect_le3"].__file__
# The history compiler must load its source recipes from the archive too.
history_preview = compile_history_preview(resolve_history())
assert history_preview["actions"] and not history_preview["executable"]
multiworld = setup_multiworld(MassEffectLE3World, gen_steps, 101)
distribute_items_restrictive(multiworld)
assert not multiworld.get_unfilled_locations()
assert multiworld.can_beat_game(multiworld.state)
filled = sum(location.address is not None for location in multiworld.get_filled_locations())
print(f"Packaged archive loads {len(data.LOCATIONS)} registered source IDs, fills {filled} selected checks, and reaches its modeled goal.")

"""Shim: the ME2 save code lives in the world (world/mass_effect_le3/me2save/patch.py) so the client can use it.
Loaded as a standalone package so research scripts don't need Archipelago installed."""
import importlib
import importlib.util
import sys
from pathlib import Path

if "le3_me2save" not in sys.modules:
    _home = Path(__file__).resolve().parents[2] / "world/mass_effect_le3/me2save"
    _spec = importlib.util.spec_from_file_location("le3_me2save", _home / "__init__.py", submodule_search_locations=[str(_home)])
    sys.modules["le3_me2save"] = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(sys.modules["le3_me2save"])
sys.modules[__name__] = importlib.import_module("le3_me2save.patch")

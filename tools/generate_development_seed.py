"""Generate a real local AP seed for integration development, without hosting it."""
import argparse
import os
from pathlib import Path
import sys
import tempfile
import unittest  # Scope the supplied AP checkout's optional world imports.

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--seed", type=int, default=314159)
args = parser.parse_args()
os.environ["AP_TEST_WORLDS"] = "mass_effect_le3"
os.environ["SKIP_REQUIREMENTS_UPDATE"] = "1"
sys.path.insert(0, str(ROOT / "Archipelago-main"))
from Generate import main, mystery_argparse
from Main import main as generate

players = ROOT / "build/development_players"
players.mkdir(parents=True, exist_ok=True)
scratch = ROOT / "build/generation_tmp"
scratch.mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(scratch)
options = mystery_argparse(["--player_files_path", str(players), "--weights_file_path",
    str(ROOT / "Mass Effect Legendary Edition 3 - Development.yaml"), "--multi", "1",
    "--seed", str(args.seed), "--outputpath", str(ROOT / "build/development_seed")])
generated_args, seed = main(options)
multiworld = generate(generated_args, seed)
print(f"Generated development seed {seed} for {multiworld.players} player(s). Native game integration remains incomplete.")

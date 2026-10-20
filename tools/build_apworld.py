"""Package the ME3 world reproducibly; --sync also updates the local AP source copy."""
import argparse
import hashlib
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "world/mass_effect_le3"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--sync", action="store_true")
args = parser.parse_args()
if args.sync:
    shutil.copytree(SOURCE, ROOT / "Archipelago-main/worlds/mass_effect_le3", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
output = ROOT / "build/mass_effect_le3.apworld"
output.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
    for source in sorted(SOURCE.rglob("*")):
        relative = source.relative_to(SOURCE)
        if source.is_dir() or "__pycache__" in relative.parts or relative.parts[0] == "test" or source.suffix == ".pyc":
            continue
        info = zipfile.ZipInfo((Path("mass_effect_le3") / relative).as_posix(), (1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(info, source.read_bytes())
print(f"{output}\nSHA256 {hashlib.sha256(output.read_bytes()).hexdigest()}")

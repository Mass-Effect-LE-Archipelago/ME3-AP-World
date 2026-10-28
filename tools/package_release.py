r"""Stage the ME3 release payload in build/release-<version>/ for Mass Effect AP Setup (tools/setup/package.py).

usage: python tools/package_release.py <version>
Contents: mass_effect_le3.apworld, LE3APBridge.asi (the pinned delivery build), ArchipelagoME3\ (moddesc.ini,
DLC_MOD_ArchipelagoME3, built from the local game by le3mod), README.md, SHA256SUMS.
Run tools/build_apworld.py, the bridge build (build.py --delivery-dev) and le3mod openstart first.
"""
import hashlib
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/le3apbridge"))
from install_research import DELIVERY_DEV_HASH  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    version = sys.argv[1]
    out = ROOT / "build" / f"release-{version}"
    bridge = ROOT / "tools/le3apbridge/build-delivery/bin/Release/LE3APBridge.asi"
    mod = ROOT / "build" / f"le3mod-{version}" / "ArchipelagoME3"
    world = ROOT / "build/mass_effect_le3.apworld"
    if sha(bridge) != DELIVERY_DEV_HASH:
        raise SystemExit(f"bridge build {sha(bridge)[:12]} is not the pinned {DELIVERY_DEV_HASH[:12]}")
    if f"modver = {version}" not in (mod / "moddesc.ini").read_text():
        raise SystemExit(f"{mod} is not mod version {version}")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    shutil.copy(world, out / world.name)
    shutil.copy(bridge, out / bridge.name)
    # The DLC's file table is written on install (Mass Effect AP Setup or Mod Manager), as for ME2.
    shutil.copytree(mod, out / "ArchipelagoME3", ignore=shutil.ignore_patterns("PCConsoleTOC.bin"))
    shutil.copy(ROOT / "world/mass_effect_le3/docs/setup_en.md", out / "README.md")
    sums = [f"{sha(p)}  {p.relative_to(out).as_posix()}" for p in sorted(out.rglob("*")) if p.is_file()]
    (out / "SHA256SUMS").write_text("\n".join(sums) + "\n", newline="\n")
    print(f"staged {out} ({len(sums)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

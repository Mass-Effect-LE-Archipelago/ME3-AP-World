"""Install/restore the research bridge, or an explicitly selected development writer.

Default action is inspection. Live game writes require the host's filesystem approval.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
GAME = Path(r"C:\Steam\steamapps\common\Mass Effect Legendary Edition\Game\ME3")
VANILLA_HASH = "653247e35db8d6453e83a008c805a877fd2d56a1d844282f9065ce2f34388fec"
BRIDGE_HASH = "29ca2f8d5b247e62e5e59dffa5f860f83816c00c3505597be0ed7d5ca1d59e9b"
# 0.2.4-delivery-dev (2026-10-28): + KEY (mission access bools). 0.2.3 (4b6e35b5..., the 0.1.0 release) and older
# builds stay in build/live-original.
DELIVERY_DEV_HASH = "7aded9ecc303541120939446b54bda572e286dc89a60d9e99dec451e333e7f45"  # rebuilt from db8ecb8; the first 0.2.4 build (784f5b49) was lost with its folder
# Read-only career observer 0.3.0, built 2026-10-20 from build.py --career-trace.
CAREER_TRACE_HASH = "5a645f7a3e623e1c3c45988043dadc13e2fe04eded1ab8fab75f23073dffce81"
PROFILE_DIRS = {"research": "build", "delivery-dev": "build-delivery", "career-trace": "build-career"}
RECEIPT = ROOT / "research/live_install_receipt.json"
BACKUP = ROOT / "build/live-original/bink2w64.dll"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def profile_hash(profile: str) -> str:
    return {"research": BRIDGE_HASH, "delivery-dev": DELIVERY_DEV_HASH, "career-trace": CAREER_TRACE_HASH}[profile]


def profile_source(profile: str, expected: str) -> Path:
    """Staged build output, else the verified backup of that exact binary.

    The backup fallback lets a profile be reselected after its build directory
    was rebuilt; a hash mismatch on both candidates still refuses the update.
    """
    built = ROOT / "tools/le3apbridge" / PROFILE_DIRS[profile] / "bin/Release/LE3APBridge.asi"
    backup = ROOT / "build/live-original" / (expected + ".asi")
    for candidate in (built, backup):
        if candidate.is_file() and digest(candidate) == expected:
            return candidate
    return built


def original_baseline(receipt: dict) -> tuple[str, Path]:
    """Expected original Bink hash and its verified workspace copy."""
    if "current_original_sha256" in receipt:
        return receipt["current_original_sha256"], ROOT / receipt["current_original_backup"]
    return VANILLA_HASH, BACKUP


def ensure_closed() -> None:
    result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq MassEffect3.exe", "/FO", "CSV", "/NH"],
                            capture_output=True, text=True, check=True)
    for row in csv.reader(io.StringIO(result.stdout)):
        if row and row[0].lower() == "masseffect3.exe":
            raise RuntimeError("Close Mass Effect 3 before installing or restoring")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("inspect", "install", "update", "restore", "rebaseline"), nargs="?", default="inspect")
    parser.add_argument("--game", type=Path, default=GAME)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--profile", choices=tuple(PROFILE_DIRS), help="Bridge profile to install or update")
    selection.add_argument("--delivery-dev", action="store_true", help="Alias for --profile delivery-dev")
    args = parser.parse_args()
    profile = args.profile or ("delivery-dev" if args.delivery_dev else "research")
    bridge_hash = profile_hash(profile)
    bridge_source = profile_source(profile, bridge_hash)
    game = args.game.resolve(strict=True)
    binary = game / "Binaries/Win64"
    exe = binary / "MassEffect3.exe"
    if game.name.upper() != "ME3" or not exe.is_file() or not (game / "BioGame").is_dir():
        raise RuntimeError("Expected the LE3 Game/ME3 installation directory")
    target = binary / "bink2w64.dll"
    original = binary / "bink2w64_original.dll"
    asi = binary / "ASI/LE3APBridge.asi"
    if args.action == "inspect":
        print(json.dumps({"game": str(game), "bink_sha256": digest(target),
                          "original_exists": original.exists(), "bridge_exists": asi.exists(),
                          "asi_files": sorted(p.name for p in (binary / "ASI").glob("*.asi"))}, indent=2))
        return
    ensure_closed()
    if args.action == "rebaseline":
        # An external manager (ME3Tweaks) replaced the loader and its saved original.
        # Record the current pair as the new baseline; the bridge must still match.
        receipt = json.loads(RECEIPT.read_text())
        if receipt["game"] != str(game) or receipt["status"] != "installed":
            raise RuntimeError("No matching installed receipt")
        if digest(asi) != receipt["bridge_sha256"]:
            raise RuntimeError(f"Changed file; refusing rebaseline: {asi}")
        original_hash, loader_hash = digest(original), digest(target)
        backup = BACKUP.parent / f"bink2w64_original_{original_hash}.dll"
        if not backup.exists():
            shutil.copy2(original, backup)
        if digest(backup) != original_hash:
            raise RuntimeError("Original DLL backup verification failed")
        archive = RECEIPT.with_name(RECEIPT.stem + f".before-rebaseline-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json")
        archive.write_text(RECEIPT.read_text())
        receipt.setdefault("baseline_history", []).append(
            {"loader_sha256": receipt["loader_sha256"], "original_sha256": receipt.get("current_original_sha256", VANILLA_HASH),
             "replaced_utc": datetime.now(timezone.utc).isoformat(), "archived_receipt": archive.name})
        receipt.update(loader_sha256=loader_hash, current_original_sha256=original_hash,
                       current_original_backup=str(backup.relative_to(ROOT)), runtime_verified=False)
        RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n")
        print(f"Re-baselined loader {loader_hash[:12]} / original {original_hash[:12]}; receipt archived as {archive.name}.")
        return
    if args.action == "update":
        receipt = json.loads(RECEIPT.read_text())
        if receipt["game"] != str(game) or receipt["status"] != "installed":
            raise RuntimeError("No matching installed receipt")
        bridge = bridge_source
        current_original, current_backup = original_baseline(receipt)
        for path, expected in ((target, receipt["loader_sha256"]), (original, current_original),
                               (current_backup, current_original), (asi, receipt["bridge_sha256"]), (bridge, bridge_hash)):
            if digest(path) != expected:
                raise RuntimeError(f"Changed file; refusing bridge update: {path}")
        previous = ROOT / "build/live-original" / (receipt["bridge_sha256"] + ".asi")
        previous.parent.mkdir(parents=True, exist_ok=True)
        if not previous.exists():
            shutil.copy2(asi, previous)
        if digest(previous) != receipt["bridge_sha256"]:
            raise RuntimeError("Previous bridge backup verification failed")
        try:
            shutil.copy2(bridge, asi)
            if digest(asi) != bridge_hash:
                raise RuntimeError("Updated bridge verification failed")
        except Exception:
            shutil.copy2(previous, asi)
            raise
        receipt.setdefault("previous_bridge_hashes", []).append(receipt["bridge_sha256"])
        receipt["bridge_sha256"] = bridge_hash
        receipt["bridge_profile"] = profile
        receipt["updated_utc"] = datetime.now(timezone.utc).isoformat()
        receipt["runtime_verified"] = False
        RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n")
        print(f"Updated and hash-verified {profile} bridge; previous binary backed up.")
        return
    if args.action == "restore":
        receipt = json.loads(RECEIPT.read_text())
        if receipt["game"] != str(game) or receipt["status"] != "installed":
            raise RuntimeError("No matching installed receipt")
        current_original, current_backup = original_baseline(receipt)
        for path, expected in ((target, receipt["loader_sha256"]),
                               (original, current_original), (asi, receipt["bridge_sha256"]), (current_backup, current_original)):
            if digest(path) != expected:
                raise RuntimeError(f"Changed file; refusing automatic restore: {path}")
        shutil.copy2(current_backup, target)
        if digest(target) != current_original:
            raise RuntimeError("Original DLL restoration did not verify")
        asi.unlink()
        original.unlink()
        receipt["status"] = "restored"
        receipt["restored_utc"] = datetime.now(timezone.utc).isoformat()
        RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n")
        print("Restored original Bink DLL and removed this research ASI; logs retained.")
        return
    loader = ROOT / "build/loader/bink2w64.dll"
    bridge = bridge_source
    if digest(target) != VANILLA_HASH or digest(bridge) != bridge_hash:
        raise RuntimeError("Unexpected original DLL or research bridge hash")
    if original.exists() or asi.exists() or RECEIPT.exists() or BACKUP.exists():
        raise RuntimeError("Existing loader, bridge, receipt or backup; refusing overwrite")
    loader_hash = digest(loader)
    # A verified workspace backup precedes all game writes.
    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target, BACKUP)
    if digest(BACKUP) != VANILLA_HASH:
        raise RuntimeError("Backup verification failed")
    receipt = {"game": str(game), "status": "prepared", "original_sha256": VANILLA_HASH,
               "loader_sha256": loader_hash, "bridge_sha256": bridge_hash,
               "bridge_profile": profile,
               "loader_source_commit": "1c435d8df0367642d9fc8572b67b6ae92295967e",
               "installed_utc": datetime.now(timezone.utc).isoformat(), "runtime_verified": False}
    RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n")
    try:
        shutil.copy2(BACKUP, original)
        shutil.copy2(loader, target)
        asi.parent.mkdir(exist_ok=True)
        shutil.copy2(bridge, asi)
        for path, expected in ((original, VANILLA_HASH), (target, loader_hash), (asi, bridge_hash)):
            if digest(path) != expected:
                raise RuntimeError(f"Installed file verification failed: {path}")
    except Exception:
        shutil.copy2(BACKUP, target)
        # Remove only files this installation created and which still match its inputs.
        for path, expected in ((original, VANILLA_HASH), (asi, bridge_hash)):
            if path.exists() and digest(path) == expected:
                path.unlink()
        receipt["status"] = "rolled_back"
        RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n")
        raise
    receipt["status"] = "installed"
    RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n")
    print("Installed and hash-verified read-only research bridge; game has not been launched.")


if __name__ == "__main__":
    main()

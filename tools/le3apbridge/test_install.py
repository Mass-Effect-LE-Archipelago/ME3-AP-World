"""Exercise game-file rollback in an isolated temporary directory."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.le3apbridge import install_research as installer


class InstallerTests(unittest.TestCase):
    def setUp(self):
        temporary_parent = installer.ROOT / "build/installer-tests"
        temporary_parent.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=temporary_parent)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.game = self.root / "Game/ME3"
        self.binary = self.game / "Binaries/Win64"
        (self.binary / "ASI").mkdir(parents=True)
        (self.game / "BioGame").mkdir()
        (self.binary / "MassEffect3.exe").write_bytes(b"test executable placeholder")
        (self.binary / "bink2w64.dll").write_bytes(b"original")
        for relative, contents in (("build/loader/bink2w64.dll", b"loader"),
                ("tools/le3apbridge/build/bin/Release/LE3APBridge.asi", b"bridge"),
                ("tools/le3apbridge/build-delivery/bin/Release/LE3APBridge.asi", b"devbridge"),
                ("tools/le3apbridge/build-career/bin/Release/LE3APBridge.asi", b"tracebridge")):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(contents)
        (self.root / "research").mkdir()
        for name, value in {"ROOT": self.root, "RECEIPT": self.root / "research/receipt.json",
                            "BACKUP": self.root / "backup/bink2w64.dll",
                            "VANILLA_HASH": hashlib.sha256(b"original").hexdigest(),
                            "BRIDGE_HASH": hashlib.sha256(b"bridge").hexdigest(),
                            "DELIVERY_DEV_HASH": hashlib.sha256(b"devbridge").hexdigest(),
                            "CAREER_TRACE_HASH": hashlib.sha256(b"tracebridge").hexdigest()}.items():
            context = patch.object(installer, name, value)
            context.start()
            self.addCleanup(context.stop)
        context = patch.object(installer, "ensure_closed")
        context.start()
        self.addCleanup(context.stop)

    def run_action(self, action, *extra):
        with patch("sys.argv", ["installer", action, "--game", str(self.game), *extra]), contextlib.redirect_stdout(io.StringIO()):
            installer.main()

    def test_install_restore_preserves_original(self):
        self.run_action("install")
        self.assertEqual((self.binary / "bink2w64.dll").read_bytes(), b"loader")
        self.run_action("restore")
        self.assertEqual((self.binary / "bink2w64.dll").read_bytes(), b"original")
        self.assertFalse((self.binary / "ASI/LE3APBridge.asi").exists())

    def test_changed_installed_file_blocks_restore(self):
        self.run_action("install")
        (self.binary / "ASI/LE3APBridge.asi").write_bytes(b"another version")
        with self.assertRaisesRegex(RuntimeError, "Changed file"):
            self.run_action("restore")
        self.assertEqual((self.binary / "bink2w64.dll").read_bytes(), b"loader")

    def test_failed_bridge_copy_rolls_back_loader(self):
        copy = installer.shutil.copy2
        def fail_bridge(source, target):
            if Path(target).suffix == ".asi":
                raise OSError("simulated bridge copy failure")
            return copy(source, target)
        with patch.object(installer.shutil, "copy2", side_effect=fail_bridge):
            with self.assertRaisesRegex(OSError, "simulated"):
                self.run_action("install")
        self.assertEqual((self.binary / "bink2w64.dll").read_bytes(), b"original")
        self.assertFalse((self.binary / "bink2w64_original.dll").exists())
        self.assertEqual(json.loads(installer.RECEIPT.read_text())["status"], "rolled_back")

    def test_update_retains_original_restore(self):
        self.run_action("install")
        revised = b"revised bridge"
        (self.root / "tools/le3apbridge/build/bin/Release/LE3APBridge.asi").write_bytes(revised)
        with patch.object(installer, "BRIDGE_HASH", hashlib.sha256(revised).hexdigest()):
            self.run_action("update")
        self.assertEqual((self.binary / "ASI/LE3APBridge.asi").read_bytes(), revised)
        # Restoration uses the receipt, even if the source was rebuilt again.
        self.run_action("restore")
        self.assertEqual((self.binary / "bink2w64.dll").read_bytes(), b"original")

    def test_writer_requires_explicit_profile_and_restores(self):
        self.run_action("install")
        self.assertEqual((self.binary / "ASI/LE3APBridge.asi").read_bytes(), b"bridge")
        self.run_action("update", "--delivery-dev")
        self.assertEqual((self.binary / "ASI/LE3APBridge.asi").read_bytes(), b"devbridge")
        self.assertEqual(json.loads(installer.RECEIPT.read_text())["bridge_profile"], "delivery-dev")
        self.run_action("restore")
        self.assertEqual((self.binary / "bink2w64.dll").read_bytes(), b"original")

    def test_career_trace_swap_returns_to_backed_up_writer(self):
        self.run_action("install")
        self.run_action("update", "--delivery-dev")
        self.run_action("update", "--profile", "career-trace")
        self.assertEqual((self.binary / "ASI/LE3APBridge.asi").read_bytes(), b"tracebridge")
        self.assertEqual(json.loads(installer.RECEIPT.read_text())["bridge_profile"], "career-trace")
        # A rebuilt writer no longer matches its pin; the verified backup is used instead.
        (self.root / "tools/le3apbridge/build-delivery/bin/Release/LE3APBridge.asi").write_bytes(b"rebuilt")
        self.run_action("update", "--delivery-dev")
        self.assertEqual((self.binary / "ASI/LE3APBridge.asi").read_bytes(), b"devbridge")
        self.run_action("restore")
        self.assertEqual((self.binary / "bink2w64.dll").read_bytes(), b"original")

    def test_mismatched_profile_binary_refuses_update(self):
        self.run_action("install")
        (self.root / "tools/le3apbridge/build-career/bin/Release/LE3APBridge.asi").write_bytes(b"unpinned")
        with self.assertRaisesRegex(RuntimeError, "Changed file"):
            self.run_action("update", "--profile", "career-trace")
        self.assertEqual((self.binary / "ASI/LE3APBridge.asi").read_bytes(), b"bridge")

    def test_rebaseline_after_external_loader_replacement(self):
        self.run_action("install")
        (self.binary / "bink2w64.dll").write_bytes(b"newer loader")
        (self.binary / "bink2w64_original.dll").write_bytes(b"newer original")
        with self.assertRaisesRegex(RuntimeError, "Changed file"):
            self.run_action("update", "--profile", "career-trace")
        self.run_action("rebaseline")
        self.run_action("update", "--profile", "career-trace")
        self.assertEqual((self.binary / "ASI/LE3APBridge.asi").read_bytes(), b"tracebridge")
        self.run_action("restore")
        self.assertEqual((self.binary / "bink2w64.dll").read_bytes(), b"newer original")
        self.assertFalse((self.binary / "ASI/LE3APBridge.asi").exists())

    def test_rebaseline_refuses_changed_bridge(self):
        self.run_action("install")
        (self.binary / "ASI/LE3APBridge.asi").write_bytes(b"foreign")
        with self.assertRaisesRegex(RuntimeError, "Changed file"):
            self.run_action("rebaseline")


if __name__ == "__main__":
    unittest.main()

import shutil
import tempfile
import unittest
from pathlib import Path

from .. import data
from ..client_core import history_digest
from ..me2save.import_save import ensure_import_career
from ..me2save.layout import parse

ENDGAME = next((root / "ME2 Saves" / "Vector_22_Sentinel_150123_368d7d4" / "Save_0050.pcsav" for root in Path(__file__).resolve().parents
               if (root / "ME2 Saves").is_dir()), Path("missing"))


@unittest.skipUnless(ENDGAME.exists(), "owner-supplied ME2 end-game save not present (source checkout only)")
class ImportSaveTests(unittest.TestCase):
    def test_writes_one_career_per_history_from_the_newest_finished_save(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            (root / "Vector_22_Sentinel_150123_368d7d4").mkdir()
            shutil.copy2(ENDGAME, root / "Vector_22_Sentinel_150123_368d7d4" / "Save_0050.pcsav")
            digest = history_digest(data.HISTORY)
            path, created = ensure_import_career(data.HISTORY, digest, root)
            self.assertTrue(created)
            self.assertTrue(path.parent.name.startswith("Vector_22_Sentinel_") and path.parent.name.endswith("_" + digest[:7]))
            self.assertEqual(parse(path.read_bytes()).end_game_state, 2)
            again, created = ensure_import_career(data.HISTORY, digest, root)
            self.assertEqual((again, created), (path, False))
            self.assertEqual(len(list(root.iterdir())), 2)

    def test_no_finished_save_is_reported(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(FileNotFoundError):
                ensure_import_career(data.HISTORY, "0" * 64, Path(root))

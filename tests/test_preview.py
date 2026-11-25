import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from system_manager import jsonconf, paths, preview, rpc, state, util


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sm-preview-"))
        self.saved = {"BAR_CONFIG": paths.BAR_CONFIG, "CONFIG_ROOT": paths.CONFIG_ROOT,
                      "BACKUP_ROOT": paths.BACKUP_ROOT}
        paths.BAR_CONFIG = self.tmp / "bar.json"
        paths.CONFIG_ROOT = self.tmp / "state"
        paths.BACKUP_ROOT = self.tmp / "state" / "backups"

    def tearDown(self):
        paths.BAR_CONFIG = self.saved["BAR_CONFIG"]
        paths.CONFIG_ROOT = self.saved["CONFIG_ROOT"]
        paths.BACKUP_ROOT = self.saved["BACKUP_ROOT"]

    def test_atomic_write_records_and_does_not_write(self):
        target = self.tmp / "file.txt"
        target.write_text("old\n")
        with preview.capture() as entries:
            util.atomic_write(target, "new\n")
        self.assertEqual(target.read_text(), "old\n")
        self.assertEqual(len(entries), 1)
        self.assertIn("-old", entries[0]["diff"])
        self.assertIn("+new", entries[0]["diff"])

    def test_identical_content_is_not_a_change(self):
        target = self.tmp / "file.txt"
        target.write_text("same\n")
        with preview.capture() as entries:
            util.atomic_write(target, "same\n")
        self.assertEqual(entries, [])

    def test_session_commit_keeps_no_backup_in_preview(self):
        target = self.tmp / "file.txt"
        target.write_text("old\n")
        with preview.capture() as entries:
            session = state.Session("test")
            session.write(target, "new\n")
            session.commit()
        self.assertEqual(len(entries), 1)
        self.assertFalse((self.tmp / "state" / "backups").exists())

    def test_preview_flag_is_scoped(self):
        self.assertFalse(preview.active())
        with preview.capture():
            self.assertTrue(preview.active())
        self.assertFalse(preview.active())

    def test_apply_preview_returns_a_diff_and_leaves_the_file(self):
        paths.BAR_CONFIG.write_text('{\n  "notifications": {"max_stored": 25}\n}\n')
        response = rpc.handle({"id": 1, "method": "apply", "params": {
            "id": "notifications", "changes": {"max_stored": 60}, "preview": True}})
        result = response["result"]
        self.assertTrue(result["ok"])
        self.assertEqual(result["preview"][0]["path"], str(paths.BAR_CONFIG))
        self.assertEqual(jsonconf.load()["notifications"]["max_stored"], 25)
        self.assertIn("+", result["preview"][0]["diff"])

    def test_apply_preview_is_refused_for_system_only_panels(self):
        response = rpc.handle({"id": 1, "method": "apply", "params": {
            "id": "power", "changes": {"ppd_profile": "balanced"}, "preview": True}})
        self.assertFalse(response["result"]["ok"])
        self.assertIn("no file diff", response["result"]["message"])

    def test_apply_without_preview_still_writes(self):
        paths.BAR_CONFIG.write_text('{}\n')
        response = rpc.handle({"id": 1, "method": "apply", "params": {
            "id": "notifications", "changes": {"max_stored": 60}}})
        self.assertTrue(response["result"]["ok"])
        self.assertEqual(jsonconf.load()["notifications"]["max_stored"], 60)


if __name__ == "__main__":
    unittest.main()

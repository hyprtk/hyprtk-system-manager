import json
import tempfile
import unittest
from pathlib import Path

from system_manager import paths, state


class StateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sm-state-"))
        self.saved = (paths.CONFIG_ROOT, paths.BACKUP_ROOT)
        paths.CONFIG_ROOT = self.tmp
        paths.BACKUP_ROOT = self.tmp / "backups"

    def tearDown(self):
        paths.CONFIG_ROOT, paths.BACKUP_ROOT = self.saved

    def test_commit_snapshots_and_restore(self):
        target = self.tmp / "x.conf"
        target.write_text("a\n")
        session = state.Session("test edit")
        session.write(target, "b\n")
        self.assertEqual(target.read_text(), "b\n")
        manifest = session.commit()
        self.assertEqual(manifest["status"], "ok")
        self.assertTrue((paths.BACKUP_ROOT / manifest["stamp"] / "manifest.json").is_file())
        result = state.restore(manifest["stamp"])
        self.assertEqual(result["restored"], [str(target)])
        self.assertEqual(target.read_text(), "a\n")

    def test_rollback_restores_original(self):
        target = self.tmp / "x.conf"
        target.write_text("a\n")
        session = state.Session("test")
        session.write(target, "b\n")
        session.rollback()
        self.assertEqual(target.read_text(), "a\n")

    def test_rollback_removes_created_file(self):
        target = self.tmp / "new.conf"
        session = state.Session("test")
        session.write(target, "new\n")
        self.assertTrue(target.is_file())
        session.rollback()
        self.assertFalse(target.exists())

    def test_backups_lists_manifests(self):
        target = self.tmp / "x.conf"
        target.write_text("a\n")
        session = state.Session("listed")
        session.write(target, "b\n")
        session.commit()
        listed = state.backups()
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["reason"], "listed")
        self.assertIn(str(target), listed[0]["files"])

    def test_restore_unknown_stamp(self):
        with self.assertRaises(state.TransactionError):
            state.restore("does-not-exist")

    def test_manifest_is_json(self):
        target = self.tmp / "x.conf"
        target.write_text("a\n")
        session = state.Session("json")
        session.write(target, "b\n")
        manifest = session.commit()
        data = json.loads((paths.BACKUP_ROOT / manifest["stamp"] / "manifest.json").read_text())
        self.assertEqual(data["stamp"], manifest["stamp"])


if __name__ == "__main__":
    unittest.main()

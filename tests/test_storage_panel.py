import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from system_manager import form, paths, priv, util
from system_manager.panels import storage
from system_manager.util import RunResult

FSTAB = """\
# /etc/fstab: static file system information
UUID=1234-abcd / ext4 rw,relatime 0 1
tmpfs /tmp tmpfs defaults,noatime 0 0
"""


def fake_install(argv, *, input=None, timeout=120, action="system"):
    """Emulate ``install`` so the mocked privilege layer still writes."""
    import shutil

    if argv and argv[0] == "tee":
        Path(argv[1]).write_text(input or "")
        return RunResult(0, "", "")
    if "-d" in argv:
        Path(argv[-1]).mkdir(parents=True, exist_ok=True)
        return RunResult(0, "", "")
    target = argv[-1]
    source = argv[-2]
    Path(target).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    return RunResult(0, "", "")


class FstabParseTests(unittest.TestCase):
    def test_comments_and_blank_lines_are_skipped(self):
        entries = storage.parse_fstab(FSTAB)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["device"], "UUID=1234-abcd")
        self.assertEqual(entries[0]["index"], 1)

    def test_short_lines_are_ignored(self):
        self.assertEqual(storage.parse_fstab("garbage\n"), [])

    def test_entry_line_round_trips(self):
        entry = {"device": "/dev/sdb1", "mountpoint": "/mnt/data", "fstype": "ext4",
                 "options": "defaults", "dump": 0, "pass": 2}
        self.assertEqual(storage._entry_line(entry),
                         "/dev/sdb1 /mnt/data ext4 defaults 0 2")


class FstabValidationTests(unittest.TestCase):
    def test_good_entry_passes(self):
        entry = {"device": "UUID=abcd", "mountpoint": "/mnt/data", "fstype": "ext4",
                 "options": "defaults,noatime", "dump": 0, "pass": 2}
        self.assertEqual(storage.validate_entry(entry, []), [])

    def test_relative_mountpoint_is_rejected(self):
        entry = {"device": "UUID=abcd", "mountpoint": "data", "fstype": "ext4",
                 "options": "defaults", "dump": 0, "pass": 2}
        self.assertTrue(any("absolute" in item for item in
                            storage.validate_entry(entry, [])))

    def test_duplicate_mountpoint_is_rejected(self):
        existing = [{"index": 1, "mountpoint": "/mnt/data"}]
        entry = {"device": "UUID=abcd", "mountpoint": "/mnt/data", "fstype": "ext4",
                 "options": "defaults", "dump": 0, "pass": 2}
        self.assertTrue(any("already" in item for item in
                            storage.validate_entry(entry, existing)))

    def test_unknown_device_is_rejected(self):
        entry = {"device": "/dev/nope9", "mountpoint": "/mnt/x", "fstype": "ext4",
                 "options": "defaults", "dump": 0, "pass": 2}
        self.assertTrue(any("does not exist" in item for item in
                            storage.validate_entry(entry, [], exists=lambda _p: False)))

    def test_injected_option_is_rejected(self):
        entry = {"device": "UUID=abcd", "mountpoint": "/mnt/x", "fstype": "ext4",
                 "options": "defaults;rm -rf /", "dump": 0, "pass": 2}
        self.assertTrue(storage.validate_entry(entry, []))

    def test_pass_out_of_range_is_rejected(self):
        entry = {"device": "UUID=abcd", "mountpoint": "/mnt/x", "fstype": "ext4",
                 "options": "defaults", "dump": 0, "pass": 9}
        self.assertTrue(any("fsck" in item for item in
                            storage.validate_entry(entry, [])))


class FstabVerifyTests(unittest.TestCase):
    def test_findmnt_errors_are_collected(self):
        output = "0 parse errors, 1 error\n/mnt/x\n   [E] unreachable target\n"
        with mock.patch.object(util, "which", return_value="/usr/bin/findmnt"), \
             mock.patch.object(util, "run", return_value=RunResult(1, output, "")):
            result = storage.verify_fstab("x\n")
        self.assertFalse(result["ok"])
        self.assertEqual(result["errors"], ["unreachable target"])

    def test_warnings_do_not_fail(self):
        output = "   [W] ext4 does not match with on-disk ntfs\n"
        with mock.patch.object(util, "which", return_value="/usr/bin/findmnt"), \
             mock.patch.object(util, "run", return_value=RunResult(0, output, "")):
            result = storage.verify_fstab("x\n")
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["warnings"]), 1)

    def test_without_findmnt_nothing_is_checked(self):
        with mock.patch.object(util, "which", return_value=None):
            result = storage.verify_fstab("x\n")
        self.assertTrue(result["ok"])
        self.assertFalse(result["checked"])


class FstabApplyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sm-fstab-"))
        self.fstab = self.tmp / "fstab"
        self.fstab.write_text(FSTAB)
        self.mountpoint = self.tmp / "mnt" / "data"
        self.saved = {"FSTAB": storage.FSTAB, "CONFIG_ROOT": paths.CONFIG_ROOT}
        storage.FSTAB = self.fstab
        paths.CONFIG_ROOT = self.tmp / "state"

    def tearDown(self):
        storage.FSTAB = self.saved["FSTAB"]
        paths.CONFIG_ROOT = self.saved["CONFIG_ROOT"]

    def _changes(self):
        return {"fstab_device": "UUID=new-disk", "fstab_mount": str(self.mountpoint),
                "fstab_type": "ext4", "fstab_options": "defaults,noatime",
                "fstab_pass": 2}

    def test_add_entry_creates_mountpoint_and_writes(self):
        with mock.patch.object(util, "which", return_value=None), \
             mock.patch.object(priv, "run_priv", side_effect=fake_install) as run:
            result = storage.apply(self._changes())
        self.assertTrue(result["ok"], result)
        self.assertTrue(self.mountpoint.is_dir())
        self.assertIn("UUID=new-disk", self.fstab.read_text())
        self.assertTrue(any(str(self.fstab) in str(call) for call in run.call_args_list))

    def test_add_entry_refuses_a_duplicate_mountpoint(self):
        changes = self._changes()
        changes["fstab_mount"] = "/tmp"
        with mock.patch.object(util, "which", return_value=None), \
             mock.patch.object(priv, "run_priv", side_effect=fake_install):
            result = storage.apply(changes)
        self.assertFalse(result["ok"])

    def test_findmnt_error_blocks_the_write(self):
        output = "   [E] unreachable source\n"
        with mock.patch.object(util, "which", return_value="/usr/bin/findmnt"), \
             mock.patch.object(util, "run", return_value=RunResult(1, output, "")), \
             mock.patch.object(priv, "run_priv", side_effect=fake_install):
            result = storage.apply(self._changes())
        self.assertFalse(result["ok"])
        self.assertNotIn("UUID=new-disk", self.fstab.read_text())

    def test_remove_entry_rewrites_the_file(self):
        with mock.patch.object(util, "which", return_value=None), \
             mock.patch.object(priv, "run_priv", side_effect=fake_install):
            result = storage.action("storage.fstab_remove", {"line": 2})
        self.assertTrue(result["ok"], result)
        self.assertNotIn("tmpfs /tmp", self.fstab.read_text())
        self.assertIn("UUID=1234-abcd", self.fstab.read_text())

    def test_remove_refuses_a_comment_line(self):
        result = storage.action("storage.fstab_remove", {"line": 0})
        self.assertFalse(result["ok"])

    def test_snapshot_is_kept_before_writing(self):
        with mock.patch.object(util, "which", return_value=None), \
             mock.patch.object(priv, "run_priv", side_effect=fake_install):
            storage.apply(self._changes())
        kept = list((self.tmp / "state" / "system").glob("*fstab*"))
        self.assertEqual(len(kept), 1)
        self.assertIn("tmpfs /tmp", kept[0].read_text())


class StorageActionTests(unittest.TestCase):
    def test_mount_uses_udisks(self):
        with mock.patch.object(util, "which", return_value="/usr/bin/udisksctl"), \
             mock.patch.object(util, "run", return_value=RunResult(0, "mounted", "")) as run:
            storage.action("storage.mount", {"device": "/dev/sdb1"})
        self.assertEqual(run.call_args[0][0], ["udisksctl", "mount", "-b", "/dev/sdb1"])

    def test_unmount_uses_udisks(self):
        with mock.patch.object(util, "which", return_value="/usr/bin/udisksctl"), \
             mock.patch.object(util, "run", return_value=RunResult(0, "unmounted", "")) as run:
            storage.action("storage.unmount", {"device": "/dev/sdb1"})
        self.assertEqual(run.call_args[0][0], ["udisksctl", "unmount", "-b", "/dev/sdb1"])

    def test_invalid_device_is_refused(self):
        self.assertFalse(storage.action("storage.mount", {"device": "/etc/passwd"})["ok"])

    def test_format_refuses_a_mounted_device(self):
        with mock.patch.object(util, "which", return_value="/usr/bin/mkfs.ext4"), \
             mock.patch.object(util, "run", return_value=RunResult(0, "/dev/sdb1 /mnt\n", "")):
            result = storage.action("storage.format",
                                    {"device": "/dev/sdb1", "fstype": "ext4"})
        self.assertFalse(result["ok"])
        self.assertIn("mounted", result["message"])

    def test_format_requires_a_confirmed_filesystem(self):
        with mock.patch.object(util, "which", return_value="/usr/bin/mkfs.ext4"):
            result = storage.action("storage.format",
                                    {"device": "/dev/sdb1", "fstype": "zfs"})
        self.assertFalse(result["ok"])


class StoragePageTests(unittest.TestCase):
    def test_page_lists_the_fstab_entries(self):
        tmp = Path(tempfile.mkdtemp(prefix="sm-fstab-"))
        fstab = tmp / "fstab"
        fstab.write_text(FSTAB)
        with mock.patch.object(storage, "FSTAB", fstab), \
             mock.patch.object(util, "which", return_value=None), \
             mock.patch.object(util, "run", return_value=RunResult(127, "", "missing")):
            model = storage.probe()
        self.assertEqual(form.validate(model), [])
        titles = [row.get("title") for section in model["sections"]
                  for row in section["rows"] if row["type"] == "list"]
        self.assertIn("/tmp", [item["title"] for row in model["sections"]
                               for row in row["rows"] if row["type"] == "list"
                               for item in row["items"]])


if __name__ == "__main__":
    unittest.main()

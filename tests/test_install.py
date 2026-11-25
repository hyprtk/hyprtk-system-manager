import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from system_manager import __version__

ROOT = Path(__file__).resolve().parents[1]


class InstallerTests(unittest.TestCase):
    def test_destdir_system_install_and_uninstall(self):
        tmp = Path(tempfile.mkdtemp(prefix="sm-install-"))
        (tmp / "home").mkdir()
        try:
            result = subprocess.run(
                ["./install.sh", "--system", "--prefix", "/usr"],
                cwd=ROOT, env={"DESTDIR": str(tmp), "PATH": "/usr/bin:/bin",
                               "HOME": str(tmp / "home")},
                capture_output=True, text=True, timeout=120,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = tmp / "usr/share/hyprtk-system-manager"
            self.assertTrue((payload / "backend/system_manager/cli.py").is_file())
            link = tmp / "usr/bin/hyprtk-settings"
            self.assertTrue(link.is_symlink())
            self.assertEqual(os.readlink(link),
                             "/usr/share/hyprtk-system-manager/bin/hyprtk-settings")
            self.assertTrue((tmp / "usr/libexec/hyprtk-sm-helper").is_file())
            self.assertTrue(
                (tmp / "usr/share/polkit-1/actions/org.hyprtk.system-manager.policy").is_file())
            desktop = (tmp / "usr/share/applications/hyprtk-system-manager.desktop").read_text()
            self.assertIn('Exec="/usr/bin/hyprtk-settings"', desktop)
            self.assertIn("Icon=/usr/share/hyprtk-system-manager/", desktop)
            self.assertNotIn(str(tmp), desktop)
            self.assertIn(__version__, result.stdout)

            removal = subprocess.run(
                ["./install.sh", "--system", "--prefix", "/usr", "--uninstall"],
                cwd=ROOT, env={"DESTDIR": str(tmp), "PATH": "/usr/bin:/bin",
                               "HOME": str(tmp / "home")},
                capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(removal.returncode, 0, removal.stderr)
            self.assertFalse((tmp / "usr/share/hyprtk-system-manager").exists())
            self.assertFalse((tmp / "usr/libexec/hyprtk-sm-helper").exists())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_dry_run_system_mode_needs_no_root(self):
        result = subprocess.run(
            ["./install.sh", "--system", "--prefix", "/usr", "--dry-run"],
            cwd=ROOT, env={"PATH": "/usr/bin:/bin", "HOME": "/tmp"}, capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("/usr/share/hyprtk-system-manager", result.stdout)
        self.assertIn("polkit", result.stdout.lower())


class PackagingTests(unittest.TestCase):
    def test_recipes_exist_and_match_the_version(self):
        recipes = {
            "PKGBUILD": r"^pkgver=(.+)$",
            "hyprtk-system-manager.spec": r"^Version:\s+(\S+)$",
            "APKBUILD": r"^pkgver=(.+)$",
        }
        for name, pattern in recipes.items():
            with self.subTest(recipe=name):
                text = (ROOT / "packaging" / name).read_text()
                match = re.search(pattern, text, re.MULTILINE)
                self.assertIsNotNone(match, name)
                self.assertEqual(match.group(1).strip(), __version__)

    def test_debian_rules_use_the_installer(self):
        rules = (ROOT / "packaging" / "debian" / "rules").read_text()
        self.assertIn("install.sh --system --prefix /usr", rules)
        self.assertIn("DESTDIR=", rules)

    def test_policy_is_valid_xml(self):
        import xml.dom.minidom

        document = xml.dom.minidom.parse(
            str(ROOT / "data" / "org.hyprtk.system-manager.policy"))
        actions = document.getElementsByTagName("action")
        ids = [item.getAttribute("id") for item in actions]
        self.assertEqual(len(ids), 5)
        self.assertIn("org.hyprtk.system-manager.manage-storage", ids)
        for action in actions:
            annotations = action.getElementsByTagName("annotate")
            keys = [item.getAttribute("key") for item in annotations]
            self.assertIn("org.freedesktop.policykit.exec.path", keys)
            self.assertIn("org.freedesktop.policykit.exec.argv1", keys)


if __name__ == "__main__":
    unittest.main()

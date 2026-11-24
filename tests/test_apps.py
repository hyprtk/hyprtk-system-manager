import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from system_manager import apps


class AppsTests(unittest.TestCase):
    def test_version_from_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "__init__.py"
            path.write_text('"""x"""\n__version__ = "1.2.3"\n')
            self.assertEqual(apps.version_from(path), "1.2.3")

    def test_version_from_zip(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "app"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("pkg/__init__.py", '__version__ = "0.9.1"\n')
            self.assertEqual(apps._version_from_zip(archive, "pkg/__init__.py"), "0.9.1")
            self.assertEqual(apps._version_from_zip(archive, "nope.py"), "")

    def test_version_globs_expand_parent_wildcards(self):
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp) / "venv" / "lib" / "python3.14" / "site-packages" / "pkg"
            pkg.mkdir(parents=True)
            (pkg / "__init__.py").write_text('__version__ = "4.5.6"\n')
            pattern = str(Path(tmp) / "venv" / "lib" / "python*" / "site-packages" / "pkg" / "__init__.py")
            self.assertEqual(apps.version({"version_globs": [pattern]}), "4.5.6")

    def test_version_prefers_files_then_glob_then_zip(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "a.py"
            first.write_text('__version__ = "1.0.0"\n')
            self.assertEqual(apps.version({"version_files": [first]}), "1.0.0")

    def test_settings_argv_requires_installed_command(self):
        with mock.patch.object(apps.util, "which", return_value=None):
            self.assertEqual(apps.settings_argv({"settings": ["definitely-not-here"]}), [])
        with mock.patch.object(apps.util, "which", return_value="/usr/bin/config-manager"):
            self.assertEqual(apps.settings_argv({"settings": ["config-manager", "open"]}),
                             ["config-manager", "open"])
        self.assertEqual(apps.settings_argv({"settings": []}), [])

    def test_describe_fields(self):
        described = apps.describe({
            "id": "x", "name": "pkg", "title": "X", "binary": "x",
            "version_files": [], "settings": [], "settings_hint": "Ctrl+,",
        })
        self.assertEqual(described["settings_hint"], "Ctrl+,")
        self.assertIn("installed", described)
        self.assertIn("running", described)


if __name__ == "__main__":
    unittest.main()

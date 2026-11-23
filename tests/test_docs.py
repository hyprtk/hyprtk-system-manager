import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


class DocsTests(unittest.TestCase):
    def test_required_docs_exist(self):
        for name in ("README.md", "PLAN.md", "RESEARCH.md", "CHANGELOG.md", "LICENSE"):
            self.assertTrue((ROOT / name).is_file(), name)

    def test_readme_relative_links_resolve(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        for target in LINK_RE.findall(text):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            with self.subTest(target=target):
                self.assertTrue((ROOT / target.split("#")[0]).exists(), target)

    def test_readme_images_exist(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        for target in IMAGE_RE.findall(text):
            if target.startswith(("http://", "https://")):
                continue
            with self.subTest(target=target):
                self.assertTrue((ROOT / target).is_file(), target)

    def test_changelog_has_current_version(self):
        from system_manager import __version__

        text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn(f"## [{__version__}]", text)

    def test_desktop_entry_and_icon(self):
        desktop = (ROOT / "data" / "hyprtk-system-manager.desktop").read_text(encoding="utf-8")
        self.assertIn("Exec=hyprtk-settings open", desktop)
        self.assertIn("Icon=hyprtk-system-manager", desktop)
        self.assertIn("Categories=Settings;System;", desktop)
        icon = (ROOT / "data" / "hyprtk-system-manager.svg").read_text(encoding="utf-8")
        self.assertTrue(icon.lstrip().startswith("<svg"))
        self.assertIn("</svg>", icon)


if __name__ == "__main__":
    unittest.main()

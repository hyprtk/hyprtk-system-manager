import json
import tempfile
import unittest
from pathlib import Path

from system_manager import jsonconf, paths


class JsonConfTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sm-json-"))
        self.saved = paths.BAR_CONFIG
        paths.BAR_CONFIG = self.tmp / "config.json"

    def tearDown(self):
        paths.BAR_CONFIG = self.saved

    def test_patch_preserves_unknown_keys(self):
        jsonconf.patch({"a": {"b": 1}, "keep": True})
        data = jsonconf.patch({"a": {"c": 2}})
        self.assertEqual(data["a"], {"b": 1, "c": 2})
        self.assertTrue(data["keep"])
        on_disk = json.loads(paths.BAR_CONFIG.read_text())
        self.assertEqual(on_disk, data)

    def test_get_nested(self):
        jsonconf.patch({"theme": {"accent": "#c084fc"}, "opacity": 0.9})
        self.assertEqual(jsonconf.get("theme.accent"), "#c084fc")
        self.assertEqual(jsonconf.get("nope", "fallback"), "fallback")

    def test_load_corrupt_file(self):
        paths.BAR_CONFIG.write_text("{not json")
        self.assertEqual(jsonconf.load(), {})

    def test_flatten(self):
        flat = jsonconf.flatten({"a": {"b": 1}, "c": 2})
        self.assertEqual(flat, {"a.b": 1, "c": 2})

    def test_atomic_write_leaves_no_temp_files(self):
        jsonconf.patch({"x": 1})
        leftovers = [p.name for p in self.tmp.iterdir() if p.name.startswith(".config.")]
        self.assertEqual(leftovers, [])


if __name__ == "__main__":
    unittest.main()

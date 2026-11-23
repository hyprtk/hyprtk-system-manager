import unittest

from system_manager import catalog, form


class CatalogTests(unittest.TestCase):
    def test_ids_unique(self):
        ids = [panel["id"] for panel in catalog.PANELS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_panel_has_metadata(self):
        for panel in catalog.PANELS:
            with self.subTest(panel=panel["id"]):
                self.assertIn(panel["group"], catalog.GROUP_INDEX)
                self.assertTrue(panel["title"])
                self.assertTrue(panel["description"])
                self.assertTrue(panel["keywords"])
                self.assertIn(panel["status"], form.STATUS_LABELS)
                self.assertEqual(len(panel["icon"]), 1)

    def test_groups_cover_all_panels(self):
        catalog_data = catalog.catalog()
        listed = []
        for group in catalog_data["groups"]:
            self.assertTrue(group["panels"])
            listed.extend(group["panels"])
        self.assertEqual(sorted(listed), sorted(p["id"] for p in catalog.PANELS))

    def test_every_module_imports(self):
        for panel in catalog.PANELS:
            with self.subTest(panel=panel["id"]):
                module = catalog.module_for(panel["id"])
                self.assertTrue(callable(module.probe))

    def test_unknown_panel_raises(self):
        with self.assertRaises(KeyError):
            catalog.module_for("nope")

    def test_search(self):
        self.assertEqual(catalog.search("wifi")[0]["id"], "network")
        self.assertEqual(catalog.search("display")[0]["id"], "displays")
        self.assertIn("users", [item["id"] for item in catalog.search("user accounts")])
        self.assertEqual(catalog.search(""), [])
        self.assertEqual(catalog.search("zzzz-nothing"), [])


if __name__ == "__main__":
    unittest.main()

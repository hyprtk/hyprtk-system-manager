import unittest
from unittest import mock

from system_manager import catalog, form, util
from system_manager.util import RunResult


class OfflinePanelTests(unittest.TestCase):
    """Every panel must return a valid page with no tools on the machine."""

    def test_all_panels_degrade_cleanly(self):
        with mock.patch.object(util, "which", return_value=None), \
             mock.patch.object(util, "run", return_value=RunResult(127, "", "missing")):
            for panel in catalog.PANELS:
                with self.subTest(panel=panel["id"]):
                    module = catalog.module_for(panel["id"])
                    model = module.probe()
                    self.assertEqual(model["id"], panel["id"])
                    self.assertEqual(model["title"], panel["title"])
                    self.assertEqual(form.validate(model), [])

    def test_panel_ids_match_catalog(self):
        for panel in catalog.PANELS:
            with self.subTest(panel=panel["id"]):
                self.assertIn("sections", catalog.module_for(panel["id"]).probe())


if __name__ == "__main__":
    unittest.main()

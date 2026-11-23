import tempfile
import unittest
from pathlib import Path

from system_manager import paths, rpc


class RpcTests(unittest.TestCase):
    def test_unknown_method(self):
        response = rpc.handle({"id": 1, "method": "nope"})
        self.assertEqual(response["id"], 1)
        self.assertIn("unknown method", response["error"])

    def test_unknown_panel(self):
        response = rpc.handle({"id": 2, "method": "panel", "params": {"id": "nope"}})
        self.assertIn("unknown panel", response["error"])

    def test_catalog(self):
        response = rpc.handle({"id": 3, "method": "catalog"})
        self.assertEqual(response["result"]["groups"][0]["id"], "system")
        self.assertTrue(response["result"]["panels"])

    def test_search(self):
        response = rpc.handle({"id": 4, "method": "search", "params": {"query": "bluetooth"}})
        self.assertEqual(response["result"]["results"][0]["id"], "bluetooth")

    def test_ui_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            saved = paths.UI_STATE
            paths.UI_STATE = Path(tmp) / "ui.json"
            try:
                rpc.handle({"id": 5, "method": "ui.set", "params": {"values": {"last_page": "fonts"}}})
                response = rpc.handle({"id": 6, "method": "ui.get"})
                self.assertEqual(response["result"]["last_page"], "fonts")
            finally:
                paths.UI_STATE = saved

    def test_fs_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "a.txt").write_text("x")
            Path(tmp, "dir").mkdir()
            response = rpc.handle({"id": 7, "method": "fs.list", "params": {"path": tmp}})
            names = [entry["name"] for entry in response["result"]["entries"]]
            self.assertEqual(names, ["dir", "a.txt"])

    def test_handler_exception_is_isolated(self):
        def boom(params):
            raise RuntimeError("kaboom")

        rpc.HANDLERS["boom"] = boom
        try:
            response = rpc.handle({"id": 8, "method": "boom"})
        finally:
            rpc.HANDLERS.pop("boom", None)
        self.assertIn("RuntimeError: kaboom", response["error"])

    def test_panel_contract_is_valid(self):
        response = rpc.handle({"id": 9, "method": "panel", "params": {"id": "datetime"}})
        self.assertNotIn("error", response)
        self.assertEqual(response["result"]["id"], "datetime")
        self.assertIn("sections", response["result"])


if __name__ == "__main__":
    unittest.main()

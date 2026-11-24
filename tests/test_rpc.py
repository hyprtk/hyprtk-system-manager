import io
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from system_manager import form, paths, rpc, util


class RpcTests(unittest.TestCase):
    def setUp(self):
        with rpc._CACHE_LOCK:
            rpc._CACHE.clear()
        with rpc._WARM_LOCK:
            rpc._WARM["started"] = False
            rpc._WARM["running"] = False

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

    def test_ui_set_stores_last_page_only(self):
        # The sidebar no longer has a Recent section, so ui state must not keep a
        # recent list around (a stale one was previously served on `hello`).
        with tempfile.TemporaryDirectory() as tmp:
            saved = paths.UI_STATE
            paths.UI_STATE = Path(tmp) / "ui.json"
            try:
                util.write_json(paths.UI_STATE, {"last_page": "about",
                                                 "recent": ["fonts", "users"]})
                rpc.handle({"id": 10, "method": "ui.set", "params": {"values": {"last_page": "fonts"}}})
                rpc.handle({"id": 11, "method": "ui.set", "params": {"values": {"last_page": "users"}}})
                response = rpc.handle({"id": 12, "method": "ui.get"})
                self.assertEqual(response["result"]["last_page"], "users")
                self.assertNotIn("recent", response["result"])
                self.assertNotIn("recent", util.read_json(paths.UI_STATE, {}))
            finally:
                paths.UI_STATE = saved

    def test_search_matches_cached_rows(self):
        model = form.page(
            id="input", title="Input Devices", group="hardware", icon="\uf11c",
            status="live", sections=[form.section("Touchpad", [
                form.toggle("tap", "Tap to click", True),
                form.slider("sensitivity", "Mouse sensitivity", 0, minimum=-1, maximum=1),
            ])],
        )
        fake = mock.Mock(probe=lambda: model)
        with mock.patch.object(rpc.catalog, "module_for", return_value=fake):
            rpc.handle({"id": 20, "method": "panel", "params": {"id": "input"}})
        response = rpc.handle({"id": 21, "method": "search", "params": {"query": "tap"}})
        results = response["result"]["results"]
        self.assertTrue(results)
        self.assertEqual(results[0]["id"], "input")
        self.assertIn("Tap to click", results[0]["matches"])
        self.assertTrue(response["result"]["indexed"] >= 1)

    def test_search_matches_rows_without_catalog_hit(self):
        model = form.page(
            id="input", title="Input Devices", group="hardware", icon="\uf11c",
            status="live", sections=[form.section("Touchpad", [
                form.toggle("tap", "Tap to click", True),
            ])],
        )
        with rpc._CACHE_LOCK:
            rpc._CACHE["input"] = (time.time(), model)
        response = rpc.handle({"id": 22, "method": "search", "params": {"query": "click"}})
        self.assertEqual(response["result"]["results"][0]["id"], "input")

    def test_search_empty_query(self):
        response = rpc.handle({"id": 23, "method": "search", "params": {"query": "  "}})
        self.assertEqual(response["result"]["results"], [])

    def test_serve_answers_out_of_order(self):
        def slow(params):
            time.sleep(0.25)
            return {"ok": True}

        def fast(params):
            return {"ok": True}

        rpc.HANDLERS["slow-test"] = slow
        rpc.HANDLERS["fast-test"] = fast
        source = io.StringIO('{"id": 1, "method": "slow-test"}\n{"id": 2, "method": "fast-test"}\n')
        sink = io.StringIO()
        try:
            with mock.patch.object(sys, "stdin", source), mock.patch.object(sys, "stdout", sink):
                rpc.serve()
        finally:
            rpc.HANDLERS.pop("slow-test", None)
            rpc.HANDLERS.pop("fast-test", None)
        ids = [json.loads(line)["id"] for line in sink.getvalue().splitlines() if line.strip()]
        self.assertEqual(ids[0], 2)
        self.assertEqual(sorted(ids), [1, 2])

    def test_panel_contract_is_valid(self):
        response = rpc.handle({"id": 9, "method": "panel", "params": {"id": "datetime"}})
        self.assertNotIn("error", response)
        self.assertEqual(response["result"]["id"], "datetime")
        self.assertIn("sections", response["result"])


if __name__ == "__main__":
    unittest.main()

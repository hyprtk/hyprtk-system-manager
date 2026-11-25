import unittest
from pathlib import Path
from unittest import mock

from system_manager import util
from system_manager.panels import locale
from system_manager.util import RunResult

LOCALECTL = """System Locale: LANG=en_GB.UTF-8
       VC Keymap: uk
      X11 Layout: gb
       X11 Model: pc105
     X11 Options: terminate:ctrl_alt_bksp
"""

LOCALE_GEN = """# Configuration file for locale-gen
# en_US.UTF-8 UTF-8
#de_DE.UTF-8 UTF-8
en_GB.UTF-8 UTF-8
"""

SUPPORTED = """# comment
en_GB.UTF-8 UTF-8
en_US.UTF-8 UTF-8
de_DE.UTF-8 UTF-8
de_DE ISO-8859-1
ja_JP.EUC-JP EUC-JP
fr_FR.UTF-8 UTF-8
"""


class ParserTests(unittest.TestCase):
    def test_parse_localectl(self):
        state = locale.parse_localectl(LOCALECTL)
        self.assertEqual(state["System Locale"], "LANG=en_GB.UTF-8")
        self.assertEqual(state["VC Keymap"], "uk")

    def test_parse_locale_gen_ignores_comments(self):
        self.assertEqual(locale.parse_locale_gen(LOCALE_GEN), ["en_GB.UTF-8"])

    def test_supported_locales_are_utf8_only(self):
        choices = locale.supported_locales(SUPPORTED, ["C.utf8"])
        self.assertIn("en_US.UTF-8", choices)
        self.assertNotIn("de_DE", choices)
        self.assertNotIn("ja_JP.EUC-JP", choices)
        self.assertIn("C.UTF-8", choices)

    def test_normalise_locale(self):
        self.assertEqual(locale.normalise_locale("en_GB.utf8"), "en_GB.UTF-8")
        self.assertEqual(locale.normalise_locale("de_DE"), "de_DE.UTF-8")
        self.assertEqual(locale.normalise_locale("  "), "")

    def test_enable_locale_uncomments_existing_line(self):
        updated = locale.enable_locale(LOCALE_GEN, "de_DE.UTF-8")
        self.assertIn("\nde_DE.UTF-8 UTF-8\n", updated)
        self.assertEqual(updated.count("de_DE.UTF-8 UTF-8"), 1)
        self.assertEqual(sorted(locale.parse_locale_gen(updated)),
                         ["de_DE.UTF-8", "en_GB.UTF-8"])

    def test_enable_locale_appends_when_absent(self):
        updated = locale.enable_locale(LOCALE_GEN, "fr_FR.UTF-8")
        self.assertTrue(updated.rstrip().endswith("fr_FR.UTF-8 UTF-8"))
        self.assertIn("en_GB.UTF-8 UTF-8", updated)


class ProbeTests(unittest.TestCase):
    def test_probe_shows_new_locales_are_offered(self):
        def fake_run(argv, **kwargs):
            if argv[:2] == ["localectl", "status"]:
                return RunResult(0, LOCALECTL, "")
            if argv[:1] == ["locale"]:
                return RunResult(0, "C\nC.utf8\nen_GB.utf8\nPOSIX\n", "")
            return RunResult(0, "", "")

        def fake_read(path, default=""):
            return {"SUPPORTED": SUPPORTED}.get(str(path).split("/")[-1], LOCALE_GEN) \
                if "/etc/locale.gen" in str(path) or "SUPPORTED" in str(path) else default

        with mock.patch.object(util, "which", return_value="/usr/bin/localectl"), \
             mock.patch.object(util, "run", side_effect=fake_run), \
             mock.patch.object(locale.util, "read_text", side_effect=fake_read):
            page = locale.probe()

        rows = {row.get("key") or row.get("label"): row
                for section in page["sections"] for row in section["rows"]}
        values = [choice["value"] for choice in rows["locale"]["choices"]]
        self.assertIn("de_DE.UTF-8", values)
        self.assertEqual(rows["locale"]["value"], "en_GB.UTF-8")
        self.assertEqual(rows["keymap"]["value"], "uk")


class ApplyTests(unittest.TestCase):
    def setUp(self):
        # A test must never reach the real privilege helper: on this box pkexec
        # authorisation is session-cached, so an unmocked call really does change
        # the system (it once set the console keymap from a test).
        self.priv = mock.patch.object(locale.priv, "run_priv",
                                      return_value=RunResult(0, "", ""))
        self.run_priv = self.priv.start()
        self.addCleanup(self.priv.stop)

    def test_apply_sets_and_generates_in_one_privileged_call(self):
        calls = []
        with mock.patch.object(locale.util, "read_text", return_value=LOCALE_GEN), \
             mock.patch.object(locale.priv, "run_priv",
                               side_effect=lambda argv, **kw: calls.append(argv) or RunResult(0, "", "")):
            result = locale.apply({"locale": "de_DE.UTF-8", "generate": True})
        self.assertTrue(result["ok"])
        self.assertEqual(len(calls), 1)
        script = calls[0][-1]
        self.assertIn("install -m 0644", script)
        self.assertIn("locale-gen", script)
        self.assertIn("localectl set-locale LANG=de_DE.UTF-8", script)

    def test_apply_without_generate_skips_locale_gen(self):
        calls = []
        with mock.patch.object(locale.priv, "run_priv",
                               side_effect=lambda argv, **kw: calls.append(argv) or RunResult(0, "", "")):
            result = locale.apply({"locale": "fr_FR.UTF-8", "generate": False})
        self.assertTrue(result["ok"])
        self.assertNotIn("locale-gen", calls[0][-1])
        self.assertIn("LANG=fr_FR.UTF-8", calls[0][-1])

    def test_apply_validates_locale_name(self):
        result = locale.apply({"locale": "not a locale; rm -rf /", "generate": True})
        self.assertFalse(result["ok"])

    def test_apply_validates_keymap(self):
        with mock.patch.object(util, "which", return_value="/usr/bin/localectl"), \
             mock.patch.object(util, "run", return_value=RunResult(0, "uk\nde\nus\n", "")):
            good = locale.apply({"keymap": "de"})
            bad = locale.apply({"keymap": "nope"})
        self.assertTrue(good["ok"])
        self.assertFalse(bad["ok"])
        self.assertIn("list-keymaps", bad["message"])
        self.assertIn("localectl set-keymap de", self.run_priv.call_args.args[0][-1])
        self.assertEqual(self.run_priv.call_count, 1)

    def test_apply_denied_reports_root(self):
        with mock.patch.object(locale.priv, "run_priv",
                               return_value=RunResult(1, "", "denied")):
            result = locale.apply({"locale": "en_US.UTF-8", "generate": False})
        self.assertFalse(result["ok"])
        self.assertEqual(result["requires"], "root")

    def test_apply_rejects_keymap_with_spaces(self):
        self.assertFalse(locale.apply({"keymap": "us extra"})["ok"])


if __name__ == "__main__":
    unittest.main()


class InputMethodTests(unittest.TestCase):
    def setUp(self):
        import os
        import tempfile
        from unittest import mock

        from system_manager import paths
        from system_manager.panels import locale

        self.locale = locale
        self.mock = mock
        self.tmp = tempfile.mkdtemp(prefix="sm-im-")
        self.hypr = os.path.join(self.tmp, "hypr")
        os.makedirs(self.hypr)
        self.env_file = os.path.join(self.hypr, "environment.lua")
        with open(self.env_file, "w") as handle:
            handle.write('hl.env("TERMINAL", "hyprtk-term")\n')
        self.saved = os.environ.get("HYPRTK_HYPR_DIR")
        os.environ["HYPRTK_HYPR_DIR"] = self.hypr
        self.paths = paths

    def tearDown(self):
        import os

        if self.saved is None:
            os.environ.pop("HYPRTK_HYPR_DIR", None)
        else:
            os.environ["HYPRTK_HYPR_DIR"] = self.saved

    def test_block_round_trip_preserves_the_rest(self):
        text = self.locale.im_block("fcitx5")
        self.assertIn('GTK_IM_MODULE", "fcitx"', text)
        self.assertEqual(self.locale.strip_im_block("a\n" + text + "b\n"), "a\nb\n")

    def test_read_im_from_block_and_from_plain_env(self):
        self.assertEqual(self.locale.read_im(self.locale.im_block("ibus")), "ibus")
        plain = 'hl.env("GTK_IM_MODULE", "fcitx")\n'
        self.assertEqual(self.locale.read_im(plain), "fcitx5")

    def test_apply_writes_the_block_and_reloads(self):
        with self.mock.patch.object(self.locale.base, "hypr_reload",
                                    return_value=(True, "ok")):
            result = self.locale.apply({"im_framework": "fcitx5"})
        self.assertTrue(result["ok"], result)
        text = Path(self.env_file).read_text()
        self.assertIn(self.locale.IM_START, text)
        self.assertIn('hl.env("TERMINAL", "hyprtk-term")', text)
        self.assertEqual(self.locale.read_im(text), "fcitx5")

    def test_apply_rolls_back_when_hyprland_rejects(self):
        with self.mock.patch.object(self.locale.base, "hypr_reload",
                                    return_value=(False, "error: nope")):
            result = self.locale.apply({"im_framework": "ibus"})
        self.assertFalse(result["ok"])
        self.assertNotIn(self.locale.IM_START, Path(self.env_file).read_text())

    def test_none_removes_the_block(self):
        with self.mock.patch.object(self.locale.base, "hypr_reload",
                                    return_value=(True, "ok")):
            self.locale.apply({"im_framework": "fcitx5"})
            result = self.locale.apply({"im_framework": "none"})
        self.assertTrue(result["ok"])
        self.assertNotIn(self.locale.IM_START, Path(self.env_file).read_text())

    def test_unknown_framework_is_refused(self):
        result = self.locale.apply({"im_framework": "magic"})
        self.assertFalse(result["ok"])

    def test_no_environment_file_is_reported(self):
        import os

        os.unlink(self.env_file)
        result = self.locale.apply({"im_framework": "ibus"})
        self.assertFalse(result["ok"])
        self.assertIn("environment.lua", result["message"])

    def test_probe_has_the_section(self):
        with self.mock.patch.object(self.locale.util, "which", return_value=None), \
             self.mock.patch.object(self.locale.util, "run",
                                    return_value=self.mock.Mock(ok=False, out="", lines=list)), \
             self.mock.patch.object(self.locale.util, "read_text", return_value=""):
            page = self.locale.probe()
        titles = [section["title"] for section in page["sections"]]
        self.assertIn("Input methods", titles)

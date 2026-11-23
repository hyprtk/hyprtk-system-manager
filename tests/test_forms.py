import unittest

from system_manager import form


class FormBuilderTests(unittest.TestCase):
    def test_builders(self):
        self.assertEqual(form.info("A", 1)["value"], "1")
        self.assertTrue(form.toggle("k", "L", True)["value"])
        self.assertEqual(form.choice("k", "L", "b", ["a", "b"])["choices"][1]["value"], "b")
        self.assertEqual(form.number("k", "L", 3, minimum=1, maximum=5)["min"], 1)
        self.assertEqual(form.slider("k", "L", 3, minimum=0, maximum=10)["type"], "slider")
        self.assertEqual(form.action("Go", "panel.go")["action"], "panel.go")
        self.assertEqual(form.note("hi", "warn")["tone"], "warn")

    def test_validate_accepts_a_real_page(self):
        page = form.page(
            id="x", title="X", group="system", icon="\uf013", status="full",
            sections=[form.section("S", [
                form.info("a", "b"),
                form.toggle("t", "T", True),
                form.choice("c", "C", "a", ["a"]),
                form.number("n", "N", 1, minimum=0, maximum=2),
                form.action("Go", "x.go"),
                form.note("n"),
                form.kv([{"label": "k", "value": "v"}]),
                form.list_row([{"title": "t", "actions": []}]),
            ])],
        )
        self.assertEqual(form.validate(page), [])

    def test_validate_catches_contract_breaks(self):
        bad = form.page(id="x", title="X", group="system", icon="i", status="nope",
                        sections=[form.section("S", [
                            {"type": "bogus"},
                            {"type": "choice", "label": "C"},
                            {"type": "number", "label": "N", "key": "n", "value": "one"},
                            {"type": "action", "label": "Go"},
                        ])])
        problems = form.validate(bad)
        self.assertTrue(any("bad status" in p for p in problems))
        self.assertTrue(any("unknown type" in p for p in problems))
        self.assertTrue(any("no choices" in p for p in problems))
        self.assertTrue(any("non-number" in p for p in problems))
        self.assertTrue(any("no action" in p for p in problems))

    def test_coerce(self):
        self.assertIs(form.coerce("true", False), True)
        self.assertEqual(form.coerce("12.7", 3), 13)
        self.assertEqual(form.coerce("0.5", 1.0), 0.5)
        self.assertEqual(form.coerce(None, "x"), "")

    def test_status_labels_cover_every_status(self):
        for status in ("full", "live", "partial", "read", "link", "planned"):
            self.assertIn(status, form.STATUS_LABELS)


if __name__ == "__main__":
    unittest.main()

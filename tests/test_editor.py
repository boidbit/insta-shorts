"""The Harkat editor (editor.html): a separate page that changes only what you pick, and the `X -> move 0.35` line
it writes (walk to 35% of the width). The studio page only gains a link to it. python -m unittest"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import script                                 # noqa: E402
from studio.render import Sequence                        # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
HEAD = "HOOK: x\nCAST: A = papa, B = beta\nSCENE: room\n"


class MoveLine(unittest.TestCase):
    def test_move_to_a_point(self):
        sc, w = script.parse_script(HEAD + "A: Haan | हाँ\nA -> move 0.8\nB -> move 25%\nB: Kya | क्या\n")
        self.assertEqual(w, [])
        p = Sequence(sc, 270, False, None, None).parts[0]
        end = p.plan.duration - 0.05
        self.assertAlmostEqual(p.plan.chars["A"].draw_pos(end)[0], 70 + 0.8 * 940, delta=2)
        self.assertAlmostEqual(p.plan.chars["B"].draw_pos(end)[0], 70 + 0.25 * 940, delta=2)

    def test_out_of_range_is_clamped(self):
        sc, _w = script.parse_script(HEAD + "A: Haan | हाँ\nA -> move 1.0\nB: Kya | क्या\n")
        ev = [e for e in sc["scenes"][0]["timeline"] if "move" in e][0]
        self.assertEqual(ev["move"]["x"], 1010.0)


class Pages(unittest.TestCase):
    def test_editor_page(self):
        with open(os.path.join(ROOT, "editor.html"), encoding="utf-8") as f:
            ed = f.read()
        for needle in ('id="stage"', '"move"', 'store.set("editor_out"', 'store.get("editor_in")',
                       '— studio khud —', 'fetch("index.html"'):
            self.assertIn(needle, ed)

    def test_the_studio_page_only_links_to_it(self):
        with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as f:
            page = f.read()
        self.assertIn('href="editor.html"', page)
        self.assertIn('store.get("editor_out")', page)
        self.assertIn("feel.slice(2)", page)                  # two feelings on a line are fine on the page too


if __name__ == "__main__":
    unittest.main()

"""Series by their people's names (the short prompt's talk: "Sheru (akad): ..."), the new series, the short prompt
file and the page's pickers. python -m unittest discover -s tests"""
import json
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import script                                  # noqa: E402
from studio.script import parse_script                     # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")


def page():
    with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as f:
        return f.read()


class SeriesNames(unittest.TestCase):
    def test_names_work_like_letters_and_the_series_line_can_be_anywhere(self):
        t = ("HOOK: x\nCAST: Sheru = boy, Doctor = doctor\nSheru (smug): Abey compounder! | अबे कंपाउंडर!\n"
             "Doctor (scared): Phir? | फिर?\nSheru -> bark\nSERIES: sheru_mohalla 2\n")
        sc, w = parse_script(t)
        self.assertEqual(w, [])
        ch = sc["characters"]
        self.assertEqual(sorted(ch), ["D", "S"])                       # no extra "Sheru" / "Doctor" people
        self.assertEqual(ch["S"]["kind"], "dog")
        self.assertEqual(sc["scenes"][0]["background"]["type"], "gully")   # the series' own place, from the start

    def test_the_new_series(self):
        for sid, people in (("sheru_mohalla", {"Sheru", "Doctor", "Chotu"}), ("gaon_ke_tau", {"Tau", "Tai", "Bablu",
                            "Sarpanch"}), ("pappu_class", {"Pappu", "Masterji", "Pinky"})):
            data = script.load_series(sid)
            self.assertEqual(set(data["names"].values()), people, sid)
            lines = "".join("%s: Haan. | हाँ।\n" % n for n in sorted(people))
            sc, w = parse_script("HOOK: x\nSERIES: %s\n%s" % (sid, lines))
            self.assertEqual(w, [], sid)
            self.assertEqual(len(sc["characters"]), len(people), sid)

    def test_hindi_feeling_words(self):
        sc, w = parse_script("HOOK: x\nCAST: A = uncle\nSCENE: room\nA (bore): Haan. | हाँ।\nA (darr): Na. | ना।\n")
        self.assertEqual(w, [])


class Page(unittest.TestCase):
    def test_the_short_prompt(self):
        with open(os.path.join(ROOT, "SHORT_PROMPT.md"), encoding="utf-8") as f:
            text = f.read()
        self.assertIn("| wahi line Devanagari me", text)
        self.assertTrue(text.rstrip().endswith("Mera idea:"))
        self.assertLess(len(text), 3000)
        self.assertIn('id="copyShort"', page())
        self.assertIn('fetch("SHORT_PROMPT.md"', page())

    def test_the_series_list_and_the_pickers(self):
        s = page()
        vocab = json.loads(re.search(r'<script type="application/json" id="vocab">(.*?)</script>', s, re.S).group(1))
        ids = [x["id"] for x in vocab["series"]]
        for sid in ("sharma_parivar", "office_gang", "sheru_mohalla", "gaon_ke_tau", "pappu_class"):
            self.assertIn(sid, ids)
        for needle in ("function seriesBox", "function extrasPicker", "🎒 Haath me", "🔊 Awaaz", "✨ Effect"):
            self.assertIn(needle, s)

    def test_the_series_prompt_module(self):
        from studio import director
        with open(os.path.join(ROOT, "SCRIPT_PROMPT.md"), encoding="utf-8") as f:
            text = f.read()
        self.assertNotIn("sheru_mohalla", director.prompt_text(text, keep=()))
        self.assertIn("sheru_mohalla", director.prompt_text(text, keep=("series",)))


if __name__ == "__main__":
    unittest.main()

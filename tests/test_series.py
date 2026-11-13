"""SERIES: the same family in every episode.  python -m unittest discover -s tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio.characters import assign_faces        # noqa: E402
from studio.script import load_series, parse_script  # noqa: E402

EP1 = ("HOOK: Bijli ka bill 😭\nSERIES: sharma_parivar 1\nP (angry): Bill! | बिल\nM (smug): Haan. | हाँ\n"
       "B (scared): Main nahi. | मैं नहीं\nCAPTION: Har ghar ki kahani\n")
EP2 = "HOOK: Result day 😭\nSERIES: sharma_parivar part 2\nB (grin): Papa! | पापा\nP: Kya? | क्या\n"


def faces(text):
    sc, w = parse_script(text)
    assert not w, w
    return sc, {k: (v.get("look"), v.get("face"), v.get("eyes"), v.get("nose"), v.get("brows"), v.get("hair"))
                for k, v in assign_faces(sc["characters"]).items()}


class Series(unittest.TestCase):
    def test_the_two_series_files_load(self):
        for name in ("sharma_parivar", "office_gang"):
            data = load_series(name)
            self.assertTrue(data and data["cast"] and data["title"], name)
            sc, w = parse_script("HOOK: x\nSERIES: %s\n%s: Haan. | हाँ\n" % (name, sorted(data["cast"])[0]))
            self.assertEqual(w, [], name)

    def test_only_the_people_in_the_script_come_and_they_look_the_same_in_every_episode(self):
        sc1, f1 = faces(EP1)
        sc2, f2 = faces(EP2)
        self.assertEqual(sorted(f1), ["B", "M", "P"])
        self.assertEqual(sorted(f2), ["B", "P"])
        self.assertEqual(f1["B"], f2["B"])
        self.assertEqual(f1["P"], f2["P"])
        self.assertEqual(sc1["scenes"][0]["background"]["type"], "living_room")
        self.assertEqual(sc1["meta"]["theme"], "golden")

    def test_the_badge_the_caption_and_the_hashtag(self):
        sc, _ = faces(EP1)
        self.assertEqual([o["text"] for o in sc["overlays"] if o.get("series")], ["Sharma Parivar • Part 1"])
        self.assertEqual(sc["post"]["caption"], "Har ghar ki kahani (Part 1)")
        self.assertEqual(sc["post"]["hashtags"][0], "#sharmaparivar")

    def test_the_script_s_own_cast_and_place_win(self):
        sc, w = parse_script("HOOK: x\nSERIES: sharma_parivar 4\nCAST: B = college_boy\nSCENE: park\n"
                             "B: Hi | हाय\nD: Kaun? | कौन\n")
        self.assertEqual(w, [])
        self.assertEqual(sc["characters"]["B"]["look"], "college_boy")
        self.assertEqual(sc["characters"]["D"]["look"], "dadi")
        self.assertEqual(sc["scenes"][0]["background"]["type"], "park")

    def test_an_unknown_series_says_so(self):
        _sc, w = parse_script("HOOK: x\nSERIES: nahi_hai 1\nCAST: A = uncle\nSCENE: room\nA: Haan | हाँ\n")
        self.assertTrue(any("nahi_hai" in x for x in w))


if __name__ == "__main__":
    unittest.main()

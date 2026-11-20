"""The village pack: the five places (2D and 2.5D), the five people (ghunghat, gamchha), the bhains, the tractor and
the bullock cart, the village pieces and actions. python -m unittest discover -s tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import actions, director, objects, rides, styles   # noqa: E402
from studio.characters import LOOKS                           # noqa: E402
from studio.render import make_video                          # noqa: E402
from studio.script import ROLE_LOOKS, parse_script            # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
PLACES = ("khet", "chaupal", "handpump", "kachcha_ghar", "gaon_school")
PEOPLE = ("kisan", "gaon_aurat", "sarpanch", "tau", "gaon_ladka")


def video(text, width=120):
    sc, w = parse_script(text)
    return make_video(sc, width, use_tts=False, hook="off"), w


class Places(unittest.TestCase):
    def test_every_place_in_both_looks(self):
        for place in PLACES:
            self.assertIn(place, styles.PLACES_25D)
            self.assertTrue(os.path.isfile(os.path.join(ROOT, "assets", "places", place + ".jpg")), place)
            for style in ("2d", "2.5d"):
                v, w = video("HOOK: x\nMYSTERY: off\nSTYLE: %s\nCAST: A = kisan\nSCENE: %s\nA: Ram ram. | राम राम।\n"
                             % (style, place))
                self.assertEqual(w, [], place)
                im = v.frame(v.duration * 0.5).convert("RGB")
                self.assertGreater(len(set(im.resize((40, 70)).getdata())), 60, (place, style))   # not a blank frame

    def test_the_place_words(self):
        for word, place in (("panchayat", "chaupal"), ("nal", "handpump"), ("field", "khet"),
                            ("mitti_ka_ghar", "kachcha_ghar"), ("pathshala", "gaon_school")):
            sc, w = parse_script("HOOK: x\nCAST: A = tau\nSCENE: %s\nA: Haan. | हाँ।\n" % word)
            self.assertEqual((w, sc["scenes"][0]["background"]["type"]), ([], place))


class People(unittest.TestCase):
    def test_the_looks_and_roles(self):
        for look in PEOPLE:
            self.assertIn(look, LOOKS)
            self.assertTrue(os.path.isfile(os.path.join(ROOT, "assets", "looks", look + ".png")), look)
        self.assertIn("ghunghat", LOOKS["gaon_aurat"]["accessories"])
        self.assertIn("gamchha", LOOKS["kisan"]["accessories"])
        for role, look in (("sarpanch", "sarpanch"), ("pradhan", "sarpanch"), ("tau", "tau"), ("chaudhary", "tau"),
                           ("kisan", "kisan"), ("tai", "gaon_aurat"), ("chhora", "gaon_ladka")):
            self.assertEqual(ROLE_LOOKS[role], look)

    def test_the_ghunghat_from_the_front_and_the_back(self):
        v, w = video("HOOK: x\nMYSTERY: off\nCAST: A = gaon_aurat\nSCENE: handpump\nA: Haan. | हाँ।\n"
                     "A -> turn_around\nA: Achha. | अच्छा।\n")
        self.assertEqual(w, [])
        for f in (0.3, 0.9):
            v.frame(v.duration * f)


class AnimalsAndRides(unittest.TestCase):
    def test_the_bhains_talks(self):
        v, w = video("HOOK: x\nMYSTERY: off\nCAST: K = kisan, B = bhains\nSCENE: khet\nB: Mooo. | मूऊ।\n")
        self.assertEqual(w, [])
        self.assertEqual(v.parts[-1].plan.chars["B"].spec["kind"], "buffalo")
        v.frame(v.duration * 0.5)

    def test_tractor_and_bullock_cart(self):
        for kind in ("tractor", "bail_gaadi"):
            self.assertIn(kind, objects.VEHICLES)
            self.assertTrue(rides.rideable(kind))
        self.assertEqual(objects.resolve_kind("bailgadi"), "bail_gaadi")
        v, w = video("HOOK: x\nMYSTERY: off\nCAST: K = kisan, A = gaon_aurat\nSCENE: chaupal\n"
                     "K -> ride bail_gaadi\nA -> ride bail_gaadi back\nK: Chalo mele! | चलो मेले!\n"
                     "OBJ: bail_gaadi go right\n")
        self.assertEqual(w, [])
        v.frame(v.duration * 0.5)
        v, w = video("HOOK: x\nMYSTERY: off\nCAST: K = kisan\nSCENE: khet\nK -> ride tractor enter left to center\n"
                     "K: Naya tractor! | नया ट्रैक्टर!\n")
        self.assertEqual(w, [])
        v.frame(v.duration * 0.6)


class Actions(unittest.TestCase):
    def test_the_village_actions_bring_their_things(self):
        for act, piece in (("hookah", "hookah"), ("handpump", "handpump"), ("doodh_nikalna", "bucket")):
            v, w = video("HOOK: x\nMYSTERY: off\nCAST: T = tau\nSCENE: chaupal\nT -> %s\nT: Haan. | हाँ।\n" % act)
            self.assertEqual(w, [], act)
            plan = v.parts[-1].plan
            self.assertTrue([o for o in plan.sets if o["type"] == piece and o.get("auto")], act)
        for act in ("ghunghat", "lathi_tek"):
            self.assertIn(act, actions.VILLAGE_ACTIONS)
            self.assertIn(act, actions.ACTIONS)

    def test_the_lathi_beats_the_looks_stick(self):
        v, _ = video("HOOK: x\nMYSTERY: off\nCAST: T = tau\nSCENE: chaupal\nT -> lathi_tek\nT: Haan. | हाँ।\n")
        p = v.parts[-1]
        t = next(e["t"] for e in p.plan.chars["T"].events if e.get("action") == "lathi_tek") + 0.6
        self.assertEqual(p._prep(p.plan.chars["T"], t, {})["pose"].get("prop"), "lathi")


class Prompt(unittest.TestCase):
    def test_the_gaon_module(self):
        with open(os.path.join(ROOT, "SCRIPT_PROMPT.md"), encoding="utf-8") as f:
            text = f.read()
        core, full = director.prompt_text(text, keep=()), director.prompt_text(text)
        self.assertNotIn("Village places", core)          # only when the idea is about a village
        self.assertIn("Village places", full)
        self.assertIn("Village places", director.prompt_text(text, keep=("gaon",)))


if __name__ == "__main__":
    unittest.main()

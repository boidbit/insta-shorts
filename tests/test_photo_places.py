"""Photo places (assets/backgrounds/<name>.jpg + <name>.json): Paglet's clinic and the podcast studio. The people
sit on the seats painted in the photo, at the photo's scale, the desk stands in front of the doctor; the
podcaster kirdaar and the headphones. python -m unittest"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import script                                 # noqa: E402
from studio.render import Sequence                        # noqa: E402


def part(text):
    sc, w = script.parse_script(text)
    return Sequence(sc, 1080, False, None, None).parts[0], w, sc


class DrawnPlaces(unittest.TestCase):
    """clinic and podcast drawn in the studio's own style (2D and 2.5D), with the same spots."""

    def test_the_clinic(self):
        p, w, sc = part("HOOK: x\nSCENE: clinic\nMareez (rona): Hichki band nahi ho rahi.\nPaglet (pagal): Injection lagega!\n")
        self.assertEqual(sc["scenes"][0]["background"], {"type": "clinic"})
        doc, pat = p.plan.chars["Paglet"], p.plan.chars["Mareez"]
        desk = next(o for o in p.plan.sets if o.get("type") == "desk")
        self.assertLess(doc.y, desk["y"])                           # behind the desk (it stands in front of him)
        self.assertGreater(pat.y, desk["y"])
        chairs = {o["id"]: o for o in p.plan.sets if o.get("type") == "chair"}
        self.assertTrue(chairs["seat_paglet"]["hidden"])            # his chair is behind the desk
        self.assertFalse(chairs["seat_mareez"]["hidden"])           # the patient's chair is drawn
        for c in (doc, pat):
            self.assertTrue(c.state_at(3.0).get("on"))

    def test_the_podcast(self):
        p, w, sc = part("HOOK: x\nSCENE: podcast\nGappu (khush): Toh bataiye... aapka struggle kya tha?\n"
                        "Daddu (soch): Tera podcast sunna, chhore.\n")
        g, d = p.plan.chars["Gappu"], p.plan.chars["Daddu"]
        self.assertEqual((g.x, d.x), (170.0, 910.0))                # the yellow armchair, the teal one
        self.assertTrue(g.state_at(2.0).get("on") and d.state_at(2.0).get("on"))

    def test_both_in_2_5d(self):
        from studio import styles
        from studio.style25d.scenery import PRESETS as SETS
        for place in ("clinic", "podcast"):
            self.assertEqual(styles.PLACES_25D[place], place + "_25d")
            self.assertIn(place + "_25d", SETS)
            layered = SETS[place + "_25d"](0.1)
            self.assertGreaterEqual(len(layered.back), 2, place)

    def test_paglet_and_gappu_live_there(self):
        self.assertEqual(script.load_kirdaar("paglet")["place"], "clinic")
        self.assertEqual(script.load_kirdaar("gappu")["place"], "podcast")


class PhotoPlaces(unittest.TestCase):
    def test_the_words_find_the_photos(self):
        for word, stem in (("clinic_photo", "paglet_clinic"), ("dawakhana_photo", "paglet_clinic"),
                           ("podcast_photo", "podcast_studio"), ("studio_photo", "podcast_studio")):
            bg, warn = script.resolve_background(word)
            self.assertIsNone(warn, word)
            self.assertEqual(bg["type"], "image")
            self.assertIn(stem, bg["path"])
        places = script.vocab()["places"]
        for w in ("clinic", "podcast", "clinic_photo", "podcast_photo"):
            self.assertIn(w, places)

    def test_the_clinic_seats_the_doctor_behind_the_desk(self):
        p, w, sc = part("HOOK: x\nSCENE: clinic_photo\nMareez (rona): Hichki band nahi ho rahi.\n"
                        "Paglet (pagal): Injection lagega!\n")
        doc, pat = p.plan.chars["Paglet"], p.plan.chars["Mareez"]
        self.assertEqual((doc.x, doc.y), (850.0, 985.0))           # the spot meant for a doctor, whoever speaks first
        self.assertEqual((pat.x, pat.y), (232.0, 1258.0))
        for c in (doc, pat):
            self.assertTrue(c.state_at(3.0).get("on"))              # on their seat while they talk / cry
        self.assertEqual(sc["scenes"][0]["meta"]["people_scale"], 1.0)
        fronts = [f for f in p.bg.fg if f[0] == 1199.0]
        self.assertEqual(len(fronts), 1)                            # the desk, cut out of the photo
        self.assertGreater(fronts[0][0], doc.y)                     # in front of the doctor
        self.assertLess(fronts[0][0], pat.y)                        # behind the patient
        self.assertFalse(any(not o.get("hidden") for o in p.plan.sets if o.get("type") == "chair"))   # no drawn chair

    def test_the_podcast_seats_host_and_guest(self):
        p, w, _ = part("HOOK: x\nSCENE: podcast_photo\nGappu (khush): Toh bataiye... aapka struggle kya tha?\n"
                       "Daddu (soch): Tera podcast sunna, chhore.\n")
        self.assertFalse([x for x in w if "CAST" in x or "samajh" in x])
        g, d = p.plan.chars["Gappu"], p.plan.chars["Daddu"]
        self.assertLess(g.x, 540)                                    # the host's chair (left)
        self.assertGreater(d.x, 540)                                 # the guest's
        self.assertEqual(g.spec["look"], "podcaster")
        self.assertIn("headphones", g.spec.get("accessories") or ["headphones"])
        self.assertEqual(g.spec["voice"]["gemini"], "Algieba")

    def test_the_film_camera_keeps_them_seated(self):
        p, _, _ = part("HOOK: x\nSCENE: podcast\nGappu (khush): Toh bataiye Daddu ji, aapka struggle kya tha?\n"
                       "Daddu (soch): Roj subah tera podcast sunna, chhore.\nGappu (hairan): Wow, ye clip viral hogi!\n"
                       "Daddu (chalak): Tere bara views me se gyarah toh main hi hoon.\n")
        kinds = [s["kind"] for s in p.plan.counter_shots]
        self.assertIn("ots", kinds)                                  # seated is not "moving": the film shots come

    def test_headphones(self):
        from studio.characters import ACCESSORIES, ACCESSORY_WORDS
        self.assertIn("headphones", ACCESSORIES)
        self.assertEqual(ACCESSORY_WORDS["headset"], "headphones")
        spec = script.cast_spec("boy headset".split(), 0)
        self.assertIn("headphones", spec["accessories"])


if __name__ == "__main__":
    unittest.main()

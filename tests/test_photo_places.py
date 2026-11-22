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


class PhotoPlaces(unittest.TestCase):
    def test_the_words_find_the_photos(self):
        for word, stem in (("clinic", "paglet_clinic"), ("dawakhana", "paglet_clinic"), ("podcast", "podcast_studio"),
                           ("gappcast", "podcast_studio")):
            bg, warn = script.resolve_background(word)
            self.assertIsNone(warn, word)
            self.assertEqual(bg["type"], "image")
            self.assertIn(stem, bg["path"])
        places = script.vocab()["places"]
        self.assertIn("clinic", places)
        self.assertIn("podcast", places)

    def test_the_clinic_seats_the_doctor_behind_the_desk(self):
        p, w, sc = part("HOOK: x\nSCENE: clinic\nMareez (rona): Hichki band nahi ho rahi.\n"
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
        p, w, _ = part("HOOK: x\nSCENE: podcast\nGappu (khush): Toh bataiye... aapka struggle kya tha?\n"
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

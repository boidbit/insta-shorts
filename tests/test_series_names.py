"""Series and kirdaar by their people's names (the short prompt's talk: "Sultan (akad): ..."), the kirdaar files,
the dog's three angles, the new looks, the short prompt file and the page's pickers.
python -m unittest discover -s tests"""
import json
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import script                                  # noqa: E402
from studio.animals import build_animal                    # noqa: E402
from studio.script import parse_script                     # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")


def page():
    with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as f:
        return f.read()


class SeriesNames(unittest.TestCase):
    def test_names_work_like_letters_and_the_series_line_can_be_anywhere(self):
        t = ("HOOK: x\nCAST: Papa = boy, Mummy = aunty\nPapa (gussa): Bill dekha? | बिल देखा?\n"
             "Mummy (smug): Haan. | हाँ।\nPapa -> facepalm\nSERIES: sharma_parivar 2\n")
        sc, w = parse_script(t)
        self.assertEqual(w, [])
        self.assertEqual(sorted(sc["characters"]), ["M", "P"])           # no extra "Papa" / "Mummy" people
        self.assertEqual(sc["scenes"][0]["background"]["type"], "living_room")   # the series' own place, from the start

    def test_the_series_i_made_without_asking_are_gone(self):
        for sid in ("sheru_mohalla", "gaon_ke_tau", "pappu_class"):
            self.assertIsNone(script.load_series(sid))

    def test_feeling_words_of_the_short_prompt_all_work(self):
        with open(os.path.join(ROOT, "SHORT_PROMPT.md"), encoding="utf-8") as f:
            text = f.read()
        words = re.search(r"Feeling sirf ek shabd: (.*?)\.\n", text).group(1).split(", ")
        self.assertIn("akad", words)
        for w_ in words:
            sc, w = parse_script("HOOK: x\nCAST: A = uncle\nSCENE: room\nA (%s): Haan. | हाँ।\n" % w_)
            self.assertEqual(w, [], w_)


class Kirdaar(unittest.TestCase):
    def test_each_alone_by_any_of_its_names(self):
        for kid, said, kind, look in (("sultan", "Sultan Bhai", "dog", None), ("paglet", "Doctor Paglet", None, "pagla_doctor"),
                                      ("daddu", "Dada Daddu", None, "dada")):
            d = script.load_kirdaar(kid)
            self.assertTrue(d["line"] and d["aadat"] and d["hashtag"], kid)
            sc, w = parse_script("HOOK: x\nKIRDAAR: %s\n%s (gussa): Haan. | हाँ।\n%s -> saamne\n" % (said, said, said))
            self.assertEqual(w, [], kid)
            self.assertEqual(list(sc["characters"]), [d["name"]], kid)    # only them, nobody else
            spec = sc["characters"][d["name"]]
            self.assertEqual(spec.get("kind"), kind, kid)
            if look:
                self.assertEqual(spec["look"], look, kid)
            self.assertEqual(sc["scenes"][0]["background"]["type"], d["place"], kid)
            self.assertIn(d["hashtag"], sc["post"]["hashtags"])

    def test_the_same_face_every_episode(self):
        one = parse_script("HOOK: a\nKIRDAAR: Paglet\nPaglet: Haan. | हाँ।\n")[0]["characters"]["Paglet"]
        two = parse_script("HOOK: b\nSCENE: gully\nKIRDAAR: Paglet 4\nCAST: A = uncle\nA: Na. | ना।\n"
                           "Doctor Paglet (pagal): Injection! | इंजेक्शन!\n")[0]["characters"]["Paglet"]
        for k in ("face", "eyes", "nose", "brows", "look", "hair"):
            self.assertEqual(one.get(k), two.get(k), k)

    def test_a_crossover(self):
        sc, w = parse_script("HOOK: x\nKIRDAAR: Sultan, Paglet part 2\nSultan (akad): Abey! | अबे!\n"
                             "Paglet (pagal): Injection lagega! | इंजेक्शन लगेगा!\n")
        self.assertEqual(w, [])
        self.assertEqual(sorted(sc["characters"]), ["Paglet", "Sultan"])
        self.assertEqual(sc["series"]["label"], "Sultan Bhai × Doctor Paglet • Part 2")
        self.assertEqual(sc["post"]["hashtags"][:2], ["#sultanbhai", "#doctorpaglet"])

    def test_swag_and_pagla(self):
        sultan = script.cast_spec(script.load_kirdaar("sultan")["words"].split(), 0)
        self.assertEqual(set(sultan["accessories"]) & {"sunglasses", "chain", "cap"}, {"sunglasses", "chain", "cap"})
        daddu = script.cast_spec(script.load_kirdaar("daddu")["words"].split(), 0)
        self.assertEqual(daddu["prop"], "lathi")
        from studio.characters import LOOKS
        pg = LOOKS["pagla_doctor"]
        self.assertEqual((pg["hair"], pg["prop"], pg["expression"]), ("wild", "injection", "pagla"))
        self.assertIn("tedha_chashma", pg["accessories"])

    def test_own_voice_and_boli_every_episode(self):
        voices = {}
        for kid in ("sultan", "paglet", "daddu"):
            d = script.load_kirdaar(kid)
            self.assertTrue(d["boli"], kid)
            a = d["awaaz"]
            self.assertTrue(a["gemini"] and a["andaaz"], kid)
            self.assertGreater(int(a["rate"].strip("+%")), 0, kid)            # all of them talk fast
            voices[kid] = a["gemini"]
            for order in ("HOOK: a\nKIRDAAR: %s\nCAST: A = uncle\nSCENE: room\nA: Haan. | हाँ।\n%s: Na. | ना।\n",
                          "HOOK: b\nKIRDAAR: %s\nSCENE: room\n%s: Na. | ना।\n"):
                sc, w = parse_script(order % (d["name"], d["name"]))
                v = sc["characters"][d["name"]]["voice"]
                self.assertEqual((v["gemini"], v["pitch"], v["rate"]), (a["gemini"], a["pitch"], a["rate"]), kid)
        self.assertEqual(len(set(voices.values())), 3)                          # three different voices

    def test_the_manner_goes_to_gemini(self):
        from studio import gemini_tts
        p = gemini_tts.build_payload([{"voice": "Charon", "text": "Apun Sultan!"}, {"voice": "Kore", "text": "Hat!"}],
                                     gemini_tts.DEFAULT_STYLE, {"Charon": "a cocky tapori don"})
        text = p["contents"][0]["parts"][0]["text"]
        self.assertIn("Speaker1 sounds like a cocky tapori don.", text)
        one = gemini_tts.build_payload([{"voice": "Charon", "text": "Apun!"}], "", {"Charon": "a cocky tapori don"})
        self.assertIn("The speaker sounds like a cocky tapori don.", one["contents"][0]["parts"][0]["text"])

    def test_the_prompts_carry_the_boli(self):
        with open(os.path.join(ROOT, "SHORT_PROMPT.md"), encoding="utf-8") as f:
            short = f.read()
        from studio import director
        with open(os.path.join(ROOT, "SCRIPT_PROMPT.md"), encoding="utf-8") as f:
            module = director.prompt_text(f.read(), keep=("series",))
        for text in (short, module):
            for w in ("apun", "Haryanvi", "tension ka virus"):
                self.assertIn(w, text)

    def test_unknown_kirdaar_says_so(self):
        sc, w = parse_script("HOOK: x\nKIRDAAR: Gabbar\nCAST: A = uncle\nSCENE: room\nA: Haan. | हाँ।\n")
        self.assertTrue(any("Gabbar" in x for x in w))


class NoCastNeeded(unittest.TestCase):
    """A script with no CAST and no KIRDAAR line (as a chat AI writes it): the names alone decide who is who."""

    def test_kirdaar_and_animals_by_their_names(self):
        sc, w = parse_script("HOOK: x\nSCENE: gaon\nSultan -> enter left\nSultan (swag): Ae bhains! | ऐ भैंस!\n"
                             "Bhains (akad): Hat ja! | हट जा!\nKutta: Bhau! | भौ!\nMummy: Chup! | चुप!\n")
        self.assertEqual(w, [])
        ch = sc["characters"]
        self.assertEqual(ch["Sultan"]["kind"], "dog")
        self.assertIn("sunglasses", ch["Sultan"]["accessories"])
        self.assertEqual(ch["Bhains"]["kind"], "buffalo")
        self.assertEqual(ch["Bhains"]["voice"]["name"], "hi-IN-SwaraNeural")     # the bhains is a she
        self.assertEqual(ch["Kutta"]["kind"], "dog")
        self.assertEqual(ch["Mummy"]["look"], "aunty")
        self.assertEqual(sc["series"]["title"], "Sultan Bhai")
        self.assertEqual(sc["scenes"][0]["background"]["type"], "gaon")          # the script's place stays

    def test_the_bhains_stands_clear_of_the_dog_that_walks_in(self):
        from studio.render import Sequence
        from studio import animals
        sc, w = parse_script("HOOK: x\nSCENE: gaon\nSultan -> enter left\nSultan (swag): Ae bhains! | ऐ भैंस!\n"
                             "Bhains (akad): Hat ja! | हट जा!\n")
        r = Sequence(sc, 1080, False, None, None).parts[0]
        dog, bh = r.plan.chars["Sultan"], r.plan.chars["Bhains"]
        t = r.plan.duration - 0.5
        nose_dog = dog.draw_pos(t)[0] + animals.extent("dog", dog.scale)[0]
        nose_bh = bh.draw_pos(t)[0] - animals.extent("buffalo", bh.scale)[0]
        self.assertGreater(nose_bh - nose_dog, 60)

    def test_cast_still_wins(self):
        sc, w = parse_script("HOOK: x\nCAST: Sultan = boy, Bhains = uncle\nSCENE: room\nSultan: Haan. | हाँ।\n"
                             "Bhains: Na. | ना।\n")
        self.assertEqual(w, [])
        self.assertIsNone(sc["characters"]["Sultan"].get("kind"))
        self.assertIsNone(sc["characters"]["Bhains"].get("kind"))
        self.assertNotIn("series", sc)


class DogAngles(unittest.TestCase):
    def spot(self, view, acc=()):
        spec = {"kind": "dog", "pose_view": view, "accessories": list(acc)}
        ops, an = build_animal(spec, "bark", 0.3, 1.0, 500, 1500, 0.82, 1, False, False, 0.7, "neutral")
        return ops, an

    def test_three_angles_draw_differently(self):
        side, a_side = self.spot("side")
        turn, a_turn = self.spot("turn")
        front, a_front = self.spot("front")
        xs = lambda ops: [p[0] for op in ops for p in op["pts"]]
        self.assertGreater(max(xs(side)) - min(xs(side)), 2 * (max(xs(front)) - min(xs(front))))   # front: narrow
        self.assertAlmostEqual(a_front["head_center"][0], 500, delta=5)                           # head over the body
        self.assertGreater(a_side["head_center"][0], 600)                                          # profile: head ahead
        self.assertNotEqual(len(side), len(turn))

    def test_swag_on_every_angle(self):
        for view in ("side", "turn", "front"):
            plain, _ = self.spot(view)
            swag, _ = self.spot(view, ("sunglasses", "chain", "cap"))
            self.assertGreater(len(swag), len(plain) + 5, view)

    def test_renderer_picks_the_angle(self):
        from studio.render import Renderer
        self.assertTrue(hasattr(Renderer, "_dog_view"))


class Page(unittest.TestCase):
    def test_animals_get_animal_actions(self):
        s = page()
        for needle in ("function suggestAnimalActs", "const lineAnimal", "lineAnimal(it))"):
            self.assertIn(needle, s)
        vocab = json.loads(re.search(r'<script type="application/json" id="vocab">(.*?)</script>', s, re.S).group(1))
        self.assertEqual({k["id"]: k["animal"] for k in vocab["kirdaar"]}, {"sultan": "dog", "paglet": None, "daddu": None})

    def test_the_short_prompt(self):
        with open(os.path.join(ROOT, "SHORT_PROMPT.md"), encoding="utf-8") as f:
            text = f.read()
        self.assertIn("| wahi line Devanagari me", text)
        self.assertIn("Sultan, Paglet, Daddu", text)
        self.assertTrue(text.rstrip().endswith("Mera idea:"))
        self.assertLess(len(text), 3000)
        self.assertIn('id="copyShort"', page())
        self.assertIn('fetch("SHORT_PROMPT.md"', page())

    def test_the_lists_and_the_pickers(self):
        s = page()
        vocab = json.loads(re.search(r'<script type="application/json" id="vocab">(.*?)</script>', s, re.S).group(1))
        self.assertEqual(sorted(x["id"] for x in vocab["series"]), ["office_gang", "sharma_parivar"])
        self.assertEqual(sorted(x["id"] for x in vocab["kirdaar"]), ["daddu", "paglet", "sultan"])
        for needle in ("function seriesBox", "function kirdaarBox", "function kirdaarPick", "function extrasPicker",
                       "🎒 Haath me", "🔊 Awaaz", "✨ Effect"):
            self.assertIn(needle, s)

    def test_the_prompt_module(self):
        from studio import director
        with open(os.path.join(ROOT, "SCRIPT_PROMPT.md"), encoding="utf-8") as f:
            text = f.read()
        self.assertNotIn("KIRDAAR:", director.prompt_text(text, keep=()))
        self.assertIn("KIRDAAR: Sultan", director.prompt_text(text, keep=("series",)))
        self.assertNotIn("sheru_mohalla", text)


if __name__ == "__main__":
    unittest.main()

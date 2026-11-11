"""New looks (neta, chor, nurse...), places (jail, gaon, school_ground), set pieces, props and sounds.
python -m unittest discover -s tests"""
import os
import sys
import unittest
import wave
from unittest import mock

import numpy as np

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)

from studio import audio, characters, effects, script, sets as S                # noqa: E402
from studio.characters import LOOKS, build_character, resolve_spec               # noqa: E402
from studio.render import make_video                                             # noqa: E402

NEW_LOOKS = ("neta", "chor", "nurse", "saas", "bahu", "principal", "sabziwala", "nai")
NEW_PLACES = ("jail", "gaon", "school_ground")
NEW_SETS = ("khaat", "matka", "chulha", "blackboard", "drip", "wheelchair", "cooler", "washing_machine", "mirror")
NEW_PROPS = ("cooker", "thali", "lota", "tiffin", "mithai", "report_card", "injection", "stethoscope")
NEW_SFX = ("cooker", "siren", "train_horn", "dhol", "shehnai", "baby_cry", "glass_break")


def cast(word):
    sc, w = script.parse_script("HOOK: x\nCAST: N = %s\nSCENE: street\nN (smile): Vote do | वोट दो\n" % word)
    return sc["characters"]["N"], w


class LookTests(unittest.TestCase):
    def test_neta_wears_kurta_jacket_and_a_gandhi_topi(self):
        spec, w = cast("neta")
        self.assertEqual(w, [])                                     # it used to be an unknown word -> a boy
        o = resolve_spec(spec)
        self.assertEqual((o["outfit"], o["color"]), ("kurta_jacket", "white"))
        self.assertIn("topi", o["accessories"])
        self.assertNotIn("cap", o["accessories"])                   # not a sports cap
        for word in ("netaji", "mantri", "sarpanch"):
            self.assertEqual(cast(word)[0]["look"], "neta")

    def test_every_new_look_draws_and_has_a_picture(self):
        for look in NEW_LOOKS:
            self.assertIn(look, LOOKS)
            self.assertIn(look, script.vocab()["looks"])
            self.assertTrue(os.path.isfile(os.path.join(ROOT, "assets", "looks", look + ".png")), look)
            for facing in ("front", "left"):
                ops, an = build_character({"look": look, "facing": facing}, {}, "smile", 0.0, 0.0, 540, 1700)
                self.assertGreater(len(ops), 30, look)
            ops, _an = build_character({"look": look, "view": "back"}, {}, "smile", 0.0, 0.0, 540, 1700)
            self.assertGreater(len(ops), 10, look)
        for look in ("nurse", "saas", "bahu"):
            self.assertIn(look, script.FEMALE_LOOKS)

    def test_new_extras_are_words_of_the_script(self):
        spec, w = cast("boy kurta_jacket topi")
        self.assertEqual(w, [])
        self.assertEqual(spec["outfit"], "kurta_jacket")
        spec, w = cast("boy stripes beanie")
        self.assertEqual((w, spec["outfit"]), ([], "stripes"))
        self.assertIn("nurse_cap", characters.ACCESSORIES)

    def test_bubble_sits_above_a_topi(self):
        _o, a = build_character({"look": "uncle"}, {}, "smile", 0.0, 0.0, 540, 1700)
        _o, b = build_character({"look": "uncle", "accessories": ["topi"]}, {}, "smile", 0.0, 0.0, 540, 1700)
        self.assertLess(b["head_top"][1], a["head_top"][1])


class PlaceTests(unittest.TestCase):
    def test_new_places_render_in_both_styles(self):
        from studio.styles import has_depth
        for place in NEW_PLACES:
            self.assertIn(place, script.vocab()["places"])
            self.assertTrue(has_depth(place), place)
            sc, w = script.parse_script("HOOK: x\nCAST: A = chor\nSCENE: %s\nA (smile): Haan | हाँ\n" % place)
            self.assertEqual(w, [], place)
            for style in ("2d", "2.5d"):
                im = make_video(sc, 90, use_tts=False, style=style).frame(0.5)
                self.assertEqual(im.size[0], 90)
                self.assertGreater(len(np.unique(np.asarray(im.resize((20, 36)).convert("RGB")).reshape(-1, 3), axis=0)), 40,
                                   (place, style))   # not blank


class SetTests(unittest.TestCase):
    def test_pieces_draw_and_seat(self):
        objs = [{"type": t, "x": 540, "y": 1700, "state": "on"} for t in NEW_SETS]
        sets = S.Sets(objs, [], 0.2, 216, 384)
        for oid, ob in sets.objs.items():
            im, _pos = sets._image(ob, "on", 1.0)
            self.assertGreater(im.getbbox()[2], 4, ob["type"])
        self.assertEqual(S.SPEC["khaat"][4], 205)                   # you can sit / lie on it
        self.assertIsNotNone(S.SPEC["wheelchair"][4])
        for t in NEW_SETS:
            self.assertIn(t, script.SET_TYPES)

    def test_blackboard_takes_writing_in_hindi(self):
        sc, w = script.parse_script("HOOK: x\nCAST: A = principal\nSCENE: school_ground\nOBJ: blackboard center चमगादड़\n"
                                    "A (smile): Padho | पढ़ो\n")
        self.assertEqual(w, [])
        self.assertEqual(sc["scenes"][0]["sets"][0]["text"], "चमगादड़")
        kinds = []
        real = effects.font
        board = {"id": "b", "type": "blackboard", "x": 540, "y": 1700, "text": "चमगादड़"}
        with mock.patch.object(effects, "font", lambda size, kind="main": kinds.append(kind) or real(size, kind)):
            S.Sets([board], [], 0.2, 216, 384)._image(board, "idle", 0.0)
        self.assertIn("deva", kinds)                                # Hindi letters get the Devanagari font

    def test_lie_and_get_up_from_a_khaat(self):
        sc, w = script.parse_script("HOOK: x\nCAST: A = dada\nSCENE: gaon\nOBJ: khaat center\nA -> lie_down khaat\n"
                                    "A (smile): Aaram | आराम\nA -> get_up\nA: Chalo | चलो\n")
        self.assertEqual(w, [])
        with mock.patch.dict(os.environ, {"STUDIO_CAMERA": "cine"}):
            v = make_video(sc, 90, use_tts=False)
        a = v.parts[0].plan.chars["A"] if hasattr(v, "parts") else v.plan.chars["A"]
        t_up = next(e["t"] for e in a.events if e.get("action") == "get_up")
        self.assertTrue(170 <= a.pos_at(t_up + 1.0)[0] <= 910)


class PropTests(unittest.TestCase):
    def test_props_draw(self):
        base, _ = build_character({"look": "boy"}, {}, "smile", 0.0, 0.0, 540, 1700)
        for prop in NEW_PROPS:
            self.assertIn(prop, script.PROPS)
            ops, _an = build_character({"look": "boy"}, {}, "smile", 0.0, 0.0, 540, 1700, prop=prop)
            self.assertGreater(len(ops), len(base), prop)
            _sc, w = script.parse_script("HOOK: x\nCAST: A = boy\nSCENE: room\nA (smile, %s): Lo | लो\n" % prop)
            self.assertFalse([x for x in w if "samajh" in x], (prop, w))


class SoundTests(unittest.TestCase):
    def test_sounds_are_made_and_not_clipped(self):
        for name in NEW_SFX:
            self.assertIn(name, script.SFX)
            p = audio.sfx_path(name)
            with wave.open(p) as w_:
                x = np.frombuffer(w_.readframes(w_.getnframes()), dtype="<i2").astype(float) / 32767
            self.assertGreater(x.size / audio.SR, 0.8, name)
            self.assertLess(np.abs(x).max(), 0.99, name)
            self.assertGreater(np.sqrt((x ** 2).mean()), 0.02, name)


if __name__ == "__main__":
    unittest.main()

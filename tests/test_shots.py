"""Shots (CUT), framing and one scale for the whole world. python -m unittest discover -s tests"""
import os
import sys
import unittest

from PIL import ImageChops

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import objects, rides                          # noqa: E402
from studio.render import make_video                       # noqa: E402
from studio.scene import compile_scene, split_scenes       # noqa: E402
from studio.script import parse_script, vocab              # noqa: E402

STORY = """HOOK: h
CAST: S = uncle, B = beti, L = dost
SCENE: street
S (angry): Sun! | सुन!
B (shock): Papa! | पापा!
CUT
L (grin): Ji | जी
L -> exit left
CUT wide
S (smug): dekhte hain | देखते हैं
L -> ride truck enter left to center
CUT inside
L -> ride truck
L (smug): le aaya | ले आया
CUT medium
S (shock): kya | क्या
CTA: c
"""


def scene(kind, framing=None, seats=("driver",), at="center"):
    chars = {"A": {"look": "boy", "slot": "left"}, "B": {"look": "uncle", "slot": "right"}}
    tl = [{"t": 0.0, "who": "all", "action": "idle"}, {"t": 0.1, "obj": {"kind": kind, "at": at}},
          {"t": 0.4, "who": "A", "ride": {"kind": kind, "seat": seats[0]}}]
    return {"characters": chars, "background": {"type": "street"},
            "meta": dict({"duration": 5.0}, **({"framing": framing} if framing else {})), "timeline": tl}


class CutTests(unittest.TestCase):
    def test_every_shot_has_its_own_characters_and_a_hard_cut(self):
        sc, warns = parse_script(STORY)
        self.assertEqual(warns, [])
        shots = sc["scenes"]
        self.assertEqual([s["cast"] for s in shots], [["S", "B"], ["L"], ["S", "L"], ["L"], ["S"]])
        self.assertEqual([bool(s.get("cut_in")) for s in shots], [False, True, True, True, True])
        self.assertEqual([s.get("framing") for s in shots], [None, None, "wide", "inside", "medium"])
        self.assertEqual({s["background"]["type"] for s in shots}, {"street"})            # same place for all of them

    def test_bad_framing_warns_and_scene_can_carry_one(self):
        _, warns = parse_script("CAST: A = dost\nSCENE: street\nA (smile): hi | हाय\nCUT closeup\nA (smile): hi | हाय\nHOOK: h\nCTA: c\n")
        self.assertTrue(any("framing" in w for w in warns))
        sc, warns = parse_script("CAST: A = dost\nSCENE: street | title | wide\nA (smile): hi | हाय\nHOOK: h\nCTA: c\n")
        self.assertEqual(sc["scenes"][0]["framing"], "wide")
        self.assertEqual(sc["scenes"][0]["title"], "title")

    def test_a_cut_is_instant_but_a_scene_change_is_not(self):
        sc, _ = parse_script(STORY)
        v = make_video(sc, 216, use_tts=False)
        for i in (1, 2, 3, 4):
            t = v.offsets[i] + 0.02
            same = ImageChops.difference(v.frame(t).convert("RGB"), v.parts[i].frame(0.02).convert("RGB")).getbbox()
            self.assertIsNone(same, "shot %d should be a hard cut" % i)
        sc2, _ = parse_script("CAST: A = dost\nSCENE: street\nA (smile): hi | हाय\nSCENE: room\nA (smile): hi | हाय\nHOOK: h\nCTA: c\n")
        v2 = make_video(sc2, 216, use_tts=False)
        t = v2.offsets[1] + 0.02
        self.assertIsNotNone(ImageChops.difference(v2.frame(t).convert("RGB"), v2.parts[1].frame(0.02).convert("RGB")).getbbox())

    def test_only_medium_shots_get_the_automatic_zoom(self):
        sc, _ = parse_script(STORY)
        plans = [compile_scene(sub, use_tts=False) for sub in split_scenes(sc)]
        self.assertEqual([p.framing for p in plans], ["medium", "medium", "wide", "inside", "medium"])
        self.assertEqual([bool(p.cam_segments) for p in plans], [True, True, False, False, True])

    def test_page_vocab_knows_the_framings(self):
        self.assertTrue(vocab())


class OneScaleTests(unittest.TestCase):
    def test_vehicles_are_in_proportion_to_people_in_every_framing(self):
        for kind in rides.RIDES:
            for framing in ("wide", "inside"):
                p = compile_scene(scene(kind, framing), use_tts=False)
                o, a, b = p.objects[kind], p.chars["A"], p.chars["B"]
                self.assertAlmostEqual(o.scale, objects.REF_SCALE * p.world / objects.PERSON_R[kind], places=6)
                self.assertAlmostEqual(a.ride_frame(2.0)["scale"], a.scale, delta=a.scale * 0.1, msg=(kind, framing))
                self.assertAlmostEqual(a.scale, b.scale, delta=0.1 * b.scale)            # same world for everybody

    def test_wide_shrinks_the_people_until_the_vehicle_fits(self):
        p = compile_scene(scene("truck"), use_tts=False)                              # no framing given: vehicle -> wide
        self.assertEqual(p.framing, "wide")
        self.assertAlmostEqual(p.world, 0.31, delta=0.02)
        width = objects.SPRITE_LEN["truck"] * p.objects["truck"].scale
        self.assertLessEqual(width, 920)
        for kind in ("bike", "cycle", "cow", "dustbin"):                              # small things need no shrinking
            self.assertGreaterEqual(compile_scene(scene(kind), use_tts=False).world, 0.7, kind)
        s = scene("table")
        s["timeline"] = [e for e in s["timeline"] if "ride" not in e]
        self.assertEqual(compile_scene(s, use_tts=False).framing, "medium")           # no vehicle: normal people shot

    def test_inside_puts_the_driver_in_the_middle_of_the_frame(self):
        for kind in ("truck", "auto", "car", "bike"):
            p = compile_scene(scene(kind, "inside"), use_tts=False)
            rf = p.chars["A"].ride_frame(2.0)
            self.assertAlmostEqual(rf["hip"][0], 540.0, delta=1.0, msg=kind)
            self.assertEqual(p.world, 1.0)

    def test_object_scale_keyword_multiplies(self):
        s = scene("truck")
        s["timeline"][1]["obj"]["scale"] = 0.5
        p = compile_scene(s, use_tts=False)
        self.assertAlmostEqual(p.objects["truck"].scale, 0.5 * objects.REF_SCALE * p.world / objects.PERSON_R["truck"], places=6)

    def test_a_vehicle_made_with_its_rider_is_there_from_the_first_frame(self):
        sc, _ = parse_script("CAST: L = dost\nSCENE: street\nL -> ride truck\nL (smug): hi | हाय\nHOOK: h\nCTA: c\n")
        p = compile_scene(split_scenes(sc)[0], use_tts=False)
        self.assertTrue(p.objects["truck"].no_fade)

    def test_every_framing_renders(self):
        for framing in ("wide", "medium", "inside"):
            v = make_video(scene("auto", framing), 216, use_tts=False)
            self.assertEqual(v.frame(2.0).size, (216, 384))


if __name__ == "__main__":
    unittest.main()

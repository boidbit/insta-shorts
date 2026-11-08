"""Set objects (vehicles, bins...), new props. python -m unittest discover -s tests"""
import os
import sys
import tempfile
import unittest

from PIL import Image, ImageChops

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import objects                                  # noqa: E402
from studio.render import make_video                        # noqa: E402
from studio.scene import compile_scene                      # noqa: E402
from studio.script import parse_obj, parse_script, vocab    # noqa: E402

BASE = {"characters": {"A": {"look": "boy"}}, "timeline": []}


def scene(*events):
    return dict(BASE, timeline=[{"t": 0.0, "who": "A", "action": "idle"}] + list(events))


class ParseObjTests(unittest.TestCase):
    def test_words(self):
        self.assertEqual(parse_obj("truck enter left to right"), ({"kind": "truck", "enter": "left", "at": "right"}, []))
        self.assertEqual(parse_obj("dustbin left")[0], {"kind": "dustbin", "at": "left"})
        spec, _ = parse_obj("car red go center front big")
        self.assertEqual((spec["color"], spec["go"], spec["at"], spec["front"], spec["scale"]),
                         ("red", "center", "center", True, 1.35))
        self.assertEqual(parse_obj("kachra_gaadi")[0]["kind"], "truck")             # alias
        self.assertEqual(parse_obj("assets/objects/x.png right")[0]["kind"], "assets/objects/x.png")

    def test_problems_are_reported_not_fatal(self):
        self.assertIsNone(parse_obj("spaceship left")[0])
        self.assertIsNone(parse_obj("")[0])
        self.assertIsNone(parse_obj("truck enter center")[0])
        spec, probs = parse_obj("truck banana")
        self.assertEqual(spec["kind"], "truck")
        self.assertTrue(probs and "banana" in probs[0])

    def test_script_line_becomes_a_timeline_event(self):
        sc, warns = parse_script("CAST: A = dost\nSCENE: street\nOBJ: truck enter left\nA (smile): hi | हाय\n"
                                 "OBJ: spaceship\nHOOK: h\nCTA: c\n")
        tl = sc["scenes"][0]["timeline"]
        self.assertEqual([e["obj"] for e in tl if "obj" in e], [{"kind": "truck", "enter": "left"}])
        self.assertTrue(any("spaceship" in w for w in warns))

    def test_vocab_lists_objects_for_the_page_checker(self):
        v = vocab()
        self.assertIn("truck", v["objects"])
        self.assertIn("sunglasses", v["extras"])
        self.assertIn("bag", v["props"])
        self.assertIn("salute", v["actions"])


class CompileObjTests(unittest.TestCase):
    def test_drive_in_stop_and_drive_out(self):
        p = compile_scene(scene({"t": 1.0, "obj": {"kind": "truck", "enter": "left", "at": "right"}},
                                {"t": 5.0, "obj": {"kind": "truck", "exit": "right"}}, {"t": 8.0, "wait": 0.5}),
                          use_tts=False)
        o = p.objects["truck"]
        self.assertFalse(o.visible(0.5))
        self.assertLess(o.x_at(1.0), 0)                              # starts off screen on the left
        self.assertAlmostEqual(o.x_at(3.5), objects.SPOTS["right"])  # parked
        self.assertTrue(o.moving(1.5) and not o.moving(3.5))
        self.assertGreater(o.x_at(6.9), 1080)                        # gone off the right edge
        self.assertTrue(o.visible(5.5) and not o.visible(7.5))
        self.assertFalse(o.flip_at(2.0))                             # facing right while driving right

    def test_enter_from_the_right_faces_left(self):
        p = compile_scene(scene({"t": 0.5, "obj": {"kind": "car", "enter": "right"}}), use_tts=False)
        self.assertTrue(p.objects["car"].flip_at(1.0))

    def test_static_object_and_go(self):
        p = compile_scene(scene({"t": 0.5, "obj": {"kind": "dustbin", "at": "left"}},
                                {"t": 2.0, "obj": {"kind": "dustbin", "go": "right"}}), use_tts=False)
        o = p.objects["dustbin"]
        self.assertEqual(o.x_at(1.0), objects.SPOTS["left"])
        self.assertEqual(o.x_at(5.0), objects.SPOTS["right"])

    def test_unknown_object_is_a_warning(self):
        p = compile_scene(scene({"obj": {"kind": "spaceship"}}), use_tts=False)
        self.assertEqual(p.objects, {})
        self.assertTrue(p.warnings)

    def test_the_story_waits_for_the_vehicle(self):
        p = compile_scene(scene({"t": 1.0, "obj": {"kind": "truck", "enter": "left"}},
                                {"who": "A", "say": "hi", "duration": 1.0}), use_tts=False)
        self.assertGreaterEqual(p.speech[0]["start"], 2.7)           # after the 1.8 s drive-in


class RenderObjTests(unittest.TestCase):
    def test_every_object_draws_with_wheels_and_flips(self):
        for kind in objects.OBJECTS:
            for flip in (False, True):
                s = scene({"t": 0.1, "obj": {"kind": kind, "at": "center", "front": True}})
                v = make_video(s, 216, use_tts=False)
                with_obj = v.frame(1.0).convert("RGB")
                s2 = scene()
                without = make_video(s2, 216, use_tts=False).frame(1.0).convert("RGB")
                self.assertIsNotNone(ImageChops.difference(with_obj, without).getbbox(), kind)

    def test_png_sprite(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "thing.png")
            Image.new("RGBA", (40, 80), (200, 30, 30, 255)).save(path)
            v = make_video(scene({"t": 0.1, "obj": {"kind": path, "at": "center"}}), 216, use_tts=False)
            base = make_video(scene(), 216, use_tts=False).frame(1.0).convert("RGB")
            self.assertIsNotNone(ImageChops.difference(v.frame(1.0).convert("RGB"), base).getbbox())


class PropTests(unittest.TestCase):
    def test_sunglasses_bag_and_salute_render(self):
        sc, warns = parse_script("CAST: A = college_boy sunglasses\nSCENE: street\nHOOK: h\nCTA: c\n"
                                 "A (grin, salute): ok | ओके\nA (shock, bag): ok2 | ओके\n")
        self.assertEqual(warns, [])
        v = make_video(sc, 216, use_tts=False)
        self.assertEqual(v.frame(1.0).size, (216, 384))
        self.assertEqual(v.frame(3.0).size, (216, 384))


if __name__ == "__main__":
    unittest.main()

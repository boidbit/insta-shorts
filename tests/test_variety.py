"""Characters, faces and camera angles look different. python -m unittest discover -s tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio.characters import LOOKS, assign_faces, build_character      # noqa: E402
from studio.script import parse_script                     # noqa: E402
from studio.scene import ANGLES, compile_scene, shot_angle, split_scenes      # noqa: E402
from studio.render import Renderer                         # noqa: E402
from studio.script import vocab                            # noqa: E402

OTS = """HOOK: h
CAST: A = college_boy, B = college_girl
SCENE: room
A (angry): Premium mera? | प्रीमियम मेरा?
CUT
B (smug): Haan | हाँ
CUT ots
A (angry): Kyun? | क्यों?
CUT ots A
B (sly): Bas | बस
CUT reverse
A (shock): Kya | क्या
CTA: c
"""


def cast_of(cast_line):
    text = "HOOK: h\nCAST: %s\nSCENE: street\n" % cast_line
    names = [p.split("=")[0].strip() for p in cast_line.split(",")]
    text += "".join("%s (happy): hi | हाय\n" % n for n in names) + "CTA: c\n"
    scene, _ = parse_script(text)
    return scene["characters"]


def look_of(spec):
    base = LOOKS.get(spec.get("look", "boy"), {})
    return spec.get("hair", base.get("hair")), spec.get("skin", base.get("skin"))


class CastVariety(unittest.TestCase):
    def test_same_look_is_not_twins(self):
        c = cast_of("A = college_boy, B = college_boy")
        self.assertNotEqual(look_of(c["A"]), look_of(c["B"]))

    def test_three_of_a_kind_all_differ(self):
        c = cast_of("A = dost, B = dost, C = dost")
        looks = [look_of(c[n]) for n in "ABC"]
        self.assertEqual(len(set(looks)), 3)

    def test_girls_get_girls_hair(self):
        c = cast_of("A = college_girl, B = college_girl")
        self.assertNotEqual(look_of(c["A"]), look_of(c["B"]))
        self.assertIn(look_of(c["B"])[0], ("ponytail", "bun", "long", "braid"))

    def test_first_character_keeps_its_look(self):
        c = cast_of("A = college_boy, B = college_boy")
        self.assertEqual(look_of(c["A"]), look_of({"look": "college_boy"}))

    def test_chosen_words_are_kept(self):
        c = cast_of("A = college_boy curly fair, B = college_boy curly fair")
        self.assertEqual(look_of(c["A"]), ("curly", "fair"))
        self.assertEqual(c["B"]["hair"], "curly")
        self.assertEqual(c["B"]["skin"], "fair")       # both chosen by the script: it is the writer's call

    def test_different_looks_untouched(self):
        c = cast_of("A = college_boy, B = uncle")
        self.assertNotIn("hair", c["B"])
        self.assertNotIn("skin", c["B"])


    def test_same_shirt_gets_another_colour(self):
        c = cast_of("A = college_boy, B = college_boy")
        base = LOOKS["college_boy"].get("color", "blue")
        self.assertEqual(c["A"].get("color", base), base)
        self.assertNotEqual(c["B"].get("color", base), base)

    def test_chosen_colour_is_kept(self):
        c = cast_of("A = college_boy red, B = college_boy red")
        self.assertEqual(c["B"]["color"], "red")


FACE_KEYS = ("face", "eyes", "nose", "brows")


class FaceVariety(unittest.TestCase):
    def test_every_character_gets_its_own_face(self):
        faces = assign_faces({n: {"look": "boy"} for n in "ABCD"})
        combos = [tuple(faces[n][k] for k in FACE_KEYS) for n in "ABCD"]
        self.assertEqual(len(set(combos)), 4)
        for a in range(4):                      # neighbours differ in every feature, not just one
            for b in range(a + 1, 4):
                self.assertGreaterEqual(sum(x != y for x, y in zip(combos[a], combos[b])), 2)

    def test_first_character_keeps_the_classic_face(self):
        f = assign_faces({"A": {}})["A"]
        self.assertEqual((f["face"], f["eyes"], f["nose"], f["brows"]), ("oval", "dot", "hook", "normal"))

    def test_hidden_narrator_does_not_take_a_face(self):
        f = assign_faces({"N": {"hidden": True}, "A": {}, "B": {}})
        self.assertNotIn("face", f["N"])
        self.assertEqual(f["A"]["face"], "oval")

    def test_script_words_choose_the_face(self):
        c = cast_of("A = uncle square_face small_eyes big_nose thick_brows")
        f = assign_faces(c)["A"]
        self.assertEqual((f["face"], f["eyes"], f["nose"], f["brows"]), ("square", "small", "big", "thick"))

    def test_face_is_the_same_in_every_scene(self):
        scene, _ = parse_script("HOOK: h\nCAST: A = boy, B = boy\nSCENE: room\nA: hi | हाय\nB: hi | हाय\n"
                                "SCENE: street\nB: bye | बाय\nCTA: c\n")
        subs = split_scenes(scene)
        self.assertEqual(subs[0]["characters"]["B"]["face"], subs[1]["characters"]["B"]["face"])
        self.assertNotEqual(subs[0]["characters"]["A"]["face"], subs[0]["characters"]["B"]["face"])

    def test_every_variant_draws(self):
        for face in ("oval", "round", "long", "square"):
            for eyes in ("dot", "big", "small"):
                for nose in ("hook", "button", "long", "big"):
                    spec = {"look": "boy", "face": face, "eyes": eyes, "nose": nose, "brows": "thick"}
                    ops, anchors = build_character(spec, {}, "neutral", 0.0, 0.0, 540, 1500)
                    self.assertTrue(ops)
                    self.assertLess(anchors["head_top"][1], anchors["mouth"][1])



class Angles(unittest.TestCase):
    def test_each_cut_gets_a_new_angle(self):
        scene, warn = parse_script(OTS)
        self.assertEqual(warn, [])
        subs = split_scenes(scene)
        angles = [shot_angle(sub, None) for sub in subs]
        self.assertEqual(angles[0], dict(zoom=1.0, x=540.0, mirror=False))      # the first shot shows the whole place
        for a, b in zip(angles, angles[1:]):
            self.assertNotEqual(a, b)

    def test_reverse_mirrors(self):
        scene, _ = parse_script(OTS)
        last = split_scenes(scene)[-1]
        self.assertTrue(last.get("reverse"))
        self.assertTrue(shot_angle(last, None)["mirror"])

    def test_wide_and_inside_show_the_whole_place(self):
        self.assertEqual(shot_angle({"angle": 2}, "wide")["zoom"], 1.0)
        self.assertEqual(shot_angle({"angle": 1, "reverse": True}, "inside"), dict(zoom=1.0, x=540.0, mirror=True))

    def test_angles_cycle_after_the_list(self):
        self.assertEqual(shot_angle({"angle": len(ANGLES)}, None), shot_angle({"angle": 1}, None))

    def test_photo_is_not_mirrored_unless_asked(self):
        bg = {"type": "image", "path": "x.png"}
        self.assertFalse(shot_angle({"angle": 1, "background": bg}, None)["mirror"])
        self.assertTrue(shot_angle({"angle": 1, "background": bg, "reverse": True}, None)["mirror"])

    def test_json_cuts_get_angles_too(self):
        scene = {"characters": {"A": {}}, "scenes": [
            {"background": {"type": "room"}, "timeline": []},
            {"background": {"type": "room"}, "cut_in": True, "timeline": []},
            {"background": {"type": "street"}, "timeline": []}]}
        subs = split_scenes(scene)
        self.assertEqual([s_.get("angle") for s_ in subs], [None, 1, None])

    def test_angled_background_is_crisp_and_differs(self):
        base = {"characters": {}, "background": {"type": "room"}, "meta": {"duration": 1.0}, "timeline": []}
        a = Renderer(dict(base), width=270, use_tts=False).frame(0.5)
        b = Renderer(dict(base, angle=1), width=270, use_tts=False).frame(0.5)
        self.assertEqual(a.size, b.size)
        self.assertNotEqual(a.tobytes(), b.tobytes())


class OverTheShoulder(unittest.TestCase):
    def setUp(self):
        self.scene, self.warn = parse_script(OTS)
        self.subs = split_scenes(self.scene)

    def test_listener_is_seen_from_behind(self):
        ots = self.subs[2]                           # CUT ots with only A speaking: B (spoke before) is the back
        self.assertEqual(ots["framing"], "ots")
        self.assertEqual(ots["characters"]["B"]["view"], "back")
        self.assertNotEqual(ots["characters"]["A"].get("view"), "back")

    def test_named_back(self):
        self.assertEqual(self.subs[3]["characters"]["A"]["view"], "back")
        self.assertNotEqual(self.subs[2]["characters"]["B"]["slot"], self.subs[3]["characters"]["A"]["slot"])

    def test_back_is_big_and_near(self):
        plan = compile_scene(self.subs[2], use_tts=False)
        back, front = plan.chars["B"], plan.chars["A"]
        self.assertGreater(back.scale, front.scale * 1.8)
        self.assertGreater(back.y, 1920)                 # feet below the frame: only head and shoulders show
        self.assertLess(abs(back.x - 540), abs(front.x - 540) + 400)
        self.assertNotEqual(back.x > 540, front.x > 540)  # opposite halves

    def test_no_one_to_show_from_behind(self):
        _, warn = parse_script("HOOK: h\nCAST: A = boy\nSCENE: room\nCUT ots\nA: hi | हाय\nCTA: c\n")
        self.assertTrue(any("ots" in w for w in warn))

    def test_back_view_has_no_face(self):
        front, _ = build_character({"look": "boy"}, {}, "neutral", 0.0, 0.0, 540, 1700)
        back, an = build_character({"look": "boy", "view": "back"}, {}, "neutral", 0.0, 0.0, 540, 1700)
        self.assertLess(len(back), len(front))
        self.assertIn("head_top", an)
        for hair in ("short", "long", "braid", "bun", "ponytail", "curly", "spiky", "balding", "bald"):
            for acc in ([], ["cap"], ["turban"], ["earrings"]):
                build_character({"look": "girl", "hair": hair, "view": "back", "accessories": acc,
                                 "outfit": "saree"}, {}, "neutral", 0.0, 0.0, 540, 1700)

    def test_renders(self):
        img = Renderer(self.subs[2], width=270, use_tts=False).frame(0.5)
        self.assertEqual(img.size[0], 270)

    def test_page_knows_the_words(self):
        v = vocab()
        self.assertIn("ots", v["framings"])
        self.assertIn("reverse", v["angle_words"])


if __name__ == "__main__":
    unittest.main()

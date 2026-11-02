"""Characters, faces and camera angles look different. python -m unittest discover -s tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio.characters import LOOKS, assign_faces, build_character      # noqa: E402
from studio.script import parse_script                     # noqa: E402
from studio.scene import split_scenes                      # noqa: E402


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


if __name__ == "__main__":
    unittest.main()

"""Characters, faces and camera angles look different. python -m unittest discover -s tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio.characters import LOOKS                        # noqa: E402
from studio.script import parse_script                     # noqa: E402


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


if __name__ == "__main__":
    unittest.main()

"""Four people in one scene (a family, an office team): each has a place of their own, left to right, a little
smaller than three; 1-3 people stand exactly as before. python -m unittest discover -s tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import director  # noqa: E402
from studio.render import make_video  # noqa: E402
from studio.scene import PEOPLE_SCALE_3, SLOTS, compile_scene, split_scenes  # noqa: E402
from studio.script import parse_script  # noqa: E402

FAMILY = """HOOK: Family 😂
CAST: P = papa, M = mummy, B = beta, D = dadi
SCENE: living_room
P (angry): Bill kisne badhaya? | बिल किसने बढ़ाया?
M (point): Tumhare bete ne! | तुम्हारे बेटे ने!
B (shock): Main? Dadi ka TV! | मैं? दादी का टीवी!
D (smug): Mera serial bijli nahi khata. | मेरा सीरियल बिजली नहीं खाता।
"""


def plan_of(text):
    sc, warns = parse_script(text)
    return compile_scene(split_scenes(sc)[0], use_tts=False), warns


class FourPeople(unittest.TestCase):
    def test_everybody_has_a_place(self):
        plan, warns = plan_of(FAMILY)
        self.assertEqual(warns, [])
        xs = [plan.chars[n].draw_pos(0.0)[0] for n in ("P", "M", "B", "D")]
        self.assertEqual(xs, sorted(xs))                                  # left to right, in CAST order
        self.assertGreater(min(b - a for a, b in zip(xs, xs[1:])), 200)  # nobody on top of anybody
        self.assertTrue(all(60 < x < 1020 for x in xs))
        three, _w = plan_of(FAMILY.replace(", D = dadi", "").replace("D (smug)", "B (smug)"))
        self.assertLess(plan.chars["P"].scale, three.chars["P"].scale)  # four: a little smaller than three
        self.assertEqual(problems_for(FAMILY), [])                        # the studio's own check agrees
        self.assertTrue(problems_for(FAMILY.replace("D = dadi", "D = dadi, K = kid") + "K: Main bhi! | मैं भी!\n"))

    def test_one_to_three_as_before(self):
        self.assertEqual(SLOTS[3], {"left": 190, "center": 540, "right": 890})
        self.assertEqual(SLOTS[2], {"left": 300, "right": 780, "center": 540})
        plan, _w = plan_of(FAMILY.replace(", D = dadi", "").replace("D (smug)", "B (smug)"))
        self.assertEqual(sorted(round(c.draw_pos(0.0)[0]) for c in plan.chars.values()), [190, 540, 890])
        self.assertAlmostEqual(PEOPLE_SCALE_3, 1.06)

    def test_five_is_too_many(self):
        _sc, warns = parse_script(FAMILY.replace("D = dadi", "D = dadi, K = kid"))
        self.assertTrue(any("more than 4" in w for w in warns))

    def test_it_renders_in_both_looks(self):
        for style in ("", "STYLE: 2.5d\n"):
            sc, _w = parse_script(FAMILY + style)
            v = make_video(sc, 216, use_tts=False)
            self.assertEqual(v.frame(2.0).size, (216, 384))


def problems_for(text):
    import tempfile
    sc, _w = parse_script(text)
    with tempfile.TemporaryDirectory() as tmp:
        found = director.problems(sc, os.path.join(tmp, "scene.json"))
    return [p for p in found if "more than" in p or "does not load" in p]


if __name__ == "__main__":
    unittest.main()

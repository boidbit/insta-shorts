"""People move like people (cine camera): planted feet, a crouch before a jump, turning through the front, sitting
side-on, a scene title as its own card, and different heights and builds. CAMERA: classic keeps the old motion.
python -m unittest discover -s tests"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import script                                   # noqa: E402
from studio.characters import HEIGHTS                       # noqa: E402
from studio.render import Renderer, make_video              # noqa: E402
from studio.scene import TITLE_LEAD, split_scenes           # noqa: E402
from studio.script import parse_script, vary_bodies         # noqa: E402

WALK = "HOOK: h\nCAST: A = boy\nSCENE: street\nA -> walk left\nA -> walk right\nCTA: c\n"


def renderer(text, classic=False):
    sc, _ = parse_script(text + ("CAMERA: classic\n" if classic else ""))
    return Renderer(split_scenes(sc)[0], 216, use_tts=False)


def moving(r, c):
    mv = [m for m in c.moves if m[1] - m[0] > 0.5]
    return mv[0]


class FeetTests(unittest.TestCase):
    def feet(self, r, c, t):
        """[(world x, on the ground?)] of both feet at t, from the leg IK targets."""
        got = []
        real = Renderer._leg_ik

        def spy(hx, fx, fy, th, sh, dirn):
            got.append((fx, fy))
            return real(hx, fx, fy, th, sh, dirn)
        with mock.patch.object(Renderer, "_leg_ik", staticmethod(spy)):
            r._prep(c, t, {})
        x, k = c.pos_at(t)[0], c.draw_scale(t)
        low = max(fy for _fx, fy in got[:2])
        return [(x + fx * k, fy >= low - 1e-6) for fx, fy in got[:2]]

    def test_a_foot_on_the_ground_does_not_slide(self):
        r = renderer(WALK)
        c = r.plan.chars["A"]
        t0, t1 = moving(r, c)[:2]
        dt = 1.0 / 30
        slides = []
        t = t0 + 0.25 * (t1 - t0)
        while t < t0 + 0.75 * (t1 - t0):
            for (xa, down_a), (xb, down_b) in zip(self.feet(r, c, t), self.feet(r, c, t + dt)):
                if down_a and down_b:               # on the ground in both frames: it must not move
                    slides.append(abs(xa - xb))
            t += dt
        self.assertGreater(len(slides), 5)
        self.assertLess(max(slides), 0.5, slides)

    def test_steps_follow_the_distance_walked(self):
        r = renderer(WALK)
        c = r.plan.chars["A"]
        t0, t1, x0, _y0, x1 = moving(r, c)[:5]
        tm = (t0 + t1) / 2
        self.assertAlmostEqual(r._travel(c, tm) - r._travel(c, t0), abs(c.pos_at(tm)[0] - x0), places=3)

    def test_classic_keeps_the_old_walk(self):
        r = renderer(WALK, classic=True)
        c = r.plan.chars["A"]
        with mock.patch.object(Renderer, "_planted_legs", side_effect=AssertionError("planted legs in classic")):
            r._prep(c, sum(moving(r, c)[:2]) / 2, {})


class BodyTests(unittest.TestCase):
    def test_a_crouch_before_a_jump(self):
        r = renderer("HOOK: h\nCAST: A = boy\nSCENE: room\nA (jump): Haan! | हाँ!\nCTA: c\n")
        c = r.plan.chars["A"]
        t = next(e["t"] for e in c.events if e.get("action") == "jump")
        E = r._eff(c, t + 0.1)
        pose = r._build_pose(c, t + 0.1, E)
        self.assertGreater(pose.get("_crouch", 0.0), 0.5)

    def test_turning_round_goes_through_the_front(self):
        r = renderer(WALK)
        c = r.plan.chars["A"]
        m1, m2 = [m for m in c.moves if m[1] - m[0] > 0.5][:2]
        self.assertEqual(r._eff(c, m2[0] + 0.05)["st"]["facing"], "front")
        self.assertEqual(r._eff(c, m2[0] + 0.3)["st"]["facing"], "right")

    def test_sitting_people_turn_to_each_other(self):
        r = renderer("HOOK: h\nCAST: A = boy, B = girl\nSCENE: room\nOBJ: sofa center\nA -> sit sofa\n"
                     "B: Kya hua? | क्या हुआ?\nCTA: c\n")
        c = r.plan.chars["A"]
        t = r.plan.duration - 0.6
        E = r._eff(c, t)
        self.assertEqual(E["action"], "sit")
        other = r.plan.chars["B"].pos_at(t)[0]
        self.assertEqual(E["st"]["facing"], "right" if other > E["x"] else "left")

    def test_a_scene_title_is_its_own_card_before_the_shot(self):
        sc, _ = parse_script("HOOK: h\nCAST: A = boy\nSCENE: room | Agle din...\nA: Hi | हाय\nCTA: c\n")
        sub = split_scenes(sc)[0]
        self.assertEqual(sub["lead_in"], TITLE_LEAD)
        self.assertTrue(any(o.get("type") == "timecard" for o in sub["overlays"]))
        sc, _ = parse_script("HOOK: h\nCAST: A = boy\nSCENE: room | Agle din...\nA: Hi | हाय\nCTA: c\nCAMERA: classic\n")
        self.assertFalse(any(o.get("type") == "timecard" for o in split_scenes(sc)[0].get("overlays", [])))


class HeightWeightTests(unittest.TestCase):
    def test_people_of_one_video_get_different_bodies(self):
        cast = {n: {"look": "boy"} for n in "ABCD"}
        vary_bodies(cast)
        bodies = [(c.get("height", "normal"), c.get("build", "normal")) for c in cast.values()]
        self.assertEqual(len(set(bodies)), 4, bodies)

    def test_the_script_words(self):
        sc, warns = parse_script("HOOK: h\nCAST: A = boy mota nata, B = girl patli lambi\nSCENE: room\n"
                                 "A: Hi | हाय\nB: Hi | हाय\nCTA: c\n")
        self.assertEqual(warns, [])
        a, b = sc["characters"]["A"], sc["characters"]["B"]
        self.assertEqual((a["build"], a["height"]), ("chubby", "short"))
        self.assertEqual((b["build"], b["height"]), ("slim", "tall"))

    def test_a_tall_person_is_taller_and_has_longer_legs(self):
        r = renderer("HOOK: h\nCAST: A = boy lamba, B = boy nata\nSCENE: street\nA: Hi | हाय\nB: Hi | हाय\nCTA: c\n")
        a, b = r.plan.chars["A"], r.plan.chars["B"]
        self.assertAlmostEqual(a.scale / b.scale, HEIGHTS["tall"][0] / HEIGHTS["short"][0], places=3)
        self.assertGreater(a.leg_k, 1.0)
        self.assertLess(b.leg_k, 1.0)

    def test_classic_keeps_everybody_the_same(self):
        sc, _ = parse_script("HOOK: h\nCAST: A = boy, B = boy, C = boy\nSCENE: room\nA: Hi | हाय\nCTA: c\n"
                             "CAMERA: classic\n")
        self.assertFalse(any("height" in c or "build" in c for c in sc["characters"].values()))

    def test_a_video_still_renders(self):
        sc, _ = parse_script("HOOK: h\nCAST: A = uncle lamba, B = college_girl moti\nSCENE: room\n"
                             "A (angry): Kahan thi? | कहाँ थी?\nB (sit): Yahin | यहीं\nCTA: c\n")
        v = make_video(sc, 216, use_tts=False)
        v.frame(v.duration / 2)


if __name__ == "__main__":
    unittest.main()

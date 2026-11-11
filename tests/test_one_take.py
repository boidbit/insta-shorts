"""One take across places (`SCENE: <place> pan`): whoever leaves walks on into the next place and the camera goes
with them, no cut. And the jail's barred door that can be kicked down. python -m unittest discover -s tests"""
import os
import sys
import unittest

from PIL import ImageChops, ImageStat

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio.render import make_video                         # noqa: E402
from studio.scene import drop_last_exit, split_scenes, wide_weight   # noqa: E402
from studio.script import parse_script                       # noqa: E402
from studio.sets import Sets                                 # noqa: E402

HOME_TO_STREET = """HOOK: h
CAST: R = college_boy, M = aunty, S = chaiwala
SCENE: room
M (angry): Doodh le aa! | दूध ले आ!
R -> exit right
SCENE: street pan | Bazaar
S: Chai piyoge? | चाय पियोगे?
CTA: c
"""

JAIL = """HOOK: h
CAST: C = chor
SCENE: jail
C (sly): Aaj bhaag jaunga | आज भाग जाऊँगा
C -> walk right
C -> kick
OBJ: jail_door broken
C -> exit right fast
SCENE: street pan
C (laugh): Azaad! | आज़ाद!
CTA: c
"""


def diff(a, b):
    return sum(ImageStat.Stat(ImageChops.difference(a.convert("RGB"), b.convert("RGB"))).mean) / 3


class ScriptTests(unittest.TestCase):
    def test_the_one_who_left_walks_into_the_next_place(self):
        sc, warns = parse_script(HOME_TO_STREET)
        self.assertEqual(warns, [])
        self.assertEqual(sc["scenes"][1]["pan"], {"who": "R", "dir": "right"})
        self.assertEqual(sc["scenes"][1]["cast"][0], "R")          # comes in from the left: stands on the left
        subs = split_scenes(sc)
        self.assertFalse(any(e.get("who") == "R" and "move" in e for e in subs[0]["timeline"]))   # exit gone
        self.assertEqual(subs[1]["pan"]["who"], "R")
        self.assertIn("R", subs[1]["characters"])
        self.assertNotIn("lead_in", subs[1])                       # (the title waits for the walk, no card)

    def test_any_place_any_person_and_a_named_walker(self):
        sc, warns = parse_script("HOOK: h\nCAST: A = boy, B = girl\nSCENE: street\nA: Chalo | चलो\n"
                                 "SCENE: school pan A\nB: Aa gaye? | आ गए?\nCTA: c\n")
        self.assertEqual(warns, [])
        self.assertEqual(sc["scenes"][1]["pan"]["who"], "A")
        self.assertEqual(sc["scenes"][1]["background"]["type"], "school")

    def test_nobody_to_follow_is_a_warning(self):
        _sc, warns = parse_script("HOOK: h\nCAST: A = boy\nSCENE: street\nA: Hi | हाय\nSCENE: room pan\n"
                                  "A: Hello | हेलो\nCTA: c\n")
        self.assertTrue(any("pan" in w for w in warns))

    def test_drop_last_exit_only_when_it_ends_the_scene(self):
        tl = [{"t": 0, "who": "A", "say": "x"}, {"who": "A", "move": {"x": 1240}, "facing": "right", "hold": 1.1}]
        out, side, fast = drop_last_exit(tl, "A")
        self.assertEqual((len(out), side, fast), (1, "right", False))
        tl2 = tl + [{"who": "B", "say": "gaya"}]
        self.assertEqual(drop_last_exit(tl2, "A"), (tl2, None, False))
        out, side, fast = drop_last_exit([{"who": "A", "leave": {"style": "fast", "side": "left"}}], "A")
        self.assertEqual((out, side, fast), ([], "left", True))


class TakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sc, _ = parse_script(HOME_TO_STREET)
        cls.v = make_video(sc, 216, use_tts=False)

    def test_the_next_place_waits_for_the_walk(self):
        g = self.v.pans[1]
        self.assertIsNotNone(g)
        self.assertGreaterEqual(g["dur"], 2.0)
        part = self.v.parts[1]
        first_line = min(sp["start"] for sp in part.speech)
        self.assertGreaterEqual(first_line, g["dur"])

    def test_no_cut_the_take_starts_and_ends_on_the_shots(self):
        v, g = self.v, self.v.pans[1]
        o = v.offsets[1]
        dt = 1.0 / v.fps
        self.assertLess(diff(v.frame(o - dt), v.frame(o)), 4.0)            # the last place, then it starts to slide
        self.assertLess(diff(v.frame(o + g["dur"] - dt), v.frame(o + g["dur"])), 4.0)   # ... lands on the new shot
        self.assertGreater(diff(v.frame(o), v.frame(o + g["dur"] / 2)), 10.0)          # (and it really travels)

    def test_both_cameras_show_the_whole_picture_meanwhile(self):
        prev, part, g = self.v.parts[0], self.v.parts[1], self.v.pans[1]
        self.assertEqual(wide_weight(prev.plan, g["t0"] + 0.1), 1.0)
        self.assertEqual(wide_weight(part.plan, g["dur"] / 2), 1.0)
        self.assertEqual(wide_weight(part.plan, g["dur"] + 2.0), 0.0)

    def test_the_walker_keeps_stepping_from_one_place_into_the_next(self):
        prev, part, g = self.v.parts[0], self.v.parts[1], self.v.pans[1]
        ca, cb = prev.plan.chars["R"], part.plan.chars["R"]
        tau = g["dur"] * 0.5
        self.assertAlmostEqual(prev._travel(ca, g["t0"] + tau), part._travel(cb, tau), places=3)
        xa = ca.pos_at(g["t0"] + tau)[0]
        xb = cb.pos_at(tau)[0]
        self.assertAlmostEqual(xa, xb + g["dirn"] * 1080, places=3)      # one path through both places

    def test_the_title_shows_while_they_walk_in(self):
        part, g = self.v.parts[1], self.v.pans[1]
        card = [o for o in part.plan.overlays if o.get("text") == "Bazaar"]
        first_line = min(sp["start"] for sp in part.speech)
        self.assertTrue(card and card[0]["from"] < g["dur"] and card[0]["to"] < first_line)


class JailDoorTests(unittest.TestCase):
    def test_a_jail_scene_has_its_door_and_a_kick_breaks_it(self):
        sc, warns = parse_script(JAIL)
        self.assertEqual(warns, [])
        sets = sc["scenes"][0]["sets"]
        self.assertEqual(sets[0]["type"], "jail_door")
        v = make_video(sc, 216, use_tts=False)
        p = v.parts[0].plan
        ev = [e for e in p.set_events if e["set"] == "jail_door"]
        self.assertEqual(ev[0]["state"], "broken")
        self.assertTrue(any(abs(sh[0] - ev[0]["t"]) < 1e-6 for sh in p.shakes))
        self.assertTrue(any(abs(fx["t"] - ev[0]["t"]) < 1e-6 for fx in p.sfx))
        self.assertEqual(v.pans[1]["who"], "C")
        self.assertTrue(v.pans[1]["run"])                          # `exit right fast`: he runs out

    def test_the_door_looks_different_closed_open_and_broken(self):
        ob = {"id": "d", "type": "jail_door", "x": 930, "y": 1290}
        sets = Sets([ob], [], 0.2, 216, 384)
        ims = [sets._image(ob, st, 0.0)[0] for st in ("closed", "open", "broken")]
        self.assertGreater(diff(ims[0], ims[1]), 3.0)
        self.assertGreater(diff(ims[0], ims[2]), 3.0)

    def test_the_door_sits_over_the_painted_one(self):
        sc, _ = parse_script(JAIL)
        v = make_video(sc, 216, use_tts=False)
        p = v.parts[0].plan
        door = [o for o in p.sets if o["type"] == "jail_door"][0]
        self.assertEqual(door.get("scale", 1.0), 1.0)              # not grown with the people
        self.assertEqual((door["x"], door["y"]), (930, 1290))


if __name__ == "__main__":
    unittest.main()

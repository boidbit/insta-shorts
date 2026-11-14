"""The sarkari daftar (its desk comes by itself, the babu sits behind it), chalk writing on a blackboard, somebody
lying on a bed while another walks in. python -m unittest discover -s tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import director, scene, styles      # noqa: E402
from studio.render import make_video             # noqa: E402
from studio.script import parse_script           # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")


def video(text, width=160):
    sc, w = parse_script(text)
    return make_video(sc, width, use_tts=False, hook="off"), w


class Daftar(unittest.TestCase):
    TEXT = ("HOOK: x\nMYSTERY: off\nCAST: B = clerk babu, A = uncle\nSCENE: sarkari office\nCUT wide\n"
            "A: Babu ji, meri file? | बाबू जी, मेरी फ़ाइल?\nB: Kal aana. | कल आना।\n")

    def test_the_place_and_its_desk(self):
        sc, w = parse_script(self.TEXT)
        self.assertEqual(w, [])
        first = sc["scenes"][0]
        self.assertEqual(first["background"]["type"], "sarkari_daftar")
        desk = first["sets"][0]
        self.assertEqual((desk["type"], desk["items"]), ("desk", ["files", "register", "thappa"]))
        self.assertIn("sarkari_daftar", styles.PLACES_25D)
        sc, _ = parse_script("HOOK: x\nCAST: B = clerk\nSCENE: daftar\nOBJ: desk left chai\n")
        self.assertEqual([(s_["type"], s_["items"]) for s_ in sc["scenes"][0]["sets"]], [("desk", ["chai"])])

    def test_the_babu_is_behind_the_desk_also_in_the_wide_shot(self):
        v, _ = video(self.TEXT)
        for p in v.parts:
            b = p.plan.chars["B"]
            self.assertEqual(b.x, 540.0, p.plan.framing)
            self.assertTrue(b.depth and b.depth[0][2] < 0)
        for style in ("2d", "2.5d"):            # both looks draw it
            v, _ = video(self.TEXT.replace("MYSTERY: off\n", "MYSTERY: off\nSTYLE: %s\n" % style), 120)
            v.frame(v.duration * 0.5)


class Board(unittest.TestCase):
    def test_the_words_appear_as_the_chalk_writes(self):
        v, w = video("HOOK: t\nMYSTERY: off\nCAST: T = master_ji, S = school_boy\nSCENE: classroom\n"
                     "OBJ: blackboard center 2+2=5\nT -> write_board\nS (shock): Sir, ye galat hai! | सर, ये ग़लत है!\n")
        self.assertEqual(w, [])
        p = v.parts[-1]
        ev = next(e for e in p.plan.set_events if e.get("write"))
        board = p.sets
        self.assertEqual(board.written("blackboard", ev["t"] - 0.1), 0)
        mid = board.written("blackboard", ev["t"] + ev["write"] / 2)
        self.assertTrue(0 < mid < 5, mid)
        self.assertIsNone(board.written("blackboard", ev["t"] + ev["write"] + 0.1))      # all of it
        t_wb = next(e["t"] for e in p.plan.chars["T"].events if e.get("action") == "write_board")
        x = p.plan.chars["T"].pos_at(t_wb)[0]
        self.assertGreater(abs(x - 760), 200)   # beside the board, not in front of it


class Bed(unittest.TestCase):
    TEXT = ("HOOK: t\nMYSTERY: off\nCAST: H = uncle, W = aunty\nSCENE: bedroom\nOBJ: bed center\n"
            "H -> sleep_lie bed\nH: Aaj chhutti hai. | आज छुट्टी है।\nW -> enter left\n"
            "W (angry): Uthiye! Sabzi laani hai! | उठिए! सब्ज़ी लानी है!\n")

    def test_the_one_who_walks_in_stands_on_the_far_side(self):
        v, w = video(self.TEXT)
        self.assertEqual(w, [])
        wife = v.parts[-1].plan.chars["W"]
        self.assertTrue(wife.depth and wife.depth[0][2] < 0)

    def test_the_camera_shows_the_whole_body(self):
        v, _ = video(self.TEXT)
        plan = v.parts[-1].plan
        h = plan.chars["H"]
        t = next(sp["start"] for sp in plan.speech if sp["who"] == "H") + 0.3
        fx, _fy = h.focus_at(t)
        self.assertLess(fx, h.draw_pos(t)[0] - 200)        # the middle of the body, not the feet
        z = scene.camera_at(plan, t)
        z = z.get("zoom", z) if isinstance(z, dict) else z[0]
        self.assertLessEqual(z, scene.LIE_ZOOM + 0.15)


class Prompt(unittest.TestCase):
    def test_the_rule_and_the_place(self):
        with open(os.path.join(ROOT, "SCRIPT_PROMPT.md"), encoding="utf-8") as f:
            core = director.prompt_text(f.read(), keep=())
        self.assertIn("change the joke", core)
        self.assertIn("sarkari_daftar", core)


if __name__ == "__main__":
    unittest.main()

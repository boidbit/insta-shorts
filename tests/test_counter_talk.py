"""A conversation across a counter, directed like a film (the opening with the customer's back to us, over the
shoulder, the reverse shot, a side two-shot), and people seen from the side. python -m unittest discover -s tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio.characters import HAIR_STYLES, LOOKS, build_character   # noqa: E402
from studio.render import make_video                                 # noqa: E402
from studio.scene import compile_scene, split_scenes                 # noqa: E402
from studio.script import parse_script                               # noqa: E402

TALK = """HOOK: Kulche ka review
CAST: F = food_blogger, K = kulchewala
SCENE: street
OBJ: thela kulche center
F (excited): Bhaiya, ek plate matar kulche! | भैया, एक प्लेट मटर कुलचे!
K (proud): Chalees saal se yahin bana raha hoon. | चालीस साल से यहीं बना रहा हूँ।
F (point): Toh secret kya hai? | तो सीक्रेट क्या है?
K (sly): Pehle camera band karo. | पहले कैमरा बंद करो।
F (shock): Arre bhaiya! | अरे भैया!
"""


def plan_of(text):
    sc, warns = parse_script(text)
    return compile_scene(split_scenes(sc)[0], use_tts=False), warns


class SideView(unittest.TestCase):
    def test_everybody_can_turn(self):
        for look in LOOKS:
            for facing in ("left", "right"):
                ops, an = build_character({"look": look, "view": "side", "facing": facing}, {}, "smile", 0.0, 0.0,
                                          540, 1700)
                self.assertTrue(ops)
                self.assertLess(an["head_top"][1], an["head_center"][1])
        front, _ = build_character({"look": "boy"}, {}, "smile", 0.0, 0.0, 540, 1700)
        side, _ = build_character({"look": "boy", "view": "side"}, {}, "smile", 0.0, 0.0, 540, 1700)
        self.assertNotEqual(front, side)
        for hair in HAIR_STYLES:
            self.assertTrue(build_character({"look": "girl", "hair": hair, "view": "side"}, {}, "laugh", 0.5, 0.0,
                                            540, 1700, talking=True)[0])

    def test_the_side_word(self):
        plan, warns = plan_of("HOOK: h\nCAST: A = boy, B = girl\nSCENE: room\nA (side, smile): Suno | सुनो\n"
                              "B: Haan | हाँ\nA (saamne): Kuch nahi | कुछ नहीं\n")
        self.assertEqual(warns, [])
        a = plan.chars["A"]
        said = [sp["start"] for sp in plan.speech if sp["who"] == "A"]
        self.assertEqual(a.state_at(said[0] + 0.1)["view"], "side")
        self.assertEqual(a.state_at(said[1] + 0.1)["view"], "front")


class CounterTalk(unittest.TestCase):
    def test_the_shots(self):
        plan, warns = plan_of(TALK)
        self.assertEqual(warns, [])
        kinds = [sh["kind"] for sh in plan.counter_shots]
        self.assertEqual(kinds[0], "open")
        for k in ("ots", "reverse", "profile"):
            self.assertIn(k, kinds)
        sh = {s_["kind"]: s_ for s_ in plan.counter_shots}
        self.assertEqual(sh["open"]["ov"]["F"]["view"], "back")             # the customer's back to us
        self.assertEqual(sh["ots"]["ov"]["F"]["view"], "back")
        self.assertGreater(sh["ots"]["ov"]["F"]["k"], plan.chars["F"].scale)  # big in the near corner
        self.assertTrue(sh["reverse"]["ov"]["K"]["hidden"])                # (the seller is where the camera is)
        self.assertTrue(sh["reverse"]["blur"] and sh["reverse"]["edge"])
        self.assertEqual(sh["profile"]["ov"]["F"]["view"], "side")
        speakers = {sp["start"]: sp["who"] for sp in plan.speech}
        for t0, who in speakers.items():                                   # the seller speaks over the shoulder,
            cur = next(s_ for s_ in plan.counter_shots if s_["t0"] <= t0 + 0.1 < s_["t1"])
            if cur["kind"] != "open":                                      # the customer in the reverse / side shot
                self.assertEqual(cur["kind"] == "ots", who == "K")

    def test_frames_and_people_back_in_place(self):
        sc, _ = parse_script(TALK)
        r = make_video(sc, 216, use_tts=False)
        part = getattr(r, "parts", [r])[0]
        for sh in part.plan.counter_shots:
            self.assertEqual(r.frame(min(sh["t0"] + 0.3, part.plan.duration - 0.1)).size, (216, 384))
        self.assertTrue(all(c.ov is None for c in part.plan.chars.values()))

    def test_only_with_the_new_camera_and_its_own_camera(self):
        plan, _ = plan_of(TALK + "CAMERA: classic\n")
        self.assertEqual(plan.counter_shots, [])
        plan, _ = plan_of(TALK.replace("F (point):", "F (point, zoom):"))
        self.assertEqual(plan.counter_shots, [])                           # the script directs the camera itself
        plan, _ = plan_of("HOOK: h\nCAST: A = boy, B = girl\nSCENE: room\nA: Hi | हाय\nB: Hello | हेलो\n")
        self.assertEqual(plan.counter_shots, [])                           # no counter: as before

    def test_painted_counter(self):
        plan, _ = plan_of("HOOK: h\nCAST: B = college_boy, C = chaiwala\nSCENE: chai_tapri\nB: Ek cutting! | एक कटिंग!\n"
                          "C (smile): Abhi lo. | अभी लो।\nB (shock): Itni chhoti?! | इतनी छोटी?!\n")
        kinds = [sh["kind"] for sh in plan.counter_shots]
        self.assertEqual(kinds[:2], ["open", "reverse"])
        self.assertIn("ots", kinds)
        self.assertNotIn("profile", kinds)                                 # the chaiwala is far: no side two-shot


if __name__ == "__main__":
    unittest.main()


class StudioOpening(unittest.TestCase):
    def test_the_studios_own_opening_gives_way(self):
        # every video gets an opening of its own (plain / reveal / close, by its hook): a counter scene keeps its shots
        for hook in ("Cutting chai", "Kulche ka review", "Bhaiya ek plate", "Order order", "Chai pe charcha"):
            plan, _ = plan_of(TALK.replace("HOOK: Kulche ka review", "HOOK: " + hook))
            self.assertTrue(plan.counter_shots, hook)
        plan, _ = plan_of(TALK.replace("F (excited):", "F (excited, reveal):"))
        self.assertEqual(plan.counter_shots, [])                           # the writer's own reveal: their camera

    def test_in_25d(self):
        sc, _ = parse_script(TALK + "STYLE: 2.5d\n")
        r = make_video(sc, 216, use_tts=False)
        part = getattr(r, "parts", [r])[0]
        self.assertTrue(part.bd25 is not None and part.plan.counter_shots)
        for sh in part.plan.counter_shots:
            self.assertEqual(r.frame(min(sh["t0"] + 0.3, part.plan.duration - 0.1)).size, (216, 384))
        sc, _ = parse_script("HOOK: h\nCAST: A = boy, B = girl\nSCENE: room\nA (side): Suno | सुनो\nB: Haan | हाँ\n"
                             "STYLE: 2.5d\n")
        self.assertEqual(make_video(sc, 216, use_tts=False).frame(0.8).size, (216, 384))

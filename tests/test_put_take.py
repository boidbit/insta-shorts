"""Things on furniture: OBJ: desk center file chai; A -> put bag desk; A -> take file; a babu behind his desk.
python -m unittest discover -s tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import ImageChops                         # noqa: E402

from studio import sets                            # noqa: E402
from studio.render import make_video               # noqa: E402
from studio.script import parse_script             # noqa: E402

SCRIPT = ("HOOK: x\nMYSTERY: off\nCAST: A = uncle, B = clerk glasses\nSCENE: office\nOBJ: desk center file chai\n"
          "B (bored): File halki hai. | फ़ाइल हल्की है।\nA -> put bag desk\nA (proud): Lijiye! | लीजिए!\n"
          "B -> take file\nB (shock): Hain?! | हैं?!\n")


def video(text=SCRIPT, width=180):
    sc, w = parse_script(text)
    return make_video(sc, width, use_tts=False, hook="off"), w


class PutTake(unittest.TestCase):
    def test_the_lines(self):
        sc, w = parse_script(SCRIPT)
        self.assertEqual(w, [])
        self.assertEqual(sc["scenes"][0]["sets"][0]["items"], ["file", "chai"])
        acts = [e for e in sc["scenes"][0]["timeline"] if e.get("action") in ("put", "take")]
        self.assertEqual(acts[0]["put"], {"item": "bag", "on": "desk"})
        self.assertEqual(acts[1]["take"], {"item": "file"})
        sc, w = parse_script("HOOK: x\nCAST: A = uncle\nSCENE: room\nOBJ: table center pathar paperweight\n"
                             "A -> rakh notes table\n")
        self.assertEqual(w, [])
        self.assertEqual(sc["scenes"][0]["sets"][0]["items"], ["pathar", "paperweight"])

    def test_the_thing_goes_from_the_hand_to_the_desk_and_back(self):
        v, _ = video()
        p = v.parts[0]
        add = next(e for e in p.sets.events if e.get("add"))
        rem = next(e for e in p.sets.events if e.get("remove"))
        self.assertEqual((add["add"], rem["remove"]), ("bag", "file"))
        self.assertEqual(p.sets.items("desk", add["t"] - 0.01), ["file", "chai"])
        self.assertEqual(p.sets.items("desk", add["t"] + 0.01), ["file", "chai", "bag"])
        self.assertEqual(p.sets.items("desk", rem["t"] + 0.01), ["chai", "bag"])
        a, b = p.plan.chars["A"], p.plan.chars["B"]
        self.assertEqual(a.state_at(add["t"] - 0.1)["prop"], "bag")
        self.assertIn(a.state_at(add["t"] + 0.1)["prop"], ("", None))
        self.assertEqual(b.state_at(rem["t"] + 0.1)["prop"], "file")
        self.assertIsNotNone(ImageChops.difference(v.frame(add["t"] - 0.05).convert("RGB"),
                                                   v.frame(add["t"] + 0.05).convert("RGB")).getbbox())

    def test_a_far_person_walks_over_first(self):
        v, _ = video()
        p = v.parts[0]
        a = p.plan.chars["A"]
        add = next(e for e in p.sets.events if e.get("add"))
        self.assertTrue(a.moves)                             # stood at the far side: walks up to the desk
        self.assertLess(abs(a.pos_at(add["t"])[0] - 540.0), 330.0)

    def test_the_babu_sits_behind_his_desk(self):
        v, _ = video()
        b = v.parts[0].plan.chars["B"]
        self.assertEqual(b.x, 540.0)
        self.assertLess(b.depth_at(1.0)[1], 0)              # one step back: the desk is in front of him

    def test_every_item_draws_and_every_carried_item_has_a_hand_prop(self):
        from studio.characters import PROPS
        for name in sets.ITEMS:
            self.assertIn(sets.HELD_AS[name], PROPS, name)
        for word, name in sets.ITEM_WORDS.items():
            self.assertIn(name, sets.ITEMS, word)


if __name__ == "__main__":
    unittest.main()


class Work(unittest.TestCase):
    def test_every_work_action_brings_a_tool_that_exists_and_moves_smoothly(self):
        import math
        from studio import actions
        from studio.characters import DEFAULT_POSE, PROPS, skeleton
        for name in sorted(actions.WORK_ACTIONS):
            prev = None
            for i in range(0, 6 * 120):
                p = dict(DEFAULT_POSE)
                p.update(actions.pose_for(name, i / 120.0, 1.0, 1.0, 0.0, {"_dir": 1}))
                if p.get("prop"):
                    self.assertIn(p["prop"], PROPS, name)
                hand = skeleton(p)["handR"]
                if prev is not None:
                    # (a strike is fast, never a teleport: under ~40 px in 1/120 s)
                    self.assertLess(math.hypot(hand[0] - prev[0], hand[1] - prev[1]), 40.0, (name, i / 120.0))
                prev = hand

    def test_the_prompt_has_them_in_a_module_the_page_knows(self):
        root = os.path.join(os.path.dirname(__file__), "..")
        prompt = open(os.path.join(root, "SCRIPT_PROMPT.md"), encoding="utf-8").read()
        self.assertIn("<!-- module: work -->", prompt)
        page = open(os.path.join(root, "index.html"), encoding="utf-8").read()
        self.assertIn('work: { label: "kaam-kaaj"', page)

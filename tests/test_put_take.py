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

"""Seen from the side (sitting on the podcast chairs, `side`), a front pose whose hand comes across the body to the
face or the chest (think, eat, drink, text, arms crossed, holding the vlog camera) has the hand in front of the body,
not bent back behind it, for somebody facing right and somebody facing left. python -m unittest"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import actions, profile                       # noqa: E402
from studio.characters import DEFAULT_POSE                # noqa: E402

COLS = {"skin": (200, 150, 110), "main": (100, 150, 220), "accent": (50, 50, 50), "pants": (60, 60, 90)}


def near_hand(act, f):
    p = dict(DEFAULT_POSE)
    p.update(actions.ACTIONS[act](0.5, 1.0, 1.0, 0.0, {"_dir": "right" if f > 0 else "left"}))
    _ops, anc = profile.draw_side({}, p, COLS, "neutral", 0.0, 0.5, 540.0, 1700.0, 1.0, f=f)
    return anc["hand_r" if f > 0 else "hand_l"], anc["head_center"]


class SideArms(unittest.TestCase):
    def test_reaching_hands_are_in_front(self):
        for act in ("think", "eat", "drink", "text", "arms_crossed"):
            for f in (1, -1):
                (hx, _hy), (cx, _cy) = near_hand(act, f)
                self.assertGreater((hx - cx) * f, 0, "%s facing %s" % (act, "right" if f > 0 else "left"))


if __name__ == "__main__":
    unittest.main()

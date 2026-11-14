"""Every move is smooth: no joint of any action jumps in time (a joint that covers most of a 1/240 s step in one
eighth of it is a pop, not motion), and the new reaction moves exist with their Hinglish names.
python -m unittest discover -s tests"""
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import actions                                  # noqa: E402
from studio.characters import DEFAULT_POSE, skeleton        # noqa: E402

JOINTS = ("handL", "handR", "elbL", "elbR", "footL", "footR", "kneeL", "kneeR")
DT = 1 / 240.0
POP = 6.0                   # px (reference body): the biggest pop allowed (a punch's snap is ~5 px)


def points(name, t, opts):
    p = dict(DEFAULT_POSE)
    p.update(actions.pose_for(name, t, 1.0, 1.0, 0.0, dict(opts)))
    sk = skeleton(p)
    out = {j: sk[j] for j in JOINTS if j in sk}
    out["body"] = (p.get("shift", 0.0) + p.get("dx", 0.0), p.get("lift", 0.0))
    for key, r in (("tilt", 290.0), ("head_tilt", 115.0)):     # round the circle: a full turn is no jump
        a = math.radians(p.get(key, 0.0))
        out[key] = (r * math.sin(a), r * math.cos(a))
    out["head"] = (p.get("head_dx", 0.0), p.get("head_dy", 0.0))
    return out


def dist(a, b):
    return max(math.hypot(a[k][0] - b[k][0], a[k][1] - b[k][1]) for k in a if k in b)


def pops(name, seconds=6.0, opts=None):
    """[(t, px)] of the jumps in this action."""
    opts = opts or {"_dir": 1, "_bpm": 100}
    out, t, prev = [], 0.0, points(name, 0.0, opts)
    while t < seconds:
        t2 = t + DT
        cur = points(name, t2, opts)
        d = dist(prev, cur)
        if d > POP:                         # most of the step inside one eighth of it: a pop
            sub = [points(name, t + DT * i / 8.0, opts) for i in range(9)]
            if max(dist(a, b) for a, b in zip(sub, sub[1:])) > 0.6 * d:
                out.append((round(t2, 3), round(d, 1)))
        prev, t = cur, t2
    return out


class Smooth(unittest.TestCase):
    def setUp(self):
        self._soft = actions.SOFT_REACH
        actions.SOFT_REACH = True           # the cine camera's natural reach

    def tearDown(self):
        actions.SOFT_REACH = self._soft

    def test_no_action_pops(self):
        seen = {}
        for name, fn in sorted(actions.ACTIONS.items()):
            seen.setdefault(fn, name)
        bad = {}
        for fn, name in seen.items():
            for opts in ({"_dir": 1, "_bpm": 100}, {"_dir": -1, "_bpm": 100, "_facing": "left"}):
                p = pops(name, opts=opts)
                if p:
                    bad[name] = p[:3]
        self.assertEqual(bad, {})

    def test_the_new_reaction_moves(self):
        for name, alias in (("double_take", "dobara_dekh"), ("slow_clap", "dheere_taali"), ("mic_drop", "mic_drop"),
                            ("collar_up", "collar_khada"), ("nazar_utaar", "nazar")):
            self.assertIn(name, actions.REACTION_MOVES)
            self.assertIs(actions.ACTIONS[alias], actions.ACTIONS[name])
        self.assertEqual(actions.pose_for("mic_drop", 0.5).get("prop"), "mic")     # in the hand...
        self.assertNotIn("prop", actions.pose_for("mic_drop", 1.2))              # ...and dropped
        far = points("double_take", 0.95, {"_dir": 1})["handR"]
        near = points("double_take", 0.1, {"_dir": 1})["handR"]
        self.assertLess(far[1], near[1] - 60)                                    # the hands come up in the snap


if __name__ == "__main__":
    unittest.main()

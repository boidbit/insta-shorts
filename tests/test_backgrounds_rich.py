"""Backgrounds of the new camera: a finishing pass (contact shadow, texture, light) and the desi dressing of the
busiest places; `CAMERA: classic` keeps the old flat drawings. python -m unittest"""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import dressing                               # noqa: E402
from studio.backgrounds import Background                 # noqa: E402


def img(kind, **kw):
    return np.asarray(Background(dict(type=kind, **kw), 270, 480).frame(0).convert("RGB"), np.int16)


class RichBackgrounds(unittest.TestCase):
    def test_classic_is_untouched(self):
        a = img("room", classic=True)
        b = img("room", classic=True, finish=False)
        self.assertEqual(np.abs(a - b).max(), 0)

    def test_the_wall_meets_the_floor_in_shadow(self):
        flat, rich = img("room", finish=False), img("room")
        row = int(1255 / 4)                                   # just above the floor line (room: 1260)
        self.assertLess(rich[row, 100:170].mean(), flat[row, 100:170].mean() - 3)

    def test_the_same_place_looks_the_same_every_time(self):
        self.assertEqual(np.abs(img("gully") - img("gully")).max(), 0)

    def test_desi_dressing(self):
        for kind in ("gully", "gaon", "room", "kitchen", "kachcha_ghar", "chai_tapri"):
            self.assertIn(kind, dressing.PLACES)
            self.assertGreater(np.abs(img(kind) - img(kind, finish=False)).mean(), 1.0, kind)
        self.assertEqual(dressing.PLACES["gully"][0][0], "wires")


if __name__ == "__main__":
    unittest.main()

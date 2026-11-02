"""New places and the moving things behind the characters. python -m unittest discover -s tests"""
import os
import sys
import unittest

from PIL import ImageChops

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio.backgrounds import AMBIENT, Background   # noqa: E402
from studio.script import BACKGROUNDS, parse_script, vocab   # noqa: E402

W, H = 216, 384


class PlaceTests(unittest.TestCase):
    def test_new_places_are_known_everywhere(self):
        for p in ("market", "office", "bus_stop"):
            self.assertIn(p, BACKGROUNDS)
            self.assertIn(p, vocab()["places"])
            sc, warns = parse_script("CAST: A = dost\nSCENE: %s\nHOOK: h\nCTA: c\nA (smile): hi | हाय\n" % p)
            self.assertEqual(warns, [], p)

    def test_every_place_draws_a_full_frame(self):
        for kind in ("kitchen", "room", "street", "school", "market", "office", "bus_stop", "night_road", "plain"):
            im = Background({"type": kind}, W, H).frame(1.0)
            self.assertEqual(im.size, (W, H), kind)


class AmbientTests(unittest.TestCase):
    def test_street_moves_on_its_own(self):
        bg = Background({"type": "street"}, W, H)
        diff = ImageChops.difference(bg.frame(1.0).convert("RGB"), bg.frame(4.0).convert("RGB"))
        self.assertIsNotNone(diff.getbbox())                           # clouds / birds / traffic changed something

    def test_traffic_crosses_and_then_the_lane_is_empty(self):
        bg = Background({"type": "bus_stop"}, 360, 640)
        period = [i for i in AMBIENT["bus_stop"] if i[0] == "traffic"][0][3]
        still = Background({"type": "bus_stop", "ambient": False}, 360, 640).frame(0.0).convert("RGB")
        busy = bg.frame(period * 0.3).convert("RGB")                   # mid-crossing
        quiet = bg.frame(period * 0.9).convert("RGB")                  # lane empty; only clouds / birds differ
        lane = (0, int(1380 * 360 / 1080), 360, int(1560 * 360 / 1080))
        self.assertIsNotNone(ImageChops.difference(busy.crop(lane), still.crop(lane)).getbbox())
        self.assertIsNone(ImageChops.difference(quiet.crop(lane), still.crop(lane)).getbbox())

    def test_can_be_switched_off(self):
        bg = Background({"type": "street", "ambient": False}, W, H)
        self.assertIsNone(ImageChops.difference(bg.frame(1.0).convert("RGB"), bg.frame(4.0).convert("RGB")).getbbox())

    def test_indoor_places_are_still(self):
        for kind in ("kitchen", "room", "office", "market"):
            bg = Background({"type": kind}, W, H)
            self.assertIsNone(ImageChops.difference(bg.frame(1.0).convert("RGB"), bg.frame(4.0).convert("RGB")).getbbox())


if __name__ == "__main__":
    unittest.main()

"""Your own picture as a place in the text script. python -m unittest discover -s tests"""
import os
import sys
import tempfile
import unittest
from unittest import mock

from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import script                      # noqa: E402
from studio.render import make_video           # noqa: E402

SCRIPT = "CAST: A = dost\nSCENE: %s | Gali me\nHOOK: h\nCTA: c\nA (smile): hi | हाय\n"


class ImagePlaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = os.path.join(self.tmp.name, "assets", "backgrounds")
        os.makedirs(d)
        self.png = os.path.join(d, "gali.png")
        Image.new("RGB", (540, 960), (120, 40, 160)).save(self.png)
        self.patch = mock.patch.object(script, "asset_path", lambda p: p if os.path.isabs(p) else os.path.join(self.tmp.name, p))
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_name_of_a_file_in_assets_backgrounds(self):
        sc, warns = script.parse_script(SCRIPT % "gali")
        self.assertEqual(warns, [])
        self.assertEqual(sc["scenes"][0]["background"], {"type": "image", "path": "assets/backgrounds/gali.png"})

    def test_explicit_path(self):
        sc, warns = script.parse_script(SCRIPT % self.png)
        self.assertEqual(warns, [])
        self.assertEqual(sc["scenes"][0]["background"]["type"], "image")

    def test_builtin_names_still_win_and_unknown_ones_warn(self):
        sc, warns = script.parse_script(SCRIPT % "street")
        self.assertEqual(sc["scenes"][0]["background"], {"type": "street"})
        sc, warns = script.parse_script(SCRIPT % "nahi_hai")
        self.assertTrue(any("unknown place" in w for w in warns))
        self.assertEqual(sc["scenes"][0]["background"], {"type": "room"})
        sc, warns = script.parse_script(SCRIPT % "assets/backgrounds/missing.jpg")
        self.assertTrue(any("image nahi mili" in w for w in warns))

    def test_the_video_uses_the_picture(self):
        sc, _ = script.parse_script(SCRIPT % self.png)
        v = make_video(sc, 216, use_tts=False)
        r, g, b = v.frame(1.5).convert("RGB").getpixel((10, 10))     # (after the "Gali me" title card)
        self.assertTrue(abs(r - 120) < 12 and abs(b - 160) < 12, (r, g, b))


if __name__ == "__main__":
    unittest.main()

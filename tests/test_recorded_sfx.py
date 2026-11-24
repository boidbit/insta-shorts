"""Recorded CC0 sound effects (assets/sfx/*.ogg) play instead of the synthesized ones of the same name; the rest are
still made by the studio; SFX_RECORDED=0 brings the old ones back. python -m unittest"""
import os
import subprocess
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import audio                                  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
RECORDED = ("boing", "whoosh", "pop", "thud", "punch", "slap", "cash", "applause", "crowd_cheer", "glass_break",
            "thunder", "footsteps", "knock", "bat_hit")


class RecordedSfx(unittest.TestCase):
    def test_recorded_ones_play(self):
        for n in RECORDED:
            p = audio.sfx_path(n)
            self.assertTrue(p.endswith(os.path.join("assets", "sfx", n + ".ogg")), (n, p))
            self.assertLess(os.path.getsize(p), 80000, n)          # small (the whole set is ~250 KB)

    def test_the_others_are_still_made(self):
        self.assertTrue(audio.sfx_path("doorbell").endswith(".wav"))

    def test_the_old_sound_on_request(self):
        with mock.patch.dict(os.environ, {"SFX_RECORDED": "0"}):
            self.assertTrue(audio.sfx_path("boing").endswith(".wav"))

    def test_each_is_credited_cc0(self):
        with open(os.path.join(ROOT, "assets", "sfx", "CREDITS.md"), encoding="utf-8") as f:
            credits = f.read()
        self.assertIn("CC0 1.0", credits)
        for n in RECORDED:
            self.assertIn("| `%s` |" % n, credits)
        self.assertNotIn("CC-BY", credits)

    def test_they_decode(self):
        for n in ("boing", "footsteps", "applause"):
            r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                audio.sfx_path(n)], capture_output=True, text=True)
            self.assertGreater(float(r.stdout.strip()), 0.1, n)


if __name__ == "__main__":
    unittest.main()

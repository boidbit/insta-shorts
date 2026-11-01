"""Plain lyrics (no script format) -> one-singer song reel. python -m unittest discover -s tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio.render import make_video          # noqa: E402
from studio.scene import compile_scene        # noqa: E402
from studio.script import parse_script        # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
LYRICS = "Raat lambi hai\nChalta hu bina manzil ke | चलता हूँ बिना मंज़िल के\n\n// comment\nChaand bhi saath hai\n"


class LyricsModeTests(unittest.TestCase):
    def test_plain_lines_become_timed_lyrics(self):
        sc, warns = parse_script(LYRICS)
        lyr = [o for o in sc["overlays"] if o["style"] == "lyric"]
        self.assertEqual([o["text"] for o in lyr], ["Raat lambi hai", "Chalta hu bina manzil ke", "Chaand bhi saath hai"])
        self.assertTrue(all(a["to"] <= b["from"] + 1e-6 for a, b in zip(lyr, lyr[1:])))   # never overlap
        self.assertEqual(list(sc["characters"]), ["M"])                                    # one singer only
        self.assertEqual(warns, [])
        self.assertEqual(compile_scene(sc, use_tts=False).duration, sc["meta"]["duration"])

    def test_seconds_sets_the_length(self):
        sc, _ = parse_script("SECONDS: 60\n" + "\n".join("lyric %d" % i for i in range(17)))
        self.assertEqual(sc["meta"]["duration"], 60.0)
        lyr = [o for o in sc["overlays"] if o["style"] == "lyric"]
        self.assertEqual(len(lyr), 17)
        self.assertLessEqual(lyr[-1]["to"], 60.0)

    def test_optional_lines(self):
        sc, _ = parse_script("HOOK: Gaana 🎤\nMUSIC: none\nCTA: Tag karo\nCAPTION: cap\nline one\nline two")
        self.assertNotIn("music", sc)
        self.assertEqual({o["style"] for o in sc["overlays"]}, {"lyric", "hook", "card"})
        self.assertEqual(sc["post"]["caption"], "cap")
        sc, _ = parse_script("MUSIC: beat 90\nline one")
        self.assertEqual(sc["music"]["bpm"], 90)

    def test_too_fast_warns_and_bad_seconds_is_ignored(self):
        _, warns = parse_script("SECONDS: 6\n" + "\n".join("l%d" % i for i in range(10)))
        self.assertTrue(any("bahut tez" in w for w in warns))
        sc, warns = parse_script("SECONDS: abc\nline one")
        self.assertTrue(any("number nahi" in w for w in warns))
        self.assertGreater(sc["meta"]["duration"], 0)

    def test_structured_scripts_are_not_treated_as_lyrics(self):
        for text in ("CAST: A = dost\nA: namaste | नमस्ते", "A (laugh): ha ha | हा हा", "A -> jump",
                     "A = mummy\nA: hi", "SCENE: kitchen\nsome line"):
            sc, _ = parse_script(text)
            self.assertIn("scenes", sc, text)
        with open(os.path.join(ROOT, "scripts", "shaadi_dance.txt"), encoding="utf-8") as f:
            self.assertIn("scenes", parse_script(f.read())[0])

    def test_lyrics_video_renders(self):
        sc, _ = parse_script("SECONDS: 8\nline one\nline two\nline three")
        v = make_video(sc, 216, use_tts=False)
        self.assertEqual(v.n_frames, 8 * 30)
        self.assertEqual(v.frame(3.0).size, (216, 384))


if __name__ == "__main__":
    unittest.main()

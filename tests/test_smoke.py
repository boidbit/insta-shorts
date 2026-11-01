"""Fast checks (no network, no ffmpeg): every template/scene/script compiles and draws.

    python -m unittest discover -s tests -v
"""
import glob
import json
import os
import random
import tempfile
import unittest

from studio import director, hooks, script
from studio.characters import LOOKS, build_character, render_ops
from studio.render import make_video
from studio.scene import compile_scene, split_scenes
from studio.util import ROOT, load_scene


def scene_files():
    return sorted(glob.glob(os.path.join(ROOT, "templates", "*.json")) +
                  glob.glob(os.path.join(ROOT, "scenes", "*.json")))


class SceneTests(unittest.TestCase):
    def test_every_scene_compiles_and_draws(self):
        for path in scene_files():
            with self.subTest(os.path.basename(path)):
                scene = load_scene(path)
                for sub in split_scenes(scene):
                    plan = compile_scene(sub, use_tts=False)
                    self.assertGreater(plan.duration, 1.0)
                video = make_video(scene, 216, use_tts=False)
                for t in (0.1, video.duration / 2, video.duration - 0.1):
                    self.assertEqual(video.frame(t).size, (216, 384))

    def test_every_look_draws(self):
        for look in LOOKS:
            with self.subTest(look):
                ops, an = build_character({"look": look}, {}, "laugh", 0.5, 0.0, 540, 1700)
                self.assertTrue(render_ops(ops, 0.2, 216, 384))
                self.assertLess(an["head_top"][1], an["feet"][1])

    def test_multi_scene_timing(self):
        video = make_video(load_scene(os.path.join(ROOT, "scenes", "doodh_story_demo.json")), 216, use_tts=False)
        self.assertEqual(len(video.parts), 3)
        self.assertAlmostEqual(video.duration, sum(p.duration for p in video.parts), places=2)
        starts = [sp["start"] for sp in video.speech]
        self.assertEqual(starts, sorted(starts))
        self.assertGreater(starts[-1], video.offsets[2])


class ScriptTests(unittest.TestCase):
    def test_example_script_passes_director_checks(self):
        with open(os.path.join(ROOT, "scripts", "doodh_story.txt"), encoding="utf-8") as f:
            scene, warnings = script.parse_script(f.read())
        self.assertEqual(warnings, [])
        self.assertEqual(len(scene["scenes"]), 3)
        self.assertEqual(scene["characters"]["M"]["look"], "aunty")
        self.assertEqual(scene["characters"]["M"]["voice"]["name"], "hi-IN-SwaraNeural")
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(director.problems(scene, os.path.join(d, "x.json")), [])

    def test_roman_only_line_warns(self):
        scene, warnings = script.parse_script("HOOK: Test\nA (smile): Bhai chai pila de\n")
        self.assertTrue(any("Devanagari" in w for w in warnings))
        self.assertEqual(scene["scenes"][0]["timeline"][2]["speak"], "Bhai chai pila de")


class DirectorTests(unittest.TestCase):
    def test_retries_until_scene_is_clean(self):
        with open(os.path.join(ROOT, "scenes", "doodh_story_demo.json"), encoding="utf-8") as f:
            good = f.read()
        bad = json.loads(good)
        bad.pop("hook")
        bad["overlays"] = []
        replies = iter([json.dumps(bad), good])
        calls = []

        def fake_llm(system, messages):
            calls.append(messages)
            return next(replies)

        with tempfile.TemporaryDirectory() as d:
            scene = director.direct("mummy aur doodh", "cold_open", fake_llm, os.path.join(d, "c.json"),
                                    rng=random.Random(1), log=lambda m: None)
        self.assertEqual(len(calls), 2)
        self.assertIn("hook", calls[1][-1]["content"])
        self.assertEqual(scene["meta"]["hook_style"], "cold_open")

    def test_hook_pick(self):
        key, h = hooks.pick("auto", random.Random(3), avoid=list(hooks.HOOKS)[:-1])
        self.assertEqual(key, list(hooks.HOOKS)[-1])
        self.assertIn("how", h)


if __name__ == "__main__":
    unittest.main()

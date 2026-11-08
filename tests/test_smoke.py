"""Fast checks (no network, no ffmpeg): every template/scene/script compiles and draws.

    python -m unittest discover -s tests -v
"""
import glob
import io
import json
import os
import random
import re
import tempfile
import unittest
import urllib.error
from unittest import mock

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

    def test_every_action_draws_and_dances_follow_the_beat(self):
        from studio import actions
        self.assertTrue(actions.DANCES <= set(actions.ACTIONS))
        for name in actions.ACTIONS:
            for t in (0.0, 0.7, 2.5):
                with self.subTest(action=name, t=t):
                    pose = actions.pose_for(name, t, 1, 1, 0, {"_bpm": 110})
                    ops, _ = build_character({"look": "uncle"}, pose, "smile", 0.4, t, 540, 1700, prop="mic")
                    self.assertTrue(render_ops(ops, 0.2, 216, 384))
        slow = actions.pose_for("bhangra", 0.25, 1, 1, 0, {"_bpm": 60})
        fast = actions.pose_for("bhangra", 0.25, 1, 1, 0, {"_bpm": 120})
        self.assertNotEqual(round(slow["ra1"], 3), round(fast["ra1"], 3))

    def test_dance_line_is_held_long_enough_to_see(self):
        scene, warnings = script.parse_script("HOOK: x\nCAST: A = aunty\nA -> naagin sly\nCTA: y\n")
        self.assertEqual(warnings, [])
        ev = next(e for e in scene["scenes"][0]["timeline"] if e.get("who") == "A")
        self.assertEqual((ev["action"], ev["expression"], ev["hold"]), ("naagin", "sly", 1.6))

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

    def test_wrong_format_is_caught(self):
        bad = ("HOOK: Test\n"
               "CAST: A = college_boy poor [tshirt], B = college_girl rich [pink, saree, earrings]\n"
               "A (Aalu khareedne aaye ho?): Aalu khareedne aaye ho? | आलू खरीदने आए हो?\n"
               "A -> point | shock\n"
               "B -> wink | smile\n"
               "C (smile): Main kaun? | मैं कौन?\n"
               "CTA: Tag karo\n")
        scene, warnings = script.parse_script(bad)
        text = "\n".join(warnings)
        self.assertIn("'poor'", text)
        self.assertIn("'rich'", text)
        self.assertIn("brackets me dialogue", text)
        self.assertIn("'wink'", text)                      # two expressions on one line
        self.assertNotIn("'point'", text)                  # point + shock = action + face, fine
        self.assertIn("C CAST me nahi hai", text)
        self.assertEqual(scene["characters"]["A"]["outfit"], "tshirt")
        self.assertEqual(scene["characters"]["B"]["outfit"], "saree")
        self.assertIn("earrings", scene["characters"]["B"]["accessories"])

    def test_page_checker_uses_the_same_words(self):
        with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as f:
            page = f.read()
        m = re.search(r'<script type="application/json" id="vocab">(.*?)</script>', page, re.S)
        self.assertEqual(json.loads(m.group(1)), script.vocab(),
                         "index.html vocab is stale: paste json.dumps(studio.script.vocab()) into it")

    def test_roman_only_line_warns(self):
        scene, warnings = script.parse_script("HOOK: Test\nA (smile): Bhai chai pila de\n")
        self.assertTrue(any("Devanagari" in w for w in warnings))
        self.assertEqual(next(e for e in scene["scenes"][0]["timeline"] if "say" in e)["speak"], "Bhai chai pila de")


class DirectorTests(unittest.TestCase):
    def test_retries_until_scene_is_clean(self):
        with open(os.path.join(ROOT, "scenes", "doodh_story_demo.json"), encoding="utf-8") as f:
            good = f.read()
        bad = json.loads(good)
        bad.pop("hook")
        bad["overlays"] = []
        replies = iter([json.dumps(bad), good])
        calls = []

        def fake_llm(system, messages, json_mode=True):
            calls.append(messages)
            return next(replies)

        with tempfile.TemporaryDirectory() as d:
            scene = director.direct("mummy aur doodh", "cold_open", fake_llm, os.path.join(d, "c.json"),
                                    rng=random.Random(1), log=lambda m: None)
        self.assertEqual(len(calls), 2)
        self.assertIn("hook", calls[1][-1]["content"])
        self.assertEqual(scene["meta"]["hook_style"], "cold_open")

    def test_write_script_for_approval(self):
        with open(os.path.join(ROOT, "scripts", "dadi_phone.txt"), encoding="utf-8") as f:
            good = f.read()
        bad = good.replace(" | दादी, बस ये बटन दबाओ!", "")          # a line without Devanagari
        replies = iter(["```\n" + bad + "```", good])
        calls = []

        def fake_llm(system, messages, json_mode=True):
            calls.append(json_mode)
            return next(replies)

        with tempfile.TemporaryDirectory() as d:
            text = director.write_script("dadi aur phone", "pov", fake_llm, os.path.join(d, "c.json"),
                                         rng=random.Random(1), log=lambda m: None)
        self.assertEqual(calls, [False, False])
        self.assertTrue(text.startswith("HOOK:"))
        self.assertIn("दादी, बस ये बटन दबाओ!", text)

    def test_generic_key_is_routed_by_prefix(self):
        keep = {k: os.environ.pop(k, None) for k in ("AI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY",
                                                     "GOOGLE_API_KEY", "DIRECTOR_PROVIDER")}
        try:
            os.environ["AI_API_KEY"] = "AIzaFAKE"
            self.assertEqual(director.provider_name(), "gemini")
        finally:
            for k, v in keep.items():
                os.environ.pop(k, None)
                if v is not None:
                    os.environ[k] = v

    def test_gemini_busy_retries_then_next_model(self):
        tried, waits = [], []

        class Reply(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def fake_urlopen(req, timeout=None):
            model = req.full_url.split("/models/")[1].split(":")[0]
            tried.append(model)
            if model == "busy-model":
                raise urllib.error.HTTPError(req.full_url, 503, "busy", {}, io.BytesIO(b'{"error": "high demand"}'))
            return Reply(json.dumps({"candidates": [{"content": {"parts": [{"text": "HOOK: ok"}]}}]}).encode())

        llm = director.GeminiLLM(key="AIzaFAKE")
        llm.models = ["busy-model", "good-model"]
        with mock.patch.object(director.urllib.request, "urlopen", fake_urlopen), \
                mock.patch.object(director, "_sleep", waits.append):
            text = llm("sys", [{"role": "user", "content": "x"}], json_mode=False)
        self.assertEqual(text, "HOOK: ok")
        self.assertEqual(tried, ["busy-model"] * 3 + ["good-model"])
        self.assertEqual(waits, [10, 20])
        self.assertEqual(llm.models, ["good-model"])

    def test_hook_pick(self):
        key, h = hooks.pick("auto", random.Random(3), avoid=list(hooks.HOOKS)[:-1])
        self.assertEqual(key, list(hooks.HOOKS)[-1])
        self.assertIn("how", h)


if __name__ == "__main__":
    unittest.main()

"""ElevenLabs as a voice engine (Awaaz: ElevenLabs on the page, --tts elevenlabs), and the studio page layout
(script first and empty, GitHub as a small corner button). No network: the API is faked.
python -m unittest discover -s tests"""
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import audio, elevenlabs_tts, scene                # noqa: E402
from studio.script import parse_script                         # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
STORY = """HOOK: h
CAST: M = mummy, R = beta, K = bachcha
SCENE: kitchen
M (angry): Raju! | राजू!
R (smile): Haan mummy | हाँ मम्मी
K (laugh): Hi hi | ही ही
M (sad): Kya karun | क्या करूँ
CTA: c
"""


def read(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return f.read()


class FakeAPI:
    def __init__(self, fail=None):
        self.calls, self.fail = [], fail

    def __call__(self, url, key, body=None, timeout=120):
        if body is None:                                    # the voice list
            return json.dumps({"voices": [{"voice_id": "IND_F", "name": "Priya",
                                           "labels": {"accent": "indian", "gender": "female"}}]}).encode()
        if self.fail:
            raise elevenlabs_tts.ElevenLabsError(self.fail)
        self.calls.append((url, body))
        return b"ID3" + b"\0" * 4000


class ElevenTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"ELEVENLABS_API_KEY": "k"})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def items(self):
        sc, _ = parse_script(STORY)
        sub = scene.split_scenes(sc)[0]
        return scene.collect_lines(sub)

    def test_the_provider_names(self):
        for name in ("elevenlabs", "eleven", "11labs"):
            self.assertEqual(audio.resolve_provider(name), ("elevenlabs", True))
        self.assertEqual(audio.resolve_provider("free")[0], "edge")

    def test_every_character_keeps_its_own_voice(self):
        api = FakeAPI()
        with mock.patch.object(elevenlabs_tts, "_request", api), \
                mock.patch.object(elevenlabs_tts, "_kid_voice", lambda p, pitch: p):
            paths = elevenlabs_tts.synth_lines(self.items(), cache_dir=self.tmp.name)
        self.assertEqual(len(paths), 4)
        voice = [url.split("/")[-1].split("?")[0] for url, _b in api.calls]
        self.assertEqual(voice[0], "IND_F")                 # mummy: the account's Indian woman's voice first
        self.assertEqual(voice[0], voice[3])                # ... the same voice for her second line
        self.assertEqual(len({voice[0], voice[1], voice[2]}), 3)
        self.assertTrue(all(b["text"] for _u, b in api.calls))
        self.assertIn("राजू", api.calls[0][1]["text"])     # the Devanagari is what is spoken
        self.assertLess(api.calls[0][1]["voice_settings"]["stability"],     # angry line: more expressive
                        api.calls[3][1]["voice_settings"]["stability"])     # than the sad one

    def test_a_library_voice_the_free_plan_refuses_is_swapped_for_a_standard_one(self):
        class FreePlan(FakeAPI):
            def __call__(self, url, key, body=None, timeout=120):
                if body is not None and "IND_F" in url:
                    raise elevenlabs_tts.ElevenLabsError(
                        'HTTP 402 {"detail":{"code":"paid_plan_required","message":"Free users cannot use library voices"}}')
                return super().__call__(url, key, body, timeout)
        api = FreePlan()
        with mock.patch.object(elevenlabs_tts, "_request", api), \
                mock.patch.object(elevenlabs_tts, "_kid_voice", lambda p, pitch: p):
            paths = elevenlabs_tts.synth_lines(self.items(), cache_dir=self.tmp.name)
        self.assertEqual(len(paths), 4)
        voice = [url.split("/")[-1].split("?")[0] for url, _b in api.calls]
        self.assertNotIn("IND_F", voice)
        self.assertEqual(voice[0], elevenlabs_tts.FEMALE[0])       # mummy: the first standard woman's voice
        self.assertEqual(voice[0], voice[3])
        self.assertEqual(len({voice[0], voice[1], voice[2]}), 3)
        api.calls.clear()                                   # the next video does not ask for the refused voice
        items = [dict(it, text=it["text"] + " 2") for it in self.items()]
        with mock.patch.object(elevenlabs_tts, "_request", api), \
                mock.patch.object(elevenlabs_tts, "_kid_voice", lambda p, pitch: p):
            elevenlabs_tts.synth_lines(items, cache_dir=self.tmp.name)
        self.assertEqual(len(api.calls), 4)

    def test_a_second_render_costs_nothing(self):
        api = FakeAPI()
        with mock.patch.object(elevenlabs_tts, "_request", api), \
                mock.patch.object(elevenlabs_tts, "_kid_voice", lambda p, pitch: p):
            elevenlabs_tts.synth_lines(self.items(), cache_dir=self.tmp.name)
            n = len(api.calls)
            elevenlabs_tts.synth_lines(self.items(), cache_dir=self.tmp.name)
        self.assertEqual(len(api.calls), n)

    def test_a_failure_falls_back_and_the_video_is_still_made(self):
        sc, _ = parse_script(STORY)
        subs = scene.split_scenes(sc)
        with mock.patch.object(elevenlabs_tts, "_request", FakeAPI(fail="HTTP 401 invalid key")), \
                mock.patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": ""}):
            out = scene.prepare_voice(subs, True, "elevenlabs")
        self.assertTrue(out[0]["edge"])                     # free voice instead of stopping

    def test_it_feeds_the_scenes(self):
        sc, _ = parse_script(STORY)
        subs = scene.split_scenes(sc)
        with mock.patch.object(elevenlabs_tts, "_request", FakeAPI()), \
                mock.patch.object(elevenlabs_tts, "CACHE_DIR", self.tmp.name), \
                mock.patch.object(elevenlabs_tts, "_kid_voice", lambda p, pitch: p):
            out = scene.prepare_voice(subs, True, "elevenlabs")
        self.assertFalse(out[0]["edge"])
        self.assertEqual(len(out[0]["paths"]), 4)

    def test_no_key_is_an_error_not_a_crash(self):
        with mock.patch.dict(os.environ, {n: "" for n in elevenlabs_tts.KEY_NAMES}):
            with self.assertRaises(elevenlabs_tts.ElevenLabsError):
                elevenlabs_tts.synth_lines(self.items(), cache_dir=self.tmp.name)


class WorkflowAndPageTests(unittest.TestCase):
    def test_the_workflow_offers_it_and_finds_the_key(self):
        wf = read(".github/workflows/render.yml")
        self.assertIn("options: [auto, gemini, elevenlabs, edge]", wf)
        line = next(ln for ln in wf.splitlines() if ln.strip().startswith("ELEVENLABS_API_KEY: ${{"))
        for name in ("ELEVEN_LAB_1", "ELEVENLABS_API_KEY"):        # this repo's secret, and the usual name
            self.assertIn("secrets.%s " % name, line)

    def test_the_page_has_the_voice_choice_and_sends_it(self):
        page = read("index.html")
        self.assertIn('<option value="elevenlabs">ElevenLabs</option>', page)
        self.assertIn('tts: $("tts").value', page)

    def test_script_first_and_empty_github_in_a_corner(self):
        page = read("index.html")
        tabs = page[page.index('<div class="tabs"'):page.index("</div>", page.index('<div class="tabs"'))]
        self.assertLess(tabs.index('data-mode="script"'), tabs.index('data-mode="idea"'))
        self.assertIn('const drafts = { idea: "", script: "" };', page)
        self.assertIn('setMode("script");\ncheckConnection();', page)
        self.assertIn('<details class="gh setup" id="setup">', page)
        self.assertIn("@media (max-width: 640px)", page)


if __name__ == "__main__":
    unittest.main()

"""python -m unittest discover -s tests -v   (no network, no API key needed: the Gemini call is mocked)"""
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import audio, gemini_tts as g   # noqa: E402
from studio.scene import compile_scene      # noqa: E402

SR = g.SR


def fake_take(durations, gaps, intra_pause=0.14, seed=3, spans=None):
    """Fake 'speech': each line = syllable bursts with short intra-line pauses; lines separated by `gaps`.
    If `spans` is a list, the real (start, end) second of every line is appended to it."""
    rng = np.random.RandomState(seed)
    out = [np.zeros(int(0.2 * SR))]
    pos = 0.2
    for i, d in enumerate(durations):
        t, line = 0.0, []
        while t < d:
            syl = min(0.22, d - t)
            n = int(syl * SR)
            line.append(rng.randn(n) * 0.2 * np.hanning(n))
            t += syl
            if t < d:
                line.append(np.zeros(int(intra_pause * SR)))
                t += intra_pause
        out.append(np.concatenate(line))
        n_line = sum(len(seg) for seg in line)
        if spans is not None:
            spans.append((pos, pos + n_line / SR))
        pos += n_line / SR
        if i < len(durations) - 1:
            out.append(np.zeros(int(gaps[i] * SR)))
            pos += gaps[i]
    out.append(np.zeros(int(0.3 * SR)))
    return np.concatenate(out).astype(np.float32)


class SplitTests(unittest.TestCase):
    def test_splits_at_the_long_pauses(self):
        texts = ["a" * 40, "b" * 25, "c" * 55]
        real = []
        x = fake_take([2.8, 1.8, 3.8], [1.0, 0.8], spans=real)
        spans, method = g.split_audio(x, texts)
        self.assertEqual(method, "pauses")
        self.assertEqual(len(spans), 3)
        for (c0, c1), (r0, r1) in zip(spans, real):
            # every clip fully contains its line (minus float noise) and stays well inside the gaps
            self.assertLessEqual(c0, r0 + 0.01)
            self.assertGreaterEqual(c1, r1 - 0.12)      # (hann-window tails are inaudible)
            self.assertLess(r0 - c0, 0.2)
            self.assertLess(c1 - r1, 0.2)
        for (a0, a1), (b0, b1) in zip(spans, spans[1:]):
            self.assertLessEqual(a1, b0 + 0.13)      # clips don't overlap (only the small padding)

    def test_short_gaps_between_lines(self):
        # gaps barely longer than the pauses inside lines still split correctly
        texts = ["a" * 30, "b" * 30, "c" * 30]
        x = fake_take([2.0, 2.0, 2.0], [0.45, 0.45], intra_pause=0.14)
        spans, _ = g.split_audio(x, texts)
        self.assertEqual(len(spans), 3)
        self.assertTrue(all(b > a for a, b in spans))

    def test_single_line(self):
        spans, method = g.split_audio(fake_take([2.0], []), ["hello"])
        self.assertEqual((len(spans), method), (1, "pauses"))

    def test_silence_is_an_error(self):
        with self.assertRaises(g.GeminiTTSError):
            g.split_audio(np.zeros(SR, dtype=np.float32), ["x", "y"])


class PayloadTests(unittest.TestCase):
    def test_one_voice_is_single_speaker(self):
        p = g.build_payload([{"voice": "Puck", "text": "ek"}, {"voice": "Puck", "text": "do"}])
        sc = p["generationConfig"]["speechConfig"]
        self.assertEqual(sc["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"], "Puck")
        self.assertIn("ek\n\ndo", p["contents"][0]["parts"][0]["text"])

    def test_two_voices_is_multi_speaker(self):
        p = g.build_payload([{"voice": "Kore", "text": "ek"}, {"voice": "Puck", "text": "do"}])
        cfgs = p["generationConfig"]["speechConfig"]["multiSpeakerVoiceConfig"]["speakerVoiceConfigs"]
        self.assertEqual([c["speaker"] for c in cfgs], ["Speaker1", "Speaker2"])
        self.assertIn("Speaker2: do", p["contents"][0]["parts"][0]["text"])

    def test_three_voices_rejected(self):
        with self.assertRaises(ValueError):
            g.build_payload([{"voice": v, "text": "x"} for v in ("Kore", "Puck", "Fenrir")])

    def test_voice_mapping_and_pitch(self):
        self.assertEqual(g.voice_for({"name": "hi-IN-SwaraNeural"}), "Kore")
        self.assertEqual(g.voice_for({"name": "hi-IN-MadhurNeural"}), "Puck")
        self.assertEqual(g.voice_for({"name": "hi-IN-MadhurNeural", "gemini": "Fenrir"}), "Fenrir")
        self.assertGreater(g.semitones("+22Hz"), 0)
        self.assertLess(g.semitones("-6Hz"), 0)
        self.assertAlmostEqual(g.rate_factor("+8%"), 1.08)


class SceneTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cwd = os.getcwd()
        os.chdir(self.tmp)                      # synth_script caches under ./.cache/tts
        self.scene = {
            "characters": {"A": {"voice": {"name": "hi-IN-SwaraNeural"}},
                           "B": {"voice": {"name": "hi-IN-MadhurNeural", "pitch": "+22Hz"}},
                           "C": {"voice": {"name": "hi-IN-MadhurNeural", "pitch": "-6Hz"}}},
            "timeline": [
                {"t": 0.0, "who": "A", "say": "one", "speak": "पहली लाइन है ये"},
                {"who": "B", "say": "two", "speak": "दूसरी लाइन थोड़ी लंबी है भाई"},
                {"who": "C", "say": "three", "speak": "तीसरी"},
                {"who": "C", "say": "muted", "speak": "ye nahi bolna", "tts": False},
            ]}
        self.calls = []

        def fake_request(payload, model=g.DEFAULT_MODEL, **kw):
            self.calls.append(payload)
            return fake_take([2.2, 3.0, 0.9], [1.0, 1.0])

        self.patch = mock.patch.object(g, "request_audio", fake_request)
        self.patch.start()
        self.env = mock.patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
        self.env.start()

    def tearDown(self):
        self.patch.stop()
        self.env.stop()
        os.chdir(self.cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_whole_script_is_one_request_and_every_line_gets_its_own_clip(self):
        plan = compile_scene(self.scene)
        self.assertEqual(len(self.calls), 1)
        voiced = [s for s in plan.speech if s["audio"]]
        self.assertEqual(len(voiced), 3)
        self.assertEqual(len({s["audio"] for s in voiced}), 3)
        self.assertIsNone(plan.speech[3]["audio"])                      # "tts": false line stays silent
        self.assertEqual(len(self.calls[0]["generationConfig"]["speechConfig"]
                             ["multiSpeakerVoiceConfig"]["speakerVoiceConfigs"]), 2)
        # lines come out in order, one after another
        starts = [s["start"] for s in plan.speech]
        self.assertEqual(starts, sorted(starts))

    def test_second_compile_uses_the_cache(self):
        compile_scene(self.scene)
        compile_scene(self.scene)
        self.assertEqual(len(self.calls), 1)

    def test_auto_mode_falls_back_to_edge_when_gemini_fails(self):
        with mock.patch.object(g, "request_audio", side_effect=g.QuotaExceeded("daily")), \
                mock.patch.object(audio, "synth_tts", return_value=None) as edge:
            plan = compile_scene(self.scene)                            # provider=auto (key is set)
        self.assertEqual(edge.call_count, 3)
        self.assertTrue(all(s["audio"] is None for s in plan.speech))

    def test_explicit_gemini_fails_loudly(self):
        with mock.patch.object(g, "request_audio", side_effect=g.QuotaExceeded("daily")):
            with self.assertRaises(SystemExit):
                compile_scene(self.scene, tts_provider="gemini")

    def test_no_key_means_edge(self):
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": ""}), \
                mock.patch.object(audio, "synth_tts", return_value=None) as edge:
            compile_scene(self.scene)
        self.assertEqual(self.calls, [])
        self.assertEqual(edge.call_count, 3)


if __name__ == "__main__":
    unittest.main()

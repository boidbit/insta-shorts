"""The same voice for the same character: a recurring character's voice description (hulia) and a rule to keep every
speaker's voice the same go to Gemini, a lower temperature, a long line said in pieces (its voice does not drift)
and joined into one clip again, and a third voice (a narrator) in a request of its own, never another one's voice.
python -m unittest"""
import os
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import gemini_tts as G                        # noqa: E402

LONG = ("भाई नंबर मत देख, क्वालिटी देख! मेरे पास भीड़ नहीं है, मेरे पास एक कोर कल्ट कम्युनिटी है... ऐसे लोग जो मेरे "
        "एक इशारे पे जान दे दें! अब देख हिसाब—बीस तो मेरी ख़ुद की बैकअप और फ़ैन-पेज आईडीज़ हैं, ग्यारह मम्मी के किटी "
        "ग्रुप वाली आंटियाँ हैं जिनको अनफ़ॉलो का बटन नहीं मिलता, पंद्रह फ़ॉरेन बॉट्स हैं... और भाई एक है मेरा सबसे "
        "लॉयल, सबसे असली फ़ैन!")


def fake_take(payload, model=None):
    """A take like Gemini's: each line a tone as long as its text, a second of silence between the lines."""
    text = payload["contents"][0]["parts"][0]["text"]
    body = text.split("\n\n")[1:]
    out = []
    for ln in body:
        n = len(ln.split(":", 1)[-1])
        t = np.arange(int(G.SR * max(0.4, n / 14.0))) / G.SR
        out += [0.5 * np.sin(2 * np.pi * 180 * t).astype(np.float32), np.zeros(G.SR, np.float32)]
    return np.concatenate([np.zeros(G.SR // 4, np.float32)] + out)


class SameVoice(unittest.TestCase):
    def setUp(self):
        self.calls = []

        def req(payload, model=None):
            self.calls.append(payload)
            return fake_take(payload)
        self.p = mock.patch.object(G, "request_audio", side_effect=req)
        self.p.start()
        self.cache = tempfile.mkdtemp()

    def tearDown(self):
        self.p.stop()

    def items(self):
        hul = "a young man of about twenty-two: light, bright tenor"
        return [dict(text="तो बताइए रीलेश जी...", voice="Algieba", spec={"andaaz": "a podcast host", "hulia": "a man around thirty"}),
                dict(text=LONG, voice="Sadachbia", spec={"andaaz": "an excited vlogger", "hulia": hul}),
                dict(text="बने रहिए", voice="Charon", spec={})]

    def test_a_long_line_goes_whole(self):
        """(Pieces are off: Gemini says one speaker's pieces without a pause, the take is cut in the wrong places
        and every later line gets another line's voice.)"""
        self.assertIsNone(G.PIECE_MAX)
        self.assertEqual(G.pieces(LONG), [" ".join(LONG.split())])
        paths = G.synth_script(self.items()[:2], cache_dir=self.cache)
        body = self.calls[0]["contents"][0]["parts"][0]["text"].split("\n\n")[1:]
        self.assertEqual(len(body), 2)                                    # one line, one paragraph
        self.assertEqual(len(paths), 2)
        x, _ = G.read_wav(paths[1])
        self.assertGreater(len(x) / G.SR, len(LONG) / 14.0 * 0.8)

    def test_pieces_still_join_when_asked(self):
        self.assertGreater(len(G.pieces(LONG, limit=200)), 1)             # (kept for later, with its own splitting)

    def test_the_voice_rule_the_hulia_and_a_lower_temperature(self):
        G.synth_script(self.items()[:2], cache_dir=self.cache)
        pl = self.calls[0]
        text = pl["contents"][0]["parts"][0]["text"]
        self.assertIn(G.SAME_VOICE, text)
        self.assertIn("always with the voice of a young man of about twenty-two", text)
        self.assertEqual(pl["generationConfig"]["temperature"], G.TEMPERATURE)

    def test_a_third_voice_has_its_own_request(self):
        paths = G.synth_script(self.items(), cache_dir=self.cache)
        self.assertEqual(len(self.calls), 2)
        voices = [[c["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"]
                   for c in p["generationConfig"]["speechConfig"].get("multiSpeakerVoiceConfig", {}).get(
                       "speakerVoiceConfigs", [{"voiceConfig": p["generationConfig"]["speechConfig"].get("voiceConfig")}])]
                  for p in self.calls]
        self.assertEqual(voices, [["Algieba", "Sadachbia"], ["Charon"]])  # the narrator in its own voice
        self.assertEqual(len(paths), 3)

    def test_kirdaar_have_a_hulia(self):
        import json
        for k in ("sultan", "paglet", "daddu", "reelesh", "gappu"):
            with open(os.path.join(os.path.dirname(__file__), "..", "kirdaar", k + ".json"), encoding="utf-8") as f:
                self.assertTrue(json.load(f)["awaaz"].get("hulia"), k)


if __name__ == "__main__":
    unittest.main()


class SteadyLoudness(unittest.TestCase):
    """Gemini once said the first half-minute of a take very softly: one gain for the take left those lines near
    silent in the reel. Each line is levelled, and steady inside a long line."""

    def speech(self, amp, secs):
        t = np.arange(int(G.SR * secs)) / G.SR
        return (amp * np.sin(2 * np.pi * 160 * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 3 * t))).astype(np.float32)

    def rms(self, x):
        return float(np.sqrt((x ** 2).mean()))

    def test_a_soft_line_is_lifted(self):
        y = G.level(self.speech(0.01, 4.0))
        self.assertGreater(self.rms(y), 0.07)
        self.assertLessEqual(float(np.abs(y).max()), 0.98)

    def test_soft_then_loud_inside_one_line(self):
        x = np.concatenate([self.speech(0.02, 6.0), self.speech(0.3, 6.0)])     # 15x softer, then loud
        y = G.level(x)
        a, b = self.rms(y[G.SR: 5 * G.SR]), self.rms(y[7 * G.SR: 11 * G.SR])
        self.assertGreater(a / b, 0.6)                                   # was 1:15

    def test_pauses_are_not_pumped_up(self):
        x = np.concatenate([self.speech(0.2, 2.0), np.random.RandomState(1).randn(G.SR * 2).astype(np.float32) * 1e-4,
                            self.speech(0.2, 2.0)])
        y = G.level(x)
        self.assertLess(self.rms(y[int(2.6 * G.SR): int(3.4 * G.SR)]), 0.01)

    def test_lines_are_levelled_when_cut(self):
        G_calls = []
        with mock.patch.object(G, "request_audio", side_effect=lambda p, m=None: G_calls.append(p) or
                               np.concatenate([np.zeros(G.SR // 4, np.float32), self.speech(0.01, 3.0),
                                               np.zeros(G.SR, np.float32), self.speech(0.4, 3.0),
                                               np.zeros(G.SR, np.float32)])):
            paths = G.synth_script([dict(text="पहली लाइन धीरे से", voice="Algieba", spec={}),
                                    dict(text="दूसरी लाइन ज़ोर से", voice="Sadachbia", spec={})],
                                   cache_dir=tempfile.mkdtemp())
        a, b = (self.rms(G.read_wav(p)[0]) for p in paths)
        self.assertGreater(a / b, 0.6)

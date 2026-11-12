"""Sound mode: a viral sound as a reel's voice (SOUND line, @times, lines timed to the sound, mouths from it, the sound
in the video), the web page's sound (unpacked from the run's event), and the script made from what Gemini hears.

    python -m unittest tests.test_sound
"""
import base64
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
import wave
from unittest import mock

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import sound                                    # noqa: E402
from studio.script import parse_script, parse_sound, sound_time   # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
HAVE_FFMPEG = bool(shutil.which("ffmpeg"))

# 4 "lines" (a buzzing voice-like sound) with pauses between them; line 3 has a pause inside it ("Galti se? ...")
TRUTH = [0.6, 3.1, 5.4, 8.2]
SHAPE = [(0.6, 2.4), (3.1, 4.9), (5.4, 6.2), (6.55, 7.6), (8.2, 9.6)]     # (line 3 = two parts)
LENGTH = 10.2


def voice_wav(path, sr=16000):
    t = np.arange(int(LENGTH * sr)) / sr
    x = 0.004 * np.sin(2 * np.pi * 220 * t)                          # a soft music bed under it
    rng = np.random.default_rng(1)
    for a, b in SHAPE:
        m = (t >= a) & (t < b)
        syl = 0.6 + 0.4 * np.abs(np.sin(2 * np.pi * 3.0 * (t[m] - a)))
        x[m] += 0.3 * syl * (np.sin(2 * np.pi * 180 * t[m]) + 0.3 * rng.standard_normal(m.sum()))
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return path


SCRIPT = """HOOK: POV: report card wala din 😭
SOUND: {src}
CAST: M = mummy, B = beta
SCENE: living_room
M (angry, point{a0}): Ye kya hai? Ye report card hai ya mazaak?
B (nervous{a1}): Mummy, wo teacher ne galti se kam number de diye.
M (shock{a2}): Galti se? Paanch subjects me?
B (sly{a3}): Haan mummy, unki galti ki aadat hai.
M -> facepalm
CTA_STYLE: caption
CTA: Tag karo 👇
"""


def script(src, ats=(None, None, None, None)):
    kw = {"a%d" % i: (", @%s" % a if a is not None else "") for i, a in enumerate(ats)}
    return SCRIPT.format(src=src, **kw)


class Script(unittest.TestCase):
    def test_sound_line_and_times(self):
        self.assertEqual(sound_time("@1.8"), 1.8)
        self.assertEqual(sound_time("@0:03.2"), 3.2)
        self.assertEqual(sound_time("@1:05"), 65.0)
        self.assertIsNone(sound_time("1.8"))
        self.assertEqual(parse_sound("sound-ab12 0:05-0:20")[0], {"src": "sound-ab12", "start": 5.0, "end": 20.0})
        self.assertEqual(parse_sound("assets/x.mp3")[0], {"src": "assets/x.mp3", "start": 0.0, "end": None})
        self.assertTrue(parse_sound("sound-x 5-x")[1])

    def test_one_place_one_take_no_studio_voice(self):
        sc, warns = parse_script(script("sound-ab12", (0.5, 3.0, 5.3, 8.1)) + "CUT ots\nSCENE: kitchen\nLOOP: on\n"
                                 "B (cry, @9.5): Arre!\n")
        self.assertEqual(len(sc["scenes"]), 1)                        # CUT / a 2nd SCENE do not split the sound
        self.assertEqual(sc["sound"], {"src": "sound-ab12", "start": 0.0, "end": None})
        self.assertNotIn("music", sc)                                 # the sound is the music
        says = [e for e in sc["scenes"][0]["timeline"] if "say" in e]
        self.assertEqual([e["sound_at"] for e in says], [0.5, 3.0, 5.3, 8.1, 9.5])
        self.assertTrue(all(e["tts"] is False for e in says))
        self.assertFalse([w for w in warns if "Devanagari" in w])     # the sound speaks: no Devanagari needed
        self.assertEqual(len([w for w in warns if w.startswith("SOUND ke saath")]), 3)
        self.assertFalse(sc.get("loop"))

    def test_scripts_without_a_sound_are_unchanged(self):
        sc, _ = parse_script("HOOK: h\nCAST: A = boy\nSCENE: room\nA (shock, @1.2): Arre!\nCTA: c\n")
        self.assertNotIn("sound", sc)
        ev = next(e for e in sc["scenes"][0]["timeline"] if "say" in e)
        self.assertEqual(ev["sound_at"], 1.2)                          # (harmless without a SOUND)
        self.assertNotIn("tts", ev)


@unittest.skipUnless(HAVE_FFMPEG, "needs ffmpeg")
class Timing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.wav = voice_wav(os.path.join(cls.tmp.name, "viral.wav"))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def starts(self, ats):
        sc = sound.prepare(parse_script(script(self.wav, ats))[0])
        return [e for e in sc["scenes"][0]["timeline"] if "say" in e], sc

    def test_written_times_land_on_the_voice(self):
        for ats in ((0.6, 3.1, 5.4, 8.2), (0.3, 3.4, 5.1, 8.5), (0.9, 2.8, 5.7, 7.9)):     # off by up to 0.3 s
            says, _ = self.starts(ats)
            for e, truth in zip(says, TRUTH):
                self.assertAlmostEqual(e["t"], truth, delta=0.08, msg=(ats, [x["t"] for x in says]))

    def test_the_sound_is_the_voice(self):
        says, sc = self.starts((0.6, 3.1, 5.4, 8.2))
        for e in says:
            self.assertFalse(e["tts"])
            self.assertTrue(os.path.isfile(e["lip_src"]))
            self.assertGreater(e["duration"], 0.5)
        self.assertAlmostEqual(sc["_sound"]["duration"], LENGTH, delta=0.05)
        self.assertNotIn("music", sc)
        self.assertGreaterEqual(max(e.get("t", 0) for e in sc["scenes"][0]["timeline"]), LENGTH - 0.05)

    def test_a_part_of_the_sound(self):
        sc = sound.prepare(parse_script(script(self.wav, (0.1, 2.6, 4.9, 7.7)).replace(
            "SOUND: %s" % self.wav, "SOUND: %s 0:00.5-0:10" % self.wav))[0])
        says = [e for e in sc["scenes"][0]["timeline"] if "say" in e]
        self.assertAlmostEqual(sc["_sound"]["duration"], 9.5, delta=0.05)
        for e, truth in zip(says, TRUTH):
            self.assertAlmostEqual(e["t"], truth - 0.5, delta=0.08)

    def test_a_missing_sound_says_so(self):
        with self.assertRaises(SystemExit) as cm:
            sound.prepare(parse_script(script("sound-nahihai"))[0])
        self.assertIn("nahi mili", str(cm.exception))

    def test_the_video_has_the_sound_in_it(self):
        from studio.render import make_video
        v = make_video(parse_script(script(self.wav, (0.6, 3.1, 5.4, 8.2)))[0], 120)
        self.assertTrue(v.sound and os.path.isfile(v.sound["path"]))
        self.assertIn(v.sound["path"], v.ffmpeg_cmd("x.mp4"))
        v.with_sound = False
        self.assertNotIn(v.sound["path"], v.ffmpeg_cmd("x.mp4"))
        self.assertFalse([sp for sp in v.speech if sp.get("audio")])                         # no studio voice
        part = v.parts[0]
        sp = part.plan.speech[0]
        talking = [part._lip_open(sp, sp["start"] + 0.1 + k * 0.05) for k in range(20)]
        quiet = [part._lip_open(sp, 2.6 + k * 0.05) for k in range(6)]                       # the pause after line 1
        self.assertGreater(max(talking), 0.6)
        self.assertLess(max(quiet), 0.15)


class Page(unittest.TestCase):
    def test_unpack_the_pages_sound(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(sound, "SOUND_DIR", d):
            ev = os.path.join(d, "event.json")
            with open(ev, "w") as f:
                json.dump({"inputs": {"sound": "sound-abc123;ogg;" + base64.b64encode(b"OggS-test").decode()}}, f)
            path = sound.unpack(ev)
            self.assertEqual(os.path.basename(path), "sound-abc123.ogg")
            with open(path, "rb") as f:
                self.assertEqual(f.read(), b"OggS-test")
            with open(ev, "w") as f:
                json.dump({"inputs": {"sound": "../../etc;ogg;AAAA"}}, f)
            with self.assertRaises(SystemExit):
                sound.unpack(ev)
            with open(ev, "w") as f:
                json.dump({"inputs": {}}, f)
            self.assertIsNone(sound.unpack(ev))

    def test_the_workflow_listens_and_brings_the_sound_back(self):
        with open(os.path.join(ROOT, ".github", "workflows", "render.yml"), encoding="utf-8") as f:
            flow = f.read()
        self.assertIn("options: [video, script, sound, sound_video]", flow)
        self.assertIn("--no-ideas -o scenes/generated/web_script.txt", flow)        # straight to the video
        self.assertIn('echo "<!-- script -->"', flow)                                # the reel brings its script back
        self.assertIn("      sound:\n", flow)
        self.assertIn('python -m studio.sound draft --event "$GITHUB_EVENT_PATH"', flow)
        self.assertIn('python -m studio.sound unpack --event "$GITHUB_EVENT_PATH"', flow)
        self.assertNotIn("inputs.sound }}", flow)                     # never through an env variable (the log)
        with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as f:
            page = f.read()
        self.assertIn('id="sndFile"', page)
        self.assertIn('data-mode="sound"', page)                                    # its own tab
        self.assertIn('start(review ? "sound" : "sound_video"', page)
        self.assertIn('split("<!-- script -->")', page)
        self.assertIn("JSON.stringify(inputs).length > 64000", page)


INFO = {"kind": "dialogue", "meme": "Jab galti pakdi jaaye",
        "speakers": [{"id": "S1", "gender": "female", "age": "adult", "role": "mummy"},
                     {"id": "S2", "gender": "male", "age": "young", "role": "superhero"},
                     {"id": "S3", "gender": "male", "age": "old", "role": ""},
                     {"id": "S4", "gender": "female", "age": "kid", "role": "kid_girl"}],
        "lines": [{"start": 0.5, "speaker": "S1", "roman": "Ye kya hai?", "feeling": "gussa", "action": "point"},
                  {"start": 1.8, "speaker": "S2", "roman": "Mummy | wo...", "feeling": "dancing", "action": "fly_away"},
                  {"start": "x", "speaker": "S3", "roman": "Hmm.", "feeling": "think"},
                  {"start": 4.0, "speaker": "S4", "roman": "Main bhi!", "feeling": "excited"}],
        "place": "spaceship",
        "ideas": [{"hook": "POV: report card 😭", "situation": "ghar", "place": "living_room",
                   "roles": {"S1": "mummy", "S2": "beta"}, "caption": "Har ghar 😂"},
                  {"hook": "Boss 💀", "situation": "office"}]}


class Draft(unittest.TestCase):
    def test_what_gemini_heard_becomes_a_clean_script(self):
        text, notes = sound.draft(INFO, "sound-abc123")
        self.assertIn("SOUND: sound-abc123", text)
        self.assertIn("CAST: A = mummy, B = beta, C = dada", text)    # idea roles, else voice -> a look; max 3
        self.assertIn("SCENE: living_room", text)                    # the idea's place (Gemini's own was unknown)
        self.assertIn("A (point, angry, @0.5): Ye kya hai?", text)   # gussa -> angry
        self.assertIn("B (@1.8): Mummy / wo...", text)              # unknown words out, no `|` in the line
        self.assertIn("C (think): Hmm.", text)                        # no time: found from the sound later
        self.assertIn("CTA_STYLE: caption", text)                     # the reel ends with the sound
        self.assertIn("1. POV: report card 😭: ghar", notes)
        _, warns = parse_script(text)
        self.assertEqual(warns, [])

    def test_the_voice_s_emotion_becomes_acting(self):
        info = json.loads(json.dumps(INFO))
        info["lines"][0]["extras"] = ["shake", "boing", "fireworks_party"]
        info["lines"][3]["extras"] = "close"
        text, _ = sound.draft(info, "sound-abc123")
        self.assertIn("A (point, angry, shake, boing, @0.5): Ye kya hai?", text)
        self.assertIn("(excited, close, @4.0): Main bhi!", text)
        self.assertEqual(parse_script(text)[1], [])

    def test_only_music_makes_them_dance(self):
        text, _ = sound.draft({"kind": "music", "speakers": [], "lines": []}, "sound-abc123")
        self.assertIn("A -> dance excited", text)
        self.assertEqual(parse_script(text)[1], [])

    def test_gemini_hears_the_file(self):
        seen = {}

        def fake(system, messages, json_mode=True):
            seen["parts"] = messages[0]["content"]
            return json.dumps(INFO)
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            f.write(b"OggS")
        try:
            info = sound.analyze(f.name, "office", llm=fake)
        finally:
            os.unlink(f.name)
        self.assertEqual(info["place"], "spaceship")
        self.assertEqual(seen["parts"][0]["inline_data"]["mime_type"], "audio/ogg")
        self.assertEqual(seen["parts"][0]["inline_data"]["data"], base64.b64encode(b"OggS").decode())
        ask = seen["parts"][1]["text"]
        for must in ("ROLES:", "PLACES:", "FEELINGS:", "EXTRAS:", "the user wants: office", '"start"', "Do not translate",
                     '"shake" when the voice shouts'):
            self.assertIn(must, ask)

    def test_the_gemini_client_sends_audio_parts(self):
        from studio.director import GeminiLLM
        llm = GeminiLLM(model="m", key="k")
        sent = {}

        class R(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def fake_open(req, timeout=None):
            sent["body"] = json.loads(req.data)
            return R(json.dumps({"candidates": [{"content": {"parts": [{"text": "{}"}]}}]}).encode())
        with mock.patch("urllib.request.urlopen", fake_open):
            llm("sys", [{"role": "user", "content": [{"inline_data": {"mime_type": "audio/ogg", "data": "AA"}},
                                                     {"text": "listen"}]}])
            self.assertEqual(sent["body"]["contents"][0]["parts"][0]["inline_data"]["data"], "AA")
            llm("sys", [{"role": "user", "content": "plain text"}])
            self.assertEqual(sent["body"]["contents"][0]["parts"], [{"text": "plain text"}])


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class Checker(unittest.TestCase):
    def test_the_page_checker_and_builder_know_sound_mode(self):
        from tests.test_cards import run_js
        text, _ = sound.draft(INFO, "sound-abc123")
        out = run_js("""
const m = scriptToCards(DATA);
console.log(JSON.stringify({ lint: lintScript(DATA), back: cardsToScript(m) === DATA,
  setting: m.items.some((it) => it.k === "raw" && it.text.startsWith("SOUND:") && isSetting(it)),
  bad: lintScript("HOOK: h\\nSOUND: sound-x 5-x\\nCAST: A = boy\\nA: hi\\n") }));""", text)
        self.assertEqual(out["lint"], [])
        self.assertTrue(out["back"])
        self.assertTrue(out["setting"])
        self.assertTrue(any("0:05-0:20" in w for w in out["bad"]))


if __name__ == "__main__":
    unittest.main()

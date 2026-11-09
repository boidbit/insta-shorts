"""python -m unittest discover -s tests -v   (no network, no API key: the Gemini call is mocked)"""
import base64
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
import urllib.error
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import gemini_music as gm, script   # noqa: E402
from studio.render import make_video             # noqa: E402

MP3 = b"ID3\x03\x00\x00\x00\x00\x00\x00" + bytes(range(256)) * 12        # >2000 bytes, starts like an mp3
WAV = b"RIFF\x24\x00\x00\x00WAVEfmt " + bytes(range(256)) * 12
LYRICS = ("HOOK: Mummy ka gussa\nCAPTION: Full gaana\nMUSIC: gemini bollywood item song, dhol\n[Verse]\n"
          "Mummy naraaz hui | मम्मी नाराज़ हुई\nSink bhar gaya beta | सिंक भर गया बेटा\n[Chorus]\n"
          "Ab main bhaaga re | अब मैं भागा रे\nBartan dho de | बर्तन धो दे\n")


def answer(data, texts=("[Verse 1] ...",)):
    steps = [{"type": "model_output", "content": [{"type": "text", "text": t} for t in texts]
              + [{"type": "audio", "data": base64.b64encode(data).decode()}]}]
    return json.dumps({"steps": steps}).encode()


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def http_error(code, message):
    body = json.dumps({"error": {"message": message}}).encode()
    return urllib.error.HTTPError(gm.ENDPOINT, code, "x", {}, io.BytesIO(body))


class PromptTests(unittest.TestCase):
    def test_lyrics_prompt_keeps_direction_and_lyrics_apart(self):
        p = gm.build_prompt("dhol and female vocals", ["Line one", "Line two"])
        head, _, body = p.partition("\n\n")
        self.assertIn("dhol and female vocals", head)
        self.assertIn("Hindi", head)
        self.assertEqual(body.splitlines(), ["[Verse]", "Line one", "Line two"])

    def test_own_section_tags_are_kept(self):
        p = gm.build_prompt("pop", ["[Chorus]", "La la", "[Verse]", "Na na"])
        self.assertNotIn("[Verse]\n[Chorus]", p)
        self.assertTrue(p.split("\n\n", 1)[1].startswith("[Chorus]"))

    def test_instrumental_prompt(self):
        self.assertIn("Instrumental only, no vocals.", gm.build_prompt("lofi"))
        self.assertIn(gm.DEFAULT_STYLE, gm.build_prompt(""))

    def test_music_spec_words(self):
        a = gm.music_spec("gemini qawwali with tabla")
        self.assertEqual((a["model"], a["style"], a["vocals"]), (gm.CLIP_MODEL, "qawwali with tabla", False))
        b = gm.music_spec("GEMINI full  sad ghazal", ["x"])
        self.assertEqual((b["model"], b["style"], b["vocals"]), (gm.FULL_MODEL, "sad ghazal", True))
        self.assertEqual(gm.music_spec("gemini")["style"], gm.DEFAULT_STYLE)
        self.assertEqual(b["fallback"]["type"], "beat")


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)

    def test_extract_audio(self):
        data, texts = gm.extract_audio(json.loads(answer(MP3, ("[Verse] a", "b"))))
        self.assertEqual(data, MP3)
        self.assertEqual(texts, ["[Verse] a", "b"])
        with self.assertRaises(gm.MusicError):
            gm.extract_audio({"steps": [{"type": "model_output", "content": [{"type": "text", "text": "no"}]}]})
        with self.assertRaises(gm.MusicError):
            gm.extract_audio({"error": "x"})

    def test_request_shape_and_cache(self):
        with mock.patch("urllib.request.urlopen", return_value=FakeResponse(answer(MP3))) as up:
            p = gm.song_path("Create a song", gm.CLIP_MODEL, cache_dir=self.dir, key="K")
            req = up.call_args[0][0]
            self.assertEqual(req.full_url, gm.ENDPOINT)
            self.assertEqual(req.get_header("X-goog-api-key"), "K")
            self.assertEqual(req.get_header("Api-revision"), gm.API_REVISION)
            self.assertEqual(json.loads(req.data), {"model": gm.CLIP_MODEL, "input": "Create a song"})
            self.assertTrue(p.endswith(".mp3") and open(p, "rb").read() == MP3)
            again = gm.song_path("Create a song", gm.CLIP_MODEL, cache_dir=self.dir, key="K")
            self.assertEqual(again, p)
            self.assertEqual(up.call_count, 1)                      # the second time comes from the cache

    def test_wav_is_recognised(self):
        with mock.patch("urllib.request.urlopen", return_value=FakeResponse(answer(WAV))):
            self.assertTrue(gm.song_path("p", gm.FULL_MODEL, cache_dir=self.dir, key="K").endswith(".wav"))

    def test_no_key(self):
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": ""}):
            with self.assertRaises(gm.MusicUnavailable):
                gm.song_path("p", gm.CLIP_MODEL, cache_dir=self.dir)

    def test_no_access_is_not_retried(self):
        with mock.patch("urllib.request.urlopen", side_effect=http_error(403, "free tier")) as up:
            with self.assertRaises(gm.MusicUnavailable) as cm:
                gm.song_path("p", gm.CLIP_MODEL, cache_dir=self.dir, key="K")
            self.assertIn("403", str(cm.exception))
            self.assertEqual(up.call_count, 1)

    def test_server_error_is_retried(self):
        with mock.patch("time.sleep"), mock.patch("urllib.request.urlopen",
                                                   side_effect=[http_error(503, "busy"), FakeResponse(answer(MP3))]):
            self.assertTrue(os.path.isfile(gm.song_path("p", gm.CLIP_MODEL, cache_dir=self.dir, key="K")))

    def test_too_short_audio_is_refused(self):
        with mock.patch("urllib.request.urlopen", return_value=FakeResponse(answer(b"ID3tiny"))):
            with self.assertRaises(gm.MusicError):
                gm.song_path("p", gm.CLIP_MODEL, cache_dir=self.dir, key="K")
        self.assertEqual(os.listdir(self.dir), [])


class ScriptTests(unittest.TestCase):
    def test_lyrics_script_asks_for_a_sung_song(self):
        sc, warnings = script.parse_script(LYRICS)
        self.assertEqual(warnings, [])
        m = sc["music"]
        self.assertEqual((m["type"], m["model"], m["vocals"]), ("gemini", gm.CLIP_MODEL, True))
        body = m["prompt"].split("\n\n", 1)[1].splitlines()
        self.assertEqual(body, ["[Verse]", "मम्मी नाराज़ हुई", "सिंक भर गया बेटा", "[Chorus]", "अब मैं भागा रे", "बर्तन धो दे"])
        shown = [o["text"] for o in sc["overlays"] if o["style"] == "lyric"]
        self.assertEqual(shown, ["Mummy naraaz hui", "Sink bhar gaya beta", "Ab main bhaaga re", "Bartan dho de"])

    def test_seconds_is_explained(self):
        _sc, warnings = script.parse_script(LYRICS + "SECONDS: 20\n")
        self.assertTrue(any("SECONDS" in w for w in warnings))

    def test_story_script_gets_instrumental_music(self):
        sc, _w = script.parse_script("HOOK: x\nCAST: A = boy\nSCENE: kitchen\nMUSIC: gemini full qawwali\nA: Hi | हाय\n")
        m = sc["music"]
        self.assertEqual((m["model"], m["style"], m["vocals"]), (gm.FULL_MODEL, "qawwali", False))
        self.assertIn("seed", m["fallback"])
        self.assertIn("Instrumental only", m["prompt"])

    def test_other_music_lines_are_unchanged(self):
        sc, _w = script.parse_script("HOOK: x\nCAST: A = boy\nSCENE: kitchen\nMUSIC: sad\nA: Hi | हाय\n")
        self.assertEqual(sc["music"]["type"], "beat")
        self.assertEqual(sc["music"]["style"], "sad")


class PrepareTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.song = os.path.join(self.dir, "song.mp3")
        with open(self.song, "wb") as f:
            f.write(MP3)

    def scene(self):
        return script.parse_script(LYRICS)[0]

    def test_other_scenes_pass_through(self):
        sc = {"music": {"type": "beat", "bpm": 90}}
        self.assertIs(gm.prepare(sc), sc)
        empty = {}
        self.assertIs(gm.prepare(empty), empty)

    def test_preview_never_calls_the_network(self):
        with mock.patch.object(gm, "song_path", side_effect=AssertionError("network")):
            out = gm.prepare(self.scene(), use_tts=False)
        self.assertEqual(out["music"]["type"], "beat")

    def test_failure_falls_back_to_the_beat(self):
        with mock.patch.object(gm, "song_path", side_effect=gm.MusicUnavailable("HTTP 403 free tier")):
            out = gm.prepare(self.scene())
        self.assertEqual(out["music"], self.scene()["music"]["fallback"])
        self.assertEqual(out["meta"]["duration"], self.scene()["meta"]["duration"])      # timing as before

    def test_song_retimes_the_lyrics_reel(self):
        with mock.patch.object(gm, "song_path", return_value=self.song), \
                mock.patch.object(gm.audio, "audio_duration", return_value=24.0):
            out = gm.prepare(self.scene())
        self.assertEqual(out["music"]["path"], self.song)
        self.assertEqual(out["meta"]["duration"], 24.0)
        lyric = [o for o in out["overlays"] if o["style"] == "lyric"]
        self.assertEqual(len(lyric), 4)
        self.assertAlmostEqual(lyric[-1]["to"], 0.3 + 4 * (23.0 / 4) - 0.1, places=1)    # spread over the song
        self.assertEqual(out["post"]["caption"], "Full gaana")
        self.assertEqual(out["hook"], "Mummy ka gussa")

    def test_cut_off_song_is_dropped(self):
        with mock.patch.object(gm, "song_path", return_value=self.song), \
                mock.patch.object(gm.audio, "audio_duration", return_value=1.5):
            out = gm.prepare(self.scene())
        self.assertEqual(out["music"]["type"], "beat")
        self.assertFalse(os.path.exists(self.song))

    def test_story_scene_keeps_its_timing(self):
        sc, _w = script.parse_script("HOOK: x\nCAST: A = boy\nSCENE: kitchen\nMUSIC: gemini lofi\nA: Hi | हाय\n")
        with mock.patch.object(gm, "song_path", return_value=self.song), \
                mock.patch.object(gm.audio, "audio_duration", return_value=30.0):
            out = gm.prepare(sc)
        self.assertEqual(out["music"], {"path": self.song, "volume": 0.3})
        self.assertEqual(out["scenes"], sc["scenes"])

    def test_make_video_without_voice_uses_the_beat(self):
        v = make_video(self.scene(), 120, use_tts=False)
        self.assertTrue(v.music["generated"])


class PageTests(unittest.TestCase):
    def test_page_checker_accepts_the_gemini_music_line(self):
        with open(os.path.join(os.path.dirname(__file__), "..", "index.html"), encoding="utf-8") as f:
            page = f.read()
        self.assertIn('first !== "gemini"', page)


if __name__ == "__main__":
    unittest.main()

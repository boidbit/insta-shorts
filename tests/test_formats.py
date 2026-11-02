"""Narration (voice-over + subtitles) and chat-screen scenes. python -m unittest discover -s tests"""
import os
import sys
import unittest

from PIL import ImageChops

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio.render import make_video                 # noqa: E402
from studio.scene import compile_scene, split_scenes, chat_length   # noqa: E402
from studio.script import parse_script               # noqa: E402

NARRATED = """HOOK: h
CAST: A = dost, B = aunty
SCENE: street
NARRATOR: Ek din ki baat hai | एक दिन की बात है
A (shock): Kya?! | क्या?!
B (smile): Haan! | हाँ!
NARRATOR (laugh): Phir kya hua | फिर क्या हुआ
CTA: c
"""
CHAT = """HOOK: h
SCENE: plain | Message 📱
CHAT: Mummy ❤️
CHAT left: Beta khana kha liya?
CHAT right: Haan mummy 😅 | हाँ मम्मी
CHAT left: Jhooth mat bol
CTA: Tag karo
"""


class NarrationTests(unittest.TestCase):
    def test_narrator_is_a_voice_with_no_body(self):
        sc, warns = parse_script(NARRATED)
        self.assertEqual(warns, [])
        self.assertTrue(sc["characters"]["NARRATOR"]["hidden"])
        p = compile_scene(split_scenes(sc)[0], use_tts=False)
        n = p.chars["NARRATOR"]
        self.assertTrue(n.spec["hidden"])
        # the two visible characters still get the two-person layout (the narrator takes no slot)
        self.assertEqual((p.chars["A"].x, p.chars["B"].x), (300.0, 780.0))
        subs = [o for o in p.overlays if o.get("style") == "subtitle"]
        self.assertEqual([o["text"] for o in subs], ["Ek din ki baat hai", "Phir kya hua"])
        self.assertTrue(all(o["to"] > o["from"] for o in subs))
        vo = [sp for sp in p.speech if sp["who"] == "NARRATOR"]
        self.assertEqual(len(vo), 2)
        self.assertFalse(vo[0]["bubble"])
        self.assertEqual(n.voice["gemini"], "Charon")

    def test_camera_ignores_the_narrator(self):
        p = compile_scene(split_scenes(parse_script(NARRATED)[0])[0], use_tts=False)
        narrator_lines = [sp for sp in p.speech if sp["who"] == "NARRATOR"]
        for seg in p.cam_segments:
            self.assertTrue(any(abs(seg[0] - sp["start"]) < 0.2 for sp in narrator_lines) is False
                            or seg[3] == 1.0)

    def test_narrator_is_not_drawn_and_aliases_work(self):
        sc, _ = parse_script(NARRATED.replace("NARRATOR", "VO"))
        self.assertIn("NARRATOR", sc["characters"])
        v = make_video(sc, 216, use_tts=False)
        self.assertEqual(v.frame(0.5).size, (216, 384))

    def test_gemini_batch_gives_the_narrator_its_own_voice(self):
        from studio.scene import collect_lines
        sub = split_scenes(parse_script(NARRATED)[0])[0]
        voices = [it["voice"] for it in collect_lines(sub)]
        self.assertEqual(voices[0], "Charon")


class ChatTests(unittest.TestCase):
    def test_parse(self):
        sc, warns = parse_script(CHAT)
        self.assertEqual(warns, [])
        chat = sc["scenes"][0]["chat"]
        self.assertEqual(chat["title"], "Mummy ❤️")
        self.assertEqual([(m["side"], m["text"]) for m in chat["messages"]],
                         [("left", "Beta khana kha liya?"), ("right", "Haan mummy 😅"), ("left", "Jhooth mat bol")])
        self.assertEqual(sc["scenes"][0]["cast"], [])               # no characters in a chat scene

    def test_messages_are_timed_and_have_a_pop(self):
        sub = split_scenes(parse_script(CHAT)[0])[0]
        self.assertEqual(sub["characters"], {})                    # shared cast is not dragged in
        p = compile_scene(sub, use_tts=False)
        ts = [m["t"] for m in sub["chat"]["messages"]]
        self.assertEqual(ts, [0.6, 2.1, 3.6])
        pops = sorted(round(fx["t"], 2) for fx in p.sfx if round(fx["t"], 2) in ts)
        self.assertEqual(pops, ts)                                  # one pop at every message
        self.assertAlmostEqual(p.duration, chat_length(3) + 2.0 + 0.9, delta=0.6)     # + CTA hold + tail

    def test_chat_grows_and_cta_comes_last_and_visible(self):
        v = make_video(parse_script(CHAT)[0], 216, use_tts=False)
        f0, f1, f2 = (v.frame(t).convert("RGB") for t in (0.3, 2.5, 4.5))
        self.assertIsNotNone(ImageChops.difference(f1, f2).getbbox())            # third message appeared
        end = v.frame(v.duration - 0.5).convert("RGB")
        self.assertIsNotNone(ImageChops.difference(f2, end).getbbox())           # CTA card now on screen
        self.assertEqual(f0.size, (216, 384))

    def test_old_messages_scroll_away_when_the_panel_is_full(self):
        from studio.text import chat_image
        many = {"title": "x", "messages": [{"side": "left" if i % 2 else "right", "text": "message number %d" % i}
                                           for i in range(40)]}
        im = chat_image(many, 40, 0.3)
        self.assertLessEqual(im.height, 1200 * 0.3)

    def test_bad_chat_lines_warn(self):
        _, warns = parse_script("HOOK: h\nSCENE: plain\nCHAT left:\nCHAT right: ok\nCTA: c\n")
        self.assertTrue(any("khali" in w for w in warns))


if __name__ == "__main__":
    unittest.main()

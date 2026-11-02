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
CHAT: Mummy ❤️
< Beta khana kha liya?
> Haan mummy 😅 | हाँ मम्मी
< Jhooth mat bol
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
    """Chat is its own tiny format (lines starting with < or >), not a part of the story format."""

    def test_parse(self):
        sc, warns = parse_script(CHAT)
        self.assertEqual(warns, [])
        self.assertEqual(sc["characters"], {})                         # no characters
        self.assertNotIn("scenes", sc)
        chat = sc["chat"]
        self.assertEqual(chat["title"], "Mummy ❤️")
        self.assertEqual([(m["side"], m["text"]) for m in chat["messages"]],
                         [("left", "Beta khana kha liya?"), ("right", "Haan mummy 😅"), ("left", "Jhooth mat bol")])

    def test_old_spelling_still_works_inside_a_chat(self):
        sc, _ = parse_script("CHAT: x\nCHAT left: hi\nCHAT right: hello\n")
        self.assertEqual([m["side"] for m in sc["chat"]["messages"]], ["left", "right"])

    def test_typing_gap_before_the_other_persons_messages_and_two_sounds(self):
        p = compile_scene(parse_script(CHAT)[0], use_tts=False)
        ts = [m["t"] for m in p.overlays[0]["chat"]["messages"]]
        self.assertEqual(ts, [1.5, 3.0, 5.4])                          # +0.9 s "typing..." only before left messages
        by_t = {round(fx["t"], 2): fx for fx in p.sfx}
        self.assertNotEqual(by_t[1.5]["path"], by_t[3.0]["path"])        # incoming ding vs sent pop
        self.assertEqual(by_t[1.5]["path"], by_t[5.4]["path"])

    def test_length_matches_chat_length_and_cta_comes_last(self):
        sc, _ = parse_script(CHAT)
        p = compile_scene(sc, use_tts=False)
        self.assertAlmostEqual(p.duration, chat_length(3, sc["chat"]) + 2.0 + 0.6, delta=0.1)
        cta = [o for o in p.overlays if o.get("style") == "card"][0]
        self.assertGreaterEqual(cta["from"], chat_length(3, sc["chat"]) - 0.01)

    def test_typing_dots_then_message_then_growth(self):
        v = make_video(parse_script(CHAT)[0], 216, use_tts=False)
        f = {t: v.frame(t).convert("RGB") for t in (0.3, 1.0, 1.7, 3.2, 6.0)}
        for a, b in ((0.3, 1.0), (1.0, 1.7), (1.7, 3.2), (3.2, 6.0)):
            self.assertIsNotNone(ImageChops.difference(f[a], f[b]).getbbox(), (a, b))
        end = v.frame(v.duration - 0.4).convert("RGB")
        self.assertIsNotNone(ImageChops.difference(f[6.0], end).getbbox())      # CTA card shown at the end

    def test_chat_lines_in_a_story_script_are_rejected_with_a_warning(self):
        sc, warns = parse_script("HOOK: h\nCAST: A = dost\nSCENE: street\nA (smile): hi | हाय\n"
                                 "CHAT: Mummy\n< hello\n> hi\nCTA: c\n")
        self.assertIn("scenes", sc)
        self.assertNotIn("chat", sc["scenes"][0])
        self.assertEqual(sum("chat alag format" in w for w in warns), 3)

    def test_other_formats_are_not_mistaken_for_chat(self):
        sc, _ = parse_script("Raat lambi hai\nChalta hu\n")                  # lyrics
        self.assertNotIn("chat", sc)
        sc, _ = parse_script("< hello\nthis line is not a chat line\n")        # a stray line: not a chat
        self.assertNotIn("chat", sc)

    def test_old_messages_scroll_away_when_the_panel_is_full(self):
        from studio.text import chat_image
        many = {"title": "x", "messages": [{"side": "left" if i % 2 else "right", "text": "message number %d" % i}
                                           for i in range(40)]}
        im = chat_image(many, 40, 0.3)
        self.assertLessEqual(im.height, 1200 * 0.3)

    def test_empty_message_warns(self):
        _, warns = parse_script("CHAT: x\n< \n> ok\n")
        self.assertTrue(any("khali" in w for w in warns))


if __name__ == "__main__":
    unittest.main()

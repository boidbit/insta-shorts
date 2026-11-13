"""LOOP mode (the reel runs round without a seam), the hidden mascot (easter egg), the short copy prompt and the plain
feeling words the script reader understands. python -m unittest discover -s tests"""
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

from PIL import ImageChops, ImageStat

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import director, script                          # noqa: E402
from studio.render import Looped, make_video, mascot_sprite  # noqa: E402
from studio.scene import apply_loop                           # noqa: E402
from studio.script import parse_script                        # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
STORY = """HOOK: Mummy ka "bas 5 minute" 😭
CAST: M = mummy, R = beta
SCENE: kitchen
M (angry, point): Raju, bas 5 minute me khana lag raha hai! | राजू, बस 5 मिनट में खाना लग रहा है!
R (smile): Theek hai mummy, ek game aur | ठीक है मम्मी, एक गेम और
M (shock): Teen ghante ho gaye! | तीन घंटे हो गए!
R (think): To khana kab lagega? | तो खाना कब लगेगा?
M (angry): Bas 5 minute! | बस 5 मिनट!
CTA: Har ghar ki kahani 😂 Tag karo
"""


def diff(a, b):
    return sum(ImageStat.Stat(ImageChops.difference(a.convert("RGB"), b.convert("RGB"))).mean) / 3


class LoopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sc, cls.warns = parse_script(STORY + "LOOP: on\n")
        cls.v = make_video(cls.sc, 216, use_tts=False)

    def test_the_script_line_turns_it_on(self):
        self.assertEqual(self.warns, [])
        self.assertTrue(self.sc["loop"])
        self.assertIsInstance(self.v, Looped)
        _sc, warns = parse_script(STORY + "LOOP: kabhi\n")
        self.assertTrue(any("LOOP" in w for w in warns))

    def test_no_end_card_the_cta_goes_to_the_caption(self):
        def ctas(sc):
            return [ev for s in sc["scenes"] for ev in s["timeline"] if (ev.get("overlay") or {}).get("cta")]
        plain, _ = parse_script(STORY)
        self.assertTrue(ctas(plain))
        self.assertEqual(ctas(self.sc), [])
        self.assertIn("Tag karo", self.sc["post"]["caption"])
        self.assertLess(self.v.duration, make_video(plain, 216, use_tts=False).duration)   # no 2 s card at the end

    def test_the_last_frame_is_the_first_frame(self):
        v = self.v
        last = v.frame((v.n_frames - 1) / v.fps)
        self.assertLess(diff(last, v.frame(0.0)), 0.5)
        mid = v.frame(v.duration - 0.16)                           # (and it really whips across)
        self.assertGreater(diff(mid, v.frame(0.0)), 5.0)

    def test_the_music_dips_at_the_loop_point(self):
        cmd = " ".join(self.v.ffmpeg_cmd("x.mp4"))
        self.assertIn("afade=t=out", cmd)
        plain, _ = parse_script(STORY)
        self.assertNotIn("afade=t=out", " ".join(make_video(plain, 216, use_tts=False).ffmpeg_cmd("x.mp4")))

    def test_the_command_line_switch_and_twice_is_the_same(self):
        plain, _ = parse_script(STORY)
        v = make_video(plain, 216, use_tts=False, loop=True)
        self.assertIsInstance(v, Looped)
        once = apply_loop(plain)
        self.assertEqual(apply_loop(once)["post"], once["post"])


class MascotTests(unittest.TestCase):
    def make(self, kind, loop=False):
        sc, warns = parse_script(STORY + "MASCOT: %s\n" % kind + ("LOOP: on\n" if loop else ""))
        self.assertEqual(warns, [])
        v = make_video(sc, 216, use_tts=False)
        return v, [m for p in v.parts for m in p.mascots]

    def test_it_peeks_out_in_the_middle_of_the_story(self):
        for kind in ("bhoot", "billi", "chooha"):
            v, ms = self.make(kind)
            self.assertEqual(len(ms), 1, kind)
            m = ms[0]
            speech = [sp for p in v.parts for sp in p.plan.speech]
            self.assertNotIn(m["t0"] - 0.25, (speech[0]["start"], speech[-1]["start"]))   # not the first / punch line
            p = v.parts[0]
            # the peek really changes the picture
            with_m = p.frame((m["t0"] + m["t1"]) / 2)
            saved, p.mascots = p.mascots, []
            without = p.frame((m["t0"] + m["t1"]) / 2)
            p.mascots = saved
            self.assertGreater(diff(with_m, without), 0.05, kind)

    def test_same_video_same_place_and_loop_adds_an_end_peek(self):
        _v, a = self.make("bhoot")
        _v, b = self.make("bhoot")
        self.assertEqual(a, b)
        v, ms = self.make("billi", loop=True)
        self.assertEqual(len(ms), 2)
        self.assertGreater(ms[1]["t0"], v.parts[-1].plan.duration - 1.5)

    def test_off_and_unknown(self):
        sc, warns = parse_script(STORY + "MASCOT: off\n")
        self.assertEqual(warns, [])
        self.assertNotIn("mascot", sc)
        _sc, warns = parse_script(STORY + "MASCOT: dinosaur\n")
        self.assertTrue(any("MASCOT" in w for w in warns))
        sc, _ = parse_script(STORY + "MASCOT: bhoot\n")
        v = make_video(sc, 216, use_tts=False, mascot="off")
        self.assertEqual([m for p in v.parts for m in p.mascots], [])

    def test_the_sprites(self):
        for kind in ("bhoot", "billi", "chooha"):
            im = mascot_sprite(kind, 30.0, 1, False)
            self.assertEqual(im.mode, "RGBA")
            self.assertIsNotNone(im.getchannel("A").getbbox())


def read(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return f.read()


class PromptTests(unittest.TestCase):
    TEXT = read("SCRIPT_PROMPT.md")

    def test_the_short_prompt_is_much_shorter(self):
        core = director.prompt_text(self.TEXT, keep=())
        full = director.prompt_text(self.TEXT)
        self.assertLess(len(core), 22500)        # the writer craft + two example scripts + the Nov 2026 people, faces, places
        self.assertLess(len(core), 0.8 * len(full))
        self.assertNotIn("<!--", core + full)
        for must in ("HOOK:", "Story facts first", "ALREADY in their place", "- ONE expression:"):
            self.assertIn(must, core)

    def test_the_studio_writer_gets_every_module_but_loop(self):
        full = director.prompt_text(self.TEXT)
        for must in ("Dark comedy craft", "ride bike", "NOTIFY:", "SCENE: <place> pan", "naagin", "slowmo"):
            self.assertIn(must, full)
        self.assertNotIn("# Loop", full)
        self.assertIn("# Loop", director.prompt_text(self.TEXT, keep=("loop",)))

    def test_every_module_is_closed(self):
        opens = re.findall(r"<!-- module: (\w+) -->", self.TEXT)
        self.assertEqual(len(opens), self.TEXT.count("<!-- /module -->"))
        with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as f:
            page = f.read()
        for name in set(opens) - {"loop"}:
            self.assertIn("%s: {" % name, page)                     # the page knows when to add it


class FeelWordTests(unittest.TestCase):
    def test_gussa_means_an_angry_face_too(self):
        sc, warns = parse_script("HOOK: h\nCAST: A = boy\nSCENE: room\nA (gussa): Hi | हाय\nB (gussa, smile): Hi | हाय\n"
                                 "CTA: c\n")
        ev = [e for e in sc["scenes"][0]["timeline"] if e.get("who") in ("A", "B")]
        self.assertEqual((ev[0]["expression"], ev[0]["fx"]), ("angry", ["anger"]))
        self.assertEqual(ev[1]["expression"], "smile")             # a face the writer chose wins

    def test_plain_words_act(self):
        sc, warns = parse_script("HOOK: h\nCAST: A = boy, B = girl\nSCENE: room\nA (happy, pointing): Dekho! | देखो!\n"
                                 "B (worried): Kya? | क्या?\nA -> running scared\nCTA: c\n")
        self.assertEqual(warns, [])
        ev = [(e.get("action"), e.get("expression")) for e in sc["scenes"][0]["timeline"] if e.get("who") in ("A", "B")]
        self.assertEqual(ev, [("point", "smile"), (None, "nervous"), ("run", "scared")])

    def test_they_never_hide_a_real_word(self):
        v = script.vocab()
        known = {w for k, val in v.items() if k not in ("feel_words", "role_looks") and isinstance(val, list)
                 for w in val if isinstance(w, str)}
        self.assertEqual([k for k in script.FEEL_WORDS if k in known], [])
        self.assertEqual([w for w in script.FEEL_WORDS.values() if w not in known], [])


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class PageTests(unittest.TestCase):
    PAGE = read("index.html")

    def js(self, expr):
        vocab = re.search(r'id="vocab">(.*?)</script>', self.PAGE, re.S).group(1)
        start, at = self.PAGE.index("const V = "), self.PAGE.index("function lintScript")
        code = "const $ = (id) => ({ textContent: %s });\n%s\n" % (
            json.dumps(vocab), self.PAGE[start:self.PAGE.index("\nfunction ", at + 10)])
        out = subprocess.run(["node", "-e", code + "console.log(JSON.stringify(%s));" % expr],
                             capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)

    def test_the_checker_accepts_loop_mascot_and_plain_words(self):
        text = STORY.replace("(smile)", "(happy)") + "LOOP: on\nMASCOT: billi\n"
        self.assertEqual(self.js("lintScript(%s)" % json.dumps(text)), [])
        self.assertTrue(self.js("lintScript(%s)" % json.dumps(STORY + "MASCOT: dinosaur\n")))

    def test_the_page_has_the_options(self):
        for needle in ('id="loop"', 'id="mascot"', 'id="fullPrompt"', "function withVideoOptions", "function trimPrompt"):
            self.assertIn(needle, self.PAGE)


if __name__ == "__main__":
    unittest.main()

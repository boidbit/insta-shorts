"""cine: tight pacing, people turned to each other while they talk, the feeling in the whole body.
CAMERA: classic keeps the old timing, front view and plain idle. python -m unittest discover -s tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import actions, scene                              # noqa: E402
from studio.render import make_video                           # noqa: E402
from studio.script import parse_script                         # noqa: E402

TWO = ("HOOK: h\nMYSTERY: off\n%sCAST: A = uncle, B = aunty\nSCENE: room\n"
       "A: Chai bani? | चाय बनी?\nB (angry): Khud bana lo! | ख़ुद बना लो!\nA (sad): Theek hai. | ठीक है।\n")


def video(classic=False, text=TWO):
    sc, w = parse_script(text % ("CAMERA: classic\n" if classic else ""))
    assert w == [], w
    return make_video(sc, 160, use_tts=False, hook="off")


class Pacing(unittest.TestCase):
    def test_the_next_line_comes_right_after(self):
        cine, classic = video(), video(True)
        for v, gap in ((cine, scene.TIGHT_GAP), (classic, 0.3)):
            sp = v.parts[-1].plan.speech
            punch = v is cine and len(sp) >= 3          # cine: a breath of silence before the punch line
            for i, (a, b) in enumerate(zip(sp, sp[1:])):
                beat = scene.PUNCH_BEAT if punch and i == len(sp) - 2 else 0.0
                self.assertAlmostEqual(b["start"] - a["end"], gap - 0.12 + beat, delta=0.02)
        self.assertLess(cine.duration, classic.duration)


class Turned(unittest.TestCase):
    def test_two_people_talk_turned_to_each_other(self):
        p = video().parts[-1]
        for name in ("A", "B"):
            self.assertEqual(p.plan.chars[name].state_at(1.0)["view"], "side")
        p = video(True).parts[-1]
        self.assertIsNone(p.plan.chars["A"].state_at(1.0)["view"])

    def test_alone_or_turned_by_the_script(self):
        p = video(text="HOOK: h\nMYSTERY: off\n%sCAST: A = uncle\nSCENE: room\nA: Haan. | हाँ।\n").parts[-1]
        self.assertIsNone(p.plan.chars["A"].state_at(0.5)["view"])
        p = video(text=TWO.replace("SCENE: room\n", "SCENE: room\nA -> saamne\n")).parts[-1]
        self.assertNotEqual(p.plan.chars["A"].state_at(1.0)["view"], "side")

    def test_a_dance_faces_us(self):
        from studio.render import Renderer
        self.assertIn("dance", Renderer.FRONT_ACTIONS)
        self.assertNotIn("talk", Renderer.FRONT_ACTIONS)


class Mood(unittest.TestCase):
    def test_the_feeling_changes_the_body(self):
        base = actions.pose_for("idle", 1.0)
        for expr in ("angry", "sad", "scared", "proud", "nervous"):
            m = actions.mood_pose(base, expr, 1.0, 0.0, 1.0)
            self.assertNotEqual(round(m["ra1"], 1), round(base["ra1"], 1), expr)
        self.assertGreater(actions.mood_pose(base, "sad", 1.0, 0.0, 1.0)["head_dy"], 5)     # slumped
        self.assertIs(actions.mood_pose(base, "smile", 1.0, 0.0, 1.0), base)                # no mood: as it was

    def test_it_comes_in_gently(self):
        p = video().parts[-1]
        b = p.plan.chars["B"]
        t0 = next(e["t"] for e in b.events if e.get("expression") == "angry")
        poses = [p._build_pose(b, t0 + d, p._eff(b, t0 + d))["la1"] for d in (0.0, 0.1, 0.2, 0.4)]
        steps = [abs(y - x) for x, y in zip(poses, poses[1:])]
        self.assertLess(max(steps), 40)                     # eased in over MOOD_IN, no jump

    def test_classic_keeps_the_plain_idle(self):
        p = video(True).parts[-1]
        b = p.plan.chars["B"]
        t = next(e["t"] for e in b.events if e.get("expression") == "angry") + 0.6
        self.assertNotEqual(p._eff(b, t)["action"], None)
        pose = p._build_pose(b, t, p._eff(b, t))
        mood = actions.mood_pose(pose, "angry", t, b.phase, 1.0)
        self.assertNotEqual(round(pose["la1"], 1), round(mood["la1"], 1))


if __name__ == "__main__":
    unittest.main()


class CloseUp(unittest.TestCase):
    def test_a_close_up_faces_us_a_two_shot_does_not(self):
        p = video().parts[-1]
        segs = p.plan.cam_segments
        close = [s for s in segs if len(s) > 7 and s[6] and s[3] >= p.CLOSE_ZOOM]
        self.assertTrue(close)
        s = close[0]
        c = p.plan.chars[s[6]]
        self.assertTrue(p._close_on(c, (s[0] + s[1]) / 2))
        other = next(o for o in p.plan.chars.values() if o is not c)
        self.assertFalse(p._close_on(other, (s[0] + s[1]) / 2))


class WriterCut(unittest.TestCase):
    def test_cut_close_and_two_shot_are_kept_whole(self):
        from studio import scene as S
        sc, w = parse_script("HOOK: h\nMYSTERY: off\nCAST: A = uncle, B = aunty\nSCENE: room\nA: Pehle. | पहले।\n"
                             "CUT close B\nB: Close. | क्लोज़।\nA: Haan. | हाँ।\nCUT A\nA: Ab main. | अब मैं।\n"
                             "CUT two_shot\nB: Dono. | दोनों।\nA: Haan. | हाँ।\n")
        self.assertEqual(w, [])
        v = make_video(sc, 120, use_tts=False, hook="off")
        close_b, close_a, two = v.parts[1].plan, v.parts[2].plan, v.parts[3].plan
        for pl, who in ((close_b, "B"), (close_a, "A")):
            zs = [S.camera_at(pl, t)[0] for t in (0.3, pl.duration / 2, pl.duration - 0.1)]
            self.assertTrue(all(z >= 1.65 for z in zs), zs)                    # close all through
            self.assertEqual(pl.cam_segments[0][6], who)
        zs = [S.camera_at(two, t)[0] for t in (0.3, two.duration - 0.1)]
        self.assertTrue(all(z < 1.45 for z in zs), zs)                         # never one face alone

    def test_unknown_cut_words_still_warn(self):
        _sc, w = parse_script("HOOK: h\nCAST: A = uncle\nSCENE: room\nCUT sideways\nA: Haan. | हाँ।\n")
        self.assertTrue(any("CUT" in x for x in w))


class Subtitles(unittest.TestCase):
    def test_short_subtitles_by_default_in_cine(self):
        p = video().parts[-1]
        subs = [o for o in p.plan.overlays if o.get("style") == "subline"]
        self.assertTrue(subs)
        self.assertTrue(all(len(o["text"]) <= scene.SUB_CHARS + 6 for o in subs))
        self.assertFalse(any(sp["bubble"] for sp in p.plan.speech))           # no bubbles
        q = video(True).parts[-1]                                              # classic: bubbles, as before
        self.assertTrue(all(sp["bubble"] for sp in q.plan.speech))
        self.assertFalse([o for o in q.plan.overlays if o.get("style") in ("subline", "subtitle")])

    def test_the_pieces_follow_the_line(self):
        pieces = scene.subtitle_chunks("Tau, sheher mein sab kuch online milta hai!", 1.0, 3.0, 3.1)
        self.assertEqual(" ".join(p for p, _, _ in pieces), "Tau, sheher mein sab kuch online milta hai!")
        self.assertEqual(pieces[0][1], 1.0)
        self.assertAlmostEqual(pieces[-1][2], 4.1)
        self.assertTrue(all(a < b for _, a, b in pieces))
        self.assertFalse(any(" " not in p for p, _, _ in pieces[1:]))            # no lone last word

    def test_the_page_can_still_ask_for_bubbles(self):
        sc, _ = parse_script(TWO % "")
        v = make_video(scene.apply_options(sc, dialogue="bubble"), 160, use_tts=False, hook="off")
        self.assertTrue(all(sp["bubble"] for sp in v.parts[-1].plan.speech))


class Devanagari(unittest.TestCase):
    def test_the_writer_and_the_studio_keep_the_slang(self):
        root = os.path.join(os.path.dirname(__file__), "..")
        with open(os.path.join(root, "SCRIPT_PROMPT.md"), encoding="utf-8") as f:
            prompt = f.read()
        self.assertIn("<Hinglish> | <the same words in Devanagari>", prompt)        # dialogue-only mode too
        self.assertIn("abey = अबे", prompt)
        from studio import hindi
        self.assertIn("never make them proper", hindi.SYSTEM)
        with open(os.path.join(root, "index.html"), encoding="utf-8") as f:
            self.assertIn("| देवनागरी bhi do", f.read())

    def test_a_pasted_dialogue_keeps_its_devanagari(self):
        sc, w = parse_script("HOOK: h\nCAST: K = kutta, D = doctor\nSCENE: hospital\n"
                             "K (smug): Abey chup | अबे चुप\nD (scared): Kya hua? | क्या हुआ?\n")
        self.assertEqual(w, [])
        says = [e for e in sc["scenes"][0]["timeline"] if "say" in e]
        self.assertEqual(says[0]["speak"], "अबे चुप")

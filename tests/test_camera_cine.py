"""The "cine" camera direction and the livelier entrances. python -m unittest discover -s tests"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image                                                    # noqa: E402

from studio import render, scene as S, script                            # noqa: E402
from studio.render import make_video                                     # noqa: E402

HEAD = "HOOK: Test\nCAST: A = beta, B = mummy\nSCENE: kitchen\n"
TWO = HEAD + ("A (grin): Mummy, khana kab banega? | मम्मी, खाना कब बनेगा?\n"
              "B (angry): Pehle bartan dho, phir khana milega! | पहले बर्तन धो, फिर खाना मिलेगा!\n")


def plan(text, **env):
    with mock.patch.dict(os.environ, env):
        os.environ.pop("STUDIO_CAMERA", None) if "STUDIO_CAMERA" not in env else None
        sc, _w = script.parse_script(text)
        return [S.compile_scene(sub, use_tts=False) for sub in S.split_scenes(sc)]


class StyleSwitchTests(unittest.TestCase):
    def test_default_is_cine_and_classic_can_be_asked_for(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("STUDIO_CAMERA", None)
            self.assertEqual(S.camera_style({}), "cine")
            self.assertEqual(S.camera_style({"camera": "classic"}), "classic")
            os.environ["STUDIO_CAMERA"] = "classic"
            self.assertEqual(S.camera_style({"camera": "cine"}), "classic")      # the guard's switch wins

    def test_camera_header(self):
        sc, w = script.parse_script(TWO + "CAMERA: classic\n")
        self.assertEqual((sc["meta"]["camera"], w), ("classic", []))
        sc, w = script.parse_script(TWO + "CAMERA: cine\n")
        self.assertNotIn("camera", sc["meta"])
        self.assertTrue(any("CAMERA" in x for x in script.parse_script(TWO + "CAMERA: 3d\n")[1]))

    def test_classic_plan_has_the_old_segments(self):
        p = plan(TWO, STUDIO_CAMERA="classic")[0]
        self.assertEqual(p.camera, "classic")
        self.assertTrue(all(len(seg) == 6 for seg in p.cam_segments))
        self.assertEqual((p.rolls, p.drift), ([], False))
        self.assertEqual(p.cam_segments[-1][3], 1.0)                  # pulls back to the wide shot at the end
        self.assertEqual(S.camera_roll(p, 7.0), 0.0)


class CineTests(unittest.TestCase):
    def test_reaction_shot_on_the_listener(self):
        p = plan(TWO)[0]
        last = p.speech[-1]
        after = [seg for seg in p.cam_segments if seg[0] > last["end"]]
        self.assertTrue(after and all(seg[6] == "A" for seg in after))          # the camera turns to the one spoken to
        self.assertGreaterEqual(after[0][3], 1.4)                               # ...close, not a wide shot
        face = p.chars["A"].state_at(p.duration - 0.05)["expression"]
        self.assertEqual(face, S.REACTIONS["angry"])                            # and the listener's face answers

    def test_a_directed_reaction_is_left_alone(self):
        p = plan(TWO + "A (shock): Achanak bhookh khatam! | अचानक भूख ख़त्म!\nB -> facepalm\n")[0]
        after = [seg for seg in p.cam_segments if seg[0] > p.speech[-1]["end"]]
        self.assertEqual(after[0][6], "B")                                      # the one who acts gets the shot
        self.assertEqual(p.chars["B"].state_at(p.duration - 0.05)["expression"], "angry")   # no invented face

    def test_auto_react_can_be_switched_off(self):
        sc, _w = script.parse_script(TWO)
        sc["meta"]["auto_react"] = False
        p = S.compile_scene(S.split_scenes(sc)[0], use_tts=False)
        self.assertEqual(p.chars["A"].state_at(p.duration - 0.05)["expression"], "grin")

    def test_tilt_on_an_angry_line_only(self):
        p = plan(TWO)[0]
        angry = p.speech[1]
        self.assertEqual(len(p.rolls), 1)
        self.assertAlmostEqual(abs(S.camera_roll(p, (angry["start"] + angry["end"]) / 2)), S.TILT_DEG, places=2)
        self.assertEqual(S.camera_roll(p, p.speech[0]["start"] + 0.5), 0.0)
        self.assertEqual(S.camera_roll(p, angry["end"] + 0.4), 0.0)             # level again after the line

    def test_camera_never_stands_still(self):
        p = plan(TWO)[0]
        a, b = S.camera_at(p, 0.05), S.camera_at(p, 0.20)                       # before the first move starts
        self.assertNotEqual(a[:3], b[:3])
        self.assertLess(abs(a[0] - b[0]), 0.01)                                 # ...but only a breath
        c = plan(TWO, STUDIO_CAMERA="classic")[0]
        self.assertEqual(S.camera_at(c, 0.05)[:3], S.camera_at(c, 0.20)[:3])

    def test_camera_follows_a_walk(self):
        p = plan(HEAD + "A (smile): Main chala | मैं चला\nA -> walk right\nA (grin): Aa gaya | आ गया\n")[0]
        mv = p.chars["A"].moves[0]
        mid, end = mv[0] + 0.4, mv[1] - 0.1                                     # two moments of the walk itself
        self.assertTrue(any(seg[6] == "A" and seg[0] <= mv[0] for seg in p.cam_segments))
        self.assertGreater(S.camera_at(p, end)[1], S.camera_at(p, mid)[1] + 40)  # the camera goes with him
        c = plan(HEAD + "A (smile): Main chala | मैं चला\nA -> walk right\nA (grin): Aa gaya | आ गया\n",
                 STUDIO_CAMERA="classic")[0]
        self.assertAlmostEqual(S.camera_at(c, end)[1], S.camera_at(c, mid)[1], places=3)

    def test_after_an_exit_the_camera_turns_to_who_is_left(self):
        p = plan(TWO + "A -> exit left\n")[0]
        mv = p.chars["A"].moves[-1]
        last_seg = p.cam_segments[-1]
        self.assertEqual(last_seg[6], "B")
        self.assertGreater(last_seg[0], mv[0])

    def test_fast_talk_is_one_two_shot(self):
        text = HEAD + "".join("%s: %s | %s\n" % (w, t, t) for w, t in
                              (("A", "Mummy"), ("B", "Kya"), ("A", "Paise"), ("B", "Nahi"), ("A", "Please")))
        text += "B (shout): Bilkul nahi, ja ke padhai kar! | बिल्कुल नहीं, जा के पढ़ाई कर!\n"
        p = plan(text)[0]
        first, punch = p.speech[0], p.speech[-1]
        held = [seg for seg in p.cam_segments if first["start"] - 0.1 <= seg[0] < punch["start"] - 0.1]
        self.assertLessEqual(len(held), 2)                                       # no cut for every short line
        self.assertTrue(all(seg[6] is None and 440 < seg[5][0] < 640 for seg in held))   # both in the frame
        tight = next(seg for seg in p.cam_segments if seg[0] >= punch["start"] - 0.1)
        self.assertEqual((tight[6], tight[3]), ("B", 1.7))                       # the punch line keeps its close shot
        self.assertEqual(len(S._banter_runs(p.speech)), 1)

    def test_narrator_after_the_last_line_keeps_the_wide_shot(self):
        p = plan(TWO + "NARRATOR: Aur phir bartan dhule | और फिर बर्तन धुले\n")[0]
        self.assertEqual(p.cam_segments[-1][3], 1.0)

    def test_close_reaction_stays_below_the_cta_card(self):
        p = plan(TWO + "CTA: Tag karo\n")[-1]
        after = [seg for seg in p.cam_segments if seg[0] > p.speech[-1]["end"]]
        self.assertTrue(S._card_over_faces(p, p.speech[-1]["end"] + 0.2))
        self.assertLessEqual(after[0][3], 1.3)
        self.assertLess(after[0][5][1], p.chars["A"].focus_at(after[0][0])[1])   # looks higher: the face sits lower


class EntryTests(unittest.TestCase):
    def one(self, line):
        sc, w = script.parse_script(HEAD + "B (smile): Koi hai? | कोई है?\n" + line + "\nA (grin): Main hoon | मैं हूँ\n")
        self.assertEqual(w, [], line)
        sub = S.split_scenes(sc)[0]
        ev = next(e for e in sub["timeline"] if "entry" in e or "leave" in e)
        return S.compile_scene(sub, use_tts=False), ev

    def test_words(self):
        for line, style, side in (("A -> enter back", "back", None), ("A -> enter back left", "back", "left"),
                                  ("A -> enter pop", "pop", None), ("A -> enter left fast", "fast", "left"),
                                  ("A -> enter right peek", "peek", "right")):
            _p, ev = self.one(line)
            self.assertEqual((ev["entry"]["style"], ev["entry"].get("side")), (style, side), line)
            self.assertEqual(ev["hold"], S.ENTRY_HOLD[style])
        _p, ev = self.one("A -> exit right fast")
        self.assertEqual(ev["leave"], {"style": "fast", "side": "right"})
        sc, _w = script.parse_script(HEAD + "A -> enter left\nA: Hi | हाय\n")           # the plain walk is unchanged
        self.assertNotIn("entry", sc["scenes"][0]["timeline"][2])

    def test_out_of_sight_before_and_in_place_after(self):
        for line in ("A -> enter back", "A -> enter pop", "A -> enter left fast", "A -> enter right peek"):
            p, ev = self.one(line)
            a = p.chars["A"]
            t = a.moves[0][0]
            self.assertFalse(S._on_stage(a, max(0.0, t - 0.2)), line)
            end = t + ev["hold"] + 0.05
            self.assertTrue(S._on_stage(a, end), line)
            self.assertAlmostEqual(a.draw_pos(end)[0], ev["entry"]["x"], delta=2, msg=line)
            self.assertAlmostEqual(a.draw_pos(end)[1], S.GROUND_Y, delta=2, msg=line)
            self.assertAlmostEqual(a.draw_scale(end), a.scale, places=3, msg=line)

    def test_back_starts_small_and_far(self):
        p, _ev = self.one("A -> enter back")
        a = p.chars["A"]
        t = a.moves[0][0]
        self.assertAlmostEqual(a.draw_scale(t + 0.01) / a.scale, S.BACK_DEPTH[0], places=2)
        self.assertLess(a.draw_pos(t + 0.01)[1], S.GROUND_Y - 150)

    def test_pop_overshoots_and_makes_a_sound(self):
        p, _ev = self.one("A -> enter pop")
        a = p.chars["A"]
        t0, t1 = a.moves[0][0], a.moves[0][1]
        ys = [a.draw_pos(t0 + (t1 - t0) * k / 20.0)[1] for k in range(21)]
        self.assertLess(min(ys), S.GROUND_Y - 5)                    # bounces a little above the floor
        self.assertTrue(any("boing" in fx["path"] and abs(fx["t"] - t0) < 0.01 for fx in p.sfx))

    def test_fast_entry_and_exit_have_dust(self):
        p, _ev = self.one("A -> enter left fast")
        self.assertTrue(any(fx.get("type") == "dust" and fx.get("who") == "A" for fx in p.effects))
        self.assertTrue(p.chars["A"].moves[0][6])                   # runs
        p, _ev = self.one("A -> exit right fast")
        a = p.chars["A"]
        self.assertGreater(a.draw_pos(a.moves[-1][1] + 0.1)[0], S.LW)
        self.assertTrue(any(fx.get("type") == "dust" for fx in p.effects))

    def test_old_moves_and_depth_are_unchanged(self):
        c = S.Char("A", {}, 300.0, 1700.0, 0)
        c.moves.append((1.0, 2.0, 300.0, 1700.0, 700.0, 1700.0, False))
        self.assertAlmostEqual(c.pos_at(1.5)[0], 500.0)             # ease_in_out is symmetric: half-way at half time
        c.depth.append((1.0, 1.0, 0.0, 1.3, 110.0))
        self.assertAlmostEqual(c.depth_at(1.25)[0], 1.15)           # 0.5 s, as before


class SetPieceWordTests(unittest.TestCase):
    def test_unknown_word_on_a_set_piece_is_a_warning_not_a_crash(self):
        # an AI wrote `OBJ: door left lakdi`: the script reader used to crash (KeyError 'id') on every attempt
        sc, w = script.parse_script(HEAD + "OBJ: door left lakdi\nB (angry): Kahan the? | कहाँ थे?\n")
        self.assertTrue(any("lakdi" in x for x in w))
        self.assertEqual(sc["scenes"][0]["sets"][0]["type"], "door")
        sc, w = script.parse_script(HEAD + "OBJ: door left lakdi\nOBJ: door open\nB: Aa gaye | आ गए\n")
        self.assertTrue(any(e.get("set") == "door" and e.get("state") == "open" for e in sc["scenes"][0]["timeline"]))


class RenderTests(unittest.TestCase):
    W = 160

    def test_rolled_crop_fills_the_frame(self):
        img = Image.new("RGB", (160, 284), (200, 30, 30))
        out = render._rolled_crop(img, 20, 30, 160 / 1.4, 284 / 1.4, 3.5, 160, 284)
        self.assertEqual(out.size, (160, 284))
        for xy in ((0, 0), (159, 0), (0, 283), (159, 283)):         # no empty (black) corner
            self.assertGreater(out.getpixel(xy)[0], 150)
        tight = render._rolled_crop(img, 0, 0, 160 / 1.02, 284 / 1.02, 8.0, 160, 284)   # hardly any room: tilts less
        self.assertGreater(tight.getpixel((0, 0))[0], 150)

    def test_frames_render_in_both_styles_and_cameras(self):
        sc, _w = script.parse_script(TWO + "A -> enter pop\nA -> exit left fast\nCTA: Tag karo\n")
        sizes = set()
        for style in ("2d", "2.5d"):
            for cam in ("cine", "classic"):
                with mock.patch.dict(os.environ, {"STUDIO_CAMERA": cam}):
                    v = make_video(sc, self.W, use_tts=False, style=style)
                    sizes.update(v.frame(t).size for t in (0.4, 6.5, v.duration - 0.2))
        self.assertEqual(len(sizes), 1)

    def test_cine_differs_from_classic_only_by_the_camera(self):
        sc, _w = script.parse_script(TWO)
        with mock.patch.dict(os.environ, {"STUDIO_CAMERA": "classic"}):
            a = make_video(sc, self.W, use_tts=False, style="2d")
            fa = a.frame(a.duration - 0.3)
        with mock.patch.dict(os.environ, {"STUDIO_CAMERA": "cine"}):
            b = make_video(sc, self.W, use_tts=False, style="2d")
            fb = b.frame(b.duration - 0.3)
        self.assertEqual(a.duration, b.duration)                    # the story's timing is the same
        self.assertNotEqual(fa.tobytes(), fb.tobytes())


class PageTests(unittest.TestCase):
    def test_page_checker_knows_the_new_words(self):
        with open(os.path.join(os.path.dirname(__file__), "..", "index.html"), encoding="utf-8") as f:
            page = f.read()
        self.assertIn('"CAMERA"', page[page.index("const HEADERS"):page.index("const HEADERS") + 400])
        self.assertIn('nxt === "back" || nxt === "pop"', page)
        self.assertIn('tokens[i + 1] === "peek"', page)
        self.assertIn("fast", script.vocab()["moves"])

    def test_writer_prompt_teaches_them(self):
        with open(os.path.join(os.path.dirname(__file__), "..", "SCRIPT_PROMPT.md"), encoding="utf-8") as f:
            prompt = f.read()
        for word in ("enter back", "enter pop", "enter left fast", "enter left peek", "exit left fast",
                     "ALREADY in their place"):
            self.assertIn(word, prompt)


if __name__ == "__main__":
    unittest.main()

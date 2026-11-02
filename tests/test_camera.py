"""Auto camera + bubbles that stay in shot.  python -m unittest discover -s tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio.render import make_video      # noqa: E402
from studio.scene import compile_scene    # noqa: E402

TALK = [{"t": 0.0, "who": "A", "say": "ek", "duration": 2.0},
        {"who": "B", "say": "do", "duration": 2.0},
        {"who": "A", "say": "teen", "duration": 2.0},
        {"who": "all", "action": "jump", "hold": 1.5}]


def scene(**kw):
    s = {"characters": {"A": {"look": "boy"}, "B": {"look": "aunty"}}, "timeline": [dict(e) for e in TALK]}
    s.update(kw)
    return s


class AutoCameraTests(unittest.TestCase):
    def test_every_line_gets_a_shot_on_its_speaker(self):
        p = compile_scene(scene(), use_tts=False)
        self.assertGreaterEqual(len(p.cam_segments), 4)
        self.assertEqual(p.cam_segments[-1][3], 1.0)                       # pulls back to wide at the end
        self.assertGreater(max(sg[3] for sg in p.cam_segments), 1.4)       # punch line is the tightest shot
        self.assertEqual(len(p.shakes), 1)                                 # one hit on the punch line

    def test_explicit_camera_wins(self):
        s = scene()
        s["timeline"].insert(1, {"t": 0.2, "camera": {"zoom": 1.1, "dur": 0.3}})
        p = compile_scene(s, use_tts=False)
        self.assertEqual([sg[3] for sg in p.cam_segments], [1.1])

    def test_can_be_switched_off(self):
        p = compile_scene(scene(meta={"auto_camera": False}), use_tts=False)
        self.assertEqual(p.cam_segments, [])

    def test_no_speech_no_camera(self):
        s = {"characters": {"A": {"look": "boy"}}, "timeline": [{"t": 0, "who": "A", "action": "dance", "hold": 3}]}
        self.assertEqual(compile_scene(s, use_tts=False).cam_segments, [])

    def test_frames_render_at_every_zoom_and_bubbles_fit(self):
        s = scene()
        s["timeline"][0]["say"] = "Ye ek kaafi lambi line hai jo bubble ko chauda banayegi, dekhte hain kat ti hai ya nahi"
        v = make_video(s, 216, use_tts=False)
        for t in [0.1, 0.8, 1.9, 2.6, 4.1, 5.2, 6.6]:
            self.assertEqual(v.frame(t).size, (216, 384))


if __name__ == "__main__":
    unittest.main()


class ShotAndDepthTests(unittest.TestCase):
    def test_script_words_become_shots_and_depth(self):
        from studio.script import parse_script, vocab
        sc, warns = parse_script("CAST: A = dost, B = aunty\nSCENE: street\nHOOK: x\n"
                                 "A (laugh, wide): ek | एक\nB -> near smug\nB (angry, close): do | दो\n"
                                 "A -> shock two_shot\nA (cry, closeup): teen | तीन\nB -> far\nCTA: y\n")
        self.assertEqual(warns, [])
        tl = sc["scenes"][0]["timeline"]
        self.assertEqual([e.get("shot") for e in tl if "say" in e], ["wide", "close", "close"])   # closeup -> close
        self.assertIn("depth", [k for e in tl for k in e])
        v = vocab()
        self.assertIn("two_shot", v["shots"])
        self.assertEqual(v["depth"], ["far", "mid", "near"])

    def test_depth_moves_the_character_towards_the_camera_smoothly(self):
        s = scene()
        s["timeline"] = [{"t": 0.0, "who": "A", "say": "ek", "duration": 1.0},
                         {"t": 2.0, "who": "B", "depth": "near", "action": "idle", "hold": 1.0},
                         {"t": 4.0, "who": "B", "depth": "far", "action": "idle", "hold": 1.0}]
        p = compile_scene(s, use_tts=False)
        b = p.chars["B"]
        self.assertEqual(b.depth_at(1.9), (1.0, 0.0))
        k_mid, dy_mid = b.depth_at(2.25)
        self.assertTrue(1.0 < k_mid < 1.3 and 0 < dy_mid < 110)             # in between: eased, not a jump
        self.assertEqual(b.depth_at(3.0), (1.3, 110.0))
        self.assertEqual(b.depth_at(5.0), (0.75, -150.0))
        self.assertGreater(b.draw_pos(3.0)[1], p.chars["A"].draw_pos(3.0)[1])   # feet lower = in front

    def test_shot_word_overrides_the_automatic_size_and_two_shot_frames_both(self):
        s = scene()
        s["timeline"] = [{"t": 0.0, "who": "A", "say": "ek", "duration": 2.0, "shot": "wide"},
                         {"who": "B", "say": "do", "duration": 2.0, "shot": "two_shot"},
                         {"who": "A", "say": "teen", "duration": 2.0}]
        p = compile_scene(s, use_tts=False)
        self.assertEqual(p.cam_segments[0][3], 1.0)                          # first line forced wide
        two = [sg for sg in p.cam_segments if sg[3] == 1.3][0]
        a_x, b_x = p.chars["A"].draw_pos(0)[0], p.chars["B"].draw_pos(0)[0]
        self.assertAlmostEqual(two[5][0], (a_x + b_x) / 2, delta=1)           # centred between the two

    def test_frames_render_with_depth(self):
        s = scene()
        s["timeline"].insert(1, {"t": 1.0, "who": "B", "depth": "near", "action": "idle"})
        v = make_video(s, 216, use_tts=False)
        self.assertEqual(v.frame(3.0).size, (216, 384))

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

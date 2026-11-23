"""The Harkat editor (editor.html): a separate page that changes only what you pick, and the `X -> move 0.35` line
it writes (walk to 35% of the width). The studio page only gains a link to it. python -m unittest"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import script                                 # noqa: E402
from studio.render import Sequence                        # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
HEAD = "HOOK: x\nCAST: A = papa, B = beta\nSCENE: room\n"


class MoveLine(unittest.TestCase):
    def test_move_to_a_point(self):
        sc, w = script.parse_script(HEAD + "A: Haan | हाँ\nA -> move 0.8\nB -> move 25%\nB: Kya | क्या\n")
        self.assertEqual(w, [])
        p = Sequence(sc, 270, False, None, None).parts[0]
        end = p.plan.duration - 0.05
        self.assertAlmostEqual(p.plan.chars["A"].draw_pos(end)[0], 70 + 0.8 * 940, delta=2)
        self.assertAlmostEqual(p.plan.chars["B"].draw_pos(end)[0], 70 + 0.25 * 940, delta=2)

    def test_out_of_range_is_clamped(self):
        sc, _w = script.parse_script(HEAD + "A: Haan | हाँ\nA -> move 1.0\nB: Kya | क्या\n")
        ev = [e for e in sc["scenes"][0]["timeline"] if "move" in e][0]
        self.assertEqual(ev["move"]["x"], 1010.0)


class Pages(unittest.TestCase):
    def test_editor_page(self):
        with open(os.path.join(ROOT, "editor.html"), encoding="utf-8") as f:
            ed = f.read()
        for needle in ('id="stage"', '"move"', 'store.set("editor_out"', 'store.get("editor_in")',
                       '— studio khud —', 'fetch("index.html"'):
            self.assertIn(needle, ed)

    def test_the_studio_page_only_links_to_it(self):
        with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as f:
            page = f.read()
        self.assertIn('href="editor.html"', page)
        self.assertIn('store.get("editor_out")', page)
        self.assertIn("feel.slice(2)", page)                  # two feelings on a line are fine on the page too


if __name__ == "__main__":
    unittest.main()


class PoseLine(unittest.TestCase):
    def test_the_puppets_angles_are_the_pose(self):
        sc, w = script.parse_script(HEAD + "CAMERA: classic\nA: Haan | हाँ\n"
                                    "A -> pose ra=150/170 la=-30/-150 rl=20/5 ll=-7/-2 head=12\nB: Kya | क्या\n")
        self.assertEqual(w, [])
        ev = [e for e in sc["scenes"][0]["timeline"] if e.get("action") == "pose"][0]
        self.assertEqual(ev["pose"], {"ra1": 150.0, "ra2": 170.0, "la1": -30.0, "la2": -150.0, "rl1": 20.0,
                                      "rl2": 5.0, "ll1": -7.0, "ll2": -2.0, "head_tilt": 12.0})
        from studio import actions
        p = actions.pose_for("pose", 1.0, opts={"pose": ev["pose"]})
        self.assertEqual((p["ra1"], p["ra2"], p["la2"], p["head_tilt"]), (150.0, 170.0, -150.0, 12.0))


class ThingsAnywhere(unittest.TestCase):
    def test_obj_at_a_fraction(self):
        sc, w = script.parse_script(HEAD + "OBJ: chair 0.2\nOBJ: cycle 75%\nA: Haan | हाँ\nB: Kya | क्या\n")
        self.assertEqual(w, [])
        sets = sc["scenes"][0]["sets"]
        chair = (sets.values() if isinstance(sets, dict) else sets)
        self.assertEqual([c["x"] for c in chair if c["type"] == "chair"], [258.0])
        self.assertIn({"obj": {"kind": "cycle", "at": 775.0}}, sc["scenes"][0]["timeline"])


class VoicePack(unittest.TestCase):
    def test_saved_then_used_again(self):
        import tempfile
        from unittest import mock
        from studio import scene as S
        d = tempfile.mkdtemp()
        wav = os.path.join(d, "x.wav")
        with open(wav, "wb") as f:
            f.write(b"RIFF....WAVE")
        with mock.patch.dict(os.environ, {"VOICE_PACK_OUT": os.path.join(d, "pack")}):
            S.voice_pack_save("Daddu", "Re  Sultan, kahan?", wav)
        with mock.patch.dict(os.environ, {"VOICE_PACK_IN": os.path.join(d, "pack")}):
            pack = S.voice_pack_in()
        self.assertTrue(os.path.isfile(pack[S.pack_key("daddu", "Re Sultan, kahan?")]))   # (spaces, case)

    def test_the_workflow_keeps_and_reuses_it(self):
        with open(os.path.join(ROOT, ".github", "workflows", "render.yml"), encoding="utf-8") as f:
            wf = f.read()
        for needle in ("voice_from:", 'VOICE_PACK_OUT="out/$name.voice"', "out/*.voice.zip", "out/*.project.json",
                       "<!-- project ", "VOICE_PACK_IN="):
            self.assertIn(needle, wf)


class EditorFeatures(unittest.TestCase):
    def test_puppet_things_and_the_reel(self):
        with open(os.path.join(ROOT, "editor.html"), encoding="utf-8") as f:
            ed = f.read()
        for needle in ('id="puppet"', "function ik(", "TORSO_H: 290, UA: 114, LA: 108, TH: 146, SH: 146",
                       'id="objBtn"', "OBJ: ${o.kind}", "editor.html?reel=" if False else "openReel(",
                       'store.set("editor_go"', '"480"'):
            self.assertIn(needle, ed)

    def test_the_skeleton_matches_the_studio(self):
        from studio import characters as C
        self.assertEqual((C.TORSO_H, C.UA, C.LA, C.TH, C.SH), (290.0, 114.0, 108.0, 146.0, 146.0))
        with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as f:
            page = f.read()
        self.assertIn("editor.html?reel=", page)
        self.assertIn("extra.voice_from", page)

"""The place's colour look (studio.look) and the strange thing hidden in every video (studio.mystery).
python -m unittest discover -s tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image, ImageChops                   # noqa: E402

from studio import look, mystery, render            # noqa: E402
from studio.script import parse_script, vocab       # noqa: E402

SCRIPT = ("HOOK: Test 😭\n%sCAST: A = uncle, B = college_girl\nSCENE: %s\n"
          "A (point, angry): Ye kya hai beta, batao mujhe abhi? | x\nB (shrug, smug): Pata nahi papa, sach me. | x\n"
          "A (shock): Kya matlab pata nahi?! | x\nB (grin): Matlab pata nahi. | x\nA (facepalm): Hey bhagwan. | x\n")


def video(place, head="", **kw):
    scene, warnings = parse_script(SCRIPT % (head, place))[:2]
    v = render.make_video(scene, 180, use_tts=False, hook="off", **kw)
    return v, getattr(v, "parts", [v]), warnings


class Look(unittest.TestCase):
    def test_every_place_of_the_studio_has_a_look_that_exists(self):
        for place, name in look.PLACE_LOOK.items():
            self.assertIn(place, vocab()["places"], place)
            self.assertIn(name, look.LOOKS, place)

    def test_places_get_different_looks_and_a_mood_changes_them(self):
        names = {look.choose(p)[0] for p in ("hospital", "dhaba", "mandap", "haunted_house", "jail", "office")}
        self.assertEqual(len(names), 6)
        self.assertNotEqual(look.choose("room")[1], look.choose("room", mood="sad")[1])
        self.assertLess(look.choose("room", mood="sad")[1]["sat"], look.choose("room")[1]["sat"])
        self.assertNotEqual(look.choose("kitchen")[1], look.choose("kitchen", time="night")[1])

    def test_off_plain_and_your_own_picture_stay_as_painted(self):
        self.assertEqual(look.choose("hospital", asked="off"), (None, None))
        self.assertEqual(look.choose("plain"), (None, None))
        self.assertEqual(look.choose("image"), (None, None))

    def test_the_grade_changes_the_picture_and_keeps_its_size(self):
        im = Image.linear_gradient("L").resize((90, 160)).convert("RGB")
        for name in look.LOOKS:
            out = look.Grade(look.LOOKS[name], 90, 160).apply(im, 3)
            self.assertEqual((out.size, out.mode), ((90, 160), "RGB"), name)
            self.assertIsNotNone(ImageChops.difference(out, im).getbbox(), name)

    def test_the_look_line_of_a_script(self):
        scene, warnings = parse_script(SCRIPT % ("LOOK: horror\n", "room"))[:2]
        self.assertEqual((scene["meta"]["look"], warnings), ("darr", []))
        self.assertEqual(parse_script(SCRIPT % ("LOOK: off\n", "room"))[0]["meta"]["look"], "off")
        self.assertTrue(any("LOOK" in w for w in parse_script(SCRIPT % ("LOOK: gulabi_jadoo\n", "room"))[1]))

    def test_a_hospital_and_a_dhaba_do_not_come_out_of_the_same_camera(self):
        (a, pa, _), (b, pb, _) = video("hospital"), video("dhaba")
        self.assertNotEqual(pa[0]._look.name, pb[0]._look.name)
        off, _parts, _ = video("hospital", "LOOK: off\n")
        self.assertIsNone(_parts[0]._look)
        self.assertIsNotNone(ImageChops.difference(a.frame(1.0).convert("RGB"), off.frame(1.0).convert("RGB")).getbbox())

    def test_the_old_camera_keeps_the_old_picture(self):
        _v, parts, _ = video("hospital", "CAMERA: classic\n")
        self.assertIsNone(parts[0]._look)
        self.assertIsNone(parts[0].mystery)


class NewPlaces(unittest.TestCase):
    def test_the_nov_2026_places_are_complete(self):
        from studio import crowd, places_2026, styles
        from studio.scene import WRITTEN_PLACES
        root = os.path.join(os.path.dirname(__file__), "..")
        for p in places_2026.NEW:
            self.assertIn(p, vocab()["places"], p)
            self.assertIn(p, look.PLACE_LOOK, p)
            self.assertTrue(mystery.pool(p, False), p)
            self.assertIn(p, WRITTEN_PLACES, p)
            self.assertIn(p + "_25d", styles.NO_MIRROR, p)
            self.assertEqual(styles.PLACES_25D[p], p + "_25d")
            self.assertTrue(os.path.exists(os.path.join(root, "assets", "places", p + ".jpg")), p)
        self.assertIn("park", crowd.LANES_2D)

    def test_a_cut_never_mirrors_their_signs(self):
        from studio.scene import shot_angle
        for k in range(1, 5):
            self.assertFalse(shot_angle({"background": {"type": "atm"}, "angle": k}, "medium")["mirror"])
        self.assertTrue(shot_angle({"background": {"type": "atm"}, "reverse": True}, "medium")["mirror"])


class Mystery(unittest.TestCase):
    def test_every_video_gets_one_and_the_same_script_the_same_one(self):
        for place in ("room", "street", "night_road", "office", "gaon", "bus"):
            _v, parts, _ = video(place)
            got = [p.mystery for p in parts if p.mystery]
            self.assertEqual(len(got), 1, place)
            self.assertIn(got[0]["kind"], mystery.pool(place, place == "night_road", False) + ["tv"], place)
            again = [p.mystery for p in video(place)[1] if p.mystery][0]
            self.assertEqual((got[0]["kind"], got[0]["t0"]), (again["kind"], again["t0"]), place)

    def test_it_happens_in_the_middle_never_at_the_start_or_the_end(self):
        v, parts, _ = video("street")
        m = parts[0].mystery
        self.assertGreater(m["t0"], 1.0)
        self.assertLess(m["t1"], parts[0].duration - 0.5)

    def test_each_kind_is_drawn_and_only_in_its_moment(self):
        for place, kind in (("street", "ufo"), ("gaon", "aadmi"), ("night_road", "toota_taara"),
                            ("graveyard", "aankhen"), ("room", "saaya"), ("bedroom", "jhapak")):
            v, parts, warnings = video(place, "MYSTERY: %s\n" % kind)
            self.assertEqual(warnings, [], kind)
            p = parts[0]
            m = p.mystery
            self.assertEqual(m["kind"], kind)
            t = m["t0"] + (0.25 if kind == "jhapak" else (m["t1"] - m["t0"]) * 0.4)
            with_it = v.frame(t).convert("RGB")
            before = v.frame(max(0.0, m["t0"] - 0.4)).convert("RGB")
            p.mystery = None
            self.assertIsNotNone(ImageChops.difference(with_it, v.frame(t).convert("RGB")).getbbox(), kind)
            self.assertIsNone(ImageChops.difference(before, v.frame(max(0.0, m["t0"] - 0.4)).convert("RGB")).getbbox(),
                              kind)

    def test_the_portrait_hangs_there_all_the_time_and_wakes_up_once(self):
        v, parts, _ = video("office", "MYSTERY: tasveer\n")
        m = parts[0].mystery
        asleep = mystery._tasveer(m, False, parts[0].s)
        awake = mystery._tasveer(m, True, parts[0].s)
        self.assertIsNotNone(ImageChops.difference(asleep.convert("RGB"), awake.convert("RGB")).getbbox())

    def test_off_and_the_words_of_the_script_line(self):
        _v, parts, _ = video("room", "MYSTERY: off\n")
        self.assertFalse(any(p.mystery for p in parts))
        self.assertEqual(mystery.resolve("shadow"), "saaya")
        self.assertEqual(mystery.resolve("UFO"), "ufo")
        self.assertIsNone(mystery.resolve("dinosaur"))
        self.assertTrue(any("MYSTERY" in w for w in parse_script(SCRIPT % ("MYSTERY: dinosaur\n", "room"))[1]))

    def test_the_page_and_the_prompt_know_the_two_lines(self):
        root = os.path.join(os.path.dirname(__file__), "..")
        with open(os.path.join(root, "index.html"), encoding="utf-8") as f:
            page = f.read()
        self.assertGreaterEqual(page.count("LOOK|MYSTERY"), 3)
        with open(os.path.join(root, "SCRIPT_PROMPT.md"), encoding="utf-8") as f:
            prompt = f.read()
        self.assertIn("one strange thing in the background", prompt)
        self.assertNotIn("`CUT ots` / `CUT ots`", prompt)


if __name__ == "__main__":
    unittest.main()

"""People in the background of public places (studio.crowd), and a car / an auto drive seen from different places
(studio.drive): from the side, from in front, the driver's eyes, the rear-view mirror.
python -m unittest discover -s tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import crowd, drive, styles, vehicles  # noqa: E402
from studio.render import Renderer, make_video  # noqa: E402
from studio.scene import split_scenes  # noqa: E402
from studio.script import parse_script, vocab  # noqa: E402

W = 216


def scene_of(text, i=0):
    sc, warns = parse_script(text)
    return split_scenes(sc)[i], warns


STREET = """HOOK: Bheed 😂
CAST: A = college_boy, B = uncle
SCENE: {place}
{extra}A (smile): Bhai chai pila de | भाई चाय पिला दे
B (sly): Pehle paise | पहले पैसे
"""

DRIVE = """HOOK: Long drive 🚗
CAST: R = boy, P = girl
SCENE: {veh}
R (happy): Chalo long drive pe! | चलो लंबी ड्राइव पे!
P (smile): Dhyan se chalana. | ध्यान से चलाना।
R (wink): Main pro driver hoon. | मैं प्रो ड्राइवर हूँ।
P (shock): Aage truck hai! | आगे ट्रक है!
R (scared): Arre baap re! | अरे बाप रे!
P (laugh): Pro driver? | प्रो ड्राइवर?
"""


class Crowd(unittest.TestCase):
    def test_how_many(self):
        self.assertEqual(crowd.amount({}), 3)                                     # a few by default
        self.assertEqual(crowd.amount({"crowd": "none"}), 0)
        self.assertEqual(crowd.amount({"crowd": "zyada"}), 6)
        self.assertEqual(len(crowd.extras("market", n=6, seed="x")), 6)
        self.assertEqual(crowd.extras("market", n=3, seed="x"), crowd.extras("market", n=3, seed="x"))  # same video,
        self.assertEqual(crowd.extras("kitchen", n=3), [])                         # same people; a home: nobody
        far = min(crowd.extras("street", n=3, seed="x"), key=lambda e: e["y"])
        self.assertLess(far["scale"], 0.5)                                          # far back: small

    def test_the_script_line(self):
        sc, warns = scene_of(STREET.format(place="market", extra="CROWD: zyada\n"))
        self.assertEqual(warns, [])
        self.assertEqual(crowd.amount(sc), 6)
        _sc, warns = scene_of(STREET.format(place="market", extra="CROWD: lakhon\n"))
        self.assertTrue(any("CROWD" in w for w in warns))
        self.assertIn("zyada", vocab()["crowd_words"])                              # the page knows the words

    def test_where_they_are_drawn(self):
        for style in ("", "2.5d"):
            road, _w = scene_of(STREET.format(place="street", extra=""))
            shop, _w = scene_of(STREET.format(place="market", extra=""))
            if style:
                road["style"] = shop["style"] = style
            r = Renderer(road, W, use_tts=False)                                   # a road: behind the traffic
            if style:
                self.assertTrue([ly for ly in r.bd25.layered.back if ly.name == "crowd"])
            else:
                self.assertIsNotNone(r.bg.crowd)
            r = Renderer(shop, W, use_tts=False)                                   # a shop: sorted with the people
            self.assertIsNotNone(getattr(r, "_crowd", None), style)
            self.assertEqual(r.frame(1.0).size, (W, W * 16 // 9))

    def test_none_classic_and_vehicles_stay_empty(self):
        sc, _w = scene_of(STREET.format(place="market", extra="CROWD: none\n"))
        self.assertIsNone(getattr(Renderer(sc, W, use_tts=False), "_crowd", None))
        sc, _w = scene_of(STREET.format(place="market", extra="CAMERA: classic\n"))
        self.assertIsNone(getattr(Renderer(sc, W, use_tts=False), "_crowd", None))
        sc, _w = scene_of(STREET.format(place="bus", extra=""))
        r = Renderer(sc, W, use_tts=False)
        self.assertIsNone(getattr(r, "_crowd", None))
        self.assertIsNone(r.bg.crowd)


class Drive(unittest.TestCase):
    def test_the_studio_cuts_a_drive(self):
        for veh in ("car", "auto"):
            sc, warns = parse_script(DRIVE.format(veh=veh))
            self.assertEqual(warns, [])
            kinds = [s["background"]["type"] for s in sc["scenes"]]
            self.assertEqual(kinds[0], veh + "_side")                                # it opens outside
            self.assertEqual(kinds[-1], veh + "_mirror")                             # the punch line in the mirror
            self.assertIn(veh + "_front", kinds)
            self.assertIn({"car": "car_cabin", "auto": "auto"}[veh], kinds)          # and inside
            self.assertIn(veh + "_pov", kinds)                                       # the driver's eyes
            for a, b in zip(kinds, kinds[1:]):
                self.assertNotEqual(a, b)                                            # every cut somewhere else
            side = sc["scenes"][0]["characters"]
            self.assertGreater(side["R"]["x"], side["P"]["x"])                       # R drives: in front (facing right)
            self.assertEqual(side["R"]["facing"], "right")
            mirror = sc["scenes"][-1]["characters"]
            self.assertTrue(mirror["R"].get("hidden"))                               # only the speaker is in the mirror
            self.assertFalse(mirror["P"].get("hidden"))
            for s in sc["scenes"]:
                if s["background"]["type"] != veh:                                   # a driving shot: no seats, no zoom
                    self.assertFalse([p for p in (s.get("sets") or []) if "seat" in str(p.get("type"))])
                    self.assertEqual(s["meta"]["auto_camera"], False)
                    self.assertEqual(s["angle"], {"zoom": 1.0, "x": 540.0, "mirror": False})

    def test_the_writer_cuts_a_drive(self):
        text = DRIVE.format(veh="car").replace("SCENE: car\n", "SCENE: car\nCUT front\n")
        text = text.replace("R (scared)", "CUT pov\nR (scared)").replace("P (laugh)", "CUT sheesha\nP (laugh)")
        sc, warns = parse_script(text)
        self.assertEqual(warns, [])
        self.assertEqual([s["background"]["type"] for s in sc["scenes"]], ["car_front", "car_pov", "car_mirror"])
        self.assertFalse(sc["scenes"][0].get("cut_in"))                              # no empty shot before it
        pov = sc["scenes"][1]
        self.assertTrue(pov["characters"]["R"].get("hidden"))                        # the driver is the camera:
        said = [e for e in pov["timeline"] if e.get("say")]
        self.assertTrue(said[0].get("subtitle"))                                    # his words as a subtitle
        self.assertFalse(said[0].get("bubble", True))

    def test_classic_and_a_short_ride_stay_inside(self):
        sc, _w = parse_script(DRIVE.format(veh="car") + "CAMERA: classic\n")
        self.assertEqual({s["background"]["type"] for s in sc["scenes"]}, {"car"})
        one = "\n".join(DRIVE.format(veh="car").splitlines()[:4]) + "\n"
        sc, _w = parse_script(one)
        self.assertEqual([s["background"]["type"] for s in sc["scenes"]], ["car_cabin"])     # a short ride: inside
        self.assertNotIn("car_front", vocab()["places"])                             # not a place of its own

    def test_four_in_the_car(self):
        text = DRIVE.format(veh="car").replace("CAST: R = boy, P = girl", "CAST: R = boy, P = girl, M = aunty, "
                                                                            "D = dadi")
        text = text.replace("P (laugh)", "M (laugh)").replace("P (shock)", "D (shock)")
        sc, _w = parse_script(text)
        front = next(s for s in sc["scenes"] if s["background"]["type"] == "car_front")["characters"]
        self.assertEqual(front["R"]["x"], drive.PLACES["car_front"]["xs"][0])         # at the wheel
        self.assertLess(front["M"].get("depth_k", 1), 1)                             # the back seat: further back
        self.assertLess(front["M"]["y"], front["R"]["y"])

    def test_a_car_inside_is_a_car(self):
        """From the dashboard: the driver and the one beside him in front with the front seats behind them, the
        back seat's people behind those seats (their heads between them); the driver's hands on the wheel."""
        text = DRIVE.format(veh="car").replace("CAST: R = boy, P = girl", "CAST: R = boy, P = girl, M = aunty, "
                                                                            "D = dadi")
        text = text.replace("SCENE: car\n", "SCENE: car\nCUT inside\n").replace("P (laugh)", "M (laugh)")
        text = text.replace("P (shock)", "D (shock)")
        sc, _w = scene_of(text)
        self.assertEqual(sc["background"]["type"], "car_cabin")
        ch = sc["characters"]
        self.assertLess(ch["R"]["x"], ch["M"]["x"], ch["P"]["x"])                    # the driver on the left (India)
        self.assertLess(ch["M"]["y"], drive.SEAT_DEPTH)                              # the back seat: behind the
        self.assertGreater(ch["R"]["y"], drive.SEAT_DEPTH)                           # front seats; the front: before
        self.assertIn({"t": 0.0, "who": "R", "action": "steer"}, sc["timeline"])
        self.assertFalse([e for e in sc["timeline"] if e.get("who") == "R" and e.get("say") and e.get("action")])
        for style in ("", "2.5d"):
            r = Renderer(dict(sc, style=style) if style else sc, W, use_tts=False)
            pieces = r._foreground(1.0)
            self.assertTrue([p for p in pieces if p[0] == drive.SEAT_DEPTH], style)  # the seats, sorted with them
            r.frame(1.0)
        sc, _w = parse_script(text + "CAMERA: classic\n")
        self.assertEqual(sc["scenes"][0]["background"]["type"], "car")             # classic: as before

    def test_hands_on_the_wheel(self):
        from studio import actions
        from studio.characters import build_character
        pose = actions.pose_for("steer", 1.0, 1.0, 1.0, 0.0, {})
        self.assertTrue(pose["wheel"])
        _ops, an = build_character({"look": "boy"}, pose, "smile", 0.0, 1.0, 540.0, 1700.0, 1.0)
        (lx, ly), (rx, ry) = an["hand_l"], an["hand_r"]
        self.assertLess(lx, 540)
        self.assertGreater(rx, 540)
        self.assertLess(abs(ly - ry), 40)                                            # both up at the rim
        self.assertLess(max(ly, ry), 1700 - 300)

    def test_an_auto_driver_drives(self):
        text = ("HOOK: x\nCAST: P = papa, A = autowala, B = beta\nSCENE: rickshaw city\nCUT inside\n"
                "P (tired): Bhaiya AC chalao | भैया एसी चलाओ\nB (laugh): Auto me AC? | ऑटो में एसी?\n")
        sc, _w = parse_script(text)
        s0 = sc["scenes"][0]
        self.assertEqual(s0["background"]["type"], "auto")
        self.assertTrue(s0["characters"]["A"]["hidden"])                            # the silent autowala sits in front:
        self.assertFalse(s0["characters"]["P"].get("hidden"))                        # the bench has the passengers
        sc, _w = parse_script(text.replace("CUT inside\n", "CUT front\n"))
        self.assertEqual(sc["scenes"][0]["characters"]["A"]["x"], drive.PLACES["auto_front"]["xs"][0])

    def test_the_highway_is_not_bare(self):
        from PIL import Image
        im = Image.new("RGB", (216, 384))
        drive.road_ahead(im, 1.0, 0.2, "car_pov", "highway", None)
        colours = len(set(im.resize((108, 192)).getdata()))
        self.assertGreater(colours, 150)                                            # sky, hills, fields, trees, truck
        sky, layers = vehicles.outside("highway", 0.2, None, "car_side")
        old_sky, old = vehicles.outside("highway", 0.2, None, "car")
        self.assertEqual(len(layers), 3)
        self.assertNotEqual(layers[1][0].tobytes(), old[1][0].tobytes())             # a driving shot: its own view

    def test_it_renders_in_both_looks(self):
        for style in ("", "2.5d"):
            for kind in ("car_front", "car_side", "car_pov", "car_mirror", "car_cabin", "auto_front", "auto_side",
                         "auto_pov", "auto_mirror"):
                base, pov = drive.POV[kind]
                pov = "inside" if pov == "cabin" else pov
                text = DRIVE.format(veh=base).replace("SCENE: %s\n" % base, "SCENE: %s\nCUT %s\n" % (base, pov))
                sc, _w = scene_of(text)
                if style:
                    sc["style"] = style
                    self.assertEqual(styles.preset_for(sc), kind + "_25d")
                r = Renderer(sc, W, use_tts=False)
                self.assertEqual(r.plan.vehicle, kind)
                a, b = r.frame(1.0), r.frame(1.5)
                self.assertEqual(a.size, (W, W * 16 // 9))
                if pov in ("pov", "side"):
                    self.assertNotEqual(a.tobytes(), b.tobytes(), (style, kind))      # the road runs past

    def test_the_vehicle_engine_knows_the_shots(self):
        for kind in drive.POV:
            self.assertTrue(vehicles.VEHICLES[kind].get("pov"))
            self.assertIsNone(vehicles.VEHICLES[kind].get("seat"))
            self.assertEqual(vehicles.inside(kind, 0.1).mode, "RGBA")

    def test_a_whole_video(self):
        sc, _w = parse_script(DRIVE.format(veh="auto") + "STYLE: 2.5d\n")
        v = make_video(sc, W, use_tts=False)
        self.assertGreater(v.duration, 10)
        self.assertEqual(v.frame(v.duration / 2).size, (W, W * 16 // 9))


if __name__ == "__main__":
    unittest.main()

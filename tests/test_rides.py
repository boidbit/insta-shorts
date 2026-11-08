"""Characters riding vehicles. python -m unittest discover -s tests"""
import math
import os
import sys
import unittest

from PIL import ImageChops

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import objects, rides                                   # noqa: E402
from studio.characters import skeleton                              # noqa: E402
from studio.render import make_video                                # noqa: E402
from studio.scene import compile_scene                              # noqa: E402
from studio.script import parse_script, vocab                       # noqa: E402


def scene(*events, chars=None, **meta):
    return {"characters": chars or {"A": {"look": "boy", "slot": "left"}}, "background": {"type": "street"},
            "meta": dict({"auto_camera": False, "duration": 9.0}, **meta),
            "timeline": [{"t": 0.0, "who": "all", "action": "idle"}] + list(events)}


BIKE = [{"t": 0.1, "obj": {"kind": "bike", "at": "center"}}, {"t": 0.4, "who": "A", "ride": {"kind": "bike"}}]


class IKTests(unittest.TestCase):
    def test_a_reachable_target_is_reached(self):
        for origin, target, l1, l2, bend in (((56.0, -268.0), (150.0, -150.0), 114.0, 108.0, -1),
                                             ((32.0, 0.0), (130.0, 120.0), 146.0, 146.0, +1)):
            a1, a2 = rides._ik(origin, target, l1, l2, bend)
            ex, ey = origin[0] + l1 * math.sin(math.radians(a1)), origin[1] + l1 * math.cos(math.radians(a1))
            hx, hy = ex + l2 * math.sin(math.radians(a2)), ey + l2 * math.cos(math.radians(a2))
            self.assertAlmostEqual(hx, target[0], delta=0.5)
            self.assertAlmostEqual(hy, target[1], delta=0.5)

    def test_knees_point_forward_and_elbows_down(self):
        a1, a2 = rides._ik((32.0, 0.0), (140.0, 100.0), 146.0, 146.0, +1)
        self.assertGreater(a1, a2)                       # thigh swings further forward than the shin
        b1, b2 = rides._ik((56.0, -268.0), (160.0, -170.0), 114.0, 108.0, -1)
        self.assertLess(b1, b2)                          # upper arm hangs lower than the forearm

    def test_unreachable_targets_do_not_crash(self):
        a1, a2 = rides._ik((0.0, 0.0), (5000.0, 5000.0), 100.0, 100.0, 1)
        self.assertTrue(math.isfinite(a1) and math.isfinite(a2))

    def test_the_riders_hands_reach_the_handlebar_of_every_open_vehicle(self):
        from studio.scene import SceneObj
        reach = (rides.UA + rides.LA) * rides.ARM_K
        for kind in ("bike", "scooter", "cycle", "auto"):
            o = SceneObj(kind, None, 1.0, 1650.0, False, 0.0, 540.0)
            seat = rides.seat_for(kind, "driver")
            sk = skeleton(rides.ride_pose(o, seat, 0.0))
            r = seat["r"]

            def want(target):
                return ((target[0] - seat["hip"][0]) / r, (target[1] - seat["hip"][1]) / r)

            w = want(seat["hands"][0])                           # the near hand (right arm) grips the handlebar
            self.assertLess(math.hypot(sk["handR"][0] - w[0], sk["handR"][1] - w[1]), 25.0, kind)
            w = want(seat["hands"][1])                           # the far hand: there too, or at least fully stretched
            miss = math.hypot(sk["handL"][0] - w[0], sk["handL"][1] - w[1])
            out = math.hypot(sk["handL"][0] - sk["shL"][0], sk["handL"][1] - sk["shL"][1])
            self.assertTrue(miss < 25.0 or out > 0.97 * reach, (kind, miss, out))


class CompileTests(unittest.TestCase):
    def test_riding_creates_the_vehicle_bigger_and_follows_it(self):
        p = compile_scene(scene({"t": 0.4, "who": "A", "ride": {"kind": "bike"}},
                                {"t": 3.0, "obj": {"kind": "bike", "go": "right"}}), use_tts=False)
        bike = p.objects["bike"]
        self.assertAlmostEqual(bike.scale, objects.REF_SCALE * p.world / objects.PERSON_R["bike"], places=6)
        a_ = p.chars["A"]                                              # the rider is as big as somebody standing
        self.assertAlmostEqual(a_.ride_frame(2.0)["scale"], a_.scale, delta=0.08)
        a = p.chars["A"]
        x0 = a.draw_pos(2.0)[0]
        self.assertAlmostEqual(x0, bike.x_at(2.0) + rides.RIDES["bike"]["driver"]["hip"][0] * bike.scale, delta=1.0)
        self.assertGreater(a.draw_pos(5.0)[0], x0 + 100)             # the rider went along when the bike drove off

    def test_phases_and_hold(self):
        p = compile_scene(scene(*BIKE, {"t": 3.0, "who": "A", "getoff": {}}, {"who": "A", "say": "hi", "duration": 1.0}),
                          use_tts=False)
        a = p.chars["A"]
        self.assertIsNone(a.ride_at(0.2))
        self.assertEqual(a.ride_at(0.5)[1], "on")
        self.assertEqual(a.ride_at(2.0)[1], "riding")
        self.assertEqual(a.ride_at(3.2)[1], "off")
        self.assertIsNone(a.ride_at(3.7))
        self.assertGreaterEqual(p.speech[0]["start"], 3.0 + rides.RIDE_HOP)        # the story waits for the hop

    def test_the_hop_is_continuous(self):
        p = compile_scene(scene(*BIKE, {"t": 3.0, "who": "A", "getoff": {"side": "right"}}), use_tts=False)
        a = p.chars["A"]
        gx, gy, gscale = a.ground_state(0.4)
        x, y = a.draw_pos(0.4 + 1e-3)
        self.assertAlmostEqual(x, gx, delta=3)                       # starts where A stood
        self.assertAlmostEqual(y, gy, delta=8)
        rf = a.ride_frame(0.4 + rides.RIDE_HOP + 0.01)
        self.assertAlmostEqual(rf["scale"], rides.seat_for("bike", "driver")["r"] * p.objects["bike"].scale, delta=0.01)
        land = a.rides[0]["land_x"]
        x_end, y_end = a.draw_pos(3.0 + rides.RIDE_HOP + 0.02)
        self.assertAlmostEqual(x_end, land, delta=2)                 # ends where getoff said, and stays there
        self.assertAlmostEqual(y_end, a.y, delta=2)
        self.assertAlmostEqual(a.draw_pos(8.0)[0], land, delta=0.1)

    def test_getoff_lands_towards_the_centre_or_where_told(self):
        for side in ("left", "right"):
            p = compile_scene(scene(*BIKE, {"t": 3.0, "who": "A", "getoff": {"side": side}}), use_tts=False)
            land = p.chars["A"].rides[0]["land_x"]
            self.assertTrue(land < 540 if side == "left" else land > 540, side)
        p = compile_scene(scene(*BIKE, {"t": 3.0, "who": "A", "getoff": True}), use_tts=False)     # default side
        self.assertTrue(150 <= p.chars["A"].rides[0]["land_x"] <= 930)

    def test_two_riders_get_two_seats(self):
        chars = {"A": {"look": "boy", "slot": "left"}, "B": {"look": "aunty", "slot": "right"}}
        p = compile_scene(scene({"t": 0.1, "obj": {"kind": "auto", "at": "center"}},
                                {"t": 0.3, "who": "A", "ride": {"kind": "auto"}},
                                {"t": 0.3, "who": "B", "ride": {"kind": "auto"}}, chars=chars), use_tts=False)
        seats = {p.chars["A"].rides[0]["seat"], p.chars["B"].rides[0]["seat"]}
        self.assertEqual(seats, {"driver", "back"})

    def test_mistakes_are_warnings(self):
        p = compile_scene(scene({"t": 0.3, "who": "A", "ride": {"kind": "cow"}}, {"t": 1.0, "who": "A", "getoff": {}}),
                          use_tts=False)
        self.assertEqual(len([w for w in p.warnings if "cannot ride" in w or "not on a vehicle" in w]), 2)
        p = compile_scene(scene(*BIKE, {"t": 1.0, "who": "A", "ride": {"kind": "bike"}}), use_tts=False)
        self.assertTrue(any("already" in w for w in p.warnings))

    def test_vehicle_flip_mirrors_the_rider(self):
        p = compile_scene(scene({"t": 0.1, "obj": {"kind": "bike", "at": "right"}}, {"t": 0.4, "who": "A", "ride": {"kind": "bike"}},
                                {"t": 2.0, "obj": {"kind": "bike", "go": "left"}}), use_tts=False)
        a = p.chars["A"]
        right, left = a.ride_frame(1.8), a.ride_frame(4.5)
        self.assertGreater(right["pose"]["ra1"], 0)                  # reaching forward = to the right
        self.assertLess(left["pose"]["la1"], 0)                      # mirrored: forward = to the left
        self.assertLess(left["pose"]["look_x"], 0)

    def test_pedals_turn_with_the_cycle(self):
        p = compile_scene(scene({"t": 0.1, "obj": {"kind": "cycle", "at": "left"}}, {"t": 0.4, "who": "A", "ride": {"kind": "cycle"}},
                                {"t": 2.0, "obj": {"kind": "cycle", "go": "right"}}), use_tts=False)
        c = p.objects["cycle"]
        a = p.chars["A"]
        self.assertEqual(rides.crank_angle(c, 1.0), rides.crank_angle(c, 1.5))    # parked: pedals rest
        self.assertNotEqual(rides.crank_angle(c, 2.4), rides.crank_angle(c, 2.9))
        self.assertNotEqual(a.ride_frame(2.4)["pose"]["ll1"], a.ride_frame(2.9)["pose"]["ll1"])   # the legs follow them

    def test_camera_follows_the_rider_not_the_feet_formula(self):
        p = compile_scene(scene(*BIKE), use_tts=False)
        a = p.chars["A"]
        fx, fy = a.focus_at(2.0)
        rf = a.ride_frame(2.0)
        self.assertAlmostEqual(fx, rf["hip"][0], delta=1)
        self.assertLess(fy, rf["hip"][1])                            # above the seat, on the rider's upper body
        self.assertGreater(fy, rf["hip"][1] - 500 * rf["scale"])


class DriveInTests(unittest.TestCase):
    """`A -> ride truck enter left to center`: the vehicle drives in with the rider already inside."""

    def make(self):
        sc, warns = parse_script("CAST: L = dost, S = uncle\nSCENE: street\nL -> ride truck enter left to center\n"
                                 "L (smug): le aaya | ले आया\nL -> getoff right\nS (shock): kya | क्या\nHOOK: h\nCTA: c\n")
        self.assertEqual(warns, [])
        from studio.scene import split_scenes
        return compile_scene(split_scenes(sc)[0], use_tts=False)

    def test_no_hop_and_the_rider_goes_in_with_the_truck(self):
        p = self.make()
        truck, l = p.objects["truck"], p.chars["L"]
        ride = l.rides[0]
        self.assertTrue(ride["instant"])
        self.assertEqual(l.ride_at(ride["t0"] + 0.01)[1], "riding")              # no "on" phase
        self.assertLess(truck.x_at(ride["t0"]), 0)                                # starts off screen
        for t in (ride["t0"] + 0.5, ride["t0"] + 1.2, ride["t0"] + 1.9):
            rf = l.ride_frame(t)
            self.assertAlmostEqual(rf["hip"][0] - truck.x_at(t),
                                   rides.RIDES["truck"]["driver"]["hip"][0] * truck.scale, delta=1.0)

    def test_the_story_waits_for_the_drive_and_the_truck_is_in_front(self):
        p = self.make()
        self.assertGreaterEqual(p.speech[0]["start"], p.chars["L"].rides[0]["t0"] + 1.8)
        self.assertTrue(p.objects["truck"].front)

    def test_riders_are_drawn_over_standing_characters(self):
        from studio.script import parse_script as ps
        from studio.util import load_scene  # noqa: F401
        sc, _ = ps("CAST: L = dost, S = uncle\nSCENE: street\nL -> ride truck enter left to center\n"
                   "L (smug): le aaya | ले आया\nS (shock): kya | क्या\nHOOK: h\nCTA: c\n")
        v = make_video(sc, 216, use_tts=False)
        self.assertEqual(v.frame(3.0).size, (216, 384))
        self.assertEqual(v.frame(v.duration - 0.3).size, (216, 384))


class ScriptTests(unittest.TestCase):
    def test_words(self):
        sc, warns = parse_script("CAST: A = dost, B = aunty\nSCENE: street\nOBJ: bike enter left to center\n"
                                 "A -> ride bike\nB -> ride bike back\nA (smile): hi | हाय\nOBJ: bike go right\n"
                                 "A -> getoff left\nB -> utar\nHOOK: h\nCTA: c\n")
        self.assertEqual(warns, [])
        tl = sc["scenes"][0]["timeline"]
        self.assertEqual([e["ride"] for e in tl if "ride" in e], [{"kind": "bike"}, {"kind": "bike", "seat": "back"}])
        self.assertEqual([e["getoff"] for e in tl if "getoff" in e], [{"side": "left"}, {}])
        v = vocab()
        self.assertIn("truck", v["rides"])
        self.assertIn("getoff", v["ride_words"])

    def test_unknown_vehicle_warns(self):
        _, warns = parse_script("CAST: A = dost\nSCENE: street\nA -> ride cow\nA (smile): hi | हाय\nHOOK: h\nCTA: c\n")
        self.assertTrue(any("ride cow" in w for w in warns))

    def test_a_whole_script_renders(self):
        sc, warns = parse_script("CAST: A = dost, B = aunty\nSCENE: street\nOBJ: auto enter left to center\n"
                                 "A -> ride auto\nB -> ride auto back\nA (smile, close): chalo | चलो\nOBJ: auto go right\n"
                                 "A -> getoff\nHOOK: h\nCTA: c\n")
        self.assertEqual(warns, [])
        v = make_video(sc, 216, use_tts=False)
        for t in (0.5, 2.0, 4.0, 6.0, v.duration - 0.5):
            self.assertEqual(v.frame(t).size, (216, 384))


class RenderTests(unittest.TestCase):
    def test_every_vehicle_and_seat_renders_and_changes_the_picture(self):
        for kind, seats in rides.RIDES.items():
            for seat in seats:
                with_rider = scene({"t": 0.1, "obj": {"kind": kind, "at": "center"}},
                                   {"t": 0.3, "who": "A", "ride": {"kind": kind, "seat": seat}})
                without = scene({"t": 0.1, "obj": {"kind": kind, "at": "center"}})
                a = make_video(with_rider, 216, use_tts=False).frame(2.0).convert("RGB")
                b = make_video(without, 216, use_tts=False).frame(2.0).convert("RGB")
                self.assertIsNotNone(ImageChops.difference(a, b).getbbox(), (kind, seat))

    def test_car_and_truck_hide_the_legs(self):
        for kind in ("car", "truck"):
            p = compile_scene(scene({"t": 0.1, "obj": {"kind": kind, "at": "center"}},
                                    {"t": 0.3, "who": "A", "ride": {"kind": kind}}), use_tts=False)
            rf = p.chars["A"].ride_frame(2.0)
            sk = skeleton(rf["pose"])
            feet_y = rf["hip"][1] + max(sk["footL"][1], sk["footR"][1]) * rf["scale"]
            body_bottom = p.objects[kind].y - (44 if kind == "car" else 62) * p.objects[kind].scale
            self.assertLess(feet_y, body_bottom + 4, kind)           # the feet stay inside the body

    def test_non_riders_are_unchanged(self):
        s = scene({"t": 0.5, "who": "A", "say": "hi", "duration": 1.0})
        p = compile_scene(s, use_tts=False)
        a = p.chars["A"]
        self.assertIsNone(a.ride_frame(1.0))
        self.assertEqual(a.draw_pos(1.0), (a.x, a.y))


if __name__ == "__main__":
    unittest.main()

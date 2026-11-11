"""Inside moving vehicles (train, bus, metro, plane, car, auto), dressing a place (DRESS), the richer street / market /
office / hospital, the new places and the new people. python -m unittest discover -s tests"""
import os
import sys
import unittest

from PIL import ImageChops, ImageStat

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import decor, places_plus, script, vehicles      # noqa: E402
from studio.backgrounds import Background                    # noqa: E402
from studio.characters import LOOKS, resolve_spec            # noqa: E402
from studio.render import make_video                         # noqa: E402
from studio.scene import camera_at, compile_scene, split_scenes   # noqa: E402
from studio.script import parse_script                       # noqa: E402

TRAIN = """HOOK: Train me uncle 🚆
CAST: U = uncle, B = college_boy, T = tt
SCENE: train pahad night
U (point): Beta, window seat ka bhi niyam hota hai | बेटा, विंडो सीट का भी नियम होता है
B (shock): Kaunsa niyam? | कौनसा नियम?
T (angry): Ticket dikhao dono! | टिकट दिखाओ दोनों!
U -> run scared
CTA: c
"""


def diff(a, b):
    return sum(ImageStat.Stat(ImageChops.difference(a.convert("RGB"), b.convert("RGB"))).mean) / 3


class VehicleTests(unittest.TestCase):
    def test_the_script_words(self):
        sc, warns = parse_script(TRAIN)
        self.assertEqual(warns, [])
        self.assertEqual(sc["scenes"][0]["background"], {"type": "train", "view": "pahad", "time": "night"})
        for word, kind in (("aeroplane", "plane"), ("auto_rickshaw", "auto"), ("flight", "plane")):
            sc, warns = parse_script("HOOK: h\nCAST: A = boy\nSCENE: %s\nA: Hi | हाय\n" % word)
            self.assertEqual((warns, sc["scenes"][0]["background"]["type"]), ([], kind))

    def test_people_sit_and_stay_seated_while_they_gesture(self):
        sc, _ = parse_script(TRAIN)
        s0 = sc["scenes"][0]
        seats = {o["id"]: o for o in s0["sets"]}
        self.assertEqual(sorted(seats), ["seat_b", "seat_u"])          # the TT stands
        self.assertTrue(all(o["type"] == "berth" for o in seats.values()))
        evs = [e for e in s0["timeline"] if e.get("who") == "U"]
        self.assertEqual(evs[0].get("on"), "seat_u")                  # sits at the start
        point = next(e for e in evs if e.get("action") == "point")
        self.assertEqual(point.get("on"), "seat_u")                   # points sitting down
        run = next(e for e in evs if e.get("action") == "run")
        self.assertNotIn("on", run)                                   # gets up to run

    def test_the_view_moves_and_the_vehicle_rocks(self):
        bg = Background({"type": "train"}, 216, 384)
        self.assertIsNotNone(bg.interior)
        self.assertGreater(diff(bg.frame(0.0), bg.frame(0.4)), 0.5)   # the fields go past the windows
        sc, _ = parse_script(TRAIN)
        plan = compile_scene(split_scenes(sc)[0], use_tts=False)
        self.assertEqual(plan.vehicle, "train")
        a, b = camera_at(plan, 1.0), camera_at(plan, 1.3)
        self.assertGreater(a[0], 1.0)
        self.assertNotEqual((a[1], a[2]), (b[1], b[2]))
        self.assertTrue(any("train" in amb["path"] for amb in plan.ambience))   # you hear the train

    def test_every_vehicle_and_view_draws(self):
        for kind in vehicles.VEHICLES:
            for view in (None,) + vehicles.VIEWS[:2]:
                spec = {"type": kind}
                if view:
                    spec["view"] = view
                im = Background(spec, 108, 192).frame(0.5)
                self.assertEqual(im.size, (108, 192))


class DressTests(unittest.TestCase):
    def test_packs_pieces_none_and_unknown(self):
        items, bad = decor.words_to_items(["shaadi", "poster", "wedding", "dinosaur"])
        self.assertEqual(bad, ["dinosaur"])
        self.assertIn("garland", [k for k, _ in items])
        sc, warns = parse_script("HOOK: h\nCAST: A = boy\nSCENE: office\nDRESS: birthday, plant\nA: Hi | हाय\n")
        self.assertEqual(warns, [])
        self.assertEqual(sc["scenes"][0]["dress"], ["birthday", "plant"])
        _sc, warns = parse_script("HOOK: h\nCAST: A = boy\nSCENE: office\nDRESS: dinosaur\nA: Hi | हाय\n")
        self.assertTrue(any("DRESS" in w for w in warns))

    def test_the_pieces_hang_in_the_place(self):
        sc, _ = parse_script("HOOK: h\nCAST: A = boy\nSCENE: bank\nDRESS: independence\nA: Hi | हाय\n")
        plan = compile_scene(split_scenes(sc)[0], use_tts=False)
        kinds = {o["type"] for o in plan.sets if o.get("decor")}
        self.assertEqual(kinds, {"bunting", "flag_stand", "poster"})
        self.assertTrue(all(o.get("fit") for o in plan.sets if o.get("decor")))

    def test_auto_dressing_varies_by_video_and_stays_through_cuts(self):
        def pieces(hook):
            sc, _ = parse_script("HOOK: %s\nCAST: A = boy, B = girl\nSCENE: office\nA: Hi | हाय\nCUT\nB: Ha | हा\n" % hook)
            subs = split_scenes(sc)
            return [sorted(o["type"] for o in compile_scene(s_, use_tts=False).sets if o.get("decor")) for s_ in subs]
        seen = set()
        for i in range(8):
            a, b = pieces("video %d" % i)
            self.assertEqual(a, b)                                    # same place, same walls after a CUT
            seen.add(tuple(a))
        self.assertGreater(len(seen), 2)
        sc, _ = parse_script("HOOK: h\nCAST: A = boy\nSCENE: office\nA: Hi | हाय\nCAMERA: classic\n")
        self.assertNotIn("dress", sc["scenes"][0])                    # classic: as before
        sc, _ = parse_script("HOOK: h\nCAST: A = boy\nSCENE: office\nDRESS: none\nA: Hi | हाय\n")
        self.assertEqual(decor.pieces_for("office", sc["scenes"][0]["dress"]), [])

    def test_nothing_religious(self):
        words = " ".join(list(decor.PACKS) + list(decor.PACK_WORDS) + list(decor.PIECES)).lower()
        for w in ("diwali", "holi", "eid", "christmas", "mandir", "temple", "diya", "puja", "ganesh", "swarg"):
            self.assertNotIn(w, words)


class PlaceTests(unittest.TestCase):
    def test_new_places_and_richer_ones(self):
        for p in ("court", "dhaba", "salon", "mall", "train", "bus", "metro", "plane", "car", "auto"):
            self.assertIn(p, script.BACKGROUNDS)
        for p in places_plus.NEW:
            self.assertEqual(Background({"type": p}, 108, 192).frame(0.0).size, (108, 192))
        for p in places_plus.RICH:                                   # classic keeps the old drawing
            rich = Background({"type": p}, 108, 192).frame(0.0)
            old = Background({"type": p, "classic": True}, 108, 192).frame(0.0)
            self.assertGreater(diff(rich, old), 3.0, p)

    def test_classic_video_uses_the_old_street(self):
        text = "HOOK: h\nCAST: A = boy\nSCENE: street\nA: Hi | हाय\n"
        cine = make_video(parse_script(text)[0], 216, use_tts=False).parts[0]
        classic = make_video(parse_script(text + "CAMERA: classic\n")[0], 216, use_tts=False).parts[0]
        old = Background({"type": "street", "classic": True}, 216, 384).static
        self.assertLess(diff(classic.bg.static, old), 0.01)            # classic: the old drawing exactly
        self.assertGreater(diff(cine.bg.static, old), 3.0)


class PeopleTests(unittest.TestCase):
    def test_new_looks_and_roles(self):
        for look in ("delivery_boy", "driver", "conductor", "watchman", "landlord", "influencer", "doodhwala", "tt",
                     "bhoot", "pilot", "air_hostess"):
            self.assertIn(look, LOOKS)
            self.assertTrue(os.path.exists(os.path.join(os.path.dirname(__file__), "..", "assets", "looks",
                                                        look + ".png")))
        sc, warns = parse_script("HOOK: h\nCAST: A = autowala, B = chowkidar, C = ghost\nSCENE: street\nA: Hi | हाय\n")
        self.assertEqual(warns, [])
        self.assertEqual([sc["characters"][n]["look"] for n in "ABC"], ["driver", "watchman", "bhoot"])

    def test_a_look_brings_its_own_prop_and_face(self):
        sc, _ = parse_script("HOOK: h\nCAST: A = doodhwala, B = bhoot\nSCENE: gaon\nA: Doodh | दूध\nB: Hi | हाय\n")
        plan = compile_scene(split_scenes(sc)[0], use_tts=False)
        self.assertEqual(plan.chars["A"].state_at(0.5)["prop"], "milk_can")
        self.assertEqual(plan.chars["B"].state_at(0.0)["expression"], "evil")
        self.assertEqual(resolve_spec({"look": "bhoot"})["skin"], "ghost")
        self.assertNotIn("ghost", script.SKIN_ORDER)                # nobody else gets the ghost's skin by chance


if __name__ == "__main__":
    unittest.main()

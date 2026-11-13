"""The 2.5D style: picked per video, every place gets depth (hand-made sets or made automatically), 2d stays
exactly as it was."""
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

from studio import director, script, styles  # noqa: E402
from studio.render import Renderer, make_video  # noqa: E402

with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as _f:
    PAGE = _f.read()
SCRIPT = ("HOOK: Test 😂\nCAST: A = college_boy, B = uncle\nSCENE: {place}\n"
          "A (smile): Bhai chai pila de | भाई चाय पिला दे\nB (sly): Pehle paise | पहले पैसे\nCTA: Tag karo\n")


def one_scene(place, style=None):
    """A single-place scene from the script format (the first scene of the sequence)."""
    sc, _w = script.parse_script(SCRIPT.format(place=place))
    sub = dict(sc, **sc["scenes"][0])
    sub.pop("scenes")
    if style:
        sub["style"] = style
    return sub


class StyleWordsTests(unittest.TestCase):
    def test_names(self):
        self.assertEqual(styles.normalize("2.5D"), "2.5d")
        self.assertEqual(styles.normalize("25d"), "2.5d")
        self.assertEqual(styles.normalize("flat"), "2d")
        with self.assertRaises(ValueError):
            styles.normalize("3d")
        self.assertEqual(styles.scene_style({}), "2d")

    def test_which_set_each_place_gets(self):
        self.assertEqual(styles.preset_for(one_scene("kitchen", "2.5d")), "kitchen_25d")
        self.assertEqual(styles.preset_for(one_scene("chai_tapri", "2.5d")), "gali_25d")
        self.assertEqual(styles.preset_for(one_scene("living_room", "2.5d")), "room_25d")
        self.assertEqual(styles.preset_for(one_scene("classroom", "2.5d")), "classroom_25d")
        self.assertEqual(styles.preset_for(one_scene("office", "2.5d")), "office_25d")
        self.assertEqual(styles.preset_for(one_scene("hospital", "2.5d")), "hospital_25d")
        self.assertEqual(styles.preset_for(one_scene("graveyard", "2.5d")), "graveyard_25d")
        self.assertEqual(styles.preset_for(one_scene("taxi", "2.5d")), "car_25d")             # a vehicle's other name
        from unittest import mock
        with mock.patch.dict(styles.PLACES_25D):                                              # a place with no set:
            del styles.PLACES_25D["hostel"]                                                   # made automatically
            self.assertEqual(styles.preset_for(one_scene("hostel", "2.5d")), "auto:hostel")
        self.assertIsNone(styles.preset_for(one_scene("plain", "2.5d")))                     # stays flat
        self.assertIsNone(styles.preset_for(one_scene("kitchen")))           # 2d

    def test_every_place_has_depth_in_2_5d(self):
        from studio.style25d.autoset import build_auto, place_function
        for place in script.vocab()["places"]:
            if place in styles.FLAT_IN_25D:
                continue
            self.assertTrue(styles.has_depth(place), place)
            if place_function(place):                              # the automatic layering still works for every
                layered = build_auto(place, 0.1)                   # drawn place (a new place gets it until it has
                self.assertGreaterEqual(len(layered.back), 2, place)    # a hand-made set)

    def test_every_preset_exists(self):
        from studio.style25d.scenery import PRESETS
        for place, preset in styles.PLACES_25D.items():
            self.assertIn(preset, PRESETS, place)
            self.assertIn(place, script.vocab()["places"], place)


class ScriptTests(unittest.TestCase):
    def test_style_line(self):
        sc, w = script.parse_script(SCRIPT.format(place="kitchen").replace("CAST:", "STYLE: 2.5d\nCAST:"))
        self.assertEqual(sc.get("style"), "2.5d")
        self.assertFalse([x for x in w if "STYLE" in x])

    def test_no_style_line_is_2d(self):
        sc, _w = script.parse_script(SCRIPT.format(place="kitchen"))
        self.assertNotIn("style", sc)

    def test_flat_place_is_mentioned_but_not_a_problem_for_the_ai(self):
        text = SCRIPT.format(place="plain").replace("CAST:", "STYLE: 2.5d\nCAST:") + "CAPTION: x\n"
        _sc, w = script.parse_script(text)
        self.assertTrue(any("2.5D me flat" in x for x in w))
        _sc, w = script.parse_script(text.replace("SCENE: plain", "SCENE: office"))
        self.assertFalse(any("2.5D me flat" in x for x in w))
        self.assertFalse(any("2.5D me flat" in p for p in director.script_problems(text, "/tmp/_style25d_check.json")))

    def test_bad_style_warns(self):
        _sc, w = script.parse_script(SCRIPT.format(place="kitchen").replace("CAST:", "STYLE: 3d\nCAST:"))
        self.assertTrue(any("STYLE" in x for x in w))

    def test_examples_parse_clean(self):
        folder = os.path.join(ROOT, "scripts", "25d")
        for name in sorted(os.listdir(folder)):
            with open(os.path.join(folder, name), encoding="utf-8") as f:
                sc, w = script.parse_script(f.read())
            self.assertEqual(sc.get("style"), "2.5d", name)
            self.assertEqual([x for x in w if "Devanagari" not in x], [], name)


class DirectorTests(unittest.TestCase):
    def test_writer_prompt_per_style(self):
        self.assertEqual(director.style_prompt("2d"), "")
        self.assertIn("STYLE: 2.5d", director.style_prompt("2.5d"))

    def test_style_line_follows_the_choice(self):
        text = "HOOK: Hi\nCAST: A = boy\nSCENE: kitchen\n"
        self.assertEqual(director.with_style_line(text, "2.5d").splitlines()[1], "STYLE: 2.5d")
        self.assertNotIn("STYLE", director.with_style_line("HOOK: Hi\nSTYLE: 2.5d\nSCENE: x\n", "2d"))


class RenderTests(unittest.TestCase):
    W = 180

    def frame(self, scene, t=1.0):
        return Renderer(scene, self.W, use_tts=False).frame(t)

    def test_flat_places_render_exactly_like_2d(self):
        a = self.frame(one_scene("plain"))
        b = self.frame(one_scene("plain", "2.5d"))
        self.assertEqual(a.tobytes(), b.tobytes())

    def test_2_5d_places_look_different(self):
        for place in ("kitchen", "gully", "terrace", "room", "school", "office", "jungle"):
            a = self.frame(one_scene(place))
            b = self.frame(one_scene(place, "2.5d"))
            self.assertNotEqual(a.tobytes(), b.tobytes(), place)
            self.assertEqual(b.size, a.size)

    def test_command_line_style_wins(self):
        sc, _w = script.parse_script(SCRIPT.format(place="kitchen"))
        v = make_video(sc, self.W, use_tts=False, style="2.5d")
        self.assertTrue(v.parts[0].bd25)
        self.assertIsNone(make_video(sc, self.W, use_tts=False).parts[0].bd25)

    def test_signs_are_never_mirrored(self):
        for place in ("gully", "canteen", "school"):
            r = Renderer(dict(one_scene(place, "2.5d"), angle=1), self.W, use_tts=False)   # angle 1 = a mirrored shot
            self.assertTrue(r.plan.angle["mirror"])
            self.assertFalse(r._view25(1.0)["mirror"], place)
        for place in ("beach", "jungle"):                             # no writing: the reverse shot is mirrored
            r = Renderer(dict(one_scene(place, "2.5d"), angle=1), self.W, use_tts=False)
            self.assertTrue(r._view25(1.0)["mirror"], place)
        for place in ("office", "meeting_room"):                      # (their boards and the TV have writing)
            r = Renderer(dict(one_scene(place, "2.5d"), angle=1), self.W, use_tts=False)
            self.assertFalse(r._view25(1.0)["mirror"], place)

    def test_the_new_premium_sets(self):
        for place, preset in (("office", "office_25d"), ("meeting_room", "meeting_25d"), ("jungle", "jungle_25d"),
                              ("haunted_house", "haunted_25d"), ("bedroom", "bedroom_25d"),
                              ("street", "street_25d"), ("bus_stop", "busstop_25d"), ("market", "market_25d"),
                              ("festival_street", "festival_25d"), ("railway", "railway_25d"), ("gaon", "gaon_25d"),
                              ("hospital", "hospital_25d"), ("bank", "bank_25d"), ("police_station", "police_25d"),
                              ("court", "court_25d"), ("canteen", "canteen_25d"), ("dhaba", "dhaba_25d"),
                              ("mithai_shop", "mithai_25d"), ("mobile_shop", "mobile_25d"),
                              ("medical_store", "medical_25d"), ("salon", "salon_25d"), ("mall", "mall_25d"),
                              ("cinema", "cinema_25d"), ("balcony", "balcony_25d"), ("bathroom", "bathroom_25d"),
                              ("hostel", "hostel_25d"), ("library", "library_25d"), ("coaching", "coaching_25d"),
                              ("exam_hall", "exam_hall_25d"), ("gym", "gym_25d"), ("party", "party_25d"),
                              ("jail", "jail_25d"), ("beach", "beach_25d"), ("desert", "desert_25d"),
                              ("mountain_road", "mountain_road_25d"), ("cricket_ground", "cricket_ground_25d"),
                              ("school_ground", "school_ground_25d"), ("mandap", "mandap_25d"),
                              ("graveyard", "graveyard_25d"), ("night_road", "night_road_25d")):
            r = Renderer(one_scene(place, "2.5d"), self.W, use_tts=False)
            self.assertEqual(r.bd25.preset, preset)
            self.assertNotEqual(r.frame(1.0).tobytes(), r.frame(1.4).tobytes(), place)    # screens, fan, leaves, bats
            self.assertFalse([o for o in r.plan.sets if o.get("decor")], place)           # no auto posters on it
            sc = one_scene(place, "2.5d")
            sc["background"] = dict(sc["background"], time="night")
            self.assertEqual(Renderer(sc, self.W, use_tts=False).frame(1.0).size, r.frame(1.0).size)

    def test_2d_never_uses_the_hand_made_sets(self):
        """2D stays as it always was: the 2.5D sets (and their rules) only come with STYLE 2.5d."""
        for place in list(styles.PLACES_25D) + ["hospital", "street"]:
            r = Renderer(one_scene(place), self.W, use_tts=False)
            self.assertIsNone(r.bd25, place)
        sc = one_scene("office")
        sc["dress"] = "auto"                                              # 2D office: still dressed up as before
        self.assertTrue([o for o in Renderer(sc, self.W, use_tts=False).plan.sets if o.get("decor")])
        sc = dict(one_scene("office", "2.5d"), dress="auto")              # the hand-made set: dressed already
        self.assertFalse([o for o in Renderer(sc, self.W, use_tts=False).plan.sets if o.get("decor")])

    def test_road_sets_keep_their_traffic(self):
        """The hand-made street and bus stop still have the place's own cars, clouds and birds; the bazaar's
        sabziwala stands behind his stall's counter."""
        for place in ("street", "bus_stop", "mountain_road"):
            names = [ly.name for ly in Renderer(one_scene(place, "2.5d"), self.W, use_tts=False).bd25.layered.back]
            self.assertIn("ambient", names, place)
            self.assertIn("sky_life", names, place)
        names = [ly.name for ly in Renderer(one_scene("market", "2.5d"), self.W, use_tts=False).bd25.layered.back]
        self.assertNotIn("ambient", names)
        s = ("HOOK: x\nSTYLE: 2.5d\nCAST: A = sabziwala, B = aunty\nSCENE: market\n"
             "B (angry): Tamatar itne mehenge? | टमाटर\nA (smile): Aunty, sone ke hain! | आंटी\nCTA: tag\n")
        sc, _w = script.parse_script(s)
        r = make_video(sc, self.W, use_tts=False)
        r = getattr(r, "parts", [r])[0]
        self.assertEqual(r.plan.counter_mode, "preset")
        self.assertTrue(r.plan.counters)
        self.assertEqual(len([sp for sp in r.bd25.layered.sprites if sp.name == "counter"]), 3)

    def test_counter_sets(self):
        """In the hand-made hospital, bank, police station, court and canteen the person of the place stands behind
        their counter (the same spot as in 2D) and the counter is a piece the people are sorted with."""
        for place, cast, n in (("hospital", "A = receptionist, B = uncle", 1), ("bank", "A = cashier, B = aunty", 1),
                               ("police_station", "A = police, B = boy", 1), ("court", "A = judge, B = boy gawah", 3),
                               ("canteen", "A = chaiwala, B = college_boy", 1)):
            s = ("HOOK: x\nSTYLE: 2.5d\nCAST: %s\nSCENE: %s\nB (angry): Suniye! | सुनिए\nA (smile): Ji? | जी\n"
                 "CTA: tag\n") % (cast, place)
            sc, _w = script.parse_script(s)
            r = make_video(sc, self.W, use_tts=False)
            r = getattr(r, "parts", [r])[0]
            self.assertEqual(r.plan.counter_mode, "preset", place)
            self.assertTrue(r.plan.counters, place)
            self.assertEqual(len([sp for sp in r.bd25.layered.sprites if sp.name == "counter"]), n, place)
            self.assertEqual(r.frame(1.0).size, (self.W, self.W * 16 // 9), place)

    def test_jail_door_on_the_hand_made_jail(self):
        """The jail's barred door (open / broken) is still the set piece, over the same place as in 2D."""
        for state in ("", " broken"):
            s = ("HOOK: x\nSTYLE: 2.5d\nCAST: A = chor, B = police\nSCENE: jail\nOBJ: jail_door%s\n"
                 "A (sad): Saheb! | साहब\nB (angry): Chup! | चुप\nCTA: tag\n") % state
            sc, _w = script.parse_script(s)
            r = make_video(sc, self.W, use_tts=False)
            r = getattr(r, "parts", [r])[0]
            self.assertEqual(r.bd25.preset, "jail_25d")
            self.assertTrue([o for o in r.plan.sets if o.get("type") == "jail_door"])
            self.assertEqual(r.frame(1.0).size, (self.W, self.W * 16 // 9))

    def test_every_place_has_a_hand_made_set(self):
        """In 2.5D every studio place is a hand-made set (vehicles included); only your own photo and the plain
        colour stay flat."""
        left = [p for p in script.vocab()["places"]
                if p not in styles.PLACES_25D and p not in styles.FLAT_IN_25D]
        self.assertEqual(left, [])
        self.assertEqual(styles.FLAT_IN_25D, {"image", "plain"})

    def test_vehicles_in_2_5d(self):
        """Inside a vehicle the view outside slides past in depth layers, the seats and the rocking stay; the view and
        time words still work; 2D vehicles are as they were."""
        for words in ("train", "bus city night", "metro", "plane", "car pahad", "auto"):
            sc = one_scene(words.split()[0], "2.5d")
            bg = dict(sc["background"])
            if len(words.split()) > 1:
                bg["view"] = words.split()[1]
            if "night" in words:
                bg["time"] = "night"
            r = Renderer(dict(sc, background=bg), self.W, use_tts=False)
            kind = words.split()[0]
            self.assertEqual(r.bd25.preset, kind + "_25d")
            self.assertTrue([ly for ly in r.bd25.layered.back if ly.name == "view"], words)
            self.assertEqual(r.plan.vehicle, kind)
            self.assertTrue([o for o in r.plan.sets if o.get("type") in ("berth", "bus_seat", "metro_seat",
                                                                          "plane_seat", "car_seat", "auto_seat")])
            self.assertNotEqual(r.frame(1.0).tobytes(), r.frame(1.4).tobytes(), words)   # the view slides past
            self.assertIsNone(Renderer(one_scene(kind), self.W, use_tts=False).bd25)    # 2D: as before

    def test_people_stand_on_the_footpath(self):
        """On the road sets the people's feet (y 1700) are on the near footpath, drawn after the traffic: the cars
        pass behind them, as big as their distance makes them."""
        from studio.objects import PERSON_R, REF_SCALE
        for place in ("street", "bus_stop", "mountain_road", "night_road"):
            r = Renderer(one_scene(place, "2.5d"), self.W, use_tts=False)
            ground = r.bd25.layered.ground
            self.assertLess(ground, 1700, place)                   # the footpath starts before the feet
            names = [ly.name for ly in r.bd25.layered.back]
            near = next(i for i, n in enumerate(names) if n in ("footpath", "shoulder"))
            moving = [i for i, n in enumerate(names) if n in ("ambient", "cars")]
            self.assertTrue(moving and max(moving) < near, place)
        for place, preset in (("street", "street_road_25d"), ("bus_stop", "busstop_road_25d"), ("night_road", None)):
            s = ("HOOK: x\nSTYLE: 2.5d\nCAST: A = boy, B = autowala\nSCENE: %s\nOBJ: auto right\n"
                 "A: Bhaiya chaloge? | भैया\nB: Haan | हाँ\n") % place
            sc, _w = script.parse_script(s)
            sub = dict(sc, **sc["scenes"][0]) if sc.get("scenes") else sc
            sub.pop("scenes", None)
            self.assertEqual(styles.preset_for(sub), preset, place)         # with its vehicle: on the road
        lane, horizon = 1470, 860
        car = styles.SET_AMBIENT["street_25d"][-1]
        self.assertEqual(car[1], lane)
        self.assertAlmostEqual(car[2]["car"], REF_SCALE * (lane - horizon) / (1700.0 - horizon) / PERSON_R["car"])

    def test_premium_sets_move(self):
        r = Renderer(one_scene("room", "2.5d"), self.W, use_tts=False)
        self.assertNotEqual(r.frame(1.0).tobytes(), r.frame(1.03).tobytes())       # the fan turns, the TV flickers

    def test_auto_place_at_night_and_in_a_close_shot(self):
        from unittest import mock
        with mock.patch.dict(styles.PLACES_25D):                  # (every place has a hand-made set: take two away)
            for place in ("street", "hostel"):
                del styles.PLACES_25D[place]
                sc = one_scene(place, "2.5d")
                sc["background"] = dict(sc["background"], time="night")
                r = Renderer(dict(sc, angle=3), self.W, use_tts=False)
                self.assertTrue(r.bd25.preset.startswith("auto:"))
                self.assertEqual(r.frame(1.0).size, self.frame(one_scene(place)).size)


class PeopleTests(unittest.TestCase):
    NEW_LOOKS = ("pandit", "police", "doctor", "chaiwala", "madam", "dulha", "dulhan", "gym_bro")

    def test_new_looks_everywhere(self):
        from studio.characters import LOOKS
        v = script.vocab()
        for look in self.NEW_LOOKS:
            self.assertIn(look, LOOKS)
            self.assertIn(look, v["looks"])
            self.assertTrue(os.path.isfile(os.path.join(ROOT, "assets", "looks", look + ".png")), look)
        self.assertIn("madam", script.FEMALE_LOOKS)
        self.assertIn("dulhan", script.FEMALE_LOOKS)
        self.assertEqual(script.ROLE_LOOKS["policewala"], "police")

    def test_cast_line_picks_a_new_look(self):
        sc, w = script.parse_script(SCRIPT.format(place="mandap").replace("A = college_boy, B = uncle",
                                                                         "A = dulha, B = pujari"))
        self.assertEqual((sc["characters"]["A"]["look"], sc["characters"]["B"]["look"]), ("dulha", "pandit"))

    def test_shading_keeps_the_shape(self):
        from PIL import Image, ImageDraw
        from studio.style25d.shading import volume
        im = Image.new("RGBA", (120, 300), (0, 0, 0, 0))
        ImageDraw.Draw(im).rounded_rectangle([20, 10, 100, 290], 30, fill=(80, 130, 200, 255))
        out = volume(im, 1.0, -1, (255, 250, 240))
        self.assertEqual(out.getchannel("A").tobytes(), im.getchannel("A").tobytes())
        left, right = out.getpixel((26, 150)), out.getpixel((94, 150))
        self.assertGreater(sum(left[:3]), sum(right[:3]))            # lit from the left: the right side is darker


class PageTests(unittest.TestCase):
    def test_page_knows_the_2_5d_places(self):
        m = re.search(r"const STYLE_PLACES = (\[[^\]]*\]);", PAGE)
        self.assertEqual(sorted(json.loads(m.group(1))), sorted(styles.PLACES_25D))

    def test_page_sends_the_style_and_the_workflow_takes_it(self):
        with open(os.path.join(ROOT, ".github", "workflows", "render.yml"), encoding="utf-8") as f:
            flow = f.read()
        self.assertIn('if (currentStyle() === "2.5d") inputs.style = "2.5d";', PAGE)
        self.assertIn("      style:\n", flow)
        self.assertIn("--style $STYLE", flow)
        self.assertIn('--style "$WRITER_STYLE"', flow)
        options = re.search(r"      style:.*?options: (\[[^\]]*\])", flow, re.S).group(1)
        for v in re.findall(r'name="style" value="([^"]+)"', PAGE):
            self.assertIn('"%s"' % v, options)

    def test_two_prompt_copy_buttons(self):
        self.assertIn('id="copyPrompt"', PAGE)
        self.assertIn('id="copyPrompt25"', PAGE)
        self.assertIn('"SCRIPT_PROMPT_25D.md"', PAGE)
        self.assertTrue(os.path.isfile(os.path.join(ROOT, "SCRIPT_PROMPT_25D.md")))

    def test_page_lint_accepts_the_style_line(self):
        self.assertIn('"STYLE"', PAGE[PAGE.index("const HEADERS"):PAGE.index("const HEADERS") + 300])

    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_builder_writes_the_style_line(self):
        a = PAGE.index("// ---------------------------------------------------------------- builder (pure")
        b = PAGE.index("// ---------------------------------------------------------------- builder end")
        vocab = re.search(r'id="vocab">(.*?)</script>', PAGE, re.S).group(1)
        js = ("const V = %s;\n" % vocab + PAGE[a:b] +
              "const s = buildScript('Papa: Ghar aao | घर आओ\\nBeta: Ji papa | जी पापा', {place: 'kitchen', cast: []}, "
              "'2.5d').script;\nconsole.log(JSON.stringify([s.split('\\n')[1], styleOf(s), "
              "withStyle(s, '2d').includes('STYLE')]));")
        out = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(json.loads(out.stdout), ["STYLE: 2.5d", "2.5d", False])


if __name__ == "__main__":
    unittest.main()

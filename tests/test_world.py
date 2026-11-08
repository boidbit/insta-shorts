"""Set pieces (sofa, door, lights), places with time / weather, effects and throws.
python -m unittest discover -s tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio.render import Renderer                    # noqa: E402
from studio.scene import compile_scene, split_scenes  # noqa: E402
from studio.script import parse_script                # noqa: E402

ROOM = """HOOK: Raat ko 2 baje 😬
CAST: A = boy, B = aunty
SCENE: room night
OBJ: sofa left
OBJ: door right
LIGHTS: off
A (scared, sweat): Shhh... | श्श्श...
A -> sit sofa
CUT
B (angry, point): Kahan the? | कहाँ थे?
LIGHTS: on
CUT
A (nervous): Library me | लाइब्रेरी में
CTA: Tag karo 👇
"""

JUNGLE = """HOOK: Jungle 😱
CAST: A = college_boy, B = college_boy glasses chubby
SCENE: jungle night fog
A (scared): Awaaz aayi? | आवाज़ आई?
B (think, question): Pet bol raha hai | पेट बोल रहा है
A -> throw B angry
B (dizzy, thud): Aaah! | आह!
CTA: Tag karo 👇
"""


def plans(text):
    scene, warns = parse_script(text)
    return scene, warns, [compile_scene(s, use_tts=False) for s in split_scenes(scene)]


class SetPieceTests(unittest.TestCase):
    def test_sets_are_placed_and_carried_into_every_shot(self):
        scene, warns, ps = plans(ROOM)
        self.assertEqual(warns, [])
        self.assertEqual(scene["scenes"][0]["background"], {"type": "room", "time": "night"})
        for p in ps:
            self.assertEqual(sorted(o["type"] for o in p.sets), ["door", "sofa"])

    def test_sit_on_a_sofa(self):
        scene, _, ps = plans(ROOM)
        ev = next(e for e in scene["scenes"][0]["timeline"] if e.get("action") == "sit")
        self.assertEqual(ev["on"], "sofa")
        self.assertIn("hold", ev)

    def test_lights_stay_off_after_a_cut_until_switched_on(self):
        scene, _, ps = plans(ROOM)
        self.assertEqual(scene["scenes"][1].get("lights"), "off")      # still dark in the next shot
        self.assertNotIn("lights", scene["scenes"][2])                  # switched on in shot 2
        shots = split_scenes(scene)
        self.assertLess(Renderer(shots[1], width=270, use_tts=False)._light_level(0.5), 0.5)
        self.assertEqual(Renderer(shots[2], width=270, use_tts=False)._light_level(0.5), 1.0)

    def test_set_piece_frame_renders(self):
        scene, _, _ = plans(ROOM)
        img = Renderer(split_scenes(scene)[0], width=270, use_tts=False).frame(2.0)
        self.assertEqual(img.size[1] * 9, img.size[0] * 16)


class WorldTests(unittest.TestCase):
    def test_place_time_weather(self):
        scene, warns, ps = plans(JUNGLE)
        self.assertEqual(warns, [])
        self.assertEqual(scene["background"] if "background" in scene else scene["scenes"][0]["background"],
                         {"type": "jungle", "time": "night", "weather": ["fog"]})
        self.assertTrue(any(fx["type"] == "fog" for fx in ps[0].effects))

    def test_throw_hits_before_the_next_line(self):
        _, _, ps = plans(JUNGLE)
        p = ps[0]
        proj = next(fx for fx in p.effects if fx["type"] == "projectile")
        self.assertEqual((proj["src"], proj["dst"]), ("A", "B"))
        aah = next(sp for sp in p.speech if sp["text"] == "Aaah!")
        self.assertLessEqual(proj["to"], aah["start"])                   # THAK! first, then "Aaah!"
        self.assertTrue(any(fx["type"] == "pow" for fx in p.effects))

    def test_effect_words_on_lines(self):
        _, _, ps = plans(JUNGLE)
        kinds = {fx["type"] for fx in ps[0].effects}
        self.assertIn("question", kinds)


ANIMALS = """HOOK: Kutte ne sach bol diya 🐶
CAST: A = papa moustache, B = kutta brown, C = tota
SCENE: kitchen
A (angry, point): Samosa kisne khaya? | समोसा किसने खाया?
B (wag, smile): Bhau! Tote ne! | भौ! तोते ने!
C (fly, grin): Hehe | हेहे
CTA: Tag karo 👇
"""


class AnimalTests(unittest.TestCase):
    def test_animal_cast_words(self):
        scene, warns = parse_script(ANIMALS)
        self.assertEqual(warns, [])
        self.assertEqual(scene["characters"]["B"]["kind"], "dog")
        self.assertEqual(scene["characters"]["C"]["kind"], "parrot")
        self.assertIsInstance(scene["characters"]["B"]["color"], list)     # brown -> RGB for the animal rig

    def test_animals_render_and_talk(self):
        scene, _ = parse_script(ANIMALS)
        r = Renderer(split_scenes(scene)[0], width=270, use_tts=False)
        sp = next(x for x in r.plan.speech if x["who"] == "B")
        img = r.frame((sp["start"] + sp["end"]) / 2)
        self.assertEqual(img.size, (270, 480))


UI = """HOOK: Salary aayi aur gayi 💸
CAST: A = office_guy glasses
SCENE: office
NOTIFY: Bank | Salary credited | Balance: Rs 50,012
A (excited, jump): Salary aa gayi! | सैलरी आ गई!
COUNTER: Balance 50000 -> 12
LOADING: Dimaag loading...
TIMECARD: 5 minute baad...
CHAPTER: Chapter 2 | EMI ka din
A (dead, fall, thud): Barah rupaye | बारह रुपये
ENDCARD: Follow karo | @desitoons
CTA: Tag karo 👇
"""


class UiTests(unittest.TestCase):
    def test_ui_lines(self):
        scene, warns = parse_script(UI)
        self.assertEqual(warns, [])
        tl = scene["timeline"] if "timeline" in scene else scene["scenes"][0]["timeline"]
        ui = [e["overlay"] for e in tl if "overlay" in e and e["overlay"].get("type")]
        self.assertEqual([o["type"] for o in ui], ["notification", "counter", "loading", "timecard", "chapter", "endcard"])
        self.assertEqual(ui[0]["app"], "Bank")
        self.assertEqual((ui[1]["start"], ui[1]["end"], ui[1]["label"]), (50000, 12, "Balance"))
        cta = next(e["overlay"] for e in tl if "overlay" in e and e["overlay"].get("style") == "card")
        self.assertGreater(cta["pos"][1], 1000)                             # under the end card, not on it

    def test_ui_frames_render(self):
        scene, _ = parse_script(UI)
        r = Renderer(split_scenes(scene)[0], width=270, use_tts=False)
        for o in r.plan.overlays:
            if o.get("type"):
                r.frame(float(o["from"]) + 0.5)

    def test_bad_counter_warns(self):
        _, warns = parse_script(UI.replace("Balance 50000 -> 12", "Balance"))
        self.assertTrue(any("COUNTER" in w for w in warns))


class SoundTests(unittest.TestCase):
    def test_music_mood_and_ambience(self):
        text = ROOM.replace("SCENE: room night", "SCENE: room night\nMUSIC: sad\nAMBIENCE: rain")
        text = text.replace("(scared, sweat)", "(scared, sweat, knock)")
        scene, warns = parse_script(text)
        self.assertEqual(warns, [])
        self.assertEqual((scene["music"]["style"], scene["music"]["bpm"]), ("sad", 72))
        self.assertIn("seed", scene["music"])
        self.assertTrue(all(sc.get("ambience") == ["rain"] for sc in scene["scenes"]))   # CUTs keep the sound
        from studio.render import Sequence
        seq = Sequence(scene, width=270, use_tts=False)
        self.assertEqual(len(seq.ambience), 3)
        cmd = " ".join(seq.ffmpeg_cmd("x.mp4"))
        self.assertIn("-stream_loop -1", cmd)
        self.assertIn("knock", cmd)

    def test_rain_place_brings_rain_sound(self):
        scene, _ = parse_script(JUNGLE.replace("jungle night fog", "street rain"))
        p = compile_scene(split_scenes(scene)[0], use_tts=False)
        self.assertEqual(len(p.ambience), 1)

    def test_bad_ambience_warns(self):
        _, warns = parse_script(ROOM.replace("SCENE: room night", "SCENE: room night\nAMBIENCE: disco"))
        self.assertTrue(any("AMBIENCE" in w for w in warns))


if __name__ == "__main__":
    unittest.main()

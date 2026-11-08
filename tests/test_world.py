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


class VideoOptionTests(unittest.TestCase):
    """The studio page's "Dialogue text" and "Hook card" options."""

    def plan(self, **opt):
        from studio.scene import apply_options
        scene, _ = parse_script(JUNGLE)
        return scene, [compile_scene(s, use_tts=False) for s in split_scenes(apply_options(scene, **opt))]

    def test_default_is_bubbles(self):
        _, ps = self.plan()
        self.assertTrue(all(sp["bubble"] for sp in ps[0].speech))
        self.assertFalse(any(o.get("style") == "subtitle" for o in ps[0].overlays))

    def test_subtitle_both_none(self):
        _, ps = self.plan(dialogue="subtitle")
        self.assertFalse(any(sp["bubble"] for sp in ps[0].speech))
        subs = [o for o in ps[0].overlays if o.get("style") == "subtitle"]
        self.assertEqual(len(subs), len(ps[0].speech))
        self.assertEqual(subs[0]["pos"], "lower")               # above Instagram's caption area
        _, ps = self.plan(dialogue="both")
        self.assertTrue(all(sp["bubble"] for sp in ps[0].speech))
        self.assertEqual(len([o for o in ps[0].overlays if o.get("style") == "subtitle"]), len(ps[0].speech))
        _, ps = self.plan(dialogue="none")
        self.assertFalse(any(sp["bubble"] for sp in ps[0].speech))
        self.assertFalse(any(o.get("style") == "subtitle" for o in ps[0].overlays))

    def test_hook_first_delays_the_story(self):
        from studio.scene import HOOK_LEAD, apply_options
        _, base = self.plan()
        scene, ps = self.plan(hook="first")
        self.assertAlmostEqual(ps[0].speech[0]["start"], base[0].speech[0]["start"] + HOOK_LEAD, places=2)
        hook = next(o for o in apply_options(scene, hook="first")["overlays"] if o["style"] == "hook")
        self.assertLessEqual(hook["to"], ps[0].speech[0]["start"])
        self.assertTrue(any(fx["t"] == 0.0 for fx in ps[0].sfx))      # the whoosh still comes with the hook card

    def test_hook_off(self):
        from studio.scene import apply_options
        scene, _ = parse_script(JUNGLE)
        self.assertFalse(any(o.get("style") == "hook" for o in apply_options(scene, hook="off")["overlays"]))
        self.assertTrue(any(o.get("style") == "hook" for o in scene["overlays"]))     # the original is untouched

    def test_page_and_workflow_send_the_options(self):
        root = os.path.join(os.path.dirname(__file__), "..")
        page = open(os.path.join(root, "index.html"), encoding="utf-8").read()
        flow = open(os.path.join(root, ".github", "workflows", "render.yml"), encoding="utf-8").read()
        for opt in ("dialogue", "intro"):
            self.assertIn('id="%s"' % opt, page)
            self.assertIn("%s: $(\"%s\").value" % (opt, opt), page)
            self.assertIn("      %s:\n" % opt, flow)
        self.assertIn("--dialogue $DIALOGUE --hook $INTRO", flow)

    @unittest.skipUnless(__import__("importlib").util.find_spec("yaml"), "needs PyYAML")
    def test_workflow_accepts_every_value_the_page_sends(self):
        """A bare `off` in YAML is the boolean false, so GitHub refused intro=off. Every choice must be a string,
        and every <option> of the page's selects must be one of the workflow's choices."""
        import re
        import yaml
        root = os.path.join(os.path.dirname(__file__), "..")
        page = open(os.path.join(root, "index.html"), encoding="utf-8").read()
        flow = yaml.safe_load(open(os.path.join(root, ".github", "workflows", "render.yml"), encoding="utf-8"))
        inputs = (flow.get("on") or flow.get(True))["workflow_dispatch"]["inputs"]
        for name, spec in inputs.items():
            for o in spec.get("options", []):
                self.assertIsInstance(o, str, (name, o))
        for sel in ("dialogue", "intro", "hook", "tone"):
            m = re.search(r'<select id="%s">(.*?)</select>' % sel, page, re.S)
            self.assertTrue(m, sel)
            for v in re.findall(r'<option value="([^"]+)"', m.group(1)):
                self.assertIn(v, inputs[sel]["options"], (sel, v))


class VoiceTests(unittest.TestCase):
    def test_interrupt_cuts_the_other_line(self):
        text = JUNGLE.replace("B (think, question):", "B (interrupt, think, question):")
        scene, warns = parse_script(text)
        self.assertEqual(warns, [])
        p = compile_scene(split_scenes(scene)[0], use_tts=False)
        a, b = p.speech[0], p.speech[1]
        self.assertLess(b["start"], compile_scene(split_scenes(parse_script(JUNGLE)[0])[0], use_tts=False)
                        .speech[0]["end"])                               # B starts before A would have finished
        self.assertAlmostEqual(a["end"], b["start"] + 0.1, places=3)    # A is cut off
        self.assertIn("cut", a)

    def test_cut_line_is_trimmed_in_the_mix(self):
        from studio.render import Renderer
        scene, _ = parse_script(JUNGLE.replace("B (think, question):", "B (interrupt, think, question):"))
        r = Renderer(split_scenes(scene)[0], width=270, use_tts=False)
        r.speech[0]["audio"] = __file__                                  # any input: only the filter text is checked
        self.assertIn("atrim=0:%.2f" % r.speech[0]["cut"], " ".join(r.ffmpeg_cmd("x.mp4")))

    @unittest.skipUnless(__import__("shutil").which("ffmpeg"), "needs ffmpeg")
    def test_dead_air_is_trimmed(self):
        import subprocess
        import tempfile
        from studio import audio
        d = tempfile.mkdtemp()
        wav = os.path.join(d, "line.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono:d=0.5",
                        "-f", "lavfi", "-i", "sine=f=300:d=1.0:sample_rate=24000", "-f", "lavfi", "-i",
                        "anullsrc=r=24000:cl=mono:d=0.6", "-filter_complex", "[0][1][2]concat=n=3:v=0:a=1", wav],
                       check=True)
        self.assertLess(audio.audio_duration(audio.trim_silence(wav)), 1.25)

    def test_emotion_shifts_the_edge_voice(self):
        from studio import audio
        self.assertEqual(audio.shift_value("+0%", audio.EMOTION_VOICE["angry"][0], "%"), "+8%")
        self.assertEqual(audio.shift_value("-14Hz", audio.EMOTION_VOICE["sad"][1], "Hz"), "-22Hz")


GYM = """HOOK: Gym ka pehla din 💪
CAST: A = college_boy chubby, B = boy spiky
SCENE: gym
B (reveal, smug): Aaj se roz gym! | आज से रोज़ जिम!
A (lift_weights, determined): Dekh mera form | देख मेरा फॉर्म
A -> fall shock slowmo thud
A -> freeze
NARRATOR: Haan, ye main hoon | हाँ, ये मैं हूँ
B (laugh, zoom): Pehla aur aakhri din | पहला और आखिरी दिन
CTA: Tag karo 👇
"""


class TimeTests(unittest.TestCase):
    def setUp(self):
        scene, self.warns = parse_script(GYM)
        self.r = Renderer(split_scenes(scene)[0], width=270, use_tts=False)

    def test_slowmo_and_freeze_make_the_video_longer(self):
        self.assertEqual(self.warns, [])
        kinds = [w[0] for w in self.r.plan.warps]
        self.assertEqual(kinds, ["slow", "freeze"])
        self.assertGreater(self.r.duration, self.r.plan.duration + 2.5)

    def test_narrator_speaks_over_the_freeze(self):
        slow, frz = self.r.plan.warps
        narr = next(sp for sp in self.r.speech if sp["who"] == "NARRATOR")
        self.assertAlmostEqual(narr["start"], self.r.warp.real(frz[1]), places=3)       # when the picture stops
        self.assertGreaterEqual(frz[2], 1.2)
        b = next(sp for sp in self.r.speech if sp["who"] == "B" and sp["start"] > narr["start"])
        self.assertGreater(b["start"], narr["start"] + frz[2] - 0.1)                   # B after the freeze
        scratch = [fx for fx in self.r.sfx if fx["path"].endswith("record_scratch.wav")]
        self.assertEqual(len(scratch), 1)

    def test_freeze_frame_is_grey_and_shows_the_subtitle(self):
        slow, frz = self.r.plan.warps
        T = self.r.warp.real(frz[1]) + 0.5
        ts, style = self.r.warp.at(T)
        self.assertEqual(style, "grey")
        img = self.r.frame(T)
        px = img.convert("RGB").getpixel((5, 5))
        self.assertLess(max(px) - min(px), 25)                                         # almost no colour

    def test_zoom_and_reveal_keep_the_auto_camera(self):
        zooms = [seg[3] for seg in self.r.plan.cam_segments]
        self.assertIn(1.8, zooms)                                                       # reveal starts close
        self.assertIn(1.75, zooms)                                                      # zoom on B


class NightRoadTests(unittest.TestCase):
    def test_parallax_layers_and_front_poles(self):
        from studio.backgrounds import Background, NIGHT_LAYER_SPEEDS
        bg = Background({"type": "night_road", "scroll": 220}, 270, 480)
        self.assertEqual(len(bg.layers), len(NIGHT_LAYER_SPEEDS))
        self.assertTrue(bg.foreground(0.0))                       # street poles in front of the people
        a, b = bg.frame(0.0), bg.frame(1.0)
        self.assertNotEqual(a.tobytes(), b.tobytes())             # it scrolls

    def test_foreground_props_on_request(self):
        from studio.backgrounds import Background
        self.assertEqual(Background({"type": "kitchen"}, 270, 480).foreground(0.0), [])
        self.assertEqual(len(Background({"type": "kitchen", "foreground": ["table"]}, 270, 480).foreground(0.0)), 1)


class NaturalActingTests(unittest.TestCase):
    """The user's notes on the first videos: people jumped through whole lines, were small next to the furniture,
    a talking dog sat at the bottom of the screen, a `wait` before a line did nothing."""

    def test_a_jump_said_with_a_line_happens_once_then_talks(self):
        scene, _ = parse_script("HOOK: h\nCAST: A = boy, B = girl\nSCENE: office\n"
                                "A (jump, excited): Sach me sir? Teen saal se ek bhi chhutti nahi li, nabbe pending "
                                "hain! | सच में सर? तीन साल से एक भी छुट्टी नहीं ली, नब्बे पेंडिंग हैं!\nCTA: c\n")
        p = compile_scene(split_scenes(scene)[0], use_tts=False)
        a = p.chars["A"]
        sp = a.speech[0]
        self.assertEqual(a.state_at(sp["start"] + 0.3)["action"], "jump")
        self.assertEqual(a.state_at(sp["start"] + 2.0)["action"], "talk")        # settled, same excited face
        self.assertEqual(a.state_at(sp["start"] + 2.0)["expression"], "excited")

    def test_people_are_bigger_than_the_painted_place_in_medium_shots(self):
        scene, _ = parse_script(ROOM)
        p = compile_scene(split_scenes(scene)[0], use_tts=False)
        self.assertGreaterEqual(p.chars["A"].scale, 1.2)
        self.assertTrue(all(o.get("scale", 1.0) >= 1.2 for o in p.sets))          # the sofa grows with them

    def test_camera_looks_at_a_dog_lower_than_at_a_person(self):
        scene, _ = parse_script(ANIMALS)
        p = compile_scene(split_scenes(scene)[0], use_tts=False)
        dog, papa = p.chars["B"], p.chars["A"]
        self.assertGreater(dog.focus_at(1.0)[1], papa.focus_at(1.0)[1] + 300)

    def test_a_wait_before_the_first_line_is_kept(self):
        base = "HOOK: h\nCAST: A = boy\nSCENE: room\n%sA (smile): Haan | हाँ\nCTA: c\n"
        p0 = compile_scene(split_scenes(parse_script(base % "")[0])[0], use_tts=False)
        p1 = compile_scene(split_scenes(parse_script(base % "wait 1\n")[0])[0], use_tts=False)
        self.assertAlmostEqual(p1.speech[0]["start"] - p0.speech[0]["start"], 1.0, places=2)


if __name__ == "__main__":
    unittest.main()

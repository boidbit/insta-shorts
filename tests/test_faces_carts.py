"""Real-world sizes inside the vehicles and on the road, the street-food carts (thela) and their people, a face card
for every character (eyes, lips, ears, marks, beards, moustaches, new hair, jaws) and saved characters (@name).
python -m unittest discover -s tests"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import objects, vehicles                                  # noqa: E402
from studio.backgrounds import Background, TRAFFIC_NEW                # noqa: E402
from studio.characters import (FACE_PARTS, FACE_WORDS, HAIR_STYLES, LOOKS, MARKS, build_character,   # noqa: E402
                               face_word)
from studio.scene import compile_scene, split_scenes                  # noqa: E402
from studio.script import parse_script, vocab                         # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")


def cast(words, extra=""):
    sc, warns = parse_script("HOOK: h\nCAST: A = %s\nSCENE: street\n%sA: Hi | हाय\n" % (words, extra))
    return sc["characters"]["A"], warns


def ops_of(spec, expr="smile"):
    ops, _ = build_character(spec, {}, expr, 0.0, 0.0, 540, 1700)
    return ops


class RealSizes(unittest.TestCase):
    def test_a_seated_head_is_in_the_window(self):
        # a seated person's head is around y 980-1180 (seat at ~1520): every vehicle's windows reach it
        for kind, (top, bot) in vehicles.BANDS.items():
            self.assertLess(top, 1000, kind)
            self.assertGreater(bot, 1170, kind)
            inner = vehicles.inside(kind, 0.25)
            x = 540 if kind == "auto" else {"plane": 220, "metro": 260, "car": 260, "bus": 200}.get(kind, 300)
            y = (top + bot) / 2.0
            self.assertEqual(inner.getpixel((int(x * 0.25), int(y * 0.25)))[3], 0, kind)     # see-through there
        wall = vehicles.inside("train", 0.25).getpixel((int(300 * 0.25), int(760 * 0.25)))
        self.assertEqual(wall[3], 255)                                # the old window height is wall now
        self.assertGreater(vehicles.FLOOR_Y, 1500)                    # the wall stands right behind the seats

    def test_the_view_moves_down_with_the_windows(self):
        _sky, layers = vehicles.outside("gaon", 0.25, kind="train")
        _sky, old = vehicles.outside("gaon", 0.25)
        lo = [l.getchannel("A").getbbox()[1] for l, _ in layers]
        hi = [l.getchannel("A").getbbox()[1] for l, _ in old]
        self.assertTrue(all(a > b for a, b in zip(lo, hi)))

    def test_road_traffic_is_people_sized_in_the_new_camera_only(self):
        cine = Background({"type": "street"}, 108, 192).ambient
        classic = Background({"type": "street", "classic": True}, 108, 192).ambient
        self.assertIn(TRAFFIC_NEW["street"], cine)
        old = next(a for a in classic if a[0] == "traffic")
        self.assertLess(old[2], 0.5)                                  # classic: the little toy cars as before
        self.assertGreater(TRAFFIC_NEW["street"][2], 2 * old[2])
        frames = [Background({"type": "street"}, 216, 384).frame(t) for t in (0.5, 2.5)]
        self.assertEqual(frames[0].size, (216, 384))


class Carts(unittest.TestCase):
    def test_every_cart_draws_with_wheels(self):
        self.assertEqual(len(objects.THELAS), 6)
        for k in objects.THELAS:
            im, _anchor, wheels = objects.sprite(k, 0.3)
            self.assertIsNotNone(im)
            self.assertEqual(len(wheels), 2)
            self.assertIn(k, objects.PERSON_R)

    def test_the_script_picks_the_cart(self):
        sc, warns = parse_script("HOOK: h\nCAST: K = kulchewala\nSCENE: street\nOBJ: thela kulche enter left\n"
                                 "K: Garam kulche! | गरम कुलचे!\nOBJ: rehri panipuri right\n")
        self.assertEqual(warns, [])
        objs = [e["obj"] for e in sc["scenes"][0]["timeline"] if "obj" in e]
        self.assertEqual([o["kind"] for o in objs], ["thela_kulche", "thela_golgappe"])
        plan = compile_scene(split_scenes(sc)[0], use_tts=False)
        cart = plan.objects["thela_kulche"]
        t0, t1, _a, _b = cart.moves[0]
        self.assertGreaterEqual(t1 - t0, 2.5)                         # pushed in slowly, not driven

    def test_cart_people(self):
        for look in ("kulchewala", "thelewala", "food_blogger", "food_blogger_girl"):
            self.assertIn(look, LOOKS)
            self.assertTrue(os.path.exists(os.path.join(ROOT, "assets", "looks", look + ".png")))
        sc, warns = parse_script("HOOK: h\nCAST: A = rehriwala, B = food_vlogger, C = matar_kulche_wala\n"
                                 "SCENE: street\nA: Hi | हाय\nB: Hello doston! | हेलो दोस्तों!\n")
        self.assertEqual(warns, [])
        self.assertEqual([sc["characters"][n]["look"] for n in "ABC"], ["thelewala", "food_blogger", "kulchewala"])
        plan = compile_scene(split_scenes(sc)[0], use_tts=False)
        self.assertEqual(plan.chars["B"].state_at(0.5)["prop"], "vlog_cam")


class Faces(unittest.TestCase):
    def test_every_face_word_is_understood(self):
        for w in FACE_WORDS:
            _spec, warns = cast("boy " + w)
            self.assertEqual(warns, [], w)
        for part, vals in FACE_PARTS.items():
            for v in vals:
                self.assertEqual(FACE_WORDS[face_word(part, v)], (part, v))
        for h in ("bob", "two_plaits", "side_braid", "mohawk", "man_bun", "curly_open"):
            self.assertIn(h, HAIR_STYLES)
        spec, _ = cast("girl do_choti mole freckles lipstick")
        self.assertEqual(spec["hair"], "two_plaits")
        self.assertEqual(sorted(spec["marks"]), ["freckles", "mole"])

    def test_every_choice_changes_the_drawing(self):
        base = {"look": "boy", "face": "oval", "eyes": "dot", "nose": "hook", "brows": "normal"}
        ref = ops_of(base)
        for part, vals in FACE_PARTS.items():
            for v in vals:
                if base.get(part) == v or v in ("normal", "none"):
                    continue
                self.assertNotEqual(ops_of(dict(base, **{part: v})), ref, (part, v))
        for m in MARKS:
            self.assertNotEqual(ops_of(dict(base, marks=[m])), ref, m)
        for k, v in (("cheeks", "blush"), ("lashes", True), ("shave", True)):
            spec = dict(base, accessories=["moustache"]) if k == "shave" else base
            self.assertNotEqual(ops_of(dict(spec, **{k: v})), ops_of(spec), k)
        for h in HAIR_STYLES:
            self.assertTrue(ops_of(dict(base, hair=h)))
            self.assertTrue(build_character(dict(base, hair=h, view="back"), {}, "smile", 0, 0, 540, 1700)[0])

    def test_an_old_moustache_is_drawn_as_before(self):
        a = ops_of({"look": "police"})
        b = ops_of({"look": "police", "moustache": "normal"})
        self.assertEqual(a, b)
        self.assertNotEqual(a, ops_of({"look": "police", "moustache": "handlebar"}))
        self.assertNotEqual(a, ops_of({"look": "police", "moustache": "none"}))

    def test_everybody_gets_small_things_of_their_own(self):
        sc, _ = parse_script("HOOK: h\nCAST: A = boy, B = girl, C = dada\nSCENE: room\nA: Hi | हाय\n")
        ch = sc["characters"]
        self.assertIn("age_lines", ch["C"]["marks"])                  # the old have lines on the face
        self.assertTrue(ch["B"].get("lashes"))                        # women get lashes
        sc, _ = parse_script("HOOK: h\nCAST: A = boy, B = girl, C = dada\nSCENE: room\nA: Hi | हाय\nCAMERA: classic\n")
        for spec in sc["characters"].values():                        # classic: faces exactly as before
            for k in ("lips", "ears", "marks", "lashes"):
                self.assertNotIn(k, spec)
        sc, _ = parse_script("HOOK: h\nCAST: A = boy thin_lips no_beard\nSCENE: room\nA: Hi | हाय\n")
        self.assertEqual(sc["characters"]["A"]["lips"], "thin")      # the script's own choice wins


class Saved(unittest.TestCase):
    def test_saved_characters_from_the_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({"raju": "uncle mohawk handlebar_moustache big_ears", "@Pinky": ["girl", "bob", "mole"]}, f)
        old = os.environ.get("STUDIO_CHARACTERS")
        os.environ["STUDIO_CHARACTERS"] = f.name
        try:
            sc, warns = parse_script("HOOK: h\nCAST: R = @raju, P = @pinky, X = @nobody\nSCENE: room\nR: Hi | हाय\n")
        finally:
            if old is None:
                del os.environ["STUDIO_CHARACTERS"]
            else:
                os.environ["STUDIO_CHARACTERS"] = old
            os.unlink(f.name)
        r, p = sc["characters"]["R"], sc["characters"]["P"]
        self.assertEqual((r["look"], r["hair"], r["moustache"], r["ears"]), ("uncle", "mohawk", "handlebar", "big"))
        self.assertEqual((p["look"], p["hair"]), ("girl", "bob"))
        self.assertIn("mole", p["marks"])
        self.assertEqual(len([w for w in warns if "@nobody" in w]), 1)


PAGE = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()


def page(expr):
    import re
    vocab_json = re.search(r'id="vocab">(.*?)</script>', PAGE, re.S).group(1)
    checker = PAGE[PAGE.index("const V = "):PAGE.index("function checkActing")]
    lint = PAGE[PAGE.index("function lintScript"):PAGE.index("\nfunction ", PAGE.index("function lintScript") + 10)]
    builder = PAGE[PAGE.index("// ---------------------------------------------------------------- builder (pure"):
                   PAGE.index("// ---------------------------------------------------------------- builder end")]
    helpers = PAGE[PAGE.index("function checkActing"):PAGE.index("function lintScript")]
    js = "const $ = (id) => ({ textContent: %s });\n%s\n%s\n%s\n%s\n" % (json.dumps(vocab_json), checker, helpers, lint,
                                                                         builder)
    out = subprocess.run(["node", "-e", js + "console.log(JSON.stringify(%s));" % expr], capture_output=True,
                         text=True, timeout=30)
    if out.returncode:
        raise AssertionError(out.stderr)
    return json.loads(out.stdout)


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class Page(unittest.TestCase):
    def test_the_page_knows_the_new_words(self):
        v = json.loads(__import__("re").search(r'id="vocab">(.*?)</script>', PAGE, __import__("re").S).group(1))
        self.assertEqual(v, json.loads(json.dumps(vocab())))

    def test_face_card_words_and_saved_names(self):
        c = {"role": "papa", "eyes": "almond", "beard": "stubble", "moustache": "handlebar", "lips": "auto",
             "marks": ["mole"], "lashes": True}
        words = page("castWords(%s)" % json.dumps(c)).split()
        self.assertEqual(words, ["papa", "almond_eyes", "stubble", "handlebar_moustache", "lashes", "mole"])
        _spec, warns = cast(" ".join(words))
        self.assertEqual(warns, [])
        out = page('expandSaved("HOOK: h\\nCAST: R = @raju, X = @kaun\\nR: hi", {raju: %s})' % json.dumps(c))
        self.assertIn("R = papa almond_eyes", out["text"])
        self.assertEqual(len(out["problems"]), 1)

    def test_the_checker_accepts_carts_and_faces(self):
        script = ("HOOK: h\nCAST: K = kulchewala, B = food_blogger mole goatee, G = girl do_choti lashes\n"
                  "SCENE: street\nOBJ: thela kulche enter left\nK: Garam kulche! | गरम कुलचे!\nCTA: c\n")
        self.assertEqual(page("lintScript(%s)" % json.dumps(script)), [])


if __name__ == "__main__":
    unittest.main()

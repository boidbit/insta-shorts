"""The page's Builder: plain "Naam: baat" lines -> a script the studio accepts. Runs the page's own JS in node.
python -m unittest discover -s tests"""
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio.characters import LOOKS                        # noqa: E402
from studio.scene import split_scenes                      # noqa: E402
from studio.script import parse_script                     # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
PAGE = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()


def page_js():
    vocab = re.search(r'id="vocab">(.*?)</script>', PAGE, re.S).group(1)
    checker = PAGE[PAGE.index("const V = "):PAGE.index("function checkActing")]
    builder = PAGE[PAGE.index("// ---------------------------------------------------------------- builder (pure"):
                   PAGE.index("// ---------------------------------------------------------------- builder end")]
    return "const $ = (id) => ({ textContent: %s });\n%s\n%s\n" % (json.dumps(vocab), checker, builder)


def run(expr):
    out = subprocess.run(["node", "-e", page_js() + "console.log(JSON.stringify(%s));" % expr],
                         capture_output=True, text=True, timeout=30)
    if out.returncode:
        raise AssertionError(out.stderr)
    return json.loads(out.stdout)


def build(text, builder=None):
    return run("buildScript(%s, %s)" % (json.dumps(text), json.dumps(builder or {})))


DIALOGUE = """Papa: Sarkari gaadi se aana!
Beta: Ji papa ji!
Papa (gussa): Aur time pe aana.
Beta: Haan haan.
Papa: Kya bola?!
Beta (akad): Kuch nahi 😏
Narrator: Aur phir beta kachra gaadi le aaya.
"""


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class Builder(unittest.TestCase):
    def parsed(self, script):
        scene, warns = parse_script(script)
        return scene, [w for w in warns if not w.startswith("no Devanagari")]

    def test_dialogue_becomes_a_clean_script(self):
        out = build(DIALOGUE)
        self.assertEqual(out["problems"], [])
        scene, warns = self.parsed(out["script"])
        self.assertEqual(warns, [], out["script"])
        self.assertIn("Papa = papa", out["script"])                 # a role word as a name gets that role
        self.assertIn("Beta = beta", out["script"])
        self.assertIn("Papa (angry): Aur time pe aana.", out["script"])     # Hindi chip words -> acting words
        self.assertIn("Beta (smug): Kuch nahi", out["script"])
        self.assertIn("Papa (surprised): Kya bola?!", out["script"])       # ?! -> surprised by itself
        self.assertTrue(out["script"].startswith("HOOK: Sarkari gaadi se aana!"))

    def test_automatic_shots(self):
        script = build(DIALOGUE)["script"]
        lines = script.splitlines()
        first_cut = next(i for i, l in enumerate(lines) if l.startswith("CUT"))
        self.assertTrue(lines[first_cut - 2].startswith("Papa") and lines[first_cut - 1].startswith("Beta"))
        cuts = [l for l in lines if l.startswith("CUT")]
        self.assertEqual(len(cuts), 4)
        self.assertIn("CUT ots", cuts)
        self.assertIn("CUT", cuts)
        scene, _ = self.parsed(script)
        subs = split_scenes(scene)
        self.assertTrue(any(sc.get("framing") == "ots" for sc in subs))

    def test_blank_lines_are_the_writers_shots(self):
        script = build("A: ek\nB: do\n\nA: teen\nB: char\n\n\nA: paanch\n")["script"]
        self.assertEqual([l for l in script.splitlines() if l.startswith("CUT")], ["CUT", "CUT"])

    def test_builder_choices_win(self):
        b = {"place": "market", "hook": "Bazaar me bawaal", "cta": "Follow karo",
             "cast": [{"name": "Sharma ji", "role": "uncle", "hair": "balding", "outfit": "kurta", "color": "saffron",
                       "extra": "moustache"}, {"name": "Pinky", "role": "college_girl", "skin": "fair"}]}
        out = build("sharma ji: Bhindi kitne ki?\nPinky: Sau rupaye kilo!\nSharmaJi -> facepalm\n", b)
        s = out["script"]
        self.assertIn("SCENE: market", s)
        self.assertIn("HOOK: Bazaar me bawaal", s)
        self.assertIn("CTA: Follow karo", s)
        self.assertIn("SharmaJi = uncle balding kurta saffron moustache", s)
        self.assertIn("Pinky = college_girl fair", s)
        scene, warns = self.parsed(s)
        self.assertEqual(warns, [], s)
        self.assertEqual(scene["characters"]["SharmaJi"]["hair"], "balding")

    def test_unknown_names_get_different_looks(self):
        s = build("Raju: hi\nPappu: hello\n")["script"]
        self.assertIn("Raju = college_boy", s)
        self.assertIn("Pappu = college_girl", s)

    def test_devanagari_kept_when_given(self):
        s = build("A: Kya? | क्या?\nB: Haan\n")["script"]
        self.assertIn("A: Kya? | क्या?", s)

    def test_unreadable_line_is_reported(self):
        out = build("A: hi\nB: hello\nye ek line bina naam ke\n")
        self.assertEqual(len(out["problems"]), 1)

    def test_dialogue_or_idea(self):
        self.assertTrue(run('isDialogue("A: hi\\nB: hello")'))
        self.assertFalse(run('isDialogue("mummy ne doodh mangaya aur beta cricket khelne chala gaya")'))
        self.assertFalse(run('isDialogue("HOOK: x\\nCTA: y")'))

    def test_idea_carries_the_settings(self):
        text = run('ideaWithSettings("doodh wala idea", {place: "kitchen", cast: [{name: "Maa", role: "mummy"}]})')
        self.assertIn("doodh wala idea", text)
        self.assertIn("SCENE: kitchen", text)
        self.assertIn("CAST: Maa = mummy", text)
        self.assertEqual(run('ideaWithSettings("x", {})'), "x")

    def test_every_look_has_a_picture(self):
        for look in LOOKS:
            self.assertTrue(os.path.exists(os.path.join(ROOT, "assets", "looks", look + ".png")), look)


    def test_page_puts_lost_line_breaks_back_like_the_parser(self):
        from studio.script import unflatten
        for flat in (FLAT, FLAT.replace("CUT A (smug)", "CUT ots B A (smug)"), FLAT.replace("CUT B", "CUT wide B")):
            self.assertEqual(run("unflatten(%s)" % json.dumps(flat)), unflatten(flat)[0])
        self.assertEqual(run('unflatten("A: hi\\nB: ho\\nC: x\\nD: y")'), "A: hi\nB: ho\nC: x\nD: y")


FLAT = ("HOOK: Chachi boss ban gayi 😂 CAST: A = chachi, B = office_guy SCENE: office A (angry): Tu late aaya! | "
        "तू लेट आया! B (shock): Sorry madam! | सॉरी मैडम! CUT A (smug): Accha, apna resign bhej! | अच्छा, अपना रिज़ाइन "
        "भेज! CUT B (shock): Kyun? Maine kya kiya? | क्यों? मैंने क्या किया? CUT A (laugh): Ab tu mera boss banega! | "
        "अब तू मेरा बॉस बनेगा! B -> shock boing CTA: Tag karo 😂 CAPTION: Chachi ne system badal diya HASHTAGS: #Desi")


class Flattened(unittest.TestCase):
    """A script pasted into a one-line box (GitHub's "Run workflow" form) loses its line breaks."""

    def test_parser_splits_it_back(self):
        scene, warns = parse_script(FLAT)
        self.assertIn("ek hi line", warns[0])
        self.assertEqual(warns[1:], [w for w in warns[1:] if w.startswith("no Devanagari")])
        self.assertEqual(len(scene["scenes"]), 4)
        says = [ev["say"] for sc in scene["scenes"] for ev in sc["timeline"] if "say" in ev]
        self.assertEqual(says[0], "Tu late aaya!")
        self.assertEqual(says[-1], "Ab tu mera boss banega!")

    def test_framing_and_ots_words_stay_on_the_cut(self):
        from studio.script import unflatten
        t, _ = unflatten(FLAT.replace("CUT A (smug)", "CUT ots B A (smug)").replace("CUT B (shock)", "CUT wide B (shock)"))
        self.assertIn("\nCUT ots B\nA (smug)", t)
        self.assertIn("\nCUT wide\nB (shock)", t)

    def test_normal_scripts_untouched(self):
        from studio.script import unflatten
        text = "HOOK: h\nCAST: A = boy\nSCENE: room\nA: hi | हाय\nCTA: c\n"
        self.assertEqual(unflatten(text), (text, False))


if __name__ == "__main__":
    unittest.main()

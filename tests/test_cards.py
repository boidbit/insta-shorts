"""The page's 🧩 Builder tab: a script <-> cards, line by line. Runs the page's own JS in node.

The promise: opening a script in the Builder and going back gives the very same script (nothing lost, nothing moved),
and a card made or changed on the Builder writes a line the studio reads.

    python -m unittest tests.test_cards
    CARDS_EXTRA_SCRIPTS=/path/to/more/scripts python -m unittest tests.test_cards    # your own scripts too
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio.script import BACKGROUNDS, parse_script     # noqa: E402
from tests.test_builder import PAGE, ROOT              # noqa: E402


def page_js():
    """The page's checker (lintScript) and builder functions, without the page around them."""
    vocab = re.search(r'id="vocab">(.*?)</script>', PAGE, re.S).group(1)
    checker = PAGE[PAGE.index("const V = "):PAGE.index("function showLint")]
    builder = PAGE[PAGE.index("// ---------------------------------------------------------------- builder (pure"):
                   PAGE.index("// ---------------------------------------------------------------- builder end")]
    return "const $ = (id) => ({ textContent: %s });\nconst savedChars = () => ({});\n%s\n%s\n" % (
        json.dumps(vocab), checker, builder)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def script_files():
    pats = ["scripts/*.txt", "scripts/demo/*.txt", "scripts/25d/*.txt"]
    files = sorted(f for p in pats for f in glob.glob(os.path.join(ROOT, p)))
    extra = os.environ.get("CARDS_EXTRA_SCRIPTS")
    if extra:
        files += sorted(glob.glob(os.path.join(extra, "*.txt")))
    return files


def run_js(code, data):
    """Run `code` after the page's builder functions; `DATA` is `data`; the code prints JSON."""
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(page_js() + "const DATA = %s;\n%s\n" % (json.dumps(data, ensure_ascii=False), code))
        path = f.name
    try:
        out = subprocess.run(["node", path], capture_output=True, text=True, timeout=60)
    finally:
        os.unlink(path)
    if out.returncode:
        raise AssertionError(out.stderr)
    return json.loads(out.stdout)


def lint(script):
    return run_js("console.log(JSON.stringify(lintScript(DATA)));", script)


def scene_of(script):
    scene, warns = parse_script(script)
    return json.dumps(scene, sort_keys=True, ensure_ascii=False), [w for w in warns if not w.startswith("no Devanagari")]


# odd things people paste: they must come back exactly as they went in
ODD = [
    "",
    "\n\n",
    "HOOK:\nCAST: A = boy\n",
    "  HOOK: spaces around  \nCAST:A=boy,B = girl\nA(angry):hi|हाय\nA (): empty brackets\n",
    "HOOK: x\nA ->  two  spaces\nB -> exit right fast\n...\nwait 1.5\n// a note\n#tags line\n[Chorus]\n",
    "> chat message\n< reply\nCHAT: x\n",
    "HOOK: x\r\nCAST: A = boy\r\nA: hi\r\n",
    "SCENE: street pan | Raste me... 🚶\nSCENE: train pahad\nSCENE: assets/backgrounds/my.png\nOBJ: thela kulche enter left\n",
    "NOTIFY: Bank | Salary credited | Balance: Rs 12\nnotify: lower case\nCOUNTER: Rotiyan | 0 | 14\nLIGHTS: off\n",
    "CAST: R = @raju, P = papa bald glasses kurta white chubby\nCAST: broken line without equals\n",
    "A (point left, carry tiffin): x | य | z\nSharma ji (angry): naam me space\nNARRATOR: aur phir...\nALL -> laugh\n",
]


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class RoundTrip(unittest.TestCase):
    def test_every_script_comes_back_the_same(self):
        files = script_files()
        self.assertGreater(len(files), 15)
        data = {os.path.relpath(f, ROOT): read(f) for f in files}
        data["EXAMPLE_SCRIPT"] = re.search(r"const EXAMPLE_SCRIPT = `(.*?)`;", PAGE, re.S).group(1)
        for i, s in enumerate(ODD):
            data["odd%d" % i] = s
        out = run_js("""
const res = {};
for (const [f, s] of Object.entries(DATA)) {
  const m = scriptToCards(s), lines = m.items.filter((it) => it.k !== "blank");
  res[f] = { back: cardsToScript(m), lines: lines.length, raw: lines.filter((it) => it.k === "raw").length,
             kept: lines.filter((it) => it.orig !== undefined).length };
}
console.log(JSON.stringify(res));""", data)
        for f, r in out.items():
            want = data[f].replace("\r\n", "\n")
            self.assertEqual(r["back"], want, f)
        # the cards understand the real scripts (not just keep them as raw text)
        real = [r for f, r in out.items() if f.startswith("scripts")]
        lines = sum(r["lines"] for r in real)
        self.assertGreater(lines, 300)
        self.assertLess(sum(r["raw"] for r in real) / lines, 0.12)
        self.assertEqual(sum(r["kept"] for r in real), 0)       # every line already in the cards' own shape

    def test_cards_rebuilt_from_their_fields_tell_the_same_story(self):
        """Every card written again from its fields (as after an edit): the studio reads the same scene."""
        files = script_files()
        data = {os.path.relpath(f, ROOT): read(f) for f in files}
        out = run_js("""
const res = {};
for (const [f, s] of Object.entries(DATA)) {
  const m = scriptToCards(s);
  for (const it of m.items) { delete it.orig; if (it.k === "cast") for (const c of it.chars) delete c.origWords; }
  res[f] = cardsToScript(m);
}
console.log(JSON.stringify(res));""", data)
        for f, fresh in out.items():
            self.assertEqual(scene_of(fresh)[0], scene_of(data[f])[0], f)


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class Editing(unittest.TestCase):
    def test_one_feeling_one_action(self):
        out = run_js("""
const a = setFeel(["arms_crossed", "confused"], "hasi");
const b = setFeel(["point"], "gussa");
const c = setFeel(["angry", "point"], "");
const d = setAction(["shrug", "smug"], "facepalm");
const e = setAction(["smile"], "point left");
const f = setAction(["point", "sly"], "");
const g = setCam(setCam(["shock"], "zoom", true), "slowmo", true);
const h = setCam(["shock", "slow_motion"], "slowmo", false);
const k = setExtras(["eat", "excited", "plate"], "phone, boing");
const p = actingParts(["exit right fast", "angry", "zoom", "thud"]);
console.log(JSON.stringify({a, b, c, d, e, f, g, h, k, p, t: actTokens("enter back siren lie_down bed walk left ride bike back")}));""", None)
        self.assertEqual(out["a"], ["arms_crossed", "laugh"])           # the old feeling goes: the studio uses one
        self.assertEqual(out["b"], ["point", "angry"])
        self.assertEqual(out["c"], ["point"])
        self.assertEqual(out["d"], ["facepalm", "smug"])
        self.assertEqual(out["e"], ["point left", "smile"])
        self.assertEqual(out["f"], ["sly"])
        self.assertEqual(out["g"], ["shock", "zoom", "slowmo"])
        self.assertEqual(out["h"], ["shock"])
        self.assertEqual(out["k"], ["eat", "excited", "phone", "boing"])
        self.assertEqual(out["p"], {"feel": 1, "action": 0, "cam": [2], "extra": [3]})
        self.assertEqual(out["t"], ["enter back", "siren", "lie_down bed", "walk left", "ride bike back"])

    def test_a_reel_made_only_with_cards(self):
        """Empty page -> hook, place, two characters, lines, a screen card, CTA: a script the studio reads."""
        script = run_js("""
const m = scriptToCards("");
Object.assign(ensureItem(m.items, "HOOK"), { value: "Mummy ka 5 minute 😂" });
Object.assign(ensureItem(m.items, "SCENE"), { place: "kitchen", words: ["evening"] });
const cast = ensureItem(m.items, "CAST");
cast.chars.push({ id: freeId(m.items), f: { role: "beta", hair: "spiky", rest: [] } });
cast.chars.push({ id: freeId(m.items), f: { role: "mummy", outfit: "saree", color: "maroon", eyes: "almond", rest: [] } });
Object.assign(ensureItem(m.items, "CTA"), { value: "Apni mummy ko tag karo 👇" });
const add = (it) => m.items.splice(storyEnd(m.items), 0, it);
add({ k: "line", who: "A", acting: setFeel([], "rona"), text: "Mummy, khana kab milega?", dev: "" });
add({ k: "line", who: "B", acting: setAction(setFeel([], "khush"), "stir"), text: "Bas 5 minute beta!", dev: "" });
add({ k: "screen", key: "TIMECARD", value: "1 ghante baad... ⏰" });
add({ k: "line", who: "A", acting: setCam(setAction(setFeel([], "mar"), "faint"), "slowmo", true), text: "", dev: "" });
add({ k: "line", who: "B", acting: [], text: "", dev: "" });          // an empty card: no line
renameChar(m.items, "A", "Beta");
console.log(JSON.stringify(cardsToScript(m)));""", None)
        self.assertEqual(script, "\n".join([
            "HOOK: Mummy ka 5 minute 😂",
            "CAST: Beta = beta spiky, B = mummy saree maroon almond_eyes",
            "SCENE: kitchen evening",
            "Beta (cry): Mummy, khana kab milega?",
            "B (stir, smile): Bas 5 minute beta!",
            "TIMECARD: 1 ghante baad... ⏰",
            "Beta -> faint dead slowmo",
            "CTA: Apni mummy ko tag karo 👇",
            "",
        ]))
        self.assertEqual(lint(script), [])
        scene, warns = parse_script(script)
        self.assertEqual(warns, [w for w in warns if w.startswith("no Devanagari")])

    def test_an_edited_line_of_a_real_script(self):
        src = read(os.path.join(ROOT, "scripts/demo/kulche_vlog.txt"))
        out = run_js("""
const m = scriptToCards(DATA);
const line = m.items.find((it) => it.k === "line" && it.text);
line.acting = setFeel(line.acting, "akad"); line.text = "Naya dialogue, bilkul naya!"; line.dev = ""; touch(line);
console.log(JSON.stringify({ script: cardsToScript(m), who: line.who }));""", src)
        new, old = out["script"].split("\n"), src.split("\n")
        changed = [i for i, (a, b) in enumerate(zip(new, old)) if a != b]
        self.assertEqual(len(new), len(old))
        self.assertEqual(len(changed), 1)                        # only that line, all the others byte for byte
        self.assertIn("smug", new[changed[0]])
        self.assertTrue(new[changed[0]].endswith(": Naya dialogue, bilkul naya!"))   # no stale Devanagari
        self.assertEqual(lint(out["script"]), lint(src))

    def test_rename_follows_lines_shots_and_throws(self):
        out = run_js("""
const m = scriptToCards("CAST: A = papa, B = beta\\nA (angry, throw B): Idhar aa!\\nCUT ots B\\nB -> exit right fast\\nAB: not B\\n");
renameChar(m.items, "B", "Pappu");
console.log(JSON.stringify(cardsToScript(m)));""", None)
        self.assertEqual(out, "CAST: A = papa, Pappu = beta\nA (angry, throw Pappu): Idhar aa!\nCUT ots Pappu\n"
                              "Pappu -> exit right fast\nAB: not B\n")

    def test_moving_and_where_new_cards_go(self):
        out = run_js("""
const m = scriptToCards("HOOK: h\\nMUSIC: comedy 110\\nCAST: A = boy, B = girl\\nSCENE: room\\nA: one\\n\\nB: two\\nCUT\\nA: three\\nCTA: c\\nCAPTION: x\\nCOVER: y\\nLOOP: on\\n");
const shown = listIndexes(m.items).map((i) => itemText(m.items[i]));
const two = m.items.findIndex((it) => it.text === "two");
moveItem(m.items, two, -1);                           // over the blank line, before "one"
const first = listIndexes(m.items)[0];
const top = moveItem(m.items, first, -1);             // the first card cannot go above the top box
const at = storyEnd(m.items);
console.log(JSON.stringify({ shown, script: cardsToScript(m), top, before: itemText(m.items[at]) }));""", None)
        self.assertEqual(out["shown"], ["A: one", "B: two", "CUT", "A: three"])      # settings and heads have boxes
        self.assertIn("SCENE: room\nB: two\n\nA: one\nCUT", out["script"])
        self.assertFalse(out["top"])
        self.assertEqual(out["before"], "CTA: c")                   # a new card goes after the story, before CTA

    def test_missing_heads_go_where_a_script_has_them(self):
        out = run_js("""
const m = scriptToCards("A: hi\\nB: bye\\nCOVER: z\\n");
ensureItem(m.items, "CTA").value = "tag";
ensureItem(m.items, "HASHTAGS").value = "#x";
ensureItem(m.items, "CAPTION").value = "cap";
ensureItem(m.items, "HOOK").value = "hook";
ensureItem(m.items, "SCENE").place = "office";
ensureItem(m.items, "CAST").chars.push({ id: "A", f: { role: "boss", rest: [] } });
console.log(JSON.stringify(cardsToScript(m)));""", None)
        self.assertEqual(out, "HOOK: hook\nCAST: A = boss\nSCENE: office\nA: hi\nB: bye\nCTA: tag\nCAPTION: cap\n"
                              "HASHTAGS: #x\nCOVER: z\n")


class Page(unittest.TestCase):
    def test_the_tab_and_its_box(self):
        self.assertIn('data-mode="cards"', PAGE)
        self.assertIn('id="cards"', PAGE)
        self.assertIn('data-mode="script"', PAGE)                # the old tabs stay
        self.assertIn('data-mode="idea"', PAGE)

    def test_every_place_has_a_picture(self):
        for place in BACKGROUNDS:
            self.assertTrue(os.path.exists(os.path.join(ROOT, "assets", "places", place + ".jpg")), place)


if __name__ == "__main__":
    unittest.main()

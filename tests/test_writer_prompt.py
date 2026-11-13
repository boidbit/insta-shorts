"""The writer prompt (SCRIPT_PROMPT.md), after the writer upgrade: its example scripts are scripts the studio reads
cleanly, its dialogue-only mode is something the page turns into a script, and the old contradictions stay gone.

    python -m unittest tests.test_writer_prompt
"""
import json
import os
import re
import shutil
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import director                                # noqa: E402
from studio.script import parse_script                     # noqa: E402
from tests.test_cards import run_js                        # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")


def read(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return f.read()


PROMPT = read("SCRIPT_PROMPT.md")
SECTION = PROMPT[PROMPT.index("# Two example scripts"):PROMPT.index("# Before you answer")]
EXAMPLES = re.findall(r"```\n(HOOK:.*?)\n```", SECTION, re.S)
DIALOGUE = re.search(r"Example:\n  ```\n(.*?)\n  ```", PROMPT, re.S).group(1)
DIALOGUE = "\n".join(l[2:] for l in DIALOGUE.splitlines())
SAY = re.compile(r"^([A-Za-z][\w ]*?)\s*(?:\(([^)]*)\))?\s*:\s*(.+)$")
HEADS = re.compile(r"^(HOOK|CAST|SCENE|CTA|CAPTION|HASHTAGS|COVER|MUSIC|STYLE|OBJ)\s*:")


def spoken(script):
    return [m.group(3).split("|")[0].strip() for m in map(SAY.match, script.splitlines()) if m and not HEADS.match(m.group(0))]


def clean(script):
    _, warns = parse_script(script)
    return [w for w in warns if not w.startswith("no Devanagari")]


class Examples(unittest.TestCase):
    def test_two_full_examples(self):
        self.assertEqual(len(EXAMPLES), 2)

    def test_the_studio_reads_them_cleanly(self):
        for ex in EXAMPLES:
            self.assertEqual(clean(ex), [], ex[:40])
            lines = spoken(ex)
            self.assertTrue(4 <= len(lines) <= 8, ex[:40])
            self.assertTrue(all(len(l) <= 100 for l in lines), [len(l) for l in lines])       # a speech bubble
            self.assertLess(sum(map(len, lines)), 400)
            for line in ex.splitlines():                                                       # Devanagari everywhere
                m = SAY.match(line)
                if m and not HEADS.match(line):
                    self.assertRegex(m.group(3), r"\| .*[ऀ-ॿ]", line)
            self.assertNotRegex(ex, r"(?m)^CUT")          # both are talks across a counter: the studio films them

    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_the_page_checker_agrees(self):
        for ex in EXAMPLES:
            self.assertEqual(run_js("console.log(JSON.stringify(lintScript(DATA)));", ex), [], ex[:40])

    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_dialogue_only_becomes_a_script_on_the_page(self):
        out = run_js("""
const m = scriptToCards("");
const r = addDialogue(m.items, DATA);
const script = cardsToScript(m);
console.log(JSON.stringify({ r, script, lint: lintScript(script), idea: buildScript(DATA, {}).script }));""", DIALOGUE)
        self.assertEqual(out["r"]["raw"], [])
        self.assertIn("Boss = boss", out["script"])
        self.assertIn("SCENE: office", out["script"])
        self.assertIn("(smile): Dekho, ye company nahi", out["script"])                       # khush -> smile
        self.assertEqual(out["lint"], [])
        self.assertEqual(clean(out["script"]), [])
        self.assertEqual(clean(out["idea"]), [])                                              # the Idea tab too

    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_two_word_roles(self):
        out = run_js('console.log(JSON.stringify(["Food Blogger", "gym bro", "Sarkari Babu", "PA", "Pinky"].map((n) => roleFor(n))));', None)
        self.assertEqual(out[:4], ["food_blogger", "gym_bro", "babu", "clerk"])


class Rules(unittest.TestCase):
    def test_the_craft_is_in_the_short_prompt_too(self):
        core = director.prompt_text(PROMPT, keep=())
        for must in ("# Natural desi comedy", "Not every line is a joke", "Every character sounds like themselves",
                     "ONE main comedy flavour", "Punch line craft", "`Trend: ...`", "Never present an old trend as new",
                     "DIALOGUE ONLY", "FULL STUDIO SCRIPT", "# Two example scripts",
                     "The order of the words inside ( ) does not matter", "`near` / `far`", "moonwalk, dance"):
            self.assertIn(must, core)

    def test_the_old_contradictions_are_gone(self):
        self.assertNotIn("Change at least every 1-2 lines", PROMPT)       # the camera cuts by itself
        self.assertNotIn("none over 75", PROMPT)
        self.assertIn("Max 4 characters", PROMPT)                         # a family / an office team fits
        self.assertIn("Never write CUT in a talk across a counter", PROMPT)
        self.assertIn("near` / `far` (`B -> near shock`", read("SCRIPT_PROMPT_25D.md"))
        self.assertNotIn("use `CUT` (a new shot)", read("SCRIPT_PROMPT_25D.md"))

    def test_every_module_still_opens_and_closes(self):
        self.assertEqual(len(re.findall(r"<!-- module: \w+ -->", PROMPT)), PROMPT.count("<!-- /module -->"))
        self.assertIn("sets: {", read("index.html"))


if __name__ == "__main__":
    unittest.main()

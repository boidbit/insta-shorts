"""Every word the writer prompt (SCRIPT_PROMPT.md) offers must be one the script reader understands,
so the AI never writes something that is silently ignored. python -m unittest discover -s tests"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import actions, audio, script                 # noqa: E402
from studio.characters import EXPRESSIONS                 # noqa: E402
from studio.script import parse_script                    # noqa: E402

PROMPT = open(os.path.join(os.path.dirname(__file__), "..", "SCRIPT_PROMPT.md"), encoding="utf-8").read()


def words(text):
    """`a, b (note), c / d` -> ["a", "b", "c", "d"]: the plain words of a list."""
    text = re.sub(r"\([^)]*\)", "", text)
    out = []
    for item in re.split(r"[,/]", text):
        item = item.strip().rstrip(".").strip()
        if re.fullmatch(r"[a-z_]+", item):
            out.append(item)
    return out


def line(prefix):
    m = re.search(r"^\s*" + re.escape(prefix) + r"(.*)$", PROMPT, re.M)
    assert m, prefix
    return m.group(1)


def block(start, end):
    return PROMPT[PROMPT.index(start):PROMPT.index(end)]


def lines_with(text, start, end=None):
    """The lines of one bulleted section."""
    sec = block(start, end) if end else PROMPT[PROMPT.index(start):]
    return sec.splitlines()


class PromptWordTests(unittest.TestCase):
    def test_actions(self):
        acts = []
        for ln in block("- ONE action:", "- ONE expression:").splitlines()[1:]:
            m = re.match(r"^\s{4}[a-z /]+: (.*)$", ln)
            if m:
                acts += words(m.group(1))
        self.assertGreater(len(acts), 120)
        for w in acts:
            self.assertIn(w, actions.ACTIONS, w)
            _, warns = parse_script("HOOK: h\nCAST: A = dost\nSCENE: room\nA -> %s\nCTA: c\n" % w)
            self.assertFalse([x for x in warns if "samajh" in x], (w, warns))

    def test_expressions(self):
        ex = words(line("- ONE expression: "))
        self.assertEqual(sorted(ex), sorted(EXPRESSIONS))          # all of them, nothing extra

    def test_props_are_props(self):
        props = words(line("- optional prop (held in the hand): "))
        self.assertGreater(len(props), 30)
        for w in props:
            self.assertIn(w, script.PROPS, w)
            self.assertNotIn(w, actions.ACTIONS, w)                 # otherwise it would be read as an action

    def test_sounds(self):
        self.assertEqual(sorted(words(line("- optional sound: "))), sorted(script.SFX))

    def test_effects(self):
        fx = words(line("- optional effect").split(":", 1)[1].split("Example")[0])
        self.assertGreater(len(fx), 15)
        for w in fx:
            self.assertIn(w, script.FX, w)
            self.assertNotIn(w, actions.ACTIONS, w)
            self.assertNotIn(w, EXPRESSIONS, w)

    def test_places_times_weather(self):
        places = words(line("- Places: ").split("(street and")[0])
        self.assertEqual(sorted(places), sorted(script.BACKGROUNDS))
        for w in ("day", "night", "evening", "sunset", "dawn", "rain", "fog", "snow", "fireflies", "leaves"):
            self.assertIn(w, script.TIMES + script.WEATHER)

    def test_set_pieces_and_states(self):
        pieces = words(line("Pieces: "))
        self.assertEqual(sorted(pieces), sorted(script.SET_TYPES))
        for w in words(line("States: ").replace(":", ",").replace(";", ",")):
            if w not in pieces:
                self.assertIn(w, script.SET_STATES, w)

    def test_animals_moods_ambience(self):
        an = words(line("Animals (they can talk too, and count as characters): ").split(".")[0])
        for w in an:
            self.assertIn(w, script.ANIMAL_WORDS, w)
        moods = line("- Optional `MUSIC: beat 110`")
        for w in ("sad", "suspense", "festive", "lofi", "comedy", "pop", "soft", "desi"):
            self.assertIn(w, moods)
            self.assertIn(w, audio.MOODS)
        amb = words(line("- Optional `AMBIENCE: rain` (a sound bed under the scene: ").split(")")[0])
        self.assertEqual(sorted(amb), sorted(audio.AMBIENCE))

    def test_every_example_line_reads_cleanly(self):
        text = """HOOK: Raat ke 2 baje 🌙
CAST: A = college_boy, B = kutta brown, C = mummy
SCENE: jungle night fog | Raat ke 2 baje... 🌙
MUSIC: suspense 90
AMBIENCE: rain
OBJ: sofa left
OBJ: door right
OBJ: signboard center CHAI POINT
A -> sit sofa
OBJ: door open
LIGHTS: off
NOTIFY: Bank | Salary credited Rs 50,000 | Balance: Rs 50,012
LOADING: Dimaag loading...
COUNTER: Balance | 50000 | 12
A (think, bulb, ding): Ek idea hai | एक आइडिया है
A (point, shock): Wo dekho | वो देखो
B (interrupt, angry): Bhau! | भौ!
A -> throw B
A -> fall shock slowmo thud
A -> freeze
NARRATOR: Haan, ye main hoon | हाँ, ये मैं हूँ
C (reveal, smug): Main aa gayi | मैं आ गई
C (zoom, angry): Ghar chalo | घर चलो
TIMECARD: 3 ghante baad...
CHAPTER: Chapter 2 | Exam ka din
LIGHTS: on
ENDCARD: Follow karo | @page
CTA: Tag karo 👇
"""
        _, warns = parse_script(text)
        self.assertEqual(warns, [])

    def test_no_fixed_length_limit(self):
        self.assertIn("no fixed time limit", PROMPT)
        self.assertNotIn("15-30 seconds", PROMPT)


if __name__ == "__main__":
    unittest.main()

"""Tone for the AI writer: light / dark / satire / absurd / twist.  python -m unittest discover -s tests"""
import os
import random
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import director, hooks                  # noqa: E402
from studio.script import parse_script              # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")


def read(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return f.read()


class FakeLLM:
    """Records what the writer was asked and answers with a valid script."""

    def __init__(self, answer):
        self.answer, self.calls = answer, []

    def __call__(self, system, messages, json_mode=True):
        self.calls.append((system, [m["content"] if isinstance(m, dict) else m for m in messages]))
        return self.answer


class ToneTableTests(unittest.TestCase):
    def test_every_example_is_a_valid_script_in_the_exact_format(self):
        for key, t in hooks.TONES.items():
            sc, warns = parse_script(t["script"])
            self.assertEqual(warns, [], key)
            spoken = [e for sh in sc["scenes"] for e in sh["timeline"] if "say" in e]
            self.assertGreaterEqual(len(spoken), 4, key)                     # examples show the default length
            self.assertTrue(all(e.get("speak") for e in spoken), key)         # Devanagari on every line
            self.assertTrue(sc["post"]["caption"] and sc["hook"], key)

    def test_inline_tone_line(self):
        self.assertEqual(hooks.split_tone("TONE: Dark\nmera idea"), ("dark", "mera idea"))
        self.assertEqual(hooks.split_tone("mera idea\ntone: satire"), ("satire", "mera idea"))
        self.assertEqual(hooks.split_tone("bas ek idea"), (None, "bas ek idea"))
        self.assertEqual(hooks.split_tone("TONE: nonsense\nx"), (None, "x"))

    def test_pick_tone(self):
        self.assertEqual(hooks.pick_tone("dark", "idea"), "dark")                  # an explicit choice wins
        self.assertEqual(hooks.pick_tone("auto", "an idea"), "auto")               # idea but no tone: the writer decides
        seen = {hooks.pick_tone("auto", "", random.Random(i)) for i in range(80)}
        self.assertEqual(seen, set(hooks.TONE_ODDS))                                # no idea: a mix, the dark ones included

    def test_tone_blocks(self):
        dark = hooks.tone_block("dark")
        self.assertIn("Dark comedy", dark)
        self.assertIn("Pension chahiye?", dark)
        auto = hooks.tone_block("auto")
        for key in hooks.TONES:
            self.assertIn("[%s]" % key, auto)
        self.assertIn("Do not water a dark", auto)


class PromptTests(unittest.TestCase):
    def test_the_light_only_rule_is_gone_and_the_two_limits_stay(self):
        for name in ("SCRIPT_PROMPT.md", "DIRECTOR_PROMPT.md"):
            text = read(name)
            self.assertNotIn("Keep it light", text, name)
            self.assertIn("never water", text.lower().replace("do not water", "never water"), name)
            for must in ("religion, caste, region, gender, body or disability", "committing a crime", "nothing explicit",
                         "never target a private person"):
                self.assertIn(must, text, (name, must))
        s = read("SCRIPT_PROMPT.md")
        self.assertIn("Dark comedy craft", s)
        self.assertIn("up to 10 spoken lines and 40 seconds", s)
        self.assertIn("three different premises", s)
        self.assertIn("Story facts first", s)                        # the logic rule (who owes whom stays the same)
        self.assertIn("contradict an earlier one", s)                # ...and the logic check before answering
        self.assertIn("Story facts first", read("DIRECTOR_PROMPT.md"))

    def test_long_stories_are_not_rejected(self):
        """Length never fails a video: a long script only gets a soft note (the writer is asked once to tighten)."""
        line = "Ye ek lambi si line hai jo kaafi der tak chalti hai aur poori baat saaf saaf samjhati hai"
        body = "\n".join("A (smile): %s | ये एक लंबी सी लाइन है जो काफ़ी देर तक चलती है" % line for _ in range(14))
        text = "HOOK: h\nCAST: A = dost\nSCENE: room\n%s\nCTA: c\nCAPTION: c\n" % body
        _, warns = parse_script(text)
        self.assertFalse([w for w in warns if "long" in w], warns)
        import tempfile
        probs = director.script_problems(text, os.path.join(tempfile.mkdtemp(), "x.json"))
        long_ = [p for p in probs if "long" in p]
        self.assertEqual(len(long_), 1, probs)
        self.assertTrue(long_[0].startswith(director.SOFT))
        short = text.replace(line, "Chhoti line")
        self.assertFalse([p for p in director.script_problems(short, os.path.join(tempfile.mkdtemp(), "y.json"))
                          if "long" in p])

    def test_a_long_script_is_asked_once_then_accepted(self):
        calls = []

        def llm(system, messages, json_mode=False):
            calls.append(messages[-1]["content"])
            return "same long script"
        out = director._iterate(llm, "sys", "idea", lambda t: t, lambda r: [director.SOFT + "too long"], False,
                                lambda m: None, 3)
        self.assertEqual((out, len(calls)), ("same long script", 2))      # one retry, then it is used as it is
        with self.assertRaises(SystemExit):                                 # a real problem still fails
            director._iterate(llm, "sys", "idea", lambda t: t, lambda r: ["missing CTA: line"], False,
                              lambda m: None, 2)


class WriterTests(unittest.TestCase):
    def run_writer(self, **kw):
        llm = FakeLLM(hooks.TONES["dark"]["script"])
        with tempfile.TemporaryDirectory() as d:
            text = director.write_script(llm=llm, tmp_path=os.path.join(d, "x.json"), rng=random.Random(3),
                                         log=lambda m: None, **kw)
        return llm, text

    def test_the_tone_reaches_the_system_prompt(self):
        llm, text = self.run_writer(instruction="ek aadmi aur uski EMI", tone="dark")
        system = llm.calls[0][0]
        self.assertIn("# Tone for THIS video: Dark comedy (dark)", system)
        self.assertIn("Dark comedy craft", system)                  # from SCRIPT_PROMPT.md
        self.assertTrue(text.startswith("HOOK:"))

    def test_a_tone_line_inside_the_idea_works_and_is_not_sent_as_the_idea(self):
        llm, _ = self.run_writer(instruction="TONE: satire\nmantri aur pul")
        self.assertIn("(satire)", llm.calls[0][0])
        user = str(llm.calls[0][1])
        self.assertIn("mantri aur pul", user)
        self.assertNotIn("TONE:", user)

    def test_an_idea_without_a_tone_lets_the_writer_choose_among_all_of_them(self):
        llm, _ = self.run_writer(instruction="ghar ka wifi")
        self.assertIn("Tone for THIS video: your choice", llm.calls[0][0])

    def test_no_idea_gets_a_random_topic_and_a_tone(self):
        llm, _ = self.run_writer(instruction="")
        self.assertIn("Koi idea nahi diya", str(llm.calls[0][1]))
        self.assertIn("# Tone for THIS video:", llm.calls[0][0])

    def test_the_argument_beats_the_inline_line(self):
        llm, _ = self.run_writer(instruction="TONE: light\nx", tone="absurd")
        self.assertIn("(absurd)", llm.calls[0][0])


if __name__ == "__main__":
    unittest.main()

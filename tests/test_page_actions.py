"""The studio page's action picker: every action it suggests or finds is one the studio knows, and the dropdown's
groups cover the actions. python -m unittest discover -s tests"""
import json
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import actions, script                 # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")


def page():
    with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as f:
        return f.read()


def block(text, start, end):
    i = text.index(start)
    return text[i:text.index(end, i)]


class PageActions(unittest.TestCase):
    def test_every_suggested_action_exists(self):
        s = page()
        entry = re.findall(r'"([a-z_ ]+)"', block(s, "const ENTRY_ACTS", ";"))
        ok = set(actions.ACTIONS) | set(script.SEAT_ACTIONS) | set(entry)
        for name, end in (("const ACT_HINTS", "\n];"), ("const FEEL_ACTS", "};"), ("const LOOK_ACTS", "};"),
                          ("const FIND_WORDS", "};"), ("const SELF_ACTS", "]);")):
            b = block(s, name, end)
            words = re.findall(r'\[\s*((?:"[a-z_ ]+"\s*,?\s*)+)\]', b) if name != "const SELF_ACTS" else [b]
            for group in words:
                for a in re.findall(r'"([a-z_ ]+)"', group):
                    self.assertIn(a, ok, "%s: %s" % (name, a))

    def test_the_dropdown_groups(self):
        vocab = json.loads(re.search(r'<script type="application/json" id="vocab">(.*?)</script>', page(), re.S).group(1))
        groups = vocab["action_groups"]
        self.assertGreaterEqual(len(groups), 8)
        names = [a for _label, acts in groups for a in acts]
        self.assertTrue(set(names) <= set(actions.ACTIONS))
        for a in ("sleep", "sit", "double_take", "iron", "dance", "slap", "namaste"):
            self.assertIn(a, names)
        self.assertEqual(vocab["action_aliases"]["iron"], ["istri", "press"])


if __name__ == "__main__":
    unittest.main()

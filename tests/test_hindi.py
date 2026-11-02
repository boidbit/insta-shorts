"""Roman lines get Devanagari before the voice. python -m unittest discover -s tests"""
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import hindi                                   # noqa: E402
from studio.script import parse_script                     # noqa: E402

SCRIPT = """HOOK: h
CAST: P = papa, L = beta
SCENE: room
P (angry): Sarkari gaadi se aana!
L (smile): Ji papa ji! | जी पापा जी!
NARRATOR: 10 hazar gaye 😂
CTA: c
"""


class FakeLLM:
    def __init__(self, answer=None):
        self.calls, self.answer = [], answer

    def __call__(self, system, messages, json_mode=True):
        lines = json.loads(messages[0]["content"])
        self.calls.append(lines)
        if self.answer is not None:
            return self.answer
        return json.dumps(["हिंदी " + str(i) for i in range(len(lines))], ensure_ascii=False)


class Hindi(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        patcher = mock.patch.object(hindi, "CACHE", self.tmp)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.scene, self.warn = parse_script(SCRIPT)

    def spoken(self):
        return [ev for ev in hindi._spoken(self.scene)]

    def test_only_roman_lines_are_sent_in_one_request(self):
        llm = FakeLLM()
        self.assertEqual(hindi.fill_hindi(self.scene, llm, log=lambda m: None), 2)
        self.assertEqual(len(llm.calls), 1)
        self.assertEqual(llm.calls[0], ["Sarkari gaadi se aana!", "10 hazar gaye"])       # emoji dropped
        speaks = [ev["speak"] for ev in self.spoken()]
        self.assertEqual(speaks, ["हिंदी 0", "जी पापा जी!", "हिंदी 1"])
        self.assertEqual(self.spoken()[0]["say"], "Sarkari gaadi se aana!")               # the bubble stays Roman

    def test_cached(self):
        hindi.fill_hindi(self.scene, FakeLLM(), log=lambda m: None)
        again, _ = parse_script(SCRIPT)
        llm = FakeLLM()
        self.assertEqual(hindi.fill_hindi(again, llm, log=lambda m: None), 2)
        self.assertEqual(llm.calls, [])

    def test_bad_answer_keeps_roman(self):
        for answer in ("not json", json.dumps(["एक"]), json.dumps(["still roman", "x"])):
            scene, _ = parse_script(SCRIPT)
            n = hindi.fill_hindi(scene, FakeLLM(answer), log=lambda m: None)
            self.assertEqual(n, 0, answer)
            self.assertFalse(hindi.DEVANAGARI.search(list(hindi._spoken(scene))[0]["speak"]))

    def test_no_key_no_request(self):
        with mock.patch("studio.director.provider_name", return_value=None):
            self.assertEqual(hindi.fill_hindi(self.scene, log=lambda m: None), 0)

    def test_ai_giving_up_does_not_stop_the_video(self):
        def boom(*a, **k):
            raise SystemExit("all models busy")
        self.assertEqual(hindi.fill_hindi(self.scene, boom, log=lambda m: None), 0)

    def test_nothing_to_do(self):
        scene, _ = parse_script(SCRIPT.replace("aana!\n", "aana! | आना!\n").replace("gaye 😂", "gaye | गए"))
        llm = FakeLLM()
        self.assertEqual(hindi.fill_hindi(scene, llm, log=lambda m: None), 0)
        self.assertEqual(llm.calls, [])

    def test_parser_says_it_will_be_made(self):
        self.assertTrue(any("Devanagari" in w and "GEMINI" in w for w in self.warn))


if __name__ == "__main__":
    unittest.main()

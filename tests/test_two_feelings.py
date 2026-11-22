"""Two feelings on one line ("shout, angry" / "hairan, nervous"): nothing is thrown away. A feeling that is heard
(shout, relaxed...) goes to the voice and the other one is the face; two different faces change half-way through the
line; both reach the voice (Gemini's direction, edge-tts' rate / pitch). python -m unittest"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import gemini_tts as G                        # noqa: E402
from studio import scene as S                             # noqa: E402
from studio import script                                 # noqa: E402

HEAD = "HOOK: x\nSCENE: handpump\nKIRDAAR: Daddu, Sultan\n"
LINES = ("Daddu (shout, angry, stick): Oye ruk ja! Kahan bhaage se?! | ओए रुक जा! कहाँ भागे से?!\n"
         "Daddu (relaxed, smug, stick): Chal chhod. Sandook mein jo rakha se. | चल छोड़। संदूक में जो रखा से।\n"
         "Sultan (hairan, nervous, close): Ek minute... wo patta tere paas kaise aaya? | एक मिनट... वो पट्टा तेरे पास कैसे आया?\n")


def says(text):
    sc, w = script.parse_script(text)
    return [e for e in sc["scenes"][0]["timeline"] if "say" in e], sc, w


class TwoFeelings(unittest.TestCase):
    def test_no_warning_and_the_face(self):
        evs, _sc, w = says(HEAD + LINES)
        self.assertFalse([x for x in w if "ek hi expression" in x], w)
        self.assertEqual([(e["expression"], e.get("expr_then")) for e in evs],
                         [("angry", None), ("smug", None), ("surprised", "nervous")])

    def test_the_face_changes_mid_line(self):
        _evs, sc, _w = says(HEAD + LINES)
        p = S.compile_scene(S.split_scenes(sc)[0], use_tts=False)
        c = p.chars["Sultan"]
        sp = c.speech[0]
        self.assertEqual(c.state_at(sp["start"] + 0.1)["expression"], "surprised")
        self.assertEqual(c.state_at(sp["end"] - 0.1)["expression"], "nervous")

    def test_the_voice_hears_both(self):
        _evs, sc, _w = says(HEAD + LINES)
        items = S.collect_lines(sc["scenes"][0])
        self.assertEqual([i["expression"] for i in items], ["shout", "relaxed", "nervous"])
        lines = [{"voice": "Charon" if i["who"] == "Sultan" else "Algenib", "text": i["text"],
                  "how": G.delivery(i["feel"])} for i in items]
        text = G.build_payload(lines)["contents"][0]["parts"][0]["text"]
        self.assertIn("shouting loudly and angry", text)
        self.assertIn("surprised and nervous", text)

    def test_one_feeling_is_unchanged(self):
        evs, sc, w = says(HEAD + "Daddu (gussa): Oye! | ओए!\nSultan (smug): Haan? | हाँ?\n")
        self.assertNotIn("voice_feel", evs[0])
        items = S.collect_lines(sc["scenes"][0])
        self.assertIsNone(items[0]["feel"])
        lines = [{"voice": "A", "text": "x"}, {"voice": "B", "text": "y"}]
        self.assertNotIn("How some lines", G.build_payload(lines)["contents"][0]["parts"][0]["text"])

    def test_three_feelings_still_warn(self):
        _evs, _sc, w = says(HEAD + "Daddu (shout, angry, sad): Oye! | ओए!\nSultan (smug): Haan? | हाँ?\n")
        self.assertTrue([x for x in w if "ek hi expression" in x])


if __name__ == "__main__":
    unittest.main()

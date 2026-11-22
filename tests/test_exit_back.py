"""Somebody walks out (`X -> exit right [fast]`) and later speaks again with no `X -> enter`: the studio brings
them back from the side they left by, and they are in the shot before they went. python -m unittest"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import script                                 # noqa: E402
from studio.render import Sequence                        # noqa: E402

TEXT = """HOOK: x
SCENE: handpump
Sultan (darr): Baba, apun nikal raha hai! | बाबा, अपुन निकल रहा है!
Sultan -> exit right%s
Daddu (gussa): Oye ruk ja! Kahan bhaage se?! | ओए रुक जा! कहाँ भागे से?!
Sultan (gussa): Abey toh kya karun? | अबे तो क्या करूँ?
Daddu (chalak): Re na na! Tu toh mera locker se. | रे ना ना! तू तो मेरा लॉकर से।
"""


def xs(text):
    sc, w = script.parse_script(text)
    p = Sequence(sc, 540, False, None, None).parts[0]
    c = p.plan.chars["Sultan"]
    c.ov = None
    sp = [s for s in p.plan.speech if s["who"] == "Sultan"]
    return [c.draw_pos((s["start"] + s["end"]) / 2)[0] for s in sp], p.plan.speech, c, w


class ExitAndBack(unittest.TestCase):
    def test_comes_back_after_a_fast_exit(self):
        (first, again), speech, c, w = xs(TEXT % " fast")
        self.assertTrue(0 < first < 1080)                  # there before running out
        self.assertTrue(0 < again < 1080)                  # and back for the next line
        daddu = speech[1]
        self.assertGreater(c.draw_pos((daddu["start"] + daddu["end"]) / 2)[0], 1080)   # gone in between
        self.assertTrue(any("wapas le aaya" in x for x in w))

    def test_comes_back_after_a_walk_out(self):
        (first, again), _sp, _c, _w = xs(TEXT % "")
        self.assertTrue(0 < first < 1080 and 0 < again < 1080)

    def test_an_enter_line_is_left_alone(self):
        text = TEXT.replace("Sultan (gussa)", "Sultan -> enter right\nSultan (gussa)") % " fast"
        (first, again), _sp, _c, w = xs(text)
        self.assertTrue(0 < again < 1080)
        self.assertFalse(any("wapas le aaya" in x for x in w))


if __name__ == "__main__":
    unittest.main()

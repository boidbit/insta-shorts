"""WHATSAPP / INSTA / ORDER / UPI cards inside a story.  python -m unittest discover -s tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import ui                               # noqa: E402
from studio.render import make_video                # noqa: E402
from studio.script import parse_script, ui_line     # noqa: E402

STORY = ("HOOK: x\nCAST: M = mummy, B = school_boy\nSCENE: living_room\nM: Padhai? | पढ़ाई?\n%s\n"
         "B (scared): Mummy! | मम्मी!\n")


class Cards(unittest.TestCase):
    def test_the_lines(self):
        spec, hold, warn = ui_line("WHATSAPP", "Mummy | < Kahan ho? | > Library me | < Photo bhejo")
        self.assertIsNone(warn)
        self.assertEqual([m["side"] for m in spec["messages"]], ["them", "me", "them"])
        self.assertGreater(hold, 3.0)
        self.assertEqual(ui_line("INSTA", "bittu | 2,500 | chill | 🏖️")[0]["likes"], 2500)
        self.assertEqual(ui_line("ORDER", "Zomato | Paneer | Rs 349")[0]["color"], [226, 55, 68])
        self.assertEqual(ui_line("UPI", "Rs 2000 | Sharma ji | Payment failed")[0]["payee"], "Sharma ji")
        self.assertIsNotNone(ui_line("WHATSAPP", "Mummy")[2])

    def test_each_card_is_drawn_and_the_story_waits_for_it(self):
        for line, typ in (("WHATSAPP: Mummy | < Kahan ho? | > Library me", "phone_chat"),
                          ("INSTA: bittu | 2 | chill", "insta"), ("ORDER: Swiggy | Biryani | Rs 299", "order"),
                          ("UPI: Rs 50 | Chaiwala", "upi")):
            sc, w = parse_script(STORY % line)
            self.assertEqual(w, [], line)
            v = make_video(sc, 180, use_tts=False, hook="off")
            p = getattr(v, "parts", [v])[0]
            o = next(o for o in p.plan.overlays if o.get("type") == typ)
            after = next(sp for sp in p.plan.speech if sp["who"] == "B")
            self.assertGreaterEqual(after["start"], o["from"] + 1.5, typ)
            self.assertEqual(v.frame(o["from"] + 1.2).size, (180, 320))

    def test_a_failed_payment_gets_a_red_cross(self):
        for status, red in (("Payment failed", True), ("Payment successful", False), ("Declined", True)):
            im = ui.upi({"amount": "Rs 1", "status": status}, 1.5, 0.5)
            px = im.getpixel((int(im.width / 2) - 40, int(230 * 0.5)))
            self.assertEqual(px[0] > px[1], red, status)


if __name__ == "__main__":
    unittest.main()

"""On a call (phone_call) the phone is upright on the ear: in the hand that is up (also for somebody facing left,
whose pose is mirrored), on the ear in profile, and a dog has it tucked against its ear. python -m unittest"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import actions                                # noqa: E402
from studio import animals                                # noqa: E402


class PhoneCall(unittest.TestCase):
    def test_the_phone_is_in_the_raised_hand(self):
        for d in ("right", "left"):
            p = actions.phone_call(0.5, 1.0, 1.0, 0.0, {"_dir": d})
            self.assertEqual(p["prop"], "phone_ear")
            up = "R" if d == "right" else "L"
            self.assertEqual(p["prop_hand"], up, d)              # the hand that goes to the ear holds it

    def test_a_dog_on_the_phone(self):
        calls = []
        real = animals._dog_phone
        animals._dog_phone = lambda *a: calls.append(a)
        try:
            from studio.render import Sequence
            from studio import script
            sc, _w = script.parse_script("HOOK: x\nSCENE: gaon\nKIRDAAR: Sultan, Daddu\nCAMERA: classic\n"
                                         "Sultan (phone_call): Haan bol. | हाँ बोल।\nDaddu (soch): Kaun? | कौन?\n")
            seq = Sequence(sc, 270, False, None, None)
            seq.frame(seq.parts[0].plan.speech[0]["start"] + 0.5)
        finally:
            animals._dog_phone = real
        self.assertTrue(calls)


if __name__ == "__main__":
    unittest.main()

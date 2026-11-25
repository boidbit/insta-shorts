"""The film camera (CAMERA: film, the default of the new camera): a conversation cut into over-the-shoulder shots,
three-quarter singles, reactions, low / high angles, inserts and a punch that pushes in. python -m unittest"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import script                                 # noqa: E402
from studio.render import Sequence                        # noqa: E402

OFFICE = """HOOK: Boss ka 2 minute ka kaam
SCENE: office
Boss (khush): Arey Sharma, sun, ek chhota sa kaam hai, bas do minute ka. | अरे शर्मा, सुन, एक छोटा सा काम है, बस दो मिनट का।
Sharma (soch): Sir, saat baj gaye hain. | सर, सात बज गए हैं।
Boss (akad): Haan toh? Do minute hi toh hai. | हाँ तो? दो मिनट ही तो है।
Sharma (bore): Pichhle hafte wala kaam abhi tak chal raha hai. | पिछले हफ़्ते वाला काम अभी तक चल रहा है।
Sharma -> facepalm
Boss (khush): Toh dono saath me kar lo, time bachega. | तो दोनों साथ में कर लो, टाइम बचेगा।
"""


def part(text):
    sc, w = script.parse_script(text)
    return Sequence(sc, 1080, False, None, None).parts[0], w


class FilmShots(unittest.TestCase):
    def test_a_conversation_is_cut_like_a_film(self):
        p, w = part(OFFICE)
        self.assertEqual(w, [])
        shots = p.plan.counter_shots
        kinds = [s["kind"] for s in shots]
        self.assertEqual(kinds[0], "free")                               # the opening: wide, the plain camera
        self.assertIn("ots", kinds)
        self.assertIn("react", kinds)                                    # Sharma's facepalm gets his own shot
        self.assertIn("low", kinds)                                      # Boss's swagger (akad): from below
        self.assertEqual(kinds[-1], "punch")
        for s in shots:
            if s["kind"] == "ots":                                       # the listener's back in the near corner
                backs = [n for n, o in s["ov"].items() if o.get("view") == "back"]
                self.assertEqual(len(backs), 1)
                talker = [n for n, o in s["ov"].items() if o.get("view") == "front"][0]
                self.assertEqual(s["ov"][talker]["turn34"], 1.0)        # three-quarter, not to the lens
                self.assertTrue(s["blur"])

    def test_the_180_degree_rule_and_the_reverse_angle(self):
        p, _ = part(OFFICE)
        for s in p.plan.counter_shots:
            if s["kind"] in ("ots", "single", "low", "react", "punch"):
                talker = next(n for n, o in s["ov"].items() if not o.get("hidden") and o.get("view") != "back")
                left = p.plan.chars[talker].x < min(c.x for c in p.plan.chars.values() if c.name != talker)
                self.assertEqual(s["ov"][talker]["facing"], "right" if left else "left")   # looks across the frame
                self.assertEqual(s["mirror"], not left)                  # the right one: the other side of the place

    def test_no_mirror_where_something_is_written(self):
        p, _ = part("HOOK: x\nSCENE: podcast\nGappu (khush): Toh bataiye Daddu ji, aapka struggle kya tha?\n"
                    "Daddu (soch): Roj subah tera podcast sunna, chhore.\nGappu (hairan): Wow, ye clip viral hogi!\n"
                    "Daddu (chalak): Tere bara views me se gyarah toh main hi hoon.\n")
        self.assertTrue(p.plan.counter_shots)
        self.assertFalse(any(s.get("mirror") for s in p.plan.counter_shots))     # GAPPCAST never reads backwards

    def test_the_punch_line_pushes_in(self):
        p, _ = part(OFFICE)
        last = p.plan.counter_shots[-1]
        self.assertEqual(last["kind"], "punch")
        self.assertGreater(last["cam1"][0], last["cam"][0])
        z0 = p._cam_view(last["t0"] + 0.01)[0]
        z1 = p._cam_view(min(last["t1"], p.plan.duration) - 0.01)[0]
        self.assertGreater(z1, z0)

    def test_an_insert_on_what_they_hold(self):
        p, _ = part("HOOK: x\nSCENE: room\nPapa (gussa, phone): Ye kya hai? Raat ke do baje tak phone pe kiske saath "
                    "chat chal rahi thi?\nBeta (darr): Papa... wo... group study thi, sach me.\n"
                    "Papa (soch): Group study? Group ka naam Pubg Squad hai.\nBeta (chalak): Haan papa, physics.\n")
        kinds = [s["kind"] for s in p.plan.counter_shots]
        self.assertEqual(kinds[1], "insert")
        self.assertEqual(kinds[3], "high")                               # the scared one: from above
        ins = p.plan.counter_shots[1]
        x, y = p._insert_hand("Papa", ins["t0"] + 0.3)
        z, vl, vt, vw, vh = p._cam_view(ins["t0"] + 0.3)
        self.assertGreater(z, 2.0)
        self.assertTrue(vl <= x * p.s <= vl + vw and vt <= y * p.s <= vt + vh)

    def test_a_dog_gets_singles_turned_to_the_one_it_talks_to(self):
        p, _ = part("HOOK: x\nSCENE: gaon\nDaddu (gussa): Re Sultan, meri safed murgi kahan gayi?\n"
                    "Sultan (smile): Kaunsi murgi baba, apun ne toh dekhi bhi nahi.\n"
                    "Daddu (hairan): Wahi safed wali, tere mooh pe pankh hain!\nSultan (smile): Wo toh haftaa thi baba.\n")
        shots = [s for s in p.plan.counter_shots if s["kind"] != "free"]
        self.assertNotIn("ots", [s["kind"] for s in shots])              # a dog has no back-of-the-head shot
        dog = [s for s in shots if "Sultan" in s["ov"] and not s["ov"]["Sultan"].get("hidden")]
        self.assertTrue(dog)
        self.assertEqual(dog[0]["ov"]["Sultan"]["view"], "turn")

    def test_sitcom_and_seedha(self):
        p, _ = part(OFFICE + "CAMERA: seedha\n")
        self.assertEqual(p.plan.counter_shots, [])
        p, _ = part(OFFICE + "CAMERA: sitcom\n")
        self.assertEqual(p.plan.counter_shots, [])
        self.assertTrue(all(seg[3] <= 1.15 + 1e-6 for seg in p.plan.cam_segments))   # mostly wide
        p, w = part(OFFICE + "CAMERA: classic\n")
        self.assertEqual(p.plan.counter_shots, [])

    def test_a_walk_or_a_fall_is_seen_wide(self):
        p, _ = part(OFFICE.replace("Sharma -> facepalm", "Sharma -> faint"))
        self.assertNotIn("react", [s["kind"] for s in p.plan.counter_shots])

    def test_running_out_is_seen_wide(self):
        """`Papa -> ghoorna` then `Reelesh -> exit left fast`, `Papa -> exit left fast`: the reaction single on Papa hid
        everybody else and went on through both exits, so Reelesh ran out unseen and the camera stayed on the empty
        spot. An exit is a wide shot with everybody in it."""
        p, w = part(OFFICE + "Boss -> ghoorna angry\nSharma -> exit left fast\nBoss -> exit left fast\n")
        shots = p.plan.counter_shots
        for name in ("Sharma", "Boss"):
            c = p.plan.chars[name]
            m = next(m for m in c.moves if m[4] < -100)
            run = (m[0] + m[1]) / 2.0
            shot = next(s for s in shots if s["t0"] <= run < s["t1"])
            self.assertEqual(shot["kind"], "free", (name, shot))
            self.assertFalse(shot.get("ov", {}).get(name, {}).get("hidden"))

    def test_the_page_has_the_camera_option(self):
        with open(os.path.join(os.path.dirname(__file__), "..", "index.html"), encoding="utf-8") as f:
            page = f.read()
        self.assertIn('<select id="shots">', page)
        self.assertIn('"CAMERA: " + $("shots").value', page)


if __name__ == "__main__":
    unittest.main()

import unittest

from studio import animals, script
from studio.scene import split_scenes


class DogActingTests(unittest.TestCase):
    def test_dog_folds_to_the_floor_and_stays_there(self):
        def head_height(t):
            _, anchors = animals.build_animal({"kind": "dog", "pose_view": "front"}, "faint",
                                              t, t, 540, 1500, 1, 1, False, False)
            return anchors["feet"][1] - anchors["head_center"][1]
        self.assertGreater(head_height(0), head_height(1) + 130)
        self.assertAlmostEqual(head_height(1), head_height(3), delta=6)

    def test_collar_cutaway_keeps_daddu_as_an_offscreen_voice(self):
        scene, warnings = script.parse_script(
            "HOOK: Chitthi\nKIRDAAR: Sultan, Daddu\nSCENE: handpump\n"
            "Sultan (wag): Kya? | क्या?\nSCENE: sultan_patta\n"
            "Daddu: Ek patta. | एक पट्टा।\nCTA: Part 3?\n")
        self.assertEqual(warnings, [])
        wide, insert = split_scenes(scene)
        self.assertFalse(wide["characters"]["Sultan"].get("hidden"))
        self.assertTrue(all(c.get("hidden") for c in insert["characters"].values()))
        self.assertFalse(insert["meta"]["auto_camera"])
        self.assertTrue(any(e.get("who") == "Daddu" and "say" in e for e in insert["timeline"]))

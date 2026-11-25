"""The voice take is cut where each line's words end (studio.align), not at a comma's pause inside a line."""
import os
import sys
import unittest
from unittest import mock

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from studio import align as A                 # noqa: E402
from studio import gemini_tts as G            # noqa: E402

SR = 24000


def tone(secs, f=180):
    t = np.arange(int(SR * secs)) / SR
    return (0.3 * np.sin(2 * np.pi * f * t)).astype(np.float32)


def gap(secs):
    return np.zeros(int(SR * secs), np.float32)


class Skeleton(unittest.TestCase):
    def test_script_and_heard_spelling_read_the_same(self):
        self.assertEqual(A.skeleton("जब घरवाले और दुनिया"), A.skeleton("जब गर्वाले और दून्या"))
        self.assertEqual(A.skeleton("आज़ाद"), A.skeleton("आजाद"))


class CommaIsNotALineBreak(unittest.TestCase):
    """Gappu: "Jab gharwale ... haste the, toh aapne haar kyun nahi maani?" then Reelesh: "Gappu bhai...".
    The comma's pause (0.5 s) is longer than the line break (0.2 s): the pause cut takes the comma."""
    texts = ["जब घरवाले हँसते थे, तो आपने हार क्यों नहीं मानी?", "गप्पू भाई सच बोलूँ"]

    def take(self):
        # 0.1 | "jab gharwale haste the" 0.1-2.1 | comma 2.1-2.6 | "toh aapne haar..." 2.6-4.6 | break 4.6-4.8 | ...
        return np.concatenate([gap(0.1), tone(2.0), gap(0.5), tone(2.0, 140), gap(0.2), tone(1.5, 220), gap(0.1)])

    def heard(self):
        return [(0.1, 0.6, " जब"), (0.6, 1.3, " गरवाले"), (1.3, 2.0, " हसते थे,"), (2.6, 3.0, " तो"),
                (3.0, 3.5, " आपने"), (3.5, 3.9, " हार"), (3.9, 4.3, " क्यों नहीं"), (4.3, 4.6, " मानी?"),
                (4.8, 5.3, " गपू"), (5.3, 5.8, " भाई"), (5.8, 6.3, " सच बोलू")]

    def test_the_heard_words_move_the_cut_to_the_line_break(self):
        x = self.take()
        wrong = [(0.0, 2.3), (2.3, len(x) / SR)]          # cut at the comma (what happened in the reel)
        with mock.patch.object(A, "words", return_value=self.heard()):
            spans, moved = A.fix_spans(x, SR, self.texts, wrong)
        self.assertEqual(moved, 1)
        self.assertTrue(4.6 <= spans[0][1] <= 4.9 and 4.55 <= spans[1][0] <= 4.8, spans)

    def test_a_right_cut_stays(self):
        x = self.take()
        right = [(0.0, 4.76), (4.64, len(x) / SR)]
        with mock.patch.object(A, "words", return_value=self.heard()):
            self.assertEqual(A.fix_spans(x, SR, self.texts, right), (right, 0))

    def test_without_the_recogniser_the_pause_cut_stays(self):
        x = self.take()
        cut = [(0.0, 2.3), (2.3, len(x) / SR)]
        with mock.patch.object(A, "words", side_effect=ImportError("no faster_whisper")):
            self.assertEqual(A.fix_spans(x, SR, self.texts, cut), (cut, 0))

    def test_something_else_heard_is_not_trusted(self):
        x = self.take()
        cut = [(0.0, 2.3), (2.3, len(x) / SR)]
        with mock.patch.object(A, "words", return_value=[(0.1, 4.0, " नमस्ते दुनिया")]):
            self.assertEqual(A.fix_spans(x, SR, self.texts, cut), (cut, 0))

    def test_the_gemini_cut_uses_it_once_per_take(self):
        import tempfile
        x = self.take()
        d = tempfile.mkdtemp()
        wrong = [(0.0, 2.3), (2.3, len(x) / SR)]
        with mock.patch.dict(os.environ, {"ALIGN": "on"}), \
                mock.patch.object(A, "words", return_value=self.heard()) as w:
            a = G._heard_spans(d, x, self.texts, wrong)
            b = G._heard_spans(d, x, self.texts, wrong)       # the frame / cover render: from the file
        self.assertEqual(w.call_count, 1)
        self.assertEqual([list(s) for s in a], [list(s) for s in b])
        self.assertGreater(a[0][1], 4.5)


if __name__ == "__main__":
    unittest.main()

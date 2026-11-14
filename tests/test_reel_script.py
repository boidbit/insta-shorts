"""Every reel keeps the script it was made from.  python -m unittest discover -s tests"""
import json
import os
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")


def read(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return f.read()


class ReelScript(unittest.TestCase):
    def test_the_workflow_puts_the_script_in_every_release(self):
        wf = read(".github/workflows/render.yml")
        self.assertIn("cp scenes/generated/web_script.txt out/script.txt", wf)
        self.assertIn('echo "<!-- script -->"; cat out/script.txt', wf)
        self.assertIn("out/script.txt out/*.scene.json", wf)
        self.assertNotIn('if [ "$STAGE" = "sound_video" ] && [ -f scenes/generated/web_script.txt ]', wf)

    def test_the_page_shows_it(self):
        page = read("index.html")
        for needle in ('id="relScriptBox"', 'id="relScriptCopy"', 'id="relScriptOpen"', 'id="relScriptCards"',
                       "function showReelScript", 'fetch("assets/reel_scripts.json"'):
            self.assertIn(needle, page)

    def test_the_older_reels_scripts(self):
        old = json.loads(read("assets/reel_scripts.json"))
        self.assertGreater(len(old), 50)
        for tag, script in old.items():
            self.assertTrue(tag.startswith("reel-"), tag)
            self.assertIn("HOOK:", script, tag)


if __name__ == "__main__":
    unittest.main()

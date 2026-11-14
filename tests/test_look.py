"""Every video its own look (colour mood, place colours, opening shot), the CTA as a card / sticker / caption, the
@handle in the corner, and the cover picture. python -m unittest discover -s tests"""
import os
import sys
import unittest

from PIL import Image, ImageChops, ImageStat

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from studio import theme                                       # noqa: E402
from studio.cover import cover_emoji, cover_words, make_cover  # noqa: E402
from studio.render import make_video                           # noqa: E402
from studio.script import OPENINGS, parse_script               # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
STORY = """HOOK: Mummy ka "bas 5 minute" 😭
CAST: M = mummy, R = beta
SCENE: kitchen
M (angry, point): Raju, bas 5 minute me khana lag raha hai! | राजू, बस 5 मिनट में खाना लग रहा है!
R (smile): Theek hai mummy, ek game aur | ठीक है मम्मी, एक गेम और
M (angry): Bas 5 minute! | बस 5 मिनट!
CTA: Har ghar ki kahani 😂 Tag karo
"""


def read(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return f.read()


def diff(a, b):
    return sum(ImageStat.Stat(ImageChops.difference(a.convert("RGB"), b.convert("RGB"))).mean) / 3


def hook_card(sc):
    return next(o for o in sc["overlays"] if o.get("style") == "hook")


class ThemeTests(unittest.TestCase):
    def test_every_video_gets_its_own_and_the_same_hook_the_same(self):
        names = {theme.auto("hook %d" % i) for i in range(40)}
        self.assertGreaterEqual(len(names), 5)
        self.assertEqual(theme.auto("Dadi ka phone"), theme.auto("Dadi ka phone"))
        sc, warns = parse_script(STORY)
        self.assertEqual(warns, [])
        self.assertEqual(sc["meta"]["theme"], theme.auto(sc["hook"]))

    def test_the_script_chooses_and_classic_keeps_the_old_look(self):
        sc, _ = parse_script(STORY + "COLOR: gulabi\n")
        self.assertEqual(sc["meta"]["theme"], "rose")
        self.assertEqual(hook_card(sc)["color"], list(theme.THEMES["rose"]["hook"]))
        cta = [ev["overlay"] for ev in sc["scenes"][-1]["timeline"] if (ev.get("overlay") or {}).get("cta")][0]
        self.assertEqual(cta["color"], list(theme.THEMES["rose"]["card"]))
        sc, _ = parse_script(STORY + "CAMERA: classic\n")
        self.assertNotIn("theme", sc["meta"])
        self.assertNotIn("color", hook_card(sc))
        _sc, warns = parse_script(STORY + "COLOR: purple\n")
        self.assertTrue(any("COLOR" in w for w in warns))

    def test_the_grade_and_the_place_colours(self):
        im = Image.new("RGB", (8, 8), (180, 140, 100))
        self.assertEqual(theme.grade(im, "classic").getpixel((0, 0)), (180, 140, 100))
        self.assertNotEqual(theme.grade(im, "golden").getpixel((0, 0)), (180, 140, 100))
        sky, wall = Image.new("RGB", (4, 4), (120, 190, 240)), Image.new("RGB", (4, 4), (220, 200, 140))
        self.assertLess(diff(theme.shift_place(sky, "rose"), sky), 2.0)          # the sky stays blue
        self.assertGreater(diff(theme.shift_place(wall, "rose"), wall), 3.0)     # the walls change

    def test_two_moods_two_different_pictures(self):
        a, _ = parse_script(STORY + "COLOR: golden\n")
        b, _ = parse_script(STORY + "COLOR: cool\n")
        fa = make_video(a, 216, use_tts=False).frame(1.0)
        fb = make_video(b, 216, use_tts=False).frame(1.0)
        self.assertGreater(diff(fa, fb), 3.0)


class OpeningTests(unittest.TestCase):
    def test_the_first_shot_varies_by_video(self):
        seen = set()
        for i in range(30):
            sc, _ = parse_script(STORY.replace("Mummy ka", "Mummy %d ka" % i))
            first = next(e for e in sc["scenes"][0]["timeline"] if e.get("say"))
            seen.add("reveal" if first.get("camera", {}).get("reveal") else first.get("shot") or "plain")
        self.assertEqual(seen, set(OPENINGS) - {"plain"} | {"plain"})

    def test_not_on_quick_banter_nor_in_classic(self):
        for extra, line in (("", "A: Kya? | क्या?\n"), ("CAMERA: classic\n", "A: Raju, bas 5 minute me khana | राजू\n")):
            for i in range(12):
                sc, _ = parse_script("HOOK: h%d\nCAST: A = boy, B = girl\nSCENE: room\n%sB: Haan | हाँ\n%s" % (i, line, extra))
                first = next(e for e in sc["scenes"][0]["timeline"] if e.get("say"))
                self.assertNotIn("camera", first)
                self.assertNotIn("shot", first)


class CtaTests(unittest.TestCase):
    def overlays(self, sc):
        return [ev["overlay"] for s in sc["scenes"] for ev in s["timeline"] if isinstance(ev.get("overlay"), dict)]

    def test_card_sticker_caption(self):
        card, _ = parse_script(STORY)
        self.assertTrue(any(o.get("cta") for o in self.overlays(card)))
        sticker, warns = parse_script(STORY + "CTA_STYLE: sticker\n")
        self.assertEqual(warns, [])
        st = [o for o in self.overlays(sticker) if o.get("cta_sticker")]
        self.assertEqual(len(st), 1)
        self.assertFalse(any(o.get("cta") for o in self.overlays(sticker)))
        last_say = [ev for ev in sticker["scenes"][-1]["timeline"] if "say" in ev][-1]
        self.assertIs(last_say.get("overlay"), st[0])                         # on the punch line
        caption, _ = parse_script(STORY + "CTA_STYLE: caption\n")
        self.assertEqual([o for o in self.overlays(caption) if o.get("cta") or o.get("cta_sticker")], [])
        self.assertIn("Tag karo", caption["post"]["caption"])
        d = [make_video(sc, 216, use_tts=False).duration for sc in (card, sticker, caption)]
        self.assertLess(d[1], d[0])                                           # no end card: shorter
        self.assertAlmostEqual(d[1], d[2], delta=0.05)

    def test_no_cta_at_all_is_fine(self):
        sc, warns = parse_script(STORY.replace("CTA: Har ghar ki kahani 😂 Tag karo\n", ""))
        self.assertEqual(warns, [])
        self.assertFalse(any(o.get("cta") for o in self.overlays(sc)))


class HandleAndCoverTests(unittest.TestCase):
    def test_the_handle_runs_up_the_side(self):
        sc, _ = parse_script(STORY + "HANDLE: desitoons\n")
        h = [o for o in sc["overlays"] if o.get("handle")][0]
        self.assertEqual(h["text"], "@desitoons")
        self.assertEqual(h["rotate"], 90)
        v = make_video(sc, 216, use_tts=False)
        plain = make_video(parse_script(STORY)[0], 216, use_tts=False)
        self.assertGreater(diff(v.frame(3.0), plain.frame(3.0)), 0.05)

    def test_the_cover(self):
        sc, _ = parse_script(STORY + "COLOR: rose\nHANDLE: desitoons\nMASCOT: bhoot\n")
        self.assertEqual(cover_words(sc), 'MUMMY KA "BAS 5 MINUTE"')
        self.assertEqual(cover_emoji(sc), "😭")
        v = make_video(sc, 216, use_tts=False)
        im = make_cover(v, sc)
        self.assertEqual(im.size, (216, 384))
        self.assertEqual(im.getpixel((1, 200)), tuple(theme.THEMES["rose"]["hook"]))   # the frame in its colour
        sc2, _ = parse_script(STORY + "COLOR: cool\nCOVER: KHANA KAB? 🍛\n")
        self.assertEqual(cover_words(sc2), "KHANA KAB?")
        im2 = make_cover(make_video(sc2, 216, use_tts=False), sc2)
        self.assertGreater(diff(im, im2), 5.0)

    def test_a_runner_without_network_cannot_hang_the_job(self):
        for wf in (".github/workflows/render.yml", ".github/workflows/golden.yml"):
            text = read(wf)
            step = text[text.index("- name: System packages"):]
            step = step[:step.index("- name:", 10)]
            self.assertIn("timeout-minutes: 12", step, wf)
            self.assertIn("Acquire::http::Timeout=20", step, wf)
            self.assertIn("for try in 1 2 3", step, wf)
            self.assertIn("bash .github/apt_mirrors.sh", step, wf)          # *.ubuntu.com down: another mirror
        sh = read(".github/apt_mirrors.sh")
        self.assertIn("mirrors.edge.kernel.org/ubuntu", sh)

    def test_the_workflow_and_the_page(self):
        self.assertIn("--cover -o \"out/$name.cover.png\"", read(".github/workflows/render.yml"))
        page = read("index.html")
        for needle in ('id="color"', 'id="ctaStyle"', 'id="handle"', "🖼️ Cover download", 'endsWith(".cover.png")'):
            self.assertIn(needle, page)
        self.assertNotIn('out.push("CTA: line nahi hai")', page)


if __name__ == "__main__":
    unittest.main()


class Clothes(unittest.TestCase):
    """All clothes words of a CAST entry are read together (a second one used to throw the first away)."""

    def spec(self, words):
        from studio.characters import resolve_spec
        sc, w = parse_script("HOOK: x\nCAST: A = %s\nSCENE: office\nA: Haan | हाँ\n" % words)
        self.assertEqual(w, [])
        return resolve_spec(sc["characters"]["A"])

    def test_a_kurta_with_a_vest_is_the_neta_s_jacket_not_a_banyan(self):
        s = self.spec("uncle short kurta saffron chubby tilak vest saffron moustache")
        self.assertEqual((s["outfit"], s["color"]), ("kurta_jacket", "saffron"))
        self.assertNotEqual(s["accent"], "saffron")              # the jacket shows on the kurta
        s = self.spec("uncle kurta white vest grey")
        self.assertEqual((s["outfit"], s["color"], s["accent"]), ("kurta_jacket", "white", "grey"))
        self.assertEqual(self.spec("uncle kurta jacket maroon")["accent"], "maroon")

    def test_a_banyan_is_still_a_banyan(self):
        self.assertEqual(self.spec("uncle vest")["outfit"], "vest")
        self.assertEqual(self.spec("uncle banyan white")["outfit"], "vest")
        self.assertEqual(self.spec("chaiwala")["outfit"], "vest")

    def test_a_shirt_with_a_jacket_is_a_blazer(self):
        s = self.spec("boy shirt jacket navy")
        self.assertEqual((s["outfit"], s["accent"]), ("blazer", "navy"))
        self.assertNotEqual(s.get("color"), "navy")

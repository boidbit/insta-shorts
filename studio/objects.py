"""Set objects: drawn vehicles / props that sit in a scene or drive in and out (or your own PNG sprite).

    OBJ: truck enter left          drives in from the left and stops at its place (right of centre)
    OBJ: dustbin left              just appears at the left
    OBJ: car red go center         (re)positions: drives to the centre
    OBJ: truck exit right          drives away
    OBJ: assets/objects/x.png right   your own transparent PNG

Everything is drawn in logical 1080x1920 units with the ground-contact point of the object at (0, 0).
"""
import math

from PIL import Image

from .backgrounds import G, INK
from .characters import PALETTE, shade
from .util import asset_path

PAD = 30
SPOTS = {"left": 270.0, "center": 540.0, "right": 810.0}      # where an object rests (x of its middle)
OFFSCREEN = {"left": -480.0, "right": 1560.0}
GREEN = (64, 150, 92)


class Pen:
    """Draws in object coordinates (origin = ground contact, y up is negative)."""

    def __init__(self, s, w, h):
        self.g = G(s, w + 2 * PAD, h + 2 * PAD, (0, 0, 0, 0), "RGBA")
        self.ox, self.oy = w / 2.0 + PAD, h + PAD
        self.w, self.h = w, h

    def _t(self, pts):
        return [(x + self.ox, y + self.oy) for x, y in pts]

    def rect(self, x0, y0, x1, y1, fill=None, outline=INK, w=5):
        self.g.rect(x0 + self.ox, y0 + self.oy, x1 + self.ox, y1 + self.oy, fill, outline, w)

    def rrect(self, x0, y0, x1, y1, r, fill=None, outline=INK, w=5):
        self.g.rrect(x0 + self.ox, y0 + self.oy, x1 + self.ox, y1 + self.oy, r, fill, outline, w)

    def poly(self, pts, fill=None, outline=INK, w=5):
        self.g.poly(self._t(pts), fill, outline, w)

    def line(self, pts, color=INK, w=5):
        self.g.line(self._t(pts), color, w)

    def ellipse(self, x0, y0, x1, y1, fill=None, outline=INK, w=5):
        self.g.ellipse(x0 + self.ox, y0 + self.oy, x1 + self.ox, y1 + self.oy, fill, outline, w)

    def circle(self, cx, cy, r, fill=None, outline=INK, w=5):
        self.g.circle(cx + self.ox, cy + self.oy, r, fill, outline, w)

    def image(self):
        return self.g.done()


# ---------------------------------------------------------------- the drawings
# each returns (pen, wheels) where wheels = [(x, y, radius)] drawn separately so they can spin
def _truck(s, c):
    p = Pen(s, 640, 330)
    body, dark = c, shade(c, 0.78)
    p.rrect(-305, -85, 305, -62, 8, (70, 72, 80))                                   # chassis
    p.rrect(-312, -258, 96, -80, 16, body)                                          # waste box
    for x in range(-270, 80, 52):
        p.line([(x, -240), (x, -100)], dark, 5)                                     # ribs
    p.poly([(-318, -258), (-318, -236), (-250, -214), (-250, -258)], dark)          # loading hopper lip
    p.rect(-312, -140, -262, -82, (44, 46, 52))                                     # hopper opening
    p.poly([(98, -80), (98, -252), (192, -252), (262, -184), (306, -172), (306, -80)], shade(c, 1.12))   # cab
    p.poly([(118, -236), (118, -176), (246, -176), (190, -236)], (170, 214, 238))   # window
    p.line([(160, -168), (160, -84)], INK, 4)
    p.rect(292, -128, 310, -104, (255, 232, 140), INK, 4)                           # headlight
    p.rect(296, -92, 316, -70, (96, 98, 106))                                       # bumper
    p.circle(150, -270, 13, (255, 176, 40), INK, 4)                                 # beacon
    p.rrect(-150, -204, -20, -146, 8, (244, 242, 236))                              # white label with a bin pictogram
    p.rect(-104, -190, -66, -158, (96, 150, 110), INK, 4)
    p.rect(-110, -196, -60, -190, (96, 150, 110), INK, 4)
    return p, [(-190, -52, 52), (-60, -52, 52), (212, -52, 52)]


def _auto(s, c):
    p = Pen(s, 330, 270)
    p.poly([(-148, -104), (-140, -226), (84, -226), (124, -160), (156, -104)], (36, 38, 46))     # canopy
    p.line([(-120, -226), (-124, -104)], INK, 7)                                                 # rear pillar
    p.line([(70, -226), (88, -104)], INK, 7)                                                     # front pillar
    p.rrect(-150, -138, 156, -58, 14, c)                                                          # body
    p.rrect(-128, -184, 50, -138, 10, (150, 110, 80))                                             # passenger seat
    p.poly([(124, -160), (156, -104), (116, -104)], (170, 214, 238), INK, 4)                     # windscreen
    p.poly([(124, -92), (170, -92), (180, -64), (116, -58)], shade(c, 0.85))                      # front mudguard
    p.circle(168, -114, 11, (255, 232, 140), INK, 4)
    return p, [(-92, -34, 34), (-18, -34, 34), (136, -34, 34)]


def _car(s, c):
    p = Pen(s, 520, 250)
    p.rrect(-235, -118, 235, -44, 22, c)
    p.poly([(-120, -116), (-70, -192), (96, -192), (150, -116)], shade(c, 1.1))
    p.poly([(-96, -122), (-58, -178), (-4, -178), (-4, -122)], (170, 214, 238), INK, 4)
    p.poly([(14, -122), (14, -178), (86, -178), (126, -122)], (170, 214, 238), INK, 4)
    p.rect(214, -102, 236, -78, (255, 232, 140), INK, 4)
    p.rect(-236, -104, -222, -80, (220, 70, 70), INK, 3)
    return p, [(-142, -40, 40), (142, -40, 40)]


def _scooter(s, c):
    p = Pen(s, 300, 250)
    p.poly([(-110, -70), (-84, -160), (-30, -160), (-4, -92), (60, -92), (90, -150), (104, -150), (96, -60)], c)
    p.rrect(-84, -176, 4, -150, 8, (60, 52, 50))                                                           # seat
    p.line([(90, -148), (100, -232)], INK, 9)                                                               # fork
    p.line([(70, -234), (132, -234)], INK, 9)                                                               # handlebar
    p.circle(104, -222, 11, (255, 232, 140), INK, 4)
    return p, [(-96, -38, 38), (100, -38, 38)]


def _cow(s, c):
    p = Pen(s, 430, 290)
    white = (246, 242, 232)
    for x in (-118, -78, 52, 92):
        p.rect(x - 11, -112, x + 11, 0, white, INK, 5)                                                      # legs
        p.rect(x - 13, -16, x + 13, 0, (60, 52, 50), INK, 4)                                                # hooves
    p.line([(-176, -196), (-210, -150), (-206, -92)], INK, 6)                                               # tail
    p.rrect(-178, -218, 112, -92, 40, white)                                                                # body
    p.ellipse(-120, -208, -48, -150, c, None)
    p.ellipse(10, -150, 80, -100, c, None)
    p.poly([(96, -218), (128, -256), (186, -258), (200, -204), (176, -150), (116, -146)], white)            # head
    p.ellipse(150, -176, 214, -128, (236, 190, 170))                                                        # muzzle
    p.circle(176, -240, 7, INK, INK, 2)
    p.circle(168, -214, 6, INK, INK, 2)
    p.poly([(120, -252), (104, -276), (132, -266)], (236, 190, 170))                                        # ear
    p.line([(134, -258), (126, -290)], (220, 214, 190), 8)                                                  # horn
    return p, []


def _dustbin(s, c):
    p = Pen(s, 170, 210)
    p.poly([(-54, 0), (-66, -150), (66, -150), (54, 0)], c)
    for x in (-30, 0, 30):
        p.line([(x * 0.9, -12), (x * 1.0, -140)], shade(c, 0.74), 4)
    p.rrect(-74, -184, 74, -150, 10, shade(c, 1.12))
    p.rrect(-16, -200, 16, -184, 4, shade(c, 0.8))
    return p, []


def _bags(s, c):
    p = Pen(s, 280, 170)
    black = (38, 38, 46)
    for cx, w, h in ((-70, 56, 66), (24, 64, 76), (100, 48, 56)):
        p.ellipse(cx - w, -h * 1.6, cx + w, 0, black)
        p.poly([(cx - 14, -h * 1.6 + 6), (cx, -h * 1.6 - 22), (cx + 14, -h * 1.6 + 6)], black)
        p.line([(cx - w * 0.5, -h * 1.1), (cx - w * 0.3, -h * 0.45)], (96, 96, 108), 4)
    return p, []


def _table(s, c):
    p = Pen(s, 380, 230)
    for x in (-150, 150):
        p.rect(x - 11, -150, x + 11, 0, shade(c, 0.8))
    p.rrect(-185, -176, 185, -146, 8, c)
    return p, []


OBJECTS = {            # kind: (drawer, default colour, default scale, spins its wheels)
    "truck": (_truck, GREEN, 1.0),
    "auto": (_auto, (240, 196, 60), 1.0),
    "car": (_car, PALETTE["red"], 1.0),
    "scooter": (_scooter, PALETTE["blue"], 1.0),
    "cow": (_cow, (156, 110, 76), 1.0),
    "dustbin": (_dustbin, (70, 130, 170), 1.0),
    "bags": (_bags, (38, 38, 46), 1.0),
    "table": (_table, (160, 112, 76), 1.0),
}
ALIASES = {"garbage_truck": "truck", "kachra_gaadi": "truck", "gaadi": "truck", "rickshaw": "auto", "gai": "cow",
           "bike": "scooter", "dustbin": "dustbin", "bin": "dustbin", "thaila": "bags", "kachra": "bags"}
VEHICLES = ("truck", "auto", "car", "scooter")


def resolve_kind(word):
    w = str(word).lower()
    w = ALIASES.get(w, w)
    return w if w in OBJECTS or w.endswith((".png", ".webp")) else None


_cache = {}


def sprite(kind, s, color=None):
    """(RGBA image, (anchor x, anchor y), wheels [(x, y, r)] in image px) at render scale s."""
    key = (kind, round(s, 4), tuple(color) if color else None)
    if key in _cache:
        return _cache[key]
    if kind in OBJECTS:
        drawer, col, _ = OBJECTS[kind]
        pen, wheels = drawer(s, tuple(color) if color else col)
        im = pen.image()
        k = s
        out = (im, (pen.ox * k, pen.oy * k), [((x + pen.ox) * k, (y + pen.oy) * k, r * k) for x, y, r in wheels])
    else:                                                      # your own PNG: 320 logical px tall, feet at the bottom
        src = Image.open(asset_path(kind)).convert("RGBA")
        h = max(8, int(320 * s))
        im = src.resize((max(1, int(src.width * h / src.height)), h), Image.LANCZOS)
        out = (im, (im.width / 2.0, float(im.height)), [])
    _cache[key] = out
    return out


_wheel_cache = {}


def wheel_image(r, angle):
    """A wheel (tyre + hub + spokes) of pixel radius r rotated by `angle` degrees."""
    r = max(4, int(round(r)))
    key = (r, int(angle) % 360 // 6)
    if key in _wheel_cache:
        return _wheel_cache[key]
    sc = 3
    big = Image.new("RGBA", (r * 2 * sc + 8, r * 2 * sc + 8), (0, 0, 0, 0))
    from PIL import ImageDraw
    d = ImageDraw.Draw(big)
    c = big.width / 2.0
    R = r * sc
    d.ellipse([c - R, c - R, c + R, c + R], fill=(34, 34, 40), outline=INK, width=max(2, sc * 2))
    d.ellipse([c - R * 0.62, c - R * 0.62, c + R * 0.62, c + R * 0.62], fill=(190, 190, 198), outline=INK, width=sc * 2)
    for k in range(4):
        a = math.radians(k * 90)
        d.line([c, c, c + R * 0.58 * math.cos(a), c + R * 0.58 * math.sin(a)], fill=INK, width=max(2, sc * 2))
    d.ellipse([c - R * 0.14, c - R * 0.14, c + R * 0.14, c + R * 0.14], fill=(90, 90, 100), outline=INK, width=sc)
    big = big.rotate(-key[1] * 6, resample=Image.BICUBIC)
    im = big.resize((big.width // sc, big.height // sc), Image.LANCZOS)
    _wheel_cache[key] = im
    return im

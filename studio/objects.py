"""Set objects: drawn vehicles / props that sit in a scene or drive in and out (or your own PNG sprite).

    OBJ: truck enter left          drives in from the left and stops at its place (right of centre)
    OBJ: dustbin left              just appears at the left
    OBJ: car red go center         (re)positions: drives to the centre
    OBJ: truck exit right          drives away
    OBJ: assets/objects/x.png right   your own transparent PNG

Vehicles a character can ride (see rides.py) are drawn in parts: "back" = what is behind the rider (the inside of
a cab, seats), "front" = what is in front of the rider (the body with the windows cut out, pillars, roof).
"all" is the whole vehicle in one go (what you see when nobody rides it).

Everything is drawn in logical 1080x1920 units with the ground-contact point of the object at (0, 0).
"""
import math

from PIL import Image

from .backgrounds import G, INK
from .characters import PALETTE, shade
from .util import asset_path

PAD = 30
# One scale for the whole world. A standing character is ~800 units tall (at character scale 1); PERSON_R[kind] is how
# big that person is relative to the object's sprite, from real sizes (truck ~6.8 x 3.1 m, auto 2.7 x 1.75, car
# 4.2 x 1.5, bike 2.1 x 1.2, cow 2 x 1.45, person 1.7 m...). An object is drawn at (character scale / PERSON_R), so
# a vehicle is always in proportion to the people next to it, and a rider is as big as somebody standing.
PERSON_R = {"truck": 0.21, "auto": 0.34, "car": 0.27, "bike": 0.35, "scooter": 0.36, "cycle": 0.39,
            "cow": 0.44, "dustbin": 0.43, "bags": 0.62, "table": 0.50}
SPRITE_LEN = {"truck": 640, "auto": 380, "car": 520, "bike": 340, "scooter": 300, "cycle": 340,
              "cow": 430, "dustbin": 170, "bags": 280, "table": 380}
REF_SCALE = 0.95                                 # a typical character's scale
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
def _truck(s, c, part="all"):
    p = Pen(s, 640, 330)
    body, dark = c, shade(c, 0.78)
    win = [(118, -244), (118, -170), (246, -170), (196, -244)]
    if part == "back":                                                              # inside the cab, behind the driver
        p.poly(win, (62, 80, 96), None)
        p.rect(104, -170, 124, -90, (44, 58, 70), None)                             # seat back
        return p, []
    p.rrect(-305, -85, 305, -62, 8, (70, 72, 80))                                   # chassis
    p.rrect(-312, -258, 96, -80, 16, body)                                          # waste box
    for x in range(-270, 80, 52):
        p.line([(x, -240), (x, -100)], dark, 5)                                     # ribs
    p.poly([(-318, -258), (-318, -236), (-250, -214), (-250, -258)], dark)          # loading hopper lip
    p.rect(-312, -140, -262, -82, (44, 46, 52))                                     # hopper opening
    p.poly([(98, -80), (98, -252), (192, -252), (262, -184), (306, -172), (306, -80)], shade(c, 1.12))   # cab
    p.poly(win, (170, 214, 238) if part == "all" else (205, 232, 246, 46))          # window (see-through when ridden)
    p.line([(160, -166), (160, -84)], INK, 4)
    p.rect(292, -128, 310, -104, (255, 232, 140), INK, 4)                           # headlight
    p.rect(296, -92, 316, -70, (96, 98, 106))                                       # bumper
    p.circle(150, -270, 13, (255, 176, 40), INK, 4)                                 # beacon
    p.rrect(-150, -204, -20, -146, 8, (244, 242, 236))                              # white label with a bin pictogram
    p.rect(-104, -190, -66, -158, (96, 150, 110), INK, 4)
    p.rect(-110, -196, -60, -190, (96, 150, 110), INK, 4)
    return p, [(-190, -52, 52), (-60, -52, 52), (212, -52, 52)]


def _auto(s, c, part="all"):
    p = Pen(s, 380, 400)
    glass = (170, 214, 238) if part == "all" else (205, 232, 246, 46)
    if part in ("all", "back"):                                                     # seats, behind the riders
        p.rrect(-146, -176, -34, -124, 10, (150, 110, 80))                          # rear bench
        p.rrect(30, -166, 112, -124, 10, (128, 90, 66))                             # driver seat
        p.line([(96, -236), (126, -246)], INK, 9)                                   # steering handle
    if part == "back":
        return p, []
    p.rrect(-158, -128, 160, -62, 14, c)                                            # body
    p.line([(-146, -354), (-146, -128)], INK, 10)                                   # rear pillar
    p.line([(28, -354), (28, -128)], INK, 10)                                       # middle pillar
    p.poly([(118, -354), (150, -128), (118, -128)], glass)                          # windscreen
    p.line([(118, -354), (150, -128)], INK, 10)                                     # front pillar
    p.rrect(-170, -384, 128, -352, 10, (36, 38, 46))                                # roof
    p.poly([(120, -384), (178, -362), (120, -352)], (36, 38, 46))                   # roof peak over the windscreen
    p.poly([(126, -100), (176, -100), (188, -66), (122, -60)], shade(c, 0.85))      # front mudguard
    p.circle(174, -114, 11, (255, 232, 140), INK, 4)
    return p, [(-95, -36, 36), (136, -36, 36)]


def _car(s, c, part="all"):
    p = Pen(s, 520, 290)
    glass = (170, 214, 238) if part == "all" else (205, 232, 246, 46)
    rear = [(-100, -122), (-64, -232), (-6, -232), (-6, -122)]
    front = [(14, -122), (14, -232), (92, -232), (132, -122)]
    if part == "back":                                                              # the inside, behind the people
        for w in (rear, front):
            p.poly(w, (70, 82, 98), None)
        p.rect(-40, -226, -22, -122, (52, 62, 76), None)                            # seat backs
        p.rect(40, -226, 58, -122, (52, 62, 76), None)
        return p, []
    p.rrect(-235, -118, 235, -24, 22, c)
    p.poly([(-122, -116), (-74, -250), (104, -250), (154, -116)], shade(c, 1.1))     # cabin
    for w in (rear, front):
        p.poly(w, glass)
    p.rect(214, -102, 236, -78, (255, 232, 140), INK, 4)
    p.rect(-236, -104, -222, -80, (220, 70, 70), INK, 3)
    return p, [(-142, -40, 40), (142, -40, 40)]


def _scooter(s, c):
    p = Pen(s, 300, 250)
    p.poly([(-110, -70), (-84, -160), (-30, -160), (-4, -92), (60, -92), (90, -150), (104, -150), (96, -60)], c)
    p.rrect(-84, -176, 4, -150, 8, (60, 52, 50))                                                           # seat
    p.line([(86, -148), (76, -232)], INK, 9)                                                                # fork
    p.line([(46, -234), (108, -234)], INK, 9)                                                               # handlebar
    p.circle(88, -218, 11, (255, 232, 140), INK, 4)
    return p, [(-96, -38, 38), (100, -38, 38)]


def _bike(s, c, part="all"):
    """A motorbike, facing right."""
    p = Pen(s, 340, 270)
    p.line([(-112, -46), (-12, -74)], (60, 62, 70), 12)                              # swing arm
    p.rrect(-48, -128, 60, -50, 14, (90, 94, 104))                                   # engine block
    p.rect(-30, -112, 40, -96, (150, 154, 164), None)
    p.poly([(-36, -152), (62, -160), (100, -142), (84, -120), (-36, -120)], c)       # tank
    p.rrect(-140, -142, -34, -120, 9, (44, 40, 44))                                  # seat
    p.line([(100, -140), (126, -48)], (150, 152, 160) if False else (160, 162, 170), 10)   # front fork
    p.line([(94, -152), (86, -200), (112, -206)], INK, 8)                            # handlebar
    p.circle(128, -150, 17, (255, 232, 140), INK, 4)                                 # headlight
    p.line([(-12, -60), (-128, -72)], (130, 132, 140), 9)                            # exhaust
    p.rect(26, -66, 50, -58, (60, 60, 66), None)                                     # foot peg
    return p, [(-112, -46, 46), (118, -46, 46)]


def _cycle(s, c, part="all"):
    """A bicycle, facing right. The crank and pedals are drawn per frame (they turn)."""
    p = Pen(s, 340, 260)
    fr = (60, 62, 70)
    bb, seat, head, rear, front = (0, -58), (-8, -178), (84, -168), (-108, -60), (112, -60)
    for a, b in ((bb, seat), (seat, head), (bb, head), (bb, rear), (seat, rear)):
        p.line([a, b], c, 9)
    p.line([head, front], fr, 8)                                                     # fork
    p.line([head, (80, -206)], fr, 8)                                                # stem
    p.line([(68, -208), (100, -206)], INK, 8)                                        # handlebar
    p.rrect(-34, -194, 22, -178, 7, (44, 40, 44))                                    # saddle
    p.circle(bb[0], bb[1], 12, (150, 152, 160), INK, 4)
    return p, [(rear[0], rear[1], 60), (front[0], front[1], 60)]


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
    "bike": (_bike, PALETTE["red"], 1.0),
    "cycle": (_cycle, (60, 140, 200), 1.0),
    "cow": (_cow, (156, 110, 76), 1.0),
    "dustbin": (_dustbin, (70, 130, 170), 1.0),
    "bags": (_bags, (38, 38, 46), 1.0),
    "table": (_table, (160, 112, 76), 1.0),
}
ALIASES = {"garbage_truck": "truck", "kachra_gaadi": "truck", "gaadi": "truck", "rickshaw": "auto", "gai": "cow",
           "motorcycle": "bike", "bullet": "bike", "bicycle": "cycle", "dustbin": "dustbin", "bin": "dustbin", "thaila": "bags", "kachra": "bags"}
VEHICLES = ("truck", "auto", "car", "scooter", "bike", "cycle")
SPLIT = ("truck", "auto", "car")               # drawn in two parts so a driver can show through the windows


def resolve_kind(word):
    w = str(word).lower()
    w = ALIASES.get(w, w)
    return w if w in OBJECTS or w.endswith((".png", ".webp")) else None


_cache = {}


def sprite(kind, s, color=None, part="all"):
    """(RGBA image or None, (anchor x, anchor y), wheels [(x, y, r)] in image px) at render scale s.
    part = "all" | "back" | "front" (only the SPLIT vehicles have two parts; the others are all "back")."""
    key = (kind, round(s, 4), tuple(color) if color else None, part)
    if key in _cache:
        return _cache[key]
    if kind in OBJECTS:
        drawer, col, _ = OBJECTS[kind]
        split = kind in SPLIT
        if not split and part == "front":
            pen, wheels = drawer(s, tuple(color) if color else col)
            out = (None, (pen.ox * s, pen.oy * s), [])
        else:
            pen, wheels = drawer(s, tuple(color) if color else col, part) if split else drawer(s, tuple(color) if color else col)
            im = pen.image()
            out = (im, (pen.ox * s, pen.oy * s), [((x + pen.ox) * s, (y + pen.oy) * s, r * s) for x, y, r in wheels])
    else:                                                      # your own PNG: 320 logical px tall, feet at the bottom
        if part == "front":
            out = (None, (0.0, 0.0), [])
        else:
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

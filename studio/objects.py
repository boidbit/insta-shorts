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
# a thela is drawn at 250 units a metre and a person (~1.7 m) is ~800 units: 0.95 * 250 / (800 / 1.7) = 0.5
# (the carts and the shop counters are added below, where they are drawn)
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

    def text(self, cx, cy, txt, size, fill=(200, 30, 30)):
        from .text import font
        f = font(size * self.g.k, "main")
        self.g.d.text(((cx + self.ox) * self.g.k, (cy + self.oy) * self.g.k), txt, font=f, fill=fill, anchor="mm")

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


# ---------------------------------------------------------------- the thela: a street-food / fruit / sabzi cart
# Drawn at 250 units a metre: a 1.9 m cart, the platform at a grown-up's waist, the tarp above a person's head.
THELA = {   # variant: (sign, sign colour, sign text colour, tarp colour)
    "sabzi": ("TAZI SABZI", (60, 140, 70), (255, 255, 255), (50, 110, 190)),
    "fruits": ("FRESH FRUITS", (250, 210, 60), (180, 40, 40), (60, 150, 80)),
    "kulche": ("MATAR KULCHE", (250, 220, 70), (200, 30, 30), (210, 50, 50)),
    "chaat": ("CHAAT CORNER", (240, 120, 40), (255, 255, 255), (240, 150, 40)),
    "momos": ("STEAM MOMOS", (200, 30, 40), (255, 240, 200), (200, 40, 50)),
    "golgappe": ("GOLGAPPE", (250, 230, 120), (40, 90, 40), (240, 200, 40)),
    "chai": ("GARAM CHAI", (250, 210, 70), (150, 40, 30), (150, 90, 50)),
    "ganna": ("GANNE KA JUICE", (110, 180, 70), (255, 255, 255), (70, 150, 60)),
    "bhutta": ("BHUTTA", (250, 220, 90), (120, 70, 20), (60, 120, 70)),
    "gola": ("BARF KA GOLA", (90, 170, 230), (255, 255, 255), (230, 80, 140)),
    "pav_bhaji": ("PAV BHAJI", (240, 120, 40), (255, 255, 255), (220, 90, 40)),
    "chole_bhature": ("CHOLE BHATURE", (250, 230, 150), (170, 60, 20), (190, 60, 50)),
}
THELA_SPOT = {"sabzi": -40, "fruits": 0, "kulche": 80, "chaat": 90, "momos": 100, "golgappe": 20, "chai": 100,
              "ganna": 40, "bhutta": 100, "gola": 70, "pav_bhaji": 20, "chole_bhature": 170}
THELA_WORDS = {"sabzi": "sabzi", "sabji": "sabzi", "vegetables": "sabzi", "veg": "sabzi", "fruits": "fruits",
               "fruit": "fruits", "phal": "fruits", "kulche": "kulche", "kulcha": "kulche", "matar_kulche": "kulche",
               "chaat": "chaat", "tikki": "chaat", "momos": "momos", "momo": "momos", "golgappe": "golgappe",
               "golgappa": "golgappe", "panipuri": "golgappe", "pani_puri": "golgappe", "puchka": "golgappe",
               "chai": "chai", "chay": "chai", "tea": "chai", "ganna": "ganna", "ganne": "ganna", "juice": "ganna",
               "sugarcane": "ganna", "bhutta": "bhutta", "corn": "bhutta", "makka": "bhutta", "gola": "gola",
               "barf_gola": "gola", "ice_gola": "gola", "kulfi": "gola", "pav_bhaji": "pav_bhaji",
               "pavbhaji": "pav_bhaji", "chole_bhature": "chole_bhature", "chole": "chole_bhature",
               "bhature": "chole_bhature"}


def _pile(p, x0, x1, y, r, col, rows=2, dark=None):
    """A heap of round things (tomatoes, apples, puris...) on the platform at height y."""
    n = max(1, int((x1 - x0) / (2 * r)))
    for row in range(rows):
        k = n - row
        if k <= 0:
            break
        off = x0 + r + row * r + (x1 - x0 - 2 * r * n) / 2.0
        for i in range(k):
            p.circle(off + i * 2 * r, y - r - row * r * 1.6, r, col, INK, 3)
            if dark:
                p.circle(off + i * 2 * r - r * 0.3, y - r - row * r * 1.6 - r * 0.3, r * 0.25, dark, None)


def _thela(s, c, variant="sabzi"):
    sign, sign_c, txt_c, _tarp = THELA[variant]
    p = Pen(s, 560, 560)
    wood, wood_d, steel = (176, 124, 76), (130, 88, 52), (196, 198, 206)
    top = -232                                                                       # the platform's top
    p.line([(-214, top + 30), (-270, top - 6)], (90, 92, 100), 12)                   # the handle (pushed from here)
    p.line([(-270, top - 6), (-282, top - 6)], INK, 16)
    for x in (-196, 196):                                                            # tarp poles
        p.line([(x, top), (x, -506)], (120, 120, 126), 10)
    p.rect(-226, -150, 226, -128, (80, 82, 90))                                      # the frame and axle stays
    for x in (-150, 150):
        p.line([(x, -136), (x - 24, -70), (x + 24, -70), (x, -136)], (80, 82, 90), 8)
    p.rect(-220, top, 220, -150, wood)                                               # the wooden box
    for y in (top + 28, top + 56):
        p.line([(-216, y), (216, y)], wood_d, 4)
    p.rect(-232, top - 12, 232, top + 4, wood_d)                                     # the platform's rim
    p.poly([(-246, -506), (246, -506), (226, -548), (-226, -548)], c)               # the tarp
    for x in range(-200, 220, 80):
        p.line([(x, -548), (x - 6, -506)], shade(c, 0.8), 6)
    p.rect(-150, -500, 150, -444, sign_c, INK, 4)                                    # the board under the tarp
    p.text(0, -472, sign, 34 if len(sign) > 10 else 40, txt_c)
    y = top - 12
    if variant == "sabzi":
        _pile(p, -214, -70, y, 20, (220, 50, 40))                                    # tomatoes
        for i in range(7):                                                           # bhindi / mirchi
            x = -56 + i * 14
            p.line([(x, y - 4), (x + 10, y - 58)], (70, 150, 60), 9)
        p.circle(100, y - 40, 40, (248, 246, 230), INK, 4)                           # a cauliflower
        for a in (-50, 0, 50):
            p.poly([(100, y - 10), (100 + a, y - 48), (100 + a * 0.6, y - 4)], (90, 160, 80), INK, 3)
        _pile(p, 150, 226, y, 16, (190, 150, 90), rows=2)                            # potatoes
    elif variant == "fruits":
        for i in range(3):                                                           # bananas
            x = -200 + i * 40
            p.line([(x, y - 4), (x + 18, y - 60), (x + 40, y - 74)], (245, 210, 60), 16)
        _pile(p, -70, 70, y, 22, (210, 40, 50), dark=(150, 20, 30))                  # apples
        _pile(p, 80, 226, y, 22, (250, 150, 40))                                     # oranges
        p.line([(196, -440), (150, -400)], INK, 4)                                   # the weighing scale
        p.line([(110, -400), (190, -400)], INK, 6)
        for x in (110, 190):
            p.line([(x, -400), (x - 16, -360), (x + 16, -360), (x, -400)], INK, 3)
            p.ellipse(x - 22, -366, x + 22, -352, steel, INK, 3)
    elif variant == "kulche":
        p.ellipse(-190, y - 110, -20, y + 4, (214, 170, 70), INK, 5)                 # the brass pot of matar
        p.ellipse(-178, y - 120, -32, y - 92, (196, 178, 90), INK, 4)
        for (x, yy) in ((-150, -110), (-120, -102), (-90, -112), (-62, -104), (-104, -116)):
            p.circle(x, y + yy, 6, (120, 170, 70), None)
        p.line([(-60, y - 116), (-10, y - 170)], (150, 150, 156), 7)                 # the ladle
        for i in range(6):                                                           # a stack of kulche
            p.ellipse(10, y - 16 - i * 12, 140, y - i * 12, (236, 204, 140), INK, 3)
        p.ellipse(150, y - 34, 226, y, steel, INK, 3)                                # onion and chutney bowls
        p.ellipse(160, y - 40, 216, y - 24, (200, 110, 170), None)
    elif variant == "chaat":
        p.rect(-200, y - 50, -40, y, (60, 60, 66), INK, 4)                           # the stove
        p.ellipse(-214, y - 70, -26, y - 44, (40, 40, 44), INK, 4)                  # the big tawa
        for x in (-170, -120, -72):                                                  # aloo tikki
            p.ellipse(x - 20, y - 72, x + 20, y - 58, (200, 140, 60), INK, 3)
        for i, col in enumerate(((240, 240, 230), (130, 60, 40), (90, 170, 80), (230, 200, 90))):
            x = 0 + i * 56                                                           # bowls of curd, chutneys, sev
            p.ellipse(x - 26, y - 30, x + 26, y, steel, INK, 3)
            p.ellipse(x - 20, y - 34, x + 20, y - 22, col, None)
    elif variant == "momos":
        for i in range(3):                                                           # the steamer, three tiers
            p.rect(-180, y - 40 - i * 40, -40, y - i * 40, steel, INK, 4)
        p.ellipse(-190, y - 140, -30, y - 116, (220, 222, 230), INK, 4)
        for (x, yy) in ((-130, -170), (-90, -190), (-60, -160)):                     # steam
            p.circle(x, y + yy, 18, (255, 255, 255, 160), None)
        p.ellipse(10, y - 20, 190, y, (240, 240, 236), INK, 3)                        # a plate of momos
        for x in (40, 80, 120, 160):
            p.ellipse(x - 20, y - 46, x + 20, y - 12, (250, 246, 232), INK, 3)
        p.rect(200, y - 70, 222, y, (210, 40, 30), INK, 3)                           # red chutney bottle
    elif variant == "golgappe":
        p.rect(-206, y - 104, -10, y, (200, 230, 246, 150), INK, 4)                  # the glass box of puris
        for row in range(3):
            for i in range(6):
                p.circle(-182 + i * 32 + (row % 2) * 12, y - 18 - row * 28, 14, (226, 176, 90), INK, 2)
        p.line([(-180, y - 96), (-150, y - 20)], (255, 255, 255, 180), 4)
        p.ellipse(60, y - 96, 210, y + 4, steel, INK, 5)                             # the pot of pani
        p.ellipse(72, y - 104, 198, y - 78, (110, 170, 90), INK, 3)
        p.line([(160, y - 92), (214, y - 160)], (150, 150, 156), 7)                  # the ladle
    elif variant == "chai":
        p.rect(-200, y - 46, -60, y, (60, 60, 66), INK, 4)                           # the stove
        p.ellipse(-196, y - 150, -64, y - 40, (196, 198, 206), INK, 5)               # the big kettle
        p.line([(-64, y - 110), (-24, y - 132)], INK, 9)                             # its spout
        p.line([(-170, y - 150), (-150, y - 176), (-110, y - 176), (-90, y - 150)], INK, 6)
        for (x, yy) in ((-140, -190), (-110, -214)):                                  # steam
            p.circle(x, y + yy, 16, (255, 255, 255, 160), None)
        for i in range(6):                                                           # glasses of chai
            x = 0 + i * 36
            p.poly([(x, y - 46), (x + 26, y - 46), (x + 23, y), (x + 3, y)], (236, 240, 240), INK, 3)
            p.poly([(x + 3, y - 36), (x + 23, y - 36), (x + 21, y - 2), (x + 5, y - 2)], (178, 112, 62), None)
        p.rect(186, y - 40, 222, y, (240, 200, 120), INK, 3)                         # a tin of rusks
    elif variant == "ganna":                                                         # the sugarcane crusher
        p.rect(-200, y - 150, -40, y, (40, 120, 70), INK, 5)
        p.circle(-120, y - 136, 54, (60, 60, 66), INK, 6)                            # the big wheel
        for a in range(0, 360, 60):
            r = math.radians(a)
            p.line([(-120, y - 136), (-120 + 48 * math.cos(r), y - 136 + 48 * math.sin(r))], (120, 120, 126), 6)
        for i in range(3):                                                           # sugarcane sticks
            p.line([(150 + i * 22, y), (166 + i * 22, y - 170)], (150, 170, 80), 12)
            p.line([(154 + i * 22, y - 80), (170 + i * 22, y - 80)], (100, 120, 50), 4)
        for x in (10, 56):                                                           # glasses of juice
            p.poly([(x, y - 60), (x + 30, y - 60), (x + 26, y), (x + 4, y)], (180, 210, 110), INK, 3)
    elif variant == "bhutta":                                                        # corn roasting on coals
        p.rect(-210, y - 40, -20, y, (60, 60, 66), INK, 4)
        for x in range(-196, -30, 26):
            p.circle(x + 12, y - 44, 11, (240, 110, 40), None)
        for i in range(4):
            x = -190 + i * 44
            p.ellipse(x, y - 76, x + 36, y - 46, (240, 200, 70), INK, 3)
        for i in range(5):                                                           # a pile of corn
            x = 20 + i * 40
            p.ellipse(x, y - 34, x + 34, y, (230, 200, 80), INK, 3)
            p.poly([(x + 4, y - 4), (x + 17, y - 40), (x + 30, y - 4)], (110, 170, 80), None)
        p.circle(190, y - 60, 22, (240, 240, 236), INK, 3)                           # nimbu-masala bowl
        p.circle(190, y - 60, 10, (240, 220, 80), None)
    elif variant == "gola":                                                          # the ice block, coloured syrups
        p.rect(-200, y - 110, -60, y, (220, 240, 250), INK, 5)
        p.line([(-180, y - 90), (-90, y - 40)], (255, 255, 255), 6)
        for i, col in enumerate(((230, 40, 60), (250, 140, 40), (60, 170, 80), (80, 120, 220), (230, 200, 40))):
            x = -20 + i * 40                                                         # syrup bottles
            p.rect(x, y - 66, x + 28, y, col + (220,), INK, 3)
            p.rect(x + 8, y - 80, x + 20, y - 66, (240, 240, 240), INK, 2)
        for i, col in enumerate(((230, 40, 60), (80, 120, 220))):                     # two golas on sticks
            x = 186 + i * 30
            p.line([(x, y), (x, y - 50)], (150, 110, 70), 5)
            p.ellipse(x - 16, y - 92, x + 16, y - 46, col, INK, 3)
    elif variant == "pav_bhaji":
        p.ellipse(-214, y - 40, 40, y - 4, (40, 40, 44), INK, 5)                      # the huge flat tawa
        p.ellipse(-180, y - 40, -10, y - 16, (210, 90, 50), None)                    # the bhaji
        p.circle(-150, y - 36, 10, (250, 240, 200), None)                             # a lump of butter
        for i in range(4):                                                           # pav
            x = 70 + i * 38
            p.ellipse(x, y - 40, x + 36, y - 6, (230, 170, 90), INK, 3)
        p.ellipse(70, y - 64, 220, y - 40, steel, INK, 3)                             # onions and lemon
        p.ellipse(90, y - 66, 200, y - 52, (200, 110, 170), None)
    elif variant == "chole_bhature":
        p.ellipse(-206, y - 110, -40, y + 4, (60, 60, 66), INK, 5)                   # the kadhai
        p.ellipse(-196, y - 116, -50, y - 88, (230, 170, 70), INK, 3)                # a bhatura puffing up in it
        p.ellipse(10, y - 70, 150, y + 2, (176, 120, 70), INK, 4)                    # the pot of chole
        p.ellipse(18, y - 78, 142, y - 54, (170, 110, 60), INK, 3)
        for (x, yy) in ((40, -70), (80, -76), (110, -68)):
            p.circle(x, y + yy, 6, (120, 70, 40), None)
        for i in range(3):                                                           # a stack of bhature
            p.ellipse(160, y - 22 - i * 10, 226, y - i * 10, (240, 200, 120), INK, 3)
    return p, [(-150, -64, 64), (150, -64, 64)]


# ---------------------------------------------------------------- a shop counter (a person stands behind it)
# 250 units a metre: 1.7 m long, a metre high, a glass case on top; `OBJ: counter mithai center`
SHOP = {    # variant: (front text, front colour, text colour)
    "general": ("GENERAL STORE", (176, 124, 78), (255, 240, 200)),
    "mithai": ("MITHAI", (230, 120, 40), (255, 255, 255)),
    "mobile": ("MOBILE", (40, 90, 170), (255, 255, 255)),
    "medical": ("MEDICAL", (40, 140, 90), (255, 255, 255)),
    "bakery": ("BAKERY", (200, 120, 160), (255, 255, 255)),
    "kapde": ("KAPDE", (150, 60, 120), (255, 240, 200)),
}
SHOP_WORDS = {"general": "general", "kirana": "general", "dukaan": "general", "dukan": "general", "shop": "general",
              "mithai": "mithai", "sweets": "mithai", "halwai": "mithai", "mobile": "mobile", "phone": "mobile",
              "medical": "medical", "dawai": "medical", "chemist": "medical", "bakery": "bakery", "cake": "bakery",
              "kapde": "kapde", "kapda": "kapde", "clothes": "kapde"}


def _counter(s, c, variant="general"):
    text, front, txt_c = SHOP[variant]
    front = c if c else front
    p = Pen(s, 440, 330)
    top = -226                                                                       # 0.9 m: a person shows above it
    p.rect(-212, top + 20, 212, 0, front)                                            # the front
    p.rect(-200, top + 40, 200, top + 96, shade(front, 1.18), INK, 3)                # the name strip
    p.text(0, top + 68, text, 30 if len(text) > 8 else 38, txt_c)
    for x in (-150, -50, 50, 150):                                                   # panels below
        p.rect(x - 44, top + 114, x + 44, -20, shade(front, 0.9), INK, 3)
    p.rect(-220, top, 220, top + 22, (110, 80, 50))                                  # the counter top
    p.rect(-210, top - 64, 210, top, (200, 230, 246, 140), INK, 4)                   # the glass case
    y = top - 4
    if variant == "mithai":
        for row in range(2):
            for i in range(7):
                x = -186 + i * 56
                col = ((250, 210, 80), (240, 150, 60), (250, 250, 240), (200, 120, 70))[(i + row) % 4]
                p.circle(x + 16, y - 14 - row * 28, 12, col, INK, 2)
    elif variant == "mobile":
        for i in range(6):
            x = -186 + i * 64
            p.rrect(x, y - 52, x + 30, y - 4, 6, (40, 44, 52), INK, 3)
            p.rect(x + 4, y - 46, x + 26, y - 12, ((120, 190, 235), (240, 140, 160), (150, 220, 160))[i % 3], None)
    elif variant == "medical":
        for i in range(8):
            x = -190 + i * 48
            p.rect(x, y - 44, x + 34, y - 4, ((250, 250, 250), (240, 220, 120), (200, 230, 250))[i % 3], INK, 2)
            p.rect(x + 6, y - 34, x + 28, y - 26, ((220, 60, 60), (60, 140, 220), (60, 160, 90))[i % 3], None)
    elif variant == "bakery":
        p.ellipse(-190, y - 46, -70, y - 4, (250, 240, 230), INK, 3)                 # a cake
        p.ellipse(-180, y - 52, -80, y - 34, (240, 150, 180), INK, 3)
        p.circle(-130, y - 56, 7, (220, 40, 60), None)
        for i in range(5):                                                           # buns and rusks
            x = -40 + i * 46
            p.ellipse(x, y - 34, x + 40, y - 4, (220, 160, 80), INK, 3)
    elif variant == "kapde":
        for i in range(5):                                                           # folded clothes
            x = -190 + i * 78
            for j in range(3):
                col = ((200, 60, 80), (60, 120, 200), (240, 200, 60), (90, 160, 90), (150, 90, 180))[(i + j) % 5]
                p.rect(x, y - 18 - j * 18, x + 66, y - 2 - j * 18, col, INK, 2)
    else:                                                                            # jars, packets, a scale
        for i in range(4):
            x = -190 + i * 70
            p.rrect(x, y - 54, x + 50, y - 4, 10, (236, 236, 230), INK, 3)
            p.circle(x + 25, y - 28, 13, ((250, 200, 60), (230, 120, 80), (140, 90, 60), (250, 250, 250))[i], None)
        p.line([(110, y - 60), (190, y - 60)], INK, 5)
        p.ellipse(100, y - 30, 140, y - 18, (196, 198, 206), INK, 3)
        p.ellipse(160, y - 30, 200, y - 18, (196, 198, 206), INK, 3)
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
for _v, (_sign, _sc, _tc, _tarp) in THELA.items():       # thela (sabzi), thela_kulche, thela_fruits...
    OBJECTS["thela" if _v == "sabzi" else "thela_" + _v] = (
        (lambda v: (lambda s, c: _thela(s, c, v)))(_v), _tarp, 1.0)
THELAS = tuple(k for k in OBJECTS if k.startswith("thela"))
for _v in SHOP:                                           # counter (general), counter_mithai, counter_mobile...
    OBJECTS["counter" if _v == "general" else "counter_" + _v] = ((lambda v: (lambda s, c: _counter(s, c, v)))(_v),
                                                                  None, 1.0)
SHOP_COUNTERS = tuple(k for k in OBJECTS if k.startswith("counter"))
# a thela and a counter are drawn at 250 units a metre and a person (~1.7 m) is ~800 units: 0.95 * 250 / 470 = 0.5
for _k in THELAS + SHOP_COUNTERS:
    PERSON_R[_k], SPRITE_LEN[_k] = 0.5, 560 if _k in THELAS else 440
ENTER_DUR = {k: 2.6 for k in THELAS}                      # a pushed cart rolls in slowly
COUNTERS = THELAS + SHOP_COUNTERS + ("table",)            # things a person can stand behind
ALIASES = {"garbage_truck": "truck", "kachra_gaadi": "truck", "gaadi": "truck", "rickshaw": "auto", "gai": "cow",
           "motorcycle": "bike", "bullet": "bike", "bicycle": "cycle", "dustbin": "dustbin", "bin": "dustbin", "thaila": "bags", "kachra": "bags",
           "rehri": "thela", "rehdi": "thela", "redi": "thela", "cart": "thela", "thelaa": "thela",
           "kulche_thela": "thela_kulche", "fruit_thela": "thela_fruits", "chaat_thela": "thela_chaat",
           "momos_thela": "thela_momos", "golgappe_thela": "thela_golgappe", "sabzi_thela": "thela",
           "chai_thela": "thela_chai", "juice_thela": "thela_ganna", "dukaan": "counter", "dukan": "counter",
           "shop_counter": "counter"}


def thela_kind(variant):
    """`kulche` -> "thela_kulche" (None if the word is not a cart)."""
    v = THELA_WORDS.get(str(variant).lower())
    return None if v is None else ("thela" if v == "sabzi" else "thela_" + v)


def counter_kind(variant):
    """`mithai` -> "counter_mithai" (None if the word is not a shop)."""
    v = SHOP_WORDS.get(str(variant).lower())
    return None if v is None else ("counter" if v == "general" else "counter_" + v)
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

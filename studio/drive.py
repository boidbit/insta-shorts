"""Driving shots: a car or an auto on the move, seen from different places (POV), like a film cuts a car scene.

    car / auto          inside, from the side (the vehicle engine: studio.vehicles)
    car_front / ..      from in front, through the windshield: the driver at the wheel, the passenger beside him,
                        the dashboard, the bonnet; the view going past in the side and back windows
    car_side / ..       from outside, beside the road: the whole car driving, wheels spinning, the people in its
                        windows, the place going past behind it
    car_pov / ..        the driver's eyes: the road rushing towards us, the dashboard, the hands on the wheel (the
                        auto's handle bar), the passenger at the side
    mirror (a shot)     the rear-view mirror: the speaker's face in it, close

Script: inside a `SCENE: car` / `SCENE: auto`, `CUT front`, `CUT side`, `CUT pov`, `CUT mirror`, `CUT inside`; with no
CUT the studio cuts between them by itself (side to open, then front / inside, the punch line in the mirror).
The people in front of the camera are the cast in order: the first one drives."""
import math
import random

from PIL import ImageDraw

from .backgrounds import G, INK
from .util import LH, LW

POV = {"car_front": ("car", "front"), "car_side": ("car", "side"), "car_pov": ("car", "pov"),
       "car_mirror": ("car", "mirror"), "auto_front": ("auto", "front"), "auto_side": ("auto", "side"),
       "auto_pov": ("auto", "pov"), "auto_mirror": ("auto", "mirror")}
POV_WORDS = {"front": "front", "saamne": "front", "samne": "front", "windshield": "front",
             "side": "side", "bahar": "side", "outside": "side",
             "pov": "pov", "driver": "pov", "nazar": "pov",
             "mirror": "mirror", "sheesha": "mirror", "shisha": "mirror",
             "inside": "inside", "andar": "inside"}
# the window band (the part of the view that shows) of each shot, as studio.vehicles.BANDS
BANDS = {"car_front": (520, 800), "car_side": (700, 1240), "auto_front": (560, 1060), "auto_side": (640, 1240),
         "car_mirror": (520, 800), "auto_mirror": (560, 1060)}
# where the people stand in each shot: x of the driver, then the others (None: not in the shot), their feet (ys) and
# their size against the driver (ks: a back seat is further from the camera); the shot's own size, facing / view
PLACES = {"car_front": dict(xs=(300, 780, 480, 620), ys=(1700, 1700, 1590, 1590), ks=(1, 1, 0.8, 0.8), scale=1.32,
                            facing="front"),
          "car_side": dict(xs=(770, 330, 190), scale=0.9, facing="right", view="side"),
          "car_pov": dict(xs=(None, 930), scale=1.3, facing="left"),
          "auto_front": dict(xs=(540, 250, 830), ys=(1640, 1500, 1500), ks=(1, 0.86, 0.86), scale=1.25,
                             facing="front"),
          "auto_side": dict(xs=(800, 430, 290), scale=0.85, facing="right", view="side"),
          "auto_pov": dict(xs=(None,), scale=1.2, facing="front"),
          "car_mirror": dict(xs=(540,), scale=1.6, y=2120, facing="front", only_speaker=True),
          "auto_mirror": dict(xs=(540,), scale=1.6, y=2120, facing="front", only_speaker=True)}
CAR_COL = (196, 46, 50)
AUTO_GREEN, AUTO_YELLOW = (40, 130, 70), (244, 200, 40)
GLASS = (0, 0, 0, 0)


def _g(s):
    return G(s, color=(0, 0, 0, 0), mode="RGBA")


def _shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c[:3])


# ------------------------------------------------------------------ car, from in front
def car_front_inside(s):
    g = _g(s)
    A = 255
    g.rect(0, 0, LW, 520, (214, 208, 196, A))                                  # roof lining
    g.circle(540, 150, 26, (250, 246, 220, A), INK + (A,), 4)                 # the cabin light
    g.rect(0, 800, LW, LH, (62, 64, 72, A))                                     # the back seat
    for x in range(60, LW, 160):
        g.line([(x, 820), (x, 1500)], (54, 56, 64, A), 3)
    g.rrect(220, 500, 860, 820, 40, (36, 36, 40, A), INK + (A,), 5)            # the back window (the view in it)
    g.rrect(244, 524, 836, 796, 30, GLASS)
    g.rect(200, 800, 880, 840, (48, 48, 54, A), INK + (A,), 4)                 # parcel shelf
    for x in (300, 780):                                                       # the front seats behind the people
        g.rrect(x - 175, 880, x + 175, 1560, 50, (70, 70, 80, A), INK + (A,), 5)
        g.rrect(x - 85, 700, x + 85, 850, 34, (78, 78, 88, A), INK + (A,), 4)
        g.rect(x - 30, 850, x - 18, 890, (150, 150, 156, A))
        g.rect(x + 18, 850, x + 30, 890, (150, 150, 156, A))
    return g.done()


def car_front_front(s):
    g = _g(s)
    A = 255
    body, dark = CAR_COL, _shade(CAR_COL, 0.72)
    g.poly([(0, 0), (LW, 0), (LW, 330), (0, 330)], body + (A,), INK + (A,), 6)     # the roof's front edge
    g.rect(0, 300, LW, 340, dark + (A,))
    g.poly([(0, 330), (130, 330), (40, 1290), (0, 1290)], body + (A,), INK + (A,), 6)   # the pillars
    g.poly([(LW, 330), (LW - 130, 330), (LW - 40, 1290), (LW, 1290)], body + (A,), INK + (A,), 6)
    for (x0, x1) in ((150, 330), (620, 760)):                                  # the glass: a soft reflection
        g.poly([(x0, 1270), (x0 + 220, 360), (x1 + 220, 360), (x1, 1270)], (255, 255, 255, 26))
    g.rect(0, 1160, LW, 1300, (40, 40, 46, A), INK + (A,), 5)                 # the dashboard (behind the glass)
    for x in (430, 650):
        g.rrect(x - 40, 1180, x + 40, 1220, 10, (24, 24, 28, A), INK + (A,), 3)
    g.rect(840, 1110, 880, 1160, (240, 200, 60, A), INK + (A,), 3)            # a little dashboard dog
    g.circle(860, 1096, 24, (240, 200, 60, A), INK + (A,), 3)
    cx, cy = 300, 1140                                                          # the steering wheel (from in front)
    g.ellipse(cx - 150, cy - 120, cx + 150, cy + 120, None, (30, 30, 34, A), 26)
    g.circle(cx, cy, 40, (40, 40, 46, A), INK + (A,), 4)
    for (dx, dy) in ((-150, 0), (150, 0), (0, 120)):
        g.line([(cx, cy), (cx + dx * 0.9, cy + dy * 0.9)], (30, 30, 34, A), 16)
    for (a, b) in (((160, 1295), (520, 1240)), ((600, 1295), (960, 1240))):   # wipers
        g.line([a, b], (20, 20, 24, A), 9)
    g.poly([(0, 1290), (LW, 1290), (LW, LH), (0, LH)], body + (A,), INK + (A,), 6)   # the bonnet
    g.poly([(40, 1300), (LW - 40, 1300), (LW - 120, 1600), (120, 1600)], _shade(body, 1.12) + (A,))
    g.line([(540, 1300), (540, 1600)], dark + (A,), 6)
    g.rect(0, 1600, LW, 1660, dark + (A,), INK + (A,), 5)
    for x in (150, 930):                                                       # headlights and the grille
        g.ellipse(x - 120, 1680, x + 120, 1800, (250, 248, 220, A), INK + (A,), 6)
    g.rrect(330, 1690, 750, 1800, 30, (40, 40, 46, A), INK + (A,), 5)
    for x in range(360, 740, 40):
        g.line([(x, 1700), (x, 1790)], (90, 90, 96, A), 4)
    g.circle(540, 1640, 34, (220, 220, 226, A), INK + (A,), 4)                 # the badge
    g.rect(0, 1840, LW, LH, (30, 30, 34, A))                                    # the bumper
    return g.done()


# ------------------------------------------------------------------ car, from the side (outside)
def car_side_inside(s):
    """Behind the people, inside the car: the far windows (the view shows) and the seat backs."""
    g = _g(s)
    A = 255
    for x in (650, 250):                                                       # seat backs (they face right)
        g.rrect(x - 40, 880, x + 30, 1200, 20, (60, 60, 68, A), INK + (A,), 4)
        g.rrect(x - 30, 820, x + 25, 900, 16, (66, 66, 74, A), INK + (A,), 3)
    return g.done()


def _wheel(g, x, y, r, A=255):
    """A wheel from the side, spinning (blurred rims)."""
    g.circle(x, y, r, (26, 26, 30, A), INK + (A,), 6)
    g.circle(x, y, r * 0.6, (150, 150, 158, A), INK + (A,), 4)
    for k in (0.45, 0.3, 0.15):
        g.circle(x, y, r * k, None, (120, 120, 128, A), 5)
    g.circle(x, y, r * 0.1, (60, 60, 66, A))


def car_side_front(s):
    """The car's body (in front of the people), driving to the right, close: its nose and its boot run out of the
    frame (a real car is long), the windows cut out, the doors down to the road; wheels blurred spinning."""
    g = _g(s)
    A = 255
    body, dark = CAR_COL, _shade(CAR_COL, 0.7)
    g.ellipse(-140, 1760, 1220, 1830, (0, 0, 0, 80))                            # its shadow on the road
    g.poly([(-120, 1140), (-40, 1110), (110, 850), (870, 850), (1090, 1140), (1220, 1170), (1220, 1660),
            (-120, 1660)], body + (A,), INK + (A,), 7)
    g.poly([(150, 1150), (200, 900), (505, 900), (505, 1150)], GLASS)           # back window
    g.poly([(550, 1150), (550, 900), (850, 900), (1030, 1150)], GLASS)          # front window
    g.poly([(170, 1150), (220, 990), (250, 990), (200, 1150)], (255, 255, 255, 50))
    g.poly([(600, 1150), (640, 960), (670, 960), (630, 1150)], (255, 255, 255, 50))
    g.rect(505, 880, 550, 1160, dark + (A,), INK + (A,), 4)                     # the pillar
    g.line([(-120, 1160), (1220, 1170)], INK + (A,), 5)                         # the waist line
    g.poly([(-120, 1250), (1220, 1260), (1220, 1280), (-120, 1270)], _shade(body, 1.18) + (A,))   # its shine
    g.line([(550, 1160), (550, 1590)], dark + (A,), 4)                          # door lines + handles
    g.line([(130, 1160), (120, 1590)], dark + (A,), 4)
    for x in (420, 830):
        g.rrect(x, 1210, x + 80, 1234, 8, (220, 220, 226, A), INK + (A,), 3)
    g.poly([(1000, 1080), (1070, 1060), (1080, 1110), (1010, 1120)], dark + (A,), INK + (A,), 3)   # side mirror
    g.rect(-120, 1590, 1220, 1665, (40, 40, 46, A))                             # the sill
    g.rect(-120, 1660, 1220, 1730, (22, 22, 26, A))                             # under it, in its shadow
    for x in (60, 1040):                                                       # wheel wells and wheels
        g.ellipse(x - 190, 1450, x + 190, 1830, (24, 24, 28, A))
        _wheel(g, x, 1660, 150)
    return g.done()


# ------------------------------------------------------------------ auto, from in front and from the side
def auto_front_inside(s):
    """Behind the people: the back of the auto's cabin (the bench, the little back window); its open sides show
    the street (the view)."""
    g = _g(s)
    A = 255
    g.rect(0, 0, LW, 560, (30, 30, 32, A))                                      # the canopy from inside
    for y in range(60, 540, 90):
        g.line([(0, y), (LW, y)], (52, 52, 56, A), 3)
    g.rect(150, 560, LW - 150, 1420, (36, 36, 38, A))                            # the back of the cabin
    g.rrect(400, 620, 680, 790, 30, GLASS)                                       # the little back window
    g.rect(170, 1040, LW - 170, 1420, (140, 90, 50, A), INK + (A,), 5)          # the passengers' bench back
    for x in range(230, LW - 170, 120):
        g.line([(x, 1050), (x, 1410)], (120, 76, 42, A), 3)
    return g.done()


def auto_front_front(s):
    """In front of the people: the canopy's edge and poles, the little windshield, the handle bar, the auto's green
    nose with its one headlight, its body round the passengers, the road under it."""
    g = _g(s)
    A = 255
    g.rect(0, 1560, LW, LH, (96, 98, 104, A))                                    # the road under it
    g.ellipse(60, 1760, 1020, 1860, (0, 0, 0, 80))
    g.rect(0, 0, LW, 230, (24, 24, 26, A))                                      # the canopy's front edge
    g.rect(0, 200, LW, 240, AUTO_YELLOW + (A,), INK + (A,), 4)
    for x in (80, LW - 130):                                                   # its poles
        g.rect(x, 240, x + 50, 1300, (24, 24, 26, A))
    for x in (150, 930):                                                       # the back wheels at the sides
        g.rrect(x - 60, 1560, x + 60, 1800, 24, (26, 26, 30, A), INK + (A,), 5)
    g.poly([(70, 1060), (LW - 70, 1060), (LW - 50, 1640), (50, 1640)], AUTO_GREEN + (A,), INK + (A,), 6)  # its body
    g.rect(70, 1060, LW - 70, 1110, AUTO_YELLOW + (A,), INK + (A,), 4)
    g.rrect(330, 440, 750, 900, 34, None, (200, 202, 208, A), 14)               # the little windshield
    g.poly([(370, 880), (520, 470), (570, 470), (420, 880)], (255, 255, 255, 34))
    g.line([(380, 890), (600, 850)], (20, 20, 24, A), 8)                        # wiper
    g.line([(300, 990), (780, 990)], (40, 40, 44, A), 16)                       # the handle bar
    for x in (300, 780):
        g.rrect(x - 46, 975, x + 46, 1005, 12, (20, 20, 22, A), INK + (A,), 3)
    g.poly([(250, 950), (830, 950), (720, 1700), (360, 1700)], AUTO_GREEN + (A,), INK + (A,), 6)   # the nose
    g.poly([(270, 950), (810, 950), (790, 1050), (290, 1050)], AUTO_YELLOW + (A,), INK + (A,), 5)
    g.circle(540, 1240, 78, (250, 248, 220, A), INK + (A,), 6)                  # the headlight
    g.circle(540, 1240, 50, (255, 255, 236, A))
    g.rrect(430, 1440, 650, 1510, 12, (250, 250, 246, A), INK + (A,), 4)        # number plate (no number)
    g.rrect(480, 1700, 600, 1880, 26, (26, 26, 30, A), INK + (A,), 5)           # the front wheel
    return g.done()


def auto_side_inside(s):
    g = _g(s)
    A = 255
    g.rect(220, 990, 600, 1300, (140, 90, 50, A), INK + (A,), 4)               # the back bench's back
    return g.done()


def auto_side_front(s):
    """The auto from the side, driving to the right: the black canopy, the open side (the people show), the green
    body up to the waist and down to the road, the driver's little windshield, wheels spinning."""
    g = _g(s)
    A = 255
    g.ellipse(60, 1760, 1120, 1830, (0, 0, 0, 80))
    g.poly([(110, 1040), (150, 830), (300, 760), (900, 760), (970, 820), (1000, 900), (190, 900)],
           (24, 24, 26, A), INK + (A,), 6)                                     # the black canopy
    g.rect(150, 880, 990, 912, AUTO_YELLOW + (A,), INK + (A,), 4)
    g.rect(110, 900, 160, 1280, (24, 24, 26, A))                                # its back post
    g.poly([(880, 900), (990, 900), (1080, 1150), (1080, 1680), (880, 1680)], AUTO_GREEN + (A,), INK + (A,), 6)
    g.poly([(900, 914), (980, 914), (1040, 1100), (900, 1100)], GLASS)          # the windshield (side)
    g.poly([(90, 1260), (1080, 1260), (1080, 1680), (110, 1680)], AUTO_GREEN + (A,), INK + (A,), 6)
    g.rect(90, 1260, 1080, 1300, AUTO_YELLOW + (A,), INK + (A,), 4)
    g.rect(130, 1650, 1060, 1715, (30, 30, 34, A))                              # under it
    g.line([(880, 1020), (770, 1060)], (40, 40, 44, A), 12)                    # the handle bar
    for x, r in ((300, 110), (980, 104)):
        g.ellipse(x - r - 30, 1560, x + r + 30, 1840, (24, 24, 28, A))
        _wheel(g, x, 1700, r)
    return g.done()


# ------------------------------------------------------------------ the driver's eyes
def pov_inside(kind, s):
    """Around the windshield (behind the passenger): the roof, the pillars, the rear-view mirror."""
    g = _g(s)
    A = 255
    if kind == "car_pov":
        g.rect(0, 0, LW, 230, (214, 208, 196, A))
        g.poly([(0, 230), (170, 230), (60, 1400), (0, 1400)], (180, 174, 162, A), INK + (A,), 5)
        g.poly([(LW, 230), (LW - 170, 230), (LW - 60, 1400), (LW, 1400)], (180, 174, 162, A), INK + (A,), 5)
        g.line([(540, 230), (540, 300)], (40, 40, 44, A), 10)
        g.rrect(400, 290, 680, 380, 26, (30, 30, 34, A), INK + (A,), 5)          # the rear-view mirror
        g.rrect(414, 302, 666, 368, 20, (110, 130, 150, A))
    else:
        g.rect(0, 0, LW, 230, (24, 24, 26, A))                                  # the canopy
        for y in range(40, 220, 60):
            g.line([(0, y), (LW, y)], (46, 46, 50, A), 3)
        g.rect(0, 200, LW, 240, AUTO_YELLOW + (A,), INK + (A,), 4)
        for x in (30, LW - 80):                                                # its poles (the sides are open)
            g.rect(x, 240, x + 50, 1500, (24, 24, 26, A))
    return g.done()


def _dial(g, cx, cy, r, A=255):
    """A gauge: a dark face, a ring of ticks, an orange needle."""
    g.circle(cx, cy, r, (16, 16, 20, A), (200, 200, 206, A), 3)
    for i in range(9):
        a = math.radians(150 + i * 30)
        g.line([(cx + math.cos(a) * r * 0.72, cy + math.sin(a) * r * 0.72),
                (cx + math.cos(a) * r * 0.9, cy + math.sin(a) * r * 0.9)], (220, 220, 226, A), 3)
    g.line([(cx, cy), (cx + r * 0.6, cy - r * 0.45)], (255, 130, 40, A), 4)
    g.circle(cx, cy, 5, (200, 200, 206, A))


def pov_front(kind, s):
    """In front of everybody: the dashboard (the auto's front), the wheel / the handle bar and the driver's hands."""
    g = _g(s)
    A = 255
    skin, sleeve = (214, 160, 120), (70, 110, 180)
    if kind == "car_pov":
        g.rect(0, 1380, LW, LH, (40, 40, 46, A), INK + (A,), 6)
        g.poly([(0, 1380), (LW, 1380), (LW, 1440), (0, 1440)], (52, 52, 58, A))
        g.rrect(290, 1430, 610, 1570, 30, (24, 24, 28, A), INK + (A,), 4)        # the cluster behind the wheel
        _dial(g, 375, 1500, 50)
        _dial(g, 525, 1500, 50)
        g.rrect(760, 1300, 900, 1440, 14, (20, 20, 24, A), INK + (A,), 4)        # a phone with the map
        g.rect(772, 1312, 888, 1428, (120, 200, 140, A))
        g.line([(790, 1420), (830, 1360), (870, 1330)], (60, 120, 220, A), 6)
        cx, cy = 450, 1720                                                      # the wheel
        g.ellipse(cx - 380, cy - 260, cx + 380, cy + 260, None, (24, 24, 28, A), 40)
        g.line([(cx - 360, cy), (cx + 360, cy)], (30, 30, 34, A), 30)
        g.circle(cx, cy, 70, (40, 40, 46, A), INK + (A,), 5)
        hands = ((cx - 330, cy - 120), (cx + 330, cy - 120))
    else:
        g.rrect(90, 300, 990, 1330, 40, None, (190, 192, 198, A), 18)          # the windshield's frame
        g.poly([(160, 1280), (420, 360), (480, 360), (220, 1280)], (255, 255, 255, 30))
        g.line([(200, 1310), (560, 1240)], (20, 20, 24, A), 9)                  # wiper
        g.rect(80, 1330, 1000, LH, (30, 34, 32, A), INK + (A,), 6)              # the dashboard, the auto's front
        g.rect(80, 1330, 1000, 1380, AUTO_YELLOW + (A,), INK + (A,), 4)
        g.rrect(130, 1190, 330, 1320, 12, (20, 20, 22, A), INK + (A,), 4)       # the fare meter
        g.rect(152, 1215, 308, 1262, (230, 60, 40, A))
        g.rrect(470, 1440, 610, 1520, 14, (60, 64, 60, A), INK + (A,), 3)       # the key, a sticker
        g.circle(780, 1470, 40, (240, 200, 40, A), INK + (A,), 3)
        g.line([(100, 1640), (980, 1640)], (40, 40, 44, A), 26)                 # the handle bar
        for x in (150, 930):
            g.rrect(x - 70, 1620, x + 70, 1660, 16, (20, 20, 22, A), INK + (A,), 3)
        hands = ((170, 1625), (910, 1625))
    for (hx, hy), side in zip(hands, (-1, 1)):                                  # the driver's arms and hands
        g.poly([(hx + side * 40, hy + 40), (hx + side * 260, LH + 40), (hx + side * 120, LH + 40),
                (hx - side * 30, hy + 60)], sleeve + (A,), INK + (A,), 5)
        g.ellipse(hx - 60, hy - 40, hx + 60, hy + 50, skin + (A,), INK + (A,), 5)
    return g.done()


def road_ahead(img, t, s, kind, view="city", time=None):
    """The road rushing towards the driver: sky, the far side, the road to the vanishing point, its middle line and
    the poles / trees at the side coming closer (drawn every frame onto img)."""
    d = ImageDraw.Draw(img, "RGBA")
    W, H = img.size
    k = s
    night = time == "night"
    hz = 760
    sky0, sky1 = ((14, 18, 50), (54, 50, 96)) if night else ((96, 160, 228), (210, 230, 246))
    for i in range(0, int(hz * k) + 1, 4):
        u = i / (hz * k)
        d.rectangle([0, i, W, i + 4], fill=tuple(int(a + (b - a) * u) for a, b in zip(sky0, sky1)))
    far = (40, 46, 70) if night else {"gaon": (120, 160, 110), "pahad": (130, 140, 176)}.get(view, (170, 180, 196))
    rnd = random.Random(7)
    x = 0
    while x < LW:                                                               # the far side of the land
        w = rnd.uniform(60, 140)
        h = rnd.uniform(40, 140) if view in ("city", "highway") else rnd.uniform(30, 90)
        d.rectangle([x * k, (hz - h) * k, (x + w) * k, hz * k + 2], fill=far)
        x += w
    ground = (40, 44, 40) if night else ((150, 176, 110) if view in ("gaon", "pahad", "highway") else (196, 190, 180))
    d.rectangle([0, hz * k, W, H], fill=ground)
    vx = 540

    def gx(x_bottom, y):
        return vx + (x_bottom - vx) * (y - hz) / (LH - hz)
    road = (60, 60, 66) if night else (96, 98, 104)
    d.polygon([(gx(-900, hz) * k, hz * k), (gx(1980, hz) * k, hz * k), (1980 * k, H), (-900 * k, H)], fill=road)
    speed = 1.6
    for i in range(10):                                                         # the middle line coming at us
        u = ((i / 10.0) + t * speed / 4.0) % 1.0
        ya, yb = hz + (LH - hz) * u ** 2.2, hz + (LH - hz) * min(1.0, (u + 0.045)) ** 2.2
        w0, w1 = 6 * (ya - hz) / (LH - hz) + 1, 6 * (yb - hz) / (LH - hz) + 1
        d.polygon([(gx(540 - w0 * 6, ya) * k, ya * k), (gx(540 + w0 * 6, ya) * k, ya * k),
                   (gx(540 + w1 * 6, yb) * k, yb * k), (gx(540 - w1 * 6, yb) * k, yb * k)],
                  fill=(240, 220, 120) if not night else (220, 200, 120))
    for side in (-1, 1):                                                        # the edges of the road
        d.line([(gx(540 + side * 1400, hz) * k, hz * k), ((540 + side * 1400) * k, H)], fill=(236, 236, 230), width=max(
            1, int(6 * k)))
    for i in range(6):                                                          # poles / trees at the side
        u = ((i / 6.0) + t * speed / 6.0) % 1.0
        y = hz + (LH - hz) * u ** 2.6
        sc = (y - hz) / (LH - hz)
        for side in (-1, 1):
            xb = gx(540 + side * 1900, y)
            if view in ("gaon", "pahad", "highway"):
                r = 260 * sc + 4
                d.rectangle([(xb - 14 * sc) * k, (y - 600 * sc) * k, (xb + 14 * sc) * k, y * k], fill=(110, 80, 56))
                d.ellipse([(xb - r) * k, (y - 600 * sc - r) * k, (xb + r) * k, (y - 600 * sc + r * 0.6) * k],
                          fill=(60, 130, 70) if not night else (24, 50, 34))
            else:
                d.rectangle([(xb - 10 * sc) * k, (y - 900 * sc) * k, (xb + 10 * sc) * k, y * k], fill=(80, 80, 86))
                d.rectangle([(xb - 60 * sc - side * 60 * sc) * k, (y - 900 * sc) * k, (xb + 6 * sc) * k,
                             (y - 880 * sc) * k], fill=(80, 80, 86))
                if night:
                    d.ellipse([(xb - 50 * sc) * k, (y - 910 * sc) * k, (xb + 10 * sc) * k, (y - 860 * sc) * k],
                              fill=(255, 220, 140))
    ahead = 0.5 + 0.5 * math.sin(t * 0.4)                                       # a truck ahead, far down the road
    y = hz + 90 + 20 * ahead
    sc = (y - hz) / (LH - hz)
    tx = gx(560, y)
    d.rectangle([(tx - 520 * sc) * k, (y - 900 * sc) * k, (tx + 520 * sc) * k, y * k], fill=(200, 110, 40))
    d.rectangle([(tx - 520 * sc) * k, (y - 900 * sc) * k, (tx + 520 * sc) * k, (y - 760 * sc) * k], fill=(40, 120, 200))
    for side in (-1, 1):
        d.rectangle([(tx + side * 420 * sc - 40 * sc) * k, (y - 200 * sc) * k, (tx + side * 420 * sc + 40 * sc) * k,
                     (y - 120 * sc) * k], fill=(240, 40, 40))


def _mirror_front(kind, s):
    """The rear-view mirror shot: round the mirror, the roof (the auto's canopy) and the windshield with the road
    ahead (out of focus), the dashboard below; the mirror's frame round the glass, in which the speaker (and the
    back of the car behind them) shows."""
    from PIL import ImageFilter
    g = _g(s)
    A = 255
    g.vgrad(380, 1330, (110, 168, 228), (214, 232, 246))                       # the windshield: the sky ...
    g.rect(0, 1240, LW, 1340, (176, 184, 196, A))                               # ... the far side ...
    g.rect(0, 1330, LW, 1760, (150, 160, 140, A))                               # ... the ground beside the road ...
    g.poly([(470, 1330), (610, 1330), (1400, 1760), (-320, 1760)], (100, 102, 108, A))   # ... the road
    for y0, y1, w in ((1360, 1400, 6), (1450, 1530, 10), (1600, 1700, 16)):
        g.poly([(540 - w, y0), (540 + w, y0), (540 + w * 1.3, y1), (540 - w * 1.3, y1)], (240, 220, 120, A))
    g.im = g.im.filter(ImageFilter.GaussianBlur(10 * g.k))                     # (the camera looks at the mirror)
    g.d = ImageDraw.Draw(g.im)
    if kind.startswith("auto"):
        g.rect(0, 0, LW, 380, (24, 24, 26, A))
        g.rect(0, 350, LW, 390, AUTO_YELLOW + (A,), INK + (A,), 4)
        g.rect(0, 1700, LW, LH, AUTO_GREEN + (A,), INK + (A,), 6)
        g.rect(0, 1700, LW, 1750, AUTO_YELLOW + (A,))
    else:
        g.rect(0, 0, LW, 380, (204, 198, 186, A))                               # the roof lining
        g.rect(0, 360, LW, 400, (150, 146, 136, A))
        g.rect(0, 1700, LW, LH, (40, 40, 46, A), INK + (A,), 6)                 # the dashboard
    g.line([(540, 380), (540, 560)], (40, 40, 44, A), 24)                       # the mirror's stem
    g.rrect(40, 540, LW - 40, 1320, 90, (30, 30, 34, A), INK + (A,), 8)
    g.rrect(80, 580, LW - 80, 1280, 70, GLASS)                                   # the glass: the shot shows here
    g.poly([(160, 1260), (380, 600), (440, 600), (220, 1260)], (255, 255, 255, 40))
    return g.done()


def mirror_front(s):
    return _mirror_front("car", s)


INSIDE = {"car_front": car_front_inside, "car_side": car_side_inside, "auto_front": auto_front_inside,
          "auto_side": auto_side_inside, "car_mirror": car_front_inside, "auto_mirror": auto_front_inside}
FRONT = {"car_front": car_front_front, "car_side": car_side_front, "auto_front": auto_front_front,
         "auto_side": auto_side_front, "car_mirror": mirror_front, "auto_mirror": lambda s: _mirror_front("auto", s)}


def inside(kind, s):
    return pov_inside(kind, s) if kind.endswith("_pov") else INSIDE[kind](s)


def front(kind, s):
    return pov_front(kind, s) if kind.endswith("_pov") else FRONT[kind](s)


def road_strip(s):
    """The road under the car in the side shot (two frames wide, it scrolls with the ground)."""
    g = G(s, w=LW * 2, color=(0, 0, 0, 0), mode="RGBA")
    A = 255
    g.rect(0, 1500, LW * 2, LH, (96, 98, 104, A))
    g.rect(0, 1500, LW * 2, 1520, (236, 236, 230, A))
    for x in range(0, LW * 2, 240):
        g.rect(x, 1862, x + 130, 1884, (240, 220, 120, A))
    return g.done()


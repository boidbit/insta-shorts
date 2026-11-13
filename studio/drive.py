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
       "car_mirror": ("car", "mirror"), "car_cabin": ("car", "cabin"), "auto_front": ("auto", "front"),
       "auto_side": ("auto", "side"), "auto_pov": ("auto", "pov"), "auto_mirror": ("auto", "mirror")}
POV_WORDS = {"front": "front", "saamne": "front", "samne": "front", "windshield": "front",
             "side": "side", "bahar": "side", "outside": "side",
             "pov": "pov", "driver": "pov", "nazar": "pov",
             "mirror": "mirror", "sheesha": "mirror", "shisha": "mirror",
             "inside": "inside", "andar": "inside"}
# the window band (the part of the view that shows) of each shot, as studio.vehicles.BANDS
BANDS = {"car_front": (520, 800), "car_side": (480, 960), "auto_front": (560, 1060), "auto_side": (640, 1240),
         "car_mirror": (520, 800), "auto_mirror": (560, 1060), "car_cabin": (440, 760)}
SEAT_DEPTH = 1640          # the front seats' backs: in front of the back seat's people (feet ~1590), behind the front
# where the people stand in each shot: x of the driver, then the others (None: not in the shot), their feet (ys) and
# their size against the driver (ks: a back seat is further from the camera); the shot's own size, facing / view
PLACES = {"car_front": dict(xs=(300, 780, 450, 640), ys=(1700, 1700, 1600, 1600), ks=(1, 1, 0.86, 0.86),
                            scale=1.32, facing="front", steer=True),
          "car_cabin": dict(xs=(255, 825, 430, 650), ys=(1700, 1700, 1540, 1540), ks=(1, 1, 0.84, 0.84),
                            scale=1.6, facing="front", steer=True),
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
    for x in (320, 760):                                                       # the back seat's headrests
        g.rrect(x - 70, 760, x + 70, 860, 30, (66, 66, 76, A), INK + (A,), 4)
    return g.done()


def _front_seats(g, xs, top, bottom, w, A=255):
    """Two front seats seen from in front of the car: backrest, headrest on its two posts."""
    for x in xs:
        g.rrect(x - w, top + 180, x + w, bottom, 54, (70, 70, 80, A), INK + (A,), 5)
        g.rrect(x - w + 26, top + 210, x + w - 26, bottom - 30, 40, None, (60, 60, 70, A), 4)   # its stitching
        g.rrect(x - w * 0.5, top, x + w * 0.5, top + 150, 34, (78, 78, 88, A), INK + (A,), 4)
        g.rect(x - 30, top + 150, x - 18, top + 190, (150, 150, 156, A))
        g.rect(x + 18, top + 150, x + 30, top + 190, (150, 150, 156, A))


def seats(kind, s):
    """The front seats, a piece of its own: depth-sorted with the people (SEAT_DEPTH), so the back seat's people
    are behind them (their heads show between and over them) and the driver and the one beside him in front of
    them. None for a shot without them."""
    if kind == "car_front":
        g = _g(s)
        _front_seats(g, (300, 780), 700, 1560, 175)
        return g.done()
    if kind == "car_cabin":
        g = _g(s)
        _front_seats(g, (255, 825), 600, 1660, 200)
        return g.done()
    return None


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


# ------------------------------------------------------------------ inside the car, from the dashboard
def car_cabin_inside(s):
    """Behind everybody: the roof lining with its light, the back window (the road going away shows in it), the
    back pillars and little side windows, the back seat with its headrests."""
    g = _g(s)
    A = 255
    lining, pillar = (214, 208, 196), (184, 178, 166)
    g.rect(0, 0, LW, 440, lining + (A,))
    g.rrect(470, 120, 610, 170, 20, (250, 246, 220, A), INK + (A,), 4)        # the cabin light
    g.line([(0, 420), (LW, 420)], _shade(lining, 0.86) + (A,), 6)
    g.rect(0, 430, LW, 820, pillar + (A,))                                       # the back pillars
    g.rrect(240, 430, 840, 780, 46, (40, 40, 44, A), INK + (A,), 6)            # the back window's frame
    g.rrect(262, 452, 818, 758, 34, GLASS)
    for x0, x1 in ((40, 180), (900, 1040)):                                      # the little side windows
        g.rrect(x0, 470, x1, 720, 30, (40, 40, 44, A), INK + (A,), 5)
        g.rrect(x0 + 14, 484, x1 - 14, 706, 22, GLASS)
    g.poly([(300, 750), (380, 470), (410, 470), (330, 750)], (255, 255, 255, 40))   # the glass shines
    g.rect(200, 760, 880, 800, (48, 48, 54, A), INK + (A,), 4)                 # the parcel shelf
    g.rect(0, 800, LW, LH, (64, 66, 76, A))                                      # the back seat
    for x in range(90, LW, 180):
        g.line([(x, 860), (x, 1500)], (56, 58, 68, A), 4)
    g.rect(0, 1480, LW, 1530, (54, 56, 66, A))
    for x in (330, 750):                                                        # its headrests
        g.rrect(x - 80, 760, x + 80, 880, 34, (74, 76, 86, A), INK + (A,), 4)
    g.rect(0, 1530, LW, LH, (40, 40, 46, A))                                     # the floor
    return g.done()


def car_cabin_front(s):
    """In front of everybody: the dashboard right under the camera (the people show from the waist up, as from a
    dashboard camera), its vents, a phone on its stand with the map, and a little air freshener hanging from the
    mirror (its string comes in from the top)."""
    g = _g(s)
    A = 255
    dash, top = (40, 40, 46), (58, 58, 66)
    g.poly([(0, 1290), (300, 1262), (780, 1252), (LW, 1270), (LW, LH), (0, LH)], dash + (A,), INK + (A,), 6)
    g.poly([(0, 1290), (300, 1262), (780, 1252), (LW, 1270), (LW, 1320), (780, 1306), (300, 1316), (0, 1340)],
           top + (A,))
    for x in (120, 960):                                                       # the side vents
        g.rrect(x - 70, 1400, x + 70, 1480, 18, (24, 24, 28, A), INK + (A,), 4)
        for yy in (1420, 1440, 1460):
            g.line([(x - 56, yy), (x + 56, yy)], (70, 70, 78, A), 4)
    for x in (470, 610):                                                       # the middle vents
        g.rrect(x - 50, 1410, x + 50, 1480, 14, (24, 24, 28, A), INK + (A,), 4)
    g.rrect(380, 1560, 700, 1680, 20, (20, 20, 24, A), INK + (A,), 4)          # the music system
    g.rect(400, 1580, 520, 1620, (90, 180, 220, A))
    g.rrect(730, 1150, 880, 1270, 16, (20, 20, 24, A), INK + (A,), 4)          # a phone on its stand, the map
    g.rect(744, 1164, 866, 1256, (120, 200, 140, A))
    g.line([(760, 1246), (810, 1196), (856, 1176)], (60, 120, 220, A), 6)
    g.line([(540, -10), (540, 120)], (40, 40, 44, A), 4)                        # the air freshener
    g.poly([(510, 120), (570, 120), (556, 200), (524, 200)], (60, 170, 90, A), INK + (A,), 4)
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


def rich_view(view, s, time, dy):
    """The view going past the windows in a driving shot, richer than the vehicles' own (which stays as it was
    for their insides and CAMERA: classic): highway / gaon get two hill ranges, fields with crop rows, full trees,
    a dhaba and a billboard, electric poles; close by a crash barrier with its posts, kilometre stones, bushes and
    street lights whizzing past. None for the other views. Same form as studio.vehicles._outside."""
    if view not in ("highway", "gaon"):
        return None
    from . import vehicles as V
    night = time == "night"
    sky = V._sky(s, (14, 18, 50) if night else (92, 158, 230), (54, 50, 96) if night else (222, 236, 244), dy)
    far, mid, near = V._wide(s, (150, 170, 190)), V._wide(s, (120, 140, 120)), V._wide(s, (40, 44, 40))
    A = 255
    field = (150, 188, 98) if view == "gaon" else (128, 172, 92)
    for ox in V.TILES:                                    # (every tile the same: the strip wraps without a seam)
        if not night:                                                         # clouds, high up, slow
            for cx, cy, r in ((160, 260, 60), (620, 200, 80), (930, 330, 50)):
                for dx, dyy, rr in ((0, 0, 1.0), (r * 0.9, 12, 0.75), (-r * 0.9, 16, 0.7), (r * 0.3, -r * 0.4, 0.7)):
                    far.ellipse(ox + cx + dx - r * rr, cy + dyy - r * rr * 0.7, ox + cx + dx + r * rr,
                                cy + dyy + r * rr * 0.7, (255, 255, 255, 225))
        for col, base, amp, f in (((158, 182, 208), 700, 130, (2, 0.4, 5)), ((118, 162, 128), 790, 70, (3, 1.7, 7))):
            pts = [(ox, 900)]
            for xi in range(0, LW + 1, 24):
                y = base - amp * (0.55 + 0.25 * math.sin(2 * math.pi * xi / LW * f[0] + f[1])
                                  + 0.2 * math.sin(2 * math.pi * xi / LW * f[2]))
                pts.append((ox + xi, y))
            pts.append((ox + LW, 900))
            far.poly(pts, col + (A,))
        mid.rect(ox, 846, ox + LW, 1000, field + (A,))                       # the fields, their rows
        for yy in range(862, 1000, 20):
            mid.line([(ox, yy), (ox + LW, yy + 6)], _shade(field, 0.86) + (A,), 4)
        for i, x in enumerate((60, 300, 520, 860, 1010)):                     # trees
            r = (64, 80, 58, 90, 70)[i]
            mid.rect(ox + x - 9, 790 - r * 0.2, ox + x + 9, 870, (104, 76, 50, A))
            for dx, dyy, rr, c in ((0, 0, 1.0, (52, 116, 62)), (-r * 0.6, 16, 0.7, (52, 116, 62)),
                                   (r * 0.6, 16, 0.7, (44, 100, 54)), (-r * 0.25, -r * 0.3, 0.55, (90, 156, 80))):
                mid.circle(ox + x + dx, 760 - r * 0.6 + dyy, r * rr, c + (A,))
        mid.rect(ox + 640, 770, ox + 800, 860, (236, 206, 120, A), INK + (A,), 4)   # a dhaba
        mid.poly([(ox + 626, 774), (ox + 720, 728), (ox + 814, 774)], (190, 70, 50, A), INK + (A,), 4)
        mid.rect(ox + 660, 740, ox + 780, 768, (250, 240, 220, A), INK + (A,), 3)
        mid.rect(ox + 696, 810, ox + 730, 860, (110, 70, 44, A))
        mid.rect(ox + 380, 640, ox + 480, 700, (250, 246, 236, A), INK + (A,), 4)   # a billboard
        mid.rect(ox + 390, 650, ox + 470, 690, (60, 150, 210, A))
        mid.rect(ox + 425, 700, ox + 435, 860, (80, 80, 84, A))
        for x in (180, 960):                                                  # electric poles and their wires
            mid.rect(ox + x, 640, ox + x + 8, 860, (90, 90, 96, A))
            mid.rect(ox + x - 22, 650, ox + x + 30, 658, (90, 90, 96, A))
        mid.line([(ox - 20, 660), (ox + 180, 654), (ox + 560, 668), (ox + 960, 654), (ox + LW + 20, 660)],
                 (50, 50, 56, A), 2)
        near.rect(ox, 950, ox + LW, 1000, (176, 150, 112, A))                 # the road's shoulder
        near.rect(ox, 896, ox + LW, 918, (206, 208, 214, A))                  # the crash barrier
        near.rect(ox, 906, ox + LW, 910, (150, 152, 160, A))
        for x in range(0, LW, 120):
            near.rect(ox + x, 896, ox + x + 14, 960, (130, 132, 140, A))
        for x in (250, 790):                                                  # kilometre stones
            near.rect(ox + x, 920, ox + x + 40, 960, (244, 244, 238, A), INK + (A,), 3)
            near.ellipse(ox + x, 906, ox + x + 40, 934, (246, 196, 40, A), INK + (A,), 3)
        for x in (90, 470, 650, 1000):                                        # bushes
            near.circle(ox + x, 958, 34, (54, 110, 58, A))
            near.circle(ox + x + 30, 964, 26, (64, 126, 64, A))
        near.rect(ox + 560, 380, ox + 574, 960, (70, 72, 80, A))              # a street light
        near.line([(ox + 567, 384), (ox + 620, 370), (ox + 680, 380)], (70, 72, 80, A), 8)
        near.rect(ox + 662, 376, ox + 704, 390, (54, 56, 62, A))
    layers = [(far.done(), V.LAYER_SPEEDS[0]), (mid.done(), V.LAYER_SPEEDS[1]),
              (V._blur_x(near.done(), 5), V.LAYER_SPEEDS[2])]
    layers = [(V._lift(l, 170 * s), sp) for l, sp in layers]
    if night:
        layers = [(V._night_layer(l), sp) for l, sp in layers]
    return sky, layers


HZ = 760                   # the driver's eye line (the horizon) in the road-ahead shot
_STATIC = {}


def _persp(y):
    """How big a thing on the road is at screen height y (0 at the horizon, 1 at the bottom of the frame)."""
    return max(0.0, (y - HZ) / float(LH - HZ))


def _ahead_static(W, H, k, view, night):
    """What does not move in the road-ahead shot: the sky (clouds, sun / moon and stars), the far hills or the
    skyline, the land on both sides. Cached per size."""
    from PIL import Image, ImageFilter
    key = (W, H, round(k, 4), view, night)
    if key in _STATIC:
        return _STATIC[key]
    img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    d = ImageDraw.Draw(img, "RGBA")
    sky0, sky1 = ((10, 14, 44), (52, 48, 96)) if night else ((84, 150, 226), (214, 232, 246))
    for i in range(0, int(HZ * k) + 4, 3):
        u = min(1.0, i / (HZ * k))
        d.rectangle([0, i, W, i + 3], fill=tuple(int(a + (b - a) * u) for a, b in zip(sky0, sky1)))
    rnd = random.Random(11)
    if night:
        for _ in range(70):
            x, y = rnd.uniform(0, LW), rnd.uniform(0, HZ - 200)
            r = rnd.uniform(1.5, 3.5)
            d.ellipse([(x - r) * k, (y - r) * k, (x + r) * k, (y + r) * k], fill=(255, 250, 230, rnd.randint(140, 255)))
        d.ellipse([820 * k, 120 * k, 920 * k, 220 * k], fill=(250, 246, 226))
    else:
        cl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dc = ImageDraw.Draw(cl, "RGBA")
        for cx, cy, r in ((180, 200, 70), (720, 140, 90), (980, 320, 60), (420, 360, 50)):
            for dx, dy, rr in ((0, 0, 1.0), (r * 0.9, 12, 0.75), (-r * 0.9, 16, 0.7), (r * 0.3, -r * 0.4, 0.7)):
                q = r * rr
                dc.ellipse([(cx + dx - q) * k, (cy + dy - q * 0.7) * k, (cx + dx + q) * k, (cy + dy + q * 0.7) * k],
                           fill=(255, 255, 255, 215))
        img.alpha_composite(cl.filter(ImageFilter.GaussianBlur(4 * k)))
    if view == "city":                                                          # the city ahead: a skyline
        x = -20
        while x < LW + 20:
            w, h = rnd.uniform(50, 110), rnd.uniform(90, 300)
            col = (36, 40, 66) if night else (164, 176, 200)
            d.rectangle([x * k, (HZ - h) * k, (x + w) * k, HZ * k + 2], fill=col)
            for wy in range(int(HZ - h + 14), HZ - 14, 26):
                for wx in range(int(x + 10), int(x + w - 12), 22):
                    if rnd.random() < (0.5 if night else 0.8):
                        c = (255, 214, 120) if night else (128, 146, 176)
                        d.rectangle([wx * k, wy * k, (wx + 9) * k, (wy + 12) * k], fill=c)
            x += w + rnd.uniform(0, 14)
        land = (60, 62, 70) if night else (186, 182, 172)
    else:                                                                       # hills, two ranges
        far_c, near_c = ((40, 46, 80), (30, 44, 50)) if night else (
            {"pahad": ((150, 166, 204), (92, 132, 116))}.get(view, ((156, 180, 202), (118, 160, 128))))
        for col, base, amp, f in ((far_c, HZ - 120, 90, (1, 3, 5)), (near_c, HZ - 40, 46, (2, 5, 9))):
            if view == "pahad":
                amp *= 2.4
            pts = [(0, HZ * k + 2)]
            for xi in range(0, LW + 21, 20):
                y = base - amp * (0.55 + 0.25 * math.sin(xi / LW * math.pi * f[0] + f[1])
                                  + 0.2 * math.sin(xi / LW * math.pi * f[2] + 1.3))
                pts.append((xi * k, y * k))
            pts.append((LW * k, HZ * k + 2))
            d.polygon(pts, fill=col)
        if view == "pahad" and not night:
            for px in (260, 760):
                d.polygon([((px - 60) * k, (HZ - 250) * k), (px * k, (HZ - 330) * k), ((px + 70) * k, (HZ - 245) * k)],
                          fill=(246, 248, 252))
        land = (34, 46, 34) if night else ({"gaon": (150, 182, 96), "pahad": (110, 150, 96)}.get(view, (132, 172, 96)))
    d.rectangle([0, HZ * k, W, H], fill=land)
    _STATIC[key] = img
    if len(_STATIC) > 12:
        _STATIC.pop(next(iter(_STATIC)))
    return img


def _tree(d, x, y, sc, k, night):
    """A roadside tree standing at (x, y) at size sc: a trunk and a full crown, lit from the left."""
    if sc < 0.01:
        return
    trunk = (70, 52, 36) if night else (112, 80, 52)
    crown = [(26, 52, 34), (20, 42, 28), (34, 64, 42)] if night else [(64, 134, 70), (46, 108, 56), (96, 162, 84)]
    h, r = 560 * sc, 250 * sc
    d.rectangle([(x - 18 * sc) * k, (y - h) * k, (x + 18 * sc) * k, y * k], fill=trunk)
    cy = y - h - r * 0.4
    for dx, dy, rr, ci in ((0, 0, 1.0, 1), (-r * 0.6, r * 0.25, 0.75, 1), (r * 0.6, r * 0.25, 0.75, 1),
                           (-r * 0.25, -r * 0.3, 0.6, 2), (r * 0.35, r * 0.35, 0.55, 1)):
        q = r * rr
        d.ellipse([(x + dx - q) * k, (cy + dy - q) * k, (x + dx + q) * k, (cy + dy + q) * k], fill=crown[ci])
    q = r * 0.42
    d.ellipse([(x - r * 0.45 - q) * k, (cy - r * 0.35 - q) * k, (x - r * 0.45 + q) * k, (cy - r * 0.35 + q) * k],
              fill=crown[2])


def _lamp(d, x, y, sc, k, side, night):
    """A street light on the side of the road, its arm over the road."""
    pole = (70, 72, 80)
    h = 1150 * sc
    d.rectangle([(x - 9 * sc) * k, (y - h) * k, (x + 9 * sc) * k, y * k], fill=pole)
    ax = x - side * 230 * sc
    d.line([(x * k, (y - h) * k), (((x + ax) / 2) * k, (y - h - 40 * sc) * k), (ax * k, (y - h - 10 * sc) * k)],
           fill=pole, width=max(1, int(14 * sc * k)))
    d.rectangle([(ax - 36 * sc) * k, (y - h - 22 * sc) * k, (ax + 36 * sc) * k, (y - h + 4 * sc) * k], fill=(54, 56, 62))
    if night:
        g = 90 * sc
        d.ellipse([(ax - g) * k, (y - h - g * 0.6) * k, (ax + g) * k, (y - h + g * 0.9) * k], fill=(255, 220, 140, 120))
        d.ellipse([(ax - 26 * sc) * k, (y - h - 6 * sc) * k, (ax + 26 * sc) * k, (y - h + 12 * sc) * k],
                  fill=(255, 236, 170))


def _milestone(d, x, y, sc, k, n):
    """A kilometre stone: white, a yellow cap, the distance on it."""
    w, h = 80 * sc, 130 * sc
    d.rectangle([(x - w / 2) * k, (y - h) * k, (x + w / 2) * k, y * k], fill=(244, 244, 238))
    d.pieslice([(x - w / 2) * k, (y - h - w / 2) * k, (x + w / 2) * k, (y - h + w / 2) * k], 180, 360,
               fill=(246, 196, 40))
    d.rectangle([(x - w / 2) * k, (y - h) * k, (x + w / 2) * k, (y - h + 12 * sc) * k], fill=(246, 196, 40))
    if w * k > 26:
        from .text import font
        f = font(30 * sc * k)
        d.text((x * k, (y - h * 0.45) * k), str(n), fill=(40, 40, 44), font=f, anchor="mm")


def _sign(d, x, y, sc, k, text, sub):
    """A big green highway sign on two legs."""
    w, h = 760 * sc, 300 * sc
    top = y - 900 * sc
    for lx in (x - w * 0.32, x + w * 0.32):
        d.rectangle([(lx - 10 * sc) * k, top * k, (lx + 10 * sc) * k, y * k], fill=(140, 142, 148))
    d.rounded_rectangle([(x - w / 2) * k, top * k, (x + w / 2) * k, (top + h) * k], radius=max(1, 18 * sc * k),
                        fill=(26, 120, 70), outline=(240, 240, 236), width=max(1, int(8 * sc * k)))
    if w * k > 90:
        from .text import font
        d.text((x * k, (top + h * 0.36) * k), text, fill=(255, 255, 255), font=font(74 * sc * k), anchor="mm")
        d.text((x * k, (top + h * 0.74) * k), sub, fill=(255, 236, 140), font=font(52 * sc * k), anchor="mm")


def _truck_back(d, x, y, sc, k, night):
    """A desi truck seen from behind: the painted body, HORN OK PLEASE, its lights, the mudflaps."""
    w, h = 1250 * sc, 1300 * sc
    top = y - h
    d.rectangle([(x - w / 2) * k, top * k, (x + w / 2) * k, (y - 230 * sc) * k], fill=(238, 170, 40))
    d.rectangle([(x - w / 2) * k, top * k, (x + w / 2) * k, (top + 120 * sc) * k], fill=(196, 40, 50))
    d.rectangle([(x - w / 2) * k, (y - 420 * sc) * k, (x + w / 2) * k, (y - 330 * sc) * k], fill=(30, 120, 80))
    for i in range(7):                                                          # the painted border
        cx = x - w / 2 + (i + 0.5) * w / 7
        d.ellipse([(cx - 34 * sc) * k, (top + 150 * sc) * k, (cx + 34 * sc) * k, (top + 218 * sc) * k],
                  fill=(40, 90, 200) if i % 2 else (220, 40, 120))
    if w * k > 110:
        from .text import font
        d.text((x * k, (top + 520 * sc) * k), "HORN OK", fill=(180, 30, 40), font=font(170 * sc * k), anchor="mm")
        d.text((x * k, (top + 700 * sc) * k), "PLEASE", fill=(30, 60, 160), font=font(150 * sc * k), anchor="mm")
    d.rectangle([(x - w / 2 - 10 * sc) * k, (y - 240 * sc) * k, (x + w / 2 + 10 * sc) * k, (y - 170 * sc) * k],
                fill=(40, 40, 44))                                              # the bumper
    lit = (255, 60, 50) if night else (220, 40, 40)
    for side in (-1, 1):
        lx = x + side * (w / 2 - 70 * sc)
        d.rectangle([(lx - 50 * sc) * k, (y - 330 * sc) * k, (lx + 50 * sc) * k, (y - 260 * sc) * k], fill=lit)
        if night:
            d.ellipse([(lx - 120 * sc) * k, (y - 380 * sc) * k, (lx + 120 * sc) * k, (y - 210 * sc) * k],
                      fill=(255, 60, 50, 70))
        mx = x + side * (w / 2 - 190 * sc)                                      # mudflaps and wheels
        d.rectangle([(mx - 70 * sc) * k, (y - 170 * sc) * k, (mx + 70 * sc) * k, (y - 10 * sc) * k], fill=(24, 24, 28))
        d.rectangle([(mx - 70 * sc) * k, (y - 60 * sc) * k, (mx + 70 * sc) * k, (y - 40 * sc) * k], fill=(200, 40, 40))


def _car_coming(d, x, y, sc, k, night):
    """A car coming the other way, seen from in front."""
    w, h = 900 * sc, 640 * sc
    top = y - h
    body = (60, 110, 190)
    d.rounded_rectangle([(x - w / 2) * k, (top + h * 0.38) * k, (x + w / 2) * k, (y - 60 * sc) * k],
                        radius=max(1, 40 * sc * k), fill=body)
    d.polygon([((x - w * 0.36) * k, (top + h * 0.4) * k), ((x - w * 0.26) * k, top * k), ((x + w * 0.26) * k, top * k),
               ((x + w * 0.36) * k, (top + h * 0.4) * k)], fill=body)
    d.polygon([((x - w * 0.31) * k, (top + h * 0.38) * k), ((x - w * 0.23) * k, (top + h * 0.06) * k),
               ((x + w * 0.23) * k, (top + h * 0.06) * k), ((x + w * 0.31) * k, (top + h * 0.38) * k)],
              fill=(150, 190, 220))
    lamp = (255, 250, 210) if night else (240, 240, 226)
    for side in (-1, 1):
        lx = x + side * w * 0.36
        d.ellipse([(lx - 60 * sc) * k, (y - 250 * sc) * k, (lx + 60 * sc) * k, (y - 190 * sc) * k], fill=lamp)
        d.rectangle([(lx - 60 * sc) * k, (y - 70 * sc) * k, (lx - 10 * sc) * k, y * k], fill=(24, 24, 28))
    d.rectangle([(x - 120 * sc) * k, (y - 240 * sc) * k, (x + 120 * sc) * k, (y - 180 * sc) * k], fill=(40, 40, 46))


def road_ahead(img, t, s, kind, view="city", time=None):
    """The road rushing towards the driver (drawn every frame onto img, a picture of the whole frame at s): the sky
    and the far hills / skyline, fields or the town on both sides, a two-lane road (we keep left) with its white
    edges, the dashed middle line and the shoulders coming at us; trees, street lights, kilometre stones, a crash
    barrier and now and then a big green sign going past; a painted truck ahead, cars coming the other way."""
    night = time == "night"
    k = s
    W, H = img.size
    img.paste(_ahead_static(W, H, k, view, night), (0, 0))
    d = ImageDraw.Draw(img, "RGBA")
    vx = 540
    speed = 0.55                                                     # road lengths a second (the feel of speed)

    def X(lat, y):                                                   # lateral place lat (px at the bottom) at y
        return vx + lat * _persp(y)

    def at(u):                                                       # depth phase 0 (far) .. 1 (here) -> y
        return HZ + (LH - HZ) * u ** 2.3
    rural = view != "city"
    if rural:                                                        # crop rows / grass stripes coming closer
        for i in range(14):
            u0 = ((i / 14.0) + t * speed) % 1.0
            ya, yb = at(u0), at(min(1.0, u0 + 0.5 / 14))
            c = (28, 40, 28) if night else ((120, 162, 86) if view != "gaon" else (138, 172, 84))
            for side in (-1, 1):
                d.polygon([(X(side * 1500, ya) * k, ya * k), (X(side * 9000, ya) * k, ya * k),
                           (X(side * 9000, yb) * k, yb * k), (X(side * 1500, yb) * k, yb * k)], fill=c)
    else:                                                            # the town: a footpath on both sides
        for side in (-1, 1):
            d.polygon([(X(side * 1300, HZ) * k, HZ * k), (X(side * 2600, HZ) * k, HZ * k),
                       (X(side * 2600, LH) * k, H), (X(side * 1300, LH) * k, H)],
                      fill=(70, 70, 78) if night else (176, 170, 160))
    left, right, mid = -1000, 1700, 350                              # the road: we keep left
    shoulder = (60, 54, 46) if night else (176, 150, 112)
    d.polygon([(X(left - 280, HZ) * k, HZ * k), (X(right + 280, HZ) * k, HZ * k),
               (X(right + 280, LH) * k, H), (X(left - 280, LH) * k, H)], fill=shoulder)
    for i in range(0, 40):                                           # the tarmac: lighter far away (haze)
        ya, yb = HZ + (LH - HZ) * (i / 40.0) ** 1.6, HZ + (LH - HZ) * ((i + 1) / 40.0) ** 1.6
        u = i / 40.0
        c = tuple(int(a + (b - a) * u) for a, b in zip(((70, 72, 92) if night else (150, 150, 156)),
                                                       ((40, 40, 48) if night else (88, 90, 96))))
        d.polygon([(X(left, ya) * k, ya * k), (X(right, ya) * k, ya * k), (X(right, yb) * k, yb * k + 1),
                   (X(left, yb) * k, yb * k + 1)], fill=c)
    if night:                                                        # our headlights on the road
        d.polygon([(X(-700, HZ + 120) * k, (HZ + 120) * k), (X(500, HZ + 120) * k, (HZ + 120) * k),
                   (X(900, LH) * k, H), (X(-1100, LH) * k, H)], fill=(255, 240, 190, 46))
    for i in range(10):                                              # tyre marks / patches whizzing past
        u = ((i / 10.0) + t * speed * 1.0 + 0.03) % 1.0
        y = at(u)
        sc = _persp(y)
        lat = (-640, -80, 980, 1300, -420)[i % 5]
        d.rectangle([(X(lat, y) - 90 * sc) * k, y * k, (X(lat, y) + 90 * sc) * k, (y + 6 * sc + 1) * k],
                    fill=(255, 255, 255, 26))
    for lat in (left, right):                                        # the white edges
        d.polygon([(X(lat - 22, HZ) * k, HZ * k), (X(lat + 22, HZ) * k, HZ * k), (X(lat + 22, LH) * k, H),
                   (X(lat - 22, LH) * k, H)], fill=(236, 236, 228))
    for i in range(12):                                              # the dashed middle line coming at us
        u0 = ((i / 12.0) + t * speed) % 1.0
        ya, yb = at(u0), at(min(1.0, u0 + 0.045))
        d.polygon([(X(mid - 26, ya) * k, ya * k), (X(mid + 26, ya) * k, ya * k), (X(mid + 26, yb) * k, yb * k),
                   (X(mid - 26, yb) * k, yb * k)], fill=(246, 214, 70) if not night else (220, 196, 90))
    things = []                                                      # the roadside, far to near
    n = 8
    for i in range(n):
        u = ((i / float(n)) + t * speed) % 1.0
        y = at(u)
        sc = _persp(y)
        if sc < 0.012:
            continue
        if rural:
            things.append((y, "tree", X(-1750 if i % 2 else -2250, y), sc, -1))
            things.append((y, "tree", X(2250 if i % 2 else 2750, y), sc, 1))
            if i % 2 == 0:
                things.append((y + 0.01, "lamp", X(-1380, y), sc, -1))
            if i % 4 == 1:
                things.append((y + 0.02, "stone", X(-1200, y), sc, 12 - i // 4))
        else:
            things.append((y, "block", X(-3300, y), sc, -1))
            things.append((y, "block", X(3800, y), sc, 1))
            things.append((y + 0.01, "lamp", X(-1500, y), sc, -1))
            things.append((y + 0.01, "lamp", X(2200, y), sc, 1))
    su = ((t * speed * 0.25) + 0.15) % 1.0                           # a big green sign every few seconds
    ys = at(su)
    if _persp(ys) > 0.02:
        things.append((ys, "sign", X(-1900, ys), _persp(ys), -1))
    cu = (t / 6.5) % 1.0                                             # a car coming the other way
    if cu < 0.45:
        yc = at(cu / 0.45)
        things.append((yc, "car", X(1050, yc), _persp(yc), 1))
    for y, what, x, sc, extra in sorted(things, key=lambda q: q[0]):
        if what == "tree":
            _tree(d, x, y, sc, k, night)
        elif what == "lamp":
            _lamp(d, x, y, sc, k, extra, night)
        elif what == "stone":
            _milestone(d, x, y, sc, k, max(1, extra))
        elif what == "sign":
            _sign(d, x, y, sc, k, "DESIPUR", "12 km  →")
        elif what == "car":
            _car_coming(d, x, y, sc, k, night)
        elif what == "block":                                         # a house / shop going past
            w, h = 900 * sc, (1500 + 500 * ((int(y) // 7) % 3)) * sc
            col = ((60, 56, 80) if night else ((214, 160, 120), (232, 206, 140), (160, 196, 214))[int(y) % 3])
            d.rectangle([(x - w / 2) * k, (y - h) * k, (x + w / 2) * k, y * k], fill=col)
            for wy in (0.25, 0.5):
                for wx in (-0.3, 0.05):
                    d.rectangle([(x + wx * w) * k, (y - h + wy * h) * k, (x + (wx + 0.22) * w) * k,
                                 (y - h + (wy + 0.14) * h) * k], fill=(255, 214, 120) if night else (90, 120, 150))
    if rural:                                                        # the crash barrier on our side
        top_bar = []
        for i in range(0, 41):
            y = HZ + (LH - HZ) * (i / 40.0) ** 1.4
            top_bar.append(y)
        for ya, yb in zip(top_bar, top_bar[1:]):
            sa, sb = _persp(ya), _persp(yb)
            d.polygon([(X(-1300, ya) * k, (ya - 150 * sa) * k), (X(-1300, yb) * k, (yb - 150 * sb) * k),
                       (X(-1300, yb) * k, (yb - 90 * sb) * k), (X(-1300, ya) * k, (ya - 90 * sa) * k)],
                      fill=(196, 198, 204) if not night else (90, 92, 104))
        for i in range(16):
            u = ((i / 16.0) + t * speed) % 1.0
            y = at(u)
            sc = _persp(y)
            d.rectangle([(X(-1300, y) - 8 * sc) * k, (y - 150 * sc) * k, (X(-1300, y) + 8 * sc) * k, y * k],
                        fill=(120, 122, 130))
    ahead = 0.5 + 0.5 * math.sin(t * 0.35)                           # the truck ahead, in our lane
    y = HZ + 210 + 80 * ahead
    _truck_back(d, X(-330, y), y, _persp(y), k, night)


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
          "auto_side": auto_side_inside, "car_mirror": car_cabin_inside, "auto_mirror": auto_front_inside,
          "car_cabin": car_cabin_inside}
FRONT = {"car_front": car_front_front, "car_side": car_side_front, "auto_front": auto_front_front,
         "auto_side": auto_side_front, "car_mirror": mirror_front, "auto_mirror": lambda s: _mirror_front("auto", s),
         "car_cabin": car_cabin_front}


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


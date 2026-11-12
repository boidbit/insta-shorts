"""Hand-made 2.5D sets for more rooms, painted like the kitchen and the living room.

balcony_25d    a balcony by day: the city far away and the building opposite in their own layers, the house wall with
               its door and an AC box whose fan turns, a grille railing with pots, a wind chime swaying, clothes on a
               line, a plastic chair, pigeons on the railing.
bathroom_25d   a bathroom: tiles, a frosted window, the shower dripping, the mirror cabinet and basin, the geyser with its
               red light, the blue bucket and the red mug, a towel, a slipper blurred in front.
hostel_25d     a hostel room: a bunk bed with a crumpled blanket, posters, a study table with a laptop that glows and a
               pot of maggi steaming, towels on a line, a window, a fan turning, a guitar blurred in front.
library_25d    a library: SILENCE, three tall cases of books, a ladder, a reading table with a green lamp and open books,
               dust in the lamp's light, a pile of books blurred in front.
coaching_25d   a coaching class: TOPPERS ACADEMY, the whiteboard of formulas, OUR TOPPERS, rows of benches, two fans.
exam_hall_25d  an exam hall: the EXAM board (Time: 3 hrs), a clock whose seconds hand runs, a window onto the school
               ground with sunlight, rows of desks with papers, two fans, a desk and a pen blurred in front.
gym_25d        a gym: GYM, NO PAIN NO GAIN, a mirror wall, a dumbbell rack, kettlebells, a treadmill whose belt runs.
party_25d      a birthday party: HAPPY BIRTHDAY, streamers and bulbs that twinkle, balloons bobbing, a cake whose candles
               flicker, gifts, coloured disco spots running over the walls.
jail_25d       inside a lock-up: the high barred window (sky and a tree outside, its own layer) and its beam with dust,
               the concrete bench, a shelf with a mug, days scratched on the wall, the corridor with a flickering bulb.
               The barred door is the jail_door set piece (open / broken), drawn over the same place as in 2D.
(library, coaching, exam hall, gym and party have writing on them, so a reverse shot never mirrors them.)
"""
import math
import random

from PIL import Image

from .scenery import PAL_BULB, Cv, Layer, Layered, along, catenary, fill_tex, mix, motes, mul, quad_image, \
    sign_image, steam, twinkle
from .scenery_civic import _room_shell, board_image
from .scenery_home import _class_outside, _clock, _curtain, _floor_tiles, _leaves, _room_outside, _shadow, \
    _tube_light, _window, fan
from .scenery_road import day_sky, rooftops, skyline
from .scenery_town import _second_hand
from ..util import LH, LW

INK = (44, 38, 40, 255)
VP, F = (540, 800), 1280


def _blank(k, fill=(0, 0, 0, 0)):
    return Image.new("RGBA", (8, 8), fill)


def _layered(back, front, light, horizon, ground, sprites=None):
    return Layered(back, front, light=light, horizon=horizon, ground=ground, sprites=sprites)


# ------------------------------------------------------------------ balcony
BAL_F = 1260
AC = (150, 300, 290, 400)
CHIME = (700, 70)


def _balcony(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(255, 236, 190, 0))
    rnd = random.Random(301)
    cv.rect(-20, -20, LW + 20, 60, (226, 220, 210, 255), INK, 3)                       # the slab above
    fill_tex(cv, [(-20, 60), (300, 60), (300, BAL_F), (-20, BAL_F)], [(0, (240, 226, 196)), (BAL_F, (226, 208, 176))],
             seed=303, cell=50, lo=0.95, hi=1.04)
    cv.line([(300, 60), (300, BAL_F)], INK, 3)
    cv.rect(60, 560, 240, BAL_F, (130, 84, 50, 255), INK, 3)                           # the door
    for (a, b) in ((600, 860), (900, BAL_F - 30)):
        cv.rect(80, a, 220, b, (146, 96, 58, 255), (100, 64, 38, 255), 2)
    cv.ell(210, 900, 9, 9, (220, 190, 80, 255), INK, 2)
    x0, y0, x1, y1 = AC                                                                 # the AC's outdoor box
    cv.rect(x0, y0, x1, y1, (236, 236, 232, 255), INK, 3)
    cv.ell((x0 + x1) / 2 - 16, (y0 + y1) / 2, 40, 40, (200, 200, 196, 255), INK, 2)
    cv.line([(x1 - 30, y0 + 20), (x1 - 30, y1 - 20)], (170, 170, 166, 255), 3)
    cv.line([(x1 - 50, y0 + 20), (x1 - 50, y1 - 20)], (170, 170, 166, 255), 3)
    pts = catenary(300, 150, 1100, 160, 50)                                             # clothes on a line
    cv.line(pts, (60, 50, 50, 255), 2)
    for i, (cx, cy) in enumerate(along(pts, 110)[1:-1]):
        col = ((220, 60, 60), (60, 120, 220), (250, 200, 50), (240, 240, 236), (60, 170, 120))[i % 5]
        if i % 2:
            cv.poly([(cx - 34, cy), (cx + 34, cy), (cx + 26, cy + 90), (cx - 26, cy + 90)], col + (255,), INK, 2)
        else:
            cv.poly([(cx - 40, cy), (cx + 40, cy), (cx + 40, cy + 24), (cx + 24, cy + 20), (cx + 22, cy + 90),
                     (cx - 22, cy + 90), (cx - 24, cy + 20), (cx - 40, cy + 24)], col + (255,), INK, 2)
    cv.line([CHIME, (CHIME[0], 0)], (60, 60, 64, 255), 2)
    # the railing
    cv.rect(300, 1000, LW + 20, 1016, (60, 64, 70, 255), INK, 2)
    for x in range(310, LW + 20, 30):
        cv.rect(x, 1016, x + 6, 1236, (70, 74, 80, 255))
    for x in range(330, LW, 120):                                                       # a pattern in the grille
        cv.ell(x + 30, 1120, 26, 26, None, (70, 74, 80, 255), 5)
    cv.rect(300, 1236, LW + 20, BAL_F, (190, 186, 178, 255), INK, 2)
    for px in (380, 1000):                                                              # pots
        cv.poly([(px - 40, BAL_F), (px + 40, BAL_F), (px + 50, BAL_F - 80), (px - 50, BAL_F - 80)],
                (200, 110, 70, 255), INK, 2)
        _leaves(cv, 16, px - 90, px + 90, BAL_F - 240, BAL_F - 70, 34, ((50, 130, 60), (120, 180, 80)), px)
        for j in range(3):
            cv.ell(px - 40 + j * 40, BAL_F - 210 + (j % 2) * 30, 12, 12, ((230, 60, 90), (250, 200, 60),
                                                                          (240, 120, 40))[j] + (255,))
    cv.rect(780, 1120, 940, 1140, (240, 240, 236, 255), INK, 2)                         # a plastic chair
    cv.poly([(790, 1120), (930, 1120), (940, 960), (780, 960)], (240, 240, 236, 255), INK, 2)
    for lx in (790, 920):
        cv.poly([(lx, 1140), (lx + 16, 1140), (lx + 10 + (lx - 850) * 0.1, BAL_F), (lx - 4 + (lx - 850) * 0.1, BAL_F)],
                (230, 230, 226, 255), INK, 1)
    _floor_tiles(cv, (540, 820), BAL_F, (214, 196, 170), (200, 180, 154), step=120, grow=1.24,
                 grout=(170, 150, 124, 255))
    _shadow(cv, 860, BAL_F + 4, 90, 10)
    light.poly([(500, 60), (1100, 60), (1100, 1900), (300, 1900)], (255, 236, 190, 30))
    light.blur(30)
    del rnd
    return cv, light


def _balcony_life(k):
    """fn: the AC's fan turning, the wind chime swaying, two pigeons on the railing bobbing."""
    x0, y0, x1, y1 = AC
    cx, cy = (x0 + x1) / 2 - 16, (y0 + y1) / 2

    def fn(_im, t):
        cv = Cv(k, fill=(60, 60, 64, 0))
        for i in range(3):
            a = t * 9.0 + i * 2.094
            cv.line([(cx, cy), (cx + 34 * math.cos(a), cy + 34 * math.sin(a))], (120, 120, 126, 255), 7)
        cv.ell(cx, cy, 7, 7, (90, 90, 96, 255))
        sw = math.sin(t * 1.6) * 0.18
        hx, hy = CHIME
        cv.ell(hx, hy + 6, 30, 8, (200, 170, 90, 255), INK, 1)
        for j in range(5):
            dx = (j - 2) * 12
            cv.line([(hx + dx, hy + 10), (hx + dx + 150 * math.sin(sw + j * 0.05), hy + 10 + 150 * math.cos(sw))],
                    (190, 194, 200, 255), 3)
        for (px, ph) in ((560, 0.0), (630, 1.3)):
            bob = max(0.0, math.sin(t * 2.3 + ph)) ** 6 * 14
            cv.ell(px, 984, 26, 16, (150, 156, 170, 255), INK, 1)
            cv.ell(px + 22, 966 + bob, 11, 10, (130, 136, 150, 255), INK, 1)
            cv.poly([(px + 32, 966 + bob), (px + 42, 970 + bob), (px + 32, 972 + bob)], (230, 170, 60, 255))
            cv.poly([(px - 26, 982), (px - 46, 976), (px - 26, 992)], (120, 126, 140, 255))
            cv.line([(px - 4, 998), (px - 4, 1002)], (220, 120, 100, 255), 3)
        return cv.im
    return fn


def _balcony_front(k):
    cv = Cv(k, fill=(70, 130, 60, 0), blend=True)
    _leaves(cv, 16, 860, 1160, 1700, 1990, 60, ((50, 120, 50), (130, 180, 80)), 307)
    cv.blur(9)
    return cv


def balcony_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    sky = day_sky(0.5 * s, sun=(900, 300), seed=309)
    far = skyline(0.5 * s, seed=311, tops=(420, 700), base=1300)
    mid = rooftops(0.6 * s, board=None, seed=313)
    st, light = _balcony(kr, kg)
    fg = _balcony_front(0.5 * s)
    back = [
        Layer(sky.im, 0.5 * s, 0.0, None, "sky"),
        Layer(far.im, 0.5 * s, 0.15, None, "far"),
        Layer(mid.im, 0.6 * s, 0.45, None, "mid"),
        Layer(st.im, kr, 1.0, None, "set"),
        Layer(light.im, kg, 1.0, None, "sunlight", mode="screen"),
        Layer(_blank(0.5 * s), 0.5 * s, 1.0, _balcony_life(0.5 * s), "life"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return _layered(back, front, {"ambient": [255, 250, 240], "dir": 1, "vignette": 0.22}, 820, BAL_F)


# ------------------------------------------------------------------ bathroom
SHOWER = (700, 520)


def _bathroom(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(240, 250, 255, 0))
    fill_tex(cv, [(0, 0), (LW, 0), (LW, F), (0, F)], [(0, (226, 240, 248)), (F, (210, 228, 240))], seed=321, cell=40,
             lo=0.97, hi=1.03)
    for x in range(0, LW, 60):
        cv.line([(x, 0), (x, F)], (190, 210, 222, 255), 2)
    for y in range(0, F, 60):
        cv.line([(0, y), (LW, y)], (190, 210, 222, 255), 2)
    cv.rect(0, 880, LW, 900, (90, 140, 190, 255))                                       # a band of dark tiles
    cv.rect(80, 200, 300, 360, (236, 244, 248, 255), INK, 3)                            # frosted window
    cv.line([(190, 200), (190, 360)], INK, 3)
    light.glow(190, 280, 200, (255, 252, 240), 80)
    light.poly([(80, 360), (300, 360), (560, F), (200, F)], (255, 252, 240, 30))
    cv.line([(760, 0), (760, 470), (720, 500)], (190, 194, 200, 255), 12)               # the shower
    cv.ell(SHOWER[0], SHOWER[1], 46, 18, (200, 204, 210, 255), INK, 3)
    cv.rect(740, 780, 780, 840, (200, 204, 210, 255), INK, 2)                           # its mixer
    cv.line([(760, 780), (760, 470)], (190, 194, 200, 255), 8)
    cv.rect(380, 330, 620, 560, (230, 236, 240, 255), INK, 3)                           # mirror cabinet
    cv.rect(396, 346, 604, 544, (196, 220, 232, 255), INK, 2)
    cv.poly([(420, 540), (480, 350), (510, 350), (450, 540)], (255, 255, 255, 90))
    cv.poly([(400, 760), (600, 760), (580, 830), (420, 830)], (250, 250, 250, 255), INK, 3)   # basin
    cv.rect(480, 830, 520, F - 6, (244, 244, 244, 255), INK, 2)
    cv.line([(500, 760), (500, 720), (530, 720)], (190, 194, 200, 255), 7)
    cv.rect(560, 726, 586, 760, (90, 170, 220, 255), INK, 1)                            # toothbrush cup
    cv.line([(566, 726), (560, 690)], (230, 60, 60, 255), 4)
    cv.line([(578, 726), (586, 692)], (60, 160, 90, 255), 4)
    cv.rect(860, 260, 1020, 500, (246, 246, 244, 255), INK, 3)                          # the geyser
    cv.ell(940, 260, 80, 16, (250, 250, 248, 255), INK, 2)
    cv.ell(980, 460, 9, 9, (200, 30, 30, 255), INK, 1)
    light.glow(980, 460, 30, (255, 60, 60), 120)
    cv.line([(900, 500), (900, 620)], (190, 194, 200, 255), 7)
    cv.rect(860, 640, 1040, 652, (190, 194, 200, 255), INK, 2)                          # towel rail + towel
    cv.poly([(880, 646), (1020, 646), (1014, 860), (886, 860)], (240, 150, 170, 255), INK, 2)
    cv.line([(886, 820), (1014, 820)], (250, 250, 250, 255), 5)
    cv.poly([(640, F - 4), (780, F - 4), (796, 1150), (624, 1150)], (40, 120, 210, 255), INK, 3)   # bucket
    cv.ell(710, 1150, 86, 16, (30, 100, 190, 255), INK, 2)
    cv.ell(710, 1150, 70, 11, (170, 210, 236, 255))
    cv.rect(760, 1110, 812, 1150, (220, 50, 50, 255), INK, 2)                           # the red mug
    cv.line([(812, 1120), (830, 1124), (826, 1142), (812, 1142)], (220, 50, 50, 255), 5)
    cv.rect(840, 1220, 980, F - 6, (200, 140, 90, 255), INK, 2)                         # a patla
    _floor_tiles(cv, VP, F, (200, 214, 222), (186, 200, 210), step=90, grow=1.2, grout=(160, 176, 186, 255))
    light.blur(10)
    return cv, light


def _drips(k):
    """fn: drops falling from the shower head."""
    rnd = random.Random(323)
    drops = [(rnd.uniform(-30, 30), rnd.uniform(0, 1), rnd.uniform(0.8, 1.2)) for _ in range(7)]

    def fn(_im, t):
        cv = Cv(k, fill=(170, 210, 240, 0))
        for (dx, ph, sp) in drops:
            u = (t * 0.9 * sp + ph) % 1.0
            y = SHOWER[1] + 20 + u * (F - SHOWER[1] - 40)
            cv.ell(SHOWER[0] + dx, y, 3, 7, (160, 210, 245, 220))
        return cv.im
    return fn


def _bathroom_front(k):
    cv = Cv(k, fill=(240, 150, 170, 0), blend=True)
    cv.poly([(-40, -40), (140, -40), (120, 700), (-40, 720)], (240, 150, 170, 255))      # a towel hanging
    cv.ell(980, 1880, 130, 50, (40, 120, 210, 255))                                       # a slipper
    cv.blur(9)
    return cv


def bathroom_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    st, light = _bathroom(kr, kg)
    fg = _bathroom_front(0.5 * s)
    back = [
        Layer(st.im, kr, 1.0, None, "set"),
        Layer(light.im, kg, 1.0, None, "lights", mode="screen"),
        Layer(_blank(0.4 * s), 0.4 * s, 1.0, _drips(0.4 * s), "drips"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return _layered(back, front, {"ambient": [246, 252, 255], "dir": -1, "vignette": 0.22}, VP[1], F)


# ------------------------------------------------------------------ hostel room
LAPTOP = (720, 900, 860, 990)
MAGGI = (960, 990)


def _hostel(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(255, 236, 190, 0))
    _room_shell(cv, F, (214, 224, 202), (204, 214, 190))
    _window(cv, light, ((560, 1380), (860, 1380), (1000, 1640), (600, 1640)), 700, 380, 1000, 760, bars_v=4)
    _curtain(cv, 950, 1040, 350, 820, (60, 90, 150), 1)
    for i, (x, y, col) in enumerate(((520, 330, (220, 70, 60)), (590, 420, (60, 110, 200)), (530, 560, (240, 200, 60)))):
        cv.rect(x, y, x + 110, y + 140, col + (255,), INK, 3)                           # posters
        cv.ell(x + 55, y + 60, 30, 30, (250, 250, 246, 255), INK, 2)
        cv.ell(x + 55, y + 60, 12, 12, mul(col, 0.7) + (255,))
    pts = catenary(30, 250, 690, 250, 40)                                               # towels on a line
    cv.line(pts, (60, 50, 50, 255), 2)
    for i, (cx, cy) in enumerate(along(pts, 150)[1:-1]):
        cv.poly([(cx - 40, cy), (cx + 40, cy), (cx + 36, cy + 120), (cx - 36, cy + 120)],
                ((240, 150, 60), (90, 170, 200), (240, 240, 236), (200, 80, 120))[i % 4] + (255,), INK, 2)
    # the bunk bed
    for px in (40, 460):
        cv.rect(px, 340, px + 20, F, (150, 156, 166, 255), INK, 2)
    for (y, blanket) in ((520, (200, 60, 60)), (980, (60, 90, 160))):
        cv.rect(40, y + 60, 480, y + 76, (150, 156, 166, 255), INK, 2)
        cv.rect(60, y, 460, y + 60, (90, 120, 190, 255), INK, 2)                        # the mattress
        cv.ell(130, y - 6, 60, 22, (250, 250, 246, 255), INK, 2)                        # pillow
        cv.poly([(220, y - 4), (300, y - 30), (380, y - 10), (450, y - 20), (460, y + 30), (220, y + 34)],
                blanket + (255,), INK, 2)                                               # a crumpled blanket
    for y in range(600, 980, 70):                                                       # ladder
        cv.line([(440, y), (480, y)], (150, 156, 166, 255), 5)
    cv.poly([(80, 1100), (180, 1100), (190, 1220), (70, 1220)], (40, 40, 44, 255), INK, 2)   # a bag under the bed
    # the study table
    cv.rect(640, 990, 1040, 1010, (150, 104, 66, 255), INK, 3)
    for lx in (650, 1020):
        cv.rect(lx, 1010, lx + 14, F - 4, (120, 80, 50, 255), INK, 1)
    x0, y0, x1, y1 = LAPTOP
    cv.rect(x0, y0, x1, y1 - 6, (40, 40, 46, 255), INK, 2)
    cv.rect(x0 + 6, y0 + 6, x1 - 6, y1 - 14, (40, 60, 90, 255))
    cv.poly([(x0 - 14, y1 - 6), (x1 + 14, y1 - 6), (x1 + 4, y1), (x0 - 4, y1)], (170, 174, 180, 255), INK, 2)
    for i in range(4):                                                                   # books
        cv.rect(660, 970 - i * 16, 720, 986 - i * 16, ((220, 60, 60), (60, 120, 200), (240, 200, 60),
                                                       (60, 160, 90))[i] + (255,), INK, 1)
    mx, my = MAGGI                                                                       # a pot of maggi
    cv.poly([(mx - 40, my), (mx + 40, my), (mx + 34, my - 50), (mx - 34, my - 50)], (190, 194, 200, 255), INK, 2)
    cv.ell(mx, my - 50, 36, 9, (250, 210, 100, 255), INK, 1)
    for j in range(4):
        cv.line([(mx - 20 + j * 12, my - 52), (mx - 14 + j * 12, my - 44)], (240, 190, 80, 255), 3)
    cv.rect(780, 1040, 900, 1060, (60, 60, 70, 255), INK, 2)                             # chair
    cv.rect(790, 900, 890, 1040, (70, 70, 80, 255), INK, 2)
    for lx in (790, 880):
        cv.rect(lx, 1060, lx + 10, F - 6, (60, 60, 66, 255))
    _floor_tiles(cv, VP, F, (200, 196, 184), (186, 182, 170), step=110, grow=1.24, grout=(160, 156, 144, 255))
    _shadow(cv, 260, F + 4, 230, 12)
    return cv, light


def _laptop(k):
    x0, y0, x1, y1 = LAPTOP

    def fn(_im, t):
        cv = Cv(k, fill=(120, 170, 255, 0))
        n = int(t / 3.0)
        c = ((90, 140, 255), (255, 140, 120), (120, 230, 170))[n % 3]
        b = 0.75 + 0.2 * math.sin(t * 4.0)
        cv.rect(x0 + 8, y0 + 8, x1 - 8, y1 - 16, c + (int(170 * b),))
        cv.glow((x0 + x1) / 2, y0 + 40, 150, c, int(40 * b))
        return cv.im
    return fn


def _hostel_front(k):
    cv = Cv(k, fill=(170, 110, 60, 0), blend=True)
    cv.ell(1090, 1880, 130, 150, (190, 120, 60, 255))                                    # a guitar in the corner
    cv.ell(1080, 1870, 36, 36, (60, 40, 30, 255))
    cv.line([(1070, 1740), (1050, 1500)], (110, 70, 40, 255), 36)
    cv.blur(9)
    return cv


def hostel_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    outside = _room_outside(0.5 * s)
    st, light = _hostel(kr, kg)
    fg = _hostel_front(0.5 * s)
    back = [
        Layer(outside.im, 0.5 * s, 0.12, None, "outside"),
        Layer(st.im, kr, 1.0, None, "set"),
        Layer(light.im, kg, 1.0, None, "sunlight", mode="screen"),
        Layer(_blank(0.4 * s), 0.4 * s, 1.0, _laptop(0.4 * s), "laptop", mode="screen"),
        Layer(_blank(0.3 * s), 0.3 * s, 1.0, steam([(MAGGI[0], MAGGI[1] - 56, 0.6, 0.5)], 0.3 * s), "steam"),
        Layer(_blank(0.4 * s), 0.4 * s, 1.0, fan(560, 200, 0.4 * s, R=170, speed=2.4, top=76), "fan"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return _layered(back, front, {"ambient": [252, 248, 236], "dir": 1, "vignette": 0.26}, VP[1], F)


# ------------------------------------------------------------------ library
LAMP = (420, 1030)


def _books(cv, x0, x1, y0, y1, rnd):
    x = x0
    while x < x1 - 8:
        w = rnd.uniform(14, 26)
        h = (y1 - y0) * rnd.uniform(0.7, 0.96)
        col = rnd.choice(((150, 40, 40), (40, 80, 140), (60, 120, 70), (200, 150, 50), (110, 60, 120), (200, 90, 50),
                          (230, 220, 200), (40, 40, 44)))
        if rnd.random() < 0.08:                                                          # a book leaning
            cv.poly([(x, y1), (x + w, y1), (x + w + h * 0.3, y1 - h), (x + h * 0.3, y1 - h)], col + (255,), INK, 1)
            x += w + h * 0.3
            continue
        cv.rect(x, y1 - h, min(x + w, x1), y1, col + (255,), INK, 1)
        cv.line([(x + 3, y1 - h * 0.8), (x + w - 3, y1 - h * 0.8)], (230, 200, 120, 255), 2)
        x += w + 1


def _library(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(255, 230, 170, 0))
    rnd = random.Random(331)
    _room_shell(cv, F, (230, 214, 186), (220, 202, 172))
    quad_image(cv, sign_image("SILENCE", (250, 250, 246), (200, 40, 40), 600, 150), [(410, 110), (670, 110),
                                                                                    (670, 176), (410, 176)])
    for (x0, x1) in ((30, 340), (380, 700), (740, 1050)):                               # the book cases
        cv.rect(x0, 210, x1, F, (110, 70, 40, 255), INK, 3)
        cv.rect(x0 + 14, 224, x1 - 14, F - 14, (70, 44, 26, 255))
        for y in range(380, F, 170):
            _books(cv, x0 + 18, x1 - 18, y - 150, y, rnd)
            cv.rect(x0 + 10, y, x1 - 10, y + 14, (140, 92, 54, 255), INK, 2)
    cv.line([(250, F), (370, 300)], (150, 104, 66, 255), 10)                            # a ladder
    cv.line([(320, F), (440, 300)], (150, 104, 66, 255), 10)
    for i in range(1, 9):
        u = i / 9.0
        cv.line([(250 + 120 * u, F - (F - 300) * u), (320 + 120 * u, F - (F - 300) * u)], (150, 104, 66, 255), 6)
    cv.rect(220, 1090, 860, 1110, (120, 76, 44, 255), INK, 3)                           # reading table
    for lx in (240, 830):
        cv.rect(lx, 1110, lx + 16, F - 4, (100, 64, 36, 255), INK, 1)
    lx, ly = LAMP                                                                        # the green lamp
    cv.rect(lx - 6, ly, lx + 6, 1090, (200, 170, 80, 255))
    cv.poly([(lx - 60, ly), (lx + 60, ly), (lx + 40, ly - 34), (lx - 40, ly - 34)], (30, 120, 70, 255), INK, 2)
    cv.ell(lx, 1088, 30, 8, (200, 170, 80, 255), INK, 1)
    light.glow(lx, ly + 20, 260, (255, 220, 140), 90)
    for (bx, col) in ((560, (250, 248, 236)), (700, (250, 248, 236))):                  # open books
        cv.poly([(bx - 60, 1090), (bx, 1080), (bx + 60, 1090), (bx + 56, 1072), (bx, 1064), (bx - 56, 1072)],
                col + (255,), INK, 1)
    _floor_tiles(cv, VP, F, (150, 104, 66), (136, 92, 58), step=150, grow=1.2, grout=(110, 72, 44, 255))
    _shadow(cv, 540, F + 4, 330, 14)
    light.blur(10)
    return cv, light


def _library_front(k):
    cv = Cv(k, fill=(150, 40, 40, 0), blend=True)
    for i, col in enumerate(((150, 40, 40), (40, 80, 140), (200, 150, 50), (60, 120, 70))):
        cv.rect(-40 + i * 6, 1700 + i * 60, 300 - i * 8, 1760 + i * 60, col + (255,))
    cv.blur(9)
    return cv


def library_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    st, light = _library(kr, kg)
    fg = _library_front(0.5 * s)
    back = [
        Layer(st.im, kr, 1.0, None, "set"),
        Layer(light.im, kg, 1.0, None, "lamp", mode="screen"),
        Layer(_blank(0.3 * s), 0.3 * s, 1.0, motes(((420, 900), (520, 1300), 300), 0.3 * s, n=40), "lamp dust",
              mode="screen"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return _layered(back, front, {"ambient": [255, 244, 222], "dir": -1, "vignette": 0.34}, VP[1], F)


# ------------------------------------------------------------------ coaching
CO_F = 1260


def _bench_row(cv, y, n, w, gap, col=(150, 100, 60)):
    x = (LW - (n * w + (n - 1) * gap)) / 2.0
    for i in range(n):
        bx = x + i * (w + gap)
        cv.rect(bx, y - 70, bx + w, y - 56, mul(col, 1.1) + (255,), INK, 2)              # desk top
        cv.rect(bx + 6, y - 56, bx + w - 6, y - 20, col + (255,), INK, 2)
        cv.rect(bx, y - 20, bx + w, y - 10, mul(col, 0.9) + (255,), INK, 1)               # seat
        for lx in (bx + 8, bx + w - 14):
            cv.rect(lx, y - 10, lx + 6, y, (90, 90, 96, 255))


def _coaching(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(250, 252, 255, 0))
    _room_shell(cv, CO_F, (238, 234, 218), (228, 222, 204), dado=(960, (176, 196, 214), (160, 182, 202),
                                                                  (110, 130, 160)))
    _tube_light(cv, light, 400, 680, 84)
    quad_image(cv, sign_image("TOPPERS ACADEMY", (40, 80, 170), (255, 255, 255), 1100, 160),
               [(320, 120), (760, 120), (760, 180), (320, 180)])
    quad_image(cv, board_image(["PHYSICS", "F = m x a", "E = m c²", "v = u + at", "s = ut + ½at²"], (250, 250, 248),
                               (30, 50, 120), w=900, h=520, border=(150, 156, 166), title_col=(200, 40, 40)),
               [(150, 220), (880, 220), (880, 640), (150, 640)])
    cv.rect(150, 640, 880, 656, (170, 174, 180, 255), INK, 2)                           # its marker tray
    for i, col in enumerate(((200, 40, 40), (30, 50, 160), (40, 140, 60))):
        cv.rect(300 + i * 50, 628, 336 + i * 50, 640, col + (255,))
    cv.rect(910, 240, 1060, 620, (250, 246, 230, 255), INK, 3)                          # OUR TOPPERS
    quad_image(cv, sign_image("TOPPERS", (200, 40, 40), (255, 255, 255), 500, 140), [(920, 250), (1050, 250),
                                                                                    (1050, 290), (920, 290)])
    for i in range(3):
        cy = 350 + i * 95
        cv.ell(985, cy, 30, 34, (220, 180, 140, 255), INK, 2)
        cv.poly([(955, cy - 10), (985, cy - 40), (1015, cy - 10)], (40, 30, 30, 255))
        cv.poly([(950, cy + 30), (1020, cy + 30), (1010, cy + 52), (960, cy + 52)], (240, 200, 60, 255), INK, 1)
    _bench_row(cv, 1120, 4, 170, 50)
    _bench_row(cv, 1230, 3, 230, 70)
    _floor_tiles(cv, VP, CO_F, (210, 196, 170), (196, 182, 156), step=120, grow=1.24, grout=(170, 156, 130, 255))
    light.blur(8)
    return cv, light


def _coaching_front(k):
    cv = Cv(k, fill=(150, 100, 60, 0), blend=True)
    cv.rect(-40, 1820, 1120, 1860, (160, 108, 66, 255))                                   # a bench in front
    cv.poly([(600, 1820), (820, 1810), (830, 1830), (610, 1840)], (250, 250, 246, 255))    # a notebook
    cv.blur(9)
    return cv


def coaching_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    st, light = _coaching(kr, kg)
    fg = _coaching_front(0.5 * s)
    back = [
        Layer(st.im, kr, 1.0, None, "set"),
        Layer(light.im, kg, 1.0, None, "lights", mode="screen"),
        Layer(_blank(0.4 * s), 0.4 * s, 1.0, fan(170, 170, 0.4 * s, R=120, speed=2.0, top=76), "fan"),
        Layer(_blank(0.4 * s), 0.4 * s, 1.0, fan(930, 170, 0.4 * s, R=120, speed=1.8, top=76), "fan2"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return _layered(back, front, {"ambient": [250, 250, 246], "dir": 1, "vignette": 0.24}, VP[1], CO_F)


# ------------------------------------------------------------------ exam hall
EX_F = 1150
EX_CLOCK = (960, 230, 50)


def _exam(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(255, 236, 190, 0))
    _room_shell(cv, EX_F, (242, 228, 190), (232, 216, 176), dado=(860, (200, 180, 140), (186, 166, 126),
                                                                  (140, 120, 90)))
    _window(cv, light, ((200, 1180), (420, 1180), (700, 1500), (300, 1500)), 40, 300, 220, 760, bars_v=2, bars_h=3)
    cv.rect(260, 160, 820, 480, (120, 76, 44, 255), INK, 4)                             # the board
    quad_image(cv, board_image(["EXAM", "Time: 3 hrs"], (40, 90, 66), (240, 240, 230), w=700, h=380,
                               border=(40, 90, 66), title_col=(250, 250, 240)), [(276, 176), (804, 176), (804, 464),
                                                                                (276, 464)])
    cx, cy, r = EX_CLOCK
    _clock(cv, cx, cy, r)
    rows = ((1170, 5, 120, 60), (1240, 4, 160, 80), (1330, 4, 200, 60))
    fill_tex(cv, [(0, EX_F), (LW, EX_F), (LW, LH), (0, LH)], [(EX_F, (196, 172, 130)), (LH, (176, 150, 110))],
             seed=341, cell=24, lo=0.92, hi=1.06)
    for y in (1200, 1290, 1420, 1600, 1820):
        cv.line([(0, y), (LW, y)], (160, 136, 100, 200), 2)
    cv.line([(0, EX_F), (LW, EX_F)], INK, 2)
    for (y, n, w, gap) in rows:                                                         # desks with papers
        x = (LW - (n * w + (n - 1) * gap)) / 2.0
        for i in range(n):
            bx = x + i * (w + gap)
            hh = w * 0.42
            cv.rect(bx, y - hh, bx + w, y - hh + 12, (170, 116, 70, 255), INK, 2)
            cv.poly([(bx + w * 0.25, y - hh), (bx + w * 0.7, y - hh - 4), (bx + w * 0.72, y - hh + 6),
                     (bx + w * 0.27, y - hh + 10)], (250, 250, 246, 255), INK, 1)
            for lx in (bx + 8, bx + w - 14):
                cv.rect(lx, y - hh + 12, lx + 6, y, (90, 90, 96, 255))
            _shadow(cv, bx + w / 2, y + 2, w * 0.5, 6, 50)
    return cv, light


def _exam_front(k):
    cv = Cv(k, fill=(170, 116, 70, 0), blend=True)
    cv.poly([(-60, 1780), (1140, 1760), (1140, 1960), (-60, 1960)], (170, 116, 70, 255))   # a desk in front
    cv.poly([(300, 1770), (620, 1760), (640, 1840), (300, 1850)], (250, 250, 246, 255))    # the question paper
    cv.line([(700, 1800), (860, 1760)], (30, 60, 160, 255), 10)                           # a pen
    cv.blur(9)
    return cv


def exam_hall_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    outside = _class_outside(0.5 * s)
    st, light = _exam(kr, kg)
    fg = _exam_front(0.5 * s)
    cx, cy, r = EX_CLOCK
    back = [
        Layer(outside.im, 0.5 * s, 0.12, None, "outside"),
        Layer(st.im, kr, 1.0, None, "set"),
        Layer(light.im, kg, 1.0, None, "sunlight", mode="screen"),
        Layer(_blank(0.5 * s), 0.5 * s, 1.0, _second_hand(0.5 * s, cx, cy, r * 0.88), "clock"),
        Layer(_blank(0.4 * s), 0.4 * s, 1.0, fan(300, 120, 0.4 * s, R=140, speed=1.6, top=76), "fan"),
        Layer(_blank(0.4 * s), 0.4 * s, 1.0, fan(860, 120, 0.4 * s, R=140, speed=1.4, top=76), "fan2"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return _layered(back, front, {"ambient": [255, 248, 230], "dir": -1, "vignette": 0.26}, VP[1], EX_F)


# ------------------------------------------------------------------ gym
TREAD = (740, 1170, 1060, 1260)


def _gym(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(240, 246, 255, 0))
    _room_shell(cv, F, (196, 202, 210), (184, 190, 198), dado=(880, (90, 96, 106), (76, 82, 92), (200, 40, 40)))
    _tube_light(cv, light, 140, 400, 96)
    _tube_light(cv, light, 700, 960, 96)
    quad_image(cv, sign_image("GYM", (210, 40, 40), (255, 255, 255), 400, 160), [(440, 110), (640, 110), (640, 180),
                                                                              (440, 180)])
    quad_image(cv, board_image(["NO PAIN", "NO GAIN"], (30, 30, 34), (250, 210, 40), w=500, h=300,
                               title_col=(250, 210, 40), border=(250, 210, 40)), [(760, 220), (1040, 220),
                                                                                 (1040, 400), (760, 400)])
    cv.rect(50, 220, 710, 860, (90, 96, 106, 255), INK, 3)                              # the mirror wall
    cv.rect(64, 234, 696, 846, (190, 210, 222, 255))
    cv.rect(64, 640, 696, 846, (150, 160, 170, 200))
    for (a, b) in ((80, 150), (240, 280)):
        cv.poly([(64 + a, 846), (64 + a + 200, 234), (64 + b + 200, 234), (64 + b, 846)], (255, 255, 255, 60))
    cv.rect(60, 960, 600, 980, (60, 62, 70, 255), INK, 2)                               # dumbbell rack
    cv.rect(60, 1040, 600, 1060, (60, 62, 70, 255), INK, 2)
    for lx in (70, 580):
        cv.rect(lx, 980, lx + 14, F - 4, (60, 62, 70, 255))
    for i in range(8):
        x = 90 + i * 64
        for (y, sz) in ((950, 10 + i), (1030, 12 + i)):
            cv.rect(x, y - 4, x + 40, y + 4, (150, 150, 156, 255))
            cv.rect(x - 4, y - sz, x + 6, y + sz, (40, 40, 44, 255), INK, 1)
            cv.rect(x + 34, y - sz, x + 44, y + sz, (40, 40, 44, 255), INK, 1)
    for (x, r) in ((640, 34), (700, 28)):                                               # kettlebells
        cv.ell(x, F - 30, r, r, (40, 40, 44, 255), INK, 2)
        cv.ell(x, F - 30 - r - 6, r * 0.6, r * 0.5, None, (40, 40, 44, 255), 8)
    x0, y0, x1, y1 = TREAD                                                              # the treadmill
    cv.poly([(x0, y1), (x1, y1), (x1 - 20, y0), (x0 + 30, y0)], (50, 52, 58, 255), INK, 3)
    cv.line([(x0 + 40, y0), (x0 + 70, 900)], (70, 72, 80, 255), 12)
    cv.line([(x0 + 260, y0), (x0 + 230, 900)], (70, 72, 80, 255), 12)
    cv.rect(x0 + 40, 860, x0 + 260, 920, (40, 40, 46, 255), INK, 2)
    cv.rect(x0 + 70, 872, x0 + 230, 908, (40, 100, 160, 255))
    cv.line([(x0 + 40, 960), (x0 + 260, 960)], (70, 72, 80, 255), 8)
    fill_tex(cv, [(0, F), (LW, F), (LW, LH), (0, LH)], [(F, (60, 62, 70)), (LH, (44, 46, 52))], seed=351, cell=8,
             lo=0.9, hi=1.1)
    for y in (1360, 1480, 1640, 1860):
        cv.line([(0, y), (LW, y)], (36, 38, 44, 255), 3)
    for x in range(-900, 2000, 180):
        cv.line([(VP[0] + (x - VP[0]), F), (VP[0] + (x - VP[0]) * (LH - VP[1]) / float(F - VP[1]), LH)],
                (36, 38, 44, 255), 3)
    light.blur(8)
    return cv, light


def _treadmill(k):
    x0, y0, x1, y1 = TREAD

    def fn(_im, t):
        cv = Cv(k, fill=(40, 40, 46, 0))
        cv.poly([(x0 + 40, y0 + 20), (x1 - 30, y0 + 20), (x1 - 20, y1 - 16), (x0 + 30, y1 - 16)], (30, 30, 34, 255))
        off = (t * 120.0) % 40.0
        for i in range(9):
            x = x0 + 40 + i * 40 - off
            if x0 + 36 < x < x1 - 30:
                cv.line([(x, y0 + 22), (x - 6, y1 - 18)], (70, 70, 78, 255), 3)
        n = int(t) % 10
        cv.rect(x0 + 80, 878, x0 + 80 + 14 * n, 900, (90, 220, 140, 220))
        return cv.im
    return fn


def _gym_front(k):
    cv = Cv(k, fill=(40, 40, 44, 0), blend=True)
    cv.rect(-40, 1840, 260, 1870, (150, 150, 156, 255))                                   # a dumbbell
    cv.rect(-40, 1760, 40, 1950, (40, 40, 44, 255))
    cv.rect(200, 1760, 280, 1950, (40, 40, 44, 255))
    cv.blur(9)
    return cv


def gym_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    st, light = _gym(kr, kg)
    fg = _gym_front(0.5 * s)
    back = [
        Layer(st.im, kr, 1.0, None, "set"),
        Layer(light.im, kg, 1.0, None, "lights", mode="screen"),
        Layer(_blank(0.5 * s), 0.5 * s, 1.0, _treadmill(0.5 * s), "treadmill"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return _layered(back, front, {"ambient": [246, 250, 255], "dir": 1, "vignette": 0.26}, VP[1], F)


# ------------------------------------------------------------------ birthday party
CANDLES = [(690, 930), (730, 924), (770, 930)]


def _party(k, kg):
    cv = Cv(k, blend=True)
    gA = Cv(kg, fill=(255, 190, 110, 0))
    gB = Cv(kg, fill=(255, 190, 110, 0))
    gS = Cv(kg, fill=(255, 210, 160, 0))
    _room_shell(cv, F, (246, 222, 238), (236, 206, 226))
    quad_image(cv, sign_image("HAPPY BIRTHDAY", (240, 100, 160), (255, 255, 255), 1200, 200),
               [(270, 190), (810, 190), (810, 280), (270, 280)])
    for (y0, sag, seed) in ((330, 60, 1), (420, 70, 2)):                                 # streamers + bulbs
        pts = catenary(-20, y0, 1100, y0, sag)
        cv.line(pts, (80, 60, 80, 255), 2)
        for i, (bx, by) in enumerate(along(pts, 40)):
            if seed == 1:
                cv.poly([(bx - 14, by), (bx + 14, by), (bx, by + 34)], PAL_BULB[i % len(PAL_BULB)] + (255,))
            else:
                (gA if i % 2 else gB).ell(bx, by + 8, 6, 6, PAL_BULB[i % len(PAL_BULB)] + (250,))
                gS.ell(bx, by + 8, 16, 16, PAL_BULB[i % len(PAL_BULB)] + (40,))
    cv.rect(580, 1060, 900, 1080, (250, 250, 250, 255), INK, 2)                         # the table and its cloth
    for x in range(580, 900, 32):
        cv.ell(x + 16, 1086, 16, 10, (250, 250, 250, 255))
    for lx in (600, 870):
        cv.rect(lx, 1090, lx + 14, F - 4, (150, 100, 60, 255), INK, 1)
    cv.rect(650, 990, 810, 1060, (240, 140, 180, 255), INK, 3)                          # the cake
    cv.rect(670, 940, 790, 990, (250, 240, 246, 255), INK, 3)
    for x in range(656, 810, 22):
        cv.ell(x, 992, 9, 7, (250, 250, 250, 255))
    for (x, y) in CANDLES:
        cv.rect(x - 4, y, x + 4, 942, ((80, 160, 240), (250, 200, 60), (240, 90, 130))[CANDLES.index((x, y))]
                + (255,), INK, 1)
    for (x, w, h, col) in ((900, 120, 100, (60, 140, 220)), (960, 80, 80, (240, 200, 60)), (860, 70, 60,
                                                                                         (220, 60, 90))):
        cv.rect(x, F - h, x + w, F, col + (255,), INK, 2)                               # gifts
        cv.rect(x + w / 2 - 6, F - h, x + w / 2 + 6, F, (250, 250, 250, 255))
        cv.ell(x + w / 2, F - h - 6, 16, 8, (250, 250, 250, 255), INK, 1)
    _floor_tiles(cv, VP, F, (210, 180, 150), (196, 166, 136), step=130, grow=1.22, grout=(170, 140, 110, 255))
    for b in (gA, gB):
        b.blur(1.0)
    gS.blur(12)
    return cv, gA, gB, gS


def _party_life(k):
    """fn: balloons bobbing on their strings, the candles' flames flickering."""
    rnd = random.Random(361)
    bunches = []
    for (bx, by) in ((120, 1100), (990, 1060)):
        for _ in range(4):
            bunches.append((bx, by, rnd.uniform(-70, 70), rnd.uniform(-420, -260), rnd.choice(PAL_BULB),
                            rnd.uniform(0, 6.28)))

    def fn(_im, t):
        cv = Cv(k, fill=(240, 120, 160, 0))
        for (bx, by, dx, dy, col, ph) in bunches:
            x = bx + dx + math.sin(t * 1.2 + ph) * 10
            y = by + dy + math.cos(t * 1.0 + ph) * 8
            cv.line([(bx, by), (x, y + 44)], (120, 120, 126, 255), 2)
            cv.ell(x, y, 40, 48, mix(col, (240, 80, 120), 0.3) + (255,), INK, 2)
            cv.ell(x - 14, y - 16, 9, 13, (255, 255, 255, 150))
        for i, (x, y) in enumerate(CANDLES):
            f = 1.0 + 0.25 * math.sin(t * 13 + i * 2) + 0.1 * math.sin(t * 31 + i)
            cv.ell(x + math.sin(t * 9 + i) * 2, y - 12 * f, 6, 12 * f, (255, 200, 60, 255))
            cv.ell(x, y - 8 * f, 3, 6 * f, (255, 250, 220, 255))
        return cv.im
    return fn


def _disco(k):
    """fn (screen): coloured disco spots running over the walls and the floor."""
    rnd = random.Random(363)
    spots = [(rnd.uniform(0, 6.28), rnd.uniform(0.3, 0.7), rnd.choice(PAL_BULB)) for _ in range(7)]

    def fn(_im, t):
        cv = Cv(k, fill=(255, 150, 200, 0))
        for (ph, sp, col) in spots:
            x = 540 + 460 * math.sin(t * sp + ph)
            y = 900 + 500 * math.sin(t * sp * 0.7 + ph * 2)
            cv.ell(x, y, 46, 30, col + (60,))
        cv.blur(8)
        return cv.im
    return fn


def _party_front(k):
    cv = Cv(k, fill=(240, 120, 160, 0), blend=True)
    rnd = random.Random(367)
    cv.ell(60, 160, 120, 140, (240, 90, 140, 255))
    for _ in range(26):
        x, y = rnd.uniform(0, LW), rnd.uniform(1600, 1960)
        cv.rect(x, y, x + 16, y + 10, rnd.choice(PAL_BULB) + (255,))
    cv.blur(8)
    return cv


def party_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    st, gA, gB, gS = _party(kr, kg)
    fg = _party_front(0.5 * s)
    back = [
        Layer(st.im, kr, 1.0, None, "set"),
        Layer(gA.im, kg, 1.0, twinkle((gA.im, gB.im), 0.9, static=gS.im), "bulbs", mode="screen"),
        Layer(_blank(0.3 * s), 0.3 * s, 1.0, _disco(0.3 * s), "disco", mode="screen"),
        Layer(_blank(0.5 * s), 0.5 * s, 1.0, _party_life(0.5 * s), "balloons"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return _layered(back, front, {"ambient": [255, 240, 246], "dir": 1, "vignette": 0.26}, VP[1], F)


# ------------------------------------------------------------------ jail
J_F = 1280
BULB = (930, 260)


def _jail(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(255, 240, 200, 0))
    rnd = random.Random(371)
    fill_tex(cv, [(0, 0), (LW, 0), (LW, 860), (0, 860)], [(0, (176, 170, 150)), (860, (168, 160, 140))], seed=373,
             cell=40, lo=0.9, hi=1.07)
    fill_tex(cv, [(0, 860), (LW, 860), (LW, J_F), (0, J_F)], [(860, (96, 110, 124)), (J_F, (84, 96, 110))], seed=374,
             cell=30, lo=0.92, hi=1.06)
    cv.line([(0, 860), (LW, 860)], INK, 4)
    for _ in range(10):                                                                  # damp stains
        x, y, r = rnd.uniform(40, 760), rnd.uniform(120, 820), rnd.uniform(24, 70)
        cv.ell(x, y, r, r * 0.8, (150, 144, 120, 90))
    _window(cv, light, ((330, 1360), (650, 1360), (760, 1640), (300, 1640)), 360, 300, 660, 520, bars_v=6,
            bars_h=1, frame=(90, 90, 96), sill=False)
    cv.rect(40, 1060, 430, 1110, (150, 150, 146, 255), INK, 4)                          # the concrete bench
    cv.rect(40, 1110, 430, J_F, (120, 120, 118, 255), INK, 4)
    cv.poly([(80, 1060), (200, 1060), (190, 1040), (90, 1040)], (110, 100, 80, 255), INK, 2)   # a thin blanket
    cv.rect(60, 760, 250, 780, (110, 80, 54, 255), INK, 3)                              # shelf: mug and plate
    cv.rect(90, 700, 140, 760, (196, 198, 206, 255), INK, 3)
    cv.line([(140, 716), (156, 716), (156, 744), (140, 744)], INK, 3)
    cv.ell(205, 752, 38, 8, (196, 198, 206, 255), INK, 2)
    for i in range(4):                                                                   # days scratched in
        for j in range(4):
            x = 470 + i * 70 + j * 12
            cv.line([(x, 640), (x, 700)], (120, 112, 96, 255), 4)
        cv.line([(462 + i * 70, 690), (512 + i * 70, 650)], (120, 112, 96, 255), 4)
    # the corridor behind the cell door (the door itself is the jail_door set piece, drawn over it)
    fill_tex(cv, [(780, 180), (LW, 180), (LW, 1290), (780, 1290)], [(180, (70, 72, 80)), (1290, (54, 56, 62))],
             seed=375, cell=30, lo=0.9, hi=1.08)
    cv.line([(BULB[0], 180), (BULB[0], BULB[1] - 16)], (40, 40, 44, 255), 3)
    cv.ell(BULB[0], BULB[1], 14, 16, (255, 240, 190, 255), INK, 1)
    for x in range(800, LW + 40, 56):                                                    # its bars (as in 2D)
        cv.line([(x, 180), (x, 1290)], (150, 152, 160, 255), 16)
        cv.line([(x - 4, 180), (x - 4, 1290)], (200, 202, 210, 255), 4)
    for y in (220, 740, 1240):
        cv.line([(780, y), (LW, y)], (150, 152, 160, 255), 18)
    cv.rect(820, 700, 880, 790, (120, 100, 60, 255), INK, 4)
    fill_tex(cv, [(0, J_F), (LW, J_F), (LW, LH), (0, LH)], [(J_F, (140, 140, 136)), (LH, (120, 120, 116))], seed=376,
             cell=20, lo=0.9, hi=1.08)
    for (ax, ay, bx, by) in ((120, 1400, 260, 1460), (260, 1460, 300, 1560), (700, 1360, 820, 1420)):
        cv.line([(ax, ay), (bx, by)], (110, 110, 108, 255), 3)
    cv.line([(0, J_F), (LW, J_F)], INK, 4)
    return cv, light


def _jail_bulb(k):
    """fn (screen): the corridor's bulb, flickering now and then."""
    def fn(_im, t):
        cv = Cv(k, fill=(255, 230, 170, 0))
        ph = t % 7.0
        f = 0.25 if (5.0 < ph < 5.12 or 5.3 < ph < 5.38) else 1.0
        cv.glow(BULB[0], BULB[1], 200, (255, 226, 160), int(70 * f))
        cv.poly([(BULB[0] - 20, BULB[1]), (BULB[0] + 20, BULB[1]), (BULB[0] + 150, 1290), (BULB[0] - 150, 1290)],
                (255, 226, 160, int(26 * f)))
        cv.blur(6)
        return cv.im
    return fn


def _jail_front(k):
    cv = Cv(k, fill=(170, 170, 176, 0), blend=True)
    cv.ell(960, 1860, 150, 40, (170, 172, 178, 255))                                      # a tin plate
    cv.ell(960, 1856, 110, 26, (150, 152, 158, 255))
    cv.blur(9)
    return cv


def jail_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    outside = _room_outside(0.5 * s)
    st, light = _jail(kr, kg)
    fg = _jail_front(0.5 * s)
    back = [
        Layer(outside.im, 0.5 * s, 0.12, None, "outside"),
        Layer(st.im, kr, 1.0, None, "set"),
        Layer(light.im, kg, 1.0, None, "sunlight", mode="screen"),
        Layer(_blank(0.3 * s), 0.3 * s, 1.0, motes(((510, 520), (560, 1300), 240), 0.3 * s), "dust", mode="screen"),
        Layer(_blank(0.4 * s), 0.4 * s, 1.0, _jail_bulb(0.4 * s), "bulb", mode="screen"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return _layered(back, front, {"ambient": [236, 236, 230], "dir": -1, "vignette": 0.36}, VP[1], J_F)

"""More procedural locations. Each function takes the output scale s and returns an RGB image
(drawn with backgrounds.G in logical 1080x1920 coordinates). Characters stand around y = 1700,
so floors start around y = 1250-1350."""
import math
import random

from PIL import Image, ImageDraw

from .backgrounds import G, INK, _floor_perspective, _light_patch
from .text import font
from .util import LH, LW

WOOD, WOOD_D = (176, 124, 78), (130, 90, 56)


# ------------------------------------------------------------------ helpers
def _txt(g, x, y, text, size, fill=INK):
    f = font(size * g.k)
    g.d.text((x * g.k, y * g.k), text, font=f, fill=fill, anchor="mm")


def _sign(g, x0, y0, x1, y1, text, bg=(250, 210, 70), fg=INK, size=None, w=6):
    g.rect(x0, y0, x1, y1, bg, INK, w)
    size = size or min((y1 - y0) * 0.6, (x1 - x0) / max(3, len(text)) * 1.35)
    _txt(g, (x0 + x1) / 2, (y0 + y1) / 2 + 2, text, size, fg)


def _wall_floor(g, wall, floor, y_floor, kind="wood", line=None, skirting=None):
    g.rect(0, 0, LW, y_floor, wall)
    if skirting:
        g.rect(0, y_floor - 40, LW, y_floor, skirting)
    if kind == "tile":
        _floor_perspective(g, y_floor, floor, line or tuple(max(0, c - 30) for c in floor))
    else:
        g.rect(0, y_floor, LW, LH, floor)
        lc = line or tuple(max(0, c - 28) for c in floor)
        if kind == "wood":
            for i in range(8):
                y = y_floor + i * i * 14 + 20
                g.line([(0, y), (LW, y)], lc, 3)
        elif kind == "carpet":
            for i in range(0, LW, 90):
                g.line([(i, y_floor), (i - 60, LH)], tuple(min(255, c + 8) for c in floor), 2)
    g.line([(0, y_floor), (LW, y_floor)], INK, 5)


def _sky(g, top, bottom, y1=1300):
    with g.on("sky"):
        g.vgrad(0, y1, top, bottom)


def _window(g, x0, y0, x1, y1, view="day"):
    g.rect(x0, y0, x1, y1, (250, 250, 248), INK, 8)
    g.punch(x0 + 16, y0 + 16, x1 - 16, y1 - 16)        # 2.5D: the view outside is its own (far) layer
    with g.on("window"):
        sky = {"day": (170, 214, 238), "night": (28, 32, 66), "city": (160, 200, 230)}[view]
        g.rect(x0 + 16, y0 + 16, x1 - 16, y1 - 16, sky)
        if view == "city":
            rnd = random.Random(int(x0))
            x = x0 + 16
            while x < x1 - 20:
                w = rnd.randint(40, 80)
                h = rnd.randint(int((y1 - y0) * 0.3), int((y1 - y0) * 0.75))
                g.rect(x, y1 - 16 - h, min(x + w, x1 - 16), y1 - 16, (120, 140, 170))
                x += w + 4
        elif view == "day":
            g.poly([(x0 + 16, y1 - 80), ((x0 + x1) / 2, y1 - 160), (x1 - 16, y1 - 90), (x1 - 16, y1 - 16),
                    (x0 + 16, y1 - 16)], (150, 200, 150))
        else:
            g.circle(x1 - 70, y0 + 80, 26, (250, 244, 210))
    g.note_window(x0 + 16, y0 + 16, x1 - 16, y1 - 16)
    g.line([((x0 + x1) / 2, y0 + 16), ((x0 + x1) / 2, y1 - 16)], INK, 6)
    g.line([(x0 + 16, (y0 + y1) / 2), (x1 - 16, (y0 + y1) / 2)], INK, 6)


def _books(g, x0, x1, y_base, h=90, seed=1):
    rnd = random.Random(seed)
    cols = [(200, 70, 64), (70, 110, 180), (230, 190, 70), (90, 160, 100), (150, 100, 180), (220, 130, 60)]
    x = x0
    while x < x1 - 14:
        w = rnd.randint(16, 30)
        hh = h - rnd.randint(0, 24)
        g.rect(x, y_base - hh, min(x + w, x1), y_base, cols[rnd.randint(0, 5)], INK, 2)
        x += w + 1


def _shelf(g, x0, y0, x1, y1, rows=4, item="books", seed=2, col=WOOD_D):
    g.rect(x0, y0, x1, y1, col, INK, 6)
    g.rect(x0 + 14, y0 + 14, x1 - 14, y1 - 14, tuple(max(0, c - 30) for c in col))
    step = (y1 - y0 - 28) / rows
    rnd = random.Random(seed)
    for r in range(rows):
        yb = y0 + 14 + (r + 1) * step
        g.rect(x0 + 14, yb - 8, x1 - 14, yb, col)
        if item == "books":
            _books(g, x0 + 20, x1 - 20, yb - 8, step - 16, seed + r)
        else:  # grocery packets / jars
            x = x0 + 22
            while x < x1 - 50:
                w = rnd.randint(34, 56)
                hh = rnd.randint(int(step * 0.4), int(step * 0.8))
                c = rnd.choice([(230, 90, 70), (250, 200, 70), (90, 150, 210), (110, 180, 110), (240, 240, 230)])
                if rnd.random() < 0.35:
                    g.rrect(x, yb - 8 - hh, x + w, yb - 8, 10, (236, 230, 210), INK, 3)
                    g.rect(x + 4, yb - 8 - hh - 10, x + w - 4, yb - 8 - hh, (150, 150, 150), INK, 2)
                else:
                    g.rect(x, yb - 8 - hh, x + w, yb - 8, c, INK, 3)
                x += w + 6


def _string_lights(g, x0, x1, y, sag=60, n=14, seed=4):
    pts = [(x0 + (x1 - x0) * i / 30, y + sag * math.sin(math.pi * i / 30)) for i in range(31)]
    g.line(pts, (40, 40, 40), 3)
    rnd = random.Random(seed)
    cols = [(250, 90, 80), (250, 210, 70), (90, 200, 120), (90, 160, 250), (240, 120, 220)]
    for i in range(n):
        u = (i + 0.5) / n
        x = x0 + (x1 - x0) * u
        yy = y + sag * math.sin(math.pi * u)
        c = cols[rnd.randint(0, 4)]
        g.circle(x, yy + 12, 10, c, INK, 2)
        g.note_light(x, yy + 12, 10, c)


def _garland(g, x0, x1, y, sag=50, col=(246, 150, 40)):
    for i in range(41):
        u = i / 40
        x = x0 + (x1 - x0) * u
        yy = y + sag * math.sin(math.pi * u)
        g.circle(x, yy, 13, col if i % 2 else (250, 200, 60))


def _buildings(g, y_base, seed=7, h=(400, 800), cols=None, windows=True, night=False):
    with g.on("far"):                               # 2.5D: the skyline is a far layer (moves slower than the ground)
        _buildings_draw(g, y_base, seed, h, cols, windows, night)


def _buildings_draw(g, y_base, seed, h, cols, windows, night):
    rnd = random.Random(seed)
    cols = cols or [(210, 150, 120), (170, 190, 200), (222, 190, 120), (170, 150, 190), (150, 190, 160)]
    x = -20
    while x < LW:
        w = rnd.randint(170, 280)
        hh = rnd.randint(*h)
        c = cols[rnd.randint(0, len(cols) - 1)]
        g.rect(x, y_base - hh, x + w, y_base, c, INK, 5)
        if windows:
            for wy in range(y_base - hh + 36, y_base - 60, 100):
                for wx in range(x + 26, x + w - 44, 64):
                    lit = rnd.random() < (0.55 if night else 0.35)
                    g.rect(wx, wy, wx + 34, wy + 56, (250, 226, 140) if lit else (140, 175, 205), INK, 2)
        x += w + 6


def _tree(g, x, y, r=120, trunk=(110, 80, 54), leaf=(96, 168, 92)):
    g.rect(x - 14, y - r * 3, x + 14, y, trunk, INK, 5)
    g.circle(x, y - r * 3.2, r, leaf, INK, 6)


def _crowd(g, x0, x1, y0, y1, seed=9):
    rnd = random.Random(seed)
    cols = [(220, 90, 80), (80, 120, 200), (240, 200, 80), (90, 170, 110), (230, 230, 230), (160, 100, 180)]
    for row, y in enumerate(range(int(y0), int(y1), 46)):
        for x in range(int(x0) + (row % 2) * 20, int(x1), 40):
            g.circle(x, y, 14, rnd.choice(cols))
            g.circle(x, y - 22, 11, (235, 210, 180))


# ------------------------------------------------------------------ desi everyday
def chai_tapri(s):
    g = G(s)
    _sky(g, (150, 205, 240), (236, 240, 244), 1250)
    _buildings(g, 1250, seed=11, h=(300, 650))
    g.rect(0, 1250, LW, LH, (214, 196, 160))
    g.line([(0, 1250), (LW, 1250)], INK, 5)
    for x in range(0, LW, 140):
        g.line([(x, 1400), (x + 60, 1404)], (190, 172, 138), 4)
    # stall
    g.rect(80, 760, 96, 1300, (90, 90, 96), INK, 3)
    g.rect(760, 760, 776, 1300, (90, 90, 96), INK, 3)
    for i in range(8):
        c = (232, 110, 60) if i % 2 == 0 else (250, 240, 220)
        g.poly([(40 + i * 100, 700), (140 + i * 100, 700), (140 + i * 100, 780), (40 + i * 100, 800)], c, INK, 4)
    _sign(g, 240, 590, 620, 690, "CHAI", (250, 210, 70), (160, 40, 30))
    g.rect(110, 1010, 740, 1300, (150, 104, 66), INK, 6)
    g.rect(100, 990, 750, 1020, (110, 80, 50), INK, 5)
    g.rect(160, 1060, 690, 1270, (176, 124, 78))
    g.line([(160, 1160), (690, 1160)], WOOD_D, 4)
    # stove + kettle + glasses
    g.rect(170, 940, 330, 990, (60, 60, 66), INK, 4)
    g.rrect(190, 850, 300, 945, 20, (190, 190, 196), INK, 5)
    g.line([(300, 880), (350, 860)], INK, 8)
    g.line([(200, 850), (186, 830)], INK, 6)
    for i in range(6):
        x = 420 + i * 48
        g.poly([(x, 950), (x + 30, 950), (x + 26, 990), (x + 4, 990)], (236, 240, 240), INK, 3)
        g.poly([(x + 3, 962), (x + 27, 962), (x + 25, 988), (x + 5, 988)], (178, 112, 62))
    g.rect(820, 1130, 1060, 1170, WOOD, INK, 5)      # bench
    g.rect(840, 1170, 856, 1300, WOOD_D, INK, 3)
    g.rect(1024, 1170, 1040, 1300, WOOD_D, INK, 3)
    return g.done()


def gully(s):
    g = G(s)
    _sky(g, (150, 205, 240), (230, 238, 244), 700)
    vp = (540, 820)
    g.poly([(0, 0), (360, 360), (360, 1180), (0, 1500)], (226, 170, 120), INK, 6)
    g.poly([(LW, 0), (720, 360), (720, 1180), (LW, 1500)], (150, 190, 200), INK, 6)
    g.rect(360, 360, 720, 1180, (236, 220, 180), INK, 5)
    g.rect(470, 920, 610, 1180, (120, 80, 50), INK, 4)
    for (x0, y0, x1, y1) in [(60, 360, 220, 560), (60, 760, 220, 960), (860, 360, 1020, 560), (860, 760, 1020, 960)]:
        g.rect(x0, y0, x1, y1, (110, 150, 190), INK, 5)
    g.poly([(0, 1500), (360, 1180), (720, 1180), (LW, 1500), (LW, LH), (0, LH)], (176, 170, 160))
    for i in range(6):
        y = 1180 + i * i * 22 + 20
        g.line([(0, y), (LW, y)], (150, 144, 134), 3)
    g.line([(0, 300), (LW, 380)], INK, 3)
    g.line([(0, 330), (LW, 300)], INK, 2)
    for i, c in enumerate([(230, 90, 80), (90, 140, 220), (250, 210, 70)]):     # clothesline
        x = 420 + i * 80
        g.poly([(x, 520), (x + 60, 520), (x + 54, 610), (x + 6, 610)], c, INK, 3)
    g.line([(360, 516), (720, 516)], INK, 3)
    return g.done()


def kirana(s):
    g = G(s)
    _wall_floor(g, (238, 226, 196), (190, 170, 140), 1300, "tile")
    g.rect(0, 380, LW, 470, (60, 70, 90), INK, 6)
    for x in range(0, LW, 24):
        g.line([(x, 380), (x, 470)], (80, 90, 110), 2)
    _sign(g, 160, 260, 920, 370, "KIRANA STORE", (220, 60, 60), (255, 255, 255))
    _shelf(g, 60, 500, 1020, 1060, rows=4, item="grocery", seed=21, col=(150, 104, 66))
    g.rect(120, 1080, 960, 1300, (176, 124, 78), INK, 6)
    g.rect(100, 1060, 980, 1096, (130, 90, 56), INK, 5)
    for i in range(4):
        x = 200 + i * 170
        g.rrect(x, 970, x + 90, 1062, 14, (236, 236, 230), INK, 4)
        g.rect(x + 10, 950, x + 80, 972, (200, 60, 60), INK, 3)
        g.circle(x + 45, 1022, 26, [(250, 200, 60), (230, 120, 80), (140, 90, 60), (250, 250, 250)][i])
    g.rect(820, 960, 940, 1060, (60, 60, 66), INK, 4)
    return g.done()


def market(s):
    g = G(s)
    _sky(g, (150, 205, 240), (236, 240, 244), 1200)
    _buildings(g, 1200, seed=31, h=(250, 520))
    g.rect(0, 1200, LW, LH, (190, 176, 150))
    g.line([(0, 1200), (LW, 1200)], INK, 5)
    rnd = random.Random(5)
    for i, x in enumerate((30, 380, 730)):
        c = [(236, 110, 60), (60, 140, 200), (230, 70, 110)][i]
        g.poly([(x - 20, 860), (x + 340, 860), (x + 300, 760), (x + 20, 760)], c, INK, 5)
        g.line([(x + 160, 860), (x + 160, 1230)], INK, 8)
        g.rect(x, 1080, x + 320, 1200, (176, 124, 78), INK, 5)
        g.rect(x + 20, 1200, x + 40, 1270, WOOD_D, INK, 3)
        g.rect(x + 280, 1200, x + 300, 1270, WOOD_D, INK, 3)
        veg = [(220, 50, 50), (250, 150, 40), (100, 170, 70), (150, 70, 140), (250, 220, 80)]
        for j in range(20):
            vx, vy = x + 30 + (j % 10) * 28, 1060 - (j // 10) * 26 + rnd.randint(-4, 4)
            g.circle(vx, vy, 15, veg[(i * 2 + j) % 5], INK, 2)
    return g.done()


def bus_stop(s):
    g = G(s)
    _sky(g, (150, 205, 240), (236, 240, 244), 1240)
    _buildings(g, 1240, seed=41, h=(380, 760))
    g.rect(0, 1240, LW, 1380, (206, 202, 192))
    g.line([(0, 1240), (LW, 1240)], INK, 5)
    g.rect(0, 1380, LW, LH, (92, 94, 100))
    g.line([(0, 1380), (LW, 1380)], INK, 6)
    for xx in range(-40, LW, 220):
        g.rect(xx, 1700, xx + 120, 1718, (240, 220, 120))
    g.rect(120, 760, 860, 800, (70, 120, 170), INK, 6)
    g.rect(140, 800, 160, 1250, (120, 120, 126), INK, 3)
    g.rect(820, 800, 840, 1250, (120, 120, 126), INK, 3)
    g.rect(170, 820, 810, 1060, (190, 220, 235), INK, 4)
    g.rect(220, 1110, 760, 1140, WOOD, INK, 4)
    g.rect(960, 680, 976, 1250, (110, 110, 116), INK, 3)
    g.circle(968, 660, 60, (60, 140, 220), INK, 6)
    _txt(g, 968, 662, "BUS", 40, (255, 255, 255))
    return g.done()


def railway(s):
    g = G(s)
    _sky(g, (176, 210, 236), (236, 240, 244), 700)
    g.rect(0, 340, LW, 400, (120, 70, 50), INK, 5)
    for x in range(60, LW, 260):
        g.rect(x, 400, x + 28, 1000, (150, 110, 80), INK, 4)
    _sign(g, 330, 440, 750, 540, "STATION", (250, 210, 70))
    g.circle(540, 640, 54, (255, 255, 255), INK, 6)
    g.line([(540, 640), (540, 606)], INK, 5)
    g.line([(540, 640), (566, 652)], INK, 5)
    g.rect(0, 1000, LW, 1180, (120, 110, 100))
    for x in range(0, LW, 70):
        g.rect(x, 1060, x + 40, 1170, (110, 80, 60))
    g.line([(0, 1080), (LW, 1080)], (170, 170, 176), 10)
    g.line([(0, 1150), (LW, 1150)], (170, 170, 176), 10)
    g.rect(0, 1180, LW, LH, (200, 190, 170))
    g.rect(0, 1180, LW, 1214, (250, 210, 60), INK, 5)
    g.line([(0, 1180), (LW, 1180)], INK, 6)
    for x in range(0, LW, 120):
        g.line([(x, 1214), (x - 40, LH)], (180, 170, 150), 3)
    return g.done()


def terrace(s):
    g = G(s)
    _sky(g, (120, 190, 240), (230, 240, 248), 1250)
    _buildings(g, 1150, seed=51, h=(120, 360), windows=False,
               cols=[(220, 210, 190), (200, 190, 170), (230, 220, 200)])
    for (x, y, c) in [(200, 280, (230, 60, 80)), (800, 380, (60, 140, 220)), (600, 200, (250, 200, 50))]:  # kites
        g.poly([(x, y - 50), (x + 40, y), (x, y + 60), (x - 40, y)], c, INK, 4)
        g.line([(x, y + 60), (x - 30, y + 160), (x + 10, y + 260)], INK, 2)
    g.rect(760, 820, 1000, 1150, (60, 60, 64), INK, 6)
    g.rect(740, 800, 1020, 830, (80, 80, 86), INK, 5)
    g.rect(0, 1150, LW, 1260, (214, 206, 190), INK, 6)
    g.rect(0, 1260, LW, LH, (196, 188, 172))
    g.line([(0, 1260), (LW, 1260)], INK, 5)
    g.line([(60, 980), (700, 1010)], INK, 3)
    for i, c in enumerate([(230, 90, 80), (90, 140, 220), (250, 210, 70), (120, 190, 120)]):
        x = 110 + i * 140
        g.poly([(x, 988 + i * 2), (x + 90, 990 + i * 2), (x + 80, 1110), (x + 10, 1110)], c, INK, 3)
    return g.done()


def balcony(s):
    g = G(s)
    _sky(g, (150, 205, 240), (230, 238, 244), 1300)
    _buildings(g, 1240, seed=61, h=(500, 1000))
    g.rect(0, 0, 360, 1300, (230, 216, 190), INK, 6)
    g.rect(80, 520, 300, 1300, (150, 104, 66), INK, 6)
    g.circle(270, 920, 12, (230, 200, 90))
    g.rect(0, 1300, LW, LH, (200, 180, 160))
    g.line([(0, 1300), (LW, 1300)], INK, 5)
    g.rect(360, 1060, LW, 1090, (70, 70, 76), INK, 5)
    for x in range(380, LW, 46):
        g.line([(x, 1090), (x, 1300)], (70, 70, 76), 8)
    for x in (420, 900):
        g.poly([(x, 1010), (x + 80, 1010), (x + 66, 1060), (x + 14, 1060)], (190, 104, 70), INK, 4)
        g.circle(x + 40, 980, 40, (90, 160, 84), INK, 4)
    return g.done()


def bedroom(s):
    g = G(s, color=(214, 222, 236))
    _wall_floor(g, (214, 222, 236), (176, 140, 110), 1290, "wood", skirting=(196, 204, 220))
    _window(g, 640, 420, 960, 860, "day")
    g.rect(60, 580, 420, 1290, (130, 96, 70), INK, 6)
    g.line([(240, 580), (240, 1290)], INK, 5)
    g.rect(200, 900, 216, 980, (230, 200, 90))
    g.rect(264, 900, 280, 980, (230, 200, 90))
    g.rect(560, 960, 1080, 1180, (110, 150, 210), INK, 5)      # bed headboard area (wall)
    g.rect(600, 1000, 1040, 1050, (250, 250, 248), INK, 4)
    return g.done()


def bathroom(s):
    g = G(s, color=(220, 236, 244))
    g.rect(0, 0, LW, 1320, (220, 236, 244))
    for x in range(0, LW, 70):
        g.line([(x, 0), (x, 1320)], (190, 212, 224), 3)
    for y in range(0, 1320, 70):
        g.line([(0, y), (LW, y)], (190, 212, 224), 3)
    _floor_perspective(g, 1320, (200, 220, 226), (170, 192, 200))
    g.line([(0, 1320), (LW, 1320)], INK, 5)
    g.rect(640, 420, 920, 760, (200, 230, 245), INK, 8)              # mirror
    g.line([(680, 480), (760, 440)], (250, 250, 255), 6)
    g.poly([(650, 900), (910, 900), (880, 980), (680, 980)], (250, 250, 250), INK, 6)
    g.rect(760, 980, 800, 1320, (240, 240, 240), INK, 4)
    g.line([(780, 900), (780, 850), (820, 850)], (170, 170, 176), 10)
    g.line([(140, 200), (140, 560), (240, 560)], (170, 170, 176), 12)  # shower
    g.circle(250, 590, 40, (190, 190, 196), INK, 5)
    g.poly([(140, 1120), (300, 1120), (280, 1320), (160, 1320)], (70, 130, 210), INK, 5)  # bucket
    g.poly([(320, 1220), (380, 1220), (376, 1320), (324, 1320)], (230, 90, 80), INK, 4)   # mug
    return g.done()


def canteen(s):
    g = G(s, color=(240, 226, 196))
    _wall_floor(g, (240, 226, 196), (210, 200, 180), 1280, "tile")
    g.rect(80, 300, 600, 720, (40, 70, 60), INK, 8)
    _txt(g, 340, 370, "MENU", 56, (250, 250, 240))
    for i, line in enumerate(["Samosa ....... 15", "Chai .......... 10", "Maggi ........ 40", "Vada Pav ...... 20"]):
        _txt(g, 340, 450 + i * 64, line, 36, (240, 240, 230))
    g.rect(660, 820, LW, 1280, (176, 124, 78), INK, 6)
    g.rect(640, 800, LW, 836, (130, 90, 56), INK, 5)
    for i in range(3):
        x = 700 + i * 120
        g.rrect(x, 700, x + 90, 800, 12, (200, 200, 206), INK, 4)
    for (x0, x1) in ((60, 420), (480, 840)):
        g.rect(x0, 1120, x1, 1150, (200, 90, 70), INK, 5)
        g.rect(x0 + 20, 1150, x0 + 36, 1280, (110, 110, 116), INK, 3)
        g.rect(x1 - 36, 1150, x1 - 20, 1280, (110, 110, 116), INK, 3)
    return g.done()


def hostel(s):
    g = G(s, color=(206, 214, 196))
    _wall_floor(g, (206, 214, 196), (170, 160, 150), 1290, "tile")
    g.rect(40, 520, 460, 1290, None, (90, 90, 96), 10)
    for y in (760, 1120):
        g.rect(50, y, 450, y + 50, (90, 120, 170), INK, 5)
        g.rect(60, y - 20, 160, y + 4, (250, 250, 250), INK, 3)
    g.line([(470, 520), (470, 1290)], (90, 90, 96), 10)
    for i in range(5):
        g.line([(470, 600 + i * 120), (430, 600 + i * 120)], (90, 90, 96), 6)
    for (x, y, c) in [(560, 380, (230, 90, 80)), (760, 420, (80, 130, 210)), (640, 600, (250, 210, 70))]:
        g.rect(x, y, x + 160, y + 210, c, INK, 5)
        g.circle(x + 80, y + 90, 40, (250, 250, 240), INK, 3)
    g.rect(620, 1000, 1040, 1040, WOOD, INK, 5)
    g.rect(640, 1040, 656, 1290, WOOD_D, INK, 3)
    g.rect(1004, 1040, 1020, 1290, WOOD_D, INK, 3)
    g.rect(700, 920, 800, 1000, (60, 60, 66), INK, 4)
    _books(g, 840, 1010, 1000, 70, 3)
    return g.done()


def office(s):
    g = G(s, color=(226, 230, 234))
    _wall_floor(g, (226, 230, 234), (110, 120, 140), 1270, "carpet")
    g.rect(80, 300, 1000, 760, (190, 214, 236), INK, 8)
    for y in range(320, 760, 34):
        g.line([(96, y), (984, y)], (220, 230, 240), 6)
    for x0 in (40, 560):
        g.rect(x0, 900, x0 + 480, 1270, (150, 160, 176), INK, 6)
        g.rect(x0 + 80, 840, x0 + 260, 960, (40, 44, 52), INK, 5)
        g.rect(x0 + 94, 852, x0 + 246, 948, (120, 190, 235))
        g.rect(x0 + 150, 960, x0 + 190, 990, (40, 44, 52), INK, 3)
    g.poly([(990, 1180), (1060, 1180), (1050, 1270), (1000, 1270)], (190, 104, 70), INK, 4)
    for (c, d) in ((-40, -140), (0, -190), (40, -150)):
        g.line([(1025, 1180), (1025 + c, 1180 + d)], (70, 130, 70), 8)
        g.circle(1025 + c, 1170 + d, 24, (90, 160, 84), INK, 3)
    return g.done()


def meeting_room(s):
    g = G(s, color=(236, 236, 232))
    _wall_floor(g, (236, 236, 232), (130, 120, 110), 1260, "carpet")
    g.rect(220, 300, 860, 700, (250, 250, 252), INK, 8)
    for i, (h, c) in enumerate([(120, (90, 160, 230)), (200, (230, 110, 80)), (280, (110, 190, 120)), (340, (250, 200, 70))]):
        x = 320 + i * 120
        g.rect(x, 660 - h, x + 80, 660, c, INK, 4)
    g.line([(280, 660), (800, 660)], INK, 4)
    g.poly([(160, 1260), (920, 1260), (800, 1060), (280, 1060)], (150, 104, 66), INK, 6)
    for x in (300, 460, 620, 780):
        g.rrect(x - 50, 940, x + 50, 1060, 16, (40, 44, 52), INK, 4)
    return g.done()


def exam_hall(s):
    g = G(s, color=(238, 228, 196))
    _wall_floor(g, (238, 228, 196), (196, 160, 118), 1180, "wood")
    g.rect(170, 260, 910, 640, (150, 104, 66), INK, 8)
    g.rect(194, 284, 886, 616, (46, 92, 72))
    _txt(g, 540, 380, "EXAM", 90, (240, 240, 230))
    _txt(g, 540, 500, "Time: 3 hrs", 46, (220, 220, 210))
    g.circle(1000, 300, 54, (255, 255, 255), INK, 6)
    g.line([(1000, 300), (1000, 264)], INK, 5)
    g.line([(1000, 300), (1024, 314)], INK, 5)
    for row, (y, w, sc) in enumerate(((1200, 200, 0.6), (1280, 240, 0.75), (1380, 300, 0.95))):
        for i in range(-2, 3):
            x = 540 + i * w * 1.3
            g.rect(x - w / 2, y - 40 * sc, x + w / 2, y, (176, 124, 78), INK, 4)
            g.rect(x - w / 2 + 10, y, x - w / 2 + 22, y + 60 * sc, (110, 110, 116), INK, 2)
            g.rect(x + w / 2 - 22, y, x + w / 2 - 10, y + 60 * sc, (110, 110, 116), INK, 2)
    return g.done()


def library(s):
    g = G(s, color=(226, 214, 190))
    _wall_floor(g, (226, 214, 190), (150, 110, 80), 1290, "wood")
    for i, x in enumerate((20, 380, 740)):
        _shelf(g, x, 260, x + 320, 1290, rows=6, item="books", seed=70 + i)
    _sign(g, 360, 140, 720, 230, "SILENCE", (250, 250, 248), (200, 40, 40))
    return g.done()


def coaching(s):
    g = G(s, color=(232, 230, 214))
    _wall_floor(g, (232, 230, 214), (190, 170, 140), 1290, "tile")
    g.rect(100, 300, 980, 800, (250, 250, 252), INK, 8)
    for i, line in enumerate(["F = m x a", "E = m c²", "x = (-b ± √(b²-4ac)) / 2a", "v = u + at"]):
        _txt(g, 540, 380 + i * 100, line, 52, (40, 70, 160))
    _sign(g, 330, 180, 750, 270, "TOPPERS ACADEMY", (60, 120, 200), (255, 255, 255))
    for (x0, x1) in ((80, 360), (400, 680), (720, 1000)):
        g.rect(x0, 1160, x1, 1200, (160, 110, 68), INK, 6)
        g.rect(x0 + 20, 1200, x0 + 36, 1290, (110, 110, 116), INK, 3)
        g.rect(x1 - 36, 1200, x1 - 20, 1290, (110, 110, 116), INK, 3)
    return g.done()


# ------------------------------------------------------------------ events
def mandap(s):
    g = G(s, color=(120, 30, 40))
    g.vgrad(0, 1280, (120, 26, 40), (180, 50, 50))
    for x in range(0, LW, 120):                         # drapes
        g.poly([(x, 0), (x + 120, 0), (x + 90, 1280), (x + 30, 1280)], (200, 50, 60) if (x // 120) % 2 else (230, 170, 60))
    g.rect(0, 1280, LW, LH, (190, 60, 50))
    g.line([(0, 1280), (LW, 1280)], INK, 5)
    for x in (120, 960):
        g.rect(x - 24, 380, x + 24, 1290, (236, 190, 70), INK, 5)
    g.poly([(60, 380), (1020, 380), (900, 260), (180, 260)], (236, 120, 40), INK, 6)
    for i in range(4):
        _garland(g, 120, 960, 420 + i * 70, 50 + i * 10)
    for x in range(100, 1000, 70):
        g.line([(x, 260), (x, 340)], (250, 160, 40), 6)
        g.circle(x, 352, 14, (250, 200, 60))
    g.rect(420, 1160, 660, 1290, (200, 110, 50), INK, 6)    # havan kund
    g.poly([(470, 1160), (500, 1080), (540, 1120), (570, 1060), (610, 1160)], (250, 150, 40), INK, 4)
    return g.done()


def party(s):
    g = G(s, color=(236, 220, 240))
    _wall_floor(g, (236, 220, 240), (200, 170, 150), 1290, "wood")
    _sign(g, 160, 230, 920, 350, "HAPPY BIRTHDAY", (250, 120, 160), (255, 255, 255))
    for i in range(3):
        _string_lights(g, 0, LW, 400 + i * 40, 60, 12, 30 + i)
    rnd = random.Random(8)
    for x, y in ((90, 700), (180, 640), (950, 680), (1020, 760), (860, 620)):
        c = rnd.choice([(230, 70, 90), (80, 140, 230), (250, 210, 70), (110, 200, 120)])
        g.line([(x, y + 60), (x + 10, 1000)], (90, 90, 90), 2)
        g.ellipse(x - 44, y - 56, x + 44, y + 60, c, INK, 4)
    g.rect(340, 1050, 740, 1090, (250, 250, 248), INK, 5)
    g.rect(360, 1090, 380, 1290, WOOD_D, INK, 3)
    g.rect(700, 1090, 720, 1290, WOOD_D, INK, 3)
    g.rect(450, 940, 630, 1050, (250, 220, 230), INK, 5)
    g.rect(450, 940, 630, 970, (230, 100, 140), INK, 4)
    for x in (490, 540, 590):
        g.rect(x - 5, 890, x + 5, 940, (120, 170, 230), INK, 2)
        g.poly([(x - 6, 890), (x + 6, 890), (x, 872)], (250, 200, 60))
    return g.done()


def festival_street(s):
    g = G(s)
    _sky(g, (24, 20, 60), (90, 50, 110), 1240)
    _buildings(g, 1240, seed=81, h=(420, 820), night=True,
               cols=[(110, 80, 110), (90, 90, 130), (130, 90, 90), (80, 110, 120)])
    for i in range(4):
        _string_lights(g, -40, LW + 40, 300 + i * 160, 70, 16, 90 + i)
    g.rect(0, 1240, LW, LH, (90, 80, 90))
    g.line([(0, 1240), (LW, 1240)], INK, 5)
    for x in range(80, LW, 180):                            # diyas
        g.poly([(x - 30, 1260), (x + 30, 1260), (x + 20, 1282), (x - 20, 1282)], (200, 110, 50), INK, 3)
        g.poly([(x - 6, 1258), (x, 1230), (x + 6, 1258)], (255, 210, 80))
    for x in (160, 920):                                    # lanterns
        g.line([(x, 0), (x, 200)], INK, 3)
        g.rrect(x - 40, 200, x + 40, 300, 20, (240, 80, 60), INK, 4)
    return g.done()


def cricket_ground(s):
    g = G(s)
    _sky(g, (130, 196, 240), (230, 240, 248), 760)
    g.rect(0, 560, LW, 780, (200, 200, 206), INK, 5)
    _crowd(g, 20, LW, 600, 760, 3)
    g.rect(0, 780, LW, LH, (100, 170, 80))
    g.line([(0, 780), (LW, 780)], INK, 5)
    for i in range(8):
        g.rect(0, 800 + i * 140, LW, 870 + i * 140, (110, 180, 90))
    g.poly([(470, 900), (610, 900), (700, LH), (380, LH)], (210, 180, 120))
    g.line([(0, 820), (LW, 820)], (250, 250, 250), 6)
    for x in (520, 540, 560):
        g.rect(x - 4, 860, x + 4, 960, (250, 240, 220), INK, 2)
    g.line([(512, 862), (568, 862)], INK, 4)
    return g.done()


def gym(s):
    g = G(s, color=(200, 206, 214))
    _wall_floor(g, (200, 206, 214), (60, 62, 70), 1280, "carpet")
    g.rect(60, 280, 1020, 820, (190, 214, 230), INK, 8)
    g.line([(140, 340), (300, 300)], (230, 240, 248), 8)
    _sign(g, 400, 170, 680, 250, "GYM", (230, 60, 60), (255, 255, 255))
    g.rect(80, 1000, 520, 1030, (90, 90, 96), INK, 5)
    for i in range(6):
        x = 110 + i * 68
        g.line([(x, 980), (x + 40, 980)], (120, 120, 126), 6)
        g.rect(x - 8, 962, x + 4, 998, (40, 40, 44))
        g.rect(x + 36, 962, x + 48, 998, (40, 40, 44))
    g.rect(100, 1030, 116, 1280, (90, 90, 96), INK, 3)
    g.rect(484, 1030, 500, 1280, (90, 90, 96), INK, 3)
    g.poly([(640, 1280), (1020, 1280), (1000, 1200), (660, 1200)], (40, 40, 44), INK, 5)   # treadmill
    g.line([(980, 1200), (960, 900)], (90, 90, 96), 10)
    g.rect(900, 860, 1010, 920, (60, 60, 66), INK, 4)
    return g.done()


# ------------------------------------------------------------------ mood scenes
def jungle(s):
    g = G(s)
    with g.on("sky"):
        g.vgrad(0, 1300, (90, 150, 120), (150, 190, 140))
    rnd = random.Random(12)
    for layer, (col, tr) in enumerate((((60, 110, 80), (70, 60, 50)), ((44, 94, 60), (60, 50, 40)), ((30, 76, 46), (50, 40, 34)))):
        with g.on(("far", "mid", "set")[layer]):          # 2.5D: three rows of trees at three depths
            for i in range(7):
                x = rnd.randint(-60, LW + 60)
                w = 26 + layer * 14
                g.rect(x - w / 2, 200 + layer * 80, x + w / 2, 1320, tr)
                for j in range(3):
                    g.circle(x + rnd.randint(-120, 120), 180 + layer * 90 + rnd.randint(-60, 160), 120 + layer * 20,
                             col)
    for x in range(0, LW, 90):                            # vines
        g.line([(x, 0), (x + 20, 200 + (x * 37) % 300)], (40, 100, 50), 5)
    g.rect(0, 1300, LW, LH, (70, 90, 50))
    g.line([(0, 1300), (LW, 1300)], INK, 5)
    for x in range(-40, LW, 130):                         # undergrowth
        g.circle(x, 1300, 80, (40, 90, 50), INK, 4)
    layer = Image.new("RGBA", g.im.size, (255, 250, 200, 0))
    d = ImageDraw.Draw(layer)
    for x in (260, 620, 880):                             # light rays
        d.polygon([(x * g.k, 0), ((x + 60) * g.k, 0), ((x + 260) * g.k, 1300 * g.k), ((x + 120) * g.k, 1300 * g.k)],
                  fill=(255, 250, 200, 36))
    g.overlay(layer)
    return g.done()


def haunted_house(s):
    g = G(s)
    with g.on("sky"):
        g.vgrad(0, 1300, (20, 14, 40), (70, 40, 90))
        g.circle(820, 280, 110, (240, 236, 200))
    with g.on("far"):
        for (x, y) in ((200, 300), (300, 260), (700, 420)):       # bats
            g.poly([(x - 40, y), (x - 14, y - 16), (x, y - 4), (x + 14, y - 16), (x + 40, y), (x, y + 10)],
                   (20, 16, 30))
    g.poly([(240, 1300), (240, 640), (480, 420), (720, 640), (720, 1300)], (50, 40, 60), INK, 6)
    g.poly([(200, 660), (480, 380), (760, 660)], (36, 28, 46), INK, 6)
    g.rect(420, 520, 540, 620, (250, 220, 120), INK, 5)       # glowing attic window
    g.line([(480, 520), (480, 620)], INK, 5)
    for (x0, y0) in ((300, 760), (580, 760)):
        g.rect(x0, y0, x0 + 90, y0 + 130, (30, 26, 36), INK, 5)
        g.line([(x0, y0), (x0 + 90, y0 + 130)], (60, 50, 70), 4)
    g.rect(430, 1080, 530, 1300, (30, 24, 30), INK, 5)
    for x in (80, 960):                                       # dead trees
        g.line([(x, 1300), (x + 10, 800)], (30, 24, 30), 22)
        g.line([(x + 6, 950), (x - 80, 860)], (30, 24, 30), 12)
        g.line([(x + 8, 880), (x + 90, 790)], (30, 24, 30), 12)
    g.rect(0, 1300, LW, LH, (44, 40, 50))
    g.line([(0, 1300), (LW, 1300)], INK, 5)
    return g.done()


def graveyard(s):
    g = G(s)
    with g.on("sky"):
        g.vgrad(0, 1260, (30, 30, 60), (90, 90, 120))
        g.circle(220, 300, 100, (240, 236, 210))
    g.rect(0, 1260, LW, LH, (60, 76, 60))
    g.line([(0, 1260), (LW, 1260)], INK, 5)
    for x in range(0, LW, 60):
        g.line([(x, 1260), (x, 1080)], (40, 40, 46), 6)
        g.poly([(x - 8, 1080), (x, 1060), (x + 8, 1080)], (40, 40, 46))
    g.line([(0, 1110), (LW, 1110)], (40, 40, 46), 6)
    for (x, y, w) in ((180, 1360, 110), (520, 1330, 100), (860, 1370, 120), (340, 1250, 80), (700, 1240, 80)):
        g.rect(x - w / 2, y - w * 1.3, x + w / 2, y, (150, 150, 160), INK, 5)
        g.ellipse(x - w / 2, y - w * 1.3 - w / 2, x + w / 2, y - w * 1.3 + w / 2, (150, 150, 160), INK, 5)
        g.rect(x - w / 2 + 6, y - w * 1.3, x + w / 2 - 6, y - w * 1.3 + 10, (150, 150, 160))
        g.line([(x - w / 4, y - w * 0.9), (x + w / 4, y - w * 0.9)], (110, 110, 120), 4)
    g.line([(940, 1260), (950, 760)], (30, 24, 30), 20)
    g.line([(946, 900), (860, 810)], (30, 24, 30), 10)
    return g.done()


def beach(s):
    g = G(s)
    _sky(g, (110, 190, 245), (220, 238, 250), 1000)
    with g.on("sky"):
        g.circle(820, 300, 90, (255, 226, 130))
    with g.on("far"):                                         # 2.5D: the sea is far away
        g.rect(0, 1000, LW, 1260, (60, 150, 210))
        for i, y in enumerate(range(1030, 1260, 50)):
            for x in range(-60 + (i % 2) * 60, LW, 120):
                g.line([(x, y), (x + 30, y - 12), (x + 60, y)], (200, 230, 250), 4)
        g.line([(0, 1000), (LW, 1000)], INK, 4)
    g.poly([(0, 1260), (LW, 1240), (LW, LH), (0, LH)], (240, 220, 170))
    g.line([(0, 1260), (LW, 1240)], INK, 5)
    g.line([(140, 1300), (180, 760)], (150, 110, 70), 22)       # palm
    for a in (-60, -20, 20, 60, 100):
        r = math.radians(a)
        g.line([(180, 760), (180 + 200 * math.cos(r), 760 - 60 * math.sin(r) + 80)], (70, 150, 70), 18)
    g.line([(860, 1300), (880, 1000)], (90, 90, 96), 8)
    g.poly([(700, 1010), (1060, 1010), (880, 920)], (240, 90, 80), INK, 5)
    return g.done()


def mountain_road(s):
    g = G(s)
    _sky(g, (130, 190, 240), (230, 240, 248), 1100)
    with g.on("far"):                                         # 2.5D: far mountains, a nearer hillside of pines
        g.poly([(-100, 1100), (260, 520), (560, 1100)], (150, 160, 190), INK, 5)
        g.poly([(300, 1100), (700, 420), (1180, 1100)], (130, 140, 176), INK, 5)
        g.poly([(640, 470), (700, 420), (760, 470), (730, 500), (680, 490)], (250, 250, 255))
    with g.on("mid"):
        g.poly([(0, 1100), (LW, 1100), (LW, 1300), (0, 1300)], (110, 160, 90))
        for x in range(30, LW, 110):
            g.poly([(x, 1180), (x + 40, 1060), (x + 80, 1180)], (50, 110, 60), INK, 3)
    g.rect(0, 1300, LW, LH, (96, 98, 104))
    g.line([(0, 1300), (LW, 1300)], INK, 6)
    for xx in range(-40, LW, 220):
        g.rect(xx, 1700, xx + 120, 1718, (240, 220, 120))
    g.line([(0, 1270), (LW, 1270)], (200, 200, 206), 10)
    for x in range(20, LW, 120):
        g.rect(x, 1260, x + 14, 1300, (200, 200, 206), INK, 2)
    return g.done()


def desert(s):
    g = G(s)
    _sky(g, (250, 190, 110), (250, 236, 190), 1150)
    with g.on("sky"):
        g.circle(760, 360, 110, (255, 244, 180))
    with g.on("far"):                                         # 2.5D: the far dunes
        g.poly([(0, 1150), (200, 1060), (420, 1120), (700, 1020), (LW, 1130), (LW, 1300), (0, 1300)], (230, 190, 120))
    g.rect(0, 1240, LW, LH, (240, 206, 140))
    g.poly([(0, 1260), (300, 1200), (600, 1250), (LW, 1210), (LW, LH), (0, LH)], (244, 214, 150))
    g.line([(0, 1260), (300, 1200), (600, 1250), (LW, 1210)], INK, 5)
    for (x, h) in ((180, 360), (880, 280)):                  # cactus
        g.rrect(x - 26, 1240 - h, x + 26, 1250, 26, (90, 160, 80), INK, 5)
        g.rrect(x - 90, 1240 - h * 0.7, x - 50, 1240 - h * 0.35, 20, (90, 160, 80), INK, 4)
        g.rect(x - 70, 1240 - h * 0.4, x - 26, 1240 - h * 0.35 + 6, (90, 160, 80))
    return g.done()


def hospital(s):
    g = G(s, color=(214, 236, 222))
    _wall_floor(g, (214, 236, 222), (210, 214, 214), 1280, "tile", skirting=(170, 200, 182))
    for i, x in enumerate((60, 420, 780)):
        g.rect(x, 560, x + 240, 1280, (170, 200, 220), INK, 6)
        g.rect(x + 60, 620, x + 180, 760, (220, 236, 245), INK, 4)
        _sign(g, x + 40, 470, x + 200, 540, "OPD %d" % (i + 1), (250, 250, 250), (40, 120, 80), 36)
    _sign(g, 330, 220, 750, 330, "HOSPITAL", (40, 140, 90), (255, 255, 255))
    for x in range(330, 760, 110):                         # waiting chairs
        g.rect(x, 1150, x + 90, 1176, (60, 120, 190), INK, 4)
        g.rect(x, 1060, x + 90, 1150, (60, 120, 190), INK, 4)
        g.rect(x + 40, 1176, x + 50, 1280, (120, 120, 126))
    return g.done()


def police_station(s):
    g = G(s, color=(214, 206, 180))
    _wall_floor(g, (214, 206, 180), (170, 160, 140), 1280, "tile")
    _sign(g, 200, 160, 880, 270, "POLICE STATION", (40, 60, 120), (255, 255, 255))
    for i, x in enumerate((90, 260)):
        g.rect(x, 360, x + 140, 560, (250, 246, 230), INK, 5)
        _txt(g, x + 70, 390, "WANTED", 28, (180, 40, 30))
        g.circle(x + 70, 470, 46, (60, 60, 66))
    g.rect(640, 360, 1060, 1280, (90, 90, 96), INK, 6)      # lockup
    g.rect(660, 380, 1040, 1280, (60, 56, 60))
    for x in range(680, 1050, 50):
        g.line([(x, 380), (x, 1280)], (170, 170, 176), 12)
    g.line([(660, 700), (1040, 700)], (170, 170, 176), 12)
    g.rect(60, 1000, 560, 1060, (130, 90, 56), INK, 6)
    g.rect(80, 1060, 540, 1280, (150, 104, 66), INK, 6)
    g.rect(140, 940, 300, 1000, (250, 250, 248), INK, 4)
    return g.done()


def jail(s):
    """Inside a lockup: a high barred window (with a bit of sky and a tree outside), the prisoner's concrete bench,
    days scratched into the wall, and the barred cell door on the right."""
    g = G(s, color=(176, 170, 150))
    g.rect(0, 0, LW, 1280, (176, 170, 150))
    g.rect(0, 860, LW, 1280, (96, 110, 124))                   # dark painted lower wall
    g.line([(0, 860), (LW, 860)], INK, 5)
    rnd = random.Random(21)
    for _ in range(9):                                          # damp stains
        x, y = rnd.randint(40, 760), rnd.randint(120, 820)
        g.circle(x, y, rnd.randint(24, 60), (166, 160, 140))
    x0, y0, x1, y1 = 360, 300, 660, 520                        # the high window
    g.rect(x0 - 14, y0 - 14, x1 + 14, y1 + 14, (90, 90, 96), INK, 6)
    g.punch(x0, y0, x1, y1)
    with g.on("window"):
        g.rect(x0, y0, x1, y1, (170, 214, 238))
        g.circle(x0 + 210, y1 - 30, 70, (96, 160, 92))
        g.rect(x0 + 200, y1 - 30, x0 + 216, y1, (110, 80, 54))
    g.note_window(x0, y0, x1, y1)
    for x in range(x0 + 30, x1, 40):
        g.line([(x, y0), (x, y1)], (60, 60, 66), 9)
    g.line([(x0, (y0 + y1) / 2), (x1, (y0 + y1) / 2)], (60, 60, 66), 9)
    g.rect(40, 1060, 430, 1110, (150, 150, 146), INK, 5)       # concrete bench
    g.rect(40, 1110, 430, 1280, (120, 120, 118), INK, 5)
    g.rect(60, 760, 250, 780, (110, 80, 54), INK, 4)            # shelf with a steel mug and a plate
    g.rect(90, 700, 140, 760, (196, 198, 206), INK, 4)
    g.line([(140, 716), (156, 716), (156, 744), (140, 744)], INK, 4)
    g.rect(170, 744, 240, 760, (196, 198, 206), INK, 3)
    for i in range(4):                                          # days scratched into the wall
        for j in range(4):
            x = 470 + i * 70 + j * 12
            g.line([(x, 640), (x, 700)], (120, 112, 96), 4)
        g.line([(462 + i * 70, 690), (512 + i * 70, 650)], (120, 112, 96), 4)
    g.rect(780, 180, LW, 1280, (64, 66, 72))                    # the corridor behind the cell door
    for x in range(800, LW + 40, 56):
        g.line([(x, 180), (x, 1290)], (150, 152, 160), 16)
        g.line([(x - 4, 180), (x - 4, 1290)], (200, 202, 210), 4)
    for y in (220, 740, 1240):
        g.line([(780, y), (LW, y)], (150, 152, 160), 18)
    g.rect(820, 700, 880, 790, (120, 100, 60), INK, 4)          # the lock
    g.rect(0, 1280, LW, LH, (140, 140, 136))
    for (ax, ay, bx, by) in ((120, 1400, 260, 1460), (260, 1460, 300, 1560), (700, 1360, 820, 1420)):
        g.line([(ax, ay), (bx, by)], (110, 110, 108), 3)
    g.line([(0, 1280), (LW, 1280)], INK, 5)
    return g.done()


def gaon(s):
    """A village courtyard (aangan) by day: a mud house with a tiled roof and dung cakes on the wall, a washing
    line, a neem tree with a chabutra round it, a hand pump, fields and trees far away."""
    g = G(s)
    _sky(g, (128, 196, 242), (236, 240, 228), 1000)
    with g.on("sky"):
        g.circle(830, 260, 70, (255, 230, 140))
    with g.on("far"):                                           # 2.5D: the fields and a line of trees far away
        g.rect(0, 930, LW, 1240, (166, 196, 108))
        for y in range(960, 1240, 40):
            g.line([(0, y), (LW, y + 10)], (146, 176, 92), 4)
        rnd = random.Random(5)
        for x in range(-20, LW + 40, 90):
            g.circle(x + rnd.randint(-10, 10), 930 - rnd.randint(0, 30), rnd.randint(40, 70), (92, 140, 80))
        g.poly([(600, 935), (660, 880), (720, 935)], (170, 110, 80))                # a far hut
        g.rect(612, 935, 708, 990, (196, 160, 120))
    g.poly([(-30, 600), (240, 430), (520, 600)], (176, 82, 60), INK, 6)            # the house: tiled roof
    for i in range(1, 6):
        y = 600 - i * 30
        g.line([(-30 + i * 46, y), (520 - i * 46, y)], (150, 66, 50), 4)
    g.rect(0, 600, 480, 1240, (204, 160, 112), INK, 6)
    g.rect(170, 820, 320, 1240, (70, 46, 34), INK, 6)           # doorway with a curtain
    g.poly([(176, 826), (314, 826), (300, 1000), (190, 1000)], (200, 60, 70))
    g.rect(360, 700, 450, 790, (90, 70, 50), INK, 5)            # small window
    g.line([(405, 700), (405, 790)], INK, 4)
    for (cx, cy) in ((50, 700), (110, 690), (60, 780), (120, 770), (80, 860)):      # dung cakes drying
        g.circle(cx, cy, 24, (120, 90, 60), INK, 3)
    g.line([(480, 760), (760, 720)], (60, 50, 40), 3)           # washing line with clothes
    for i, (col, w) in enumerate((((230, 120, 60), 60), ((90, 140, 200), 50), ((240, 220, 100), 70))):
        x = 520 + i * 80
        y = 760 - (x - 480) * 40 / 280.0
        g.rect(x, y, x + w, y + 110, col, INK, 3)
    g.rect(890, 640, 940, 1170, (110, 80, 54), INK, 6)          # the neem tree...
    for (cx, cy, r) in ((860, 520, 150), (1000, 560, 140), (930, 420, 150), (800, 640, 100), (1040, 680, 100)):
        g.circle(cx, cy, r, (86, 150, 74), INK, 5)
    g.rect(760, 1150, 1080, 1240, (196, 176, 150), INK, 5)      # ...with a chabutra round it
    g.rect(760, 1130, 1080, 1150, (216, 196, 170), INK, 4)
    g.rect(610, 1000, 640, 1240, (60, 90, 70), INK, 5)          # hand pump
    g.line([(625, 1000), (700, 960)], (60, 90, 70), 10)
    g.line([(640, 1060), (672, 1072)], (60, 90, 70), 10)
    g.rect(0, 1240, LW, LH, (214, 180, 130))                    # the beaten earth of the courtyard
    rnd = random.Random(8)
    for _ in range(26):
        x, y = rnd.randint(0, LW), rnd.randint(1270, LH - 20)
        g.circle(x, y, rnd.randint(4, 9), (190, 156, 110))
    for x in (40, 360, 700, 1020):
        g.line([(x, 1260), (x - 10, 1230), (x + 4, 1258), (x + 14, 1232), (x + 10, 1262)], (110, 150, 80), 4)
    g.line([(0, 1240), (LW, 1240)], INK, 5)
    return g.done()


def school_ground(s):
    """The school ground by day: the two-storey school building (yellow, blue windows, a red-tiled roof edge)
    across the playground, a big tree with a chabutra, the dusty ground."""
    g = G(s)
    _sky(g, (120, 190, 240), (230, 240, 248), 1000)
    with g.on("far"):                                           # 2.5D: the school building across the ground
        g.rect(40, 560, 1040, 1100, (240, 214, 140), INK, 5)
        g.rect(20, 520, 1060, 566, (206, 106, 70), INK, 5)
        g.rect(40, 820, 1040, 846, (226, 130, 80), INK, 4)      # the floor band between the storeys
        for y0 in (610, 880):
            for x in range(80, 1000, 120):
                g.rect(x, y0, x + 70, y0 + 140, (60, 120, 190), INK, 4)
                g.line([(x + 35, y0), (x + 35, y0 + 140)], (40, 90, 150), 3)
        g.rect(500, 960, 580, 1100, (120, 80, 50), INK, 4)      # the main door
        for x in range(60, 1030, 30):                           # corridor railing upstairs
            g.line([(x, 790), (x, 820)], (60, 120, 190), 3)
        g.line([(40, 790), (1040, 790)], (60, 120, 190), 5)
    with g.on("mid"):
        g.rect(0, 1040, LW, 1110, (226, 210, 180), INK, 4)     # the boundary wall
    g.rect(150, 700, 200, 1180, (110, 80, 54), INK, 6)          # a big tree on the left...
    for (cx, cy, r) in ((120, 600, 150), (260, 640, 130), (180, 500, 140), (40, 700, 100), (300, 740, 90)):
        g.circle(cx, cy, r, (92, 156, 80), INK, 5)
    g.rect(40, 1160, 320, 1230, (196, 176, 150), INK, 5)        # ...with a chabutra
    g.rect(0, 1110, LW, LH, (214, 186, 140))                    # the dusty ground
    rnd = random.Random(4)
    for _ in range(30):
        x, y = rnd.randint(0, LW), rnd.randint(1140, LH - 20)
        g.circle(x, y, rnd.randint(3, 8), (194, 164, 120))
    g.line([(0, 1110), (LW, 1110)], INK, 5)
    return g.done()


def cinema(s):
    g = G(s, color=(30, 24, 36))
    g.rect(0, 0, LW, LH, (30, 24, 36))
    g.rect(60, 160, 1020, 760, (200, 220, 240), INK, 8)
    g.poly([(140, 700), (420, 380), (600, 560), (760, 300), (960, 700)], (110, 150, 200))
    g.circle(800, 300, 60, (255, 230, 150))
    layer = Image.new("RGBA", g.im.size, (200, 220, 255, 0))
    ImageDraw.Draw(layer).polygon([(60 * g.k, 760 * g.k), (1020 * g.k, 760 * g.k), (LW * g.k, 1300 * g.k), (0, 1300 * g.k)],
                                  fill=(200, 220, 255, 40))
    g.overlay(layer)
    for row, y in enumerate((1000, 1120, 1250)):
        for x in range(20 + row * 30, LW, 110):
            g.rrect(x, y, x + 96, y + 100, 18, (150, 40, 50), INK, 4)
            g.circle(x + 48, y - 6, 34, (20, 16, 24))
    g.rect(0, 1320, LW, LH, (50, 40, 50))
    g.line([(0, 1320), (LW, 1320)], INK, 5)
    for x in range(40, LW, 160):
        g.circle(x, 1340, 6, (250, 210, 100))
    return g.done()


def bank(s):
    g = G(s, color=(228, 232, 224))
    _wall_floor(g, (228, 232, 224), (200, 200, 196), 1280, "tile")
    _sign(g, 380, 150, 700, 250, "BANK", (40, 90, 160), (255, 255, 255))
    for i, x in enumerate((60, 400, 740)):
        g.rect(x, 360, x + 280, 900, (190, 220, 235), INK, 6)
        _sign(g, x + 40, 380, x + 240, 450, ["CASH", "LOANS", "ENQUIRY"][i], (250, 250, 250), (40, 90, 160), 34)
        g.rect(x + 100, 840, x + 180, 900, (250, 250, 250), INK, 3)
    g.rect(40, 900, 1040, 1100, (150, 104, 66), INK, 6)
    g.rect(20, 880, 1060, 916, (120, 84, 54), INK, 5)
    g.rect(800, 200, 1040, 300, (20, 20, 24), INK, 5)
    _txt(g, 920, 250, "TOKEN 42", 40, (250, 80, 60))
    for x in (160, 420):                                   # queue posts
        g.rect(x - 10, 1180, x + 10, 1290, (200, 180, 90), INK, 3)
    g.line([(170, 1196), (410, 1210), (420, 1196)], (180, 40, 50), 8)
    return g.done()


LOCATIONS = {
    "chai_tapri": chai_tapri, "gully": gully, "kirana": kirana, "market": market, "bus_stop": bus_stop,
    "railway": railway, "terrace": terrace, "balcony": balcony, "bedroom": bedroom, "bathroom": bathroom,
    "canteen": canteen, "hostel": hostel, "office": office, "meeting_room": meeting_room, "exam_hall": exam_hall,
    "library": library, "coaching": coaching, "mandap": mandap, "party": party, "festival_street": festival_street,
    "cricket_ground": cricket_ground, "gym": gym, "jungle": jungle, "haunted_house": haunted_house,
    "graveyard": graveyard, "beach": beach, "mountain_road": mountain_road, "desert": desert, "hospital": hospital,
    "police_station": police_station, "cinema": cinema, "bank": bank, "jail": jail, "gaon": gaon,
    "school_ground": school_ground,
}
# floor line (y where the floor/ground starts) used for depth scaling
LOC_HORIZON = {
    "chai_tapri": 1250, "gully": 1180, "kirana": 1300, "market": 1200, "bus_stop": 1380, "railway": 1180,
    "terrace": 1260, "balcony": 1300, "bedroom": 1290, "bathroom": 1320, "canteen": 1280, "hostel": 1290,
    "office": 1270, "meeting_room": 1260, "exam_hall": 1180, "library": 1290, "coaching": 1290, "mandap": 1280,
    "party": 1290, "festival_street": 1240, "cricket_ground": 900, "gym": 1280, "jungle": 1300,
    "haunted_house": 1300, "graveyard": 1260, "beach": 1260, "mountain_road": 1300, "desert": 1250,
    "hospital": 1280, "police_station": 1280, "cinema": 1320, "bank": 1280, "jail": 1280, "gaon": 1240,
    "school_ground": 1110,
}


# ------------------------------------------------------------------ time of day
def grade(img, time):
    """Re-light a finished background: night, evening/sunset, rain, dawn."""
    if not time or time == "day":
        return img
    W, H = img.size
    if time == "night":
        return Image.blend(img, Image.new("RGB", img.size, (10, 14, 40)), 0.62)
    if time in ("evening", "sunset"):
        grad = Image.new("RGB", (1, 2))
        grad.putpixel((0, 0), (250, 130, 70))
        grad.putpixel((0, 1), (120, 70, 120))
        grad = grad.resize((W, H), Image.BILINEAR)
        return Image.blend(img, grad, 0.32)
    if time == "dawn":
        grad = Image.new("RGB", (1, 2))
        grad.putpixel((0, 0), (250, 190, 200))
        grad.putpixel((0, 1), (200, 210, 240))
        return Image.blend(img, grad.resize((W, H), Image.BILINEAR), 0.25)
    if time == "rain":
        gray = img.convert("L").convert("RGB")
        img = Image.blend(img, gray, 0.4)
        return Image.blend(img, Image.new("RGB", img.size, (60, 70, 90)), 0.28)
    return img

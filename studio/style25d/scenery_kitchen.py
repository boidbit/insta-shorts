"""2.5D desi kitchen (daytime): window with a view outside (its own far layer, so it parallaxes),
sunlight patch with the window-grille shadow on the floor, dust in the light beam, steam from the
pressure cooker, fridge, chimney, tiled backsplash, perspective floor tiles, blurred foreground."""
import math
import random

from PIL import Image, ImageDraw

from .scenery import Cv, Layer, Layered, fill_tex, mix, motes, mul, steam, toward, vgrad
from ..util import LH, LW

VP = (560, 800)
INK = (46, 36, 34, 255)
WIN = (690, 470, 990, 810)            # window opening x0, y0, x1, y1
COUNTER_Y = 1030                       # front edge of the counter top
FLOOR_Y = 1300                         # where the counter meets the floor


def _outside(k):
    """What you see through the window: sky, clouds, neighbours' houses, a tree. Far + blurred."""
    cv = Cv(k)
    cv.im = vgrad(k, [(0, (96, 160, 228)), (420, (128, 186, 238)), (820, (206, 228, 244)), (LH, (206, 228, 244))])
    cv.d = ImageDraw.Draw(cv.im)
    rnd = random.Random(4)
    for (cx, cy, w) in ((720, 520, 140), (930, 560, 180), (1040, 500, 120)):
        for i in range(5):
            cv.ell(cx + rnd.uniform(-w / 2, w / 2), cy + rnd.uniform(-14, 14), w * 0.32, w * 0.2, (255, 255, 255, 230))
    x = 560
    for col in ((236, 196, 160), (190, 210, 220), (240, 220, 170), (214, 170, 170), (200, 220, 190), (236, 204, 180)):
        w = rnd.uniform(90, 140)
        top = rnd.uniform(620, 700)
        cv.rect(x, top, x + w, 1100, col + (255,))
        cv.rect(x - 4, top - 8, x + w + 4, top, mul(col, 1.08) + (255,))
        for wy in range(int(top) + 20, 900, 46):
            for wx in range(int(x) + 14, int(x + w) - 24, 34):
                cv.rect(wx, wy, wx + 18, wy + 24, mul(col, 0.62) + (255,))
        if rnd.random() < 0.6:
            cv.rect(x + 16, top - 34, x + 50, top - 8, (60, 64, 70, 255))      # water tank
        x += w + rnd.uniform(-6, 8)
    for i in range(14):                                                    # a tree on the right
        cv.ell(960 + rnd.uniform(-70, 80), 690 + rnd.uniform(-60, 60), rnd.uniform(36, 60), rnd.uniform(30, 50),
               mix((70, 140, 70), (120, 180, 90), rnd.random()) + (255,))
    cv.rect(950, 720, 966, 900, (100, 76, 56, 255))
    cv.blur(3.5)
    return cv


def _box(cv, x0, x1, y0, y1, front, side=0.06, top=False):
    """A box standing against the wall: front face + the side face that faces the vanishing point."""
    if x1 < VP[0]:
        a, b = (x1, y0), (x1, y1)
        q = [a, toward(a, VP, side), toward(b, VP, side), b]
    else:
        a, b = (x0, y0), (x0, y1)
        q = [toward(a, VP, side), a, b, toward(b, VP, side)]
    cv.poly(q, mul(front, 0.72) + (255,), INK, 3)
    if top:
        tl, tr = (x0, y0), (x1, y0)
        cv.poly([toward(tl, VP, side), toward(tr, VP, side), tr, tl], mul(front, 1.12) + (255,), INK, 3)
    cv.rect(x0, y0, x1, y1, front + (255,), INK, 3)


def _room(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(255, 236, 190, 0))
    x0w, y0w, x1w, y1w = WIN

    # ---- back wall + window hole ----
    fill_tex(cv, [(0, 0), (LW, 0), (LW, FLOOR_Y), (0, FLOOR_Y)],
             [(0, (222, 204, 168)), (700, (240, 226, 192)), (1000, (234, 218, 182))], seed=2, cell=60,
             lo=0.96, hi=1.035)
    cv.rect(0, 0, LW, 64, (214, 200, 176, 255))                                          # ceiling
    cv.rect(0, 64, LW, 76, (196, 180, 150, 255))                                         # cornice
    cv.erase([(x0w, y0w), (x1w, y0w), (x1w, y1w), (x0w, y1w)])
    # tube light + a calendar
    cv.rect(650, 128, 980, 146, (250, 252, 248, 255), INK, 2)
    cv.rect(640, 124, 662, 150, (200, 200, 196, 255), INK, 2)
    cv.rect(968, 124, 990, 150, (200, 200, 196, 255), INK, 2)
    light.glow(815, 137, 300, (255, 252, 236), 70)
    cv.line([(110, 120), (110, 134)], (90, 80, 70, 255), 3)
    cv.rect(46, 134, 176, 330, (250, 250, 246, 255), INK, 2)
    cv.rect(46, 134, 176, 214, (230, 120, 60, 255), INK, 2)
    for r_ in range(4):
        for c_ in range(5):
            cv.rect(56 + c_ * 23, 226 + r_ * 24, 72 + c_ * 23, 242 + r_ * 24, (200, 196, 190, 255))
    # window frame, grille, sill
    cv.rect(x0w - 16, y0w - 16, x1w + 16, y0w, (246, 244, 236, 255), INK, 3)
    cv.rect(x0w - 16, y1w, x1w + 16, y1w + 22, (246, 244, 236, 255), INK, 3)
    cv.rect(x0w - 16, y0w, x0w, y1w, (246, 244, 236, 255), INK, 3)
    cv.rect(x1w, y0w, x1w + 16, y1w, (246, 244, 236, 255), INK, 3)
    cv.line([((x0w + x1w) / 2, y0w), ((x0w + x1w) / 2, y1w)], (246, 244, 236, 255), 12)
    for i in range(1, 8):
        gx = x0w + (x1w - x0w) * i / 8.0
        cv.line([(gx, y0w), (gx, y1w)], (70, 70, 76, 255), 4)
    for gy in (y0w + 110, y0w + 230):
        cv.line([(x0w, gy), (x1w, gy)], (70, 70, 76, 255), 4)
    # tulsi-green curtains tied at the sides
    for (cx0, cx1, sgn) in ((x0w - 52, x0w + 34, -1), (x1w - 34, x1w + 52, 1)):
        pts = [(cx0, y0w - 34), (cx1, y0w - 34), (cx1 + sgn * -10, y0w + 210), (cx1 - sgn * 6, y1w + 40),
               (cx0, y1w + 40), (cx0 + sgn * 8, y0w + 210)]
        cv.poly(pts, (64, 140, 118, 255), INK, 3)
        for f in (0.33, 0.66):
            fx = cx0 + (cx1 - cx0) * f
            cv.line([(fx, y0w - 30), (fx + sgn * -4, y0w + 210), (fx, y1w + 36)], (44, 108, 90, 255), 3)
        cv.line([(cx0 - 4, y0w + 210), (cx1 + 4, y0w + 205)], (230, 190, 80, 255), 6)
    cv.rect(x0w - 70, y0w - 44, x1w + 70, y0w - 32, (150, 110, 70, 255), INK, 2)   # curtain rod

    # ---- chimney hood + duct ----
    cv.rect(505, -10, 585, 560, (176, 178, 184, 255), INK, 3)
    cv.poly([(470, 560), (620, 560), (668, 790), (412, 790)], (60, 62, 68, 255), INK, 3)
    cv.rect(406, 780, 674, 800, (40, 42, 46, 255), INK, 3)
    cv.rect(560, 766, 600, 780, (120, 220, 255, 255))                                  # little indicator

    # ---- upper cabinets (left) ----
    for i, (a, b) in enumerate(((196, 300), (300, 404))):
        cv.rect(a, 470, b, 762, (156, 102, 62, 255), INK, 3)
        cv.rect(a + 12, 484, b - 12, 748, (170, 114, 70, 255), (110, 70, 42, 255), 2)
        hx = b - 26 if i == 0 else a + 22
        cv.line([(hx, 590), (hx, 650)], (220, 220, 226, 255), 6)
    cv.rect(190, 456, 410, 470, (130, 84, 50, 255), INK, 2)
    light.glow(300, 780, 140, (255, 230, 170), 90)                                     # under-cabinet light

    # ---- backsplash tiles ----
    fill_tex(cv, [(196, 800), (LW, 800), (LW, 1004), (196, 1004)], (236, 238, 240), seed=5, cell=14, lo=0.95, hi=1.03)
    for ty in range(800, 1004, 34):
        cv.line([(196, ty), (LW, ty)], (190, 196, 204, 255), 2)
    for tx in range(196, LW, 34):
        cv.line([(tx, 800), (tx, 1004)], (190, 196, 204, 255), 2)
    rnd = random.Random(9)
    for _ in range(14):
        tx, ty = 196 + 34 * rnd.randint(0, 25), 800 + 34 * rnd.randint(0, 5)
        cv.ell(tx + 17, ty + 17, 8, 8, (80, 130, 190, 255))
    # utensil rack with ladles
    cv.line([(210, 812), (396, 812)], (200, 200, 206, 255), 6)
    for i, x in enumerate(range(226, 392, 32)):
        L = 70 + (i % 3) * 14
        cv.line([(x, 812), (x, 812 + L)], (200, 202, 210, 255), 5)
        if i % 2:
            cv.ell(x, 812 + L + 10, 13, 10, (206, 208, 214, 255), INK, 2)
        else:
            cv.rect(x - 9, 812 + L, x + 9, 812 + L + 22, (206, 208, 214, 255), INK, 2)

    # ---- counter: top surface in perspective + cabinet front ----
    fl, fr = (196, COUNTER_Y), (LW + 20, COUNTER_Y)
    top = [toward(fl, VP, 0.12), toward(fr, VP, 0.12), fr, fl]
    fill_tex(cv, top, (58, 60, 58), seed=7, cell=6, lo=0.75, hi=1.25)
    cv.line([fl, fr], (150, 152, 156, 255), 7)
    fill_tex(cv, [(196, COUNTER_Y + 4), (LW, COUNTER_Y + 4), (LW, FLOOR_Y), (196, FLOOR_Y)],
             [(COUNTER_Y, (204, 160, 110)), (FLOOR_Y, (176, 132, 90))], seed=8, cell=20)
    for i, x in enumerate(range(196, LW, 176)):
        cv.rect(x + 8, COUNTER_Y + 18, x + 168, FLOOR_Y - 30, None, (130, 92, 60, 255), 3)
        hx = x + 150 if i % 2 == 0 else x + 26
        cv.line([(hx, COUNTER_Y + 50), (hx, COUNTER_Y + 110)], (220, 222, 228, 255), 6)
    cv.rect(196, FLOOR_Y - 26, LW, FLOOR_Y, (90, 66, 50, 255))

    # ---- stove, pressure cooker, kadhai ----
    cv.poly([(398, 1000), (690, 1000), (700, 1018), (388, 1018)], (40, 40, 44, 255), INK, 3)
    cv.rect(388, 1018, 700, 1040, (150, 152, 158, 255), INK, 3)
    for kx in (430, 470, 620, 660):
        cv.ell(kx, 1029, 7, 7, (30, 30, 30, 255))
    cv.ell(610, 1004, 40, 8, (60, 120, 230, 255))                                       # blue flame ring
    cv.ell(610, 1004, 26, 5, (140, 200, 255, 255))
    # cooker
    cv.ell(470, 1004, 46, 10, (150, 152, 160, 255), INK, 3)
    cv.rect(424, 926, 516, 1004, (196, 198, 206, 255), INK, 3)
    cv.rect(430, 932, 452, 998, (226, 228, 234, 255))
    cv.ell(470, 926, 48, 11, (120, 122, 130, 255), INK, 3)
    cv.poly([(510, 920), (612, 904), (614, 916), (512, 932)], (30, 30, 32, 255), INK, 2)
    cv.rect(462, 896, 478, 920, (30, 30, 32, 255), INK, 2)
    # kadhai
    cv.poly([(552, 984)] + [(610 + 58 * math.cos(a), 984 + 26 * math.sin(a)) for a in
                            [i * math.pi / 12 for i in range(13)]], (54, 54, 58, 255), INK, 3)
    cv.ell(610, 984, 58, 10, (80, 80, 86, 255), INK, 3)
    # steel dabbas + masala box + chopping board
    for (x, w, h) in ((770, 54, 90), (834, 60, 70), (904, 50, 104), (962, 56, 80)):
        cv.rect(x, 1012 - h, x + w, 1012, (200, 204, 212, 255), INK, 2)
        cv.ell(x + w / 2, 1012 - h, w / 2, 7, (170, 174, 182, 255), INK, 2)
        cv.rect(x + 6, 1012 - h + 8, x + 14, 1006, (232, 234, 240, 255))
    cv.poly([(250, 1010), (380, 1010), (388, 1024), (244, 1024)], (214, 170, 110, 255), INK, 2)
    for (tx, col) in ((285, (220, 50, 40)), (318, (224, 60, 46)), (352, (150, 60, 120))):
        cv.ell(tx, 1004, 16, 13, col + (255,), INK, 2)

    # ---- fridge (left) ----
    _box(cv, -12, 176, 446, FLOOR_Y + 12, (170, 48, 56), side=0.07, top=True)
    cv.line([(-12, 700), (176, 700)], (110, 30, 36, 255), 4)
    cv.line([(152, 560), (152, 670)], (230, 230, 236, 255), 8)
    cv.line([(152, 740), (152, 900)], (230, 230, 236, 255), 8)
    for (mx, my, col) in ((40, 760, (250, 210, 60)), (90, 800, (90, 170, 230)), (52, 850, (250, 250, 250)),
                          (110, 900, (120, 200, 110))):
        cv.rect(mx, my, mx + 30, my + 22, col + (255,), INK, 2)
    cv.rect(20, 404, 140, 446, (214, 190, 140, 255), INK, 2)                            # basket on top

    # ---- floor tiles in perspective ----
    def fx_at(x_at_floor, y):
        return VP[0] + (x_at_floor - VP[0]) * (y - VP[1]) / float(FLOOR_Y - VP[1])
    rows = [FLOOR_Y]
    while rows[-1] < LH + 300:
        rows.append(VP[1] + (rows[-1] - VP[1]) * 1.22)
    cols = list(range(-2400, 3400, 92))
    for i in range(len(rows) - 1):
        ya, yb = rows[i], rows[i + 1]
        for j in range(len(cols) - 1):
            c = (236, 226, 204) if (i + j) % 2 == 0 else (206, 186, 156)
            cv.poly([(fx_at(cols[j], ya), ya), (fx_at(cols[j + 1], ya), ya),
                     (fx_at(cols[j + 1], yb), yb), (fx_at(cols[j], yb), yb)], c + (255,))
    cv.rect(0, FLOOR_Y, LW, FLOOR_Y + 14, (90, 70, 60, 110))                            # contact shadow

    # ---- sunlight: patch on the floor with grille shadows + soft beam + window glow ----
    pa, pb, pc, pd = (520, 1360), (880, 1360), (760, 1700), (300, 1700)
    for i in range(8):
        u0, u1 = i / 8.0 + 0.012, (i + 1) / 8.0 - 0.012
        q = [(pa[0] + (pb[0] - pa[0]) * u0, pa[1]), (pa[0] + (pb[0] - pa[0]) * u1, pa[1]),
             (pd[0] + (pc[0] - pd[0]) * u1, pd[1]), (pd[0] + (pc[0] - pd[0]) * u0, pd[1])]
        light.poly(q, (255, 236, 190, 175))
    beam = Cv(kg, fill=(255, 236, 190, 0))
    beam.poly([(x0w, y0w), (x1w, y0w), (x1w, y1w), (pb[0], pb[1]), (pc[0], pc[1]), (pd[0], pd[1]), (x0w, y1w)],
              (255, 236, 196, 60))
    beam.blur(40)
    light.blur(5)
    light.over(beam)
    light.glow((x0w + x1w) / 2, (y0w + y1w) / 2, 330, (255, 246, 220), 80)
    cv.blur(0.35)
    return cv, light


def _foreground(k):
    cv = Cv(k, fill=(70, 120, 60, 0))
    rnd = random.Random(12)
    # money plant leaves, bottom-left
    for i in range(16):
        x, y = rnd.uniform(-60, 230), rnd.uniform(1700, 1990)
        a = rnd.uniform(0, math.pi)
        pts = []
        for j in range(18):
            b = 2 * math.pi * j / 18
            r = 54 * (1 - 0.35 * math.sin(b) ** 2)
            px, py = r * math.cos(b), r * 0.62 * math.sin(b)
            pts.append((x + px * math.cos(a) - py * math.sin(a), y + px * math.sin(a) + py * math.cos(a)))
        cv.poly(pts, mix((60, 130, 50), (150, 190, 80), rnd.random()) + (255,))
    # table corner with a steel glass of chai, bottom-right
    cv.poly([(800, 1830), (LW + 40, 1790), (LW + 40, LH + 40), (760, LH + 40)], (130, 82, 50, 255))
    cv.rect(930, 1640, 1010, 1810, (196, 198, 206, 255))
    cv.rect(936, 1680, 1004, 1806, (170, 110, 60, 255))
    cv.ell(970, 1640, 40, 9, (220, 222, 230, 255))
    # nimbu-mirchi hanging at the top-right
    cv.line([(1020, -20), (1020, 210)], (240, 240, 230, 255), 3)
    cv.ell(1020, 112, 26, 30, (240, 214, 60, 255))
    for i in range(5):
        cv.poly([(1006 + i * 7, 150), (1016 + i * 6, 150), (1010 + i * 6, 260 + (i % 2) * 18)], (40, 150, 50, 255))
    cv.blur(8)
    return cv


def kitchen_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    outside = _outside(0.5 * s)
    room, light = _room(kr, kg)
    fg = _foreground(0.5 * s)
    empty = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    back = [
        Layer(outside.im, 0.5 * s, 0.12, None, "outside"),
        Layer(room.im, kr, 1.0, None, "room"),
        Layer(light.im, kg, 1.0, None, "sunlight", mode="screen"),
        Layer(empty, 0.3 * s, 1.0, motes(((840, 640), (560, 1520), 260), 0.3 * s), "dust", mode="screen"),
        Layer(empty, 0.3 * s, 1.0, steam([(470, 890, 0.9, 0.55), (610, 975, 0.6, 0.4)], 0.3 * s), "steam"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    light_cfg = {"ambient": [255, 248, 238], "dir": 1, "vignette": 0.26}
    return Layered(back, front, light=light_cfg, horizon=VP[1], ground=FLOOR_Y)

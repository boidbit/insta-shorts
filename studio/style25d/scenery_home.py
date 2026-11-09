"""Two more hand-made 2.5D sets, painted like the kitchen.

room_25d       ghar ka kamra (daytime): sofa under a window with a view outside (its own far layer), TV that
               flickers on the wall and floor, ceiling fan that turns, rug on a marble floor, sunlight with the
               grille's shadow and dust in the beam, wall clock, family photo, a blurred table in front.
classroom_25d  school classroom (daytime): blackboard with chalk writing, teacher's table with a globe, benches,
               two ceiling fans, a window onto the school ground with sunlight and chalk dust, a blurred desk in
               front. (It has writing on it, so a reverse shot never mirrors it.)
"""
import math
import random

from PIL import Image, ImageDraw

from .scenery import Cv, Layer, Layered, catenary, fill_tex, mix, motes, mul, quad_image, toward, vgrad
from ..util import LH, LW

INK = (46, 36, 34, 255)


# ------------------------------------------------------------------ shared pieces
def _floor_tiles(cv, vp, floor_y, c1, c2, step=92, grow=1.22, grout=None):
    """Square tiles on the floor, in perspective towards the vanishing point vp."""
    def fx(x, y):
        return vp[0] + (x - vp[0]) * (y - vp[1]) / float(floor_y - vp[1])
    rows = [floor_y]
    while rows[-1] < LH + 300:
        rows.append(vp[1] + (rows[-1] - vp[1]) * grow)
    cols = list(range(-2400, 3400, step))
    for i in range(len(rows) - 1):
        ya, yb = rows[i], rows[i + 1]
        for j in range(len(cols) - 1):
            c = c1 if (i + j) % 2 == 0 else c2
            cv.poly([(fx(cols[j], ya), ya), (fx(cols[j + 1], ya), ya), (fx(cols[j + 1], yb), yb),
                     (fx(cols[j], yb), yb)], c + (255,), grout, 1 if grout else 0)
    return fx


def _box(cv, vp, x0, x1, y0, y1, front, side=0.06, top=True, outline=INK):
    """A box standing against the back wall: front face, the side facing the vanishing point, the top."""
    if x1 < vp[0]:
        a, b = (x1, y0), (x1, y1)
        cv.poly([a, toward(a, vp, side), toward(b, vp, side), b], mul(front, 0.72) + (255,), outline, 3)
    elif x0 > vp[0]:
        a, b = (x0, y0), (x0, y1)
        cv.poly([toward(a, vp, side), a, b, toward(b, vp, side)], mul(front, 0.72) + (255,), outline, 3)
    if top and y0 > vp[1]:
        tl, tr = (x0, y0), (x1, y0)
        cv.poly([toward(tl, vp, side), toward(tr, vp, side), tr, tl], mul(front, 1.12) + (255,), outline, 3)
    cv.rect(x0, y0, x1, y1, front + (255,), outline, 3)


def _shadow(cv, cx, cy, rx, ry, a=80):
    for i in range(4):
        f = 1 - i * 0.2
        cv.ell(cx, cy, rx * f, ry * f, (20, 14, 10, int(a / 4)))


def _window(cv, light, beam_to, x0, y0, x1, y1, bars_v=6, bars_h=2, frame=(246, 244, 236), sill=True):
    """Window opening (erased: the far layer shows through), frame, grille, and the sunlight it throws onto the
    floor: a patch with the grille's shadow (light layer) plus a soft beam. beam_to = floor quad (a, b, c, d)."""
    cv.erase([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    fr = frame + (255,)
    cv.rect(x0 - 16, y0 - 16, x1 + 16, y0, fr, INK, 3)
    cv.rect(x0 - 16, y1, x1 + 16, y1 + (22 if sill else 16), fr, INK, 3)
    cv.rect(x0 - 16, y0, x0, y1, fr, INK, 3)
    cv.rect(x1, y0, x1 + 16, y1, fr, INK, 3)
    cv.line([((x0 + x1) / 2, y0), ((x0 + x1) / 2, y1)], fr, 10)
    for i in range(1, bars_v + 1):
        gx = x0 + (x1 - x0) * i / float(bars_v + 1)
        cv.line([(gx, y0), (gx, y1)], (70, 70, 76, 255), 4)
    for i in range(1, bars_h + 1):
        gy = y0 + (y1 - y0) * i / float(bars_h + 1)
        cv.line([(x0, gy), (x1, gy)], (70, 70, 76, 255), 4)
    pa, pb, pc, pd = beam_to
    n = bars_v + 1
    for i in range(n):
        u0, u1 = i / float(n) + 0.012, (i + 1) / float(n) - 0.012
        q = [(pa[0] + (pb[0] - pa[0]) * u0, pa[1]), (pa[0] + (pb[0] - pa[0]) * u1, pa[1]),
             (pd[0] + (pc[0] - pd[0]) * u1, pd[1]), (pd[0] + (pc[0] - pd[0]) * u0, pd[1])]
        light.poly(q, (255, 236, 190, 150))
    beam = Cv(light.k, fill=(255, 236, 196, 0))
    beam.poly([(x0, y0), (x1, y0), (x1, y1), pb, pc, pd, (x0, y1)], (255, 236, 196, 52))
    beam.blur(40)
    light.blur(5)
    light.over(beam)
    light.glow((x0 + x1) / 2.0, (y0 + y1) / 2.0, max(x1 - x0, y1 - y0) * 0.75, (255, 246, 220), 76)


def _curtain(cv, x0, x1, top, bottom, col, sgn):
    tie = top + (bottom - top) * 0.45
    pts = [(x0, top), (x1, top), (x1 + sgn * -10, tie), (x1 - sgn * 6, bottom),
           (x0, bottom), (x0 + sgn * 8, tie)]
    cv.poly(pts, col + (255,), INK, 3)
    for f in (0.33, 0.66):
        fx = x0 + (x1 - x0) * f
        cv.line([(fx, top + 4), (fx + sgn * -4, tie), (fx, bottom - 4)], mul(col, 0.74) + (255,), 3)
    cv.line([(x0 - 4, tie), (x1 + 4, tie - 5)], (230, 190, 80, 255), 6)


def _clock(cv, cx, cy, r, rim=(140, 40, 50)):
    cv.ell(cx, cy, r + 8, r + 8, rim + (255,), INK, 3)
    cv.ell(cx, cy, r, r, (252, 250, 244, 255), INK, 2)
    for i in range(12):
        a = i * math.pi / 6
        r0 = r * (0.78 if i % 3 else 0.7)
        cv.line([(cx + r0 * math.cos(a), cy + r0 * math.sin(a)), (cx + r * 0.9 * math.cos(a), cy + r * 0.9 * math.sin(a))],
                (60, 50, 50, 255), 3 if i % 3 else 5)
    cv.line([(cx, cy), (cx - r * 0.42, cy - r * 0.3)], (40, 34, 34, 255), 6)     # 10:10
    cv.line([(cx, cy), (cx + r * 0.62, cy - r * 0.42)], (40, 34, 34, 255), 4)
    cv.ell(cx, cy, 5, 5, (40, 34, 34, 255))


def _tube_light(cv, light, x0, x1, y):
    cv.rect(x0, y, x1, y + 16, (250, 252, 248, 255), INK, 2)
    cv.rect(x0 - 12, y - 4, x0 + 10, y + 20, (200, 200, 196, 255), INK, 2)
    cv.rect(x1 - 10, y - 4, x1 + 12, y + 20, (200, 200, 196, 255), INK, 2)
    light.glow((x0 + x1) / 2.0, y + 8, (x1 - x0) * 0.9, (255, 252, 236), 64)


def fan(cx, hub_y, k, R=220, speed=2.6, top=0, col=(178, 140, 104)):
    """fn for a dynamic layer: a ceiling fan turning (seen from below and in front, so the blades sweep an ellipse;
    each blade is drawn a few times along its path for motion blur)."""
    def fn(_im, t):
        cv = Cv(k, fill=col + (0,))
        cv.line([(cx, top), (cx, hub_y - 18)], (120, 116, 110, 255), 10)
        cv.ell(cx, top + 8, 26, 10, (200, 196, 190, 255), INK, 2)
        blades = []
        for i in range(3):
            for j in range(4):                                   # motion blur: the blade a moment earlier
                a = (t - j * 0.012) * speed * 2 * math.pi + i * 2 * math.pi / 3
                blades.append((math.sin(a), a, j))
        blades.sort()                                            # far blades (behind the hub) first
        hub_drawn = False
        for (sa, a, j) in blades:
            if sa > 0 and not hub_drawn:
                cv.ell(cx, hub_y, 46, 22, (186, 180, 172, 255), INK, 3)
                hub_drawn = True
            tip = (cx + R * math.cos(a), hub_y + R * 0.16 * math.sin(a))
            root = (cx + 40 * math.cos(a), hub_y + 40 * 0.16 * math.sin(a))
            w = 24 * (0.65 + 0.35 * abs(math.sin(a)))
            nx, ny = -math.sin(a) * w * 0.16, math.cos(a) * w * 0.16 + w * 0.5
            alpha = (230, 120, 70, 40)[j]
            cv.poly([(root[0] - nx * 0.4, root[1] - ny * 0.4), (tip[0] - nx, tip[1] - ny), (tip[0] + nx, tip[1] + ny),
                     (root[0] + nx * 0.4, root[1] + ny * 0.4)], mul(col, 0.94 + 0.08 * sa) + (alpha,))
        if not hub_drawn:
            cv.ell(cx, hub_y, 46, 22, (186, 180, 172, 255), INK, 3)
        cv.ell(cx, hub_y + 16, 30, 10, (150, 146, 140, 255), INK, 2)
        cv.blur(0.8)
        return cv.im
    return fn


def _leaves(cv, n, x0, x1, y0, y1, size, cols, seed):
    rnd = random.Random(seed)
    for _ in range(n):
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        a = rnd.uniform(0, math.pi)
        pts = []
        for j in range(18):
            b = 2 * math.pi * j / 18
            r = size * (1 - 0.35 * math.sin(b) ** 2)
            px, py = r * math.cos(b), r * 0.6 * math.sin(b)
            pts.append((x + px * math.cos(a) - py * math.sin(a), y + px * math.sin(a) + py * math.cos(a)))
        cv.poly(pts, mix(cols[0], cols[1], rnd.random()) + (255,))


# ------------------------------------------------------------------ ghar ka kamra
ROOM_VP = (540, 820)
ROOM_FLOOR = 1300
ROOM_WIN = (96, 430, 396, 880)
TV = (684, 790, 1004, 990)


def _room_outside(k):
    """Through the window: sky, clouds, the neighbours' houses, a neem tree, electric wires. Far + blurred."""
    cv = Cv(k)
    cv.im = vgrad(k, [(0, (98, 162, 228)), (400, (130, 188, 238)), (820, (210, 230, 244)), (LH, (210, 230, 244))])
    cv.d = ImageDraw.Draw(cv.im)
    rnd = random.Random(6)
    for (cx, cy, w) in ((160, 500, 150), (340, 470, 120)):
        for _ in range(5):
            cv.ell(cx + rnd.uniform(-w / 2, w / 2), cy + rnd.uniform(-12, 12), w * 0.3, w * 0.19, (255, 255, 255, 230))
    x = -20
    for col in ((236, 200, 160), (196, 214, 224), (240, 222, 176), (216, 176, 176), (204, 222, 194)):
        w = rnd.uniform(90, 130)
        top = rnd.uniform(610, 700)
        cv.rect(x, top, x + w, 1200, col + (255,))
        cv.rect(x - 4, top - 8, x + w + 4, top, mul(col, 1.08) + (255,))
        for wy in range(int(top) + 22, 1000, 46):
            for wx in range(int(x) + 14, int(x + w) - 24, 34):
                cv.rect(wx, wy, wx + 18, wy + 24, mul(col, 0.62) + (255,))
        if rnd.random() < 0.6:
            cv.rect(x + 16, top - 34, x + 50, top - 8, (60, 64, 70, 255))            # water tank
        x += w + rnd.uniform(-6, 8)
    for _ in range(16):                                                            # neem tree
        cv.ell(300 + rnd.uniform(-90, 90), 640 + rnd.uniform(-70, 60), rnd.uniform(34, 58), rnd.uniform(28, 48),
               mix((64, 132, 64), (120, 176, 86), rnd.random()) + (255,))
    cv.rect(292, 680, 308, 900, (100, 76, 56, 255))
    cv.line(catenary(-20, 560, 480, 590, 40), (40, 40, 44, 255), 2)
    cv.line(catenary(-20, 590, 480, 620, 44), (40, 40, 44, 255), 2)
    cv.blur(3.5)
    return cv


def _room(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(255, 236, 190, 0))
    vp, F = ROOM_VP, ROOM_FLOOR
    # back wall, ceiling, skirting
    fill_tex(cv, [(0, 0), (LW, 0), (LW, F), (0, F)], [(0, (236, 216, 190)), (700, (242, 226, 200)), (F, (228, 206, 176))],
             seed=3, cell=60, lo=0.96, hi=1.035)
    cv.rect(0, 0, LW, 60, (244, 238, 228, 255))
    cv.rect(0, 60, LW, 72, (214, 196, 168, 255))
    cv.rect(0, F - 30, LW, F, (170, 128, 92, 255), INK, 2)
    _tube_light(cv, light, 430, 700, 150)

    # window over the sofa, maroon curtains
    x0, y0, x1, y1 = ROOM_WIN
    _window(cv, light, ((380, 1380), (700, 1380), (880, 1650), (430, 1650)), x0, y0, x1, y1)
    cv.rect(x0 - 70, y0 - 44, x1 + 70, y0 - 32, (150, 110, 70, 255), INK, 2)       # curtain rod
    _curtain(cv, x0 - 54, x0 + 30, y0 - 34, y1 + 60, (140, 36, 50), -1)
    _curtain(cv, x1 - 30, x1 + 54, y0 - 34, y1 + 60, (140, 36, 50), 1)

    # wall clock, family photo, calendar
    _clock(cv, 246, 300, 46)
    cv.rect(712, 380, 888, 600, (200, 160, 70, 255), INK, 3)                       # family photo
    cv.rect(728, 396, 872, 584, (186, 214, 228, 255), INK, 2)
    for (px, pr, col) in ((760, 22, (150, 40, 60)), (800, 26, (60, 90, 150)), (842, 20, (220, 140, 40))):
        cv.ell(px, 500 - pr, pr * 0.7, pr * 0.8, (210, 160, 120, 255), INK, 2)
        cv.poly([(px - pr, 584), (px - pr * 0.8, 510), (px + pr * 0.8, 510), (px + pr, 584)], col + (255,), INK, 2)
    cv.line([(800, 350), (712, 380)], (90, 80, 70, 255), 2)
    cv.line([(800, 350), (888, 380)], (90, 80, 70, 255), 2)
    cv.rect(950, 250, 1044, 400, (250, 250, 246, 255), INK, 2)                       # calendar
    cv.rect(950, 250, 1044, 300, (210, 70, 60, 255), INK, 2)
    for r_ in range(3):
        for c_ in range(4):
            cv.rect(960 + c_ * 21, 312 + r_ * 26, 974 + c_ * 21, 328 + r_ * 26, (200, 196, 190, 255))

    # TV on a wooden unit, a vase of flowers
    _box(cv, vp, 640, 1060, 1100, F, (146, 96, 58), side=0.07)
    for i, xx in enumerate((640, 780, 920)):
        cv.rect(xx + 10, 1120, xx + 130, F - 16, None, (110, 70, 42, 255), 3)
        cv.line([(xx + (110 if i % 2 == 0 else 20), 1180), (xx + (110 if i % 2 == 0 else 20), 1230)], (226, 220, 210, 255), 6)
    tx0, ty0, tx1, ty1 = TV
    cv.rect((tx0 + tx1) / 2 - 40, ty1, (tx0 + tx1) / 2 + 40, 1100, (40, 40, 44, 255), INK, 2)
    cv.rect(tx0, ty0, tx1, ty1, (24, 24, 28, 255), INK, 3)
    cv.rect(tx0 + 12, ty0 + 12, tx1 - 12, ty1 - 12, (30, 36, 46, 255))
    cv.poly([(tx0 + 20, ty0 + 20), (tx0 + 120, ty0 + 20), (tx0 + 40, ty1 - 20), (tx0 + 20, ty1 - 20)],
            (255, 255, 255, 18))
    cv.rect(990, 1040, 1036, 1100, (60, 110, 160, 255), INK, 2)                       # vase
    _leaves(cv, 7, 980, 1046, 960, 1040, 22, ((220, 70, 80), (250, 190, 60)), 4)

    # plant in the corner between sofa and TV
    cv.poly([(552, 1210), (620, 1210), (608, F), (564, F)], (176, 92, 56, 255), INK, 3)
    _leaves(cv, 14, 520, 650, 980, 1200, 42, ((50, 120, 60), (110, 170, 80)), 7)

    # sofa under the window
    teal, cushion = (42, 112, 122), [(230, 180, 60), (214, 104, 60), (230, 180, 60)]
    cv.poly([(70, 1010), (520, 1010), (530, 1160), (60, 1160)], teal + (255,), INK, 3)                 # back
    for i in range(3):
        bx = 92 + i * 142
        cv.poly([(bx, 1030), (bx + 132, 1030), (bx + 136, 1150), (bx - 4, 1150)], mul(teal, 1.08) + (255,), INK, 2)
    for i, c in enumerate(cushion):
        cx = 150 + i * 145
        cv.poly([(cx - 52, 1060), (cx + 50, 1052), (cx + 56, 1148), (cx - 48, 1154)], c + (255,), INK, 3)
        cv.ell(cx + 2, 1103, 8, 8, mul(c, 0.8) + (255,))
    cv.rect(96, 1150, 494, 1218, mul(teal, 1.14) + (255,), INK, 3)                                    # seat
    cv.line([(229, 1152), (229, 1216)], mul(teal, 0.8) + (255,), 3)
    cv.line([(362, 1152), (362, 1216)], mul(teal, 0.8) + (255,), 3)
    cv.rect(96, 1218, 494, 1284, mul(teal, 0.84) + (255,), INK, 3)                                    # base
    for ax in (40, 494):                                                                              # arms
        cv.rect(ax, 1100, ax + 66, 1284, mul(teal, 0.96) + (255,), INK, 3)
        cv.ell(ax + 33, 1100, 36, 18, mul(teal, 1.1) + (255,), INK, 3)
    for lx in (56, 534):
        cv.rect(lx, 1284, lx + 14, F + 4, (60, 40, 30, 255))
    _shadow(cv, 286, F + 2, 270, 16)
    _shadow(cv, 850, F + 2, 230, 14)

    # marble floor + a rug
    fx = _floor_tiles(cv, vp, F, (238, 234, 226), (218, 212, 204), step=110, grow=1.24)
    for (ya, yb) in ((F, F + 3),):
        cv.rect(0, ya, LW, yb, (120, 100, 90, 120))
    q = [(fx(260, 1390), 1390), (fx(860, 1390), 1390), (fx(860, 1660), 1660), (fx(260, 1660), 1660)]
    cv.poly(q, (150, 40, 50, 255))
    inner = [toward(q[0], toward(q[2], q[0], 0.5), 0.1), toward(q[1], toward(q[3], q[1], 0.5), 0.1),
             toward(q[2], toward(q[0], q[2], 0.5), 0.1), toward(q[3], toward(q[1], q[3], 0.5), 0.1)]
    cv.poly(inner, (196, 120, 60, 255))
    cv.line(inner + [inner[0]], (236, 200, 120, 255), 4)
    mid = ((q[0][0] + q[2][0]) / 2, (q[0][1] + q[2][1]) / 2)
    cv.ell(mid[0], mid[1], 90, 42, (150, 40, 50, 255), (236, 200, 120, 255), 4)
    cv.ell(mid[0], mid[1], 40, 18, (236, 200, 120, 255))
    cv.blur(0.35)
    return cv, light


def _room_front(k):
    cv = Cv(k, fill=(70, 120, 60, 0))
    _leaves(cv, 16, -60, 230, 1700, 1990, 54, ((60, 130, 50), (150, 190, 80)), 12)       # money plant, bottom-left
    cv.poly([(780, 1840), (LW + 40, 1800), (LW + 40, LH + 40), (740, LH + 40)], (120, 76, 46, 255))   # centre table
    cv.poly([(860, 1780), (1020, 1760), (1040, 1800), (880, 1822)], (236, 232, 222, 255))           # newspaper
    cv.rect(840, 1730, 900, 1760, (40, 40, 44, 255))                                             # TV remote
    cv.blur(8)
    return cv


def _tv_light(k):
    """fn for a dynamic screen layer: the TV picture flickering, its glow on the wall and floor."""
    x0, y0, x1, y1 = TV
    pals = [(120, 170, 255), (255, 200, 140), (170, 255, 190), (255, 150, 170), (210, 220, 255)]

    def fn(_im, t):
        cut = int(t / 2.3)
        c0, c1 = pals[cut % len(pals)], pals[(cut * 3 + 1) % len(pals)]
        b = 0.62 + 0.22 * math.sin(t * 3.1) + 0.12 * math.sin(t * 7.7 + 1.0)
        cv = Cv(k, fill=c0 + (0,))
        cv.rect(x0 + 12, y0 + 12, x1 - 12, (y0 + y1) / 2, c0 + (int(150 * b),))
        cv.rect(x0 + 12, (y0 + y1) / 2, x1 - 12, y1 - 12, c1 + (int(130 * b),))
        cv.glow((x0 + x1) / 2, (y0 + y1) / 2, 300, mix(c0, c1, 0.5), int(46 * b))
        cv.poly([(x0, 1310), (x1, 1310), (x1 + 140, 1560), (x0 - 140, 1560)], mix(c0, c1, 0.5) + (int(30 * b),))
        cv.blur(6)
        return cv.im
    return fn


def room_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    outside = _room_outside(0.5 * s)
    room, light = _room(kr, kg)
    fg = _room_front(0.5 * s)
    empty = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    back = [
        Layer(outside.im, 0.5 * s, 0.12, None, "outside"),
        Layer(room.im, kr, 1.0, None, "room"),
        Layer(light.im, kg, 1.0, None, "sunlight", mode="screen"),
        Layer(empty, kg, 1.0, _tv_light(kg), "tv", mode="screen"),
        Layer(empty, 0.3 * s, 1.0, motes(((300, 660), (640, 1500), 240), 0.3 * s), "dust", mode="screen"),
        Layer(empty, 0.7 * s, 1.0, fan(560, 300, 0.7 * s, R=230, top=72), "fan"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    light_cfg = {"ambient": [255, 248, 238], "dir": -1, "vignette": 0.26}
    return Layered(back, front, light=light_cfg, horizon=ROOM_VP[1], ground=ROOM_FLOOR)


# ------------------------------------------------------------------ classroom
CLASS_VP = (520, 800)
CLASS_FLOOR = 1290
BOARD = (110, 380, 740, 800)
CLASS_WIN = (812, 430, 1036, 860)
CHALK_LINES = [("HOMEWORK", 1.0, 0.05), ("Q1.  25 x 4 = ?", 0.82, 0.08), ("Q2.  Bharat ki rajdhani?", 0.82, 0.08),
               ("Kal TEST hai !!", 0.9, 0.2)]


def _class_outside(k):
    """Through the window: sky, the school ground, a big tree, the next school block. Far + blurred."""
    cv = Cv(k)
    cv.im = vgrad(k, [(0, (100, 166, 230)), (420, (136, 192, 240)), (760, (214, 232, 246)), (LH, (214, 232, 246))])
    cv.d = ImageDraw.Draw(cv.im)
    rnd = random.Random(11)
    for (cx, cy, w) in ((880, 500, 140),):
        for _ in range(5):
            cv.ell(cx + rnd.uniform(-w / 2, w / 2), cy + rnd.uniform(-12, 12), w * 0.3, w * 0.19, (255, 255, 255, 230))
    cv.rect(700, 600, 1100, 800, (226, 190, 150, 255))                         # the next block
    cv.rect(690, 588, 1110, 604, (196, 150, 120, 255))
    for wx in range(720, 1100, 60):
        for wy in (630, 710):
            cv.rect(wx, wy, wx + 34, wy + 46, (110, 120, 140, 255))
    cv.rect(700, 800, 1100, 1200, (150, 186, 96, 255))                         # the ground
    for gx in range(720, 1100, 36):
        cv.line([(gx, 840), (gx - 6, 1200)], (130, 170, 84, 255), 3)
    for _ in range(16):                                                        # a big tree
        cv.ell(960 + rnd.uniform(-100, 90), 640 + rnd.uniform(-70, 70), rnd.uniform(36, 60), rnd.uniform(30, 50),
               mix((60, 130, 60), (120, 176, 86), rnd.random()) + (255,))
    cv.rect(950, 680, 970, 860, (100, 76, 56, 255))
    cv.blur(3.5)
    return cv


def _chalk_board(cv):
    """The blackboard: texture, chalk smudges, the writing, a doodle, the ledge with chalk and a duster."""
    from ..text import font
    x0, y0, x1, y1 = BOARD
    cv.rect(x0 - 18, y0 - 18, x1 + 18, y1 + 18, (132, 88, 52, 255), INK, 3)
    fill_tex(cv, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], (40, 76, 60), seed=4, cell=18, lo=0.9, hi=1.1)
    rnd = random.Random(3)
    for _ in range(6):                                                          # old rubbed-out chalk
        cx, cy = rnd.uniform(x0 + 80, x1 - 80), rnd.uniform(y0 + 60, y1 - 60)
        cv.ell(cx, cy, rnd.uniform(60, 120), rnd.uniform(18, 34), (200, 210, 200, 22))
    w, h = int((x1 - x0) * 2), int((y1 - y0) * 2)                               # writing, at 2 px per unit
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    y = 40
    for (text, size, indent) in CHALK_LINES:
        f = font(int(86 * size))
        d.text((int(w * indent), y), text, font=f, fill=(238, 240, 232, 225))
        y += int(86 * size * 1.45)
    d.text((int(w * 0.66), 26), "Date: ____", font=font(54), fill=(238, 240, 232, 200))
    cx, cy, r = int(w * 0.82), int(h * 0.74), 70                               # a smiley doodle
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(250, 230, 120, 220), width=8)
    d.ellipse([cx - 30, cy - 24, cx - 14, cy - 8], fill=(250, 230, 120, 220))
    d.ellipse([cx + 14, cy - 24, cx + 30, cy - 8], fill=(250, 230, 120, 220))
    d.arc([cx - 40, cy - 30, cx + 40, cy + 40], 20, 160, fill=(250, 230, 120, 220), width=8)
    quad_image(cv, im, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    cv.rect(x0 - 24, y1 + 18, x1 + 24, y1 + 34, (120, 80, 48, 255), INK, 2)      # ledge
    for i, cx_ in enumerate((200, 230, 262)):
        cv.rect(cx_, y1 + 8, cx_ + 22, y1 + 18, ((246, 246, 240), (250, 220, 120), (240, 160, 170))[i] + (255,))
    cv.rect(620, y1 + 2, 700, y1 + 18, (60, 60, 140, 255), INK, 2)              # duster
    cv.rect(620, y1 - 6, 700, y1 + 2, (150, 110, 70, 255), INK, 2)


def _bench(cv, vp, x0, x1, yb, floor_y, col=(150, 100, 60)):
    """A wooden student desk with its bench, standing on the floor at yb (front-bottom), in perspective."""
    sc = (yb - vp[1]) / float(floor_y - vp[1])
    h = 200 * sc
    depth = 0.16
    top_f = yb - h
    tl, tr = (x0, top_f), (x1, top_f)
    cv.poly([toward(tl, vp, depth), toward(tr, vp, depth), tr, tl], mul(col, 1.15) + (255,), INK, 3)  # desk top
    cv.rect(x0, top_f, x1, top_f + 70 * sc, col + (255,), INK, 3)                                       # front panel
    for lx in (x0 + 10 * sc, x1 - 24 * sc):
        cv.rect(lx, top_f + 70 * sc, lx + 14 * sc, yb, mul(col, 0.7) + (255,), INK, 2)
    _shadow(cv, (x0 + x1) / 2, yb + 2, (x1 - x0) * 0.55, 12 * sc, 70)


def _classroom(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(255, 236, 190, 0))
    vp, F = CLASS_VP, CLASS_FLOOR
    # walls: cream above, green dado below
    fill_tex(cv, [(0, 0), (LW, 0), (LW, 930), (0, 930)], [(0, (240, 230, 196)), (930, (232, 220, 182))],
             seed=5, cell=60, lo=0.96, hi=1.035)
    fill_tex(cv, [(0, 930), (LW, 930), (LW, F), (0, F)], [(930, (112, 166, 126)), (F, (98, 148, 112))],
             seed=6, cell=50, lo=0.95, hi=1.04)
    cv.line([(0, 930), (LW, 930)], (70, 110, 80, 255), 6)
    cv.rect(0, 0, LW, 56, (246, 242, 232, 255))
    cv.rect(0, 56, LW, 66, (210, 196, 160, 255))
    cv.rect(0, F - 24, LW, F, (80, 120, 90, 255), INK, 2)
    _tube_light(cv, light, 260, 520, 160)

    _chalk_board(cv)
    _clock(cv, 560, 300, 42, rim=(40, 60, 120))
    cv.rect(30, 960, 84, 1040, (246, 244, 236, 255), INK, 2)                    # switchboard
    for i in range(3):
        cv.rect(40 + i * 14, 976, 48 + i * 14, 994, (60, 60, 60, 255))
    cv.rect(26, 250, 96, 306, (60, 60, 64, 255), INK, 2)                        # school bell speaker
    cv.ell(61, 278, 18, 18, (40, 40, 44, 255))

    # window onto the school ground, with sunlight going down to the left
    x0, y0, x1, y1 = CLASS_WIN
    _window(cv, light, ((360, 1360), (660, 1360), (520, 1640), (120, 1640)), x0, y0, x1, y1, bars_v=5, bars_h=3,
            frame=(110, 150, 120))

    # teacher's table with books, register and a globe
    _box(cv, vp, 470, 820, 1080, F, (140, 92, 56), side=0.08)
    cv.rect(500, 1110, 790, 1170, None, (100, 64, 40, 255), 3)
    cv.line([(630, 1140), (660, 1140)], (226, 220, 210, 255), 6)
    for i, (bw, col) in enumerate(((150, (200, 60, 60)), (136, (60, 100, 170)), (144, (240, 190, 60)))):
        cv.rect(500 + i * 4, 1060 - i * 22, 500 + bw + i * 4, 1080 - i * 22, col + (255,), INK, 2)
    cv.rect(660, 1066, 740, 1080, (40, 120, 90, 255), INK, 2)                   # register
    cv.rect(756, 1056, 784, 1080, (90, 90, 96, 255), INK, 2)                    # globe stand
    cv.ell(770, 1000, 44, 44, (70, 140, 210, 255), INK, 3)
    _leaves(cv, 5, 740, 800, 970, 1030, 16, ((70, 160, 80), (120, 180, 90)), 2)
    cv.line([(728, 1000), (812, 1000)], (230, 200, 90, 255), 3)
    _shadow(cv, 645, F + 2, 200, 14)

    # floor and the benches
    _floor_tiles(cv, vp, F, (206, 200, 188), (190, 184, 172), step=100, grow=1.22)
    cv.rect(0, F, LW, F + 3, (110, 100, 90, 120))
    _bench(cv, vp, -40, 250, 1420, F)
    _bench(cv, vp, -120, 200, 1610, F)
    _bench(cv, vp, 880, 1140, 1440, F)
    cv.blur(0.35)
    return cv, light


def _class_front(k):
    cv = Cv(k, fill=(140, 92, 56, 0))
    cv.poly([(-40, 1780), (300, 1810), (330, LH + 40), (-40, LH + 40)], (150, 100, 60, 255))     # a front desk
    cv.poly([(40, 1760), (220, 1772), (230, 1830), (30, 1820)], (250, 250, 244, 255))           # open notebook
    cv.line([(130, 1764), (130, 1826)], (180, 180, 190, 255), 3)
    cv.line([(240, 1750), (330, 1790)], (240, 190, 50, 255), 10)                                # pencil
    cv.poly([(900, 1700), (LW + 40, 1680), (LW + 40, LH + 40), (880, LH + 40)], (50, 90, 170, 255))  # school bag
    cv.rect(930, 1760, 1060, 1860, (40, 70, 140, 255))
    cv.blur(8)
    return cv


def classroom_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    outside = _class_outside(0.5 * s)
    room, light = _classroom(kr, kg)
    fg = _class_front(0.5 * s)
    empty = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    back = [
        Layer(outside.im, 0.5 * s, 0.12, None, "outside"),
        Layer(room.im, kr, 1.0, None, "classroom"),
        Layer(light.im, kg, 1.0, None, "sunlight", mode="screen"),
        Layer(empty, 0.3 * s, 1.0, motes(((920, 640), (400, 1500), 260), 0.3 * s, n=60, seed=5), "chalk dust",
              mode="screen"),
        Layer(empty, 0.7 * s, 1.0, fan(290, 290, 0.7 * s, R=190, top=66, speed=2.4), "fan"),
        Layer(empty, 0.7 * s, 1.0, fan(830, 290, 0.7 * s, R=190, top=66, speed=2.9), "fan2"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    light_cfg = {"ambient": [255, 249, 240], "dir": 1, "vignette": 0.24}
    return Layered(back, front, light=light_cfg, horizon=CLASS_VP[1], ground=CLASS_FLOOR)

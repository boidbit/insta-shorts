"""Hand-made 2.5D sets: a festival street at night, a railway platform, a village.

festival_25d  a lit-up street at night: fireworks in the sky, the festive city far away, a row of old houses with
              strings of lights down their faces and paper lanterns, a glowing MITHAI shop, strings of bulbs across
              the street that twinkle, a balloon seller's balloons bobbing, soft bokeh in front.
railway_25d   a station platform by day, looking across the tracks: the far platform with its shed and the yellow
              DESIPUR JN board, two tracks with sleepers, a train that rushes through now and then, our own
              platform with its yellow line, a hanging clock and a pillar, a blurred pillar and a suitcase in front.
gaon_25d      a village by day: hills and fields far away, a mustard field with a hut, a mud house with a tiled
              roof and smoke from its chulha, a hand pump, a haystack, a neem tree, clothes on a line, hens pecking.
(festival and railway have writing on them, so a reverse shot never mirrors them.)
"""
import math
import random

from PIL import Image, ImageDraw

from .scenery import (PAL_BULB, Cv, Layer, Layered, _far_city, _fireworks, _sky, along, birds, catenary, fill_tex,
                      mix, mul, quad_image, sign_image, steam, twinkle, vgrad)
from .scenery_home import _leaves
from .scenery_road import day_sky, gx, skyline
from ..util import LH, LW

INK = (44, 36, 40, 255)


def _blank(k, fill=(0, 0, 0, 0)):
    return Image.new("RGBA", (8, 8), fill)


# ------------------------------------------------------------------ festival street (night)
FEST_GROUND = 1260
FEST_VP = (540, 880)
LANTERNS = [(170, 780), (420, 700), (690, 760), (930, 690)]
BALLOONS = (930, 1180)                        # where the balloon seller's stick stands (top of the stick)


def _fest_houses(k, kg):
    cv = Cv(k, blend=True)
    gA = Cv(kg, fill=(255, 190, 110, 0))
    gB = Cv(kg, fill=(255, 190, 110, 0))
    gS = Cv(kg, fill=(255, 190, 110, 0))
    rnd = random.Random(91)
    houses = [(-30, 330, 430, (92, 70, 104)), (330, 760, 520, (110, 78, 92)), (760, 1110, 400, (84, 74, 112))]
    for (x0, x1, top, col) in houses:
        cv.rect(x0, top, x1, FEST_GROUND, col + (255,), INK, 3)
        cv.rect(x0 - 8, top - 16, x1 + 8, top + 4, mul(col, 0.8) + (255,), INK, 2)
        y = top + 50
        while y < 940:
            for wx in range(int(x0) + 34, int(x1) - 90, 120):
                lit = rnd.random() < 0.7
                wc = rnd.choice(((255, 206, 128), (255, 226, 160), (255, 180, 100))) if lit else mul(col, 0.6)
                cv.rect(wx - 6, y - 6, wx + 76, y + 106, mul(col, 0.8) + (255,), INK, 2)
                cv.rect(wx, y, wx + 70, y + 100, wc + (255,))
                cv.line([(wx + 35, y), (wx + 35, y + 100)], mul(col, 0.6) + (255,), 3)
                if lit:
                    gS.glow(wx + 35, y + 50, 90, wc, 60)
            cv.rect(x0 - 6, y + 118, x1 + 6, y + 132, mul(col, 1.2) + (255,), INK, 2)   # balcony slab
            for bx in range(int(x0), int(x1), 22):                       # balcony railing
                cv.line([(bx, y + 132), (bx, y + 160)], mul(col, 1.3) + (255,), 2)
            cv.line([(x0, y + 160), (x1, y + 160)], mul(col, 1.3) + (255,), 3)
            y += 190
        # strings of lights down the face (two groups that twinkle in turn)
        xs = list(range(int(x0) + 16, int(x1) - 8, 24))
        for i, sx in enumerate(xs):
            L = 160 + 60 * math.sin(i * 0.9 + x0) + rnd.uniform(0, 90)
            c = PAL_BULB[(i + int(x0)) % len(PAL_BULB)]
            g = gA if i % 2 else gB
            for (bx, by) in along([(sx, top + 6), (sx, top + 6 + L)], 16):
                g.ell(bx, by, 4.6, 4.6, c + (240,))
                gS.ell(bx, by, 9, 9, c + (40,))
        for (bx, by) in along(catenary(x0, top - 4, x1, top - 4, 26), 16):
            gA.ell(bx, by, 5, 5, PAL_BULB[int(bx) % len(PAL_BULB)] + (240,))
    # the MITHAI shop on the ground floor of the middle house
    sx0, sx1 = 380, 720
    quad_image(cv, sign_image("MITHAI", (250, 170, 40), (120, 30, 30), 800, 200),
               [(sx0 + 40, 1000), (sx1 - 40, 1000), (sx1 - 40, 1060), (sx0 + 40, 1060)])
    cv.rect(sx0, 1070, sx1, FEST_GROUND, (250, 214, 150, 255), INK, 3)
    for ry in (1110, 1160):
        cv.rect(sx0 + 12, ry, sx1 - 12, ry + 6, (170, 120, 70, 255))
        for j in range(9):
            cx = sx0 + 34 + j * 34
            cv.ell(cx, ry - 10, 12, 10, ((250, 200, 80), (250, 150, 60), (250, 240, 220), (230, 120, 150))[j % 4]
                   + (255,), INK, 1)
    cv.rect(sx0 + 10, 1196, sx1 - 10, FEST_GROUND, (200, 226, 236, 255), INK, 2)   # glass counter
    gS.glow((sx0 + sx1) / 2, 1150, 260, (255, 210, 140), 80)
    # closed shutters of the side houses, decorated with flower strings
    for (x0, x1) in ((30, 290), (800, 1060)):
        cv.rect(x0, 1060, x1, FEST_GROUND, (120, 110, 120, 255), INK, 2)
        for yy in range(1070, FEST_GROUND, 12):
            cv.line([(x0 + 2, yy), (x1 - 2, yy)], (96, 88, 100, 255), 2)
        for (fx, fy) in along(catenary(x0, 1060, x1, 1060, 40), 14):
            cv.ell(fx, fy, 7, 7, (250, 150, 30, 255))
    # the street: paving with the lights' reflections
    fill_tex(cv, [(-10, FEST_GROUND), (LW + 10, FEST_GROUND), (LW + 10, LH), (-10, LH)],
             [(FEST_GROUND, (84, 70, 92)), (LH, (52, 46, 64))], seed=93, cell=16, lo=0.9, hi=1.08)
    for x in range(-900, 2000, 110):
        cv.line([(gx(x, FEST_GROUND, FEST_GROUND, FEST_VP), FEST_GROUND), (gx(x, FEST_GROUND, LH, FEST_VP), LH)],
                (60, 50, 70, 200), 2)
    for y in (1320, 1420, 1570, 1780):
        cv.line([(-10, y), (LW + 10, y)], (60, 50, 70, 200), 2)
    for (cx, w) in ((550, 300), (170, 180), (920, 160)):
        gS.ell(cx, 1420, w, 60, (255, 190, 110, 40))                        # warm pools on the street
    # lanterns hanging from the balconies (with their glow)
    for (lx, ly) in LANTERNS:
        cv.line([(lx, ly - 70), (lx, ly - 24)], (60, 50, 50, 255), 2)
        cv.poly([(lx, ly - 30), (lx + 26, ly), (lx, ly + 34), (lx - 26, ly)], (240, 90, 60, 255), INK, 2)
        cv.poly([(lx - 10, ly + 30), (lx + 10, ly + 30), (lx + 6, ly + 70), (lx - 6, ly + 70)], (250, 200, 60, 255))
        gS.glow(lx, ly, 90, (255, 150, 90), 90)
    # strings of bulbs across the street
    for (y0, y1, sag) in ((140, 220, 140), (320, 260, 120)):
        pts = catenary(-40, y0, 1120, y1, sag)
        cv.line(pts, (40, 30, 40, 255), 2)
        for i, (bx, by) in enumerate(along(pts, 30)):
            g = gA if i % 2 else gB
            c = PAL_BULB[i % len(PAL_BULB)]
            g.ell(bx, by + 6, 6, 6, c + (250,))
            gS.ell(bx, by + 6, 14, 14, c + (46,))
    # the balloon seller's stick
    bx, by = BALLOONS
    cv.rect(bx - 6, by, bx + 6, FEST_GROUND + 40, (170, 130, 80, 255), INK, 2)
    for b in (gA, gB, gS):
        b.blur(1.0)
    gS.blur(14)
    return cv, gA, gB, gS


def _balloons(k):
    """fn: the balloon seller's bunch of balloons, bobbing on their strings."""
    bx, by = BALLOONS
    rnd = random.Random(97)
    bal = [(rnd.uniform(-90, 90), rnd.uniform(-260, -120), rnd.choice(((240, 60, 80), (250, 200, 50),
                                                                       (80, 160, 240), (120, 220, 120),
                                                                       (240, 120, 220), (250, 140, 40))),
            rnd.uniform(0, 6.28)) for _ in range(9)]

    def fn(_im, t):
        cv = Cv(k, fill=(240, 60, 80, 0))
        for (dx, dy, col, ph) in sorted(bal, key=lambda b: b[1]):
            x = bx + dx + math.sin(t * 1.3 + ph) * 8
            y = by + dy + math.cos(t * 1.1 + ph) * 6
            cv.line([(bx, by), (x, y + 34)], (230, 230, 230, 255), 1.5)
            cv.ell(x, y, 30, 36, col + (255,), INK, 2)
            cv.ell(x - 10, y - 12, 7, 10, (255, 255, 255, 150))
        return cv.im
    return fn


def _fest_front(k):
    cv = Cv(k, fill=(255, 190, 110, 0), blend=True)
    rnd = random.Random(99)
    for _ in range(16):                                                  # big soft bokeh
        x = rnd.choice((rnd.uniform(-60, 260), rnd.uniform(820, 1140)))
        y = rnd.uniform(-40, 360) if rnd.random() < 0.7 else rnd.uniform(1760, 1960)
        r = rnd.uniform(26, 60)
        cv.ell(x, y, r, r, rnd.choice(PAL_BULB) + (int(rnd.uniform(90, 160)),))
    cv.blur(6)
    return cv


def festival_25d(s, zmax=1.0):
    kb = 0.5 * s
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    sky = _sky(kb)
    far = _far_city(0.6 * s)
    st, gA, gB, gS = _fest_houses(kr, kg)
    fg = _fest_front(0.5 * s)
    back = [
        Layer(sky.im, kb, 0.0, _fireworks(sky.im, kb), "sky"),
        Layer(far.im, 0.6 * s, 0.14, None, "far"),
        Layer(st.im, kr, 1.0, None, "set"),
        Layer(gA.im, kg, 1.0, twinkle((gA.im, gB.im), 0.8, static=gS.im), "street_glow", mode="screen"),
        Layer(_blank(0.5 * s), 0.5 * s, 1.0, _balloons(0.5 * s), "balloons"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "bokeh")]               # (a front layer is never "screen")
    return Layered(back, front, light={"ambient": [236, 220, 226], "dir": -1, "vignette": 0.4},
                   horizon=FEST_VP[1], ground=FEST_GROUND)


# ------------------------------------------------------------------ railway platform
RAIL_VP = (540, 860)
FAR_EDGE, FAR_FACE = 1020, 1100              # the far platform's top edge, the foot of its face
TRACKS = ((1130, 1170), (1220, 1272))        # (far rail y, near rail y) of each track
NEAR_EDGE = 1300                              # our platform's edge
TRAIN_FIRST, TRAIN_EVERY, TRAIN_PASS = 7.0, 26.0, 3.2


def _station_far(k):
    """The far side: trees and the town beyond the station (far layer)."""
    cv = skyline(k, seed=13, tops=(520, 700), base=1000, tint=(160, 178, 196))
    _leaves(cv, 60, -40, LW + 40, 700, 860, 44, ((80, 130, 80), (120, 160, 110)), 17)
    cv.blur(1.6)
    return cv


def _tracks(k, kg):
    """The far platform with its shed and board, and the two tracks (behind the train)."""
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(255, 236, 190, 0), blend=True)
    # the far platform's shed
    for x in (60, 330, 600, 870):
        cv.rect(x - 9, 640, x + 9, FAR_EDGE, (90, 110, 120, 255), INK, 2)
    cv.poly([(-20, 600), (LW + 20, 600), (LW + 20, 646), (-20, 646)], (120, 140, 150, 255), INK, 3)
    for x in range(-20, LW + 20, 26):
        cv.line([(x, 602), (x, 644)], (100, 120, 130, 255), 2)
    cv.rect(-20, 646, LW + 20, 664, (80, 96, 106, 255), INK, 2)
    quad_image(cv, sign_image("DESIPUR JN", (250, 210, 40), (30, 30, 30), 1000, 220),
               [(380, 760), (700, 760), (700, 830), (380, 830)])
    for x in (420, 660):
        cv.rect(x - 5, 830, x + 5, FAR_EDGE, (60, 60, 66, 255))
    for bx in (140, 860):                                                # benches
        cv.rect(bx - 60, 960, bx + 60, 976, (60, 110, 160, 255), INK, 2)
        cv.rect(bx - 60, 930, bx + 60, 944, (60, 110, 160, 255), INK, 2)
        for lx in (bx - 50, bx + 50):
            cv.rect(lx - 4, 976, lx + 4, FAR_EDGE, (60, 60, 66, 255))
    # its surface and its face
    cv.rect(-20, FAR_EDGE - 30, LW + 20, FAR_EDGE, (196, 190, 180, 255), INK, 2)
    cv.rect(-20, FAR_EDGE - 8, LW + 20, FAR_EDGE, (240, 200, 50, 255))
    fill_tex(cv, [(-20, FAR_EDGE), (LW + 20, FAR_EDGE), (LW + 20, FAR_FACE), (-20, FAR_FACE)],
             [(FAR_EDGE, (150, 146, 140)), (FAR_FACE, (120, 116, 112))], seed=101, cell=14, lo=0.9, hi=1.08)
    cv.line([(-20, FAR_FACE), (LW + 20, FAR_FACE)], INK, 2)
    # the track bed and the two tracks
    fill_tex(cv, [(-20, FAR_FACE), (LW + 20, FAR_FACE), (LW + 20, NEAR_EDGE + 40), (-20, NEAR_EDGE + 40)],
             [(FAR_FACE, (130, 118, 106)), (NEAR_EDGE, (112, 100, 90))], seed=103, cell=5, lo=0.75, hi=1.2)
    for (ya, yb) in TRACKS:
        for x in range(-900, 2000, 46):                                  # sleepers, running to the vanishing point
            a0, a1 = gx(x, ya, ya - 4, RAIL_VP), gx(x + 22, ya, ya - 4, RAIL_VP)
            b0, b1 = gx(x + 22, ya, yb + 6, RAIL_VP), gx(x, ya, yb + 6, RAIL_VP)
            cv.poly([(a0, ya - 4), (a1, ya - 4), (b0, yb + 6), (b1, yb + 6)], (110, 96, 84, 255), (70, 60, 54, 255), 1)
        for y in (ya, yb):                                               # the rails
            cv.rect(-20, y - 7, LW + 20, y + 1, (150, 150, 156, 255), INK, 1)
            cv.line([(-20, y - 6), (LW + 20, y - 6)], (230, 232, 236, 255), 2)
    for (x0, x1) in ((200, 360), (640, 780)):
        light.poly([(x0 + 260, -40), (x1 + 260, -40), (x1 - 60, 1300), (x0 - 60, 1300)], (255, 236, 190, 40))
    light.blur(30)
    return cv, light


def _train_strip(k):
    """One long train (engine + coaches) pre-drawn once; the train layer only slides it."""
    coach, n = 760, 4
    W = 300 + coach * n
    top, bot = 760, TRACKS[0][0] - 6
    cv = Cv(k, w=W, h=LH, blend=True)
    blue, cream = (40, 80, 150), (236, 226, 200)
    # the engine (at the left: the train runs to the left)
    cv.poly([(10, bot - 30), (40, top + 40), (120, top), (300, top), (300, bot - 30)], (200, 70, 40, 255), INK, 3)
    cv.rect(60, top + 60, 150, top + 140, (180, 210, 230, 255), INK, 2)
    cv.rect(10, bot - 70, 300, bot - 50, cream + (255,))
    cv.ell(40, top + 190, 14, 14, (255, 240, 180, 255), INK, 2)
    for i in range(n):
        x0 = 300 + i * coach + 8
        x1 = x0 + coach - 16
        cv.rect(x0, top + 6, x1, bot - 30, blue + (255,), INK, 3)
        cv.rect(x0, top + 6, x1, top + 30, mul(blue, 0.8) + (255,))
        cv.rect(x0, bot - 90, x1, bot - 74, cream + (255,))
        for wx in range(int(x0) + 90, int(x1) - 60, 70):                 # windows with bars
            cv.rect(wx, top + 70, wx + 46, top + 140, (60, 70, 90, 255), INK, 2)
            for b in range(1, 4):
                cv.line([(wx, top + 70 + b * 17), (wx + 46, top + 70 + b * 17)], (180, 180, 186, 255), 2)
        for dx in (20, coach - 76):                                      # doors
            cv.rect(x0 + dx, top + 50, x0 + dx + 50, bot - 34, mul(blue, 0.85) + (255,), INK, 2)
        cv.rect(x1, top + 80, x1 + 16, bot - 60, (50, 50, 56, 255))      # the gangway
    for x in range(40, W - 40, 190):                                     # bogies and wheels
        cv.rect(x - 10, bot - 30, x + 110, bot - 10, (40, 40, 44, 255))
        for wx in (x + 10, x + 90):
            cv.ell(wx, bot - 8, 22, 22, (50, 50, 56, 255), INK, 2)
    return cv.im, W


def _train(k):
    strip, W = _train_strip(k)
    speed = (W + LW) / TRAIN_PASS

    def fn(_im, t):
        ph = t - TRAIN_FIRST
        if ph < 0:
            return _im
        ph %= TRAIN_EVERY
        if ph > TRAIN_PASS:
            return _im
        x = int((LW - ph * speed) * k)                                   # comes in from the right
        out = Image.new("RGBA", (int(round(LW * k)), int(round(LH * k))), (40, 80, 150, 0))
        a, b = max(0, -x), min(strip.width, out.width - x)
        if b > a:
            out.alpha_composite(strip.crop((a, 0, b, min(strip.height, out.height))), dest=(x + a, 0))
        return out
    return fn


def _platform(k):
    """Our platform (in front of the tracks and the train): tiles, the yellow line, the roof above, a pillar,
    the hanging clock."""
    cv = Cv(k, blend=True)
    fill_tex(cv, [(-20, NEAR_EDGE), (LW + 20, NEAR_EDGE), (LW + 20, LH), (-20, LH)],
             [(NEAR_EDGE, (206, 200, 190)), (LH, (176, 170, 160))], seed=107, cell=20, lo=0.93, hi=1.05)
    cv.rect(-20, NEAR_EDGE, LW + 20, NEAR_EDGE + 22, (226, 222, 214, 255), INK, 2)   # the coping stones
    cv.rect(-20, NEAR_EDGE + 44, LW + 20, NEAR_EDGE + 74, (244, 204, 50, 255))       # the yellow line
    for x in range(-20, LW + 20, 18):
        cv.ell(x + 9, NEAR_EDGE + 59, 4, 4, (220, 180, 40, 255))
    for x in range(-1400, 2600, 150):
        cv.line([(gx(x, NEAR_EDGE + 74, NEAR_EDGE + 74, RAIL_VP), NEAR_EDGE + 74),
                 (gx(x, NEAR_EDGE + 74, LH, RAIL_VP), LH)], (170, 164, 156, 255), 2)
    for y in (1450, 1600, 1800):
        cv.line([(-20, y), (LW + 20, y)], (170, 164, 156, 255), 2)
    # our roof (we stand under it)
    cv.poly([(-20, -10), (LW + 20, -10), (LW + 20, 150), (-20, 190)], (110, 120, 126, 255), INK, 3)
    for x in range(-20, LW + 40, 120):
        cv.line([(x, 0), (x - 10, 180)], (80, 90, 96, 255), 6)
    cv.rect(-20, 150, LW + 20, 176, (70, 80, 86, 255), INK, 2)
    # the pillar on the left with a PF 1 board, and the clock hanging from the roof
    cv.rect(40, 150, 100, 1500, (150, 60, 50, 255), INK, 3)
    cv.rect(30, 1460, 110, 1500, (120, 50, 40, 255), INK, 2)
    quad_image(cv, sign_image("PF 1", (240, 240, 236), (30, 30, 30), 300, 180), [(104, 560), (220, 560),
                                                                               (220, 630), (104, 630)])
    cv.line([(760, 176), (760, 270)], (60, 60, 66, 255), 4)
    cv.rect(700, 270, 820, 290, (60, 60, 66, 255))
    cv.ell(760, 340, 54, 54, (250, 250, 246, 255), INK, 4)
    for i in range(12):
        a = i * math.pi / 6
        cv.line([(760 + 44 * math.cos(a), 340 + 44 * math.sin(a)), (760 + 50 * math.cos(a), 340 + 50 * math.sin(a))],
                (40, 40, 44, 255), 2)
    cv.line([(760, 340), (760, 306)], (40, 40, 44, 255), 4)
    cv.line([(760, 340), (786, 352)], (40, 40, 44, 255), 4)
    # a bench by the pillar
    cv.rect(130, 1400, 380, 1420, (60, 110, 160, 255), INK, 2)
    cv.rect(130, 1350, 380, 1366, (60, 110, 160, 255), INK, 2)
    for lx in (150, 360):
        cv.rect(lx - 5, 1420, lx + 5, 1480, (60, 60, 66, 255))
    return cv


def _second_hand(k, cx=760, cy=340, r=42):
    """fn: the platform clock's red seconds hand, sweeping round."""
    def fn(_im, t):
        cv = Cv(k, fill=(200, 30, 30, 0))
        a = (t * 6.0 + 120.0) * math.pi / 180.0 - math.pi / 2
        cv.line([(cx - 10 * math.cos(a), cy - 10 * math.sin(a)), (cx + r * math.cos(a), cy + r * math.sin(a))],
                (210, 30, 30, 255), 2.5)
        cv.ell(cx, cy, 5, 5, (210, 30, 30, 255))
        return cv.im
    return fn


def _rail_front(k):
    cv = Cv(k, fill=(150, 60, 50, 0), blend=True)
    cv.rect(990, -40, 1130, 1960, (140, 56, 46, 255))                       # a pillar right in front
    cv.rect(975, 1820, 1140, 1960, (110, 44, 36, 255))
    cv.rect(-60, 1700, 170, 1960, (50, 70, 120, 255))                        # a suitcase
    cv.rect(10, 1660, 100, 1700, None, (30, 30, 34, 255), 10)
    cv.blur(9)
    return cv


def railway_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    sky = day_sky(0.5 * s, sun=(260, 300), seed=11)
    far = _station_far(0.5 * s)
    tr, light = _tracks(kr, kg)
    pf = _platform(kr)
    fg = _rail_front(0.5 * s)
    back = [
        Layer(sky.im, 0.5 * s, 0.0, None, "sky"),
        Layer(far.im, 0.5 * s, 0.2, None, "far"),
        Layer(tr.im, kr, 1.0, None, "tracks"),
        Layer(light.im, kg, 1.0, None, "sunlight", mode="screen"),
        Layer(_blank(0.5 * s), 0.5 * s, 1.0, _train(0.5 * s), "train"),
        Layer(pf.im, kr, 1.0, None, "set"),
        Layer(_blank(0.5 * s), 0.5 * s, 1.0, _second_hand(0.5 * s), "clock"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return Layered(back, front, light={"ambient": [252, 250, 244], "dir": -1, "vignette": 0.24},
                   horizon=RAIL_VP[1], ground=NEAR_EDGE)


# ------------------------------------------------------------------ gaon (village)
GAON_GROUND = 1240
GAON_VP = (540, 900)
CHIMNEY = (300, 520)


def _hills(k):
    cv = Cv(k, blend=True)
    cv.im = vgrad(k, [(0, (90, 160, 226)), (600, (150, 200, 240)), (950, (230, 236, 226)), (LH, (230, 236, 226))])
    cv.d = ImageDraw.Draw(cv.im)
    g = Cv(k, fill=(255, 244, 210, 0))
    g.glow(240, 300, 300, (255, 246, 214), 120)
    g.blur(24)
    cv.over(g)
    cv.ell(240, 300, 56, 56, (255, 250, 228, 255))
    for (base, amp, col, seed) in ((860, 120, (150, 176, 196), 1), (920, 80, (126, 160, 140), 2)):
        rnd = random.Random(seed)
        pts = [(-20, LH)]
        x = -20
        while x <= LW + 40:
            pts.append((x, base - amp * (0.5 + 0.5 * math.sin(x / 170.0 + seed)) - rnd.uniform(0, 20)))
            x += 40
        pts.append((LW + 40, LH))
        cv.poly(pts, col + (255,))
    _leaves(cv, 50, -40, LW + 40, 900, 990, 30, ((90, 130, 80), (120, 156, 100)), 5)   # a line of far trees
    cv.rect(-20, 980, LW + 20, LH, (150, 176, 110, 255))
    cv.blur(2.0)
    return cv


def _fields(k):
    """Middle layer: a mustard field with a hut and a palm, fields in strips."""
    cv = Cv(k, blend=True)
    for i, (y0, y1, col) in enumerate(((980, 1040, (230, 200, 60)), (1040, 1100, (120, 170, 80)),
                                       (1100, 1180, (240, 210, 70)), (1180, 1300, (110, 160, 70)))):
        cv.rect(-20, y0, LW + 20, y1, col + (255,))
        rnd = random.Random(i)
        for _ in range(60):
            x = rnd.uniform(-20, LW + 20)
            cv.ell(x, rnd.uniform(y0, y1), 6, 3, mul(col, rnd.choice((0.85, 1.12))) + (255,))
    cv.rect(700, 900, 830, 990, (200, 170, 130, 255), INK, 2)                  # a far hut
    cv.poly([(680, 910), (765, 850), (850, 910)], (170, 120, 70, 255), INK, 2)
    cv.rect(750, 940, 776, 990, (90, 60, 40, 255))
    cv.line([(980, 990), (960, 760)], (120, 90, 60, 255), 8)                   # a palm
    for a in range(7):
        ang = -math.pi / 2 + (a - 3) * 0.5
        cv.line([(960, 760), (960 + 80 * math.cos(ang) * 1.4, 760 + 80 * math.sin(ang) + 50)], (70, 130, 60, 255), 8)
    cv.blur(1.0)
    return cv


def _gaon(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(255, 236, 190, 0), blend=True)
    rnd = random.Random(111)
    fill_tex(cv, [(-20, GAON_GROUND), (LW + 20, GAON_GROUND), (LW + 20, LH), (-20, LH)],
             [(GAON_GROUND, (214, 180, 130)), (LH, (190, 150, 100))], seed=113, cell=16, lo=0.88, hi=1.08)
    cv.poly([(470, GAON_GROUND), (640, GAON_GROUND), (gx(640, GAON_GROUND, LH, GAON_VP) + 200, LH),
             (gx(470, GAON_GROUND, LH, GAON_VP) - 100, LH)], (226, 196, 150, 160))   # the beaten path
    for _ in range(70):                                                   # pebbles and grass tufts
        x, y = rnd.uniform(0, LW), rnd.uniform(GAON_GROUND + 10, LH)
        if rnd.random() < 0.6:
            cv.ell(x, y, rnd.uniform(3, 7), rnd.uniform(2, 4), (160, 130, 96, 255))
        else:
            for j in range(4):
                cv.line([(x, y), (x + (j - 1.5) * 6, y - rnd.uniform(14, 26))], (90, 150, 60, 255), 3)
    # the mud house with its tiled roof
    hx0, hx1, htop = -20, 470, 720
    fill_tex(cv, [(hx0, htop), (hx1, htop), (hx1, GAON_GROUND), (hx0, GAON_GROUND)],
             [(htop, (212, 166, 120)), (GAON_GROUND, (190, 140, 96))], seed=115, cell=14, lo=0.9, hi=1.08)
    cv.rect(hx0, htop, hx1, GAON_GROUND, None, INK, 3)
    cv.rect(hx0, GAON_GROUND - 40, hx1, GAON_GROUND, (240, 236, 226, 255), INK, 2)   # whitewashed plinth
    cv.poly([(hx0 - 40, htop + 10), (hx1 + 50, htop + 10), (hx1 - 40, 560), (hx0 + 40, 560)], (190, 80, 50, 255),
            INK, 3)
    for i, y in enumerate(range(574, htop, 22)):                          # rows of roof tiles
        u = (y - 560) / float(htop + 10 - 560)
        xa, xb = hx0 + 40 - 80 * u, hx1 - 40 + 90 * u
        cv.line([(xa, y), (xb, y)], (150, 60, 40, 255), 2)
        for x in range(int(xa) + (i % 2) * 14, int(xb), 28):
            cv.line([(x, y), (x, y + 20)], (160, 66, 44, 255), 2)
    cv.rect(CHIMNEY[0] - 14, CHIMNEY[1], CHIMNEY[0] + 14, CHIMNEY[1] + 60, (150, 110, 90, 255), INK, 2)
    cv.rect(170, 900, 300, GAON_GROUND - 40, (110, 70, 40, 255), INK, 3)   # the door
    cv.line([(235, 900), (235, GAON_GROUND - 40)], (80, 50, 30, 255), 3)
    cv.poly([(160, 900), (310, 900), (300, 880), (170, 880)], (240, 236, 226, 255), INK, 2)
    cv.rect(350, 860, 430, 940, (80, 60, 40, 255), INK, 2)                 # a small window with bars
    for bx in (370, 390, 410):
        cv.line([(bx, 862), (bx, 938)], (40, 30, 24, 255), 3)
    for (cx, cy) in ((60, 820), (110, 860), (60, 900), (110, 940), (420, 1020)):   # painted dots on the wall
        cv.ell(cx, cy, 14, 14, (240, 236, 226, 255))
        cv.ell(cx, cy, 6, 6, (200, 80, 60, 255))
    # a cart wheel leaning on the wall
    cv.ell(400, 1150, 66, 66, None, (100, 70, 40, 255), 10)
    for i in range(8):
        a = i * math.pi / 4
        cv.line([(400, 1150), (400 + 60 * math.cos(a), 1150 + 60 * math.sin(a))], (120, 86, 50, 255), 5)
    # the hand pump
    px, pb = 600, 1290
    cv.rect(px - 50, pb - 16, px + 60, pb, (170, 170, 170, 255), INK, 2)
    cv.rect(px - 12, pb - 170, px + 12, pb - 16, (50, 90, 70, 255), INK, 2)
    cv.poly([(px + 12, pb - 140), (px + 50, pb - 120), (px + 46, pb - 110), (px + 12, pb - 124)], (50, 90, 70, 255),
            INK, 2)
    cv.line([(px - 4, pb - 160), (px - 110, pb - 210)], (50, 90, 70, 255), 7)
    cv.ell(px - 16, pb - 178, 18, 14, (50, 90, 70, 255), INK, 2)
    # the haystack
    cv.poly([(700, 1250), (880, 1250), (850, 1080), (790, 1000), (730, 1080)], (230, 196, 90, 255), INK, 3)
    for i in range(14):
        x = 720 + i * 11
        cv.line([(x, 1240), (x + 8 + (i % 3) * 6, 1060 + abs(i - 7) * 14)], (200, 166, 70, 255), 2)
    # the neem tree
    cv.poly([(940, GAON_GROUND + 10), (1010, GAON_GROUND + 10), (995, 760), (1060, 640), (1040, 630), (980, 720),
             (960, 600), (940, 610), (955, 760)], (120, 90, 64, 255), INK, 3)
    _leaves(cv, 80, 760, 1160, 380, 720, 44, ((50, 116, 50), (100, 160, 70)), 117)
    _leaves(cv, 30, 780, 1100, 380, 560, 34, ((110, 170, 80), (150, 200, 100)), 118)
    # the clothes line from the house to the tree
    pts = catenary(470, 820, 950, 800, 50)
    cv.line(pts, (60, 50, 50, 255), 2)
    for i, (cx, cy) in enumerate(along(pts, 70)[1:-1]):
        col = ((220, 60, 60), (60, 120, 220), (250, 200, 50), (240, 240, 236), (60, 170, 120))[i % 5]
        cv.poly([(cx - 22, cy), (cx + 22, cy), (cx + 18, cy + 60), (cx - 18, cy + 60)], col + (255,), INK, 1)
    # sunlight and the tree's shade
    cv.ell(980, 1290, 210, 40, (60, 50, 30, 60))
    light.poly([(0, -40), (300, -40), (700, 1400), (300, 1400)], (255, 236, 190, 34))
    light.blur(30)
    return cv, light


def _hens(k, n=3, seed=121):
    """fn: hens pecking about on the ground."""
    rnd = random.Random(seed)
    hens = [(rnd.uniform(620, 900), rnd.uniform(1330, 1400), rnd.uniform(0, 6.28), rnd.choice((1, -1)))
            for _ in range(n)]

    def fn(_im, t):
        cv = Cv(k, fill=(240, 236, 226, 0))
        for i, (x0, y0, ph, d) in enumerate(hens):
            x = x0 + math.sin(t * 0.3 + ph) * 40
            peck = max(0.0, math.sin(t * 3 + ph * 2)) ** 4
            col = ((250, 248, 240), (180, 110, 60), (230, 220, 200))[i % 3]
            cv.ell(x, y0 - 30, 32, 24, col + (255,), INK, 2)
            cv.poly([(x - 30 * d, y0 - 40), (x - 50 * d, y0 - 60), (x - 40 * d, y0 - 30)], col + (255,), INK, 2)
            hx, hy = x + 28 * d, y0 - 50 + peck * 34
            cv.ell(hx, hy, 12, 12, col + (255,), INK, 2)
            cv.ell(hx, hy - 12, 6, 6, (220, 40, 40, 255))
            cv.poly([(hx + 10 * d, hy - 2), (hx + 22 * d, hy + 2), (hx + 10 * d, hy + 6)], (240, 170, 40, 255))
            for lx in (x - 8, x + 8):
                cv.line([(lx, y0 - 8), (lx, y0)], (240, 170, 40, 255), 3)
        return cv.im
    return fn


def _gaon_front(k):
    cv = Cv(k, fill=(70, 130, 60, 0), blend=True)
    rnd = random.Random(127)
    for cx in (-20, 60, 980, 1080):                                      # tall grass in the corners
        for j in range(9):
            a = rnd.uniform(-0.5, 0.5)
            L = rnd.uniform(200, 340)
            cv.poly([(cx - 12 + j * 4, 1960), (cx + 12 + j * 4, 1960), (cx + j * 4 + L * math.sin(a), 1960 - L)],
                    mix((60, 120, 50), (130, 170, 80), rnd.random()) + (255,))
    cv.blur(8)
    return cv


def gaon_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    far = _hills(0.5 * s)
    mid = _fields(0.6 * s)
    st, light = _gaon(kr, kg)
    fg = _gaon_front(0.5 * s)
    back = [
        Layer(far.im, 0.5 * s, 0.1, birds(0.5 * s, n=5, y0=300, y1=600), "far"),
        Layer(mid.im, 0.6 * s, 0.45, None, "fields"),
        Layer(st.im, kr, 1.0, None, "set"),
        Layer(light.im, kg, 1.0, None, "sunlight", mode="screen"),
        Layer(_blank(0.3 * s), 0.3 * s, 1.0, steam([(CHIMNEY[0], CHIMNEY[1], 1.0, 0.25)], 0.3 * s,
                                                   color=(226, 226, 230)), "smoke"),
        Layer(_blank(0.5 * s), 0.5 * s, 1.0, _hens(0.5 * s), "hens"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return Layered(back, front, light={"ambient": [255, 248, 236], "dir": -1, "vignette": 0.24},
                   horizon=GAON_VP[1], ground=GAON_GROUND)

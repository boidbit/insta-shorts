"""2.5D desi gali at golden hour: looking down a lane toward the setting sun.

Depth layers: sky (sun, clouds, birds) -> far end of the lane -> middle buildings with bunting and
wires -> near buildings (kirana store, electric pole with a tangle of wires, chai tapri) -> blurred
foreground. The chai-stall counter is a Sprite, so a chaiwala can stand behind it while a customer
stands in front.
"""
import math
import random

from PIL import Image, ImageDraw

from .scenery import (Cv, Layer, Layered, Sprite, along, catenary, fill_tex, mix, mul, quad_image, sign_image,
                      steam, sub_quad, vgrad, birds)
from ..util import LH, LW

VP = (560, 930)
SUN = (582, 760)
INK = (52, 38, 40, 255)
M_BL, M_BR = -0.846, 0.846              # slopes of the lane's left / right base lines (through VP)
HAZE = (250, 170, 120)


def bot_l(x):
    return VP[1] + (x - VP[0]) * M_BL


def bot_r(x):
    return VP[1] + (x - VP[0]) * M_BR


def x_on(m, y):
    return VP[0] + (y - VP[1]) / m


def line_y(m, x):
    return VP[1] + (x - VP[0]) * m


def facade(xa, xb, m_top, side):
    """Quad (tl, tr, br, bl) of a facade between xa < xb whose top edge runs to the VP with slope m_top."""
    bot = bot_l if side == "L" else bot_r
    return [(xa, line_y(m_top, xa)), (xb, line_y(m_top, xb)), (xb, bot(xb)), (xa, bot(xa))]


def _windows(cv, q, rows, cols, rnd, frame=(240, 236, 226), lit_p=0.45, v0=0.12, v1=0.5, side="L"):
    for r in range(rows):
        for c in range(cols):
            u0 = 0.12 + c * (0.76 / cols)
            u1 = u0 + 0.76 / cols * 0.62
            va = v0 + r * ((v1 - v0) / rows)
            vb = va + (v1 - v0) / rows * 0.62
            w = sub_quad(q, u0, va, u1, vb)
            lit = rnd.random() < lit_p
            cv.poly(w, (frame + (255,)), INK, 2)
            inner = sub_quad(q, u0 + 0.012, va + 0.012, u1 - 0.012, vb - 0.012)
            cv.poly(inner, ((255, 206, 128) if lit else (70, 70, 84)) + (255,))
            for g in (0.25, 0.5, 0.75):
                a = sub_quad(q, u0 + (u1 - u0) * g, va, u0 + (u1 - u0) * g, vb)
                cv.line([a[0], a[3]], (60, 60, 66, 255), 2)


# ------------------------------------------------------------------ layers
def _sky(k):
    cv = Cv(k)
    cv.im = vgrad(k, [(0, (54, 70, 138)), (380, (128, 100, 152)), (640, (232, 140, 112)), (820, (255, 186, 118)),
                      (960, (255, 214, 150)), (LH, (255, 214, 150))])
    cv.d = ImageDraw.Draw(cv.im)
    g = Cv(k, fill=(255, 200, 130, 0))
    g.glow(SUN[0], SUN[1], 420, (255, 196, 120), 150)
    g.glow(SUN[0], SUN[1], 150, (255, 236, 190), 200)
    g.blur(30)
    cv.over(g)
    cv.ell(SUN[0], SUN[1], 52, 52, (255, 246, 214, 255))
    rnd = random.Random(2)
    for (cx, cy, w) in ((250, 540, 300), (820, 600, 260), (480, 470, 220), (930, 420, 200)):
        for i in range(4):
            cv.ell(cx + rnd.uniform(-w / 3, w / 3), cy + rnd.uniform(-10, 10), w * 0.4, 14,
                   (255, 178, 140, 150))
    cv.blur(1.5)
    return cv


def _far(k):
    cv = Cv(k, fill=(150, 96, 100, 0))
    rnd = random.Random(5)
    # skyline beyond the end of the lane
    x = 330
    while x < 800:
        w = rnd.uniform(40, 80)
        top = rnd.uniform(700, 820)
        col = mix((150, 92, 100), (176, 112, 112), rnd.random())
        cv.rect(x, top, x + w, 1010, col + (255,))
        if rnd.random() < 0.5:
            cv.rect(x + 8, top - 18, x + 26, top, mul(col, 0.85) + (255,))
        for wy in range(int(top) + 14, 990, 26):
            for wx in range(int(x) + 8, int(x + w) - 10, 18):
                if rnd.random() < 0.3:
                    cv.rect(wx, wy, wx + 8, wy + 10, (255, 214, 150, 255))
        x += w - 4
    # a dome + minaret silhouette
    cv.ell(700, 760, 44, 40, (140, 88, 96, 255))
    cv.rect(656, 760, 744, 820, (140, 88, 96, 255))
    cv.rect(756, 690, 768, 820, (140, 88, 96, 255))
    cv.poly([(752, 690), (762, 660), (772, 690)], (140, 88, 96, 255))
    # the building that closes the lane + cross-street
    xl, xr = x_on(M_BL, 990), x_on(M_BR, 990)
    cv.rect(xl - 30, 820, xr + 30, 992, (196, 132, 118, 255))
    for wy in (840, 900, 950):
        for wx in range(int(xl - 20), int(xr + 20), 30):
            cv.rect(wx, wy, wx + 14, wy + 22, (255, 220, 160, 255) if (wx + wy) % 3 else (110, 76, 80, 255))
    cv.poly([(xl - 60, 990), (xr + 60, 990), (xr + 120, 1040), (xl - 120, 1040)], (170, 130, 116, 255))
    cv.blur(2.2)
    arr = cv.im.copy()
    tint = Image.new("RGBA", arr.size, HAZE + (0,))
    tint.putalpha(arr.getchannel("A").point(lambda v: int(v * 0.32)))
    cv.im.alpha_composite(tint)
    return cv


def _mid(k):
    cv = Cv(k, fill=(170, 120, 110, 0), blend=True)
    rnd = random.Random(9)
    # floor segment
    y0, y1 = 985, 1230
    cv.poly([(x_on(M_BL, y0), y0), (x_on(M_BR, y0), y0), (x_on(M_BR, y1), y1), (x_on(M_BL, y1), y1)],
            (176, 150, 132, 255))
    left = [(250, 380, 1.5, (236, 170, 170)), (380, 452, 2.2, (240, 210, 140)), (452, 508, 1.35, (180, 200, 220))]
    right = [(612, 668, -1.3, (200, 220, 180)), (668, 742, -2.4, (236, 186, 150)), (742, 860, -1.6, (210, 180, 220))]
    for (xa, xb, m, col) in left + right:
        side = "L" if xb <= VP[0] else "R"
        q = facade(xa, xb, m, side)
        c = mix(col, HAZE, 0.18)
        cv.poly(q, mul(c, 0.86) + (255,), INK, 2)
        _windows(cv, q, 3, 2, rnd, frame=mul(c, 1.08), v0=0.1, v1=0.62)
        # ground floor shutter / shop
        cv.poly(sub_quad(q, 0.1, 0.74, 0.9, 0.98), (120, 110, 110, 255), INK, 2)
        cv.poly(sub_quad(q, 0.08, 0.66, 0.92, 0.72), (mix((220, 60, 60), (60, 120, 200), rnd.random())) + (255,),
                INK, 2)
        # balcony slab
        cv.poly(sub_quad(q, 0.0, 0.62, 1.0, 0.645), mul(c, 1.12) + (255,))
    # wires + bunting across the lane
    for (a, b, sag) in (((300, 560), (800, 540), 60), ((330, 610), (780, 650), 46), ((410, 690), (700, 680), 30)):
        cv.line(catenary(a[0], a[1], b[0], b[1], sag), (40, 32, 36, 255), 2.2)
    pts = catenary(390, 720, 720, 712, 36, 60)
    cv.line(pts, (60, 50, 50, 255), 2)
    for i, (bx, by) in enumerate(along(pts, 22)):
        col = [(240, 60, 60), (250, 200, 50), (60, 160, 80), (70, 120, 220), (240, 120, 40)][i % 5]
        cv.poly([(bx - 8, by), (bx + 8, by), (bx, by + 20)], col + (255,))
    cv.blur(1.1)
    return cv


def _near(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(255, 210, 150, 0))
    rnd = random.Random(14)

    # ---- lane floor ----
    floor = [(-60, bot_l(-60)), (300, bot_l(300)), (820, bot_r(820)), (1140, bot_r(1140)), (1140, 1980),
             (-60, 1980)]
    fill_tex(cv, floor, [(1150, (176, 150, 132)), (1500, (150, 128, 116)), (LH, (118, 100, 96))], seed=4, cell=10,
             lo=0.86, hi=1.1)
    for side, f in (("L", bot_l), ("R", bot_r)):          # open drains (nali) along both sides
        xs = (-60, 300) if side == "L" else (820, 1140)
        a, b = (xs[0], f(xs[0])), (xs[1], f(xs[1]))
        off = 26 if side == "L" else 26
        cv.poly([a, b, (b[0], b[1] + off * 0.5), (a[0], a[1] + off)], (70, 66, 64, 255))
    for _ in range(7):                                     # a few long hairline cracks + pebbles
        x, y = rnd.uniform(80, 1000), rnd.uniform(1300, 1880)
        pts = [(x, y)]
        for j in range(6):
            x += rnd.uniform(14, 40) * (1 if rnd.random() < 0.5 else -1)
            y += rnd.uniform(2, 10)
            pts.append((x, y))
        cv.line(pts, (104, 90, 86, 90), 1.6)
    for _ in range(26):
        cv.ell(rnd.uniform(40, 1040), rnd.uniform(1250, 1910), 4, 2.5, (110, 100, 96, 200))
    # puddle reflecting the sunset (soft, blended into the road)
    pud = Cv(k, fill=(240, 180, 130, 0))
    pud.ell(430, 1810, 150, 26, (232, 170, 128, 120))
    pud.ell(410, 1806, 90, 9, (255, 226, 180, 120))
    pud.blur(4)
    cv.over(pud)

    # ---- near-left building: kirana store, balcony with clothes, windows ----
    QL = facade(-40, 300, 1.846, "L")
    fill_tex(cv, QL, [(0, (236, 204, 140)), (1000, (226, 190, 126)), (1400, (196, 160, 110))], seed=6, cell=18,
             lo=0.9, hi=1.07)
    cv.line([QL[1], QL[2]], (250, 226, 170, 255), 6)                                     # lit corner
    shop = sub_quad(QL, 0.1, 0.66, 0.92, 0.985)
    fill_tex(cv, shop, [(900, (255, 206, 140)), (1400, (214, 150, 96))], seed=7, lo=0.95, hi=1.04)
    for v in (0.72, 0.8, 0.88):
        sh = sub_quad(QL, 0.12, v, 0.9, v + 0.012)
        cv.poly(sh, (120, 80, 50, 255))
        for i in range(10):
            u = 0.14 + i * 0.075
            pk = sub_quad(QL, u, v - 0.045, u + 0.05, v)
            cv.poly(pk, [(230, 60, 60), (250, 200, 60), (60, 150, 220), (90, 180, 90), (240, 130, 40)][(i + int(v * 10)) % 5]
                    + (255,), INK, 1)
    cv.poly(sub_quad(QL, 0.08, 0.62, 0.94, 0.665), (150, 150, 156, 255), INK, 2)       # rolled-up shutter
    for v in (0.63, 0.645):
        a = sub_quad(QL, 0.08, v, 0.94, v)
        cv.line([a[0], a[1]], (110, 110, 116, 255), 2)
    quad_image(cv, sign_image("BABLU KIRANA STORE", (190, 34, 40), (255, 236, 190)),
               sub_quad(QL, 0.04, 0.535, 0.97, 0.6))
    light.poly(shop, (255, 200, 130, 80))
    # balcony + clothes line
    cv.poly(sub_quad(QL, 0.04, 0.47, 0.96, 0.49), (210, 200, 190, 255), INK, 2)
    for i in range(14):
        u = 0.06 + i * 0.065
        a = sub_quad(QL, u, 0.405, u, 0.47)
        cv.line([a[0], a[3]], (60, 60, 66, 255), 4)
    a = sub_quad(QL, 0.04, 0.405, 0.96, 0.405)
    cv.line([a[0], a[1]], (60, 60, 66, 255), 5)
    for i, col in enumerate(((230, 60, 70), (60, 120, 210), (250, 210, 60), (240, 240, 236), (60, 170, 120))):
        u = 0.12 + i * 0.16
        cv.poly(sub_quad(QL, u, 0.33, u + 0.1, 0.39 + 0.02 * (i % 2)), col + (255,), INK, 2)
    a = sub_quad(QL, 0.08, 0.33, 0.92, 0.33)
    cv.line([a[0], a[1]], (240, 240, 240, 255), 2)
    _windows(cv, QL, 1, 2, rnd, v0=0.17, v1=0.29, lit_p=0.6)
    _windows(cv, QL, 1, 2, rnd, v0=0.02, v1=0.12, lit_p=0.4)
    cv.poly(sub_quad(QL, 0.62, 0.29, 0.86, 0.32), (226, 228, 230, 255), INK, 2)         # AC unit

    # ---- near-right building with the chai sign + awning ----
    QR = facade(820, 1140, -1.769, "R")
    fill_tex(cv, QR, [(0, (164, 196, 206)), (900, (150, 184, 196)), (1400, (124, 150, 160))], seed=8, cell=18,
             lo=0.9, hi=1.07)
    cv.line([QR[0], QR[3]], (200, 226, 232, 255), 6)
    _windows(cv, QR, 2, 2, rnd, v0=0.08, v1=0.42, lit_p=0.5)
    cv.poly(sub_quad(QR, 0.0, 0.44, 1.0, 0.465), (220, 224, 226, 255), INK, 2)
    quad_image(cv, sign_image("CHOTU CHAI CORNER", (40, 120, 70), (255, 246, 210)), sub_quad(QR, 0.06, 0.5, 0.96, 0.575))
    door = sub_quad(QR, 0.1, 0.66, 0.9, 1.0)
    fill_tex(cv, door, [(900, (120, 80, 60)), (1400, (70, 50, 44))], seed=9, lo=0.95, hi=1.04)
    awn = [sub_quad(QR, 0.0, 0.6, 1.0, 0.6)[0], sub_quad(QR, 0.0, 0.6, 1.0, 0.6)[1], (1140, 1090), (800, 1000)]
    cv.poly(awn, (40, 110, 190, 255), INK, 3)
    for i in range(1, 6):
        u = i / 6.0
        a = (awn[0][0] + (awn[1][0] - awn[0][0]) * u, awn[0][1] + (awn[1][1] - awn[0][1]) * u)
        b = (awn[3][0] + (awn[2][0] - awn[3][0]) * u, awn[3][1] + (awn[2][1] - awn[3][1]) * u)
        cv.line([a, b], (30, 90, 160, 255), 3)
    cv.line([(830, 1004), (830, 1230)], (90, 80, 70, 255), 6)                             # bamboo post
    cv.line([(910, 1030), (910, 1090)], (40, 40, 40, 255), 2)
    cv.ell(910, 1100, 11, 13, (255, 244, 200, 255))                                        # hanging bulb
    light.glow(910, 1100, 170, (255, 214, 140), 150)

    # ---- electric pole, transformer, street lamp, tangle of wires ----
    PX, PB = 176, 1330
    cv.poly([(PX - 13, PB), (PX + 13, PB), (PX + 9, -80), (PX - 9, -80)], (170, 166, 160, 255), INK, 3)
    for y in (300, 360):
        cv.rect(PX - 80, y, PX + 80, y + 12, (110, 104, 98, 255), INK, 2)
        for dx in (-70, -30, 30, 70):
            cv.rect(PX + dx - 5, y - 16, PX + dx + 5, y, (236, 236, 230, 255), INK, 1)
    cv.rect(PX - 46, 540, PX + 46, 680, (126, 132, 128, 255), INK, 3)
    for i in range(6):
        cv.line([(PX - 40 + i * 16, 552), (PX - 40 + i * 16, 668)], (100, 104, 100, 255), 3)
    cv.line([(PX, 470), (PX + 130, 450)], (90, 90, 92, 255), 7)
    cv.poly([(PX + 112, 444), (PX + 162, 438), (PX + 158, 456), (PX + 116, 462)], (60, 60, 64, 255), INK, 2)
    cv.ell(PX + 138, 458, 16, 6, (255, 240, 190, 255))
    light.glow(PX + 138, 470, 200, (255, 214, 150), 130)
    targets = [((PX - 70, 300), (380, 600), 60), ((PX - 30, 300), (480, 700), 40), ((PX + 30, 300), (740, 610), 70),
               ((PX + 70, 300), (1140, 280), 50), ((PX + 70, 360), (1140, 420), 70), ((PX - 70, 360), (-60, 420), 40),
               ((PX + 30, 360), (840, 560), 90), ((PX - 30, 300), (-60, 200), 30)]
    for (a, b, sag) in targets:
        cv.line(catenary(a[0], a[1], b[0], b[1], sag), (34, 28, 30, 255), 2.6)
    for i in range(7):                                                                     # the famous tangle
        cx, cy = PX + rnd.uniform(-60, 60), rnd.uniform(380, 520)
        cv.line([(cx + 30 * math.cos(a), cy + 18 * math.sin(a)) for a in
                 [j * 0.5 + i for j in range(14)]], (30, 26, 28, 255), 2.2)

    # ---- warm light: sun streak down the lane + god rays ----
    rays = Cv(kg, fill=(255, 200, 140, 0))
    rays.poly([(VP[0] - 10, VP[1]), (VP[0] + 10, VP[1]), (780, LH), (360, LH)], (255, 196, 130, 70))
    for a in (-0.9, -0.55, -0.25, 0.2, 0.5, 0.85):
        ex, ey = SUN[0] + math.sin(a) * 1600, SUN[1] + math.cos(a) * 1600
        rays.poly([SUN, (ex - 70, ey), (ex + 70, ey)], (255, 210, 150, 26))
    rays.blur(26)
    light.over(rays)
    light.blur(6)
    cv.blur(0.35)
    return cv, light


def _tapri(k):
    """The chai stall counter (a Sprite: depth-sorted with the characters)."""
    x0, y0, x1, y1 = 820, 980, LW, 1460
    cv = Cv(k, w=x1 - x0, h=y1 - y0, blend=True)

    def P(pts):
        return [(x - x0, y - y0) for x, y in pts]

    st_, sb = 0.36, 0.92
    face = [(860, line_y(st_, 860)), (1100, line_y(st_, 1100)), (1100, line_y(sb, 1100)), (860, line_y(sb, 860))]
    top = [face[0], face[1], (1120, line_y(st_, 1100) - 16), (884, line_y(st_, 860) - 12)]
    cv.poly(P(top), (150, 104, 66, 255), INK, 3)
    cv.poly(P(face), (186, 132, 82, 255), INK, 3)
    for u in (0.33, 0.66):
        a = (860 + 240 * u, line_y(st_, 860 + 240 * u))
        b = (860 + 240 * u, line_y(sb, 860 + 240 * u))
        cv.line(P([a, b]), (140, 96, 60, 255), 4)
    # little poster on the counter
    quad_image(cv, sign_image("CHAI 10/-", (250, 230, 120), (120, 40, 30), 600, 220),
               P([(890, line_y(st_, 890) + 30), (1000, line_y(st_, 1000) + 34), (1000, line_y(st_, 1000) + 104),
                  (890, line_y(st_, 890) + 90)]))
    # stove + big kettle + glasses on top
    kx, ky = 930, line_y(st_, 930) - 6
    cv.poly(P([(kx - 34, ky), (kx + 34, ky), (kx + 30, ky - 16), (kx - 30, ky - 16)]), (50, 50, 54, 255), INK, 2)
    cv.poly(P([(kx - 28, ky - 16), (kx + 28, ky - 16), (kx + 22, ky - 74), (kx - 22, ky - 74)]),
            (200, 202, 210, 255), INK, 3)
    cv.poly(P([(kx + 22, ky - 56), (kx + 50, ky - 80), (kx + 54, ky - 74), (kx + 26, ky - 46)]),
            (180, 182, 190, 255), INK, 2)
    cv.line(P([(kx - 18, ky - 74), (kx, ky - 96), (kx + 18, ky - 74)]), (40, 40, 44, 255), 4)
    for i in range(4):
        gx = 990 + i * 22
        gy = line_y(st_, gx) - 4
        cv.poly(P([(gx - 8, gy), (gx + 8, gy), (gx + 9, gy - 26), (gx - 9, gy - 26)]), (236, 236, 240, 255), INK, 2)
        cv.poly(P([(gx - 7, gy - 2), (gx + 7, gy - 2), (gx + 8, gy - 18), (gx - 8, gy - 18)]), (176, 110, 58, 255))
    return Sprite(cv.im, k, x0, y0, line_y(sb, 960), "tapri"), (kx, ky - 98)


def _foreground(k):
    cv = Cv(k, fill=(60, 50, 50, 0))
    pts = catenary(-60, 70, 1140, 40, 110, 80)
    cv.line(pts, (50, 40, 40, 255), 3)
    for i, (bx, by) in enumerate(along(pts, 54)):
        col = [(240, 60, 60), (250, 200, 50), (60, 160, 80), (70, 120, 220), (240, 120, 40)][i % 5]
        cv.poly([(bx - 22, by), (bx + 22, by), (bx, by + 54)], col + (255,))
    # bicycle wheel, bottom-left
    cx, cy, r = 70, 1900, 190
    cv.ell(cx, cy, r, r, None, (30, 30, 34, 255), 16)
    cv.ell(cx, cy, r - 14, r - 14, None, (170, 170, 176, 255), 4)
    for i in range(16):
        a = i * math.pi / 8
        cv.line([(cx, cy), (cx + (r - 14) * math.cos(a), cy + (r - 14) * math.sin(a))], (190, 190, 196, 255), 2)
    cv.ell(cx, cy, 16, 16, (120, 120, 126, 255))
    cv.blur(8)
    return cv


def gali_25d(s, zmax=1.0):
    kb = 0.5 * s
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    sky = _sky(kb)
    far = _far(0.6 * s)
    mid = _mid(0.7 * s)
    near, light = _near(kr, kg)
    tapri, kettle_top = _tapri(kr)
    fg = _foreground(0.5 * s)
    empty = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    back = [
        Layer(sky.im, kb, 0.0, birds(kb), "sky"),
        Layer(far.im, 0.6 * s, 0.12, None, "far"),
        Layer(mid.im, 0.7 * s, 0.38, None, "mid"),
        Layer(near.im, kr, 1.0, None, "near"),
        Layer(light.im, kg, 1.0, None, "warm_light", mode="screen"),
        Layer(empty, 0.3 * s, 1.0, steam([(kettle_top[0], kettle_top[1], 0.7, 0.5)], 0.3 * s), "steam"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.35, None, "foreground")]
    light_cfg = {"ambient": [255, 234, 214], "dir": 1, "vignette": 0.36}
    return Layered(back, front, light=light_cfg, horizon=VP[1], ground=1150, sprites=[tapri])

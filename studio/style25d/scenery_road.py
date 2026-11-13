"""Hand-made 2.5D road sets, painted like the kitchen and the gali.

street_25d   a busy shop street by day: the city far away (its own layer), rooftops with water tanks and a hoarding
             (middle layer), a row of four shops (MEDICAL, MOBILE, SWEETS, TAILOR) with awnings, shelves of goods and
             balconies above on the far footpath, the road with a zebra crossing, a blinking OPEN sign; the people
             stand on the near footpath with the electric pole and the street lamp, and the traffic passes behind
             them, in proportion (styles.SET_AMBIENT); a bollard and a plant blurred in front.
busstop_25d  a bus stop: the people wait on the near footpath by the shelter (its roof, bench, an ad, glass the
             traffic shows through) and the BUS STOP sign; across the road a row of flats with a XEROX shop and a
             big shady tree.
market_25d   a sabzi bazaar: three stalls (SABZI, FRUITS, MASALA) under striped canopies, the old market far behind,
             bunting that flutters; each stall's counter is a piece the people are depth-sorted with, so the
             sabziwala stands behind it and the customer in front (counters.PRESET_PLACES["market"]).
(All three have writing on them, so a reverse shot never mirrors them.)
"""
import math
import random

from PIL import Image, ImageDraw

from .scenery import Cv, Layer, Layered, Sprite, along, catenary, fill_tex, mix, motes, mul, quad_image, sign_image, \
    vgrad
from .scenery_home import _leaves
from ..util import LH, LW

INK = (46, 40, 44, 255)
ROAD_VP = (540, 900)
PATH_Y = 1250                           # where a shop of the row stands (before it is moved up)


def gx(x, y_ref, y, vp=ROAD_VP):
    """x at height y on the ground line through (x, y_ref) that runs to the vanishing point."""
    return vp[0] + (x - vp[0]) * (y - vp[1]) / float(y_ref - vp[1])


def _blank(k, fill=(0, 0, 0, 0)):
    return Image.new("RGBA", (8, 8), fill)


# ------------------------------------------------------------------ shared: sky, city, road
def day_sky(k, sun=(880, 250), seed=3):
    cv = Cv(k, blend=True)
    cv.im = vgrad(k, [(0, (64, 132, 216)), (520, (112, 176, 236)), (900, (190, 222, 246)), (LH, (210, 230, 246))])
    cv.d = ImageDraw.Draw(cv.im)
    g = Cv(k, fill=(255, 244, 210, 0))
    g.glow(sun[0], sun[1], 320, (255, 246, 214), 130)
    g.blur(24)
    cv.over(g)
    cv.ell(sun[0], sun[1], 58, 58, (255, 250, 228, 255))
    rnd = random.Random(seed)
    for (cx, cy, w) in ((200, 230, 250), (600, 380, 190), (980, 520, 160)):
        for _ in range(7):
            cv.ell(cx + rnd.uniform(-w / 2, w / 2), cy + rnd.uniform(-14, 14), w * 0.27, w * 0.14,
                   (255, 255, 255, 200))
    cv.blur(1.2)
    return cv


def skyline(k, seed=4, tops=(250, 470), base=1150, tint=(150, 174, 204), haze=(206, 224, 242)):
    """Far layer: the city far away, towers with water tanks and antennas, hazy and blurred."""
    cv = Cv(k, blend=True)
    rnd = random.Random(seed)
    x = -40.0
    while x < LW + 40:
        w = rnd.uniform(60, 130)
        top = rnd.uniform(*tops)
        col = mix(tint, haze, rnd.uniform(0, 0.35))
        cv.rect(x, top, x + w, base, col + (255,))
        r = rnd.random()
        if r < 0.3:                                                      # a water tank on the roof
            cv.rect(x + w * 0.2, top - 26, x + w * 0.45, top, mul(col, 0.88) + (255,))
            cv.ell(x + w * 0.325, top - 26, w * 0.125, 6, mul(col, 0.95) + (255,))
        elif r < 0.5:
            cv.line([(x + w * 0.6, top), (x + w * 0.6, top - 54)], mul(col, 0.8) + (255,), 3)
        for wy in range(int(top) + 16, base - 20, 28):
            for wx in range(int(x) + 8, int(x + w) - 12, 20):
                cv.rect(wx, wy, wx + 10, wy + 14, mul(col, 1.1 if rnd.random() < 0.7 else 0.86) + (255,))
        x += w + rnd.uniform(-6, 10)
    for i in range(6):                                                    # haze at the foot of the city
        y = base - 260 + i * 44
        cv.rect(-10, y, LW + 10, base, haze + (34,))
    cv.blur(2.4)
    return cv


def rooftops(k, board=("SALE 50% OFF", (250, 210, 60), (180, 40, 40)), seed=6):
    """Middle layer: old rooftops just behind the shop row: water tanks, a dish, a mobile tower, a hoarding."""
    cv = Cv(k, blend=True)
    rnd = random.Random(seed)
    for (x0, x1, top, col) in ((-30, 300, 400, (196, 170, 150)), (330, 560, 450, (180, 164, 160)),
                               (700, 1110, 380, (190, 176, 160))):
        cv.rect(x0, top, x1, 900, col + (255,), INK, 2)
        cv.rect(x0 - 6, top - 10, x1 + 6, top, mul(col, 0.86) + (255,), INK, 2)
        for wy in range(top + 30, 860, 70):
            for wx in range(x0 + 24, x1 - 40, 70):
                cv.rect(wx, wy, wx + 34, wy + 44, mix((120, 150, 180), (230, 236, 240), rnd.random() * 0.4) + (255,),
                        INK, 2)
        tx = x0 + (x1 - x0) * rnd.uniform(0.15, 0.6)                     # a black water tank
        cv.rect(tx, top - 70, tx + 64, top - 8, (40, 40, 44, 255), INK, 2)
        cv.ell(tx + 32, top - 70, 32, 8, (70, 70, 76, 255), INK, 2)
        for ry in (top - 50, top - 30):
            cv.line([(tx, ry), (tx + 64, ry)], (60, 60, 66, 255), 2)
    cv.ell(280, 380, 40, 30, (226, 226, 230, 255), INK, 2)                # a dish antenna
    cv.line([(280, 380), (300, 410)], (90, 90, 96, 255), 3)
    cv.line([(470, 450), (500, 160), (530, 450)], (120, 120, 130, 255), 4)  # a mobile tower
    for y in range(190, 450, 50):
        w = (y - 160) / 290.0 * 30
        cv.line([(500 - w, y), (500 + w, y)], (120, 120, 130, 255), 3)
    cv.rect(488, 210, 512, 250, (210, 210, 216, 255), INK, 2)
    if board:                                                              # a hoarding on scaffolding
        text, bg, fg = board
        for x in (760, 980):
            cv.line([(x, 380), (x, 300)], (80, 80, 86, 255), 5)
        cv.line([(740, 340), (1000, 300)], (80, 80, 86, 255), 3)
        quad_image(cv, sign_image(text, bg, fg, 900, 300), [(700, 170), (1040, 170), (1040, 300), (700, 300)])
    cv.blur(1.1)
    return cv


def electric_pole(cv, x, base, top=230, wires_to=((LW + 40, 330), (LW + 40, 420))):
    cv.rect(x - 11, top, x + 11, base, (170, 166, 160, 255), INK, 3)
    for y in (top + 50, top + 100):
        cv.rect(x - 90, y, x + 90, y + 12, (90, 86, 84, 255), INK, 2)
        for dx in (-76, -30, 30, 76):
            cv.rect(x + dx - 4, y - 16, x + dx + 4, y, (220, 220, 210, 255), INK, 1)
    cv.rect(x - 46, top + 320, x + 46, top + 440, (120, 128, 120, 255), INK, 3)  # the transformer
    for dy in (20, 50, 80):
        cv.line([(x - 40, top + 320 + dy), (x + 40, top + 320 + dy)], (90, 98, 90, 255), 3)
    for i, (ex, ey) in enumerate(wires_to):                               # the tangle of wires
        for j in range(3):
            cv.line(catenary(x + (-76, -30, 30, 76)[j % 4], top + 46 + 50 * (i % 2), ex, ey + j * 18,
                             60 + 25 * j), (40, 36, 40, 255), 2)
    cv.line(catenary(-40, top + 120, x - 76, top + 46, 50), (40, 36, 40, 255), 2)
    for j in range(5):                                                    # cable bundle coiled on the pole
        cv.ell(x, top + 520 + j * 10, 30, 10, None, (30, 30, 34, 255), 3)


def street_lamp(cv, x, base, top=520, arm=-110):
    cv.rect(x - 8, top, x + 8, base, (70, 74, 80, 255), INK, 2)
    cv.rect(x - 16, base - 40, x + 16, base, (60, 62, 68, 255), INK, 2)
    pts = [(x, top + 10), (x + arm * 0.3, top - 30), (x + arm * 0.8, top - 34), (x + arm, top - 20)]
    cv.line(pts, (70, 74, 80, 255), 8)
    cv.poly([(x + arm - 36, top - 22), (x + arm + 30, top - 22), (x + arm + 16, top - 6), (x + arm - 22, top - 6)],
            (230, 232, 220, 255), INK, 2)


# ------------------------------------------------------------------ the shop row
def _goods(cv, x0, x1, y0, y1, kind, rnd):
    """What a shop shows inside its open shutter."""
    cv.rect(x0, y0, x1, y1, (66, 54, 52, 255))
    cv.rect(x0, y0, x1, y0 + 26, (150, 150, 156, 255), INK, 2)             # the shutter rolled up
    for yy in range(y0 + 6, y0 + 26, 7):
        cv.line([(x0 + 2, yy), (x1 - 2, yy)], (120, 120, 126, 255), 1)
    rows = [y0 + 50, y0 + 100, y0 + 150]
    for ry in rows:
        cv.rect(x0 + 8, ry + 30, x1 - 8, ry + 36, (150, 110, 70, 255))    # shelf boards
    pal = {"medical": [(250, 250, 250), (120, 200, 160), (240, 120, 120), (120, 160, 230)],
           "mobile": [(40, 40, 50), (70, 120, 220), (230, 230, 236), (240, 90, 90)],
           "sweets": [(250, 200, 80), (250, 160, 70), (240, 236, 210), (220, 120, 140)],
           "tailor": [(200, 60, 80), (70, 120, 200), (240, 200, 70), (90, 170, 120)]}[kind]
    for ry in rows:
        x = x0 + 14
        while x < x1 - 30:
            w = rnd.uniform(14, 26)
            h = rnd.uniform(18, 28)
            col = rnd.choice(pal)
            if kind == "mobile":                                            # phone boxes and phones standing up
                cv.rect(x, ry + 30 - h, x + w * 0.7, ry + 30, col + (255,), INK, 1)
                cv.rect(x + 3, ry + 34 - h, x + w * 0.7 - 3, ry + 26, (120, 180, 240, 255))
            elif kind == "sweets":                                          # sweets piled in trays
                cv.ell(x + w / 2, ry + 26, w * 0.7, 6, (200, 200, 206, 255))
                for j in range(3):
                    cv.ell(x + w / 2 + (j - 1) * 6, ry + 18 - (j % 2) * 6, 7, 6, col + (255,), INK, 1)
            elif kind == "tailor":                                          # folded cloth
                cv.rect(x, ry + 30 - h * 0.6, x + w, ry + 30, col + (255,), INK, 1)
                cv.line([(x, ry + 30 - h * 0.3), (x + w, ry + 30 - h * 0.3)], mul(col, 0.8) + (255,), 1)
            else:
                cv.rect(x, ry + 30 - h, x + w, ry + 30, col + (255,), INK, 1)
                cv.rect(x + 2, ry + 30 - h * 0.7, x + w - 2, ry + 30 - h * 0.45, mul(col, 0.75) + (255,))
            x += w + rnd.uniform(4, 10)
    if kind == "sweets":                                                   # a glass counter in the door
        cv.rect(x0 + 10, y1 - 70, x1 - 10, y1, (200, 226, 236, 255), INK, 2)
        for i in range(5):
            cx = x0 + 30 + i * (x1 - x0 - 60) / 4.0
            cv.ell(cx, y1 - 40, 16, 10, ((250, 200, 80), (250, 160, 70), (240, 236, 210))[i % 3] + (255,), INK, 1)
    elif kind == "tailor":                                                 # a sewing machine and hanging shirts
        cv.rect(x1 - 90, y1 - 60, x1 - 20, y1, (120, 80, 50, 255), INK, 2)
        cv.poly([(x1 - 84, y1 - 60), (x1 - 84, y1 - 92), (x1 - 40, y1 - 92), (x1 - 34, y1 - 76), (x1 - 50, y1 - 60)],
                (30, 30, 34, 255), INK, 2)
        cv.line([(x0 + 10, y0 + 40), (x0 + 90, y0 + 40)], (180, 180, 186, 255), 3)
        for i, col in enumerate(((240, 240, 236), (120, 170, 230), (240, 160, 160))):
            sx = x0 + 22 + i * 26
            cv.poly([(sx, y0 + 42), (sx + 22, y0 + 42), (sx + 26, y0 + 110), (sx - 4, y0 + 110)], col + (255,), INK, 1)
    elif kind == "medical":
        cv.rect(x0 + 10, y1 - 66, x1 - 10, y1, (226, 236, 236, 255), INK, 2)


def _awning(cv, x0, x1, y0, y1, cols):
    n = max(4, int((x1 - x0) / 34))
    for i in range(n):
        a, b = x0 + (x1 - x0) * i / float(n), x0 + (x1 - x0) * (i + 1) / float(n)
        a2, b2 = x0 - 10 + (x1 - x0 + 20) * i / float(n), x0 - 10 + (x1 - x0 + 20) * (i + 1) / float(n)
        cv.poly([(a, y0), (b, y0), (b2, y1), (a2, y1)], cols[i % 2] + (255,))
        cv.ell((a2 + b2) / 2, y1, (b2 - a2) / 2, 9, cols[i % 2] + (255,))
    cv.line([(x0, y0), (x1, y0)], INK, 3)
    cv.line([(x0, y0), (x0 - 10, y1)], INK, 2)
    cv.line([(x1, y0), (x1 + 10, y1)], INK, 2)


def _upper_floors(cv, x0, x1, top, col, rnd, floors=2, bottom=900):
    h = (bottom - (top + 40)) / float(floors)
    for f in range(floors):
        fy = top + 40 + f * h
        n = 2 if x1 - x0 < 300 else 3
        ww = (x1 - x0 - 40) / float(n) - 34
        for i in range(n):
            wx = x0 + 30 + i * (ww + 34)
            wy, wb = fy + 26, fy + h - 40
            cv.rect(wx - 6, wy - 6, wx + ww + 6, wb + 6, mul(col, 1.12) + (255,), INK, 2)
            cv.rect(wx, wy, wx + ww, wb, (140, 176, 206, 255), INK, 2)
            cv.poly([(wx + ww * 0.15, wb), (wx + ww * 0.55, wy), (wx + ww * 0.75, wy), (wx + ww * 0.35, wb)],
                    (196, 220, 236, 160))                                   # a glint on the glass
            for g in range(1, 4):
                cv.line([(wx + ww * g / 4.0, wy), (wx + ww * g / 4.0, wb)], (60, 60, 66, 255), 2)
            cv.line([(wx, (wy + wb) / 2), (wx + ww, (wy + wb) / 2)], (60, 60, 66, 255), 2)
            cv.rect(wx - 10, wb + 6, wx + ww + 10, wb + 14, mul(col, 0.8) + (255,), INK, 1)   # the sill
            r = rnd.random()
            if r < 0.25:                                                     # a pot plant on the sill
                cv.poly([(wx + 6, wb + 6), (wx + 30, wb + 6), (wx + 26, wb - 16), (wx + 10, wb - 16)],
                        (190, 110, 70, 255), INK, 1)
                _leaves(cv, 6, wx + 4, wx + 34, wb - 40, wb - 16, 12, ((50, 130, 60), (110, 180, 80)), int(wx))
            elif r < 0.45 and i == n - 1:                                    # an AC box
                cv.rect(wx + ww + 10, wy + 10, wx + ww + 66, wy + 50, (236, 236, 232, 255), INK, 2)
                for gy in range(int(wy) + 18, int(wy) + 46, 7):
                    cv.line([(wx + ww + 16, gy), (wx + ww + 60, gy)], (170, 170, 170, 255), 1)
        cv.rect(x0 - 8, fy + h - 14, x1 + 8, fy + h, mul(col, 0.82) + (255,), INK, 2)  # floor slab


def _shop(cv, x0, x1, top, col, sign, sign_col, awn, kind, seed):
    rnd = random.Random(seed)
    cv.rect(x0, top, x1, PATH_Y, col + (255,), INK, 3)
    cv.rect(x0 - 8, top - 16, x1 + 8, top + 4, mul(col, 0.84) + (255,), INK, 2)
    for px in range(int(x0) + 10, int(x1) - 10, 30):                      # parapet pattern
        cv.rect(px, top - 12, px + 14, top, mul(col, 1.1) + (255,))
    _upper_floors(cv, x0, x1, top, col, rnd, floors=2 if top < 520 else 1 + (top < 600))
    quad_image(cv, sign_image(sign, sign_col, (255, 255, 255), 900, 200),
               [(x0 + 14, 924), (x1 - 14, 924), (x1 - 14, 994), (x0 + 14, 994)])
    _goods(cv, x0 + 22, x1 - 22, 1062, PATH_Y - 12, kind, rnd)
    _awning(cv, x0 + 6, x1 - 6, 1000, 1062, awn)
    cv.rect(x0 + 10, PATH_Y - 14, x1 - 10, PATH_Y, (170, 166, 160, 255), INK, 2)   # the step


SHOPS = [(-20, 270, 470, (236, 222, 196), "MEDICAL", (40, 150, 90), ((40, 150, 90), (240, 240, 236)), "medical"),
         (270, 540, 560, (214, 196, 226), "MOBILE", (60, 90, 190), ((60, 90, 190), (240, 240, 236)), "mobile"),
         (540, 820, 430, (248, 214, 186), "SWEETS", (230, 110, 40), ((230, 110, 40), (250, 230, 150)), "sweets"),
         (820, 1100, 510, (200, 226, 206), "TAILOR", (150, 60, 140), ((150, 60, 140), (240, 240, 236)), "tailor")]
# The road sets, from the back: the shops (or flats) on the far footpath, the road with its traffic, and the near
# footpath the people stand on (y 1700). The road runs BEHIND the people, so a car passes behind them, as big as
# its distance makes it (styles.SET_AMBIENT); everything on the near footpath is a layer drawn after the traffic.
STREET_VP = (540, 860)
FAR_PATH, FAR_KERB, ROAD_TOP, ROAD_BOT, NEAR_KERB = 1100, 1156, 1172, 1540, 1566
SHOP_SHIFT = 150                                            # the shop row is drawn as before, moved up by this much
OPEN_SIGN = (300, 1020 - SHOP_SHIFT, 380, 1052 - SHOP_SHIFT)


def _moved_up(cv, draw, dy):
    """draw(canvas) on a canvas of its own, then laid on cv moved up by dy logical px."""
    c = Cv(cv.k, blend=True)
    draw(c)
    off = int(round(dy * cv.k))
    cv.im.alpha_composite(c.im.crop((0, off, c.im.width, c.im.height)), dest=(0, 0))
    cv.d = ImageDraw.Draw(cv.im)


def _footpath(cv, y0, y1, seed, col=(198, 192, 184), vp=STREET_VP):
    fill_tex(cv, [(-10, y0), (LW + 10, y0), (LW + 10, y1), (-10, y1)], [(y0, col), (y1, mul(col, 0.95))], seed=seed,
             cell=18, lo=0.93, hi=1.05)
    y = y0
    while y < y1:                                                   # rows of slabs, wider apart nearer the lens
        y = vp[1] + (y - vp[1]) * 1.13
        if y < y1:
            cv.line([(-10, y), (LW + 10, y)], mul(col, 0.8) + (255,), 2)
    for x in range(-2400, 3400, 120):
        cv.line([(gx(x, y0, y0, vp), y0), (gx(x, y0, y1, vp), y1)], mul(col, 0.8) + (255,), 2)
    cv.line([(-10, y0), (LW + 10, y0)], INK, 2)


def _kerb(cv, y0, y1, vp=STREET_VP):
    for i, x in enumerate(range(-2400, 3400, 80)):
        cv.poly([(gx(x, y0, y0, vp), y0), (gx(x + 80, y0, y0, vp), y0), (gx(x + 80, y0, y1, vp), y1),
                 (gx(x, y0, y1, vp), y1)], ((236, 196, 50) if i % 2 else (40, 40, 44)) + (255,))
    cv.line([(-10, y0), (LW + 10, y0)], INK, 2)
    cv.line([(-10, y1), (LW + 10, y1)], INK, 2)


def _road(cv, y0, y1, seed, zebra=None, vp=STREET_VP):
    fill_tex(cv, [(-10, y0), (LW + 10, y0), (LW + 10, y1), (-10, y1)], [(y0, (104, 106, 112)), (y1, (84, 86, 92))],
             seed=seed, cell=10, lo=0.88, hi=1.08)
    rnd = random.Random(seed)
    for _ in range(7):                                                # patches and cracks
        x, y = rnd.uniform(0, LW), rnd.uniform(y0 + 30, y1 - 30)
        w = rnd.uniform(40, 110) * (y - vp[1]) / 600.0
        cv.ell(x, y, w, w * 0.18, (64, 66, 72, 90))
    for y in (y0 + 12, y1 - 16):                                      # the yellow edge lines
        cv.rect(-10, y, LW + 10, y + 6 * (y - vp[1]) / 600.0, (236, 200, 60, 255))
    ym = (y0 + y1) / 2.0                                               # the dashed middle line
    for x in range(-60, LW + 60, 170):
        cv.rect(x, ym - 5, x + 90, ym + 5, (240, 240, 236, 255))
    if zebra:
        for xs in range(zebra[0], zebra[1], 70):                      # stripes running to the vanishing point
            cv.poly([(gx(xs, y1, y0 + 24, vp), y0 + 24), (gx(xs + 40, y1, y0 + 24, vp), y0 + 24),
                     (xs + 40, y1 - 24), (xs, y1 - 24)], (236, 236, 232, 235))
    cv.ell(260, y1 - 70, 70, 14, (70, 70, 74, 255), (40, 40, 44, 255), 3)   # a manhole


def _street(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(255, 236, 190, 0), blend=True)

    def shops(c):
        for i, sh in enumerate(SHOPS):
            _shop(c, *sh, seed=20 + i)
    _moved_up(cv, shops, SHOP_SHIFT)
    _footpath(cv, FAR_PATH, FAR_KERB, 12)
    for (x0, x1, _t, _c, _s, _sc, _a, _k) in SHOPS:                      # the awnings' shade on the footpath
        cv.poly([(x0 + 10, FAR_PATH), (x1 - 4, FAR_PATH), (x1 - 24, FAR_PATH + 26), (x0 - 10, FAR_PATH + 26)],
                (30, 24, 30, 46))
    _kerb(cv, FAR_KERB, ROAD_TOP)
    _road(cv, ROAD_TOP, ROAD_BOT, 13, zebra=(700, 1040))
    # a green dustbin and a parked cycle on the far footpath
    cv.poly([(452, 1140), (482, 1140), (478, 1096), (456, 1096)], (60, 140, 80, 255), INK, 2)
    cv.rect(450, 1090, 484, 1098, (40, 110, 60, 255), INK, 1)
    for wx in (600, 660):
        cv.ell(wx, 1130, 22, 22, None, (40, 40, 44, 255), 4)
    cv.line([(600, 1130), (630, 1096), (660, 1130), (640, 1130), (630, 1096), (618, 1088)], (200, 50, 50, 255), 4)
    for (x0, x1) in ((560, 760), (820, 1000)):
        light.poly([(x0 + 300, -40), (x1 + 300, -40), (x1 - 100, 1540), (x0 - 100, 1540)], (255, 236, 190, 40))
    light.glow(680, 1160 - SHOP_SHIFT, 160, (255, 210, 140), 70)          # the sweet shop's warm bulbs
    light.blur(30)
    return cv, light


def _street_near(k):
    """The near footpath the people stand on, with its kerb, the electric pole and the street lamp (drawn after the
    traffic: the cars pass behind them)."""
    cv = Cv(k, blend=True)
    _kerb(cv, ROAD_BOT, NEAR_KERB)
    _footpath(cv, NEAR_KERB, LH, 14, col=(206, 198, 186))
    cv.poly([(70, NEAR_KERB + 90), (100, NEAR_KERB + 90), (-60, LH), (-120, LH)], (20, 20, 30, 40))   # pole shadow
    electric_pole(cv, 90, 1660, top=-40, wires_to=((LW + 40, 260), (LW + 40, 340), (700, 360)))
    street_lamp(cv, 1000, 1650, top=420, arm=-130)
    return cv


def _open_sign(k):
    """fn for a screen layer: the mobile shop's LED OPEN sign, blinking."""
    x0, y0, x1, y1 = OPEN_SIGN

    def fn(_im, t):
        cv = Cv(k, fill=(255, 80, 80, 0))
        on = (t * 1.6) % 2.0 < 1.4
        col = (255, 70, 90) if int(t * 1.6 / 2.0) % 2 == 0 else (90, 255, 140)
        cv.rect(x0, y0, x1, y1, (20, 20, 30, 230))
        if on:
            cv.glow((x0 + x1) / 2, (y0 + y1) / 2, 70, col, 70)
            for i in range(4):
                cx = x0 + 12 + i * 19
                cv.ell(cx, (y0 + y1) / 2, 7, 10, None, col + (255,), 3)
        return cv.im
    return fn


def _street_front(k):
    cv = Cv(k, fill=(240, 200, 40, 0), blend=True)
    cv.rect(990, 1640, 1080, 1960, (40, 40, 44, 255))                   # a bollard, black and yellow
    for y in (1680, 1780, 1880):
        cv.rect(990, y, 1080, y + 40, (240, 200, 40, 255))
    cv.ell(1035, 1640, 45, 16, (60, 60, 64, 255))
    _leaves(cv, 14, -80, 200, 1760, 1990, 60, ((50, 120, 50), (120, 170, 80)), 17)   # a potted plant's leaves
    cv.blur(9)
    return cv


NEAR_D = 1.0005                         # the near footpath: just after the traffic in the stack (which is at d = 1)


def street_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    sky = day_sky(0.5 * s)
    far = skyline(0.5 * s)
    mid = rooftops(0.6 * s)
    st, light = _street(kr, kg)
    near = _street_near(kr)
    fg = _street_front(0.5 * s)
    back = [
        Layer(sky.im, 0.5 * s, 0.0, None, "sky"),
        Layer(far.im, 0.5 * s, 0.18, None, "far"),
        Layer(mid.im, 0.6 * s, 0.5, None, "mid"),
        Layer(st.im, kr, 1.0, None, "set"),
        Layer(light.im, kg, 1.0, None, "sunlight", mode="screen"),
        Layer(_blank(0.4 * s), 0.4 * s, 1.0, _open_sign(0.4 * s), "open_sign", mode="screen"),
        Layer(near.im, kr, NEAR_D, None, "footpath"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return Layered(back, front, light={"ambient": [255, 250, 242], "dir": 1, "vignette": 0.24},
                   horizon=STREET_VP[1], ground=NEAR_KERB)


# ------------------------------------------------------------------ bus stop
STOP_PATH = 1170                                  # (the flats are drawn as before, then moved up to the far footpath)


def _flats(cv, rnd):
    """A row of flats across the road from the bus stop: balconies, a XEROX shop."""
    for (x0, x1, top, col) in ((-20, 360, 560, (226, 206, 176)), (360, 700, 640, (200, 214, 226)),
                               (700, 1100, 520, (232, 200, 190))):
        cv.rect(x0, top, x1, STOP_PATH, col + (255,), INK, 3)
        cv.rect(x0 - 6, top - 12, x1 + 6, top, mul(col, 0.84) + (255,), INK, 2)
        y = top + 30
        while y < 960:
            for bx in range(int(x0) + 26, int(x1) - 90, 110):
                cv.rect(bx, y, bx + 80, y + 70, (130, 164, 196, 255), INK, 2)
                cv.line([(bx + 40, y), (bx + 40, y + 70)], (60, 60, 66, 255), 2)
                cv.rect(bx - 8, y + 56, bx + 88, y + 82, mul(col, 0.9) + (255,), INK, 2)     # balcony wall
                if rnd.random() < 0.35:
                    for j in range(3):                                         # clothes drying
                        c = rnd.choice(((220, 60, 60), (60, 120, 220), (250, 210, 60), (240, 240, 240)))
                        cv.rect(bx + 6 + j * 24, y + 40, bx + 24 + j * 24, y + 60, c + (255,), INK, 1)
            y += 112
    for (x0, x1, text, col) in ((60, 300, "XEROX", (30, 120, 200)), (760, 1000, "STD PCO", (200, 60, 50))):
        quad_image(cv, sign_image(text, col, (255, 255, 255), 800, 200), [(x0, 980), (x1, 980), (x1, 1036), (x0, 1036)])
        cv.rect(x0 + 10, 1040, x1 - 10, STOP_PATH, (150, 150, 156, 255), INK, 2)              # shutters
        for yy in range(1048, STOP_PATH, 12):
            cv.line([(x0 + 12, yy), (x1 - 12, yy)], (120, 120, 126, 255), 2)
    cv.rect(380, 1040, 680, STOP_PATH, (90, 70, 60, 255), INK, 2)          # the building's gate
    for gxx in range(392, 680, 24):
        cv.line([(gxx, 1044), (gxx, STOP_PATH)], (50, 50, 54, 255), 3)


def _tree(cv, x, top, base, spread=230, seed=31):
    cv.poly([(x - 30, base), (x + 30, base), (x + 20, top + 200), (x + 70, top + 120), (x + 50, top + 110),
             (x + 6, top + 180), (x - 10, top + 120), (x - 26, top + 130), (x - 14, top + 210)], (110, 80, 60, 255),
            INK, 3)
    _leaves(cv, 70, x - spread, x + spread, top - 40, top + 200, 46, ((40, 112, 52), (96, 166, 72)), seed)
    _leaves(cv, 26, x - spread * 0.8, x + spread * 0.6, top - 30, top + 90, 36, ((90, 160, 70), (140, 196, 92)),
            seed + 1)


def _busstop(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(255, 236, 190, 0), blend=True)
    _moved_up(cv, lambda c: _flats(c, random.Random(41)), STOP_PATH - FAR_PATH)
    _footpath(cv, FAR_PATH, FAR_KERB, 43)
    _tree(cv, 930, 330, 1150, spread=200)
    _kerb(cv, FAR_KERB, ROAD_TOP)
    _road(cv, ROAD_TOP, ROAD_BOT, 44)
    for (x0, x1) in ((300, 520), (640, 900)):
        light.poly([(x0 - 300, -40), (x1 - 300, -40), (x1 + 100, 1600), (x0 + 100, 1600)], (255, 236, 190, 38))
    light.blur(30)
    return cv, light


def _busstop_near(k):
    """The near footpath with the bus shelter and the BUS STOP sign (drawn after the traffic, which shows through the
    shelter's glass)."""
    cv = Cv(k, blend=True)
    _kerb(cv, ROAD_BOT, NEAR_KERB)
    _footpath(cv, NEAR_KERB, LH, 45, col=(206, 198, 186))
    x0, x1, base = -40, 620, 1600
    cv.poly([(x0 - 30, base + 10), (x1 + 30, base + 10), (x1 + 60, base + 70), (x0 - 60, base + 70)], (20, 20, 30, 50))
    cv.rect(x0, 880, x1, base, (180, 214, 232, 110), INK, 3)                # the glass back
    cv.poly([(x0 + 300, base - 20), (x0 + 380, 900), (x0 + 420, 900), (x0 + 340, base - 20)], (255, 255, 255, 50))
    quad_image(cv, sign_image("CHAI BREAK", (250, 196, 60), (120, 40, 30), 700, 900),
               [(10, 960), (230, 960), (230, 1300), (10, 1300)])
    cv.ell(120, 1200, 34, 24, (240, 240, 240, 255), INK, 2)                 # a cup on the ad
    cv.rect(260, 1440, 600, 1472, (60, 120, 160, 255), INK, 2)              # the bench
    cv.rect(260, 1370, 600, 1390, (60, 120, 160, 255), INK, 2)
    for bx in (280, 580):
        cv.rect(bx - 6, 1472, bx + 6, base, (80, 80, 86, 255))
    for px in (x0 + 10, 300, x1 - 10):                                      # back posts
        cv.rect(px - 8, 640, px + 8, base, (120, 126, 134, 255), INK, 2)
    for px in (x0 - 30, x1 + 30):                                            # front posts
        cv.rect(px - 12, 600, px + 12, 1670, (110, 116, 124, 255), INK, 3)
    cv.poly([(x0 - 80, 600), (x1 + 80, 600), (x1 + 20, 650), (x0 - 20, 650)], (60, 110, 120, 255), INK, 3)
    cv.rect(x0 - 80, 530, x1 + 80, 600, (40, 150, 160, 255), INK, 3)        # the roof's front with its name
    quad_image(cv, sign_image("BUS STOP  21  45  102", (40, 150, 160), (255, 255, 255), 1400, 120),
               [(x0 - 50, 540), (x1 + 50, 540), (x1 + 50, 592), (x0 - 50, 592)])
    px = 880                                                                 # the bus stop sign
    cv.rect(px - 8, 760, px + 8, 1650, (120, 126, 134, 255), INK, 2)
    cv.ell(px, 760, 66, 66, (40, 90, 190, 255), INK, 3)
    cv.ell(px, 760, 56, 56, None, (250, 250, 250, 255), 4)
    cv.rect(px - 32, 734, px + 32, 786, (250, 250, 250, 255))
    cv.rect(px - 25, 740, px + 25, 760, (40, 90, 190, 255))
    cv.ell(px - 18, 788, 8, 8, (40, 40, 44, 255))
    cv.ell(px + 18, 788, 8, 8, (40, 40, 44, 255))
    quad_image(cv, sign_image("BUS STOP", (40, 90, 190), (255, 255, 255), 600, 160),
               [(px - 80, 840), (px + 80, 840), (px + 80, 886), (px - 80, 886)])
    return cv


def _leaf_shadows(k, region=(740, 1100, 1100, 1160), seed=47):
    """fn: the tree's dappled shade on the footpath, moving a little in the breeze."""
    rnd = random.Random(seed)
    spots = [(rnd.uniform(region[0], region[2]), rnd.uniform(region[1], region[3]), rnd.uniform(10, 24),
              rnd.uniform(0, 6.28)) for _ in range(22)]

    def fn(_im, t):
        cv = Cv(k, fill=(20, 30, 20, 0))
        for (x, y, r, ph) in spots:
            cv.ell(x + math.sin(t * 0.9 + ph) * 5, y, r, r * 0.35, (20, 30, 20, 60))
        cv.blur(3)
        return cv.im
    return fn


def _busstop_front(k):
    cv = Cv(k, fill=(60, 120, 60, 0), blend=True)
    _leaves(cv, 22, 820, 1180, -120, 160, 60, ((36, 96, 44), (70, 140, 60)), 53)   # branches over the top
    cv.blur(9)
    return cv


def busstop_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    sky = day_sky(0.5 * s, sun=(200, 260), seed=7)
    far = skyline(0.5 * s, seed=9, tops=(300, 500))
    st, light = _busstop(kr, kg)
    near = _busstop_near(kr)
    fg = _busstop_front(0.5 * s)
    back = [
        Layer(sky.im, 0.5 * s, 0.0, None, "sky"),
        Layer(far.im, 0.5 * s, 0.2, None, "far"),
        Layer(st.im, kr, 1.0, None, "set"),
        Layer(light.im, kg, 1.0, None, "sunlight", mode="screen"),
        Layer(_blank(0.4 * s), 0.4 * s, 1.0, _leaf_shadows(0.4 * s), "leaf_shade"),
        Layer(near.im, kr, NEAR_D, None, "footpath"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return Layered(back, front, light={"ambient": [255, 250, 240], "dir": -1, "vignette": 0.24},
                   horizon=STREET_VP[1], ground=NEAR_KERB)


# ------------------------------------------------------------------ market
MARKET_FLOOR = 1300
STALLS = [(20, (220, 50, 50), "SABZI", (40, 140, 70), "veg"),
          (380, (240, 170, 30), "FRUITS", (220, 120, 30), "fruit"),
          (740, (40, 140, 90), "MASALA", (180, 60, 40), "spice")]
STALL_W = 320
COUNTER_TOP, COUNTER_BOT = 1150, 1300


def _old_market(k):
    """Far layer: the old market behind, sandstone buildings with arches, crowd far away, all hazy."""
    cv = Cv(k, blend=True)
    cv.im = vgrad(k, [(0, (250, 200, 150)), (600, (252, 222, 176)), (1000, (246, 230, 200)), (LH, (240, 226, 200))])
    cv.d = ImageDraw.Draw(cv.im)
    rnd = random.Random(61)
    x = -30
    while x < LW + 30:
        w = rnd.uniform(140, 220)
        top = rnd.uniform(380, 560)
        col = mix((214, 160, 120), (236, 196, 150), rnd.random())
        cv.rect(x, top, x + w, 1200, col + (255,))
        cv.rect(x - 4, top - 10, x + w + 4, top, mul(col, 0.86) + (255,))
        for wy in range(int(top) + 40, 1000, 110):
            for wx in range(int(x) + 20, int(x + w) - 50, 60):
                cv.rect(wx, wy + 20, wx + 36, wy + 70, mul(col, 0.7) + (255,))
                cv.ell(wx + 18, wy + 20, 18, 18, mul(col, 0.7) + (255,))
        x += w + rnd.uniform(4, 16)
    for i in range(40):                                                    # far crowd
        px = rnd.uniform(0, LW)
        h = rnd.uniform(80, 110)
        c = rnd.choice(((180, 80, 80), (80, 110, 170), (200, 170, 80), (120, 120, 120), (230, 230, 220)))
        cv.rect(px - 12, 1200 - h * 0.65, px + 12, 1200, mix(c, (240, 220, 190), 0.4) + (255,))
        cv.ell(px, 1200 - h * 0.75, 10, 12, mix((150, 100, 70), (240, 220, 190), 0.4) + (255,))
    cv.rect(-10, 1060, LW + 10, 1240, (246, 226, 196, 110))
    cv.blur(2.6)
    return cv


def _stall_back(cv, x, canopy, sign, sign_col, kind, rnd):
    x0, x1 = x, x + STALL_W
    for px in (x0 + 10, x1 - 10):                                          # bamboo poles
        cv.rect(px - 6, 860, px + 6, MARKET_FLOOR, (170, 130, 80, 255), INK, 2)
    cv.rect(x0 + 18, 960, x1 - 18, COUNTER_TOP + 10, (120, 96, 76, 255), INK, 2)   # the back of the stall
    for (yy, n) in ((1000, 6), (1070, 5)):                                 # crates on the back shelves
        for j in range(n):
            cx = x0 + 40 + j * (STALL_W - 80) / float(n - 1)
            cv.rect(cx - 22, yy, cx + 22, yy + 40, (190, 150, 100, 255), INK, 2)
            for b in range(3):
                col = {"veg": ((60, 150, 60), (230, 60, 50), (150, 80, 160)),
                       "fruit": ((250, 200, 40), (230, 60, 50), (250, 140, 30)),
                       "spice": ((210, 60, 30), (240, 190, 40), (140, 80, 40))}[kind][(b + j) % 3]
                cv.ell(cx - 12 + b * 12, yy + 4, 8, 7, col + (255,), INK, 1)
    if kind == "fruit":                                                    # bananas hanging
        for j in range(3):
            bx = x0 + 70 + j * 90
            cv.line([(bx, 900), (bx, 930)], (110, 80, 50, 255), 3)
            for b in range(5):
                cv.ell(bx - 12 + b * 6, 948 + (b % 2) * 6, 7, 20, (250, 210, 60, 255), INK, 1)
    elif kind == "veg":                                                    # a weighing scale hanging
        cv.line([(x0 + 160, 880), (x0 + 160, 930)], (80, 80, 86, 255), 3)
        cv.line([(x0 + 110, 930), (x0 + 210, 930)], (80, 80, 86, 255), 4)
        for sx in (x0 + 110, x0 + 210):
            cv.line([(sx, 930), (sx - 16, 960), (sx + 16, 960), (sx, 930)], (80, 80, 86, 255), 2)
            cv.ell(sx, 962, 20, 6, (170, 170, 176, 255), INK, 1)
    else:                                                                  # strings of red chillies
        for j in range(4):
            bx = x0 + 60 + j * 70
            for b in range(6):
                cv.ell(bx, 900 + b * 12, 5, 9, (200, 40, 30, 255), INK, 1)
    n = 9                                                                  # the striped canopy
    for i in range(n):
        a, b = x0 - 6 + (STALL_W + 12) * i / float(n), x0 - 6 + (STALL_W + 12) * (i + 1) / float(n)
        col = canopy if i % 2 == 0 else (245, 245, 240)
        cv.poly([(a + 10, 790), (b + 10, 790), (b, 860), (a, 860)], col + (255,))
        cv.ell((a + b) / 2, 860, (b - a) / 2, 10, col + (255,))
    cv.line([(x0 + 4, 790), (x1 + 16, 790)], INK, 3)
    quad_image(cv, sign_image(sign, (250, 248, 236), sign_col, 700, 160), [(x0 + 40, 740), (x1 - 40, 740),
                                                                          (x1 - 40, 784), (x0 + 40, 784)])
    for sx in (x0 + 60, x1 - 60):
        cv.line([(sx, 784), (sx, 790)], INK, 2)


def _market(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(255, 230, 180, 0), blend=True)
    rnd = random.Random(71)
    fill_tex(cv, [(-10, 1180), (LW + 10, 1180), (LW + 10, LH), (-10, LH)],
             [(1180, (200, 176, 140)), (LH, (176, 150, 116))], seed=73, cell=20, lo=0.9, hi=1.08)
    vp = (540, 860)
    for y in (1220, 1300, 1420, 1580, 1780):                               # old stone pavers
        cv.line([(-10, y), (LW + 10, y)], (160, 136, 104, 200), 2)
    for x in range(-900, 2000, 120):
        cv.line([(gx(x, 1180, 1180, vp), 1180), (gx(x, 1180, LH, vp), LH)], (160, 136, 104, 170), 2)
    for (x, canopy, sign, sign_col, kind) in STALLS:
        _stall_back(cv, x, canopy, sign, sign_col, kind, rnd)
    for _ in range(26):                                                    # leaves and bits on the ground
        x, y = rnd.uniform(0, LW), rnd.uniform(1320, 1900)
        cv.ell(x, y, rnd.uniform(5, 12), rnd.uniform(3, 6), rnd.choice(((80, 150, 60), (200, 70, 50), (120, 100, 70)))
               + (220,))
    for (x0, y0) in ((350, 1330), (712, 1320)):                            # sacks between the stalls
        cv.poly([(x0 - 26, y0), (x0 + 26, y0), (x0 + 22, y0 - 70), (x0 + 8, y0 - 82), (x0 - 8, y0 - 82),
                 (x0 - 22, y0 - 70)], (210, 186, 140, 255), INK, 2)
        cv.ell(x0, y0 - 74, 18, 6, (180, 130, 60, 255), INK, 1)
    cv.line(catenary(-40, 640, 1120, 600, 120), (60, 50, 50, 255), 3)
    light.glow(540, 300, 600, (255, 230, 170), 50)
    for (x0, x1) in ((150, 330), (560, 700)):
        light.poly([(x0 + 200, -40), (x1 + 200, -40), (x1 - 80, 1500), (x0 - 80, 1500)], (255, 230, 170, 34))
    light.blur(30)
    return cv, light


def _stall_counter(k, x, kind, seed):
    """The front of a stall: a wooden counter with its heaps of produce (a Sprite: people sort with it)."""
    x0, y0, x1, y1 = x, COUNTER_TOP - 70, x + STALL_W, COUNTER_BOT + 10
    cv = Cv(k, w=x1 - x0, h=y1 - y0, blend=True)

    def P(pts):
        return [(px - x0, py - y0) for px, py in pts]
    rnd = random.Random(seed)
    cv.poly(P([(x + 8, COUNTER_TOP), (x + STALL_W - 8, COUNTER_TOP), (x + STALL_W - 2, COUNTER_TOP + 16),
               (x + 2, COUNTER_TOP + 16)]), (170, 120, 76, 255), INK, 2)
    cv.poly(P([(x + 2, COUNTER_TOP + 16), (x + STALL_W - 2, COUNTER_TOP + 16), (x + STALL_W - 2, COUNTER_BOT),
               (x + 2, COUNTER_BOT)]), (196, 146, 96, 255), INK, 3)
    for u in (0.25, 0.5, 0.75):
        cx = x + STALL_W * u
        cv.line(P([(cx, COUNTER_TOP + 18), (cx, COUNTER_BOT - 2)]), (150, 108, 70, 255), 3)
    for yy in (COUNTER_TOP + 60, COUNTER_TOP + 104):
        cv.line(P([(x + 4, yy), (x + STALL_W - 4, yy)]), (166, 120, 80, 255), 2)
    cols = {"veg": [(60, 150, 60), (230, 60, 50), (150, 80, 160), (250, 140, 40)],
            "fruit": [(250, 200, 40), (230, 60, 50), (250, 140, 30), (120, 190, 60)],
            "spice": [(210, 60, 30), (240, 190, 40), (140, 80, 40), (230, 120, 40)]}[kind]
    for j in range(5):                                                     # heaps on the counter
        cx = x + 40 + j * 58
        col = cols[j % len(cols)]
        if kind == "spice":                                                # cones of powder in bowls
            cv.ell(*P([(cx, COUNTER_TOP - 2)])[0], 26, 8, (200, 200, 206, 255), INK, 2)
            cv.poly(P([(cx - 24, COUNTER_TOP - 4), (cx + 24, COUNTER_TOP - 4), (cx, COUNTER_TOP - 44)]), col + (255,),
                    INK, 2)
        else:
            for b in range(7):
                bx = cx - 18 + (b % 4) * 12 + (b // 4) * 6
                by = COUNTER_TOP - 8 - (b // 4) * 14
                cv.ell(*P([(bx, by)])[0], 10, 9, mix(col, (255, 255, 255), rnd.uniform(0, 0.15)) + (255,), INK, 1)
    if kind == "veg":                                                      # a bunch of greens
        cv.poly(P([(x + 280, COUNTER_TOP), (x + 310, COUNTER_TOP), (x + 320, COUNTER_TOP - 50),
                   (x + 270, COUNTER_TOP - 54)]), (70, 150, 60, 255), INK, 2)
    return Sprite(cv.im, k, x0, y0, COUNTER_BOT, "counter")


def _bunting(k):
    """fn: bunting across the market, the flags swinging in the breeze."""
    pts = catenary(-40, 640, 1120, 600, 120)
    flags = along(pts, 46)
    pal = [(230, 60, 60), (250, 200, 50), (60, 160, 80), (70, 120, 220), (240, 120, 40), (240, 240, 236)]

    def fn(_im, t):
        cv = Cv(k, fill=(240, 120, 40, 0))
        for i, (bx, by) in enumerate(flags):
            sw = math.sin(t * 2.4 + i * 0.7) * 7
            cv.poly([(bx - 18, by), (bx + 18, by), (bx + sw, by + 46)], pal[i % len(pal)] + (255,))
        return cv.im
    return fn


def _market_front(k):
    cv = Cv(k, fill=(200, 60, 40, 0), blend=True)
    # a basket of tomatoes bottom-right, a stack of crates bottom-left
    cv.ell(980, 1860, 170, 50, (170, 120, 60, 255))
    cv.poly([(810, 1860), (1150, 1860), (1120, 1960), (840, 1960)], (190, 140, 70, 255))
    rnd = random.Random(79)
    for _ in range(18):
        cv.ell(rnd.uniform(840, 1120), rnd.uniform(1790, 1860), 26, 24, (220, 50, 40, 255))
    for (x0, y0) in ((-40, 1780), (-40, 1680)):
        cv.rect(x0, y0, x0 + 200, y0 + 100, (190, 150, 100, 255))
        for yy in range(y0 + 18, y0 + 100, 26):
            cv.rect(x0, yy, x0 + 200, yy + 8, (150, 110, 70, 255))
    cv.blur(9)
    return cv


def market_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    far = _old_market(0.5 * s)
    st, light = _market(kr, kg)
    fg = _market_front(0.5 * s)
    counters = [_stall_counter(kr, x, kind, 80 + i) for i, (x, _c, _s, _sc, kind) in enumerate(STALLS)]
    back = [
        Layer(far.im, 0.5 * s, 0.15, None, "far"),
        Layer(st.im, kr, 1.0, None, "set"),
        Layer(light.im, kg, 1.0, None, "sunlight", mode="screen"),
        Layer(_blank(0.5 * s), 0.5 * s, 1.0, _bunting(0.5 * s), "bunting"),
        Layer(_blank(0.3 * s), 0.3 * s, 1.0, motes(((200, 500), (900, 1300), 260), 0.3 * s), "dust", mode="screen"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return Layered(back, front, light={"ambient": [255, 246, 232], "dir": 1, "vignette": 0.26},
                   horizon=860, ground=MARKET_FLOOR, sprites=counters)

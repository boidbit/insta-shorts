"""Hand-made 2.5D sets: the wedding stage, the graveyard and the road at night.

mandap_25d     the wedding stage (shaadi ka stage, no ritual things on it): drapes of red and gold, a canopy of
               marigold strings, fairy lights that twinkle, the two big chairs of the couple on a raised stage,
               flower stands, rose petals on the floor, a chandelier, a glowing back wall, petals falling.
graveyard_25d  a spooky graveyard at night (horror-comedy): a big moon behind thin clouds, a dead tree with a crow,
               an iron fence and gate, old RIP stones leaning, a lantern, fog drifting over the ground, bats.
night_road_25d a road at night: the moon and stars, the city's lights far away, a wall and trees across the road,
               a street lamp with its pool of light and moths round it; the people stand on the footpath and now and
               then a car passes behind them with its headlights on.
(mandap is the place for weddings, so it has no writing; the graveyard's stones say RIP: it is never mirrored.)
"""
import math
import random

from PIL import Image, ImageDraw

from .scenery import PAL_BULB, Cv, Layer, Layered, along, catenary, fill_tex, mul, quad_image, sign_image, \
    twinkle, vgrad
from .scenery_home import _floor_tiles, _leaves
from .scenery_road import FAR_PATH, NEAR_KERB, ROAD_BOT, ROAD_TOP, STREET_VP, FAR_KERB, _footpath, _kerb, skyline
from ..util import LH, LW

INK = (40, 32, 36, 255)


def _blank(k, fill=(0, 0, 0, 0)):
    return Image.new("RGBA", (8, 8), fill)


# ------------------------------------------------------------------ mandap (wedding stage)
MD_F = 1280
STAGE = (180, 1060, 900, 1180)                 # x0, top, x1, front edge


def _mandap(k, kg):
    cv = Cv(k, blend=True)
    gA = Cv(kg, fill=(255, 200, 120, 0))
    gB = Cv(kg, fill=(255, 200, 120, 0))
    gS = Cv(kg, fill=(255, 210, 150, 0))
    cv.im = vgrad(k, [(0, (110, 20, 34)), (MD_F, (160, 40, 44)), (LH, (160, 40, 44))])
    cv.d = ImageDraw.Draw(cv.im)
    for i, x in enumerate(range(-60, LW + 60, 120)):                                    # the drapes
        col = (196, 40, 56) if i % 2 else (236, 176, 70)
        cv.poly([(x, 0), (x + 120, 0), (x + 100, MD_F), (x + 20, MD_F)], col + (255,))
        cv.line([(x + 60, 0), (x + 60, MD_F)], mul(col, 0.8) + (255,), 3)
    gS.glow(540, 700, 520, (255, 200, 140), 70)                                         # the glowing back wall
    for x in range(60, LW, 120):                                                        # strings of marigold
        for (bx, by) in along([(x, 0), (x, 860)], 22):
            cv.ell(bx, by, 11, 11, ((250, 150, 20), (250, 200, 40))[int(by / 22) % 2] + (255,))
    for j in range(5):                                                                  # the canopy of flowers
        pts = catenary(-20, 120 + j * 40, LW + 20, 120 + j * 40, 90 + j * 16)
        for i, (bx, by) in enumerate(along(pts, 26)):
            cv.ell(bx, by, 12, 12, ((250, 150, 20), (250, 240, 236), (230, 60, 80))[(i + j) % 3] + (255,))
        for i, (bx, by) in enumerate(along(pts, 40)):
            (gA if (i + j) % 2 else gB).ell(bx, by + 18, 5, 5, PAL_BULB[(i + j) % len(PAL_BULB)] + (250,))
            gS.ell(bx, by + 18, 14, 14, PAL_BULB[(i + j) % len(PAL_BULB)] + (40,))
    cx = 540                                                                            # a chandelier
    cv.line([(cx, 0), (cx, 300)], (200, 170, 90, 255), 4)
    cv.ell(cx, 330, 120, 30, (230, 196, 100, 255), INK, 2)
    for i in range(9):
        x = cx - 110 + i * 27.5
        cv.line([(x, 330), (x, 380 + (i % 2) * 20)], (250, 240, 220, 255), 3)
        cv.ell(x, 384 + (i % 2) * 20, 6, 8, (255, 250, 230, 255))
        gS.glow(x, 384, 40, (255, 240, 200), 60)
    # the raised stage with the couple's two chairs
    x0, top, x1, front = STAGE
    cv.poly([(x0 - 40, front), (x1 + 40, front), (x1, top), (x0, top)], (230, 210, 200, 255), INK, 3)
    cv.rect(x0 - 40, front, x1 + 40, MD_F, (200, 60, 60, 255), INK, 3)
    for x in range(int(x0) - 30, int(x1) + 40, 60):
        cv.ell(x, front + 10, 12, 12, (250, 150, 20, 255))
    for (chx, col) in ((400, (200, 40, 50)), (680, (200, 40, 50))):
        cv.poly([(chx - 90, 1110), (chx + 90, 1110), (chx + 80, 860), (chx, 800), (chx - 80, 860)],
                (230, 190, 90, 255), INK, 3)                                           # its golden back
        cv.poly([(chx - 66, 1100), (chx + 66, 1100), (chx + 60, 880), (chx, 836), (chx - 60, 880)], col + (255,))
        cv.rect(chx - 100, 1060, chx + 100, 1130, (230, 190, 90, 255), INK, 3)          # seat
        cv.rect(chx - 90, 1070, chx + 90, 1110, col + (255,))
        for lx in (chx - 90, chx + 80):
            cv.rect(lx, 1130, lx + 12, 1170, (200, 160, 70, 255), INK, 1)
    for fx in (110, 970):                                                               # flower stands
        cv.rect(fx - 8, 900, fx + 8, MD_F, (220, 190, 100, 255), INK, 2)
        cv.poly([(fx - 50, 900), (fx + 50, 900), (fx + 30, 940), (fx - 30, 940)], (220, 190, 100, 255), INK, 2)
        _leaves(cv, 16, fx - 80, fx + 80, 780, 900, 30, ((240, 240, 236), (250, 160, 190)), fx)
    _floor_tiles(cv, (540, 800), MD_F, (200, 60, 54), (180, 50, 46), step=140, grow=1.24, grout=(150, 40, 36, 255))
    rnd = random.Random(501)
    for _ in range(60):                                                                 # rose petals
        x, y = rnd.uniform(0, LW), rnd.uniform(MD_F + 20, LH)
        cv.ell(x, y, 9, 5, rnd.choice(((230, 40, 70), (250, 150, 20), (250, 240, 236))) + (255,))
    for b in (gA, gB):
        b.blur(1.0)
    gS.blur(14)
    return cv, gA, gB, gS


def _petals(k, n=14, seed=503):
    """fn: petals drifting down."""
    rnd = random.Random(seed)
    ps = [(rnd.uniform(0, LW), rnd.uniform(0, 1), rnd.uniform(0.6, 1.1), rnd.uniform(0, 6.28),
           rnd.choice(((230, 40, 70), (250, 150, 20), (250, 240, 236)))) for _ in range(n)]

    def fn(_im, t):
        cv = Cv(k, fill=(230, 40, 70, 0))
        for (x0, ph, sp, rot, col) in ps:
            u = (t * 0.06 * sp + ph) % 1.0
            x = x0 + math.sin(t * 1.4 + rot) * 50
            y = u * (LH + 100) - 50
            a = t * 3 + rot
            cv.ell(x, y, 10 * abs(math.cos(a)) + 3, 6, col + (230,))
        return cv.im
    return fn


def _mandap_front(k):
    cv = Cv(k, fill=(250, 150, 20, 0), blend=True)
    for x in (-40, 1040):                                                               # marigold strings in front
        for (bx, by) in along([(x + 40, -40), (x + 50, 560)], 30):
            cv.ell(bx, by, 22, 22, ((250, 150, 20), (250, 200, 40))[int(by / 30) % 2] + (255,))
    cv.blur(8)
    return cv


def mandap_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    st, gA, gB, gS = _mandap(kr, kg)
    fg = _mandap_front(0.5 * s)
    back = [
        Layer(st.im, kr, 1.0, None, "set"),
        Layer(gA.im, kg, 1.0, twinkle((gA.im, gB.im), 0.7, static=gS.im), "lights", mode="screen"),
        Layer(_blank(0.5 * s), 0.5 * s, 1.0, _petals(0.5 * s), "petals"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return Layered(back, front, light={"ambient": [255, 236, 220], "dir": 1, "vignette": 0.3}, horizon=800,
                   ground=MD_F)


# ------------------------------------------------------------------ graveyard
GY_F = 1240
MOON = (260, 300)


def _gy_sky(k):
    cv = Cv(k, blend=True)
    cv.im = vgrad(k, [(0, (16, 18, 44)), (700, (40, 44, 86)), (1100, (70, 74, 110)), (LH, (70, 74, 110))])
    cv.d = ImageDraw.Draw(cv.im)
    rnd = random.Random(511)
    for _ in range(120):
        x, y = rnd.uniform(0, LW), rnd.uniform(0, 900)
        cv.ell(x, y, rnd.choice((1.2, 1.6, 2.2)), rnd.choice((1.2, 1.6, 2.2)), (255, 250, 230, int(rnd.uniform(80, 230))))
    g = Cv(k, fill=(240, 236, 210, 0))
    g.glow(MOON[0], MOON[1], 300, (230, 230, 210), 90)
    g.blur(20)
    cv.over(g)
    cv.ell(MOON[0], MOON[1], 110, 110, (244, 240, 214, 255))
    for (cx, cy, r) in ((230, 270, 20), (300, 340, 14), (270, 320, 9)):
        cv.ell(cx, cy, r, r, (220, 216, 190, 255))
    for (y, a) in ((330, 120), (380, 90)):                                              # thin clouds over the moon
        cv.ell(MOON[0] + 40, y, 260, 18, (90, 94, 130, a))
    cv.poly([(-20, 1100), (200, 980), (420, 1040), (640, 960), (900, 1030), (1100, 990), (1100, 1200), (-20, 1200)],
            (34, 38, 60, 255))                                                          # hills
    cv.blur(1.0)
    return cv


def _graveyard(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(255, 220, 150, 0))
    rnd = random.Random(513)
    fill_tex(cv, [(-20, GY_F - 60), (LW + 20, GY_F - 60), (LW + 20, LH), (-20, LH)],
             [(GY_F - 60, (50, 66, 54)), (LH, (40, 52, 42))], seed=515, cell=14, lo=0.88, hi=1.1)
    for _ in range(90):                                                                 # grass blades
        x, y = rnd.uniform(0, LW), rnd.uniform(GY_F - 40, LH)
        cv.line([(x, y), (x + rnd.uniform(-6, 6), y - rnd.uniform(10, 24))], (70, 90, 70, 255), 2)
    # the dead tree with a crow
    tx = 900
    cv.poly([(tx - 30, GY_F - 40), (tx + 30, GY_F - 40), (tx + 14, 700), (tx + 4, 520), (tx - 10, 700)], (30, 26, 30, 255))
    for (a, b, c, d, w) in ((tx + 8, 760, tx + 160, 620, 12), (tx + 4, 640, tx - 140, 520, 10),
                            (tx + 120, 650, tx + 190, 560, 6), (tx - 100, 545, tx - 170, 470, 5),
                            (tx + 6, 560, tx + 60, 430, 7)):
        cv.line([(a, b), (c, d)], (30, 26, 30, 255), w)
    cv.ell(tx + 150, 610, 18, 12, (20, 20, 24, 255))                                    # the crow
    cv.ell(tx + 166, 598, 9, 8, (20, 20, 24, 255))
    cv.poly([(tx + 174, 598), (tx + 186, 601), (tx + 174, 604)], (200, 160, 60, 255))
    # the iron fence and its gate
    fy = GY_F - 70
    for x in range(-10, LW + 20, 40):
        if 420 < x < 640:
            continue
        cv.line([(x, fy), (x, fy - 160)], (24, 24, 30, 255), 6)
        cv.poly([(x - 8, fy - 160), (x, fy - 180), (x + 8, fy - 160)], (24, 24, 30, 255))
    for y in (fy - 30, fy - 130):
        cv.line([(-10, y), (420, y)], (24, 24, 30, 255), 5)
        cv.line([(640, y), (LW + 10, y)], (24, 24, 30, 255), 5)
    for gx0 in (430, 540):                                                              # the gate, half open
        cv.rect(gx0, fy - 220, gx0 + 100, fy, None, (24, 24, 30, 255), 6)
        for x in range(gx0 + 20, gx0 + 100, 20):
            cv.line([(x, fy - 220), (x, fy)], (24, 24, 30, 255), 4)
    cv.ell(535, fy - 240, 60, 20, None, (24, 24, 30, 255), 5)
    # the old stones
    for (x, y, w, lean) in ((180, 1400, 130, -6), (520, 1360, 110, 4), (860, 1420, 140, 7), (340, 1270, 90, -3),
                            (720, 1260, 90, 5), (90, 1260, 70, 2)):
        h = w * 1.25
        dx = lean * h / 40.0
        pts = [(x - w / 2, y), (x + w / 2, y), (x + w / 2 + dx, y - h * 0.7), (x + dx, y - h), (x - w / 2 + dx, y - h * 0.7)]
        cv.poly(pts, (150, 150, 160, 255), INK, 4)
        cv.ell(x + dx * 0.9, y - h * 0.86, w * 0.42, h * 0.16, (150, 150, 160, 255))
        quad_image(cv, sign_image("RIP", (150, 150, 160), (60, 60, 70), 300, 160, border=(150, 150, 160)),
                   [(x - w * 0.3 + dx * 0.6, y - h * 0.62), (x + w * 0.3 + dx * 0.6, y - h * 0.62),
                    (x + w * 0.3 + dx * 0.3, y - h * 0.4), (x - w * 0.3 + dx * 0.3, y - h * 0.4)])
        cv.line([(x - w * 0.2, y - h * 0.25), (x - w * 0.05, y - h * 0.15)], (110, 110, 120, 255), 2)   # a crack
        cv.ell(x, y + 6, w * 0.7, 12, (20, 30, 20, 120))
    lx, ly = 300, 1150                                                                  # a lantern on a post
    cv.rect(lx - 6, ly, lx + 6, GY_F + 40, (40, 34, 30, 255))
    cv.rect(lx - 24, ly - 60, lx + 24, ly, (60, 54, 40, 255), INK, 2)
    cv.rect(lx - 16, ly - 52, lx + 16, ly - 8, (255, 210, 120, 255))
    light.glow(lx, ly - 30, 200, (255, 200, 110), 90)
    light.glow(MOON[0], MOON[1], 500, (200, 210, 255), 30)
    light.blur(10)
    return cv, light


def _fog_and_bats(k):
    """fn: fog rolling slowly over the ground, a couple of bats flapping across the moon."""
    rnd = random.Random(517)
    puffs = [(rnd.uniform(-200, LW + 200), rnd.uniform(GY_F - 40, GY_F + 260), rnd.uniform(120, 260),
              rnd.uniform(0.5, 1.2)) for _ in range(12)]

    def fn(_im, t):
        cv = Cv(k, fill=(210, 214, 230, 0))
        for (x0, y, r, sp) in puffs:
            x = (x0 + t * 14 * sp) % (LW + 500) - 250
            cv.ell(x, y, r, r * 0.25, (200, 206, 224, 70))
        for i in range(2):
            u = ((t * 0.07 + i * 0.5) % 1.2) - 0.1
            bx, by = u * LW, 260 + 90 * math.sin(t * 0.8 + i * 2) + i * 60
            fl = math.sin(t * 14 + i) * 12
            cv.poly([(bx - 26, by - fl), (bx - 8, by + 4), (bx, by - 4), (bx + 8, by + 4), (bx + 26, by - fl),
                     (bx, by + 10)], (16, 14, 20, 255))
        cv.blur(6)
        return cv.im
    return fn


def _graveyard_front(k):
    cv = Cv(k, fill=(20, 24, 20, 0), blend=True)
    for x in (-60, 1020):                                                               # dark weeds at the corners
        for j in range(9):
            cv.poly([(x + j * 14, 1960), (x + j * 14 + 16, 1960), (x + j * 14 + 8 + (j - 4) * 10, 1700 + (j % 3) * 50)],
                    (20, 30, 24, 255))
    cv.blur(8)
    return cv


def graveyard_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    sky = _gy_sky(0.5 * s)
    st, light = _graveyard(kr, kg)
    fg = _graveyard_front(0.5 * s)
    back = [
        Layer(sky.im, 0.5 * s, 0.05, None, "sky"),
        Layer(st.im, kr, 1.0, None, "set"),
        Layer(light.im, kg, 1.0, None, "lantern", mode="screen"),
        Layer(_blank(0.4 * s), 0.4 * s, 1.0, _fog_and_bats(0.4 * s), "fog"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return Layered(back, front, light={"ambient": [196, 204, 236], "dir": -1, "vignette": 0.44}, horizon=1000,
                   ground=GY_F)


# ------------------------------------------------------------------ night road
LAMP = (860, 520)


def _night_sky(k):
    cv = Cv(k, blend=True)
    cv.im = vgrad(k, [(0, (10, 14, 40)), (600, (24, 30, 70)), (1000, (60, 54, 96)), (LH, (60, 54, 96))])
    cv.d = ImageDraw.Draw(cv.im)
    rnd = random.Random(521)
    for _ in range(160):
        x, y = rnd.uniform(0, LW), rnd.uniform(0, 900)
        r = rnd.choice((1.2, 1.5, 2.0, 2.6))
        cv.ell(x, y, r, r, (255, 250, 230, int(rnd.uniform(90, 240))))
    g = Cv(k, fill=(240, 236, 210, 0))
    g.glow(820, 230, 200, (230, 230, 210), 70)
    g.blur(16)
    cv.over(g)
    cv.ell(820, 230, 64, 64, (246, 242, 216, 255))
    cv.ell(846, 214, 58, 58, (24, 30, 70, 255))                                          # a crescent
    cv.blur(0.8)
    return cv


def _city_lights(k):
    """Far layer: the city at night (dark towers, lit windows) far beyond the road."""
    cv = skyline(k, seed=523, tops=(560, 800), base=1120, tint=(40, 44, 70), haze=(60, 60, 96))
    rnd = random.Random(525)
    for _ in range(240):
        x, y = rnd.uniform(0, LW), rnd.uniform(600, 1100)
        if cv.im.getpixel((int(x * k), int(y * k)))[3] > 200:
            cv.rect(x, y, x + 8, y + 10, rnd.choice(((255, 210, 130), (255, 230, 170), (200, 220, 255))) + (255,))
    cv.blur(1.0)
    return cv


def _night_far_side(k):
    """Across the road: a long wall with trees behind it, the far footpath, the far kerb, the road."""
    cv = Cv(k, blend=True)
    fill_tex(cv, [(-20, 940), (LW + 20, 940), (LW + 20, FAR_PATH), (-20, FAR_PATH)],
             [(940, (70, 66, 80)), (FAR_PATH, (56, 52, 64))], seed=527, cell=20, lo=0.9, hi=1.08)
    cv.rect(-20, 930, LW + 20, 946, (90, 86, 100, 255), INK, 2)
    for x in range(0, LW, 160):
        cv.rect(x, 940, x + 6, FAR_PATH, (48, 44, 56, 255))
    _leaves(cv, 50, -60, LW + 60, 700, 950, 56, ((20, 40, 34), (34, 56, 44)), 529)       # trees behind the wall
    _footpath(cv, FAR_PATH, FAR_KERB, 531, col=(86, 84, 96))
    _kerb(cv, FAR_KERB, ROAD_TOP)
    fill_tex(cv, [(-10, ROAD_TOP), (LW + 10, ROAD_TOP), (LW + 10, ROAD_BOT), (-10, ROAD_BOT)],
             [(ROAD_TOP, (44, 46, 56)), (ROAD_BOT, (36, 38, 46))], seed=533, cell=10, lo=0.88, hi=1.1)
    ym = (ROAD_TOP + ROAD_BOT) / 2.0
    for x in range(-60, LW + 60, 170):
        cv.rect(x, ym - 5, x + 90, ym + 5, (210, 210, 200, 255))
    return cv


def _night_near(k, kg):
    """The near footpath the people stand on and the street lamp with its pool of light."""
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(255, 220, 150, 0))
    _kerb(cv, ROAD_BOT, NEAR_KERB)
    _footpath(cv, NEAR_KERB, LH, 535, col=(96, 94, 104))
    lx, ly = LAMP
    cv.rect(lx + 120 - 9, ly, lx + 120 + 9, 1660, (60, 62, 70, 255), INK, 2)
    cv.line([(lx + 120, ly + 10), (lx + 80, ly - 20), (lx, ly - 10)], (60, 62, 70, 255), 9)
    cv.poly([(lx - 40, ly - 12), (lx + 30, ly - 12), (lx + 18, ly + 8), (lx - 28, ly + 8)], (230, 232, 220, 255), INK, 2)
    cv.ell(lx - 5, ly + 10, 26, 8, (255, 240, 190, 255))
    light.glow(lx - 5, ly + 10, 160, (255, 220, 150), 120)
    light.poly([(lx - 30, ly + 14), (lx + 20, ly + 14), (lx + 360, 1760), (lx - 440, 1760)], (255, 214, 140, 40))
    light.ell(lx - 40, 1740, 420, 90, (255, 214, 140, 60))
    light.blur(18)
    return cv, light


def _night_cars(k):
    """fn (normal): now and then a car passes on the road behind the people, its headlights on (a dark body, lit
    windows, the beam ahead, red lights behind)."""
    lane = 1470
    f = (lane - STREET_VP[1]) / (1700.0 - STREET_VP[1])
    L, H = 1150 * f, 420 * f                                   # in proportion to the people on the footpath

    def fn(_im, t):
        cv = Cv(k, fill=(255, 240, 200, 0))
        ph = (t - 2.0) % 10.0
        if t < 2.0 or ph > 4.0:
            return cv.im
        right = int((t - 2.0) // 10.0) % 2 == 0
        u = ph / 4.0
        x = -L - 300 + u * (LW + 2 * L + 600) if right else LW + 300 - u * (LW + 2 * L + 600)
        d = 1 if right else -1
        x0, x1 = (x - L, x) if right else (x, x + L)
        front = x1 if right else x0
        back = x0 if right else x1
        beam = Cv(k, fill=(255, 240, 190, 0))                                            # the beam, soft
        beam.poly([(front + d * 420, lane - H * 0.5), (front + d * 420, lane + 30), (front, lane - 24),
                   (front, lane - H * 0.4)], (255, 240, 190, 90))
        beam.blur(16)
        cv.im.alpha_composite(beam.im)
        cv.d = ImageDraw.Draw(cv.im)
        cv.poly([(x0, lane - H * 0.45), (x1, lane - H * 0.45), (x1, lane - 30), (x0, lane - 30)],
                (24, 24, 30, 255))
        cv.poly([(x0 + L * 0.22, lane - H * 0.45), (x0 + L * 0.34, lane - H), (x0 + L * 0.7, lane - H),
                 (x0 + L * 0.82, lane - H * 0.45)], (30, 30, 36, 255))
        cv.poly([(x0 + L * 0.28, lane - H * 0.5), (x0 + L * 0.37, lane - H * 0.92), (x0 + L * 0.66, lane - H * 0.92),
                 (x0 + L * 0.76, lane - H * 0.5)], (90, 100, 130, 255))
        for wx in (x0 + L * 0.2, x0 + L * 0.8):
            cv.ell(wx, lane - 30, H * 0.17, H * 0.17, (14, 14, 18, 255))
        cv.ell(front - d * 10, lane - H * 0.36, 16, 12, (255, 250, 220, 255))
        cv.ell(back + d * 8, lane - H * 0.36, 12, 10, (240, 40, 40, 255))
        return cv.im
    return fn


def _moths(k):
    """fn (screen): moths fluttering round the street lamp."""
    lx, ly = LAMP

    def fn(_im, t):
        cv = Cv(k, fill=(255, 240, 200, 0))
        for i in range(5):
            a = t * (2.0 + i * 0.4) + i * 1.3
            x = lx - 5 + math.cos(a) * (30 + i * 9) + math.sin(t * 7 + i) * 6
            y = ly + 40 + math.sin(a * 1.3) * (20 + i * 6)
            cv.ell(x, y, 3, 3, (255, 250, 230, 230))
        return cv.im
    return fn


def night_road_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    sky = _night_sky(0.5 * s)
    city = _city_lights(0.5 * s)
    far = _night_far_side(kr)
    near, light = _night_near(kr, kg)
    back = [
        Layer(sky.im, 0.5 * s, 0.0, None, "sky"),
        Layer(city.im, 0.5 * s, 0.15, None, "city"),
        Layer(far.im, kr, 1.0, None, "set"),
        Layer(_blank(0.5 * s), 0.5 * s, 1.0, _night_cars(0.5 * s), "cars"),
        Layer(near.im, kr, 1.0005, None, "footpath"),
        Layer(light.im, kg, 1.0005, None, "lamp", mode="screen"),
        Layer(_blank(0.4 * s), 0.4 * s, 1.0005, _moths(0.4 * s), "moths", mode="screen"),
    ]
    return Layered(back, [], light={"ambient": [170, 180, 230], "dir": 1, "vignette": 0.4}, horizon=STREET_VP[1],
                   ground=NEAR_KERB)

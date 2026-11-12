"""More hand-made 2.5D sets.

jungle_25d   a jungle by day in three depths: misty trunks far away, trees with hanging vines in the middle, big
             trunks, ferns, a path, a fallen log and mushrooms near; sun rays through the leaves, motes and falling
             leaves in them, blurred fern fronds right in front of the lens.
haunted_25d  the haunted house at night: a big moon with a halo, clouds, bats flying across, dead trees, the old
             house with broken shutters and a window whose light flickers, a lantern, a broken fence, fog drifting
             over the ground (and in front of the lens).
bedroom_25d  a bedroom by day: the bed against the wall with pillows and a quilt, a bedside lamp, a wardrobe, a
             shelf with books, a window with curtains and its sunlight, a ceiling fan turning, a rug.
"""
import math
import random

from PIL import Image, ImageDraw

from .scenery import Cv, Layer, Layered, fill_tex, mix, motes, mul, toward, vgrad
from .scenery_home import _box, _clock, _curtain, _leaves, _room_outside, _shadow, _window, fan
from ..util import LH, LW

INK = (40, 34, 30, 255)


def _blank(k, fill=(0, 0, 0, 0)):
    return Cv(k, fill=fill)


# ------------------------------------------------------------------ jungle
JUNGLE_VP = (560, 820)
JUNGLE_GROUND = 1240


def _trunk(cv, x, top, bottom, w, col, seed, roots=True, vines=True):
    rnd = random.Random(seed)
    pts_l = [(x - w / 2 + rnd.uniform(-4, 4), y) for y in range(int(top), int(bottom) + 1, 60)]
    pts_r = [(x + w / 2 + rnd.uniform(-4, 4), y) for y in range(int(bottom), int(top) - 1, -60)]
    cv.poly(pts_l + pts_r, col + (255,), INK, 3)
    for _ in range(int((bottom - top) / 40)):                              # bark
        yy = rnd.uniform(top, bottom)
        xx = x + rnd.uniform(-w * 0.35, w * 0.35)
        cv.line([(xx, yy), (xx + rnd.uniform(-4, 4), yy + rnd.uniform(20, 50))], mul(col, 0.72) + (255,), 3)
    if roots:
        for sgn in (-1, 1):
            cv.poly([(x + sgn * w * 0.3, bottom - 40), (x + sgn * w * 1.1, bottom + 6), (x + sgn * w * 0.4, bottom + 4)],
                    col + (255,), INK, 2)
    if vines:
        for _ in range(3):
            vx = x + rnd.uniform(-w * 0.4, w * 0.4)
            vy = top + rnd.uniform(0, 200)
            pts = [(vx + 10 * math.sin(i * 0.8), vy + i * 40) for i in range(rnd.randint(6, 12))]
            cv.line(pts, (70, 120, 50, 255), 4)
            for (px, py) in pts[1::2]:
                cv.ell(px + 8, py, 10, 6, (90, 150, 60, 255))


def _canopy(cv, n, y0, y1, size, cols, seed):
    _leaves(cv, n, -80, LW + 80, y0, y1, size, cols, seed)


def _jungle_far(k):
    cv = _blank(k)
    cv.im = vgrad(k, [(0, (226, 236, 196)), (600, (190, 214, 170)), (1100, (150, 184, 140)), (LH, (110, 150, 100))])
    cv.d = ImageDraw.Draw(cv.im)
    rnd = random.Random(31)
    for _ in range(18):                                                    # pale far trunks in the mist
        x = rnd.uniform(-20, LW + 20)
        w = rnd.uniform(18, 40)
        cv.rect(x, 0, x + w, 1300, mix((150, 170, 140), (190, 206, 176), rnd.random()) + (255,))
    _canopy(cv, 60, -40, 380, 70, ((150, 180, 130), (186, 206, 160)), 32)
    cv.rect(0, 1000, LW, LH, (120, 156, 104, 255))
    cv.rect(0, 860, LW, 1060, (220, 232, 210, 120))                       # mist
    cv.blur(4.0)
    return cv


def _jungle_mid(k):
    cv = _blank(k)
    rnd = random.Random(41)
    for x in (120, 330, 560, 770, 930):
        x += rnd.uniform(-30, 30)
        _trunk(cv, x, -40, 1140, rnd.uniform(40, 64), mix((96, 78, 60), (120, 100, 76), rnd.random()), int(x))
    _canopy(cv, 70, -60, 420, 80, ((44, 104, 52), (90, 150, 70)), 42)
    for x in range(-40, LW + 60, 110):                                     # bushes along the ground
        _leaves(cv, 10, x, x + 160, 1060, 1160, 46, ((40, 98, 46), (84, 140, 62)), int(x) + 3)
    cv.blur(1.2)
    return cv


def _jungle_near(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(255, 246, 200, 0))
    vp, G = JUNGLE_VP, JUNGLE_GROUND
    # the ground: dark grass, a path of earth into the jungle
    fill_tex(cv, [(0, G), (LW, G), (LW, LH), (0, LH)], [(G, (78, 116, 54)), (LH, (54, 86, 40))], seed=43, cell=30,
             lo=0.9, hi=1.08)
    path = [(vp[0] - 30, G), (vp[0] + 30, G), (760, LH), (300, LH)]
    fill_tex(cv, path, [(G, (170, 140, 96)), (LH, (140, 110, 74))], seed=44, cell=26, lo=0.9, hi=1.08)
    rnd = random.Random(45)
    for _ in range(220):                                                   # grass blades
        x, y = rnd.uniform(0, LW), rnd.uniform(G, LH)
        u = (y - G) / float(LH - G)                                        # not on the path
        if (vp[0] - 30) + (300 - (vp[0] - 30)) * u < x < (vp[0] + 30) + (760 - (vp[0] + 30)) * u:
            continue
        h = 14 + 30 * (y - G) / (LH - G)
        cv.line([(x, y), (x + rnd.uniform(-6, 6), y - h)], mix((60, 120, 50), (120, 170, 70), rnd.random()) + (255,), 2)
    # big trunks framing the shot, roots in the ground
    _trunk(cv, 30, -40, G + 40, 150, (104, 80, 58), 46)
    _trunk(cv, 1040, -40, G + 30, 130, (96, 74, 54), 47)
    _canopy(cv, 40, -80, 260, 90, ((36, 92, 44), (76, 132, 58)), 48)
    # ferns, rocks, a fallen log, mushrooms, flowers along the back
    for (fx, fy, sz) in ((200, G + 10, 70), (880, G + 6, 80), (430, G - 4, 50), (680, G - 2, 54)):
        for i in range(9):
            a = math.pi * (0.1 + 0.8 * i / 8.0)
            tip = (fx + math.cos(a) * sz * 1.6, fy - math.sin(a) * sz)
            cv.line([(fx, fy), tip], (50, 118, 52, 255), 5)
            for j in range(1, 6):
                px, py = fx + (tip[0] - fx) * j / 6.0, fy + (tip[1] - fy) * j / 6.0
                cv.ell(px, py, 9, 5, (70, 140, 60, 255))
    cv.ell(800, G + 40, 70, 36, (130, 130, 124, 255), INK, 3)             # rocks
    cv.ell(860, G + 54, 44, 24, (150, 150, 142, 255), INK, 3)
    cv.poly([(560, G + 20), (720, G + 6), (730, G + 44), (566, G + 58)], (120, 90, 60, 255), INK, 3)   # a fallen log
    cv.ell(726, G + 25, 12, 20, (160, 126, 86, 255), INK, 2)
    for (mx, my) in ((600, G + 56), (624, G + 62), (330, G + 30)):
        cv.rect(mx - 3, my - 16, mx + 3, my, (240, 230, 210, 255))
        cv.ell(mx, my - 16, 12, 7, (200, 60, 50, 255), INK, 1)
        cv.ell(mx - 3, my - 18, 2, 2, (255, 255, 255, 255))
    for (fx, fy, c) in ((150, G + 70, (250, 220, 80)), (950, G + 80, (240, 120, 160)), (480, G + 40, (255, 255, 255))):
        for i in range(5):
            a = i * 2 * math.pi / 5
            cv.ell(fx + 8 * math.cos(a), fy + 8 * math.sin(a), 6, 6, c + (255,))
        cv.ell(fx, fy, 4, 4, (240, 160, 40, 255))
    # sun rays through the leaves and spots on the ground
    for (x, w) in ((640, 90), (780, 60), (900, 110), (480, 50)):
        light.poly([(x, 0), (x + w, 0), (x + w - 420, G + 80), (x - 420, G + 80)], (255, 244, 190, 34))
    for (x, y, r) in ((300, G + 120, 90), (520, G + 260, 120), (240, G + 400, 110), (640, G + 520, 140)):
        light.ell(x, y, r, r * 0.3, (255, 240, 180, 60))
    cv.blur(0.3)
    return cv, light


def _jungle_front(k):
    cv = _blank(k)
    for (fx, fy, sz, sgn) in ((40, LH + 40, 260, 1), (LW - 40, LH + 40, 240, -1)):
        for i in range(7):
            a = math.pi * (0.5 - sgn * (0.05 + 0.4 * i / 6.0))
            tip = (fx + math.cos(a) * sz * 1.4, fy - math.sin(a) * sz * 1.4)
            cv.line([(fx, fy), tip], (40, 100, 40, 255), 10)
            for j in range(1, 8):
                px, py = fx + (tip[0] - fx) * j / 8.0, fy + (tip[1] - fy) * j / 8.0
                cv.ell(px, py, 26, 12, (60, 130, 54, 255))
    cv.blur(9)
    return cv


def _falling_leaves(k, n=7, seed=51):
    rnd = random.Random(seed)
    leaves = [(rnd.uniform(100, LW - 100), rnd.uniform(0, 1), rnd.uniform(0.07, 0.12), rnd.uniform(0, 6.28)) for _ in range(n)]

    def fn(_im, t):
        cv = _blank(k, fill=(120, 160, 60, 0))
        for (x0, ph, sp, rot) in leaves:
            u = (ph + t * sp) % 1.0
            y = -40 + u * 1300
            x = x0 + 60 * math.sin(t * 1.3 + rot)
            a = rot + t * 2.0
            cv.poly([(x + 14 * math.cos(a), y + 6 * math.sin(a)), (x - 3 * math.sin(a), y + 9 * math.cos(a)),
                     (x - 14 * math.cos(a), y - 6 * math.sin(a)), (x + 3 * math.sin(a), y - 9 * math.cos(a))],
                    (150, 170, 60, 220))
        return cv.im
    return fn


def jungle_25d(s, zmax=1.0):
    kn = s * max(1.0, zmax)
    kg = 0.32 * s
    far = _jungle_far(0.4 * s)
    mid = _jungle_mid(0.6 * s)
    near, light = _jungle_near(kn, kg)
    fg = _jungle_front(0.5 * s)
    empty = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    back = [
        Layer(far.im, 0.4 * s, 0.1, None, "far jungle"),
        Layer(mid.im, 0.6 * s, 0.45, None, "trees"),
        Layer(near.im, kn, 1.0, None, "jungle"),
        Layer(light.im, kg, 1.0, None, "sunlight", mode="screen"),
        Layer(empty, 0.3 * s, 1.0, motes(((420, 200), (1000, 1300), 300), 0.3 * s, n=60, seed=52), "dust", mode="screen"),
        Layer(empty, 0.5 * s, 0.8, _falling_leaves(0.5 * s), "leaves"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return Layered(back, front, light={"ambient": [238, 250, 226], "dir": 1, "vignette": 0.32},
                   horizon=JUNGLE_VP[1], ground=JUNGLE_GROUND)


# ------------------------------------------------------------------ haunted house (night)
HAUNT_GROUND = 1270
HOUSE = (300, 420, 800, HAUNT_GROUND)            # x0, roof peak y, x1, ground
LIT_WIN = (560, 720, 650, 830)


def _night_sky(k):
    cv = _blank(k)
    cv.im = vgrad(k, [(0, (16, 14, 40)), (700, (44, 30, 80)), (1200, (70, 50, 104)), (LH, (40, 30, 60))])
    cv.d = ImageDraw.Draw(cv.im)
    rnd = random.Random(61)
    for _ in range(80):
        x, y = rnd.uniform(0, LW), rnd.uniform(0, 900)
        r = rnd.uniform(1.2, 3)
        cv.ell(x, y, r, r, (255, 255, 240, int(rnd.uniform(120, 230))))
    cv.glow(800, 300, 300, (220, 220, 255), 70)
    cv.ell(800, 300, 120, 120, (244, 240, 210, 255))
    for (cx, cy, r) in ((770, 270, 18), (830, 330, 12), (800, 350, 9)):          # craters
        cv.ell(cx, cy, r, r, (226, 220, 190, 255))
    for (cx, cy, w) in ((300, 420, 260), (900, 560, 220)):                       # clouds over the moonlit sky
        for _ in range(6):
            cv.ell(cx + rnd.uniform(-w / 2, w / 2), cy + rnd.uniform(-16, 16), w * 0.3, w * 0.1, (110, 96, 150, 200))
    # hills and dead trees far away
    cv.poly([(0, 1080), (300, 1000), (620, 1060), (900, 990), (LW, 1040), (LW, LH), (0, LH)], (30, 24, 50, 255))
    for x in (90, 960):
        cv.line([(x, 1060), (x + 10, 860)], (24, 20, 40, 255), 10)
        for (dx, dy) in ((-60, -80), (50, -60), (-30, -140), (40, -130)):
            cv.line([(x + 8, 920 + dy * 0.2), (x + 8 + dx, 900 + dy)], (24, 20, 40, 255), 4)
    cv.blur(1.5)
    return cv


def _bats(k, n=5, seed=63):
    rnd = random.Random(seed)
    bats = [(rnd.uniform(0, 1), rnd.uniform(260, 700), rnd.uniform(0.05, 0.09), rnd.uniform(0, 6)) for _ in range(n)]

    def fn(_im, t):
        cv = _blank(k, fill=(20, 16, 30, 0))
        for (ph, y0, sp, wob) in bats:
            u = (ph + t * sp) % 1.0
            x = -80 + u * (LW + 160)
            y = y0 + 40 * math.sin(t * 2 + wob)
            flap = math.sin(t * 16 + wob)
            cv.poly([(x, y), (x - 34, y - 14 * flap - 6), (x - 18, y + 4), (x, y + 8), (x + 18, y + 4),
                     (x + 34, y - 14 * flap - 6)], (20, 16, 30, 255))
        return cv.im
    return fn


def _haunted(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(255, 210, 120, 0))
    x0, peak, x1, G = HOUSE
    wall = (64, 56, 74)
    # the old house: planks, a crooked roof, a chimney, broken shutters
    cv.rect(x0, 560, x1, G, wall + (255,), INK, 4)
    for y in range(580, G, 34):
        cv.line([(x0 + 4, y), (x1 - 4, y + (6 if (y // 34) % 3 == 0 else 0))], mul(wall, 0.8) + (255,), 2)
    cv.poly([(x0 - 50, 580), ((x0 + x1) / 2, peak), (x1 + 50, 580)], (38, 30, 46, 255), INK, 4)
    cv.rect(700, 430, 750, 520, (52, 44, 58, 255), INK, 3)                       # chimney
    cv.ell((x0 + x1) / 2, 500, 34, 34, (30, 26, 36, 255), INK, 3)                # attic window
    cv.line([((x0 + x1) / 2 - 30, 500), ((x0 + x1) / 2 + 30, 500)], INK, 3)
    for (wx0, wy0, wx1, wy1) in ((380, 720, 470, 830), LIT_WIN):
        lit = (wx0, wy0, wx1, wy1) == LIT_WIN
        cv.rect(wx0, wy0, wx1, wy1, ((250, 210, 110) if lit else (24, 22, 30)) + (255,), INK, 3)
        cv.line([((wx0 + wx1) / 2, wy0), ((wx0 + wx1) / 2, wy1)], INK, 3)
        cv.line([(wx0, (wy0 + wy1) / 2), (wx1, (wy0 + wy1) / 2)], INK, 3)
        cv.poly([(wx0 - 34, wy0 + 6), (wx0, wy0), (wx0, wy1), (wx0 - 30, wy1 + 20)], mul(wall, 0.7) + (255,), INK, 2)  # shutter
    cv.poly([(LIT_WIN[2], LIT_WIN[1]), (LIT_WIN[2] + 30, LIT_WIN[1] - 14), (LIT_WIN[2] + 22, LIT_WIN[3] - 10),
             (LIT_WIN[2], LIT_WIN[3])], mul(wall, 0.7) + (255,), INK, 2)            # a broken shutter, hanging
    # the porch and the door, a little open
    cv.rect(470, 980, 630, G, (40, 30, 30, 255), INK, 4)
    cv.poly([(470, 980), (520, 990), (520, G - 10), (470, G)], (90, 60, 44, 255), INK, 3)
    cv.ell(510, 1130, 5, 5, (220, 190, 90, 255))
    cv.rect(430, 950, 670, 980, (50, 40, 46, 255), INK, 3)
    cv.rect(440, G - 6, 660, G + 12, (70, 60, 66, 255), INK, 2)                # steps
    cv.rect(420, G + 12, 680, G + 30, (62, 54, 60, 255), INK, 2)
    # cobwebs in the corners of the porch
    for (cx, cy, sgn) in ((430, 980, 1), (670, 980, -1)):
        for r in (20, 40, 60):
            cv.line([(cx + sgn * r, cy), (cx + sgn * r * 0.7, cy + r * 0.7), (cx, cy + r)], (200, 200, 220, 120), 1)
        cv.line([(cx, cy), (cx + sgn * 70, cy + 70)], (200, 200, 220, 120), 1)
    # ivy up the wall
    rnd = random.Random(64)
    for _ in range(40):
        cv.ell(x0 + rnd.uniform(0, 90), rnd.uniform(620, G), 10, 7, (40, 80, 50, 255))
    # the ground, a path to the door, a broken fence, a lantern on a post
    fill_tex(cv, [(0, G), (LW, G), (LW, LH), (0, LH)], [(G, (44, 40, 58)), (LH, (28, 26, 38))], seed=65, cell=30,
             lo=0.88, hi=1.1)
    cv.poly([(500, G), (600, G), (760, LH), (280, LH)], (70, 62, 78, 255))
    for x in range(-20, LW, 70):
        if 440 < x < 660 or rnd.random() < 0.18:
            continue
        lean = rnd.uniform(-10, 10)
        cv.poly([(x, G + 30), (x + 30, G + 30), (x + 30 + lean, G - 90), (x + 15 + lean, G - 110), (x + lean, G - 90)],
                (90, 80, 84, 255), INK, 2)
    cv.line([(-20, G - 50), (430, G - 46)], (90, 80, 84, 255), 8)
    cv.line([(670, G - 46), (LW + 20, G - 52)], (90, 80, 84, 255), 8)
    cv.rect(890, 900, 904, G + 20, (40, 34, 30, 255), INK, 2)                    # lantern post
    cv.rect(870, 860, 924, 920, (40, 34, 30, 255), INK, 2)
    cv.rect(878, 868, 916, 912, (255, 210, 110, 255))
    for (dx, dy) in ((0, 0), (30, 12), (-26, 18)):                               # dry leaves
        for _ in range(8):
            cv.ell(rnd.uniform(0, LW), rnd.uniform(G + 30, LH), 8, 4, (110, 70, 40, 255))
    _shadow(cv, 550, G + 6, 300, 14, a=120)
    # light: the lantern, the moon's rim light on the roof
    light.glow(897, 890, 220, (255, 200, 110), 90)
    light.poly([(x1 + 50, 580), ((x0 + x1) / 2, peak), ((x0 + x1) / 2 + 20, peak + 10), (x1 + 50, 596)], (180, 190, 255, 90))
    cv.blur(0.3)
    return cv, light


def _flicker_window(k):
    x0, y0, x1, y1 = LIT_WIN

    def fn(_im, t):
        b = 0.55 + 0.25 * math.sin(t * 7.3) + 0.2 * math.sin(t * 13.1 + 1.0)
        if (t % 4.0) > 3.6:                                                     # now and then it nearly goes out
            b *= 0.25
        cv = _blank(k, fill=(255, 200, 110, 0))
        cv.glow((x0 + x1) / 2, (y0 + y1) / 2, 200, (255, 200, 110), int(90 * max(0.1, b)))
        cv.poly([(x0, y1 + 300), (x1, y1 + 300), (x1 + 160, y1 + 700), (x0 - 160, y1 + 700)], (255, 200, 110, int(16 * b)))
        return cv.im
    return fn


def _fog(k, y0, y1, alpha, speed, seed):
    rnd = random.Random(seed)
    puffs = [(rnd.uniform(0, LW * 2), rnd.uniform(y0, y1), rnd.uniform(160, 300)) for _ in range(18)]

    def fn(_im, t):
        cv = _blank(k, fill=(190, 190, 220, 0))
        for (x, y, r) in puffs:
            xx = (x + t * speed) % (LW * 2) - LW * 0.5
            cv.ell(xx, y, r, r * 0.35, (200, 200, 228, alpha))
        cv.blur(14)
        return cv.im
    return fn


def haunted_25d(s, zmax=1.0):
    kn = s * max(1.0, zmax)
    kg = 0.32 * s
    sky = _night_sky(0.4 * s)
    house, light = _haunted(kn, kg)
    empty = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    back = [
        Layer(sky.im, 0.4 * s, 0.1, None, "night sky"),
        Layer(empty, 0.4 * s, 0.3, _bats(0.4 * s), "bats"),
        Layer(house.im, kn, 1.0, None, "haunted house"),
        Layer(light.im, kg, 1.0, None, "lantern", mode="screen"),
        Layer(empty, 0.4 * s, 1.0, _flicker_window(0.4 * s), "window light", mode="screen"),
        Layer(empty, 0.25 * s, 1.0, _fog(0.25 * s, HAUNT_GROUND - 60, HAUNT_GROUND + 200, 60, 22, 66), "fog"),
    ]
    front = [Layer(empty, 0.25 * s, 1.3, _fog(0.25 * s, 1700, 2000, 70, 34, 67), "fog near")]
    return Layered(back, front, light={"ambient": [196, 196, 240], "dir": 1, "vignette": 0.42},
                   horizon=900, ground=HAUNT_GROUND)


# ------------------------------------------------------------------ bedroom
BED_VP = (540, 820)
BED_FLOOR = 1290
BED_WIN = (690, 420, 960, 820)


def _bedroom(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(255, 236, 190, 0))
    vp, F = BED_VP, BED_FLOOR
    fill_tex(cv, [(0, 0), (LW, 0), (LW, F), (0, F)], [(0, (214, 222, 240)), (700, (222, 228, 244)), (F, (204, 212, 232))],
             seed=71, cell=60, lo=0.96, hi=1.035)
    cv.rect(0, 0, LW, 60, (244, 244, 248, 255))
    cv.rect(0, 60, LW, 72, (190, 196, 214, 255))
    cv.rect(0, F - 28, LW, F, (170, 130, 96, 255), INK, 2)
    # window with curtains and its sunlight
    x0, y0, x1, y1 = BED_WIN
    _window(cv, light, ((560, 1380), (860, 1380), (980, 1650), (560, 1650)), x0, y0, x1, y1, bars_v=4)
    cv.rect(x0 - 70, y0 - 44, x1 + 70, y0 - 32, (150, 110, 70, 255), INK, 2)
    _curtain(cv, x0 - 54, x0 + 26, y0 - 34, y1 + 70, (90, 120, 190), -1)
    _curtain(cv, x1 - 26, x1 + 54, y0 - 34, y1 + 70, (90, 120, 190), 1)
    # shelf with books and a trophy, posters, a clock
    cv.rect(80, 520, 420, 540, (150, 106, 70, 255), INK, 3)
    rnd = random.Random(72)
    bx = 96
    for _ in range(9):
        w = rnd.uniform(18, 30)
        h = rnd.uniform(60, 90)
        cv.rect(bx, 520 - h, bx + w, 520, mix((200, 60, 60), (60, 120, 200), rnd.random()) + (255,), INK, 2)
        bx += w + 2
    cv.poly([(360, 520), (400, 520), (392, 470), (368, 470)], (230, 190, 60, 255), INK, 2)
    cv.ell(380, 458, 20, 16, (240, 200, 70, 255), INK, 2)
    for (px0, py0, px1, py1, c) in ((90, 600, 250, 800, (240, 120, 90)), (280, 620, 420, 780, (90, 170, 150))):
        cv.rect(px0, py0, px1, py1, c + (255,), INK, 3)
        cv.ell((px0 + px1) / 2, (py0 + py1) / 2 - 10, (px1 - px0) * 0.25, (px1 - px0) * 0.25, mul(c, 1.25) + (255,))
        cv.poly([(px0 + 10, py1 - 10), ((px0 + px1) / 2, py0 + 90), (px1 - 10, py1 - 10)], mul(c, 0.7) + (255,))
    _clock(cv, 250, 330, 40, rim=(60, 90, 160))
    # wardrobe on the left wall's side
    _box(cv, vp, 40, 300, 860, F, (150, 104, 68), side=0.06)
    cv.line([(170, 880), (170, F - 10)], INK, 3)
    for hx in (150, 190):
        cv.rect(hx - 4, 1040, hx + 4, 1100, (220, 190, 110, 255), INK, 1)
    # the bed against the wall: headboard, mattress, pillows, a quilt; a bedside table with a lamp
    cv.rect(380, 900, 820, 1110, (130, 86, 60, 255), INK, 4)                       # headboard
    cv.rect(400, 920, 800, 1090, (150, 104, 74, 255), INK, 2)
    cv.poly([(360, 1080), (840, 1080), (900, 1200), (300, 1200)], (240, 240, 246, 255), INK, 3)       # mattress top
    cv.poly([(300, 1200), (900, 1200), (900, 1260), (300, 1260)], (226, 226, 234, 255), INK, 3)
    for (px, c) in ((470, (250, 246, 236)), (720, (250, 246, 236))):
        cv.ell(px, 1086, 90, 34, c + (255,), INK, 3)
    cv.poly([(330, 1130), (870, 1130), (900, 1200), (300, 1200)], (220, 90, 110, 255), INK, 3)        # quilt
    cv.poly([(300, 1200), (900, 1200), (900, 1262), (300, 1262)], (196, 70, 92, 255), INK, 3)
    for x in range(330, 880, 60):
        cv.line([(x, 1134), (x - 10, 1260)], (240, 140, 150, 255), 2)
    for lx in (306, 888):
        cv.rect(lx, 1262, lx + 12, F + 4, (90, 60, 40, 255))
    _box(cv, vp, 860, 1000, 1110, F, (140, 98, 66), side=0.06)                      # bedside table
    cv.rect(900, 1030, 960, 1110, (230, 220, 200, 255), INK, 2)                     # lamp
    cv.poly([(880, 1030), (980, 1030), (960, 970), (900, 970)], (250, 220, 150, 255), INK, 2)
    light.glow(930, 1000, 200, (255, 220, 150), 70)
    _shadow(cv, 600, F + 2, 330, 16)
    # floor: wooden boards + a round rug
    fill_tex(cv, [(0, F), (LW, F), (LW, LH), (0, LH)], [(F, (184, 140, 100)), (LH, (160, 118, 82))], seed=73, cell=40,
             lo=0.94, hi=1.05)
    for x in range(-1600, 2700, 100):
        cv.line([(x, F), (vp[0] + (x - vp[0]) * (LH - vp[1]) / float(F - vp[1]), LH)], (140, 100, 70, 255), 2)
    cv.ell(560, 1500, 330, 90, (110, 150, 200, 255), (240, 240, 250, 255), 4)
    cv.ell(560, 1500, 200, 52, (150, 186, 226, 255))
    cv.blur(0.35)
    return cv, light


def _bedroom_front(k):
    cv = _blank(k)
    cv.poly([(780, 1830), (LW + 40, 1790), (LW + 40, LH + 40), (740, LH + 40)], (150, 104, 74, 255))   # a study table corner
    cv.rect(860, 1700, 930, 1790, (60, 100, 170, 255))                                          # a school bag
    _leaves(cv, 12, -60, 220, 1720, 1990, 54, ((60, 130, 50), (150, 190, 80)), 74)
    cv.blur(8)
    return cv


def bedroom_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    outside = _room_outside(0.5 * s)
    room, light = _bedroom(kr, kg)
    fg = _bedroom_front(0.5 * s)
    empty = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    back = [
        Layer(outside.im, 0.5 * s, 0.12, None, "outside"),
        Layer(room.im, kr, 1.0, None, "bedroom"),
        Layer(light.im, kg, 1.0, None, "sunlight", mode="screen"),
        Layer(empty, 0.3 * s, 1.0, motes(((620, 700), (960, 1500), 200), 0.3 * s), "dust", mode="screen"),
        Layer(empty, 0.7 * s, 1.0, fan(540, 290, 0.7 * s, R=220, top=72), "fan"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return Layered(back, front, light={"ambient": [255, 248, 240], "dir": 1, "vignette": 0.24},
                   horizon=BED_VP[1], ground=BED_FLOOR)

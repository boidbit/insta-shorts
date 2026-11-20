"""2.5D sets for the village pack (studio/places_gaon). Each one stands on its place's own drawing split into depth
layers (autoset), with its own life on top and something blurred in front of the lens.

khet_25d          the fields: birds, the tubewell's water glinting down the channel, the mustard nodding in the
                  wind; blurred wheat ears in front.
chaupal_25d       the chaupal: the hookah's smoke curling up, banyan leaves drifting down, birds; a blurred khaat
                  corner in front.
handpump_25d      the hand pump: drops falling from the spout, rings on the puddle, a crow; a blurred matka in front.
kachcha_ghar_25d  inside the mud house: the chulha's fire flickering with smoke rising, the lantern's warm glow,
                  dust in the window's light; a blurred brass lota in front.
gaon_school_25d   the village school: the bell swinging a little, leaves falling, birds; a blurred slate and chalk.
"""
import math
import random

from .scenery import Layer, birds, motes
from .scenery_2026 import EMPTY, INK, _anim, _blur_front, _set, _steam
from ..util import LH, LW


def _leaves(cv, t, region, n=7, seed=3, color=(96, 150, 74, 230)):
    (x0, y0), (x1, y1) = region
    rnd = random.Random(seed)
    for i in range(n):
        sx, sp, ph = rnd.uniform(x0, x1), rnd.uniform(0.08, 0.16), rnd.uniform(0, 1)
        u = (t * sp + ph) % 1.0
        x = sx + 40 * math.sin(t * 1.3 + i)
        y = y0 + (y1 - y0) * u
        a = math.radians(40 * math.sin(t * 2 + i))
        pts = [(x + dx * math.cos(a) - dy * math.sin(a), y + dx * math.sin(a) + dy * math.cos(a))
               for dx, dy in ((-12, 0), (0, -7), (12, 0), (0, 7))]
        cv.poly(pts, color)


def khet_25d(s, zmax=1.0):
    k = 0.5 * s

    def water(cv, t):                                   # glints running down the channel
        for i in range(9):
            x = (t * 120 + i * 60) % 520
            cv.line([(x, 1200 + (i % 3) * 10), (x + 26, 1203 + (i % 3) * 10)], (240, 250, 255, 220), 4)
        for i in range(4):                              # the gush from the pipe
            y = 1085 + ((t * 300 + i * 40) % 150)
            cv.ell(380 + 10 * math.sin(t * 9 + i), y, 10, 6, (220, 240, 255, 200))

    def mustard(cv, t):                                 # a few flowers nodding in the wind
        rnd = random.Random(21)
        for x in range(540, LW, 52):
            h = rnd.randint(150, 230)
            sw = 8 * math.sin(t * 1.6 + x * 0.02)
            cv.ell(x + sw, 1240 - h, 16, 16, (250, 216, 70, 255), INK, 2)
    life = [Layer(EMPTY, k, 0.3, birds(k, 5, 61, 260, 640), "birds"), _anim(k, water, "water"),
            _anim(k, mustard, "mustard")]

    def front(cv):
        rnd = random.Random(7)
        for x in list(range(-20, 260, 34)) + list(range(840, LW + 40, 34)):     # wheat ears right at the lens
            top = 1620 + rnd.randint(0, 120)
            cv.line([(x, LH + 20), (x + rnd.randint(-20, 20), top)], (150, 180, 80, 255), 9)
            cv.ell(x, top - 20, 12, 34, (200, 190, 90, 255))
    return _set("khet", s, zmax, life, _blur_front(k, front), {"ambient": [255, 250, 230], "dir": 1,
                "vignette": 0.18}, 820, 1240)


def chaupal_25d(s, zmax=1.0):
    k = 0.5 * s

    def smoke(cv, t):
        _steam(cv, 330, 930, t, 3, 170, 80, seed=2)

    def leaves(cv, t):
        _leaves(cv, t, ((200, 600), (880, 1240)), 8, 4)
    life = [Layer(EMPTY, k, 0.3, birds(k, 4, 71, 200, 520), "birds"), _anim(k, smoke, "smoke", "screen"),
            _anim(k, leaves, "leaves")]

    def front(cv):
        cv.rect(-40, 1720, 360, 1790, (150, 100, 60, 255), (110, 70, 40, 255), 6)   # a khaat's corner
        cv.line([(300, 1790), (300, LH + 20)], (120, 80, 50, 255), 22)
        for x in range(-30, 360, 30):
            cv.line([(x, 1724), (x + 18, 1786)], (230, 210, 170, 255), 4)
    return _set("chaupal", s, zmax, life, _blur_front(k, front), {"ambient": [255, 246, 226], "dir": -1,
                "vignette": 0.22}, 820, 1240)


def handpump_25d(s, zmax=1.0):
    k = 0.5 * s

    def drops(cv, t):                                   # water dripping from the spout, rings on the puddle
        for i in range(3):
            u = (t * 1.4 + i / 3.0) % 1.0
            cv.ell(446, 1040 + 170 * u * u, 6, 9, (200, 230, 255, 230))
        for i in range(2):
            u = (t * 0.7 + i / 2.0) % 1.0
            r = 20 + 90 * u
            cv.ell(470, 1228, r, r * 0.2, None, (230, 245, 255, int(200 * (1 - u))), 3)
    life = [Layer(EMPTY, k, 0.3, birds(k, 3, 81, 240, 520), "birds"), _anim(k, drops, "drops")]

    def front(cv):
        cv.ell(940, 1820, 150, 170, (200, 110, 60, 255), (150, 80, 40, 255), 6)      # a matka at the lens
        cv.rect(880, 1640, 1000, 1680, (170, 90, 50, 255))
    return _set("handpump", s, zmax, life, _blur_front(k, front), {"ambient": [255, 248, 230], "dir": 1,
                "vignette": 0.2}, 820, 1240)


def kachcha_ghar_25d(s, zmax=1.0):
    k = 0.5 * s

    def fire(cv, t):                                    # the chulha's flames and their glow
        f = 0.75 + 0.25 * math.sin(t * 11) * math.sin(t * 4.3)
        cv.glow(860, 1225, 170, (255, 150, 60), int(110 * f))
        for i in range(3):
            h = 40 + 18 * math.sin(t * 9 + i * 2)
            x = 832 + i * 28
            cv.poly([(x - 16, 1255), (x, 1255 - h), (x + 16, 1255)], (255, 190 - i * 30, 60, 230))

    def smoke(cv, t):
        _steam(cv, 860, 1100, t, 4, 420, 90, seed=5)

    def lamp(cv, t):                                    # the lantern and the diya breathe
        f = 0.85 + 0.15 * math.sin(t * 5.1)
        cv.glow(330, 350, 150, (255, 210, 120), int(80 * f))
        cv.glow(200, 505, 70, (255, 200, 110), int(90 * f))
    life = [_anim(k, fire, "fire", "screen"), _anim(k, smoke, "smoke", "screen"), _anim(k, lamp, "lamp", "screen"),
            Layer(EMPTY, 0.3 * s, 1.0, motes(((460, 300), (900, 1000), 260), 0.3 * s, 26, 44), "dust", mode="screen")]

    def front(cv):
        cv.ell(130, 1840, 110, 120, (210, 170, 60, 255), (160, 120, 40, 255), 6)    # a brass lota
        cv.rect(80, 1700, 180, 1740, (210, 170, 60, 255))
    return _set("kachcha_ghar", s, zmax, life, _blur_front(k, front), {"ambient": [255, 226, 186], "dir": 1,
                "vignette": 0.36}, 820, 1270)


def gaon_school_25d(s, zmax=1.0):
    k = 0.5 * s

    def bell(cv, t):                                    # the brass bell swinging a little on its branch
        a = math.radians(6 * math.sin(t * 1.8))
        cx, cy = 300, 600

        def R(dx, dy):
            return (cx + dx * math.cos(a) - dy * math.sin(a), cy + dx * math.sin(a) + dy * math.cos(a))
        cv.line([R(0, 0), R(0, 80)], INK, 3)
        cv.poly([R(-22, 80), R(22, 80), R(34, 140), R(-34, 140)], (220, 180, 70, 255), INK, 3)

    def leaves(cv, t):
        _leaves(cv, t, ((0, 500), (400, 1240)), 6, 9)
    life = [Layer(EMPTY, k, 0.3, birds(k, 4, 91, 220, 480), "birds"), _anim(k, bell, "bell"),
            _anim(k, leaves, "leaves")]

    def front(cv):
        cv.rect(760, 1660, 1100, 1900, (60, 66, 64, 255), (140, 100, 60, 255), 14)  # a slate (patti)
        cv.rect(-30, 1820, 160, 1850, (245, 245, 240, 255))                        # a chalk
    return _set("gaon_school", s, zmax, life, _blur_front(k, front), {"ambient": [255, 250, 232], "dir": -1,
                "vignette": 0.2}, 820, 1240)


SETS = {"khet_25d": khet_25d, "chaupal_25d": chaupal_25d, "handpump_25d": handpump_25d,
        "kachcha_ghar_25d": kachcha_ghar_25d, "gaon_school_25d": gaon_school_25d}

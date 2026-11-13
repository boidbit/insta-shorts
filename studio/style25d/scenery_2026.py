"""2.5D sets for the Nov 2026 places. Each one stands on its place's own drawing (studio/places_2026), split into
depth layers the way autoset does it (sky, far buildings, the view through a window, the room), and then gets
its own hand-made life on top: things that move, its own light, and something blurred right in front of the lens.

ghar_darwaza_25d   the landing: the toran's leaves swaying, the bell's light, the tube light on the stairs that
                   flickers, a fly round the bulb; a blurred shoe rack and chappals in front.
lift_25d           the lift: the floor number counting down, the light ticking, the mirror's shine sliding; the
                   doors' steel edge blurred at the sides.
park_25d           the park: birds over the flats, leaves falling, the swing going, the lamp's soft glow; tall blurred
                   grass and flowers in front.
buffet_25d         the shaadi buffet: steam off every dish, the fairy lights and the garland bulbs breathing, a
                   marigold petal or two falling; a blurred stack of plates in front.
restaurant_25d     the restaurant: the hanging lamps' warm pools swaying a little, steam off a plate, the street's
                   lights sliding past the window; a blurred glass and menu card in front.
atm_25d            the ATM cabin: the screen's cursor blinking, the CCTV dot, the tube light's cold hum (a flicker);
                   the glass door's frame blurred at the side.
petrol_pump_25d    the pump: the meters rolling, cars passing on the road behind, the canopy lights; the nozzle on
                   its hook blurred in front.
signal_25d         the chowk: the countdown running, the red light's glow pulsing, traffic crossing behind; a bike's
                   mirror and handle blurred in front.
interview_room_25d the interview: the wall clock ticking, the whiteboard's shine, the AC's breeze on the plant; a
                   blurred water bottle and file in front.
call_center_25d    the call center at 2 a.m.: the monitors flickering, the target board's numbers blinking, the
                   ceiling lights; a blurred headset in front.
startup_office_25d the startup: the HUSTLE neon flickering, the laptops' glow, a sticky note fluttering, motes in
                   the light; a blurred coffee mug in front.
"""
import math
import random

from PIL import Image

from .autoset import build_auto
from .scenery import Cv, Layer, Layered, birds, motes
from ..util import LH, LW

INK = (40, 34, 30, 255)
EMPTY = Image.new("RGBA", (8, 8), (0, 0, 0, 0))


def _blur_front(k, draw, r=8):
    cv = Cv(k)
    draw(cv)
    cv.blur(r)
    return cv.im


def _set(place, s, zmax, life, front, light, horizon, ground):
    """The place's layers (autoset) + its own animated layers + its own blurred foreground + its light."""
    base = build_auto(place, s, zmax)
    back = list(base.back) if base else []
    back += life
    return Layered(back, [Layer(front, 0.5 * s, 1.3, None, "foreground")] if front is not None else [],
                   light=light, horizon=horizon, ground=ground)


def _anim(k, draw, name, mode="normal", d=1.0):
    """A layer redrawn every frame: draw(cv, t)."""
    def fn(_im, t):
        cv = Cv(k)
        draw(cv, t)
        return cv.im
    return Layer(EMPTY, k, d, fn, name, mode=mode)


def _steam(cv, x, y, t, n=3, h=150, a=70, seed=0):
    for i in range(n):
        u = ((t * 0.35 + i / float(n) + seed * 0.13) % 1.0)
        yy = y - u * h
        xx = x + math.sin(t * 1.7 + i * 2 + seed) * 14 * u
        cv.ell(xx, yy, 18 + 26 * u, 14 + 20 * u, (255, 255, 255, int(a * (1 - u))))


def _traffic(cv, t, y, h, speed=180, seed=1, span=(-200, LW + 200)):
    """Little cars passing far behind (body, window, wheels), both ways."""
    rnd = random.Random(seed)
    cars = [(rnd.random(), rnd.choice([(200, 50, 50), (240, 240, 236), (60, 100, 190), (230, 190, 60), (60, 60, 66)]),
             rnd.choice((1, -1)), rnd.uniform(0.8, 1.3)) for _ in range(4)]
    w0, w1 = span
    for (u, col, dirn, sp) in cars:
        x = w0 + ((u + dirn * t * speed * sp / (w1 - w0)) % 1.0) * (w1 - w0)
        L = h * 2.2
        cv.rect(x - L / 2, y - h * 0.55, x + L / 2, y, col + (255,), INK, 2)
        cv.rect(x - L * 0.25, y - h, x + L * 0.25, y - h * 0.5, col + (255,), INK, 2)
        cv.rect(x - L * 0.2, y - h * 0.92, x + L * 0.2, y - h * 0.58, (170, 210, 236, 255))
        for wx in (x - L * 0.3, x + L * 0.3):
            cv.ell(wx, y, h * 0.2, h * 0.2, (30, 30, 34, 255))


# ------------------------------------------------------------------ home
def ghar_darwaza_25d(s, zmax=1.0):
    k = 0.5 * s

    def toran(cv, t):                                  # the mango leaves sway, the marigolds bob
        for i in range(9):
            x = 170 + i * 50
            sw = 5 * math.sin(t * 1.6 + i * 0.7)
            cv.poly([(x, 300), (x + 20, 300), (x + 10 + sw, 352)], (80, 150, 70, 255), INK, 1.5)
            cv.ell(x + 25 + sw * 0.5, 307, 10, 10, (246, 150, 40, 255), INK, 1.5)

    def stair_light(cv, t):                             # the tube light over the stairs flickers now and then
        on = not (2.1 < (t % 5.0) < 2.25 or 2.4 < (t % 5.0) < 2.5)
        cv.rect(880, 560, 1060, 580, (250, 252, 240, 255) if on else (190, 196, 196, 255), INK, 2)
        if on:
            cv.glow(970, 570, 150, (240, 250, 255), 60)

    def bell(cv, t):                                    # the bell's red light breathes
        a = int(120 + 100 * (0.5 + 0.5 * math.sin(t * 3)))
        cv.glow(655, 710, 34, (255, 80, 60), a)

    def fly(cv, t):
        x = 970 + 60 * math.sin(t * 2.3) + 20 * math.sin(t * 7.1)
        y = 620 + 30 * math.cos(t * 3.1)
        cv.ell(x, y, 4, 3, (30, 30, 34, 255))

    life = [_anim(k, toran, "toran"), _anim(k, stair_light, "tube"), _anim(k, bell, "bell", "screen"),
            _anim(k, fly, "fly")]

    def front(cv):
        cv.rect(-40, 1640, 260, LH + 40, (130, 90, 56, 255))
        for x, c in ((10, (200, 70, 60)), (110, (60, 90, 170)), (190, (230, 190, 60))):
            cv.ell(x + 30, 1700, 50, 22, c + (255,))
    return _set("ghar_darwaza", s, zmax, life, _blur_front(k, front), {"ambient": [255, 246, 232], "dir": 1,
                "vignette": 0.24}, 820, 1280)


def lift_25d(s, zmax=1.0):
    k = 0.5 * s

    def display(cv, t):                                 # the floor number counts down 7, 6, 5...
        n = max(0, 7 - int(t / 1.6))
        cv.rect(860, 440, 970, 520, (20, 24, 28, 255), INK, 2)
        # seven-segment digit
        seg = {0: "abcdef", 1: "bc", 2: "abged", 3: "abgcd", 4: "fgbc", 5: "afgcd", 6: "afgedc", 7: "abc"}[n]
        x0, y0, w, h = 897, 450, 36, 58
        pts = {"a": [(x0, y0), (x0 + w, y0)], "b": [(x0 + w, y0), (x0 + w, y0 + h / 2)],
               "c": [(x0 + w, y0 + h / 2), (x0 + w, y0 + h)], "d": [(x0, y0 + h), (x0 + w, y0 + h)],
               "e": [(x0, y0 + h / 2), (x0, y0 + h)], "f": [(x0, y0), (x0, y0 + h / 2)],
               "g": [(x0, y0 + h / 2), (x0 + w, y0 + h / 2)]}
        for sgm in seg:
            cv.line(pts[sgm], (250, 80, 60, 255), 6)
        cv.poly([(940, 512), (950, 496), (960, 512)], (250, 80, 60, 255))     # the down arrow

    def shine(cv, t):                                   # a soft shine sliding over the mirror
        x = 330 + ((t * 120) % 700)
        if x < 760:
            cv.poly([(x, 270), (x + 40, 270), (x - 80, 990), (x - 120, 990)], (255, 255, 255, 50))

    def tick(cv, t):                                    # the ceiling light ticks as the lift passes a floor
        a = 40 if (t % 1.6) < 0.08 else 0
        if a:
            cv.rect(0, 0, LW, LH, (0, 0, 0, a))
    life = [_anim(k, display, "floor"), _anim(k, shine, "shine", "screen"), _anim(k, tick, "tick")]

    def front(cv):
        for x0 in (-60, LW - 40):                       # the doors' steel edges at both sides
            cv.rect(x0, 0, x0 + 100, LH, (170, 176, 186, 255))
            cv.line([(x0 + 50, 0), (x0 + 50, LH)], (120, 124, 132, 255), 6)
    return _set("lift", s, zmax, life, _blur_front(k, front, 6), {"ambient": [246, 250, 255], "dir": -1,
                "vignette": 0.3}, 820, 1300)


# ------------------------------------------------------------------ out and about
def park_25d(s, zmax=1.0):
    k = 0.5 * s
    rnd = random.Random(31)
    leaves = [(rnd.uniform(0, LW), rnd.uniform(0, 1), rnd.uniform(0.6, 1.2), rnd.uniform(0, 6.28)) for _ in range(9)]

    def falling(cv, t):
        for (x, u, sp, ph) in leaves:
            yy = 700 + ((u + t * 0.06 * sp) % 1.0) * 1100
            xx = x + 40 * math.sin(t * 1.3 * sp + ph)
            cv.ell(xx, yy, 12, 6, (140, 180, 70, 230), INK, 1)

    def swing(cv, t):                                   # the swing going by itself in the breeze
        a = 0.35 * math.sin(t * 1.9)
        px, py, L = 980, 990, 180
        sx, sy = px + L * math.sin(a), py + L * math.cos(a)
        cv.line([(940, 990), (1020, 990)], (60, 60, 66, 255), 8)
        cv.line([(px - 30, py), (sx - 30, sy)], (60, 60, 66, 255), 3)
        cv.line([(px + 30, py), (sx + 30, sy)], (60, 60, 66, 255), 3)
        cv.rect(sx - 40, sy - 6, sx + 40, sy + 8, (220, 70, 60, 255), INK, 2)

    def lamp(cv, t):
        cv.glow(170, 990, 70, (255, 246, 200), int(60 + 20 * math.sin(t * 2)))
    life = [Layer(EMPTY, k, 0.3, birds(k, 5, 32, 300, 700), "birds"), _anim(k, swing, "swing"),
            _anim(k, falling, "leaves"), _anim(k, lamp, "lamp", "screen")]

    def front(cv):
        r = random.Random(33)
        for _ in range(40):
            x = r.uniform(-40, LW + 40)
            if 220 < x < 860:
                continue
            h = r.uniform(120, 260)
            cv.poly([(x - 10, LH + 20), (x + r.uniform(-30, 30), LH - h), (x + 10, LH + 20)],
                    (70 + r.randint(0, 40), 140 + r.randint(0, 40), 60, 255))
        for _ in range(8):
            x = r.choice((r.uniform(0, 200), r.uniform(880, LW)))
            cv.ell(x, r.uniform(1760, 1880), 16, 16, r.choice([(240, 90, 90), (250, 220, 70)]) + (255,))
    return _set("park", s, zmax, life, _blur_front(k, front), {"ambient": [255, 252, 240], "dir": -1,
                "vignette": 0.14}, 860, 1060)


def atm_25d(s, zmax=1.0):
    k = 0.5 * s

    def screen(cv, t):
        if (t % 1.0) < 0.55:                            # the cursor on the screen blinks
            cv.rect(640, 640, 652, 670, (255, 255, 255, 255))
        if (t % 1.4) < 0.7:                             # the CCTV's red dot
            cv.glow(1000, 380, 30, (255, 60, 50), 200)
            cv.ell(1000, 380, 8, 8, (255, 70, 60, 255))

    def hum(cv, t):                                     # the tube light: a cold flicker now and then
        if 3.0 < (t % 6.0) < 3.12:
            cv.rect(0, 0, LW, LH, (0, 0, 20, 60))

    def glow(cv, t):
        cv.glow(550, 585, 260, (120, 200, 255), 50)
    life = [_anim(k, screen, "screen"), _anim(k, glow, "screen_glow", "screen"), _anim(k, hum, "hum")]

    def front(cv):
        cv.rect(LW - 120, 0, LW + 40, LH, (140, 170, 190, 200))     # the glass door's frame at the side
        cv.rect(LW - 120, 0, LW - 90, LH, (60, 66, 76, 255))
    return _set("atm", s, zmax, life, _blur_front(k, front, 6), {"ambient": [240, 248, 255], "dir": -1,
                "vignette": 0.26}, 820, 1290)


def petrol_pump_25d(s, zmax=1.0):
    k = 0.5 * s

    def meters(cv, t):                                  # the meters roll on as the petrol runs
        for i, x in enumerate((300, 780)):
            rs = (t * (37 + 11 * i)) % 10000
            cv.rect(x - 64, 900, x + 64, 1000, (20, 24, 28, 255), INK, 2)
            cv.rect(x - 50, 918, x + 50, 948, (20, 24, 28, 255))
            for j, ch in enumerate("%04d" % int(rs)):
                cv.rect(x - 46 + j * 24, 920, x - 28 + j * 24, 946, (30, 50, 34, 255))
                h = int(ch)
                cv.rect(x - 44 + j * 24, 944 - h * 2.4, x - 30 + j * 24, 946, (90, 240, 120, 255))

    def road(cv, t):
        _traffic(cv, t, 1235, 34, 220, seed=4)

    def canopy(cv, t):
        for x in (180, 540, 900):
            cv.glow(x, 440, 120, (255, 250, 230), 60)
    life = [_anim(k, road, "traffic", d=0.6), _anim(k, meters, "meters"), _anim(k, canopy, "canopy", "screen")]

    def front(cv):
        cv.rect(-40, 1500, 120, 1800, (240, 240, 236, 255))          # the nozzle on its hook
        cv.poly([(120, 1560), (260, 1600), (260, 1640), (120, 1620)], (40, 40, 44, 255))
        cv.line([(60, 1800), (40, LH + 40)], (20, 20, 24, 255), 24)
    return _set("petrol_pump", s, zmax, life, _blur_front(k, front), {"ambient": [255, 250, 240], "dir": 1,
                "vignette": 0.16}, 860, 1250)


def signal_25d(s, zmax=1.0):
    k = 0.5 * s

    def countdown(cv, t):
        n = max(0, 88 - int(t))
        cv.rect(900, 900, 1044, 980, (20, 20, 24, 255), INK, 2)
        txt_x = 940
        for j, ch in enumerate("%02d" % n):             # two seven-segment digits
            d = int(ch)
            seg = ["abcedf", "bc", "abged", "abgcd", "fgbc", "afgcd", "afgedc", "abc", "abcdefg", "abcdfg"][d]
            x0, y0, w, h = txt_x + j * 44, 914, 28, 50
            pts = {"a": [(x0, y0), (x0 + w, y0)], "b": [(x0 + w, y0), (x0 + w, y0 + h / 2)],
                   "c": [(x0 + w, y0 + h / 2), (x0 + w, y0 + h)], "d": [(x0, y0 + h), (x0 + w, y0 + h)],
                   "e": [(x0, y0 + h / 2), (x0, y0 + h)], "f": [(x0, y0), (x0, y0 + h / 2)],
                   "g": [(x0, y0 + h / 2), (x0 + w, y0 + h / 2)]}
            for sgm in seg:
                cv.line(pts[sgm], (240, 50, 40, 255), 5)

    def red(cv, t):
        cv.glow(972, 580, 120, (255, 70, 50), int(110 + 60 * (0.5 + 0.5 * math.sin(t * 2.5))))

    def cross(cv, t):                                   # the other road's traffic crosses behind (it has green)
        _traffic(cv, t, 1140, 40, 260, seed=9)
    life = [_anim(k, cross, "traffic", d=0.7), _anim(k, countdown, "countdown"), _anim(k, red, "red", "screen")]

    def front(cv):
        cv.line([(-40, 1560), (220, 1520)], (30, 30, 34, 255), 26)  # a bike's handle and mirror
        cv.line([(150, 1530), (190, 1400)], (30, 30, 34, 255), 8)
        cv.ell(200, 1380, 46, 34, (40, 40, 46, 255))
        cv.ell(200, 1380, 34, 24, (150, 190, 220, 255))
    return _set("signal", s, zmax, life, _blur_front(k, front), {"ambient": [255, 250, 244], "dir": -1,
                "vignette": 0.16}, 860, 1120)


# ------------------------------------------------------------------ eat
def buffet_25d(s, zmax=1.0):
    k = 0.5 * s

    def steam(cv, t):
        for i, x in enumerate((170, 410, 650, 890)):
            _steam(cv, x, 760, t, 3, 170, 80, seed=i)

    def bulbs(cv, t):                                   # the fairy lights breathe in two groups
        for i in range(31):
            x = LW * i / 30.0
            y = 320 + 80 * math.sin(math.pi * i / 30.0)
            on = 0.5 + 0.5 * math.sin(t * 2.4 + (i % 2) * math.pi)
            cv.glow(x, y, 26, (255, 210, 120), int(60 + 120 * on))

    rnd = random.Random(41)
    petals = [(rnd.uniform(0, LW), rnd.random(), rnd.uniform(0.6, 1.2)) for _ in range(7)]

    def falling(cv, t):
        for (x, u, sp) in petals:
            y = ((u + t * 0.07 * sp) % 1.0) * LH
            cv.ell(x + 30 * math.sin(t + x), y, 9, 6, (246, 150, 40, 230))
    life = [_anim(k, steam, "steam", "screen"), _anim(k, bulbs, "bulbs", "screen"), _anim(k, falling, "petals")]

    def front(cv):
        for i in range(10):                             # a stack of plates in the corner
            cv.ell(940, 1880 - i * 14, 200, 40, (250, 250, 246, 255), (190, 190, 196, 255), 3)
    return _set("buffet", s, zmax, life, _blur_front(k, front, 7), {"ambient": [255, 240, 220], "dir": 1,
                "vignette": 0.22}, 820, 1290)


def restaurant_25d(s, zmax=1.0):
    k = 0.5 * s

    def lamps(cv, t):                                   # warm pools under the lamps, swaying a little
        for i, x in enumerate((280, 800)):
            sw = 6 * math.sin(t * 0.9 + i)
            cv.glow(x + sw, 720, 220, (255, 196, 120), 70)

    def street(cv, t):                                  # head- and tail-lights sliding past the window
        for i in range(5):
            x = 96 + ((t * 90 * (1 + 0.3 * i) + i * 160) % 448)
            c = (255, 240, 200) if i % 2 else (255, 80, 60)
            cv.glow(x, 540 + (i % 3) * 8, 14, c, 200)

    def steam(cv, t):
        _steam(cv, 270, 940, t, 3, 120, 60, seed=1)
        _steam(cv, 810, 940, t, 3, 120, 60, seed=4)
    life = [_anim(k, street, "street", "screen", d=0.2), _anim(k, lamps, "lamps", "screen"),
            _anim(k, steam, "steam", "screen")]

    def front(cv):
        cv.rect(780, 1600, 900, 1880, (210, 230, 240, 160), (150, 170, 180, 255), 4)   # a glass of water
        cv.rect(-40, 1700, 300, 1960, (120, 40, 40, 255))                              # the menu card
        cv.rect(-20, 1720, 280, 1940, (240, 230, 210, 255))
    return _set("restaurant", s, zmax, life, _blur_front(k, front), {"ambient": [255, 232, 200], "dir": 1,
                "vignette": 0.3}, 820, 1290)


# ------------------------------------------------------------------ work
def interview_room_25d(s, zmax=1.0):
    k = 0.5 * s

    def clock(cv, t):                                   # a wall clock, its seconds hand ticking
        cx, cy, r = 990, 240, 54
        cv.ell(cx, cy, r, r, (250, 250, 246, 255), INK, 3)
        a = math.radians(int(t) * 6)
        cv.line([(cx, cy), (cx + 0.85 * r * math.sin(a), cy - 0.85 * r * math.cos(a))], (220, 50, 40, 255), 2)
        cv.line([(cx, cy), (cx + 0.5 * r * math.sin(1.0), cy - 0.5 * r * math.cos(1.0))], INK, 4)

    def shine(cv, t):
        x = 140 + ((t * 80) % 900)
        if x < 940:
            cv.poly([(x, 262), (x + 30, 262), (x - 40, 638), (x - 70, 638)], (255, 255, 255, 60))
    life = [_anim(k, clock, "clock"), _anim(k, shine, "shine", "screen")]

    def front(cv):
        cv.rect(800, 1500, 880, 1880, (170, 214, 236, 200), (120, 160, 180, 255), 4)   # a water bottle
        cv.rect(-40, 1760, 380, 1960, (220, 200, 120, 255))                            # a file
        cv.rect(-40, 1740, 380, 1770, (200, 170, 90, 255))
    return _set("interview_room", s, zmax, life, _blur_front(k, front), {"ambient": [246, 248, 255], "dir": -1,
                "vignette": 0.22}, 820, 1280)


def call_center_25d(s, zmax=1.0):
    k = 0.5 * s
    rnd = random.Random(51)
    mons = [(130, 700), (390, 700), (650, 700), (910, 700), (210, 960), (550, 960), (890, 960)]
    ph = [rnd.uniform(0, 6.28) for _ in mons]

    def flicker(cv, t):
        for (x, y), p in zip(mons, ph):
            a = int(50 + 40 * (0.5 + 0.5 * math.sin(t * 7 + p)) + (40 if (t * 3 + p) % 4 < 0.1 else 0))
            cv.glow(x, y, 90, (140, 200, 255), a)

    def board(cv, t):
        if (t % 1.2) < 0.6:
            cv.glow(540, 260, 260, (255, 80, 70), 50)
    life = [_anim(k, flicker, "monitors", "screen"), _anim(k, board, "target", "screen")]

    def front(cv):
        cv.line([(LW - 260, LH + 40), (LW - 260, 1760), (LW - 60, 1700), (LW - 60, LH + 40)], (30, 30, 34, 255), 26)
        cv.ell(LW - 260, 1800, 60, 80, (40, 40, 46, 255))                          # a headset on the desk edge
        cv.ell(LW - 60, 1740, 60, 80, (40, 40, 46, 255))
        cv.line([(LW - 260, 1840), (LW - 380, 1700)], (30, 30, 34, 255), 10)
    return _set("call_center", s, zmax, life, _blur_front(k, front), {"ambient": [230, 238, 255], "dir": -1,
                "vignette": 0.32}, 820, 1290)


def startup_office_25d(s, zmax=1.0):
    k = 0.5 * s

    def neon(cv, t):                                    # HUSTLE flickers like a cheap neon
        bad = (t % 4.0) < 0.12 or 1.9 < (t % 4.0) < 1.98
        if not bad:
            cv.glow(190, 360, 170, (255, 90, 210), 120)

    def laptops(cv, t):
        for i, x in enumerate((555, 755, 955)):
            cv.glow(x, 870, 60, (150, 210, 255), int(70 + 30 * math.sin(t * 2 + i)))

    def note(cv, t):                                    # one sticky note flutters in the AC
        a = 10 * math.sin(t * 5)
        cx, cy = 920, 300
        r = math.radians(a)
        pts = [(cx + dx * math.cos(r) - dy * math.sin(r), cy + dx * math.sin(r) + dy * math.cos(r))
               for dx, dy in ((-25, 0), (25, 0), (25, 50), (-25, 50))]
        cv.poly(pts, (250, 230, 90, 255), INK, 2)
    life = [_anim(k, neon, "neon", "screen"), _anim(k, laptops, "laptops", "screen"), _anim(k, note, "note"),
            Layer(EMPTY, 0.3 * s, 1.0, motes(((500, 300), (1000, 900), 300), 0.3 * s, 30, 52), "dust", mode="screen")]

    def front(cv):
        cv.rect(800, 1640, 960, 1880, (240, 240, 236, 255), (180, 180, 186, 255), 4)   # a coffee mug
        cv.ell(960, 1740, 50, 60, None, (240, 240, 236, 255), 18)
        cv.rect(-40, 1800, 420, 1960, (60, 64, 72, 255))                              # a laptop's corner
    return _set("startup_office", s, zmax, life, _blur_front(k, front), {"ambient": [255, 248, 246], "dir": -1,
                "vignette": 0.22}, 820, 1280)


SETS = {"ghar_darwaza_25d": ghar_darwaza_25d, "lift_25d": lift_25d, "park_25d": park_25d, "atm_25d": atm_25d,
        "petrol_pump_25d": petrol_pump_25d, "signal_25d": signal_25d, "buffet_25d": buffet_25d,
        "restaurant_25d": restaurant_25d, "interview_room_25d": interview_room_25d,
        "call_center_25d": call_center_25d, "startup_office_25d": startup_office_25d}

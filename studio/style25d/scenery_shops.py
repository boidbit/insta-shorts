"""Hand-made 2.5D shop sets, painted like the kitchen and the office.

mithai_25d   a sweet shop: MITHAI BHANDAR, a string of bulbs that twinkles, wooden shelves of sweet boxes and jars, the
             long glass counter of laddoos, jalebi, barfi and gulab jamun, a kadhai of jalebi steaming, a fly about,
             today's special (AAJ: RASGULLA), a pink sweet box blurred in front.
mobile_25d   a mobile shop: MOBILE POINT, a wall of phones whose screens change, the 5G SALE light box, 50% OFF / EMI 0%,
             phone covers on pegs, a glass counter of earbuds and chargers, a phone box blurred in front.
medical_25d  a chemist: MEDICAL STORE with a green cross that blinks, shelves of medicine boxes, the INSULIN fridge, the
             counter with tablet strips and a BP machine, a fan, a syrup bottle blurred in front.
salon_25d    a salon: SALON, a big mirror with bulbs round it, bottles on the shelf, the red barber chair, a barber pole
             that turns, hair-style posters, towels, a black-and-white floor, the trolley of scissors in front.
mall_25d     a mall: a glass roof onto the sky (its own far layer), two floors of shops (SALE 50%, SHOES, GADGETS), a
             glass railing with shoppers passing upstairs, a moving escalator, plants, a shiny floor, shopping bags.
cinema_25d   a cinema hall: the big screen with the film playing (its light on the audience), red curtains, the beam of
             the projector with dust in it, rows of red seats with heads, step lights, EXIT, a popcorn tub in front.
(All have writing on them, so a reverse shot never mirrors them.)
"""
import math
import random

from PIL import Image, ImageDraw

from .scenery import PAL_BULB, Cv, Layer, Layered, along, catenary, fill_tex, motes, mul, quad_image, sign_image, \
    steam, twinkle, vgrad
from .scenery_civic import _room_shell, board_image
from .scenery_home import _clock, _floor_tiles, _leaves, _shadow, _tube_light
from ..util import LH, LW

INK = (44, 38, 40, 255)
VP, F = (540, 800), 1280


def _blank(k, fill=(0, 0, 0, 0)):
    return Image.new("RGBA", (8, 8), fill)


def _glass_counter(cv, x0, x1, top, F_, base_col, items):
    """A shop's glass counter along the back wall: the glass case on top (items(cv, y0, y1) fills it), a wooden
    base below."""
    mid = top + 150
    cv.rect(x0, top, x1, top + 14, (220, 236, 244, 255), INK, 2)
    cv.rect(x0 + 6, top + 14, x1 - 6, mid, (214, 236, 246, 255), INK, 2)
    items(cv, top + 14, mid)
    cv.poly([(x0 + 30, mid - 6), (x0 + 120, top + 20), (x0 + 170, top + 20), (x0 + 80, mid - 6)], (255, 255, 255, 70))
    cv.rect(x0, mid, x1, F_, base_col + (255,), INK, 3)
    for x in range(int(x0) + 16, int(x1) - 40, 130):
        cv.rect(x, mid + 18, x + 110, F_ - 18, mul(base_col, 1.1) + (255,), mul(base_col, 0.7) + (255,), 2)
    _shadow(cv, (x0 + x1) / 2, F_ + 4, (x1 - x0) / 2, 14)


# ------------------------------------------------------------------ mithai shop
KADHAI = (960, 930)


def _sweets(cv, y0, y1):
    x = 70
    kinds = ("laddoo", "jalebi", "barfi", "jamun", "katli", "laddoo", "barfi")
    i = 0
    while x < 980:
        kind = kinds[i % len(kinds)]
        cv.rect(x, y1 - 26, x + 120, y1 - 12, (200, 200, 206, 255), INK, 1)          # a steel tray
        if kind == "laddoo":
            for r in range(3):
                for c in range(4 - r):
                    cv.ell(x + 22 + c * 26 + r * 13, y1 - 38 - r * 20, 13, 12, (250, 160, 40, 255), INK, 1)
        elif kind == "jalebi":
            for c in range(3):
                for rr in (18, 11, 5):
                    cv.ell(x + 26 + c * 34, y1 - 44, rr, rr * 0.8, None, (240, 140, 30, 255), 4)
        elif kind == "barfi":
            for c in range(4):
                for r in range(2):
                    cv.poly([(x + 18 + c * 26, y1 - 32 - r * 22), (x + 30 + c * 26, y1 - 44 - r * 22),
                             (x + 42 + c * 26, y1 - 32 - r * 22), (x + 30 + c * 26, y1 - 20 - r * 22)],
                            ((250, 246, 230), (190, 230, 170))[(c + r) % 2] + (255,), INK, 1)
        elif kind == "katli":
            for c in range(4):
                cv.poly([(x + 16 + c * 26, y1 - 34), (x + 30 + c * 26, y1 - 48), (x + 44 + c * 26, y1 - 34),
                         (x + 30 + c * 26, y1 - 20)], (226, 228, 232, 255), INK, 1)
        else:                                                                         # gulab jamun in a bowl
            cv.ell(x + 60, y1 - 34, 54, 22, (230, 232, 236, 255), INK, 2)
            for c in range(4):
                cv.ell(x + 26 + c * 22, y1 - 42 + (c % 2) * 4, 11, 10, (120, 50, 30, 255), INK, 1)
        x += 136
        i += 1


def _mithai(k, kg):
    cv = Cv(k, blend=True)
    gA = Cv(kg, fill=(255, 190, 110, 0))
    gB = Cv(kg, fill=(255, 190, 110, 0))
    gS = Cv(kg, fill=(255, 220, 160, 0))
    rnd = random.Random(201)
    _room_shell(cv, F, (250, 226, 190), (244, 212, 168))
    _tube_light(cv, gS, 130, 330, 100)
    _tube_light(cv, gS, 750, 950, 100)
    quad_image(cv, sign_image("MITHAI BHANDAR", (200, 40, 40), (255, 220, 90), 1200, 200),
               [(230, 140), (850, 140), (850, 236), (230, 236)])
    pts = catenary(-20, 262, 1100, 262, 40)
    cv.line(pts, (60, 40, 40, 255), 2)
    for i, (bx, by) in enumerate(along(pts, 34)):
        (gA if i % 2 else gB).ell(bx, by + 8, 6, 6, PAL_BULB[i % len(PAL_BULB)] + (250,))
        gS.ell(bx, by + 8, 16, 16, PAL_BULB[i % len(PAL_BULB)] + (40,))
    for (x0, x1) in ((40, 480), (600, 1040)):                                         # shelves of sweet boxes
        cv.rect(x0, 340, x1, 930, (110, 70, 44, 255), INK, 3)
        cv.rect(x0 + 14, 354, x1 - 14, 916, (80, 50, 32, 255))
        for y in (520, 700, 880):
            cv.rect(x0 + 10, y, x1 - 10, y + 14, (150, 100, 62, 255), INK, 2)
            bx = x0 + 22
            while bx < x1 - 70:
                col = rnd.choice(((240, 120, 40), (220, 40, 70), (250, 200, 60), (250, 246, 236), (70, 150, 80)))
                cv.rect(bx, y - 120, bx + 60, y, col + (255,), INK, 2)
                cv.rect(bx, y - 74, bx + 60, y - 58, (250, 250, 246, 255))
                bx += 72
        for j in range(3):                                                             # jars on top
            jx = x0 + 70 + j * 140
            cv.rect(jx - 30, 286, jx + 30, 340, (220, 240, 246, 230), INK, 2)
            cv.rect(jx - 22, 276, jx + 22, 288, (220, 60, 60, 255), INK, 1)
            for b in range(3):
                cv.ell(jx - 14 + b * 14, 324, 9, 9, ((250, 160, 40), (250, 246, 236), (250, 200, 60))[j] + (255,))
    _glass_counter(cv, 30, 1050, 960, F, (150, 96, 56), _sweets)
    quad_image(cv, sign_image("AAJ: RASGULLA", (40, 60, 50), (255, 255, 255), 700, 160),
               [(700, 1150), (960, 1150), (960, 1210), (700, 1210)])
    kx, ky = KADHAI                                                                   # the jalebi kadhai
    cv.poly([(kx - 70, ky), (kx + 70, ky), (kx + 50, ky + 30), (kx - 50, ky + 30)], (60, 56, 56, 255), INK, 3)
    cv.ell(kx, ky, 70, 12, (220, 160, 60, 255), INK, 2)
    for c in range(3):
        cv.ell(kx - 34 + c * 34, ky - 2, 14, 6, None, (240, 140, 30, 255), 3)
    _floor_tiles(cv, VP, F, (200, 150, 104), (186, 138, 94), step=160, grow=1.22, grout=(150, 108, 70, 255))
    for b in (gA, gB):
        b.blur(1.0)
    gS.blur(12)
    return cv, gA, gB, gS


def _fly(k):
    """fn: a fly buzzing over the sweets."""
    def fn(_im, t):
        cv = Cv(k, fill=(30, 30, 30, 0))
        x = 420 + 220 * math.sin(t * 1.3) + 40 * math.sin(t * 7.1)
        y = 900 + 50 * math.sin(t * 2.2 + 1.0) + 14 * math.sin(t * 11.0)
        cv.ell(x, y, 5, 4, (30, 30, 34, 255))
        flap = abs(math.sin(t * 60))
        cv.ell(x - 4, y - 5, 4, 2 + 2 * flap, (220, 220, 230, 170))
        cv.ell(x + 4, y - 5, 4, 2 + 2 * flap, (220, 220, 230, 170))
        return cv.im
    return fn


def _mithai_front(k):
    cv = Cv(k, fill=(240, 120, 160, 0), blend=True)
    cv.poly([(-60, 1700), (300, 1680), (320, 1960), (-60, 1960)], (240, 130, 170, 255))      # a pink sweet box
    cv.rect(100, 1680, 140, 1960, (250, 210, 60, 255))
    cv.blur(9)
    return cv


def mithai_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    st, gA, gB, gS = _mithai(kr, kg)
    fg = _mithai_front(0.5 * s)
    back = [
        Layer(st.im, kr, 1.0, None, "set"),
        Layer(gA.im, kg, 1.0, twinkle((gA.im, gB.im), 0.8, static=gS.im), "bulbs", mode="screen"),
        Layer(_blank(0.3 * s), 0.3 * s, 1.0, steam([(KADHAI[0], KADHAI[1] - 10, 0.8, 0.4)], 0.3 * s), "steam"),
        Layer(_blank(0.5 * s), 0.5 * s, 1.0, _fly(0.5 * s), "fly"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return Layered(back, front, light={"ambient": [255, 244, 228], "dir": 1, "vignette": 0.24}, horizon=VP[1],
                   ground=F)


# ------------------------------------------------------------------ mobile shop
PHONES = [(80 + c * 78, 330 + r * 150, 80 + c * 78 + 54, 330 + r * 150 + 110) for r in range(4) for c in range(6)]


def _mobile(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(220, 236, 255, 0))
    rnd = random.Random(211)
    _room_shell(cv, F, (232, 238, 246), (220, 228, 240))
    _tube_light(cv, light, 120, 340, 96)
    _tube_light(cv, light, 740, 960, 96)
    quad_image(cv, sign_image("MOBILE POINT", (30, 70, 170), (255, 255, 255), 1100, 200),
               [(300, 136), (780, 136), (780, 236), (300, 236)])
    cv.rect(56, 300, 564, 940, (250, 250, 252, 255), INK, 3)                           # the wall of phones
    for (x0, y0, x1, y1) in PHONES:
        cv.rect(x0, y0, x1, y1, (30, 30, 36, 255), INK, 2)
        cv.rect(x0 + 4, y0 + 8, x1 - 4, y1 - 8, (40, 50, 70, 255))
        cv.rect(x0 + 6, y1 + 6, x1 - 6, y1 + 14, (200, 200, 206, 255))                 # its price tag
    cv.rect(640, 300, 1000, 480, (40, 120, 230, 255), INK, 4)                           # the 5G light box
    quad_image(cv, sign_image("5G SALE", (40, 120, 230), (255, 255, 255), 700, 300, border=(40, 120, 230)),
               [(660, 316), (980, 316), (980, 464), (660, 464)])
    light.glow(820, 390, 240, (120, 180, 255), 70)
    quad_image(cv, board_image(["50% OFF", "EMI 0%"], (250, 220, 60), (40, 40, 40), w=560, h=400,
                               title_col=(210, 40, 40), border=(200, 160, 40)),
               [(680, 520), (960, 520), (960, 720), (680, 720)])
    for r in range(2):                                                                 # covers on pegs
        for c in range(6):
            x, y = 660 + c * 58, 760 + r * 90
            cv.line([(x + 20, y - 12), (x + 20, y)], (120, 120, 126, 255), 3)
            cv.rect(x, y, x + 40, y + 70, rnd.choice(((240, 80, 120), (60, 160, 230), (250, 200, 60), (40, 40, 44),
                                                      (120, 200, 140))) + (255,), INK, 2)
            cv.ell(x + 12, y + 14, 6, 6, (30, 30, 34, 255))

    def stuff(c, y0, y1):
        for i in range(8):
            x = 90 + i * 112
            if i % 3 == 0:                                                              # earbud boxes
                c.rect(x, y1 - 70, x + 70, y1 - 10, (250, 250, 252, 255), INK, 2)
                c.ell(x + 22, y1 - 40, 8, 10, (240, 240, 244, 255), INK, 1)
                c.ell(x + 48, y1 - 40, 8, 10, (240, 240, 244, 255), INK, 1)
            elif i % 3 == 1:                                                            # chargers
                c.rect(x + 10, y1 - 60, x + 50, y1 - 14, (240, 240, 244, 255), INK, 2)
                c.line([(x + 30, y1 - 60), (x + 60, y1 - 90), (x + 80, y1 - 20)], (240, 240, 244, 255), 3)
            else:                                                                       # power banks
                c.rect(x, y1 - 50, x + 80, y1 - 12, (60, 60, 70, 255), INK, 2)
                for d in range(4):
                    c.ell(x + 12 + d * 10, y1 - 30, 3, 3, (90, 200, 255, 255))
    _glass_counter(cv, 40, 1040, 980, F, (60, 70, 96), stuff)
    cv.rect(820, 940, 900, 980, (40, 40, 46, 255), INK, 2)                             # the billing machine
    cv.rect(830, 946, 890, 964, (120, 200, 140, 255))
    _floor_tiles(cv, VP, F, (226, 230, 236), (208, 214, 222), step=120, grow=1.24, grout=(180, 186, 196, 255))
    light.blur(10)
    return cv, light


def _phone_screens(k):
    """fn (screen): the phones' screens, each changing now and then (wallpaper, video, home screen)."""
    pal = [(70, 140, 255), (255, 120, 160), (90, 220, 170), (255, 190, 80), (170, 120, 255), (120, 220, 255)]

    def fn(_im, t):
        cv = Cv(k, fill=(100, 160, 255, 0))
        for i, (x0, y0, x1, y1) in enumerate(PHONES):
            n = int(t / 2.4 + i * 0.37)
            a, b = pal[(n + i) % len(pal)], pal[(n * 2 + i + 1) % len(pal)]
            cv.rect(x0 + 5, y0 + 10, x1 - 5, (y0 + y1) / 2, a + (200,))
            cv.rect(x0 + 5, (y0 + y1) / 2, x1 - 5, y1 - 10, b + (200,))
            if (n + i) % 3 == 0:
                for r in range(3):
                    for c in range(2):
                        cv.rect(x0 + 10 + c * 18, y0 + 18 + r * 22, x0 + 22 + c * 18, y0 + 30 + r * 22,
                                (255, 255, 255, 200))
        return cv.im
    return fn


def _mobile_front(k):
    cv = Cv(k, fill=(40, 40, 46, 0), blend=True)
    cv.rect(820, 1700, 1120, 1960, (250, 250, 252, 255))                                # a phone box
    cv.rect(880, 1760, 1060, 1900, (40, 40, 46, 255))
    cv.line(catenary(-40, 1780, 300, 1900, 120), (250, 250, 252, 255), 10)            # an earphone cable
    cv.blur(9)
    return cv


def mobile_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    st, light = _mobile(kr, kg)
    fg = _mobile_front(0.5 * s)
    back = [
        Layer(st.im, kr, 1.0, None, "set"),
        Layer(light.im, kg, 1.0, None, "lights", mode="screen"),
        Layer(_blank(0.5 * s), 0.5 * s, 1.0, _phone_screens(0.5 * s), "screens", mode="screen"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return Layered(back, front, light={"ambient": [244, 248, 255], "dir": 1, "vignette": 0.2}, horizon=VP[1],
                   ground=F)


# ------------------------------------------------------------------ medical store
CROSS = (860, 180)


def _medical(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(230, 255, 240, 0))
    rnd = random.Random(221)
    _room_shell(cv, F, (234, 246, 238), (222, 236, 228))
    _tube_light(cv, light, 140, 360, 100)
    quad_image(cv, sign_image("MEDICAL STORE", (30, 130, 80), (255, 255, 255), 1100, 200),
               [(240, 136), (760, 136), (760, 236), (240, 236)])
    cx, cy = CROSS                                                                      # the cross (lit by the layer)
    cv.rect(cx - 50, cy - 50, cx + 50, cy + 50, (40, 50, 46, 255), INK, 2)
    cv.rect(cx - 14, cy - 40, cx + 14, cy + 40, (40, 90, 60, 255))
    cv.rect(cx - 40, cy - 14, cx + 40, cy + 14, (40, 90, 60, 255))
    cv.rect(40, 300, 700, 940, (246, 248, 246, 255), INK, 3)                            # shelves of medicines
    for y in (440, 580, 720, 860):
        cv.rect(46, y, 694, y + 12, (200, 204, 206, 255), INK, 1)
        x = 56
        while x < 680:
            w = rnd.uniform(26, 50)
            h = rnd.uniform(50, 110)
            col = rnd.choice(((250, 250, 246), (236, 244, 250), (250, 240, 220)))
            stripe = rnd.choice(((220, 50, 50), (40, 120, 200), (40, 150, 90), (240, 160, 40)))
            cv.rect(x, y - h, x + w, y, col + (255,), INK, 1)
            cv.rect(x, y - h * 0.6, x + w, y - h * 0.48, stripe + (255,))
            x += w + 4
    cv.rect(760, 330, 1040, 940, (220, 226, 230, 255), INK, 3)                         # the INSULIN fridge
    cv.rect(780, 380, 1020, 920, (206, 232, 246, 255), INK, 2)
    quad_image(cv, sign_image("INSULIN", (250, 250, 252), (30, 70, 160), 500, 120), [(800, 340), (1000, 340),
                                                                                     (1000, 372), (800, 372)])
    for y in (500, 640, 780):
        cv.line([(780, y), (1020, y)], (170, 190, 204, 255), 3)
        for x in range(800, 1000, 26):
            cv.rect(x, y - 40, x + 14, y, (240, 244, 250, 255), INK, 1)
            cv.rect(x + 2, y - 46, x + 12, y - 40, (220, 120, 40, 255))
    cv.rect(1004, 560, 1012, 700, (160, 166, 170, 255))

    def stuff(c, y0, y1):
        for i in range(9):                                                              # tablet strips
            x = 80 + i * 70
            c.rect(x, y1 - 50, x + 50, y1 - 12, (220, 224, 230, 255), INK, 1)
            for r in range(2):
                for q in range(3):
                    c.ell(x + 10 + q * 15, y1 - 38 + r * 14, 5, 5, ((250, 250, 250), (240, 120, 120))[i % 2] + (255,))
        c.rect(780, y1 - 80, 900, y1 - 12, (240, 244, 248, 255), INK, 2)              # a BP machine
        c.rect(796, y1 - 70, 860, y1 - 40, (60, 80, 70, 255))
        c.line([(900, y1 - 40), (960, y1 - 70), (980, y1 - 20)], (40, 40, 44, 255), 3)
    _glass_counter(cv, 40, 1040, 980, F, (80, 140, 110), stuff)
    quad_image(cv, sign_image("STAY HEALTHY", (80, 140, 110), (255, 255, 255), 700, 150, border=(80, 140, 110)),
               [(380, 1180), (700, 1180), (700, 1230), (380, 1230)])
    _floor_tiles(cv, VP, F, (230, 236, 232), (214, 222, 218), step=120, grow=1.24, grout=(186, 196, 190, 255))
    light.blur(8)
    return cv, light


def _cross(k):
    """fn (screen): the green LED cross, its rings lighting up in turn."""
    cx, cy = CROSS

    def fn(_im, t):
        cv = Cv(k, fill=(60, 255, 120, 0))
        ph = int(t * 3) % 4
        f = 1.0 if ph else 0.55
        cv.rect(cx - 12, cy - 38, cx + 12, cy + 38, (60, 255, 120, int(230 * f)))
        cv.rect(cx - 38, cy - 12, cx + 38, cy + 12, (60, 255, 120, int(230 * f)))
        cv.glow(cx, cy, 110, (60, 255, 120), int(60 * f))
        return cv.im
    return fn


def _medical_front(k):
    cv = Cv(k, fill=(150, 60, 30, 0), blend=True)
    cv.poly([(900, 1960), (1080, 1960), (1080, 1720), (1040, 1680), (1040, 1620), (940, 1620), (940, 1680),
             (900, 1720)], (150, 60, 30, 230))                                         # a syrup bottle
    cv.rect(930, 1580, 1050, 1622, (240, 240, 244, 255))
    cv.rect(910, 1760, 1070, 1880, (250, 250, 246, 255))
    cv.blur(9)
    return cv


def medical_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    st, light = _medical(kr, kg)
    fg = _medical_front(0.5 * s)
    back = [
        Layer(st.im, kr, 1.0, None, "set"),
        Layer(light.im, kg, 1.0, None, "lights", mode="screen"),
        Layer(_blank(0.4 * s), 0.4 * s, 1.0, _cross(0.4 * s), "cross", mode="screen"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return Layered(back, front, light={"ambient": [244, 255, 248], "dir": 1, "vignette": 0.2}, horizon=VP[1],
                   ground=F)


# ------------------------------------------------------------------ salon
MIRROR = (200, 300, 860, 880)
POLE = (990, 940, 1030, 1180)


def _salon(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(255, 240, 200, 0))
    rnd = random.Random(231)
    _room_shell(cv, F, (240, 226, 206), (232, 214, 190))
    quad_image(cv, sign_image("SALON", (30, 30, 34), (240, 200, 90), 600, 180), [(380, 110), (700, 110), (700, 206),
                                                                                (380, 206)])
    x0, y0, x1, y1 = MIRROR
    cv.rect(x0 - 18, y0 - 18, x1 + 18, y1 + 18, (60, 50, 50, 255), INK, 3)
    fill_mirror = vgrad(k, [(0, (196, 220, 230)), (LH, (170, 196, 210))])
    mask = Image.new("L", cv.im.size, 0)
    ImageDraw.Draw(mask).rectangle([x0 * k, y0 * k, x1 * k, y1 * k], fill=255)
    cv.im.paste(fill_mirror, (0, 0), mask)
    cv.d = ImageDraw.Draw(cv.im)
    cv.rect(x0, y0 + 330, x1, y1, (210, 196, 180, 120))                              # the room seen in the mirror
    cv.rect(x0 + 380, y0 + 150, x0 + 470, y0 + 330, (150, 120, 100, 110))
    for (a, b) in ((60, 130), (190, 220)):                                            # shine
        cv.poly([(x0 + a, y1), (x0 + a + 160, y0), (x0 + b + 160, y0), (x0 + b, y1)], (255, 255, 255, 60))
    for bx in range(int(x0), int(x1) + 1, 60):                                         # bulbs round the mirror
        cv.ell(bx, y0 - 9, 10, 10, (255, 244, 200, 255), INK, 1)
        light.glow(bx, y0 - 9, 44, (255, 236, 180), 70)
    for by in range(int(y0) + 60, int(y1), 90):
        for bx in (x0 - 9, x1 + 9):
            cv.ell(bx, by, 10, 10, (255, 244, 200, 255), INK, 1)
            light.glow(bx, by, 44, (255, 236, 180), 60)
    cv.rect(x0 - 30, y1 + 20, x1 + 30, y1 + 40, (120, 80, 50, 255), INK, 2)           # shelf with bottles
    for i in range(14):
        bx = x0 + 10 + i * 46
        col = rnd.choice(((40, 120, 200), (220, 60, 60), (60, 160, 90), (240, 200, 60), (200, 120, 200)))
        h = rnd.uniform(40, 70)
        cv.rect(bx, y1 + 20 - h, bx + 26, y1 + 20, col + (255,), INK, 1)
        cv.rect(bx + 8, y1 + 10 - h, bx + 18, y1 + 20 - h, (40, 40, 44, 255))
    cv.rect(40, 330, 170, 600, (250, 248, 240, 255), INK, 2)                           # hair-style poster
    for i in range(3):
        cy = 380 + i * 80
        cv.ell(105, cy, 22, 26, (220, 180, 140, 255), INK, 1)
        cv.poly([(83, cy - 6), (90, cy - 30), (120, cy - 32), (127, cy - 6)], ((40, 30, 30), (90, 60, 30),
                                                                                (30, 30, 34))[i] + (255,))
    _clock(cv, 105, 700, 36)
    cv.rect(900, 360, 1050, 900, (150, 100, 62, 255), INK, 3)                          # towel cabinet
    for y in range(390, 880, 90):
        cv.rect(918, y, 1032, y + 70, (130, 84, 52, 255), INK, 1)
        cv.rect(930, y + 10, 1020, y + 60, rnd.choice(((250, 250, 250), (180, 220, 240), (250, 220, 220))) + (255,))
    # the barber chair
    cv.rect(500, 1180, 580, 1240, (150, 150, 156, 255), INK, 2)
    cv.poly([(470, F - 6), (610, F - 6), (590, 1240), (490, 1240)], (110, 110, 116, 255), INK, 2)
    cv.poly([(470, 960), (610, 960), (620, 1110), (460, 1110)], (170, 30, 40, 255), INK, 3)
    cv.ell(540, 950, 50, 18, (170, 30, 40, 255), INK, 2)
    cv.rect(440, 1110, 640, 1180, (150, 26, 36, 255), INK, 3)
    for ax in (420, 640):
        cv.rect(ax, 1080, ax + 20, 1150, (60, 60, 64, 255), INK, 2)
    pole = POLE
    cv.rect(pole[0] - 6, pole[1] - 20, pole[2] + 6, pole[1], (200, 200, 206, 255), INK, 2)
    cv.rect(pole[0] - 6, pole[3], pole[2] + 6, pole[3] + 20, (200, 200, 206, 255), INK, 2)
    # black and white floor
    _floor_tiles(cv, VP, F, (250, 250, 248), (40, 40, 44), step=110, grow=1.24)
    _shadow(cv, 540, F + 4, 140, 12)
    light.blur(4)
    return cv, light


def _barber_pole(k):
    """fn: the barber pole's stripes running up as it turns."""
    x0, y0, x1, y1 = POLE

    def fn(_im, t):
        cv = Cv(k, fill=(250, 250, 250, 0))
        cv.rect(x0, y0, x1, y1, (250, 250, 250, 255))
        off = (t * 60.0) % 60.0
        for i in range(-2, 8):
            y = y1 - i * 60 + off - 60
            for (col, d) in (((220, 40, 50), 0), ((40, 80, 180), 30)):
                cv.poly([(x0, y + d), (x1, y + d - 30), (x1, y + d - 14), (x0, y + d + 16)], col + (255,))
        out = cv.im
        mask = Image.new("L", out.size, 0)
        ImageDraw.Draw(mask).rectangle([x0 * k, y0 * k, x1 * k, y1 * k], fill=255)
        clip = Image.new("RGBA", out.size, (250, 250, 250, 0))
        clip.paste(out, (0, 0), mask)
        return clip
    return fn


def _salon_front(k):
    cv = Cv(k, fill=(60, 60, 64, 0), blend=True)
    cv.rect(-40, 1640, 260, 1670, (90, 90, 96, 255))                                   # a trolley
    cv.rect(10, 1670, 30, 1960, (90, 90, 96, 255))
    cv.rect(220, 1670, 240, 1960, (90, 90, 96, 255))
    cv.line([(40, 1630), (120, 1580)], (200, 200, 206, 255), 8)                        # scissors and a comb
    cv.line([(60, 1580), (130, 1630)], (200, 200, 206, 255), 8)
    cv.rect(160, 1600, 250, 1620, (30, 30, 34, 255))
    cv.blur(9)
    return cv


def salon_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    st, light = _salon(kr, kg)
    fg = _salon_front(0.5 * s)
    back = [
        Layer(st.im, kr, 1.0, None, "set"),
        Layer(light.im, kg, 1.0, None, "lights", mode="screen"),
        Layer(_blank(0.5 * s), 0.5 * s, 1.0, _barber_pole(0.5 * s), "pole"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return Layered(back, front, light={"ambient": [255, 248, 236], "dir": 1, "vignette": 0.22}, horizon=VP[1],
                   ground=F)


# ------------------------------------------------------------------ mall
M_F = 1250
UP_FLOOR = 600
ESC = ((400, M_F), (720, UP_FLOOR))


def _mall_sky(k):
    cv = Cv(k, blend=True)
    cv.im = vgrad(k, [(0, (90, 160, 230)), (300, (150, 200, 240)), (LH, (200, 226, 246))])
    cv.d = ImageDraw.Draw(cv.im)
    rnd = random.Random(241)
    for (cx, cy, w) in ((300, 90, 220), (800, 140, 180)):
        for _ in range(6):
            cv.ell(cx + rnd.uniform(-w / 2, w / 2), cy + rnd.uniform(-10, 10), w * 0.3, w * 0.14, (255, 255, 255, 220))
    cv.blur(2.0)
    return cv


def _shopfront(cv, x0, y0, x1, y1, name, col, goods, rnd):
    cv.rect(x0, y0, x1, y1, (236, 240, 244, 255), INK, 3)
    quad_image(cv, sign_image(name, col, (255, 255, 255), 600, 140), [(x0 + 14, y0 + 12), (x1 - 14, y0 + 12),
                                                                    (x1 - 14, y0 + 58), (x0 + 14, y0 + 58)])
    gx0, gy0 = x0 + 12, y0 + 70
    cv.rect(gx0, gy0, x1 - 12, y1 - 6, (206, 226, 238, 255), INK, 2)
    base = y1 - 10
    if goods == "clothes":                                                              # mannequins
        for i in range(2):
            mx = gx0 + 50 + i * (x1 - x0 - 120)
            cv.ell(mx, base - 190, 16, 18, (230, 230, 232, 255), INK, 1)
            cv.poly([(mx - 30, base - 170), (mx + 30, base - 170), (mx + 24, base - 60), (mx - 24, base - 60)],
                    rnd.choice(((220, 50, 70), (60, 120, 200), (250, 200, 60))) + (255,), INK, 1)
            cv.rect(mx - 3, base - 60, mx + 3, base, (120, 120, 126, 255))
    elif goods == "shoes":
        for r in range(2):
            for c in range(3):
                sx = gx0 + 20 + c * (x1 - x0 - 60) / 3.0
                sy = base - 30 - r * 80
                cv.rect(sx - 6, sy + 6, sx + 70, sy + 12, (200, 200, 206, 255))
                cv.poly([(sx, sy + 6), (sx + 60, sy + 6), (sx + 56, sy - 14), (sx + 20, sy - 22), (sx, sy - 22)],
                        rnd.choice(((40, 100, 200), (240, 240, 240), (220, 60, 60))) + (255,), INK, 1)
    else:
        for c in range(3):
            sx = gx0 + 20 + c * (x1 - x0 - 60) / 3.0
            cv.rect(sx, base - 90, sx + 60, base - 20, (30, 30, 36, 255), INK, 2)
            cv.rect(sx + 4, base - 86, sx + 56, base - 26, (60, 140, 220, 255))
            cv.rect(sx + 20, base - 20, sx + 40, base - 10, (60, 60, 66, 255))
    cv.poly([(gx0 + 20, y1 - 10), (gx0 + 70, gy0 + 6), (gx0 + 100, gy0 + 6), (gx0 + 50, y1 - 10)], (255, 255, 255, 70))


def _mall(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(255, 246, 220, 0))
    rnd = random.Random(243)
    cv.rect(0, 0, LW, M_F, (230, 232, 236, 255))
    for x in range(0, LW, 135):                                                         # the glass roof
        cv.erase([(x + 8, 0), (x + 127, 0), (x + 127, 180), (x + 8, 180)])
        cv.rect(x, 0, x + 8, 190, (150, 156, 166, 255), INK, 1)
    cv.rect(0, 180, LW, 214, (170, 176, 186, 255), INK, 2)
    for i, (name, col, goods) in enumerate((("SALE 50%", (210, 40, 60), "clothes"), ("SHOES", (40, 100, 200), "shoes"),
                                           ("GADGETS", (30, 150, 100), "gadgets"))):
        x0 = 30 + i * 345
        _shopfront(cv, x0, 240, x0 + 330, UP_FLOOR - 70, name, col, goods, rnd)
        _shopfront(cv, x0, UP_FLOOR + 50, x0 + 330, M_F, name if i != 1 else "FOOD COURT",
                   col if i != 1 else (230, 120, 30), ("shoes", "gadgets", "clothes")[i], rnd)
    cv.rect(0, UP_FLOOR - 10, LW, UP_FLOOR + 30, (240, 242, 246, 255), INK, 3)        # the upper floor's edge
    cv.rect(0, UP_FLOOR - 90, LW, UP_FLOOR - 10, (200, 230, 240, 90))                # glass railing
    cv.line([(0, UP_FLOOR - 92), (LW, UP_FLOOR - 92)], (180, 186, 196, 255), 6)
    for x in range(0, LW, 120):
        cv.line([(x, UP_FLOOR - 90), (x, UP_FLOOR - 10)], (180, 186, 196, 255), 3)
    (ax, ay), (bx, by) = ESC                                                             # the escalator
    cv.poly([(ax - 70, ay), (ax + 40, ay), (bx + 40, by), (bx - 70, by)], (120, 126, 136, 255), INK, 3)
    cv.poly([(ax - 56, ay - 10), (ax + 26, ay - 10), (bx + 26, by - 10), (bx - 56, by - 10)], (70, 74, 82, 255))
    cv.line([(ax - 70, ay - 70), (bx - 70, by - 70)], (40, 40, 44, 255), 10)            # its handrails
    cv.line([(ax + 40, ay - 70), (bx + 40, by - 70)], (40, 40, 44, 255), 10)
    for px in (90, 990):                                                                 # plants
        cv.poly([(px - 40, M_F - 80), (px + 40, M_F - 80), (px + 30, M_F), (px - 30, M_F)], (200, 120, 80, 255),
                INK, 2)
        _leaves(cv, 14, px - 80, px + 80, M_F - 260, M_F - 80, 40, ((40, 120, 60), (110, 170, 80)), px)
    _floor_tiles(cv, (540, 760), M_F, (240, 240, 242), (226, 228, 232), step=150, grow=1.24,
                 grout=(200, 204, 210, 255))
    for (x0, x1) in ((300, 420), (640, 760)):                                            # reflections on the floor
        cv.poly([(x0, M_F + 10), (x1, M_F + 10), (x1 + 60, LH), (x0 - 60, LH)], (255, 255, 255, 40))
    for (x0, x1) in ((140, 260), (560, 680)):
        light.poly([(x0, 0), (x1, 0), (x1 + 160, 1600), (x0 + 160, 1600)], (255, 246, 220, 36))
    light.blur(30)
    return cv, light


def _mall_life(k):
    """fn: the escalator's steps moving up, and shoppers passing behind the railing upstairs."""
    (ax, ay), (bx, by) = ESC
    rnd = random.Random(247)
    walkers = [(rnd.uniform(0, 1), rnd.choice((1, -1)), rnd.uniform(0.5, 1.0),
                rnd.choice(((220, 60, 80), (60, 120, 200), (250, 200, 60), (80, 160, 100), (40, 40, 44))))
               for _ in range(5)]

    def fn(_im, t):
        cv = Cv(k, fill=(70, 74, 82, 0))
        for i in range(12):
            u = ((i + t * 0.8) / 12.0) % 1.0
            x = ax + (bx - ax) * u
            y = ay + (by - ay) * u
            cv.line([(x - 54, y - 10), (x + 24, y - 10)], (170, 176, 186, 255), 3)
        for (u0, d, sp, col) in walkers:
            x = ((u0 + d * t * 0.03 * sp) % 1.2) * LW * 1.0 - 60
            y = UP_FLOOR - 16
            cv.ell(x, y - 130, 16, 18, (200, 160, 130, 200))
            cv.poly([(x - 22, y - 110), (x + 22, y - 110), (x + 18, y - 30), (x - 18, y - 30)], col + (200,))
            sw = math.sin(t * 6 * sp) * 8
            cv.line([(x - 6, y - 30), (x - 6 + sw, y)], (60, 60, 70, 200), 6)
            cv.line([(x + 6, y - 30), (x + 6 - sw, y)], (60, 60, 70, 200), 6)
        cv.blur(1.5)
        return cv.im
    return fn


def _mall_front(k):
    cv = Cv(k, fill=(220, 60, 90, 0), blend=True)
    cv.poly([(-40, 1680), (220, 1680), (240, 1960), (-40, 1960)], (220, 60, 90, 255))   # shopping bags
    cv.line([(30, 1680), (80, 1600), (150, 1680)], (40, 40, 44, 255), 8)
    cv.poly([(160, 1740), (380, 1740), (390, 1960), (150, 1960)], (250, 200, 60, 255))
    cv.blur(9)
    return cv


def mall_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    sky = _mall_sky(0.5 * s)
    st, light = _mall(kr, kg)
    fg = _mall_front(0.5 * s)
    back = [
        Layer(sky.im, 0.5 * s, 0.15, None, "sky"),
        Layer(st.im, kr, 1.0, None, "set"),
        Layer(light.im, kg, 1.0, None, "sunlight", mode="screen"),
        Layer(_blank(0.5 * s), 0.5 * s, 1.0, _mall_life(0.5 * s), "life"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return Layered(back, front, light={"ambient": [252, 252, 255], "dir": 1, "vignette": 0.2}, horizon=760,
                   ground=M_F)


# ------------------------------------------------------------------ cinema
SCREEN = (130, 150, 950, 740)
CIN_F = 1310


def _movie_frames(k):
    """The film on the screen: a few shots, each with its light (drawn once; the layer picks one)."""
    x0, y0, x1, y1 = SCREEN
    shots = []

    def new():
        cv = Cv(k, fill=(255, 255, 255, 0))
        return cv
    c = new()                                                                           # mountains and the sun
    c.rect(x0, y0, x1, y1, (150, 190, 236, 255))
    c.poly([(x0 + 60, y1 - 40), (x0 + 300, y0 + 200), (x0 + 480, y1 - 120), (x0 + 620, y0 + 150),
            (x1 - 40, y1 - 40)], (90, 120, 190, 255))
    c.ell(x1 - 160, y0 + 120, 50, 50, (255, 230, 140, 255))
    shots.append((c, (160, 200, 255)))
    c = new()                                                                           # the hero at sunset
    c.rect(x0, y0, x1, y1, (250, 150, 90, 255))
    c.rect(x0, y1 - 160, x1, y1, (90, 50, 60, 255))
    c.ell((x0 + x1) / 2, y1 - 160, 120, 120, (255, 220, 140, 255))
    c.rect((x0 + x1) / 2 - 40, y1 - 420, (x0 + x1) / 2 + 40, y1 - 160, (40, 24, 30, 255))
    c.ell((x0 + x1) / 2, y1 - 450, 36, 40, (40, 24, 30, 255))
    shots.append((c, (255, 170, 110)))
    c = new()                                                                           # an explosion
    c.rect(x0, y0, x1, y1, (60, 40, 40, 255))
    for i, (r, col) in enumerate(((260, (250, 120, 40)), (190, (255, 180, 60)), (110, (255, 240, 170)))):
        c.ell((x0 + x1) / 2, (y0 + y1) / 2 + 40, r * 1.3, r, col + (255,))
    shots.append((c, (255, 150, 70)))
    c = new()                                                                           # two people, a song
    c.rect(x0, y0, x1, y1, (120, 200, 150, 255))
    c.rect(x0, y1 - 200, x1, y1, (250, 220, 90, 255))
    for (px, col) in ((x0 + 300, (220, 50, 80)), (x0 + 520, (60, 90, 170))):
        c.ell(px, y1 - 360, 34, 38, (220, 170, 130, 255))
        c.poly([(px - 50, y1 - 320), (px + 50, y1 - 320), (px + 60, y1 - 120), (px - 60, y1 - 120)], col + (255,))
    shots.append((c, (170, 255, 190)))
    out = []
    for c, glow in shots:
        g = Cv(k, fill=glow + (0,))
        g.poly([(x0, y1), (x1, y1), (LW + 200, CIN_F), (-200, CIN_F)], glow + (40,))      # its light on the hall
        g.blur(40)
        g.im.alpha_composite(c.im)
        out.append(g.im)
    return out


def _cinema(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(220, 230, 255, 0))
    rnd = random.Random(251)
    fill_tex(cv, [(0, 0), (LW, 0), (LW, CIN_F), (0, CIN_F)], [(0, (40, 30, 46)), (CIN_F, (30, 24, 34))], seed=253,
             cell=40, lo=0.92, hi=1.06)
    x0, y0, x1, y1 = SCREEN
    cv.rect(x0 - 14, y0 - 14, x1 + 14, y1 + 14, (20, 20, 24, 255), INK, 2)
    cv.rect(x0, y0, x1, y1, (24, 24, 28, 255))
    for (a, b, sgn) in ((20, x0 - 10, 1), (x1 + 10, LW - 20, -1)):                       # red curtains
        cv.rect(a, 60, b, 900, (130, 20, 36, 255), INK, 2)
        for x in range(int(a) + 16, int(b), 22):
            cv.line([(x, 64), (x, 896)], (100, 14, 28, 255), 4)
    cv.rect(0, 40, LW, 70, (90, 14, 26, 255))
    quad_image(cv, sign_image("EXIT", (30, 150, 70), (255, 255, 255), 300, 130), [(960, 940), (1050, 940), (1050, 980),
                                                                               (960, 980)])
    light.glow(1005, 960, 80, (60, 255, 120), 60)
    # rows of seats with heads, far to near
    for r, (y, n, w, hs) in enumerate(((1020, 13, 76, 22), (1120, 12, 84, 25), (1230, 11, 94, 28))):
        x = (LW - n * w) / 2.0
        for i in range(n):
            sx = x + i * w
            cv.poly([(sx + 4, y + 60), (sx + w - 4, y + 60), (sx + w - 8, y - 10), (sx + 8, y - 10)],
                    (150, 24, 40, 255), INK, 2)
            cv.ell(sx + w / 2, y - 10, (w - 16) / 2, 10, (170, 30, 48, 255), INK, 1)
            if rnd.random() < 0.75:                                                     # somebody sitting
                cv.ell(sx + w / 2, y - 20 - hs, hs, hs * 1.1, (20, 18, 24, 255))
                cv.ell(sx + w / 2, y - 6, hs * 1.4, hs * 0.6, (20, 18, 24, 255))
        cv.rect(0, y + 60, LW, y + 74, (26, 20, 30, 255))
    fill_tex(cv, [(0, CIN_F), (LW, CIN_F), (LW, LH), (0, LH)], [(CIN_F, (44, 34, 48)), (LH, (30, 24, 34))], seed=255,
             cell=20, lo=0.9, hi=1.08)
    for x in range(60, LW, 160):                                                          # step lights
        cv.ell(x, CIN_F + 10, 6, 4, (255, 220, 120, 255))
        light.glow(x, CIN_F + 10, 30, (255, 220, 120), 60)
    light.poly([(420, -40), (660, -40), (x1, y0 + 60), (x0, y0 + 60)], (220, 230, 255, 26))   # the projector's beam
    light.blur(10)
    return cv, light


def _film(k):
    frames = _movie_frames(k)

    def fn(_im, t):
        return frames[int(t / 2.6) % len(frames)]
    return fn


def _cinema_front(k):
    cv = Cv(k, fill=(220, 40, 40, 0), blend=True)
    cv.poly([(840, 1700), (1100, 1700), (1070, 1960), (870, 1960)], (240, 240, 240, 255))    # a popcorn tub
    for x in range(860, 1100, 50):
        cv.poly([(x, 1700), (x + 24, 1700), (x + 20, 1960), (x + 2, 1960)], (220, 40, 40, 255))
    for i in range(12):
        cv.ell(860 + (i * 37) % 240, 1690 - (i % 3) * 20, 22, 18, (255, 240, 200, 255))
    cv.blur(9)
    return cv


def cinema_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    st, light = _cinema(kr, kg)
    fg = _cinema_front(0.5 * s)
    back = [
        Layer(st.im, kr, 1.0, None, "set"),
        Layer(_blank(0.5 * s), 0.5 * s, 1.0, _film(0.5 * s), "film", mode="screen"),
        Layer(light.im, kg, 1.0, None, "lights", mode="screen"),
        Layer(_blank(0.3 * s), 0.3 * s, 1.0, motes(((540, 0), (540, 200), 380), 0.3 * s, n=60), "beam_dust",
              mode="screen"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return Layered(back, front, light={"ambient": [200, 200, 230], "dir": 1, "vignette": 0.45}, horizon=760,
                   ground=CIN_F)

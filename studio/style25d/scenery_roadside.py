"""The road sets with the people ON the road (2.5D): used instead of street_25d / busstop_25d when the scene has a
vehicle in it (`OBJ: auto`, `A -> ride bike`), so the auto and the people talking to its driver stand on the road
together, not on the footpath. (These are the first hand-made street and bus stop; their background traffic is in
proportion, styles.SET_AMBIENT.)
"""
import math
import random

from PIL import Image

from .scenery import Cv, Layer, Layered, fill_tex, quad_image, sign_image
from .scenery_home import _leaves
from .scenery_road import (INK, ROAD_VP, SHOPS, _flats, _shop, _tree, day_sky, electric_pole, gx, rooftops, skyline,
                           street_lamp)
from ..util import LH, LW

PATH_Y, KERB_Y, ROAD_Y = 1250, 1330, 1352
STOP_PATH = 1170


def _blank(k, fill=(0, 0, 0, 0)):
    return Image.new("RGBA", (8, 8), fill)


def footpath_and_road(cv, path_y=PATH_Y, kerb_y=KERB_Y, road_y=ROAD_Y, zebra=(40, 330), seed=12):
    """The footpath (tiles running to the vanishing point), the kerb in black and yellow, the road with its lines."""
    fill_tex(cv, [(-10, path_y), (LW + 10, path_y), (LW + 10, kerb_y), (-10, kerb_y)],
             [(path_y, (196, 190, 182)), (kerb_y, (184, 178, 170))], seed=seed, cell=18, lo=0.93, hi=1.05)
    for y in (path_y + (kerb_y - path_y) * f for f in (0.3, 0.62)):
        cv.line([(-10, y), (LW + 10, y)], (150, 146, 140, 255), 2)
    for x in range(-560, 1700, 90):
        cv.line([(gx(x, path_y, path_y), path_y), (gx(x, path_y, kerb_y), kerb_y)], (150, 146, 140, 255), 2)
    cv.line([(-10, path_y), (LW + 10, path_y)], INK, 3)
    for i, x in enumerate(range(-600, 1800, 70)):                         # kerb stones
        a, b = gx(x, kerb_y, kerb_y), gx(x + 70, kerb_y, kerb_y)
        c, d = gx(x + 70, kerb_y, road_y), gx(x, kerb_y, road_y)
        cv.poly([(a, kerb_y), (b, kerb_y), (c, road_y), (d, road_y)],
                ((236, 196, 50) if i % 2 else (40, 40, 44)) + (255,))
    cv.line([(-10, kerb_y), (LW + 10, kerb_y)], INK, 2)
    cv.line([(-10, road_y), (LW + 10, road_y)], INK, 2)
    fill_tex(cv, [(-10, road_y), (LW + 10, road_y), (LW + 10, LH), (-10, LH)],
             [(road_y, (96, 98, 104)), (LH, (74, 76, 82))], seed=seed + 1, cell=10, lo=0.88, hi=1.08)
    rnd = random.Random(seed)
    for _ in range(9):                                                    # patches and cracks
        x, y = rnd.uniform(0, LW), rnd.uniform(road_y + 40, LH - 40)
        w = rnd.uniform(40, 120)
        cv.ell(x, y, w, w * 0.18, (60, 62, 68, 90))
        cv.line([(x - w * 0.6, y), (x - w * 0.1, y + 6), (x + w * 0.5, y - 4)], (50, 52, 58, 120), 2)
    cv.rect(-10, road_y + 14, LW + 10, road_y + 22, (236, 200, 60, 255))  # the yellow edge line
    for x in range(-40, LW + 40, 150):                                    # the dashed middle line
        cv.rect(x, 1488, x + 80, 1500, (240, 240, 236, 255))
    if zebra:
        for xs in range(zebra[0], zebra[1], 64):
            pts = [(xs, road_y + 24), (xs + 36, road_y + 24), (gx(xs + 36, road_y, LH), LH), (gx(xs, road_y, LH), LH)]
            cv.poly(pts, (236, 236, 232, 235))
    cv.ell(820, 1830, 96, 24, (70, 70, 74, 255), (40, 40, 44, 255), 3)    # a manhole
    for i in range(-3, 4):
        cv.line([(820 + i * 22, 1812), (820 + i * 22, 1848)], (52, 52, 56, 255), 2)



OPEN_SIGN = (300, 1020, 380, 1052)


def _street(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(255, 236, 190, 0), blend=True)
    for i, sh in enumerate(SHOPS):
        _shop(cv, *sh, seed=20 + i)
    for (x0, x1, _t, _c, _s, _sc, _a, _k) in SHOPS:                      # the awnings' shade on the footpath
        cv.poly([(x0 + 10, PATH_Y), (x1 - 4, PATH_Y), (x1 - 40, PATH_Y + 40), (x0 - 20, PATH_Y + 40)], (30, 24, 30, 46))
    footpath_and_road(cv)
    electric_pole(cv, 150, 1300, wires_to=((LW + 40, 300), (LW + 40, 380), (700, 500)))
    street_lamp(cv, 960, 1300)
    # a green dustbin and a parked cycle on the footpath
    cv.poly([(452, 1300), (500, 1300), (494, 1232), (458, 1232)], (60, 140, 80, 255), INK, 2)
    cv.rect(450, 1222, 502, 1234, (40, 110, 60, 255), INK, 2)
    for wx in (620, 720):
        cv.ell(wx, 1290, 34, 34, None, (40, 40, 44, 255), 5)
    cv.line([(620, 1290), (668, 1236), (720, 1290), (690, 1290), (668, 1236), (650, 1222)], (200, 50, 50, 255), 5)
    cv.line([(700, 1220), (690, 1290)], (200, 50, 50, 255), 5)
    cv.line([(690, 1214), (716, 1214)], (40, 40, 44, 255), 5)
    cv.line([(640, 1216), (664, 1216)], (40, 40, 44, 255), 6)
    # the shadow of the pole on the road (sun from the upper right)
    cv.poly([(140, 1352), (162, 1352), (20, 1920), (-20, 1920)], (20, 20, 30, 40))
    # sunlight
    for (x0, x1) in ((560, 760), (820, 1000)):
        light.poly([(x0 + 300, -40), (x1 + 300, -40), (x1 - 100, 1360), (x0 - 100, 1360)], (255, 236, 190, 40))
    light.glow(680, 1160, 160, (255, 210, 140), 70)                       # the sweet shop's warm bulbs
    light.blur(30)
    return cv, light


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
    cv = Cv(k, fill=(200, 60, 60, 0), blend=True)
    # a red and white barricade in the bottom-left corner
    for i in range(7):
        cols = (220, 50, 50) if i % 2 == 0 else (245, 245, 240)
        cv.poly([(-60 + i * 50, 1780), (-10 + i * 50, 1780), (-40 + i * 50, 1840), (-90 + i * 50, 1840)], cols + (255,))
    cv.rect(-60, 1840, 290, 1856, (60, 60, 64, 255))
    cv.rect(20, 1856, 40, 1940, (60, 60, 64, 255))
    cv.rect(220, 1856, 240, 1940, (60, 60, 64, 255))
    # a traffic cone bottom-right
    cv.poly([(990, 1660), (1020, 1660), (1070, 1900), (940, 1900)], (250, 120, 30, 255))
    for y in (1730, 1800):
        w = (y - 1660) / 240.0 * 65 + 15
        cv.poly([(1005 - w, y), (1005 + w, y), (1005 + w + 5, y + 26), (1005 - w - 5, y + 26)], (250, 250, 246, 255))
    cv.rect(910, 1890, 1100, 1930, (240, 100, 30, 255))
    cv.blur(9)
    return cv


def street_road_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    sky = day_sky(0.5 * s)
    far = skyline(0.5 * s)
    mid = rooftops(0.6 * s)
    st, light = _street(kr, kg)
    fg = _street_front(0.5 * s)
    back = [
        Layer(sky.im, 0.5 * s, 0.0, None, "sky"),
        Layer(far.im, 0.5 * s, 0.18, None, "far"),
        Layer(mid.im, 0.6 * s, 0.5, None, "mid"),
        Layer(st.im, kr, 1.0, None, "set"),
        Layer(light.im, kg, 1.0, None, "sunlight", mode="screen"),
        Layer(_blank(0.4 * s), 0.4 * s, 1.0, _open_sign(0.4 * s), "open_sign", mode="screen"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return Layered(back, front, light={"ambient": [255, 250, 242], "dir": 1, "vignette": 0.24},
                   horizon=ROAD_VP[1], ground=KERB_Y)



def _busstop(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(255, 236, 190, 0), blend=True)
    rnd = random.Random(41)
    _flats(cv, rnd)
    fill_tex(cv, [(-10, STOP_PATH), (LW + 10, STOP_PATH), (LW + 10, KERB_Y), (-10, KERB_Y)],
             [(STOP_PATH, (200, 194, 186)), (KERB_Y, (186, 180, 172))], seed=43, cell=18, lo=0.93, hi=1.05)
    for x in range(-560, 1700, 90):
        cv.line([(gx(x, STOP_PATH, STOP_PATH), STOP_PATH), (gx(x, STOP_PATH, KERB_Y), KERB_Y)],
                (156, 150, 144, 255), 2)
    for y in (1210, 1260, 1300):
        cv.line([(-10, y), (LW + 10, y)], (156, 150, 144, 255), 2)
    cv.line([(-10, STOP_PATH), (LW + 10, STOP_PATH)], INK, 3)
    footpath_and_road(cv, path_y=KERB_Y - 2, zebra=None, seed=44)
    _tree(cv, 930, 380, 1240)
    # the shelter: back panel with an ad, bench, pillars, roof
    sx0, sx1 = 90, 730
    cv.rect(sx0 + 20, 930, sx1 - 20, 1190, (170, 210, 230, 150), INK, 3)  # glass back
    quad_image(cv, sign_image("CHAI BREAK", (250, 196, 60), (120, 40, 30), 700, 600),
               [(150, 960), (330, 960), (330, 1120), (150, 1120)])
    cv.ell(240, 1080, 26, 18, (240, 240, 240, 255), INK, 2)               # a cup on the ad
    cv.rect(400, 1120, 700, 1144, (60, 120, 160, 255), INK, 2)            # the bench
    cv.rect(400, 1080, 700, 1096, (60, 120, 160, 255), INK, 2)
    for bx in (420, 680):
        cv.rect(bx - 5, 1144, bx + 5, 1200, (80, 80, 86, 255))
    for px in (sx0 + 10, 380, sx1 - 10):                                  # back posts
        cv.rect(px - 7, 905, px + 7, 1200, (120, 126, 134, 255), INK, 2)
    for px in (sx0 - 10, sx1 + 10):                                       # front posts (on the kerb side)
        cv.rect(px - 10, 905, px + 10, 1305, (110, 116, 124, 255), INK, 3)
    cv.poly([(sx0 - 40, 900), (sx1 + 40, 900), (sx1 + 10, 930), (sx0 + 10, 930)], (60, 110, 120, 255), INK, 3)
    cv.rect(sx0 - 40, 846, sx1 + 40, 900, (40, 150, 160, 255), INK, 3)    # the roof's front with its name
    quad_image(cv, sign_image("BUS STOP  21  45  102", (40, 150, 160), (255, 255, 255), 1400, 120),
               [(sx0 - 20, 852), (sx1 + 20, 852), (sx1 + 20, 894), (sx0 - 20, 894)])
    cv.poly([(sx0 - 40, 846), (sx1 + 40, 846), (sx1 + 20, 832), (sx0 - 20, 832)], (70, 170, 180, 255), INK, 2)
    cv.poly([(sx0, 1305), (sx1, 1305), (sx1 + 30, 1325), (sx0 - 30, 1325)], (20, 20, 30, 50))   # shade
    # the bus stop sign
    px = 840
    cv.rect(px - 7, 640, px + 7, 1310, (120, 126, 134, 255), INK, 2)
    cv.ell(px, 640, 58, 58, (40, 90, 190, 255), INK, 3)
    cv.ell(px, 640, 50, 50, None, (250, 250, 250, 255), 4)
    cv.rect(px - 28, 616, px + 28, 664, (250, 250, 250, 255))               # a little bus
    cv.rect(px - 22, 622, px + 22, 640, (40, 90, 190, 255))
    cv.ell(px - 16, 666, 7, 7, (40, 40, 44, 255))
    cv.ell(px + 16, 666, 7, 7, (40, 40, 44, 255))
    quad_image(cv, sign_image("BUS STOP", (40, 90, 190), (255, 255, 255), 600, 160),
               [(px - 70, 710), (px + 70, 710), (px + 70, 750), (px - 70, 750)])
    for (x0, x1) in ((300, 520), (640, 900)):
        light.poly([(x0 + 300, -40), (x1 + 300, -40), (x1 - 100, 1340), (x0 - 100, 1340)], (255, 236, 190, 38))
    light.blur(30)
    return cv, light


def _leaf_shadows_road(k, region=(760, 1180, 1100, 1330), seed=47):
    """fn: the tree's dappled shade on the footpath, moving a little in the breeze."""
    rnd = random.Random(seed)
    spots = [(rnd.uniform(region[0], region[2]), rnd.uniform(region[1], region[3]), rnd.uniform(14, 34),
              rnd.uniform(0, 6.28)) for _ in range(26)]

    def fn(_im, t):
        cv = Cv(k, fill=(20, 30, 20, 0))
        for (x, y, r, ph) in spots:
            cv.ell(x + math.sin(t * 0.9 + ph) * 6, y, r, r * 0.4, (20, 30, 20, 60))
        cv.blur(4)
        return cv.im
    return fn


def _busstop_front(k):
    cv = Cv(k, fill=(60, 120, 60, 0), blend=True)
    _leaves(cv, 22, 820, 1180, -120, 160, 60, ((36, 96, 44), (70, 140, 60)), 53)   # branches over the top
    cv.poly([(-60, 1700), (60, 1700), (80, 1940), (-60, 1940)], (240, 240, 236, 255))     # a milestone corner
    cv.poly([(-60, 1640), (40, 1640), (60, 1700), (-60, 1700)], (240, 196, 50, 255))
    cv.blur(9)
    return cv


def busstop_road_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    sky = day_sky(0.5 * s, sun=(200, 260), seed=7)
    far = skyline(0.5 * s, seed=9, tops=(330, 540))
    st, light = _busstop(kr, kg)
    fg = _busstop_front(0.5 * s)
    back = [
        Layer(sky.im, 0.5 * s, 0.0, None, "sky"),
        Layer(far.im, 0.5 * s, 0.2, None, "far"),
        Layer(st.im, kr, 1.0, None, "set"),
        Layer(light.im, kg, 1.0, None, "sunlight", mode="screen"),
        Layer(_blank(0.4 * s), 0.4 * s, 1.0, _leaf_shadows_road(0.4 * s), "leaf_shade"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return Layered(back, front, light={"ambient": [255, 250, 240], "dir": -1, "vignette": 0.24},
                   horizon=ROAD_VP[1], ground=KERB_Y)



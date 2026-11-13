"""Hand-made 2.5D sets for the open places, painted like the gali and the jungle.

beach_25d          a beach by day: the sea far away with a sailboat and an island, waves rolling in (their own
                   layer), gulls, the foam washing up the sand, a palm tree, a striped umbrella with a deck chair, a
                   sandcastle with a bucket, a beach ball blurred in front.
desert_25d         a desert in the heat: a huge pale sun, far dunes with a camel caravan walking along the ridge,
                   nearer dunes with wind ripples, cacti, rocks, a dry bush, a tumbleweed rolling by now and then.
mountain_road_25d  a mountain road: snowy peaks far away, pine slopes in the mist, an eagle circling, the crash barrier,
                   the road with its traffic behind the people, who stand on the gravel shoulder by the PAHADPUR
                   milestone and a curve sign; a pine branch in front.
cricket_ground_25d a cricket ground: the stands full of people (a Mexican wave runs through them), floodlights, the
                   score board, boundary boards (SIXER, CHAUKA), the striped outfield, the pitch with its stumps, a bat
                   and a ball blurred in front.
school_ground_25d  a school ground: the DESIPUR PUBLIC SCHOOL building with its gate and bell, a big tree with a
                   platform round it, a flag fluttering, a football, a bench, chalk lines, leaves falling.
(mountain road, cricket ground and school ground have writing on them, so a reverse shot never mirrors them.)
"""
import math
import random

from PIL import Image, ImageDraw

from .scenery import Cv, Layer, Layered, birds, catenary, fill_tex, mix, mul, quad_image, sign_image, vgrad
from .scenery_home import _leaves
from .scenery_road import day_sky, gx, skyline
from ..util import LH, LW

INK = (44, 38, 40, 255)


def _blank(k, fill=(0, 0, 0, 0)):
    return Image.new("RGBA", (8, 8), fill)


def _drift_clouds(k, n=4, seed=401, y0=150, y1=500):
    """fn: a few soft clouds drifting across the sky (over the sky picture)."""
    rnd = random.Random(seed)
    clouds = [(rnd.uniform(0, 1), rnd.uniform(y0, y1), rnd.uniform(140, 240), rnd.uniform(0.5, 1.0))
              for _ in range(n)]
    puffs = {}

    def puff(w):
        if w not in puffs:
            c = Cv(k, w=w * 1.4, h=w * 0.5, fill=(255, 255, 255, 0))
            r = random.Random(int(w))
            for _ in range(7):
                c.ell(w * 0.7 + r.uniform(-w * 0.4, w * 0.4), w * 0.27 + r.uniform(-8, 8), w * 0.28, w * 0.14,
                      (255, 255, 255, 220))
            c.blur(2.0)
            puffs[w] = c.im
        return puffs[w]

    def fn(im, t):
        out = im.copy()
        for (u, y, w, sp) in clouds:
            p = puff(int(w))
            x = int((((u + t * 0.006 * sp) % 1.3) * LW - 0.2 * LW - w * 0.7) * k)
            y = int((y - w * 0.27) * k)
            a, b = max(0, -x), min(p.width, out.width - x)                   # (clipped at the edges)
            c, d = max(0, -y), min(p.height, out.height - y)
            if b > a and d > c:
                out.alpha_composite(p.crop((a, c, b, d)), dest=(x + a, y + c))
        return out
    return fn


# ------------------------------------------------------------------ beach
SEA_TOP, SHORE = 900, 1180


def _sea_far(k):
    cv = Cv(k, blend=True)
    cv.im = vgrad(k, [(0, (70, 150, 226)), (600, (140, 200, 240)), (SEA_TOP, (210, 234, 246)),
                      (SEA_TOP + 1, (40, 120, 190)), (SHORE, (70, 170, 210)), (LH, (70, 170, 210))])
    cv.d = ImageDraw.Draw(cv.im)
    g = Cv(k, fill=(255, 244, 210, 0))
    g.glow(820, 300, 280, (255, 246, 214), 130)
    g.blur(24)
    cv.over(g)
    cv.ell(820, 300, 58, 58, (255, 250, 228, 255))
    cv.poly([(80, SEA_TOP), (160, 860), (240, 845), (330, 872), (400, SEA_TOP)], (110, 150, 140, 255))   # an island
    _leaves(cv, 8, 140, 300, 820, 860, 20, ((80, 130, 90), (110, 150, 110)), 403)
    cv.poly([(700, SEA_TOP - 4), (760, SEA_TOP - 4), (750, SEA_TOP + 6), (710, SEA_TOP + 6)], (240, 240, 236, 255))
    cv.poly([(730, SEA_TOP - 6), (730, SEA_TOP - 70), (764, SEA_TOP - 10)], (250, 250, 246, 255))   # a sailboat
    for y in range(SEA_TOP + 10, SHORE, 24):                                            # glints on the water
        for x in range(0, LW, 90):
            cv.line([(x + (y * 7) % 60, y), (x + (y * 7) % 60 + 26, y)], (200, 230, 246, 140), 2)
    cv.blur(1.2)
    return cv


def _waves(k):
    """fn: rows of waves rolling in toward the shore, foam on their crests."""
    def fn(_im, t):
        cv = Cv(k, fill=(240, 250, 255, 0))
        for i in range(6):
            u = ((i + t * 0.25) / 6.0) % 1.0
            y = SEA_TOP + 20 + u * (SHORE - SEA_TOP - 30)
            a = int(200 * min(1.0, u * 2.5) * (1.0 - u * 0.4))
            pts = [(x, y + 6 * math.sin(x / 60.0 + t * 1.5 + i)) for x in range(-20, LW + 40, 30)]
            cv.line(pts, (245, 252, 255, a), 3 + 4 * u)
        return cv.im
    return fn


def _beach(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(255, 240, 200, 0))
    rnd = random.Random(405)
    fill_tex(cv, [(-20, SHORE), (LW + 20, SHORE), (LW + 20, LH), (-20, LH)],
             [(SHORE, (214, 196, 150)), (SHORE + 70, (236, 220, 176)), (LH, (240, 222, 172))], seed=407, cell=10,
             lo=0.92, hi=1.06)
    for _ in range(40):                                                                  # shells and pebbles
        x, y = rnd.uniform(0, LW), rnd.uniform(SHORE + 80, LH)
        cv.ell(x, y, rnd.uniform(4, 9), rnd.uniform(3, 6), rnd.choice(((250, 230, 220), (200, 170, 140),
                                                                       (240, 200, 190))) + (255,))
    for i in range(10):                                                                  # footprints
        x, y = 360 + i * 30, 1300 + i * 50
        cv.ell(x + (i % 2) * 22, y, 9, 14, (200, 180, 136, 255))
    # the palm tree
    pts = [(120, 1420), (110, 1200), (120, 980), (160, 760), (210, 600)]
    for (a, b) in zip(pts, pts[1:]):
        cv.line([a, b], (140, 100, 64, 255), 34)
    for i in range(1, len(pts)):
        cv.line([(pts[i][0] - 18, pts[i][1]), (pts[i][0] + 18, pts[i][1] + 8)], (110, 76, 46, 255), 4)
    for ang in (-2.6, -2.1, -1.5, -0.9, -0.4, 0.2):
        ex, ey = 210 + 260 * math.cos(ang), 600 + 160 * math.sin(ang) + 120
        cv.line(catenary(210, 600, ex, ey, -40 if ey < 600 else 30, 16), (60, 140, 70, 255), 22)
    for (cx, cy) in ((196, 630), (226, 636), (210, 652)):
        cv.ell(cx, cy, 16, 16, (110, 80, 40, 255), INK, 1)
    # the umbrella and a deck chair
    ux, uy = 820, 1000
    cv.line([(ux, uy), (ux + 20, 1440)], (90, 90, 96, 255), 8)
    for i in range(8):
        a, b = ux - 220 + i * 55, ux - 220 + (i + 1) * 55
        cv.poly([(ux, uy - 70), (a, uy + 20), (b, uy + 20)], ((230, 60, 60), (250, 250, 246))[i % 2] + (255,))
    cv.line([(ux - 220, uy + 20), (ux + 220, uy + 20)], INK, 2)
    cv.poly([(700, 1330), (900, 1330), (960, 1240), (760, 1240)], (60, 120, 200, 255), INK, 2)
    cv.poly([(760, 1240), (800, 1240), (740, 1120), (700, 1120)], (60, 120, 200, 255), INK, 2)
    for lx in (710, 890):
        cv.line([(lx, 1330), (lx - 10, 1400)], (190, 170, 130, 255), 6)
    cv.ell(820, 1420, 230, 30, (150, 130, 90, 80))
    # a sandcastle with a bucket and spade
    sx = 520
    cv.poly([(sx - 90, 1330), (sx + 90, 1330), (sx + 70, 1270), (sx - 70, 1270)], (220, 196, 140, 255), INK, 2)
    for dx in (-60, 0, 60):
        cv.rect(sx + dx - 22, 1220 - (20 if dx == 0 else 0), sx + dx + 22, 1272, (226, 202, 146, 255), INK, 2)
    cv.line([(sx, 1200), (sx, 1160)], (90, 90, 96, 255), 3)
    cv.poly([(sx, 1160), (sx + 30, 1170), (sx, 1180)], (230, 60, 60, 255))
    cv.poly([(620, 1330), (680, 1330), (690, 1270), (610, 1270)], (250, 200, 40, 255), INK, 2)
    light.glow(820, 300, 500, (255, 236, 190), 40)
    light.blur(20)
    return cv, light


def _foam(k):
    """fn: the foam washing up the sand and sliding back."""
    def fn(_im, t):
        cv = Cv(k, fill=(250, 252, 255, 0))
        reach = 30 + 40 * (0.5 + 0.5 * math.sin(t * 0.9))
        pts = [(x, SHORE + reach + 8 * math.sin(x / 80.0 + t)) for x in range(-20, LW + 40, 30)]
        cv.poly([(-20, SHORE - 4)] + pts + [(LW + 40, SHORE - 4)], (120, 190, 220, 120))
        cv.line(pts, (250, 252, 255, 230), 6)
        return cv.im
    return fn


def _beach_front(k):
    cv = Cv(k, fill=(240, 60, 60, 0), blend=True)
    cv.ell(980, 1850, 130, 130, (240, 60, 60, 255))                                       # a beach ball
    cv.poly([(980, 1720), (1040, 1850), (980, 1980), (920, 1850)], (250, 250, 246, 255))
    cv.poly([(880, 1760), (980, 1850), (880, 1940)], (250, 200, 40, 255))
    _leaves(cv, 8, -80, 200, -60, 160, 70, ((50, 120, 50), (90, 160, 70)), 409)
    cv.blur(9)
    return cv


def beach_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    far = _sea_far(0.5 * s)
    st, light = _beach(kr, kg)
    fg = _beach_front(0.5 * s)
    back = [
        Layer(far.im, 0.5 * s, 0.05, birds(0.5 * s, n=5, seed=411, y0=420, y1=760), "sea"),
        Layer(_blank(0.5 * s), 0.5 * s, 0.6, _waves(0.5 * s), "waves"),
        Layer(st.im, kr, 1.0, None, "set"),
        Layer(_blank(0.5 * s), 0.5 * s, 1.0, _foam(0.5 * s), "foam"),
        Layer(light.im, kg, 1.0, None, "sunlight", mode="screen"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return Layered(back, front, light={"ambient": [255, 250, 236], "dir": 1, "vignette": 0.2}, horizon=SEA_TOP,
                   ground=SHORE)


# ------------------------------------------------------------------ desert
D_GROUND = 1180


def _desert_sky(k):
    cv = Cv(k, blend=True)
    cv.im = vgrad(k, [(0, (250, 180, 110)), (500, (252, 210, 140)), (900, (252, 232, 180)), (LH, (252, 232, 180))])
    cv.d = ImageDraw.Draw(cv.im)
    g = Cv(k, fill=(255, 250, 220, 0))
    g.glow(700, 330, 360, (255, 250, 220), 150)
    g.blur(30)
    cv.over(g)
    cv.ell(700, 330, 90, 90, (255, 248, 210, 255))
    for (base, amp, col, seed) in ((900, 60, (236, 196, 140), 1), (960, 80, (226, 182, 120), 2)):
        pts = [(-20, LH)]
        for x in range(-20, LW + 60, 40):
            pts.append((x, base - amp * (0.5 + 0.5 * math.sin(x / 160.0 + seed * 2.0))))
        pts.append((LW + 60, LH))
        cv.poly(pts, col + (255,))
    cv.blur(1.6)
    return cv


def _caravan(k):
    """fn: a camel caravan walking slowly along the far ridge."""
    def fn(_im, t):
        cv = Cv(k, fill=(110, 70, 50, 0))
        for i in range(4):
            x = ((t * 6.0 + i * 70) % (LW + 400)) - 200
            y = 900 - 60 * (0.5 + 0.5 * math.sin(x / 160.0 + 2.0)) + 4
            bob = math.sin(t * 3 + i) * 2
            col = (130, 86, 56, 220)
            cv.ell(x, y - 26 + bob, 22, 12, col)
            cv.ell(x + 2, y - 38 + bob, 9, 9, col)
            cv.line([(x + 18, y - 30 + bob), (x + 30, y - 46 + bob)], col, 5)
            cv.ell(x + 33, y - 48 + bob, 6, 4, col)
            for lx in (-14, -6, 8, 16):
                cv.line([(x + lx, y - 18 + bob), (x + lx + math.sin(t * 3 + lx) * 3, y)], col, 3)
            if i == 0:
                cv.line([(x - 40, y - 20), (x - 40, y)], col, 4)
                cv.ell(x - 40, y - 26, 5, 6, col)
        return cv.im
    return fn


def _dunes_mid(k):
    cv = Cv(k, blend=True)
    pts = [(-20, LH)]
    for x in range(-20, LW + 60, 40):
        pts.append((x, 1060 - 110 * (0.5 + 0.5 * math.sin(x / 210.0 + 0.8))))
    pts.append((LW + 60, LH))
    cv.poly(pts, (238, 200, 140, 255))
    for j in range(8):                                                                    # wind ripples
        y0 = 1000 + j * 26
        cv.line([(x, y0 + 8 * math.sin(x / 50.0 + j)) for x in range(-20, LW + 40, 20)], (220, 180, 120, 160), 2)
    cv.blur(1.0)
    return cv


def _cactus(cv, x, base, h, arms):
    cv.rect(x - 22, base - h, x + 22, base, (80, 150, 80, 255), INK, 3)
    cv.ell(x, base - h, 22, 22, (80, 150, 80, 255), INK, 3)
    for (side, ay, ah) in arms:
        ax = x + side * 22
        cv.rect(min(ax, ax + side * 50), base - ay - 14, max(ax, ax + side * 50), base - ay + 14, (80, 150, 80, 255),
                INK, 2)
        ex = ax + side * 50
        cv.rect(ex - 14, base - ay - ah, ex + 14, base - ay + 14, (80, 150, 80, 255), INK, 2)
        cv.ell(ex, base - ay - ah, 14, 14, (80, 150, 80, 255), INK, 2)
    for i in range(int(h / 30)):
        cv.line([(x - 10, base - 20 - i * 30), (x - 10, base - 34 - i * 30)], (50, 110, 60, 255), 2)
        cv.line([(x + 10, base - 20 - i * 30), (x + 10, base - 34 - i * 30)], (50, 110, 60, 255), 2)


def _desert(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(255, 240, 200, 0))
    rnd = random.Random(421)
    pts = [(-20, LH)]
    for x in range(-20, LW + 60, 40):
        pts.append((x, D_GROUND - 30 * math.sin(x / 260.0)))
    pts.append((LW + 60, LH))
    cv.poly(pts, (242, 210, 150, 255))
    fill_tex(cv, [(-20, D_GROUND + 30), (LW + 20, D_GROUND + 30), (LW + 20, LH), (-20, LH)],
             [(D_GROUND, (242, 212, 152)), (LH, (236, 200, 136))], seed=423, cell=12, lo=0.94, hi=1.05)
    for j in range(14):                                                                   # ripples
        y0 = D_GROUND + 60 + j * 52
        cv.line([(x, y0 + 10 * math.sin(x / 70.0 + j * 1.3)) for x in range(-20, LW + 40, 20)],
                (222, 186, 124, 200), 3)
    _cactus(cv, 170, 1300, 420, [(-1, 160, 110), (1, 240, 90)])
    _cactus(cv, 880, 1250, 280, [(1, 120, 80)])
    for (x, y, r) in ((640, 1300, 60), (700, 1310, 34), (380, 1420, 40)):                # rocks
        cv.ell(x, y, r, r * 0.6, (180, 150, 120, 255), INK, 2)
        cv.ell(x - r * 0.3, y - r * 0.2, r * 0.3, r * 0.15, (210, 186, 156, 255))
    for i in range(14):                                                                   # a dry bush
        a = -math.pi + i * math.pi / 13
        cv.line([(980, 1420), (980 + 70 * math.cos(a), 1420 + 50 * math.sin(a))], (150, 110, 70, 255), 3)
    for _ in range(20):
        x, y = rnd.uniform(0, LW), rnd.uniform(D_GROUND + 40, LH)
        cv.ell(x, y, 4, 2, (200, 166, 110, 255))
    light.glow(700, 330, 700, (255, 244, 210), 50)
    light.blur(20)
    return cv, light


def _tumbleweed(k):
    """fn: a tumbleweed rolling across now and then."""
    rnd = random.Random(427)
    twigs = [(rnd.uniform(0, 6.28), rnd.uniform(0.4, 1.0)) for _ in range(26)]

    def fn(_im, t):
        cv = Cv(k, fill=(150, 110, 70, 0))
        ph = (t - 3.0) % 14.0
        if t < 3.0 or ph > 6.0:
            return cv.im
        x = -100 + ph / 6.0 * (LW + 200)
        y = 1460 - abs(math.sin(ph * 3.0)) * 40
        r = 50
        rot = ph * 4.0
        for (a, l) in twigs:
            aa = a + rot
            cv.line([(x + r * 0.2 * math.cos(aa + 1), y + r * 0.2 * math.sin(aa + 1)),
                     (x + r * l * math.cos(aa), y + r * l * math.sin(aa))], (150, 110, 70, 230), 3)
        cv.ell(x, y, r, r, None, (140, 100, 60, 200), 3)
        cv.ell(x, 1470, r, 10, (180, 140, 90, 80))
        return cv.im
    return fn


def _desert_front(k):
    cv = Cv(k, fill=(180, 150, 120, 0), blend=True)
    cv.ell(60, 1900, 220, 120, (190, 160, 128, 255))                                       # a big rock
    cv.blur(10)
    return cv


def desert_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    sky = _desert_sky(0.5 * s)
    mid = _dunes_mid(0.6 * s)
    st, light = _desert(kr, kg)
    fg = _desert_front(0.5 * s)
    back = [
        Layer(sky.im, 0.5 * s, 0.0, None, "sky"),
        Layer(_blank(0.5 * s), 0.5 * s, 0.1, _caravan(0.5 * s), "caravan"),
        Layer(mid.im, 0.6 * s, 0.45, None, "dunes"),
        Layer(st.im, kr, 1.0, None, "set"),
        Layer(light.im, kg, 1.0, None, "sunlight", mode="screen"),
        Layer(_blank(0.5 * s), 0.5 * s, 1.0, _tumbleweed(0.5 * s), "tumbleweed"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return Layered(back, front, light={"ambient": [255, 244, 222], "dir": 1, "vignette": 0.22}, horizon=900,
                   ground=D_GROUND)


# ------------------------------------------------------------------ mountain road
MR_RAIL, MR_ROAD, MR_EDGE = 1196, 1206, 1500      # barrier, road, near edge


def _peaks(k):
    cv = Cv(k, blend=True)
    cv.im = vgrad(k, [(0, (80, 150, 226)), (500, (140, 196, 240)), (1000, (210, 230, 246)), (LH, (210, 230, 246))])
    cv.d = ImageDraw.Draw(cv.im)
    for (pts, col) in (([(-60, 1100), (260, 520), (520, 1100)], (150, 160, 190)),
                       ([(240, 1100), (680, 380), (1160, 1100)], (124, 132, 170))):
        cv.poly(pts, col + (255,), INK, 2)
        (ax, ay), (px, py), (bx, by) = pts
        f = 0.22
        cv.poly([(px, py), (px + (bx - px) * f, py + (by - py) * f), (px + (bx - px) * f * 0.6, py + (by - py) * f * 1.1),
                 (px, py + (by - py) * f * 0.8), (px + (ax - px) * f * 0.7, py + (ay - py) * f * 1.05),
                 (px + (ax - px) * f, py + (ay - py) * f)], (250, 252, 255, 255))
        cv.line([(px, py), (px + (bx - px) * 0.6, py + (by - py) * 0.6)], mul(col, 0.85) + (255,), 4)
    cv.rect(-20, 940, LW + 20, 1100, (200, 220, 236, 120))                                 # mist at their feet
    cv.blur(2.2)
    return cv


def _pine(cv, x, base, h, col):
    cv.rect(x - 5, base - 20, x + 5, base, (90, 64, 40, 255))
    for i in range(4):
        w = h * (0.42 - i * 0.08)
        y = base - 20 - i * h * 0.22
        cv.poly([(x - w, y), (x + w, y), (x, y - h * 0.38)], mul(col, 1.0 + i * 0.05) + (255,))


def _slopes(k):
    cv = Cv(k, blend=True)
    cv.poly([(-20, 1200), (-20, 980), (300, 1040), (700, 1000), (1100, 1060), (1100, 1200)], (70, 120, 80, 255))
    rnd = random.Random(431)
    for _ in range(46):
        x = rnd.uniform(-20, LW + 20)
        _pine(cv, x, rnd.uniform(1040, 1200), rnd.uniform(80, 150), mix((40, 90, 60), (60, 120, 70), rnd.random()))
    cv.rect(-20, 1100, LW + 20, 1200, (190, 214, 220, 90))
    cv.blur(1.2)
    return cv


def _mountain_road(k, kg):
    """The far side: grass and pines at the valley's edge, the crash barrier, the road (its traffic passes here)."""
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(255, 240, 200, 0))
    fill_tex(cv, [(-20, 1140), (LW + 20, 1140), (LW + 20, MR_ROAD), (-20, MR_ROAD)],
             [(1140, (110, 150, 90)), (MR_ROAD, (100, 136, 80))], seed=433, cell=14, lo=0.9, hi=1.08)
    rnd = random.Random(435)
    for _ in range(40):                                                                    # grass tufts
        x, y = rnd.uniform(0, LW), rnd.uniform(1150, MR_RAIL - 4)
        cv.line([(x, y), (x - 3, y - 10)], (80, 120, 60, 255), 2)
        cv.line([(x, y), (x + 3, y - 9)], (80, 120, 60, 255), 2)
    _pine(cv, 980, 1180, 300, (40, 100, 60))
    _pine(cv, 70, 1170, 240, (40, 96, 58))
    for x in range(20, LW, 110):                                                           # the crash barrier
        cv.rect(x - 5, MR_RAIL - 22, x + 5, MR_ROAD + 4, (150, 154, 160, 255), INK, 1)
    cv.rect(-20, MR_RAIL - 28, LW + 20, MR_RAIL, (200, 204, 210, 255), INK, 2)
    cv.line([(-20, MR_RAIL - 14), (LW + 20, MR_RAIL - 14)], (150, 154, 160, 255), 3)
    for x in range(40, LW, 220):
        cv.rect(x, MR_RAIL - 24, x + 14, MR_RAIL - 4, (240, 60, 50, 255))
    fill_tex(cv, [(-20, MR_ROAD), (LW + 20, MR_ROAD), (LW + 20, MR_EDGE), (-20, MR_EDGE)],
             [(MR_ROAD, (106, 108, 114)), (MR_EDGE, (86, 88, 94))], seed=437, cell=10, lo=0.88, hi=1.08)
    cv.rect(-20, MR_ROAD + 8, LW + 20, MR_ROAD + 14, (236, 236, 230, 255))                 # the edge lines
    cv.rect(-20, MR_EDGE - 16, LW + 20, MR_EDGE - 8, (236, 236, 230, 255))
    ym = (MR_ROAD + MR_EDGE) / 2.0
    for x in range(-40, LW + 40, 170):                                                     # the yellow middle line
        cv.rect(x, ym - 5, x + 90, ym + 5, (240, 200, 60, 255))
    light.poly([(-200, -40), (300, -40), (700, 1500), (100, 1500)], (255, 240, 200, 30))
    light.blur(30)
    return cv, light


def _mountain_near(k):
    """The near side: the gravel shoulder the people stand on, the PAHADPUR milestone and a curve sign (drawn after
    the traffic, which passes behind them)."""
    cv = Cv(k, blend=True)
    fill_tex(cv, [(-20, MR_EDGE), (LW + 20, MR_EDGE), (LW + 20, LH), (-20, LH)],
             [(MR_EDGE, (168, 150, 124)), (LH, (150, 132, 106))], seed=439, cell=8, lo=0.86, hi=1.1)
    cv.line([(-20, MR_EDGE), (LW + 20, MR_EDGE)], INK, 2)
    rnd = random.Random(441)
    for _ in range(60):                                                                    # pebbles and grass
        x, y = rnd.uniform(0, LW), rnd.uniform(MR_EDGE + 10, LH)
        if rnd.random() < 0.6:
            cv.ell(x, y, rnd.uniform(3, 8), rnd.uniform(2, 5), (130, 116, 96, 255))
        else:
            for j in range(4):
                cv.line([(x, y), (x + (j - 1.5) * 7, y - rnd.uniform(16, 30))], (90, 130, 60, 255), 3)
    mx, mb = 170, 1610                                                                     # the milestone
    cv.poly([(mx - 66, mb), (mx + 66, mb), (mx + 66, mb - 170), (mx, mb - 220), (mx - 66, mb - 170)],
            (250, 250, 246, 255), INK, 3)
    cv.poly([(mx - 66, mb - 170), (mx, mb - 220), (mx + 66, mb - 170), (mx + 66, mb - 144), (mx - 66, mb - 144)],
            (240, 200, 40, 255), INK, 2)
    quad_image(cv, sign_image("PAHADPUR 12", (250, 250, 246), (30, 30, 30), 600, 260, border=(250, 250, 246)),
               [(mx - 60, mb - 130), (mx + 60, mb - 130), (mx + 60, mb - 64), (mx - 60, mb - 64)])
    cv.ell(mx, mb + 4, 90, 12, (60, 50, 40, 70))
    sx, sb = 960, 1590                                                                     # a curve sign
    cv.rect(sx - 7, 1290, sx + 7, sb, (120, 124, 130, 255), INK, 1)
    cv.poly([(sx, 1180), (sx + 76, 1256), (sx, 1332), (sx - 76, 1256)], (250, 200, 40, 255), INK, 3)
    cv.line([(sx - 22, 1290), (sx - 22, 1250), (sx + 6, 1228), (sx + 22, 1228)], (30, 30, 30, 255), 8)
    cv.poly([(sx + 22, 1214), (sx + 40, 1228), (sx + 22, 1242)], (30, 30, 30, 255))
    return cv


def _eagle(k):
    def fn(_im, t):
        cv = Cv(k, fill=(50, 40, 40, 0))
        a = t * 0.35
        x, y = 640 + 220 * math.cos(a), 360 + 70 * math.sin(a)
        flap = math.sin(t * 2.0) * 6
        cv.line([(x - 40, y - 6 + flap), (x - 14, y - 2), (x, y + 4), (x + 14, y - 2), (x + 40, y - 6 + flap)],
                (50, 40, 40, 230), 5)
        return cv.im
    return fn


def _mountain_front(k):
    cv = Cv(k, fill=(40, 90, 50, 0), blend=True)
    for i in range(6):                                                                     # a pine branch
        y = -40 + i * 60
        cv.line([(LW + 60, y), (LW - 180 + i * 10, y + 70)], (40, 90, 50, 255), 30)
    cv.blur(9)
    return cv


def mountain_road_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    far = _peaks(0.5 * s)
    mid = _slopes(0.6 * s)
    st, light = _mountain_road(kr, kg)
    near = _mountain_near(kr)
    fg = _mountain_front(0.5 * s)
    back = [
        Layer(far.im, 0.5 * s, 0.06, _drift_clouds(0.5 * s, seed=439), "peaks"),
        Layer(_blank(0.5 * s), 0.5 * s, 0.12, _eagle(0.5 * s), "eagle"),
        Layer(mid.im, 0.6 * s, 0.4, None, "slopes"),
        Layer(st.im, kr, 1.0, None, "set"),
        Layer(light.im, kg, 1.0, None, "sunlight", mode="screen"),
        Layer(near.im, kr, 1.0005, None, "shoulder"),                 # (after the traffic, which is at d = 1)
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return Layered(back, front, light={"ambient": [248, 252, 255], "dir": -1, "vignette": 0.22}, horizon=1000,
                   ground=MR_EDGE)


# ------------------------------------------------------------------ cricket ground
STANDS = (560, 860)
CG_VP = (540, 840)


def _stadium(k):
    cv = Cv(k, blend=True)
    cv.im = vgrad(k, [(0, (70, 140, 220)), (500, (140, 196, 240)), (LH, (200, 226, 246))])
    cv.d = ImageDraw.Draw(cv.im)
    for x in (120, 960):                                                                   # floodlights
        cv.line([(x, 860), (x, 250)], (150, 154, 160, 255), 10)
        cv.rect(x - 70, 190, x + 70, 260, (200, 204, 210, 255), INK, 2)
        for r in range(2):
            for c in range(4):
                cv.ell(x - 52 + c * 35, 208 + r * 32, 12, 12, (255, 252, 230, 255))
    cv.poly([(-20, 470), (LW + 20, 470), (LW + 20, STANDS[1] + 20), (-20, STANDS[1] + 20)], (170, 176, 186, 255),
            INK, 2)
    cv.rect(-20, 440, LW + 20, 480, (220, 60, 60, 255), INK, 2)                            # the roof's edge
    cv.rect(380, 300, 700, 430, (30, 40, 36, 255), INK, 3)                                 # the score board
    quad_image(cv, sign_image("186/4", (30, 40, 36), (250, 210, 60), 600, 220, border=(30, 40, 36)),
               [(400, 316), (680, 316), (680, 410), (400, 410)])
    cv.line([(470, 430), (470, 470)], (90, 90, 96, 255), 6)
    cv.line([(610, 430), (610, 470)], (90, 90, 96, 255), 6)
    cv.blur(1.0)
    return cv


def _crowd(k):
    """fn: the people in the stands, a Mexican wave running through them."""
    rnd = random.Random(441)
    people = []
    y = STANDS[0] + 10
    row = 0
    while y < STANDS[1]:
        x = -10 + (row % 2) * 12
        while x < LW + 10:
            people.append((x, y, rnd.choice(((220, 60, 60), (60, 110, 200), (250, 200, 60), (240, 240, 236),
                                             (80, 160, 90), (150, 90, 170))), rnd.uniform(0, 1)))
            x += 24
        y += 30
        row += 1

    def fn(_im, t):
        cv = Cv(k, fill=(200, 160, 120, 0))
        wave = (t * 260.0) % (LW + 600) - 300
        for (x, y, col, j) in people:
            up = max(0.0, 1.0 - abs(x - wave) / 120.0)
            dy = -12 * up + math.sin(t * 6 + j * 9) * 1.2
            cv.ell(x, y + dy, 9, 10, col + (255,))
            cv.ell(x, y - 13 + dy, 6, 6, (210, 170, 130, 255))
            if up > 0.5:
                cv.line([(x - 6, y - 10 + dy), (x - 9, y - 26 + dy)], (210, 170, 130, 255), 3)
                cv.line([(x + 6, y - 10 + dy), (x + 9, y - 26 + dy)], (210, 170, 130, 255), 3)
        cv.blur(0.6)
        return cv.im
    return fn


def _cricket(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(255, 244, 210, 0))
    top = STANDS[1] + 20
    cv.rect(-20, top, LW + 20, top + 50, (40, 60, 120, 255), INK, 2)                       # boundary boards
    for i, (text, col) in enumerate((("SIXER", (220, 60, 60)), ("CHAUKA", (40, 120, 200)), ("BOUNDARY", (240, 160, 30)),
                                     ("OUT!", (40, 150, 90)))):
        x0 = 10 + i * 270
        quad_image(cv, sign_image(text, col, (255, 255, 255), 700, 130), [(x0, top + 6), (x0 + 250, top + 6),
                                                                         (x0 + 250, top + 44), (x0, top + 44)])
    g0 = top + 50
    for i in range(40):                                                                    # mowing stripes
        ya = CG_VP[1] + (g0 - CG_VP[1]) * (1.18 ** i)
        yb = CG_VP[1] + (g0 - CG_VP[1]) * (1.18 ** (i + 1))
        if ya > LH:
            break
        cv.rect(-20, ya, LW + 20, min(yb, LH + 10), ((96, 170, 86), (84, 154, 76))[i % 2] + (255,))
    cv.line(catenary(-20, g0 + 30, LW + 20, g0 + 30, 0), (250, 250, 250, 255), 4)           # the rope
    # the pitch, running toward us, with its creases and the far stumps
    pts = [(gx(470, 1000, 1000, CG_VP), 1000), (gx(610, 1000, 1000, CG_VP), 1000),
           (gx(610, 1000, LH, CG_VP), LH), (gx(470, 1000, LH, CG_VP), LH)]
    fill_tex(cv, pts, [(1000, (214, 186, 130)), (LH, (200, 170, 114))], seed=443, cell=10, lo=0.92, hi=1.07)
    for y in (1040, 1080):
        cv.line([(gx(440, 1000, y, CG_VP), y), (gx(640, 1000, y, CG_VP), y)], (250, 250, 246, 255), 3)
    for dx in (-12, 0, 12):
        cv.rect(540 + dx - 3, 990, 540 + dx + 3, 1040, (250, 246, 230, 255), INK, 1)
    cv.line([(524, 990), (556, 990)], (250, 246, 230, 255), 3)
    cv.rect(-20, 960, 140, 1010, (250, 250, 250, 255), INK, 2)                             # sight screen bits
    light.poly([(-200, -40), (400, -40), (800, 1800), (200, 1800)], (255, 244, 210, 26))
    light.blur(30)
    return cv, light


def _cricket_front(k):
    cv = Cv(k, fill=(220, 190, 140, 0), blend=True)
    cv.poly([(1000, 1960), (1080, 1960), (1060, 1500), (1020, 1500)], (230, 200, 150, 255))   # a bat
    cv.rect(1026, 1380, 1052, 1500, (40, 40, 44, 255))
    cv.ell(80, 1860, 70, 70, (200, 30, 40, 255))                                             # the ball
    cv.blur(9)
    return cv


def cricket_ground_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    far = _stadium(0.5 * s)
    st, light = _cricket(kr, kg)
    fg = _cricket_front(0.5 * s)
    back = [
        Layer(far.im, 0.5 * s, 0.15, None, "stadium"),
        Layer(_blank(0.5 * s), 0.5 * s, 0.15, _crowd(0.5 * s), "crowd"),
        Layer(st.im, kr, 1.0, None, "set"),
        Layer(light.im, kg, 1.0, None, "sunlight", mode="screen"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return Layered(back, front, light={"ambient": [255, 252, 240], "dir": 1, "vignette": 0.2}, horizon=CG_VP[1],
                   ground=STANDS[1] + 70)


# ------------------------------------------------------------------ school ground
SG_F = 1220
FLAG = (900, 560)
TREE = (150, 1220)


def _school(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(255, 240, 200, 0))
    x0, x1, top = 300, 1100, 520
    cv.rect(x0, top, x1, SG_F, (246, 216, 130, 255), INK, 3)                               # the building
    cv.rect(x0 - 20, top - 30, x1 + 20, top, (200, 90, 60, 255), INK, 3)
    cv.rect(x0 - 10, 860, x1 + 10, 880, (200, 90, 60, 255), INK, 2)
    for row, y in enumerate((570, 910)):
        for x in range(x0 + 40, x1 - 60, 130):
            if row == 1 and 620 < x < 760:
                continue
            cv.rect(x, y, x + 70, y + 150, (60, 110, 190, 255), INK, 2)
            cv.line([(x + 35, y), (x + 35, y + 150)], (40, 80, 150, 255), 3)
            cv.rect(x - 6, y + 150, x + 76, y + 160, (230, 200, 120, 255), INK, 1)
    for x in range(x0, x1, 22):                                                            # first-floor railing
        cv.line([(x, 820), (x, 860)], (60, 110, 190, 255), 3)
    cv.line([(x0, 820), (x1, 820)], (60, 110, 190, 255), 4)
    cv.rect(630, 940, 750, SG_F, (120, 80, 50, 255), INK, 3)                               # the door
    quad_image(cv, sign_image("DESIPUR PUBLIC SCHOOL", (40, 80, 160), (255, 255, 255), 1400, 160),
               [(420, 440), (980, 440), (980, 486), (420, 486)])
    cv.line([(780, 920), (780, 960)], (60, 60, 64, 255), 3)                                # the bell
    cv.poly([(762, 960), (798, 960), (792, 990), (768, 990)], (200, 160, 60, 255), INK, 2)
    cv.rect(x0 - 20, SG_F - 30, x1 + 20, SG_F, (220, 200, 170, 255), INK, 2)
    fx, fy = FLAG                                                                          # the flag pole
    cv.rect(fx - 6, fy, fx + 6, SG_F + 20, (200, 204, 210, 255), INK, 1)
    cv.ell(fx, fy, 10, 10, (230, 200, 80, 255), INK, 1)
    # the ground
    fill_tex(cv, [(-20, SG_F), (LW + 20, SG_F), (LW + 20, LH), (-20, LH)],
             [(SG_F, (214, 184, 136)), (LH, (200, 166, 116))], seed=451, cell=14, lo=0.9, hi=1.08)
    rnd = random.Random(453)
    for _ in range(60):
        x, y = rnd.uniform(0, LW), rnd.uniform(SG_F + 10, LH)
        cv.ell(x, y, rnd.uniform(3, 7), rnd.uniform(2, 4), (180, 150, 110, 255))
    vp = (540, 860)
    for x in (100, 980):                                                                   # chalk lines
        cv.line([(gx(x, SG_F + 60, SG_F + 60, vp), SG_F + 60), (gx(x, SG_F + 60, LH, vp), LH)], (246, 244, 236, 200),
                5)
    cv.line([(-20, SG_F + 60), (LW + 20, SG_F + 60)], (246, 244, 236, 200), 5)
    cv.ell(540, 1500, 200, 50, None, (246, 244, 236, 200), 5)
    # the big tree with its platform
    tx, tb = TREE
    cv.rect(tx - 140, tb - 10, tx + 140, tb + 50, (200, 190, 176, 255), INK, 3)
    cv.poly([(tx - 30, tb - 10), (tx + 30, tb - 10), (tx + 20, 600), (tx + 80, 500), (tx + 60, 490), (tx, 560),
             (tx - 30, 470), (tx - 50, 480), (tx - 20, 600)], (110, 80, 56, 255), INK, 3)
    _leaves(cv, 90, -120, 420, 180, 640, 56, ((50, 120, 50), (100, 166, 70)), 455)
    _leaves(cv, 34, -60, 360, 200, 420, 40, ((110, 170, 80), (150, 200, 100)), 456)
    cv.rect(420, 1300, 640, 1320, (60, 110, 160, 255), INK, 2)                             # a bench
    for lx in (430, 620):
        cv.rect(lx, 1320, lx + 10, 1370, (60, 60, 66, 255))
    cv.ell(860, 1420, 34, 34, (250, 250, 250, 255), INK, 2)                                # a football
    cv.poly([(860, 1406), (872, 1414), (868, 1428), (852, 1428), (848, 1414)], (40, 40, 44, 255))
    cv.ell(tx, tb + 52, 260, 30, (60, 50, 30, 60))
    light.poly([(-200, -40), (300, -40), (800, 1700), (200, 1700)], (255, 240, 200, 30))
    light.blur(30)
    return cv, light


def _school_life(k):
    """fn: the school's flag fluttering, leaves falling from the big tree."""
    rnd = random.Random(457)
    leaves = [(rnd.uniform(-60, 360), rnd.uniform(0, 1), rnd.uniform(0.6, 1.2), rnd.uniform(0, 6.28)) for _ in range(6)]
    fx, fy = FLAG

    def fn(_im, t):
        cv = Cv(k, fill=(60, 110, 190, 0))
        pts_top = [(fx + 6 + i * 20, fy + 4 + 8 * math.sin(t * 5 - i * 0.8)) for i in range(8)]
        pts_bot = [(x, y + 80) for (x, y) in pts_top]
        cv.poly(pts_top + pts_bot[::-1], (60, 110, 190, 255), INK, 2)
        cx = sum(p[0] for p in pts_top) / 8.0
        cy = sum(p[1] for p in pts_top) / 8.0 + 40
        cv.ell(cx, cy, 18, 18, (250, 220, 80, 255))
        for (x0, ph, sp, rot) in leaves:
            u = (t * 0.07 * sp + ph) % 1.0
            x = x0 + math.sin(t * 1.5 + rot) * 40
            y = 500 + u * 900
            a = t * 2 + rot
            cv.poly([(x + 12 * math.cos(a), y + 6 * math.sin(a)), (x - 12 * math.cos(a), y - 6 * math.sin(a)),
                     (x + 4 * math.sin(a), y + 10)], (110, 160, 60, 220))
        return cv.im
    return fn


def _school_front(k):
    cv = Cv(k, fill=(60, 120, 50, 0), blend=True)
    _leaves(cv, 14, -100, 220, -80, 180, 70, ((40, 100, 40), (90, 150, 60)), 459)
    cv.blur(9)
    return cv


def school_ground_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    sky = day_sky(0.5 * s, sun=(980, 200), seed=461)
    far = skyline(0.5 * s, seed=463, tops=(560, 760), base=1250)
    st, light = _school(kr, kg)
    fg = _school_front(0.5 * s)
    back = [
        Layer(sky.im, 0.5 * s, 0.0, birds(0.5 * s, n=4, seed=465, y0=200, y1=420), "sky"),
        Layer(far.im, 0.5 * s, 0.18, None, "far"),
        Layer(st.im, kr, 1.0, None, "set"),
        Layer(light.im, kg, 1.0, None, "sunlight", mode="screen"),
        Layer(_blank(0.5 * s), 0.5 * s, 1.0, _school_life(0.5 * s), "life"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return Layered(back, front, light={"ambient": [255, 250, 238], "dir": -1, "vignette": 0.22}, horizon=860,
                   ground=SG_F)

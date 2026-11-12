"""Hand-made 2.5D sets for work places, painted like the kitchen and the living room.

office_25d   an office by day: a wide glass window onto the city (its own far layer) with a blind half down and
             its striped sunlight on the carpet, the TEAM AWESOME board with a chart and a clock, two desks with
             monitors that change, a water cooler, a plant, panel lights, a blurred mug and papers in front.
meeting_25d  a meeting room: a glass wall onto the open office (far layer), a wall TV with this quarter's targets,
             a long table with its chairs along the back wall, pendant lamps, a laptop's glow, a blurred chair in
             front. (Both have writing on them, so a reverse shot never mirrors them.)
"""
import math
import random

from PIL import Image

from .scenery import Cv, Layer, Layered, fill_tex, mix, motes, mul, quad_image, sign_image, vgrad
from .scenery_home import _box, _clock, _floor_tiles, _leaves, _shadow
from ..util import LH, LW

INK = (46, 40, 44, 255)
ALU = (176, 184, 194)
OFFICE_VP = (540, 800)
OFFICE_FLOOR = 1290
OFFICE_WIN = (560, 300, 1040, 980)
MONITORS = [(150, 860, 330, 990), (720, 860, 900, 990)]


# ------------------------------------------------------------------ shared pieces
def _city(k, seed=4, top=520):
    """Far layer: the city by day through a big office window (sky, two rows of towers, haze), blurred."""
    cv = Cv(k)
    cv.im = vgrad(k, [(0, (86, 150, 222)), (500, (132, 186, 238)), (900, (206, 226, 242)), (LH, (214, 228, 238))])
    from PIL import ImageDraw
    cv.d = ImageDraw.Draw(cv.im)
    rnd = random.Random(seed)
    for (cx, cy, w) in ((680, 380, 180), (930, 330, 140)):
        for _ in range(6):
            cv.ell(cx + rnd.uniform(-w / 2, w / 2), cy + rnd.uniform(-14, 14), w * 0.3, w * 0.18, (255, 255, 255, 220))
    for row, (shade, y0, y1, wmin, wmax) in enumerate((((150, 170, 196), top, top + 140, 70, 110),
                                                         ((96, 120, 156), top + 90, top + 200, 80, 140))):
        x = 520
        while x < LW + 40:
            w = rnd.uniform(wmin, wmax)
            t = rnd.uniform(y0, y1)
            col = mix(shade, (210, 220, 236), rnd.uniform(0, 0.25))
            cv.rect(x, t, x + w, 1300, col + (255,))
            if rnd.random() < 0.3:
                cv.rect(x + w * 0.4, t - 40, x + w * 0.45, t, mul(col, 0.8) + (255,))      # antenna
            for wy in range(int(t) + 14, 1100, 30 if row else 26):
                for wx in range(int(x) + 8, int(x + w) - 12, 20):
                    lit = rnd.random() < 0.15
                    cv.rect(wx, wy, wx + 11, wy + 16, ((250, 236, 170) if lit else mul(col, 1.18)) + (255,))
            x += w + rnd.uniform(2, 14)
    cv.rect(0, 1100, LW, LH, (176, 186, 196, 255))
    cv.rect(0, 960, LW, 1100, (196, 204, 214, 180))                                    # haze at the bottom
    cv.blur(3.0)
    return cv


def _plant(cv, x, y_floor, h=300, w=150, seed=5):
    cv.poly([(x - w * 0.34, y_floor - 120), (x + w * 0.34, y_floor - 120), (x + w * 0.27, y_floor),
             (x - w * 0.27, y_floor)], (196, 120, 80, 255), INK, 3)
    cv.rect(x - w * 0.38, y_floor - 132, x + w * 0.38, y_floor - 116, (214, 140, 96, 255), INK, 2)
    _leaves(cv, 22, x - w * 0.6, x + w * 0.6, y_floor - 120 - h, y_floor - 120, 40, ((46, 116, 58), (112, 172, 78)), seed)


def _poster(cv, img, x0, y0, x1, y1):
    quad_image(cv, img, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def _screens(k, rects, palette, seed=3, glow=True):
    """fn for a dynamic layer: monitor screens whose picture changes now and then (a sheet, a chart, a call) and
    their soft glow on the wall."""
    def fn(_im, t):
        cv = Cv(k, fill=(160, 200, 255, 0))
        for i, (x0, y0, x1, y1) in enumerate(rects):
            n = int(t / 3.2 + i * 1.7)
            rnd = random.Random(seed * 31 + n * 7 + i)
            base = palette[n % len(palette)]
            if glow:
                cv.glow((x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) * 0.9, base, 26)
            cv.rect(x0 + 8, y0 + 8, x1 - 8, y1 - 8, base + (120,))
            kind = n % 3
            if kind == 0:                                          # a spreadsheet
                for r in range(5):
                    yy = y0 + 18 + r * 20
                    cv.rect(x0 + 16, yy, x0 + 16 + rnd.uniform(40, x1 - x0 - 40), yy + 8, (255, 255, 255, 150))
            elif kind == 1:                                        # a bar chart
                for b in range(5):
                    h = rnd.uniform(20, y1 - y0 - 36)
                    bx = x0 + 18 + b * (x1 - x0 - 30) / 5.0
                    cv.rect(bx, y1 - 14 - h, bx + 18, y1 - 14, (255, 255, 255, 170))
            else:                                                  # a video call: two faces
                for b in range(2):
                    cx = x0 + (x1 - x0) * (0.3 + 0.4 * b)
                    cv.ell(cx, (y0 + y1) / 2 - 6, 16, 18, (255, 220, 190, 170))
                    cv.ell(cx, y1 - 18, 26, 14, (255, 255, 255, 120))
            ph = (t * 1.3 + i) % 1.0                               # a cursor blinking
            if ph < 0.5:
                cv.rect(x1 - 30, y1 - 26, x1 - 24, y1 - 14, (255, 255, 255, 200))
        cv.blur(0.6)
        return cv.im
    return fn


def _chair_back(cv, cx, top, bottom, w=110, col=(40, 40, 48)):
    """An office chair seen from behind, standing at a desk (only the backrest and the seat show)."""
    cv.poly([(cx - w / 2, top + 20), (cx - w / 2 + 10, top), (cx + w / 2 - 10, top), (cx + w / 2, top + 20),
             (cx + w / 2 - 6, bottom - 40), (cx - w / 2 + 6, bottom - 40)], col + (255,), INK, 3)
    cv.line([(cx - w / 2 + 18, top + 22), (cx + w / 2 - 18, top + 22)], mul(col, 1.6) + (255,), 3)
    cv.rect(cx - w * 0.6, bottom - 44, cx + w * 0.6, bottom - 22, mul(col, 1.2) + (255,), INK, 3)
    cv.rect(cx - 6, bottom - 22, cx + 6, bottom + 30, (120, 120, 128, 255))
    for dx in (-44, 0, 44):
        cv.line([(cx, bottom + 30), (cx + dx, bottom + 44)], (60, 60, 66, 255), 6)
        cv.ell(cx + dx, bottom + 46, 7, 5, (20, 20, 24, 255))


# ------------------------------------------------------------------ office
def _office(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(255, 244, 214, 0))
    vp, F = OFFICE_VP, OFFICE_FLOOR
    fill_tex(cv, [(0, 0), (LW, 0), (LW, F), (0, F)], [(0, (226, 230, 236)), (700, (232, 236, 240)), (F, (214, 220, 228))],
             seed=8, cell=70, lo=0.97, hi=1.03)
    # ceiling with panel lights
    cv.rect(0, 0, LW, 96, (242, 244, 246, 255))
    cv.rect(0, 96, LW, 108, (200, 206, 214, 255))
    for x0 in (90, 420, 750):
        cv.rect(x0, 30, x0 + 240, 70, (252, 252, 248, 255), (190, 196, 204, 255), 3)
        light.glow(x0 + 120, 90, 240, (255, 250, 236), 40)
    # the window onto the city, aluminium frame, a blind half down
    x0, y0, x1, y1 = OFFICE_WIN
    cv.erase([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    for (a, b, c, d) in ((x0 - 18, y0 - 18, x1 + 18, y0), (x0 - 18, y1, x1 + 18, y1 + 24),
                         (x0 - 18, y0, x0, y1), (x1, y0, x1 + 18, y1)):
        cv.rect(a, b, c, d, ALU + (255,), INK, 3)
    for gx in (x0 + (x1 - x0) / 3.0, x0 + 2 * (x1 - x0) / 3.0):
        cv.rect(gx - 7, y0, gx + 7, y1, ALU + (255,), INK, 2)
    cv.rect(x0, 640, x1, 652, ALU + (255,), INK, 2)
    blind = 470
    for yy in range(y0, blind, 16):                                         # slats
        cv.rect(x0, yy, x1, yy + 12, (238, 236, 228, 255), (196, 194, 186, 255), 1)
    cv.rect(x0 - 10, blind, x1 + 10, blind + 14, (220, 218, 210, 255), INK, 2)
    cv.line([(x1 - 40, blind + 14), (x1 - 40, blind + 160)], (150, 150, 150, 255), 2)
    cv.ell(x1 - 40, blind + 166, 6, 8, (200, 200, 200, 255), INK, 1)
    cv.poly([(x0 + 4, y0 + 4), (x0 + 120, y0 + 4), (x0 + 30, y1 - 4), (x0 + 4, y1 - 4)], (255, 255, 255, 26))   # glare
    # sunlight through the glass onto the carpet: stripes of the frame, softer under the blind
    for i in range(3):
        u0, u1 = i / 3.0 + 0.02, (i + 1) / 3.0 - 0.02
        a = (x0 + (x1 - x0) * u0 - 120, 1330)
        b = (x0 + (x1 - x0) * u1 - 120, 1330)
        light.poly([a, b, (b[0] - 260, 1700), (a[0] - 260, 1700)], (255, 236, 190, 70))
    light.poly([(x0 - 40, 1310), (x1 - 40, 1310), (x1 - 300, 1340), (x0 - 300, 1340)], (255, 236, 190, 40))

    # TEAM AWESOME board: header, a chart, sticky notes, a clock
    bx0, by0, bx1, by1 = 50, 250, 480, 660
    cv.rect(bx0, by0, bx1, by1, (238, 242, 248, 255), INK, 4)
    _poster(cv, sign_image("TEAM AWESOME", (60, 86, 140), (255, 255, 255), w=860, h=110, border=(30, 40, 70)),
            bx0 + 14, by0 + 14, bx1 - 14, by0 + 70)
    cv.rect(bx0 + 30, by0 + 100, bx0 + 230, by0 + 290, (255, 255, 255, 255), INK, 3)
    for i, (h, c) in enumerate(((60, (86, 140, 220)), (110, (230, 100, 80)), (80, (110, 190, 110)), (150, (240, 190, 60)))):
        cv.rect(bx0 + 48 + i * 44, by0 + 270 - h, bx0 + 78 + i * 44, by0 + 270, c + (255,), INK, 2)
    for (sx, sy, c) in ((bx0 + 260, by0 + 110, (255, 236, 120)), (bx0 + 330, by0 + 130, (255, 170, 200)),
                        (bx0 + 270, by0 + 220, (170, 230, 255)), (bx0 + 340, by0 + 240, (190, 250, 170))):
        cv.rect(sx, sy, sx + 56, sy + 56, c + (255,), (150, 150, 150, 255), 1)
        cv.line([(sx + 8, sy + 20), (sx + 46, sy + 20)], (120, 120, 120, 255), 2)
        cv.line([(sx + 8, sy + 34), (sx + 36, sy + 34)], (120, 120, 120, 255), 2)
    _clock(cv, bx0 + 340, by0 + 340, 44, rim=(60, 70, 90))

    # two desks with monitors, a water cooler between them
    wood = (190, 150, 108)
    for (dx0, dx1) in ((40, 470), (610, 1040)):
        _box(cv, vp, dx0, dx1, 1000, 1030, wood, side=0.05)
        cv.rect(dx0 + 20, 1030, dx0 + 34, F, (130, 134, 140, 255), INK, 2)
        cv.rect(dx1 - 34, 1030, dx1 - 20, F, (130, 134, 140, 255), INK, 2)
        cv.rect(dx0 + 40, 1030, dx1 - 40, 1150, mul(wood, 0.82) + (255,), INK, 2)       # modesty panel
        _shadow(cv, (dx0 + dx1) / 2, F + 2, (dx1 - dx0) / 2, 14)
    for (mx0, my0, mx1, my1) in MONITORS:
        cv.rect(mx0, my0, mx1, my1, (26, 28, 34, 255), INK, 3)
        cv.rect(mx0 + 8, my0 + 8, mx1 - 8, my1 - 8, (40, 70, 110, 255))
        cv.rect((mx0 + mx1) / 2 - 10, my1, (mx0 + mx1) / 2 + 10, 1000, (60, 60, 66, 255))
        cv.rect((mx0 + mx1) / 2 - 44, 994, (mx0 + mx1) / 2 + 44, 1002, (60, 60, 66, 255))
        cv.rect(mx0 + 10, 1004, mx1 - 10, 1016, (230, 232, 236, 255), INK, 1)            # keyboard
    cv.rect(380, 960, 420, 1000, (250, 250, 250, 255), INK, 2)                            # a mug
    cv.ell(426, 978, 10, 12, None, INK, 2)
    cv.poly([(940, 990), (1010, 980), (1016, 998), (946, 1004)], (250, 250, 246, 255), INK, 1)   # papers
    cv.rect(960, 930, 990, 990, (90, 160, 90, 255), INK, 2)                               # a cactus in a cup
    cv.rect(952, 970, 998, 1000, (220, 120, 80, 255), INK, 2)
    # water cooler
    cv.rect(500, 980, 590, F - 6, (226, 232, 238, 255), INK, 3)
    cv.rect(512, 1060, 578, 1120, (200, 210, 220, 255), INK, 2)
    cv.ell(526, 1080, 6, 6, (70, 120, 220, 255))
    cv.ell(564, 1080, 6, 6, (220, 70, 70, 255))
    cv.poly([(508, 980), (582, 980), (572, 900), (518, 900)], (150, 200, 240, 210), INK, 3)
    cv.ell(545, 898, 30, 10, (150, 200, 240, 230), INK, 2)
    _shadow(cv, 545, F, 60, 10)
    # chairs at the desks
    _chair_back(cv, 250, 1020, 1230)
    _chair_back(cv, 820, 1020, 1230)
    _plant(cv, 50, F, h=280, w=130, seed=9)
    # carpet tiles
    _floor_tiles(cv, vp, F, (120, 132, 150), (112, 124, 142), step=120, grow=1.24, grout=(100, 110, 126, 255))
    cv.rect(0, F, LW, F + 4, (80, 88, 100, 160))
    cv.blur(0.35)
    return cv, light


def _office_front(k):
    cv = Cv(k, fill=(80, 80, 80, 0))
    cv.poly([(-40, 1800), (380, 1830), (420, LH + 40), (-40, LH + 40)], (176, 138, 98, 255))       # a desk corner
    cv.rect(160, 1700, 250, 1810, (240, 240, 240, 255))                                         # coffee mug
    cv.ell(260, 1750, 22, 28, None, (240, 240, 240, 255), 8)
    cv.poly([(280, 1790), (400, 1770), (414, 1810), (292, 1830)], (250, 250, 246, 255))         # papers
    _leaves(cv, 14, 850, LW + 60, 1640, 1960, 56, ((50, 120, 60), (120, 176, 84)), 21)        # a plant, right
    cv.blur(8)
    return cv


def office_25d(s, zmax=1.0):
    ko = s * max(1.0, zmax)
    kg = 0.32 * s
    outside = _city(0.5 * s)
    room, light = _office(ko, kg)
    fg = _office_front(0.5 * s)
    empty = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    back = [
        Layer(outside.im, 0.5 * s, 0.12, None, "outside"),
        Layer(room.im, ko, 1.0, None, "office"),
        Layer(light.im, kg, 1.0, None, "sunlight", mode="screen"),
        Layer(empty, 0.5 * s, 1.0, _screens(0.5 * s, MONITORS, [(70, 130, 220), (60, 170, 140), (120, 90, 200)]),
              "screens", mode="screen"),
        Layer(empty, 0.3 * s, 1.0, motes(((620, 560), (1000, 1300), 220), 0.3 * s), "dust", mode="screen"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return Layered(back, front, light={"ambient": [248, 250, 255], "dir": 1, "vignette": 0.22},
                   horizon=OFFICE_VP[1], ground=OFFICE_FLOOR)


# ------------------------------------------------------------------ meeting room
MEET_VP = (540, 800)
MEET_FLOOR = 1290
MEET_GLASS = (40, 300, 470, 1060)
MEET_TV = (560, 330, 1010, 620)
LAPTOPS = [(330, 1030, 430, 1090), (690, 1030, 790, 1090)]


def _open_office(k):
    """Far layer: the open office seen through the meeting room's glass wall (desks, people-less chairs, lights)."""
    cv = Cv(k)
    cv.im = vgrad(k, [(0, (236, 238, 240)), (800, (226, 230, 234)), (1060, (200, 206, 214)), (LH, (150, 160, 176))])
    from PIL import ImageDraw
    cv.d = ImageDraw.Draw(cv.im)
    for x in range(0, LW, 180):
        cv.rect(x + 20, 120, x + 150, 150, (252, 252, 248, 255))
    cv.rect(0, 360, LW, 820, (214, 220, 228, 255))
    for x in range(-40, 600, 210):                                         # a far window band, the city in it
        cv.rect(x + 40, 400, x + 190, 640, (150, 190, 230, 255))
        for bx in range(int(x) + 50, int(x) + 180, 30):
            cv.rect(bx, 520 - (bx % 70), bx + 22, 640, (110, 140, 180, 255))
    rnd = random.Random(12)
    for row, y in enumerate((900, 1010)):
        for x in range(0, 560, 140):
            cv.rect(x + 10, y, x + 130, y + 16, (190, 150, 110, 255))
            cv.rect(x + 40, y - 70, x + 100, y - 4, (30, 34, 40, 255))
            cv.rect(x + 46, y - 64, x + 94, y - 10, mix((70, 130, 200), (90, 180, 150), rnd.random()) + (255,))
            cv.rect(x + 50, y + 16, x + 90, y + 70, (50, 50, 58, 255))
    cv.blur(3.2)
    return cv


def _meeting(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(255, 236, 200, 0))
    vp, F = MEET_VP, MEET_FLOOR
    fill_tex(cv, [(0, 0), (LW, 0), (LW, F), (0, F)], [(0, (234, 230, 222)), (700, (238, 234, 226)), (F, (222, 216, 206))],
             seed=14, cell=60, lo=0.97, hi=1.03)
    cv.rect(560, 120, LW, F, (206, 178, 146, 255))                          # a wood-panelled feature wall
    for x in range(580, LW, 70):
        cv.line([(x, 120), (x, F)], (184, 154, 122, 255), 3)
    cv.rect(0, 0, LW, 96, (244, 244, 242, 255))
    cv.rect(0, 96, LW, 106, (200, 196, 190, 255))
    # the glass wall onto the open office (frosted band across it)
    x0, y0, x1, y1 = MEET_GLASS
    cv.erase([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    for (a, b, c, d) in ((x0 - 14, y0 - 14, x1 + 14, y0), (x0 - 14, y1, x1 + 14, y1 + 14),
                         (x0 - 14, y0, x0, y1), (x1, y0, x1 + 14, y1)):
        cv.rect(a, b, c, d, (90, 94, 102, 255), INK, 2)
    cv.rect((x0 + x1) / 2 - 6, y0, (x0 + x1) / 2 + 6, y1, (90, 94, 102, 255), INK, 2)
    cv.rect(x0, 700, x1, 760, (255, 255, 255, 120))
    cv.poly([(x0 + 10, y0 + 10), (x0 + 80, y0 + 10), (x0 + 20, y1 - 10), (x0 + 10, y1 - 10)], (255, 255, 255, 30))
    # the wall TV: this quarter's targets
    tx0, ty0, tx1, ty1 = MEET_TV
    cv.rect(tx0 - 8, ty0 - 8, tx1 + 8, ty1 + 8, (20, 20, 24, 255), INK, 3)
    cv.rect(tx0, ty0, tx1, ty1, (24, 40, 70, 255))
    _poster(cv, sign_image("Q3 TARGETS", (24, 40, 70), (255, 255, 255), w=700, h=90, border=(24, 40, 70)),
            tx0 + 20, ty0 + 14, tx0 + 260, ty0 + 50)
    for i, (h, c) in enumerate(((80, (90, 160, 255)), (130, (110, 210, 140)), (100, (250, 190, 70)), (190, (240, 100, 90)))):
        cv.rect(tx0 + 60 + i * 90, ty1 - 30 - h, tx0 + 120 + i * 90, ty1 - 30, c + (255,))
    cv.line([(tx0 + 40, ty1 - 30), (tx1 - 30, ty1 - 30)], (200, 210, 230, 255), 3)
    cv.line([(tx0 + 70, ty1 - 120), (tx0 + 160, ty1 - 160), (tx0 + 260, ty1 - 140), (tx0 + 380, ty1 - 230)],
            (255, 255, 255, 255), 5)
    light.glow((tx0 + tx1) / 2, (ty0 + ty1) / 2, 420, (140, 180, 255), 30)
    # pendant lamps over the table
    for lx in (330, 750):
        cv.line([(lx, 106), (lx, 620)], (60, 60, 64, 255), 3)
        cv.poly([(lx - 70, 690), (lx - 30, 620), (lx + 30, 620), (lx + 70, 690)], (50, 54, 60, 255), INK, 3)
        cv.ell(lx, 690, 70, 12, (255, 236, 180, 255), INK, 2)
        light.glow(lx, 720, 260, (255, 226, 160), 60)
        light.poly([(lx - 70, 700), (lx + 70, 700), (lx + 220, 1060), (lx - 220, 1060)], (255, 230, 170, 26))
    # the long table along the back wall, chairs behind it
    for cx in (200, 400, 640, 860):
        _chair_back(cv, cx, 930, 1110, w=120, col=(36, 38, 46))
    cv.poly([(80, 1060), (1000, 1060), (1050, 1140), (30, 1140)], (110, 72, 48, 255), INK, 4)         # table top
    cv.poly([(30, 1140), (1050, 1140), (1050, 1170), (30, 1170)], (84, 54, 36, 255), INK, 3)
    for lx in (120, 960):
        cv.rect(lx - 12, 1170, lx + 12, F, (70, 70, 76, 255), INK, 2)
    _shadow(cv, 540, F, 470, 14)
    for (lx0, ly0, lx1, ly1) in LAPTOPS:                                   # laptops open on the table
        cv.poly([(lx0, ly1), (lx1, ly1), (lx1 - 8, ly0), (lx0 + 8, ly0)], (180, 186, 194, 255), INK, 2)
        cv.rect(lx0 + 14, ly0 + 8, lx1 - 14, ly1 - 8, (60, 100, 160, 255))
        cv.poly([(lx0 - 20, ly1), (lx1 + 20, ly1), (lx1 + 30, ly1 + 14), (lx0 - 30, ly1 + 14)], (200, 204, 210, 255), INK, 2)
    for (gx, gy) in ((520, 1060), (560, 1066), (920, 1062)):              # glasses of water
        cv.rect(gx, gy - 40, gx + 22, gy, (200, 230, 250, 200), INK, 1)
    cv.rect(230, 1036, 290, 1066, (250, 250, 246, 255), INK, 1)             # a file
    _plant(cv, 1010, F, h=300, w=120, seed=17)
    # wooden floor (planks towards the vanishing point)
    fill_tex(cv, [(0, F), (LW, F), (LW, LH), (0, LH)], [(F, (170, 128, 92)), (LH, (150, 110, 78))],
             seed=15, cell=40, lo=0.94, hi=1.05)
    for x in range(-1600, 2700, 90):
        cv.line([(x, F), (vp[0] + (x - vp[0]) * (LH - vp[1]) / float(F - vp[1]), LH)], (130, 94, 64, 255), 2)
    cv.rect(0, F, LW, F + 4, (100, 70, 50, 160))
    cv.blur(0.35)
    return cv, light


def _meeting_front(k):
    cv = Cv(k, fill=(40, 40, 40, 0))
    _chair_back(cv, 140, 1580, 1980, w=300, col=(34, 36, 44))              # a chair close to the lens, left
    cv.rect(840, 1760, 900, 1860, (200, 230, 250, 200))                     # a glass of water, right
    cv.blur(9)
    return cv


def meeting_25d(s, zmax=1.0):
    ko = s * max(1.0, zmax)
    kg = 0.32 * s
    outside = _open_office(0.5 * s)
    room, light = _meeting(ko, kg)
    fg = _meeting_front(0.5 * s)
    empty = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    back = [
        Layer(outside.im, 0.5 * s, 0.14, None, "outside"),
        Layer(room.im, ko, 1.0, None, "meeting"),
        Layer(light.im, kg, 1.0, None, "lamps", mode="screen"),
        Layer(empty, 0.5 * s, 1.0, _screens(0.5 * s, [(lx0 + 14, ly0 + 8, lx1 - 14, ly1 - 8) for lx0, ly0, lx1, ly1 in LAPTOPS],
                                            [(80, 130, 210), (70, 170, 150)], seed=9, glow=False), "laptops", mode="screen"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return Layered(back, front, light={"ambient": [255, 246, 234], "dir": -1, "vignette": 0.26},
                   horizon=MEET_VP[1], ground=MEET_FLOOR)

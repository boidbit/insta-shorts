"""Procedural flat-cartoon backgrounds (kitchen, room, street, school, night road, plain)
plus support for your own PNG/JPG backgrounds."""
import math
import random

from PIL import Image, ImageDraw

from .util import LW, LH, asset_path

INK = (18, 18, 18)
BG_SS = 2


class G:
    """Tiny drawing wrapper: logical 1080x1920 coords -> supersampled canvas."""

    def __init__(self, s, w=LW, h=LH, color=(255, 255, 255), mode="RGB"):
        self.k = s * BG_SS
        self.s = s
        self.im = Image.new(mode, (int(round(w * self.k)), int(round(h * self.k))), color)
        self.d = ImageDraw.Draw(self.im)

    def _p(self, pts):
        return [(x * self.k, y * self.k) for x, y in pts]

    def rect(self, x0, y0, x1, y1, fill=None, outline=None, w=5):
        self.d.rectangle([x0 * self.k, y0 * self.k, x1 * self.k, y1 * self.k], fill=fill,
                         outline=outline, width=max(1, int(w * self.k)) if outline else 0)

    def rrect(self, x0, y0, x1, y1, r, fill=None, outline=None, w=5):
        self.d.rounded_rectangle([x0 * self.k, y0 * self.k, x1 * self.k, y1 * self.k], radius=r * self.k,
                                 fill=fill, outline=outline, width=max(1, int(w * self.k)) if outline else 0)

    def poly(self, pts, fill=None, outline=None, w=5):
        pp = self._p(pts)
        if fill is not None:
            self.d.polygon(pp, fill=fill)
        if outline is not None:
            self.d.line(pp + pp[:2], fill=outline, width=max(1, int(w * self.k)), joint="curve")

    def line(self, pts, color=INK, w=5):
        self.d.line(self._p(pts), fill=color, width=max(1, int(w * self.k)), joint="curve")

    def ellipse(self, x0, y0, x1, y1, fill=None, outline=None, w=5):
        self.d.ellipse([x0 * self.k, y0 * self.k, x1 * self.k, y1 * self.k], fill=fill,
                       outline=outline, width=max(1, int(w * self.k)) if outline else 0)

    def circle(self, cx, cy, r, fill=None, outline=None, w=5):
        self.ellipse(cx - r, cy - r, cx + r, cy + r, fill, outline, w)

    def vgrad(self, y0, y1, c0, c1, x0=0, x1=LW):
        steps = max(2, int((y1 - y0) * self.k / 4))
        for i in range(steps):
            t = i / (steps - 1)
            c = tuple(int(c0[j] + (c1[j] - c0[j]) * t) for j in range(3))
            ya = (y0 + (y1 - y0) * i / steps) * self.k
            yb = (y0 + (y1 - y0) * (i + 1) / steps) * self.k + 1
            self.d.rectangle([x0 * self.k, ya, x1 * self.k, yb], fill=c)

    def done(self):
        return self.im.reduce(BG_SS)


def _floor_perspective(g, y_top, c_floor, c_line, vp=(540, 700)):
    g.rect(0, y_top, LW, LH, c_floor)
    ys = [y_top, y_top + 70, y_top + 160, y_top + 280, y_top + 430, y_top + 620]
    for y in ys:
        g.line([(0, y), (LW, y)], c_line, 3)
    for i in range(-6, 8):
        xb = 540 + i * 170
        g.line([(vp[0] + (xb - vp[0]) * (y_top - vp[1]) / (LH - vp[1]), y_top), (xb, LH)], c_line, 3)


# ------------------------------------------------------------------ kitchen
def kitchen(s):
    g = G(s, color=(216, 210, 168))
    wall, olive, olive_d = (216, 210, 168), (182, 174, 100), (150, 142, 78)
    tile, tile_l = (238, 232, 206), (208, 200, 166)
    floor, floor_l = (234, 228, 200), (205, 198, 168)
    wood, wood_d = (176, 124, 78), (140, 96, 58)
    steel, steel_d = (176, 178, 176), (130, 132, 132)
    y_floor = 1300

    g.rect(0, 0, LW, y_floor, wall)
    # backsplash tiles
    g.rect(0, 830, LW, 1120, tile)
    for x in range(0, LW + 1, 96):
        g.line([(x, 830), (x, 1120)], tile_l, 3)
    for y in range(830, 1121, 96):
        g.line([(0, y), (LW, y)], tile_l, 3)
    _floor_perspective(g, y_floor, floor, floor_l)
    g.line([(0, y_floor), (LW, y_floor)], INK, 5)

    # left shelf with jars
    g.rect(0, 690, 230, 1050, (130, 96, 60), INK, 5)
    g.rect(0, 700, 214, 1040, (96, 70, 46))
    g.line([(0, 870), (214, 870)], INK, 6)
    for (x, y, w, h) in [(18, 780, 54, 86), (92, 800, 66, 66), (180, 770, 40, 96)]:
        g.rrect(x, y, x + w, y + h, 10, (232, 226, 206), INK, 4)
        g.rect(x + 4, y - 14, x + w - 4, y, (150, 150, 150), INK, 3)
    g.rrect(70, 720, 116, 866 - 20, 12, (110, 160, 130), INK, 4)
    g.rect(84, 700, 104, 726, (110, 160, 130), INK, 4)
    for (x, y, w, h) in [(20, 960, 60, 80), (120, 940, 50, 100)]:
        g.rrect(x, y, x + w, y + h, 10, (232, 226, 206), INK, 4)
    g.rrect(188, 930, 232, 1040, 12, (190, 70, 64), INK, 4)

    # hood + duct
    g.poly([(398, 520), (518, 520), (520, 650), (396, 650)], steel, INK, 5)
    g.poly([(404, 500), (440, 470), (520, 470), (540, 500)], steel_d, INK, 4)
    g.poly([(366, 650), (556, 650), (700, 870), (232, 870)], (196, 198, 198), INK, 5)
    g.rect(232, 870, 700, 905, steel, INK, 5)
    for x in (510, 550, 590, 630):
        g.circle(x, 888, 6, steel_d, INK, 2)

    # upper cabinet right
    g.rect(640, 690, LW + 20, 1060, olive, INK, 6)
    g.line([(860, 690), (860, 1060)], INK, 5)
    g.rect(664, 714, 840, 1036, None, olive_d, 5)
    g.rect(884, 714, LW, 1036, None, olive_d, 5)
    g.line([(826, 860), (826, 960)], INK, 8)
    g.line([(876, 860), (876, 960)], INK, 8)

    # rail with utensils
    g.line([(560, 975), (810, 975)], steel_d, 8)
    for i, x in enumerate((590, 640, 700, 760)):
        g.line([(x, 975), (x, 1010)], steel_d, 4)
        if i % 2 == 0:
            g.line([(x, 1010), (x, 1100)], steel_d, 7)
            g.ellipse(x - 18, 1085, x + 18, 1140, (190, 190, 196), INK, 4)
        else:
            g.line([(x, 1010), (x, 1090)], (120, 120, 126), 7)
            g.poly([(x - 22, 1090), (x + 22, 1090), (x + 26, 1130), (x - 26, 1130)], (190, 190, 196), INK, 4)

    # stove
    g.rect(300, 1130, 690, 1310, (190, 192, 190), INK, 6)
    g.rect(330, 1200, 660, 1300, (74, 78, 80), INK, 5)
    g.rect(342, 1212, 648, 1288, (96, 100, 104))
    g.line([(352, 1190), (640, 1190)], INK, 6)
    for x in (400, 470, 540, 610):
        g.circle(x, 1160, 11, (120, 124, 126), INK, 4)
    g.rect(300, 1092, 690, 1132, (60, 62, 64), INK, 5)
    # pot + pan + flame
    g.rrect(356, 1000, 448, 1094, 8, (170, 172, 172), INK, 5)
    g.line([(344, 1010), (360, 1010)], INK, 8)
    g.poly([(500, 1078), (640, 1066), (650, 1090), (500, 1094)], (46, 46, 50), INK, 5)
    g.line([(640, 1078), (720, 1070)], INK, 9)
    for fx in (520, 546, 572):
        g.poly([(fx, 1100), (fx + 10, 1126), (fx - 10, 1126)], (80, 150, 230))

    # counters + sink
    g.rect(700, 1090, LW + 20, 1140, wood, INK, 6)
    g.rect(0, 1100, 300, 1146, wood, INK, 6)
    g.rect(700, 1140, LW + 20, y_floor + 10, olive, INK, 6)
    g.rect(0, 1146, 300, y_floor + 10, olive, INK, 6)
    g.line([(860, 1140), (860, y_floor + 8)], INK, 5)
    g.rect(740, 1176, 842, 1274, None, olive_d, 5)
    g.rect(880, 1176, LW, 1274, None, olive_d, 5)
    g.rect(150, 1180, 290, 1270, None, olive_d, 5)
    g.rect(10, 1180, 130, 1270, None, olive_d, 5)
    g.poly([(790, 1090), (1000, 1090), (980, 1126), (810, 1126)], (150, 164, 170), INK, 5)
    g.poly([(800, 1100), (990, 1100), (976, 1118), (814, 1118)], (110, 172, 204))
    g.line([(1010, 1090), (1010, 1010), (960, 990)], (150, 154, 156), 14)
    g.line([(1010, 1090), (1010, 1010), (960, 990)], INK, 3)
    return g.done()


# ------------------------------------------------------------------ living room
def room(s):
    g = G(s, color=(226, 214, 190))
    y_floor = 1260
    g.rect(0, 0, LW, y_floor, (226, 214, 190))
    g.rect(0, y_floor - 60, LW, y_floor, (210, 196, 168))          # skirting
    g.rect(0, y_floor, LW, LH, (168, 126, 88))
    for i in range(0, 8):
        y = y_floor + i * i * 14 + 20
        g.line([(0, y), (LW, y)], (140, 100, 66), 3)
    g.line([(0, y_floor), (LW, y_floor)], INK, 5)
    # window
    g.rect(110, 430, 450, 960, (255, 255, 255), INK, 8)
    g.rect(128, 448, 432, 942, (170, 214, 238))
    g.poly([(128, 800), (230, 700), (330, 780), (432, 690), (432, 942), (128, 942)], (150, 200, 150))
    g.circle(360, 540, 40, (255, 232, 140))
    g.line([(280, 448), (280, 942)], INK, 7)
    g.line([(128, 695), (432, 695)], INK, 7)
    g.poly([(60, 400), (170, 400), (160, 1000), (60, 1000)], (200, 110, 100), INK, 5)
    g.poly([(400, 400), (510, 400), (510, 1000), (390, 1000)], (200, 110, 100), INK, 5)
    # picture frames
    g.rect(600, 480, 840, 700, (250, 246, 236), INK, 8)
    g.rect(620, 500, 820, 680, (232, 180, 90))
    g.poly([(620, 680), (700, 590), (760, 650), (820, 570), (820, 680)], (120, 150, 190))
    g.rect(880, 540, 1010, 660, (250, 246, 236), INK, 8)
    g.circle(945, 600, 34, (210, 90, 90))
    # clock
    g.circle(720, 300, 62, (255, 255, 255), INK, 7)
    g.line([(720, 300), (720, 256)], INK, 6)
    g.line([(720, 300), (752, 316)], INK, 6)
    # sofa (right)
    g.rrect(660, 1000, 1110, 1290, 40, (150, 60, 66), INK, 7)
    g.rrect(640, 1100, 740, 1300, 30, (126, 46, 54), INK, 7)
    g.rrect(1030, 1100, 1130, 1300, 30, (126, 46, 54), INK, 7)
    g.rect(740, 1090, 1030, 1230, (170, 74, 80))
    # plant (left)
    g.poly([(60, 1160), (180, 1160), (160, 1300), (80, 1300)], (190, 104, 70), INK, 6)
    for (a, b, c, d_) in [(120, 1160, 60, 960), (120, 1160, 130, 920), (120, 1160, 200, 980)]:
        g.line([(a, b), (c, d_)], (70, 130, 70), 12)
        g.ellipse(c - 36, d_ - 60, c + 36, d_ + 20, (90, 160, 84), INK, 4)
    # lamp
    g.line([(560, 1290), (560, 980)], INK, 10)
    g.poly([(500, 980), (620, 980), (600, 900), (520, 900)], (250, 220, 130), INK, 6)
    return g.done()


# ------------------------------------------------------------------ street
def street(s):
    g = G(s)
    g.vgrad(0, 900, (150, 205, 240), (226, 240, 248))
    g.circle(860, 260, 80, (255, 226, 130))
    rnd = random.Random(7)
    x = -20
    cols = [(210, 150, 120), (170, 190, 200), (222, 190, 120), (170, 150, 190), (150, 190, 160)]
    while x < LW:
        w = rnd.randint(190, 300)
        h = rnd.randint(500, 900)
        c = cols[rnd.randint(0, len(cols) - 1)]
        g.rect(x, 1240 - h, x + w, 1240, c, INK, 6)
        for wy in range(1240 - h + 40, 1180, 110):
            for wx in range(x + 30, x + w - 50, 70):
                g.rect(wx, wy, wx + 38, wy + 62, (250, 236, 170) if rnd.random() < .4 else (140, 175, 205), INK, 3)
        x += w + 6
    g.rect(0, 1240, LW, 1370, (206, 202, 192))
    g.line([(0, 1240), (LW, 1240)], INK, 5)
    g.line([(0, 1370), (LW, 1370)], INK, 6)
    g.rect(0, 1370, LW, LH, (92, 94, 100))
    for xx in range(-40, LW, 220):
        g.rect(xx, 1700, xx + 120, 1718, (240, 220, 120))
    for xx in (120, 800):
        g.rect(xx - 12, 880, xx + 12, 1260, (110, 80, 54), INK, 5)
        g.circle(xx, 840, 120, (96, 168, 92), INK, 6)
    g.line([(960, 1250), (960, 760)], INK, 12)
    g.rrect(920, 730, 1000, 780, 16, (255, 230, 150), INK, 5)
    return g.done()


# ------------------------------------------------------------------ school
def school(s):
    g = G(s, color=(238, 228, 186))
    y_floor = 1290
    g.rect(0, 0, LW, y_floor, (238, 228, 186))
    g.rect(0, 1000, LW, y_floor, (220, 206, 160))
    g.line([(0, 1000), (LW, 1000)], (180, 164, 120), 4)
    g.rect(0, y_floor, LW, LH, (196, 160, 118))
    for i in range(7):
        y = y_floor + i * i * 18 + 16
        g.line([(0, y), (LW, y)], (164, 130, 92), 3)
    g.line([(0, y_floor), (LW, y_floor)], INK, 5)
    g.rect(120, 380, 960, 840, (150, 104, 66), INK, 8)
    g.rect(146, 406, 934, 814, (46, 92, 72))
    g.line([(190, 520), (330, 500), (420, 530)], (236, 236, 226), 5)
    g.line([(200, 600), (480, 590)], (236, 236, 226), 5)
    g.line([(200, 660), (400, 668)], (236, 236, 226), 5)
    g.rect(146, 814, 934, 836, (120, 82, 50))
    g.rect(300, 800, 380, 814, (240, 240, 236))
    g.circle(540, 250, 70, (255, 255, 255), INK, 7)
    g.line([(540, 250), (540, 200)], INK, 6)
    g.line([(540, 250), (578, 268)], INK, 6)
    g.rect(40, 880, 90, 1100, (190, 70, 64), INK, 4)
    g.rect(990, 480, 1060, 820, (170, 214, 238), INK, 6)
    for (x0, x1) in ((100, 360), (420, 680), (740, 1000)):
        g.rect(x0, 1160, x1, 1200, (160, 110, 68), INK, 6)
        g.rect(x0 + 20, 1200, x0 + 36, 1290, (110, 110, 116), INK, 3)
        g.rect(x1 - 36, 1200, x1 - 20, 1290, (110, 110, 116), INK, 3)
    return g.done()


# ------------------------------------------------------------------ market (bazaar)
def market(s):
    g = G(s, color=(250, 232, 196))
    g.vgrad(0, 760, (246, 196, 140), (252, 232, 190))
    g.rect(0, 640, LW, 1300, (214, 168, 128), INK, 6)
    g.line([(0, 560), (LW, 600), (LW, 560)], INK, 4)
    for i, x in enumerate(range(0, LW + 90, 90)):                                   # bunting
        g.poly([(x, 580 + (i % 2) * 6), (x + 70, 586), (x + 35, 650)],
               [(214, 70, 64), (240, 190, 60), (70, 150, 96), (70, 120, 190)][i % 4], INK, 3)
    g.line([(0, 580), (LW, 590)], INK, 5)
    stalls = ((30, (206, 64, 60)), (385, (230, 170, 50)), (740, (62, 140, 96)))
    for (x, col) in stalls:
        w = 310
        for k in range(8):                                                           # striped awning
            g.rect(x + k * w / 8.0, 770, x + (k + 1) * w / 8.0, 880, col if k % 2 == 0 else (250, 246, 236), INK, 3)
            g.circle(x + (k + 0.5) * w / 8.0, 880, w / 16.0, col if k % 2 == 0 else (250, 246, 236), INK, 3)
        g.poly([(x - 14, 770), (x + w + 14, 770), (x + w - 14, 730), (x + 14, 730)], shade_c(col, 0.8), INK, 5)
        g.line([(x, 900), (x, 1300)], INK, 9)
        g.line([(x + w, 900), (x + w, 1300)], INK, 9)
        g.rrect(x + 8, 1150, x + w - 8, 1300, 14, (160, 112, 76), INK, 6)
        for j in range(5):                                                           # produce on the counter
            cx = x + 40 + j * 56
            g.circle(cx, 1128, 28, [(214, 64, 56), (240, 150, 50), (110, 176, 84), (230, 200, 70), (214, 64, 56)][(j + x // 300) % 5], INK, 4)
            g.circle(cx + 26, 1146, 24, [(240, 150, 50), (110, 176, 84), (214, 64, 56)][(j + 1) % 3], INK, 4)
        g.line([(x + 50, 900), (x + 50, 960)], INK, 3)
        g.circle(x + 50, 976, 16, (255, 236, 150), INK, 4)                           # hanging bulb
    g.rect(0, 1300, LW, LH, (208, 188, 150))
    g.line([(0, 1300), (LW, 1300)], INK, 5)
    for i in range(7):
        y = 1300 + i * i * 16 + 14
        g.line([(0, y), (LW, y)], (180, 160, 122), 3)
    return g.done()


def shade_c(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c)


# ------------------------------------------------------------------ office
def office(s):
    g = G(s, color=(226, 230, 238))
    y_floor = 1290
    g.rect(0, 0, LW, y_floor, (226, 230, 238))
    g.rect(0, y_floor - 70, LW, y_floor, (204, 210, 222))
    g.rect(620, 330, 1030, 900, (255, 255, 255), INK, 8)                              # big window with a skyline
    g.rect(638, 348, 1012, 882, (170, 214, 240))
    for (x0, w, h) in ((650, 70, 260), (730, 90, 360), (830, 70, 200), (910, 90, 320)):
        g.rect(x0, 882 - h, x0 + w, 882, (110, 138, 168), INK, 4)
        for wy in range(882 - h + 24, 860, 46):
            g.rect(x0 + 12, wy, x0 + 26, wy + 24, (230, 240, 250))
    g.line([(826, 348), (826, 882)], INK, 6)
    g.rect(80, 420, 520, 760, (252, 252, 250), INK, 8)                                # whiteboard
    g.line([(130, 500), (300, 480), (380, 520)], (60, 100, 190), 6)
    g.line([(140, 580), (440, 570)], (60, 100, 190), 5)
    g.rect(140, 640, 200, 700, (230, 120, 90))
    g.circle(310, 250, 60, (255, 255, 255), INK, 7)                                   # wall clock
    g.line([(310, 250), (310, 206)], INK, 6)
    g.line([(310, 250), (344, 262)], INK, 6)
    g.rect(0, y_floor, LW, LH, (98, 108, 128))
    _floor_perspective(g, y_floor, (98, 108, 128), (82, 92, 110), (540, 900))
    g.line([(0, y_floor), (LW, y_floor)], INK, 5)
    g.rrect(120, 1130, 700, 1170, 8, (170, 120, 80), INK, 6)                          # desk with a monitor
    g.rect(150, 1170, 176, 1290, (140, 96, 64), INK, 5)
    g.rect(644, 1170, 670, 1290, (140, 96, 64), INK, 5)
    g.rrect(260, 940, 560, 1110, 14, (46, 50, 60), INK, 6)
    g.rect(276, 956, 544, 1094, (104, 168, 220))
    g.line([(300, 1000), (480, 1000)], (240, 248, 255), 6)
    g.line([(300, 1040), (430, 1040)], (240, 248, 255), 6)
    g.rect(396, 1110, 424, 1130, (46, 50, 60))
    g.rrect(300, 1112, 520, 1130, 6, (210, 214, 222), INK, 4)                         # keyboard
    g.rrect(780, 1000, 940, 1290, 12, (120, 138, 160), INK, 6)                        # filing cabinet / water cooler
    g.rrect(796, 920, 924, 1000, 20, (190, 226, 244), INK, 5)
    g.rect(856, 1000, 864, 1040, INK)
    return g.done()


# ------------------------------------------------------------------ bus stop
def bus_stop(s):
    g = G(s)
    g.vgrad(0, 1000, (150, 205, 240), (226, 240, 248))
    g.circle(200, 240, 80, (255, 226, 130))
    rnd = random.Random(11)
    x = -30
    while x < LW:
        w = rnd.randint(170, 260)
        h = rnd.randint(380, 720)
        g.rect(x, 1180 - h, x + w, 1180, [(190, 176, 160), (160, 184, 200), (206, 176, 120)][rnd.randint(0, 2)], INK, 6)
        for wy in range(1180 - h + 36, 1130, 100):
            for wx in range(x + 24, x + w - 40, 62):
                g.rect(wx, wy, wx + 30, wy + 54, (140, 175, 205), INK, 3)
        x += w + 8
    g.rect(0, 1180, LW, 1330, (206, 202, 192))
    g.line([(0, 1180), (LW, 1180)], INK, 5)
    g.line([(0, 1330), (LW, 1330)], INK, 6)
    g.rect(0, 1330, LW, LH, (92, 94, 100))
    for xx in range(-40, LW, 220):
        g.rect(xx, 1700, xx + 120, 1718, (240, 220, 120))
    g.rect(150, 1000, 160, 1330, (90, 110, 130), INK, 4)                              # shelter
    g.rect(760, 1000, 770, 1330, (90, 110, 130), INK, 4)
    g.rect(130, 960, 800, 1000, (70, 150, 150), INK, 6)
    g.rect(160, 1000, 760, 1290, (190, 226, 240))
    g.rect(190, 1030, 360, 1210, (240, 200, 90), INK, 5)                              # poster
    g.circle(275, 1100, 36, (214, 70, 64), INK, 4)
    g.rrect(420, 1218, 740, 1250, 8, (150, 104, 68), INK, 6)                          # bench
    g.rect(440, 1250, 456, 1330, INK)
    g.rect(704, 1250, 720, 1330, INK)
    g.line([(930, 1330), (930, 800)], INK, 12)                                        # bus-stop pole + sign
    g.circle(930, 770, 62, (60, 110, 200), INK, 7)
    g.rrect(900, 748, 960, 790, 8, (255, 255, 255), INK, 4)
    g.circle(912, 796, 7, INK, INK, 2)
    g.circle(948, 796, 7, INK, INK, 2)
    return g.done()


# ------------------------------------------------------------------ plain / studio
def plain(s, colors=None):
    c0, c1 = (colors or [(255, 214, 120), (255, 150, 110)])[:2]
    g = G(s)
    g.vgrad(0, LH, tuple(c0), tuple(c1))
    return g.done()


# ------------------------------------------------------------------ night road (scrolling)
def night_road(s, world_w=LW):
    """Returns (static sky, scrolling ground wide image). Ground repeats every 1080."""
    sky = G(s)
    sky.vgrad(0, 1300, (10, 12, 38), (42, 36, 86))
    rnd = random.Random(3)
    for _ in range(90):
        x, y, r = rnd.randint(0, LW), rnd.randint(0, 900), rnd.choice((2, 2, 3, 4))
        sky.circle(x, y, r, (255, 250, 220))
    sky.circle(820, 330, 110, (252, 244, 214))
    sky.circle(782, 304, 110, (17, 18, 49))      # crescent bite
    sky.circle(820, 330, 112, None, (252, 244, 214), 3)
    sky_img = sky.done()

    gr = G(s, w=LW * 2, color=(0, 0, 0, 0), mode="RGBA")
    for ox in (0, LW):
        for (hx, hy, hr) in [(120, 1120, 260), (520, 1160, 320), (900, 1110, 240)]:
            gr.ellipse(ox + hx - hr, hy - hr * 0.55, ox + hx + hr, hy + hr * 0.9, (20, 22, 52))
        for (wx, wy) in [(80, 1090), (150, 1120), (610, 1080), (680, 1120), (940, 1090)]:
            gr.rect(ox + wx, wy, ox + wx + 22, wy + 28, (255, 214, 120))
    gr.rect(0, 1240, LW * 2, 1380, (30, 32, 50))           # footpath
    gr.rect(0, 1380, LW * 2, LH, (26, 26, 36))               # road
    gr.line([(0, 1380), (LW * 2, 1380)], (60, 62, 90), 6)
    for ox in (0, LW):
        for xx in (20, 380, 740):
            gr.rect(ox + xx, 1700, ox + xx + 190, 1722, (214, 196, 120))
        lx = ox + 300
        gr.line([(lx, 1260), (lx, 780)], (14, 14, 22), 16)
        gr.line([(lx, 790), (lx + 90, 790)], (14, 14, 22), 12)
        gr.ellipse(lx + 60, 790, lx + 130, 822, (255, 226, 150))
        glow = Image.new("RGBA", gr.im.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        for i in range(12):
            a = 9
            r = (170 - i * 13) * gr.k
            gd.ellipse([(lx + 95) * gr.k - r, 806 * gr.k - r, (lx + 95) * gr.k + r, 806 * gr.k + r],
                       fill=(255, 220, 140, a))
        gr.im.alpha_composite(glow)
        gr.d = ImageDraw.Draw(gr.im)
    return sky_img, gr.done()


# ------------------------------------------------------------------ public API
# Things that move behind the characters: ("cloud", y, speed px/s, scale), ("birds", y, speed, count),
# ("traffic", y, scale, period s) = a small vehicle crossing the far lane every `period` seconds.
AMBIENT = {
    "street": [("cloud", 190, 14, 1.0), ("cloud", 450, 9, 0.75), ("birds", 330, 60, 3), ("traffic", 1500, 0.4, 9.0)],
    "bus_stop": [("cloud", 220, 11, 1.0), ("cloud", 460, 7, 0.7), ("birds", 360, 55, 2), ("traffic", 1470, 0.42, 7.5)],
    "school": [("birds", 110, 48, 2)],
}


def _cloud_sprite(s, scale):
    w, h = 260, 110
    g = G(s * scale, w, h, (0, 0, 0, 0), "RGBA")
    for (cx, cy, r) in ((70, 70, 44), (125, 50, 52), (185, 68, 42), (130, 78, 40)):
        g.circle(cx, cy, r, (255, 255, 255, 235))
    g.rect(60, 70, 200, 108, (255, 255, 255, 235))
    return g.done()


class Background:
    def __init__(self, spec, out_w, out_h):
        self.out_w, self.out_h = out_w, out_h
        s = out_w / float(LW)
        spec = spec or {"type": "plain"}
        if isinstance(spec, str):
            spec = {"type": spec}
        self.kind = spec.get("type", "plain")
        self.scroll = float(spec.get("scroll", 0.0))   # logical px per second
        self.ambient = AMBIENT.get(self.kind, []) if spec.get("ambient", True) else []
        self._clouds = {}
        self.static = None
        self.wide = None
        if self.kind == "image":
            im = Image.open(asset_path(spec["path"])).convert("RGB")
            r = max(out_w / im.width, out_h / im.height)
            im = im.resize((int(im.width * r + 1), int(im.height * r + 1)), Image.LANCZOS)
            l, t = (im.width - out_w) // 2, (im.height - out_h) // 2
            self.static = im.crop((l, t, l + out_w, t + out_h))
        elif self.kind == "night_road":
            sky, wide = night_road(s)
            self.static = sky
            self.wide = wide
        else:
            fn = {"kitchen": kitchen, "room": room, "street": street, "school": school,
                  "market": market, "office": office, "bus_stop": bus_stop}.get(self.kind)
            if fn:
                self.static = fn(s)
            else:
                self.static = plain(s, spec.get("colors"))
            if self.static.size != (out_w, out_h):
                self.static = self.static.resize((out_w, out_h), Image.LANCZOS)
        if self.wide is not None:
            self.wide = self.wide.resize((out_w * 2, out_h), Image.LANCZOS) if self.wide.size != (out_w * 2, out_h) else self.wide
            if self.static.size != (out_w, out_h):
                self.static = self.static.resize((out_w, out_h), Image.LANCZOS)

    def frame(self, t):
        if self.wide is None:
            base = self.static.copy()
        else:
            off = int((t * self.scroll * self.out_w / LW) % self.out_w)
            base = self.static.copy()
            part = self.wide.crop((off, 0, off + self.out_w, self.out_h))
            base.paste(part, (0, 0), part)
        if self.ambient:
            self._draw_ambient(base, t)
        return base

    def _draw_ambient(self, img, t):
        s = self.out_w / float(LW)
        for n, item in enumerate(self.ambient):
            kind = item[0]
            if kind == "cloud":
                _k, y, speed, scale = item
                sp = self._clouds.get(scale)
                if sp is None:
                    sp = self._clouds[scale] = _cloud_sprite(s, scale)
                span = self.out_w + 2 * sp.width
                x = (n * 0.37 * span + t * speed * s) % span - sp.width
                img.paste(sp, (int(x), int(y * s)), sp)
            elif kind == "birds":
                _k, y, speed, count = item
                d = ImageDraw.Draw(img)
                for b in range(count):
                    span = self.out_w + 200 * s
                    x = (b * 70 * s + t * speed * s + n * 190 * s) % span - 100 * s
                    yy = y * s + math.sin(t * 1.3 + b) * 18 * s + b * 26 * s
                    a = math.sin(t * 11 + b * 1.7) * 7 * s
                    w = 15 * s
                    d.line([(x - w, yy + a), (x, yy), (x + w, yy + a)], fill=INK, width=max(2, int(3 * s)))
            elif kind == "traffic":
                self._draw_traffic(img, t, item, s)

    def _draw_traffic(self, img, t, item, s):
        from . import objects                      # (objects imports this module, so import lazily)
        _k, y, scale, period = item
        cycle, ct = int(t // period), t % period
        crossing = period * 0.62
        if ct > crossing:
            return
        kinds = ("car", "auto", "scooter", "truck")
        kind = kinds[cycle % len(kinds)]
        right = cycle % 2 == 0
        im, (ax, ay), wheels = objects.sprite(kind, s * scale)
        p = ct / crossing
        x = (-ax + p * (self.out_w + 2 * im.width)) if right else (self.out_w + im.width - p * (self.out_w + 2 * im.width))
        if not right:
            im = im.transpose(Image.FLIP_LEFT_RIGHT)
            ax = im.width - ax
        bob = math.sin(t * 17) * 2 * s
        img.paste(im, (int(x - ax), int(y * s - ay + bob)), im)
        for (wx, wy, r) in wheels:
            w = objects.wheel_image(r, -(x) / max(r, 1.0) * 57.2958)
            wxx = (im.width - wx) if not right else wx
            img.paste(w, (int(x - ax + wxx - w.width / 2), int(y * s - ay + bob + wy - w.height / 2)), w)

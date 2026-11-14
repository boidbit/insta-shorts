"""The village pack (gaon): the fields, the chaupal under the banyan, the hand pump, inside a mud house, the village
school under the tree.

Logical 1080 x 1920, the people stand around y = 1700; drawn with the layer hooks (sky / far) so the 2.5D look gives
them depth by itself (studio.style25d.autoset), and each also has a hand-made 2.5D set (style25d/scenery_gaon)."""
import random

from .backgrounds import G, INK
from .util import LH, LW


def _loc():
    from . import locations
    return locations


def _txt(*a, **k):
    return _loc()._txt(*a, **k)


def _sky(g, top=(128, 196, 242), bottom=(236, 240, 228), y1=1000):
    _loc()._sky(g, top, bottom, y1)
    with g.on("sky"):
        g.circle(860, 250, 70, (255, 232, 150))


def _far_fields(g, y0=930, y1=1240, seed=5, color=(166, 196, 108)):
    """Fields to the horizon and a line of trees (the 2.5D far layer)."""
    with g.on("far"):
        g.rect(0, y0, LW, y1, color)
        for y in range(y0 + 30, y1, 40):
            g.line([(0, y), (LW, y + 10)], tuple(max(0, v - 20) for v in color), 4)
        rnd = random.Random(seed)
        for x in range(-20, LW + 40, 90):
            g.circle(x + rnd.randint(-10, 10), y0 - rnd.randint(0, 30), rnd.randint(40, 70), (92, 140, 80))


def _hut(g, x, y, w=220, h=180, roof=(176, 110, 70), wall=(206, 164, 116)):
    g.rect(x, y - h, x + w, y, wall, INK, 5)
    g.poly([(x - 30, y - h), (x + w / 2, y - h - 110), (x + w + 30, y - h)], roof, INK, 5)
    for i in range(1, 4):
        yy = y - h - i * 26
        g.line([(x - 30 + i * 34, yy), (x + w + 30 - i * 34, yy)], tuple(v - 24 for v in roof), 4)
    g.rect(x + w * 0.38, y - h * 0.62, x + w * 0.62, y, (90, 62, 44), INK, 4)


def _uple(g, x, y, n=5):
    """Dung cakes drying on a wall."""
    for i in range(n):
        g.circle(x + (i % 3) * 52, y + (i // 3) * 54, 22, (120, 90, 60), INK, 3)


def _earth(g, y0, color=(214, 180, 130), seed=8):
    g.rect(0, y0, LW, LH, color)
    rnd = random.Random(seed)
    for _ in range(26):
        x, y = rnd.randint(0, LW), rnd.randint(y0 + 30, LH - 20)
        g.circle(x, y, rnd.randint(4, 9), tuple(v - 24 for v in color))
    g.line([(0, y0), (LW, y0)], INK, 5)


def khet(s):
    """The fields: rows of mustard (yellow) on one side and green wheat on the other, the mend (raised path) in the
    middle where the people stand, the tubewell's little pump house with water gushing into the channel, a
    scarecrow, a hut and trees far away."""
    g = G(s)
    _sky(g)
    _far_fields(g, 900, 1240, 11, (178, 204, 110))
    with g.on("far"):
        _hut(g, 760, 960, 150, 110)
    g.rect(40, 860, 300, 1180, (214, 196, 170), INK, 6)                       # the tubewell's pump house
    g.poly([(20, 860), (170, 780), (320, 860)], (170, 90, 70), INK, 6)
    g.rect(130, 960, 210, 1180, (90, 70, 52), INK, 4)
    g.rect(300, 1080, 350, 1110, (110, 120, 130), INK, 4)                      # the pipe and its water
    g.poly([(350, 1080), (420, 1100), (430, 1240), (360, 1240)], (150, 200, 240))
    g.rect(0, 1180, 520, 1240, (120, 170, 220), INK, 3)                        # the channel
    for x in range(10, 520, 60):
        g.line([(x, 1200), (x + 30, 1205)], (220, 240, 255), 3)
    rnd = random.Random(21)
    for x in range(520, LW, 26):                                               # mustard on the right
        h = rnd.randint(150, 230)
        g.line([(x, 1240), (x + rnd.randint(-6, 6), 1240 - h)], (110, 150, 70), 4)
        g.circle(x, 1240 - h, rnd.randint(14, 20), (246, 210, 60))
    sx, sy = 880, 1000                                                         # the scarecrow (bijooka)
    g.line([(sx, sy - 40), (sx, 1240)], (120, 86, 56), 10)
    g.line([(sx - 110, sy + 30), (sx + 110, sy + 30)], (120, 86, 56), 9)
    g.poly([(sx - 70, sy + 20), (sx + 70, sy + 20), (sx + 50, sy + 170), (sx - 50, sy + 170)], (200, 70, 60), INK, 4)
    g.circle(sx, sy - 40, 46, (236, 220, 180), INK, 4)
    g.poly([(sx - 70, sy - 70), (sx + 70, sy - 70), (sx, sy - 140)], (180, 150, 80), INK, 4)
    g.circle(sx - 16, sy - 46, 6, INK)
    g.circle(sx + 16, sy - 46, 6, INK)
    g.rect(0, 1240, LW, LH, (156, 190, 96))                                    # the wheat in front, the mend
    for x in range(0, LW, 22):
        g.line([(x, LH), (x + rnd.randint(-10, 10), 1260 + rnd.randint(0, 40))], (120, 160, 70), 4)
    g.poly([(380, 1240), (700, 1240), (900, LH), (180, LH)], (196, 160, 112))
    g.line([(380, 1240), (180, LH)], INK, 4)
    g.line([(700, 1240), (900, LH)], INK, 4)
    g.line([(0, 1240), (LW, 1240)], INK, 5)
    return g.done()


def chaupal(s):
    """The chaupal: a huge banyan with its hanging roots, the round chabutra under it where the old men sit, a
    hookah and a khaat on it, mud houses behind, the GRAM PANCHAYAT board. Gossip, the panchayat, the tau."""
    g = G(s)
    _sky(g)
    _far_fields(g, 920, 1240, 3)
    with g.on("far"):
        _hut(g, 20, 1000, 200, 150)
        _hut(g, 840, 1010, 200, 140, roof=(160, 100, 70))
    g.rect(470, 560, 610, 1170, (110, 80, 54), INK, 7)                         # the banyan's trunk
    for (cx, cy, r) in ((540, 380, 230), (330, 470, 190), (760, 470, 190), (220, 600, 140), (880, 600, 140),
                        (540, 560, 180)):
        g.circle(cx, cy, r, (70, 136, 66), INK, 5)
    for x in (300, 380, 700, 790, 860, 230):                                   # the hanging roots
        g.line([(x, 640), (x + 6, 900 + (x % 7) * 20)], (120, 92, 64), 5)
    g.rect(200, 1110, 880, 1240, (204, 186, 160), INK, 6)                      # the chabutra
    g.rect(180, 1090, 900, 1112, (222, 206, 182), INK, 4)
    for x in range(240, 880, 80):
        g.line([(x, 1112), (x, 1240)], (180, 162, 138), 3)
    g.rect(640, 1020, 840, 1050, (150, 100, 60), INK, 4)                       # a khaat on it
    for x in (650, 830):
        g.line([(x, 1050), (x, 1090)], (120, 80, 50), 8)
    for x in range(650, 840, 18):
        g.line([(x, 1022), (x + 8, 1048)], (230, 210, 170), 2)
    hx = 330                                                                   # the hookah
    g.ellipse(hx - 34, 1030, hx + 34, 1090, (150, 110, 70), INK, 4)
    g.rect(hx - 8, 960, hx + 8, 1032, (120, 90, 60), INK, 3)
    g.poly([(hx - 26, 940), (hx + 26, 940), (hx + 16, 966), (hx - 16, 966)], (180, 80, 50), INK, 3)
    g.line([(hx + 20, 1050), (hx + 90, 1000), (hx + 120, 1020)], (60, 40, 30), 4)
    g.rect(40, 760, 260, 860, (250, 240, 214), INK, 5)                         # the panchayat board
    _txt(g, 150, 795, "GRAM", 28, (40, 90, 50))
    _txt(g, 150, 830, "PANCHAYAT", 28, (40, 90, 50))
    g.line([(80, 860), (80, 1100)], (90, 70, 50), 6)
    g.line([(220, 860), (220, 1100)], (90, 70, 50), 6)
    _earth(g, 1240)
    return g.done()


def handpump(s):
    """The hand pump in the lane: the green pump on its cement platform with a little puddle, matkas waiting in a
    line, a bucket, the washing stone, mud houses with dung cakes, a buffalo tied far behind."""
    g = G(s)
    _sky(g, (134, 200, 240), (240, 238, 226))
    _far_fields(g, 940, 1240, 17)
    with g.on("far"):                                                          # a buffalo tied by a hut, far away
        g.ellipse(780, 1060, 900, 1120, (60, 56, 56))
        g.circle(905, 1070, 26, (60, 56, 56))
        for x in (795, 815, 865, 885):
            g.line([(x, 1110), (x, 1150)], (60, 56, 56), 8)
    g.rect(0, 620, 330, 1240, (210, 168, 120), INK, 6)                         # houses on the left
    g.poly([(-20, 620), (165, 500), (350, 620)], (176, 90, 66), INK, 6)
    g.rect(110, 900, 220, 1240, (80, 56, 40), INK, 5)
    _uple(g, 20, 700, 6)
    g.rect(840, 700, LW, 1240, (220, 180, 130), INK, 6)
    g.poly([(820, 700), (960, 610), (1100, 700)], (160, 100, 70), INK, 6)
    _uple(g, 880, 780, 5)
    g.rect(400, 1150, 700, 1240, (190, 190, 186), INK, 5)                      # the platform
    g.ellipse(420, 1210, 680, 1250, (150, 200, 230))
    px = 520                                                                   # the pump
    g.rect(px - 22, 900, px + 22, 1160, (60, 120, 80), INK, 5)
    g.rect(px - 32, 880, px + 32, 910, (60, 120, 80), INK, 4)
    g.line([(px, 900), (px + 150, 850)], (60, 120, 80), 12)
    g.line([(px - 20, 1000), (px - 70, 1010), (px - 74, 1040)], (60, 120, 80), 12)
    for i, x in enumerate((740, 790, 840)):                                    # matkas waiting their turn
        g.ellipse(x - 26, 1180, x + 26, 1240, (200, 110, 60) if i != 1 else (180, 180, 186), INK, 4)
        g.rect(x - 12, 1170, x + 12, 1184, (170, 90, 50), INK, 3)
    g.rect(330, 1180, 390, 1240, (110, 140, 190), INK, 4)                      # a bucket
    g.rect(680, 1215, 780, 1240, (150, 150, 146), INK, 4)                      # the washing stone
    _earth(g, 1240, (210, 176, 128))
    return g.done()


def kachcha_ghar(s):
    """Inside a mud house: earth walls with a niche holding a diya, the chulha in the corner with its smoke,
    brass pots on a shelf, a lantern hanging, dung cakes by the chulha, a folded khaat against the wall, a little
    window, the earthen floor."""
    g = G(s, color=(196, 146, 100))
    y_floor = 1270
    g.rect(0, 0, LW, y_floor, (198, 150, 104))
    rnd = random.Random(41)
    for _ in range(40):                                                        # the mud wall's texture
        x, y = rnd.randint(0, LW), rnd.randint(0, y_floor - 20)
        g.ellipse(x - 30, y - 8, x + 30, y + 8, (186, 138, 94))
    g.rect(0, 0, LW, 120, (120, 86, 60))                                       # the roof beams
    for x in range(40, LW, 180):
        g.rect(x, 0, x + 40, 160, (100, 70, 48), INK, 4)
    g.rect(460, 300, 640, 470, (170, 200, 220), INK, 6)                        # a little window
    g.line([(550, 300), (550, 470)], (100, 70, 48), 6)
    g.note_light(550, 385, 150, (255, 236, 190))
    g.rrect(140, 420, 260, 560, 50, (120, 86, 60), INK, 5)                     # the niche with a diya
    g.ellipse(176, 520, 224, 546, (200, 140, 70), INK, 3)
    g.poly([(200, 520), (192, 500), (200, 486), (208, 500)], (255, 190, 60))
    g.note_light(200, 505, 70, (255, 200, 110))
    g.rect(700, 520, 1040, 540, (110, 76, 52), INK, 4)                         # brass pots on a shelf
    for i, x in enumerate((730, 800, 880, 960)):
        g.ellipse(x, 440 + (i % 2) * 20, x + 60, 520, (210, 170, 60), INK, 4)
    g.line([(330, 120), (330, 300)], (60, 50, 40), 3)                          # the lantern
    g.rect(300, 300, 360, 400, (240, 220, 160), INK, 4)
    g.rect(292, 290, 368, 304, (90, 90, 96), INK, 3)
    g.note_light(330, 350, 120, (255, 214, 130))
    g.rect(40, 640, 110, 1250, (130, 90, 56), INK, 5)                          # a folded khaat
    g.rect(110, 640, 180, 1250, (130, 90, 56), INK, 5)
    for y in range(660, 1240, 30):
        g.line([(44, y), (176, y + 10)], (220, 200, 160), 2)
    cx = 860                                                                   # the chulha and its smoke
    g.rect(cx - 120, 1150, cx + 120, 1270, (170, 120, 80), INK, 5)
    g.rrect(cx - 70, 1180, cx + 70, 1260, 30, (60, 40, 30), INK, 4)
    g.poly([(cx - 40, 1250), (cx, 1200), (cx + 40, 1250)], (255, 150, 60))
    g.rect(cx - 70, 1110, cx + 70, 1150, (80, 76, 74), INK, 4)                 # the tawa
    for i in range(3):
        g.circle(cx - 30 + i * 30, 1000 - i * 90, 50 + i * 16, (220, 214, 206))
    _uple(g, 990, 1180, 3)
    g.rect(0, y_floor, LW, LH, (176, 132, 90))                                 # the earthen floor (leepa)
    for i in range(9):
        y = y_floor + i * i * 9 + 18
        g.line([(0, y), (LW, y)], (160, 118, 80), 3)
    g.line([(0, y_floor), (LW, y_floor)], INK, 5)
    return g.done()


def gaon_school(s):
    """The village school: classes under the big tree, the blackboard on its stand, the jute mats (tat-patti) on
    the ground, the little school building with PRATHMIK VIDYALAYA, the brass bell hanging from a branch."""
    g = G(s)
    _sky(g)
    _far_fields(g, 940, 1240, 29)
    g.rect(560, 640, 1060, 1180, (246, 220, 150), INK, 6)                      # the school building
    g.rect(540, 610, 1080, 650, (200, 80, 60), INK, 5)
    g.rect(600, 680, 1020, 760, (250, 246, 230), INK, 4)
    _txt(g, 810, 720, "PRATHMIK VIDYALAYA", 34, (180, 50, 40))
    for x in (620, 760, 900):
        g.rect(x, 820, x + 100, 960, (120, 170, 210), INK, 4)
    g.rect(980, 900, 1040, 1180, (110, 76, 52), INK, 4)
    g.rect(120, 560, 190, 1180, (110, 80, 54), INK, 6)                         # the tree on the left
    for (cx, cy, r) in ((150, 420, 190), (20, 520, 150), (300, 480, 160), (200, 300, 130)):
        g.circle(cx, cy, r, (86, 150, 74), INK, 5)
    g.line([(300, 600), (300, 680)], (60, 50, 40), 3)                          # the bell from a branch
    g.poly([(278, 680), (322, 680), (334, 740), (266, 740)], (210, 170, 60), INK, 4)
    g.line([(300, 740), (300, 762)], (60, 50, 40), 4)
    g.rect(260, 860, 500, 1020, (40, 60, 50), INK, 6)                          # the blackboard on its stand
    g.line([(280, 1020), (260, 1180)], (120, 86, 56), 8)
    g.line([(480, 1020), (500, 1180)], (120, 86, 56), 8)
    _txt(g, 380, 920, "A  B  C", 34, (240, 240, 232))
    _txt(g, 380, 970, "1 + 1 = 2", 30, (240, 240, 232))
    _earth(g, 1240, (218, 186, 136))
    for i, y in enumerate((1300, 1420)):                                       # the jute mats
        g.rect(80 + i * 30, y, 1000 - i * 30, y + 60, (196, 160, 90), INK, 4)
        for x in range(100 + i * 30, 1000 - i * 30, 30):
            g.line([(x, y + 4), (x, y + 56)], (176, 140, 74), 2)
    return g.done()


NEW = {"khet": khet, "chaupal": chaupal, "handpump": handpump, "kachcha_ghar": kachcha_ghar,
       "gaon_school": gaon_school}
HORIZON = {"khet": 1240, "chaupal": 1240, "handpump": 1240, "kachcha_ghar": 1270, "gaon_school": 1240}
OUTDOOR = {"khet", "chaupal", "handpump", "gaon_school"}
WRITTEN = {"chaupal", "gaon_school"}          # writing on them: never mirrored for a reverse shot

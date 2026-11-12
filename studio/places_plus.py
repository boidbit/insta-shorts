"""Richer drawings of the most used places (street, market, office, hospital) and new places (court, dhaba, salon,
mall). The new camera uses these; `CAMERA: classic` keeps the old drawings. Logical 1080 x 1920, people stand
around y = 1700. Drawn with layers (sky / far / window) so the 2.5D look gives them depth too."""
import math
import random

from .backgrounds import G, INK, _floor_perspective, _light_patch


def _loc():                          # (locations imports this module at its end: look its helpers up when drawing)
    from . import locations
    return locations


def _shelf(*a, **k):
    return _loc()._shelf(*a, **k)


def _sign(*a, **k):
    return _loc()._sign(*a, **k)


def _string_lights(*a, **k):
    return _loc()._string_lights(*a, **k)


def _txt(*a, **k):
    return _loc()._txt(*a, **k)
from .util import LH, LW


def _floor_tiles(g, y0, c, line):
    _floor_perspective(g, y0, c, line, (540, 820))
    g.line([(0, y0), (LW, y0)], INK, 5)


def _ceiling_lights(g, y, xs, w=220, col=(255, 252, 236)):
    for x in xs:
        g.rect(x - w / 2, y, x + w / 2, y + 22, col, INK, 3)
    _light_patch(g, [(xs[0] - 260, 1300), (xs[-1] + 260, 1300), (xs[-1] + 360, LH), (xs[0] - 360, LH)],
                 (255, 250, 230), 26, 30)


def _plant(g, x, y, h=180):
    g.poly([(x - 46, y - 90), (x + 46, y - 90), (x + 34, y), (x - 34, y)], (190, 104, 70), INK, 4)
    rnd = random.Random(int(x))
    for i in range(7):
        a = math.radians(-150 + i * 20 + rnd.randint(-8, 8))
        ex, ey = x + h * 0.6 * math.cos(a), y - 90 + h * math.sin(a)
        g.line([(x, y - 90), (ex, ey)], (60, 120, 70), 7)
        g.circle(ex, ey, 20, (80, 150, 84), INK, 2)


# ------------------------------------------------------------------ street
def street(s):
    g = G(s)
    with g.on("sky"):
        g.vgrad(0, 1000, (130, 196, 240), (230, 240, 246))
        g.circle(880, 230, 76, (255, 228, 140))
    rnd = random.Random(11)
    with g.on("far"):                                           # the far skyline, hazy
        x = -30
        while x < LW:
            w, h = rnd.randint(120, 200), rnd.randint(380, 640)
            g.rect(x, 900 - h, x + w, 900, (182, 198, 216))
            for wy in range(900 - h + 40, 880, 60):
                for wx in range(x + 18, x + w - 30, 44):
                    g.rect(wx, wy, wx + 20, wy + 30, (204, 216, 230))
            x += w + rnd.randint(8, 30)
    shops = [("MEDICAL", (60, 160, 110)), ("MOBILE", (70, 110, 200)), ("SWEETS", (230, 120, 50)),
             ("TAILOR", (170, 80, 160))]
    for i, (name, col) in enumerate(shops):                     # a row of shop buildings
        x0 = -10 + i * 275
        x1 = x0 + 268
        g.rect(x0, 420, x1, 1240, ((236, 214, 170), (214, 196, 214), (226, 206, 160), (196, 214, 200))[i], INK, 6)
        for wx in (x0 + 30, x0 + 150):                          # the flats above
            g.rect(wx, 480, wx + 90, 620, (150, 180, 206), INK, 4)
            g.line([(wx + 45, 480), (wx + 45, 620)], INK, 3)
            g.rect(wx - 6, 620, wx + 96, 640, (180, 170, 150), INK, 3)
        g.rect(x0 + 40, 690, x0 + 130, 760, (240, 240, 236), INK, 3)                   # an AC box
        g.line([(x0 + 50, 740), (x0 + 120, 740)], (170, 170, 170), 3)
        _sign(g, max(x0 + 16, 14), 800, min(x1 - 16, LW - 14), 880, name, col, (255, 255, 255), 44)
        g.poly([(x0, 900), (x1, 900), (x1 + 10, 960), (x0 - 10, 960)], col, INK, 4)     # the awning
        for k in range(6):
            xx = x0 + k * (x1 - x0) / 6.0
            g.line([(xx, 900), (xx - 4, 960)], (250, 246, 236), 6)
        g.rect(x0 + 20, 970, x1 - 20, 1240, (90, 96, 104), INK, 5)                     # the open shop
        _shelf(g, x0 + 30, 990, x1 - 30, 1200, 3, "grocery" if i % 2 else "books", seed=i + 3,
               col=(150, 110, 76))
    g.line([(0, 380), (LW, 430)], (40, 40, 44), 3)               # the wires
    g.line([(0, 400), (LW, 470)], (40, 40, 44), 2)
    g.rect(0, 1240, LW, 1380, (206, 200, 188))                   # footpath with a painted kerb
    for x in range(0, LW, 120):
        g.line([(x, 1240), (x - 20, 1380)], (186, 180, 170), 3)
        g.rect(x, 1370, x + 60, 1392, (20, 20, 20))
        g.rect(x + 60, 1370, x + 120, 1392, (250, 210, 40))
    g.line([(0, 1240), (LW, 1240)], INK, 5)
    g.rect(0, 1392, LW, LH, (92, 94, 102))
    for x in range(160, 900, 110):                                # a zebra crossing far side
        g.poly([(x, 1420), (x + 60, 1420), (x + 80, 1500), (x + 10, 1500)], (230, 230, 226))
    for xx in range(-40, LW, 240):
        g.rect(xx, 1760, xx + 130, 1780, (240, 220, 120))
    g.line([(980, 1250), (980, 640)], (60, 60, 64), 14)           # a street lamp and an electric pole
    g.line([(980, 650), (900, 650)], (60, 60, 64), 10)
    g.rrect(880, 640, 920, 676, 10, (255, 236, 160), INK, 4)
    g.note_light(900, 660, 24, (255, 236, 160))
    g.rect(60, 560, 84, 1250, (90, 90, 96), INK, 4)
    g.rect(40, 600, 104, 680, (110, 110, 118), INK, 4)            # the transformer box
    _light_patch(g, [(0, 1250), (LW, 1250), (LW, 1392), (0, 1392)], (255, 240, 200), 30, 20)
    return g.done()


# ------------------------------------------------------------------ market
def market(s):
    g = G(s, color=(250, 232, 196))
    with g.on("sky"):
        g.vgrad(0, 700, (240, 186, 130), (252, 230, 190))
    rnd = random.Random(5)
    with g.on("far"):                                            # buildings behind the stalls
        x = -20
        while x < LW:
            w, h = rnd.randint(150, 230), rnd.randint(360, 560)
            c = ((214, 170, 130), (200, 180, 160), (226, 196, 150), (190, 160, 150))[rnd.randint(0, 3)]
            g.rect(x, 760 - h, x + w, 760, c, INK, 4)
            for wy in range(760 - h + 40, 720, 80):
                g.rect(x + 30, wy, x + w - 30, wy + 34, (150, 120, 100))
            x += w + 6
    _string_lights(g, 0, LW, 560, 50, 18, seed=8)
    g.rect(0, 640, LW, 1300, (214, 168, 128), INK, 6)
    stalls = ((20, (206, 64, 60), "SABZI"), (380, (230, 170, 50), "FRUITS"), (740, (62, 140, 96), "MASALA"))
    for (x, col, name) in stalls:
        w = 320
        _sign(g, x + 30, 660, x + w - 30, 720, name, (250, 246, 236), col, 40)
        for k in range(8):
            g.rect(x + k * w / 8.0, 770, x + (k + 1) * w / 8.0, 880, col if k % 2 == 0 else (250, 246, 236), INK, 3)
            g.circle(x + (k + 0.5) * w / 8.0, 880, w / 16.0, col if k % 2 == 0 else (250, 246, 236), INK, 3)
        g.line([(x, 900), (x, 1300)], INK, 9)
        g.line([(x + w, 900), (x + w, 1300)], INK, 9)
        g.rect(x + 10, 920, x + w - 10, 1150, (120, 84, 56))                             # inside the stall
        for j in range(4):                                                                 # baskets on shelves
            bx = x + 30 + j * 72
            g.ellipse(bx, 990, bx + 60, 1030, (190, 150, 90), INK, 3)
            for k in range(3):
                g.circle(bx + 14 + k * 16, 986, 12, ((214, 64, 56), (110, 176, 84), (240, 150, 50))[(j + k) % 3],
                         INK, 2)
        g.rrect(x + 8, 1150, x + w - 8, 1300, 14, (160, 112, 76), INK, 6)
        for j in range(5):
            cx = x + 40 + j * 58
            g.circle(cx, 1128, 28, ((214, 64, 56), (240, 150, 50), (110, 176, 84), (230, 200, 70))[(j + x // 300) % 4],
                     INK, 4)
        g.circle(x + 50, 976, 16, (255, 236, 150), INK, 4)
        g.note_light(x + 50, 976, 16, (255, 236, 150))
    g.rect(0, 1300, LW, LH, (208, 188, 150))
    g.line([(0, 1300), (LW, 1300)], INK, 5)
    for x, c in ((60, (150, 110, 70)), (960, (170, 130, 80))):                            # sacks on the ground
        g.rrect(x - 50, 1230, x + 50, 1330, 24, c, INK, 4)
        g.ellipse(x - 40, 1222, x + 40, 1246, (230, 210, 150), INK, 3)
    for i in range(7):
        y = 1300 + i * i * 16 + 14
        g.line([(0, y), (LW, y)], (180, 160, 122), 3)
    return g.done()


# ------------------------------------------------------------------ office
def office(s):
    g = G(s, color=(228, 232, 238))
    y_floor = 1280
    g.vgrad(0, y_floor, (236, 238, 242), (210, 216, 226))
    g.rect(0, 0, LW, 120, (244, 244, 246))
    g.line([(0, 120), (LW, 120)], (190, 194, 200), 4)
    g.rect(600, 250, 1040, 900, (255, 255, 255), INK, 8)                                 # a big window, the city
    g.punch(618, 268, 1022, 882)
    with g.on("window"):
        g.vgrad(268, 882, (150, 200, 240), (220, 236, 248), 618, 1022)
        rnd = random.Random(4)
        x = 618
        while x < 1022:
            w, h = rnd.randint(50, 90), rnd.randint(200, 480)
            g.rect(x, 882 - h, min(x + w, 1022), 882, (120, 146, 176), INK, 3)
            for wy in range(882 - h + 20, 860, 40):
                g.rect(x + 10, wy, x + 22, wy + 20, (226, 236, 248))
            x += w + 6
    g.note_window(618, 268, 1022, 882)
    g.line([(820, 268), (820, 882)], INK, 6)
    g.rect(40, 250, 560, 700, (240, 246, 250), (150, 160, 176), 6)                      # a glass partition
    g.rect(40, 420, 560, 470, (200, 210, 224))
    _txt(g, 300, 445, "TEAM AWESOME", 30, (90, 100, 120))
    g.rect(80, 520, 300, 680, (252, 252, 250), INK, 5)                                   # a chart on the board
    for i, h in enumerate((40, 80, 60, 110)):
        g.rect(100 + i * 46, 660 - h, 130 + i * 46, 660, ((90, 160, 230), (230, 110, 80), (110, 190, 120),
                                                         (250, 200, 70))[i])
    g.circle(440, 580, 54, (255, 255, 255), INK, 6)                                      # the clock
    g.line([(440, 580), (440, 544)], INK, 5)
    g.line([(440, 580), (470, 594)], INK, 5)
    _floor_tiles(g, y_floor, (104, 114, 134), (90, 100, 118))
    for x0 in (30, 560):                                                                   # two desks
        g.rrect(x0, 1100, x0 + 470, 1140, 8, (196, 160, 120), INK, 5)
        g.rect(x0 + 20, 1140, x0 + 40, y_floor, (140, 140, 146), INK, 3)
        g.rect(x0 + 430, 1140, x0 + 450, y_floor, (140, 140, 146), INK, 3)
        g.rect(x0 + 120, 980, x0 + 300, 1090, (36, 38, 46), INK, 5)
        g.rect(x0 + 132, 992, x0 + 288, 1078, (110, 180, 230))
        g.rect(x0 + 196, 1090, x0 + 224, 1100, (36, 38, 46))
        g.rect(x0 + 330, 1060, x0 + 400, 1100, (236, 232, 222), INK, 3)                  # files
    g.rect(980, 960, 1050, 1270, (200, 210, 224), INK, 5)                                 # the water cooler
    g.rrect(985, 880, 1045, 960, 14, (150, 200, 240), INK, 4)
    _plant(g, 70, 1270)
    _ceiling_lights(g, 40, (260, 540, 820))
    return g.done()


# ------------------------------------------------------------------ hospital
def hospital(s):
    g = G(s, color=(214, 236, 226))
    y_floor = 1280
    g.vgrad(0, y_floor, (224, 242, 234), (200, 226, 214))
    g.rect(0, 860, LW, 900, (120, 190, 160))                                              # the wall stripe
    g.rect(0, 0, LW, 110, (240, 246, 244))
    _sign(g, 330, 150, 750, 250, "HOSPITAL", (40, 140, 90), (255, 255, 255))
    g.rect(180, 168, 236, 232, (255, 255, 255), INK, 4)                                   # the red cross
    g.rect(200, 176, 216, 224, (220, 40, 40))
    g.rect(188, 192, 228, 208, (220, 40, 40))
    for i, x in enumerate((60, 820)):                                                      # OPD doors
        g.rect(x, 520, x + 200, y_floor, (170, 200, 220), INK, 6)
        g.rect(x + 40, 580, x + 160, 720, (220, 236, 245), INK, 4)
        g.circle(x + 170, 920, 10, (200, 200, 200), INK, 3)
        _sign(g, x + 20, 430, x + 180, 500, "OPD %d" % (i + 1), (250, 250, 250), (40, 120, 80), 34)
    g.rrect(330, 560, 750, 900, 16, (244, 250, 248), INK, 5)                              # the notice board
    _txt(g, 540, 600, "SILENCE PLEASE", 34, (200, 50, 50))
    for k in range(3):
        g.rect(370 + k * 128, 660, 470 + k * 128, 860, ((250, 240, 170), (200, 230, 250), (250, 210, 220))[k],
               INK, 3)
    g.rrect(300, 990, 780, 1080, 12, (236, 236, 232), INK, 5)                             # the reception desk
    g.rect(320, 1080, 760, y_floor, (130, 190, 170), INK, 5)
    _txt(g, 540, 1180, "RECEPTION", 40, (255, 255, 255))
    g.rect(380, 940, 460, 990, (40, 44, 52), INK, 3)
    _floor_tiles(g, y_floor, (220, 224, 224), (196, 202, 202))
    _plant(g, 290, y_floor)
    _ceiling_lights(g, 30, (300, 780))
    return g.done()


# ------------------------------------------------------------------ new places
def court(s):
    """A courtroom: the judge's high bench under the scales of justice, a witness box, the lawyers' tables."""
    g = G(s, color=(196, 160, 118))
    y_floor = 1270
    g.rect(0, 0, LW, y_floor, (206, 172, 128))
    for x in range(0, LW, 120):                                                           # wood panelling
        g.rect(x + 8, 300, x + 112, 860, (190, 152, 108), (160, 120, 80), 4)
    g.rect(0, 860, LW, y_floor, (150, 104, 66))
    g.circle(540, 190, 70, (240, 220, 160), INK, 5)                                       # the scales of justice
    g.line([(540, 140), (540, 236)], INK, 6)
    g.line([(486, 170), (594, 170)], INK, 6)
    for x in (486, 594):
        g.line([(x, 170), (x - 20, 210)], INK, 3)
        g.line([(x, 170), (x + 20, 210)], INK, 3)
        g.ellipse(x - 26, 204, x + 26, 220, (220, 190, 100), INK, 3)
    g.rect(260, 520, 820, 900, (120, 80, 50), INK, 8)                                     # the judge's bench
    g.rect(260, 500, 820, 540, (150, 104, 66), INK, 6)
    g.rect(470, 380, 610, 520, (60, 40, 30), INK, 5)                                      # the high chair back
    _txt(g, 540, 700, "COURT", 60, (240, 220, 160))
    g.rect(40, 700, 220, 1100, (140, 96, 60), INK, 6)                                     # the witness box
    for x in range(60, 220, 36):
        g.line([(x, 720), (x, 1100)], (110, 74, 46), 6)
    g.rect(860, 960, 1060, 1100, (140, 96, 60), INK, 5)                                   # the clerk's table
    _floor_tiles(g, y_floor, (170, 130, 90), (150, 110, 74))
    g.rect(0, 1240, LW, 1270, (120, 80, 50))                                              # the railing
    for x in range(20, LW, 70):
        g.rect(x, 1180, x + 14, 1260, (120, 80, 50))
    g.line([(0, 1180), (LW, 1180)], (120, 80, 50), 12)
    for x in (270, 810):
        g.circle(x, 70, 18, (120, 120, 126), INK, 3)
        g.line([(x - 120, 80), (x + 120, 60)], (150, 150, 156), 8)
    return g.done()


def dhaba(s):
    """A highway dhaba in the evening: a tin-roofed shed, its big signboard in bulbs, a clay tandoor glowing, a
    menu board, trucks far away."""
    g = G(s)
    with g.on("sky"):
        g.vgrad(0, 1000, (250, 150, 90), (120, 80, 130))
    with g.on("far"):
        g.rect(0, 860, LW, 1000, (80, 70, 90))
        for x in (120, 760):                                                              # trucks far away
            g.rect(x, 900, x + 180, 960, (200, 120, 60))
            g.rect(x + 180, 916, x + 230, 960, (220, 200, 90))
            g.circle(x + 40, 966, 12, (30, 30, 30))
            g.circle(x + 190, 966, 12, (30, 30, 30))
    g.rect(0, 1000, LW, 1260, (160, 104, 74))                                             # a low brick wall
    for y in range(1020, 1260, 40):
        g.line([(0, y), (LW, y)], (130, 80, 56), 3)
        for x in range((y // 40 % 2) * 40, LW, 80):
            g.line([(x, y - 40), (x, y)], (130, 80, 56), 3)
    g.line([(0, 1000), (LW, 1000)], INK, 5)
    g.poly([(-20, 380), (LW + 20, 380), (LW, 460), (0, 460)], (160, 170, 176), INK, 6)    # the tin roof
    for x in range(0, LW, 60):
        g.line([(x, 380), (x, 460)], (130, 140, 146), 3)
    for x in (40, 1020):
        g.rect(x, 460, x + 24, 1260, (120, 84, 56), INK, 4)
    _sign(g, 260, 230, 820, 360, "SHER-E-DHABA", (200, 40, 30), (255, 230, 120))
    for x in range(280, 820, 40):                                                          # bulbs round the sign
        g.circle(x, 222, 8, (255, 236, 150))
        g.note_light(x, 222, 8, (255, 236, 150))
    _string_lights(g, 60, 1020, 480, 40, 14, seed=3)
    g.rrect(700, 760, 940, 1080, 18, (170, 100, 60), INK, 6)                               # the tandoor
    g.ellipse(730, 740, 910, 790, (60, 30, 20), INK, 5)
    g.ellipse(760, 750, 880, 780, (255, 150, 60))
    g.note_light(820, 765, 50, (255, 150, 60))
    g.rect(120, 600, 420, 900, (40, 44, 40), (120, 84, 56), 10)                            # the menu board
    for i, item in enumerate(("DAL MAKHANI 120", "PANEER 180", "ROTI 10", "CHAI 15")):
        _txt(g, 270, 650 + i * 64, item, 30, (240, 240, 220))
    g.rect(0, 1260, LW, LH, (170, 140, 100))
    g.line([(0, 1260), (LW, 1260)], INK, 5)
    for i in range(6):
        g.line([(0, 1260 + i * i * 20 + 18), (LW, 1260 + i * i * 20 + 18)], (150, 120, 84), 3)
    g.rect(500, 1080, 600, 1260, (40, 90, 160), INK, 5)                                   # the water drum
    _light_patch(g, [(600, 1260), (1080, 1260), (1080, LH), (500, LH)], (255, 170, 90), 40, 30)
    return g.done()


def salon(s):
    """A barber's salon: the big mirror with bulbs round it, the chair, shelves of bottles, a hairstyle poster."""
    g = G(s, color=(236, 226, 214))
    y_floor = 1280
    g.vgrad(0, y_floor, (240, 232, 220), (220, 206, 190))
    _sign(g, 330, 120, 750, 220, "SALON", (40, 40, 44), (250, 210, 80))
    g.rect(220, 300, 860, 880, (210, 230, 240), INK, 10)                                   # the mirror
    g.poly([(260, 860), (420, 330), (470, 330), (310, 860)], (240, 248, 252))
    g.poly([(500, 860), (620, 330), (650, 330), (530, 860)], (236, 246, 250))
    for x in range(240, 860, 60):                                                          # bulbs round it
        g.circle(x, 300, 10, (255, 240, 170), INK, 2)
        g.note_light(x, 300, 10, (255, 240, 170))
    g.rect(220, 900, 860, 940, (160, 120, 90), INK, 5)                                     # the counter
    for i, x in enumerate(range(260, 840, 60)):                                            # bottles
        h = 50 + (i * 17) % 40
        g.rrect(x, 900 - h, x + 30, 900, 8, ((70, 140, 200), (220, 90, 90), (90, 170, 110), (240, 200, 70))[i % 4],
                INK, 2)
    g.rect(40, 360, 180, 560, (250, 246, 236), INK, 4)                                     # the hairstyle poster
    for k in range(3):
        g.circle(110, 400 + k * 56, 22, (222, 176, 134), INK, 2)
        g.poly([(88, 392 + k * 56), (110, 372 + k * 56), (132, 392 + k * 56)], (40, 30, 30))
    g.rect(900, 380, 1040, 900, (150, 110, 76), INK, 5)                                     # towels on a rack
    for y in range(420, 860, 90):
        g.rect(920, y, 1020, y + 60, ((250, 250, 250), (200, 230, 250))[(y // 90) % 2], INK, 3)
    g.rrect(430, 1000, 650, 1180, 30, (150, 30, 40), INK, 6)                               # the barber's chair
    g.rect(530, 1180, 550, 1260, (150, 150, 156), INK, 3)
    g.ellipse(470, 1250, 610, 1280, (150, 150, 156), INK, 3)
    g.rect(0, y_floor, LW, LH, (240, 240, 236))
    for i in range(0, LW, 90):                                                              # checker floor
        for j, y in enumerate(range(y_floor, LH, 90)):
            if (i // 90 + j) % 2 == 0:
                g.rect(i, y, i + 90, y + 90, (40, 40, 44))
    g.line([(0, y_floor), (LW, y_floor)], INK, 5)
    return g.done()


def mall(s):
    """Inside a shopping mall: shop fronts with glass and SALE signs on two floors, an escalator, a skylight,
    a glossy floor."""
    g = G(s, color=(236, 236, 240))
    y_floor = 1300
    g.rect(0, 0, LW, 120, (210, 220, 236))
    with g.on("window"):
        g.rect(160, 0, 920, 110, (170, 214, 240))
    g.note_window(160, 0, 920, 110)
    for x in range(160, 920, 76):
        g.line([(x, 0), (x, 110)], (120, 130, 150), 4)
    g.rect(0, 120, LW, y_floor, (232, 232, 236))
    g.rect(0, 600, LW, 650, (200, 200, 206), INK, 4)                                      # the upper floor's edge
    g.line([(0, 560), (LW, 560)], (170, 200, 220), 6)                                      # its glass railing
    for x in range(0, LW, 120):
        g.line([(x, 560), (x, 600)], (150, 160, 176), 4)
    shops = ((40, "SALE 50%", (220, 50, 80)), (400, "SHOES", (40, 120, 200)), (760, "GADGETS", (40, 160, 120)))
    for (x, name, col) in shops:
        g.rect(x, 200, x + 300, 540, (250, 250, 252), INK, 5)                              # upstairs
        _sign(g, x + 20, 210, x + 280, 260, name, col, (255, 255, 255), 30)
        g.rect(x + 20, 280, x + 280, 530, (196, 222, 236))
        g.rect(x, 700, x + 300, y_floor - 20, (250, 250, 252), INK, 5)                      # downstairs
        _sign(g, x + 20, 710, x + 280, 770, name, col, (255, 255, 255), 34)
        g.rect(x + 20, 790, x + 280, y_floor - 30, (200, 226, 240))
        for k in range(3):                                                                   # things on display
            g.rrect(x + 40 + k * 80, 1100, x + 100 + k * 80, 1200, 10, (col[0], col[1], col[2]), INK, 3)
        g.poly([(x + 40, 800), (x + 120, 800), (x + 60, 1000), (x + 20, 1000)], (236, 246, 252))
    g.poly([(360, y_floor), (420, y_floor), (700, 650), (640, 650)], (150, 160, 176), INK, 5)   # the escalator
    for k in range(12):
        t_ = k / 12.0
        g.line([(390 + 280 * t_, y_floor - 650 * t_ + 20), (420 + 280 * t_, y_floor - 650 * t_ + 20)], (90, 90, 96), 3)
    g.rect(0, y_floor, LW, LH, (226, 226, 230))
    _floor_tiles(g, y_floor, (226, 226, 230), (206, 206, 212))
    _light_patch(g, [(140, y_floor), (940, y_floor), (1040, LH), (40, LH)], (255, 255, 255), 50, 24)
    _plant(g, 1000, y_floor)
    return g.done()


# ------------------------------------------------------------------ shops (the counter comes as a set object)
def _shop_room(g, wall, floor, y_floor=1280):
    g.vgrad(0, y_floor, wall, tuple(max(0, c - 18) for c in wall))
    g.rect(0, 0, LW, 100, tuple(min(255, c + 12) for c in wall))
    for x in (200, 760):                                                                  # tube lights
        g.rect(x, 110, x + 160, 128, (255, 255, 240), INK, 3)
    g.rect(0, y_floor, LW, LH, floor)
    for i, y in enumerate(range(y_floor + 60, LH, 110)):
        g.line([(0, y), (LW, y)], tuple(max(0, c - 22) for c in floor), 3 + i)
    g.line([(0, y_floor), (LW, y_floor)], INK, 5)


def mithai_shop(s):
    """A sweet shop: shelves of sweet boxes, glass jars of laddoos, a board of today's sweets, lights."""
    g = G(s, color=(246, 226, 190))
    _shop_room(g, (246, 226, 190), (200, 170, 130))
    _sign(g, 200, 150, 880, 260, "MITHAI BHANDAR", (200, 40, 50), (255, 230, 120))
    _string_lights(g, 0, LW, 280, 40, 16, seed=12)
    for (x0, x1) in ((40, 500), (580, 1040)):                                             # shelves of boxes
        g.rect(x0, 400, x1, 1000, (150, 104, 66), INK, 6)
        g.rect(x0 + 14, 414, x1 - 14, 986, (120, 84, 56))
        for r, y in enumerate((540, 700, 860)):
            g.rect(x0 + 14, y, x1 - 14, y + 10, (150, 104, 66))
            for k in range(5):
                bx = x0 + 30 + k * 90
                col = ((240, 120, 50), (230, 60, 90), (250, 200, 60), (240, 240, 230), (90, 160, 90))[(k + r) % 5]
                g.rect(bx, y - 90, bx + 70, y, col, INK, 3)
                g.rect(bx + 10, y - 60, bx + 60, y - 50, (255, 255, 255))
    for i, col in enumerate(((250, 200, 60), (240, 150, 60), (250, 250, 240))):           # jars of laddoos on top
        x = 120 + i * 140
        g.rrect(x, 330, x + 90, 400, 14, (220, 236, 244), INK, 3)
        for k in range(3):
            g.circle(x + 24 + k * 22, 378, 12, col, INK, 2)
    g.rrect(700, 300, 1000, 400, 10, (40, 70, 60), INK, 5)                                # today's special
    _txt(g, 850, 350, "AAJ: RASGULLA", 30, (255, 255, 255))
    return g.done()


def mobile_shop(s):
    """A mobile phone shop: a wall of phones, an offer poster, earphones hanging, a TV playing an ad."""
    g = G(s, color=(230, 238, 248))
    _shop_room(g, (230, 238, 248), (190, 196, 206))
    _sign(g, 220, 150, 860, 260, "MOBILE POINT", (30, 80, 170), (255, 255, 255))
    g.rect(60, 330, 620, 1000, (250, 250, 252), INK, 6)                                   # the wall of phones
    for r in range(4):
        for k in range(6):
            x, y = 90 + k * 88, 360 + r * 156
            g.rrect(x, y, x + 60, y + 118, 10, (40, 44, 52), INK, 3)
            g.rect(x + 6, y + 10, x + 54, y + 100, ((120, 190, 235), (240, 140, 160), (150, 220, 160),
                                                     (250, 210, 120))[(k + r) % 4])
    g.rect(680, 330, 1020, 560, (40, 40, 44), INK, 6)                                     # the TV ad
    g.rect(696, 346, 1004, 544, (90, 160, 240))
    _txt(g, 850, 445, "5G SALE", 52, (255, 255, 255))
    g.rect(700, 620, 1000, 820, (250, 220, 70), INK, 5)                                   # the offer poster
    _txt(g, 850, 690, "50% OFF", 50, (200, 30, 40))
    _txt(g, 850, 760, "EMI 0%", 34, (40, 40, 44))
    for k in range(5):                                                                     # earphones on hooks
        x = 700 + k * 64
        g.line([(x, 860), (x, 880)], INK, 4)
        g.line([(x - 14, 880), (x - 18, 960), (x, 990), (x + 18, 960), (x + 14, 880)], (240, 240, 240), 4)
    return g.done()


def medical_store(s):
    """A chemist's shop: a green cross, shelves full of medicine boxes, a fridge, a weighing machine."""
    g = G(s, color=(236, 246, 240))
    _shop_room(g, (236, 246, 240), (206, 214, 210))
    _sign(g, 200, 150, 760, 260, "MEDICAL STORE", (30, 130, 80), (255, 255, 255))
    g.rect(840, 150, 900, 270, (40, 170, 90))                                             # the green cross
    g.rect(810, 180, 930, 240, (40, 170, 90))
    g.rect(40, 330, 760, 1010, (240, 240, 236), INK, 6)                                   # shelves of medicines
    for r, y in enumerate((470, 620, 770, 920)):
        g.rect(54, y, 746, y + 10, (190, 190, 186))
        x = 70
        k = 0
        while x < 720:
            w = 40 + (k * 13 + r * 7) % 30
            h = 60 + (k * 11 + r * 5) % 50
            col = ((250, 250, 250), (220, 236, 250), (250, 236, 210), (230, 250, 230))[(k + r) % 4]
            g.rect(x, y - h, x + w, y, col, INK, 2)
            g.rect(x + 6, y - h + 12, x + w - 6, y - h + 22, ((220, 60, 60), (60, 140, 220), (60, 160, 90))[k % 3])
            x += w + 8
            k += 1
    g.rect(800, 420, 1040, 1010, (250, 250, 252), INK, 6)                                 # the fridge
    g.rect(816, 436, 1024, 994, (210, 236, 250))
    _txt(g, 920, 480, "INSULIN", 28, (30, 80, 140))
    for y in (560, 700, 840):
        g.line([(816, y), (1024, y)], (170, 190, 210), 4)
    return g.done()


RICH = {"street": street, "market": market, "office": office, "hospital": hospital}
SHOPS = {"mithai_shop": "counter_mithai", "mobile_shop": "counter_mobile", "medical_store": "counter_medical"}
NEW = {"court": court, "dhaba": dhaba, "salon": salon, "mall": mall, "mithai_shop": mithai_shop,
       "mobile_shop": mobile_shop, "medical_store": medical_store}
HORIZON = {"court": 1270, "dhaba": 1260, "salon": 1280, "mall": 1300, "mithai_shop": 1280, "mobile_shop": 1280,
           "medical_store": 1280}

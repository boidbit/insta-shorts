"""Two places drawn for the kirdaar: Doctor Paglet's village clinic and the Gappcast podcast studio.

Logical 1080 x 1920, drawn in the studio's own flat style (so the characters sit in them naturally). The furniture
people sit on is painted where the script's spots put them (studio.script.PLACE_SPOTS): the podcast's two
armchairs, and in the clinic the doctor's chair behind the desk (the desk itself is a set piece, so it stands in
front of him) and the patient's chair. Each also has a hand-made 2.5D set (style25d/scenery_studio)."""
import random

from .backgrounds import G, INK
from .util import LH, LW


def _txt(*a, **k):
    from . import locations
    return locations._txt(*a, **k)


def _tiles(g, y0, base=(196, 196, 192), line=(170, 170, 166)):
    """A tiled floor going back to the wall: rows closer together near the wall, the joints fanning out."""
    g.rect(0, y0, LW, LH, base)
    for i in range(1, 10):
        y = y0 + i * i * 8 + 10
        g.line([(0, y), (LW, y)], line, 3)
    for x in range(-600, LW + 700, 180):
        g.line([(540 + (x - 540) * 0.35, y0), (x, LH)], line, 3)
    g.line([(0, y0), (LW, y0)], INK, 5)


def _planks(g, y0, base=(150, 92, 60), line=(120, 70, 44)):
    g.rect(0, y0, LW, LH, base)
    for i in range(1, 9):
        y = y0 + i * i * 9 + 12
        g.line([(0, y), (LW, y)], line, 3)
    rnd = random.Random(4)
    for i in range(1, 9):
        y = y0 + i * i * 9 + 12
        for _ in range(3):
            x = rnd.randint(0, LW)
            g.line([(x, y - i * 6 - 6), (x, y)], line, 2)
    g.line([(0, y0), (LW, y0)], INK, 5)


def _plant(g, x, y, s=1.0):
    g.poly([(x - 40 * s, y - 70 * s), (x + 40 * s, y - 70 * s), (x + 30 * s, y), (x - 30 * s, y)], (196, 110, 70), INK, 4)
    for dx, dy, r in ((-30, -120, 34), (10, -150, 38), (40, -110, 32), (-5, -95, 30)):
        g.circle(x + dx * s, y + dy * s, r * s, (90, 160, 80), INK, 4)


def clinic(s):
    """Doctor Paglet's village clinic: cream walls with a green dado, the open door onto the village lane, the red
    cross, an anatomy chart, the teal medicine cabinet full of bottles, a steel trolley with the first-aid box,
    the tube light, the fan, his sign "DR. PAGLET  M.B.B.S. (Try kiya)", a tiled floor. The desk (a set piece)
    and the chairs stand on the floor."""
    g = G(s, color=(238, 228, 200))
    y_floor = 1270
    g.rect(0, 0, LW, y_floor, (240, 230, 204))                                 # the cream wall
    g.rect(0, 860, LW, y_floor, (120, 176, 140))                               # the green dado
    g.line([(0, 860), (LW, 860)], INK, 5)
    g.rect(0, 0, LW, 90, (226, 214, 186))                                      # the ceiling's edge
    g.line([(0, 90), (LW, 90)], (200, 188, 160), 4)
    # the open door onto the lane (sunlight outside)
    g.rect(0, 300, 190, y_floor, (60, 120, 150), INK, 6)
    g.rect(20, 330, 170, y_floor, (190, 220, 240))
    g.rect(20, 900, 170, y_floor, (214, 186, 140))                             # the lane
    g.rect(40, 640, 150, 900, (226, 196, 150), INK, 3)                          # a hut across it
    g.poly([(30, 640), (95, 560), (160, 640)], (180, 100, 70), INK, 3)
    g.circle(150, 470, 60, (110, 170, 90), INK, 3)                              # a tree
    g.note_light(100, 800, 260, (255, 240, 200))
    # the red cross and the anatomy chart
    g.rect(260, 400, 400, 540, (250, 246, 236), (120, 80, 50), 8)
    g.rect(312, 420, 348, 520, (210, 40, 40))
    g.rect(280, 452, 380, 488, (210, 40, 40))
    g.rect(470, 330, 700, 640, (246, 238, 214), (120, 80, 50), 8)
    g.circle(585, 380, 26, (236, 180, 140), INK, 3)                             # the body on the chart
    g.rrect(555, 405, 615, 520, 20, (236, 180, 140), INK, 3)
    g.ellipse(570, 430, 600, 470, (220, 90, 90))                                # heart and lungs
    g.ellipse(558, 420, 578, 470, (230, 140, 150))
    g.ellipse(592, 420, 612, 470, (230, 140, 150))
    g.line([(570, 520), (562, 600)], (236, 180, 140), 14)
    g.line([(600, 520), (608, 600)], (236, 180, 140), 14)
    for y in range(350, 620, 36):
        g.line([(490, y), (530, y)], (170, 160, 140), 3)
        g.line([(640, y), (680, y)], (170, 160, 140), 3)
    # his sign
    g.rect(240, 160, 840, 250, (250, 246, 230), (60, 110, 120), 6)
    _txt(g, 540, 190, "DR. PAGLET", 40, (40, 90, 110))
    _txt(g, 540, 230, "M.B.B.S. (Try kiya)", 26, (200, 60, 60))
    # the tube light
    g.rrect(300, 286, 720, 306, 10, (250, 252, 255), INK, 4)
    g.note_light(510, 300, 260, (240, 250, 255))
    # the medicine cabinet
    g.rect(780, 330, 1080, 1180, (90, 150, 140), INK, 6)
    g.rect(800, 350, 1060, 860, (200, 230, 226), INK, 4)
    rnd = random.Random(11)
    for row, y in enumerate((470, 600, 730, 856)):
        g.line([(800, y), (1060, y)], (80, 130, 120), 6)
        x = 812
        while x < 1040:
            w = rnd.choice((22, 28, 34))
            h = rnd.choice((50, 64, 80))
            col = rnd.choice(((250, 250, 246), (240, 200, 90), (230, 120, 90), (130, 170, 220), (200, 140, 90)))
            g.rect(x, y - h, x + w, y, col, INK, 2)
            x += w + 8
    g.line([(930, 350), (930, 860)], INK, 4)
    g.rect(800, 880, 1060, 1160, (80, 136, 126), INK, 4)
    g.circle(915, 1020, 8, (220, 200, 120), INK, 2)
    g.circle(945, 1020, 8, (220, 200, 120), INK, 2)
    g.rect(840, 270, 960, 330, (240, 236, 226), INK, 4)                         # a first-aid box on top
    g.rect(892, 282, 908, 318, (210, 40, 40))
    g.rect(882, 292, 918, 308, (210, 40, 40))
    _plant(g, 1010, 330, 0.8)
    # the steel trolley with the first-aid box, a steel dabba and a sanitizer
    g.rect(250, 960, 470, 980, (190, 196, 202), INK, 4)
    g.rect(250, 1110, 470, 1130, (190, 196, 202), INK, 4)
    for x in (256, 464):
        g.line([(x, 960), (x, 1220)], (150, 156, 162), 6)
    for x in (262, 458):
        g.circle(x, 1232, 12, (60, 60, 64), INK, 3)
    g.rect(280, 1030, 440, 1110, (246, 246, 242), INK, 4)
    g.rect(348, 1048, 372, 1094, (210, 40, 40))
    g.rect(336, 1060, 384, 1082, (210, 40, 40))
    g.rrect(290, 900, 360, 960, 10, (200, 204, 210), INK, 3)
    g.rect(400, 880, 430, 960, (240, 240, 250), INK, 3)
    g.rect(408, 862, 422, 880, (80, 140, 200), INK, 2)
    g.rrect(500, 1110, 570, 1250, 12, (190, 196, 202), INK, 4)                 # the dustbin
    _plant(g, 230, 1250, 0.9)
    _tiles(g, y_floor)
    g.note_light(540, 1500, 380, (255, 248, 230))
    return g.done()


def podcast(s):
    """The Gappcast studio: a dark purple wall with acoustic foam, the glowing neon mic and GAPPCAST under it,
    shelves with books, a toy auto, a radio, a little India Gate and hanging plants, a pendant lamp, two armchairs
    (yellow on the left for the host, teal on the right for the guest), the round table with two boom mics, mugs
    and headphones, a jute rug on a wooden floor."""
    g = G(s, color=(66, 48, 84))
    y_floor = 1300
    g.rect(0, 0, LW, y_floor, (70, 52, 90))
    for x0 in (0, 860):                                                         # acoustic foam panels
        for i in range(5):
            x = x0 + i * 44
            g.rect(x, 140, x + 36, 1040, (52, 38, 66), (40, 28, 52), 2)
    for x0 in (300, 640):
        for i in range(3):
            x = x0 + i * 46
            g.rect(x, 260, x + 38, 760, (54, 40, 70), (40, 28, 52), 2)
    # the neon mic and its glow
    g.note_light(540, 520, 260, (255, 170, 60))
    g.circle(540, 520, 130, None, (255, 176, 60), 12)
    g.rrect(510, 430, 570, 540, 30, None, (255, 196, 90), 10)
    g.line([(490, 520), (490, 540), (540, 590), (590, 540), (590, 520)], (255, 196, 90), 9)
    g.line([(540, 590), (540, 630)], (255, 196, 90), 9)
    for dx in (-200, 200):
        for dy in (-40, 0, 40):
            x = 540 + dx
            g.line([(x - (20 if dx < 0 else -20), 520 + dy), (x, 520 + dy * 1.2)], (255, 176, 60), 7)
    _txt(g, 540, 720, "GAPPCAST", 54, (255, 196, 90))
    # shelves with their things (left and right)
    for (x0, x1) in ((20, 290), (790, 1060)):
        for y in (420, 640):
            g.rect(x0, y, x1, y + 18, (150, 96, 60), INK, 4)
            g.note_light((x0 + x1) / 2, y + 30, 120, (255, 190, 100))
    for i, col in enumerate(((220, 80, 60), (240, 190, 70), (80, 140, 200), (240, 240, 230), (200, 110, 60))):
        g.rect(160 + i * 24, 520, 182 + i * 24, 640, col, INK, 2)               # books
    g.rrect(40, 340, 170, 420, 16, (240, 200, 60), INK, 4)                      # the toy auto
    g.rect(60, 330, 150, 350, (60, 140, 80), INK, 3)
    g.circle(70, 420, 14, (40, 40, 44), INK, 2)
    g.circle(140, 420, 14, (40, 40, 44), INK, 2)
    g.rrect(810, 560, 960, 640, 10, (170, 110, 60), INK, 4)                     # the radio
    g.circle(850, 600, 24, (220, 200, 150), INK, 3)
    for x in range(890, 950, 12):
        g.line([(x, 576), (x, 624)], (110, 70, 40), 3)
    g.rect(960, 320, 1040, 420, (226, 170, 110), INK, 4)                        # a little India Gate
    g.rect(984, 360, 1016, 420, (70, 52, 90))
    g.circle(860, 380, 28, (255, 214, 140), INK, 3)                             # an Edison bulb
    g.note_light(860, 380, 70, (255, 200, 110))
    for (x, y) in ((40, 300), (1030, 260)):                                     # hanging plants
        for i in range(6):
            g.circle(x + (i % 2) * 20 - 10, y + i * 46, 22, (96, 170, 80), INK, 3)
    _plant(g, 120, 1250, 0.9)
    _plant(g, 960, 1250, 0.9)
    # the floor lamp (left)
    g.line([(80, 1250), (80, 900)], (110, 80, 50), 8)
    g.poly([(30, 900), (130, 900), (110, 820), (50, 820)], (246, 220, 170), INK, 4)
    g.note_light(80, 880, 140, (255, 220, 160))
    # the pendant lamp
    g.line([(540, 0), (540, 120)], (30, 24, 36), 6)
    g.poly([(430, 210), (650, 210), (600, 120), (480, 120)], (30, 28, 34), INK, 5)
    g.ellipse(470, 196, 610, 226, (255, 230, 150))
    g.note_light(540, 260, 240, (255, 210, 130))
    _planks(g, y_floor)
    g.ellipse(80, 1430, 1000, 1760, (210, 170, 120), (160, 120, 80), 4)         # the jute rug
    for r in (0.8, 0.6, 0.4):
        g.ellipse(540 - 460 * r, 1595 - 165 * r, 540 + 460 * r, 1595 + 165 * r, None, (184, 144, 96), 3)
    # the armchairs: yellow (host, left), teal (guest, right); the seat top at y ~1330, the legs down to 1480
    for cx, col, dark in ((170, (236, 186, 60), (200, 150, 40)), (910, (60, 160, 160), (40, 126, 128))):
        g.line([(cx - 110, 1420), (cx - 120, 1490)], (110, 70, 40), 10)
        g.line([(cx + 110, 1420), (cx + 120, 1490)], (110, 70, 40), 10)
        g.rrect(cx - 150, 1040, cx + 150, 1340, 60, dark, INK, 6)               # the back
        g.rrect(cx - 170, 1290, cx + 170, 1430, 40, col, INK, 6)                # the seat
        g.rrect(cx - 190, 1180, cx - 120, 1420, 30, col, INK, 6)                # the arms
        g.rrect(cx + 120, 1180, cx + 190, 1420, 30, col, INK, 6)
        g.rrect(cx - 60 if cx < 540 else cx - 40, 1110, cx + 40 if cx < 540 else cx + 60, 1220, 24,
                (220, 100, 60), INK, 4)                                         # the cushion
    # the round table with the boom mics, the mugs, a bottle and the headphones
    g.line([(540, 1330), (540, 1500)], (120, 76, 46), 12)
    g.line([(460, 1500), (620, 1500)], (120, 76, 46), 10)
    g.ellipse(400, 1300, 680, 1360, (160, 100, 60), INK, 5)
    for sx in (-1, 1):
        bx = 540 + sx * 120
        g.line([(bx, 1310), (bx + sx * 40, 1150), (bx + sx * 110, 1110)], (40, 40, 46), 9)
        g.rrect(bx + sx * 110 - 24, 1060, bx + sx * 110 + 24, 1140, 20, (36, 36, 40), INK, 4)
    for x in (470, 610):
        g.rrect(x - 22, 1270, x + 22, 1314, 8, (246, 242, 236), INK, 3)
    g.rrect(525, 1200, 555, 1312, 8, (190, 196, 204), INK, 3)
    g.ellipse(500, 1298, 580, 1322, (40, 40, 46), INK, 3)
    return g.done()


NEW = {"clinic": clinic, "podcast": podcast}
HORIZON = {"clinic": 1270, "podcast": 1300}
WRITTEN = {"clinic", "podcast"}          # their signs: never mirrored for a reverse angle

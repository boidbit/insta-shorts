"""Everyday places for the Nov 2026 stories: the flat's front door, the park, the wedding buffet, the lift, an ATM,
a petrol pump, a traffic signal, a restaurant, an interview room, a call center and a startup office.

Logical 1080 x 1920, the people stand around y = 1700; drawn with the layer hooks (sky / far / window) so the 2.5D
look gives them depth by itself (studio.style25d.autoset)."""
import random

from .backgrounds import G, INK, _floor_perspective, _light_patch
from .util import LH, LW


def _loc():
    from . import locations
    return locations


def _sign(*a, **k):
    return _loc()._sign(*a, **k)


def _txt(*a, **k):
    return _loc()._txt(*a, **k)


def _plus():
    from . import places_plus
    return places_plus


def _tiles(g, y0, c, line):
    _floor_perspective(g, y0, c, line, (540, 820))
    g.line([(0, y0), (LW, y0)], INK, 5)


def _tree(g, x, y, r=120, leaf=(96, 168, 92)):
    g.rect(x - 18, y - r, x + 18, y + 60, (110, 80, 54), INK, 5)
    for dx, dy, rr in ((-r * 0.6, -r * 1.1, r * 0.7), (r * 0.5, -r * 1.2, r * 0.75), (0, -r * 1.7, r * 0.8)):
        g.circle(x + dx, y + dy, rr, leaf, INK, 5)


# ------------------------------------------------------------------ home
def ghar_darwaza(s):
    """The landing outside a flat: the front door with a nameplate and a bell, a shoe rack, a toran over the door,
    the stairs going up on the right. Where the relatives, the delivery boy and the neighbour turn up."""
    g = G(s, color=(232, 222, 196))
    y_floor = 1280
    g.rect(0, 0, LW, y_floor, (232, 222, 196))
    g.rect(0, 0, LW, 120, (214, 202, 172))
    g.rect(150, 300, 590, y_floor, (150, 96, 56), INK, 8)                    # the door frame
    g.rect(184, 334, 556, y_floor, (176, 112, 64), INK, 5)                   # the door
    for (x0, y0, x1, y1) in ((220, 380, 520, 700), (220, 760, 520, 1180)):
        g.rect(x0, y0, x1, y1, (164, 102, 58), (120, 74, 40), 4)
    g.circle(500, 820, 14, (220, 190, 80), INK, 4)                           # the handle
    g.rect(306, 450, 434, 470, (60, 60, 66), INK, 3)                         # the peep-hole plate
    g.circle(370, 500, 10, (40, 40, 44), INK, 3)
    _sign(g, 610, 560, 820, 630, "SHARMA", (240, 236, 220), (60, 40, 30), 34)  # the nameplate
    g.rect(630, 680, 680, 740, (240, 240, 236), INK, 4)                      # the bell
    g.circle(655, 710, 12, (210, 60, 50), INK, 3)
    for i in range(9):                                                       # the toran of mango leaves and marigold
        x = 170 + i * 50
        g.poly([(x, 300), (x + 20, 300), (x + 10, 350)], (80, 150, 70), INK, 2)
        g.circle(x + 25, 306, 10, (246, 150, 40), INK, 2)
    g.rect(40, 1100, 140, y_floor, (130, 90, 56), INK, 5)                    # the shoe rack with chappals
    for y in (1150, 1210):
        g.line([(40, y), (140, y)], INK, 4)
        g.rect(50, y - 26, 84, y - 6, (200, 70, 60), INK, 2)
        g.rect(92, y - 26, 128, y - 6, (60, 90, 170), INK, 2)
    for i in range(8):                                                       # the stairs going up on the right
        x0, y0 = 760 + i * 40, y_floor - i * 70
        g.rect(x0, y0 - 70, LW, y0, (200, 196, 188), INK, 4)
    g.line([(760, 1110), (1080, 650)], (90, 90, 96), 8)                      # the railing
    for i in range(6):
        g.line([(780 + i * 52, 1080 - i * 75), (780 + i * 52, 1180 - i * 75)], (90, 90, 96), 4)
    g.rect(0, y_floor, LW, LH, (204, 196, 186))
    _tiles(g, y_floor, (204, 196, 186), (180, 172, 160))
    g.rect(240, y_floor + 10, 500, y_floor + 60, (170, 60, 60), INK, 4)      # the door mat
    _txt(g, 370, y_floor + 36, "WELCOME", 26, (240, 220, 200))
    return g.done()


def lift(s):
    """Inside a lift: steel walls, the button panel with a floor display, a mirror at the back, the doors shut."""
    g = G(s, color=(196, 200, 206))
    y_floor = 1300
    g.vgrad(0, y_floor, (214, 218, 224), (176, 182, 190))
    for x in range(0, LW, 180):                                              # brushed steel panels
        g.rect(x + 6, 140, x + 174, y_floor - 20, None, (150, 156, 166), 4)
    g.rect(330, 260, 750, 1000, (200, 222, 232), INK, 6)                     # the mirror at the back
    g.line([(380, 320), (480, 420)], (240, 250, 252), 8)
    g.rect(840, 420, 990, 1040, (150, 156, 166), INK, 6)                     # the button panel
    g.rect(860, 440, 970, 520, (20, 24, 28), INK, 3)
    _txt(g, 915, 482, "7", 56, (250, 80, 60))
    for i in range(10):
        bx, by = 880 + (i % 2) * 70, 570 + (i // 2) * 90
        g.circle(bx, by, 26, (224, 226, 230), INK, 3)
        _txt(g, bx, by, str(10 - i), 26, (60, 60, 66))
    g.rect(0, 0, LW, 140, (230, 232, 236))                                   # the ceiling light
    g.rect(240, 60, 840, 110, (255, 252, 230), INK, 4)
    _light_patch(g, [(160, 140), (920, 140), (1080, 1300), (0, 1300)], (255, 250, 220), 30)
    g.rect(0, y_floor, LW, LH, (120, 120, 126))
    for x in range(0, LW, 60):
        g.line([(x, y_floor), (x - 40, LH)], (104, 104, 110), 3)
    g.line([(0, y_floor), (LW, y_floor)], INK, 5)
    _sign(g, 60, 200, 300, 260, "MAX 8 PERSONS", (240, 240, 236), (60, 60, 66), 24)
    return g.done()


# ------------------------------------------------------------------ out and about
def park(s):
    """The colony park in the morning: a walking track, benches, trees, a slide and a swing, a lamp post, the
    flats behind the hedge. Morning-walk uncles, yoga, couples, the bench gossip."""
    g = G(s)
    _loc()._sky(g, (150, 206, 240), (236, 242, 236), 1000)
    with g.on("far"):
        _loc()._buildings(g, 1000, seed=11, h=(300, 560), cols=[(228, 214, 190), (210, 220, 228), (236, 206, 180)])
    with g.on("mid"):
        g.rect(0, 960, LW, 1060, (70, 140, 70), INK, 4)                      # the hedge
        for x in range(0, LW, 60):
            g.circle(x + 30, 966, 34, (80, 152, 76), INK, 3)
    for x, r in ((120, 130), (930, 150)):
        _tree(g, x, 1050, r)
    g.rect(0, 1060, LW, LH, (120, 186, 96))                                  # the grass
    g.poly([(0, 1300), (LW, 1240), (LW, 1360), (0, 1430)], (214, 186, 150), INK, 4)   # the walking track
    g.rect(330, 1120, 640, 1150, (150, 100, 60), INK, 4)                     # a bench
    g.rect(330, 1070, 640, 1100, (150, 100, 60), INK, 4)
    for x in (350, 620):
        g.rect(x - 8, 1150, x + 8, 1200, (70, 70, 76), INK, 3)
    g.line([(700, 1200), (760, 1020), (800, 1020)], (220, 70, 60), 10)      # the slide
    g.line([(760, 1020), (760, 1200)], (60, 60, 66), 8)
    g.poly([(800, 1020), (880, 1180), (900, 1172), (814, 1010)], (240, 200, 60), INK, 4)
    g.line([(170, 1000), (170, 1210)], (60, 60, 66), 8)                      # the lamp post
    g.circle(170, 990, 22, (250, 240, 200), INK, 4)
    rnd = random.Random(5)
    for _ in range(26):                                                      # flowers in the grass
        x, y = rnd.randint(0, LW), rnd.randint(1450, LH - 30)
        g.circle(x, y, 7, rnd.choice([(240, 90, 90), (250, 220, 70), (240, 240, 240)]))
    g.line([(0, 1060), (LW, 1060)], INK, 4)
    return g.done()


def atm(s):
    """An ATM cabin: the machine with its screen and keypad, the glass door with the bank's sign, a guard's stool."""
    g = G(s, color=(214, 226, 236))
    y_floor = 1290
    g.rect(0, 0, LW, y_floor, (226, 234, 240))
    g.rect(0, 0, LW, 230, (30, 90, 160))
    _txt(g, 540, 120, "24x7 ATM", 90, (255, 255, 255))
    g.rect(360, 420, 740, y_floor, (60, 66, 76), INK, 6)                     # the machine
    g.rect(400, 470, 700, 700, (20, 30, 40), INK, 5)
    g.rect(414, 484, 686, 686, (60, 150, 210))
    _txt(g, 550, 560, "Insert Card", 34, (255, 255, 255))
    _txt(g, 550, 620, "Balance: Rs 47", 28, (255, 236, 160))
    g.rect(450, 760, 650, 940, (120, 126, 136), INK, 4)                      # the keypad
    for i in range(12):
        g.rect(470 + (i % 3) * 60, 776 + (i // 3) * 40, 510 + (i % 3) * 60, 806 + (i // 3) * 40, (220, 224, 230), INK, 2)
    g.rect(470, 980, 630, 1010, (20, 20, 24), INK, 3)                        # the cash slot
    g.rect(40, 300, 300, y_floor, (200, 226, 236), INK, 6)                   # the glass door
    g.line([(80, 340), (200, 460)], (240, 250, 252), 8)
    g.rect(800, 1080, 940, 1110, (130, 90, 56), INK, 4)                      # the guard's stool (empty)
    g.rect(820, 1110, 836, y_floor, (90, 90, 96), INK, 3)
    g.rect(904, 1110, 920, y_floor, (90, 90, 96), INK, 3)
    _sign(g, 780, 420, 1040, 500, "CCTV ON", (240, 60, 50), (255, 255, 255), 32)
    _tiles(g, y_floor, (220, 222, 226), (196, 198, 204))
    g.rect(820, y_floor + 20, 1000, y_floor + 120, (90, 90, 96), INK, 4)    # the bin, full of slips
    for i in range(5):
        g.rect(830 + i * 32, y_floor + 6 - (i % 2) * 10, 856 + i * 32, y_floor + 30, (250, 250, 246), INK, 2)
    return g.done()


def petrol_pump(s):
    """A petrol pump: the canopy with its lights, two dispensers with their meters, the price board, the road."""
    g = G(s)
    _loc()._sky(g, (140, 196, 236), (232, 238, 240), 1100)
    with g.on("far"):
        _loc()._buildings(g, 1080, seed=3, h=(200, 420), cols=[(220, 210, 196), (200, 210, 220)])
    g.rect(0, 280, LW, 400, (250, 250, 248), INK, 6)                         # the canopy
    g.rect(0, 380, LW, 420, (220, 40, 40), INK, 4)
    _txt(g, 540, 340, "DESI PETROLEUM", 64, (220, 40, 40))
    for x in (180, 540, 900):
        g.rect(x - 70, 420, x + 70, 440, (255, 252, 230), INK, 3)
    for x in (80, 1000):                                                     # the pillars
        g.rect(x - 24, 420, x + 24, 1250, (240, 240, 236), INK, 5)
    for x in (300, 780):                                                     # the dispensers
        g.rect(x - 90, 820, x + 90, 1250, (240, 240, 236), INK, 6)
        g.rect(x - 90, 820, x + 90, 870, (220, 40, 40), INK, 4)
        g.rect(x - 64, 900, x + 64, 1000, (20, 24, 28), INK, 4)
        _txt(g, x, 930, "Rs 0000", 26, (90, 240, 120))
        _txt(g, x, 975, "0.00 L", 24, (90, 240, 120))
        g.line([(x + 90, 1050), (x + 140, 1100), (x + 130, 1200)], INK, 9)  # the hose
    g.rect(470, 560, 610, 760, (30, 34, 40), INK, 5)                         # the price board
    _txt(g, 540, 600, "PETROL", 26, (255, 255, 255))
    _txt(g, 540, 650, "107.48", 40, (250, 210, 60))
    _txt(g, 540, 700, "DIESEL", 26, (255, 255, 255))
    _txt(g, 540, 740, "94.27", 34, (250, 210, 60))
    g.rect(0, 1250, LW, LH, (120, 120, 126))
    for x in range(-40, LW, 160):
        g.rect(x, 1500, x + 90, 1520, (240, 240, 236))
    g.line([(0, 1250), (LW, 1250)], INK, 5)
    return g.done()


def signal(s):
    """A busy chowk at the red light: the signal on its pole (red, a countdown), the zebra crossing, shops and a
    flyover behind, a hoarding. Beggars, hawkers, the bike that jumps the light."""
    g = G(s)
    _loc()._sky(g, (150, 200, 236), (236, 236, 230), 1000)
    with g.on("far"):
        _loc()._buildings(g, 980, seed=8, h=(360, 700))
        g.rect(0, 760, LW, 820, (190, 190, 186), INK, 5)                     # the flyover
        for x in (160, 540, 920):
            g.rect(x - 30, 820, x + 30, 980, (176, 176, 172), INK, 4)
    with g.on("mid"):
        g.rect(120, 980, 960, 1120, (220, 200, 160), INK, 5)                 # the shop front across the road
        for i, (t_, c) in enumerate((("CHAI", (230, 120, 60)), ("PAAN", (80, 160, 90)), ("MOBILE", (60, 110, 190)))):
            _sign(g, 150 + i * 270, 1000, 380 + i * 270, 1060, t_, c, (255, 255, 255), 30)
    g.rect(0, 1120, LW, LH, (96, 96, 102))                                   # the road
    for i in range(7):                                                       # the zebra crossing
        g.rect(80 + i * 130, 1330, 160 + i * 130, 1440, (240, 240, 236))
    g.rect(0, 1120, LW, 1150, (200, 196, 186), INK, 4)                       # the far footpath
    g.rect(960, 640, 984, 1240, (60, 60, 66), INK, 4)                        # the signal pole
    g.rect(900, 520, 1044, 900, (30, 32, 36), INK, 5)
    for i, c in enumerate(((240, 50, 40), (70, 60, 40), (40, 70, 40))):
        g.circle(972, 580 + i * 110, 42, c, INK, 4)
    g.note_light(972, 580, 90, (255, 80, 60))
    g.rect(900, 900, 1044, 980, (20, 20, 24), INK, 4)                        # the countdown
    _txt(g, 972, 940, "88", 52, (240, 50, 40))
    g.rect(60, 420, 520, 640, (250, 236, 200), INK, 6)                       # a hoarding
    _txt(g, 290, 490, "SALE! SALE!", 52, (220, 40, 40))
    _txt(g, 290, 570, "EMI sirf Rs 999", 36, (40, 40, 44))
    g.line([(140, 640), (140, 760)], (60, 60, 66), 8)
    g.line([(440, 640), (440, 760)], (60, 60, 66), 8)
    return g.done()


# ------------------------------------------------------------------ eat
def buffet(s):
    """The wedding buffet: the long table with its chafing dishes and the PANEER card, the shamiana's drapes and
    fairy lights, the plate stack. The queue, the relatives, the last piece of paneer."""
    g = G(s, color=(250, 224, 196))
    y_floor = 1290
    g.rect(0, 0, LW, y_floor, (250, 230, 200))
    for x in range(0, LW, 120):                                              # the shamiana's drapes
        g.poly([(x, 0), (x + 120, 0), (x + 100, 300), (x + 60, 260), (x + 20, 300)],
               (240, 120, 70) if (x // 120) % 2 else (250, 210, 90), INK, 3)
    _loc()._string_lights(g, 0, LW, 320, 80, 16, 4)
    _loc()._garland(g, 60, 1020, 440, 60)
    g.rect(40, 880, 1040, 960, (250, 250, 246), INK, 5)                      # the table and its cloth
    g.rect(40, 960, 1040, y_floor, (200, 40, 60), INK, 5)
    for x in range(40, 1040, 80):
        g.line([(x, 960), (x + 20, y_floor)], (170, 30, 50), 3)
    names = ("PANEER", "DAL", "PULAO", "GULAB JAMUN")
    for i, x in enumerate((170, 410, 650, 890)):                             # the chafing dishes
        g.rect(x - 90, 800, x + 90, 880, (200, 204, 210), INK, 5)
        g.ellipse(x - 90, 760, x + 90, 830, (220, 224, 230), INK, 5)
        g.circle(x, 762, 12, (180, 184, 190), INK, 3)
        _sign(g, x - 80, 680, x + 80, 730, names[i], (250, 250, 246), (60, 40, 30), 22)
        g.note_light(x, 900, 30, (255, 180, 80))
    g.rect(960, 700, 1040, 880, (250, 250, 246), INK, 4)                     # the plate stack
    for y in range(710, 880, 14):
        g.line([(960, y), (1040, y)], (200, 200, 204), 2)
    g.rect(0, y_floor, LW, LH, (176, 40, 50))                                # the red carpet
    for x in range(0, LW, 100):
        g.line([(x, y_floor), (x - 70, LH)], (150, 30, 44), 3)
    g.line([(0, y_floor), (LW, y_floor)], INK, 5)
    return g.done()


def restaurant(s):
    """A family restaurant: the booth tables, the menu board with its prices, hanging lamps, a big window onto the
    evening street. Dates, the bill, "ek plate me do chamach"."""
    g = G(s, color=(84, 56, 44))
    y_floor = 1290
    g.rect(0, 0, LW, y_floor, (96, 64, 50))
    for x in range(0, LW, 90):                                               # wood panelling
        g.line([(x, 640), (x, y_floor)], (80, 52, 40), 4)
    g.rect(0, 620, LW, 650, (120, 80, 56), INK, 4)
    g.rect(80, 200, 560, 600, (60, 70, 100), INK, 8)                         # the window onto the street
    g.punch(96, 216, 544, 584)
    with g.on("window"):
        g.rect(96, 216, 544, 584, (60, 70, 110))
        _loc()._buildings(g, 584, seed=21, h=(180, 340), night=True)
    g.note_window(96, 216, 544, 584)
    g.rect(640, 180, 1020, 560, (30, 34, 30), INK, 8)                        # the menu board
    _txt(g, 830, 230, "MENU", 46, (250, 220, 120))
    for i, (a, b) in enumerate((("Paneer Tikka", "349"), ("Dal Makhani", "289"), ("Butter Naan", "79"),
                                ("Cold Coffee", "199"), ("Gulab Jamun", "129"))):
        _txt(g, 760, 290 + i * 52, a, 26, (240, 240, 230))
        _txt(g, 960, 290 + i * 52, b, 26, (250, 200, 120))
    for x in (280, 800):                                                     # hanging lamps
        g.line([(x, 0), (x, 640)], INK, 3)
        g.poly([(x - 60, 700), (x + 60, 700), (x + 30, 640), (x - 30, 640)], (220, 150, 60), INK, 4)
        g.note_light(x, 700, 120, (255, 200, 120))
        _light_patch(g, [(x - 70, 700), (x + 70, 700), (x + 200, 1100), (x - 200, 1100)], (255, 210, 140), 40)
    for x0 in (60, 600):                                                     # booth tables
        g.rect(x0, 960, x0 + 420, 1010, (190, 140, 90), INK, 5)
        g.rect(x0 + 190, 1010, x0 + 230, 1180, (90, 60, 40), INK, 4)
        g.rect(x0 - 30, 900, x0 + 40, 1190, (160, 40, 40), INK, 5)
        g.rect(x0 + 380, 900, x0 + 450, 1190, (160, 40, 40), INK, 5)
        g.rect(x0 + 140, 930, x0 + 170, 960, (240, 240, 236), INK, 3)        # salt and pepper
        g.rect(x0 + 250, 930, x0 + 280, 960, (60, 50, 44), INK, 3)
    g.rect(0, y_floor, LW, LH, (120, 84, 60))
    for i in range(10):
        y = y_floor + i * i * 8 + 20
        g.line([(0, y), (LW, y)], (100, 70, 50), 3)
    g.line([(0, y_floor), (LW, y_floor)], INK, 5)
    return g.done()


# ------------------------------------------------------------------ work
def interview_room(s):
    """An interview: the panel's long table with name cards and water bottles, a whiteboard, the company logo, the
    one chair on this side. The candidate, the HR and the 'where do you see yourself in 5 years'."""
    g = G(s, color=(232, 234, 238))
    y_floor = 1280
    g.rect(0, 0, LW, y_floor, (236, 238, 242))
    g.rect(0, 0, LW, 160, (60, 90, 160))
    _txt(g, 540, 84, "TECHNOVA SOLUTIONS", 54, (255, 255, 255))
    g.rect(140, 260, 940, 640, (252, 252, 252), INK, 6)                      # the whiteboard
    _txt(g, 540, 330, "INTERVIEW: 10:00 - 6:00", 34, (60, 90, 160))
    _txt(g, 540, 400, "Round 1  ✓", 32, (40, 140, 60))
    _txt(g, 540, 460, "Round 2  ✓", 32, (40, 140, 60))
    _txt(g, 540, 520, "Round 3  ?", 32, (200, 50, 50))
    _txt(g, 540, 590, "Round 7  ??", 30, (200, 50, 50))
    g.rect(60, 900, 1020, 980, (120, 84, 56), INK, 6)                        # the panel's table
    g.rect(90, 980, 990, 1200, (100, 70, 46), INK, 5)
    for i, (x, nm) in enumerate(((240, "HR"), (540, "MANAGER"), (840, "CEO"))):
        g.rect(x - 60, 850, x + 60, 900, (250, 250, 246), INK, 3)
        _txt(g, x, 876, nm, 20, (60, 60, 66))
        g.rect(x + 80, 820, x + 104, 900, (170, 214, 236), INK, 3)          # water bottles
    g.rect(0, y_floor, LW, LH, (150, 150, 160))
    for x in range(0, LW, 70):
        g.line([(x, y_floor), (x - 50, LH)], (140, 140, 150), 2)
    g.line([(0, y_floor), (LW, y_floor)], INK, 5)
    _plus()._plant(g, 1010, y_floor)
    return g.done()


def call_center(s):
    """A call center floor at night: rows of cubicles with monitors and headsets, the target board, ceiling
    lights, the clock at 2 a.m. "Thank you for calling, how may I help you?"."""
    g = G(s, color=(196, 206, 222))
    y_floor = 1290
    g.rect(0, 0, LW, y_floor, (200, 210, 226))
    g.rect(240, 140, 840, 340, (30, 34, 40), INK, 6)                         # the target board
    _txt(g, 540, 190, "TODAY'S TARGET", 34, (250, 220, 120))
    _txt(g, 540, 260, "CALLS: 487 / 600", 44, (240, 80, 70))
    _txt(g, 540, 310, "AHT: 4:59", 28, (140, 220, 160))
    g.circle(960, 230, 70, (250, 250, 246), INK, 6)                          # the clock: 2 a.m.
    g.line([(960, 230), (960, 180)], INK, 6)
    g.line([(960, 230), (990, 214)], INK, 8)
    for row, (y0, k) in enumerate(((620, 0.8), (880, 1.0))):                 # two rows of cubicles
        for i in range(4 if row == 0 else 3):
            x0 = (40 + i * 260) if row == 0 else (60 + i * 340)
            w = 220 * k if row == 0 else 300
            g.rect(x0, y0, x0 + w, y0 + 240 * k, (120, 140, 170), INK, 5)
            g.rect(x0 + w * 0.3, y0 + 30 * k, x0 + w * 0.7, y0 + 120 * k, (30, 34, 40), INK, 4)
            g.rect(x0 + w * 0.3 + 8, y0 + 38 * k, x0 + w * 0.7 - 8, y0 + 112 * k, (110, 180, 230))
            g.note_light(x0 + w * 0.5, y0 + 80 * k, 60, (140, 200, 255))
            g.line([(x0 + w * 0.15, y0 + 130 * k), (x0 + w * 0.15, y0 + 90 * k), (x0 + w * 0.25, y0 + 90 * k)],
                   INK, 4)                                                   # a headset on its hook
    _plus()._ceiling_lights(g, 30, (220, 540, 860))
    g.rect(0, y_floor, LW, LH, (90, 100, 120))
    for i in range(8):
        g.line([(0, y_floor + i * i * 14 + 20), (LW, y_floor + i * i * 14 + 20)], (80, 90, 108), 3)
    g.line([(0, y_floor), (LW, y_floor)], INK, 5)
    return g.done()


def startup_office(s):
    """A startup: bean bags, a foosball table, a glass wall with sticky notes, the neon 'HUSTLE' sign, a
    ping-pong paddle on the wall, laptops on a long table. Gen-Z, the founder, 'we are a family'."""
    g = G(s, color=(236, 236, 230))
    y_floor = 1280
    g.rect(0, 0, LW, y_floor, (238, 238, 232))
    g.rect(0, 0, 360, y_floor, (60, 64, 72))                                 # the brick-look accent wall
    for y in range(0, y_floor, 40):
        for x in range((y // 40) % 2 * 40 - 40, 360, 80):
            g.rect(x, y, x + 76, y + 36, (190, 100, 70), (150, 76, 54), 2)
    g.rrect(60, 300, 320, 420, 20, (30, 30, 36), INK, 4)                     # the neon sign
    _txt(g, 190, 360, "HUSTLE", 56, (255, 80, 200))
    g.note_light(190, 360, 140, (255, 90, 210))
    g.rect(420, 200, 1040, 760, (210, 230, 238), INK, 6)                     # the glass wall with sticky notes
    rnd = random.Random(13)
    for _ in range(18):
        x, y = rnd.randint(450, 980), rnd.randint(230, 700)
        g.rect(x, y, x + 50, y + 50, rnd.choice([(250, 230, 90), (250, 160, 170), (140, 220, 160), (150, 200, 250)]),
               INK, 2)
    _txt(g, 730, 250, "Q4 OKRs", 34, (60, 60, 66))
    g.rect(460, 900, 1040, 950, (220, 200, 170), INK, 5)                     # the long table with laptops
    for x in (500, 700, 900):
        g.poly([(x, 900), (x + 100, 900), (x + 110, 840), (x + 10, 840)], (60, 64, 72), INK, 3)
        g.note_light(x + 55, 870, 30, (150, 210, 255))
    for x in (520, 1000):
        g.rect(x - 10, 950, x + 10, 1180, (60, 64, 72), INK, 3)
    for (cx, c) in ((150, (240, 120, 60)), (330, (60, 140, 200))):           # bean bags
        g.ellipse(cx - 120, 1080, cx + 120, 1280, c, INK, 5)
        g.ellipse(cx - 80, 1060, cx + 80, 1140, tuple(min(255, v + 30) for v in c), INK, 4)
    g.rect(0, y_floor, LW, LH, (190, 170, 140))
    for x in range(0, LW, 110):
        g.line([(x, y_floor), (x - 80, LH)], (176, 156, 126), 3)
    g.line([(0, y_floor), (LW, y_floor)], INK, 5)
    return g.done()


NEW = {"ghar_darwaza": ghar_darwaza, "lift": lift, "park": park, "atm": atm, "petrol_pump": petrol_pump,
       "signal": signal, "buffet": buffet, "restaurant": restaurant, "interview_room": interview_room,
       "call_center": call_center, "startup_office": startup_office}
HORIZON = {"ghar_darwaza": 1280, "lift": 1300, "park": 1060, "atm": 1290, "petrol_pump": 1250, "signal": 1120,
           "buffet": 1290, "restaurant": 1290, "interview_room": 1280, "call_center": 1290, "startup_office": 1280}
OUTDOOR = {"park", "petrol_pump", "signal"}

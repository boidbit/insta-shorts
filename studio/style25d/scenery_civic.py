"""Hand-made 2.5D sets for the places with a counter, painted like the kitchen and the office.

Each counter (the reception desk, the bank counter, the police desk, the judge's bench, the witness box, the
munshi's desk, the canteen counter) is a piece the people are depth-sorted with, at the same place and size as in the
2D picture (counters.PLACES), so whoever stands behind it (counters.PRESET_PLACES) is cut off by it like in real life.

hospital_25d  a hospital lobby: OPD 1 / OPD 2 doors, the HOSPITAL board, a heart monitor on the wall whose line beats,
              SILENCE PLEASE, the RECEPTION desk with its computer and bell, a plant, a drip stand blurred in front.
bank_25d      a bank hall: CASH / LOANS / ENQUIRY windows of glass (the cashier is seen through it), the back office
              with its files and the strong-room door, a TOKEN board whose number goes up, two fans, a queue rope.
police_25d    a police station: POLICE STATION board, WANTED posters, the lock-up with its bars, a bench and a small
              window, the duty desk with the register, the phone and a cap, a fan turning, a lathi in front.
court_25d     a court room: wood panelling, the scales of justice, the judge's raised bench with the gavel, a red drape
              and a high chair, the witness box with its railing, the munshi's desk with files, two long-rod fans,
              beams of sunlight with dust, the gallery bench blurred in front.
canteen_25d   a college canteen: the chalk MENU (samosa, chai, maggi, vada pav), the counter with a glass case of
              samosas, a tea urn that steams, steel tins, a cold-drinks fridge, tables with benches, a fan, a plate of
              samosas and chai in front.
dhaba_25d     a highway dhaba at sunset: the lit SHER-E-DHABA board on a tin shed, strings of bulbs, the menu, a glowing
              tandoor with its smoke, a blue water drum, a charpai, a decorated truck parked on the highway behind.
(All have writing on them, so a reverse shot never mirrors them.)
"""
import math
import random

from PIL import Image, ImageDraw

from .scenery import (PAL_BULB, Cv, Layer, Layered, Sprite, along, catenary, fill_tex, motes, mul, quad_image,
                      sign_image, steam, twinkle, vgrad)
from .scenery_home import _clock, _floor_tiles, _leaves, _shadow, _tube_light, fan
from ..util import LH, LW

INK = (44, 38, 40, 255)


def _blank(k, fill=(0, 0, 0, 0)):
    return Image.new("RGBA", (8, 8), fill)


class Part(Cv):
    """A canvas that covers only the logical box (x0, y0, x1, y1), drawn in the set's own coordinates (for the
    pieces the people are depth-sorted with)."""

    def __init__(self, k, box):
        x0, y0, x1, y1 = box
        Cv.__init__(self, k, w=x1 - x0, h=y1 - y0, blend=True)
        self.ox, self.oy = x0, y0

    def P(self, pts):
        return [((x - self.ox) * self.k, (y - self.oy) * self.k) for x, y in pts]

    def ell(self, cx, cy, rx, ry, fill=None, outline=None, w=0):
        Cv.ell(self, cx - self.ox, cy - self.oy, rx, ry, fill, outline, w)

    def quad(self, img, q):
        quad_image(self, img, [(x - self.ox, y - self.oy) for x, y in q])

    def tex(self, pts, stops, **kw):
        fill_tex(self, [(x - self.ox, y - self.oy) for x, y in pts],
                 [(p - self.oy, c) for p, c in stops] if isinstance(stops, list) else stops, **kw)

    def sprite(self, ground_y, name="counter"):
        return Sprite(self.im, self.k, self.ox, self.oy, ground_y, name)


def board_image(lines, bg, fg, w=640, h=520, border=(90, 64, 44), title_col=None):
    """A board with several lines of writing (a menu, a notice); the first line is the title."""
    from ..text import font
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=int(h * 0.03), fill=bg + (255,), outline=border + (255,),
                        width=max(6, h // 30))
    n = len(lines)
    lh = (h - 40) / float(n + 0.4)
    for i, text in enumerate(lines):
        size = int(lh * (0.78 if i == 0 else 0.56))
        f = font(size)
        while f.getlength(text) > w * 0.86 and size > 10:
            size -= 2
            f = font(size)
        tw = f.getlength(text)
        y = 20 + lh * (i + (0.1 if i == 0 else 0.4))
        d.text(((w - tw) / 2, y), text, font=f, fill=((title_col or fg) if i == 0 else fg) + (255,))
    return im


def _room_shell(cv, F, wall_top, wall_bot, dado=None, ceiling=(246, 244, 238), seed=3):
    """Back wall (with a painted dado below dado[0]), a ceiling strip and the skirting."""
    fill_tex(cv, [(0, 0), (LW, 0), (LW, F), (0, F)], [(0, wall_top), (F, wall_bot)], seed=seed, cell=60, lo=0.96,
             hi=1.035)
    if dado:
        y, c0, c1, line = dado
        fill_tex(cv, [(0, y), (LW, y), (LW, F), (0, F)], [(y, c0), (F, c1)], seed=seed + 1, cell=50, lo=0.95, hi=1.04)
        cv.rect(0, y - 6, LW, y + 6, line + (255,), INK, 1)
    cv.rect(0, 0, LW, 64, ceiling + (255,))
    cv.rect(0, 64, LW, 76, mul(ceiling, 0.86) + (255,))
    cv.rect(0, F - 24, LW, F, mul(wall_bot if not dado else dado[2], 0.7) + (255,), INK, 2)


# ------------------------------------------------------------------ hospital
H_VP, H_F = (540, 800), 1280
ECG = (330, 500, 520, 630)


def _door(cv, x0, x1, top, F, col, label):
    cv.rect(x0 - 14, top - 14, x1 + 14, F, (236, 236, 232, 255), INK, 3)          # frame
    cv.rect(x0, top, x1, F, col + (255,), INK, 3)
    cv.rect(x0 + 26, top + 60, x1 - 26, top + 230, (220, 236, 244, 255), INK, 2)  # frosted glass
    cv.line([(x0 + 40, top + 80), (x0 + 70, top + 200)], (255, 255, 255, 160), 6)
    cv.rect(x0 + 26, top + 300, x1 - 26, F - 60, mul(col, 0.92) + (255,), INK, 2)
    cv.rect(x1 - 34, top + 290, x1 - 16, top + 330, (190, 190, 196, 255), INK, 2)  # handle
    quad_image(cv, sign_image(label, (250, 250, 246), (30, 120, 80), 500, 160), [(x0 + 10, top - 80), (x1 - 10, top - 80),
                                                                                (x1 - 10, top - 30), (x0 + 10, top - 30)])


def _hospital(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(250, 252, 255, 0))
    _room_shell(cv, H_F, (234, 244, 240), (222, 236, 230), dado=(900, (196, 226, 212), (184, 216, 202), (60, 160, 140)))
    _tube_light(cv, light, 200, 420, 110)
    _tube_light(cv, light, 660, 880, 110)
    quad_image(cv, sign_image("HOSPITAL", (36, 140, 90), (255, 255, 255), 900, 200),
               [(330, 150), (750, 150), (750, 236), (330, 236)])
    cv.rect(250, 160, 304, 214, (250, 250, 250, 255), INK, 2)                     # the red cross
    cv.rect(270, 168, 284, 206, (220, 40, 40, 255))
    cv.rect(258, 180, 296, 194, (220, 40, 40, 255))
    _door(cv, 40, 220, 480, H_F, (166, 198, 220), "OPD 1")
    _door(cv, 860, 1040, 480, H_F, (166, 198, 220), "OPD 2")
    _clock(cv, 960, 320, 38)
    quad_image(cv, sign_image("SILENCE PLEASE", (250, 250, 246), (200, 40, 40), 800, 160),
               [(570, 520), (790, 520), (790, 576), (570, 576)])
    for i, col in enumerate(((250, 236, 160), (190, 220, 250), (250, 200, 210))):  # health posters
        x = 580 + i * 72
        cv.rect(x, 600, x + 60, 690, col + (255,), INK, 2)
        cv.ell(x + 30, 630, 14, 14, mul(col, 0.8) + (255,))
        for j in range(3):
            cv.line([(x + 10, 656 + j * 10), (x + 50, 656 + j * 10)], mul(col, 0.6) + (255,), 2)
    x0, y0, x1, y1 = ECG                                                          # the heart monitor on its bracket
    cv.rect(x0 - 10, y0 - 10, x1 + 10, y1 + 10, (60, 64, 70, 255), INK, 3)
    cv.rect(x0, y0, x1, y1, (16, 24, 22, 255))
    cv.rect((x0 + x1) / 2 - 12, y1 + 10, (x0 + x1) / 2 + 12, y1 + 40, (90, 94, 100, 255), INK, 2)
    cv.rect(820, 700, 850, 760, (240, 240, 236, 255), INK, 2)                     # sanitizer
    cv.rect(826, 690, 844, 700, (60, 140, 200, 255))
    # the plant by the desk
    cv.poly([(236, 1190), (296, 1190), (286, H_F), (246, H_F)], (190, 100, 70, 255), INK, 2)
    _leaves(cv, 14, 200, 330, 990, 1190, 40, ((40, 120, 60), (110, 170, 80)), 9)
    _floor_tiles(cv, H_VP, H_F, (238, 240, 240), (224, 228, 230), step=120, grow=1.24, grout=(200, 204, 206, 255))
    _shadow(cv, 540, H_F + 4, 260, 14)
    return cv, light


def _reception(k):
    p = Part(k, (280, 900, 800, 1292))
    p.rect(380, 930, 460, 988, (40, 40, 46, 255), INK, 2)                          # the computer
    p.rect(386, 936, 454, 980, (90, 150, 210, 255))
    p.rect(412, 988, 428, 998, (40, 40, 46, 255))
    p.rect(560, 960, 640, 992, (250, 250, 246, 255), INK, 1)                      # files
    p.rect(566, 948, 636, 962, (240, 200, 90, 255), INK, 1)
    p.ell(720, 984, 16, 9, (210, 170, 60, 255), INK, 2)                          # the bell
    p.ell(720, 978, 4, 4, (120, 100, 40, 255))
    p.rect(300, 990, 780, 1080, (246, 246, 244, 255), INK, 3)                     # the high top
    p.rect(300, 990, 780, 1004, (255, 255, 255, 255), INK, 2)
    p.rect(320, 1080, 760, 1280, (110, 190, 170, 255), INK, 3)                    # the front
    p.rect(320, 1240, 760, 1280, (80, 160, 140, 255), INK, 2)
    p.quad(sign_image("RECEPTION", (110, 190, 170), (255, 255, 255), 800, 160), [(380, 1130), (700, 1130),
                                                                                (700, 1190), (380, 1190)])
    return p.sprite(1280)


def _ecg(k):
    """fn (screen): the heart monitor's green line, a beat running across."""
    x0, y0, x1, y1 = ECG

    def beat(u):
        u = u % 1.0
        if 0.40 < u < 0.44:
            return -0.9 * math.sin((u - 0.40) / 0.04 * math.pi)
        if 0.44 < u < 0.48:
            return 0.5 * math.sin((u - 0.44) / 0.04 * math.pi)
        if 0.6 < u < 0.7:
            return -0.18 * math.sin((u - 0.6) / 0.1 * math.pi)
        return 0.0

    def fn(_im, t):
        cv = Cv(k, fill=(80, 255, 140, 0))
        pts = []
        n = 60
        for i in range(n + 1):
            x = x0 + 8 + (x1 - x0 - 16) * i / float(n)
            pts.append((x, (y0 + y1) / 2 + 34 * beat(i / float(n) * 1.6 - t * 1.1)))
        cv.line(pts, (90, 255, 150, 255), 2.5)
        cv.glow((x0 + x1) / 2, (y0 + y1) / 2, 120, (60, 255, 120), 26)
        return cv.im
    return fn


def _hospital_front(k):
    cv = Cv(k, fill=(200, 200, 210, 0), blend=True)
    cv.rect(1010, 1240, 1026, 1960, (190, 194, 200, 255))                          # a drip stand
    cv.line([(960, 1250), (1076, 1250)], (190, 194, 200, 255), 8)
    cv.poly([(950, 1260), (1000, 1260), (1004, 1400), (946, 1400)], (230, 240, 250, 220))
    cv.line([(975, 1400), (990, 1700)], (230, 240, 250, 255), 4)
    _leaves(cv, 10, -60, 200, 1760, 1990, 54, ((50, 120, 60), (120, 170, 80)), 13)
    cv.blur(9)
    return cv


def hospital_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    st, light = _hospital(kr, kg)
    fg = _hospital_front(0.5 * s)
    back = [
        Layer(st.im, kr, 1.0, None, "set"),
        Layer(light.im, kg, 1.0, None, "lights", mode="screen"),
        Layer(_blank(0.5 * s), 0.5 * s, 1.0, _ecg(0.5 * s), "ecg", mode="screen"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return Layered(back, front, light={"ambient": [246, 252, 255], "dir": 1, "vignette": 0.2},
                   horizon=H_VP[1], ground=H_F, sprites=[_reception(kr)])


# ------------------------------------------------------------------ bank
B_VP, B_F = (540, 760), 1100
B_WINDOWS = [((60, 340, 340, 880), "CASH"), ((400, 340, 720, 880), "LOANS"), ((740, 340, 1020, 880), "ENQUIRY")]
TOKEN = (800, 196, 1040, 280)


def _bank(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(255, 248, 230, 0))
    rnd = random.Random(141)
    _room_shell(cv, B_F, (238, 232, 218), (226, 218, 200))
    quad_image(cv, sign_image("BANK", (36, 84, 160), (255, 255, 255), 600, 200), [(390, 170), (690, 170), (690, 270),
                                                                                (390, 270)])
    cv.rect(TOKEN[0] - 8, TOKEN[1] - 8, TOKEN[2] + 8, TOKEN[3] + 8, (40, 40, 44, 255), INK, 3)
    # the back office behind the glass: wall, files, a strong-room door, a clock
    fill_tex(cv, [(20, 330), (1060, 330), (1060, 880), (20, 880)], [(330, (214, 204, 186)), (880, (200, 190, 172))],
             seed=143, cell=40, lo=0.95, hi=1.04)
    for x in range(40, 330, 44):                                                   # files on a rack
        for row, y in enumerate((470, 560)):
            c = rnd.choice(((200, 60, 60), (60, 110, 190), (230, 190, 60), (90, 150, 90)))
            cv.rect(x, y, x + 34, y + 80, c + (255,), INK, 1)
            cv.rect(x + 8, y + 14, x + 26, y + 30, (250, 250, 246, 255))
        cv.rect(36, 550, 334, 560, (140, 100, 70, 255))
        cv.rect(36, 640, 334, 650, (140, 100, 70, 255))
    cv.ell(560, 600, 120, 120, (150, 156, 164, 255), INK, 4)                       # the strong-room door
    cv.ell(560, 600, 100, 100, (176, 182, 190, 255), INK, 2)
    cv.ell(560, 600, 26, 26, (120, 124, 130, 255), INK, 2)
    for i in range(6):
        a = i * math.pi / 3
        cv.line([(560, 600), (560 + 70 * math.cos(a), 600 + 70 * math.sin(a))], (110, 114, 120, 255), 8)
    _clock(cv, 880, 470, 36)
    for x in (800, 940):                                                           # back desks with monitors
        cv.rect(x - 50, 780, x + 50, 840, (140, 100, 70, 255), INK, 2)
        cv.rect(x - 30, 730, x + 30, 778, (40, 40, 46, 255), INK, 2)
    # the counter's stand under the glass, the floor of the hall
    _floor_tiles(cv, B_VP, B_F, (226, 220, 210), (206, 198, 186), step=130, grow=1.2, grout=(180, 172, 160, 255))
    _shadow(cv, 540, B_F + 6, 560, 18)
    for (x0, x1) in ((120, 300), (500, 680)):
        light.poly([(x0 - 200, -40), (x1 - 200, -40), (x1 + 160, 1500), (x0 + 160, 1500)], (255, 244, 214, 30))
    light.blur(30)
    return cv, light


def _bank_glass(k):
    """The glass windows over the counter (in front of the cashier): faint tint, frames, the talk grille, the
    boards on top."""
    p = Part(k, (40, 300, 1040, 892))
    for (x0, y0, x1, y1), name in B_WINDOWS:
        p.rect(x0, y0, x1, y1, (190, 220, 236, 46))
        p.poly([(x0 + 30, y1 - 40), (x0 + 110, y0 + 60), (x0 + 150, y0 + 60), (x0 + 70, y1 - 40)], (255, 255, 255, 40))
        for (a, b, c, d) in ((x0 - 8, y0 - 8, x1 + 8, y0), (x0 - 8, y0, x0, y1), (x1, y0, x1 + 8, y1)):
            p.rect(a, b, c, d, (150, 156, 164, 255), INK, 1)
        cx = (x0 + x1) / 2
        p.ell(cx, y0 + 330, 34, 34, None, (150, 156, 164, 255), 3)                 # the talk grille
        for i in range(-2, 3):
            for j in range(-2, 3):
                if i * i + j * j <= 5:
                    p.ell(cx + i * 10, y0 + 330 + j * 10, 2.5, 2.5, (120, 126, 134, 200))
        p.erase([(cx - 60, y1 - 30), (cx + 60, y1 - 30), (cx + 60, y1), (cx - 60, y1)])      # the slot
        p.quad(sign_image(name, (250, 250, 246), (36, 84, 160), 600, 150), [(cx - 90, y0 + 20), (cx + 90, y0 + 20),
                                                                            (cx + 90, y0 + 66), (cx - 90, y0 + 66)])
    return p.sprite(1099, "glass")


def _bank_counter(k):
    p = Part(k, (10, 860, 1070, 1104))
    p.rect(20, 880, 1060, 900, (226, 226, 222, 255), INK, 3)                       # marble top
    p.rect(20, 900, 1060, 1100, (130, 86, 54, 255), INK, 3)
    for x in range(20, 1060, 130):
        p.rect(x + 14, 920, x + 116, 1080, (146, 98, 62, 255), (100, 66, 40, 255), 2)
    for (x0, _y0, x1, _y1), _n in B_WINDOWS:                                        # the pass-through trays
        cx = (x0 + x1) / 2
        p.poly([(cx - 70, 880), (cx + 70, 880), (cx + 60, 866), (cx - 60, 866)], (170, 176, 184, 255), INK, 2)
    p.rect(860, 860, 920, 880, (250, 250, 246, 255), INK, 1)                      # a pen on a chain, slips
    p.line([(250, 872), (300, 860)], (40, 40, 44, 255), 3)
    return p.sprite(1100)


def _token(k, blank):
    """fn: the TOKEN board, its number going up every few seconds (it blinks when it changes)."""
    x0, y0, x1, y1 = TOKEN
    frames = []
    for n in range(42, 52):                                     # drawn once: the layer only picks one
        cv = Cv(k, fill=(20, 20, 24, 0))
        quad_image(cv, sign_image("TOKEN %d" % n, (20, 20, 24), (255, 70, 60), 600, 200, border=(20, 20, 24)),
                   [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
        frames.append(cv.im)

    def fn(_im, t):
        if t >= 6.0 and (t % 6.0) < 0.5 and int((t % 6.0) * 8) % 2:
            return blank
        return frames[int(t / 6.0) % len(frames)]
    return fn


def _bank_front(k):
    cv = Cv(k, fill=(200, 160, 60, 0), blend=True)
    for x in (40, 420):                                                            # the queue rope
        cv.rect(x - 12, 1560, x + 12, 1940, (210, 170, 70, 255))
        cv.ell(x, 1556, 20, 14, (230, 200, 100, 255))
        cv.rect(x - 40, 1930, x + 40, 1960, (190, 150, 60, 255))
    cv.line(catenary(52, 1580, 408, 1580, 70), (190, 40, 50, 255), 14)
    cv.blur(8)
    return cv


def bank_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    st, light = _bank(kr, kg)
    fg = _bank_front(0.5 * s)
    back = [
        Layer(st.im, kr, 1.0, None, "set"),
        Layer(light.im, kg, 1.0, None, "sunlight", mode="screen"),
        Layer(_blank(0.6 * s), 0.6 * s, 1.0, _token(0.6 * s, _blank(0.6 * s)), "token"),
        Layer(_blank(0.4 * s), 0.4 * s, 1.0, fan(200, 130, 0.4 * s, R=150, speed=1.6, top=76), "fan"),
        Layer(_blank(0.4 * s), 0.4 * s, 1.0, fan(700, 130, 0.4 * s, R=150, speed=1.4, top=76), "fan2"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return Layered(back, front, light={"ambient": [252, 248, 240], "dir": -1, "vignette": 0.22},
                   horizon=B_VP[1], ground=B_F, sprites=[_bank_glass(kr), _bank_counter(kr)])


# ------------------------------------------------------------------ police station
P_VP, P_F = (540, 800), 1280
LOCKUP = (600, 330, 1060)


def _wanted(cv, x, y):
    cv.rect(x, y, x + 110, y + 160, (246, 238, 214, 255), INK, 2)
    quad_image(cv, sign_image("WANTED", (246, 238, 214), (190, 30, 30), 400, 110, border=(246, 238, 214)),
               [(x + 6, y + 6), (x + 104, y + 6), (x + 104, y + 34), (x + 6, y + 34)])
    cv.ell(x + 55, y + 82, 30, 34, (50, 46, 46, 255))
    cv.rect(x + 22, y + 116, x + 88, y + 150, (50, 46, 46, 255))
    cv.line([(x + 18, y + 154), (x + 92, y + 154)], (150, 120, 90, 255), 2)


def _police(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(255, 246, 220, 0))
    _room_shell(cv, P_F, (236, 226, 196), (226, 214, 180), dado=(820, (150, 150, 104), (136, 136, 94), (100, 100, 70)))
    _tube_light(cv, light, 420, 640, 300)
    quad_image(cv, sign_image("POLICE STATION", (30, 50, 110), (255, 255, 255), 1200, 200),
               [(230, 150), (850, 150), (850, 246), (230, 246)])
    _wanted(cv, 90, 360)
    _wanted(cv, 230, 360)
    cv.rect(380, 380, 540, 560, (200, 150, 100, 255), INK, 3)                      # a notice board
    for i, col in enumerate(((250, 250, 240), (250, 230, 160), (230, 240, 250))):
        cv.rect(394 + i * 48, 400 + (i % 2) * 30, 434 + i * 48, 470 + (i % 2) * 30, col + (255,), INK, 1)
    cv.rect(60, 600, 340, 616, (130, 90, 60, 255), INK, 2)                         # a shelf: wireless set, files
    cv.rect(80, 540, 180, 600, (70, 74, 64, 255), INK, 2)
    cv.ell(110, 570, 14, 14, (40, 40, 40, 255))
    cv.line([(160, 540), (180, 470)], (40, 40, 40, 255), 3)
    for i in range(5):
        cv.rect(200 + i * 24, 548, 220 + i * 24, 600, ((200, 60, 60), (230, 200, 90), (70, 110, 180))[i % 3] + (255,),
                INK, 1)
    # the lock-up: a dark cell behind bars
    x0, y0, x1 = LOCKUP
    fill_tex(cv, [(x0, y0), (x1, y0), (x1, P_F), (x0, P_F)], [(y0, (110, 110, 100)), (P_F, (80, 80, 74))], seed=151,
             cell=30, lo=0.9, hi=1.08)
    cv.rect(780, 420, 900, 500, (180, 200, 220, 255), INK, 2)                      # its small barred window
    for bx in range(796, 900, 22):
        cv.line([(bx, 420), (bx, 500)], (50, 50, 54, 255), 4)
    cv.rect(700, 1120, 1040, 1150, (120, 100, 80, 255), INK, 2)                    # a bench inside
    for lx in (720, 1020):
        cv.rect(lx - 6, 1150, lx + 6, P_F - 10, (90, 76, 60, 255))
    cv.poly([(640, P_F - 10), (680, P_F - 10), (676, P_F - 70), (644, P_F - 70)], (90, 110, 140, 255), INK, 2)  # bucket
    light.poly([(780, 420), (900, 420), (980, 1270), (760, 1270)], (220, 230, 255, 40))
    cv.rect(x0 - 16, y0 - 20, x1 + 20, y0, (60, 60, 64, 255), INK, 2)              # the bars
    for bx in range(int(x0), int(x1) + 1, 36):
        cv.rect(bx - 5, y0, bx + 5, P_F, (70, 72, 78, 255), INK, 1)
        cv.line([(bx - 2, y0), (bx - 2, P_F)], (150, 154, 160, 255), 2)
    for by in (600, 1000):
        cv.rect(x0 - 10, by - 8, x1 + 10, by + 8, (70, 72, 78, 255), INK, 1)
    cv.rect(640, 880, 676, 930, (180, 150, 60, 255), INK, 2)                       # the padlock
    cv.ell(658, 876, 12, 12, None, (150, 150, 156, 255), 4)
    quad_image(cv, sign_image("LOCK-UP", (250, 240, 220), (150, 30, 30), 600, 150), [(760, 250), (940, 250),
                                                                                    (940, 296), (760, 296)])
    _floor_tiles(cv, P_VP, P_F, (200, 192, 170), (184, 176, 154), step=120, grow=1.24, grout=(160, 150, 130, 255))
    light.blur(10)
    return cv, light


def _police_desk(k):
    p = Part(k, (50, 900, 570, 1290))
    p.rect(150, 950, 290, 1000, (240, 236, 220, 255), INK, 2)                      # the register, open
    p.line([(220, 950), (220, 1000)], (150, 140, 120, 255), 2)
    for j in range(3):
        p.line([(160, 964 + j * 10), (210, 964 + j * 10)], (120, 120, 140, 255), 1)
    p.rect(390, 966, 460, 1000, (30, 30, 34, 255), INK, 2)                         # the black phone
    p.ell(425, 962, 34, 10, (30, 30, 34, 255), INK, 2)
    p.ell(425, 984, 10, 10, (200, 200, 200, 255))
    p.ell(510, 990, 38, 12, (130, 110, 70, 255), INK, 2)                           # the cap
    p.poly([(476, 990), (544, 990), (536, 966), (484, 966)], (150, 130, 80, 255), INK, 2)
    p.rect(60, 1000, 560, 1014, (150, 104, 66, 255), INK, 3)
    p.rect(60, 1014, 560, 1280, (120, 80, 50, 255), INK, 3)
    p.rect(80, 1040, 300, 1250, (136, 92, 58, 255), (96, 62, 38, 255), 2)
    p.rect(320, 1040, 540, 1250, (136, 92, 58, 255), (96, 62, 38, 255), 2)
    p.quad(sign_image("DUTY OFFICER", (240, 230, 200), (30, 50, 110), 700, 150), [(200, 1110), (420, 1110),
                                                                                 (420, 1160), (200, 1160)])
    return p.sprite(1280)


def _police_front(k):
    cv = Cv(k, fill=(120, 80, 50, 0), blend=True)
    cv.line([(1000, 1960), (1080, 1300)], (150, 110, 60, 255), 22)                 # a lathi leaning
    cv.poly([(-40, 1700), (300, 1700), (290, 1760), (-40, 1760)], (110, 70, 44, 255))  # a visitor's chair
    cv.rect(-40, 1760, 0, 1960, (90, 58, 36, 255))
    cv.rect(250, 1760, 280, 1960, (90, 58, 36, 255))
    cv.blur(9)
    return cv


def police_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    st, light = _police(kr, kg)
    fg = _police_front(0.5 * s)
    back = [
        Layer(st.im, kr, 1.0, None, "set"),
        Layer(light.im, kg, 1.0, None, "lights", mode="screen"),
        Layer(_blank(0.4 * s), 0.4 * s, 1.0, fan(150, 290, 0.4 * s, R=130, speed=1.2, top=76), "fan"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return Layered(back, front, light={"ambient": [248, 244, 232], "dir": 1, "vignette": 0.3},
                   horizon=P_VP[1], ground=P_F, sprites=[_police_desk(kr)])


# ------------------------------------------------------------------ court
C_VP, C_F = (540, 760), 1000


def _scales(cv, cx, cy, r):
    cv.ell(cx, cy, r, r, (226, 186, 90, 255), INK, 3)
    cv.ell(cx, cy, r - 10, r - 10, (246, 230, 180, 255), INK, 2)
    cv.line([(cx, cy - r + 18), (cx, cy + r - 22)], (110, 80, 30, 255), 4)
    cv.line([(cx - r + 22, cy - r * 0.35), (cx + r - 22, cy - r * 0.35)], (110, 80, 30, 255), 4)
    for sx in (cx - r + 26, cx + r - 26):
        cv.line([(sx, cy - r * 0.35), (sx - 12, cy + 4), (sx + 12, cy + 4), (sx, cy - r * 0.35)], (110, 80, 30, 255), 2)
        cv.ell(sx, cy + 6, 16, 5, (190, 150, 60, 255), INK, 1)
    cv.rect(cx - 20, cy + r - 26, cx + 20, cy + r - 18, (110, 80, 30, 255))


def _court(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(255, 236, 190, 0))
    fill_tex(cv, [(0, 0), (LW, 0), (LW, 420), (0, 420)], [(0, (224, 202, 164)), (420, (214, 190, 150))], seed=161,
             cell=60, lo=0.96, hi=1.035)
    fill_tex(cv, [(0, 420), (LW, 420), (LW, C_F), (0, C_F)], [(420, (150, 98, 60)), (C_F, (126, 82, 50))], seed=162,
             cell=30, lo=0.92, hi=1.06)
    cv.rect(0, 410, LW, 430, (110, 70, 40, 255), INK, 2)
    for x in range(0, LW, 120):                                                    # wood panels
        cv.rect(x + 12, 446, x + 108, C_F - 20, None, (110, 70, 42, 255), 3)
        cv.rect(x + 22, 456, x + 98, C_F - 30, None, (170, 116, 72, 160), 2)
    cv.rect(0, 0, LW, 60, (240, 230, 210, 255))
    _scales(cv, 540, 190, 72)
    cv.poly([(380, 250), (700, 250), (720, 520), (360, 520)], (130, 30, 40, 255), INK, 3)   # the red drape
    for x in (420, 470, 540, 610, 660):
        cv.line([(x, 256), (x + (x - 540) * 0.08, 516)], (100, 20, 30, 255), 3)
    cv.poly([(470, 300), (610, 300), (620, 520), (460, 520)], (110, 40, 36, 255), INK, 3)    # the judge's high chair
    cv.ell(540, 300, 70, 26, (110, 40, 36, 255), INK, 3)
    for x in range(486, 600, 24):
        cv.ell(x, 330, 4, 4, (210, 170, 80, 255))
    # the raised dais under the bench
    cv.rect(230, 900, 850, C_F, (110, 70, 44, 255), INK, 3)
    cv.rect(230, 900, 850, 916, (140, 92, 58, 255), INK, 2)
    for x in range(240, 850, 62):
        cv.rect(x, 930, x + 50, C_F - 12, None, (90, 58, 36, 255), 2)
    # parquet floor
    _floor_tiles(cv, C_VP, C_F, (176, 124, 80), (160, 110, 70), step=70, grow=1.18, grout=(120, 80, 50, 255))
    _shadow(cv, 540, C_F + 6, 340, 16)
    for (x0, x1) in ((60, 200), (300, 420)):                                        # sunbeams from a high window
        light.poly([(x0 - 260, -40), (x1 - 260, -40), (x1 + 240, 1700), (x0 + 240, 1700)], (255, 230, 170, 34))
    light.blur(30)
    return cv, light


def _judge_bench(k):
    p = Part(k, (250, 440, 830, 905))
    p.rect(330, 486, 420, 500, (240, 236, 220, 255), INK, 1)                      # files
    p.rect(336, 474, 414, 486, (220, 180, 90, 255), INK, 1)
    p.rect(640, 488, 700, 500, (90, 60, 36, 255), INK, 1)                         # the gavel on its block
    p.line([(650, 480), (720, 470)], (120, 80, 48, 255), 5)
    p.rect(640, 466, 666, 486, (110, 70, 40, 255), INK, 2)
    p.rect(520, 476, 560, 500, (40, 40, 44, 255), INK, 1)                         # pen stand
    p.line([(532, 476), (526, 456)], (30, 60, 140, 255), 3)
    p.rect(260, 500, 820, 520, (150, 98, 60, 255), INK, 3)
    p.rect(260, 520, 820, 900, (120, 76, 46, 255), INK, 3)
    for x in (280, 560):
        p.rect(x, 560, x + 240, 860, (136, 88, 54, 255), (96, 60, 36, 255), 3)
    p.quad(sign_image("COURT", (120, 76, 46), (246, 220, 150), 600, 180, border=(120, 76, 46)),
           [(440, 640), (640, 640), (640, 700), (440, 700)])
    return p.sprite(900)


def _witness_box(k):
    p = Part(k, (30, 690, 230, 1104))
    p.rect(40, 700, 220, 720, (150, 98, 60, 255), INK, 3)                          # the rail
    for x in range(52, 216, 26):                                                    # balusters (gaps between)
        p.rect(x, 720, x + 10, 860, (130, 84, 52, 255), INK, 1)
    p.rect(40, 700, 56, 1100, (120, 76, 46, 255), INK, 2)
    p.rect(204, 700, 220, 1100, (120, 76, 46, 255), INK, 2)
    p.rect(40, 860, 220, 1100, (120, 76, 46, 255), INK, 3)
    p.rect(58, 880, 202, 1080, (136, 88, 54, 255), (96, 60, 36, 255), 2)
    return p.sprite(1100)


def _munshi_desk(k):
    p = Part(k, (850, 900, 1070, 1104))
    for i in range(4):                                                             # a pile of files
        c = ((240, 236, 220), (230, 200, 120), (220, 120, 100), (240, 236, 220))[i]
        p.rect(880 + (i % 2) * 6, 950 - i * 12, 960 + (i % 2) * 6, 962 - i * 12, c + (255,), INK, 1)
    p.rect(990, 930, 1030, 960, (40, 40, 44, 255), INK, 1)                        # an ink pad / stamp
    p.rect(860, 960, 1060, 974, (150, 98, 60, 255), INK, 3)
    p.rect(860, 974, 1060, 1100, (120, 76, 46, 255), INK, 3)
    return p.sprite(1100)


def _court_front(k):
    cv = Cv(k, fill=(110, 70, 40, 0), blend=True)
    cv.rect(-40, 1800, 1120, 1850, (120, 78, 46, 255))                             # the gallery bench's back
    cv.rect(-40, 1850, 1120, 1880, (96, 60, 36, 255))
    for x in (60, 520, 980):
        cv.rect(x, 1880, x + 30, 1960, (90, 56, 34, 255))
    cv.blur(9)
    return cv


def court_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    st, light = _court(kr, kg)
    fg = _court_front(0.5 * s)
    back = [
        Layer(st.im, kr, 1.0, None, "set"),
        Layer(light.im, kg, 1.0, None, "sunlight", mode="screen"),
        Layer(_blank(0.3 * s), 0.3 * s, 1.0, motes(((200, 300), (700, 1500), 260), 0.3 * s), "dust", mode="screen"),
        Layer(_blank(0.4 * s), 0.4 * s, 1.0, fan(230, 200, 0.4 * s, R=160, speed=1.0, top=60), "fan"),
        Layer(_blank(0.4 * s), 0.4 * s, 1.0, fan(850, 200, 0.4 * s, R=160, speed=1.1, top=60), "fan2"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    sprites = [_judge_bench(kr), _witness_box(kr), _munshi_desk(kr)]
    return Layered(back, front, light={"ambient": [255, 240, 220], "dir": -1, "vignette": 0.32},
                   horizon=C_VP[1], ground=C_F, sprites=sprites)


# ------------------------------------------------------------------ canteen
K_VP, K_F = (540, 800), 1280
URN = (1000, 600)


def _canteen(k, kg):
    cv = Cv(k, blend=True)
    light = Cv(kg, fill=(255, 246, 220, 0))
    _room_shell(cv, K_F, (248, 234, 192), (240, 224, 180), dado=(930, (120, 172, 120), (106, 156, 106), (70, 120, 70)))
    _tube_light(cv, light, 150, 380, 120)
    _tube_light(cv, light, 700, 930, 120)
    quad_image(cv, board_image(["MENU", "Samosa ....... 15", "Chai .......... 10", "Maggi ........ 40",
                                "Vada Pav ...... 20"], (40, 70, 56), (240, 240, 230), title_col=(250, 220, 120)),
               [(80, 300), (560, 300), (560, 700), (80, 700)])
    # behind the counter: a fridge, a shelf of plates and glasses
    cv.rect(640, 380, 800, 800, (200, 40, 40, 255), INK, 3)
    cv.rect(656, 420, 784, 700, (180, 220, 236, 255), INK, 2)
    for r in range(3):
        for c in range(4):
            cv.rect(668 + c * 30, 440 + r * 86, 686 + c * 30, 500 + r * 86,
                    ((60, 30, 20), (240, 140, 40), (60, 160, 70), (230, 230, 230))[(r + c) % 4] + (255,))
    quad_image(cv, sign_image("COLD DRINKS", (200, 40, 40), (255, 255, 255), 600, 140, border=(200, 40, 40)),
               [(656, 386), (784, 386), (784, 416), (656, 416)])
    cv.rect(830, 470, 1070, 484, (150, 104, 66, 255), INK, 2)
    for i in range(6):                                                              # stacked plates
        cv.ell(860 + i * 34, 462, 16, 6, (230, 232, 236, 255), INK, 1)
        cv.ell(860 + i * 34, 452, 16, 6, (230, 232, 236, 255), INK, 1)
    # tables with benches on the left
    for (x0, x1) in ((60, 320), (350, 600)):
        cv.rect(x0, 1060, x1, 1080, (190, 80, 60, 255), INK, 2)
        for lx in (x0 + 16, x1 - 24):
            cv.rect(lx, 1080, lx + 8, 1240, (110, 110, 116, 255))
        cv.rect(x0 + 10, 1150, x1 - 10, 1166, (150, 70, 50, 255), INK, 2)
        for lx in (x0 + 24, x1 - 30):
            cv.rect(lx, 1166, lx + 6, 1250, (110, 110, 116, 255))
        for gx_ in (x0 + 60, x1 - 80):
            cv.poly([(gx_, 1060), (gx_ + 18, 1060), (gx_ + 20, 1030), (gx_ - 2, 1030)], (220, 224, 230, 255), INK, 1)
            cv.rect(gx_, 1036, gx_ + 18, 1056, (190, 120, 60, 255))
        _shadow(cv, (x0 + x1) / 2, 1250, (x1 - x0) / 2, 10)
    _floor_tiles(cv, K_VP, K_F, (220, 206, 180), (204, 190, 164), step=110, grow=1.24, grout=(170, 156, 130, 255))
    light.glow(820, 760, 260, (255, 230, 170), 40)
    light.blur(8)
    return cv, light


def _canteen_counter(k):
    p = Part(k, (630, 560, 1080, 1290))
    for i, x in enumerate((690, 770, 850)):                                         # steel tins
        p.rect(x, 700, x + 60, 800, (200, 204, 210, 255), INK, 2)
        p.ell(x + 30, 700, 30, 8, (220, 224, 230, 255), INK, 2)
        p.line([(x + 8, 720), (x + 8, 790)], (240, 244, 248, 255), 3)
    ux, uy = URN                                                                    # the tea urn with its tap
    p.rect(ux - 50, uy, ux + 50, 800, (196, 200, 208, 255), INK, 3)
    p.ell(ux, uy, 50, 14, (220, 224, 230, 255), INK, 2)
    p.ell(ux, uy - 14, 18, 8, (120, 120, 126, 255), INK, 2)
    p.rect(ux - 74, 740, ux - 50, 752, (150, 150, 156, 255), INK, 1)
    p.rect(640, 800, 1080, 816, (190, 196, 204, 255), INK, 3)                       # steel top
    p.rect(650, 816, 1070, 960, (210, 236, 244, 160), INK, 2)                       # glass case of snacks
    for i in range(7):
        x = 680 + i * 52
        p.poly([(x - 20, 880), (x + 20, 880), (x, 846)], (220, 160, 70, 255), INK, 2)      # samosas
        p.ell(x, 932, 20, 12, (230, 180, 90, 255), INK, 2)                                 # vada pav
        p.ell(x, 924, 18, 8, (240, 200, 110, 255))
    p.rect(640, 960, 1080, 1280, (150, 100, 60, 255), INK, 3)
    for x in range(660, 1060, 100):
        p.rect(x, 990, x + 80, 1250, (164, 112, 70, 255), (110, 74, 44, 255), 2)
    return p.sprite(1280)


def _canteen_front(k):
    cv = Cv(k, fill=(190, 80, 60, 0), blend=True)
    cv.poly([(-60, 1760), (700, 1740), (700, 1960), (-60, 1960)], (190, 80, 60, 255))     # a table edge
    cv.ell(170, 1740, 120, 34, (236, 238, 242, 255))                               # a plate of samosas
    for x in (120, 200):
        cv.poly([(x - 50, 1740), (x + 50, 1740), (x, 1670)], (220, 160, 70, 255))
    cv.poly([(400, 1750), (460, 1750), (466, 1640), (394, 1640)], (230, 234, 240, 220))    # a glass of chai
    cv.rect(400, 1670, 460, 1740, (190, 120, 60, 255))
    cv.blur(8)
    return cv


def canteen_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    st, light = _canteen(kr, kg)
    fg = _canteen_front(0.5 * s)
    back = [
        Layer(st.im, kr, 1.0, None, "set"),
        Layer(light.im, kg, 1.0, None, "lights", mode="screen"),
        Layer(_blank(0.4 * s), 0.4 * s, 1.0, fan(380, 160, 0.4 * s, R=170, speed=2.0, top=76), "fan"),
        Layer(_blank(0.3 * s), 0.3 * s, 1.0, steam([(URN[0], URN[1] - 20, 0.8, 0.45)], 0.3 * s), "steam"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return Layered(back, front, light={"ambient": [255, 248, 232], "dir": 1, "vignette": 0.24},
                   horizon=K_VP[1], ground=K_F, sprites=[_canteen_counter(kr)])


# ------------------------------------------------------------------ dhaba (sunset)
D_VP, D_F = (540, 900), 1240
TANDOOR = (880, 760)


def _highway(k):
    """Far layer: the sunset sky over the fields and the highway."""
    cv = Cv(k, blend=True)
    cv.im = vgrad(k, [(0, (90, 70, 140)), (360, (200, 110, 140)), (700, (250, 160, 110)), (900, (255, 200, 120)),
                      (LH, (255, 200, 120))])
    cv.d = ImageDraw.Draw(cv.im)
    g = Cv(k, fill=(255, 210, 130, 0))
    g.glow(300, 860, 260, (255, 220, 150), 150)
    g.blur(24)
    cv.over(g)
    cv.ell(300, 860, 60, 60, (255, 236, 180, 255))
    _leaves(cv, 40, -40, LW + 40, 860, 940, 34, ((110, 70, 80), (140, 90, 90)), 171)   # trees on the horizon
    cv.rect(-20, 920, LW + 20, LH, (150, 110, 80, 255))
    cv.rect(-20, 960, LW + 20, 1010, (90, 84, 90, 255))                                # the highway
    for x in range(-20, LW, 120):
        cv.rect(x, 982, x + 60, 988, (240, 220, 160, 255))
    for x in range(40, LW, 260):                                                       # poles and wires
        cv.line([(x, 960), (x, 820)], (80, 60, 70, 255), 4)
    cv.line(catenary(40, 830, 300, 830, 20), (70, 50, 60, 255), 2)
    cv.line(catenary(300, 830, 560, 830, 20), (70, 50, 60, 255), 2)
    cv.blur(2.0)
    return cv


def _truck(k):
    """Middle layer: a decorated truck parked by the highway."""
    cv = Cv(k, blend=True)
    x0, y0, x1, y1 = 520, 700, 1040, 1000
    cv.rect(x0 + 140, y0, x1, y1 - 50, (240, 170, 40, 255), INK, 3)                 # the body
    for i, col in enumerate(((220, 50, 60), (40, 140, 200), (60, 170, 80), (240, 240, 240))):
        cv.rect(x0 + 150, y0 + 14 + i * 22, x1 - 10, y0 + 30 + i * 22, col + (255,))
    quad_image(cv, sign_image("HORN OK PLEASE", (240, 170, 40), (160, 30, 40), 900, 150, border=(240, 170, 40)),
               [(x0 + 200, y0 + 120), (x1 - 40, y0 + 120), (x1 - 40, y0 + 170), (x0 + 200, y0 + 170)])
    cv.poly([(x0, y1 - 50), (x0, y0 + 90), (x0 + 30, y0 + 50), (x0 + 140, y0 + 50), (x0 + 140, y1 - 50)],
            (60, 120, 170, 255), INK, 3)                                            # the cab
    cv.rect(x0 + 30, y0 + 70, x0 + 120, y0 + 140, (190, 220, 236, 255), INK, 2)
    for wx in (x0 + 80, x0 + 300, x1 - 90):
        cv.ell(wx, y1 - 40, 40, 40, (40, 40, 44, 255), INK, 3)
        cv.ell(wx, y1 - 40, 16, 16, (170, 170, 176, 255))
    cv.blur(1.4)
    return cv


def _dhaba(k, kg):
    cv = Cv(k, blend=True)
    gA = Cv(kg, fill=(255, 190, 110, 0))
    gB = Cv(kg, fill=(255, 190, 110, 0))
    gS = Cv(kg, fill=(255, 190, 110, 0))
    rnd = random.Random(181)
    fill_tex(cv, [(-20, D_F - 10), (LW + 20, D_F - 10), (LW + 20, LH), (-20, LH)],
             [(D_F, (180, 130, 90)), (LH, (150, 106, 72))], seed=183, cell=16, lo=0.88, hi=1.08)
    for _ in range(40):
        x, y = rnd.uniform(0, LW), rnd.uniform(D_F + 20, LH)
        cv.ell(x, y, rnd.uniform(3, 7), rnd.uniform(2, 4), (130, 96, 66, 255))
    # the low brick wall at the back, open above (the highway shows)
    fill_tex(cv, [(-20, 1000), (LW + 20, 1000), (LW + 20, D_F), (-20, D_F)], [(1000, (170, 90, 66)), (D_F, (150, 80, 58))],
             seed=185, cell=10, lo=0.9, hi=1.1)
    for i, y in enumerate(range(1000, D_F, 30)):
        cv.line([(-20, y), (LW + 20, y)], (120, 64, 48, 255), 2)
        for x in range(-20 + (i % 2) * 40, LW + 20, 80):
            cv.line([(x, y), (x, y + 30)], (120, 64, 48, 255), 2)
    cv.rect(-20, 990, LW + 20, 1004, (196, 170, 150, 255), INK, 2)
    # the shed: posts, the tin roof, its beam
    for x in (40, 1040):
        cv.rect(x - 14, 420, x + 14, D_F + 30, (110, 76, 50, 255), INK, 3)
    cv.poly([(-40, 300), (LW + 40, 300), (LW + 40, 420), (-40, 420)], (150, 156, 164, 255), INK, 3)
    for x in range(-40, LW + 40, 30):
        cv.line([(x, 302), (x, 418)], (120, 126, 134, 255), 3)
    cv.rect(-40, 412, LW + 40, 436, (110, 76, 50, 255), INK, 2)
    quad_image(cv, sign_image("SHER-E-DHABA", (200, 30, 30), (255, 220, 80), 1000, 200, border=(250, 200, 60)),
               [(300, 210), (780, 210), (780, 300), (300, 300)])
    gS.glow(540, 255, 300, (255, 120, 80), 60)
    for (bx, by) in along([(300, 206), (780, 206)], 24):                            # bulbs on the board
        gA.ell(bx, by, 5, 5, (255, 230, 150, 250))
    pts = catenary(-20, 440, 1100, 440, 60)                                          # string of bulbs
    cv.line(pts, (40, 30, 40, 255), 2)
    for i, (bx, by) in enumerate(along(pts, 36)):
        (gA if i % 2 else gB).ell(bx, by + 8, 6, 6, PAL_BULB[i % len(PAL_BULB)] + (250,))
        gS.ell(bx, by + 8, 16, 16, PAL_BULB[i % len(PAL_BULB)] + (40,))
    quad_image(cv, board_image(["MENU", "DAL MAKHANI 120", "PANEER 180", "ROTI 10", "CHAI 15"], (40, 34, 30),
                               (250, 240, 220), title_col=(255, 200, 80)), [(110, 560), (380, 560), (380, 860),
                                                                           (110, 860)])
    cv.line([(130, 560), (180, 500), (310, 500), (360, 560)], (60, 50, 40, 255), 3)
    # a counter with big pots, the blue drum, the tandoor
    cv.rect(420, 900, 700, 1000, (130, 90, 60, 255), INK, 3)
    for i, x in enumerate((470, 560, 650)):
        cv.poly([(x - 38, 900), (x + 38, 900), (x + 30, 846), (x - 30, 846)], (200, 204, 210, 255), INK, 2)
        cv.ell(x, 846, 32, 9, (170, 174, 180, 255), INK, 2)
    cv.rect(730, 860, 800, 1010, (40, 90, 170, 255), INK, 3)
    cv.ell(765, 860, 35, 10, (60, 110, 190, 255), INK, 2)
    tx, ty = TANDOOR
    cv.poly([(tx - 80, 1010), (tx + 80, 1010), (tx + 70, ty), (tx - 70, ty)], (190, 110, 70, 255), INK, 3)
    cv.ell(tx, ty, 70, 18, (120, 60, 40, 255), INK, 3)
    cv.ell(tx, ty, 50, 12, (255, 150, 60, 255))
    for y in (840, 900, 960):
        cv.line([(tx - 74, y), (tx + 74, y)], (170, 96, 60, 255), 3)
    # a charpai with a plank table
    cv.poly([(240, 1150), (700, 1150), (720, 1210), (220, 1210)], (190, 160, 110, 255), INK, 3)
    for i in range(12):
        x = 240 + i * 40
        cv.line([(x, 1152), (x + 30, 1208)], (150, 120, 80, 255), 2)
        cv.line([(x + 30, 1152), (x, 1208)], (150, 120, 80, 255), 2)
    for lx in (226, 700):
        cv.rect(lx, 1210, lx + 16, 1260, (120, 80, 50, 255), INK, 2)
    cv.rect(380, 1120, 560, 1136, (140, 96, 60, 255), INK, 2)
    for x in (410, 520):
        cv.poly([(x, 1120), (x + 18, 1120), (x + 20, 1094), (x - 2, 1094)], (220, 224, 230, 255), INK, 1)
    for b in (gA, gB):
        b.blur(1.0)
    gS.blur(12)
    return cv, gA, gB, gS


def _tandoor_fire(k):
    """fn (screen): the tandoor's mouth glowing and flickering."""
    tx, ty = TANDOOR

    def fn(_im, t):
        cv = Cv(k, fill=(255, 140, 60, 0))
        f = 0.7 + 0.2 * math.sin(t * 9.0) + 0.1 * math.sin(t * 23.0 + 1.0)
        cv.glow(tx, ty - 10, 160 * f, (255, 150, 60), int(110 * f))
        return cv.im
    return fn


def _dhaba_front(k):
    cv = Cv(k, fill=(150, 110, 70, 0), blend=True)
    cv.poly([(700, 1780), (1120, 1740), (1120, 1820), (700, 1860)], (130, 90, 56, 255))   # a charpai's corner
    for i in range(10):
        x = 720 + i * 40
        cv.line([(x, 1790), (x + 30, 1850)], (200, 170, 120, 255), 6)
    cv.rect(700, 1850, 730, 1960, (110, 74, 46, 255))
    cv.poly([(-40, 1740), (120, 1740), (110, 1960), (-40, 1960)], (220, 224, 232, 230))   # a glass of lassi
    cv.blur(9)
    return cv


def dhaba_25d(s, zmax=1.0):
    kr = s * max(1.0, zmax)
    kg = 0.32 * s
    far = _highway(0.5 * s)
    mid = _truck(0.6 * s)
    st, gA, gB, gS = _dhaba(kr, kg)
    fg = _dhaba_front(0.5 * s)
    back = [
        Layer(far.im, 0.5 * s, 0.1, None, "far"),
        Layer(mid.im, 0.6 * s, 0.4, None, "truck"),
        Layer(st.im, kr, 1.0, None, "set"),
        Layer(gA.im, kg, 1.0, twinkle((gA.im, gB.im), 0.7, static=gS.im), "bulbs", mode="screen"),
        Layer(_blank(0.4 * s), 0.4 * s, 1.0, _tandoor_fire(0.4 * s), "tandoor", mode="screen"),
        Layer(_blank(0.3 * s), 0.3 * s, 1.0, steam([(TANDOOR[0], TANDOOR[1] - 10, 1.0, 0.3)], 0.3 * s,
                                                   color=(200, 196, 200)), "smoke"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.3, None, "foreground")]
    return Layered(back, front, light={"ambient": [255, 226, 200], "dir": 1, "vignette": 0.34},
                   horizon=D_VP[1], ground=D_F)

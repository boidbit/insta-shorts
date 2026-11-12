"""Inside a moving vehicle: a train coach, a bus, the metro, a plane, a car, an auto. The view outside the windows
scrolls in layers (far things slowly, near poles and trees fast and blurred), the vehicle rocks a little, and the
people sit on its seats. Script: `SCENE: train`, `SCENE: bus city night`, `SCENE: plane`, `SCENE: car pahad`.

Views: city, gaon, highway, pahad, samundar, clouds, tunnel (each vehicle has its own default). A time word
(night, evening...) re-lights the view; the inside keeps its own lights."""
import math
import random
import zlib

from PIL import Image, ImageFilter

from .backgrounds import G, INK
from .util import LH, LW

# kind -> default view, ground speed (logical px / s), seat type, sound bed, how it rocks
VEHICLES = {
    "train": dict(view="gaon", speed=950.0, seat="berth", ambience="train", rock="rails"),
    "bus": dict(view="city", speed=520.0, seat="bus_seat", ambience="engine", rock="bumpy"),
    "metro": dict(view="tunnel", speed=900.0, seat="metro_seat", ambience="train", rock="smooth"),
    "plane": dict(view="clouds", speed=260.0, seat="plane_seat", ambience="cabin", rock="air"),
    "car": dict(view="highway", speed=760.0, seat="car_seat", ambience="engine", rock="soft"),
    "auto": dict(view="city", speed=430.0, seat="auto_seat", ambience="engine", rock="auto"),
}
ALIASES = {"train_coach": "train", "rail": "train", "local_train": "train", "metro_train": "metro",
           "aeroplane": "plane", "airplane": "plane", "flight": "plane", "car_inside": "car", "taxi": "car",
           "cab": "car", "auto_rickshaw": "auto", "rickshaw": "auto"}
VIEWS = ("city", "gaon", "highway", "pahad", "samundar", "clouds", "tunnel")
VIEW_WORDS = {"city": "city", "shehar": "city", "sheher": "city", "gaon": "gaon", "village": "gaon", "khet": "gaon",
              "highway": "highway", "pahad": "pahad", "mountain": "pahad", "mountains": "pahad", "samundar": "samundar",
              "sea": "samundar", "clouds": "clouds", "baadal": "clouds", "badal": "clouds", "tunnel": "tunnel"}
SEATS = tuple(v["seat"] for v in VEHICLES.values())
# Real-world proportions at the people's scale (a seated person is ~540 logical px from the seat to the top of the
# head, ~6 px a cm): the wall stands right behind the seats, a window starts at a seated person's chest and ends a
# little above the head, so a head sits in the window like it does on a real train / bus / plane.
FLOOR_Y = 1610
BANDS = {"train": (900, 1320), "bus": (740, 1270), "metro": (740, 1250), "plane": (942, 1178),
         "car": (890, 1250), "auto": (880, 1340)}        # the window band (top, bottom) of each vehicle
VIEW_CENTER = 575                                         # the views are drawn around this height, then moved
# speeds of the outside layers relative to the ground speed, back to front
LAYER_SPEEDS = (0.05, 0.3, 1.0)


def resolve(kind):
    k = str(kind or "").lower()
    k = ALIASES.get(k, k)
    return k if k in VEHICLES else None


# ------------------------------------------------------------------ the vehicle rocks
def rock(kind, t):
    """(dx, dy) logical px the whole picture moves at time t: rail joints, potholes, a plane's slow float."""
    style = VEHICLES.get(kind, {}).get("rock")
    if style == "rails":            # a soft sway and a little bump at every rail joint
        ph = (t % 0.62) / 0.62
        bump = 3.2 * math.exp(-ph * 9.0) * math.sin(ph * 30.0)
        return 2.0 * math.sin(t * 2.1), 1.6 * math.sin(t * 5.3) + bump
    if style == "bumpy":
        return (1.5 * math.sin(t * 1.7), 2.6 * math.sin(t * 6.1) + 1.8 * math.sin(t * 9.7 + 1.3)
                + (4.0 * math.sin((t % 3.7) * 18.0) * math.exp(-(t % 3.7) * 5.0)))
    if style == "auto":             # the little engine shakes everything
        return 1.2 * math.sin(t * 23.0), 1.4 * math.sin(t * 31.0) + 2.2 * math.sin(t * 4.3)
    if style == "air":              # floats, and now and then a bit of turbulence
        tb = t % 7.0
        shake = 4.0 * math.sin(tb * 26.0) * max(0.0, 1.0 - abs(tb - 5.6) / 0.6) if 5.0 < tb < 6.2 else 0.0
        return 3.0 * math.sin(t * 0.7), 4.0 * math.sin(t * 0.9 + 0.5) + shake
    if style == "soft":
        return 0.8 * math.sin(t * 1.3), 1.2 * math.sin(t * 4.1) + 0.8 * math.sin(t * 7.3)
    return 0.5 * math.sin(t * 1.1), 0.9 * math.sin(t * 3.3)          # smooth (metro)


# ------------------------------------------------------------------ outside
def _wide(s, tint):
    return G(s, w=LW * 2, color=tuple(tint) + (0,), mode="RGBA")


TILES = (-LW, 0, LW, 2 * LW)


def _sky(s, top, bottom, dy=0):
    g = G(s)
    g.vgrad(0, LH, top, bottom)
    if dy:                                          # the windows sit lower: the gradient follows them down
        g.rect(0, 0, LW, dy, top)
        g.vgrad(dy, LH, top, bottom)
    return g.done()


def _blur_x(im, k=5):
    """Motion blur along the travel direction (near things whizz past)."""
    w, h = im.size
    return im.resize((max(1, w // k), h), Image.BOX).resize((w, h), Image.BILINEAR)


def _lift(im, dy):
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    out.paste(im, (0, -int(round(dy))))
    return out


def _night_layer(im, amount=0.6):
    """Darken an RGBA layer (keeps its transparency)."""
    r, g, b, a = im.split()
    dark = Image.merge("RGB", (r, g, b))
    dark = Image.blend(dark, Image.new("RGB", dark.size, (12, 16, 40)), amount)
    out = dark.convert("RGBA")
    out.putalpha(a)
    return out


def outside(view, s, time=None, kind=None):
    """(sky picture, [(wide RGBA layer, speed)...]) of the view out of the windows of `kind` (moved into its band)."""
    band = BANDS.get(kind)
    dy = (band[0] + band[1]) / 2.0 - VIEW_CENTER if band else 0.0
    sky, layers = _outside(view, s, time, dy)
    if dy:
        layers = [(_lift(l, -dy * s), sp) for l, sp in layers]
    return sky, layers


def _outside(view, s, time, dy):
    night = time == "night"
    rnd = random.Random(zlib.crc32(view.encode()) % 1000)
    if view == "clouds":
        sky = _sky(s, (40, 96, 190) if not night else (8, 12, 40), (170, 214, 248) if not night else (40, 40, 90),
                   dy)
        far, near = _wide(s, (255, 255, 255)), _wide(s, (255, 255, 255))
        for ox in TILES:
            for (x, y, r) in ((120, 640, 60), (430, 520, 80), (760, 700, 70), (980, 560, 50)):
                for dx, dy, rr in ((0, 0, 1.0), (r * 0.9, 10, 0.8), (-r * 0.9, 14, 0.75)):
                    far.circle(ox + x + dx, y + dy, r * rr, (250, 252, 255, 210))
            for (x, y, r) in ((260, 820, 140), (820, 420, 120)):
                for dx, dy, rr in ((0, 0, 1.0), (r * 0.8, 20, 0.85), (-r * 0.85, 26, 0.8), (0, 40, 0.9)):
                    near.circle(ox + x + dx, y + dy, r * rr, (255, 255, 255, 235))
        layers = [(far.done(), 0.12), (_blur_x(near.done(), 3), 0.55)]
        return sky, [(_night_layer(l) if night else l, sp) for l, sp in layers]
    if view == "tunnel":
        sky = _sky(s, (22, 22, 28), (34, 34, 40), dy)
        mid, near = _wide(s, (60, 60, 66)), _wide(s, (255, 214, 120))
        for ox in TILES:
            for x in range(0, LW, 180):
                mid.rect(ox + x, 300, ox + x + 8, 900, (44, 44, 50, 255))
            for y in (420, 470, 760):
                mid.line([(ox, y), (ox + LW, y + 6)], (18, 18, 22, 255), 6)
            for x in (120, 650):
                near.rect(ox + x, 560, ox + x + 160, 600, (255, 220, 140, 255))
                near.circle(ox + x + 80, 580, 70, (255, 220, 140, 70))
        return sky, [(mid.done(), 0.85), (_blur_x(near.done(), 6), 1.0)]
    tops = {"city": ((140, 196, 240), (214, 234, 246)), "gaon": ((126, 194, 242), (230, 240, 222)),
            "highway": ((130, 190, 238), (226, 236, 240)), "pahad": ((110, 170, 230), (226, 238, 248)),
            "samundar": ((110, 180, 236), (232, 242, 246))}
    top, bottom = ((14, 18, 50), (54, 50, 96)) if night else tops[view]
    sky = _sky(s, top, bottom, dy)
    far, mid, near = _wide(s, (150, 170, 190)), _wide(s, (120, 140, 120)), _wide(s, (40, 44, 40))
    for ox in TILES:
        if view == "city":
            x = 0
            while x < LW:                                           # the far skyline
                w, h = rnd.randint(70, 130), rnd.randint(220, 420)
                far.rect(ox + x, 820 - h, ox + x + w, 900, (168, 182, 204, 255))
                x += w + rnd.randint(4, 20)
            x = 0
            cols = [(222, 150, 110), (240, 210, 140), (150, 190, 210), (200, 160, 210), (170, 210, 160)]
            while x < LW:                                           # shops and flats
                w, h = rnd.randint(160, 260), rnd.randint(260, 460)
                c = cols[rnd.randint(0, 4)]
                mid.rect(ox + x, 900 - h, ox + x + w, 960, c + (255,), INK + (255,), 4)
                for wy in range(900 - h + 30, 840, 70):
                    for wx in range(x + 20, x + w - 40, 56):
                        lit = (255, 220, 120, 255) if night and rnd.random() < 0.6 else (90, 120, 150, 255)
                        mid.rect(ox + wx, wy, ox + wx + 30, wy + 36, lit)
                mid.rect(ox + x + 10, 850, ox + x + w - 10, 900, (60, 60, 64, 255))   # the shop shutter
                x += w + rnd.randint(10, 40)
            for x in (160, 700):                                    # lamp posts and a tree whizzing past
                near.rect(ox + x, 250, ox + x + 22, 1000, (40, 40, 44, 255))
                near.rect(ox + x - 40, 250, ox + x + 60, 270, (40, 40, 44, 255))
            near.circle(ox + 450, 520, 150, (60, 120, 70, 255))
            near.rect(ox + 440, 600, ox + 462, 1000, (90, 66, 44, 255))
        elif view in ("gaon", "highway"):
            for (hx, hy, hr) in ((120, 860, 260), (520, 840, 320), (900, 870, 260)):
                far.ellipse(ox + hx - hr, hy - hr * 0.45, ox + hx + hr, hy + hr * 0.6, (120, 160, 150, 255))
            mid.rect(ox, 860, ox + LW, 1000, (150, 190, 100, 255) if view == "gaon" else (120, 160, 90, 255))
            for i in range(6):                                      # trees, huts / billboards
                x = i * 180 + rnd.randint(0, 60)
                mid.circle(ox + x, 760, rnd.randint(50, 80), (70, 130, 70, 255))
                mid.rect(ox + x - 8, 790, ox + x + 8, 870, (100, 74, 48, 255))
            if view == "gaon":
                for x in (300, 820):
                    mid.rect(ox + x, 780, ox + x + 120, 870, (196, 150, 104, 255), INK + (255,), 4)
                    mid.poly([(ox + x - 16, 784), (ox + x + 60, 720), (ox + x + 136, 784)], (150, 100, 60, 255),
                             INK + (255,), 4)
                for x in range(0, LW, 120):                         # a fence along the line
                    near.rect(ox + x, 820, ox + x + 14, 1000, (110, 80, 50, 255))
                near.line([(ox, 860), (ox + LW, 860)], (110, 80, 50, 255), 8)
                near.rect(ox + 600, 200, ox + 620, 1000, (60, 60, 64, 255))           # an electric pole
                near.line([(ox, 260), (ox + LW, 300)], (30, 30, 34, 255), 3)
            else:
                mid.rect(ox + 400, 600, ox + 640, 740, (250, 240, 230, 255), INK + (255,), 5)  # a billboard
                mid.rect(ox + 420, 620, ox + 620, 720, (230, 90, 70, 255))
                mid.rect(ox + 510, 740, ox + 530, 860, (80, 80, 84, 255))
                near.rect(ox, 900, ox + LW, 930, (200, 200, 206, 255))                 # the crash barrier
                for x in range(0, LW, 200):
                    near.rect(ox + x, 900, ox + x + 16, 1000, (150, 150, 156, 255))
                near.rect(ox + 300, 300, ox + 318, 1000, (60, 60, 64, 255))
        elif view == "pahad":
            for (px, ph) in ((150, 500), (500, 600), (860, 520)):
                far.poly([(ox + px - 330, 900), (ox + px, 900 - ph), (ox + px + 330, 900)], (150, 170, 200, 255))
                far.poly([(ox + px - 90, 900 - ph + 120), (ox + px, 900 - ph), (ox + px + 90, 900 - ph + 120)],
                         (250, 252, 255, 255))
            for i in range(9):
                x = i * 130 + rnd.randint(0, 40)
                h = rnd.randint(140, 220)
                mid.poly([(ox + x - 50, 900), (ox + x, 900 - h), (ox + x + 50, 900)], (60, 110, 80, 255))
            mid.rect(ox, 880, ox + LW, 1000, (90, 130, 90, 255))
            for x in (200, 760):
                near.poly([(ox + x - 90, 1000), (ox + x, 520), (ox + x + 90, 1000)], (40, 80, 56, 255))
        elif view == "samundar":
            far.rect(ox, 700, ox + LW, 1000, (60, 140, 200, 255))
            for x in (300, 800):
                far.poly([(ox + x, 690), (ox + x + 90, 690), (ox + x + 70, 705), (ox + x + 20, 705)],
                         (240, 240, 240, 255))
            mid.rect(ox, 860, ox + LW, 1000, (236, 214, 160, 255))
            for x in (200, 650):
                mid.line([(ox + x, 880), (ox + x + 30, 640)], (120, 90, 60, 255), 14)
                for a in range(5):
                    ang = math.radians(200 + a * 35)
                    mid.line([(ox + x + 30, 640), (ox + x + 30 + 110 * math.cos(ang), 640 + 60 * math.sin(ang))],
                             (60, 140, 70, 255), 12)
            for x in range(0, LW, 260):
                near.rect(ox + x, 820, ox + x + 18, 1000, (200, 200, 206, 255))
            near.line([(ox, 830), (ox + LW, 830)], (200, 200, 206, 255), 8)
    layers = [(far.done(), LAYER_SPEEDS[0]), (mid.done(), LAYER_SPEEDS[1]), (_blur_x(near.done(), 5), LAYER_SPEEDS[2])]
    if view != "city":                              # the land sits low: lift it into the window band
        layers = [(_lift(l, 170 * s), sp) for l, sp in layers]
    if night and view != "city":
        layers = [(_night_layer(l), sp) for l, sp in layers]
    elif night:
        layers = [(_night_layer(l, 0.35), sp) for l, sp in layers]
    return sky, layers


# ------------------------------------------------------------------ inside
def _canvas(s):
    return G(s, color=(0, 0, 0, 0), mode="RGBA")


def _hole(g, x0, y0, x1, y1, r=0, oval=False):
    """A see-through window, with a little reflection on the glass."""
    if oval:
        g.ellipse(x0, y0, x1, y1, (0, 0, 0, 0))
    elif r:
        g.rrect(x0, y0, x1, y1, r, (0, 0, 0, 0))
    else:
        g.rect(x0, y0, x1, y1, (0, 0, 0, 0))


def _glare(g, x0, y0, x1, y1):
    w = x1 - x0
    g.poly([(x0 + w * 0.15, y1), (x0 + w * 0.32, y0), (x0 + w * 0.42, y0), (x0 + w * 0.25, y1)], (255, 255, 255, 34))
    g.poly([(x0 + w * 0.5, y1), (x0 + w * 0.62, y0), (x0 + w * 0.66, y0), (x0 + w * 0.54, y1)], (255, 255, 255, 26))


def _floor(g, col, lines=None):
    g.rect(0, FLOOR_Y, LW, LH, col + (255,))
    for i, y in enumerate((FLOOR_Y + 60, FLOOR_Y + 160, FLOOR_Y + 300, FLOOR_Y + 480)):
        g.line([(0, y), (LW, y)], (lines or tuple(max(0, c - 22) for c in col)) + (255,), 3 + i)
    g.line([(0, FLOOR_Y), (LW, FLOOR_Y)], INK + (255,), 5)


def _fan(g, x, y):
    g.circle(x, y, 22, (120, 120, 126, 255), INK + (255,), 4)
    for a in (0, 120, 240):
        r = math.radians(a + 20)
        g.poly([(x, y), (x + 130 * math.cos(r), y + 26 * math.sin(r) + 10),
                (x + 130 * math.cos(r + 0.25), y + 26 * math.sin(r + 0.25) + 18)], (150, 150, 156, 255),
               INK + (255,), 3)
    g.line([(x, y - 22), (x, y - 70)], INK + (255,), 6)


def _stitches(g, y0, y1, col, step=90):
    for y in range(y0 + step // 2, y1, step):
        g.line([(0, y), (LW, y)], col, 3)


def inside(kind, s):
    """The vehicle's inside as an RGBA picture with see-through windows (the view shows through them). The wall stands
    right behind the seats and the windows sit at a seated person's head (see BANDS)."""
    g = _canvas(s)
    A = 255
    top, bot = BANDS[kind]
    if kind == "train":                                         # an Indian sleeper coach
        wall, low = (150, 192, 206), (92, 130, 160)
        g.rect(0, 0, LW, FLOOR_Y, wall + (A,))
        g.rect(0, bot + 20, LW, FLOOR_Y, low + (A,))
        g.rect(0, 0, LW, 300, (226, 228, 222, A))                                   # the roof
        g.line([(0, 300), (LW, 300)], INK + (A,), 4)
        g.rect(380, 300, 700, 326, (255, 255, 236, A), INK + (A,), 3)               # the tubelight
        for x in (190, 890):
            _fan(g, x, 400)
        for x in (20, 1040):                                                        # the chains of the upper berth
            g.line([(x, 300), (x, 600)], (90, 90, 96, A), 6)
        g.rrect(110, 500, 330, 604, 16, (150, 60, 50, A), INK + (A,), 4)              # luggage on the upper berth
        g.rrect(330, 530, 440, 604, 12, (230, 190, 90, A), INK + (A,), 4)
        g.rrect(760, 520, 930, 604, 14, (60, 90, 70, A), INK + (A,), 4)
        g.rect(0, 600, LW, 668, (60, 92, 150, A), INK + (A,), 5)                     # the upper berth
        for (x0, x1) in ((90, 510), (570, 990)):
            g.rrect(x0 - 18, top - 18, x1 + 18, bot + 18, 26, (210, 212, 216, A), INK + (A,), 6)
            _hole(g, x0, top, x1, bot, 18)
            _glare(g, x0, top, x1, bot)
            for y in range(top + 60, bot, 70):                                       # window bars
                g.line([(x0, y), (x1, y)], (196, 198, 204, A), 9)
            g.rect(x0 + 70, bot + 22, x1 - 70, bot + 50, (120, 90, 60, A), INK + (A,), 4)   # the little table
        g.rect(520, top - 70, 560, top - 40, (200, 40, 40, A), INK + (A,), 3)          # the alarm chain
        g.line([(540, top - 40), (540, top + 40)], (120, 120, 126, A), 4)
        _floor(g, (118, 120, 120))
    elif kind in ("bus", "metro"):
        metro = kind == "metro"
        wall, low = ((228, 230, 234), (176, 180, 188)) if metro else ((232, 220, 190), (70, 110, 150))
        g.rect(0, 0, LW, FLOOR_Y, wall + (A,))
        g.rect(0, bot + 16, LW, FLOOR_Y, low + (A,))
        g.rect(0, 0, LW, 400, (214, 216, 220, A) if metro else (210, 200, 176, A))  # the roof
        g.line([(0, 400), (LW, 400)], INK + (A,), 4)
        g.rect(80, 372, 1000, 396, (255, 255, 240, A), INK + (A,), 3)                  # ceiling lights
        bands = ((30, 500), (580, 1050)) if metro else ((30, 360), (380, 700), (720, 1050))
        for (x0, x1) in bands:
            g.rrect(x0 - 10, top - 16, x1 + 10, bot + 16, 14, (60, 62, 66, A), INK + (A,), 5)
            _hole(g, x0 + 6, top, x1 - 6, bot, 10)
            _glare(g, x0 + 6, top, x1 - 6, bot)
            if not metro:                                                             # a bus window slides
                g.line([((x0 + x1) // 2, top), ((x0 + x1) // 2, bot)], (60, 62, 66, A), 8)
        rail = 520 if metro else 560
        g.line([(0, rail), (LW, rail)], (190, 192, 198, A), 12)                        # the grab rail
        for x in range(90, LW, 150):                                                    # hanging handles
            g.line([(x, rail + 6), (x, rail + 70)], (60, 60, 66, A), 6)
            g.ellipse(x - 20, rail + 66, x + 20, rail + 106, None, (60, 60, 66, A), 7)
        if metro:
            g.rect(80, 630, 1000, 676, (250, 250, 250, A), INK + (A,), 3)              # the route map
            g.line([(110, 653), (970, 653)], (220, 60, 60, A), 6)
            for x in range(130, 970, 95):
                g.circle(x, 653, 9, (255, 255, 255, A), (220, 60, 60, A), 4)
            for x in (300, 780):                                                        # poles
                g.rect(x, 400, x + 16, FLOOR_Y, (200, 202, 208, A), INK + (A,), 3)
        else:
            g.rect(470, 440, 610, 480, (250, 220, 70, A), INK + (A,), 3)               # a sign
            g.circle(1030, top - 50, 14, (220, 40, 40, A), INK + (A,), 3)              # the stop bell
        _floor(g, (150, 152, 156) if metro else (62, 64, 68))
    elif kind == "plane":
        wall = (236, 232, 222)
        g.rect(0, 0, LW, FLOOR_Y, wall + (A,))
        g.rect(0, 0, LW, 380, (226, 224, 216, A))                                       # the ceiling
        g.rrect(-40, 380, LW + 40, 690, 40, (222, 222, 218, A), INK + (A,), 5)          # overhead bins
        for x in range(180, LW, 260):
            g.line([(x, 390), (x, 686)], (180, 180, 178, A), 4)
            g.rect(x - 70, 640, x - 30, 660, (120, 120, 120, A))
        g.rrect(470, 712, 610, 756, 10, (40, 40, 44, A), INK + (A,), 3)                 # the seat-belt sign
        g.rect(492, 722, 520, 746, (250, 210, 80, A))
        g.rect(540, 722, 588, 746, (250, 210, 80, A))
        g.line([(0, bot + 90), (LW, bot + 90)], (214, 210, 200, A), 6)                  # the side panel's edge
        for cx in (220, 540, 860):
            g.ellipse(cx - 92, top - 22, cx + 92, bot + 22, (210, 208, 200, A), INK + (A,), 6)
            _hole(g, cx - 70, top, cx + 70, bot, oval=True)
            g.rect(cx - 70, top, cx + 70, top + 50, (200, 200, 196, A))               # the blind, half down
            g.line([(cx - 70, top + 50), (cx + 70, top + 50)], INK + (A,), 3)
        _floor(g, (64, 82, 140))
    elif kind == "car":
        g.rect(0, 0, LW, FLOOR_Y, (90, 90, 96, A))
        g.rect(0, 0, LW, top - 40, (204, 200, 190, A))                                  # the roof lining
        g.rect(0, top - 120, LW, top - 40, (190, 186, 176, A))
        g.circle(540, 420, 34, (250, 246, 220, A), INK + (A,), 4)                         # the cabin light
        for x0 in (190, 760):                                                           # grab handles over the doors
            g.rrect(x0, top - 104, x0 + 130, top - 80, 10, (150, 146, 136, A), INK + (A,), 3)
        g.poly([(40, top - 30), (480, top - 30), (500, bot + 18), (40, bot + 18)], (40, 40, 44, A))
        g.poly([(580, top - 30), (1040, top - 30), (1040, bot + 18), (560, bot + 18)], (40, 40, 44, A))
        _hole(g, 64, top - 10, 468, bot)
        _hole(g, 592, top - 10, 1020, bot)
        _glare(g, 64, top - 10, 468, bot)
        _glare(g, 592, top - 10, 1020, bot)
        g.rect(500, top - 60, 560, bot + 60, (30, 30, 34, A))                           # the middle pillar
        g.rect(0, bot + 40, LW, bot + 80, (70, 70, 76, A))                              # the door's top
        g.rect(120, bot + 130, 300, bot + 160, (150, 150, 156, A), INK + (A,), 3)        # door handles
        g.rect(680, bot + 130, 860, bot + 160, (150, 150, 156, A), INK + (A,), 3)
        _floor(g, (40, 40, 44))
    elif kind == "auto":
        g.rect(0, 0, LW, top, (30, 30, 32, A))                                          # the black canopy
        _stitches(g, 0, top - 60, (52, 52, 56, A))
        g.rect(0, top - 40, LW, top, (240, 200, 40, A))
        g.rrect(800, 200, 1000, 290, 14, (20, 20, 22, A), (70, 70, 76, A), 4)            # the music speaker
        for x in (850, 950):
            g.circle(x, 245, 30, (60, 60, 66, A), INK + (A,), 3)
        g.rect(0, bot, LW, FLOOR_Y, (40, 120, 70, A))                                   # green body below
        g.rect(0, bot, LW, bot + 20, (240, 200, 40, A))
        g.rect(0, top, 50, bot, (30, 30, 32, A))
        g.rect(LW - 50, top, LW, bot, (30, 30, 32, A))
        _hole(g, 50, top, LW - 50, bot)                                                 # open sides: no glass
        g.line([(50, top + 80), (LW - 50, top + 80)], (200, 202, 208, A), 10)           # the grab bar
        g.rrect(60, top + 120, 200, top + 220, 12, (20, 20, 22, A), INK + (A,), 3)      # the fare meter
        g.rect(80, top + 140, 180, top + 180, (230, 60, 40, A))
        _floor(g, (34, 34, 36))
    return g.done()

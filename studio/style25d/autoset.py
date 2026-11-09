"""Auto 2.5D: any studio place, drawn by its normal 2D code, split into depth layers.

The place functions (studio.locations / studio.backgrounds) draw with a canvas `G`. Here they draw with
LayeredG instead, which sends every shape to the layer the code is in: helpers mark the sky
(`with g.on("sky")`), the skyline ("far"), tree rows ("mid"), the view through a window ("window",
with `g.punch` opening the glass in the room) - everything else is the set the people stand in. The 2D
pictures do not change: a normal G ignores all of this.

Then every place gets the same 2.5D finish: far layers softly blurred and hazed, a glow round windows and
bulbs, a patch of window light on the floor, and (indoors) a blurred plant right in front of the lens.
"""
import contextlib
import math
import random

import numpy as np
from PIL import Image, ImageDraw

from ..util import LH, LW
from .scenery import Cv, Layer, Layered, twinkle

# depth of each layer (0 = sky at infinity, 1 = the floor the people stand on)
DEPTH = {"sky": 0.04, "far": 0.3, "window": 0.12, "mid": 0.6, "set": 1.0}
ORDER = ("sky", "far", "window", "mid", "set")
BLUR = {"sky": 0.0, "far": 2.2, "window": 2.0, "mid": 1.0, "set": 0.0}
OUTDOOR_LIGHT = {"ambient": [255, 252, 246], "vignette": 0.16, "dir": -1}
INDOOR_LIGHT = {"ambient": [255, 249, 242], "vignette": 0.22, "dir": -1}


class LayeredG:
    """Drop-in for studio.backgrounds.G that records into depth layers (RGBA, k px per logical unit)."""
    layered = True

    def __init__(self, s, w=LW, h=LH, color=(255, 255, 255), mode="RGB"):
        self.k = s
        self.s = s
        self.size = (int(round(w * s)), int(round(h * s)))
        self.layers = {"sky": Image.new("RGBA", self.size, tuple(color[:3]) + (255,))}  # base colour at the back
        self.cur = "set"
        self.windows = []
        self.lights = []
        self._use("set")

    # -- layers
    def _use(self, name):
        if name not in self.layers:
            self.layers[name] = Image.new("RGBA", self.size, (0, 0, 0, 0))
        self.cur = name
        self.d = ImageDraw.Draw(self.layers[name])

    @property
    def im(self):
        return self.layers[self.cur]

    @im.setter
    def im(self, value):                      # a place that paints on g.im directly (cinema) keeps working
        self.layers[self.cur] = value.convert("RGBA")
        self.d = ImageDraw.Draw(self.layers[self.cur])

    @contextlib.contextmanager
    def on(self, layer):
        prev = self.cur
        self._use(layer)
        try:
            yield
        finally:
            self._use(prev)

    def punch(self, x0, y0, x1, y1):
        k = self.k
        ImageDraw.Draw(self.layers["set"]).rectangle([x0 * k, y0 * k, x1 * k, y1 * k], fill=(0, 0, 0, 0))

    def note_window(self, x0, y0, x1, y1):
        self.windows.append((x0, y0, x1, y1))

    def note_light(self, x, y, r, color):
        self.lights.append((x, y, r, tuple(color[:3])))

    def overlay(self, layer):                 # light rays etc. land on the layer being drawn, keeping its see-through parts
        self.layers[self.cur] = Image.alpha_composite(self.layers[self.cur], layer)
        self.d = ImageDraw.Draw(self.layers[self.cur])

    # -- the drawing API of G (same maths, k without supersampling)
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

    def line(self, pts, color=(18, 18, 18), w=5):
        self.d.line(self._p(pts), fill=color, width=max(1, int(w * self.k)), joint="curve")

    def ellipse(self, x0, y0, x1, y1, fill=None, outline=None, w=5):
        self.d.ellipse([x0 * self.k, y0 * self.k, x1 * self.k, y1 * self.k], fill=fill,
                       outline=outline, width=max(1, int(w * self.k)) if outline else 0)

    def circle(self, cx, cy, r, fill=None, outline=None, w=5):
        self.ellipse(cx - r, cy - r, cx + r, cy + r, fill, outline, w)

    def vgrad(self, y0, y1, c0, c1, x0=0, x1=LW):
        if self.cur == "sky":                 # the sky goes on past the picture, so nearer layers can slide over it
            self.d.rectangle([x0 * self.k, 0, x1 * self.k, y0 * self.k], fill=tuple(c0[:3]))
            self.d.rectangle([x0 * self.k, y1 * self.k, x1 * self.k, self.size[1]], fill=tuple(c1[:3]))
        steps = max(2, int((y1 - y0) * self.k / 4))
        for i in range(steps):
            t = i / (steps - 1)
            c = tuple(int(c0[j] + (c1[j] - c0[j]) * t) for j in range(3))
            ya = (y0 + (y1 - y0) * i / steps) * self.k
            yb = (y0 + (y1 - y0) * (i + 1) / steps) * self.k + 1
            self.d.rectangle([x0 * self.k, ya, x1 * self.k, yb], fill=c)

    def done(self):
        return self


@contextlib.contextmanager
def layered_canvas():
    """While inside, the place functions draw on LayeredG (they look the name G up when they run)."""
    from .. import backgrounds, locations
    old = backgrounds.G, locations.G
    backgrounds.G = locations.G = LayeredG
    try:
        yield
    finally:
        backgrounds.G, locations.G = old


def place_function(place):
    from .. import backgrounds
    from ..locations import LOCATIONS
    place = {"living_room": "room", "classroom": "school"}.get(place, place)
    builtin = {"kitchen": backgrounds.kitchen, "room": backgrounds.room, "street": backgrounds.street,
               "school": backgrounds.school, "market": backgrounds.market, "office": backgrounds.office,
               "bus_stop": backgrounds.bus_stop}
    return builtin.get(place) or LOCATIONS.get(place)


# ------------------------------------------------------------------ finishing touches
def _extend_window_views(win, windows, k, pad=90):
    """Repeat the edge pixels of every window view outwards, so a sliding view never shows an empty edge."""
    arr = np.asarray(win).copy()
    for (x0, y0, x1, y1) in windows:
        a, b, c, d = int(x0 * k), int(y0 * k), int(x1 * k), int(y1 * k)
        crop = arr[b:d, a:c]
        if crop.size == 0:
            continue
        p = int(pad * k)
        big = np.pad(crop, ((p, p), (p, p), (0, 0)), mode="edge")
        ya, xa = max(0, b - p), max(0, a - p)
        yb, xb = min(arr.shape[0], d + p), min(arr.shape[1], c + p)
        region = big[(ya - (b - p)):(ya - (b - p)) + (yb - ya), (xa - (a - p)):(xa - (a - p)) + (xb - xa)]
        tgt = arr[ya:yb, xa:xb]
        empty = tgt[..., 3:4] == 0
        arr[ya:yb, xa:xb] = np.where(empty, region, tgt)
    return Image.fromarray(arr, "RGBA")


def _extend_down(im, k, pad=170, low=0.35):
    """A far layer (skyline, sea, mountains) goes on a little below where the 2D picture covers it, so the nearer set
    sliding over it never opens a gap: every column whose shape reaches the lower part of the picture is continued
    downwards with its own colour (taken just above the outline)."""
    arr = np.asarray(im).copy()
    h, w = arr.shape[:2]
    solid = arr[..., 3] > 200
    has = solid.any(axis=0)
    last = np.where(has, h - 1 - np.argmax(solid[::-1], axis=0), -1)
    ok = has & (last > low * h)
    if not ok.any():
        return im
    src = np.clip(last - int(14 * k), 0, h - 1)
    color = arr[src, np.arange(w)]
    rows = np.arange(h)[:, None]
    fill = (rows > last[None, :]) & (rows <= last[None, :] + int(pad * k)) & ok[None, :] & (arr[..., 3] == 0)
    arr = np.where(fill[..., None], color[None, :, :], arr)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def _haze(im, color, amount):
    arr = np.asarray(im).astype(np.float32)
    arr[..., :3] = arr[..., :3] * (1 - amount) + np.array(color, np.float32) * amount
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def _glows(lg, kg, indoor, floor_y, dark=False):
    """Static glow (windows, the light they throw on the floor) + twinkling bulbs: screen layers. At night the
    windows only give a faint, cool moonlight."""
    g = Cv(kg, fill=(255, 240, 210, 0))
    sky, floor = ((150, 170, 220), 26), ((150, 170, 230), 18)
    if not dark:
        sky, floor = ((255, 246, 222), 70), ((255, 240, 200), 54)
    for (x0, y0, x1, y1) in lg.windows:
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        g.glow(cx, cy, max(x1 - x0, y1 - y0) * 0.75, sky[0], sky[1])
        if indoor:                                             # the window's light on the floor, a step into the room
            w = x1 - x0
            top, bot = floor_y + 40, min(LH, floor_y + 360)
            g.poly([(x0 - 40, top), (x1 + 40, top), (x1 + w * 0.5, bot), (x0 - w * 0.2, bot)], floor[0] + (floor[1],))
    g.blur(26)
    bulbs = None
    if lg.lights:
        a, b = Cv(kg, fill=(255, 210, 140, 0)), Cv(kg, fill=(255, 210, 140, 0))
        for i, (x, y, r, c) in enumerate(lg.lights):
            (a if i % 2 else b).glow(x, y, r * 4.5, c, 140)
        a.blur(5)
        b.blur(5)
        bulbs = (a.im, b.im)
    return g.im, bulbs


def _front_plant(k, seed):
    """A big, blurred potted plant in a bottom corner, right in front of the lens (indoors)."""
    cv = Cv(k, fill=(70, 120, 60, 0))
    rnd = random.Random(seed)
    left = rnd.random() < 0.5
    bx = -40 if left else LW + 40
    for i in range(14):
        x = bx + (rnd.uniform(20, 260) if left else -rnd.uniform(20, 260))
        y = rnd.uniform(1680, 1990)
        a = rnd.uniform(0, math.pi)
        pts = []
        for j in range(18):
            t = 2 * math.pi * j / 18
            r = 58 * (1 - 0.35 * math.sin(t) ** 2)
            px, py = r * math.cos(t), r * 0.6 * math.sin(t)
            pts.append((x + px * math.cos(a) - py * math.sin(a), y + px * math.sin(a) + py * math.cos(a)))
        g = rnd.random()
        cv.poly(pts, (int(60 + 70 * g), int(120 + 60 * g), int(50 + 30 * g), 255))
    cv.blur(9)
    return cv


NO_FRONT_PLANT = {"cinema", "hospital", "haunted_house", "graveyard"}


def build_auto(place, s, zmax=1.0, time=None):
    """Layered set for a studio place (None if the place cannot be drawn this way). time: the scene's time of day
    when it is not day (the layers are re-lit by the caller; here only the window light changes)."""
    fn = place_function(place)
    if fn is None:
        return None
    k = s * min(max(zmax, 1.0), 2.0)
    with layered_canvas():
        lg = fn(k)
    if not isinstance(lg, LayeredG):
        return None
    floor_y = _floor_y(place)
    outdoor = "far" in lg.layers or "mid" in lg.layers or _sky_used(lg)
    indoor = not outdoor
    back = []
    sky_col = lg.layers["sky"].getpixel((int(lg.size[0] * 0.5), 2))[:3]
    for name in ORDER:
        im = lg.layers.get(name)
        if im is None or im.getbbox() is None:
            continue
        if name == "window":
            im = _extend_window_views(im, lg.windows, k)
        if name in ("far", "mid"):
            im = _extend_down(im, k)
        if BLUR[name]:
            cv = Cv(k)
            cv.im = im
            cv.blur(BLUR[name])
            im = cv.im
        if name in ("far", "mid", "window"):
            im = _haze(im, sky_col, 0.12 if name != "mid" else 0.06)
        back.append(Layer(im, k, DEPTH[name], None, name))
    kg = 0.32 * s
    glow, bulbs = _glows(lg, kg, indoor, floor_y, dark=time in ("night", "rain"))
    empty = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    if bulbs:
        back.append(Layer(empty, kg, 1.0, twinkle(bulbs, 0.8, static=glow), "lights", mode="screen"))
    elif lg.windows:
        back.append(Layer(glow, kg, 1.0, None, "lights", mode="screen"))
    front = []
    if indoor and place not in NO_FRONT_PLANT:
        front = [Layer(_front_plant(0.5 * s, sum(map(ord, place))).im, 0.5 * s, 1.3, None, "foreground")]
    light = dict(INDOOR_LIGHT if indoor else OUTDOOR_LIGHT)
    return Layered(back, front, light=light)


def _sky_used(lg):
    sky = lg.layers["sky"]
    base = sky.getpixel((2, 2))
    small = np.asarray(sky.resize((16, 28)))
    return bool((small != np.array(base)).any())


BUILTIN_FLOOR = {"kitchen": 1240, "room": 1260, "living_room": 1260, "street": 1370, "school": 1290,
                 "classroom": 1290, "market": 1300, "office": 1290, "bus_stop": 1330}


def _floor_y(place):
    """Where the floor starts in the 2D drawing (window light is thrown just below it)."""
    from ..locations import LOC_HORIZON
    return float(BUILTIN_FLOOR.get(place, LOC_HORIZON.get(place, 1280)))

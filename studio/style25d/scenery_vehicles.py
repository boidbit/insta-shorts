"""2.5D inside the vehicles: train, bus, metro, plane, car, auto.

The vehicle engine (studio.vehicles) already paints each inside with see-through windows and the view outside in
layers. In 2.5D those become real depth layers: the sky far away, the far / middle / near rows of the view sliding
past at their own speeds AND moving with the camera by their depth (so a close-up shows the view drifting behind the
window), the inside on the people's plane, light from outside passing over the people and the seats (sun between
poles and trees, tunnel lamps in the metro, street lights at night), and something of the vehicle blurred right in
front of the lens (the berth ladder, a seat back, a grab pole, a headrest, the auto's mirror). The seats, the
rocking, the views (`SCENE: bus pahad night`) and the time words work as before.
"""
import random

from PIL import Image

from .scenery import Cv, Layer, Layered
from ..util import LH, LW

KINDS = ("train", "bus", "metro", "plane", "car", "auto")
LIGHT = {"train": [250, 246, 236], "bus": [255, 248, 236], "metro": [242, 248, 255], "plane": [252, 250, 246],
         "car": [244, 240, 234], "auto": [255, 242, 222]}


def _slider(strip, y0, k, speed):
    """fn: one row of the view (a strip two frames wide) sliding past at `speed` logical px a second."""
    W, H = int(round(LW * k)), int(round(LH * k))

    def fn(_im, t):
        o = int(((t * speed) % LW) * k)
        part = strip.crop((o, 0, o + W, strip.height))
        out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        out.paste(part, (0, y0), part)
        return out
    return fn


def _passing_light(k, kind, view, night):
    """fn (screen): light from outside sweeping over the inside: sun between poles and trees by day, the tunnel's
    lamps in the metro, street lights at night, a steady soft sun in the plane."""
    from .. import vehicles
    top, bot = vehicles.BANDS[kind]
    speed = vehicles.VEHICLES[kind]["speed"]
    rnd = random.Random(hash(kind) % 1000)
    gaps = [rnd.uniform(0, 1) for _ in range(5)]
    if view == "tunnel" or night:
        col, period, width, alpha = (255, 190, 110), 0.9 if view == "tunnel" else 2.2, 220, 70
    elif view == "clouds" or kind == "plane":
        col, period, width, alpha = (255, 244, 214), 0.0, 0, 36
    else:
        col, period, width, alpha = (255, 240, 200), 1.6, 380, 42

    def fn(_im, t):
        cv = Cv(k, fill=col + (0,))
        if period <= 0:                                            # the plane: soft beams through the windows
            for cx in (220, 540, 860):
                cv.poly([(cx - 60, top), (cx + 60, top), (cx + 170, LH), (cx - 70, LH)], col + (alpha,))
            cv.blur(30)
            return cv.im
        u = (t % period) / period
        x = LW + width - u * (LW + 2 * width)                       # it sweeps the other way to the view's motion
        shade = 1.0
        for g in gaps:                                             # now and then a pole or a tree cuts it
            if abs(((t * speed / 900.0) + g) % 1.0 - 0.5) < 0.04:
                shade = 0.35
        a = int(alpha * shade)
        cv.poly([(x - width / 2, top - 120), (x + width / 2, top - 120), (x + width * 0.9, LH),
                 (x - width * 0.3, LH)], col + (a,))
        cv.blur(28)
        return cv.im
    return fn


def _front(k, kind):
    """Something of the vehicle right in front of the lens, blurred."""
    cv = Cv(k, fill=(60, 60, 66, 0), blend=True)
    if kind == "train":                                            # the ladder to the upper berth
        for x in (1000, 1080):
            cv.rect(x - 10, -40, x + 10, 1960, (170, 172, 178, 255))
        for y in range(160, 1900, 220):
            cv.rect(990, y, 1090, y + 18, (170, 172, 178, 255))
    elif kind == "bus":                                            # a seat back and its grab handle
        cv.poly([(-60, 1760), (420, 1760), (440, 1960), (-60, 1960)], (60, 110, 160, 255))
        cv.rect(-60, 1730, 400, 1764, (200, 202, 208, 255))
        cv.rect(1020, -40, 1050, 1960, (200, 202, 208, 255))
    elif kind == "metro":                                          # a grab pole and a hanging handle
        cv.rect(990, -40, 1030, 1960, (210, 212, 218, 255))
        cv.line([(150, -40), (150, 140)], (60, 60, 66, 255), 10)
        cv.ell(150, 180, 46, 46, None, (60, 60, 66, 255), 14)
    elif kind == "plane":                                          # the seat in front: its headrest cover
        cv.poly([(-60, 1700), (380, 1690), (400, 1960), (-60, 1960)], (64, 82, 140, 255))
        cv.rect(-40, 1700, 330, 1800, (240, 240, 236, 255))
    elif kind == "car":                                            # the front seat's headrest
        cv.poly([(700, 1680), (1060, 1680), (1080, 1960), (680, 1960)], (50, 50, 56, 255))
        cv.rect(820, 1960, 860, 1980, (40, 40, 44, 255))
    elif kind == "auto":                                           # the driver's mirror with a little charm
        cv.ell(160, 120, 150, 70, (30, 30, 34, 255))
        cv.ell(160, 120, 130, 54, (150, 170, 190, 255))
        cv.line([(160, 190), (160, 300)], (200, 40, 40, 255), 6)
        cv.ell(160, 320, 22, 22, (240, 200, 40, 255))
    cv.blur(10)
    return cv


def build(kind, s, zmax=1.0, spec=None):
    from .. import vehicles
    spec = spec if isinstance(spec, dict) else {}
    v = vehicles.VEHICLES[kind]
    view = vehicles.VIEW_WORDS.get(str(spec.get("view", "")).lower(), v["view"])
    time = spec.get("time")
    night = time == "night"
    speed = float(spec.get("scroll", v["speed"]))
    ko = 0.5 * s                                                   # the view is far / moving / blurred: half size
    kr = s * max(1.0, zmax)
    sky, wides = vehicles.outside(view, ko, time, kind)
    sky = sky.convert("RGBA")                                      # (the view is already lit for the time)
    back = [Layer(sky, ko, 0.0, None, "sky")]
    for im, mult in wides:
        bb = im.getchannel("A").getbbox()
        if not bb:
            continue
        strip = im.crop((0, bb[1], im.width, bb[3]))
        d = 0.15 + 0.6 * mult                                      # far rows drift with the camera less
        back.append(Layer(Image.new("RGBA", (8, 8), (0, 0, 0, 0)), ko, d, _slider(strip, bb[1], ko, speed * mult),
                          "view"))
    inside = vehicles.inside(kind, kr)
    back.append(Layer(inside, kr, 1.0, None, "set"))
    kl = 0.3 * s
    back.append(Layer(Image.new("RGBA", (8, 8), (0, 0, 0, 0)), kl, 1.0, _passing_light(kl, kind, view, night),
                      "window_light", mode="screen"))
    front = [Layer(_front(0.5 * s, kind).im, 0.5 * s, 1.3, None, "foreground")]
    amb = LIGHT[kind] if not night else [200, 206, 236]
    return Layered(back, front, light={"ambient": amb, "dir": 1, "vignette": 0.26}, horizon=800,
                   ground=vehicles.FLOOR_Y)


def _maker(kind):
    def make(s, zmax=1.0, spec=None):
        return build(kind, s, zmax, spec)
    return make


train_25d, bus_25d, metro_25d, plane_25d, car_25d, auto_25d = (_maker(k) for k in KINDS)

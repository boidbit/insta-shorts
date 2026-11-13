"""People in the background of a public place (a crowd), so a street, a bazaar or a station does not look empty.

They are small and far back (on the far footpath, in front of the stalls, on the platform...), never speak, never
come in front of the characters, and are a little paler than them so the eye stays on the story: a few walk past,
a few stand (on the phone, with a cup of chai, waiting). Every video gets its own people (seeded by the script),
the same ones every time it is made. Script: `CROWD: none` (nobody), `CROWD: kam` (a few, default in public
places), `CROWD: zyada` (busy). `CAMERA: classic` keeps the old empty places.

On a road place (street, bus stop) they are drawn with the background, before its traffic (a car on the road passes
in front of somebody on the far footpath); anywhere else they are pieces sorted by depth with the characters and the
counters (a queue stands in front of the bank counter, a shopper in front of the stall)."""
import random
import zlib

from PIL import Image, ImageChops, ImageEnhance

LOOKS_ADULT = ("boy", "girl", "uncle", "aunty", "college_boy", "college_girl", "office_guy", "office_girl", "dada",
               "dadi", "delivery_boy", "watchman")
LOOKS_BY_PLACE = {"school_ground": ("kid", "kid_girl", "kid", "kid_girl", "college_boy"),
                  "hospital": ("nurse", "uncle", "aunty", "dada", "doctor"),
                  "bank": ("uncle", "aunty", "office_guy", "dada", "office_girl"),
                  "dhaba": ("driver", "uncle", "boy", "driver"),
                  "railway": ("uncle", "aunty", "college_boy", "college_girl", "tt", "dada", "office_guy"),
                  "market": ("aunty", "uncle", "dadi", "girl", "boy", "aunty")}
COLORS = ("red", "blue", "green", "yellow", "orange", "purple", "pink", "teal", "maroon", "navy", "mustard", "grey",
          "white", "sky", "olive")
AMOUNT = {"none": 0, "off": 0, "nahi": 0, "no": 0, "kam": 3, "few": 3, "thode": 3, "auto": 3, "on": 3,
          "zyada": 6, "jyada": 6, "bheed": 6, "busy": 6, "many": 6, "more": 6}

# Where the crowd stands in each place: lanes of (feet y, x from, x to, "walk" / "stand"); the eye height (horizon)
# makes them as small as their distance (a person at y 1700 is the size of the characters).
# 2.5D: the hand-made sets (studio/style25d); 2D: the place pictures (studio/places_plus, locations).
LANES_25D = {
    "street_25d": [(1140, -60, 1140, "walk"), (1136, 120, 960, "stand")],
    "busstop_25d": [(1140, -60, 1140, "walk"), (1136, 300, 700, "stand")],
    "street_road_25d": [(1300, -60, 1140, "walk"), (1296, 120, 960, "stand")],
    "busstop_road_25d": [(1230, -60, 1140, "walk"), (1226, 860, 1040, "stand")],
    "market_25d": [(1340, 60, 160, "stand"), (1340, 920, 1020, "stand"), (1400, -60, 1140, "walk")],
    "festival_25d": [(1330, -60, 1140, "walk"), (1320, 820, 1000, "stand")],
    "railway_25d": [(1420, -60, 1140, "walk"), (1410, 200, 900, "stand")],
    "mall_25d": [(1320, -60, 1140, "walk"), (1310, 820, 1000, "stand")],
    "beach_25d": [(1250, -60, 1140, "walk"), (1240, 560, 760, "stand")],
    "school_ground_25d": [(1300, -60, 1140, "walk"), (1290, 380, 660, "stand")],
    "gaon_25d": [(1300, -60, 1140, "walk")],
    "canteen_25d": [(1250, 120, 560, "stand")],
    "hospital_25d": [(1310, 840, 960, "stand"), (1360, -60, 1140, "walk")],
    "bank_25d": [(1210, 520, 600, "stand"), (1210, 820, 900, "stand"), (1300, -60, 1140, "walk")],
    "dhaba_25d": [(1260, 640, 760, "stand"), (1290, -60, 1140, "walk")],
}
HORIZON_25D = {"street_road_25d": 900, "busstop_road_25d": 900, "festival_25d": 880, "railway_25d": 860,
               "mall_25d": 760, "beach_25d": 900, "gaon_25d": 900, "canteen_25d": 800, "hospital_25d": 800,
               "bank_25d": 760, "dhaba_25d": 900}
LANES_2D = {
    "street": [(1140, -60, 1140, "walk"), (1136, 120, 960, "stand")],
    "bus_stop": [(1150, -60, 1140, "walk"), (1146, 300, 760, "stand")],
    "street/road": [(1330, -60, 1140, "walk"), (1326, 160, 900, "stand")],
    "bus_stop/road": [(1310, 820, 1060, "stand")],
    "market": [(1350, -60, 1140, "walk"), (1346, 40, 140, "stand")],
    "festival_street": [(1310, -60, 1140, "walk"), (1306, 820, 1000, "stand")],
    "railway": [(1290, -60, 1140, "walk"), (1286, 200, 900, "stand")],
    "mall": [(1350, -60, 1140, "walk"), (1346, 820, 1000, "stand")],
    "beach": [(1320, -60, 1140, "walk"), (1316, 560, 760, "stand")],
    "school_ground": [(1310, -60, 1140, "walk"), (1306, 380, 660, "stand")],
    "gaon": [(1310, -60, 1140, "walk")],
    "canteen": [(1320, 120, 560, "stand")],
    "hospital": [(1320, -60, 1140, "walk")],
    "bank": [(1320, -60, 1140, "walk"), (1316, 860, 980, "stand")],
    "dhaba": [(1310, -60, 1140, "walk"), (1306, 640, 760, "stand")],
}
STAND_ACTIONS = ("text", "idle", "drink", "phone_call", "look_around", "idle")
PALE = 0.78                              # their colours, a little washed out next to the characters'


def amount(scene):
    """How many people the scene's crowd has (CROWD line; default: a few in a public place)."""
    v = str(scene.get("crowd") or (scene.get("meta") or {}).get("crowd") or "auto").strip().lower()
    return AMOUNT.get(v, 3)


def lanes_for(place, preset=None, layout=None):
    """(lanes, horizon) of a place in this look: preset = the 2.5D set (None in 2D); layout "road" = people on
    the road (a scene with a vehicle)."""
    if preset:
        return LANES_25D.get(preset, []), HORIZON_25D.get(preset, 860)
    key = place + "/road" if layout == "road" and place + "/road" in LANES_2D else place
    return LANES_2D.get(key, []), 900 if layout == "road" else 860


def extras(place, preset=None, layout=None, n=3, seed=""):
    """The people of the crowd: [dict(spec, kind, y, x0, x1, scale, period, offset, dir, action)]."""
    lanes, horizon = lanes_for(place, preset, layout)
    if not lanes or n <= 0:
        return []
    rnd = random.Random(zlib.crc32(("%s|%s|%s" % (place, preset, seed)).encode("utf-8")))
    looks = LOOKS_BY_PLACE.get(place, LOOKS_ADULT)
    out = []
    for i in range(n):
        y, xa, xb, kind = lanes[i % len(lanes)]
        if kind == "stand" and sum(1 for e in out if e["y"] == y and e["kind"] == "stand") >= 2:
            kind = "walk"                                   # two standing in one spot is enough: the rest walk by
        y = y + rnd.uniform(-6, 6)
        scale = 0.95 * max(0.12, (y - horizon) / (1700.0 - horizon))
        spec = {"look": rnd.choice(looks), "color": rnd.choice(COLORS)}
        if kind == "walk":
            d = rnd.choice((1, -1))
            out.append(dict(spec=spec, kind="walk", y=y, x0=xa, x1=xb, scale=scale, dir=d,
                            period=rnd.uniform(9.0, 15.0), offset=rnd.uniform(0, 15.0), action="walk"))
        else:
            out.append(dict(spec=spec, kind="stand", y=y, x=rnd.uniform(xa, xb), scale=scale,
                            dir=rnd.choice((1, -1)), action=rnd.choice(STAND_ACTIONS), offset=rnd.uniform(0, 5)))
    return out


class Crowd:
    """Draws the crowd onto a picture of the whole frame (logical px * s)."""

    def __init__(self, people, tint=None):
        self.people = people
        self.tint = tuple(tint) if tint else None              # the place's light (night: darker people)
        self._cache = {}

    def _sprite(self, i, e, t, s):
        from . import actions
        from .characters import build_character, render_ops
        if e["kind"] == "walk":
            span = (e["x1"] - e["x0"]) + 0.0
            u = ((t + e["offset"]) % e["period"]) / e["period"]
            x = e["x0"] + u * span if e["dir"] > 0 else e["x1"] - u * span
            facing = "right" if e["dir"] > 0 else "left"
            q = round(t * 10.0) / 10.0                          # the walk cycle, 10 poses a second
        else:
            x, facing, q = e["x"], ("right" if e["dir"] > 0 else "left"), round(t * 4.0) / 4.0
        key = (i, q, round(s, 4))
        if key not in self._cache:
            if len(self._cache) > 600:
                self._cache.clear()
            opts = {"_x": 540.0, "_bpm": 0, "_prop": None, "_dir": e["dir"], "_facing": facing, "_expr": "neutral",
                    "_amp": 0.0}
            pose = actions.pose_for(e["action"], q + e["offset"], 1.0, 0.8, i * 0.37, opts)
            spec = dict(e["spec"], facing=facing)
            if e["kind"] == "walk":
                spec["view"] = "side"
            ops, _an = build_character(spec, pose, "neutral", 0.0, q, 540.0, e["y"], e["scale"],
                                       prop=pose.get("prop"))
            r = render_ops(ops, s, int(1400 * s), int(2000 * s))
            if r is None:
                self._cache[key] = None
            else:
                im, (ox, oy) = r
                im = self._finish(im)
                self._cache[key] = (im, ox - 540.0 * s, oy)
        got = self._cache[key]
        return (got[0], int(round(got[1] + x * s)), got[2]) if got else None

    def _finish(self, im):
        a = im.getchannel("A")
        rgb = ImageEnhance.Color(im.convert("RGB")).enhance(PALE)
        if self.tint and self.tint != (255, 255, 255):
            rgb = ImageChops.multiply(rgb, Image.new("RGB", rgb.size, self.tint))
        out = rgb.convert("RGBA")
        out.putalpha(a)
        return out

    def draw(self, img, t, s):
        """Paste everybody (far to near) onto img, a picture of the whole frame at s px a logical unit."""
        for i, e in sorted(enumerate(self.people), key=lambda p: p[1]["y"]):
            got = self._sprite(i, e, t, s)
            if got:
                im, x, y = got
                a, b = max(0, -x), min(im.width, img.width - x)       # (cut at the edges of the picture)
                c, d = max(0, -y), min(im.height, img.height - y)
                if b > a and d > c:
                    part = im.crop((a, c, b, d))
                    if img.mode == "RGBA":
                        img.alpha_composite(part, dest=(x + a, y + c))
                    else:
                        img.paste(part, (x + a, y + c), part)


def layer_fn(crowd, k, size):
    """fn for a 2.5D layer: the crowd on a transparent picture of the frame at k px a logical unit."""
    def fn(_im, t):
        out = Image.new("RGBA", size, (0, 0, 0, 0))
        crowd.draw(out, t, k)
        return out
    return fn


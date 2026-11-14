"""Something strange in every video, that nobody in the story notices: people look twice and ask in the comments.

One thing per video, chosen by the place and by the video's hook (the same script always gets the same thing):
  outside   ufo (a small saucer crosses the sky), aadmi (a man in a hat stands far away, watching, then he is gone),
            at night also toota_taara (a shooting star) and aankhen (two eyes in the dark)
  inside    saaya (somebody's shadow passes over the back wall), tasveer (the portrait on the wall turns its eyes
            and grins), jhapak (the light flickers), tv (the TV of the room switches itself on for a moment)

Script: `MYSTERY: auto` (default) | `MYSTERY: off` | `MYSTERY: ufo` (a name from KINDS).
It happens once, in the middle of the story (never on the first line or the punch line), behind the people.
Part of the new camera's look: `CAMERA: classic` has none.
"""
import math
import zlib

from PIL import Image, ImageDraw, ImageFilter

from . import decor
from .locations import LOC_HORIZON

KINDS = ("ufo", "aadmi", "toota_taara", "aankhen", "saaya", "tasveer", "jhapak", "tv")
ALIASES = {"udan_tashtari": "ufo", "alien": "ufo", "man": "aadmi", "stranger": "aadmi", "ajnabi": "aadmi",
           "shooting_star": "toota_taara", "taara": "toota_taara", "star": "toota_taara", "eyes": "aankhen",
           "aankhein": "aankhen", "shadow": "saaya", "parchhai": "saaya", "photo": "tasveer", "tasvir": "tasveer",
           "picture": "tasveer", "portrait": "tasveer", "flicker": "jhapak", "light": "jhapak", "bijli": "jhapak"}
OFF = ("off", "none", "nahi", "no")
SKY = {"street", "bus_stop", "gully", "market", "gaon", "beach", "desert", "mountain_road", "cricket_ground",
       "school_ground", "night_road", "terrace", "balcony", "festival_street", "graveyard", "haunted_house",
       "railway", "dhaba", "chai_tapri", "kirana", "jungle", "park", "petrol_pump", "signal"}
INDOOR = set(decor.INDOOR) | {"room", "living_room", "kitchen", "bedroom", "office", "meeting_room", "classroom",
                              "school", "hostel", "library", "coaching", "exam_hall", "hospital", "bank",
                              "police_station", "jail", "gym", "salon", "canteen", "bathroom", "medical_store",
                              "mobile_shop", "mithai_shop", "ghar_darwaza", "lift", "atm", "buffet", "restaurant",
                              "interview_room", "call_center", "startup_office", "sarkari_daftar"}
RIDES = {"train", "bus", "metro", "plane", "car", "auto"}
NIGHT_PLACES = {"night_road", "haunted_house", "graveyard", "terrace", "festival_street"}
DUR = {"ufo": 3.8, "aadmi": 2.8, "toota_taara": 0.9, "aankhen": 2.6, "saaya": 2.6, "tasveer": 2.4, "jhapak": 1.1,
       "tv": 2.2}
SS = 2                              # sprites are drawn twice as big and reduced: soft edges


def resolve(word):
    """`MYSTERY: shadow` -> "saaya"; "auto" / "off" as they are; None for an unknown word."""
    w = str(word or "").strip().lower().replace("-", "_").replace(" ", "_")
    if w in ("auto", "on", "haan"):
        return "auto"
    if w in OFF:
        return "off"
    w = ALIASES.get(w, w)
    return w if w in KINDS else None


def pool(place, night, has_tv=False):
    """The things that can happen in a place, in the order they are picked from."""
    if place in SKY:
        return ["ufo", "aadmi"] + (["toota_taara", "aankhen"] if night else [])
    if place in RIDES:
        return ["jhapak"]
    if place in INDOOR:
        return (["tv"] if has_tv else []) + ["saaya", "tasveer", "jhapak"]
    return []


# ------------------------------------------------------------------ choosing the moment and the spot
def place_mystery(parts, seed, asked="auto"):
    """Give one part of the video its mystery (part.mystery = {...}); returns it, or None.
    parts: the video's renderers in story order. asked: "auto", "off" or a kind."""
    if asked == "off":
        return None
    cands = []
    for i, p in enumerate(parts):
        plan = p.plan
        if getattr(plan, "camera", "") != "cine" or getattr(plan, "chat", None) or p.duration < 4.0:
            continue
        bg = plan.background if isinstance(plan.background, dict) else {"type": plan.background}
        place = bg.get("type")
        night = bg.get("time") in ("night", "fireflies") or place in NIGHT_PLACES
        tvs = [oid for oid, ob in p.sets.objs.items() if ob.get("type") == "tv" and p.sets.state(oid, 0.0)[0] != "on"]
        kinds = pool(place, night, bool(tvs))
        if asked in KINDS:
            kinds = [asked] if asked in kinds or asked in ("jhapak", "saaya", "tasveer", "ufo", "aadmi") else []
        if kinds:
            cands.append((i, p, place, night, kinds, tvs))
    if not cands:
        return None
    mid = [c for c in cands if 0 < c[0] < len(parts) - 1] or cands      # not the opening, not the ending if we can
    i, p, place, night, kinds, tvs = mid[seed % len(mid)]
    kind = kinds[(seed // 7) % len(kinds)]
    dur = DUR[kind]
    lo, hi = p.duration * 0.3, max(p.duration * 0.3, p.duration * 0.78 - dur)
    t0 = lo + (hi - lo) * (((seed // 31) % 100) / 99.0)
    z, vl, vt, vw, vh = p._cam_view(t0 + dur / 2.0)
    s = p.s
    view = (vl / s, vt / s, vw / s, vh / s)              # what the camera shows then, in logical px
    horizon = float(LOC_HORIZON.get(place, 1250))
    side = 1 if (seed // 3) % 2 else -1                  # which way it goes / which edge it is at
    xs = [c.draw_pos(t0 + dur / 2.0)[0] for c in plan.chars.values() if not c.spec.get("hidden")]
    edge_x = None
    if xs and kind in ("aadmi", "aankhen", "tasveer"):   # these stand still: where the people leave the most room
        xs = sorted(xs)
        spots = [view[0] + 70.0, view[0] + view[2] - 70.0] + [(a + b) / 2.0 for a, b in zip(xs, xs[1:])]
        spots = [x for x in spots if view[0] + 50 <= x <= view[0] + view[2] - 50] or spots[:2]
        edge_x = max(spots, key=lambda x: min(abs(x - c) for c in xs))
        side = -1 if edge_x < view[0] + view[2] / 2.0 else 1
    m = dict(kind=kind, t0=round(t0, 3), t1=round(t0 + dur, 3), view=view, horizon=horizon, side=side, night=night,
             seed=seed, edge_x=edge_x)
    if kind == "tv":
        oid = tvs[seed % len(tvs)]
        p.sets.events = sorted(p.sets.events + [{"t": m["t0"], "set": oid, "state": "on"},
                                                {"t": m["t1"], "set": oid, "state": "idle"}], key=lambda e: e["t"])
        m["set"] = oid
    p.mystery = m
    return m


def _fade(t, t0, t1, a=0.35, b=0.35):
    """0..1: in over a seconds, out over b seconds."""
    return max(0.0, min(1.0, (t - t0) / a, (t1 - t) / b))


class _Art:
    """A small RGBA picture drawn in logical px around its own origin, reduced for soft edges."""

    def __init__(self, w, h, s):
        self.k = s * SS
        self.im = Image.new("RGBA", (max(2, int(w * self.k)), max(2, int(h * self.k))), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)

    def P(self, pts):
        return [(x * self.k, y * self.k) for x, y in pts]

    def ell(self, cx, cy, rx, ry, fill, outline=None, w=0):
        self.d.ellipse([(cx - rx) * self.k, (cy - ry) * self.k, (cx + rx) * self.k, (cy + ry) * self.k], fill=fill,
                       outline=outline, width=int(w * self.k))

    def poly(self, pts, fill):
        self.d.polygon(self.P(pts), fill=fill)

    def line(self, pts, fill, w):
        self.d.line(self.P(pts), fill=fill, width=max(1, int(w * self.k)), joint="curve")

    def done(self, blur=0.0, alpha=1.0):
        im = self.im
        if blur:
            im = im.filter(ImageFilter.GaussianBlur(blur * self.k))
        im = im.reduce(SS)
        if alpha < 0.999:
            im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
        return im


def _paste(img, sprite, cx, cy, s):
    """Paste a sprite with its centre at logical (cx, cy)."""
    img.paste(sprite, (int(cx * s - sprite.width / 2), int(cy * s - sprite.height / 2)), sprite)


# ------------------------------------------------------------------ the things themselves
def _ufo(m, t, s):
    a = _Art(170, 110, s)
    blink = int(t * 6)
    a.ell(85, 62, 62, 9, (120, 235, 255, 70))                           # the glow under it
    a.ell(85, 40, 26, 22, (150, 225, 245, 215), (40, 60, 80, 255), 2.5)  # the dome
    a.ell(85, 52, 70, 17, (170, 178, 196, 255), (40, 46, 60, 255), 3)    # the saucer
    a.ell(85, 47, 46, 8, (206, 212, 226, 255))
    for i in range(5):
        on = (i + blink) % 3 == 0
        a.ell(37 + i * 24, 56, 4.5, 4.5, (255, 226, 90, 255) if on else (220, 70, 60, 255))
    return a.done(alpha=_fade(t, m["t0"], m["t1"], 0.5, 0.5))


def _aadmi(m, t, s):
    a = _Art(120, 210, s)
    c = (16, 14, 22, 255)
    a.poly([(38, 62), (82, 62), (94, 168), (26, 168)], c)                # the long coat
    a.poly([(42, 164), (56, 164), (55, 204), (41, 204)], c)
    a.poly([(64, 164), (78, 164), (79, 204), (65, 204)], c)
    a.ell(60, 44, 17, 19, c)                                             # the head
    a.ell(60, 30, 38, 6.5, c)                                            # the hat's brim
    a.poly([(42, 30), (45, 6), (75, 6), (78, 30)], c)
    if (t - m["t0"]) % 1.9 > 0.16:                                       # he blinks
        for dx in (-7, 7):
            a.ell(60 + dx, 44, 2.6, 2.2, (240, 240, 230, 255))
    return a.done(alpha=0.9 * _fade(t, m["t0"], m["t1"], 0.45, 0.3))


def _aankhen(m, t, s):
    a = _Art(120, 70, s)
    a.k *= 1.0
    u = t - m["t0"]
    shut = 0.9 < u < 1.08 or 1.75 < u < 1.9
    for cx in (40, 80):
        a.ell(cx, 35, 22, 16, (190, 255, 120, 70))
        if shut:
            a.line([(cx - 11, 35), (cx + 11, 35)], (200, 255, 130, 255), 2.5)
        else:
            a.ell(cx, 35, 11, 7.5, (214, 255, 130, 255))
            a.ell(cx + 2.5 * m["side"], 35, 2.6, 6.5, (20, 30, 10, 255))
    return a.done(alpha=_fade(t, m["t0"], m["t1"], 0.3, 0.25))


_STATIC = {}


def _saaya(m, s):
    key = ("saaya", round(s, 4))
    if key not in _STATIC:
        a = _Art(360, 700, s)
        c = (0, 0, 0, 120)
        a.ell(180, 110, 62, 74, c)
        a.poly([(120, 170), (240, 170), (290, 250), (300, 700), (60, 700), (70, 250)], c)
        _STATIC[key] = a.done(blur=9.0)
    return _STATIC[key]


def _tasveer(m, awake, s):
    key = ("tasveer", awake, m["side"], round(s, 4))
    if key not in _STATIC:
        a = _Art(150, 186, s)
        a.d.rectangle([0, 0, a.im.width - 1, a.im.height - 1], fill=(92, 62, 36, 255))
        a.d.rectangle(a.P([(11, 11), (139, 175)]), fill=(214, 200, 168, 255))
        a.poly([(30, 175), (38, 132), (112, 132), (120, 175)], (70, 62, 84, 255))          # the shoulders
        a.ell(75, 92, 33, 39, (196, 150, 110, 255), (40, 30, 26, 255), 2.5)                # the face
        a.poly([(42, 86), (46, 52), (75, 44), (104, 52), (108, 86), (96, 66), (54, 66)], (36, 30, 30, 255))
        for dx in (-13, 13):
            if awake:                                    # the eyes have turned to the people, and they glow
                a.ell(75 + dx, 92, 7.5, 6.5, (255, 240, 200, 255), (40, 30, 26, 255), 1.5)
                a.ell(75 + dx + 3.5 * m["side"], 92, 3.2, 3.6, (200, 30, 30, 255))
            else:
                a.ell(75 + dx, 92, 6.5, 5, (250, 246, 236, 255), (40, 30, 26, 255), 1.5)
                a.ell(75 + dx, 92, 2.6, 3, (30, 24, 22, 255))
        if awake:
            a.d.arc([(58 * a.k), (98 * a.k), (92 * a.k), (122 * a.k)], 10, 170, fill=(40, 20, 20, 255),
                    width=int(3 * a.k))
        else:
            a.line([(66, 112), (84, 112)], (60, 36, 30, 255), 2.5)
        a.d.rectangle([0, 0, a.im.width - 1, a.im.height - 1], outline=(40, 26, 14, 255), width=int(3 * a.k))
        _STATIC[key] = a.done()
    return _STATIC[key]


def draw(img, m, t, s):
    """Behind the people: draw the mystery of this part into the picture at story time t (in place)."""
    kind = m["kind"]
    vl, vt, vw, vh = m["view"]
    on = m["t0"] <= t <= m["t1"]
    u = (t - m["t0"]) / (m["t1"] - m["t0"]) if on else 0.0
    if kind == "tasveer":                                # the portrait hangs there all the time
        x = m.get("edge_x") or vl + vw * (0.2 if m["side"] < 0 else 0.8)
        y = max(vt + 210, m["horizon"] - 760)
        _paste(img, _tasveer(m, on and 0.12 < u < 0.92, s), x, y, s)
        return
    if not on:
        return
    if kind == "ufo":
        x0, x1 = (vl + vw * 0.08, vl + vw * 0.92) if m["side"] > 0 else (vl + vw * 0.92, vl + vw * 0.08)
        y = vt + 78                                      # high in the sky, over the heads and their bubbles
        e = u * u * (3 - 2 * u)
        _paste(img, _ufo(m, t, s), x0 + (x1 - x0) * e, y + 14 * math.sin(t * 3.1), s)
    elif kind == "toota_taara":
        x0 = vl + vw * (0.04 if m["side"] > 0 else 0.96)
        y0 = vt + 24
        dx, dy = vw * 0.42 * m["side"], 150
        d = ImageDraw.Draw(img, "RGBA")
        for i in range(10):                              # the tail, thinner and fainter behind the head
            a, b = max(0.0, u - 0.05 * (i + 1) * 0.5), max(0.0, u - 0.05 * i * 0.5)
            al = int(230 * (1 - i / 10.0) * math.sin(math.pi * u))
            d.line([((x0 + dx * a) * s, (y0 + dy * a) * s), ((x0 + dx * b) * s, (y0 + dy * b) * s)],
                   fill=(255, 250, 225, al), width=max(1, int((5 - i * 0.4) * s)))
    elif kind == "aadmi":
        x = m.get("edge_x") or vl + vw * (0.1 if m["side"] < 0 else 0.9)
        _paste(img, _aadmi(m, t, s), x, m["horizon"] - 80, s)
    elif kind == "aankhen":
        x = m.get("edge_x") or vl + vw * (0.12 if m["side"] < 0 else 0.88)
        _paste(img, _aankhen(m, t, s), x, m["horizon"] - 210, s)
    elif kind == "saaya":
        x0, x1 = (vl - 200, vl + vw + 200) if m["side"] > 0 else (vl + vw + 200, vl - 200)
        sp = _saaya(m, s)
        _paste(img, sp, x0 + (x1 - x0) * u, m["horizon"] - 330, s)


def post(img, m, t):
    """Over the finished scene (under the captions): the light flickers."""
    if m["kind"] != "jhapak" or not m["t0"] <= t <= m["t1"]:
        return img
    u = t - m["t0"]
    dark = 0.0
    for a, b, k in ((0.0, 0.09, 0.5), (0.2, 0.3, 0.62), (0.62, 0.95, 0.72)):      # two quick dips, then a long one
        if a <= u <= b:
            dark = k
    if not dark:
        return img
    return img.point([int(v * (1 - dark)) for v in range(256)] * 3)


def seed_of(scene):
    return zlib.crc32(("mystery|" + str(scene.get("hook") or scene.get("name") or "reel")).encode("utf-8"))

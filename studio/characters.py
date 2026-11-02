"""Procedural desi cartoon people: oval face with ears, nose and brows, real hair
styles, Indian outfits (kurta, saree, salwar-dupatta, school uniform, blazer...),
skin tones and body builds.

A character spec can name a ready-made `look` ("uncle", "aunty", "college_girl"...)
and override any part of it (skin, hair, outfit, color, pants, shoes, build,
accessories).

Everything is first turned into a display list of polygons / polylines (so that
rotation, tilt and falling are exact geometry, not image rotation), then drawn
once at 2x supersampling and reduced.
"""
import math

from PIL import Image, ImageDraw

INK = (34, 26, 24)
MOUTH_IN = (112, 30, 40)
TONGUE = (226, 110, 120)
WHITE = (252, 252, 250)
TEAR = (150, 200, 240)
GOLD = (222, 176, 60)

PALETTE = {
    "pink": (226, 120, 150),
    "blue": (74, 128, 200),
    "green": (82, 156, 96),
    "yellow": (240, 198, 70),
    "orange": (236, 136, 52),
    "purple": (140, 96, 186),
    "red": (204, 58, 56),
    "teal": (46, 156, 150),
    "white": (244, 242, 236),
    "black": (52, 50, 56),
    "brown": (128, 86, 58),
    "grey": (146, 146, 152),
    "maroon": (128, 30, 52),
    "navy": (40, 56, 104),
    "mustard": (212, 162, 36),
    "cream": (238, 226, 196),
    "denim": (66, 96, 146),
    "khaki": (178, 156, 108),
    "magenta": (196, 46, 128),
    "saffron": (240, 134, 36),
    "olive": (112, 122, 60),
    "sky": (120, 182, 230),
    "gold": GOLD,
}

SKIN_TONES = {
    "fair": (240, 208, 176),
    "wheatish": (222, 176, 134),
    "brown": (188, 134, 94),
    "dark": (140, 94, 64),
}

HAIR_COLORS = {
    "black": (36, 30, 32),
    "brown": (94, 62, 42),
    "grey": (170, 170, 174),
    "white": (232, 232, 230),
    "henna": (150, 62, 34),
}

HAIR_STYLES = ("short", "side_part", "spiky", "curly", "balding", "bald", "long", "braid", "bun", "ponytail")
OUTFITS = ("tshirt", "shirt", "kurta", "salwar", "saree", "uniform", "blazer", "vest")
BUILDS = {"slim": (0.9, 0.0), "normal": (1.0, 6.0), "chubby": (1.2, 44.0)}
# Face variety: every character on screen gets its own face (assign_faces), or the script picks one.
FACE_SHAPES = {"oval": (1.0, 1.0), "round": (1.08, 0.94), "long": (0.9, 1.08), "square": (1.04, 0.98)}
EYE_STYLES = ("dot", "big", "small")
NOSE_STYLES = ("hook", "button", "long", "big")
BROW_STYLES = {"normal": 9, "thick": 13, "thin": 6}
FACE_WORDS = dict(
    [(f + "_face", ("face", f)) for f in FACE_SHAPES] + [(e + "_eyes", ("eyes", e)) for e in EYE_STYLES if e != "dot"]
    + [(n + "_nose", ("nose", n)) for n in NOSE_STYLES] + [(b + "_brows", ("brows", b)) for b in BROW_STYLES])
ACCESSORIES = ("glasses", "sunglasses", "cap", "turban", "moustache", "beard", "bindi", "tilak", "earrings", "tuft")

# Ready-made Indian looks. Anything in the character spec overrides these.
LOOKS = {
    "boy": dict(skin="wheatish", hair="short", outfit="tshirt", color="blue", pants="denim", shoes="white"),
    "girl": dict(skin="wheatish", hair="braid", outfit="salwar", color="pink", pants="cream", accent="yellow",
                 shoes="chappal", accessories=["earrings"]),
    "college_boy": dict(skin="brown", hair="spiky", outfit="tshirt", color="green", pants="khaki", shoes="white"),
    "college_girl": dict(skin="wheatish", hair="ponytail", outfit="tshirt", color="purple", pants="denim",
                         shoes="white", accessories=["earrings"]),
    "uncle": dict(skin="brown", hair="balding", outfit="shirt", color="sky", pants="khaki", shoes="black",
                  build="chubby", accessories=["moustache"]),
    "aunty": dict(skin="wheatish", hair="bun", outfit="saree", color="maroon", accent="gold", shoes="chappal",
                  build="chubby", accessories=["bindi", "earrings"]),
    "dada": dict(skin="brown", hair="balding", hair_color="grey", outfit="kurta", color="white", pants="white",
                 shoes="chappal", build="slim", scale=0.95, accessories=["glasses", "moustache"]),
    "dadi": dict(skin="wheatish", hair="bun", hair_color="grey", outfit="saree", color="cream", accent="maroon",
                 shoes="chappal", scale=0.92, accessories=["glasses", "bindi"]),
    "kid": dict(skin="wheatish", hair="short", outfit="uniform", color="white", pants="navy", accent="red",
                shoes="black", scale=0.74),
    "kid_girl": dict(skin="wheatish", hair="ponytail", outfit="uniform", color="white", pants="navy", accent="red",
                     shoes="black", scale=0.72),
    "office_guy": dict(skin="fair", hair="side_part", outfit="blazer", color="navy", pants="grey", accent="red",
                       shoes="black", accessories=["glasses"]),
    "office_girl": dict(skin="wheatish", hair="long", outfit="blazer", color="grey", pants="black", accent="pink",
                        shoes="black", accessories=["earrings"]),
}

HEAD_RX = 78.0
HEAD_RY = 90.0
HEAD_SCALE = 1.14   # whole head (hair, face, headwear) drawn this much bigger: readable expressions
FACE = 0.8          # face features were designed for a 100px head
NECK_H = 24.0
TORSO_H = 290.0
UA = 114.0
LA = 108.0
TH = 146.0
SH = 146.0
OUTLINE = 6.0
ARM_W = 22.0
LEG_W = 30.0

DEFAULT_POSE = dict(
    la1=-14, la2=-8, ra1=14, ra2=8,
    ll1=-7, ll2=-2, rl1=7, rl2=2,
    tilt=0.0, lift=0.0, shift=0.0,
    head_tilt=0.0, look_x=0.0, look_y=0.0,
    finger=None,      # "L" / "R": draw a pointing finger on that hand
    arms_front=False,  # draw the arms over the head (hand on the forehead)
)

# name -> (eyes, mouth, brows)
EXPRESSIONS = {
    "neutral": ("dot", "flat", None),
    "smile": ("dot", "smile", None),
    "smug": ("relaxed", "smile", None),
    "sly": ("half", "smirk", None),
    "shock": ("wide", "open", "up"),
    "shout": ("wide", "shout", "angry"),
    "laugh": ("happy", "laugh", None),
    "grin": ("dot", "grin", None),
    "cry": ("dot", "frown", "sad"),
    "angry": ("dot", "frown", "angry"),
    "surprised": ("wide", "o", "up"),
    "think": ("half", "flat", "think"),
    "wink": ("wink", "grin", None),
    "dead": ("x", "open_small", None),
    "love": ("heart", "smile", None),
    "sleepy": ("closed", "flat", None),
    "sad": ("dot", "frown", "sad"),
}
# Eyes that should not be replaced by a "blink"
NO_BLINK = {"happy", "relaxed", "closed", "x", "heart", "wink"}


def d2r(a):
    return math.radians(a)


def vec(angle_deg, length):
    """Angle 0 = straight down on screen, +90 = screen-right, 180 = up."""
    a = math.radians(angle_deg)
    return (length * math.sin(a), length * math.cos(a))


def add(p, q):
    return (p[0] + q[0], p[1] + q[1])


def mix(p, q, t):
    return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)


def rot(p, a):
    c, s = math.cos(a), math.sin(a)
    return (p[0] * c - p[1] * s, p[0] * s + p[1] * c)


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c)


def ellipse_pts(cx, cy, rx, ry, n=40, a0=0.0, a1=360.0, rot_deg=0.0):
    pts = []
    r = math.radians(rot_deg)
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        x, y = rx * math.cos(a), ry * math.sin(a)
        if rot_deg:
            x, y = rot((x, y), r)
        pts.append((cx + x, cy + y))
    return pts


def closed_ellipse(cx, cy, rx, ry, n=40, rot_deg=0.0):
    return ellipse_pts(cx, cy, rx, ry, n, 0, 360, rot_deg)[:-1]


def bezier(p0, p1, p2, n=14):
    pts = []
    for i in range(n + 1):
        t = i / n
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
        pts.append((x, y))
    return pts


def heart_pts(cx, cy, size):
    pts = []
    for i in range(40):
        t = 2 * math.pi * i / 40
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((cx + x * size / 16.0, cy + y * size / 16.0))
    return pts


def color_of(c, default="blue", table=PALETTE):
    if isinstance(c, (list, tuple)) and len(c) >= 3:
        return tuple(int(v) for v in c[:3])
    if isinstance(c, str) and c in table:
        return table[c]
    if isinstance(c, str) and c in PALETTE:
        return PALETTE[c]
    return table.get(default) or PALETTE[default]


def assign_faces(cdefs):
    """{name: spec} -> a copy where every visible character has a face of its own (face shape, eyes, nose, brows),
    picked by position so that no two look alike. What a spec already says is kept."""
    out, i = {}, 0
    for name, spec in cdefs.items():
        spec = dict(spec)
        if not spec.get("hidden"):
            spec.setdefault("face", list(FACE_SHAPES)[i % len(FACE_SHAPES)])
            spec.setdefault("eyes", EYE_STYLES[i % len(EYE_STYLES)])
            spec.setdefault("nose", NOSE_STYLES[(i * 3) % len(NOSE_STYLES)])
            spec.setdefault("brows", list(BROW_STYLES)[i % len(BROW_STYLES)])
            i += 1
        out[name] = spec
    return out


def _head_pts(shape, n=64):
    if shape != "square":
        return closed_ellipse(0, 0, HEAD_RX, HEAD_RY, n)
    pts = []
    for i in range(n):                                  # a superellipse: a squarish head with round corners
        a = 2 * math.pi * i / n
        c, s_ = math.cos(a), math.sin(a)
        pts.append((HEAD_RX * math.copysign(abs(c) ** 0.6, c), HEAD_RY * math.copysign(abs(s_) ** 0.6, s_)))
    return pts


def resolve_spec(spec):
    """Character spec with its `look` preset filled in (spec keys win)."""
    out = dict(LOOKS.get(spec.get("look"), {}))
    out.update({k: v for k, v in spec.items() if v is not None})
    acc = list(out.get("accessories", []))
    if "tuft" in acc and "hair" not in spec:
        out["hair"] = "spiky"
    out["accessories"] = acc
    return out


def _capsule(p0, p1, r0, r1, n=10):
    """Outline of a tapered capsule from p0 (radius r0) to p1 (radius r1)."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    th = math.atan2(dy, dx) if (dx or dy) else 0.0
    pts = []
    for c, r, a0 in ((p1, r1, th - math.pi / 2), (p0, r0, th + math.pi / 2)):
        for i in range(n + 1):
            a = a0 + math.pi * i / n
            pts.append((c[0] + r * math.cos(a), c[1] + r * math.sin(a)))
    return pts


class Sketch:
    """Collects drawing ops in global logical coordinates."""

    def __init__(self, x0, ground_y, k, tilt_deg, shift, lift, fy):
        self.x0, self.gy, self.k = x0, ground_y, k
        self.tilt = math.radians(tilt_deg)
        self.shift, self.lift, self.fy = shift, lift, fy
        self.ops = []

    def T(self, p):
        x = p[0] + self.shift
        y = p[1] - self.fy
        x, y = rot((x, y), self.tilt)
        return (self.x0 + x * self.k, self.gy + (y + self.lift) * self.k)

    def poly(self, pts, fill=None, outline=None, w=OUTLINE):
        self.ops.append(dict(t="poly", pts=[self.T(p) for p in pts], fill=fill,
                             outline=outline, w=w * self.k))

    def line(self, pts, w, color=INK):
        self.ops.append(dict(t="line", pts=[self.T(p) for p in pts], w=w * self.k, color=color))

    def tube(self, pts, w, fill, ow=OUTLINE * 0.8):
        """A strap / scarf: thick coloured line with an ink outline."""
        self.line(pts, w + 2 * ow, INK)
        self.line(pts, w, fill)

    def limb(self, pts, widths, fill, ow=OUTLINE * 0.8):
        """A tapering limb / sleeve (one width per point). All the ink goes down before
        the fill, so the elbow / knee joints show no seams."""
        for extra, col in ((2 * ow, INK), (0.0, fill)):
            for i in range(len(pts) - 1):
                self.poly(_capsule(pts[i], pts[i + 1], (widths[i] + extra) / 2.0, (widths[i + 1] + extra) / 2.0), col)

    def dot(self, c, r, fill=INK, outline=None, w=OUTLINE):
        n = 56 if r > 40 else (32 if r > 12 else 20)
        self.poly(closed_ellipse(c[0], c[1], r, r, n), fill, outline, w)


def skeleton(p):
    hipL, hipR = (-32.0, 0.0), (32.0, 0.0)
    kneeL = add(hipL, vec(p["ll1"], TH))
    footL = add(kneeL, vec(p["ll2"], SH))
    kneeR = add(hipR, vec(p["rl1"], TH))
    footR = add(kneeR, vec(p["rl2"], SH))
    shL, shR = (-56.0, -TORSO_H + 22), (56.0, -TORSO_H + 22)
    ak = p.get("arm_k", 1.0)          # riders get longer arms so their hands reach the handlebar
    elbL = add(shL, vec(p["la1"], UA * ak))
    handL = add(elbL, vec(p["la2"], LA * ak))
    elbR = add(shR, vec(p["ra1"], UA * ak))
    handR = add(elbR, vec(p["ra2"], LA * ak))
    neck = (0.0, -TORSO_H + 4)
    hc = add(neck, rot((0.0, -(NECK_H + HEAD_RY * 0.8 * HEAD_SCALE)), d2r(p["head_tilt"])))
    fy = max(footL[1], footR[1]) + 12
    return dict(hipL=hipL, hipR=hipR, kneeL=kneeL, footL=footL, kneeR=kneeR, footR=footR,
                shL=shL, shR=shR, elbL=elbL, handL=handL, elbR=elbR, handR=handR,
                neck=neck, hc=hc, fy=fy)


def _draw_prop(S, prop, hand, fore_angle, color_hint):
    """Small props held in the hand. fore_angle = direction of the forearm."""
    if not prop:
        return
    d = vec(fore_angle, 1.0)
    n = (-d[1], d[0])

    def pt(a, b):
        return (hand[0] + d[0] * a + n[0] * b, hand[1] + d[1] * a + n[1] * b)

    if prop == "spoon":
        S.line([pt(-10, 0), pt(62, 0)], 9, (150, 150, 156))
        S.poly([pt(62 + 30 * math.cos(a), 30 * math.sin(a) * 0.62)
                for a in [i * math.pi / 12 for i in range(24)]],
               (190, 190, 196), INK, 5)
    elif prop == "phone":
        S.poly([pt(-12, -20), pt(-12, 20), pt(62, 20), pt(62, -20)], (40, 44, 52), INK, 5)
        S.poly([pt(-4, -14), pt(-4, 14), pt(54, 14), pt(54, -14)], (120, 190, 235), None)
    elif prop == "mic":
        S.line([pt(-14, 0), pt(40, 0)], 12, (70, 70, 76))
        S.dot(pt(56, 0), 22, (60, 60, 66), INK, 5)
    elif prop == "cup":
        S.poly([pt(-8, -22), pt(-8, 22), pt(52, 16), pt(52, -16)], (240, 240, 236), INK, 5)
        S.line([pt(10, 22), pt(10, 34), pt(26, 34)], 5)
    elif prop == "ball":
        S.dot(pt(30, 0), 32, (232, 120, 60), INK, 5)
    elif prop == "stick":
        S.line([pt(-30, 0), pt(150, 0)], 10, (150, 104, 70))
    elif prop == "bag":                       # a black garbage bag hanging from the hand
        top = (hand[0], hand[1] + 6)
        S.poly([(top[0] - 14, top[1]), (top[0], top[1] - 18), (top[0] + 14, top[1])], (28, 28, 34), INK, 5)
        S.poly([(top[0] + 30 * math.cos(a), top[1] + 46 + 52 * math.sin(a))
                for a in [i * math.pi / 12 for i in range(24)]], (36, 36, 44), INK, 6)
        S.line([(top[0] - 14, top[1] + 30), (top[0] - 4, top[1] + 62)], 4, (74, 74, 84))


def _eye_center(sgn, face_dx, ey=-4.0, ex=34.0):
    return (sgn * ex + face_dx, ey)


# ---------------------------------------------------------------- body parts
def _torso_pts(top, hem, sw, ww, hw, belly):
    """Torso silhouette: shoulders (half width sw) -> waist (ww, + belly) -> hem (hw)."""
    left = [(-sw + 18, top), (-sw - 2, top + 22)]
    left += bezier((-sw - 2, top + 22), (-ww - belly * 1.6, (top + hem) * 0.5 + 30), (-hw, hem), 16)[1:]
    right = [(-x, y) for x, y in reversed(left)]
    return left + right


def _draw_feet(S, sk, shoes, skin):
    for sgn, foot in ((-1, sk["footL"]), (1, sk["footR"])):
        c = (foot[0] + sgn * 14, foot[1] - 4)
        if shoes == "chappal":
            S.poly(closed_ellipse(c[0], c[1] + 6, 30, 9, 20), (120, 80, 50), INK, 4)
            S.poly(closed_ellipse(c[0], c[1] - 2, 24, 11, 20), skin, INK, 4)
            S.line([(c[0] - 12, c[1] - 6), (c[0] + 12, c[1] - 6)], 6, (120, 80, 50))
        else:
            col = color_of(shoes, "black")
            S.poly(closed_ellipse(c[0], c[1], 30, 14, 24), col, INK, 5)
            if shoes == "white":
                S.line([(c[0] - 26, c[1] + 6), (c[0] + 26, c[1] + 6)], 4, (190, 190, 190))


def _draw_outfit(S, o, sk, cols, build):
    outfit = o.get("outfit", "tshirt")
    main, accent, skin = cols["main"], cols["accent"], cols["skin"]
    bw, belly = BUILDS.get(build, BUILDS["normal"])
    top = -TORSO_H + 6
    sw, ww = 62 * bw, 52 * bw

    if outfit == "saree":
        hem_y = max(sk["footL"][1], sk["footR"][1]) - 20
        xl = min(sk["kneeL"][0], sk["footL"][0]) - 26
        xr = max(sk["kneeR"][0], sk["footR"][0]) + 26
        waist = -120
        skirt = [(-ww - belly * 0.6, waist)] + bezier((-ww - belly, waist + 60), (xl + 4, hem_y - 120), (xl, hem_y), 8) \
            + [(xr, hem_y)] + bezier((xr, hem_y), (xr - 4, hem_y - 120), (ww + belly, waist + 60), 8) \
            + [(ww + belly * 0.6, waist)]
        S.poly(skirt, main, INK, OUTLINE)
        S.line([(xl + 6, hem_y - 12), (xr - 6, hem_y - 12)], 12, accent)
        # pleats
        for dx in (-14, 0, 14):
            S.line([(dx, waist + 40), (dx * 1.6, hem_y - 24)], 3, shade(main, 0.78))
        # midriff + blouse
        S.poly(_torso_pts(top, waist + 8, sw, ww, ww + belly * 0.5, belly * 0.6), skin, INK, OUTLINE)
        S.poly(_torso_pts(top, -190, sw, ww, ww, 0)[:], accent, INK, OUTLINE)
        # pallu: across the chest from the right hip to the left shoulder, hanging behind
        pallu = [(ww + belly * 0.6, waist + 10), (ww * 0.1, waist + 14), (-sw + 4, top + 6), (-sw * 0.35, top - 4)]
        S.poly(pallu, main, INK, OUTLINE)
        S.line([pallu[0], pallu[3]], 8, accent)
        S.poly([(-sw + 6, top + 4), (-sw - 22, top + 30), (-sw - 30, -40), (-sw - 4, -54)], main, INK, OUTLINE)
        return

    hem = {"tshirt": 18, "shirt": 18, "uniform": 18, "vest": 10, "blazer": 30,
           "kurta": 130, "salwar": 120}.get(outfit, 18)
    hw = ww + (16 if outfit in ("kurta", "salwar") else 4)

    if outfit == "salwar":           # dupatta tails hang behind the shoulders
        for sgn in (-1, 1):
            S.tube([(sgn * (sw - 6), top + 10), (sgn * (sw + 14), -40)], 26, accent)

    body = _torso_pts(top, hem, sw if outfit != "vest" else sw - 10, ww, hw, belly)
    S.poly(body, main, INK, OUTLINE)

    if outfit == "vest":
        S.poly(ellipse_pts(0, top, 26, 40, 14, 0, 180), skin, INK, 4)
    elif outfit in ("tshirt",):
        S.line(ellipse_pts(0, top, 24, 18, 12, 10, 170), 5)
    elif outfit in ("shirt", "uniform"):
        S.line([(0, top + 14), (0, hem - 4)], 4, shade(main, 0.75))
        for y in range(int(top + 50), int(hem - 10), 60):
            S.dot((7, y), 4, shade(main, 0.6))
        for sgn in (-1, 1):
            S.poly([(0, top + 18), (sgn * 30, top - 4), (sgn * 34, top + 26)], shade(main, 1.04), INK, 4)
        if outfit == "uniform":
            S.poly([(-9, top + 18), (9, top + 18), (13, top + 130), (0, top + 150), (-13, top + 130)], accent, INK, 4)
            S.line([(-8, top + 70), (10, top + 56)], 4, WHITE)
        else:
            S.poly([(-sw + 22, top + 64), (-sw + 52, top + 64), (-sw + 52, top + 100), (-sw + 22, top + 100)],
                   None, shade(main, 0.7), 4)
    elif outfit == "blazer":
        S.poly([(0, top + 2), (-26, top + 2), (0, top + 118), (26, top + 2)], WHITE, INK, 4)
        S.poly([(-7, top + 14), (7, top + 14), (10, top + 104), (0, top + 120), (-10, top + 104)], accent, INK, 3)
        for sgn in (-1, 1):
            S.line([(sgn * 26, top + 2), (sgn * 40, top + 60), (sgn * 6, top + 128)], 5)
        S.dot((0, top + 160), 5, INK)
        S.dot((0, top + 206), 5, INK)
    elif outfit in ("kurta", "salwar"):
        S.poly([(-16, top - 6), (16, top - 6), (16, top + 10), (-16, top + 10)], shade(main, 0.88), INK, 4)
        if outfit == "kurta":
            S.line([(0, top + 10), (0, top + 104)], 4, shade(main, 0.7))
            for y in (top + 34, top + 62, top + 90):
                S.dot((6, y), 4, shade(main, 0.6))
        for sgn in (-1, 1):       # side slits
            S.line([(sgn * hw * 0.98, hem - 4), (sgn * hw * 0.9, hem - 70)], 4, shade(main, 0.7))
        if outfit == "salwar":    # dupatta draped across the chest
            S.tube(bezier((-sw + 4, top + 16), (0, top + 120), (sw - 4, top + 16), 14), 22, accent)


def _sleeve(S, outfit, sh, elb, hand, col):
    if outfit in ("vest",):
        return
    if outfit in ("tshirt", "uniform", "saree"):      # short sleeve, a little flared at the opening
        S.limb([sh, mix(sh, elb, 0.55)], [ARM_W + 14, ARM_W + 16], col)
    elif outfit == "salwar":
        S.limb([sh, elb, mix(elb, hand, 0.5)], [ARM_W + 12, ARM_W + 9, ARM_W + 9], col)
    else:   # shirt, kurta, blazer: full sleeves
        S.limb([sh, elb, mix(elb, hand, 0.82)], [ARM_W + 10, ARM_W + 7, ARM_W + 6], col)


def _hand(S, wrist, fore_angle, side, skin, finger=False):
    """Mitten hand: palm along the forearm, thumb towards the body (when the arm hangs)."""
    d = vec(fore_angle, 1.0)
    n = (-d[1], d[0])
    s = -1 if side == "L" else 1
    c = (wrist[0] + d[0] * 11, wrist[1] + d[1] * 11)
    thumb = (c[0] + s * n[0] * 13 - d[0] * 3, c[1] + s * n[1] * 13 - d[1] * 3)
    if finger:
        S.limb([(c[0] + d[0] * 8, c[1] + d[1] * 8), (c[0] + d[0] * 42, c[1] + d[1] * 42)], [11, 8], skin, 3)
    S.poly(closed_ellipse(c[0], c[1], 13, 17, 24, -fore_angle), skin, INK, 4.5)
    S.poly(closed_ellipse(thumb[0], thumb[1], 6.5, 11, 16, -fore_angle + s * 40), skin, INK, 4)


def _back_hair(S, HH, style, hc):
    if style in ("long", "braid"):
        pts = [(-HEAD_RX - 12, 40 if style == "braid" else 150)] + \
            ellipse_pts(0, -6, HEAD_RX + 10, HEAD_RY + 8, 30, 180, 360) + \
            [(HEAD_RX + 12, 40 if style == "braid" else 150)]
        if style == "long":
            pts += bezier((HEAD_RX + 12, 150), (0, 186), (-HEAD_RX - 12, 150), 10)[1:-1]
        S.poly([HH(q) for q in pts], hc, INK, OUTLINE)
    elif style == "bun":
        S.dot(HH((0, -HEAD_RY - 12)), 36, hc, INK, OUTLINE)
    elif style == "ponytail":
        S.poly([HH(q) for q in bezier((40, -HEAD_RY + 6), (150, -60), (104, 70), 12)
                + bezier((84, 60), (110, -40), (30, -HEAD_RY + 26), 10)], hc, INK, OUTLINE)


def _front_hair(S, HH, style, hc):
    def cap(fringe, side_y=-2):
        pts = ellipse_pts(0, 0, HEAD_RX + 5, HEAD_RY + 6, 30, 182, 358)
        pts = [(pts[0][0], side_y)] + pts + [(pts[-1][0], side_y)] + fringe
        S.poly([HH(q) for q in pts], hc, INK, OUTLINE)

    if style in ("short", "spiky", "curly"):
        if style == "spiky":
            spikes = []
            for i in range(11):
                a = math.radians(196 + 148 * i / 10)
                r = (HEAD_RX + 30, HEAD_RY + 34) if i % 2 else (HEAD_RX + 4, HEAD_RY + 4)
                spikes.append((r[0] * math.cos(a), r[1] * math.sin(a)))
            S.poly([HH(q) for q in spikes + [(HEAD_RX * 0.6, -40), (-HEAD_RX * 0.6, -40)]], hc, INK, OUTLINE)
        if style == "curly":
            for i in range(9):
                a = math.radians(190 + 160 * i / 8)
                S.dot(HH(((HEAD_RX + 4) * math.cos(a), (HEAD_RY + 4) * math.sin(a))), 22, hc, INK, 5)
        cap([(80, -24), (58, -50), (28, -60), (4, -52), (-24, -62), (-58, -50), (-80, -24)])
    elif style == "side_part":
        cap([(80, -22), (60, -54), (24, -66), (-12, -52), (-26, -64), (-60, -50), (-80, -22)])
        S.line([HH((-26, -64)), HH((-30, -HEAD_RY - 4))], 4, shade(hc, 1.6))
    elif style in ("long", "braid", "bun", "ponytail"):
        down = 26 if style in ("long", "braid") else -6
        cap([(HEAD_RX + 2, down), (70, -26), (44, -58), (6, -72), (0, -60), (-6, -72), (-44, -58),
             (-70, -26), (-HEAD_RX - 2, down)], side_y=down)
    elif style == "balding":
        for sgn in (-1, 1):
            side = ellipse_pts(sgn * (HEAD_RX - 6), -14, 13, 26, 10, 90, 270) if sgn < 0 else \
                ellipse_pts(sgn * (HEAD_RX - 6), -14, 13, 26, 10, -90, 90)
            S.poly([HH(q) for q in side], hc, INK, 4)
        S.line([HH((-30, -HEAD_RY + 18)), HH((-14, -HEAD_RY + 10))], 5, WHITE)


def _braid(S, HH, hc, accent):
    for i in range(8):
        S.poly(closed_ellipse(*HH((66 + (i % 2) * 6 - i * 1.5, 50 + i * 30)), 16, 20, 18), hc, INK, 4)
    S.dot(HH((60, 50 + 8 * 30)), 10, accent, INK, 4)


# ---------------------------------------------------------------- the character
def build_character(spec, pose, expr, mouth_open, t, x0, ground_y, k=1.0,
                    blink=False, prop=None, talking=False, tear_phase=0.0):
    """Return (ops, anchors) in global logical coordinates."""
    o = resolve_spec(spec)
    p = dict(DEFAULT_POSE)
    p.update({kk: vv for kk, vv in pose.items() if vv is not None or kk == "finger"})
    sk = skeleton(p)
    S = Sketch(x0, ground_y, k, p["tilt"], p["shift"], p["lift"], sk["fy"])

    outfit = o.get("outfit", "tshirt")
    build = o.get("build", "normal")
    skin = color_of(o.get("skin", "wheatish"), "wheatish", SKIN_TONES)
    cols = dict(
        skin=skin,
        main=color_of(o.get("color", "blue")),
        accent=color_of(o.get("accent", "red"), "red"),
        pants=color_of(o.get("pants", "white" if outfit in ("kurta", "salwar") else "denim")),
    )
    hair = o.get("hair", "short")
    hcol = color_of(o.get("hair_color", "black"), "black", HAIR_COLORS)
    acc = o.get("accessories", [])
    cap_col = color_of(o.get("cap_color", "red"), "red")
    facing = {"left": -1, "right": 1}.get(o.get("facing", "front"), 0)

    hc = sk["hc"]
    ht = d2r(p["head_tilt"])

    shape = o.get("face", "oval")
    fx, fy = FACE_SHAPES.get(shape, (1.0, 1.0))
    eye_style, nose, brow_w = o.get("eyes", "dot"), o.get("nose", "hook"), BROW_STYLES.get(o.get("brows"), 9)

    def HH(q):                      # head coordinates (the face shape stretches the head and the hair with it)
        return add(hc, rot((q[0] * HEAD_SCALE * fx, q[1] * HEAD_SCALE * fy), ht))

    def HF(q):                      # face coordinates (designed for a 100px head)
        f = FACE * HEAD_SCALE
        return add(hc, rot((q[0] * f, q[1] * f), ht))

    def hline(pts, w, col=INK):
        S.line([HF(q) for q in pts], w * FACE * HEAD_SCALE, col)

    def hpoly(pts, fill=None, outline=None, w=OUTLINE):
        S.poly([HF(q) for q in pts], fill, outline, w * FACE * HEAD_SCALE)

    covered = "turban" in acc or "cap" in acc
    if not ("turban" in acc):
        _back_hair(S, HH, hair, hcol)

    # ---- legs + feet ----
    if outfit != "saree":
        for hip, knee, foot in ((sk["hipL"], sk["kneeL"], sk["footL"]), (sk["hipR"], sk["kneeR"], sk["footR"])):
            w = LEG_W + (10 if outfit == "salwar" else 0)
            S.limb([hip, knee, add(foot, (0, -10))], [w + 4, w, w - 5], cols["pants"])
    _draw_feet(S, sk, o.get("shoes", "black"), skin)

    # ---- neck + torso ----
    S.tube([(0, -TORSO_H + 20), HH((0, HEAD_RY * 0.55))], 30, skin)
    _draw_outfit(S, o, sk, cols, build)
    if hair == "braid" and not covered:
        _braid(S, HH, hcol, cols["accent"])

    # ---- arms (normally behind the head; a pose can bring them in front, e.g. the naagin hood) ----
    def draw_arms():
        for side, sh, elb, hand, a2 in (("L", sk["shL"], sk["elbL"], sk["handL"], p["la2"]),
                                        ("R", sk["shR"], sk["elbR"], sk["handR"], p["ra2"])):
            S.limb([sh, elb, hand], [ARM_W, ARM_W - 3, ARM_W - 7], skin)
            _sleeve(S, outfit, sh, elb, hand, cols["main"])
            _hand(S, hand, a2, side, skin, finger=p.get("finger") == side)
        if prop:
            side = o.get("prop_hand", "R")
            wrist, fore = (sk["handL"], p["la2"]) if side == "L" else (sk["handR"], p["ra2"])
            _draw_prop(S, prop, add(wrist, vec(fore, 11)), fore, cols["main"])     # held in the palm

    if not p.get("arms_front"):
        draw_arms()

    # ---- head ----
    for sgn in (-1, 1):
        S.poly([HH(q) for q in closed_ellipse(sgn * (HEAD_RX - 2), 10, 14, 21, 20)], skin, INK, 5)
    S.poly([HH(q) for q in _head_pts(shape)], skin, INK, OUTLINE + 1)
    if "earrings" in acc:
        for sgn in (-1, 1):
            S.dot(HH((sgn * (HEAD_RX - 2), 36)), 7, GOLD, INK, 3)
            S.poly([HH(q) for q in [(sgn * (HEAD_RX - 2) - 8, 44), (sgn * (HEAD_RX - 2) + 8, 44),
                                    (sgn * (HEAD_RX - 2), 62)]], GOLD, INK, 3)

    eyes, mouth, brows = EXPRESSIONS.get(expr, EXPRESSIONS["neutral"])
    if blink and eyes not in NO_BLINK:
        eyes = "closed"
    fdx = facing * 14 + p["look_x"] * 5
    lx, ly = p["look_x"] * 7, p["look_y"] * 5

    for sgn in (-1, 1):
        cx, cy = _eye_center(sgn, fdx)
        if eyes == "dot" and eye_style == "big":
            hpoly(closed_ellipse(cx, cy - 1, 18, 20, 24), WHITE, INK, 5)
            hpoly(closed_ellipse(cx + lx * 1.2, cy + 1 + ly * 1.2, 10, 11, 18), INK, None)
            hpoly(closed_ellipse(cx + lx * 1.2 - 3, cy - 3 + ly * 1.2, 3.5, 3.5, 10), WHITE, None)
        elif eyes == "dot" and eye_style == "small":
            hpoly(closed_ellipse(cx + lx, cy + ly, 7.5, 8.5, 16), INK, None)
        elif eyes == "dot":
            hpoly(closed_ellipse(cx + lx, cy + ly, 11, 13, 20), INK, None)
            hpoly(closed_ellipse(cx + lx - 3, cy + ly - 5, 3.5, 3.5, 10), WHITE, None)
        elif eyes == "wide":
            hpoly(closed_ellipse(cx, cy - 2, 21, 23, 28), WHITE, INK, 5)
            hpoly(closed_ellipse(cx + lx * 1.4, cy - 2 + ly * 1.4, 9, 9, 18), INK, None)
        elif eyes == "half":
            hpoly(closed_ellipse(cx, cy, 21, 18, 28), WHITE, INK, 5)
            hpoly(closed_ellipse(cx + lx * 1.4 - 2, cy + 4 + ly, 9, 9, 18), INK, None)
            lid = ellipse_pts(cx, cy, 22, 19, 16, 180, 360) + [(cx + 22, cy - 3), (cx - 22, cy - 3)]
            lid = [(a, b if b < cy - 3 else cy - 3) for a, b in lid]
            hpoly(lid, skin, None)
            hline([(cx - 23, cy - 3), (cx + 23, cy - 3)], 6)
            hline(ellipse_pts(cx, cy, 21, 18, 14, 180, 360), 5)
        elif eyes == "happy":
            hline(ellipse_pts(cx, cy + 8, 20, 17, 16, 200, 340), 7)
        elif eyes == "relaxed":
            hline(ellipse_pts(cx, cy - 4, 20, 13, 16, 15, 165), 6)
            hline([(cx - 21, cy - 12), (cx + 21, cy - 14)], 5)
        elif eyes == "closed":
            hline(ellipse_pts(cx, cy - 2, 17, 8, 10, 15, 165), 6)
        elif eyes == "x":
            hline([(cx - 15, cy - 15), (cx + 15, cy + 15)], 7)
            hline([(cx - 15, cy + 15), (cx + 15, cy - 15)], 7)
        elif eyes == "heart":
            hpoly(heart_pts(cx, cy, 30), (214, 50, 70), INK, 4)
        elif eyes == "wink":
            if sgn < 0:
                hline(ellipse_pts(cx, cy + 8, 20, 17, 16, 200, 340), 7)
            else:
                hpoly(closed_ellipse(cx + lx, cy + ly, 11, 13, 20), INK, None)

    # brows (always drawn: thick desi eyebrows)
    for sgn in (-1, 1):
        ey = -4.0
        bc = hcol if hcol != HAIR_COLORS["white"] else (150, 150, 150)
        if brows == "angry":
            hline([(sgn * 16 + fdx, ey - 22), (sgn * 56 + fdx, ey - 42)], brow_w + 1, bc)
        elif brows == "sad":
            hline([(sgn * 16 + fdx, ey - 42), (sgn * 56 + fdx, ey - 24)], brow_w + 1, bc)
        elif brows == "up":
            hline(ellipse_pts(sgn * 36 + fdx, ey - 40, 24, 10, 10, 200, 340), brow_w, bc)
        elif brows == "think":
            if sgn > 0:
                hline([(18 + fdx, ey - 42), (56 + fdx, ey - 54)], brow_w + 1, bc)
            else:
                hline([(-56 + fdx, ey - 32), (-18 + fdx, ey - 32)], brow_w + 1, bc)
        else:
            hline(ellipse_pts(sgn * 36 + fdx, ey - 24, 22, 8, 10, 205, 335), brow_w, bc)

    # nose
    ncol = shade(skin, 0.62)
    if nose == "button":
        hline(ellipse_pts(fdx, 20, 9, 8, 10, 20, 160), 5, ncol)
    elif nose == "long":
        hline(bezier((fdx + 2, -6), (fdx - 16, 34), (fdx + 8, 36), 10), 5, ncol)
    elif nose == "big":
        hpoly(closed_ellipse(fdx, 22, 15, 12, 18), shade(skin, 0.9), ncol, 5)
    else:
        hline(bezier((fdx + 4, 0), (fdx - 12, 26), (fdx + 6, 30), 8), 5, ncol)

    # tears
    if expr == "cry":
        for sgn in (-1, 1):
            cx, cy = _eye_center(sgn, fdx)
            for j in range(2):
                ph = (tear_phase + j * 0.5) % 1.0
                ty = cy + 14 + ph * 70
                hpoly(closed_ellipse(cx + sgn * 6, ty, 7, 11, 14), TEAR, INK, 3)

    # mouth
    my = 50.0
    if talking:
        if mouth_open > 0.1:
            mouth = "talk"
        elif mouth in ("open", "shout", "laugh", "grin", "o", "open_small"):
            mouth = "smile"

    def open_mouth(cx, cy, rx, ry, teeth=True):
        pts = closed_ellipse(cx, cy, rx, ry, 32)
        hpoly(pts, MOUTH_IN, INK, 6)
        if ry > 16:
            hpoly(closed_ellipse(cx, cy + ry * 0.45, rx * 0.55, ry * 0.32, 18), TONGUE, None)
        if teeth and ry > 12:
            th = []
            for a in range(0, 181, 12):
                aa = math.radians(180 + 27 + (a / 180.0) * 126)
                th.append((cx + rx * 0.93 * math.cos(aa), cy + ry * 0.93 * math.sin(aa)))
            hpoly(th, WHITE, None)
        hline(pts + [pts[0]], 6)

    if mouth == "smile":
        hline(ellipse_pts(fdx, 24, 30, 26, 16, 28, 152), 7)
    elif mouth == "smirk":
        hline(bezier((fdx - 26, 54), (fdx + 6, 68), (fdx + 34, 40)), 7)
        hline([(fdx + 30, 44), (fdx + 38, 34)], 6)
    elif mouth == "grin":
        pts = [(fdx - 36, 42), (fdx + 36, 42)] + ellipse_pts(fdx, 42, 36, 30, 18, 0, 180)[::-1]
        hpoly(pts, WHITE, INK, 6)
        hline([(fdx - 36, 56), (fdx + 36, 56)], 4)
    elif mouth == "laugh":
        open_mouth(fdx, my + 12, 38, 32)
    elif mouth == "open":
        open_mouth(fdx, my + 12, 28, 28)
    elif mouth == "open_small":
        open_mouth(fdx, my + 8, 18, 12, teeth=False)
    elif mouth == "shout":
        open_mouth(fdx, my + 14, 42, 34)
    elif mouth == "talk":
        a = max(0.0, min(1.0, mouth_open))
        open_mouth(fdx, my + 6 + 8 * a, 18 + 14 * a, 6 + 28 * a)
    elif mouth == "frown":
        hline(ellipse_pts(fdx, 84, 28, 22, 16, 208, 332), 7)
    elif mouth == "o":
        hpoly(closed_ellipse(fdx, my + 12, 13, 15, 20), MOUTH_IN, INK, 6)
    else:  # flat
        hline([(fdx - 22, my + 10), (fdx + 22, my + 10)], 7)

    # front hair + headwear
    if not covered:
        _front_hair(S, HH, hair, hcol)

    for a in acc:
        if a == "glasses":
            for sgn in (-1, 1):
                cx, cy = _eye_center(sgn, fdx)
                ring = closed_ellipse(cx, cy, 30, 27, 28)
                hline(ring + [ring[0]], 5)
            hline([(-5 + fdx, -6), (5 + fdx, -6)], 5)
            hline([(-62 + fdx, -8), (-96, -14)], 5)
            hline([(62 + fdx, -8), (96, -14)], 5)
        elif a == "sunglasses":
            for sgn in (-1, 1):
                cx, cy = _eye_center(sgn, fdx)
                hpoly(closed_ellipse(cx, cy, 34, 24, 28), (22, 22, 28), INK, 5)
                hline([(cx - 18, cy - 10), (cx - 6, cy - 14)], 4, (150, 150, 170))     # glint
            hline([(-5 + fdx, -6), (5 + fdx, -6)], 5)
            hline([(-62 + fdx, -8), (-96, -14)], 5)
            hline([(62 + fdx, -8), (96, -14)], 5)
        elif a == "cap":
            crown = ellipse_pts(0, 0, HEAD_RX + 5, HEAD_RY + 6, 24, 192, 348)
            S.poly([HH(q) for q in crown + [(crown[-1][0], -40), (crown[0][0], -40)]], cap_col, INK, 6)
            S.poly([HH(q) for q in closed_ellipse(facing * 22, -38, 78, 12, 24)], shade(cap_col, 0.78), INK, 5)
        elif a == "turban":
            tc = color_of(o.get("turban_color", o.get("cap_color", "saffron")), "saffron")
            crown = ellipse_pts(0, -8, HEAD_RX + 12, HEAD_RY + 22, 24, 186, 354)
            S.poly([HH(q) for q in crown + [(HEAD_RX + 6, -24), (0, -44), (-HEAD_RX - 6, -24)]], tc, INK, 6)
            for j in range(3):
                S.line([HH(q) for q in bezier((-HEAD_RX + 6, -44 - j * 22), (0, -80 - j * 24),
                                              (HEAD_RX - 6, -44 - j * 22), 10)], 4, shade(tc, 0.75))
        elif a == "moustache":
            hpoly(closed_ellipse(-20 + fdx, 38, 28, 10, 18, 14), hcol, None)
            hpoly(closed_ellipse(20 + fdx, 38, 28, 10, 18, -14), hcol, None)
        elif a == "beard":
            pts = ellipse_pts(0, 10, 82, 84, 24, 24, 156)
            hpoly(pts + pts[:1], hcol, None)
        elif a == "bindi":
            hpoly(closed_ellipse(fdx, -38, 7, 7, 14), (200, 30, 50), None)
        elif a == "tilak":
            hpoly([(fdx - 5, -60), (fdx + 5, -60), (fdx + 3, -20), (fdx - 3, -20)], (220, 70, 40), None)

    if p.get("arms_front"):
        draw_arms()

    top_extra = {"spiky": 34, "curly": 26, "bun": 48, "ponytail": 8}.get(hair, 8)
    if "turban" in acc:
        top_extra = 26
    anchors = dict(
        head_top=S.T(HH((0, -HEAD_RY - top_extra))),
        head_center=S.T(HH((0, 0))),
        mouth=S.T(HF((fdx, 56))),
        feet=S.T((0, sk["fy"])),
        hand_l=S.T(sk["handL"]),
        hand_r=S.T(sk["handR"]),
    )
    return S.ops, anchors


def render_ops(ops, s, frame_w, frame_h, SS=2):
    """Rasterise ops at output scale s. Returns (RGBA layer, (ox, oy)) or None."""
    if not ops:
        return None
    xs, ys, m = [], [], 0.0
    for op in ops:
        for x, y in op["pts"]:
            xs.append(x)
            ys.append(y)
        m = max(m, op["w"])
    mg = m * s + 3
    ox = int(math.floor(min(xs) * s - mg))
    oy = int(math.floor(min(ys) * s - mg))
    ex = int(math.ceil(max(xs) * s + mg))
    ey = int(math.ceil(max(ys) * s + mg))
    ox, oy = max(ox, 0), max(oy, 0)
    ex, ey = min(ex, frame_w), min(ey, frame_h)
    w, h = ex - ox, ey - oy
    if w <= 2 or h <= 2:
        return None
    layer = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    def tp(pts):
        return [((x * s - ox) * SS, (y * s - oy) * SS) for x, y in pts]

    for op in ops:
        pts = tp(op["pts"])
        if op["t"] == "poly":
            if len(pts) >= 3:
                if op["fill"] is not None:
                    d.polygon(pts, fill=op["fill"])
                if op["outline"] is not None:
                    wd = max(1, int(round(op["w"] * s * SS)))
                    d.line(pts + pts[:2], fill=op["outline"], width=wd, joint="curve")
        else:
            wd = max(1, int(round(op["w"] * s * SS)))
            d.line(pts, fill=op["color"], width=wd, joint="curve")
            r = wd / 2.0
            for (x, y) in (pts[0], pts[-1]):
                d.ellipse([x - r, y - r, x + r, y + r], fill=op["color"])
    return layer.reduce(SS), (ox, oy)

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
    "ghost": (214, 228, 238),          # the bhoot's pale blue-white (never given to anyone by chance)
}

HAIR_COLORS = {
    "black": (36, 30, 32),
    "brown": (94, 62, 42),
    "grey": (170, 170, 174),
    "white": (232, 232, 230),
    "henna": (150, 62, 34),
}

HAIR_STYLES = ("short", "side_part", "spiky", "curly", "balding", "bald", "long", "braid", "bun", "ponytail")
OUTFITS = ("tshirt", "shirt", "kurta", "salwar", "saree", "uniform", "blazer", "vest", "kurta_jacket", "stripes")
BUILDS = {"slim": (0.9, 0.0), "normal": (1.0, 6.0), "chubby": (1.2, 44.0)}
# height: (whole-body scale, extra leg length). A tall person is mostly longer legs, the head stays readable.
HEIGHTS = {"tall": (1.05, 1.13), "normal": (1.0, 1.0), "short": (0.96, 0.9)}
# Face variety: every character on screen gets its own face (assign_faces), or the script picks one.
FACE_SHAPES = {"oval": (1.0, 1.0), "round": (1.08, 0.94), "long": (0.9, 1.08), "square": (1.04, 0.98)}
EYE_STYLES = ("dot", "big", "small")
NOSE_STYLES = ("hook", "button", "long", "big")
BROW_STYLES = {"normal": 9, "thick": 13, "thin": 6}
FACE_WORDS = dict(
    [(f + "_face", ("face", f)) for f in FACE_SHAPES] + [(e + "_eyes", ("eyes", e)) for e in EYE_STYLES if e != "dot"]
    + [(n + "_nose", ("nose", n)) for n in NOSE_STYLES] + [(b + "_brows", ("brows", b)) for b in BROW_STYLES])
ACCESSORIES = ("glasses", "sunglasses", "cap", "turban", "moustache", "beard", "bindi", "tilak", "earrings", "tuft",
               "topi", "beanie", "nurse_cap")

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
    # more people for the stories (made from the same parts)
    "pandit": dict(skin="brown", hair="bald", outfit="kurta", color="saffron", pants="white", shoes="chappal",
                   build="chubby", accessories=["tilak"]),
    "police": dict(skin="brown", hair="short", outfit="shirt", color="khaki", pants="khaki", shoes="black",
                   cap_color="khaki", accessories=["cap", "moustache"]),
    "doctor": dict(skin="fair", hair="side_part", outfit="blazer", color="white", pants="navy", accent="sky",
                   shoes="black", accessories=["glasses"]),
    "chaiwala": dict(skin="dark", hair="curly", outfit="vest", color="white", pants="khaki", shoes="chappal",
                     build="slim", accessories=["moustache"]),
    "madam": dict(skin="fair", hair="bun", outfit="saree", color="teal", accent="gold", shoes="chappal",
                  accessories=["glasses", "bindi", "earrings"]),
    "dulha": dict(skin="wheatish", hair="short", outfit="kurta", color="cream", pants="cream", accent="gold",
                  shoes="brown", turban_color="red", accessories=["turban"]),
    "dulhan": dict(skin="fair", hair="bun", outfit="saree", color="red", accent="gold", shoes="chappal",
                   accessories=["bindi", "earrings"]),
    "gym_bro": dict(skin="brown", hair="spiky", outfit="vest", color="black", pants="grey", shoes="white",
                    accessories=["sunglasses"]),
    # politician: white kurta-pyjama, a sleeveless (Nehru) jacket and a white Gandhi topi
    "neta": dict(skin="brown", hair="balding", outfit="kurta_jacket", color="white", pants="white", accent="grey",
                 shoes="chappal", build="chubby", cap_color="white", accessories=["topi", "moustache", "glasses"]),
    "chor": dict(skin="wheatish", hair="short", outfit="stripes", color="black", pants="black", shoes="black",
                 build="slim", cap_color="black", accessories=["beanie"]),
    "nurse": dict(skin="wheatish", hair="bun", outfit="shirt", color="white", pants="white", shoes="white",
                  accessories=["nurse_cap", "earrings"]),
    "saas": dict(skin="wheatish", hair="bun", outfit="saree", color="purple", accent="gold", shoes="chappal",
                 build="chubby", accessories=["glasses", "bindi", "earrings"]),
    "bahu": dict(skin="fair", hair="braid", outfit="saree", color="magenta", accent="gold", shoes="chappal",
                 accessories=["bindi", "earrings"]),
    "principal": dict(skin="brown", hair="balding", hair_color="grey", outfit="blazer", color="brown", pants="grey",
                      accent="maroon", shoes="black", accessories=["glasses", "moustache"]),
    "sabziwala": dict(skin="dark", hair="short", outfit="kurta", color="mustard", pants="white", shoes="chappal",
                      build="slim", accessories=["moustache"]),
    "nai": dict(skin="brown", hair="side_part", outfit="shirt", color="sky", pants="khaki", shoes="chappal",
                accessories=["moustache"]),
    # everyday people of the city, the road and the journey
    "delivery_boy": dict(skin="brown", hair="short", outfit="tshirt", color="red", pants="denim", shoes="white",
                         cap_color="red", prop="box", accessories=["cap"]),
    "driver": dict(skin="dark", hair="short", outfit="shirt", color="khaki", pants="khaki", shoes="chappal",
                   accessories=["moustache"]),
    "conductor": dict(skin="brown", hair="side_part", outfit="shirt", color="khaki", pants="khaki", shoes="black",
                      prop="bag", accessories=["moustache"]),
    "watchman": dict(skin="brown", hair="short", outfit="uniform", color="navy", pants="navy", accent="sky",
                     shoes="black", cap_color="navy", prop="stick", accessories=["cap", "moustache"]),
    "landlord": dict(skin="wheatish", hair="balding", hair_color="grey", outfit="kurta", color="white", pants="white",
                     shoes="chappal", build="chubby", accessories=["moustache", "glasses"]),
    "influencer": dict(skin="fair", hair="spiky", outfit="tshirt", color="teal", pants="black", shoes="white",
                       prop="phone", accessories=["sunglasses", "beard"]),
    "doodhwala": dict(skin="brown", hair="short", outfit="kurta", color="white", pants="white", shoes="chappal",
                      build="slim", prop="milk_can", accessories=["moustache"]),
    "tt": dict(skin="wheatish", hair="balding", outfit="blazer", color="black", pants="black", accent="white",
               shoes="black", prop="notebook", accessories=["glasses", "moustache"]),
    "bhoot": dict(skin="ghost", hair="long", hair_color="white", outfit="kurta", color="white", pants="white",
                  shoes="chappal", build="slim", expression="evil"),
    "pilot": dict(skin="fair", hair="side_part", outfit="blazer", color="navy", pants="navy", accent="gold",
                  shoes="black", cap_color="navy", accessories=["cap", "sunglasses"]),
    "air_hostess": dict(skin="fair", hair="bun", outfit="blazer", color="red", pants="red", accent="white",
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
    "relaxed": ("relaxed", "flat", None),
    "yawn": ("closed", "yawn", None),
    "scared": ("wide", "wavy", "sad"),
    "nervous": ("dot", "wavy", "sad"),
    "cringe": ("closed", "grin", "sad"),
    "confused": ("dot", "flat", "think"),
    "disgust": ("half", "frown", "angry"),
    "proud": ("relaxed", "smile", None),
    "dizzy": ("spiral", "wavy", None),
    "sneeze": ("closed", "open", "up"),
    "eating": ("happy", "flat", None),
    "shy": ("dot", "smile", "sad"),
    "lol": ("happy", "laugh", None),
    "evil": ("half", "grin", "angry"),
    "bored": ("half", "flat", None),
    "determined": ("dot", "flat", "angry"),
    "hurt": ("closed", "wavy", "sad"),
    "shh": ("dot", "o", None),
    "excited": ("wide", "laugh", "up"),
    "blush": ("happy", "smile", None),
    "kiss": ("closed", "o", None),
}
BLUSH = {"shy", "blush", "love", "kiss"}
TEARS = {"cry", "lol"}
# Eyes that should not be replaced by a "blink"
NO_BLINK = {"happy", "relaxed", "closed", "x", "heart", "wink", "spiral"}

PROPS = ("spoon", "phone", "mic", "cup", "ball", "stick", "bag", "chai", "glass", "plate", "samosa", "chappal",
         "money", "newspaper", "book", "notebook", "pen", "laptop", "umbrella", "remote", "broom", "belan", "pillow",
         "gift", "balloon", "trophy", "torch", "key", "bat", "flag", "camera", "banana", "bottle", "letter",
         "toothbrush", "dumbbell", "box", "cooker", "thali", "lota", "tiffin", "mithai", "report_card", "injection",
         "stethoscope", "milk_can")


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
    if out.get("height") in HEIGHTS:                # tall / short: a bigger / smaller body, longer / shorter legs
        sc, lk = HEIGHTS[out["height"]]
        out["scale"] = float(out.get("scale", 1.0)) * sc
        out["leg_k"] = lk
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

    def __init__(self, x0, ground_y, k, tilt_deg, shift, lift, fy, dx=0.0):
        self.x0, self.gy, self.k = x0, ground_y, k
        self.tilt = math.radians(tilt_deg)
        self.shift, self.lift, self.fy, self.dx = shift, lift, fy, dx
        self.ops = []

    def T(self, p):
        x = p[0] + self.shift
        y = p[1] - self.fy
        x, y = rot((x, y), self.tilt)
        return (self.x0 + (x + self.dx) * self.k, self.gy + (y + self.lift) * self.k)

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
    th, sh = TH * p.get("th_k", 1.0), SH * p.get("sh_k", 1.0)     # < 1: foreshortened (sitting, front view)
    kneeL = add(hipL, vec(p["ll1"], th))
    footL = add(kneeL, vec(p["ll2"], sh))
    kneeR = add(hipR, vec(p["rl1"], th))
    footR = add(kneeR, vec(p["rl2"], sh))
    shL, shR = (-56.0, -TORSO_H + 22), (56.0, -TORSO_H + 22)
    ak = p.get("arm_k", 1.0)          # riders get longer arms so their hands reach the handlebar
    elbL = add(shL, vec(p["la1"], UA * ak * p.get("la_k1", 1.0)))     # *_k < 1: foreshortened segment (IK)
    handL = add(elbL, vec(p["la2"], LA * ak * p.get("la_k2", 1.0)))
    elbR = add(shR, vec(p["ra1"], UA * ak * p.get("ra_k1", 1.0)))
    handR = add(elbR, vec(p["ra2"], LA * ak * p.get("ra_k2", 1.0)))
    neck = (0.0, -TORSO_H + 4)
    hc = add(neck, rot((0.0, -(NECK_H + HEAD_RY * 0.8 * HEAD_SCALE)), d2r(p["head_tilt"])))
    hc = (hc[0] + p.get("head_dx", 0.0), hc[1] + p.get("head_dy", 0.0))
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
    else:
        _draw_prop2(S, prop, hand, d, n, pt)


def _draw_prop2(S, prop, hand, d, n, pt):
    """More props. pt(a, b) = along the forearm / across it; ab(x, y) = screen-upright offset from the hand."""
    def ab(x, y):
        return (hand[0] + x, hand[1] + y)

    def rect(x0, y0, x1, y1, fill, w=5):
        S.poly([ab(x0, y0), ab(x1, y0), ab(x1, y1), ab(x0, y1)], fill, INK, w)

    def prect(a0, b0, a1, b1, fill, w=5):
        S.poly([pt(a0, b0), pt(a1, b0), pt(a1, b1), pt(a0, b1)], fill, INK, w)

    if prop in ("chai", "glass"):
        S.poly([ab(-17, -44), ab(17, -44), ab(13, 8), ab(-13, 8)], (236, 240, 240), INK, 4)
        S.poly([ab(-14, -28), ab(14, -28), ab(11, 5), ab(-11, 5)], (178, 112, 62), None)
    elif prop == "plate":
        S.poly(ellipse_pts(hand[0] + 4, hand[1] - 12, 34, 26, 14, 180, 360), (226, 150, 60), INK, 4)
        S.poly(closed_ellipse(hand[0], hand[1] - 8, 64, 13, 32), (250, 250, 248), INK, 5)
    elif prop == "samosa":
        S.poly([ab(-28, 12), ab(28, 12), ab(0, -36)], (222, 168, 78), INK, 5)
    elif prop == "chappal":
        ang = math.degrees(math.atan2(d[1], d[0]))
        c = pt(44, 0)
        S.poly(closed_ellipse(c[0], c[1], 52, 20, 24, ang), (60, 110, 190), INK, 5)
        S.line([pt(30, -16), pt(46, 0), pt(30, 16)], 6, (236, 236, 236))
    elif prop == "money":
        for i, (da, db) in enumerate(((0, -14), (8, 0), (16, 14))):
            prect(da - 6, db - 20, da + 74, db + 20, (150, 204, 140), 4)
        S.dot(pt(44, 14), 9, (110, 160, 100))
    elif prop == "newspaper":
        rect(-74, -120, 74, 40, (238, 236, 228))
        rect(-60, -104, 60, -74, (60, 60, 60), 3)
        for y in range(-60, 30, 16):
            S.line([ab(-60, y), ab(-6, y)], 4, (150, 150, 150))
            S.line([ab(8, y), ab(60, y)], 4, (150, 150, 150))
    elif prop == "book":
        S.poly([ab(0, -6), ab(-66, -18), ab(-66, -96), ab(0, -84)], (250, 248, 240), INK, 5)
        S.poly([ab(0, -6), ab(66, -18), ab(66, -96), ab(0, -84)], (250, 248, 240), INK, 5)
        for y in (-74, -60, -46, -32):
            S.line([ab(-54, y - 4), ab(-12, y + 4)], 3, (160, 160, 160))
            S.line([ab(12, y + 4), ab(54, y - 4)], 3, (160, 160, 160))
        S.poly([ab(-70, -14), ab(0, -2), ab(70, -14), ab(70, -6), ab(0, 6), ab(-70, -6)], (70, 110, 170), INK, 4)
    elif prop == "notebook":
        rect(-40, -100, 40, 6, (232, 210, 120))
        for y in range(-90, 0, 18):
            S.dot(ab(-40, y), 5, INK)
    elif prop == "pen":
        S.line([pt(-8, 0), pt(56, 0)], 8, (50, 80, 170))
        S.line([pt(56, 0), pt(66, 0)], 4, INK)
    elif prop == "laptop":
        S.poly([ab(-70, 0), ab(70, 0), ab(78, 14), ab(-78, 14)], (150, 152, 160), INK, 5)
        S.poly([ab(-62, 0), ab(62, 0), ab(70, -92), ab(-54, -92)], (70, 74, 84), INK, 5)
        S.poly([ab(-52, -8), ab(56, -8), ab(62, -82), ab(-46, -82)], (130, 190, 235), None)
    elif prop == "umbrella":
        S.line([ab(0, 30), ab(0, -230)], 8, (60, 60, 66))
        S.line(ellipse_pts(hand[0] - 14, hand[1] + 30, 14, 14, 10, 0, 180), 7)
        top = ellipse_pts(hand[0], hand[1] - 230, 160, 92, 28, 180, 360)
        scal = []
        for i in reversed(range(4)):          # right -> left so the outline closes without crossing
            x0 = -160 + i * 80
            scal += ellipse_pts(hand[0] + x0 + 40, hand[1] - 230, 40, 18, 8, 0, 180)
        S.poly(top + scal, (54, 70, 150), INK, 6)
    elif prop == "remote":
        prect(-10, -12, 60, 12, (40, 40, 46), 4)
        for a in (12, 28, 44):
            S.dot(pt(a, 0), 4, (220, 80, 70))
    elif prop == "broom":
        S.line([pt(-30, 0), pt(300, 0)], 10, (150, 104, 70))
        S.poly([pt(296, -18), pt(296, 18), pt(392, 44), pt(392, -44)], (222, 192, 112), INK, 5)
        for b in (-24, 0, 24):
            S.line([pt(320, b * 0.5), pt(386, b * 1.4)], 3, (170, 140, 70))
    elif prop == "belan":
        S.line([pt(-36, 0), pt(-4, 0)], 10, (150, 104, 70))
        S.line([pt(4, 0), pt(120, 0)], 26, (214, 172, 112))
        S.line([pt(128, 0), pt(160, 0)], 10, (150, 104, 70))
    elif prop == "pillow":
        S.poly(closed_ellipse(hand[0], hand[1] - 20, 80, 46, 30), (246, 246, 250), INK, 5)
        S.line([ab(-40, -28), ab(40, -12)], 3, (200, 200, 210))
    elif prop == "gift":
        rect(-48, -86, 48, 6, (214, 64, 70))
        S.poly([ab(-8, -86), ab(8, -86), ab(8, 6), ab(-8, 6)], (250, 210, 70), None)
        S.poly(closed_ellipse(hand[0] - 18, hand[1] - 98, 18, 11, 14), (250, 210, 70), INK, 4)
        S.poly(closed_ellipse(hand[0] + 18, hand[1] - 98, 18, 11, 14), (250, 210, 70), INK, 4)
    elif prop == "balloon":
        S.line([ab(0, 0), ab(-6, -90), ab(8, -180)], 3, (90, 90, 90))
        S.poly(closed_ellipse(hand[0] + 8, hand[1] - 246, 48, 60, 32), (226, 70, 80), INK, 5)
        S.poly([ab(0, -184), ab(16, -184), ab(8, -192)], (226, 70, 80), INK, 3)
    elif prop == "trophy":
        gold = (236, 190, 60)
        S.line(ellipse_pts(hand[0] - 40, hand[1] - 92, 18, 22, 12, 90, 270), 6, gold)
        S.line(ellipse_pts(hand[0] + 40, hand[1] - 92, 18, 22, 12, -90, 90), 6, gold)
        S.poly([ab(-42, -126), ab(42, -126), ab(22, -56), ab(-22, -56)], gold, INK, 5)
        rect(-8, -56, 8, -24, gold, 4)
        rect(-34, -24, 34, 0, (120, 84, 50), 4)
    elif prop == "torch":
        S.poly([pt(64, 0), pt(420, -110), pt(420, 110)], (255, 244, 180, 110), None)
        prect(-12, -13, 50, 13, (60, 62, 70), 4)
        prect(50, -20, 70, 20, (230, 230, 220), 4)
    elif prop == "key":
        S.dot(pt(0, 0), 16, None, (220, 180, 60), 6)
        S.line([pt(14, 0), pt(64, 0)], 7, (220, 180, 60))
        S.line([pt(52, 0), pt(52, 12)], 6, (220, 180, 60))
    elif prop == "bat":
        S.line([pt(-24, 0), pt(64, 0)], 11, (60, 50, 44))
        S.poly([pt(62, -17), pt(62, 17), pt(250, 22), pt(256, 0), pt(250, -22)], (232, 204, 146), INK, 5)
    elif prop == "flag":
        S.line([ab(0, 40), ab(0, -230)], 7, (110, 90, 70))
        S.poly([ab(0, -228), ab(130, -196), ab(0, -150)], (236, 110, 60), INK, 4)
    elif prop == "camera":
        rect(-46, -64, 46, 4, (54, 56, 64))
        rect(-30, -78, -4, -64, (54, 56, 64), 4)
        S.dot(ab(4, -30), 22, (40, 40, 44), (190, 190, 200), 5)
        S.dot(ab(4, -30), 9, (110, 160, 210))
    elif prop == "banana":
        S.line(bezier(pt(-6, -8), pt(36, 26), pt(84, -6)), 16, (240, 210, 70))
        S.line(bezier(pt(-6, -8), pt(36, 26), pt(84, -6)), 3)
    elif prop == "bottle":
        rect(-18, -92, 18, 10, (150, 210, 230))
        rect(-9, -116, 9, -92, (150, 210, 230), 4)
        rect(-11, -128, 11, -116, (60, 120, 200), 4)
    elif prop == "letter":
        rect(-54, -40, 54, 30, (250, 248, 240))
        S.line([ab(-54, -40), ab(0, -2), ab(54, -40)], 4)
    elif prop == "toothbrush":
        S.line([pt(-10, 0), pt(74, 0)], 8, (80, 140, 220))
        prect(56, -16, 76, -4, (250, 250, 250), 3)
    elif prop == "dumbbell":
        S.line([pt(-40, 0), pt(40, 0)], 10, (130, 130, 136))
        for a in (-40, 40):
            S.line([pt(a, -28), pt(a, 28)], 24, (50, 50, 56))
    elif prop == "box":
        rect(-74, -116, 74, 18, (196, 150, 100))
        S.line([ab(-74, -80), ab(74, -80)], 4, (150, 110, 70))
        S.line([ab(-20, -116), ab(-20, -80)], 8, (230, 210, 160))
    elif prop == "cooker":                    # pressure cooker held by its long handle
        steel = (196, 198, 206)
        S.line([pt(-6, 0), pt(64, 0)], 14, (40, 40, 44))
        S.poly([ab(40, -90), ab(132, -90), ab(128, 6), ab(44, 6)], steel, INK, 5)
        S.poly(closed_ellipse(hand[0] + 86, hand[1] - 90, 48, 12, 24), (150, 152, 160), INK, 5)
        S.line([ab(86, -102), ab(86, -126)], 10, (40, 40, 44))        # the whistle
        S.dot(ab(86, -130), 9, (40, 40, 44))
    elif prop == "thali":                     # steel plate with katoris, roti and rice
        S.poly(closed_ellipse(hand[0], hand[1] - 10, 78, 20, 32), (210, 212, 220), INK, 5)
        for cx, col in ((-36, (230, 170, 60)), (0, (200, 80, 50)), (36, (120, 170, 80))):
            S.poly(closed_ellipse(hand[0] + cx, hand[1] - 18, 16, 7, 14), col, INK, 3)
        S.poly(closed_ellipse(hand[0] + 20, hand[1] - 4, 22, 6, 14), (226, 190, 120), INK, 3)
    elif prop == "lota":                      # brass water pot
        brass = (214, 162, 60)
        S.poly(closed_ellipse(hand[0], hand[1] - 34, 34, 30, 24), brass, INK, 5)
        S.poly([ab(-16, -64), ab(16, -64), ab(22, -80), ab(-22, -80)], brass, INK, 4)
    elif prop == "milk_can":                  # the doodhwala's steel can, carried by its handle
        steel = (196, 198, 206)
        S.line([ab(-22, 0), ab(-22, -18), ab(22, -18), ab(22, 0)], 6, (90, 92, 100))
        S.poly([ab(-30, 0), ab(30, 0), ab(44, 40), ab(44, 130), ab(-44, 130), ab(-44, 40)], steel, INK, 4)
        S.poly([ab(-44, 70), ab(44, 70), ab(44, 80), ab(-44, 80)], (160, 162, 170), None, 0)
    elif prop == "tiffin":                    # three steel boxes on a clip, carried by the handle
        steel = (200, 202, 210)
        S.line([ab(-26, -2), ab(-26, 16), ab(26, 16), ab(26, -2)], 6, (90, 92, 100))
        for i in range(3):
            S.poly([ab(-38, 16 + i * 36), ab(38, 16 + i * 36), ab(38, 48 + i * 36), ab(-38, 48 + i * 36)], steel, INK, 4)
    elif prop == "mithai":                    # box of sweets, lid open
        S.poly([ab(-64, -40), ab(64, -40), ab(54, -96), ab(-54, -96)], (250, 160, 70), INK, 4)    # the lid, open
        rect(-64, -40, 64, 10, (236, 120, 60))
        for cx in (-38, -12, 14, 40):
            S.dot(ab(cx, -42), 13, (250, 214, 90), INK, 3)
    elif prop == "report_card":               # the result: a sheet with marks, a big red circle
        rect(-50, -132, 50, 6, (252, 252, 246))
        for y in range(-112, -20, 16):
            S.line([ab(-38, y), ab(14, y)], 3, (150, 150, 160))
        S.poly(closed_ellipse(hand[0] + 28, hand[1] - 58, 18, 14, 18), None, (210, 40, 50), 5)
        S.line([ab(-38, -10), ab(38, -10)], 5, (210, 40, 50))
    elif prop == "injection":                 # a big comic syringe
        S.poly([pt(-4, -10), pt(70, -10), pt(70, 10), pt(-4, 10)], (230, 240, 248), INK, 4)
        S.poly([pt(10, -8), pt(54, -8), pt(54, 8), pt(10, 8)], (150, 200, 240), None)
        S.line([pt(70, 0), pt(108, 0)], 4, (120, 120, 128))
        S.line([pt(-4, 0), pt(-30, 0)], 6, (120, 120, 128))
        S.line([pt(-30, -14), pt(-30, 14)], 6, INK)
    elif prop == "stethoscope":               # held up: the chest piece on its tube
        S.line([ab(0, -6), ab(-24, -60), ab(0, -96), ab(24, -60), ab(0, -6)], 6, (60, 60, 66))
        S.line([ab(0, -6), ab(22, 40)], 6, (60, 60, 66))
        S.dot(ab(26, 46), 14, (196, 198, 206), INK, 4)


def _eye_center(sgn, face_dx, ey=-4.0, ex=34.0):
    return (sgn * ex + face_dx, ey)


# ---------------------------------------------------------------- body parts
def _half_width(top, hem, sw, ww, hw, belly, y):
    """Half width of _torso_pts' silhouette at height y (for stripes across the shirt)."""
    pts = _torso_pts(top, hem, sw, ww, hw, belly)
    left = pts[:len(pts) // 2]
    for (x0, y0), (x1, y1) in zip(left, left[1:]):
        if min(y0, y1) <= y <= max(y0, y1) and y1 != y0:
            return -(x0 + (x1 - x0) * (y - y0) / (y1 - y0))
    return sw


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


def _skew(pts, y0, y1, drag):
    """Cloth below y0 trails sideways by up to `drag` at y1 (a kurta hem / saree swinging behind a walk)."""
    if not drag:
        return pts
    return [(x + drag * max(0.0, min(1.0, (y - y0) / max(1.0, y1 - y0))), y) for x, y in pts]


def _draw_outfit(S, o, sk, cols, build, back=False, drag=0.0, lap=False):
    """lap: sitting, seen from the front (the thighs point at the camera): a long kurta / saree lies on the lap
    and the knees show, otherwise the person looks as if standing."""
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
        if lap:                                     # sitting: the saree spreads over the knees
            xl, xr = min(xl, sk["kneeL"][0] - 40), max(xr, sk["kneeR"][0] + 40)
        skirt = [(-ww - belly * 0.6, waist)] + bezier((-ww - belly, waist + 60), (xl + 4, hem_y - 120), (xl, hem_y), 8) \
            + [(xr, hem_y)] + bezier((xr, hem_y), (xr - 4, hem_y - 120), (ww + belly, waist + 60), 8) \
            + [(ww + belly * 0.6, waist)]
        skirt = _skew(skirt, waist + 60, hem_y, drag)
        S.poly(skirt, main, INK, OUTLINE)
        S.line([(xl + 6 + drag, hem_y - 12), (xr - 6 + drag, hem_y - 12)], 12, accent)
        if lap:                                     # the lap: a fold over the knees
            ky = max(sk["kneeL"][1], sk["kneeR"][1])
            S.line(bezier((sk["kneeL"][0] - 34, ky - 4), (0, ky + 18), (sk["kneeR"][0] + 34, ky - 4), 10), 5,
                   shade(main, 0.7))
        # pleats
        for dx in (-14, 0, 14):
            S.line([(dx, waist + 40), (dx * 1.6, hem_y - 24)], 3, shade(main, 0.78))
        # midriff + blouse
        S.poly(_torso_pts(top, waist + 8, sw, ww, ww + belly * 0.5, belly * 0.6), skin, INK, OUTLINE)
        S.poly(_torso_pts(top, -190, sw, ww, ww, 0)[:], accent, INK, OUTLINE)
        if back:                    # seen from behind: the pallu falls down the back from the left shoulder
            S.poly([(-sw * 0.35, top - 4), (-sw + 4, top + 6), (-ww * 0.6, waist + 40), (ww * 0.4, waist + 30)],
                   main, INK, OUTLINE)
            return
        # pallu: across the chest from the right hip to the left shoulder, hanging behind
        pallu = [(ww + belly * 0.6, waist + 10), (ww * 0.1, waist + 14), (-sw + 4, top + 6), (-sw * 0.35, top - 4)]
        S.poly(pallu, main, INK, OUTLINE)
        S.line([pallu[0], pallu[3]], 8, accent)
        S.poly([(-sw + 6, top + 4), (-sw - 22, top + 30), (-sw - 30, -40), (-sw - 4, -54)], main, INK, OUTLINE)
        return

    hem = {"tshirt": 18, "shirt": 18, "uniform": 18, "vest": 10, "blazer": 30, "stripes": 18,
           "kurta": 130, "kurta_jacket": 130, "salwar": 120}.get(outfit, 18)
    hw = ww + (16 if outfit in ("kurta", "salwar", "kurta_jacket") else 4)
    long_top = outfit in ("kurta", "salwar", "kurta_jacket")
    if lap and long_top:                            # sitting: the kurta ends on the knees, wide over the lap
        hem = max(sk["kneeL"][1], sk["kneeR"][1]) + 16
        hw = max(hw, max(abs(sk["kneeL"][0]), abs(sk["kneeR"][0])) + 30)

    if outfit == "salwar":           # dupatta tails hang behind the shoulders
        for sgn in (-1, 1):
            S.tube([(sgn * (sw - 6), top + 10), (sgn * (sw + 14), -40)], 26, accent)

    body = _torso_pts(top, hem, sw if outfit != "vest" else sw - 10, ww, hw, belly)
    if long_top:
        body = _skew(body, 0.0, hem, drag)
    S.poly(body, main, INK, OUTLINE)
    if lap and long_top and not back:               # knees under the cloth
        for kx in (sk["kneeL"][0], sk["kneeR"][0]):
            S.poly(ellipse_pts(kx, hem - 10, 30, 14, 12, 0, 180), shade(main, 0.9), INK, 4)
    if outfit == "stripes":         # prisoner's stripes: white bands across the shirt
        for y in range(int(top + 34), int(hem - 8), 44):
            half = _half_width(top, hem, sw, ww, hw, belly, y) - 5
            S.line([(-half, y), (half, y)], 18, WHITE)
        S.poly(body, None, INK, OUTLINE)
    if outfit == "kurta_jacket":    # sleeveless (Nehru) jacket over the kurta, open in a V at the neck
        jh = -36
        jacket = _torso_pts(top - 2, jh, sw - 2, ww + 4, ww + 10 + belly * 0.4, belly)
        S.poly(jacket, accent, INK, OUTLINE)
        if not back:
            S.poly([(-14, top + 6), (14, top + 6), (0, top + 74)], main, INK, 4)      # the kurta in the V
            S.poly([(-15, top - 4), (15, top - 4), (13, top + 8), (-13, top + 8)], shade(accent, 0.85), INK, 4)
            for y in (top + 96, top + 140, top + 184):
                S.dot((5, y), 5, shade(accent, 0.6))
            S.line([(-ww * 0.55, top + 120), (-ww * 0.15, top + 120)], 4, shade(accent, 0.7))     # pocket
    if back:                        # the back of the clothes: a plain seam, no buttons / pockets / tie
        S.line([(0, top + 30), (0, min(hem - 10, top + 200))], 3, shade(main, 0.85))
        return

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
    elif outfit == "kurta_jacket":
        pass                        # (the jacket covers the kurta's front)
    elif outfit == "stripes":
        S.line(ellipse_pts(0, top, 24, 18, 12, 10, 170), 5)
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
    if outfit in ("tshirt", "uniform", "saree", "stripes"):      # short sleeve, a little flared at the opening
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


def _back_of_head(S, HH, style, hc, acc, o, cols):
    """The head seen from behind: hair over all of it (down to the nape), long hair / braid / bun / ponytail hanging
    on the back, a cap or turban from behind. No face."""
    covered = "turban" in acc or "cap" in acc or "beanie" in acc
    if style in ("long", "braid") and not covered:
        tail = 150 if style == "long" else 60
        S.poly([HH(q) for q in [(-HEAD_RX - 12, tail)] + ellipse_pts(0, -6, HEAD_RX + 10, HEAD_RY + 8, 30, 180, 360)
                + [(HEAD_RX + 12, tail)] + bezier((HEAD_RX + 12, tail), (0, tail + 36), (-HEAD_RX - 12, tail), 10)[1:-1]],
               hc, INK, OUTLINE)
        if style == "braid":
            for i in range(7):
                S.poly(closed_ellipse(*HH((0, 70 + i * 30)), 17, 20, 18), hc, INK, 4)
            S.dot(HH((0, 70 + 7 * 30)), 10, cols["accent"], INK, 4)
    elif style not in ("bald",) and not covered:
        nape = 30 if style == "balding" else 46
        pts = ellipse_pts(0, 0, HEAD_RX + 4, HEAD_RY + 5, 36, 165, 375)
        pts = pts + bezier(pts[-1], (0, nape + 22), pts[0], 10)[1:-1]
        if style == "balding":                      # a fringe around the back, the crown bare
            S.poly([HH(q) for q in ellipse_pts(0, 0, HEAD_RX + 4, HEAD_RY + 5, 24, 150, 390)
                    + bezier((HEAD_RX * 0.9, -6), (0, -20), (-HEAD_RX * 0.9, -6), 8)], hc, INK, 4)
        else:
            S.poly([HH(q) for q in pts], hc, INK, OUTLINE)
            if style == "curly":
                for i in range(9):
                    a = math.radians(170 + 200 * i / 8)
                    S.dot(HH(((HEAD_RX + 2) * math.cos(a), (HEAD_RY + 2) * math.sin(a))), 22, hc, INK, 5)
            elif style == "spiky":
                for i in range(9):
                    a = math.radians(200 + 140 * i / 8)
                    tip = ((HEAD_RX + 28) * math.cos(a), (HEAD_RY + 30) * math.sin(a))
                    S.poly([HH(q) for q in [(HEAD_RX * 0.8 * math.cos(a - 0.2), HEAD_RY * 0.8 * math.sin(a - 0.2)),
                                            tip, (HEAD_RX * 0.8 * math.cos(a + 0.2), HEAD_RY * 0.8 * math.sin(a + 0.2))]],
                           hc, INK, 4)
            elif style == "bun":
                S.dot(HH((0, -HEAD_RY * 0.55)), 38, hc, INK, OUTLINE)
            elif style == "ponytail":
                S.poly([HH(q) for q in bezier((-16, -10), (-30, 90), (0, 150), 10) + bezier((10, 150), (34, 80), (16, -10), 10)],
                       hc, INK, OUTLINE)
                S.dot(HH((0, -6)), 10, cols["accent"], INK, 4)
    if "cap" in acc:
        cap_col = color_of(o.get("cap_color", "red"), "red")
        crown = ellipse_pts(0, 0, HEAD_RX + 5, HEAD_RY + 6, 24, 192, 348)
        S.poly([HH(q) for q in crown + [(crown[-1][0], -30), (crown[0][0], -30)]], cap_col, INK, 6)
        S.poly([HH(q) for q in [(-26, -30), (26, -30), (20, -8), (-20, -8)]], shade(cap_col, 0.78), INK, 4)
    elif "turban" in acc:
        tc = color_of(o.get("turban_color", o.get("cap_color", "saffron")), "saffron")
        crown = ellipse_pts(0, -8, HEAD_RX + 12, HEAD_RY + 22, 24, 186, 354)
        S.poly([HH(q) for q in crown + [(HEAD_RX + 6, 20), (0, 30), (-HEAD_RX - 6, 20)]], tc, INK, 6)
        for j in range(3):
            S.line([HH(q) for q in bezier((-HEAD_RX + 6, -30 - j * 24), (0, -60 - j * 26),
                                          (HEAD_RX - 6, -30 - j * 24), 10)], 4, shade(tc, 0.75))
    for a in ("topi", "beanie", "nurse_cap"):
        if a in acc:
            _head_cap(S, HH, a, o)
    if "earrings" in acc:
        for sgn in (-1, 1):
            S.dot(HH((sgn * (HEAD_RX - 2), 36)), 7, GOLD, INK, 3)


def _head_cap(S, HH, kind, o):
    """Caps that sit on top of the hair: the white Gandhi topi (a boat shape), a knitted beanie (the prisoner's,
    striped like his shirt), a nurse's cap with a red cross."""
    if kind == "topi":
        col = color_of(o.get("cap_color", "white"), "white")
        pts = [(-HEAD_RX - 4, -34), (-HEAD_RX + 6, -HEAD_RY - 8), (-30, -HEAD_RY - 26), (0, -HEAD_RY - 30),
               (30, -HEAD_RY - 26), (HEAD_RX - 6, -HEAD_RY - 8), (HEAD_RX + 4, -34)]
        S.poly([HH(q) for q in pts + [(HEAD_RX - 4, -22), (-HEAD_RX + 4, -22)]], col, INK, 5)
        S.line([HH(q) for q in [(-HEAD_RX + 4, -38), (HEAD_RX - 4, -38)]], 5, shade(col, 0.85))
        S.line([HH(q) for q in [(-4, -HEAD_RY - 26), (-8, -44)]], 4, shade(col, 0.8))       # the fold
    elif kind == "beanie":
        col = color_of(o.get("cap_color", "black"), "black")
        dome = ellipse_pts(0, -6, HEAD_RX + 6, HEAD_RY + 8, 24, 186, 354)
        S.poly([HH(q) for q in dome + [(HEAD_RX + 6, -30), (-HEAD_RX - 6, -30)]], col, INK, 6)
        S.line([HH(q) for q in [(-HEAD_RX * 0.86, -HEAD_RY * 0.62), (HEAD_RX * 0.86, -HEAD_RY * 0.62)]], 14, WHITE)
        S.poly([HH(q) for q in [(-HEAD_RX - 8, -46), (HEAD_RX + 8, -46), (HEAD_RX + 8, -26), (-HEAD_RX - 8, -26)]],
               shade(col, 1.4) if sum(col) < 200 else shade(col, 0.8), INK, 5)
    elif kind == "nurse_cap":
        pts = [(-46, -HEAD_RY + 2), (-38, -HEAD_RY - 30), (38, -HEAD_RY - 30), (46, -HEAD_RY + 2)]
        S.poly([HH(q) for q in pts], WHITE, INK, 5)
        S.line([HH(q) for q in [(0, -HEAD_RY - 24), (0, -HEAD_RY - 4)]], 7, (210, 40, 50))
        S.line([HH(q) for q in [(-10, -HEAD_RY - 14), (10, -HEAD_RY - 14)]], 7, (210, 40, 50))


def _braid(S, HH, hc, accent, drag=0.0):
    for i in range(8):                              # (drag: the braid swings behind a walk)
        S.poly(closed_ellipse(*HH((66 + (i % 2) * 6 - i * 1.5 + drag * i / 8.0, 50 + i * 30)), 16, 20, 18), hc, INK, 4)
    S.dot(HH((60 + drag, 50 + 8 * 30)), 10, accent, INK, 4)


# ---------------------------------------------------------------- the character
def build_character(spec, pose, expr, mouth_open, t, x0, ground_y, k=1.0,
                    blink=False, prop=None, talking=False, tear_phase=0.0):
    """Return (ops, anchors) in global logical coordinates."""
    o = resolve_spec(spec)
    p = dict(DEFAULT_POSE)
    p.update({kk: vv for kk, vv in pose.items() if vv is not None or kk == "finger"})
    lk = float(o.get("leg_k", 1.0))
    if lk != 1.0:                                   # tall / short legs
        p["th_k"], p["sh_k"] = p.get("th_k", 1.0) * lk, p.get("sh_k", 1.0) * lk
    sk = skeleton(p)
    S = Sketch(x0, ground_y, k, p["tilt"], p["shift"], p["lift"], sk["fy"], p.get("dx", 0.0))
    if not pose.get("arms_front"):          # a hand in front of the face: draw the arms over the head
        hcx, hcy = sk["hc"]
        p["arms_front"] = any(math.hypot(sk[h][0] - hcx, sk[h][1] - hcy) < HEAD_RX * HEAD_SCALE + 14
                              for h in ("handL", "handR"))

    outfit = o.get("outfit", "tshirt")
    build = o.get("build", "normal")
    skin = color_of(o.get("skin", "wheatish"), "wheatish", SKIN_TONES)
    cols = dict(
        skin=skin,
        main=color_of(o.get("color", "blue")),
        accent=color_of(o.get("accent", "red"), "red"),
        pants=color_of(o.get("pants", "white" if outfit in ("kurta", "salwar", "kurta_jacket") else "denim")),
    )
    hair = o.get("hair", "short")
    hcol = color_of(o.get("hair_color", "black"), "black", HAIR_COLORS)
    acc = o.get("accessories", [])
    cap_col = color_of(o.get("cap_color", "red"), "red")
    facing = {"left": -1, "right": 1}.get(o.get("facing", "front"), 0)
    if p.get("head_facing") is not None:            # glance over the shoulder / spin
        facing = int(max(-1, min(1, round(p["head_facing"]))))
    face_f = p.get("_facing_f") if p.get("head_facing") is None else None   # smoothed turn (renderer)

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

    covered = "turban" in acc or "cap" in acc or "beanie" in acc
    back = o.get("view") == "back" or bool(p.get("hide_face"))   # seen from behind (ots shot, turn_around...)
    if not ("turban" in acc) and not back:
        _back_hair(S, HH, hair, hcol)

    # ---- legs + feet ----
    if outfit != "saree":
        for hip, knee, foot in ((sk["hipL"], sk["kneeL"], sk["footL"]), (sk["hipR"], sk["kneeR"], sk["footR"])):
            w = LEG_W + (10 if outfit == "salwar" else 0)
            S.limb([hip, knee, add(foot, (0, -10))], [w + 4, w, w - 5], cols["pants"])
            if outfit == "stripes":     # striped pyjama: white bands across each leg
                for a, b in ((hip, knee), (knee, add(foot, (0, -10)))):
                    ln = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
                    ux, uy = (b[0] - a[0]) / ln, (b[1] - a[1]) / ln
                    for u in range(22, int(ln) - 10, 44):
                        cx, cy = a[0] + ux * u, a[1] + uy * u
                        hw_ = w * 0.5 - 1               # (limb widths are full widths)
                        S.line([(cx - uy * hw_, cy + ux * hw_), (cx + uy * hw_, cy - ux * hw_)], 14, WHITE)
    _draw_feet(S, sk, o.get("shoes", "black"), skin)

    # ---- neck + torso ----
    S.tube([(0, -TORSO_H + 20), HH((0, HEAD_RY * 0.55))], 30, skin)
    _draw_outfit(S, o, sk, cols, build, back=back, drag=p.get("drag", 0.0), lap=p.get("th_k", 1.0) < 0.6)
    if hair == "braid" and not covered and not back:
        _braid(S, HH, hcol, cols["accent"], p.get("drag", 0.0))

    # ---- arms (normally behind the head; a pose can bring them in front, e.g. the naagin hood) ----
    def draw_arms():
        for side, sh, elb, hand, a2 in (("L", sk["shL"], sk["elbL"], sk["handL"], p["la2"]),
                                        ("R", sk["shR"], sk["elbR"], sk["handR"], p["ra2"])):
            S.limb([sh, elb, hand], [ARM_W, ARM_W - 3, ARM_W - 7], skin)
            _sleeve(S, outfit, sh, elb, hand, cols["main"])
            _hand(S, hand, a2, side, skin, finger=p.get("finger") == side)
            if p.get("thumb") == side:
                S.limb([hand, add(hand, (0.0, -34.0))], [12, 9], skin)
        held = [(nm, hs) for nm, hs in (p.get("props") or [])]
        if prop:
            held.append((prop, p.get("prop_hand") or o.get("prop_hand", "R")))
        for nm, side in held:
            wrist, fore = (sk["handL"], p["la2"]) if side == "L" else (sk["handR"], p["ra2"])
            _draw_prop(S, nm, add(wrist, vec(fore, 11)), fore, cols["main"])     # held in the palm

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

    if back:
        _back_of_head(S, HH, hair, hcol, acc, o, cols)
        if p.get("arms_front"):
            draw_arms()
        top_extra = 26 if "turban" in acc else {"spiky": 34, "curly": 26, "bun": 48}.get(hair, 8)
        anchors = dict(head_top=S.T(HH((0, -HEAD_RY - top_extra))), head_center=S.T(HH((0, 0))),
                       mouth=S.T(HH((0, 40))), feet=S.T((0, sk["fy"])), hand_l=S.T(sk["handL"]),
                       hand_r=S.T(sk["handR"]))
        return S.ops, anchors

    eyes, mouth, brows = EXPRESSIONS.get(expr, EXPRESSIONS["neutral"])
    if blink and eyes not in NO_BLINK:
        eyes = "closed"
    fdx = (face_f if face_f is not None else facing) * 14 + p["look_x"] * 5
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
        elif eyes == "spiral":
            hline([(cx + (2 + i * 0.9) * math.cos(i * 0.45 + t * 9 * sgn), cy + (2 + i * 0.9) * math.sin(i * 0.45 + t * 9 * sgn))
                   for i in range(22)], 4)
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

    if expr in BLUSH:
        for sgn in (-1, 1):
            cx, cy = _eye_center(sgn, fdx)
            hpoly(closed_ellipse(cx + sgn * 10, cy + 34, 20, 10, 18), (240, 150, 160), None)

    # tears
    if expr in TEARS:
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
    elif mouth == "yawn":
        open_mouth(fdx, my + 14, 24, 34, teeth=False)
    elif mouth == "wavy":
        hline([(fdx - 30 + i * 7.5, my + 10 + (5 if i % 2 else -5)) for i in range(9)], 6)
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
        elif a in ("topi", "beanie", "nurse_cap"):
            _head_cap(S, HH, a, o)
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
    if "topi" in acc or "nurse_cap" in acc:
        top_extra = max(top_extra, 32)
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

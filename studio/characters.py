"""Procedural desi-stickman: big round head, bean torso, thin black limbs.

Everything is first turned into a display list of polygons / polylines (so that
rotation, tilt and falling are exact geometry, not image rotation), then drawn
once at 2x supersampling and reduced.
"""
import math

from PIL import Image, ImageDraw

SKIN = (238, 231, 208)
INK = (16, 16, 16)
MOUTH_IN = (112, 30, 40)
TONGUE = (226, 110, 120)
WHITE = (252, 252, 250)
TEAR = (150, 200, 240)

PALETTE = {
    "pink": (222, 118, 140),
    "blue": (92, 142, 206),
    "green": (96, 168, 92),
    "yellow": (238, 196, 64),
    "orange": (232, 140, 60),
    "purple": (150, 104, 190),
    "red": (208, 70, 64),
    "teal": (64, 168, 160),
    "white": (240, 240, 236),
    "black": (56, 56, 64),
    "brown": (150, 104, 70),
    "grey": (150, 150, 156),
}

HEAD_R = 100.0
TORSO_W = 150.0
TORSO_H = 330.0
UA = 125.0
LA = 125.0
TH = 165.0
SH = 165.0
OUTLINE = 8.0
ARM_W = 11.0
LEG_W = 12.0

DEFAULT_POSE = dict(
    la1=-14, la2=-8, ra1=14, ra2=8,
    ll1=-9, ll2=-3, rl1=9, rl2=3,
    tilt=0.0, lift=0.0, shift=0.0,
    head_tilt=0.0, look_x=0.0, look_y=0.0,
    finger=None,      # "L" / "R": draw a pointing finger on that hand
)

# name -> (eyes, mouth, brows)
EXPRESSIONS = {
    "neutral": ("dot", "flat", None),
    "smile": ("dot", "smile", None),
    "smug": ("relaxed", "smile", None),
    "sly": ("half", "smirk", None),
    "shock": ("wide", "open", "up"),
    "shout": ("wide", "shout", None),
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


def d2r(a):
    return math.radians(a)


def vec(angle_deg, length):
    """Angle 0 = straight down on screen, +90 = screen-right, 180 = up."""
    a = math.radians(angle_deg)
    return (length * math.sin(a), length * math.cos(a))


def add(p, q):
    return (p[0] + q[0], p[1] + q[1])


def rot(p, a):
    c, s = math.cos(a), math.sin(a)
    return (p[0] * c - p[1] * s, p[0] * s + p[1] * c)


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

    def dot(self, c, r, fill=INK, outline=None, w=OUTLINE):
        n = 56 if r > 40 else (32 if r > 12 else 20)
        self.poly(closed_ellipse(c[0], c[1], r, r, n), fill, outline, w)


def skeleton(p):
    hipL, hipR = (-36.0, 0.0), (36.0, 0.0)
    th, sh = TH * p.get("th_k", 1.0), SH * p.get("sh_k", 1.0)     # <1 = foreshortened (e.g. sitting, front view)
    kneeL = add(hipL, vec(p["ll1"], th))
    footL = add(kneeL, vec(p["ll2"], sh))
    kneeR = add(hipR, vec(p["rl1"], th))
    footR = add(kneeR, vec(p["rl2"], sh))
    shL, shR = (-52.0, -TORSO_H + 55), (52.0, -TORSO_H + 55)
    ak = p.get("arm_k", 1.0)                 # >1 = cartoon stretch (overhead gestures)
    elbL = add(shL, vec(p["la1"], UA * ak))
    handL = add(elbL, vec(p["la2"], LA * ak))
    elbR = add(shR, vec(p["ra1"], UA * ak))
    handR = add(elbR, vec(p["ra2"], LA * ak))
    neck = (0.0, -TORSO_H + 6)
    hc = add(neck, rot((0.0, -HEAD_R * 0.9), d2r(p["head_tilt"])))
    hc = (hc[0] + p.get("head_dx", 0.0), hc[1] + p.get("head_dy", 0.0))
    fy = max(footL[1], footR[1]) + 8
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
    elif prop == "bag":
        S.line([ab(-22, 0), ab(-34, 48)], 6)
        S.line([ab(22, 0), ab(34, 48)], 6)
        rect(-56, 46, 56, 140, (156, 92, 58))
        S.line([ab(-56, 70), ab(56, 70)], 5)
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


def _eye_center(sgn, face_dx, ey=-4.0, ex=34.0):
    return (sgn * ex + face_dx, ey)


def build_character(spec, pose, expr, mouth_open, t, x0, ground_y, k=1.0,
                    blink=False, prop=None, talking=False, tear_phase=0.0):
    """Return (ops, anchors) in global logical coordinates."""
    p = dict(DEFAULT_POSE)
    p.update({kk: vv for kk, vv in pose.items() if vv is not None or kk == "finger"})
    sk = skeleton(p)
    S = Sketch(x0, ground_y, k, p["tilt"], p["shift"], p["lift"], sk["fy"], p.get("dx", 0.0))
    c = spec.get("color", "blue")
    color = tuple(c) if isinstance(c, (list, tuple)) else PALETTE.get(c, PALETTE["blue"])
    cap_col = PALETTE.get(spec.get("cap_color", "red"), PALETTE["red"])
    facing = {"left": -1, "right": 1}.get(spec.get("facing", "front"), 0)
    if p.get("head_facing") is not None:
        facing = int(max(-1, min(1, round(p["head_facing"]))))
    back_view = bool(p.get("hide_face"))

    # ---- legs (+ shoes) ----
    for side, hip, knee, foot in (("L", sk["hipL"], sk["kneeL"], sk["footL"]),
                                  ("R", sk["hipR"], sk["kneeR"], sk["footR"])):
        S.line([hip, knee, foot], LEG_W)
        sgn = -1 if side == "L" else 1
        S.poly(closed_ellipse(foot[0] + sgn * 16, foot[1] - 6, 32, 15, 24), INK, None)

    # ---- torso (bean, slightly wider at the bottom) ----
    torso = []
    for i in range(48):
        a = 2 * math.pi * i / 48
        rx = (TORSO_W / 2) * (1 + 0.14 * math.sin(a))
        torso.append((rx * math.cos(a), (-TORSO_H / 2 + 4) + (TORSO_H / 2 + 14) * math.sin(a)))
    S.poly(torso, color, INK, OUTLINE)

    # ---- arms ----  (an arm whose hand is in front of the head is drawn after the head)
    hand_props = {"L": [], "R": []}
    for extra, hside in p.get("props") or []:
        hand_props["L" if hside == "L" else "R"].append(extra)
    if prop:
        hand_props["L" if spec.get("prop_hand", "R") == "L" else "R"].append(prop)
    arms = (("L", sk["shL"], sk["elbL"], sk["handL"], p["la1"], p["la2"]),
            ("R", sk["shR"], sk["elbR"], sk["handR"], p["ra1"], p["ra2"]))

    def draw_arm(side, sh, elb, hand, a1, a2):
        S.line([sh, elb, hand], ARM_W)
        S.dot(hand, 15, INK)
        if p.get("finger") == side:
            S.line([hand, add(hand, vec(a2, 44))], 9)
        if p.get("thumb") == side:
            S.line([hand, add(hand, (0.0, -38.0))], 10)
        for pr in hand_props[side]:
            _draw_prop(S, pr, hand, a2, color)

    hcx, hcy = sk["hc"]
    front = [a for a in arms if math.hypot(a[3][0] - hcx, a[3][1] - hcy) < HEAD_R + 18 and not p.get("hide_face")]
    for a in arms:
        if a not in front:
            draw_arm(*a)

    # ---- head ----
    hc = sk["hc"]
    ht = d2r(p["head_tilt"])

    def H(q):
        return add(hc, rot(q, ht))

    def hline(pts, w, col=INK):
        S.line([H(q) for q in pts], w, col)

    def hpoly(pts, fill=None, outline=None, w=OUTLINE):
        S.poly([H(q) for q in pts], fill, outline, w)

    S.poly([H(q) for q in closed_ellipse(0, 0, HEAD_R, HEAD_R, 64)], SKIN, INK, OUTLINE + 1)
    if back_view:
        expr, talking = "_back", False
    eyes, mouth, brows = EXPRESSIONS.get(expr, EXPRESSIONS["neutral"]) if expr != "_back" else (None, None, None)
    if blink and eyes and eyes not in NO_BLINK:
        eyes = "closed"
    fdx = facing * 14 + p["look_x"] * 5
    lx, ly = p["look_x"] * 7, p["look_y"] * 5

    for sgn in (-1, 1):
        cx, cy = _eye_center(sgn, fdx)
        if eyes == "dot":
            hpoly(closed_ellipse(cx + lx, cy + ly, 10, 10, 20), INK, None)
        elif eyes == "wide":
            hpoly(closed_ellipse(cx, cy - 2, 21, 23, 28), WHITE, INK, 5)
            hpoly(closed_ellipse(cx + lx * 1.4, cy - 2 + ly * 1.4, 8, 8, 18), INK, None)
        elif eyes == "half":
            hpoly(closed_ellipse(cx, cy, 21, 18, 28), WHITE, INK, 5)
            hpoly(closed_ellipse(cx + lx * 1.4 - 2, cy + 4 + ly, 8, 8, 18), INK, None)
            lid = ellipse_pts(cx, cy, 22, 19, 16, 180, 360) + [(cx + 22, cy - 3), (cx - 22, cy - 3)]
            lid = [(a, b if b < cy - 3 else cy - 3) for a, b in lid]
            hpoly(lid, SKIN, None)
            hline([(cx - 23, cy - 3), (cx + 23, cy - 3)], 6)
            hline(ellipse_pts(cx, cy, 21, 18, 14, 180, 360), 5)
        elif eyes == "happy":
            hline(ellipse_pts(cx, cy + 8, 20, 17, 16, 200, 340), 7)
        elif eyes == "relaxed":
            hline(ellipse_pts(cx, cy - 4, 20, 13, 16, 15, 165), 6)
            hline([(cx - 21, cy - 12), (cx + 21, cy - 14)], 5)
        elif eyes == "closed":
            hline([(cx - 18, cy), (cx + 18, cy + 2)], 7)
        elif eyes == "x":
            hline([(cx - 15, cy - 15), (cx + 15, cy + 15)], 7)
            hline([(cx - 15, cy + 15), (cx + 15, cy - 15)], 7)
        elif eyes == "heart":
            hpoly(heart_pts(cx, cy, 30), (214, 50, 70), INK, 4)
        elif eyes == "spiral":
            sp_ = [(cx + (2 + i * 0.9) * math.cos(i * 0.45 + t * 9 * sgn), cy + (2 + i * 0.9) * math.sin(i * 0.45 + t * 9 * sgn))
                   for i in range(22)]
            hline(sp_, 4)
        elif eyes == "wink":
            if sgn < 0:
                hline(ellipse_pts(cx, cy + 8, 20, 17, 16, 200, 340), 7)
            else:
                hpoly(closed_ellipse(cx + lx, cy + ly, 10, 10, 20), INK, None)

    # brows
    if brows:
        for sgn in (-1, 1):
            ey = -4.0
            if brows == "angry":
                hline([(sgn * 16 + fdx, ey - 18), (sgn * 58 + fdx, ey - 42)], 8)
            elif brows == "sad":
                hline([(sgn * 16 + fdx, ey - 42), (sgn * 58 + fdx, ey - 20)], 8)
            elif brows == "up":
                hline(ellipse_pts(sgn * 36 + fdx, ey - 34, 24, 10, 10, 200, 340), 7)
            elif brows == "think":
                if sgn > 0:
                    hline([(18 + fdx, ey - 40), (56 + fdx, ey - 52)], 8)
                else:
                    hline([(-56 + fdx, ey - 30), (-18 + fdx, ey - 30)], 8)

    # blush
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
    my = 46.0
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
        hline(ellipse_pts(fdx, 18, 34, 28, 16, 28, 152), 7)
    elif mouth == "smirk":
        hline(bezier((fdx - 28, 50), (fdx + 6, 66), (fdx + 38, 34)), 7)
        hline([(fdx + 34, 38), (fdx + 42, 28)], 6)
    elif mouth == "grin":
        pts = [(fdx - 40, 36), (fdx + 40, 36)] + ellipse_pts(fdx, 36, 40, 34, 18, 0, 180)[::-1]
        hpoly(pts, WHITE, INK, 6)
        hline([(fdx - 40, 52), (fdx + 40, 52)], 4)
    elif mouth == "laugh":
        open_mouth(fdx, my + 12, 40, 34)
    elif mouth == "open":
        open_mouth(fdx, my + 12, 30, 30)
    elif mouth == "open_small":
        open_mouth(fdx, my + 8, 18, 12, teeth=False)
    elif mouth == "shout":
        open_mouth(fdx, my + 14, 44, 36)
    elif mouth == "talk":
        a = max(0.0, min(1.0, mouth_open))
        open_mouth(fdx, my + 6 + 8 * a, 20 + 14 * a, 6 + 30 * a)
    elif mouth == "frown":
        hline(ellipse_pts(fdx, 82, 30, 24, 16, 208, 332), 7)
    elif mouth == "o":
        hpoly(closed_ellipse(fdx, my + 12, 13, 15, 20), MOUTH_IN, INK, 6)
    elif mouth == "yawn":
        open_mouth(fdx, my + 14, 24, 34, teeth=False)
    elif mouth == "wavy":
        hline([(fdx - 30 + i * 7.5, my + 10 + (5 if i % 2 else -5)) for i in range(9)], 6)
    elif mouth is None:
        pass
    else:  # flat
        hline([(fdx - 24, my + 8), (fdx + 24, my + 8)], 7)

    # accessories
    for acc in spec.get("accessories", []):
        if back_view and acc in ("glasses", "moustache", "beard", "bindi"):
            continue
        if acc == "glasses":
            for sgn in (-1, 1):
                cx, cy = _eye_center(sgn, fdx)
                hline(closed_ellipse(cx, cy, 31, 29, 28) + [closed_ellipse(cx, cy, 31, 29, 28)[0]], 5)
            hline([(-5 + fdx, -6), (5 + fdx, -6)], 5)
            hline([(-65 + fdx, -8), (-98, -14)], 5)
            hline([(65 + fdx, -8), (98, -14)], 5)
        elif acc == "cap":
            top = ellipse_pts(0, 0, HEAD_R + 3, HEAD_R + 3, 24, 196, 344)
            hpoly(top + [(top[-1][0], -42), (top[0][0], -42)], cap_col, INK, 6)
            hpoly(closed_ellipse(facing * 20, -40, 82, 13, 24), tuple(int(c * 0.78) for c in cap_col), INK, 5)
        elif acc == "tuft":
            for dx, tipx in ((-12, -20), (0, 0), (12, 20)):
                hline(bezier((dx, -98), (dx * 0.4, -118), (tipx, -140)), 6)
        elif acc == "moustache":
            hpoly(closed_ellipse(-20 + fdx, 36, 28, 9, 18, 14), INK, None)
            hpoly(closed_ellipse(20 + fdx, 36, 28, 9, 18, -14), INK, None)
        elif acc == "beard":
            pts = ellipse_pts(0, 8, 84, 86, 24, 24, 156)
            hpoly(pts + pts[:1], (60, 52, 48), None)
        elif acc == "bindi":
            hpoly(closed_ellipse(fdx, -48, 7, 7, 14), (200, 40, 50), None)

    for a in front:
        draw_arm(*a)

    anchors = dict(
        head_top=S.T(H((0, -HEAD_R))),
        head_center=S.T(H((0, 0))),
        mouth=S.T(H((fdx, 56))),
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

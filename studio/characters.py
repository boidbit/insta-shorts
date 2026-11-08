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
    "nervous": ("half", "o", "sad"),        # + sweat drops
    "scared": ("wide", "open_small", "up"),  # + sweat drops
    "burnt": ("wide", "flat", None),         # soot on the face + frizzy hair (after a blast)
}
SWEAT = {"nervous", "scared"}
# Eyes that should not be replaced by a "blink"
NO_BLINK = {"happy", "relaxed", "closed", "x", "heart", "wink"}

HAIR = (36, 30, 28)


def shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c[:3])


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

    def dot(self, c, r, fill=INK, outline=None, w=OUTLINE):
        n = 56 if r > 40 else (32 if r > 12 else 20)
        self.poly(closed_ellipse(c[0], c[1], r, r, n), fill, outline, w)


def skeleton(p):
    hipL, hipR = (-36.0, 0.0), (36.0, 0.0)
    kneeL = add(hipL, vec(p["ll1"], TH))
    footL = add(kneeL, vec(p["ll2"], SH))
    kneeR = add(hipR, vec(p["rl1"], TH))
    footR = add(kneeR, vec(p["rl2"], SH))
    shL, shR = (-52.0, -TORSO_H + 55), (52.0, -TORSO_H + 55)
    elbL = add(shL, vec(p["la1"], UA))
    handL = add(elbL, vec(p["la2"], LA))
    elbR = add(shR, vec(p["ra1"], UA))
    handR = add(elbR, vec(p["ra2"], LA))
    neck = (0.0, -TORSO_H + 6)
    hc = add(neck, rot((0.0, -HEAD_R * 0.9), d2r(p["head_tilt"])))
    fy = max(footL[1], footR[1]) + 8
    return dict(hipL=hipL, hipR=hipR, kneeL=kneeL, footL=footL, kneeR=kneeR, footR=footR,
                shL=shL, shR=shR, elbL=elbL, handL=handL, elbR=elbR, handR=handR,
                neck=neck, hc=hc, fy=fy)


def _draw_prop(S, prop, hand, fore_angle, color_hint):
    """Small props held in the hand. fore_angle = direction of the forearm.
    Returns the local point of the prop's tip (for sparks etc.)."""
    if not prop:
        return hand
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
        return pt(150, 0)
    elif prop == "belan":           # rolling pin
        S.line([pt(-38, 0), pt(-14, 0)], 14, (150, 96, 56))
        S.line([pt(-12, 0), pt(118, 0)], 26 + 8, INK)
        S.line([pt(-12, 0), pt(118, 0)], 26, (214, 164, 104))
        S.line([pt(120, 0), pt(144, 0)], 14, (150, 96, 56))
        return pt(146, 0)
    elif prop == "kettle":          # steel chai kettle held by the handle
        S.poly([pt(10, -36), pt(10, 36), pt(78, 30), pt(78, -30)], (196, 198, 206), INK, 5)
        S.line([pt(78, -18), pt(112, -40)], 9, (176, 178, 186))
        S.line([pt(-6, -30), pt(-6, 30)], 7, (60, 60, 64))
        return pt(114, -42)
    elif prop == "chai_glass":      # cutting chai
        S.poly([pt(-6, -18), pt(-6, 18), pt(44, 14), pt(44, -14)], (236, 236, 240), INK, 4)
        S.poly([pt(4, -16), pt(4, 16), pt(42, 13), pt(42, -13)], (176, 110, 58), None)
        return pt(46, 0)
    elif prop == "agarbatti":       # long incense stick with a glowing tip (to light crackers)
        S.line([pt(-24, 0), pt(176, 0)], 7, (118, 72, 44))
        S.line([pt(150, 0), pt(176, 0)], 8, (70, 66, 64))
        S.dot(pt(178, 0), 6, (255, 120, 50))
        return pt(180, 0)
    elif prop == "phuljhadi":       # sparkler wire (add an fx "sparks" at "<who>.prop_tip")
        S.line([pt(-20, 0), pt(150, 0)], 5, (150, 150, 156))
        S.line([pt(60, 0), pt(150, 0)], 9, (92, 88, 86))
        return pt(152, 0)
    return pt(60, 0)


def _eye_center(sgn, face_dx, ey=-4.0, ex=34.0):
    return (sgn * ex + face_dx, ey)


def build_character(spec, pose, expr, mouth_open, t, x0, ground_y, k=1.0,
                    blink=False, prop=None, talking=False, tear_phase=0.0, body=None):
    """Return (ops, anchors) in global logical coordinates.

    `body` is the style's body plug-in (studio.style2d.body.STICK or studio.style25d.body.TOON). It draws
    everything below the head and decides the head base / eye style. Face, hair, props are shared."""
    if body is None:
        raise ValueError("build_character needs a body (style2d.body.STICK or style25d.body.TOON)")
    p = dict(DEFAULT_POSE)
    p.update({kk: vv for kk, vv in pose.items() if vv is not None or kk == "finger"})
    sk = skeleton(p)
    S = Sketch(x0, ground_y, k, p["tilt"], p["shift"], p["lift"], sk["fy"])
    c = spec.get("color", "blue")
    color = tuple(c) if isinstance(c, (list, tuple)) else PALETTE.get(c, PALETTE["blue"])
    cap_col = PALETTE.get(spec.get("cap_color", "red"), PALETTE["red"])
    facing = {"left": -1, "right": 1}.get(spec.get("facing", "front"), 0)
    light = float(spec.get("_light", -1))           # -1: key light from screen-left, +1: from the right
    skin = _rgb(spec.get("skin"), SKIN)

    body.draw_body(S, sk, p, spec, color, skin, light)
    tip = None
    if prop:
        side = spec.get("prop_hand", "R")
        if side == "L":
            tip = _draw_prop(S, prop, sk["handL"], p["la2"], color)
        else:
            tip = _draw_prop(S, prop, sk["handR"], p["ra2"], color)

    # ---- head ----
    ht = d2r(p["head_tilt"])
    hs = float(spec.get("head_scale", body.head_scale))
    hc = add(sk["neck"], rot((0.0, -HEAD_R * 0.9 * hs), ht)) if hs != 1.0 else sk["hc"]

    def H(q):
        return add(hc, rot((q[0] * hs, q[1] * hs), ht))

    def hline(pts, w, col=INK):
        S.line([H(q) for q in pts], w, col)

    def hpoly(pts, fill=None, outline=None, w=OUTLINE):
        S.poly([H(q) for q in pts], fill, outline, w)

    fdx = facing * 14 + p["look_x"] * 5
    body.draw_head(hpoly, hline, skin, facing, light)

    if expr == "burnt":       # soot patches (eyes stay white so they still read)
        soot = (58, 54, 54)
        for (sx, sy, rx, ry, rr) in ((-40, 20, 46, 34, 20), (34, -18, 52, 36, -15), (6, 58, 40, 22, 0),
                                     (-58, -40, 26, 18, 30), (60, 40, 24, 30, 10)):
            pts = [(x_, y_) for (x_, y_) in closed_ellipse(sx + fdx * 0.5, sy, rx, ry, 18, rr)
                   if x_ * x_ + y_ * y_ < (HEAD_R - 6) ** 2]
            if len(pts) >= 3:
                hpoly(pts, soot, None)

    eyes, mouth, brows = EXPRESSIONS.get(expr, EXPRESSIONS["neutral"])
    if blink and eyes not in NO_BLINK:
        eyes = "closed"
    lx, ly = p["look_x"] * 7, p["look_y"] * 5

    for sgn in (-1, 1):
        cx, cy = _eye_center(sgn, fdx)
        if eyes == "dot" and body.big_eyes:     # big cartoon eye: white + pupil + catch-light
            hpoly(closed_ellipse(cx, cy - 2, 18, 21, 24), WHITE, INK, 5)
            hpoly(closed_ellipse(cx + lx * 1.2, cy + ly * 1.2, 9, 10, 18), INK, None)
            hpoly(closed_ellipse(cx + lx * 1.2 + 3, cy + ly * 1.2 - 4, 3, 3, 8), WHITE, None)
        elif eyes == "dot":
            hpoly(closed_ellipse(cx + lx, cy + ly, 10, 10, 20), INK, None)
        elif eyes == "wide":
            hpoly(closed_ellipse(cx, cy - 2, 21, 23, 28), WHITE, INK, 5)
            hpoly(closed_ellipse(cx + lx * 1.4, cy - 2 + ly * 1.4, 8, 8, 18), INK, None)
        elif eyes == "half":
            hpoly(closed_ellipse(cx, cy, 21, 18, 28), WHITE, INK, 5)
            hpoly(closed_ellipse(cx + lx * 1.4 - 2, cy + 4 + ly, 8, 8, 18), INK, None)
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
            hline([(cx - 18, cy), (cx + 18, cy + 2)], 7)
        elif eyes == "x":
            hline([(cx - 15, cy - 15), (cx + 15, cy + 15)], 7)
            hline([(cx - 15, cy + 15), (cx + 15, cy - 15)], 7)
        elif eyes == "heart":
            hpoly(heart_pts(cx, cy, 30), (214, 50, 70), INK, 4)
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

    # tears
    if expr == "cry":
        for sgn in (-1, 1):
            cx, cy = _eye_center(sgn, fdx)
            for j in range(2):
                ph = (tear_phase + j * 0.5) % 1.0
                ty = cy + 14 + ph * 70
                hpoly(closed_ellipse(cx + sgn * 6, ty, 7, 11, 14), TEAR, INK, 3)

    # sweat drops (nervous / scared)
    if expr in SWEAT:
        for j, (sx, sy, sz) in enumerate(((-74, -30, 1.0), (-58, 6, 0.8), (78, -22, 0.9))):
            wob = math.sin(t * 5 + j) * 2
            drop = [(sx + 13 * sz * math.sin(a_) * math.sin(a_ / 2), sy + wob - 15 * sz * math.cos(a_))
                    for a_ in [i_ * 2 * math.pi / 22 for i_ in range(22)]]
            hpoly(drop, (190, 225, 250), INK, 3)

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
    else:  # flat
        hline([(fdx - 24, my + 8), (fdx + 24, my + 8)], 7)

    # accessories
    accs = list(spec.get("accessories", []))
    if expr == "burnt":
        accs = [a_ for a_ in accs if a_ not in ("hair_short", "hair_curly", "hair_bun", "tuft", "cap")] + ["hair_frizz"]
    for acc in accs:
        if acc == "hair_short":
            top = ellipse_pts(0, 0, HEAD_R + 5, HEAD_R + 5, 30, 192, 348)
            fringe = []
            for i in range(9):
                fx = top[-1][0] - (top[-1][0] - top[0][0]) * i / 8.0
                fringe.append((fx, -52 + (12 if i % 2 else 0) - 8 * math.cos(i / 8.0 * math.pi)))
            hpoly(top + fringe, HAIR, INK, 5)
        elif acc == "hair_curly":
            for i in range(11):
                a_ = math.radians(186 + i * 16.8)
                hpoly(closed_ellipse((HEAD_R - 4) * math.cos(a_), (HEAD_R - 6) * math.sin(a_), 27, 25, 18),
                      HAIR, INK, 5)
            hpoly(ellipse_pts(0, -8, HEAD_R - 2, HEAD_R - 14, 20, 196, 344), HAIR, None)
        elif acc == "hair_bun":         # long hair pulled back into a juda, centre parting
            cap = ellipse_pts(0, 0, HEAD_R + 5, HEAD_R + 5, 30, 180, 360)
            hpoly(closed_ellipse(0, -HEAD_R - 14, 40, 34, 24), HAIR, INK, 5)
            hpoly(cap + [(HEAD_R + 5, 20), (HEAD_R - 14, 10), (40, -50), (0, -66), (-40, -50), (-HEAD_R + 14, 10),
                         (-HEAD_R - 5, 20)], HAIR, INK, 5)
            hline([(0, -HEAD_R - 2), (0, -64)], 4, (90, 70, 66))
            hpoly(closed_ellipse(0, -HEAD_R - 14, 18, 12, 14), (230, 70, 90), None)       # a little gajra/clip
        elif acc == "earrings":
            for sgn in (-1, 1):
                hpoly(closed_ellipse(sgn * (HEAD_R - 2), 44, 9, 11, 14), (236, 190, 60), INK, 3)
        elif acc == "hair_frizz":       # blown-up hair after a blast
            for i in range(9):
                a_ = math.radians(198 + i * 18)
                b0 = ((HEAD_R - 10) * math.cos(a_), (HEAD_R - 10) * math.sin(a_))
                b1 = ((HEAD_R + 46) * math.cos(a_ + 0.12), (HEAD_R + 46) * math.sin(a_ + 0.12))
                hline([b0, ((b0[0] + b1[0]) / 2 + 10, (b0[1] + b1[1]) / 2), b1], 9, (44, 40, 40))
            for i in range(3):              # little smoke puffs rising off the head
                ph_ = (t * 0.7 + i / 3.0) % 1.0
                r_ = 9 + 15 * ph_
                c_ = int(120 + 90 * ph_)
                hpoly(closed_ellipse(-30 + i * 30 + 10 * math.sin(t * 2 + i), -HEAD_R - 30 - ph_ * 80, r_, r_, 18),
                      (c_, c_, c_ + 4), None)
        elif acc == "glasses":
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

    anchors = dict(
        head_top=S.T(H((0, -HEAD_R))),
        head_center=S.T(H((0, 0))),
        mouth=S.T(H((fdx, 56))),
        feet=S.T((0, sk["fy"])),
        hand_l=S.T(sk["handL"]),
        hand_r=S.T(sk["handR"]),
        prop_tip=S.T(tip) if tip else None,
    )
    return S.ops, anchors


def _rgb(c, default):
    if c is None:
        return default
    if isinstance(c, (list, tuple)):
        return tuple(int(v) for v in c[:3])
    return PALETTE.get(c, default)


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

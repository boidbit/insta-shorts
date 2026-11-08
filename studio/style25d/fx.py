"""World objects (e.g. a sutli bomb on the floor) and particle effects (sparks, boom, smoke).

Everything here produces drawing ops in logical coordinates, exactly like the characters, so the
camera can move/zoom them sharply and they get depth-sorted with the characters.
"""
import math
import random

from ..characters import INK, Sketch, bezier, closed_ellipse, ellipse_pts
from ..util import clamp, ease_out

JUTE = (218, 188, 124)


# ------------------------------------------------------------------ objects
def burn_fraction(o, t):
    """0 = full fuse, 1 = burnt down. Driven by {"object": id, "burn": secs} / {"stop": true} events."""
    t0 = o.get("_burn_t0")
    if t0 is None or t < t0:
        return 0.0
    dur = max(0.1, float(o.get("_burn_dur", 3.0)))
    te = o.get("_burn_stop")
    tt = min(t, te) if te is not None else t
    return clamp((tt - t0) / dur)


def burning(o, t):
    t0 = o.get("_burn_t0")
    if t0 is None or t < t0:
        return False
    te = o.get("_burn_stop")
    if te is not None and t >= te:
        return False
    return burn_fraction(o, t) < 1.0


def visible(o, t):
    return float(o.get("from", 0.0)) <= t < float(o.get("to", 1e9))


def build_object(o, t, k):
    """Return (ops, anchors) for a world object, in logical coordinates."""
    x, y = float(o["x"]), float(o["y"])
    S = Sketch(x, y, k, 0.0, 0.0, 0.0, 0.0)
    typ = o.get("type", "bomb")
    anchors = {"center": S.T((0, -40)), "feet": S.T((0, 0))}
    if typ == "bomb":                     # sutli bomb: round, wrapped in jute string
        R = 46.0
        S.poly(closed_ellipse(0, -R, R, R * 0.96, 44), (54, 86, 48), INK, 6)
        S.poly(closed_ellipse(-14, -R - 16, 15, 9, 16, -30), (104, 146, 86), None)
        for rot_ in (-28, 28):
            S.line(ellipse_pts(0, -R, R * 0.36, R * 0.95, 26, -90, 90, rot_), 7, JUTE)
        S.line(ellipse_pts(0, -R, R * 0.97, R * 0.3, 26, 0, 180), 7, JUTE)
        S.line(ellipse_pts(0, -R - 20, R * 0.86, R * 0.26, 26, 0, 180), 6, JUTE)
        f = burn_fraction(o, t)
        fuse = bezier((0, -2 * R + 4), (-14, -2 * R - 40), (22, -2 * R - 70), 16)
        keep = max(2, int(round(len(fuse) * (1 - 0.85 * f))))
        fz = fuse[:keep]
        S.line(fz, 7, (82, 70, 56))
        tip = fz[-1]
        if o.get("_burn_t0") is not None and t >= o["_burn_t0"]:
            S.dot(tip, 6, (255, 120, 40) if burning(o, t) else (40, 36, 34))
        anchors.update(fuse=S.T(tip), center=S.T((0, -R)))
    elif typ == "anaar":                  # flower-pot cracker
        S.poly([(-30, 0), (30, 0), (14, -80), (-14, -80)], (210, 60, 50), INK, 6)
        S.line([(-24, -26), (24, -26)], 6, (250, 210, 80))
        anchors.update(fuse=S.T((0, -84)))
    elif typ == "diya":
        S.poly([(-26, -18), (26, -18), (17, -2), (-17, -2)], (176, 84, 42), INK, 4)
        S.poly([(20, -50), (28, -28), (20, -22), (12, -28)], (255, 170, 60), None)
        anchors.update(fuse=S.T((20, -36)))
    return S.ops, anchors


# ------------------------------------------------------------------ particles
def sparks_ops(cx, cy, t, power=1.0, k=1.0, upward=0.4):
    """Crackling sparks around (cx, cy). New random pattern every frame."""
    rnd = random.Random(int(t * 30) * 7919 + int(cx * 13))
    ops = []
    for _ in range(int(20 * power) + 6):
        a = rnd.uniform(0, 2 * math.pi)
        if rnd.random() < upward:
            a = -math.pi / 2 + rnd.uniform(-1.1, 1.1)
        L = rnd.uniform(14, 72) * power * k
        r0 = rnd.uniform(0, 10) * k
        p0 = (cx + r0 * math.cos(a), cy + r0 * math.sin(a))
        p1 = (cx + (r0 + L) * math.cos(a), cy + (r0 + L) * math.sin(a))
        col = rnd.choice([(255, 236, 140), (255, 210, 90), (255, 250, 220), (255, 170, 70)])
        ops.append(dict(t="line", pts=[p0, p1], w=4.5 * k, color=col))
        ops.append(dict(t="line", pts=[p0, ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)], w=2.2 * k,
                        color=(255, 255, 250)))
        if rnd.random() < 0.4:
            q = (cx + (r0 + L * 1.25) * math.cos(a), cy + (r0 + L * 1.25) * math.sin(a))
            ops.append(dict(t="line", pts=[q, (q[0] + 0.5, q[1] + 0.5)], w=5 * k, color=col))
    ops.append(dict(t="poly", pts=[(cx + 9 * k * math.cos(i * 0.785), cy + 9 * k * math.sin(i * 0.785))
                                   for i in range(8)], fill=(255, 255, 235), outline=None, w=0))
    return ops


def _star(cx, cy, r1, r2, n, rot_, wob, rnd):
    pts = []
    for i in range(2 * n):
        r = (r1 if i % 2 == 0 else r2) * (1 + rnd.uniform(-wob, wob))
        a = rot_ + i * math.pi / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def boom_groups(cx, cy, age, k=1.0):
    """List of (ops, alpha, blur) for an explosion `age` seconds old. Empty when finished."""
    groups = []
    rnd = random.Random(int(age * 30) + 5)
    if age < 0.5:
        e = ease_out(age / 0.16)
        shrink = 1.0 - clamp((age - 0.25) / 0.25)
        R = 300 * e * (0.6 + 0.4 * shrink) * k
        ops = []
        for f, col in ((1.0, (255, 120, 40)), (0.72, (255, 200, 70)), (0.42, (255, 250, 220))):
            ops.append(dict(t="poly", pts=_star(cx, cy, R * f, R * f * 0.55, 11, age * 2, 0.18, rnd),
                            fill=col, outline=None, w=0))
        groups.append((ops, clamp(shrink + 0.2), 0))
    if age < 1.3:                         # flying debris + paper bits
        r2 = random.Random(77)
        ops = []
        for i in range(22):
            a = r2.uniform(-math.pi, 0.15)
            v = r2.uniform(380, 900)
            px = cx + math.cos(a) * v * age * k
            py = cy + (math.sin(a) * v * age + 900 * age * age) * k
            sz = r2.uniform(6, 13) * k
            col = r2.choice([(200, 50, 46), (60, 50, 44), (218, 188, 124), (255, 200, 80)])
            ops.append(dict(t="poly", pts=closed_ellipse(px, py, sz, sz * 0.6, 8, age * 400 + i * 30),
                            fill=col, outline=None, w=0))
        groups.append((ops, clamp(1.3 - age), 0))
    if age < 3.2:                         # smoke puffs
        r3 = random.Random(91)
        ops = []
        for i in range(11):
            d = r3.uniform(0.0, 0.35)
            a2 = age - d
            if a2 <= 0:
                continue
            ang = r3.uniform(-math.pi, 0)
            spread = r3.uniform(60, 190)
            px = cx + math.cos(ang) * spread * ease_out(a2 / 0.8) * k + 14 * math.sin(a2 * 2 + i) * k
            py = cy + (math.sin(ang) * spread * 0.6 * ease_out(a2 / 0.8) - 70 * a2) * k
            r = (40 + 70 * ease_out(a2 / 1.2)) * k
            g = int(r3.uniform(96, 168))
            ops.append(dict(t="poly", pts=closed_ellipse(px, py, r, r * 0.9, 26), fill=(g, g - 2, g + 6),
                            outline=None, w=0))
            ops.append(dict(t="poly", pts=closed_ellipse(px - r * 0.25, py - r * 0.3, r * 0.55, r * 0.45, 18),
                            fill=(min(255, g + 40), min(255, g + 38), min(255, g + 44)), outline=None, w=0))
        groups.append((ops, 0.8 * clamp((3.2 - age) / 1.6), 9))
    return groups

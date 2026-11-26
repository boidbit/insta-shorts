"""Animals: dog, cat, cow, goat (four-legged rig), crow, parrot, rooster (bird rig), and two pests with faces:
the lizard on the wall and the mosquito buzzing round the heads (their own little rigs).
(A monkey uses the stickman rig: { "kind": "monkey" } so every human action works for it.)

Character spec:  { "kind": "dog", "color": [180, 130, 80], "x": 300, "facing": "right" }
Actions:         idle, walk / run (automatic while moving), sit, lie_down / sleep, jump, bark (= meow, moo,
                 caw, speak), wag, eat, fly (birds), peck (birds), shock
The dog has three angles (spec["pose_view"], chosen by the renderer): "side" (the whole dog in profile), "turn" (the
body in profile, the head turned to us: while it talks) and "front" (all of it facing us: its own close-up, or
`Sultan -> saamne`). Its accessories: sunglasses, chain (a gold chain), cap (worn backwards).
"""
import math

from .characters import INK, Sketch, closed_ellipse, ellipse_pts, bezier

ANIMALS = ("dog", "cat", "cow", "buffalo", "goat", "crow", "parrot", "rooster", "lizard", "mosquito")

QUAD = {
    #        body rx, ry, leg len, head r, default color, scale
    "dog": dict(rx=150, ry=66, leg=150, head=62, color=(186, 134, 84), tail="up"),
    "cat": dict(rx=112, ry=50, leg=110, head=54, color=(232, 150, 70), tail="curl"),
    "cow": dict(rx=250, ry=118, leg=210, head=78, color=(248, 248, 244), tail="rope"),
    "goat": dict(rx=128, ry=58, leg=128, head=50, color=(236, 230, 216), tail="stub"),
    "buffalo": dict(rx=262, ry=124, leg=196, head=90, color=(84, 80, 86), tail="rope"),     # bhains
}
BIRD = {
    "crow": dict(body=(40, 52, 58), beak=(60, 60, 64), size=1.0),
    "parrot": dict(body=(70, 170, 80), beak=(220, 70, 50), size=1.1),
    "rooster": dict(body=(212, 112, 46), beak=(236, 180, 60), size=1.25),
}
WALL_Y = -640.0                     # the lizard lives on the wall, this high above the floor
HOVER_Y = -560.0                    # the mosquito buzzes about at head height


def _col(spec, default):
    c = spec.get("color")
    return tuple(c[:3]) if isinstance(c, (list, tuple)) else default


def build_animal(spec, action, at, t, x0, ground_y, k, dirn, moving, running, mouth_open=0.0, expr="neutral"):
    """Return (ops, anchors). dirn = +1 facing right, -1 facing left. at = time since the action started."""
    kind = spec.get("kind")
    if kind == "lizard":
        return _lizard(spec, action, at, t, x0, ground_y, k, dirn, moving, mouth_open, expr)
    if kind == "mosquito":
        return _mosquito(spec, action, at, t, x0, ground_y, k, dirn, moving, mouth_open, expr)
    if kind in BIRD:
        return _bird(spec, action, at, t, x0, ground_y, k, dirn, moving, mouth_open, expr)
    return _quad(spec, action, at, t, x0, ground_y, k, dirn, moving, running, mouth_open, expr)


# how big each one is next to the people (a cow / bhains is a big animal: ~1.3 m at the shoulder)
SIZE = {"dog": 0.82, "cat": 0.82, "cow": 1.2, "buffalo": 1.25, "goat": 1.0}
# the body's outline (body-local, x forward, y down, in units of rx / ry), drawn as a smooth closed curve
BODY = {
    "cow": [(0.72, -0.95), (0.5, -1.34), (0.26, -0.96), (-0.4, -0.92), (-0.82, -0.9), (-1.0, -0.55), (-1.03, 0.0),
            (-0.92, 0.5), (-0.6, 0.86), (0.0, 1.02), (0.55, 0.92), (0.9, 0.5), (1.0, 0.0), (0.93, -0.55)],
    "buffalo": [(0.6, -0.98), (0.1, -1.0), (-0.5, -0.96), (-0.86, -0.88), (-1.03, -0.5), (-1.05, 0.05),
                (-0.95, 0.56), (-0.62, 0.94), (0.0, 1.12), (0.55, 1.0), (0.92, 0.56), (1.03, 0.0), (0.96, -0.56)],
    "goat": [(0.6, -0.92), (0.0, -0.88), (-0.7, -0.96), (-1.0, -0.55), (-1.0, 0.05), (-0.85, 0.55), (-0.5, 0.8),
             (0.1, 0.9), (0.6, 0.86), (0.95, 0.45), (1.0, -0.1), (0.9, -0.6)],
    "dog": [(0.55, -0.92), (0.0, -0.86), (-0.6, -0.94), (-0.98, -0.6), (-1.02, 0.0), (-0.86, 0.45), (-0.5, 0.55),
            (0.0, 0.62), (0.45, 0.96), (0.85, 0.76), (1.0, 0.2), (0.95, -0.45)],
    "cat": [(0.6, -0.86), (0.0, -0.96), (-0.6, -1.0), (-1.0, -0.6), (-1.02, 0.1), (-0.8, 0.7), (-0.3, 0.86),
            (0.3, 0.86), (0.8, 0.66), (1.0, 0.1), (0.9, -0.5)],
}
HOOVES = ("cow", "buffalo", "goat")
LEG_W = {"cow": 0.66, "buffalo": 0.7, "goat": 0.6, "dog": 0.56, "cat": 0.6}       # thigh width, in ry
NECK_W = {"cow": 1.1, "buffalo": 1.2, "goat": 0.85, "dog": 0.82, "cat": 0.78}     # neck width at the body, in ry
HEAD_AT = {"cow": (0.55, -0.62), "buffalo": (0.58, -0.5), "goat": (0.5, -1.15), "dog": (0.35, -1.25),
           "cat": (0.25, -1.08)}                                                   # (x in hr past rx, y in ry)


def extent(kind, scale):
    """(front, back): how far a four-legged animal reaches in front of its x (to the nose) and behind it (to the
    rump), in logical px at character scale `scale`."""
    P = QUAD.get(kind)
    if P is None:
        return 0.0, 0.0
    k = scale * SIZE.get(kind, 1.0)
    return (P["rx"] + P["head"] * (HEAD_AT[kind][0] + 1.3)) * k, (P["rx"] * 1.05 + 30) * k


def _spline(pts, n=6):
    """A smooth closed curve through the points (Catmull-Rom)."""
    out, m = [], len(pts)
    for i in range(m):
        p0, p1, p2, p3 = pts[(i - 1) % m], pts[i], pts[(i + 1) % m], pts[(i + 2) % m]
        for j in range(n):
            u = j / float(n)
            u2, u3 = u * u, u * u * u
            out.append(tuple(0.5 * (2 * p1[c] + (-p0[c] + p2[c]) * u + (2 * p0[c] - 5 * p1[c] + 4 * p2[c] - p3[c]) * u2
                                    + (-p0[c] + 3 * p1[c] - 3 * p2[c] + p3[c]) * u3) for c in (0, 1)))
    return out


def _taper(n, w0, w1):
    return [w0 + (w1 - w0) * j / float(max(1, n - 1)) for j in range(n)]


def _mix(c, d, u):
    return tuple(int(c[i] + (d[i] - c[i]) * u) for i in range(3))


# These cues read through the dog's silhouette: lifted paw, raised chest, tucked tail or folded legs.
DOG_BODY_ACTIONS = {"wag", "arms_crossed", "proud", "point_self", "shiver", "ghoorna", "faint"}


def _quad(spec, action, at, t, x0, ground_y, k, dirn, moving, running, mouth_open, expr):
    kind = spec.get("kind", "dog")
    P = QUAD.get(kind, QUAD["dog"])
    col = _col(spec, P["color"])
    dk = tuple(int(v * 0.74) for v in col)
    light = _mix(col, (255, 255, 255), 0.2)
    shade_ = tuple(int(v * 0.86) for v in col)
    rx, ry, hr = P["rx"], P["ry"], P["head"]
    leg = P["leg"]
    S = Sketch(x0, ground_y, k * SIZE.get(kind, 1.0) / 0.82, 0, 0, 0, 0)
    D = dirn

    def X(p):
        return (p[0] * D, p[1])

    def poly(pts, fill, outline=INK, w=6):
        S.poly([X(p) for p in pts], fill, outline, w)

    def line(pts, w, c=INK):
        S.line([X(p) for p in pts], w, c)

    def limb(pts, widths, fill):
        S.limb([X(p) for p in pts], widths, fill, 5)

    cattle = kind in HOOVES
    sit = action == "sit" and not cattle
    lie = action in ("lie_down", "lie", "sleep", "sleep_lie") or (action == "sit" and cattle)   # cattle sit = lie
    graze = action == "eat" and cattle and not lie
    speak = action in ("bark", "meow", "moo", "speak", "caw") or mouth_open > 0.1
    jump = action in ("jump", "shock")
    gait_f = 3.0 if running else 1.8
    ph = t * 2 * math.pi * gait_f if moving else 0.0
    lift = 0.0
    if jump:
        lift = -120 * abs(math.sin(math.pi * min(1.0, at / 0.45))) if at < 0.45 else 0.0
    if moving:
        lift -= 6 * abs(math.sin(ph))
    breathe = 0.0 if moving else 3 * math.sin(t * 2.2)
    body_y = -(leg + ry * 0.5) + lift
    tilt = -24.0 if sit else 0.0
    if lie:
        body_y = -ry * 0.95
    dog_cue = action if kind == "dog" and action in DOG_BODY_ACTIONS else None
    settle = min(1.0, max(0.0, at / 0.28))
    proud = settle if dog_cue in ("arms_crossed", "proud") else 0.0
    nervous = settle if dog_cue == "shiver" else 0.0
    collapse = min(1.0, max(0.0, (at - 0.18) / 0.62)) if dog_cue == "faint" else 0.0
    collapse *= collapse * (3 - 2 * collapse)
    body_y += -12 * proud + nervous * (13 + 3 * math.sin(22 * t))
    body_y += (-ry * 0.85 - body_y) * collapse
    tilt += -5 * proud + nervous * 2.5 * math.sin(18 * t)
    bc = (0.0, body_y)
    view = spec.get("pose_view") if kind == "dog" else None
    acc = set(spec.get("accessories") or ())
    if view == "front" and not lie and not dog_cue:
        return _dog_front(S, X, poly, line, limb, P, col, dk, light, t, at, action, speak, mouth_open, expr,
                          lift, sit, acc, spec)

    def B(p):                          # body-local -> local, with the body's tilt (sitting)
        a = math.radians(tilt)
        x, y = p
        return (bc[0] + x * math.cos(a) - y * math.sin(a), bc[1] + x * math.sin(a) + y * math.cos(a))

    # ---- legs: [hip/shoulder ... hoof] with knees, hocks and fetlocks
    thick = LEG_W[kind] * ry
    legs = []
    for i, (hx, off, front) in enumerate(((-rx * 0.6, 0.0, False), (-rx * 0.46, math.pi, False),
                                          (rx * 0.5, math.pi, True), (rx * 0.64, 0.0, True))):
        top = B((hx, ry * 0.3))
        L = -top[1]
        sw = 30 * math.sin(ph + off) if moving else 0.0
        raise_ = max(0.0, 26 * math.sin(ph + off + math.pi / 2)) if moving else 0.0
        if lie:                                         # folded under the body
            pts = [top, (top[0] + (0.2 if front else 0.1) * rx, -ry * 0.25), (top[0] + (0.48 if front else 0.36) * rx, -12)]
            wid = [thick, thick * 0.5, thick * 0.38]
        elif sit and not front:                          # the haunches on the ground, the paw forward
            pts = [top, (top[0] + 0.12 * rx, -ry * 0.35), (top[0] + 0.5 * rx, -10)]
            wid = [thick * 1.15, thick * 0.6, thick * 0.38]
        elif jump and at < 0.45:
            pts = [top, (top[0] + (24 if front else -24), top[1] + L * 0.4), (top[0] + (40 if front else -40), top[1] + L * 0.7)]
            wid = [thick, thick * 0.45, thick * 0.34]
        elif front:
            foot = (top[0] + sw, -raise_)
            knee = (top[0] + sw * 0.55 + 6, top[1] + L * 0.55 - raise_ * 0.5)
            fet = (foot[0] + 4, -L * 0.13 - raise_)
            pts, wid = [top, knee, fet, foot], [thick, thick * 0.46, thick * 0.32, thick * 0.34]
        else:
            foot = (top[0] + sw, -raise_)
            stifle = (top[0] + L * 0.14 + sw * 0.3, top[1] + L * 0.28)
            hock = (top[0] - L * 0.1 + sw * 0.7, top[1] + L * 0.62 - raise_ * 0.6)
            fet = (foot[0] + 4, -L * 0.13 - raise_)
            pts, wid = [top, stifle, hock, fet, foot], [thick * 1.2, thick * 0.78, thick * 0.4, thick * 0.32, thick * 0.34]
        if collapse:
            pts = [(x + collapse * j / (len(pts) - 1) * (45 if front else 75),
                    y * (1 - 0.65 * collapse) if 0 < j < len(pts) - 1 else y)
                   for j, (x, y) in enumerate(pts)]
        if i == 3 and dog_cue in ("point_self", "proud", "arms_crossed"):
            paw = settle * (1.0 if dog_cue == "point_self" else 0.55)
            pts = [(x + 32 * paw * j / (len(pts) - 1), y - 52 * paw * (j / (len(pts) - 1)) ** 1.4)
                   for j, (x, y) in enumerate(pts)]
        legs.append((pts, wid, i))

    def foot_end(pts, c):
        fx, fy = pts[-1]
        w = thick * 0.34
        if cattle:                                       # a cloven hoof
            poly([(fx - w * 0.6, fy), (fx + w * 0.8, fy), (fx + w * 0.62, fy - w * 0.9), (fx - w * 0.55, fy - w * 0.9)],
                 (58, 50, 46), INK, 4)
            line([(fx + w * 0.1, fy), (fx + w * 0.05, fy - w * 0.6)], 3, (150, 140, 130))
        else:                                            # a paw with its toes
            poly(closed_ellipse(fx + w * 0.3, fy - w * 0.35, w * 0.95, w * 0.5, 16), c, INK, 4)
            for dx in (0.05, 0.45, 0.85):
                line([(fx + w * dx, fy - w * 0.1), (fx + w * dx, fy - w * 0.35)], 3)

    for pts, wid, i in legs:                             # the far pair first, a shade darker
        if i in (1, 2):
            limb(pts, wid, dk)
            foot_end(pts, dk)

    # ---- tail
    wag = math.sin(t * (14 if action == "wag" else 4)) * (22 if action in ("wag", "idle") else 8)
    root = B((-rx * 0.97, -ry * 0.62))
    if P["tail"] == "rope":                              # cattle: a long rope with a tuft, swishing
        tip = (root[0] - 34 + wag * 0.8, root[1] + leg * 0.95 + ry * 0.4)
        path = bezier(root, (root[0] - 40, root[1] + 60), tip, 8)
        path = path[::2] + [tip]
        limb(path, _taper(len(path), 11, 6), col)
        poly(_spline([(tip[0] - 12, tip[1] - 26), (tip[0] + 12, tip[1] - 26), (tip[0] + 16, tip[1] + 22),
                      (tip[0], tip[1] + 44), (tip[0] - 16, tip[1] + 22)]), (46, 40, 38), INK, 3)
    elif P["tail"] == "up":
        wag = 72 * settle * math.sin(17 * t) if dog_cue == "wag" else wag
        if dog_cue == "ghoorna":
            wag = 0.0
        tuck = max(nervous, collapse)
        path = bezier(root, (root[0] - 60, root[1] - 30 + wag * 0.5 + 58 * tuck),
                      (root[0] - 70 + wag + 74 * tuck, root[1] - 120 + 162 * tuck), 6)
        limb(path, _taper(len(path), 18, 4), col)
    elif P["tail"] == "curl":
        path = bezier(root, (root[0] - 100, root[1] + 20), (root[0] - 80 + wag, root[1] - 120), 6)[:-1] + \
            bezier((root[0] - 80 + wag, root[1] - 120), (root[0] - 64 + wag, root[1] - 176), (root[0] - 30 + wag, root[1] - 158), 4)
        limb(path, _taper(len(path), 16, 6), col)
    else:
        limb([root, (root[0] - 30, root[1] - 36 + wag * 0.4), (root[0] - 40, root[1] - 64 + wag * 0.6)], [16, 12, 6], col)

    # ---- the head's place
    ax, ay = HEAD_AT[kind]
    if lie:
        hcen = B((rx + hr * 0.45, -ry * 0.55))
    elif sit:
        hcen = B((rx * 0.95, -ry - hr * 0.6))
    elif graze:                                          # head down to the grass, chewing
        hcen = (B((rx + hr * 0.95, 0))[0], -hr * 0.85)
    else:
        hcen = B((rx + hr * ax, ry * ay))
    bob = 6 * math.sin(ph * 2) if moving else (2 * math.sin(t * 2) + (3 * math.sin(t * 9) if graze else 0.0))
    hx_, hy_ = hcen[0], hcen[1] + bob

    hx_ += 20 * proud
    hy_ += -26 * proud + 16 * nervous + 60 * collapse
    pitch = math.radians(-12 * proud + 9 * nervous + 35 * collapse)
    cs, sn = math.cos(pitch), math.sin(pitch)

    def H(u, v):
        return (hx_ + (u * cs - v * sn) * hr, hy_ + (u * sn + v * cs) * hr)

    # ---- neck (under the body's outline at one end, under the head at the other)
    base = B((rx * 0.72, -ry * 0.22))
    turn = view == "turn" and not lie and not graze
    neck_end = H(-0.1, 0.45) if turn else H(-0.35, 0.15)
    limb([base, ((base[0] + neck_end[0]) / 2, (base[1] + neck_end[1]) / 2 - 6), neck_end],
         [NECK_W[kind] * ry, NECK_W[kind] * ry * 0.82, hr * 0.95], col)

    # ---- body: the outline, light on the back, shade under the belly, the kind's own marks
    body = [B((u * rx, v * ry + (breathe * 0.4 if v > 0.5 else 0.0))) for u, v in _spline(BODY[kind], 6)]
    poly(body, col, INK, 6)
    poly([B(q) for q in closed_ellipse(-rx * 0.08, -ry * 0.5, rx * 0.72, ry * 0.26, 28)], light, None)
    poly([B(q) for q in closed_ellipse(0.0, ry * 0.62, rx * 0.58, ry * 0.24, 28)], shade_, None)
    if kind == "cow":                                    # the desi cow's patches and its hump
        for (sx, sy, r) in ((-0.42, -0.12, 0.2), (0.18, 0.18, 0.16), (-0.75, 0.3, 0.12)):
            poly([B((sx * rx + q[0], sy * ry + q[1])) for q in _spline([(-r * rx, 0), (-r * rx * 0.3, -r * rx * 0.8),
                  (r * rx * 0.6, -r * rx * 0.6), (r * rx, 0.1 * r * rx), (0, r * rx * 0.7)], 4)], (70, 60, 56), None)
        poly([B(q) for q in _spline([(0.28 * rx, -0.95 * ry), (0.5 * rx, -1.3 * ry), (0.7 * rx, -0.95 * ry)], 4)],
             light, None)
    elif kind == "cat":                                  # tabby stripes
        for u in (-0.6, -0.3, 0.0, 0.3):
            line([B((u * rx, -0.98 * ry)), B(((u + 0.06) * rx, -0.45 * ry))], 7, dk)
    elif kind == "dog":                                  # a darker saddle
        poly([B(q) for q in _spline([(-0.7 * rx, -0.85 * ry), (0.0, -0.95 * ry), (0.45 * rx, -0.8 * ry),
                                     (0.2 * rx, -0.35 * ry), (-0.55 * rx, -0.35 * ry)], 4)], dk, None)
    elif kind == "buffalo":                              # the bony hip and the ribs under the dark hide
        line(ellipse_pts(B((-0.68 * rx, -0.62 * ry))[0], B((-0.68 * rx, -0.62 * ry))[1], 34, 22, 8, 180, 330), 4, light)
        for u in (0.05, 0.22, 0.39):
            line(bezier(B((u * rx, -0.3 * ry)), B(((u + 0.04) * rx, 0.1 * ry)), B((u * rx, 0.45 * ry)), 6), 3, shade_)
    if cattle and not lie:                               # the udder
        uc = B((-0.42 * rx, 0.92 * ry))
        poly(closed_ellipse(uc[0], uc[1] + 10, rx * 0.15, ry * 0.2, 20), (232, 170, 176) if kind != "buffalo"
             else (150, 120, 126), INK, 4)
        for dx in (-0.08, 0.0, 0.08):
            line([(uc[0] + dx * rx, uc[1] + ry * 0.24), (uc[0] + dx * rx, uc[1] + ry * 0.36)], 6, (214, 150, 158))
    if kind == "cow" and not lie:                        # the dewlap hanging under the neck
        nb = B((0.92 * rx, 0.28 * ry))
        jaw = H(0.0, 0.62)
        poly(_spline([nb, ((nb[0] + jaw[0]) / 2 - 10, (nb[1] + jaw[1]) / 2 + ry * 0.42), jaw,
                      ((nb[0] + jaw[0]) / 2, (nb[1] + jaw[1]) / 2)], 5), col, INK, 4)

    for pts, wid, i in legs:                             # the near pair
        if i in (0, 3):
            limb(pts, wid, col if kind not in ("cow",) else _mix(col, (255, 255, 255), 0.05))
            foot_end(pts, col)

    if "chain" in acc and kind == "dog":            # the gold chain round the neck, its pendant at the throat
        _side_chain(S, X, line, base, neck_end, NECK_W[kind] * ry * 0.86)
    # ---- head
    if turn:                                        # the head turned to us (it is talking)
        mouth = _front_head(H, hr, poly, line, col, dk, light, t, speak, mouth_open, expr, action)
        _front_acc(S, X, H, hr, poly, line, acc, spec, chain=False)
        if action in ("phone_call", "call"):
            _dog_phone(poly, H, -1.02, 0.12, -12)
    else:
        mouth = _head(kind, H, hr, poly, line, limb, col, dk, light, t, speak, mouth_open, expr, action, lie, graze, at)
        if kind == "dog":
            _side_acc(S, X, H, hr, poly, line, acc, spec)
        if action in ("phone_call", "call"):
            _dog_phone(poly, H, -0.62, 0.05, 18)
    head_top = X(H(0.0, -1.2))
    anchors = dict(head_top=S.T(head_top), head_center=S.T(X((hx_, hy_))), mouth=S.T(X(mouth)),
                   feet=S.T((0, 0)), hand_l=S.T(X(mouth)), hand_r=S.T(X(mouth)))
    return S.ops, anchors


CAP_COLOR = (214, 44, 52)
SHADES = (24, 24, 32)


def _cap_col(spec):
    c = spec.get("cap_color")
    return tuple(c[:3]) if isinstance(c, (list, tuple)) else CAP_COLOR


def _side_chain(S, X, line, base, end, width):
    """A thick gold chain across the neck (seen from the side), the pendant hanging at the throat."""
    from .characters import GOLD
    dx, dy = end[0] - base[0], end[1] - base[1]
    n = math.hypot(dx, dy) or 1.0
    ux, uy = dx / n, dy / n
    px, py = -uy, ux
    m = (base[0] + dx * 0.5, base[1] + dy * 0.5)
    a = (m[0] + px * width * 0.55, m[1] + py * width * 0.55)
    b = (m[0] - px * width * 0.55, m[1] - py * width * 0.55)
    if a[1] > b[1]:
        a, b = b, a                                  # b: the lower end, the throat
    pts = bezier(a, (m[0] - ux * 14, m[1] - uy * 14), b, 10)
    line(pts, 10)
    for q in pts:
        S.dot(X(q), 5.5, GOLD, None)
    tip = (b[0] + 6, b[1] + 20)
    line([b, tip], 4, GOLD)
    S.dot(X(tip), 15, GOLD, INK, 4)
    S.dot(X(tip), 6, (180, 136, 40), None)


def _dog_phone(poly, H, cx, cy, lean):
    """On a call (phone_call): the phone tucked against the ear, a little slanted."""
    c, s_ = math.cos(math.radians(lean)), math.sin(math.radians(lean))

    def q(u, v):
        return H(cx + u * c - v * s_, cy + u * s_ + v * c)
    poly([q(-0.2, -0.46), q(0.2, -0.46), q(0.2, 0.46), q(-0.2, 0.46)], (40, 44, 52), INK, 4)
    poly([q(-0.13, -0.37), q(0.13, -0.37), q(0.13, 0.37), q(-0.13, 0.37)], (120, 190, 235), None)


def _side_acc(S, X, H, hr, poly, line, acc, spec):
    """The dog's swag in profile: wrap-round shades over its eye, a cap on backwards."""
    if "cap" in acc:
        cc = _cap_col(spec)
        poly(_spline([H(-1.45, -0.62), H(-1.4, -0.48), H(-0.6, -0.46), H(-0.62, -0.62)], 3),
             tuple(int(v * 0.75) for v in cc), INK, 4)                   # the brim, pointing back
        dome = [H(-0.72, -0.5)] + [H(-0.05 + 0.68 * math.cos(math.radians(a)), -0.55 + 0.55 * math.sin(math.radians(a)))
                                   for a in range(180, 361, 20)] + [H(0.64, -0.5)]
        poly(dome, cc, INK, 5)
        line([H(-0.7, -0.52), H(0.62, -0.52)], 6, tuple(int(v * 0.7) for v in cc))
        S.dot(X(H(-0.05, -1.08)), 7, tuple(int(v * 0.8) for v in cc), INK, 3)
    if "sunglasses" in acc:
        line([H(0.08, -0.4), H(-0.5, -0.4)], 6)                          # the arm, back to the ear
        poly(_spline([H(0.04, -0.52), H(0.62, -0.54), H(0.66, -0.18), H(0.36, -0.05), H(0.08, -0.16)], 4),
             SHADES, INK, 4)
        poly([H(0.7, -0.5), H(0.9, -0.48), H(0.86, -0.26), H(0.72, -0.24)], SHADES, INK, 3)    # the far lens
        line([H(0.62, -0.47), H(0.72, -0.46)], 5)
        line([H(0.16, -0.38), H(0.32, -0.46)], 4, (150, 150, 176))      # glint


def _front_acc(S, X, H, hr, poly, line, acc, spec, chain=True):
    """The dog's swag from the front: two black lenses, the cap's front with its strap gap, the chain on the chest."""
    from .characters import GOLD
    if chain and "chain" in acc:
        pts = bezier(H(-0.62, 0.62), H(0.0, 1.42), H(0.62, 0.62), 14)
        line(pts, 10)
        for q in pts:
            S.dot(X(q), 5.5, GOLD, None)
        S.dot(X(H(0.0, 1.06)), 17, GOLD, INK, 4)
        S.dot(X(H(0.0, 1.06)), 7, (180, 136, 40), None)
    if "cap" in acc:
        cc = _cap_col(spec)
        dome = [H(-0.8, -0.5)] + [H(0.8 * math.cos(math.radians(a)), -0.52 + 0.6 * math.sin(math.radians(a)))
                                  for a in range(180, 361, 15)] + [H(0.8, -0.5)]
        poly(dome, cc, INK, 5)
        line([H(-0.8, -0.54), H(0.8, -0.54)], 9, tuple(int(v * 0.7) for v in cc))
        poly([H(-0.2, -0.56)] + [H(0.2 * math.cos(math.radians(a)), -0.56 + 0.22 * math.sin(math.radians(a)))
                                 for a in range(180, 361, 30)], spec.get("_fur") or (186, 134, 84), INK, 3)
        S.dot(X(H(0.0, -1.12)), 7, tuple(int(v * 0.8) for v in cc), INK, 3)
    if "sunglasses" in acc:
        for sgn in (-1, 1):
            c = (sgn * 0.36, -0.2)
            poly(_spline([H(c[0] - 0.3, c[1] - 0.16), H(c[0] + 0.3, c[1] - 0.18), H(c[0] + 0.26, c[1] + 0.14),
                          H(c[0], c[1] + 0.22), H(c[0] - 0.26, c[1] + 0.14)], 4), SHADES, INK, 4)
            line([H(c[0] - 0.18, c[1] - 0.06), H(c[0] - 0.06, c[1] - 0.12)], 4, (150, 150, 176))
        line([H(-0.08, -0.32), H(0.08, -0.32)], 6)
        line([H(-0.66, -0.34), H(-0.9, -0.38)], 5)
        line([H(0.66, -0.34), H(0.9, -0.38)], 5)


def _front_head(H, hr, poly, line, col, dk, light, t, speak, mouth_open, expr, action):
    """The dog's head facing us: both floppy ears, two eyes, the muzzle in the middle. Returns the mouth."""
    closed = expr in ("sleepy", "happy", "laugh")
    poly(_spline([H(*q) for q in ((-0.9, -0.1), (-0.78, -0.7), (0.0, -0.94), (0.78, -0.7), (0.9, -0.1),
                                  (0.72, 0.56), (0.0, 0.8), (-0.72, 0.56))], 5), col, INK, 6)
    poly(closed_ellipse(*H(0.0, -0.5), hr * 0.34, hr * 0.22, 16), light, None)
    for sgn in (-1, 1):                                  # the floppy ears, hanging at the sides
        poly(_spline([H(sgn * q[0], q[1]) for q in ((0.55, -0.78), (1.12, -0.5), (1.22, 0.34), (0.98, 0.5),
                                                    (0.74, -0.08))], 4), dk, INK, 4)
    poly(closed_ellipse(*H(0.0, 0.34), hr * 0.52, hr * 0.4, 22), light, INK, 4)          # the muzzle
    nose = H(0.0, 0.1)
    poly(closed_ellipse(nose[0], nose[1], hr * 0.2, hr * 0.14, 16), (30, 26, 28), INK, 3)
    poly(closed_ellipse(nose[0] - hr * 0.06, nose[1] - hr * 0.05, hr * 0.06, hr * 0.03, 8), (120, 120, 130), None)
    mouth = H(0.0, 0.52)
    if speak:
        poly(closed_ellipse(mouth[0], mouth[1], hr * 0.26, hr * (0.08 + 0.18 * max(0.4, mouth_open)), 18),
             (110, 30, 40), INK, 3)
        poly(closed_ellipse(mouth[0], mouth[1] + hr * 0.1 * max(0.4, mouth_open), hr * 0.14, hr * 0.08, 12),
             (230, 110, 120), None)
    else:
        line([H(0.0, 0.24), H(0.0, 0.38)], 4)
        line(bezier(H(-0.26, 0.4), H(-0.12, 0.5), H(0.0, 0.38), 6), 4)
        line(bezier(H(0.0, 0.38), H(0.12, 0.5), H(0.26, 0.4), 6), 4)
        if action in ("wag", "idle") or expr in ("happy", "laugh", "smile"):         # the tongue out, panting
            poly(_spline([H(-0.1, 0.46), H(0.1, 0.46), H(0.1, 0.72 + 0.05 * math.sin(t * 8)), H(-0.1, 0.72)], 4),
                 (232, 110, 122), INK, 3)
    plain = "neutral" if expr in ("angry", "shout") else expr
    for sgn in (-1, 1):
        _eye(H, hr, poly, line, (sgn * 0.36, -0.2), plain, closed, "dog", 0.18)
        if expr in ("angry", "shout", "determined", "evil", "disgust"):
            line([H(sgn * 0.62, -0.52), H(sgn * 0.14, -0.36)], 6)
        elif expr in ("sad", "cry", "scared", "nervous", "hurt"):
            line([H(sgn * 0.6, -0.36), H(sgn * 0.16, -0.5)], 5)
        elif expr in ("shock", "surprised", "excited"):
            line(ellipse_pts(*H(sgn * 0.36, -0.46), hr * 0.2, hr * 0.08, 8, 200, 340), 5)
    return mouth


def _dog_front(S, X, poly, line, limb, P, col, dk, light, t, at, action, speak, mouth_open, expr, lift, sit, acc,
               spec):
    """The whole dog facing us: chest, the two front legs, the hind paws (or the haunches, sitting) and the tail
    wagging up behind one side, the head on top."""
    ry, leg, hr = P["ry"], P["leg"], P["head"]
    cy = (-(leg * 0.86 + ry * 0.3) if sit else -(leg + ry * 0.35)) + lift
    wag = math.sin(t * (14 if action == "wag" else 4)) * (22 if action in ("wag", "idle") else 8)
    tail = bezier((40, cy - 30), (110, cy - 60 + wag * 0.4), (96 + wag, cy - 160), 6)
    limb(tail, _taper(len(tail), 18, 4), col)
    paw_w = 26

    def paw(x, y, c, w=paw_w):
        poly(closed_ellipse(x, y, w, w * 0.6, 16), c, INK, 4)
        for dx in (-0.35, 0.0, 0.35):
            line([(x + w * dx, y + w * 0.1), (x + w * dx, y + w * 0.5)], 3)

    if sit:                                              # the haunches either side, the hind paws turned out
        for sgn in (-1, 1):
            poly(closed_ellipse(sgn * 66, -54 + lift, 54, 50, 22), col, INK, 5)
            paw(sgn * 98, -12 + lift, col, 30)
    else:
        for sgn in (-1, 1):                              # the hind legs, further back (a shade darker)
            limb([(sgn * 56, cy + 10), (sgn * 60, -leg * 0.45), (sgn * 60, -12)], [30, 24, 22], dk)
            paw(sgn * 60, -12 + lift * 0.0, dk, 22)
    poly(_spline([(0, cy - 82), (60, cy - 60), (74, cy + 6), (52, cy + 70), (0, cy + 84), (-52, cy + 70), (-74, cy + 6),
                  (-60, cy - 60)], 5), col, INK, 6)      # the chest
    poly(closed_ellipse(0, cy + 14, 38, 54, 20), light, None)
    for sgn in (-1, 1):                                  # the front legs
        top = (sgn * 34, cy + 30)
        foot = (sgn * 36, -14 + (lift if sit else lift))
        limb([top, (sgn * 35, (top[1] + foot[1]) / 2), foot], [38, 28, 26], col)
        paw(foot[0], foot[1], col)
    bob = 2 * math.sin(t * 2) + (3 * math.sin(t * 16) if speak else 0.0)
    hy = cy - 76 - hr * 0.55 + bob
    limb([(0, cy - 40), (0, hy + hr * 0.3)], [74, 66], col)

    def H(u, v):
        return (u * hr, hy + v * hr)

    spec = dict(spec, _fur=col)
    mouth = _front_head(H, hr, poly, line, col, dk, light, t, speak, mouth_open, expr, action)
    _front_acc(S, X, H, hr, poly, line, acc, spec)
    if action in ("phone_call", "call"):
        _dog_phone(poly, H, 1.02, 0.12, 12)
    anchors = dict(head_top=S.T(X(H(0.0, -1.2))), head_center=S.T(X(H(0.0, 0.0))), mouth=S.T(X(mouth)),
                   feet=S.T((0, 0)), hand_l=S.T(X(mouth)), hand_r=S.T(X(mouth)))
    return S.ops, anchors


def _eye(H, hr, poly, line, at_uv, expr, closed, kind, big=0.17, iris=None, slit=None):
    """An eye with its white, pupil, shine and lid; closed (asleep / happy) is an arc; angry gets a brow."""
    cx, cy = H(*at_uv)
    if closed:
        line(ellipse_pts(cx, cy, hr * big, hr * big * 0.6, 8, 200, 340), 5)
        return
    r = hr * big * (1.25 if expr in ("shock", "surprised", "scared") else 1.0)
    poly(closed_ellipse(cx, cy, r, r * 0.86, 18), (250, 248, 242), INK, 3)
    if iris:
        poly(closed_ellipse(cx + r * 0.15, cy, r * 0.68, r * 0.62, 16), iris, None)
    if slit == "v":                                      # the cat's slit
        poly(closed_ellipse(cx + r * 0.18, cy, r * 0.16, r * 0.56, 12), (20, 20, 22), None)
    elif slit == "h":                                    # the goat's bar
        poly(closed_ellipse(cx + r * 0.15, cy, r * 0.5, r * 0.15, 12), (20, 20, 22), None)
    else:
        poly(closed_ellipse(cx + r * 0.2, cy + r * 0.05, r * 0.5, r * 0.52, 14), (24, 22, 24), None)
    poly(closed_ellipse(cx + r * 0.05, cy - r * 0.25, r * 0.17, r * 0.17, 8), (255, 255, 255), None)
    line(ellipse_pts(cx, cy, r * 1.05, r * 0.95, 8, 195, 345), 4)          # the lid
    if expr in ("angry", "shout"):
        line([(cx - r * 1.2, cy - r * 1.5), (cx + r * 0.9, cy - r * 0.9)], 6)
    elif kind == "cow" and expr not in ("sleepy",):     # lashes
        for a in (210, 240, 270):
            ex_, ey_ = cx + r * 1.05 * math.cos(math.radians(a)), cy + r * 0.95 * math.sin(math.radians(a))
            line([(ex_, ey_), (ex_ + r * 0.25 * math.cos(math.radians(a)), ey_ + r * 0.3 * math.sin(math.radians(a)))], 3)


def _head(kind, H, hr, poly, line, limb, col, dk, light, t, speak, mouth_open, expr, action, lie, graze, at):
    """Draws the head (facing +x) and returns where its mouth is."""
    closed = (lie and action in ("sleep", "sleep_lie")) or expr in ("sleepy", "happy", "laugh")
    chew = 0.04 * math.sin(t * 9) if (graze or kind == "goat") else 0.0
    if kind in ("cow", "buffalo"):
        horn = (226, 214, 180) if kind == "cow" else (104, 100, 98)
        if kind == "buffalo":                            # the bhains's heavy crescent horns, swept back
            for dv, c in ((0.06, tuple(int(v * 0.8) for v in horn)), (0.0, horn)):
                path = [H(-0.2, -0.6 + dv), H(-0.85, -1.0 + dv), H(-1.45, -0.75 + dv), H(-1.52, -0.25 + dv)]
                limb(path, [hr * 0.32, hr * 0.26, hr * 0.15, hr * 0.05], c)
                for j in (1, 2):
                    a, b = path[j], path[j + 1]
                    line([((a[0] * 2 + b[0]) / 3, (a[1] * 2 + b[1]) / 3 - 8), ((a[0] * 2 + b[0]) / 3 + 6, (a[1] * 2 + b[1]) / 3 + 8)],
                         3, tuple(int(v * 0.7) for v in horn))
            ear = [(-0.45, -0.25), (-1.1, -0.02), (-1.16, 0.18), (-0.95, 0.27), (-0.45, 0.1)]
        else:                                            # the cow's short horns, curving up
            for du, c in ((0.18, tuple(int(v * 0.85) for v in horn)), (0.0, horn)):
                limb([H(-0.25 + du, -0.7), H(-0.38 + du, -1.12), H(-0.18 + du, -1.42)], [hr * 0.22, hr * 0.14, hr * 0.05], c)
            ear = [(-0.45, -0.36), (-1.22, -0.58), (-1.32, -0.36), (-1.16, -0.15), (-0.5, -0.1)]
        poly(_spline([H(*q) for q in ear], 4), dk, INK, 4)
        poly(_spline([H(*q) for q in ((-0.6, -0.55), (-0.1, -0.86), (0.45, -0.62), (0.95, -0.08), (1.15, 0.36),
                                      (1.02, 0.76), (0.55, 0.86), (0.0, 0.7), (-0.5, 0.42))], 5), col, INK, 6)
        poly(_spline([H(*q) for q in ((-0.4, -0.55), (0.1, -0.78), (0.45, -0.58), (0.2, -0.35), (-0.3, -0.3))], 4), light, None)
        muzzle = (236, 186, 180) if kind == "cow" else (118, 112, 118)
        mc = H(0.92, 0.42 + chew)
        poly(closed_ellipse(mc[0], mc[1], hr * 0.38, hr * 0.35, 22), muzzle, INK, 4)
        for du in (0.08, -0.14):
            n = H(0.92 + du, 0.3 + chew)
            poly(closed_ellipse(n[0], n[1], hr * 0.07, hr * 0.05, 10), (60, 44, 44), None)
        mouth = H(0.88, 0.7 + chew)
        if speak:
            poly(closed_ellipse(mouth[0], mouth[1], hr * 0.24, hr * (0.08 + 0.16 * max(0.4, mouth_open)), 16), (110, 30, 40), INK, 3)
        else:
            line([H(0.66, 0.68 + chew), H(1.06, 0.66 + chew)], 4)
        if kind == "cow":                                # a curl of hair on the forehead
            line(bezier(H(0.15, -0.72), H(0.35, -0.95), H(0.3, -0.6), 6), 4, dk)
        _eye(H, hr, poly, line, (0.25, -0.22), expr, closed, kind, 0.17 if kind == "cow" else 0.19)
        return mouth
    if kind == "goat":
        for du, c in ((0.16, (150, 132, 104)), (0.0, (176, 156, 122))):    # horns swept back
            limb([H(-0.2 + du, -0.6), H(-0.62 + du, -1.2), H(-1.05 + du, -1.05)], [hr * 0.2, hr * 0.13, hr * 0.04], c)
        poly(_spline([H(*q) for q in ((-0.35, -0.2), (-0.92, 0.3), (-0.88, 0.58), (-0.6, 0.42), (-0.25, 0.05))], 4),
             dk, INK, 4)                                 # the long ear, hanging
        poly(_spline([H(*q) for q in ((-0.55, -0.5), (-0.05, -0.76), (0.5, -0.46), (1.06, 0.1), (1.0, 0.46),
                                      (0.6, 0.56), (0.0, 0.5), (-0.5, 0.3))], 5), col, INK, 6)
        nose = H(0.98, 0.14)
        poly(closed_ellipse(nose[0], nose[1], hr * 0.1, hr * 0.07, 10), (70, 56, 56), None)
        poly([H(0.6, 0.5), H(0.88, 0.5), H(0.74, 1.25 + chew * 3)], _mix(col, (255, 255, 255), 0.3), INK, 3)   # beard
        mouth = H(0.9, 0.38)
        if speak:
            poly(closed_ellipse(mouth[0], mouth[1], hr * 0.16, hr * (0.06 + 0.12 * max(0.4, mouth_open)), 14), (110, 30, 40), INK, 3)
        else:
            line([H(0.7, 0.38), H(0.98, 0.34)], 4)
        _eye(H, hr, poly, line, (0.22, -0.2), expr, closed, kind, 0.2, iris=(226, 190, 70), slit="h")
        return mouth
    if kind == "dog":
        poly(_spline([H(*q) for q in ((-0.8, -0.2), (-0.5, -0.8), (0.2, -0.86), (0.62, -0.42), (1.15, -0.16),
                                      (1.26, 0.24), (1.0, 0.5), (0.4, 0.6), (-0.3, 0.7), (-0.8, 0.36))], 5), col, INK, 6)
        poly(_spline([H(*q) for q in ((0.55, -0.1), (1.15, -0.12), (1.2, 0.3), (0.65, 0.4))], 4), light, None)  # the muzzle
        nose = H(1.18, -0.02)
        poly(closed_ellipse(nose[0], nose[1], hr * 0.17, hr * 0.13, 14), (30, 26, 28), INK, 3)
        mouth = H(0.95, 0.42)
        if speak:
            poly(_spline([H(0.6, 0.38), H(1.12, 0.36), H(1.0, 0.36 + 0.5 * max(0.4, mouth_open)), H(0.7, 0.62)], 4),
                 (110, 30, 40), INK, 3)
            poly(closed_ellipse(*H(0.86, 0.6), hr * 0.14, hr * 0.1, 12), (230, 110, 120), None)
        else:
            line([H(1.1, 0.34), H(0.92, 0.42), H(0.62, 0.4)], 4)
            if action in ("wag", "idle") or expr in ("happy", "laugh", "smile"):         # the tongue out, panting
                poly(_spline([H(0.8, 0.4), H(0.96, 0.42), H(0.94, 0.72 + 0.05 * math.sin(t * 8)), H(0.82, 0.7)], 4),
                     (232, 110, 122), INK, 3)
        poly(_spline([H(*q) for q in ((-0.5, -0.62), (-0.98, -0.42), (-1.02, 0.36), (-0.76, 0.46), (-0.4, -0.2))], 4),
             dk, INK, 4)                                 # the floppy ear
        _eye(H, hr, poly, line, (0.32, -0.3), expr, closed, kind, 0.18)
        return mouth
    # cat: the face turned a little to us
    for (a, b, c) in (((-0.6, -0.55), (-0.62, -1.38), (-0.05, -0.8)), ((0.15, -0.82), (0.58, -1.42), (0.78, -0.52))):
        poly([H(*a), H(*b), H(*c)], col, INK, 5)
        poly([H(a[0] * 0.8 + c[0] * 0.2, a[1] * 0.8 + c[1] * 0.2 - 0.05), H(b[0] * 0.9 + c[0] * 0.1, b[1] * 0.85),
              H(a[0] * 0.2 + c[0] * 0.8, a[1] * 0.2 + c[1] * 0.8 - 0.05)], (236, 170, 176), None)
    poly(_spline([H(*q) for q in ((-0.86, 0.0), (-0.76, -0.6), (0.0, -0.86), (0.76, -0.6), (0.92, 0.0),
                                  (0.72, 0.56), (0.0, 0.76), (-0.7, 0.56))], 5), col, INK, 6)
    poly(_spline([H(*q) for q in ((-0.2, 0.2), (0.35, 0.05), (0.85, 0.2), (0.5, 0.62), (0.0, 0.6))], 4), light, None)
    nose = H(0.35, 0.22)
    poly([(nose[0] - hr * 0.09, nose[1] - hr * 0.05), (nose[0] + hr * 0.09, nose[1] - hr * 0.05), (nose[0], nose[1] + hr * 0.06)],
         (230, 140, 150), INK, 2)
    mouth = H(0.35, 0.42)
    if speak:
        poly(closed_ellipse(mouth[0], mouth[1], hr * 0.16, hr * (0.06 + 0.12 * max(0.4, mouth_open)), 14), (110, 30, 40), INK, 3)
    else:
        line([H(0.18, 0.4), H(0.35, 0.32), H(0.52, 0.4)], 3)
    for side in (-1, 1):                                 # whiskers
        for dv in (-0.05, 0.08):
            line([H(0.35 + side * 0.3, 0.3 + dv), H(0.35 + side * 1.0, 0.24 + dv * 2.2)], 2)
    for u in (0.02, 0.62):
        _eye(H, hr, poly, line, (u, -0.18), expr, closed, kind, 0.17, iris=(140, 200, 90), slit="v")
    return mouth


def _bird(spec, action, at, t, x0, ground_y, k, dirn, moving, mouth_open, expr):
    B_ = BIRD.get(spec.get("kind"), BIRD["crow"])
    col = _col(spec, B_["body"])
    sz = B_["size"]
    D = dirn
    flying = action == "fly" or (moving and spec.get("flies", True))
    S = Sketch(x0, ground_y, k * sz * 1.4, 0, 0, 0, 0)

    def X(p):
        return (p[0] * D, p[1])

    def poly(pts, fill, outline=INK, w=4):
        S.poly([X(p) for p in pts], fill, outline, w)

    def line(pts, w, c=INK):
        S.line([X(p) for p in pts], w, c)

    hop = 0.0
    if action == "jump":
        hop = -40 * abs(math.sin(math.pi * min(1.0, at / 0.35))) if at < 0.35 else 0.0
    by = -70 + hop - (60 + 12 * math.sin(t * 5) if flying else 0)
    peck = action in ("peck", "eat") and (t * 2.2) % 1.0 < 0.4
    if not flying:
        line([(-8, by + 26), (-12, 0)], 4, (90, 80, 60))
        line([(10, by + 26), (8, 0)], 4, (90, 80, 60))
    tail = [(-40, by), (-92, by + 22), (-84, by + 34), (-36, by + 14)]
    if spec.get("kind") == "rooster":   # the big dark tail feathers
        for i, c_ in enumerate(((30, 80, 60), (40, 40, 50), (30, 80, 60))):
            a = -0.4 + 0.35 * i + 0.06 * math.sin(t * 3 + i)
            tip = (-40 - 90 * math.cos(a), by - 20 - 90 * math.sin(a + 0.9))
            poly([(-34, by - 4), tip, (-44, by + 14)], c_)
    else:
        poly(tail, tuple(int(v * 0.8) for v in col))
    poly(closed_ellipse(0, by, 50, 34, 28, -8), col)
    flap = math.sin(t * 22) if flying else 0.0
    wing = [(-24, by - 6), (30, by - 10), (10, by - 10 - 70 * flap), (-30, by - 4 - 50 * flap)] if flying else \
        [(-34, by - 6), (24, by - 8), (6, by + 18), (-40, by + 12)]
    poly(wing, tuple(int(v * 0.75) for v in col))
    hc = (44, by - 34 + (26 if peck else 0))
    poly(closed_ellipse(hc[0], hc[1], 28, 26, 20), col)
    open_ = action in ("caw", "speak", "bark") or mouth_open > 0.1
    beak_c = B_["beak"]
    if open_:
        poly([(hc[0] + 22, hc[1] - 6), (hc[0] + 54, hc[1] - 14), (hc[0] + 26, hc[1] + 2)], beak_c)
        poly([(hc[0] + 22, hc[1] + 4), (hc[0] + 50, hc[1] + 12), (hc[0] + 24, hc[1] + 12)], beak_c)
    else:
        poly([(hc[0] + 22, hc[1] - 6), (hc[0] + 56, hc[1] + 2), (hc[0] + 22, hc[1] + 10)], beak_c)
    if spec.get("kind") == "rooster":   # the red comb and the wattle
        poly([(hc[0] - 18, hc[1] - 20), (hc[0] - 14, hc[1] - 44), (hc[0] - 4, hc[1] - 30), (hc[0] + 2, hc[1] - 50),
              (hc[0] + 10, hc[1] - 30), (hc[0] + 20, hc[1] - 42), (hc[0] + 22, hc[1] - 20)], (220, 40, 40))
        poly(closed_ellipse(hc[0] + 26, hc[1] + 22, 8, 13, 12), (220, 40, 40))
    S.dot(X((hc[0] + 8, hc[1] - 6)), 6, (250, 250, 250))
    S.dot(X((hc[0] + 10, hc[1] - 6)), 3.5, INK)
    anchors = dict(head_top=S.T(X((hc[0], hc[1] - 30))), head_center=S.T(X(hc)), mouth=S.T(X((hc[0] + 40, hc[1]))),
                   feet=S.T((0, 0)), hand_l=S.T(X(hc)), hand_r=S.T(X(hc)))
    return S.ops, anchors


def _face(S, X, hc, r, expr, speak, mouth_open, look=1.0):
    """Two big cartoon eyes and a mouth on a small head (the lizard, the mosquito): they talk like people."""
    for dx in (-0.38, 0.38):
        ec = (hc[0] + r * dx + r * 0.2 * look, hc[1] - r * 0.25)
        S.poly([X(q) for q in closed_ellipse(ec[0], ec[1], r * 0.32, r * 0.38, 16)], (252, 252, 250), INK, 3)
        if expr in ("sleepy", "happy", "laugh"):
            S.line([X(q) for q in ellipse_pts(ec[0], ec[1], r * 0.24, r * 0.16, 8, 200, 340)], 4, INK)
        else:
            S.dot(X((ec[0] + r * 0.1 * look, ec[1] + r * 0.05)), r * 0.15, INK)
        if expr in ("angry", "evil", "stare"):
            S.line([X((ec[0] - r * 0.3, ec[1] - r * 0.5)), X((ec[0] + r * 0.3, ec[1] - r * 0.36))], 4, INK)
    m = (hc[0] + r * 0.2 * look, hc[1] + r * 0.45)
    if speak:
        S.poly([X(q) for q in closed_ellipse(m[0], m[1], r * 0.25, r * (0.1 + 0.2 * max(0.4, mouth_open)), 12)],
               (120, 30, 40), INK, 3)
    elif expr in ("smile", "grin", "laugh", "smug", "evil", "sly"):
        S.line([X(q) for q in ellipse_pts(m[0], m[1] - r * 0.15, r * 0.3, r * 0.2, 10, 20, 160)], 4, INK)
    else:
        S.line([X((m[0] - r * 0.2, m[1])), X((m[0] + r * 0.2, m[1]))], 4, INK)


def _lizard(spec, action, at, t, x0, ground_y, k, dirn, moving, mouth_open, expr):
    """The house lizard, flat on the wall above the people, seen from the front: head up, legs splayed, the tail
    flicking; it scurries when it moves. `"floor": true` puts it down on the ground."""
    col = _col(spec, (196, 186, 150))
    dk = tuple(int(v * 0.75) for v in col)
    y_off = 0.0 if spec.get("floor") else WALL_Y
    S = Sketch(x0, ground_y + y_off * k, k * 1.25, 0, 0, 0, 0)
    D = dirn

    def X(p):
        return (p[0] * D, p[1])

    speak = action in ("speak", "bark", "talk") or mouth_open > 0.1
    run = 1.0 if moving else 0.0
    ph = t * 18 * run
    # the body runs left-right across the wall; the head is at +x
    tail_flick = 18 * math.sin(t * (9 if action in ("wag", "shock") else 2.5))
    tail = bezier((-60, -40), (-120, -40 + tail_flick), (-190, -60 - tail_flick * 0.6), 12)
    S.line([X(q) for q in tail], 18, INK)
    S.line([X(q) for q in tail], 11, col)
    for i, (lx, side) in enumerate(((-40, -1), (-40, 1), (34, -1), (34, 1))):
        sw = 12 * math.sin(ph + i * math.pi / 2) * run
        knee = (lx + sw + (10 if lx > 0 else -10), -40 + side * 34)
        foot = (lx + sw + (24 if lx > 0 else -24), -40 + side * 52)
        S.line([X((lx, -40)), X(knee), X(foot)], 9, dk)
        for f in (-1, 0, 1):
            S.dot(X((foot[0] + f * 6, foot[1] + side * 5)), 4, dk)
    S.poly([X(q) for q in closed_ellipse(-8, -40, 66, 22, 24)], col, INK, 4)
    for sx in (-40, -16, 8):
        S.dot(X((sx, -44)), 4, dk)
    hc = (68, -42)
    S.poly([X(q) for q in closed_ellipse(hc[0], hc[1], 34, 26, 20)], col, INK, 4)
    _face(S, X, hc, 30, expr, speak, mouth_open)
    anchors = dict(head_top=S.T(X((hc[0], hc[1] - 34))), head_center=S.T(X(hc)), mouth=S.T(X((hc[0] + 8, hc[1] + 12))),
                   feet=S.T((0, 0)), hand_l=S.T(X(hc)), hand_r=S.T(X(hc)))
    return S.ops, anchors


def _mosquito(spec, action, at, t, x0, ground_y, k, dirn, moving, mouth_open, expr):
    """The mosquito: a little striped body on long legs, wings a blur, a long needle nose, always wobbling in
    the air at head height (`"y"` in the spec moves the whole person spot, so it can buzz higher or lower)."""
    D = dirn
    seed = (hash(str(spec.get("name", ""))) % 7) * 0.7
    jx = 26 * math.sin(t * 3.1 + seed) + 10 * math.sin(t * 7.7)
    jy = 20 * math.sin(t * 2.3 + seed * 2) + 8 * math.sin(t * 11.0)
    S = Sketch(x0, ground_y + (HOVER_Y + jy) * k, k * 1.3, 0, jx, 0, 0)

    def X(p):
        return (p[0] * D, p[1])

    speak = action in ("speak", "bark", "talk") or mouth_open > 0.1
    body = (60, 56, 70)
    for side in (-1, 1):                # long thin legs dangling
        for lx in (-14, 0, 14):
            S.line([X((lx, 8)), X((lx + side * 22, 36)), X((lx + side * 30, 70))], 3, INK)
    flap = math.sin(t * 60)
    for side in (-1, 1):                # the wings: a pale blur
        S.poly([X(q) for q in closed_ellipse(-6 + side * 4, -26 - 12 * abs(flap), 34, 14, 14, -25 * side)],
               (210, 226, 240), (150, 160, 180), 2)
    S.poly([X(q) for q in closed_ellipse(-34, 6, 34, 15, 18, 10)], body, INK, 3)        # the striped belly
    for sx in (-52, -38, -24):
        S.line([X((sx, -6)), X((sx + 4, 18))], 4, (200, 196, 210))
    S.poly([X(q) for q in closed_ellipse(4, 0, 16, 14, 14)], body, INK, 3)
    hc = (28, -6)
    S.poly([X(q) for q in closed_ellipse(hc[0], hc[1], 20, 18, 16)], body, INK, 3)
    S.line([X((44, 0)), X((84, 10))], 4, INK)                                          # the needle
    _face(S, X, hc, 18, expr, speak, mouth_open)
    anchors = dict(head_top=S.T(X((hc[0], hc[1] - 22))), head_center=S.T(X(hc)), mouth=S.T(X((hc[0] + 6, hc[1] + 8))),
                   feet=S.T((0, 0)), hand_l=S.T(X(hc)), hand_r=S.T(X(hc)))
    return S.ops, anchors

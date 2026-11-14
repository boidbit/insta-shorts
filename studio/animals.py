"""Animals: dog, cat, cow, goat (four-legged rig), crow, parrot, rooster (bird rig), and two pests with faces:
the lizard on the wall and the mosquito buzzing round the heads (their own little rigs).
(A monkey uses the stickman rig: { "kind": "monkey" } so every human action works for it.)

Character spec:  { "kind": "dog", "color": [180, 130, 80], "x": 300, "facing": "right" }
Actions:         idle, walk / run (automatic while moving), sit, lie_down / sleep, jump, bark (= meow, moo,
                 caw, speak), wag, eat, fly (birds), peck (birds), shock
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


def _quad(spec, action, at, t, x0, ground_y, k, dirn, moving, running, mouth_open, expr):
    kind = spec.get("kind", "dog")
    P = QUAD.get(kind, QUAD["dog"])
    col = _col(spec, P["color"])
    dk = tuple(int(v * 0.72) for v in col)
    rx, ry, leg, hr = P["rx"], P["ry"], P["leg"], P["head"]
    S = Sketch(x0, ground_y, k, 0, 0, 0, 0)
    D = dirn

    def X(p):
        return (p[0] * D, p[1])

    def poly(pts, fill, outline=INK, w=6):
        S.poly([X(p) for p in pts], fill, outline, w)

    def line(pts, w, c=INK):
        S.line([X(p) for p in pts], w, c)

    sit = action == "sit"
    lie = action in ("lie_down", "lie", "sleep", "sleep_lie")
    speak = action in ("bark", "meow", "moo", "speak", "caw") or mouth_open > 0.1
    jump = action in ("jump", "shock")
    gait_f = 3.0 if running else 1.8
    ph = t * 2 * math.pi * gait_f if moving else 0.0
    lift = 0.0
    if jump:
        lift = -120 * abs(math.sin(math.pi * min(1.0, at / 0.45))) if at < 0.45 else 0.0
    if moving:
        lift -= 6 * abs(math.sin(ph))
    body_y = -(leg + ry * 0.5) + lift
    tilt = 0.0
    if sit:
        tilt = -24
    if lie:
        body_y = -ry * 0.95
    bc = (0.0, body_y)

    def B(p):                          # body-local -> local, with body tilt (sitting)
        a = math.radians(tilt)
        x, y = p
        return (bc[0] + x * math.cos(a) - y * math.sin(a), bc[1] + x * math.sin(a) + y * math.cos(a))

    # legs: back pair at -rx*0.6, front pair at +rx*0.6 (forward = +x)
    legs = []
    for i, (hx, off) in enumerate(((-rx * 0.62, 0.0), (-rx * 0.48, math.pi), (rx * 0.52, math.pi), (rx * 0.66, 0.0))):
        top = B((hx, ry * 0.4))
        if lie:
            foot = (top[0] + (40 if hx > 0 else -30), 0.0)
        elif sit and hx < 0:
            foot = (top[0] + 50, 0.0)
        else:
            sw = 28 * math.sin(ph + off) if moving else 0.0
            foot = (top[0] + sw, 0.0 + lift if jump else 0.0)
            if jump:
                foot = (top[0] + (20 if hx > 0 else -20), top[1] + leg * 0.75)
        knee = ((top[0] + foot[0]) / 2 + (8 if hx > 0 else -8), (top[1] + foot[1]) / 2)
        legs.append((top, knee, foot, i))
    for top, knee, foot, i in legs[::-1]:
        if i in (1, 2):
            line([top, knee, foot], 15, dk)
    # tail
    wag = math.sin(t * (14 if action == "wag" else 5)) * (22 if action in ("wag", "idle") else 8)
    root = B((-rx * 0.95, -ry * 0.2))
    if P["tail"] == "up":
        line(bezier(root, (root[0] - 60, root[1] - 30 + wag * 0.5), (root[0] - 70 + wag, root[1] - 110)), 13, dk)
    elif P["tail"] == "stub":
        line([root, (root[0] - 34, root[1] - 40 + wag * 0.4)], 12, dk)
    elif P["tail"] == "curl":
        line(bezier(root, (root[0] - 90, root[1] + 10), (root[0] - 80 + wag, root[1] - 120)) +
             bezier((root[0] - 80 + wag, root[1] - 120), (root[0] - 60 + wag, root[1] - 170), (root[0] - 30 + wag, root[1] - 150))[1:], 11, col)
    else:
        tip = (root[0] - 30 + wag * 0.4, root[1] + 150)
        line([root, tip], 7, dk)
        poly(closed_ellipse(tip[0], tip[1] + 10, 12, 20, 12), (60, 50, 44), INK, 3)
    # body
    poly([B(q) for q in closed_ellipse(0, 0, rx, ry, 40)], col)
    if kind == "cow":
        for (sx, sy, r) in ((-80, -20, 46), (60, 30, 38), (130, -40, 30)):
            poly([B(q) for q in closed_ellipse(sx, sy, r, r * 0.8, 20)], (40, 40, 44), None)
        poly([B(q) for q in closed_ellipse(-40, ry * 0.85, 34, 20, 16)], (240, 170, 180), INK, 4)
    for top, knee, foot, i in legs:
        if i in (0, 3):
            line([top, knee, foot], 16, col if kind != "cow" else (236, 236, 232))
            S.dot(X(foot), 10, INK)
    # head
    if lie:
        hcen = B((rx + hr * 0.5, -ry * 0.1))
    elif sit:
        hcen = B((rx * 0.95, -ry - hr * 0.6))
    else:
        hcen = B((rx + hr * 0.45, -ry * 0.9))
    bob = 6 * math.sin(ph * 2) if moving else 2 * math.sin(t * 2)
    hcen = (hcen[0], hcen[1] + bob)
    hx_, hy_ = hcen
    if kind == "dog":
        poly(closed_ellipse(hx_ - hr * 0.45, hy_ - hr * 0.15, hr * 0.32, hr * 0.7, 16, 18), dk)       # ear
    elif kind == "cat":
        for ex in (-0.5, 0.35):
            poly([(hx_ + hr * (ex - 0.25), hy_ - hr * 0.6), (hx_ + hr * (ex + 0.05), hy_ - hr * 1.35),
                  (hx_ + hr * (ex + 0.35), hy_ - hr * 0.6)], col)
    elif kind == "buffalo":             # the bhains: heavy horns curving back, droopy ears
        for ex in (-0.5, 0.25):
            line(bezier((hx_ + hr * ex, hy_ - hr * 0.75), (hx_ + hr * (ex - 0.9), hy_ - hr * 1.5),
                        (hx_ + hr * (ex - 1.1), hy_ - hr * 0.6), 10), 15, (120, 116, 112))
        poly(closed_ellipse(hx_ - hr * 0.95, hy_ - hr * 0.1, hr * 0.46, hr * 0.2, 14, 20), dk)
    elif kind == "cow":
        for ex in (-0.55, 0.45):
            line([(hx_ + hr * ex, hy_ - hr * 0.8), (hx_ + hr * (ex + 0.1), hy_ - hr * 1.3)], 12, (230, 220, 190))
        poly(closed_ellipse(hx_ - hr * 0.9, hy_ - hr * 0.4, hr * 0.42, hr * 0.2, 14, -20), col)
    if kind == "goat":                  # two curved horns and floppy ears
        for ex in (-0.45, 0.05):
            line(bezier((hx_ + hr * ex, hy_ - hr * 0.7), (hx_ + hr * (ex - 0.6), hy_ - hr * 1.7),
                        (hx_ + hr * (ex - 1.0), hy_ - hr * 1.0), 10), 11, (170, 150, 118))
        poly(closed_ellipse(hx_ - hr * 0.7, hy_ + hr * 0.05, hr * 0.42, hr * 0.17, 14, 30), dk)
    poly(closed_ellipse(hx_, hy_, hr, hr * 0.92, 32), col)
    if kind == "goat":                  # the beard under the chin, chewing all the time
        chew = 4 * math.sin(t * 9)
        poly([(hx_ + hr * 0.45, hy_ + hr * 0.75), (hx_ + hr * 0.85, hy_ + hr * 0.7),
              (hx_ + hr * 0.62, hy_ + hr * 1.6 + chew)], (220, 214, 200))
    # snout + mouth
    sn = (hx_ + hr * 0.75, hy_ + hr * 0.22)
    snout_col = (236, 190, 190) if kind == "cow" else (128, 122, 128) if kind == "buffalo" else \
        tuple(min(255, v + 30) for v in col)
    poly(closed_ellipse(sn[0], sn[1], hr * 0.5, hr * 0.38, 20), snout_col)
    poly(closed_ellipse(sn[0] + hr * 0.38, sn[1] - hr * 0.12, hr * 0.13, hr * 0.1, 12), INK, None)
    if speak:
        poly(closed_ellipse(sn[0] + hr * 0.05, sn[1] + hr * 0.3, hr * 0.28, hr * (0.12 + 0.18 * max(0.4, mouth_open)), 16),
             (120, 30, 40))
    else:
        line([(sn[0] - hr * 0.2, sn[1] + hr * 0.28), (sn[0] + hr * 0.25, sn[1] + hr * 0.3)], 5)
    if kind == "cat":
        for dy in (-6, 6):
            line([(sn[0] + hr * 0.1, sn[1] + dy), (sn[0] + hr * 0.9, sn[1] + dy * 2.4)], 3)
    # eye
    ex, ey = hx_ + hr * 0.25, hy_ - hr * 0.22
    if kind == "buffalo":               # a dark face: the eye sits in a white
        poly(closed_ellipse(ex, ey, hr * 0.2, hr * 0.17, 16), (246, 244, 240), INK, 3)
    if lie and action in ("sleep", "sleep_lie") or expr in ("sleepy", "happy", "laugh"):
        line(ellipse_pts(ex, ey, hr * 0.16, hr * 0.1, 8, 200, 340), 5)
    elif expr in ("angry",):
        S.dot(X((ex, ey)), hr * 0.11, INK)
        line([(ex - hr * 0.22, ey - hr * 0.3), (ex + hr * 0.15, ey - hr * 0.16)], 6)
    else:
        S.dot(X((ex, ey)), hr * 0.12, INK)
    head_top = X((hx_, hy_ - hr * 1.1))
    anchors = dict(head_top=S.T(head_top), head_center=S.T(X(hcen)), mouth=S.T(X(sn)),
                   feet=S.T((0, 0)), hand_l=S.T(X(sn)), hand_r=S.T(X(sn)))
    return S.ops, anchors


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

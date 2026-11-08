"""Animation library. Each action returns pose overrides for time t (seconds since
the action started). Angle convention: 0 = straight down, +90 = screen-right, 180 = up.
L = screen-left limb, R = screen-right limb."""
import math

from .util import clamp, ease_in, ease_out, ease_out_back

sin, cos, pi = math.sin, math.cos, math.pi

# ------------------------------------------------------------------ rig geometry + IK helpers
# Body coordinates: hips at y=0, up is negative. Many poses are written in a reference body
# (shoulders (+-52, -275), head centre (0, -414), feet at +330) and _remap() converts those
# targets to this rig, so hand-to-mouth / hands-on-hips land on the real character.
from .characters import HEAD_RY, HEAD_SCALE, LA, NECK_H, SH, TH, TORSO_H, UA   # noqa: E402

SHOULDER = {"L": (-56.0, -TORSO_H + 22.0), "R": (56.0, -TORSO_H + 22.0)}
HIP = {"L": (-32.0, 0.0), "R": (32.0, 0.0)}
_HC = -(TORSO_H - 4.0) - (NECK_H + HEAD_RY * 0.8 * HEAD_SCALE)     # head centre y
_HTOP = _HC - HEAD_RY * HEAD_SCALE
TH_, SH_ = TH, SH


def _remap(p):
    """Reference-body point -> this rig's body coordinates."""
    x, y = p
    sy = SHOULDER["R"][1]
    if y >= 0:
        y2 = y * (TH + SH) / 330.0
    elif y >= -275:
        y2 = y * (-sy) / 275.0
    elif y >= -414:
        y2 = sy + (y + 275) / -139.0 * (_HC - sy)
    else:
        y2 = _HC + (y + 414) / -100.0 * (_HTOP - _HC)
    x2 = x * (0.9 if y < -300 else 1.06)
    return (x2, y2)


def _ik(base, target, l1, l2, prefer):
    """Two-bone IK in the picture plane -> (upper angle, lower angle, upper scale, lower scale).
    The elbow/knee bulges toward `prefer`; when that becomes ambiguous the limb straightens and
    foreshortens instead of snapping to the other side, and near the shoulder the elbow keeps to
    its preferred direction, so motion stays continuous and the hand still reaches the target."""
    dx, dy = target[0] - base[0], target[1] - base[1]
    dist = math.hypot(dx, dy)
    if dist < 1e-6:
        dx, dy, dist = 0.0, 1.0, 1.0
    ux, uy = dx / dist, dy / dist
    nx, ny = -uy, ux
    D = max(abs(l1 - l2) + 1e-3, min(l1 + l2 - 1e-3, dist))
    a = (l1 * l1 - l2 * l2 + D * D) / (2 * D)
    h = math.sqrt(max(0.0, l1 * l1 - a * a))
    pl = math.hypot(prefer[0], prefer[1]) or 1.0
    sgn = (prefer[0] * nx + prefer[1] * ny) / pl
    f = clamp(abs(sgn) / 0.35)
    f = f * f * (3 - 2 * f)
    he = h * f * (1 if sgn >= 0 else -1)
    ex, ey = base[0] + ux * a + nx * he, base[1] + uy * a + ny * he
    hx, hy = base[0] + ux * D, base[1] + uy * D
    near = clamp((0.62 * (l1 + l2) - D) / (0.62 * (l1 + l2)))
    if near > 0:
        ex += (base[0] + prefer[0] / pl * l1 * 0.9 - ex) * near
        ey += (base[1] + prefer[1] / pl * l1 * 0.9 - ey) * near
    a1 = math.degrees(math.atan2(ex - base[0], ey - base[1]))
    a2 = math.degrees(math.atan2(hx - ex, hy - ey))
    return a1, a2, math.hypot(ex - base[0], ey - base[1]) / l1, math.hypot(hx - ex, hy - ey) / l2


def hand(side, target, prefer=None, k=1.0):
    """Arm angles that put the hand at `target` (reference-body coords). k = arm stretch (= arm_k)."""
    if prefer is None:
        prefer = (1.0 if side == "R" else -1.0, 0.5)
    a1, a2, k1, k2 = _ik(SHOULDER[side], _remap(target), UA * k, LA * k, prefer)
    p_ = "ra" if side == "R" else "la"
    return {p_ + "1": a1, p_ + "2": a2, p_ + "_k1": k1, p_ + "_k2": k2}


def foot(side, target, prefer=None):
    if prefer is None:
        prefer = (1.0 if side == "R" else -1.0, 0.0)
    a1, a2, _k1, _k2 = _ik(HIP[side], _remap(target), TH, SH, prefer)
    k_ = "rl" if side == "R" else "ll"
    return {k_ + "1": a1, k_ + "2": a2}


def _lerp2(p, q, e):
    return (p[0] + (q[0] - p[0]) * e, p[1] + (q[1] - p[1]) * e)


def _P(*parts, **kw):
    out = {}
    for p_ in parts:
        out.update(p_)
    out.update(kw)
    return out


def _stance(spread=1.0):
    return dict(ll1=-9 * spread, ll2=-3 * spread, rl1=9 * spread, rl2=3 * spread)


def idle(t, sp, I, ph, o):
    # standing still: only slow breathing in the arms and a tiny head drift, no body sway
    w = 2 * pi * 0.35 * sp
    d = _stance()
    d.update(tilt=0.2 * sin(w * t + ph) * I, head_tilt=1.2 * sin(w * 0.6 * t + ph) * I,
             la1=-14 + 0.8 * sin(w * t + ph), ra1=14 - 0.8 * sin(w * t + ph))
    return d


def talk(t, sp, I, ph, o):
    # calm speaking: small head nods and one hand gesturing, the body stays planted
    w = 2 * pi * 0.9 * sp
    d = _stance()
    d.update(
        tilt=0.4 * sin(w * 0.4 * t + ph) * I,
        head_tilt=2.2 * sin(w * t + ph) * I,
        ra1=30 + 10 * sin(w * 0.6 * t + ph) * I, ra2=58 + 16 * sin(w * 0.6 * t + 1.2 + ph) * I,
        la1=-15,
    )
    return d


def _beat(o, sp):
    """Beats per second: the music's tempo (the renderer passes it as _bpm) times the event speed."""
    return o.get("_bpm", 90) / 60.0 * sp


def dance(t, sp, I, ph, o):
    style = o.get("style", "pump")
    w = 2 * pi * _beat(o, sp)
    c = sin(w * t + ph)
    side = sin(w * 0.5 * t + ph)
    spread = 22 + 8 * c * I
    d = dict(ll1=-spread, ll2=-spread + 10, rl1=spread, rl2=spread - 10,
             tilt=7 * side * I, head_tilt=-9 * side * I + 3 * c, look_x=0.5 * side)
    if style == "pump":      # hands up beside the head, pumping
        d.update(la1=-98 + 22 * sin(w * t + ph) * I, la2=-168 + 18 * sin(w * t + ph) * I,
                 ra1=98 - 22 * sin(w * t + ph) * I, ra2=168 - 18 * sin(w * t + ph) * I)
    elif style == "swing":   # arms swing across the body
        d.update(la1=-40 + 38 * sin(w * 0.5 * t + ph) * I, la2=10 + 40 * sin(w * 0.5 * t + ph) * I,
                 ra1=40 + 38 * sin(w * 0.5 * t + ph + pi) * I, ra2=-10 + 40 * sin(w * 0.5 * t + ph + pi) * I)
    elif style == "cheer":   # arms straight up
        d.update(la1=-150 + 16 * c * I, la2=-168 + 14 * c * I,
                 ra1=150 - 16 * c * I, ra2=168 - 14 * c * I)
    elif style == "disco":   # point up / down alternately
        a = sin(w * 0.5 * t + ph)
        d.update(ra1=100 + 30 * a, ra2=125 + 25 * a, finger="R",
                 la1=-40 - 20 * a, la2=-20 - 10 * a)
    return d


def dance2(t, sp, I, ph, o):
    o = dict(o)
    o["style"] = "swing"
    return dance(t, sp, I, ph, o)


def dance3(t, sp, I, ph, o):
    o = dict(o)
    o["style"] = "cheer"
    return dance(t, sp, I, ph, o)


def disco(t, sp, I, ph, o):
    o = dict(o)
    o["style"] = "disco"
    return dance(t, sp, I, ph, o)


def point(t, sp, I, ph, o):
    target = o.get("point", "right")
    ext = ease_out(t / 0.18)
    jab = 1 + 0.06 * sin(2 * pi * 2 * t * sp)
    d = _stance()
    d.update(tilt=1.0 * sin(2 * pi * 0.8 * t), lift=-2 * abs(sin(2 * pi * 1.2 * t)))
    if target in ("left", "up_left"):
        base = -100 if target == "left" else -140
        d.update(la1=-14 + (base + 14) * ext, la2=-8 + (base + 8) * ext * jab, finger="L",
                 ra1=40, ra2=-20, look_x=-0.8)
    elif target == "up":
        d.update(ra1=14 + 150 * ext, ra2=8 + 164 * ext, finger="R", look_y=-0.6)
    elif target == "down":
        d.update(ra1=14 + 20 * ext, ra2=8 + 22 * ext, finger="R", look_y=0.8)
    else:
        base = 100 if target == "right" else 140
        d.update(ra1=14 + (base - 14) * ext, ra2=8 + (base - 8) * ext * jab, finger="R",
                 la1=-40, la2=20, look_x=0.8)
    return d


def _settle(t, after, rate=0.6, floor=0.25):
    """1 until `after` seconds, then fades towards `floor`: reactions calm down instead of looping forever."""
    return 1.0 if t < after else max(floor, 1.0 - (t - after) * rate)


def laugh(t, sp, I, ph, o):
    w = 2 * pi * 4.5 * sp
    k = I * _settle(t, 1.8)
    d = _stance(1.6)
    d.update(la1=-40, la2=48, ra1=40, ra2=-48,
             tilt=3 * sin(w * 0.5 * t) * k, head_tilt=-11 + 6 * sin(w * t) * k,
             lift=-9 * abs(sin(w * t)) * k, look_y=-0.5)
    return d


def shock(t, sp, I, ph, o):
    """Startled: a small hop and a jolt back, hands fly to the cheeks and tremble. A held prop
    (phone...) stays in its hand at chest height, as if the character is staring at it."""
    jolt = sin(pi * clamp(t / 0.28)) if t < 0.28 else 0.0
    up = ease_out(clamp(t / 0.16))
    lean = o.get("lean", -1)
    trem = 2.5 * I * sin(2 * pi * 13 * t) * math.exp(-max(0.0, t - 0.3) * 1.2) if t > 0.25 else 0.0
    held = bool(o.get("_prop"))
    cheek = 70 + 3 * sin(2 * pi * 9 * t) * (1 if t > 0.25 else 0)
    L = hand("L", _lerp2((-80, -110), (-cheek, -358), up), (-1, 0.8))
    if held:
        R = hand("R", _lerp2((80, -110), (70, -236), up), (1, 1))
    else:
        R = hand("R", _lerp2((80, -110), (cheek, -358), up), (1, 0.8))
    d = _stance(1.25)
    d.update(L)
    d.update(R)
    d.update(lift=-38 * jolt * I, tilt=lean * 7 * ease_out(t / 0.2), shift=trem, head_tilt=-lean * 4 * up,
             look_y=0.45 if held else -0.1, arms_front=up > 0.5)
    return d


def jump(t, sp, I, ph, o):
    w = 2 * pi * 1.1 * sp
    h = abs(sin(w * t / 2)) * 150 * I
    d = _stance(1.2)
    d.update(lift=-h, la1=-150, la2=-170, ra1=150, ra2=170, tilt=3 * sin(w * t / 2))
    return d


def wave(t, sp, I, ph, o):
    d = _stance()
    d.update(ra1=132, ra2=170 + 24 * sin(2 * pi * 2.4 * t * sp), tilt=1.5 * sin(2 * pi * 0.8 * t),
             head_tilt=3 * sin(2 * pi * 1.2 * t))
    return d


def clap(t, sp, I, ph, o):
    a = 95 + 14 * sin(2 * pi * 3.2 * t * sp)
    d = _stance()
    d.update(la1=-40, la2=a, ra1=40, ra2=-a, lift=-4 * abs(sin(2 * pi * 3.2 * t * sp)))
    return d


def cry(t, sp, I, ph, o):
    w = 2 * pi * 3.2 * sp
    d = _stance()
    d.update(la1=-60, la2=-168 + 6 * sin(w * t), ra1=60, ra2=168 - 6 * sin(w * t),
             head_tilt=9 * sin(w * 0.5 * t), lift=-5 * abs(sin(w * t)) * I, tilt=2 * sin(w * 0.5 * t))
    return d


def fall(t, sp, I, ph, o):
    dr = o.get("dir") or (1 if o.get("_x", 540) <= 540 else -1)   # fall toward screen centre by default
    p = clamp(t / 0.7)
    ang = 88 * ease_in(p)
    bounce = 0.0
    if t > 0.7:
        tt = t - 0.7
        bounce = abs(sin(2 * pi * 2.2 * tt)) * 22 * math.exp(-4 * tt)
    d = _stance(1.3)
    flail = (1 - p)
    d.update(tilt=dr * (ang - bounce * 0.1), lift=-bounce,
             la1=-100 * flail - 20, la2=-150 * flail - 10, ra1=100 * flail + 20, ra2=150 * flail + 10,
             head_tilt=-dr * 6 * p)
    return d


def walk(t, sp, I, ph, o):
    w = 2 * pi * 1.25 * sp
    s_ = sin(w * t + ph)
    c_ = cos(w * t + ph)
    d = dict(ll1=26 * s_, ll2=13 * s_ - 14 * max(0.0, c_),
             rl1=-26 * s_, rl2=-13 * s_ - 14 * max(0.0, -c_),
             la1=-12 - 26 * s_, la2=-8 - 16 * s_, ra1=12 + 26 * s_, ra2=8 + 16 * s_,
             lift=-5 * abs(c_), tilt=2 * s_, head_tilt=1.0 * c_)
    if o.get("hands") == "pockets":
        d.update(la1=-22, la2=14, ra1=22, ra2=-14)
    return d


def salute(t, sp, I, ph, o):
    e = ease_out(t / 0.22)
    d = _stance()
    d.update(ra1=14 + 112 * e, ra2=8 + 214 * e, tilt=-1.5 * e, head_tilt=-2 * e)
    return d


def facepalm(t, sp, I, ph, o):
    e = ease_out(t / 0.3)
    d = _stance()
    d.update(ra1=14 + 91 * e, ra2=8 + 207 * e, head_tilt=8 * e, tilt=2 * e, look_y=0.8)
    return d


def shrug(t, sp, I, ph, o):
    e = ease_out(t / 0.25)
    d = _stance()
    d.update(la1=-14 - 56 * e, la2=-8 - 34 * e, ra1=14 + 56 * e, ra2=8 + 34 * e, head_tilt=-7 * e,
             lift=-6 * e * abs(sin(2 * pi * 1.0 * t)))
    return d


def sway(t, sp, I, ph, o):
    w = 2 * pi * 0.9 * sp
    d = _stance(1.3)
    d.update(tilt=6 * sin(w * t + ph) * I, head_tilt=-8 * sin(w * t + ph) * I,
             la1=-30 + 14 * sin(w * t + ph), la2=-10 + 10 * sin(w * t + ph),
             ra1=30 + 14 * sin(w * t + ph + pi), ra2=10 + 10 * sin(w * t + ph + pi))
    return d


def sleep(t, sp, I, ph, o):
    d = _stance()
    d.update(head_tilt=22 + 2 * sin(2 * pi * 0.4 * t), tilt=3, la1=-8, ra1=8, lift=0)
    return d


# ------------------------------------------------------------------ desi dance pack
def naagin(t, sp, I, ph, o):
    # shaadi wala naagin: one hand a hood over the head, the other the tail at the waist, body slithering low
    w = 2 * pi * _beat(o, sp) * 0.5
    s = sin(w * t + ph)
    return dict(ll1=-26, ll2=14, rl1=26, rl2=-14,              # knees bent: the body sits lower
                tilt=9 * s * I, shift=14 * sin(w * t + ph + 0.8) * I, head_tilt=-12 * s * I,
                ra1=168 - 6 * s, ra2=-130 + 8 * s, arms_front=True,    # hand on the forehead = the hood
                la1=-35, la2=55 + 15 * s, look_x=0.4 * s)


def bhangra(t, sp, I, ph, o):
    # one arm up and one out, swapping every beat, a hop with the knee kicking out, shoulders up
    b = _beat(o, sp) * t + ph / pi
    k = 0.5 + 0.5 * cos(pi * b)            # 1: right arm up, 0: left arm up
    hop = abs(sin(pi * b))
    return dict(ra1=95 + 55 * k, ra2=120 + 55 * k, la1=-95 - 55 * (1 - k), la2=-120 - 55 * (1 - k),
                rl1=9 + 50 * k * hop * I, rl2=3 - 10 * k * hop, ll1=-9 - 50 * (1 - k) * hop * I,
                ll2=-3 + 10 * (1 - k) * hop, lift=-14 * hop * I, tilt=4 * (2 * k - 1) * I,
                head_tilt=-5 * (2 * k - 1), look_y=-0.3)


def aeroplane(t, sp, I, ph, o):
    # uncle special: arms out like wings, banking left and right across the floor
    w = 2 * pi * _beat(o, sp) * 0.25
    s = sin(w * t + ph)
    step = abs(sin(pi * _beat(o, sp) * t + ph))
    d = _stance(1.3)
    d.update(la1=-92 - 4 * s, la2=-92 - 4 * s, ra1=92 - 4 * s, ra2=92 - 4 * s,
             tilt=14 * s * I, shift=20 * s * I, head_tilt=-6 * s, lift=-5 * step * I, look_y=-0.4)
    return d


def thumka(t, sp, I, ph, o):
    # hip pops to the side on every beat, one hand on the hip, the other twirling up high
    b = _beat(o, sp) * t + ph / pi
    hip = sin(pi * b)
    d = _stance()
    d.update(shift=18 * hip * I, tilt=-6 * hip * I, head_tilt=8 * hip,
             la1=-35, la2=45, ra1=155, ra2=178 + 25 * sin(2 * pi * b),
             rl1=9 + 10 * max(0.0, hip), ll1=-9 + 10 * min(0.0, hip))
    return d


def dance_walk(t, sp, I, ph, o):
    # strutting down the road: a step on every beat, grooving arms, a bounce on each step
    bps = _beat(o, sp)
    d = walk(t, bps / 2.0 / 1.25, I, ph, {})          # walk() does one step per half cycle
    p = sin(2 * pi * bps * t + ph)
    d.update(la1=-35 - 25 * p, la2=-120 - 30 * p, ra1=35 - 25 * p, ra2=120 - 30 * p,
             lift=d["lift"] - 8 * abs(sin(pi * bps * t)) * I, head_tilt=4 * sin(2 * pi * bps * t))
    return d


def kamar_dard(t, sp, I, ph, o):
    # starts dancing like a hero... then the back gives way: bent over, hand on the back, trembling
    if t < 0.8:
        return dance(t, sp, I, ph, dict(o, style="pump"))
    e = ease_out((t - 0.8) / 0.35)
    shake = 2.5 * sin(2 * pi * 9 * t) * math.exp(-(t - 0.8) * 1.5) * I
    return dict(ll1=-16, ll2=10, rl1=16, rl2=-10,          # knees buckle
                tilt=-10 * e, shift=shake, head_tilt=14 * e, look_y=0.7 * e,
                ra1=20 + 30 * e, ra2=-10 - 40 * e,          # hand on the lower back
                la1=-20 - 10 * e, la2=-5 + 20 * e)          # other hand on the knee


def sing(t, sp, I, ph, o):
    # mic singer: mic at the mouth, the other arm reaching out with feeling, slow sway
    w = 2 * pi * _beat(o, sp) * 0.25
    s = sin(w * t + ph)
    d = _stance()
    d.update(ra1=55, ra2=-145 + 4 * s, la1=-100 - 25 * s * I, la2=-140 - 15 * s * I,
             tilt=3 * s * I, head_tilt=-6 + 5 * s * I, look_y=-0.3, arms_front=True)    # mic in front of the face
    return d


SING_ACTIONS = {"sing", "gaana"}
# moves worth watching for a while: a script line with only one of these holds the cursor ~1.6 s
DANCES = {"dance", "dance2", "dance3", "disco", "sway", "naagin", "nagin", "bhangra", "aeroplane", "airplane",
          "thumka", "dance_walk", "kamar_dard", "fail"} | SING_ACTIONS

ACTIONS = {
    "idle": idle, "none": idle, "stand": idle,
    "talk": talk, "dance": dance, "dance2": dance2, "dance3": dance3, "disco": disco,
    "point": point, "laugh": laugh, "shock": shock, "jump": jump, "wave": wave, "salute": salute, "clap": clap,
    "cry": cry, "fall": fall, "walk": walk, "facepalm": facepalm, "shrug": shrug, "sway": sway,
    "sleep": sleep,
    "naagin": naagin, "nagin": naagin, "bhangra": bhangra, "aeroplane": aeroplane, "airplane": aeroplane,
    "thumka": thumka, "dance_walk": dance_walk, "kamar_dard": kamar_dard, "fail": kamar_dard,
    "sing": sing, "gaana": sing,
}


def pose_for(action, t, speed=1.0, intensity=1.0, phase=0.0, opts=None):
    fn = ACTIONS.get(action or "idle", idle)
    return fn(max(0.0, t), speed or 1.0, intensity if intensity is not None else 1.0, phase, opts or {})

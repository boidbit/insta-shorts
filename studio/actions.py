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
    # calm speaking: small head nods and one hand gesturing, the body stays planted. With a feeling on the face
    # (angry, happy, sad, scared, smug, thinking) the hands talk the way that feeling does: talk_emotion
    if o.get("_expr") in EMOTIONAL:
        return talk_emotion(t, sp, I, ph, o)
    w = 2 * pi * 0.9 * sp
    amp = min(1.0, max(0.0, o.get("_amp", 0.5)))     # loud syllables get a slightly bigger gesture
    d = _stance()
    d.update(
        tilt=0.4 * sin(w * 0.4 * t + ph) * I,
        head_tilt=2.2 * sin(w * t + ph) * I,
        ra1=30 + 10 * sin(w * 0.6 * t + ph) * I + 8 * (amp - 0.5), ra2=58 + 16 * sin(w * 0.6 * t + 1.2 + ph) * I
        + 14 * (amp - 0.5),
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


# =====================================================================================
# Extended library (ported from the other branch). Poses are written facing right and mirrored
# for d = -1; the lead hand is the screen-right (R) hand.
# =====================================================================================
def _n(t, ph=0.0):
    """Smooth pseudo-noise in -1..1 (sum of incommensurate sines): organic, never repeats exactly."""
    return (sin(t * 0.73 + ph) * 0.5 + sin(t * 1.37 + ph * 2.1) * 0.3 + sin(t * 2.91 + ph * 3.7) * 0.2)


ANGRY = {"angry", "shout", "determined", "disgust", "stare"}


HAPPY = {"smile", "grin", "laugh", "lol", "excited", "love", "wink", "blush", "drool", "money_eyes"}


SAD = {"sad", "cry", "hurt", "bored", "sleepy", "yawn"}


SCARED = {"scared", "nervous", "shock", "surprised", "cringe", "dizzy", "embarrassed"}


COOL = {"smug", "sly", "proud", "evil", "kiss", "side_eye", "eye_roll"}


THINK = {"think", "confused", "shh"}


def _hinge(theta, stance=3.0):
    """Bend forward at the hips by `theta` degrees with the legs staying vertical and the feet planted."""
    r = math.radians(theta)
    leg = TH_ + SH_
    return dict(tilt=theta, ll1=theta - stance, ll2=theta - stance * 0.4, rl1=theta + stance, rl2=theta + stance * 0.4,
                dx=-(leg * math.sin(r) * math.cos(r) + 12 * math.sin(r)),
                lift=-12 - leg * math.sin(r) ** 2 + 12 * math.cos(r) + 12)


_SWAP = {"la1": "ra1", "la2": "ra2", "ra1": "la1", "ra2": "la2",
         "ll1": "rl1", "ll2": "rl2", "rl1": "ll1", "rl2": "ll2"}


_NEG = {"tilt", "shift", "head_tilt", "look_x", "dx", "head_dx", "head_facing"}


_SWAPK = {"la_k1": "ra_k1", "la_k2": "ra_k2", "ra_k1": "la_k1", "ra_k2": "la_k2"}


_LR = {"L": "R", "R": "L"}


def _side(d, pose):
    """Mirror a right-facing pose for d = -1."""
    if d >= 0:
        return pose
    out = {}
    for k, v in pose.items():
        if k in _SWAP:
            out[_SWAP[k]] = -v
        elif k in _SWAPK:
            out[_SWAPK[k]] = v
        elif k in _NEG and isinstance(v, (int, float)):
            out[k] = -v
        elif k in ("finger", "thumb", "prop_hand"):
            out[k] = _LR.get(v, v)
        elif k == "props":
            out[k] = [(nm, _LR.get(h, h)) for nm, h in v]
        else:
            out[k] = v
    return out


def _d(o):
    v = o.get("_dir", 1)
    if v in ("left", -1) or (isinstance(v, (int, float)) and v < 0):
        return -1
    return 1


def _mix(p1, p2, w):
    """Blend two poses (angles the short way round)."""
    w = clamp(w)
    w = w * w * (3 - 2 * w)
    out = dict(p2 if w >= 0.5 else p1)
    for k in set(p1) | set(p2):
        a, b = p1.get(k), p2.get(k)
        if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
            if k in ("la1", "la2", "ra1", "ra2", "ll1", "ll2", "rl1", "rl2", "tilt", "head_tilt"):
                out[k] = a + (((b - a + 180) % 360) - 180) * w
            else:
                out[k] = a + (b - a) * w
    return out


def _once(t, t0, dur):
    """0..1 progress of a sub-move that starts at t0 and lasts dur."""
    return clamp((t - t0) / dur)


def _gait(t, freq, thigh, knee, ph=0.0):
    """Side-view leg cycle. Legs swing in the screen plane (forward = right)."""
    w = 2 * pi * freq
    a = w * t + ph
    out = {}
    for k, off in (("ll", 0.0), ("rl", pi)):
        s_ = sin(a + off)
        c_ = cos(a + off)
        th = thigh * s_
        out[k + "1"] = th
        out[k + "2"] = th - knee * max(0.0, c_)        # knee bends while the leg swings forward
    return out


# ------------------------------------------------------------------ movement


def run(t, sp, I, ph, o):
    d = _d(o)
    w = 2 * pi * 2.1 * sp
    a = w * t + ph
    legs = _gait(t, 2.1 * sp, 36 * I, 62, ph)
    ua_l, ua_r = -38 * sin(a + pi), -38 * sin(a)
    pose = _P(legs, la1=ua_l, la2=ua_l + 100, ra1=ua_r, ra2=ua_r + 100,
              lift=-14 * abs(cos(a)), tilt=9 * I, head_tilt=-4, look_x=0.7)
    return _side(d, pose)


def jog(t, sp, I, ph, o):
    return run(t, sp * 0.7, I * 0.65, ph, o)


def sneak(t, sp, I, ph, o):
    d = _d(o)
    legs = _gait(t, 0.85 * sp, 26, 60, ph)
    bob = sin(2 * pi * 0.85 * sp * t + ph)
    pose = _P(legs, hand("R", (100, -300 + 8 * bob), (1, 1)), hand("L", (70, -306 - 8 * bob), (0, 1)),
              tilt=6, lift=-4 * abs(bob), look_x=0.9, head_dx=6)
    return _side(d, pose)


def limp(t, sp, I, ph, o):
    d = _d(o)
    w = 2 * pi * 0.9 * sp
    s_ = sin(w * t + ph)
    pose = dict(ll1=6 * s_, ll2=6 * s_, rl1=-24 * s_, rl2=-24 * s_ - 18 * max(0, cos(w * t + ph)),
                tilt=7 * s_, lift=-8 * max(0, s_), la1=-18, la2=-10, ra1=20 + 10 * s_, ra2=12,
                head_tilt=-4 * s_)
    return _side(d, pose)


def crouch(t, sp, I, ph, o):
    breathe = 3 * sin(2 * pi * 0.6 * t + ph)
    return _P(dict(ll1=-58, ll2=12, rl1=58, rl2=-12), hand("R", (96, -40)), hand("L", (-96, -40)),
              head_dy=breathe * 0.5)


def hide(t, sp, I, ph, o):
    sh = 2.5 * sin(2 * pi * 11 * t) * I
    return _P(dict(ll1=-58, ll2=12, rl1=58, rl2=-12), hand("R", (70, -530), (1, -0.2), 1.15),
              hand("L", (-70, -530), (-1, -0.2), 1.15), dict(arm_k=1.15), shift=sh, look_x=0.4 * sin(2 * pi * 0.4 * t), face="scared")


def peek(t, sp, I, ph, o):
    d = _d(o)
    e = ease_out(t / 0.45)
    pose = _P(_hinge(24 * e), hand("R", (96, -300), (1, 1)), head_tilt=9 * e, look_x=1.0, head_dx=10 * e)
    return _side(d, pose)


def sit(t, sp, I, ph, o):
    """Sitting on a chair / bench / sofa. Front view if the character faces front, else side view."""
    breathe = 2 * sin(2 * pi * 0.35 * t + ph)
    if o.get("_facing", "front") == "front":
        return _P(dict(ll1=-26, ll2=-4, rl1=26, rl2=4, th_k=0.36), hand("R", (78, 4)), hand("L", (-78, 4)),
                  head_dy=breathe)
    d = _d(o)
    pose = _P(dict(rl1=86, rl2=0, ll1=80, ll2=-4), hand("R", (96, -18), (0, 1)), hand("L", (76, -8), (0, 1)),
              tilt=-3, head_dy=breathe)
    return _side(d, pose)


def sit_floor(t, sp, I, ph, o):
    breathe = 2 * sin(2 * pi * 0.35 * t + ph)
    return _P(dict(ll1=-82, ll2=72, rl1=82, rl2=-72), hand("R", (104, -24)), hand("L", (-104, -24)),
              head_dy=breathe)


def lie_down(t, sp, I, ph, o):
    d = _d(o)
    pose = dict(tilt=88, la1=-6, la2=-4, ra1=6, ra2=4, ll1=-3, ll2=-2, rl1=3, rl2=2,
                head_tilt=-4, lift=-62 - 1.5 * sin(2 * pi * 0.3 * t))
    return _side(d, pose)


def sleep_lie(t, sp, I, ph, o):
    p = lie_down(t, sp, I, ph, o)
    p["face"] = "sleepy"
    return p


def rofl(t, sp, I, ph, o):
    d = _d(o)
    pose = dict(tilt=84 + 7 * sin(2 * pi * 3 * t), la1=-70, la2=40, ra1=70, ra2=-40,
                ll1=-20 + 18 * sin(2 * pi * 3 * t), rl1=20 - 18 * sin(2 * pi * 3 * t), face="lol")
    return _side(d, pose)


def slip(t, sp, I, ph, o):
    d = _d(o)
    kick = sin(pi * _once(t, 0, 0.5))
    p = _once(t, 0.08, 0.5)
    bounce = abs(sin(2 * pi * 2.2 * (t - 0.6))) * 20 * math.exp(-4 * (t - 0.6)) if t > 0.6 else 0
    flail = 1 - p
    pose = dict(tilt=-86 * ease_in(p), lift=-bounce, rl1=9 + 85 * kick, rl2=9 + 70 * kick,
                ll1=-9 + 35 * kick, ll2=-3 + 30 * kick,
                la1=-110 * flail - 20, la2=-160 * flail, ra1=110 * flail + 20, ra2=160 * flail,
                face="shock" if t < 0.7 else "hurt")
    return _side(d, pose)


def trip(t, sp, I, ph, o):
    d = _d(o)
    p = _once(t, 0.15, 0.6)
    bounce = abs(sin(2 * pi * 2.2 * (t - 0.75))) * 18 * math.exp(-4 * (t - 0.75)) if t > 0.75 else 0
    pose = _P(dict(tilt=86 * ease_in(p), lift=-bounce, ll1=-9 - 45 * sin(pi * _once(t, 0, 0.6)), ll2=-40 * p,
                   rl1=9, rl2=3), hand("R", (200, -240)), hand("L", (150, -260), (0, 1)),
              face="shock" if t < 0.8 else "hurt")
    return _side(d, pose)


def faint(t, sp, I, ph, o):
    d = _d(o)
    p = _once(t, 0.6, 0.9)
    wob = (1 - p) * sin(2 * pi * 1.4 * t)
    pose = dict(tilt=-86 * ease_in(p) + 4 * wob, head_tilt=10 * wob, la1=-10 - 30 * p, la2=-6,
                ra1=10 + 30 * p, ra2=6, face="dizzy")
    return _side(d, pose)


def get_up(t, sp, I, ph, o):
    d = _d(o)
    e = ease_out(_once(t, 0, 0.9))
    pose = dict(tilt=88 * (1 - e), la1=-14 - 50 * (1 - e), ra1=14 + 50 * (1 - e), ll1=-9, rl1=9)
    return _side(d, pose)


def wake_up(t, sp, I, ph, o):
    if t < 0.9:
        return get_up(t, sp, I, ph, o)
    return _mix(get_up(0.9, sp, I, ph, o), yawn(t - 0.9, sp, I, ph, o), (t - 0.9) / 0.3)


def turn_around(t, sp, I, ph, o):
    return _P(dict(ll1=-9, rl1=9), hide_face=True)


def spin(t, sp, I, ph, o):
    q = (t * 2.0 * sp) % 1.0
    face = [0, 1, None, -1][int(q * 4) % 4]
    pose = dict(ra1=88, ra2=92, la1=-88, la2=-92, lift=-6 * abs(sin(2 * pi * 2 * sp * t)))
    if face is None:
        pose["hide_face"] = True
    else:
        pose["head_facing"] = face
    return pose


def cartwheel(t, sp, I, ph, o):
    d = _d(o)
    p = _once(t, 0, 0.9 / max(0.2, sp))
    th = 360 * ease_in_out_(p)
    r = math.radians(th)
    c = TH_ + SH_                                # hip height when standing
    h = c + 168.0 * (1 - cos(r)) / 2             # hips rise while upside down so the hands reach the floor
    pose = dict(tilt=th, ra1=150, ra2=150, la1=-150, la2=-150, rl1=32, rl2=32, ll1=-32, ll2=-32,
                dx=-c * sin(r), lift=-h + c * cos(r))
    if p >= 1:
        pose = dict(ll1=-9, rl1=9)
    return _side(d, pose)


def ease_in_out_(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def moonwalk(t, sp, I, ph, o):
    d = _d(o)
    w = 2 * pi * 1.2 * sp
    s_ = sin(w * t + ph)
    a_ = max(0.0, s_)
    b_ = max(0.0, -s_)
    pose = dict(ll1=-14 * s_, ll2=-14 * s_ + 34 * a_, rl1=14 * s_, rl2=14 * s_ - 34 * b_,
                lift=-4 * abs(s_), la1=-20 - 10 * s_, ra1=20 - 10 * s_, tilt=-4, head_tilt=3 * s_)
    return _side(d, pose)


def climb(t, sp, I, ph, o):
    w = 2 * pi * 1.0 * sp
    s_ = sin(w * t + ph)
    up, mid = (110, -600), (110, -400)
    pose = _P(hand("R", _lerp2(mid, up, 0.5 + 0.5 * s_), (1, 0), 1.2),
              hand("L", _lerp2((-110, -400), (-110, -600), 0.5 - 0.5 * s_), (-1, 0), 1.2), dict(arm_k=1.2),
              dict(ll1=-30 * max(0, s_) - 6, ll2=20 * max(0, s_), rl1=30 * max(0, -s_) + 6, rl2=-20 * max(0, -s_)),
              face="determined")
    return pose


def jump_over(t, sp, I, ph, o):
    d = _d(o)
    p = _once(t, 0, 0.7)
    h = 230 * sin(pi * p) * I
    stand = _P(dict(ll1=-14, ll2=-4, rl1=14, rl2=4), hand("R", (80, -110)), hand("L", (-80, -110)))
    tuck = _P(dict(rl1=72, rl2=-14, ll1=58, ll2=-24), hand("R", (170, -420)), hand("L", (140, -440), (0, 1)), tilt=6)
    pose = _mix(stand, tuck, sin(pi * p) * 1.6)
    pose["lift"] = -h
    return _side(d, pose)


def slide(t, sp, I, ph, o):
    d = _d(o)
    pose = _P(dict(rl1=64, rl2=60, ll1=-34, ll2=64), hand("R", (-60, -470), (1, -1)), hand("L", (-150, -360)),
              tilt=-22, shift=2 * sin(2 * pi * 9 * t))
    return _side(d, pose)


def skid(t, sp, I, ph, o):
    d = _d(o)
    pose = dict(tilt=-14 + 3 * sin(2 * pi * 8 * t), rl1=30, rl2=24, ll1=-12, ll2=-6,
                ra1=150 + 20 * sin(2 * pi * 6 * t), ra2=170, la1=-140, la2=-160 + 20 * sin(2 * pi * 6 * t + 1),
                face="shock")
    return _side(d, pose)


# ------------------------------------------------------------------ head & small reactions


def nod(t, sp, I, ph, o):
    w = 2 * pi * 2.0 * sp
    k = max(0.0, sin(w * t)) * I
    return dict(look_y=0.7 * k, head_dy=10 * k, ll1=-9, rl1=9)


def shake_head(t, sp, I, ph, o):
    w = 2 * pi * 2.6 * sp
    s_ = sin(w * t) * I
    return dict(look_x=0.9 * s_, head_dx=7 * s_, head_facing=round(s_ * 0.8), ll1=-9, rl1=9)


def look_back(t, sp, I, ph, o):
    d = _d(o)
    e = ease_out(t / 0.25)
    return _side(d, dict(look_x=-1.0 * e, head_facing=-1 if e > 0.5 else 0, head_tilt=-4 * e, tilt=-2 * e,
                         ll1=-9, rl1=9))


def look_around(t, sp, I, ph, o):
    s_ = sin(2 * pi * 0.45 * sp * t + ph)
    return dict(look_x=s_, head_dx=6 * s_, head_facing=round(s_ * 0.9), look_y=-0.2, ll1=-9, rl1=9)


def look_up(t, sp, I, ph, o):
    return dict(look_y=-1.0, head_dy=-5, head_tilt=0, ll1=-9, rl1=9)


def look_down(t, sp, I, ph, o):
    return dict(look_y=1.0, head_dy=8, ll1=-9, rl1=9)


def scratch_head(t, sp, I, ph, o):
    d = _d(o)
    j = 6 * sin(2 * pi * 6 * t)
    return _side(d, _P(hand("R", (66 + j, -492), (1, -0.4)), face="confused", head_tilt=-4, ll1=-9, rl1=9))


def yawn(t, sp, I, ph, o):
    up = ease_out(_once(t, 0, 0.6)) * (1 - ease_in(_once(t, 2.0, 0.6)))
    pose = _P(hand("R", _lerp2((80, -110), (118, -600), up), (1, 0), 1.2),
              hand("L", _lerp2((-80, -110), (-118, -600), up), (-1, 0), 1.2),
              look_y=-0.6 * up, head_dy=-4 * up, ll1=-9, rl1=9, arm_k=1.2)
    if t < 2.4:
        pose["face"] = "yawn"
    return pose


def sneeze(t, sp, I, ph, o):
    d = _d(o)
    build = ease_out(_once(t, 0, 0.7))
    snap = sin(pi * _once(t, 0.7, 0.3))
    pose = _P(hand("R", _lerp2((80, -110), (22, -350), build * (1 - _once(t, 1.0, 0.4))), (1, 1)),
              head_dy=-7 * build * (1 - snap) + 12 * snap, look_y=-0.6 * build + 0.9 * snap,
              tilt=8 * snap, ll1=-9, rl1=9)
    if t < 1.2:
        pose["face"] = "sneeze"
    return _side(d, pose)


def scared(t, sp, I, ph, o):
    sh = 4 * sin(2 * pi * 13 * t) * I
    return _P(dict(ll1=5, ll2=-6, rl1=-5, rl2=6), hand("R", (20, -338), (1, 1)), hand("L", (-20, -338), (-1, 1)),
              shift=sh, face="scared")


def shiver(t, sp, I, ph, o):
    sh = 3 * sin(2 * pi * 14 * t) * I
    return _P(dict(ll1=4, ll2=-4, rl1=-4, rl2=4), hand("R", (-62, -236), (1, 0.6)), hand("L", (62, -230), (-1, 0.6)),
              shift=sh, head_dy=4)


def stomp(t, sp, I, ph, o):
    w = 2 * pi * 2.2 * sp
    s_ = sin(w * t)
    a_, b_ = max(0.0, s_), max(0.0, -s_)
    return _P(dict(ll1=-9 - 26 * a_, ll2=-3 + 30 * a_, rl1=9 + 26 * b_, rl2=3 - 30 * b_),
              hand("R", (112, -60)), hand("L", (-112, -60)),
              shift=3 * sin(w * 2 * t) * (1 - abs(s_)), face="angry")


def celebrate(t, sp, I, ph, o):
    w = 2 * pi * 1.3 * sp
    h = abs(sin(w * t / 2)) * 120 * I
    pump = sin(w * t)
    return _P(hand("R", (110, -610), (1, 0), 1.2), hand("L", (-150, -440 - 70 * pump), (-1, 0.4), 1.2),
              dict(ll1=-14, rl1=14), lift=-h, face="laugh", arm_k=1.2)


def fist_pump(t, sp, I, ph, o):
    d = _d(o)
    k = 0.5 + 0.5 * sin(2 * pi * 2.4 * sp * t)
    return _side(d, _P(hand("R", _lerp2((110, -380), (80, -580), k), (1, 0.4)), face="grin", ll1=-9, rl1=9))


def arms_crossed(t, sp, I, ph, o):
    return _P(hand("R", (-58, -222), (1, 0.7)), hand("L", (58, -212), (-1, 0.7)),
              head_tilt=1.5 * sin(2 * pi * 0.5 * t), ll1=-9, rl1=9)


def sulk(t, sp, I, ph, o):
    d = _d(o)
    return _side(d, _P(arms_crossed(t, sp, I, ph, o), head_dy=6, look_x=-0.9, look_y=0.3, face="sad"))


def cringe(t, sp, I, ph, o):
    return _P(hand("R", (30, -170), (1, 0.6)), hand("L", (-30, -170), (-1, 0.6)), dict(ll1=4, rl1=-4),
              tilt=-3, head_dy=8, shift=1.5 * sin(2 * pi * 10 * t), face="cringe")


def hands_on_hips(t, sp, I, ph, o):
    return _P(hand("R", (72, -92), (1, -0.3)), hand("L", (-72, -92), (-1, -0.3)), dict(ll1=-12, rl1=12),
              head_tilt=1.5 * sin(2 * pi * 0.5 * t))


def proud(t, sp, I, ph, o):
    return _P(hands_on_hips(t, sp, I, ph, o), look_y=-0.3, head_dy=-3, tilt=0, face="proud")


def think(t, sp, I, ph, o):
    d = _d(o)
    tap = 4 * sin(2 * pi * 1.5 * t)
    return _side(d, _P(hand("R", (24, -324 + tap), (1, 1)), hand("L", (46, -214), (-0.3, 1)),
                       look_y=-0.6, look_x=0.3, face="think", ll1=-9, rl1=9))


def listen(t, sp, I, ph, o):
    d = _d(o)
    return _side(d, _P(hand("R", (112, -410), (1, 0.3)), head_tilt=-8, look_x=-0.4, face="think", ll1=-9, rl1=9))


def shh(t, sp, I, ph, o):
    d = _d(o)
    return _side(d, _P(hand("R", (6, -352), (1, 1)), finger="R", face="shh", ll1=-9, rl1=9))


def point_self(t, sp, I, ph, o):
    d = _d(o)
    jab = 6 * sin(2 * pi * 2 * t)
    return _side(d, _P(hand("R", (18 + jab, -236), (1, 0.8)), finger="R", ll1=-9, rl1=9))


def thumbs_up(t, sp, I, ph, o):
    d = _d(o)
    return _side(d, _P(hand("R", (118, -330), (1, 1)), thumb="R", face="grin", ll1=-9, rl1=9))


def namaste(t, sp, I, ph, o):
    bow = 4 + 3 * sin(2 * pi * 0.4 * t)
    return _P(hand("R", (6, -248), (1, 1)), hand("L", (-6, -248), (-1, 1)), head_dy=bow, look_y=0.4,
              ll1=-6, rl1=6)


def bow(t, sp, I, ph, o):
    e = ease_out(_once(t, 0, 0.5)) * (1 - ease_in(_once(t, 1.4, 0.5)))
    if o.get("_facing", "front") == "front":
        return _P(hand("R", (8, -150), (1, 1)), hand("L", (-8, -150), (-1, 1)), head_dy=18 * e, look_y=0.9 * e,
                  ll1=-6, rl1=6)
    d = _d(o)
    return _side(d, _P(_hinge(38 * e), la1=38 * e - 4, la2=38 * e - 4, ra1=38 * e + 4, ra2=38 * e + 4))


def rub_hands(t, sp, I, ph, o):
    j = 8 * sin(2 * pi * 4 * t)
    return _P(hand("R", (12 + j, -236), (1, 1)), hand("L", (-12 + j, -236), (-1, 1)), face="evil", ll1=-9, rl1=9)


def flex(t, sp, I, ph, o):
    b = 6 * sin(2 * pi * 1.5 * t)
    return dict(ra1=90, ra2=180 - b, la1=-90, la2=-180 + b, ll1=-14, rl1=14, face="proud")


def stretch(t, sp, I, ph, o):
    s_ = sin(2 * pi * 0.4 * t)
    return _P(hand("R", (96, -620), (1, 0), 1.25), hand("L", (-96, -620), (-1, 0), 1.25), tilt=9 * s_,
              ll1=-12, rl1=12, arm_k=1.25)


def whisper(t, sp, I, ph, o):
    d = _d(o)
    e = ease_out(t / 0.35)
    return _side(d, _P(_hinge(14 * e), hand("R", (44, -344), (1, 0.7)), head_dx=8 * e, look_x=0.8))


def shy(t, sp, I, ph, o):
    d = _d(o)
    s_ = sin(2 * pi * 0.6 * t)
    return _side(d, _P(hand("R", (14, -112), (1, 1)), hand("L", (-14, -112), (-1, 1)),
                       dict(ll1=-9, rl1=9 + 10 * sin(2 * pi * 1.2 * t), rl2=3 + 14 * sin(2 * pi * 1.2 * t)),
                       tilt=4 * s_, head_dy=5, look_x=-0.6, look_y=0.5, face="shy"))


def dizzy(t, sp, I, ph, o):
    return dict(tilt=6 * sin(2 * pi * 0.8 * t), head_tilt=10 * sin(2 * pi * 1.1 * t + 1),
                shift=8 * sin(2 * pi * 0.8 * t + 0.5), ll1=-12 + 6 * sin(2 * pi * 0.8 * t), rl1=12,
                la1=-30, ra1=30, face="dizzy")


def hit_react(t, sp, I, ph, o):
    """Getting slapped / punched: head snaps away from the hitter (who is on the `_dir` side)."""
    d = _d(o)
    k = math.exp(-5 * t) * sin(pi * _once(t, 0, 0.12) + 0.0) if t < 0.12 else math.exp(-5 * (t - 0.12))
    pose = dict(tilt=-12 * k * I, head_tilt=-18 * k * I, head_dx=-10 * k, shift=-10 * k,
                la1=-30 * k - 14, ra1=30 * k + 14, ll1=-9, rl1=9, face="hurt" if t < 1.2 else None)
    return _side(d, pose)


# ------------------------------------------------------------------ everyday


def eat(t, sp, I, ph, o):
    d = _d(o)
    k = 0.5 - 0.5 * cos(2 * pi * 0.7 * sp * t)
    near = k > 0.8
    pose = _P(hand("L", (62, -186), (-0.2, 1)), hand("R", _lerp2((70, -200), (10, -352), k), (1, 1)),
              props=[("plate", "L")], prop="samosa", ll1=-9, rl1=9)
    pose["chew"] = (0.5 + 0.5 * sin(2 * pi * 3.2 * t)) if near or k > 0.5 else 0.0
    return _side(d, pose)


def drink(t, sp, I, ph, o):
    d = _d(o)
    k = ease_out(_once(t % 3.0, 0.2, 0.5)) * (1 - ease_in(_once(t % 3.0, 1.6, 0.5)))
    pose = _P(hand("R", _lerp2((80, -250), (14, -346), k), (1, 1)), look_y=-0.5 * k, head_dy=-3 * k,
              prop="chai", ll1=-9, rl1=9)
    return _side(d, pose)


def phone_call(t, sp, I, ph, o):
    d = _d(o)
    return _side(d, _P(hand("R", (96, -372), (1, 1)), hand("L", (-72, -92), (-1, -0.3)), prop="phone",
                       tilt=1.5 * sin(2 * pi * 0.4 * t), look_x=0.3 * sin(2 * pi * 0.2 * t), ll1=-9, rl1=9))


def text(t, sp, I, ph, o):
    j = 5 * sin(2 * pi * 7 * t)
    return _P(hand("R", (14, -212 + j * 0.5), (1, 1)), hand("L", (-14, -208), (-1, 1)), prop="phone",
              look_y=0.9, head_dy=5, ll1=-9, rl1=9)


def read(t, sp, I, ph, o):
    return _P(hand("R", (22, -250), (1, 1)), hand("L", (-22, -250), (-1, 1)), prop="book",
              look_y=0.8, head_dy=4, look_x=0.3 * sin(2 * pi * 0.3 * t), ll1=-9, rl1=9)


def write(t, sp, I, ph, o):
    d = _d(o)
    return _side(d, _P(hand("R", (44 + 7 * cos(2 * pi * 3 * t), -132 + 4 * sin(2 * pi * 3 * t)), (1, 0.4)),
                       hand("L", (-34, -130), (-1, 0.4)), prop="pen", look_y=1.0, head_dy=8, ll1=-9, rl1=9))


def count_money(t, sp, I, ph, o):
    d = _d(o)
    f = 6 * sin(2 * pi * 3 * t)
    return _side(d, _P(hand("L", (40, -232), (-0.3, 1)), hand("R", (62 + f, -240), (1, 1)),
                       props=[("money", "L")], look_y=0.7, face="grin", ll1=-9, rl1=9))


def wash_hands(t, sp, I, ph, o):
    j = 9 * sin(2 * pi * 3 * t)
    return _P(hand("R", (10 + j, -124), (1, 0.5)), hand("L", (-10 + j, -128), (-1, 0.5)), look_y=0.9, head_dy=5,
              ll1=-9, rl1=9)


def sweep(t, sp, I, ph, o):
    d = _d(o)
    s_ = sin(2 * pi * 1.1 * sp * t)
    return _side(d, _P(hand("R", (120 + 30 * s_, -150), (1, 0.5)), hand("L", (70 + 20 * s_, -262), (0, 1)),
                       prop="broom", tilt=3 * s_, look_y=0.8, ll1=-12, rl1=12))


def cook(t, sp, I, ph, o):
    d = _d(o)
    a = 2 * pi * 1.4 * sp * t
    return _side(d, _P(hand("R", (100 + 16 * cos(a), -176 + 6 * sin(a)), (1, 0.5)), hand("L", (-70, -120), (-1, 0.4)),
                       prop="spoon", look_y=0.8, ll1=-9, rl1=9))


def brush_teeth(t, sp, I, ph, o):
    d = _d(o)
    j = 9 * sin(2 * pi * 6 * t)
    return _side(d, _P(hand("R", (40 + j, -352), (1, 1)), prop="toothbrush", face="grin", ll1=-9, rl1=9))


def drive(t, sp, I, ph, o):
    d = _d(o)
    st = 10 * sin(2 * pi * 0.5 * t)
    return _side(d, _P(dict(rl1=86, rl2=0, ll1=80, ll2=-4), hand("R", (150, -262 + st), (0, 1)),
                       hand("L", (132, -274 - st), (0, 1)), tilt=-2))


def steer(t, sp, I, ph, o):
    """At the wheel, seen from in front (through the windshield, or from the dashboard): both hands on the rim at
    ten and two (the character draws the wheel between them: pose key `wheel`), turning it a little now and then,
    the eyes on the road."""
    turn = 7 * sin(2 * pi * 0.21 * t + ph) + 3 * sin(2 * pi * 0.57 * t + 1.1)
    d = _stance()
    d.update(hand("L", (-96, -140 + turn), (-0.35, 1.0)))
    d.update(hand("R", (96, -140 - turn), (0.35, 1.0)))
    d.update(wheel=True, tilt=0.12 * turn * I, head_tilt=0.8 * sin(2 * pi * 0.3 * t + ph) * I)
    return d


def throw(t, sp, I, ph, o):
    d = _d(o)
    if t < 0.35:
        tg = _lerp2((80, -120), (-80, -480), ease_out(t / 0.35))
    elif t < 0.5:
        tg = _lerp2((-80, -480), (210, -330), ease_in((t - 0.35) / 0.15))
    else:
        tg = _lerp2((210, -330), (120, -150), ease_out(_once(t, 0.5, 0.8)))
    lean = -6 * ease_out(_once(t, 0, 0.35)) + 16 * sin(pi * _once(t, 0.35, 0.4))
    pose = _P(hand("R", tg, (0, 1)), dict(rl1=9 + 22 * _once(t, 0.3, 0.2), ll1=-14), tilt=lean,
              hide_prop=t >= 0.45)
    return _side(d, pose)


def catch(t, sp, I, ph, o):
    d = _d(o)
    rec = ease_out(_once(t, 0.3, 0.3))
    pose = _P(hand("R", _lerp2((160, -390), (110, -300), rec), (0, 1)),
              hand("L", _lerp2((140, -410), (96, -310), rec), (0, 1)), tilt=-5 * rec,
              face="surprised" if t < 0.3 else None, ll1=-12, rl1=12)
    return _side(d, pose)


def kick(t, sp, I, ph, o):
    d = _d(o)
    k = sin(pi * _once(t, 0, 0.45))
    pose = _P(dict(rl1=9 + 86 * k, rl2=9 + 72 * k, ll1=-12, ll2=-4), hand("R", (-40, -150), (1, 1)),
              hand("L", (-160, -330)), tilt=-8 * k)
    return _side(d, pose)


def slap(t, sp, I, ph, o):
    d = _d(o)
    if t < 0.18:
        tg = _lerp2((80, -120), (-30, -430), ease_out(t / 0.18))
    elif t < 0.28:
        tg = _lerp2((-30, -430), (236, -380), ease_in((t - 0.18) / 0.1))
    else:
        tg = _lerp2((236, -380), (110, -130), ease_out(_once(t, 0.6, 0.4)))
    pose = _P(hand("R", tg, (0, 1)), tilt=9 * sin(pi * _once(t, 0.15, 0.4)), face="angry", ll1=-12, rl1=12)
    return _side(d, pose)


def punch(t, sp, I, ph, o):
    d = _d(o)
    k = sin(pi * _once(t, 0.12, 0.22))
    pose = _P(hand("R", _lerp2((64, -330), (262, -340), k), (0, 1)), hand("L", (30, -340), (-0.3, 1)),
              dict(ll1=-16, rl1=16), tilt=8 * k, face="determined")
    return _side(d, pose)


def box(t, sp, I, ph, o):
    d = _d(o)
    q = (t * sp) % 1.2
    kr = sin(pi * clamp((q - 0.1) / 0.2))
    kl = sin(pi * clamp((q - 0.7) / 0.2))
    pose = _P(hand("R", _lerp2((64, -330), (258, -340), kr), (0, 1)),
              hand("L", _lerp2((30, -344), (220, -350), kl), (-0.2, 1)),
              dict(ll1=-18, rl1=18), lift=-6 * abs(sin(2 * pi * 2 * t)), tilt=5 * (kr + kl), face="determined")
    return _side(d, pose)


def push(t, sp, I, ph, o):
    d = _d(o)
    k = ease_out(_once(t, 0.12, 0.18)) * (1 - ease_in(_once(t, 0.8, 0.4)))
    pose = _P(hand("R", _lerp2((50, -250), (206, -262), k), (0, 1)), hand("L", _lerp2((30, -240), (190, -250), k), (0, 1)),
              dict(rl1=20, ll1=-20), tilt=10 * k)
    return _side(d, pose)


def dodge(t, sp, I, ph, o):
    d = _d(o)
    k = ease_out(_once(t, 0, 0.15)) * (1 - ease_in(_once(t, 0.7, 0.35)))
    pose = _P(hand("R", (60, -470), (1, 0)), hand("L", (-30, -460), (-1, 0)), tilt=-22 * k, shift=-34 * k,
              face="shock", ll1=-12, rl1=12)
    return _side(d, pose)


def high_five(t, sp, I, ph, o):
    d = _d(o)
    up = ease_out(_once(t, 0, 0.2))
    jolt = 12 * sin(pi * _once(t, 0.22, 0.12))
    return _side(d, _P(hand("R", _lerp2((80, -120), (156 + jolt, -556), up), (1, 0.2)), face="grin",
                       tilt=4 * up, ll1=-9, rl1=9))


def handshake(t, sp, I, ph, o):
    d = _d(o)
    pump = 14 * sin(2 * pi * 3 * t) if t < 1.4 else 0
    return _side(d, _P(hand("R", (176, -206 + pump), (0, 1)), face="smile", tilt=3, ll1=-9, rl1=9))


def hug(t, sp, I, ph, o):
    d = _d(o)
    e = ease_out(_once(t, 0, 0.35))
    pose = _P(hand("R", _lerp2((80, -120), (196, -286), e), (0.2, -0.4)),
              hand("L", _lerp2((-80, -120), (176, -296), e), (0, 1)),
              tilt=7 * e, head_dx=10 * e, face="smile", ll1=-9, rl1=9)
    return _side(d, pose)


def pat_back(t, sp, I, ph, o):
    d = _d(o)
    pat = 12 * abs(sin(2 * pi * 2.5 * t))
    return _side(d, _P(hand("R", (164, -336 + pat), (0.3, -0.2)), tilt=4, face="smile", ll1=-9, rl1=9))


def carry(t, sp, I, ph, o):
    d = _d(o)
    bob = 4 * abs(sin(2 * pi * 1.2 * t))
    return _side(d, _P(hand("R", (126, -246), (0, 1)), hand("L", (110, -238), (0, 1)), dict(ll1=-16, rl1=16),
                       tilt=-4, lift=-bob, prop="box", prop_hand="R"))


def drag(t, sp, I, ph, o):
    d = _d(o)
    legs = _gait(t, 0.6 * sp, 14, 30, ph)
    return _side(d, _P(legs, hand("R", (166, -150), (0, 1)), hand("L", (150, -160), (0, 1)), tilt=-14,
                       face="determined"))


def tug(t, sp, I, ph, o):
    d = _d(o)
    j = 3 * sin(2 * pi * 1.5 * t)
    return _side(d, _P(hand("R", (196, -232), (0, 1)), hand("L", (176, -228), (0, 1)), dict(ll1=-26, rl1=22),
                       tilt=-20 + j, face="determined"))


def argue(t, sp, I, ph, o):
    d = _d(o)
    jab = 16 * sin(2 * pi * 2.5 * sp * t)
    return _side(d, _P(hand("R", (226 + jab, -362), (0, 1)), hand("L", (-72, -92), (-1, -0.3)), finger="R",
                       head_dx=8, tilt=4 + 2 * sin(2 * pi * 2.5 * t), face="angry", ll1=-12, rl1=12))


# ------------------------------------------------------------------ sports & gym


def bat(t, sp, I, ph, o):
    d = _d(o)
    q = (t * sp) % 1.6
    if q < 0.6:
        tg, lean = (-40, -330), -4
    elif q < 0.75:
        e = ease_in((q - 0.6) / 0.15)
        tg, lean = _lerp2((-40, -330), (150, -200), e), -4 + 14 * e
    else:
        e = ease_out((q - 0.75) / 0.4)
        tg, lean = _lerp2((150, -200), (60, -430), e), 10 - 10 * e
    return _side(d, _P(hand("R", tg, (0, 1)), hand("L", (tg[0] - 14, tg[1] + 8), (0, 1)), dict(ll1=-20, rl1=20),
                       tilt=lean, prop="bat", face="determined"))


def bowl(t, sp, I, ph, o):
    d = _d(o)
    q = (t * sp) % 1.4
    p = clamp(q / 0.6)
    a = 20 - 360 * ease_in_out_(p)
    rel = sin(pi * clamp((q - 0.4) / 0.3))
    return _side(d, dict(ra1=a, ra2=a, la1=-60 + 40 * p, la2=-40, rl1=9 + 40 * rel, rl2=-10 * rel, ll1=-14,
                         tilt=10 * rel))


def race_start(t, sp, I, ph, o):
    d = _d(o)
    ready = _side(d, _P(dict(ll1=-30, ll2=40, rl1=60, rl2=-10), hand("R", (120, 40)), hand("L", (100, 40)),
                        tilt=28, face="determined"))
    if t < 0.8:
        return ready
    return _mix(ready, run(t - 0.8, sp, I, ph, o), (t - 0.8) / 0.25)


def jumping_jacks(t, sp, I, ph, o):
    k = 0.5 - 0.5 * cos(2 * pi * 1.5 * sp * t)
    return dict(ra1=14 + 150 * k, ra2=8 + 164 * k, la1=-14 - 150 * k, la2=-8 - 164 * k,
                ll1=-6 - 18 * k, ll2=-3 - 16 * k, rl1=6 + 18 * k, rl2=3 + 16 * k,
                lift=-12 * abs(sin(2 * pi * 1.5 * sp * t)))


def squat(t, sp, I, ph, o):
    k = 0.5 - 0.5 * cos(2 * pi * 0.7 * sp * t)
    return _P(dict(ll1=-9 - 49 * k, ll2=-3 + 15 * k, rl1=9 + 49 * k, rl2=3 - 15 * k),
              hand("R", (110, -250 + 40 * k), (1, 1)), hand("L", (-110, -250 + 40 * k), (-1, 1)), face="determined")


def pushup(t, sp, I, ph, o):
    d = _d(o)
    k = 0.5 - 0.5 * cos(2 * pi * 0.8 * sp * t)
    th = 64 + 10 * k
    pose = dict(tilt=th, ra1=th + 55 * k, ra2=th - 35 * k, la1=th + 55 * k, la2=th - 35 * k,
                ll1=-2, rl1=2, face="determined")
    return _side(d, pose)


def lift_weights(t, sp, I, ph, o):
    k = 0.5 - 0.5 * cos(2 * pi * 0.9 * sp * t)
    return dict(ra1=18, ra2=18 + 150 * k, la1=-18, la2=-18 - 150 * k, ll1=-12, rl1=12,
                props=[("dumbbell", "L")], prop="dumbbell", face="determined")


# ------------------------------------------------------------------ dances


def garba(t, sp, I, ph, o):
    w = 2 * pi * 0.75 * sp
    side = clamp(sin(w * t + ph) * 2.2, -1, 1)
    clapk = abs(sin(2 * w * t + ph))
    return _P(hand("R", (side * 130 + 14, -320 - 20 * clapk), (1, 0.3)),
              hand("L", (side * 130 - 14, -320 - 20 * clapk), (-1, 0.3)),
              dict(ll1=-9 + 10 * side, rl1=9 + 10 * side), tilt=6 * side, shift=10 * side,
              lift=-6 * clapk, face="smile")


def hookstep(t, sp, I, ph, o):
    w = 2 * pi * 1.2 * sp
    s_ = sin(w * t + ph)
    return _P(hand("R", (128 + 14 * s_, -470), (1, 0.6)), hand("L", (-128 + 14 * s_, -470), (-1, 0.6)),
              dict(ll1=-12 + 10 * s_, ll2=-4 + 18 * max(0, s_), rl1=12 + 10 * s_, rl2=4 - 18 * max(0, -s_)),
              shift=16 * s_, tilt=5 * s_, face="grin")


def floss(t, sp, I, ph, o):
    w = 2 * pi * 2.0 * sp
    s_ = sin(w * t + ph)
    a = 10 + 36 * s_
    return dict(ra1=a, ra2=a, la1=a - 20, la2=a - 20, shift=-20 * s_, tilt=-4 * s_, ll1=-9, rl1=9, face="grin")


EMOTIONAL = ANGRY | HAPPY | SAD | SCARED | COOL | THINK


def talk_emotion(t, sp, I, ph, o):
    """Talking with a feeling: the gesture style follows the expression; big moves land on loud syllables."""
    d = _d(o)
    e = o.get("_expr", "neutral")
    amp = clamp(o.get("_amp", 0.5)) * I
    w = 2 * pi * 1.1 * sp
    n1, n2 = _n(t * 1.6, ph), _n(t * 1.3, ph + 2)
    if e in ANGRY:                                  # jabbing finger, leaning in
        jab = (0.3 + 0.7 * amp)
        pose = _P(hand("R", (120 + 70 * jab, -330 - 12 * n1), (0, 1)), hand("L", (-90, -70), (-1, 0.2)),
                  dict(ll1=-14, rl1=14), finger="R", tilt=4 + 2 * amp, head_dx=4 + 3 * amp,
                  head_tilt=2 * n2)
    elif e in HAPPY:                                # open arms, bouncy
        op = 0.4 + 0.6 * amp                       # open hands; no bouncing (it looked like jumping)
        pose = _P(hand("R", (105 + 45 * op, -230 - 45 * op + 6 * n1), (1, 0.6)),
                  hand("L", (-105 - 45 * op, -230 - 45 * op + 6 * n2), (-1, 0.6)),
                  dict(ll1=-11, rl1=11), head_tilt=4 * n1, tilt=1.5 * n2)
    elif e in SAD:                                  # small low gestures, head down
        pose = _P(hand("R", (70 + 25 * amp, -130 - 30 * amp), (1, 1)), hand("L", (-62, -110), (-1, 1)),
                  dict(ll1=-7, rl1=7), head_dy=7, look_y=0.5, head_tilt=-3 + 2 * n1, tilt=-1)
    elif e in SCARED:                               # hands up at the chest, fidgety
        tr = 0.8 * sin(2 * pi * 7 * t)
        pose = _P(hand("R", (46 + 12 * amp, -262 - 20 * amp), (1, 1)), hand("L", (-40, -256), (-1, 1)),
                  dict(ll1=-4, rl1=4), shift=tr, tilt=-3, look_x=0.4 * n1, head_dy=-2 * amp)
    elif e in COOL:                                 # hand on the hip, lazy gesture
        pose = _P(hand("L", (-72, -92), (-1, -0.3)), hand("R", (115 + 25 * amp, -205 - 30 * amp + 5 * n1), (1, 0.5)),
                  dict(ll1=-12, rl1=12), head_tilt=5 + 2 * n2, tilt=-2)
    else:                                           # thinking: a hand near the chin
        pose = _P(hand("R", (26 + 10 * amp, -320 + 6 * n1), (1, 1)), hand("L", (46, -214), (-0.3, 1)),
                  dict(ll1=-9, rl1=9), look_y=-0.4, head_tilt=4 * n2)
    return _side(d, pose)


SING_ACTIONS = {"sing", "gaana"}
# moves worth watching for a while: a script line with only one of these holds the cursor ~1.6 s
DANCES = {"dance", "dance2", "dance3", "disco", "sway", "naagin", "nagin", "bhangra", "aeroplane", "airplane",
          "garba", "hookstep", "floss", "moonwalk",
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
    # movement
    "run": run, "jog": jog, "sneak": sneak, "tiptoe": sneak, "creep": sneak, "limp": limp,
    "crouch": crouch, "hide": hide, "peek": peek, "sit": sit, "sit_floor": sit_floor,
    "lie_down": lie_down, "lie": lie_down, "sleep_lie": sleep_lie, "rofl": rofl, "slip": slip, "trip": trip,
    "faint": faint, "get_up": get_up, "wake_up": wake_up, "turn_around": turn_around, "spin": spin,
    "cartwheel": cartwheel, "moonwalk": moonwalk, "climb": climb, "jump_over": jump_over, "slide": slide,
    "skid": skid,
    # reactions
    "nod": nod, "shake_head": shake_head, "look_back": look_back, "look_around": look_around,
    "look_up": look_up, "look_down": look_down, "scratch_head": scratch_head, "yawn": yawn, "sneeze": sneeze,
    "scared": scared, "tremble": scared, "shiver": shiver, "stomp": stomp, "celebrate": celebrate,
    "jump_joy": celebrate, "fist_pump": fist_pump, "arms_crossed": arms_crossed, "sulk": sulk,
    "cringe": cringe, "hands_on_hips": hands_on_hips, "proud": proud, "think": think, "listen": listen,
    "shh": shh, "point_self": point_self, "thumbs_up": thumbs_up, "namaste": namaste, "pray": namaste,
    "bow": bow, "rub_hands": rub_hands, "flex": flex, "stretch": stretch, "whisper": whisper, "shy": shy,
    "dizzy": dizzy, "hit_react": hit_react, "get_hit": hit_react,
    # everyday
    "eat": eat, "drink": drink, "phone_call": phone_call, "call": phone_call, "text": text, "type": text,
    "read": read, "write": write, "count_money": count_money, "wash_hands": wash_hands, "sweep": sweep,
    "cook": cook, "stir": cook, "brush_teeth": brush_teeth, "drive": drive, "steer": steer,
    # two people
    "throw": throw, "catch": catch, "kick": kick, "slap": slap, "punch": punch, "box": box, "push": push,
    "dodge": dodge, "high_five": high_five, "handshake": handshake, "hug": hug, "pat_back": pat_back,
    "carry": carry, "drag": drag, "tug": tug, "argue": argue,
    # sports / gym / dance
    "bat": bat, "bowl": bowl, "race_start": race_start, "jumping_jacks": jumping_jacks, "squat": squat,
    "pushup": pushup, "lift_weights": lift_weights, "garba": garba, "hookstep": hookstep, "floss": floss,
    # animal words (studio/animals.py draws them for dogs, cats, cows and birds; a person just does the nearest thing)
    "bark": talk, "meow": talk, "moo": talk, "caw": talk, "wag": sway, "fly": aeroplane, "peck": bow,
}


def pose_for(action, t, speed=1.0, intensity=1.0, phase=0.0, opts=None):
    fn = ACTIONS.get(action or "idle", idle)
    return fn(max(0.0, t), speed or 1.0, intensity if intensity is not None else 1.0, phase, opts or {})

"""Animation library. Each action returns pose overrides for time t (seconds since
the action started). Angle convention: 0 = straight down, +90 = screen-right, 180 = up.
L = screen-left limb, R = screen-right limb."""
import math

from .util import clamp, ease_in, ease_out, ease_out_back

sin, cos, pi = math.sin, math.cos, math.pi


def _stance(spread=1.0):
    return dict(ll1=-9 * spread, ll2=-3 * spread, rl1=9 * spread, rl2=3 * spread)


def idle(t, sp, I, ph, o):
    w = 2 * pi * 0.7 * sp
    d = _stance()
    d.update(tilt=1.2 * sin(w * t + ph) * I, head_tilt=2.0 * sin(w * t * 0.5 + ph) * I,
             la1=-14 + 2 * sin(w * t), ra1=14 - 2 * sin(w * t))
    return d


def talk(t, sp, I, ph, o):
    w = 2 * pi * 1.1 * sp
    d = _stance()
    d.update(
        tilt=1.5 * sin(w * 0.5 * t + ph) * I,
        head_tilt=4.0 * sin(w * t + ph) * I,
        ra1=38 + 20 * sin(w * t + ph) * I, ra2=70 + 28 * sin(w * t + 1.2 + ph) * I,
        la1=-16 + 4 * sin(w * 0.5 * t),
        lift=-3 * abs(sin(w * t + ph)) * I,
    )
    return d


def dance(t, sp, I, ph, o):
    style = o.get("style", "pump")
    w = 2 * pi * 1.5 * sp
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


def laugh(t, sp, I, ph, o):
    w = 2 * pi * 4.5 * sp
    d = _stance(1.6)
    d.update(la1=-40, la2=48, ra1=40, ra2=-48,
             tilt=3 * sin(w * 0.5 * t) * I, head_tilt=-11 + 6 * sin(w * t) * I,
             lift=-9 * abs(sin(w * t)) * I, look_y=-0.5)
    return d


def shock(t, sp, I, ph, o):
    jump = sin(pi * clamp(t / 0.32)) * 130 * I if t < 0.32 else 0.0
    lean = o.get("lean", -1) * 10 * ease_out(t / 0.25)
    shake = sin(2 * pi * 14 * t) * 3 * I if t > 0.3 else 0
    d = _stance(1.6)
    d.update(lift=-jump, tilt=lean, shift=shake,
             la1=-120 - 20 * ease_out(t / 0.25), la2=-165,
             ra1=120 + 20 * ease_out(t / 0.25), ra2=165, head_tilt=-lean * 0.6)
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


def reach(t, sp, I, ph, o):
    """Wide, scared crouch-lean, one arm stretched toward `point` (left|right) - e.g. lighting a cracker
    with an agarbatti from as far away as possible. Other hand on the hip."""
    dr = -1 if o.get("point", o.get("dir", "right")) in ("left", -1) else 1
    e = ease_out(t / 0.45)
    tr = sin(2 * pi * 7.5 * t * sp) * 2.2 * I          # nervous tremble
    d = dict(ll1=-30 * e - 9 * (1 - e), ll2=-4, rl1=30 * e + 9 * (1 - e), rl2=4,
             tilt=dr * 13 * e + tr * 0.3, head_tilt=-dr * 6 * e, look_x=dr * 0.9, look_y=0.5,
             lift=0.0)
    arm = dict(a1=dr * (14 + 52 * e), a2=dr * (8 + 62 * e + tr))
    knee = dict(a1=-dr * (14 + 26 * e), a2=-dr * (8 - 28 * e))
    if dr > 0:
        d.update(ra1=arm["a1"], ra2=arm["a2"], la1=knee["a1"], la2=knee["a2"])
    else:
        d.update(la1=arm["a1"], la2=arm["a2"], ra1=knee["a1"], ra2=knee["a2"])
    return d


def cover_ears(t, sp, I, ph, o):
    """Hands over the ears, flinching (waiting for the bang)."""
    e = ease_out(t / 0.25)
    sh = sin(2 * pi * 9 * t) * 2.0 * I
    d = _stance(1.1)
    d.update(la1=-14 - 86 * e, la2=-8 + 162 * e + sh, ra1=14 + 86 * e, ra2=8 - 162 * e - sh,
             head_tilt=sh * 0.8, tilt=sh * 0.3, lift=4 * e)
    return d


ACTIONS = {
    "idle": idle, "none": idle, "stand": idle,
    "talk": talk, "dance": dance, "dance2": dance2, "dance3": dance3, "disco": disco,
    "point": point, "laugh": laugh, "shock": shock, "jump": jump, "wave": wave, "clap": clap,
    "cry": cry, "fall": fall, "walk": walk, "facepalm": facepalm, "shrug": shrug, "sway": sway,
    "sleep": sleep, "reach": reach, "cover_ears": cover_ears,
}


def pose_for(action, t, speed=1.0, intensity=1.0, phase=0.0, opts=None):
    fn = ACTIONS.get(action or "idle", idle)
    return fn(max(0.0, t), speed or 1.0, intensity if intensity is not None else 1.0, phase, opts or {})

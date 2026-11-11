"""Compile a scene.json dict into a render plan (timeline, speech, audio, camera)."""
import math
import os
import sys

from . import audio, effects, elevenlabs_tts, gemini_tts, objects, rides
from .characters import assign_faces, color_of, resolve_spec
from .util import LW, LH, asset_path, clamp, deep_merge, ease_in_out, ease_out, ease_out_back, lerp

SLOTS = {
    1: {"center": 540},
    2: {"left": 300, "right": 780, "center": 540},
    3: {"left": 190, "center": 540, "right": 890},
}
GROUND_Y = 1700
SHOT_ZOOM = {"wide": 1.0, "medium": 1.3, "close": 1.7, "two_shot": 1.3}
SHOT_ALIASES = {"closeup": "close", "close_up": "close", "twoshot": "two_shot", "2shot": "two_shot"}
# Camera angle of a shot (CUT): the background is seen closer (a longer lens), from a side, or from the other side
# (mirrored = the reverse shot). (zoom, centre x in logical px, mirror). Shot 0 of a place shows it all.
ANGLES = [(1.0, 540.0, False), (1.25, 400.0, True), (1.25, 680.0, False), (1.4, 540.0, True)]


def shot_angle(scene, framing):
    """The background angle of a shot: {"zoom", "x", "mirror"}. scene["angle"] is a shot number (the script counts the
    CUTs in one place) or a dict; scene["reverse"] = true asks for the view from the other side."""
    a = scene.get("angle", 0)
    if isinstance(a, dict):
        out = dict(zoom=float(a.get("zoom", 1.0)), x=float(a.get("x", 540.0)), mirror=bool(a.get("mirror", False)))
    else:
        k = int(a or 0)
        z, x, m = ANGLES[k if k < len(ANGLES) else 1 + (k - 1) % (len(ANGLES) - 1)]
        out = dict(zoom=z, x=x, mirror=m)
    if framing == "wide":                       # a wide shot shows the whole place
        out.update(zoom=1.0, x=540.0)
    if framing == "inside":
        out = dict(zoom=1.0, x=540.0, mirror=False)
    if scene.get("reverse"):
        out["mirror"] = True
    if (scene.get("background") or {}).get("type") == "image" and not scene.get("reverse"):
        out["mirror"] = False                   # a photo may have writing on it: mirror only when asked
    out["zoom"] = clamp(out["zoom"], 1.0, 1.6)
    return out


def fit_to_angle(ob, ang):
    """A set piece drawn over the painted place moves with it when a shot sees the place closer / mirrored."""
    z = float(ang.get("zoom", 1.0))
    if z > 1.001:
        left = clamp(ang["x"] * z - LW / 2.0, 0, LW * z - LW)
        top = clamp(GROUND_Y * (z - 1.0), 0, LH * z - LH)
        ob["x"] = float(ob.get("x", 540)) * z - left
        ob["y"] = float(ob.get("y", GROUND_Y)) * z - top
        ob["scale"] = float(ob.get("scale", 1.0)) * z
    if ang.get("mirror"):
        ob["x"] = LW - float(ob.get("x", 540))
        ob["flip"] = not ob.get("flip")


PEOPLE_SCALE_3 = 1.06        # ...three people side by side need the room
PEOPLE_SCALE = 1.22          # medium shots: people this much bigger than the painted place (x sqrt of the angle zoom)
FOCUS_H = {"dog": 170.0, "cat": 120.0, "cow": 260.0, "crow": 70.0, "parrot": 70.0}   # animals: camera looks lower

OTS_BACK = dict(k=2.3, drop=1200.0, left=150.0, right=930.0)      # the near shoulder: big, cut off by the frame


def place_over_shoulder(chars):
    """Over-the-shoulder shot: whoever is seen from behind stands big in a near corner (only head and shoulders in
    the frame); the others face them from the other half, a step further away."""
    backs = [c for c in chars.values() if c.spec.get("view") == "back"]
    if not backs:
        return
    side = backs[0].spec.get("slot") if backs[0].spec.get("slot") in ("left", "right") else "left"
    for c in backs:
        c.x, c.y = OTS_BACK[side], GROUND_Y + OTS_BACK["drop"]
        c.scale *= OTS_BACK["k"]
    fronts = [c for c in chars.values() if c.spec.get("view") != "back" and not c.spec.get("hidden")]
    xs = {1: [720.0], 2: [580.0, 870.0]}.get(len(fronts), [480.0, 700.0, 920.0])
    if side == "right":
        xs = [1080.0 - x for x in reversed(xs)]
    for c, x in zip(fronts, xs):
        c.x, c.y = x, GROUND_Y + 90.0          # a step closer than in a medium shot
        c.scale *= 1.12


DEPTHS = {"near": (1.3, 110.0), "mid": (1.0, 0.0), "far": (0.75, -150.0)}   # (size multiplier, feet offset in px)
# a big one-off move said with a line (jump, clap, shock, wave...) plays once, then the character settles into
# talking with the same face: a person who jumps for 6 seconds while talking looks fake
BURST_ACTIONS = {"jump": 0.95, "celebrate": 1.6, "fist_pump": 1.2, "jumping_jacks": 1.6, "spin": 1.2, "cartwheel": 1.4,
                 "stomp": 1.0, "clap": 1.2, "wave": 1.2, "laugh": 1.4, "shock": 1.2, "scared": 1.4, "flex": 1.4,
                 "salute": 1.2, "namaste": 1.2, "bow": 1.2, "nod": 1.0, "shake_head": 1.2, "high_five": 1.2,
                 "thumbs_up": 1.4, "scratch_head": 1.4, "rub_hands": 1.4, "shrug": 1.2, "cringe": 1.2, "proud": 1.4,
                 "shy": 1.4, "facepalm": 1.6, "dizzy": 1.6}

CHAR_ATTRS = ("action", "expression", "prop", "label", "look", "facing", "style", "point", "dir",
              "lean", "speed", "intensity", "hands", "tint", "on", "visible")


OBJ_Y = {"truck": 1640.0, "auto": 1650.0, "car": 1640.0, "scooter": 1660.0, "cow": 1690.0, "dustbin": 1690.0,
         "bags": 1700.0, "table": 1700.0}


class SceneObj:
    """A set object (vehicle, bin, bags...) that sits in the scene or drives in / out."""

    def __init__(self, kind, color, scale, y, front, t_in, x):
        self.kind, self.color, self.scale, self.y, self.front, self.t_in = kind, color, scale, y, front, t_in
        self.t_out = None
        self.no_fade = t_in < 0.35                      # created at the very start of a shot: it is just there
        self.x0 = x
        self.rest = x
        self.moves = []             # (t0, t1, x0, x1)
        self.flips = [(t_in, False)]

    def x_at(self, t):
        x = self.x0
        for (t0, t1, xa, xb) in self.moves:
            if t < t0:
                break
            x = lerp(xa, xb, ease_in_out((t - t0) / max(1e-6, t1 - t0)))
        return x

    def moving(self, t):
        return any(t0 <= t < t1 for (t0, t1, _a, _b) in self.moves)

    def bob_at(self, t):
        """A vehicle shakes a little while it drives (logical px); its riders shake with it."""
        return math.sin(t * 17.0) * 3.0 if (self.kind in objects.VEHICLES and self.moving(t)) else 0.0

    def flip_at(self, t):
        f = False
        for (t0, fl) in self.flips:
            if t >= t0:
                f = fl
        return f

    def visible(self, t):
        return t >= self.t_in and (self.t_out is None or t < self.t_out)


CHAT_START, CHAT_GAP, CHAT_HOLD, TYPING = 0.6, 1.5, 1.4, 0.9


def chat_length(n_messages, chat=None):
    """Seconds a chat scene with n messages lasts (so a CTA can wait for the end)."""
    chat = chat or {}
    msgs = chat.get("messages", [])
    typing = sum(TYPING for m in msgs if m.get("side") == "left") if msgs else 0.0
    return (float(chat.get("start", CHAT_START)) + n_messages * float(chat.get("gap", CHAT_GAP)) + typing
            + float(chat.get("hold", CHAT_HOLD)))


def compile_chat(plan, chat):
    """A phone-chat scene: messages appear one by one (with a pop sound). Returns the time it is all over."""
    msgs = chat.get("messages", [])
    gap = float(chat.get("gap", CHAT_GAP))
    t = float(chat.get("start", CHAT_START))
    for m in msgs:
        if m.get("side") == "left" and "t" not in m:
            t += TYPING                              # the other person "types" before their message arrives
        m.setdefault("t", round(t, 2))
        plan.sfx.append(dict(t=float(m["t"]), path=audio.sfx_path("ding" if m.get("side") == "left" else "pop"),
                             volume=0.45 if m.get("side") == "left" else 0.6))
        t = float(m["t"]) + gap
    plan.overlays.insert(0, {"chat": chat, "from": 0.0, "pos": [540, 400], "anim": "none"})   # behind hook / CTA
    return t + float(chat.get("hold", CHAT_HOLD))


def compile_ride(plan, c, spec, t):
    """`A -> ride bike [back]`: A hops on (the vehicle is created beside A if it is not in the scene yet)."""
    kind = objects.resolve_kind(spec.get("kind", ""))
    if not kind or not rides.rideable(kind):
        plan.warnings.append("cannot ride %r" % spec.get("kind"))
        return 0.0
    if c.ride_at(t) is not None or any(r["t_off"] is None for r in c.rides):
        plan.warnings.append("%s is already on a vehicle" % c.name)
        return 0.0
    instant, drive = False, 0.0
    if kind not in plan.objects:                              # created together with its rider: no hop, it drives in with him
        side = spec.get("enter")
        if side in objects.OFFSCREEN:
            drive = compile_obj(plan, {"kind": kind, "enter": side, "at": spec.get("at") or "center"}, t, plan.warnings)
        else:
            compile_obj(plan, {"kind": kind, "at": spec.get("at") or float(c.pos_at(t)[0])}, t, plan.warnings)
        instant = True
    seat = spec.get("seat", "driver")
    taken = {r["seat"] for o_ in plan.world_chars for r in o_.rides
             if r["obj"] == kind and (r["t_off"] is None or r["t_off"] > t)}
    if seat in taken and seat != "back" and "back" in rides.RIDES[kind]:
        seat = "back"
    plan.objects[kind].front = True                           # a vehicle with riders is the star: in front of everybody
    if plan.framing == "inside":                             # the shot is the cab: the driver sits in the middle of the frame
        o_ = plan.objects[kind]
        o_.x0 = o_.rest = 540.0 - rides.seat_for(kind, seat)["hip"][0] * o_.scale
        o_.moves = []
        o_.flips = [(o_.t_in, False)]
    if instant:
        plan.objects[kind].no_fade = True
    c.rides.append({"t0": t, "obj": kind, "seat": seat, "t_off": None, "land_x": None, "land_y": None,
                    "instant": instant})
    return drive if drive else (0.1 if instant else rides.RIDE_HOP + 0.1)


def compile_getoff(plan, c, spec, t):
    """`A -> getoff [left|right]`: A hops off beside the vehicle (towards the screen centre unless told)."""
    cur = [r for r in c.rides if r["t_off"] is None and r["t0"] <= t]
    if not cur:
        plan.warnings.append("%s is not on a vehicle" % c.name)
        return 0.0
    ride = cur[-1]
    obj = plan.objects.get(ride["obj"])
    ox = obj.x_at(t) if obj else c.pos_at(t)[0]
    side = spec.get("side") if isinstance(spec, dict) else None
    if side not in ("left", "right"):
        side = "right" if ox < 540 else "left"
    reach = rides.HALF_LENGTH.get(ride["obj"], 200) * (obj.scale if obj else 1.0) * 0.5 + 170
    land_x = clamp(ox + (reach if side == "right" else -reach), 150.0, 930.0)
    k, dy = c.depth_at(t)
    ride.update(t_off=t, land_x=land_x, land_y=c.y + dy, land_k=k)
    c.moves.append((t, t + rides.RIDE_HOP, land_x, c.y, land_x, c.y))       # afterwards it stands there
    return rides.RIDE_HOP + 0.1


def compile_obj(plan, spec, t, warnings=None):
    """Apply one `obj` timeline event: {"kind", "at", "enter", "exit", "go", "color", "scale", "front", "dur"}."""
    kind = objects.resolve_kind(spec.get("kind", ""))
    if not kind:
        if warnings is not None:
            warnings.append("unknown object %r" % spec.get("kind"))
        return 0.0
    o = plan.objects.get(kind)
    at = spec.get("at")
    spot = objects.SPOTS.get(at) if isinstance(at, str) else (float(at) if at is not None else None)
    dur = float(spec.get("dur", 1.8 if kind in objects.VEHICLES else 1.0))
    vehicle = kind in objects.VEHICLES
    if o is None:
        rest = spot if spot is not None else objects.SPOTS["center"]
        color = color_of(spec["color"]) if spec.get("color") else None
        base = (objects.REF_SCALE * plan.world / objects.PERSON_R[kind]) if kind in objects.PERSON_R else plan.world
        o = SceneObj(kind, color, base * float(spec.get("scale", 1.0)), float(spec.get("y", OBJ_Y.get(kind, 1680.0))),
                     bool(spec.get("front")), t, rest)
        plan.objects[kind] = o
        side = spec.get("enter")
        if side in objects.OFFSCREEN:
            o.x0 = objects.OFFSCREEN[side]
            o.moves.append((t, t + dur, o.x0, rest))
            o.flips = [(t, side == "right")]
        o.rest = rest
        if spec.get("exit") not in objects.OFFSCREEN:
            return dur if side in objects.OFFSCREEN else 0.0
    cur = o.x_at(t)
    if spec.get("go") or (spot is not None and not spec.get("enter") and not spec.get("exit")
                          and o.t_in < t and abs(spot - cur) > 1):
        tgt = spot if spot is not None else objects.SPOTS.get(spec.get("go"), cur)
        o.moves.append((t, t + dur, cur, tgt))
        o.flips.append((t, tgt < cur))
        o.rest = tgt
        return dur if vehicle else dur * 0.6
    if spec.get("exit") in objects.OFFSCREEN:
        side = spec["exit"]
        o.moves.append((t, t + dur, cur, objects.OFFSCREEN[side]))
        o.flips.append((t, side == "left"))
        o.t_out = t + dur
        return dur
    return 0.0


def ease_travel(u, a=0.2):
    """A long walk: speeds up over the first fifth, keeps an even pace, slows down over the last fifth."""
    u = clamp(u)
    if u < a:
        return u * u / (2 * a * (1 - a))
    if u > 1 - a:
        return 1 - (1 - u) ** 2 / (2 * a * (1 - a))
    return (u - a / 2) / (1 - a)


MOVE_EASE = {"out": ease_out, "back": lambda u: ease_out_back(u, 1.5), "pan": ease_travel}


class Char:
    def __init__(self, name, spec, x, ground_y, index):
        self.name = name
        self.spec = spec
        self.x = x
        self.y = ground_y
        rs = resolve_spec(spec)
        self.scale = float(rs.get("scale", 1.0))
        self.leg_k = float(rs.get("leg_k", 1.0))
        self.travel0 = 0.0      # px already walked before this shot (a walk that goes on from the last place)
        self.phase = float(spec.get("phase", index * 0.9))
        self.events = []        # sorted by t
        self.moves = []         # (t0, t1, x0, y0, x1, y1[, run[, ease]]); ease: "out" (lands fast), "back" (overshoots)
        self.speech = []        # dicts
        self.depth = []         # (t, k0, dy0, k1, dy1[, seconds]): step towards / away from the camera
        self.rides = []         # {"t0", "obj", "seat", "t_off", "land_x", "land_y"}: sitting on a vehicle
        self.world = {}         # the scene's objects (set by compile_scene)
        self._rf = (None, None)
        v = spec.get("voice", {})
        self.voice = v if isinstance(v, dict) else {"name": v}

    def pos_at(self, t):
        x, y = self.x, self.y
        for (t0, t1, x0, y0, x1, y1, *_r) in self.moves:
            if t < t0:
                break
            u = (t - t0) / max(1e-6, t1 - t0)
            e = MOVE_EASE[_r[1]](u) if len(_r) > 1 and _r[1] in MOVE_EASE else ease_in_out(u)
            x, y = lerp(x0, x1, e), lerp(y0, y1, e)
        return x, y

    def depth_at(self, t):
        """(size multiplier, feet offset) - 1.0 / 0 on the normal ground line."""
        k, dy = 1.0, 0.0
        for (t0, k0, dy0, k1, dy1, *_r) in self.depth:
            if t < t0:
                break
            e = ease_in_out((t - t0) / (_r[0] if _r else 0.5))
            k, dy = lerp(k0, k1, e), lerp(dy0, dy1, e)
        return k, dy

    def ground_state(self, t):
        """(x, feet y, size) of the character standing on the ground at time t."""
        x, y = self.pos_at(t)
        k, dy = self.depth_at(t)
        return x, y + dy, self.scale * k

    def ride_at(self, t):
        """(ride, phase, p) while on a vehicle: phase "on" / "riding" / "off", p = progress of a hop (0..1)."""
        for r in self.rides:
            end = None if r["t_off"] is None else r["t_off"] + rides.RIDE_HOP
            if t < r["t0"] or (end is not None and t >= end):
                continue
            if not r.get("instant") and t < r["t0"] + rides.RIDE_HOP:
                return r, "on", (t - r["t0"]) / rides.RIDE_HOP
            if r["t_off"] is not None and t >= r["t_off"]:
                return r, "off", (t - r["t_off"]) / rides.RIDE_HOP
            return r, "riding", 1.0
        return None

    def ride_frame(self, t):
        if not self.rides:
            return None
        if self._rf[0] != t:
            self._rf = (t, rides.frame(self, t))
        return self._rf[1]

    def draw_pos(self, t):
        rf = self.ride_frame(t)
        if rf:
            return rf["x"], rf["y"]
        x, y = self.pos_at(t)
        return x, y + self.depth_at(t)[1]

    def draw_scale(self, t):
        rf = self.ride_frame(t)
        if rf:
            return rf["scale"]
        return self.scale * self.depth_at(t)[0]

    def focus_at(self, t):
        """Where the camera looks when it follows this character (head / chest)."""
        rf = self.ride_frame(t)
        if rf:
            return rf["hip"][0], rf["hip"][1] - 250 * rf["scale"]
        x, y = self.draw_pos(t)
        h = FOCUS_H.get(self.spec.get("kind"), 560.0)            # a dog's head is not where a person's is
        return x, y - h * self.scale * self.depth_at(t)[0]

    def state_at(self, t):
        st = dict(action="idle", action_t0=0.0, expression=self.spec.get("expression", "neutral"),
                  prop=self.spec.get("prop"), label=None, look=self.spec.get("look"),
                  facing=self.spec.get("facing", "front"), visible=self.spec.get("visible", True), on=None,
                  speed=1.0, intensity=1.0, opts={}, talking=None)
        for ev in self.events:
            if ev["t"] > t + 1e-9:
                break
            if "action" in ev:
                st["action"] = ev["action"]
                st["action_t0"] = ev["t"]
                st["speed"], st["intensity"] = 1.0, 1.0
                st["opts"] = {}
                st["on"] = ev.get("on")
            for key in ("expression", "prop", "label", "look", "facing", "visible"):
                if key in ev:
                    st[key] = ev[key]
            for key in ("speed", "intensity"):
                if key in ev:
                    st[key] = ev[key]
            for key in ("style", "point", "dir", "lean", "hands"):
                if key in ev:
                    st["opts"][key] = ev[key]
        for sp in self.speech:
            if sp["start"] <= t < sp["end"]:
                st["talking"] = sp
                if st["action"] in ("idle", "none", "stand"):
                    st["action"] = "talk"
                    st["action_t0"] = sp["start"]
        return st


class Plan:
    pass


ENTRY_STYLES = ("back", "pop", "fast", "peek")      # (walking in from the side is an ordinary `move`)
ENTRY_HOLD = {"back": 1.3, "pop": 0.7, "fast": 0.95, "peek": 2.2}     # seconds until they stand in their place
BACK_DEPTH = (0.55, -215.0)                         # far end of the place: (size, feet offset)


def compile_entry(plan, c, spec, t):
    """A character comes into the shot at time t in a livelier way than walking in from the side.
    spec = {"style": "back" | "pop" | "fast" | "peek", "side": "left" | "right", "x": where they end up}
      back  from the far corner of the place towards the camera (small and far -> full size)
      pop   jumps up into the frame from below, with a bounce
      fast  shoots in from the side and skids to a stop (dust, whoosh)
      peek  leans in at the edge of the frame, looks, then walks in
    Before t they are out of sight. Returns the seconds it takes."""
    style = spec.get("style")
    x1, y1 = float(spec.get("x", c.x)), c.y
    side = spec.get("side") if spec.get("side") in ("left", "right") else ("left" if x1 < LW / 2.0 else "right")
    edge = -170.0 if side == "left" else LW + 170.0
    face = "right" if side == "left" else "left"

    def sound(name, at, volume=0.6):
        path = audio.sfx_path(name)
        if path:
            plan.sfx.append(dict(t=at, path=path, volume=volume))

    if style == "pop":
        y0 = LH + 80.0 + 920.0 * c.scale           # the whole body below the frame
        c.x, c.y = x1, y0
        c.moves.append((t, t + 0.42, x1, y0, x1, y1, False, "back"))
        sound("boing", t, 0.55)
    elif style == "fast":
        c.x = edge
        c.moves.append((t, t + 0.36, edge, y1, x1, y1, True, "out"))
        c.events.append({"t": t, "facing": face})
        c.events.append({"t": t + 0.34, "action": "skid", "facing": face})
        c.events.append({"t": t + 0.9, "action": "idle"})
        plan.effects.append(effects.normalize({"type": "dust", "who": c.name}, t + 0.3))
        sound("whoosh", t, 0.7)
    elif style == "peek":
        xp = 46.0 if side == "left" else LW - 46.0  # half of them inside the frame
        c.x = edge
        c.moves.append((t, t + 0.4, edge, y1, xp, y1, False, "out"))
        c.events.append({"t": t, "action": "peek", "facing": face})
        c.events.append({"t": t + 1.3, "action": "idle", "facing": face})
        c.moves.append((t + 1.3, t + 2.15, xp, y1, x1, y1, False))
    else:                                           # back
        k0, dy0 = BACK_DEPTH
        x0 = -70.0 if side == "left" else LW + 70.0     # the far corner of the place: in sight from the first step
        c.x = edge                                  # out of sight until they come
        c.depth.append((-1.0, k0, dy0, k0, dy0, 0.001))
        c.depth.append((t, k0, dy0, 1.0, 0.0, 1.25))
        c.moves.append((t, t + 0.001, edge, y1, x0, y1, False))
        c.moves.append((t + 0.001, t + 1.25, x0, y1, x1, y1, False))
        c.events.append({"t": t, "facing": "front"})
    return ENTRY_HOLD.get(style, 1.0)


def compile_leave(plan, c, spec, t):
    """`exit left fast`: runs out of the shot in a blink (whoosh, dust where they stood)."""
    side = spec.get("side") if spec.get("side") in ("left", "right") else "left"
    x0, y0 = c.pos_at(t)
    c.events.append({"t": t, "facing": side})
    c.moves.append((t + 0.12, t + 0.5, x0, y0, -200.0 if side == "left" else LW + 200.0, y0, True))
    plan.effects.append(effects.normalize({"type": "dust", "who": c.name}, t + 0.1))
    path = audio.sfx_path("whoosh")
    if path:
        plan.sfx.append(dict(t=t + 0.1, path=path, volume=0.7))
    return 0.7


def _norm_who(who, names):
    if who in (None, "", "all", "everyone"):
        return list(names)
    if isinstance(who, str):
        return [who]
    return list(who)


def collect_lines(scene):
    """Every line of one scene that needs a voice, in speaking order, for the Gemini batch."""
    cdefs = scene.get("characters", {})
    names = list(cdefs.keys())
    out = []
    for ti, raw in enumerate(scene.get("timeline", [])):
        if "say" not in raw or not raw.get("tts", True):
            continue
        who = [w for w in _norm_who(raw.get("who"), names) if w in cdefs]
        text = str(raw.get("speak", raw["say"])).strip()
        if not who or not text:
            continue
        v = cdefs[who[0]].get("voice", {})
        v = dict(v) if isinstance(v, dict) else {"name": v}
        v.update(raw.get("voice", {}) if isinstance(raw.get("voice"), dict) else {})
        out.append(dict(ti=ti, text=text, voice=gemini_tts.voice_for(v), pitch=v.get("pitch"), rate=v.get("rate"),
                        who=who[0], spec=v, expression=raw.get("expression") or raw.get("emotion")))
    return out


def prepare_voice(scenes, use_tts=True, tts_provider=None):
    """Voice for a whole VIDEO (all its scenes) with ONE Gemini request.

    Returns one dict per scene: {"paths": {timeline index: wav}, "edge": bool}. `edge` means
    "synthesize the lines one by one with edge-tts" (provider is edge, or Gemini failed in auto mode).
    A failure with an explicitly requested gemini provider raises SystemExit instead.
    """
    silent = [{"paths": {}, "edge": False} for _ in scenes]
    if not use_tts or not scenes:
        return silent
    cfg = (scenes[0].get("meta") or {}).get("tts") or {}
    provider, explicit = audio.resolve_provider(tts_provider, cfg)
    per_scene = [collect_lines(sc) for sc in scenes]
    flat = [it for lines in per_scene for it in lines]
    if provider == "elevenlabs" and flat:
        try:
            return _per_scene(per_scene, elevenlabs_tts.synth_lines(flat, model=cfg.get("eleven_model")))
        except Exception as e:                      # (quota, a wrong key...): the video is still made
            provider = "gemini" if gemini_tts.api_key() else "edge"
            explicit = False
            print("::warning title=ElevenLabs awaaz nahi bani::%s -> %s ki awaaz use hui"
                  % (str(e)[:200], "Gemini" if provider == "gemini" else "free (edge)"), file=sys.stderr)
    if provider != "gemini":
        return [{"paths": {}, "edge": True} for _ in scenes]
    if not flat:
        return silent
    try:
        paths = gemini_tts.synth_script(flat, model=cfg.get("model", gemini_tts.DEFAULT_MODEL),
                                        style=cfg.get("style", gemini_tts.DEFAULT_STYLE))
    except Exception as e:
        if explicit:
            raise SystemExit("[tts] Gemini failed: %s" % e)
        print("  [tts] Gemini failed (%s) -> falling back to edge-tts" % str(e)[:160], file=sys.stderr)
        return [{"paths": {}, "edge": True} for _ in scenes]
    return _per_scene(per_scene, paths)


def _per_scene(per_scene, paths):
    """Voice files of the whole video (speaking order) -> one {"paths": {timeline index: file}} per scene."""
    out, k = [], 0
    for lines in per_scene:
        out.append({"paths": {it["ti"]: paths[k + j] for j, it in enumerate(lines)}, "edge": False})
        k += len(lines)
    return out


SHOT_SIZES = (1.25, 1.5, 1.3, 1.6)       # zoom per spoken line, cycled, so neighbouring lines are different shots


def shot_camera(name, t, chars, who, speaker=None, dur=0.16):
    """Camera event for a shot word (wide / medium / close / two_shot) on the given character(s)."""
    name = SHOT_ALIASES.get(name, name)
    ev = dict(t=t, zoom=SHOT_ZOOM[name], dur=dur)
    if name == "wide":
        return ev
    names = [w for w in (who or []) if w in chars]
    if name == "two_shot" or len(names) > 1:
        sp = speaker if speaker in chars else (names[0] if names else None)
        others = [n for n in chars if n != sp and chars[n].spec.get("hidden") is not True]
        if sp and others:                           # the speaker and whoever stands closest to them
            sx = chars[sp].draw_pos(t)[0]
            near = min(others, key=lambda n_: abs(chars[n_].draw_pos(t)[0] - sx))
            pts = [chars[sp].draw_pos(t), chars[near].draw_pos(t)]
        else:
            pts = [chars[n].draw_pos(t) for n in names]
        if pts:
            ev["focus"] = [sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts) - 560]
            return ev
    focus = names[0] if names else speaker
    if focus in chars:
        ev["focus"] = focus
    return ev


def auto_camera(plan, chars, cam_events, shakes):
    """Rule-based direction for scenes that have no camera moves of their own.

    Every spoken line gets a quick cut-in on its speaker (size cycles through SHOT_SIZES) followed by a slow
    push-in while the line is spoken; the last line (the punch line) is the tightest shot and ends with a shake;
    after it the camera pulls back to a wide shot for the reaction. A shot word on the line (close, wide, ...)
    replaces the automatic size of that line.
    """
    speech = sorted((sp for sp in plan.speech if sp.get("who") and not chars[sp["who"]].spec.get("hidden")),
                    key=lambda sp: sp["start"])
    n = len(speech)
    for i, sp in enumerate(speech):
        t0 = sp["start"]
        d = max(0.6, sp["end"] - t0)
        shot = SHOT_ALIASES.get(sp.get("shot"), sp.get("shot"))
        if shot in SHOT_ZOOM:
            cut = shot_camera(shot, max(0.0, t0 - 0.05), chars, [sp["who"]], sp["who"])
            cam_events.append(cut)
            size = cut["zoom"]
            if size > 1.0 and d > 1.0:
                cam_events.append(dict(cut, t=t0 + 0.2, zoom=round(size + 0.1, 2), dur=max(0.4, d - 0.2)))
            if i == n - 1 and n > 1:
                shakes.append((max(0.0, sp["end"] - 0.15), 0.5, 0.45))
            continue
        if i == 0:                                  # first line: ease in from the wide establishing shot
            cam_events.append(dict(t=t0, zoom=1.2, focus=sp["who"], dur=min(0.6, d)))
            size = 1.2
        else:
            size = 1.7 if (i == n - 1 and n > 2) else SHOT_SIZES[i % len(SHOT_SIZES)]
            if chars[sp["who"]].spec.get("kind") in FOCUS_H:
                size = min(1.8, size + 0.2)         # a small animal talking: come a bit closer
            cam_events.append(dict(t=max(0.0, t0 - 0.05), zoom=size, focus=sp["who"], dur=0.16))
        if d > 1.0:                                 # slow push-in while the line is spoken
            cam_events.append(dict(t=t0 + 0.65 if i == 0 else t0 + 0.2, zoom=round(size + 0.12, 2),
                                   focus=sp["who"], dur=max(0.4, d - (0.65 if i == 0 else 0.2))))
        if i == n - 1 and n > 1:
            shakes.append((max(0.0, sp["end"] - 0.15), 0.5, 0.45))
    if speech and plan.duration - speech[-1]["end"] > 0.7:
        cam_events.append(dict(t=speech[-1]["end"] + 0.2, zoom=1.0, dur=0.5))
    for w in plan.warps:                            # slow motion: pull back to watch it happen
        if w[0] == "slow":
            cam_events.append(dict(t=w[1], zoom=1.0, dur=0.4))
    for fx in plan.effects:                         # a throw: frame the thrower and the target together
        if fx.get("type") == "projectile" and fx.get("src") in chars and fx.get("dst") in chars:
            t0 = max(0.0, fx["from"] - 0.45)
            (x1, y1), (x2, y2) = chars[fx["src"]].draw_pos(t0), chars[fx["dst"]].draw_pos(fx["to"])
            zoom = round(max(1.0, min(1.3, 1080.0 / (abs(x2 - x1) + 420.0))), 2)
            cam_events.append(dict(t=t0, zoom=zoom, focus=[(x1 + x2) / 2.0, (y1 + y2) / 2.0 - 560], dur=0.16))


# ------------------------------------------------------------------ camera style
# "cine" (default): the camera stays with whoever it looks at, never stands completely still, shows the listener's
# face after the last line of a shot, holds fast back-and-forth talk in one two-shot, tilts a little on an angry or
# scared line and whips (with motion blur) from one speaker to the other.
# "classic": the camera exactly as it was before (`CAMERA: classic` in a script, "meta": {"camera": "classic"} in a
# scene file, or the environment variable STUDIO_CAMERA=classic for everything).
FOLLOW_LAG = 0.1                # seconds the camera trails behind the one it follows
BANTER_MAX = 2.0                # lines up to this long, back and forth, are "fast talk"
TILT_EXPR = {"angry", "shout", "evil", "scared"}
TILT_DEG = 3.5
MOVE_MIN = 200.0                # a walk at least this long (logical px) is worth following
# the face of the one who was spoken to, when the script gave them no reaction of their own: by the speaker's mood
REACTIONS = {"angry": "nervous", "shout": "scared", "evil": "scared", "determined": "nervous",
             "shock": "confused", "surprised": "confused", "scared": "confused",
             "laugh": "bored", "lol": "bored", "grin": "bored", "smug": "bored", "sly": "confused", "proud": "bored",
             "wink": "shy", "love": "shy", "kiss": "shy", "sad": "sad", "cry": "sad", "hurt": "sad"}


CTA_Y = 330.0               # cine: the end card ("Tag karo...") sits above the faces instead of on them
LIE_ACTIONS = ("lie_down", "lie", "sleep_lie", "rofl")
# a body on its way to the floor: seconds after the action starts when it really goes down (faint wobbles first)
FALL_ACTIONS = {"faint": 0.6, "fall": 0.15, "slip": 0.1, "trip": 0.25, "lie_down": 0.0, "lie": 0.0,
                "sleep_lie": 0.0, "rofl": 0.0}
STAND_MIN = 170.0           # a standing person's centre keeps this far from the frame's edges
STAND_GAP = 240.0           # ...and this far from the next person


def stand_up_in_frame(chars, set_by_id):
    """cine: somebody lying on a bed (or sofa) has their feet at its far end - often at the edge of the picture.
    When they get up (any action that is not lying), they step to the nearest free spot inside the frame."""
    for c in chars.values():
        if c.spec.get("hidden") or c.spec.get("kind"):
            continue
        lying = False
        for e in list(c.events):
            a = e.get("action")
            if a is None:
                continue
            if a in LIE_ACTIONS and e.get("on") in set_by_id:
                lying = True
                continue
            if not lying:
                continue
            lying = False
            t2 = e["t"]
            if any(t2 - 0.01 <= m[0] <= t2 + 0.15 for m in c.moves):
                continue                            # they walk / leave right away: that move takes them
            fx, fy = c.pos_at(t2)
            others = [o.draw_pos(t2)[0] for o in chars.values()
                      if o is not c and not o.spec.get("hidden") and o.spec.get("view") != "back" and _on_stage(o, t2)]
            spots = [x for x in range(int(STAND_MIN), int(LW - STAND_MIN) + 1, 10)
                     if all(abs(x - ox) >= STAND_GAP for ox in others)]
            to = min(spots, key=lambda x: abs(x - fx)) if spots else clamp(c.x, STAND_MIN, LW - STAND_MIN)
            if abs(to - fx) > 20:
                dur = clamp(0.35 + abs(to - fx) / 1500.0, 0.4, 0.85)
                c.moves.append((t2, t2 + dur, fx, fy, float(to), fy, False, "out"))
                c.moves.sort(key=lambda m: m[0])


def _card_over_faces(plan, t):
    """True when a text card (the CTA at the end) sits in the upper middle of the screen from time t on: a close
    shot must keep the face below it."""
    for o in plan.overlays:
        if o.get("style") != "card" or float(o.get("from", 0.0)) > plan.duration or float(o.get("to", 1e9)) <= t:
            continue
        pos = o.get("pos", "upper")
        if (isinstance(pos, (list, tuple)) and 150 <= float(pos[1]) <= 1000) or pos in ("upper", "center", "middle"):
            return True
    return False


def camera_style(meta=None):
    v = os.environ.get("STUDIO_CAMERA") or (meta or {}).get("camera") or "cine"
    return "classic" if str(v).strip().lower() in ("classic", "old", "purana", "off") else "cine"


def _on_stage(c, t):
    """A person the camera can show at time t (not just a voice, not seen from behind, inside the frame)."""
    if c.spec.get("hidden") or c.spec.get("view") == "back" or not c.state_at(t).get("visible", True):
        return False
    x, y = c.draw_pos(t)
    return -40.0 <= x <= LW + 40.0 and y <= LH + 60.0


def _banter_runs(speech):
    """[(i, j)]: lines i..j (inclusive) are fast talk between changing speakers, at least 3 of them."""
    runs, i, n = [], 0, len(speech)
    while i < n:
        j = i
        while (j + 1 < n and speech[j + 1]["who"] != speech[j]["who"]
               and speech[j]["end"] - speech[j]["start"] <= BANTER_MAX
               and speech[j + 1]["end"] - speech[j + 1]["start"] <= BANTER_MAX
               and speech[j + 1]["start"] - speech[j]["end"] < 0.8):
            j += 1
        if j - i >= 2:
            runs.append((i, j))
        i = j + 1
    return runs


def auto_camera_cine(plan, chars, cam_events, shakes, rolls):
    """The "cine" direction for scenes that have no camera moves of their own (see camera_style)."""
    speech = sorted((sp for sp in plan.speech if sp.get("who") and not chars[sp["who"]].spec.get("hidden")),
                    key=lambda sp: sp["start"])
    n = len(speech)
    held = {}                                       # line index -> the run it belongs to (no cut of its own)
    for (a, b) in _banter_runs(speech):
        if b == n - 1 and n > 2:
            b -= 1                                  # the punch line keeps its own tight shot
        if b - a >= 1:
            for k in range(a, b + 1):
                held[k] = (a, b)
    size = 1.0
    for i, sp in enumerate(speech):
        t0 = sp["start"]
        d = max(0.6, sp["end"] - t0)
        c = chars[sp["who"]]
        shot = SHOT_ALIASES.get(sp.get("shot"), sp.get("shot"))
        punch = i == n - 1 and n > 1
        if shot in SHOT_ZOOM:                       # the script asked for a shot: as before
            cut = shot_camera(shot, max(0.0, t0 - 0.05), chars, [sp["who"]], sp["who"])
            cam_events.append(cut)
            size = cut["zoom"]
            if size > 1.0 and d > 1.0:
                cam_events.append(dict(cut, t=t0 + 0.2, zoom=round(size + 0.1, 2), dur=max(0.4, d - 0.2)))
        elif i in held:                             # fast talk: both in one frame, no cut for every line
            a, b = held[i]
            if i == a:
                other = chars[speech[a + 1]["who"]]
                (x1, y1), (x2, y2) = c.focus_at(t0), other.focus_at(t0)
                size = round(clamp(LW / (abs(x2 - x1) + 440.0), 1.0, 1.35), 2)
                mid = [(x1 + x2) / 2.0, (y1 + y2) / 2.0]
                run_d = speech[b]["end"] - t0
                cam_events.append(dict(t=max(0.0, t0 - 0.05), zoom=size, focus=mid, dur=0.3 if i == 0 else 0.18))
                cam_events.append(dict(t=t0 + 0.3, zoom=round(size + 0.1, 2), focus=mid, dur=max(0.4, run_d - 0.3)))
        else:
            if i == 0:                              # first line: ease in from the wide establishing shot
                cam_events.append(dict(t=t0, zoom=1.2, focus=sp["who"], dur=min(0.6, d)))
                size = 1.2
            else:
                size = 1.7 if (punch and n > 2) else SHOT_SIZES[i % len(SHOT_SIZES)]
                if c.spec.get("kind") in FOCUS_H:
                    size = min(1.8, size + 0.2)
                cam_events.append(dict(t=max(0.0, t0 - 0.05), zoom=size, focus=sp["who"], dur=0.16))
            if d > 1.0:                             # slow push-in while the line is spoken
                cam_events.append(dict(t=t0 + 0.65 if i == 0 else t0 + 0.2, zoom=round(size + 0.12, 2),
                                       focus=sp["who"], dur=max(0.4, d - (0.65 if i == 0 else 0.2))))
            if c.state_at(t0 + 0.05)["expression"] in TILT_EXPR and size >= 1.2:
                rolls.append((t0, sp["end"], TILT_DEG if c.draw_pos(t0)[0] < LW / 2.0 else -TILT_DEG))
        if punch:
            shakes.append((max(0.0, sp["end"] - 0.15), 0.5, 0.45))

    # ---- a long walk / run / entrance while nobody talks: the camera goes with the one who moves
    talk = [(sp["start"] - 0.05, sp["end"]) for sp in speech]
    movers = []
    for c in chars.values():
        if c.spec.get("hidden") or c.spec.get("view") == "back":
            continue
        for m in c.moves:
            if m[1] - m[0] < 0.25 or max(abs(m[4] - m[2]), abs(m[5] - m[3])) < MOVE_MIN:
                continue
            if any(a <= m[0] <= b for a, b in talk):
                continue
            movers.append((m[0], m[1], c.name))
    for (m0, m1, name) in movers:
        cam_events.append(dict(t=max(0.0, m0 - 0.02), zoom=1.15, focus=name, dur=0.3))

    # ---- after the last line: the reaction, not an empty wide shot
    if speech:
        last = speech[-1]
        t_free = last["end"]                        # from here the camera is free for the reaction
        later = [m for m in movers if m[0] >= last["start"]]
        if later:                                   # somebody walks after the line: the camera is with them...
            _m0, m1, name = max(later, key=lambda m: m[1])
            gone = not _on_stage(chars[name], m1 + 0.05)
            t_free = m1 - 0.35 if gone else None    # ...and when they have left, it turns to who is still there
        voice_over = any(sp["start"] >= last["start"] and sp.get("who") and chars[sp["who"]].spec.get("hidden")
                         for sp in plan.speech)
        if voice_over:                              # a narrator speaks over what follows: the whole place, as before
            if plan.duration - last["end"] > 0.7:
                cam_events.append(dict(t=last["end"] + 0.2, zoom=1.0, dur=0.5))
        elif t_free is not None and plan.duration - t_free > 0.7:
            t_r = t_free + 0.15
            left = plan.duration - t_free
            here = [c for c in chars.values() if _on_stage(c, t_r) and _on_stage(c, min(plan.duration, t_r + 0.5))]
            acting = [c for c in here if any(
                "action" in e and e["t"] >= last["end"] - 0.05 and e["action"] not in ("idle", "talk", "none", "stand")
                for e in c.events)]
            if len(acting) >= 2:                    # everybody does something (a dance): show them all
                cam_events.append(dict(t=t_free + 0.2, zoom=1.0, dur=0.5))
            elif here:
                pick = acting[0] if acting else None        # the one who reacts with an action (a facepalm)...
                if pick is None:                            # ...or the one who was spoken to
                    others = [c for c in here if c.name != last["who"]]
                    spoke = [sp["who"] for sp in reversed(speech[:-1]) if sp["who"] != last["who"]]
                    pick = next((c for w in spoke for c in others if c.name == w), None)
                    if pick is None and others:
                        sx = chars[last["who"]].draw_pos(t_r)[0]
                        pick = min(others, key=lambda c_: abs(c_.draw_pos(t_r)[0] - sx))
                if pick is not None and (pick.name != last["who"] or later):
                    z, focus = (1.6 if pick.spec.get("kind") in FOCUS_H else 1.5), pick.name
                    if _card_over_faces(plan, t_r):         # looser, and the face below the card
                        fx, fy = pick.focus_at(t_r)
                        z, focus = 1.3, [fx, fy - 170.0]
                    cam_events.append(dict(t=t_r, zoom=z, focus=focus, dur=0.14))
                    cam_events.append(dict(t=t_r + 0.2, zoom=round(z + 0.1, 2), focus=focus,
                                           dur=max(0.4, left - 0.4)))
                    # the script gave the listener no reaction of their own: their face answers the line
                    directed = any(e["t"] >= last["start"] - 0.05 and ("expression" in e or "action" in e)
                                   for e in pick.events)
                    mood = REACTIONS.get(chars[last["who"]].state_at(last["start"] + 0.05)["expression"])
                    if mood and not directed and pick.name != last["who"] and plan.auto_react \
                            and not pick.spec.get("kind"):
                        pick.events.append({"t": t_r + 0.2, "expression": mood})
                        pick.events.sort(key=lambda e: e["t"])
                else:                               # alone: stay on the face a little longer
                    z, focus = round(max(size, 1.2) + 0.2, 2), last["who"]
                    if _card_over_faces(plan, t_free + 0.05):       # looser, and the face below the card
                        fx, fy = chars[last["who"]].focus_at(t_free + 0.05)
                        z, focus = 1.3, [fx, fy - 170.0]
                    cam_events.append(dict(t=t_free + 0.05, zoom=z, focus=focus, dur=max(0.4, left - 0.15)))
    for w in plan.warps:                            # slow motion: pull back to watch it happen
        if w[0] == "slow":
            cam_events.append(dict(t=w[1], zoom=1.0, dur=0.4))
    for fx in plan.effects:                         # a throw: frame the thrower and the target together
        if fx.get("type") == "projectile" and fx.get("src") in chars and fx.get("dst") in chars:
            t0 = max(0.0, fx["from"] - 0.45)
            (x1, y1), (x2, y2) = chars[fx["src"]].draw_pos(t0), chars[fx["dst"]].draw_pos(fx["to"])
            zoom = round(max(1.0, min(1.3, 1080.0 / (abs(x2 - x1) + 420.0))), 2)
            cam_events.append(dict(t=t0, zoom=zoom, focus=[(x1 + x2) / 2.0, (y1 + y2) / 2.0 - 560], dur=0.16))
    for c in chars.values():                        # somebody faints / falls / lies down on the floor: watch it wide
        if c.spec.get("hidden") or c.spec.get("view") == "back":
            continue
        for e in c.events:
            a = e.get("action")
            if a in FALL_ACTIONS and not e.get("on"):
                tf = e["t"] + FALL_ACTIONS[a]
                cam_events[:] = [ev for ev in cam_events if not (tf < ev["t"] < tf + 3.0 and ev.get("focus") == c.name)]
                cam_events.append(dict(t=tf, zoom=1.0, dur=0.35))


def compile_scene(scene, use_tts=True, fps=None, tts_provider=None, voice=None):
    plan = Plan()
    meta = scene.get("meta", {})
    cine = camera_style(meta) == "cine"
    plan.fps = int(fps or meta.get("fps", 30))
    plan.fade_in = float(meta.get("fade_in", 0.0))
    plan.fade_out = float(meta.get("fade_out", 0.0))
    plan.background = scene.get("background", {"type": "plain"})

    # ---- one scale for the whole shot ----
    # framing: "wide" = everybody small enough that the vehicles fit in the frame in proportion; "inside" = people big
    # and the vehicle drawn huge around its driver; "medium" = people big (default when there is no vehicle).
    kinds_ = set()
    for raw_ in scene.get("timeline", []):
        for key_ in ("obj", "ride"):
            d_ = raw_.get(key_)
            k_ = objects.resolve_kind(d_.get("kind", "")) if isinstance(d_, dict) else None
            if k_ in objects.PERSON_R:
                kinds_.add(k_)
    framing = scene.get("framing") or meta.get("framing")
    if framing not in ("wide", "medium", "inside", "ots"):
        framing = "wide" if any(k_ in objects.VEHICLES for k_ in kinds_) else "medium"
    world = 1.0
    if framing == "wide" and kinds_:
        widest = max(objects.SPRITE_LEN[k_] / objects.PERSON_R[k_] for k_ in kinds_) * objects.REF_SCALE
        world = clamp(900.0 / widest, 0.22, 1.0)
    plan.angle = shot_angle(scene, framing)
    if framing == "medium":
        # people (and their props / set pieces) a bit bigger than the painted place, and more so when the shot's
        # angle shows the place closer: otherwise the room and its furniture dwarf the characters
        n_vis = sum(1 for v in scene.get("characters", {}).values() if isinstance(v, dict) and not v.get("hidden"))
        base_ = float(meta.get("people_scale", PEOPLE_SCALE if n_vis < 3 else PEOPLE_SCALE_3))   # 3 need room
        world = base_ * plan.angle["zoom"] ** 0.5
    plan.framing, plan.world = framing, world
    plan.cut_in = bool(scene.get("cut_in"))

    # ---- characters ----
    cdefs = assign_faces(scene.get("characters", {}))
    names = list(cdefs.keys())
    visible = [nm for nm in names if not cdefs[nm].get("hidden")]       # a hidden one is only a voice (narrator)
    n = len(visible)
    slots = SLOTS.get(n, SLOTS[3])
    auto = ["left", "center", "right"] if n == 3 else (["left", "right"] if n == 2 else ["center"])
    chars = {}
    for i, name in enumerate(names):
        spec = dict(cdefs[name])
        vi = visible.index(name) if name in visible else 0
        slot = spec.get("slot") or (auto[vi] if vi < len(auto) else "center")
        x = spec.get("x", slots.get(slot, 540))
        y = spec.get("y", GROUND_Y)
        chars[name] = Char(name, spec, float(x), float(y), i)
        chars[name].scale *= world
    if framing == "ots":
        place_over_shoulder(chars)
        for c_ in chars.values():               # the speaker facing us a bit bigger too (still well behind the back)
            if c_.spec.get("view") != "back":
                c_.scale *= 1.1
    plan.chars = chars

    # ---- timeline ----
    # ---- set pieces (door, bed, sofa, fan...) ----
    plan.sets = []
    for i, ob in enumerate(scene.get("sets", [])):
        ob = dict(ob)
        ob.setdefault("id", "%s%d" % (ob.get("type", "set"), i + 1))
        if ob.get("fit"):                           # drawn over the painted place (the jail door): goes with it
            fit_to_angle(ob, plan.angle)
        elif plan.world != 1.0:
            ob["scale"] = float(ob.get("scale", 1.0)) * plan.world      # a sofa grows with the people sitting on it
        plan.sets.append(ob)
    set_by_id = {o["id"]: o for o in plan.sets}
    plan.set_events = []
    plan.lights = []
    plan.warps = []                                 # slow motion / freeze frames (story time)
    if scene.get("lights") not in (None, "on"):     # a shot that starts in the dark (lights went off earlier)
        v = scene["lights"]
        plan.lights.append((-1.0, float({"off": 0.32, "dim": 0.6}.get(v, v) if not isinstance(v, (int, float)) else v)))

    lead = float(scene.get("lead_in", 0.0))        # "hook first": the story starts after the hook card
    cursor = lead
    gap = float(meta.get("line_gap", 0.35))
    dialogue = meta.get("dialogue", "bubble")       # bubble | subtitle | both | none: how the spoken words show
    plan.sfx = []
    plan.overlays = []
    plan.effects = []
    plan.objects = {}
    plan.warnings = []
    for c_ in chars.values():
        c_.world = plan.objects
    plan.world_chars = list(chars.values())
    cam_events = []
    shot_events = []        # camera moves from shot words on action lines (do not switch the auto camera off)
    cam_hold = []           # (t0, t1): a zoom / reveal is playing, the automatic camera keeps out
    shakes = []
    plan.speech = []
    warned = [False]
    plan_end = 0.0

    # voice: precomputed for the whole video by prepare_voice(); a lone scene prepares its own
    if voice is None:
        voice = prepare_voice([scene], use_tts, tts_provider)[0]
    batch, per_line_edge = voice["paths"], voice["edge"]

    for ti, raw in enumerate(scene.get("timeline", [])):
        ev = dict(raw)
        t = float(ev["t"]) if "t" in ev and ev["t"] is not None else cursor
        if lead and "t" in ev and ev["t"] is not None and not (float(ev["t"]) == 0.0 and "who" not in ev):
            t += lead                               # (the sound / shake at 0 stays with the hook card)
        if ev.get("interrupt") and "say" in ev and ev.get("t") is None and plan.speech:
            ov = 0.35 if ev["interrupt"] is True else float(ev["interrupt"])
            t = max(plan.speech[-1]["start"] + 0.3, cursor - gap - ov)   # cuts in before the other one finishes
        plan_end = max(plan_end, t)
        if "wait" in ev:
            cursor = t + float(ev["wait"])
            plan_end = max(plan_end, cursor)
            continue
        who = _norm_who(ev.get("who"), names) if ("who" in ev or any(k in ev for k in CHAR_ATTRS + ("say", "move"))) else []
        who = [w for w in who if w in chars]

        for w in who:
            c = chars[w]
            e = {"t": t}
            for key in CHAR_ATTRS:
                if key in ev:
                    e[key] = ev[key]
            if "emotion" in ev:
                e["expression"] = ev["emotion"]
            if len(e) > 1:
                c.events.append(e)
            if ev.get("depth") in DEPTHS:
                k0, dy0 = c.depth_at(t)
                k1, dy1 = DEPTHS[ev["depth"]]
                c.depth.append((t, k0, dy0, k1, dy1))
            if ev.get("on") in set_by_id:            # sit / lie on a set piece: snap onto it
                ob = set_by_id[ev["on"]]
                x0, y0 = c.pos_at(t)
                dx = float(ev.get("on_dx", 0))
                if ob.get("type") in ("bed", "khaat") and ev.get("action", "") in ("lie_down", "lie", "sleep_lie", "rofl"):
                    head = 1 if ob.get("flip") else -1           # head on the pillow end
                    dx = dx or -head * 400 * float(ob.get("scale", 1.0))
                    c.events.append({"t": t, "dir": head})
                c.moves.append((t, t + 0.001, x0, y0, float(ob.get("x", 540)) + dx, float(ob.get("y", 1700)) + 1,
                                False))
            if "move" in ev:
                m = ev["move"]
                x0, y0 = c.pos_at(t)
                dur = float(m.get("dur", 0.8))
                c.moves.append((t, t + dur, x0, y0, float(m.get("x", x0)), float(m.get("y", y0)),
                                bool(m.get("run") or ev.get("action") == "run")))
            if isinstance(ev.get("entry"), dict) and ev["entry"].get("style") in ENTRY_STYLES:
                plan_end = max(plan_end, t + compile_entry(plan, c, ev["entry"], t))
            if isinstance(ev.get("leave"), dict):
                plan_end = max(plan_end, t + compile_leave(plan, c, ev["leave"], t))

        if "say" in ev and who:
            c = chars[who[0]]
            text = str(ev["say"])
            speak = ev.get("speak", text)
            v = dict(c.voice)
            v.update(ev.get("voice", {}) if isinstance(ev.get("voice"), dict) else {})
            path, dur = None, None
            if ti in batch:
                path = audio.trim_silence(batch[ti]) if meta.get("trim_voice", True) else batch[ti]
                dur = audio.audio_duration(path)
            elif per_line_edge and ev.get("tts", True):
                rate, pitch = v.get("rate", "+0%"), v.get("pitch", "+0Hz")
                if meta.get("emotion_voice", True):  # an angry line comes faster, a sad one slower and lower...
                    d_rate, d_pitch = audio.EMOTION_VOICE.get(ev.get("expression") or c.state_at(t)["expression"],
                                                              (0, 0))
                    rate, pitch = audio.shift_value(rate, d_rate, "%"), audio.shift_value(pitch, d_pitch, "Hz")
                path = audio.synth_tts(speak, v.get("name"), rate, pitch)
                if path and meta.get("trim_voice", True):
                    path = audio.trim_silence(path)
                if path:
                    dur = audio.audio_duration(path)
                elif not warned[0]:
                    print("  [tts] unavailable -> using estimated timing, video will have no voice", file=sys.stderr)
                    warned[0] = True
            if dur is None:
                dur = float(ev.get("duration", audio.estimate_duration(speak)))
            bubble = ev.get("bubble", True)
            if dialogue == "none" or (dialogue == "subtitle" and bubble is True):
                bubble = False                      # the studio page's "Dialogue text" option
            subtitle = (ev.get("subtitle") or (dialogue in ("subtitle", "both") and ev.get("bubble", True) is True)) \
                and dialogue != "none"
            frz = next((i_ for i_, w_ in enumerate(plan.warps) if w_[0] == "freeze" and abs(w_[1] - t) < 0.02), None)
            if frz is not None:                     # said over a freeze frame: the picture waits for the line
                w_ = plan.warps[frz]
                plan.warps[frz] = ("freeze", w_[1], max(w_[2], dur + 0.35), w_[3])
                span, step = 0.05, 0.06             # (story time stands still while it is said)
            else:
                span, step = dur + 0.12, dur + gap
            sp = dict(who=c.name, text=text, start=t, end=t + span, audio=path, bubble=bubble,
                      shot=ev.get("shot"))
            if frz is not None:
                sp["frozen"] = True
            c.speech.append(sp)
            plan.speech.append(sp)
            if ev.get("action") in BURST_ACTIONS and dur > BURST_ACTIONS[ev["action"]] + 0.4:
                c.events.append({"t": t + BURST_ACTIONS[ev["action"]], "action": "idle", "_settle_from": t})
            if ev.get("interrupt") and len(plan.speech) > 1:
                prev = plan.speech[-2]
                if prev["end"] > t and prev["who"] != sp["who"]:      # the other person gets cut off
                    prev["end"] = t + 0.1
                    prev["cut"] = t + 0.1 - prev["start"]
            if subtitle:                            # voice-over / subtitle mode: the words at the bottom while spoken
                plan.overlays.append({"text": text, "style": "subtitle", "from": t,
                                      "pos": "bottom" if ev.get("subtitle") else          # (narrator)
                                      "upper" if c.spec.get("kind") in FOCUS_H else "lower",  # not over a dog's body
                                      "to": t + span})
                if frz is not None:                 # story time stands still: no fade, just there
                    plan.overlays[-1]["anim"] = "none"
            cursor = max(cursor, t + step)
            plan_end = max(plan_end, t + span)
        if "hold" in ev:
            cursor = max(cursor, t + float(ev["hold"]))
            plan_end = max(plan_end, t + float(ev["hold"]))

        if "sfx" in ev:
            p = audio.sfx_path(ev["sfx"])
            if p:
                plan.sfx.append(dict(t=t, path=p, volume=float(ev.get("volume", 0.8))))
        if "overlay" in ev:
            o = dict(ev["overlay"])
            o.setdefault("from", t)
            if cine and o.get("cta") and list(o.get("pos") or []) == [540, 640]:
                o["pos"] = [540, CTA_Y]             # (it used to sit right on the faces)
            plan.overlays.append(o)
        if "set" in ev:
            for sid in (ev["set"] if isinstance(ev["set"], list) else [ev["set"]]):
                plan.set_events.append({"t": t, "set": sid, "state": ev.get("state"), "move": ev.get("move")})
                if ev.get("state") == "broken" and set_by_id.get(sid, {}).get("type") == "jail_door":
                    for name_, vol_ in (("thud", 1.0), ("glass_break", 0.35)):      # bars torn off: a crash
                        path_ = audio.sfx_path(name_)
                        if path_:
                            plan.sfx.append(dict(t=t, path=path_, volume=vol_))
                    shakes.append((t, 0.7, 0.45))
        if "lights" in ev:
            v = ev["lights"]
            plan.lights.append((t, float({"on": 1.0, "off": 0.32, "dim": 0.6}.get(v, v)
                                         if not isinstance(v, (int, float)) else v)))
        if "fx" in ev:
            for raw_fx in (ev["fx"] if isinstance(ev["fx"], list) else [ev["fx"]]):
                fx = effects.normalize(raw_fx, t)
                if "who" not in fx and who:
                    fx["who"] = who[0]
                plan.effects.append(fx)
        if ev.get("action") == "throw" and ev.get("at") in chars and who:
            # the held prop flies from the thrower's hand to the target, who reacts on impact
            src, dst = who[0], ev["at"]
            release, obj = t + 0.42, ev.get("throw_prop") or ev.get("prop") or "chappal"
            arrive = release + float(ev.get("flight", 0.55))
            plan.effects.append({"type": "projectile", "src": src, "dst": dst, "prop": obj, "from": release,
                                 "to": arrive, "arc": ev.get("arc", 160)})
            chars[src].events.append({"t": release, "prop": ""})
            if ev.get("hit", True):
                chars[dst].events.append({"t": arrive, "action": "hit_react"})
                hp = audio.sfx_path(ev.get("hit_sfx", "thud"))
                if hp:
                    plan.sfx.append(dict(t=arrive, path=hp, volume=0.8))
                plan.effects.append({"type": "pow", "who": dst, "text": ev.get("hit_text", "THAK!"),
                                     "from": arrive, "to": arrive + 0.6})
            plan_end = max(plan_end, arrive + 0.6)
        if ev.get("ride") and who:
            hold_ = 0.0
            for w in who:
                hold_ = max(hold_, compile_ride(plan, chars[w], ev["ride"], t))
            plan_end = max(plan_end, t + hold_)
            cursor = max(cursor, t + hold_)
        if "getoff" in ev and who:
            hold_ = 0.0
            for w in who:
                hold_ = max(hold_, compile_getoff(plan, chars[w], ev["getoff"], t))
            plan_end = max(plan_end, t + hold_)
            cursor = max(cursor, t + hold_)
        if "obj" in ev:
            ev_hold = compile_obj(plan, ev["obj"], t, plan.warnings)
            plan_end = max(plan_end, t + ev_hold)
            cursor = max(cursor, t + ev_hold)
        if "shot" in ev and "say" not in ev and SHOT_ALIASES.get(ev["shot"], ev["shot"]) in SHOT_ZOOM:
            shot_events.append(shot_camera(ev["shot"], t, chars, who, dur=0.3))
        if "slowmo" in ev:                          # story time slows down here (the voice keeps its speed)
            sm = ev["slowmo"] if isinstance(ev["slowmo"], dict) else {"rate": ev["slowmo"]}
            rate = float(sm.get("rate", 0.35)) if not isinstance(sm.get("rate"), bool) else 0.35
            plan.warps.append(("slow", t, max(0.05, min(1.0, rate)), float(sm.get("dur", 1.5))))
        if "freeze" in ev:                          # the picture stops ("yup, that's me")
            fr = ev["freeze"] if isinstance(ev["freeze"], dict) else {"dur": ev["freeze"]}
            plan.warps.append(("freeze", t, float(fr.get("dur", 1.2)) if not isinstance(fr.get("dur"), bool) else 1.2,
                               fr.get("style", "grey")))
        if "camera" in ev:
            cam = dict(ev["camera"])
            cam["t"] = t
            if "shake" in cam:
                shakes.append((t, float(cam["shake"]), float(cam.get("shake_dur", 0.5))))
            if cam.get("punch"):                    # quick snap zoom onto a face (the automatic camera stays on)
                shot_events.append({"t": t, "zoom": float(cam.get("zoom", 1.75)), "focus": cam["punch"],
                                    "dur": float(cam.get("dur", 0.1))})
                if cam.get("back"):
                    shot_events.append({"t": t + float(cam["back"]), "zoom": 1.0, "dur": 0.3})
                cam_hold.append((t - 0.01, t + float(cam.get("back") or 1.0) + 0.3))
            elif cam.get("reveal"):                 # start close, pull back to the whole place
                who_ = cam["reveal"] if isinstance(cam["reveal"], str) else None
                shot_events.append({"t": t, "zoom": float(cam.get("from", 1.8)), "focus": who_, "dur": 0.001})
                shot_events.append({"t": t + 0.002, "zoom": 1.0, "dur": float(cam.get("dur", 1.6))})
                cam_hold.append((t - 0.06, t + float(cam.get("dur", 1.6)) + 0.1))
            elif "zoom" in cam or "focus" in cam:
                cam_events.append(cam)

    plan.overlays += static_overlays(scene)
    bgs = plan.background if isinstance(plan.background, dict) else {"type": plan.background}
    weather = list(bgs.get("weather", []))
    if bgs.get("time") == "rain":
        weather.append("rain")
    for w in weather:                                   # SCENE: <place> rain / fog / snow / fireflies / leaves
        if not any(e.get("type") == w for e in plan.effects):
            plan.effects.append(effects.normalize({"type": w}, 0.0))
    for raw_fx in scene.get("effects", []):
        plan.effects.append(effects.normalize(raw_fx, float(raw_fx.get("from", 0.0)) if isinstance(raw_fx, dict) else 0.0))
    if scene.get("chat"):
        plan_end = max(plan_end, compile_chat(plan, scene["chat"]))

    for c in chars.values():
        c.events.sort(key=lambda e: e["t"])
        # a settle-into-talking is dropped when the script gives this character another action before it
        c.events = [e for e in c.events if "_settle_from" not in e or not any(
            e2 is not e and "action" in e2 and e["_settle_from"] < e2["t"] <= e["t"] for e2 in c.events)]
        c.speech.sort(key=lambda s_: s_["start"])

    # ---- duration ----
    if meta.get("duration"):
        plan.duration = float(meta["duration"])
    else:
        last = max(plan_end, float(meta.get("min_duration", 4.0)))
        plan.duration = round(last + float(meta.get("tail", 0.9)), 2)
    plan.n_frames = int(round(plan.duration * plan.fps))

    # ---- camera segments ----
    if cine:                                        # off a bed: back inside the picture
        stand_up_in_frame(chars, set_by_id)
    plan.camera, plan.rolls, plan.drift = ("cine" if cine else "classic"), [], False
    plan.auto_react = bool(meta.get("auto_react", True))
    if meta.get("auto_camera", True) and not cam_events and plan.framing == "medium":     # wide / inside are composed shots
        if cine:
            auto_camera_cine(plan, chars, cam_events, shakes, plan.rolls)
            plan.drift = not scene.get("chat")      # the camera never stands completely still
        else:
            auto_camera(plan, chars, cam_events, shakes)
        cam_events[:] = [c_ for c_ in cam_events if not any(h0 <= c_["t"] <= h1 for h0, h1 in cam_hold)]
        plan.rolls = [r for r in plan.rolls if not any(h0 <= r[0] <= h1 for h0, h1 in cam_hold)]
    cam_events += shot_events
    segs = []
    z, cx, cy = 1.0, LW / 2.0, LH / 2.0
    was = None                                      # cine: who the camera was following before this move
    for cam in sorted(cam_events, key=lambda c_: c_["t"]):
        tz = float(cam.get("zoom", z))
        f = cam.get("focus")
        follow = None
        if isinstance(f, str) and f in chars:
            tc = chars[f].focus_at(cam["t"])
            follow = f if cine else None
        elif isinstance(f, (list, tuple)):
            tc = (float(f[0]), float(f[1]))
        elif tz == 1.0:
            tc = (LW / 2.0, LH / 2.0)
        else:
            tc = (cx, cy)
            follow = was                            # only the zoom changes: keep following the same one
        dur = float(cam.get("dur", 0.35))
        seg = (cam["t"], cam["t"] + dur, z, tz, (cx, cy), tc)
        segs.append(seg + (follow, was) if cine else seg)
        z, cx, cy, was = tz, tc[0], tc[1], follow
    plan.cam_segments = segs
    plan.shakes = shakes

    # ---- audio ----
    m = scene.get("music") or meta.get("music")
    plan.music = compile_music(m, plan.duration)
    plan.bpm = float(meta.get("bpm") or music_bpm(m) or 96)     # dances move on this beat
    # a sound bed around the scene (rain, street, office, night, jungle, crowd, wind, sea), looped under everything
    plan.ambience = []
    amb = scene.get("ambience")
    bg = scene.get("background") if isinstance(scene.get("background"), dict) else {}
    if amb is None and bg.get("time") == "rain":
        amb = "rain"                                # it rains: you hear it
    for a in (amb if isinstance(amb, list) else [amb] if amb else []):
        a = {"type": a} if isinstance(a, str) else dict(a)
        if a.get("type") in audio.AMBIENCE:
            plan.ambience.append(dict(path=audio.ambience_path(a["type"]), volume=float(a.get("volume", 0.22)),
                                      start=0.0, dur=plan.duration))
    return plan


def music_bpm(m):
    return m.get("bpm", 104) if isinstance(m, dict) and m.get("type") == "beat" else None


def static_overlays(scene):
    """The scene's `overlays` list plus the `caption` shorthand."""
    out = [dict(o) for o in scene.get("overlays", [])]
    if "caption" in scene:
        c = dict(scene["caption"]) if isinstance(scene["caption"], dict) else {"text": scene["caption"]}
        c.setdefault("style", "caption_box")
        c.setdefault("pos", "top")
        out.append(c)
    return out


def compile_music(m, duration):
    if not m:
        return None
    if isinstance(m, str):
        m = {"path": m}
    if m.get("type") == "gemini":                       # no song was made (frame preview, no network): the beat
        return compile_music(m.get("fallback"), duration)
    vol = float(m.get("volume", 0.35))
    if m.get("type") == "beat":
        p = audio.beat_path(float(m.get("bpm", 104)), duration, m.get("style", "desi"), seed=m.get("seed"))
    else:
        p = asset_path(m.get("path"))
    return dict(path=p, volume=vol, generated=m.get("type") == "beat") if p else None


DIALOGUE_MODES = ("bubble", "subtitle", "both", "none")
HOOK_MODES = ("over", "first", "off")
HOOK_LEAD = 1.7                                     # seconds the hook card has the screen to itself ("first")


MASCOTS = {"bhoot": "bhoot", "ghost": "bhoot", "billi": "billi", "cat": "billi", "chooha": "chooha",
           "chuha": "chooha", "mouse": "chooha"}


def mascot_kind(value):
    """`MASCOT: bhoot` / {"kind": "billi"} / "off" -> bhoot | billi | chooha | None."""
    if isinstance(value, dict):
        value = value.get("kind")
    return MASCOTS.get(str(value or "").strip().lower())


LOOP_HOLD = 0.6              # LOOP: seconds the last reaction is held before the reel whips back to its start


def apply_loop(scene):
    """LOOP: the reel plays round and round without a visible end (people watch it twice). On a copy: the CTA end
    card goes (an end card says "the end"; its text goes into the post caption instead), the last reaction is held
    only a moment, no fades. The renderer then whips the last moment back into the opening frame (render.Looped)."""
    import copy
    scene = copy.deepcopy(scene)
    if scene.get("loop") is True and scene.get("_looped"):
        return scene
    scene["loop"], scene["_looped"] = True, True
    ctas = []

    def keep(o):
        if isinstance(o, dict) and o.get("cta"):
            ctas.append(str(o.get("text", "")))
            return False
        return True
    scene["overlays"] = [o for o in scene.get("overlays", []) if keep(o)]
    for sc in scene.get("scenes", []) or [scene]:
        if sc is not scene:
            sc["overlays"] = [o for o in sc.get("overlays", []) if keep(o)]
        tl = []
        for ev in sc.get("timeline", []):
            if isinstance(ev.get("overlay"), dict) and not keep(ev["overlay"]):
                ev = {k: v for k, v in ev.items() if k not in ("overlay", "sfx", "volume")}
                ev["hold"] = min(float(ev.get("hold", LOOP_HOLD)), LOOP_HOLD)
            tl.append(ev)
        if "timeline" in sc:
            sc["timeline"] = tl
    meta = scene.setdefault("meta", {})
    meta["fade_in"] = meta["fade_out"] = 0
    if ctas:
        post = scene.setdefault("post", {})
        cap = str(post.get("caption") or "").strip()
        extra = " ".join(c for c in ctas if c and c not in cap)
        post["caption"] = (cap + "\n" + extra).strip() if extra else cap
    return scene


def apply_options(scene, dialogue=None, hook=None):
    """The studio page's video options, on a copy of the scene.
    dialogue: bubble (speech bubbles) | subtitle (words at the bottom) | both | none (voice only).
    hook: over (the hook card over the first line, the default) | first (hook card first, then the story) | off."""
    import copy
    scene = copy.deepcopy(scene)
    if dialogue and dialogue != "bubble":
        scene.setdefault("meta", {})["dialogue"] = dialogue
    if hook == "off":
        drop = lambda ovs: [o for o in ovs if o.get("style") != "hook"]      # noqa: E731
        scene["overlays"] = drop(scene.get("overlays", []))
        for sc in scene.get("scenes", []):
            if sc.get("overlays"):
                sc["overlays"] = drop(sc["overlays"])
    elif hook == "first":
        first = scene["scenes"][0] if scene.get("scenes") else scene
        first["lead_in"] = HOOK_LEAD
        for o in scene.get("overlays", []) + first.get("overlays", []):
            if o.get("style") == "hook" and float(o.get("from", 0)) < 0.5:
                o["to"] = HOOK_LEAD + 0.1           # gone as the first line starts
    return scene


def start_xs(scene):
    """Where everybody stands when a scene starts (logical x), placed the way compile_scene places them."""
    cdefs = scene.get("characters", {})
    names = list(cdefs.keys())
    visible = [nm for nm in names if not cdefs[nm].get("hidden")]
    n = len(visible)
    slots = SLOTS.get(n, SLOTS[3])
    auto = ["left", "center", "right"] if n == 3 else (["left", "right"] if n == 2 else ["center"])
    out = {}
    for name in names:
        spec = cdefs[name]
        vi = visible.index(name) if name in visible else 0
        slot = spec.get("slot") or (auto[vi] if vi < len(auto) else "center")
        out[name] = float(spec.get("x", slots.get(slot, 540)))
    return out


def drop_last_exit(timeline, who):
    """The scene before a one-take walk ends with `who` leaving the shot: they walk on into the next place instead,
    so that exit goes. Returns (timeline, side, fast); side is None when the scene does not end with their exit."""
    for i in range(len(timeline) - 1, -1, -1):
        ev = timeline[i]
        if "wait" in ev or ("who" not in ev and "say" not in ev):
            continue                                # sounds, waits, screen cards
        if ev.get("who") != who:
            return timeline, None, False
        lv, mv = ev.get("leave"), ev.get("move")
        if isinstance(lv, dict):
            side, fast = (lv.get("side") if lv.get("side") in ("left", "right") else "left"), True
        elif isinstance(mv, dict) and not -40 <= float(mv.get("x", 540)) <= LW + 40:
            side, fast = ("left" if float(mv["x"]) < 0 else "right"), bool(mv.get("run") or ev.get("action") == "run")
        else:
            return timeline, None, False
        rest = {k: v for k, v in ev.items() if k not in ("leave", "move", "hold", "facing")}
        tl = list(timeline)
        if set(rest) <= {"t", "who"}:
            del tl[i]
        else:
            tl[i] = rest
        return tl, side, fast
    return timeline, None, False


# keys of a multi-scene file that belong to the whole video, not to one scene
VIDEO_KEYS = ("scenes", "music", "caption", "overlays", "post", "hook", "vars", "name", "about", "transition",
              "loop", "mascot")


TITLE_LEAD = 1.1            # cine: seconds of the full-screen "Agle din..." card before a titled shot


def split_scenes(scene):
    """A multi-scene file ({"scenes": [...]}) -> list of ordinary single-scene dicts.

    Every scene gets the shared `characters` (only those in its `cast`, if given,
    with its own `characters` entries merged on top), the shared `meta`, and its own
    background / timeline / overlays / caption. A scene `title` shows as a card for
    its first 1.4 seconds ("Agle din...").
    """
    scene = dict(scene, characters=assign_faces(scene.get("characters", {})))   # one face per character, all video
    if not scene.get("scenes"):
        return [scene]
    base = {k: v for k, v in scene.items() if k not in VIDEO_KEYS}
    base_meta = {k: v for k, v in scene.get("meta", {}).items() if k != "duration"}
    base_meta.setdefault("tail", 0.5)
    if music_bpm(scene.get("music")) and "bpm" not in base_meta:     # scenes dance to the shared music
        base_meta["bpm"] = music_bpm(scene.get("music"))
    cast_all = scene.get("characters", {})
    out = []
    shot_no = 0
    for sc in scene["scenes"]:
        shot_no = shot_no + 1 if sc.get("cut_in") else 0           # CUTs in one place: each a new camera angle
        sub = deep_merge(base, {k: v for k, v in sc.items() if k not in ("cast", "characters", "meta", "title")})
        sub["meta"] = dict(base_meta, **sc.get("meta", {}))
        cast = sc.get("cast", []) if sc.get("chat") else (sc.get("cast") or list(cast_all.keys()))
        pan = sc.get("pan") if out and isinstance(sc.get("pan"), dict) else None
        if pan and pan.get("who") in cast_all:
            # one take: `who` walks out of the last place and on into this one, the camera going with them
            who = pan["who"]
            tl, side, fast = drop_last_exit(out[-1].get("timeline", []), who)
            out[-1]["timeline"] = tl
            pan = dict(pan, dir=pan.get("dir") or side or "right", run=bool(pan.get("run", fast)))
            if who not in cast:                     # (they come in from the side they walked towards)
                cast = ([who] + list(cast)) if pan["dir"] == "right" else (list(cast) + [who])
            if sc.get("title"):
                pan["title"] = sc["title"]
        elif "pan" in sc:
            pan = None
        chars = {n: dict(cast_all.get(n, {})) for n in cast}
        for n, spec in sc.get("characters", {}).items():
            chars[n] = dict(chars.get(n, {}), **spec)
        sub["characters"] = chars
        sub.pop("pan", None)
        if pan:
            sub["pan"] = pan                        # (its title shows while they walk in: Sequence)
        if shot_no and "angle" not in sub:
            sub["angle"] = shot_no
        if sc.get("title") and pan:
            pass                                    # (no full-screen card in the middle of one take)
        elif sc.get("title") and camera_style(sub["meta"]) == "cine":
            # its own short full-screen card before the shot (over the shot it covered the first speech bubble)
            sub["lead_in"] = max(float(sub.get("lead_in", 0.0)), TITLE_LEAD)
            sub["overlays"] = list(sub.get("overlays", [])) + [
                {"type": "timecard", "text": sc["title"], "from": 0.0, "to": TITLE_LEAD, "color": [40, 40, 48]}]
        elif sc.get("title"):
            sub["overlays"] = list(sub.get("overlays", [])) + [
                {"text": sc["title"], "style": "card", "pos": "upper", "from": 0.0, "to": 1.4, "color": [40, 40, 48]}]
        out.append(sub)
    return out


def camera_at(plan, t):
    """Returns (zoom, cx, cy, shake_dx, shake_dy)."""
    z, cx, cy = 1.0, LW / 2.0, LH / 2.0
    for (t0, t1, z0, z1, c0, c1, *fol) in plan.cam_segments:
        if t < t0:
            break
        if fol:                                     # cine: stay with the one the camera looks at (a little behind)
            if fol[1] in plan.chars:
                c0 = plan.chars[fol[1]].focus_at(max(0.0, t0 - FOLLOW_LAG))
            if fol[0] in plan.chars:
                c1 = plan.chars[fol[0]].focus_at(max(0.0, t - FOLLOW_LAG))
        e = ease_in_out((t - t0) / max(1e-6, t1 - t0))
        z, cx, cy = lerp(z0, z1, e), lerp(c0[0], c1[0], e), lerp(c0[1], c1[1], e)
    if getattr(plan, "drift", False):               # cine: a slow breath, so a held shot is never a frozen picture
        z = max(z, 1.0) * (1.014 + 0.010 * math.sin(t * 0.83 + 0.6))
        cx += 7.0 * math.sin(t * 0.61 + 1.9)
        cy += 5.0 * math.sin(t * 0.47)
    w = wide_weight(plan, t)
    if w:                                           # a one-take walk into the next place: the whole picture
        z, cx, cy = lerp(z, 1.0, w), lerp(cx, LW / 2.0, w), lerp(cy, LH / 2.0, w)
    dx = dy = 0.0
    for (ts, amp, dur) in plan.shakes:
        if ts <= t < ts + dur:
            k = (1 - (t - ts) / dur) * (1.0 - w)
            dx += amp * 22 * k * math.sin(95 * t)
            dy += amp * 16 * k * math.cos(83 * t)
    return z, cx, cy, dx, dy


def wide_weight(plan, t):
    """0..1: how far the camera has eased out to the whole picture. plan.wide = [(t0, t1, ease_in, ease_out)]: wide
    from t0 to t1, easing there over ease_in seconds before and back over ease_out seconds after (a one-take walk
    from one place into the next starts and ends on the whole picture)."""
    w = 0.0
    for (a, b, rin, rout) in getattr(plan, "wide", ()):
        if a - rin <= t < a:
            w = max(w, ease_in_out((t - (a - rin)) / rin))
        elif a <= t <= b:
            return 1.0
        elif b < t < b + rout:
            w = max(w, 1.0 - ease_in_out((t - b) / rout))
    return w


def camera_roll(plan, t):
    """Degrees the frame is tilted at time t (cine: a dutch angle on an angry / scared line); 0 = level."""
    for (t0, t1, deg) in getattr(plan, "rolls", ()):
        if t0 <= t < t1 + 0.25:
            return deg * ease_in_out((t - t0) / 0.22) * (1.0 - ease_in_out((t - t1) / 0.25))
    return 0.0


def camera_whip(plan, t, dt):
    """While the camera swings from one person to another (a move of 0.1 s or more, not a real cut): the earlier
    moment to measure its travel from. None when it is not swinging."""
    for seg in plan.cam_segments:
        if seg[0] < t <= seg[1] + dt and seg[1] - seg[0] >= 0.1:
            return max(seg[0], t - dt)
    return None

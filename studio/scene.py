"""Compile a scene.json dict into a render plan (timeline, speech, audio, camera)."""
import math
import sys

from . import audio, gemini_tts, objects, rides
from .characters import color_of, resolve_spec
from .util import LW, LH, asset_path, clamp, deep_merge, ease_in_out, lerp

SLOTS = {
    1: {"center": 540},
    2: {"left": 300, "right": 780, "center": 540},
    3: {"left": 190, "center": 540, "right": 890},
}
GROUND_Y = 1700
SHOT_ZOOM = {"wide": 1.0, "medium": 1.3, "close": 1.7, "two_shot": 1.3}
SHOT_ALIASES = {"closeup": "close", "close_up": "close", "twoshot": "two_shot", "2shot": "two_shot"}
DEPTHS = {"near": (1.3, 110.0), "mid": (1.0, 0.0), "far": (0.75, -150.0)}   # (size multiplier, feet offset in px)
CHAR_ATTRS = ("action", "expression", "prop", "label", "look", "facing", "style", "point", "dir",
              "lean", "speed", "intensity", "hands", "tint")


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


class Char:
    def __init__(self, name, spec, x, ground_y, index):
        self.name = name
        self.spec = spec
        self.x = x
        self.y = ground_y
        self.scale = float(resolve_spec(spec).get("scale", 1.0))
        self.phase = float(spec.get("phase", index * 0.9))
        self.events = []        # sorted by t
        self.moves = []         # (t0, t1, x0, y0, x1, y1)
        self.speech = []        # dicts
        self.depth = []         # (t, k0, dy0, k1, dy1): step towards / away from the camera
        self.rides = []         # {"t0", "obj", "seat", "t_off", "land_x", "land_y"}: sitting on a vehicle
        self.world = {}         # the scene's objects (set by compile_scene)
        self._rf = (None, None)
        v = spec.get("voice", {})
        self.voice = v if isinstance(v, dict) else {"name": v}

    def pos_at(self, t):
        x, y = self.x, self.y
        for (t0, t1, x0, y0, x1, y1) in self.moves:
            if t < t0:
                break
            e = ease_in_out((t - t0) / max(1e-6, t1 - t0))
            x, y = lerp(x0, x1, e), lerp(y0, y1, e)
        return x, y

    def depth_at(self, t):
        """(size multiplier, feet offset) - 1.0 / 0 on the normal ground line."""
        k, dy = 1.0, 0.0
        for (t0, k0, dy0, k1, dy1) in self.depth:
            if t < t0:
                break
            e = ease_in_out((t - t0) / 0.5)
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
        return x, y - 560 * self.depth_at(t)[0]

    def state_at(self, t):
        st = dict(action="idle", action_t0=0.0, expression=self.spec.get("expression", "neutral"),
                  prop=self.spec.get("prop"), label=None, look=self.spec.get("look"),
                  facing=self.spec.get("facing", "front"),
                  speed=1.0, intensity=1.0, opts={}, talking=None)
        for ev in self.events:
            if ev["t"] > t + 1e-9:
                break
            if "action" in ev:
                st["action"] = ev["action"]
                st["action_t0"] = ev["t"]
                st["speed"], st["intensity"] = 1.0, 1.0
                st["opts"] = {}
            for key in ("expression", "prop", "label", "look", "facing"):
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
        out.append(dict(ti=ti, text=text, voice=gemini_tts.voice_for(v), pitch=v.get("pitch"), rate=v.get("rate")))
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
    if provider != "gemini":
        return [{"paths": {}, "edge": True} for _ in scenes]
    per_scene = [collect_lines(sc) for sc in scenes]
    flat = [it for lines in per_scene for it in lines]
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
            cam_events.append(dict(t=max(0.0, t0 - 0.05), zoom=size, focus=sp["who"], dur=0.16))
        if d > 1.0:                                 # slow push-in while the line is spoken
            cam_events.append(dict(t=t0 + 0.65 if i == 0 else t0 + 0.2, zoom=round(size + 0.12, 2),
                                   focus=sp["who"], dur=max(0.4, d - (0.65 if i == 0 else 0.2))))
        if i == n - 1 and n > 1:
            shakes.append((max(0.0, sp["end"] - 0.15), 0.5, 0.45))
    if speech and plan.duration - speech[-1]["end"] > 0.7:
        cam_events.append(dict(t=speech[-1]["end"] + 0.2, zoom=1.0, dur=0.5))


def compile_scene(scene, use_tts=True, fps=None, tts_provider=None, voice=None):
    plan = Plan()
    meta = scene.get("meta", {})
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
    if framing not in ("wide", "medium", "inside"):
        framing = "wide" if any(k_ in objects.VEHICLES for k_ in kinds_) else "medium"
    world = 1.0
    if framing == "wide" and kinds_:
        widest = max(objects.SPRITE_LEN[k_] / objects.PERSON_R[k_] for k_ in kinds_) * objects.REF_SCALE
        world = clamp(900.0 / widest, 0.22, 1.0)
    plan.framing, plan.world = framing, world
    plan.cut_in = bool(scene.get("cut_in"))

    # ---- characters ----
    cdefs = scene.get("characters", {})
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
    plan.chars = chars

    # ---- timeline ----
    cursor = 0.0
    gap = float(meta.get("line_gap", 0.35))
    plan.sfx = []
    plan.overlays = []
    plan.objects = {}
    plan.warnings = []
    for c_ in chars.values():
        c_.world = plan.objects
    plan.world_chars = list(chars.values())
    cam_events = []
    shot_events = []        # camera moves from shot words on action lines (do not switch the auto camera off)
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
            if "move" in ev:
                m = ev["move"]
                x0, y0 = c.pos_at(t)
                dur = float(m.get("dur", 0.8))
                c.moves.append((t, t + dur, x0, y0, float(m.get("x", x0)), float(m.get("y", y0))))

        if "say" in ev and who:
            c = chars[who[0]]
            text = str(ev["say"])
            speak = ev.get("speak", text)
            v = dict(c.voice)
            v.update(ev.get("voice", {}) if isinstance(ev.get("voice"), dict) else {})
            path, dur = None, None
            if ti in batch:
                path = batch[ti]
                dur = audio.audio_duration(path)
            elif per_line_edge and ev.get("tts", True):
                path = audio.synth_tts(speak, v.get("name"), v.get("rate", "+0%"), v.get("pitch", "+0Hz"))
                if path:
                    dur = audio.audio_duration(path)
                elif not warned[0]:
                    print("  [tts] unavailable -> using estimated timing, video will have no voice", file=sys.stderr)
                    warned[0] = True
            if dur is None:
                dur = float(ev.get("duration", audio.estimate_duration(speak)))
            sp = dict(who=c.name, text=text, start=t, end=t + dur + 0.12, audio=path, bubble=ev.get("bubble", True),
                      shot=ev.get("shot"))
            c.speech.append(sp)
            plan.speech.append(sp)
            if ev.get("subtitle"):                  # voice-over: the words are shown at the bottom while spoken
                plan.overlays.append({"text": text, "style": "subtitle", "pos": "bottom", "from": t,
                                      "to": t + dur + 0.12})
            cursor = max(cursor, t + dur + gap)
            plan_end = max(plan_end, t + dur + 0.12)
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
            plan.overlays.append(o)
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
        if "camera" in ev:
            cam = dict(ev["camera"])
            cam["t"] = t
            if "shake" in cam:
                shakes.append((t, float(cam["shake"]), float(cam.get("shake_dur", 0.5))))
            if "zoom" in cam or "focus" in cam:
                cam_events.append(cam)

    plan.overlays += static_overlays(scene)
    if scene.get("chat"):
        plan_end = max(plan_end, compile_chat(plan, scene["chat"]))

    for c in chars.values():
        c.events.sort(key=lambda e: e["t"])
        c.speech.sort(key=lambda s_: s_["start"])

    # ---- duration ----
    if meta.get("duration"):
        plan.duration = float(meta["duration"])
    else:
        last = max(plan_end, float(meta.get("min_duration", 4.0)))
        plan.duration = round(last + float(meta.get("tail", 0.9)), 2)
    plan.n_frames = int(round(plan.duration * plan.fps))

    # ---- camera segments ----
    if meta.get("auto_camera", True) and not cam_events and plan.framing == "medium":     # wide / inside are composed shots
        auto_camera(plan, chars, cam_events, shakes)
    cam_events += shot_events
    segs = []
    z, cx, cy = 1.0, LW / 2.0, LH / 2.0
    for cam in sorted(cam_events, key=lambda c_: c_["t"]):
        tz = float(cam.get("zoom", z))
        f = cam.get("focus")
        if isinstance(f, str) and f in chars:
            tc = chars[f].focus_at(cam["t"])
        elif isinstance(f, (list, tuple)):
            tc = (float(f[0]), float(f[1]))
        elif tz == 1.0:
            tc = (LW / 2.0, LH / 2.0)
        else:
            tc = (cx, cy)
        dur = float(cam.get("dur", 0.35))
        segs.append((cam["t"], cam["t"] + dur, z, tz, (cx, cy), tc))
        z, cx, cy = tz, tc[0], tc[1]
    plan.cam_segments = segs
    plan.shakes = shakes

    # ---- audio ----
    m = scene.get("music") or meta.get("music")
    plan.music = compile_music(m, plan.duration)
    plan.bpm = float(meta.get("bpm") or music_bpm(m) or 96)     # dances move on this beat
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
    vol = float(m.get("volume", 0.35))
    if m.get("type") == "beat":
        p = audio.beat_path(float(m.get("bpm", 104)), duration, m.get("style", "desi"))
    else:
        p = asset_path(m.get("path"))
    return dict(path=p, volume=vol, generated=m.get("type") == "beat") if p else None


# keys of a multi-scene file that belong to the whole video, not to one scene
VIDEO_KEYS = ("scenes", "music", "caption", "overlays", "post", "hook", "vars", "name", "about", "transition")


def split_scenes(scene):
    """A multi-scene file ({"scenes": [...]}) -> list of ordinary single-scene dicts.

    Every scene gets the shared `characters` (only those in its `cast`, if given,
    with its own `characters` entries merged on top), the shared `meta`, and its own
    background / timeline / overlays / caption. A scene `title` shows as a card for
    its first 1.4 seconds ("Agle din...").
    """
    if not scene.get("scenes"):
        return [scene]
    base = {k: v for k, v in scene.items() if k not in VIDEO_KEYS}
    base_meta = {k: v for k, v in scene.get("meta", {}).items() if k != "duration"}
    base_meta.setdefault("tail", 0.5)
    if music_bpm(scene.get("music")) and "bpm" not in base_meta:     # scenes dance to the shared music
        base_meta["bpm"] = music_bpm(scene.get("music"))
    cast_all = scene.get("characters", {})
    out = []
    for sc in scene["scenes"]:
        sub = deep_merge(base, {k: v for k, v in sc.items() if k not in ("cast", "characters", "meta", "title")})
        sub["meta"] = dict(base_meta, **sc.get("meta", {}))
        cast = sc.get("cast", []) if sc.get("chat") else (sc.get("cast") or list(cast_all.keys()))
        chars = {n: dict(cast_all.get(n, {})) for n in cast}
        for n, spec in sc.get("characters", {}).items():
            chars[n] = dict(chars.get(n, {}), **spec)
        sub["characters"] = chars
        if sc.get("title"):
            sub["overlays"] = list(sub.get("overlays", [])) + [
                {"text": sc["title"], "style": "card", "pos": "upper", "from": 0.0, "to": 1.4, "color": [40, 40, 48]}]
        out.append(sub)
    return out


def camera_at(plan, t):
    """Returns (zoom, cx, cy, shake_dx, shake_dy)."""
    z, cx, cy = 1.0, LW / 2.0, LH / 2.0
    for (t0, t1, z0, z1, c0, c1) in plan.cam_segments:
        if t < t0:
            break
        e = ease_in_out((t - t0) / max(1e-6, t1 - t0))
        z, cx, cy = lerp(z0, z1, e), lerp(c0[0], c1[0], e), lerp(c0[1], c1[1], e)
    dx = dy = 0.0
    for (ts, amp, dur) in plan.shakes:
        if ts <= t < ts + dur:
            k = (1 - (t - ts) / dur)
            dx += amp * 22 * k * math.sin(95 * t)
            dy += amp * 16 * k * math.cos(83 * t)
    return z, cx, cy, dx, dy

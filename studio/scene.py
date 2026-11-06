"""Compile a scene.json dict into a render plan (timeline, speech, audio, camera)."""
import math
import sys

from . import audio, effects
from .util import LW, LH, asset_path, clamp, ease_in_out, lerp

SLOTS = {
    1: {"center": 540},
    2: {"left": 300, "right": 780, "center": 540},
    3: {"left": 190, "center": 540, "right": 890},
}
GROUND_Y = 1700
CHAR_ATTRS = ("action", "expression", "prop", "label", "look", "facing", "style", "point", "dir",
              "lean", "speed", "intensity", "hands", "tint", "on", "visible", "ride")


class Char:
    def __init__(self, name, spec, x, ground_y, index):
        from .characters import apply_preset
        spec = apply_preset(spec)
        self.name = name
        self.spec = spec
        self.x = x
        self.y = ground_y
        self.scale = float(spec.get("scale", 1.0))
        self.phase = float(spec.get("phase", index * 0.9))
        self.events = []        # sorted by t
        self.rides = []         # (t, vehicle id or None, seat)
        self.vehicle_pos = None  # set by compile_scene: (vid, seat, t) -> (x, y)
        self.moves = []         # (t0, t1, x0, y0, x1, y1)
        self.speech = []        # dicts
        v = spec.get("voice", {})
        self.voice = v if isinstance(v, dict) else {"name": v}

    def ride_at(self, t):
        cur = None
        for (t0, vid, seat) in self.rides:
            if t0 > t:
                break
            cur = (vid, seat) if vid else None
        return cur

    def pos_at(self, t):
        r = self.ride_at(t) if self.rides else None
        if r and self.vehicle_pos:
            return self.vehicle_pos(r[0], r[1], t)
        x, y = self.x, self.y
        for (t0, t1, x0, y0, x1, y1, *_r) in self.moves:
            if t < t0:
                break
            e = ease_in_out((t - t0) / max(1e-6, t1 - t0))
            x, y = lerp(x0, x1, e), lerp(y0, y1, e)
        return x, y

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


def _norm_who(who, names):
    if who in (None, "", "all", "everyone"):
        return list(names)
    if isinstance(who, str):
        return [who]
    return list(who)


def compile_scene(scene, use_tts=True, fps=None):
    plan = Plan()
    meta = scene.get("meta", {})
    plan.fps = int(fps or meta.get("fps", 30))
    plan.fade_in = float(meta.get("fade_in", 0.0))
    plan.fade_out = float(meta.get("fade_out", 0.0))
    plan.background = scene.get("background", {"type": "plain"})

    # ---- characters ----
    cdefs = scene.get("characters", {})
    names = list(cdefs.keys())
    n = len(names)
    slots = SLOTS.get(n, SLOTS[3])
    auto = ["left", "center", "right"] if n == 3 else (["left", "right"] if n == 2 else ["center"])
    chars = {}
    for i, name in enumerate(names):
        spec = dict(cdefs[name])
        slot = spec.get("slot") or (auto[i] if i < len(auto) else "center")
        x = spec.get("x", slots.get(slot, 540))
        y = spec.get("y", GROUND_Y)
        chars[name] = Char(name, spec, float(x), float(y), i)
    plan.chars = chars

    # ---- objects (set pieces) ----
    plan.objects = []
    from .objects import VEHICLE_SIZE
    for i, ob in enumerate(scene.get("objects", [])):
        ob = dict(ob)
        ob.setdefault("id", "%s%d" % (ob.get("type", "obj"), i + 1))
        if ob.get("type") in VEHICLE_SIZE:
            ob["scale"] = float(ob.get("scale", 1.0)) * VEHICLE_SIZE[ob["type"]]
        plan.objects.append(ob)
    obj_by_id = {o["id"]: o for o in plan.objects}
    plan.obj_events = []
    plan.lights = []
    from .objects import VEHICLES, obj_pos

    def vehicle_pos(vid, seat, t):
        ob = obj_by_id[vid]
        evs = sorted(plan.obj_events, key=lambda e: e["t"])
        vx, vy, dirn, _dist = obj_pos(ob, evs, vid, t)
        V = VEHICLES.get(ob.get("type"), {})
        seats = V.get("seats") or {"driver": (0, 250)}
        sx, _h = seats.get(seat) or next(iter(seats.values()))
        e = -1 if (bool(ob.get("flip")) != (dirn < 0)) else 1
        return vx + sx * e * float(ob.get("scale", 1.0)), vy + 1
    plan.vehicle_pos = vehicle_pos
    for c in chars.values():
        c.vehicle_pos = vehicle_pos

    # ---- timeline ----
    cursor = 0.0
    gap = float(meta.get("line_gap", 0.35))
    plan.sfx = []
    plan.overlays = []
    cam_events = []
    shakes = []
    plan.speech = []
    plan.effects = []
    plan.warps = []          # slow motion / freeze frames (story time)
    warned = [False]
    plan_end = 0.0

    for raw in scene.get("timeline", []):
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
            if "ride" in ev:                        # get on (vehicle id) / off ("" or null) a vehicle
                vid = ev["ride"] if ev["ride"] in obj_by_id else None
                if vid is None and c.ride_at(t):
                    px, py = c.pos_at(t)               # stay where you got off
                    c.rides.append((t, None, None))
                    c.moves.append((t, t + 0.001, px, py, px, py, False))
                else:
                    c.rides.append((t, vid, ev.get("seat", "driver")))
            if ev.get("on") in obj_by_id:          # sit / lie on an object: snap onto it
                ob = obj_by_id[ev["on"]]
                x0, y0 = c.pos_at(t)
                dx = float(ev.get("on_dx", 0))
                if ob.get("type") == "bed" and ev.get("action", "") in ("lie_down", "lie", "sleep_lie", "rofl"):
                    head = 1 if ob.get("flip") else -1           # head on the pillow end
                    dx = dx or -head * 400 * float(ob.get("scale", 1.0))
                    c.events.append({"t": t, "dir": head})
                c.moves.append((t, t + 0.001, x0, y0, float(ob.get("x", 540)) + dx,
                                float(ob.get("y", 1700)) + 1, False))
            if "move" in ev:
                m = ev["move"]
                x0, y0 = c.pos_at(t)
                dur = float(m.get("dur", 0.8))
                c.moves.append((t, t + dur, x0, y0, float(m.get("x", x0)), float(m.get("y", y0)),
                                bool(m.get("run") or ev.get("action") == "run")))

        if "say" in ev and who:
            c = chars[who[0]]
            text = str(ev["say"])
            speak = ev.get("speak", text)
            v = dict(c.voice)
            v.update(ev.get("voice", {}) if isinstance(ev.get("voice"), dict) else {})
            path, dur = None, None
            if use_tts and ev.get("tts", True):
                path = audio.synth_tts(speak, v.get("name"), v.get("rate", "+0%"), v.get("pitch", "+0Hz"))
                if path:
                    dur = audio.audio_duration(path)
                elif not warned[0]:
                    print("  [tts] unavailable -> using estimated timing, video will have no voice", file=sys.stderr)
                    warned[0] = True
            if dur is None:
                dur = float(ev.get("duration", audio.estimate_duration(speak)))
            sp = dict(who=c.name, text=text, start=t, end=t + dur + 0.12, audio=path, bubble=ev.get("bubble", True))
            c.speech.append(sp)
            plan.speech.append(sp)
            cursor = max(cursor, t + dur + gap)
            plan_end = max(plan_end, t + dur + 0.12)
        if "hold" in ev:
            cursor = max(cursor, t + float(ev["hold"]))
            plan_end = max(plan_end, t + float(ev["hold"]))

        if "object" in ev:
            for oid in (ev["object"] if isinstance(ev["object"], list) else [ev["object"]]):
                plan.obj_events.append({"t": t, "object": oid, "state": ev.get("state"), "move": ev.get("move")})
                if ev.get("move"):
                    plan_end = max(plan_end, t + float(ev["move"].get("dur", 2.0)))
        if "lights" in ev:
            v = ev["lights"]
            lvl = {"on": 1.0, "off": 0.32, "dim": 0.6}.get(v, v) if not isinstance(v, (int, float)) else float(v)
            plan.lights.append((t, float(lvl)))
        if "fx" in ev:
            for raw in (ev["fx"] if isinstance(ev["fx"], list) else [ev["fx"]]):
                fx = effects.normalize(raw, t)
                if "who" not in fx and who:
                    fx["who"] = who[0]
                plan.effects.append(fx)
        if ev.get("action") == "throw" and ev.get("at") and who:
            # thrown object flies from the thrower's hand to the target; target reacts on impact
            src, dst = who[0], ev["at"]
            release = t + 0.42
            arrive = release + float(ev.get("flight", 0.55))
            obj = ev.get("throw_prop") or ev.get("prop") or "chappal"
            plan.effects.append({"type": "projectile", "src": src, "dst": dst, "prop": obj,
                                 "from": release, "to": arrive, "arc": ev.get("arc", 160)})
            chars[src].events.append({"t": release, "prop": ""})
            if ev.get("hit", True) and dst in chars:
                chars[dst].events.append({"t": arrive, "action": "hit_react"})
                hp = audio.sfx_path(ev.get("hit_sfx", "thud"))
                if hp:
                    plan.sfx.append(dict(t=arrive, path=hp, volume=0.8))
                plan.effects.append({"type": "pow", "who": dst, "text": ev.get("hit_text", "THAK!"),
                                     "from": arrive, "to": arrive + 0.6})
        if "sfx" in ev:
            p = audio.sfx_path(ev["sfx"])
            if p:
                plan.sfx.append(dict(t=t, path=p, volume=float(ev.get("volume", 0.8))))
        if "overlay" in ev:
            o = dict(ev["overlay"])
            o.setdefault("from", t)
            plan.overlays.append(o)
        if "slowmo" in ev:
            sm = ev["slowmo"] if isinstance(ev["slowmo"], dict) else {"rate": ev["slowmo"]}
            rate = float(sm.get("rate", 0.35)) if not isinstance(sm.get("rate"), bool) else 0.35
            plan.warps.append(("slow", t, max(0.05, min(1.0, rate)), float(sm.get("dur", 1.5))))
        if "freeze" in ev:
            fr = ev["freeze"] if isinstance(ev["freeze"], dict) else {"dur": ev["freeze"]}
            plan.warps.append(("freeze", t, float(fr.get("dur", 1.0)) if not isinstance(fr.get("dur"), bool) else 1.0,
                               fr.get("style", "plain")))
        if "camera" in ev:
            cam = dict(ev["camera"])
            cam["t"] = t
            if cam.get("punch"):                     # quick snap zoom onto a face
                cam_events.append({"t": t, "zoom": float(cam.get("zoom", 1.7)), "focus": cam["punch"],
                                   "dur": float(cam.get("dur", 0.1))})
                if cam.get("back"):
                    cam_events.append({"t": t + float(cam["back"]), "zoom": 1.0, "dur": 0.3})
            if cam.get("reveal"):                    # start close, pull back to the full shot
                who_ = cam["reveal"] if isinstance(cam["reveal"], str) else None
                cam_events.append({"t": t, "zoom": float(cam.get("from", 2.2)), "focus": who_, "dur": 0.001})
                cam_events.append({"t": t + 0.002, "zoom": 1.0, "dur": float(cam.get("dur", 1.6))})
            if "shake" in cam:
                shakes.append((t, float(cam["shake"]), float(cam.get("shake_dur", 0.5))))
            if "zoom" in cam or "focus" in cam:
                cam_events.append(cam)

    plan.overlays += [dict(o) for o in scene.get("overlays", [])]
    bgspec = plan.background if isinstance(plan.background, dict) else {"type": plan.background}
    if bgspec.get("time") == "rain" and not any(e.get("type") == "rain" for e in plan.effects):
        plan.effects.append(effects.normalize({"type": "rain"}, 0.0))
    for raw in scene.get("effects", []):
        plan.effects.append(effects.normalize(raw, float(raw.get("from", 0.0)) if isinstance(raw, dict) else 0.0))
    if "caption" in scene:     # shorthand
        c = dict(scene["caption"]) if isinstance(scene["caption"], dict) else {"text": scene["caption"]}
        c.setdefault("style", "caption_box")
        c.setdefault("pos", "top")
        plan.overlays.append(c)

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
    segs = []
    z, cx, cy = 1.0, LW / 2.0, LH / 2.0
    for cam in sorted(cam_events, key=lambda c_: c_["t"]):
        tz = float(cam.get("zoom", z))
        f = cam.get("focus")
        if isinstance(f, str) and f in chars:
            fx, fy = chars[f].pos_at(cam["t"])
            tc = (fx, fy - 560)
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
    plan.music = None
    m = scene.get("music") or meta.get("music")
    if m:
        if isinstance(m, str):
            m = {"path": m}
        vol = float(m.get("volume", 0.35))
        if m.get("type") == "beat":
            p = audio.beat_path(float(m.get("bpm", 104)), plan.duration, m.get("style", "desi"))
        else:
            p = asset_path(m.get("path"))
        if p:
            plan.music = dict(path=p, volume=vol, generated=m.get("type") == "beat")
    return plan


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

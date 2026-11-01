"""Compile a scene.json dict into a render plan (timeline, speech, audio, camera)."""
import math
import sys

from . import audio
from .util import LW, LH, asset_path, clamp, ease_in_out, lerp

SLOTS = {
    1: {"center": 540},
    2: {"left": 300, "right": 780, "center": 540},
    3: {"left": 190, "center": 540, "right": 890},
}
GROUND_Y = 1700
CHAR_ATTRS = ("action", "expression", "prop", "label", "look", "facing", "style", "point", "dir",
              "lean", "speed", "intensity", "hands", "tint")


class Char:
    def __init__(self, name, spec, x, ground_y, index):
        self.name = name
        self.spec = spec
        self.x = x
        self.y = ground_y
        self.scale = float(spec.get("scale", 1.0))
        self.phase = float(spec.get("phase", index * 0.9))
        self.events = []        # sorted by t
        self.moves = []         # (t0, t1, x0, y0, x1, y1)
        self.speech = []        # dicts
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


def _gemini_batch(scene, chars, names, cfg, explicit):
    """Voice for EVERY spoken line of the scene in a single Gemini request.

    Returns {timeline index: wav path}. On failure: raises SystemExit if the user asked for gemini by name,
    otherwise warns and returns None so the caller falls back to per-line edge-tts.
    """
    from . import gemini_tts
    items, idxs = [], []
    for i, raw in enumerate(scene.get("timeline", [])):
        if "say" not in raw or not raw.get("tts", True):
            continue
        who = [w for w in _norm_who(raw.get("who"), names) if w in chars]
        text = str(raw.get("speak", raw["say"])).strip()
        if not who or not text:
            continue
        v = dict(chars[who[0]].voice)
        v.update(raw.get("voice", {}) if isinstance(raw.get("voice"), dict) else {})
        items.append(dict(text=text, voice=gemini_tts.voice_for(v), pitch=v.get("pitch"), rate=v.get("rate")))
        idxs.append(i)
    if not items:
        return {}
    try:
        paths = gemini_tts.synth_script(items, model=cfg.get("model", gemini_tts.DEFAULT_MODEL),
                                        style=cfg.get("style", gemini_tts.DEFAULT_STYLE))
    except Exception as e:
        if explicit:
            raise SystemExit("[tts] Gemini failed: %s" % e)
        print("  [tts] Gemini failed (%s) -> falling back to edge-tts" % str(e)[:160], file=sys.stderr)
        return None
    return dict(zip(idxs, paths))


def compile_scene(scene, use_tts=True, fps=None, tts_provider=None):
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

    # ---- timeline ----
    cursor = 0.0
    gap = float(meta.get("line_gap", 0.35))
    plan.sfx = []
    plan.overlays = []
    cam_events = []
    shakes = []
    plan.speech = []
    warned = [False]
    plan_end = 0.0

    batch, per_line_edge = {}, use_tts
    if use_tts:
        provider, explicit = audio.resolve_provider(tts_provider, meta.get("tts"))
        if provider == "gemini":
            batch = _gemini_batch(scene, chars, names, meta.get("tts") or {}, explicit)
            per_line_edge = batch is None          # None = Gemini failed in auto mode -> edge-tts per line
            batch = batch or {}

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
            sp = dict(who=c.name, text=text, start=t, end=t + dur + 0.12, audio=path, bubble=ev.get("bubble", True))
            c.speech.append(sp)
            plan.speech.append(sp)
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
        if "camera" in ev:
            cam = dict(ev["camera"])
            cam["t"] = t
            if "shake" in cam:
                shakes.append((t, float(cam["shake"]), float(cam.get("shake_dur", 0.5))))
            if "zoom" in cam or "focus" in cam:
                cam_events.append(cam)

    plan.overlays += [dict(o) for o in scene.get("overlays", [])]
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

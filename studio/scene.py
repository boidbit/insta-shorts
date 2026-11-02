"""Compile a scene.json dict into a render plan (timeline, speech, audio, camera)."""
import math
import sys

from . import audio, gemini_tts
from .characters import resolve_spec
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

    def draw_pos(self, t):
        x, y = self.pos_at(t)
        return x, y + self.depth_at(t)[1]

    def draw_scale(self, t):
        return self.scale * self.depth_at(t)[0]

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
    speech = sorted((sp for sp in plan.speech if sp.get("who")), key=lambda sp: sp["start"])
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
    if meta.get("auto_camera", True) and not cam_events:
        auto_camera(plan, chars, cam_events, shakes)
    cam_events += shot_events
    segs = []
    z, cx, cy = 1.0, LW / 2.0, LH / 2.0
    for cam in sorted(cam_events, key=lambda c_: c_["t"]):
        tz = float(cam.get("zoom", z))
        f = cam.get("focus")
        if isinstance(f, str) and f in chars:
            fx, fy = chars[f].draw_pos(cam["t"])
            tc = (fx, fy - 560 * chars[f].depth_at(cam["t"])[0])
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
        cast = sc.get("cast") or list(cast_all.keys())
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

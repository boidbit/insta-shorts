"""scene.json -> mp4.

    python -m studio.render scenes/my_scene.json -o out/my_scene.mp4
    python -m studio.render scenes/my_scene.json --frame 2.5 -o out/preview.png

A scene file can also hold several scenes ({"scenes": [...]}): they play one after
another (each with its own background) with a transition in between, under one
music track and the whole-video overlays (hook, caption).
"""
import argparse
import json
import math
import os
import subprocess
import sys
import time
import zlib

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageOps

from . import actions, audio, gemini_music, look, mystery, objects, rides, sound, styles, theme, ui
from .backgrounds import Background
from .characters import LA, SH, TH, UA, DEFAULT_POSE, build_character, render_ops, skeleton
from .scene import (DIALOGUE_MODES, GROUND_Y, HOOK_MODES, apply_options, camera_at, camera_roll, camera_whip,
                    apply_cta, apply_loop, compile_music, compile_scene, ease_travel, mascot_kind,
                    prepare_voice, split_scenes, start_xs, static_overlays)
from .animals import ANIMALS, build_animal
from .effects import Effects, Patch
from .sets import Sets
from .style25d import shading
from .text import bubble_image, chat_image, styled_box
from .util import LH, LW, clamp, ease_in_out, ease_out, ease_out_back, lerp, load_scene

POS = {"top": (540, 330), "center": (540, 960), "lower": (540, 1450), "bottom": (540, 1560),
       "upper": (540, 520)}
TRANSITIONS = ("fade", "whip", "cut")


def frame_size(width):
    W = int(width) - int(width) % 2
    H = int(round(W * LH / LW))
    return W, H - H % 2


def _shadow_sprite(w=256, h=64, peak=0.55):
    """Soft elliptical blob (dark, radial falloff) used as the contact shadow."""
    yy, xx = np.mgrid[0:h, 0:w].astype("float32")
    d = np.sqrt(((xx + 0.5) / w * 2 - 1) ** 2 + ((yy + 0.5) / h * 2 - 1) ** 2)
    a = np.clip(1.0 - d, 0.0, 1.0) ** 1.4 * peak
    rgba = np.zeros((h, w, 4), dtype="uint8")
    rgba[..., 0], rgba[..., 1], rgba[..., 2] = 24, 20, 34
    rgba[..., 3] = (a * 255).astype("uint8")
    return Image.fromarray(rgba, "RGBA")


def _rolled_crop(img, vl, vt, vw, vh, deg, W, H):
    """The camera's window (vl, vt, vw, vh) blown up to the frame, tilted by `deg` degrees - or by as much of that
    as the zoom leaves room for, so no empty corner ever shows."""
    z = W / float(vw)
    th = math.radians(deg)
    while abs(th) > 1e-3 and math.cos(th) + (H / float(W)) * abs(math.sin(th)) > z:
        th *= 0.8
    c, sn = math.cos(th) / z, math.sin(th) / z
    hx, hy = (W * abs(c) + H * abs(sn)) / 2.0, (W * abs(sn) + H * abs(c)) / 2.0     # half size of the tilted window
    cx = clamp(vl + vw / 2.0, hx, max(hx, W - hx))
    cy = clamp(vt + vh / 2.0, hy, max(hy, H - hy))
    return img.transform((W, H), Image.AFFINE, (c, -sn, cx - W / 2.0 * c + H / 2.0 * sn,
                                                sn, c, cy - W / 2.0 * sn - H / 2.0 * c), Image.BICUBIC)


def _vignette(w, h, strength):
    """RGB multiplier image (255 = untouched) that darkens the corners a touch and warms them slightly."""
    if strength <= 0:
        return None
    yy, xx = np.mgrid[0:h, 0:w].astype("float32")
    d = np.sqrt(((xx + 0.5) / w * 2 - 1) ** 2 + ((yy + 0.5) / h * 2 - 1) ** 2) / 1.4142
    v = np.clip((d - 0.45) / 0.55, 0.0, 1.0)
    v = v * v * (3 - 2 * v)
    out = np.empty((h, w, 3), dtype="uint8")
    for ch, k in enumerate((0.80, 0.95, 1.10)):     # R loses least, B most -> warm edges
        out[..., ch] = np.clip((1.0 - strength * v * k) * 255, 0, 255).astype("uint8")
    return Image.fromarray(out, "RGB")


INF = float("inf")


class TimeWarp:
    """Maps real (video) time <-> story (scene) time for slow motion and freeze frames."""

    def __init__(self, warps, story_dur):
        self.pieces = []                # (real_start, story_start, rate, real_len, style)
        real = story = 0.0
        for w in sorted(warps, key=lambda w_: w_[1]):
            ts = w[1]
            if ts < story:
                continue
            if ts > story:
                self.pieces.append((real, story, 1.0, ts - story, None))
                real, story = real + ts - story, ts
            if w[0] == "slow":
                rate, sdur = w[2], w[3]
                self.pieces.append((real, story, rate, sdur / rate, None))
                real, story = real + sdur / rate, story + sdur
            else:
                self.pieces.append((real, story, 0.0, w[2], w[3]))
                real += w[2]
        self.pieces.append((real, story, 1.0, INF, None))
        self.duration = real + max(0.0, story_dur - story)

    def at(self, T):
        """(story time, freeze style or None) at real time T."""
        for (r0, s0, rate, ln, style) in self.pieces:
            if r0 <= T < r0 + ln:
                return s0 + (T - r0) * rate, style
        r0, s0, rate, _ln, _st = self.pieces[-1]
        return s0 + (T - r0), None

    def real(self, ts):
        """Real time at which story time ts is shown (first time, if frozen)."""
        for (r0, s0, rate, ln, _style) in self.pieces:
            if rate == 0 and abs(ts - s0) < 1e-4:   # exactly at a freeze: when the freeze starts
                return r0
            if rate > 0 and s0 <= ts < s0 + rate * ln:
                return r0 + (ts - s0) / rate
        r0, s0, _r, _l, _s = self.pieces[-1]
        return r0 + (ts - s0)


class OverlayLayer:
    """Draws screen-fixed text overlays (captions, hook, cards) with their animations."""

    def __init__(self, s):
        self.s = s
        self._cache = {}

    def _image(self, o):
        key = json.dumps([o.get("text"), o.get("style"), o.get("color"), o.get("size"), o.get("max_w"), o.get("fg"),
                          o.get("rotate")], default=str)
        if key not in self._cache:
            im = styled_box(str(o.get("text", "")), o.get("style", "caption_box"), self.s,
                            o.get("color"), o.get("size"), o.get("max_w"), o.get("fg"))
            if o.get("rotate"):                     # (the @handle runs up the side of the picture)
                im = im.rotate(float(o["rotate"]), expand=True, resample=Image.BICUBIC)
            self._cache[key] = im
        return self._cache[key]

    def _chat(self, o, shown, typing=None):
        key = (id(o), shown, typing)
        if key not in self._cache:
            self._cache[key] = chat_image(o["chat"], shown, self.s, typing=typing)
        return self._cache[key]

    UI_DUR = {"notification": 3.0, "loading": 3.0, "counter": 3.0, "timecard": 1.6, "chapter": 2.2}
    UI_POS = {"notification": (540, 150), "loading": (540, 900), "counter": (540, 720), "chapter": (540, 330),
              "phone_chat": (540, 820), "insta": (540, 760), "order": (540, 700), "upi": (540, 740)}

    def _draw_ui(self, img, o, t, t0, t1):
        """Phone notification, loading bar, counter, time card, chapter card, end card (studio/ui.py)."""
        typ, lt = o["type"], t - t0
        W, H = img.size
        im = ui.render(o, lt, self.s, (t1 - t0) if t1 < 1e8 else 3.0, (W, H))
        if im is None:
            return
        fade = clamp(lt / 0.2) * (clamp((t1 - t) / 0.25) if t1 < 1e8 else 1.0)
        if typ in ("timecard", "endcard"):          # full screen
            if fade < 0.999:
                im.putalpha(im.getchannel("A").point([int(v * fade) for v in range(256)]))
            img.paste(im, (0, 0), im)
            return
        pos = o.get("pos", self.UI_POS.get(typ, (540, 900)))
        px, py = POS[pos] if isinstance(pos, str) else pos
        if typ == "notification":                   # slides down from the top, and back up at the end
            py = py - 260 * (1 - ease_out(lt / 0.3)) - (260 * (1 - clamp((t1 - t) / 0.3)) if t1 < 1e8 else 0)
        paste_rgba(img, im, px * self.s, py * self.s, 1.0, fade)

    def draw(self, img, overlays, t):
        for o in overlays:
            t0 = float(o.get("from", 0.0))
            t1 = o.get("to")
            dflt = self.UI_DUR.get(o.get("type"))
            t1 = float(t1) if t1 is not None else (t0 + float(o["dur"]) if "dur" in o else
                                                   (t0 + dflt if dflt else 1e9))
            if not (t0 <= t < t1):
                continue
            if o.get("type") in ui.TYPES and o.get("type") != "chat" and not o.get("chat"):
                self._draw_ui(img, o, t, t0, t1)
                continue
            if o.get("chat"):                       # phone chat: shows the messages whose time has come
                msgs = o["chat"].get("messages", [])
                shown = sum(1 for m in msgs if float(m.get("t", 0.0)) <= t)
                nxt = msgs[shown] if shown < len(msgs) else None
                typing = (int(t * 3.5) % 3) if (nxt and nxt.get("side") == "left"
                                                and t >= float(nxt.get("t", 0.0)) - 0.9) else None
                if not shown and typing is None:
                    continue
                im = self._chat(o, shown, typing)
            else:
                im = self._image(o)
            pos = o.get("pos", "top")
            px, py = POS[pos] if isinstance(pos, str) else pos
            default_anim = {"lyric": "fade", "subtitle": "fade", "hook": "punch"}.get(o.get("style"), "pop")
            anim = o.get("anim", default_anim)
            lt = t - t0
            sc, al = 1.0, 1.0
            if anim == "punch":      # slams in big, settles, then breathes
                sc = 1.0 + 0.55 * (1 - ease_out(lt / 0.22)) + 0.025 * math.sin(lt * 7.0)
                al = clamp(lt / 0.06)
            elif anim == "pop":
                sc = 0.35 + 0.65 * ease_out_back(lt / 0.32)
                al = clamp(lt / 0.12)
            elif anim == "fade":
                al = clamp(lt / 0.3)
            elif anim == "slide":
                py += (1 - ease_out(lt / 0.35)) * 120
                al = clamp(lt / 0.2)
            if t1 < 1e8 and anim != "none":
                al *= clamp((t1 - t) / 0.2)
            al *= float(o.get("alpha", 1.0))          # (the @handle in the corner is see-through)
            if o.get("chat"):                       # anchored at the top, so the panel only grows downwards
                paste_rgba(img, im, px * self.s, py * self.s, sc, al, anchor=(im.width / 2.0, 0.0))
            else:
                paste_rgba(img, im, px * self.s, py * self.s, sc, al)


def paste_rgba(img, rgba, cx, cy, scale=1.0, alpha=1.0, anchor=None):
    """Paste RGBA centered at (cx, cy) in OUTPUT pixels (or with a given anchor inside the image)."""
    if scale != 1.0:
        w, h = max(1, int(rgba.width * scale)), max(1, int(rgba.height * scale))
        rgba = rgba.resize((w, h), Image.BILINEAR)
        if anchor:
            anchor = (anchor[0] * scale, anchor[1] * scale)
    ax, ay = anchor if anchor else (rgba.width / 2.0, rgba.height / 2.0)
    if alpha < 1.0:
        rgba = rgba.copy()
        a = rgba.getchannel("A").point(lambda v: int(v * alpha))
        rgba.putalpha(a)
    img.paste(rgba, (int(cx - ax), int(cy - ay)), rgba)


class Output:
    """Shared ffmpeg writer. Subclasses provide W, H, fps, duration, n_frames,
    speech, sfx, music and frame(t)."""

    def ffmpeg_cmd(self, out):
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
               "-s", "%dx%d" % (self.W, self.H), "-r", str(self.fps), "-i", "-"]
        idx = 1
        speech_lbl, fx_lbl, filters = [], [], []
        for sp in self.speech:
            if sp.get("audio"):
                cmd += ["-i", sp["audio"]]
                ms = int(sp["start"] * 1000)
                cut = ",atrim=0:%.2f,afade=t=out:st=%.2f:d=0.06" % (sp["cut"], max(0.0, sp["cut"] - 0.06)) \
                    if sp.get("cut") else ""             # interrupted: the line stops where the other one cuts in
                filters.append("[%d:a]aresample=44100,aformat=channel_layouts=mono%s,adelay=%d:all=1,volume=1.0[s%d]"
                               % (idx, cut, ms, idx))
                speech_lbl.append("[s%d]" % idx)
                idx += 1
        for fx in self.sfx:
            cmd += ["-i", fx["path"]]
            ms = int(fx["t"] * 1000)
            filters.append("[%d:a]aresample=44100,aformat=channel_layouts=mono,adelay=%d:all=1,volume=%.2f[f%d]"
                           % (idx, ms, fx["volume"], idx))
            fx_lbl.append("[f%d]" % idx)
            idx += 1
        for amb in getattr(self, "ambience", []):     # looped sound beds, mixed with the sound effects
            cmd += ["-stream_loop", "-1", "-i", amb["path"]]
            filters.append("[%d:a]aresample=44100,aformat=channel_layouts=mono,atrim=0:%.2f,adelay=%d:all=1,"
                           "volume=%.2f[f%d]" % (idx, amb["dur"], int(amb["start"] * 1000), amb["volume"], idx))
            fx_lbl.append("[f%d]" % idx)
            idx += 1
        snd = getattr(self, "sound", None)
        if snd and getattr(self, "with_sound", True):  # sound mode: the viral sound itself, from the first frame
            cmd += ["-i", snd["path"]]
            filters.append("[%d:a]aresample=44100,aformat=channel_layouts=mono,atrim=0:%.2f,volume=1.0[f%d]"
                           % (idx, self.duration, idx))
            fx_lbl.append("[f%d]" % idx)
            idx += 1
        mus = None
        if self.music:
            if not self.music["generated"]:
                cmd += ["-stream_loop", "-1"]
            cmd += ["-i", self.music["path"]]
            fade = getattr(self, "loop_fade", 0.0)      # LOOP: the music dips out as the reel whips back to its start
            fade = ",afade=t=out:st=%.2f:d=%.2f" % (max(0.0, self.duration - fade), fade) if fade else ""
            filters.append("[%d:a]aresample=44100,aformat=channel_layouts=mono,atrim=0:%.2f,volume=%.2f%s[mus]"
                           % (idx, self.duration, self.music["volume"], fade))
            mus = "[mus]"
            idx += 1

        mix_in = []
        if speech_lbl:
            if len(speech_lbl) > 1:
                filters.append("%samix=inputs=%d:normalize=0:duration=longest[sp]" % ("".join(speech_lbl), len(speech_lbl)))
            else:
                filters.append("%sanull[sp]" % speech_lbl[0])
            if mus:
                filters.append("[sp]asplit=2[spa][spb]")
                filters.append("[mus][spa]sidechaincompress=threshold=0.03:ratio=8:attack=15:release=300[duck]")
                mix_in += ["[spb]", "[duck]"]
            else:
                mix_in.append("[sp]")
        elif mus:
            mix_in.append(mus)
        if fx_lbl:
            if len(fx_lbl) > 1:
                filters.append("%samix=inputs=%d:normalize=0:duration=longest[fx]" % ("".join(fx_lbl), len(fx_lbl)))
            else:
                filters.append("%sanull[fx]" % fx_lbl[0])
            mix_in.append("[fx]")

        if mix_in:
            if len(mix_in) > 1:
                filters.append("%samix=inputs=%d:normalize=0:duration=longest,apad,alimiter=limit=0.95[aout]"
                               % ("".join(mix_in), len(mix_in)))
            else:
                filters.append("%sapad,alimiter=limit=0.95[aout]" % mix_in[0])
            cmd += ["-filter_complex", ";".join(filters), "-map", "0:v", "-map", "[aout]"]
        else:
            cmd += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-map", "0:v", "-map", "%d:a" % idx]
        cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                "-r", str(self.fps), "-c:a", "aac", "-b:a", "160k", "-ac", "2",
                "-t", "%.3f" % self.duration, "-movflags", "+faststart", out]
        return cmd

    def render_video(self, out, progress=None):
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        cmd = self.ffmpeg_cmd(out)
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        n = self.n_frames
        t0 = time.time()
        try:
            for i in range(n):
                img = self.frame(i / float(self.fps))
                proc.stdin.write(img.tobytes())
                if i % 30 == 0:
                    el = time.time() - t0
                    print("  frame %d/%d  (%.1fs)" % (i, n, el), flush=True)
                    if progress:
                        progress(i / float(n))
            proc.stdin.close()
        except BrokenPipeError:
            pass
        rc = proc.wait()
        if rc != 0:
            raise SystemExit("ffmpeg failed (exit %d)" % rc)
        print("done: %s  (%d frames, %.1fs video, %.0fs render)" % (out, n, self.duration, time.time() - t0))


class Renderer(Output):
    """One scene (one background)."""

    def __init__(self, scene, width=1080, use_tts=True, fps=None, tts_provider=None, voice=None):
        self.scene = scene
        self.plan = compile_scene(scene, use_tts=use_tts, fps=fps, tts_provider=tts_provider, voice=voice)
        self.W, self.H = frame_size(width)
        self.s = self.W / float(LW)
        ang = self.plan.angle
        # 2.5D style: kitchen / gully / chai_tapri / kirana / terrace are layered parallax sets (style25d);
        # everything else (and every 2d scene) uses the normal flat place below, unchanged.
        preset = styles.preset_for(scene)
        self._auto25 = bool(preset and preset.startswith("auto:"))
        # the studio place still brings its foreground props and moving clouds / traffic to an auto 2.5D set
        bg_spec = self.plan.background if (not preset or self._auto25) else \
            {"type": "plain", "foreground": [], "ambient": False}
        if getattr(self.plan, "camera", "") != "cine" and isinstance(bg_spec, dict):
            bg_spec = dict(bg_spec, classic=True)          # CAMERA: classic keeps the old drawings
        self.bg = Background(bg_spec, int(self.W * ang["zoom"] + 0.5), int(self.H * ang["zoom"] + 0.5))
        self.bd25 = self._backdrop25(preset, scene) if preset else None
        self._add_crowd(scene, preset)
        used = getattr(self.plan, "counters", None)
        mode = getattr(self.plan, "counter_mode", "2d")
        place = bg_spec.get("type") if isinstance(bg_spec, dict) else bg_spec
        if used and mode == "2d" and self.bg.static is not None and self.bd25 is None:
            from . import counters                   # the painted counter's front, over whoever stands behind it
            for d, im, x, y in counters.counter_overlays(place, used, self.bg.static, self.bg.out_w / float(LW)):
                self.bg.fg.append((d, im, x, y, None))
            self.bg.fg.sort(key=lambda f: f[0])
        elif used and mode == "auto" and self.bd25 is not None:
            from . import counters                   # 2.5D: cut out of the layer the people stand in
            layer = next((ly for ly in self.bd25.layered.back if ly.name == "set"), None)
            if layer is not None:
                self.bd25.layered.sprites += counters.counter_sprites(place, used, layer.im, layer.k)
        self._view25_t, self._view25_v = None, None
        self.overlay_layer = OverlayLayer(self.s)
        self.fx = Effects(self.plan.effects, self.s, self.W, self.H, self.plan.fps)
        self.sets = Sets(self.plan.sets, self.plan.set_events, self.s, self.W, self.H)
        self._lip = {}
        self._blinks = {}
        self._label_cache = {}
        self.warp = TimeWarp(self.plan.warps, self.plan.duration)   # slow motion / freeze: real <-> story time
        self.fps, self.duration = self.plan.fps, round(self.warp.duration, 3)
        self.n_frames = int(round(self.duration * self.fps))
        w = self.warp.real
        self.speech = [dict(sp, start=w(sp["start"])) for sp in self.plan.speech] if self.plan.warps \
            else self.plan.speech
        self.sfx = [dict(fx, t=w(fx["t"])) for fx in self.plan.sfx] if self.plan.warps else self.plan.sfx
        self.music = self.plan.music
        self.ambience = [dict(a, dur=self.duration) for a in self.plan.ambience]
        meta = scene.get("meta", {})
        self.shadows = bool(meta.get("shadows", True))          # soft contact shadow under each character
        self._shadow = _shadow_sprite() if self.shadows else None
        own_picture = (scene.get("background") or {}).get("type") == "image"      # the user's picture stays as it is
        self._theme = theme.resolve(meta.get("theme")) if getattr(self.plan, "camera", "") == "cine" else None
        # the place's own colour grade (studio.look): a hospital, a dhaba and a shaadi each get their camera
        self._look = look.for_scene(scene, self.plan, self.W, self.H) if getattr(self.plan, "camera", "") == "cine" \
            else None
        if self._theme and self.bd25 is None and not own_picture and getattr(self.bg, "static", None) is not None:
            self.bg.static = theme.shift_place(self.bg.static, self._theme)        # this video's own colours
        vig_default = 0.0 if own_picture else 0.16
        if self.bd25:
            vig_default = float(self.bd25.light.get("vignette", vig_default))
        self._vig = _vignette(self.W, self.H, float(meta.get("vignette", vig_default)))   # 0 = off
        self._tint25 = tuple(self.bd25.light["ambient"]) if self.bd25 and self.bd25.light.get("ambient") else None

    # ------------------------------------------------------------ helpers
    def _sound_env(self, sp):
        src = sp.get("lip_src")
        if src not in self._lip:
            self._lip[src] = audio.lip_envelope(src, self.plan.fps)
        return self._lip[src]

    def _sound_gain(self, sp, env):
        """Sound mode: each line's mouth as wide as its own voice allows (a soft voice still opens the mouth)."""
        key = ("gain", id(sp))
        if key not in self._lip:
            fps = self.plan.fps
            seg = env[max(0, int(sp["start"] * fps)):max(1, int(sp["end"] * fps))]
            ref = float(np.percentile(seg, 90)) if len(seg) else 1.0
            self._lip[key] = min(3.0, 0.9 / ref) if ref > 0.02 else 1.0
        return self._lip[key]

    def _lip_open(self, sp, t):
        fps = self.plan.fps
        if sp.get("lip_src"):                       # sound mode: the whole sound, at the video's own time
            env = self._sound_env(sp)
            if env is not None:
                i = int(t * fps)
                return min(1.0, float(env[i]) * self._sound_gain(sp, env)) if 0 <= i < len(env) else 0.0
        if sp.get("audio"):
            if id(sp) not in self._lip:
                self._lip[id(sp)] = audio.lip_envelope(sp["audio"], fps)
            env = self._lip[id(sp)]
            if env is not None:
                i = int((t - sp["start"]) * fps)
                if 0 <= i < len(env):
                    return float(env[i])
                return 0.0
        # no audio: believable fake syllables
        a = abs(math.sin(t * 9.1)) * (0.55 + 0.45 * abs(math.sin(t * 3.7 + 1.3)))
        return clamp(a * 1.25 - 0.1)

    def _amp(self, sp, t):
        """How loud a line is around time t (0..1), smoothed over ~0.4 s: gestures follow the phrase, not every
        syllable (a hand that jumps on each syllable looks fake)."""
        if sp.get("audio") or sp.get("lip_src"):
            if sp.get("lip_src"):
                env, at = self._sound_env(sp), t
            else:
                if id(sp) not in self._lip:
                    self._lip[id(sp)] = audio.lip_envelope(sp["audio"], self.plan.fps)
                env, at = self._lip[id(sp)], t - sp["start"]
            if env is not None and len(env):
                fps = self.plan.fps
                i = int(at * fps)
                seg = env[max(0, i - int(0.35 * fps)):max(1, i + 2)]
                return float(sum(seg) / len(seg)) if len(seg) else 0.0
        return 0.5 + 0.2 * math.sin(t * 2.1) * math.sin(t * 0.9 + 1.0)

    # ------------------------------------------------------------ 2.5D sets
    def _backdrop25(self, preset, scene):
        from .locations import grade
        from .style25d.scenery import StudioBackdrop
        time = (scene.get("background") or {}).get("time")
        native = styles.NATIVE_TIME.get(preset)
        same = time in (None, "", "day", native) or (native == "sunset" and time == "evening") or \
            preset in styles.OWN_TIME
        cams = [sg[3] for sg in self.plan.cam_segments] + ([1.05] if self.plan.shakes else [])
        zmax = self.plan.angle["zoom"] * max([1.0] + cams)
        extra = []
        bg = self.bg if preset.startswith("auto:") else None
        if preset in styles.SET_AMBIENT:                # a hand-made road set: its own clouds, birds and traffic
            bg = Background({"type": "plain", "ambient": False}, self.bg.out_w, self.bg.out_h)
            bg.ambient = list(styles.SET_AMBIENT[preset])
        if bg is not None and bg.ambient:
            from .style25d.scenery import Layer

            def ambient(kinds):
                def draw(_im, t):
                    canvas = Image.new("RGBA", (bg.out_w, bg.out_h), (0, 0, 0, 0))
                    bg._draw_ambient(canvas, t, kinds)
                    return canvas
                return draw
            k = bg.out_w / float(LW)
            kinds = {item[0] for item in bg.ambient}
            if kinds & {"cloud", "birds"}:              # clouds and birds far away in the sky, traffic on the road
                extra.append(Layer(Image.new("RGBA", (8, 8)), k, 0.1, ambient({"cloud", "birds"}), "sky_life"))
            if kinds - {"cloud", "birds"}:
                extra.append(Layer(Image.new("RGBA", (8, 8)), k, 1.0, ambient(kinds - {"cloud", "birds"}), "ambient"))
        return StudioBackdrop(preset, self.W, self.H, zmax=min(zmax, 2.4), time=None if same else time, grade=grade,
                              extra=extra, spec=self.plan.background)

    def _add_crowd(self, scene, preset):
        """People in the background of a public place (studio.crowd): the new camera only, never in a vehicle."""
        from . import crowd as crowd_
        if getattr(self.plan, "camera", "") != "cine" or self.plan.vehicle or (preset or "").startswith("auto:"):
            return
        bg = self.plan.background if isinstance(self.plan.background, dict) else {"type": self.plan.background}
        people = crowd_.extras(bg.get("type"), preset, bg.get("layout"), crowd_.amount(scene),
                               seed=str(scene.get("hook") or "") + str(len(scene.get("timeline", []))))
        if not people:
            return
        time = bg.get("time")
        tint = {"night": (150, 156, 206), "rain": (170, 176, 196), "evening": (255, 214, 176),
                "sunset": (255, 206, 166), "dawn": (236, 214, 220)}.get(time, (255, 255, 255))
        if self.bd25 is not None:
            amb = self.bd25.light.get("ambient") or [255, 255, 255]
            tint = tuple(int(a * b / 255) for a, b in zip(amb, tint))
        crowd = crowd_.Crowd(people, tint if tint != (255, 255, 255) else None)
        road = preset in styles.SET_AMBIENT if self.bd25 is not None else self.bg.kind in ("street", "bus_stop")
        if not road:                                    # sorted with the people and the counters
            self._crowd = crowd
        elif self.bd25 is not None:                     # on the far footpath: behind the road and its traffic
            from .style25d.scenery import Layer
            k = 0.6 * self.s
            fn = crowd_.layer_fn(crowd, k, (int(round(LW * k)), int(round(LH * k))))
            back = self.bd25.layered.back
            at = next((i for i, b in enumerate(back) if b.name == "ambient" or b.d > 1.0), len(back))
            back.insert(at, Layer(Image.new("RGBA", (8, 8), (0, 0, 0, 0)), k, 1.0, fn, "crowd"))
        else:
            self.bg.crowd = crowd

    def _view25(self, t):
        """Shot angle + in-shot camera at time t, as StudioBackdrop wants it (computed like _background and the
        camera crop in story_frame)."""
        if self._view25_t == t:
            return self._view25_v
        ang, s = self.plan.angle, self.s
        za = ang["zoom"]
        left = top = 0.0
        if za > 1.001:
            sz = s * za
            left = clamp(ang["x"] * sz - self.W / 2.0, 0, self.bg.out_w - self.W)
            top = clamp(GROUND_Y * (sz - s), 0, self.bg.out_h - self.H)
        z, vl, vt, _vw, _vh = self._cam_view(t)
        mirror = ang["mirror"] and self.bd25.preset not in styles.NO_MIRROR
        v = dict(za=za, La=int(left) / (s * za), Ta=int(top) / (s * za), zc=max(z, 1.0), mirror=mirror, vl=vl, vt=vt)
        self._view25_t, self._view25_v = t, v
        return v

    cam_override = None     # (zoom, cx, cy): a fixed camera (the cover picture's close-up)

    def _cam_view(self, t):
        """The in-shot camera at time t: (zoom, left, top, width, height) of its window in frame pixels."""
        z, cx, cy, dx, dy = camera_at(self.plan, t)
        if self.cam_override:
            (z, cx, cy), dx, dy = self.cam_override, 0.0, 0.0
        else:
            shot = self._shot_at(t)
            if shot is not None:                    # a counter conversation's shot: its own fixed camera
                (z, cx, cy), dx, dy = shot["cam"], 0.0, 0.0
        if dx or dy:
            z = max(z, 1.05)
        s = self.s
        vw, vh = self.W / max(z, 1.0), self.H / max(z, 1.0)
        return z, clamp((cx + dx) * s - vw / 2, 0, self.W - vw), clamp((cy + dy) * s - vh / 2, 0, self.H - vh), vw, vh

    def _background(self, t):
        """The place, seen from this shot's angle: drawn bigger (crisp, not blown up), the part around angle x, with the
        ground line where the people stand kept in place; mirrored for a reverse shot."""
        if self.bd25 is not None:
            return self.bd25.image(t, self._view25(t))
        img = self.bg.frame(t).convert("RGB")
        ang = self.plan.angle
        z = ang["zoom"]
        if z > 1.001:
            s = self.s * z
            left = clamp(ang["x"] * s - self.W / 2.0, 0, img.width - self.W)
            top = clamp(GROUND_Y * (s - self.s), 0, img.height - self.H)
            img = img.crop((int(left), int(top), int(left) + self.W, int(top) + self.H))
        if ang["mirror"]:
            img = ImageOps.mirror(img)
        return img

    def _foreground(self, t):
        """The place's foreground props, placed like the background of this shot (angle zoom / mirror)."""
        crowd = self._crowd_pieces(t) if self._crowd is not None else []
        if self.bd25 is not None and not self._auto25:
            return self.bd25.floor_items(self._view25(t)) + crowd
        if self.bd25 is not None and self.bd25.layered.sprites:      # auto 2.5D: its counters, then the place's props
            return self.bd25.floor_items(self._view25(t)) + self._foreground_flat(t) + crowd
        return self._foreground_flat(t) + crowd

    _crowd = None           # the crowd as pieces sorted with the people (a place without a road: studio.crowd)

    def _crowd_pieces(self, t):
        """[(depth y, picture, x, y)] of the crowd in this shot, like the place's own pieces (angle zoom / mirror),
        so a counter or a character nearer the lens covers them and they cover what is behind them."""
        if self.bd25 is not None:
            v = self._view25(t)
            sc, left, top, mirror = self.s * v["za"], v["La"] * self.s * v["za"], v["Ta"] * self.s * v["za"], v["mirror"]
        else:
            ang = self.plan.angle
            z = ang["zoom"]
            sc = self.s * z
            left = clamp(ang["x"] * sc - self.W / 2.0, 0, self.bg.out_w - self.W) if z > 1.001 else 0
            top = clamp(GROUND_Y * (sc - self.s), 0, self.bg.out_h - self.H) if z > 1.001 else 0
            mirror = ang["mirror"]
        out = []
        for i, e in enumerate(self._crowd.people):
            got = self._crowd._sprite(i, e, t, sc)
            if not got:
                continue
            im, x, y = got
            x, y = x - left, y - top
            if mirror:
                im = ImageOps.mirror(im)
                x = self.W - x - im.width
            out.append((e["y"], im, int(x), int(y)))
        return out

    def _foreground_flat(self, t):
        items = self.bg.foreground(t)
        ang = self.plan.angle
        z = ang["zoom"]
        mirror = ang["mirror"] if self.bd25 is None else self._view25(t)["mirror"]   # props turn with the set
        if not items or (z <= 1.001 and not mirror):
            return items
        sz = self.s * z
        left = clamp(ang["x"] * sz - self.W / 2.0, 0, self.bg.out_w - self.W) if z > 1.001 else 0
        top = clamp(GROUND_Y * (sz - self.s), 0, self.bg.out_h - self.H) if z > 1.001 else 0
        out = []
        for d, im, x, y in items:
            x2, y2 = x - left, y - top
            if mirror:
                im = ImageOps.mirror(im)
                x2 = self.W - x2 - im.width
            out.append((d, im, int(x2), int(y2)))
        return out

    def _front_rider(self, c, t):
        rf = c.ride_frame(t)
        return bool(rf and rf["inside"] and rf["obj"].front)

    def _riders_of(self, o, t):
        return [rf for rf in (c.ride_frame(t) for c in self.plan.chars.values()) if rf and rf["obj"] is o and rf["inside"]]

    def _paste_object(self, img, o, t, part="all"):
        """One vehicle / object. part: "all", or "back" / "front" for a split vehicle with a rider in it."""
        s = self.s
        im, (ax, ay), wheels = objects.sprite(o.kind, s * o.scale, o.color, part)
        x = o.x_at(t)
        flip = o.flip_at(t)
        age = t - o.t_in
        alpha = 1.0 if o.no_fade else (clamp(age / 0.18) if not o.moves or o.moves[0][0] > o.t_in + 0.01 else 1.0)
        cx, cy = x * s, (o.y + o.bob_at(t)) * s
        if im is not None:
            if flip:
                im = im.transpose(Image.FLIP_LEFT_RIGHT)
                ax = im.width - ax
            paste_rgba(img, im, cx, cy, 1.0, alpha, anchor=(ax, ay))
        for (wx, wy, r) in wheels:
            wim = objects.wheel_image(r, -(x * s) / max(r, 1.0) * 57.2958)
            wxx = ((im.width if im is not None else 0) - wx) if flip else wx
            paste_rgba(img, wim, cx + (wxx - ax), cy + (wy - ay), 1.0, alpha)

    def _draw_crank(self, img, o, t):
        """The pedals of a bicycle turn with the wheels."""
        from PIL import ImageDraw
        s, sgn = self.s, (-1.0 if o.flip_at(t) else 1.0)
        a = rides.crank_angle(o, t)
        bx = o.x_at(t) + sgn * rides.CRANK["bb"][0] * o.scale
        by = o.y + o.bob_at(t) + rides.CRANK["bb"][1] * o.scale
        d = ImageDraw.Draw(img)
        for ang, col in ((a + math.pi, (70, 72, 80)), (a, (40, 40, 46))):
            px = bx + sgn * math.cos(ang) * rides.CRANK["length"] * o.scale
            py = by + math.sin(ang) * rides.CRANK["length"] * o.scale
            d.line([(bx * s, by * s), (px * s, py * s)], fill=(26, 26, 30), width=max(2, int(7 * s * o.scale)))
            w, h = 22 * s * o.scale, 7 * s * o.scale
            d.rectangle([px * s - w, py * s - h, px * s + w, py * s + h], fill=col, outline=(26, 26, 30))

    def _draw_objects(self, img, t, front, skip=()):
        """Set objects (vehicles, bins, bags...): `front` ones over the characters, the rest behind them.
        (A `front` vehicle with somebody in it is drawn later, together with its riders.) skip: kinds left out."""
        for o in self.plan.objects.values():
            if not o.visible(t) or o.kind in skip:
                continue
            riders = self._riders_of(o, t)
            if o.front and riders:                  # drawn together with its riders, over everybody
                continue
            if o.front != front:
                continue
            if not front and getattr(o, "depth_sort", False):     # somebody stands behind it: drawn by depth
                continue
            self._paste_object(img, o, t, "back" if (riders and o.kind in objects.SPLIT) else "all")
            if o.kind == "cycle":
                self._draw_crank(img, o, t)

    # ------------------------------------------------------------ one frame
    KEEP_MARGIN = 26.0                              # logical px a fallen body keeps from the frame's edge

    def _keep_in_frame(self, ops, pose, st, rf):
        """cine: how far (logical px) to move a person whose body is on its way down or lying on the floor, so the
        whole body stays inside the picture (it would otherwise fall out of the frame). 0 = no change: standing,
        on a set piece (the bed decides), riding, or the classic camera."""
        lean = abs(pose.get("tilt", 0.0))
        if getattr(self.plan, "camera", "") != "cine" or rf or st.get("on") or lean < 14:
            return 0.0
        xs = [px for op in ops for (px, _py) in op["pts"]]
        if not xs:
            return 0.0
        lo, hi, m = min(xs), max(xs), self.KEEP_MARGIN
        w = clamp((lean - 14.0) / 12.0)             # comes in as the body tips over (no jump at one angle)
        w = w * w * (3 - 2 * w)
        if hi - lo > LW - 2 * m:                    # longer than the picture is wide: centre it
            return (LW / 2.0 - (lo + hi) / 2.0) * w
        return (max(0.0, m - lo) - max(0.0, hi - (LW - m))) * w

    def _seated(self, c, t, st, action, pose, opts):
        """On a set piece: hips on the seat (sit), body on the mattress (lie). Any other action done
        while seated keeps the sitting legs, so a character can drink or talk on the sofa."""
        seat = self.sets.seat_height(st["on"])
        if seat is None:
            return pose
        k = c.draw_scale(t)
        lying = action in ("lie_down", "lie", "sleep_lie", "rofl")
        if not lying and action != "sit":
            legs = actions.pose_for("sit", 0.0, 1.0, 1.0, c.phase, opts)
            pose = dict(pose)
            for kk in ("ll1", "ll2", "rl1", "rl2", "th_k"):
                if kk in legs:
                    pose[kk] = legs[kk]
            for kk in ("tilt", "lift", "shift", "dx"):
                pose.pop(kk, None)
        else:
            pose = dict(pose)
        if lying:
            pose["lift"] = pose.get("lift", 0.0) - seat / k
        else:
            p_ = dict(DEFAULT_POSE)
            p_.update({kk: vv for kk, vv in pose.items() if vv is not None})
            lk = getattr(c, "leg_k", 1.0)
            p_["th_k"], p_["sh_k"] = p_.get("th_k", 1.0) * lk, p_.get("sh_k", 1.0) * lk
            fy = skeleton(p_)["fy"]                 # hips sit this high above the feet
            pose["lift"] = pose.get("lift", 0.0) + fy - (seat / k + 14.0)
        return pose

    SHADOW_W = {"dog": 0.75, "cat": 0.55, "cow": 1.5, "buffalo": 1.55, "goat": 0.7, "crow": 0.3, "parrot": 0.3, "rooster": 0.35,
                "lizard": 0.0, "mosquito": 0.0}

    def _contact_shadow(self, img, P):
        """Soft ellipse on the floor under a character; smaller and fainter while they jump, along the floor when
        they lie or fall."""
        pose, k, x, y = P["pose"], P["k"], P["x"], P["y"]
        lean = math.sin(math.radians(pose.get("tilt", 0.0)))
        lift = max(0.0, -pose.get("lift", 0.0) * k) if not P["animal"] else 0.0
        stretch = self.SHADOW_W.get(P["animal"], 1.0)
        if abs(lean) > 0.5 and not P["animal"]:     # lying / falling: the shadow follows the body
            x, stretch, lift = x + (pose.get("dx", 0.0) + lean * 380) * k, 1.0 + 2.2 * abs(lean), 0.0
        else:
            x += (pose.get("shift", 0.0) + pose.get("dx", 0.0)) * k
        shrink = 1.0 / (1.0 + lift / 260.0)
        w = max(2, int(2 * 118 * k * shrink * stretch * self.s))
        hh = max(2, int(2 * 20 * k * shrink * self.s))
        sp = self._shadow.resize((w, hh), Image.BILINEAR)
        a = 0.85 / (1.0 + lift / 200.0)
        sp.putalpha(sp.getchannel("A").point([int(v * a) for v in range(256)]))
        img.paste(sp, (int(x * self.s - w / 2), int((y + 6 * k) * self.s - hh / 2)), sp)

    def _light_level(self, t):
        lvl, prev, prev_t = 1.0, 1.0, 0.0
        for (t0, v) in sorted(self.plan.lights):
            if t < t0:
                break
            prev, lvl, prev_t = lvl, v, t0
        if t - prev_t < 0.18:                       # quick fade between levels
            lvl = prev + (lvl - prev) * (t - prev_t) / 0.18
        return lvl

    def _darken(self, img, level, t):
        """Lights off: the room goes dark blue; lamps, TVs and tubelights that are on keep glowing."""
        k = clamp(level)
        img = ImageChops.multiply(img, Image.new("RGB", img.size, (int(255 * k * 0.85), int(255 * k * 0.9),
                                                                   int(255 * min(1.0, k * 1.35)))))
        for (x, y, typ, sc) in self.sets.lights_on(t):
            if typ == "tubelight" and level < 0.5:
                continue
            cy = {"lamp": y - 650 * sc, "tv": y - 460 * sc, "tubelight": y - 1150 * sc}[typ]
            r = {"lamp": 420, "tv": 380, "tubelight": 600}[typ] * sc
            col = (255, 226, 150) if typ != "tv" else (170, 200, 255)
            p = Patch(x, cy, r, r, self.s, 1)
            for i in range(10):
                rr = r * (1 - i / 10.0)
                p.ellipse(x, cy, rr, rr, col + (int(16 + i * 2),), None)
            base = img.convert("RGBA")
            base.alpha_composite(p.im, (int(round(p.ox * self.s)), int(round(p.oy * self.s))))
            img = base.convert("RGB")
        return img

    # ------------------------------------------------------------ character state -> pose (smooth, alive)
    BLEND = 0.3           # seconds to cross-fade from one action's pose to the next
    # cine: a person takes longer for a big change (arms down -> arms up) than for a small one, and the body leads:
    # the hips / chest / head start first, the arms follow a beat later (overlapping action)
    BLEND_MIN, BLEND_MAX, BLEND_PX = 0.22, 0.46, 650.0
    BODY_KEYS = frozenset(("tilt", "lift", "shift", "dx", "head_tilt", "head_dx", "head_dy", "look_x", "look_y"))

    def _speaker_at(self, t, name):
        """The line someone else is saying at time t (latest started), or None."""
        best = None
        for sp in self.plan.speech:
            if sp["who"] != name and sp["start"] <= t < sp["end"] and sp.get("bubble") != "thought":
                if best is None or sp["start"] > best["start"]:
                    best = sp
        return best

    def _eff(self, c, t):
        """Everything that decides a character's pose at time t (no drawing)."""
        st = c.state_at(t)
        x, y = c.draw_pos(t)
        action, a_t0 = st["action"], st["action_t0"]
        mv = next((m for m in c.moves if m[0] <= t < m[1]), None)
        if mv and action in ("idle", "none", "stand", "talk"):
            action, a_t0 = ("run" if len(mv) > 6 and mv[6] else "walk"), 0.0
        if mv and st["facing"] == "front" and abs(mv[4] - mv[2]) > 1:
            st["facing"] = "right" if mv[4] > mv[2] else "left"          # face the way you walk
        if self._natural() and not c.spec.get("kind"):
            if st["facing"] in ("left", "right"):  # turning round goes through the front, it does not flip
                before = self._facing_at(c, t - self.TURN)
                if before in ("left", "right") and before != st["facing"]:
                    st["facing"] = "front"
            if action == "sit" and st.get("on") and st["facing"] == "front":
                # seen straight from the front a seated body looks like a standing one (the thighs point at the
                # camera): sit turned to the one you talk to, or alone toward the middle of the picture
                other = self._partner(c, t, x)
                if other is None:
                    other = LW / 2.0 if abs(x - LW / 2.0) > 40 else x + 1.0
                st["facing"] = "right" if other > x else "left"
        rf = c.ride_frame(t)
        listen = None
        if (not st["talking"] and not mv and not rf and action in ("idle", "none", "stand") and not st.get("on")
                and st.get("visible", True) and not c.spec.get("kind") and c.spec.get("view") != "back"):
            listen = self._speaker_at(t, c.name)
            if listen and st["look"] is None and listen["who"] in self.plan.chars \
                    and not self.plan.chars[listen["who"]].spec.get("hidden"):
                st["look"] = listen["who"]                            # listeners look at whoever is talking
        return dict(st=st, x=x, y=y, action=action, a_t0=a_t0, mv=mv, rf=rf, listen=listen,
                    dr=self._act_dir(c, st, mv, x, t))

    TURN = 0.12           # seconds a character spends facing the front while turning round

    def _natural(self):
        """The human-like motion (planted feet, turning, weight, drag) is part of the new camera's look;
        `CAMERA: classic` keeps the old motion exactly."""
        return getattr(self.plan, "camera", "") == "cine"

    def _facing_at(self, c, t):
        st = c.state_at(max(0.0, t))
        mv = next((m for m in c.moves if m[0] <= t < m[1]), None)
        if mv and st["facing"] == "front" and abs(mv[4] - mv[2]) > 1:
            return "right" if mv[4] > mv[2] else "left"
        return st["facing"]

    def _partner(self, c, t, x):
        """x of the nearest other person in the shot (to turn toward), or None."""
        xs = [o.draw_pos(t)[0] for o in self.plan.chars.values()
              if o is not c and not o.spec.get("hidden") and o.state_at(t).get("visible", True)
              and -100 <= o.draw_pos(t)[0] <= LW + 100]
        return min(xs, key=lambda ox: abs(ox - x)) if xs else None

    def _travel(self, c, t):
        """Logical px walked so far (all moves up to t): the legs step with the distance, so feet do not slide."""
        d = getattr(c, "travel0", 0.0)
        for m in c.moves:
            if m[0] >= t:
                break
            if m[1] - m[0] < 0.02:
                continue                            # (a snap onto a seat is not a walk)
            x1, y1 = c.pos_at(min(t, m[1]))
            d += math.hypot(x1 - m[2], y1 - m[3])
        return d

    @staticmethod
    def _key(E):
        return (E["action"], round(E["a_t0"], 4), E["dr"], E["st"].get("on"), bool(E["rf"]))

    def _build_pose(self, c, t, E):
        st, x, action, a_t0 = E["st"], E["x"], E["action"], E["a_t0"]
        opts = dict(st["opts"], _x=x, _bpm=self.plan.bpm, _prop=st["prop"], _dir=E["dr"], _facing=st["facing"],
                    _expr=st["expression"], _amp=self._amp(st["talking"], t) if st["talking"] else 0.0)
        at = t - a_t0 if action not in ("walk", "run") else t
        natural = self._natural() and not c.spec.get("kind")
        actions.SOFT_REACH = self._natural()        # arms slow into a full stretch; classic keeps the hard limit
        crouch = 0.0
        if natural and action in self.LEAPS and t - a_t0 < self.CROUCH:     # bend the knees before a jump
            crouch = math.sin(math.pi * (t - a_t0) / self.CROUCH)
            at = 0.0
        elif natural and action in self.LEAPS:
            at = t - a_t0 - self.CROUCH
        pose = actions.pose_for(action, at, st["speed"], st["intensity"], c.phase, opts)
        if E["rf"]:                                 # on a vehicle: the seat decides the pose
            pose = dict(E["rf"]["pose"])
        elif st.get("on"):
            pose = self._seated(c, t, st, action, pose, opts)
        elif E["listen"]:
            self._react(c, t, E, pose)
        if natural and E["mv"] and action in ("walk", "run") and not E["rf"] and not st.get("on"):
            self._planted_legs(c, t, E, pose, action)
        if natural and not E["rf"] and not st.get("on"):
            self._weight(c, t, E, pose, crouch)
        return pose

    # foot lock: (rig px the body travels per gait cycle = two steps, share of the cycle a foot is on the ground,
    # how far below the hip the feet are: knees a little bent so the stride can reach, step height)
    GAIT = {"walk": (440.0, 0.5, 0.92, 34.0), "run": (600.0, 0.38, 0.86, 70.0)}

    def _planted_legs(self, c, t, E, pose, action):
        """Legs by foot lock (inverse kinematics): a foot on the ground stays exactly where it was put down while
        the body passes over it, the other one lifts and swings forward. The steps follow the distance actually
        travelled, so the feet never slide (the old walk cycle ran on the clock and moonwalked)."""
        stride, duty, low, step_h = self.GAIT[action]
        lk = getattr(c, "leg_k", 1.0)                # tall / short legs take longer / shorter steps
        stride, step_h = stride * lk, step_h * lk
        k = max(0.05, c.draw_scale(t))
        mv = E["mv"]
        dirn = 1.0 if mv[4] >= mv[2] else -1.0
        phi = self._travel(c, t) / (stride * k)                    # gait cycles done
        th, sh = TH * pose.get("th_k", 1.0) * lk, SH * pose.get("sh_k", 1.0) * lk
        reach = (th + sh) * low
        bob = 0.0
        for side, hip_x, off in (("l", -32.0, 0.0), ("r", 32.0, 0.5)):
            ph = (phi + off) % 1.0
            if ph < duty:                               # on the ground: slides back under the hip at body speed
                rel = (0.5 - ph / duty) * duty * stride
                fy = reach
                bob = max(bob, math.sin(math.pi * ph / duty))
            else:                                       # in the air: swings forward and lifts
                u = (ph - duty) / (1.0 - duty)
                e = u * u * (3 - 2 * u)
                rel = (-0.5 + e) * duty * stride
                fy = reach - step_h * math.sin(math.pi * u)
            fx = hip_x + rel * dirn
            a1, a2 = self._leg_ik(hip_x, fx, fy, th, sh, dirn)
            pose[side + "l1"], pose[side + "l2"] = a1, a2
        swing = math.cos(2 * math.pi * phi)            # arms against the legs
        if action == "run":
            pose["la1"], pose["ra1"] = -10 - 34 * dirn * swing, 10 + 34 * dirn * swing
            pose["la2"], pose["ra2"] = pose["la1"] + 95 * dirn, pose["ra1"] + 95 * dirn
            pose["lift"] = -16 * abs(math.sin(2 * math.pi * phi))
        else:
            pose["la1"], pose["ra1"] = -14 - 16 * dirn * swing, 14 + 16 * dirn * swing
            pose["la2"], pose["ra2"] = pose["la1"] + 10 * dirn, pose["ra1"] + 10 * dirn
            pose["lift"] = -5 * bob                 # highest over the foot, lowest when both feet are down
        pose["tilt"] = 1.5 * dirn * (2.5 if action == "run" else 1.0)

    @staticmethod
    def _leg_ik(hx, fx, fy, th, sh, dirn):
        """Thigh and shin angles (0 = straight down, +90 = screen right) that put the foot at (fx, fy) from a hip
        at (hx, 0); the knee bends forward, the way the body goes."""
        dx, dy = fx - hx, fy
        d = max(1.0, min(math.hypot(dx, dy), th + sh - 0.5))
        base = math.atan2(dx, dy)
        cos_a = (th * th + d * d - sh * sh) / (2 * th * d)
        knee = base + math.acos(max(-1.0, min(1.0, cos_a))) * dirn
        kx, ky = hx + th * math.sin(knee), th * math.cos(knee)
        return math.degrees(knee), math.degrees(math.atan2(fx - kx, fy - ky))
    LEAPS = ("jump", "jump_joy", "celebrate", "jumping_jacks")
    CROUCH = 0.2                                    # seconds of bending the knees before taking off

    @staticmethod
    def _apply_crouch(pose):
        c = pose.pop("_crouch", 0.0)
        if not c:
            return pose
        pose["ll1"] = pose.get("ll1", -7.0) - 30 * c            # knees out, feet stay under the hips: the body sinks
        pose["ll2"] = pose.get("ll2", -2.0) + 26 * c
        pose["rl1"] = pose.get("rl1", 7.0) + 30 * c
        pose["rl2"] = pose.get("rl2", 2.0) - 26 * c
        pose["la1"] = pose.get("la1", -14.0) - 18 * c           # arms swing back, ready to throw up
        pose["ra1"] = pose.get("ra1", 14.0) + 18 * c
        return pose

    def _weight(self, c, t, E, pose, crouch):
        """Human weight: lean into a walk and settle back when stopping, bend before a jump, shift the weight
        from foot to foot while standing (never perfectly regular), and let the kurta hem / braid trail."""
        lo_t, hi_t = 0.0, 1e9                       # a snap to a new spot (an entrance's start) is not speed
        for m in c.moves:
            if m[1] - m[0] < 0.02:
                if m[1] <= t:
                    lo_t = max(lo_t, m[1])
                elif m[0] > t:
                    hi_t = min(hi_t, m[0] - 1e-4)

        def vx(tt):
            a_, b_ = max(lo_t, tt - 0.04), min(hi_t, tt + 0.04)
            return (c.draw_pos(b_)[0] - c.draw_pos(a_)[0]) / max(1e-3, b_ - a_) if b_ > a_ else 0.0
        v = vx(t)
        a = (vx(min(hi_t, t + 0.06)) - vx(max(lo_t, t - 0.06))) / 0.12
        if abs(v) > 1 or abs(a) > 30:               # moving: lean into it, a little more when speeding up
            pose["tilt"] = pose.get("tilt", 0.0) + clamp(v * 0.0055 + a * 0.0012, -6.0, 6.0)
        if crouch:                                  # (applied after the blend from the last action: _crouch)
            pose["_crouch"] = crouch
        if E["action"] in ("idle", "talk", "none", "stand") and not E["mv"]:   # weight from foot to foot
            ph = c.phase
            n1 = 0.6 * math.sin(0.37 * t + ph) + 0.4 * math.sin(0.83 * t + 2.1 * ph)
            n2 = 0.5 * math.sin(0.29 * t + 1.7 * ph) + 0.5 * math.sin(0.61 * t + 0.4)
            pose["shift"] = pose.get("shift", 0.0) + 5.0 * n1
            pose["tilt"] = pose.get("tilt", 0.0) + 0.9 * n1
            pose["head_tilt"] = pose.get("head_tilt", 0.0) + 1.8 * n2
        pose["drag"] = clamp(-v * 0.03, -22.0, 22.0)  # cloth trails behind the body

    def _react(self, c, t, E, pose):
        """A listener reacts to whoever is talking: nods, leans back from anger, tilts the head at questions."""
        sp = E["listen"]
        spk = self.plan.chars.get(sp["who"])
        if spk is None or spk.spec.get("hidden"):
            return
        ramp = clamp((t - sp["start"]) / 0.35) * clamp((sp["end"] - t) / 0.3)
        toward = 1 if spk.pos_at(t)[0] >= E["x"] else -1
        sx = spk.state_at(t)["expression"]
        if sx in actions.ANGRY:                                     # flinch / lean away
            pose["tilt"] = pose.get("tilt", 0.0) - 5 * toward * ramp
            pose["head_dy"] = pose.get("head_dy", 0.0) + 3 * ramp
        elif str(sp.get("text", "")).rstrip().endswith("?"):        # curious head tilt
            pose["head_tilt"] = pose.get("head_tilt", 0.0) + 8 * toward * ramp
        else:                                                       # nods every now and then
            q = (t - sp["start"] + c.phase * 0.7) % 1.7
            nod = math.sin(math.pi * q / 0.5) if q < 0.5 else 0.0
            pose["head_dy"] = pose.get("head_dy", 0.0) + 7 * nod * ramp
            pose["look_y"] = pose.get("look_y", 0.0) + 0.3 * nod * ramp
        if sx in actions.HAPPY:                                     # laughing along a little
            pose["lift"] = pose.get("lift", 0.0) - 3 * abs(math.sin(2 * math.pi * 2.6 * t)) * ramp

    _ANGLES = ("la1", "la2", "ra1", "ra2", "ll1", "ll2", "rl1", "rl2", "tilt", "head_tilt")
    _NUM_DEFAULTS = {"dx": 0.0, "drag": 0.0, "head_dx": 0.0, "head_dy": 0.0, "th_k": 1.0, "sh_k": 1.0, "arm_k": 1.0,
                     "la_k1": 1.0, "la_k2": 1.0, "ra_k1": 1.0, "ra_k2": 1.0,
                     "lift": 0.0, "shift": 0.0, "tilt": 0.0, "head_tilt": 0.0, "look_x": 0.0, "look_y": 0.0}

    def _blend_from_previous(self, c, t, E, pose, end=None, depth=0):
        """If the action (or its direction) changed less than BLEND seconds ago, cross-fade from the previous
        action's pose (still moving) to the new one. Back-to-back changes chain: a new blend starts from the
        half-finished blend that was on screen, not from the raw previous pose."""
        natural = self._natural()
        B = self.BLEND_MAX if natural else self.BLEND
        end = t if end is None else end
        t0 = max(0.0, t - B)
        if end <= t0 + 1e-6:
            return pose
        key = self._key(E)
        if self._key(self._eff(c, t0)) == key:
            return pose
        lo, hi = t0, end
        for _ in range(7):                       # find when the switch happened
            mid = (lo + hi) / 2
            if self._key(self._eff(c, mid)) == key:
                hi = mid
            else:
                lo = mid
        Eo = self._eff(c, max(t0, lo - 2e-3))     # (a step back: never the hair-thin instant between two events)
        if self._key(Eo) == key:
            Eo = self._eff(c, lo)
        if Eo["rf"]:
            return pose
        Eo["x"], Eo["y"] = E["x"], E["y"]
        old = self._build_pose(c, t, Eo)
        if depth < 2:
            old = self._blend_from_previous(c, t, Eo, old, end=lo, depth=depth + 1)
        sy = skeleton(DEFAULT_POSE)["shR"][1]       # shoulder height of the rig
        arms = {side: [self._arm_points(src, side, shx, sy) for src in (old, pose)]
                for side, shx in (("la", -56.0), ("ra", 56.0))}
        u = t - hi
        if natural:                                 # the time it takes follows how far the hands travel
            reach = max(math.hypot(b[2] - a[2], b[3] - a[3]) for a, b in arms.values())
            B = clamp(self.BLEND_MIN + reach / self.BLEND_PX, self.BLEND_MIN, self.BLEND_MAX)
            if u >= B:
                return pose
        w = clamp(u / B)
        w = w * w * (3 - 2 * w)
        w_body, w_arm = w, w
        if natural:                                 # the body leads, the arms follow
            w_body = clamp(u / (0.8 * B))
            w_body = w_body * w_body * (3 - 2 * w_body)
            w_arm = clamp((u - 0.12 * B) / (0.88 * B))
            w_arm = w_arm * w_arm * (3 - 2 * w_arm)
        out = dict(pose)
        for kk in set(old) | set(pose):
            if kk.startswith("_"):
                continue
            va = old.get(kk, DEFAULT_POSE.get(kk, self._NUM_DEFAULTS.get(kk)))
            vb = pose.get(kk, DEFAULT_POSE.get(kk, self._NUM_DEFAULTS.get(kk)))
            num = (isinstance(va, (int, float)) and isinstance(vb, (int, float)) and not isinstance(va, bool)
                   and not isinstance(vb, bool))
            if num:
                wk = w_body if kk in self.BODY_KEYS else w
                if kk in self._ANGLES:
                    dlt = ((vb - va + 180.0) % 360.0) - 180.0
                    out[kk] = va + dlt * wk
                else:
                    out[kk] = va + (vb - va) * wk
            elif w < 0.5:
                out[kk] = va
        # arms: move the elbow and hand along straight lines (angle blending can flip direction near 180 deg)
        for side, shx in (("la", -56.0), ("ra", 56.0)):
            (e0x, e0y, h0x, h0y), (e1x, e1y, h1x, h1y) = arms[side]
            ex, ey = e0x + (e1x - e0x) * w_arm, e0y + (e1y - e0y) * w_arm
            hx, hy = h0x + (h1x - h0x) * w_arm, h0y + (h1y - h0y) * w_arm
            ak = out.get("arm_k", 1.0)
            out[side + "1"] = math.degrees(math.atan2(ex - shx, ey - sy))
            out[side + "2"] = math.degrees(math.atan2(hx - ex, hy - ey))
            out[side + "_k1"] = math.hypot(ex - shx, ey - sy) / (UA * ak)
            out[side + "_k2"] = math.hypot(hx - ex, hy - ey) / (LA * ak)
        return out

    SMEAR_DT = (0.012, 0.024)   # cine: how far back (s) the faint trail of a fast hand is drawn
    SMEAR_PX = 15.0             # rig px a hand must travel (against the body) in SMEAR_DT[0] to leave a trail
    SMEAR_ALPHA = 0.42

    def _hand_rig(self, c, t):
        """Both hands, relative to the hips, in rig px (no camera, no size): what a smear is measured on."""
        E = self._eff(c, t)
        pose = self._build_pose(c, t, E)
        if not E["rf"]:
            pose = self._blend_from_previous(c, t, E, pose)
        sk = skeleton(dict(DEFAULT_POSE, **{k: v for k, v in pose.items() if not k.startswith("_")}))
        return sk["handL"], sk["handR"]

    def _smear(self, c, t, P):
        """cine: [(layer, (x, y))] faint copies of this person a moment ago, drawn under them while a hand moves
        very fast (a slap, a punch, a hammer coming down): the eye reads it as motion blur. Nothing otherwise."""
        if not self._natural() or P["animal"] or P["rf"] or c.spec.get("kind") or t < self.SMEAR_DT[1]:
            return []
        now = self._hand_rig(c, t)
        before = self._hand_rig(c, t - self.SMEAR_DT[0])
        fast = max(math.hypot(a[0] - b[0], a[1] - b[1]) for a, b in zip(now, before))
        a = clamp((fast - self.SMEAR_PX) / 40.0) * self.SMEAR_ALPHA
        if a <= 0.02:
            return []
        out = []
        for i, dt in enumerate(self.SMEAR_DT):
            G = self._prep(c, t - dt, {}, k=P["k"])
            r = render_ops(G["ops"], self.s, self.W, self.H)
            if r:
                layer, pos = r
                layer.putalpha(layer.getchannel("A").point(lambda v, m=a * (0.6 if i else 1.0): int(v * m)))
                out.append((layer, pos))
        return out[::-1]                        # the older (fainter) one first

    @staticmethod
    def _arm_points(src, side, shx, sy):
        """(elbow x, y, hand x, y) of one arm of a pose, in rig coordinates."""
        a1 = src.get(side + "1", DEFAULT_POSE[side + "1"])
        a2 = src.get(side + "2", DEFAULT_POSE[side + "2"])
        k_ = src.get("arm_k", 1.0)
        l1 = UA * k_ * src.get(side + "_k1", 1.0)
        l2 = LA * k_ * src.get(side + "_k2", 1.0)
        ex, ey = shx + l1 * math.sin(math.radians(a1)), sy + l1 * math.cos(math.radians(a1))
        return ex, ey, ex + l2 * math.sin(math.radians(a2)), ey + l2 * math.cos(math.radians(a2))

    def _look_value(self, c, t, E):
        look = E["st"]["look"]
        if isinstance(look, str) and look in self.plan.chars and look != c.name:
            ox, _oy = self.plan.chars[look].pos_at(t)
            return clamp((ox - E["x"]) / 350.0, -1, 1)
        if look == "left":
            return -1.0
        if look == "right":
            return 1.0
        if isinstance(look, (int, float)):
            return float(look)
        return None

    def _smooth_gaze(self, c, t, E, pose):
        """Eyes, gaze and the side the face points to glide over ~0.2 s instead of jumping;
        an expression change is hidden behind a blink."""
        samples = [(t, 0.5, E), (t - 0.08, 0.3, None), (t - 0.16, 0.2, None)]
        fv = {"left": -1.0, "right": 1.0}
        look_sum = face_sum = 0.0
        any_look = False
        own = pose.get("look_x", 0.0)
        prev_expr = None
        for ts, wgt, Es in samples:
            if Es is None:
                Es = self._eff(c, max(0.0, ts))
            lv = self._look_value(c, ts, Es)
            any_look = any_look or lv is not None
            look_sum += wgt * (lv if lv is not None else own)
            face_sum += wgt * fv.get(Es["st"]["facing"], 0.0)
            if ts != t and prev_expr is None:
                prev_expr = Es["st"]["expression"]
        if any_look:
            pose["look_x"] = look_sum
        pose["_facing_f"] = face_sum
        if prev_expr is not None and prev_expr != E["st"]["expression"]:
            pose["_face_change"] = True

    def _blinking(self, c, t):
        """Natural blinks: random 2-5.5 s apart, sometimes a double blink."""
        bl = self._blinks.get(c.name)
        if bl is None:
            import random as _r
            rnd = _r.Random(sum(map(ord, c.name)) * 7919 + 13)
            bl, tt = [], rnd.uniform(0.3, 2.0)
            while tt < self.plan.duration + 5:
                bl.append(tt)
                if rnd.random() < 0.15:
                    bl.append(tt + 0.24)
                tt += rnd.uniform(2.0, 5.5)
            self._blinks[c.name] = bl
        return any(b0 <= t < b0 + 0.11 for b0 in bl)

    def _act_dir(self, c, st, mv, x, t):
        """Which way a character acts (+1 = screen right): an explicit dir, else where it is walking to,
        else toward its look target, else its facing, else toward the middle of the screen."""
        o = st["opts"]
        if o.get("dir") in (1, -1, "left", "right"):
            return -1 if o["dir"] in (-1, "left") else 1
        if mv and abs(mv[4] - mv[2]) > 1:
            return 1 if mv[4] > mv[2] else -1
        look = st["look"]
        if isinstance(look, str) and look in self.plan.chars and look != c.name:
            return 1 if self.plan.chars[look].pos_at(t)[0] >= x else -1
        if st["facing"] in ("left", "right"):
            return -1 if st["facing"] == "left" else 1
        return 1 if x <= LW / 2 else -1

    def frame(self, t):
        """The picture at video time t (slow motion and freeze frames map it onto story time)."""
        if not self.plan.warps:
            return self.story_frame(t)
        ts, style = self.warp.at(t)
        img = self.story_frame(min(ts, self.plan.duration - 1e-3))
        if style == "grey":                         # freeze frame: almost black and white
            img = Image.blend(img, img.convert("L").convert("RGB"), 0.85)
        return img

    def _prep(self, c, t, states, k=None):
        """Everything about one character at time t (pose, drawing ops, anchors); painted by draw_char. k = draw
        them at this size instead of their own (the one-take walk from one place into the next)."""
        k = c.draw_scale(t) if k is None else k
        E = self._eff(c, t)
        st, x, y, action, a_t0, mv, rf = E["st"], E["x"], E["y"], E["action"], E["a_t0"], E["mv"], E["rf"]
        states[c.name] = st
        pose = self._build_pose(c, t, E)
        if not rf and not c.spec.get("kind"):
            pose = self._blend_from_previous(c, t, E, pose)     # one action flows into the next
        pose = self._apply_crouch(pose)
        singing = action in actions.SING_ACTIONS and not st["talking"]
        self._smooth_gaze(c, t, E, pose)        # eyes and face glide to a new target; a new face hides in a blink
        if c.ov and "look_x" in c.ov:           # a shot keeps them looking at the one they talk to
            pose["look_x"] = c.ov["look_x"]
        mouth_open = 0.0
        chewing = False
        if st["talking"]:
            mouth_open = self._lip_open(st["talking"], t)
        elif singing:                       # sings along to the music: believable mouth movement
            mouth_open = self._lip_open({}, t)
        elif pose.get("chew") is not None:  # eating
            mouth_open, chewing = float(pose["chew"]), pose["chew"] > 0.1
        blink = self._blinking(c, t) or pose.pop("_face_change", False)
        spec = dict(c.spec)
        spec["facing"] = st["facing"]
        if st.get("view") == "side" and not c.spec.get("kind") and not rf:   # `A -> side`: turned to the other one
            spec["view"] = "side"
            if spec["facing"] == "front":
                other = self._partner(c, t, x)
                spec["facing"] = "left" if other is not None and other < x else "right"
        if c.ov:                                    # this shot turns them (back to us / to the side / to someone)
            for key in ("view", "facing"):
                if key in c.ov:
                    spec[key] = c.ov[key]
        own = st["prop"]
        if own and pose.get("prop") and own == c.look_prop and c.spec.get("prop") is None:
            own = None                              # an action's own tool (the tau's lathi) beats the look's prop
        prop = own or ("mic" if singing else None) or pose.get("prop")
        if st["prop"] == "" or pose.get("hide_prop"):
            prop = None
        expr = pose.get("face") or st["expression"]      # some actions bring their own face (yawn, sneeze...)
        speaking = bool(st["talking"]) and st["talking"].get("bubble") != "thought"   # thoughts: lips shut
        if spec.get("kind") in ANIMALS:          # dog, cat, cow, crow, parrot: their own rig
            running = bool(mv and len(mv) > 6 and mv[6])
            dirn = -1 if st["facing"] == "left" else 1
            k_an = k * (0.82 if spec["kind"] in ("dog", "cat", "cow", "buffalo", "goat") else 1.0)   # next to these people
            ops, an = build_animal(spec, action, t - a_t0, t, x, y, k_an, dirn, bool(mv), running,
                                   mouth_open if speaking else 0.0, expr)
        else:
            ops, an = build_character(spec, pose, expr, mouth_open, t, x, y, k,
                                      blink=blink, prop=prop, talking=speaking or singing or chewing,
                                      tear_phase=(t * 1.1) % 1.0)
            dx = self._keep_in_frame(ops, pose, st, rf)
            if dx:                              # cine: a body on the floor slides back inside the picture
                x += dx
                ops, an = build_character(spec, pose, expr, mouth_open, t, x, y, k,
                                          blink=blink, prop=prop, talking=speaking or singing or chewing,
                                          tear_phase=(t * 1.1) % 1.0)
        return dict(ops=ops, an=an, rf=rf, pose=pose, x=x, y=y, k=k, animal=spec.get("kind"))

    mystery = None          # set by mystery.place_mystery: the strange thing that happens once in this video
    mascots = ()            # set by place_mascot: [{"kind", "who", "t0", "t1", "side", "level"}]

    def _draw_mascot(self, img, c, t, m):
        """The easter egg: a little bhoot / billi / chooha slides out from behind `c`, looks at us, blinks, and slides
        back. Drawn just before c, so c's body hides the part of it that is still behind them."""
        k = c.draw_scale(t)
        x, y = c.draw_pos(t)
        out = min((t - m["t0"]) / MASCOT_SLIDE, (m["t1"] - t) / MASCOT_SLIDE, 1.0)
        out = ease_in_out(clamp(out))
        if out <= 0.01:
            return
        r = MASCOT_R[m["kind"]] * k
        ax, ay = mascot_anchor(m["kind"], x, y, k, m["side"], m.get("level"))
        ax += m["side"] * (r * 1.6) * out           # slides out sideways from behind them
        if m["kind"] == "bhoot":
            ay += 6.0 * k * math.sin(t * 5.0)       # floats
        blink = abs((t - m["t0"]) - 0.75 * (m["t1"] - m["t0"])) < 0.07
        sprite = mascot_sprite(m["kind"], r * self.s, -m["side"], blink)
        if out < 0.999:
            sprite.putalpha(sprite.getchannel("A").point(lambda a_: int(a_ * min(1.0, out * 1.6))))
        img.paste(sprite, (int(ax * self.s - sprite.width / 2), int(ay * self.s - sprite.height / 2)), sprite)

    def actor(self, name, t, k=None):
        """One character alone at story time t, not cut off at the frame edge: (RGBA layer, (left, top) in this
        shot's frame pixels, prep) or None. The one-take walk carries them from this place into the next."""
        c = self.plan.chars[name]
        P = self._prep(c, t, {}, k)
        shifted = [dict(op, pts=[(x + LW, y) for x, y in op["pts"]]) for op in P["ops"]]
        r = render_ops(shifted, self.s, 3 * self.W, self.H)
        if not r:
            return None
        layer, (ox, oy) = r
        if self.bd25 is not None:
            ldir = self.bd25.light.get("dir", -1) * (-1 if self._view25(t)["mirror"] else 1)
            layer = shading.volume(layer, self.s * P["k"], ldir, self._tint25)
        return layer, (ox - int(round(LW * self.s)), oy), P

    def _shot_at(self, t):
        """The shot of a counter conversation at time t (studio.counter_shots), or None."""
        for sh in getattr(self.plan, "counter_shots", None) or ():
            if sh["t0"] <= t < sh["t1"]:
                return sh if sh["kind"] != "free" else None
        return None

    def story_frame(self, t, hide=(), bare=False, clean=False):
        """The picture at story time t. hide = names left out; bare = no lens vignette, captions, fades or whip
        streak (a part of the one-take walk between two places, put together by Sequence); clean = no speech
        bubbles or name tags either (the cover picture)."""
        shot = self._shot_at(t)
        if shot is None:
            return self._story_frame(t, hide, bare, clean, None)
        chars = self.plan.chars.values()
        for c in chars:                             # this shot moves / turns / hides people for a moment
            c.ov = shot["ov"].get(c.name)
        try:
            hide = tuple(hide) + tuple(n for n, o in shot["ov"].items() if o.get("hidden"))
            return self._story_frame(t, hide, bare, clean, shot)
        finally:
            for c in chars:
                c.ov = None

    def _counter_edge(self):
        """The counter's top, blurred, for the bottom of a reverse shot (the camera looks over it from behind, so
        only its top and what stands on it: no sign or writing, which would read backwards)."""
        if getattr(self, "_edge", None) is not None:
            return self._edge
        from PIL import ImageEnhance, ImageFilter
        s, im, flip = self.s, None, False
        seller = next((c for c in self.plan.chars.values() if getattr(c, "behind", None) is not None), None)
        b = getattr(seller, "behind", None)
        if b is not None and not isinstance(b, dict):
            im, (_ax, ay), _w = objects.sprite(b.kind, s * b.scale, b.color)
            if im is not None:                      # the top of the cart / counter and what is on it (not its sign)
                top = -232.0 if b.kind.startswith("thela") else -226.0
                k_ = s * b.scale
                im = im.crop((0, max(0, int(ay + (top - 150) * k_)), im.width, int(ay + (top + 60) * k_)))
                flip = True
        elif isinstance(b, dict):
            sprites = [sp for sp in (self.bd25.layered.sprites if self.bd25 is not None else [])
                       if sp.name in ("counter", "tapri")]
            if sprites:                             # 2.5D: the counter piece the people are sorted with
                i = (getattr(self.plan, "counters", None) or [0])[0]
                im = sprites[i if not self._auto25 and i < len(sprites) else 0].im   # (a hand-made set: all of them)
            elif self.bg.static is not None and getattr(self.plan, "counters", None):
                from . import counters
                place = self.plan.background.get("type") if isinstance(self.plan.background, dict) else None
                pieces = counters.counter_overlays(place, self.plan.counters[:1], self.bg.static,
                                                   self.bg.out_w / float(LW))
                im = pieces[0][1] if pieces else None
            if im is not None:
                bb = im.getchannel("A").getbbox()
                if bb:
                    im = im.crop((bb[0], bb[1], bb[2], bb[1] + max(4, int((bb[3] - bb[1]) * 0.42))))
        if im is None:
            im = Image.new("RGBA", (int(900 * s), int(160 * s)), (150, 104, 66, 255))
        im = im.convert("RGBA")
        if flip:
            im = ImageOps.mirror(im)
        a = im.getchannel("A")
        im = ImageEnhance.Brightness(im.convert("RGB")).enhance(0.86).convert("RGBA")   # its back is in shade
        im.putalpha(a)
        pad = int(30 * s)
        big = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
        big.paste(im, (pad, pad), im)
        self._edge = big.filter(ImageFilter.GaussianBlur(max(2.0, 8 * s)))
        return self._edge

    def _story_frame(self, t, hide, bare, clean, shot):
        plan, s = self.plan, self.s
        img = self._background(t)
        if shot is not None and shot.get("blur"):  # the reverse shot: the other side of the place, out of focus
            from PIL import ImageFilter
            img = ImageOps.mirror(img).filter(ImageFilter.GaussianBlur(max(2.0, 9 * s)))
        skip = set(shot.get("hide_objects", ())) if shot else set()
        self._draw_objects(img, t, False, skip)
        light = self._light_level(t)
        for im_, (px_, py_) in ([] if skip or (shot and shot.get("blur")) else self.sets.wall(t, power=light >= 0.5)):
            img.paste(im_, (px_, py_), im_)     # doors, windows, clocks, fans...
        if self.mystery and not (shot and shot.get("blur")):    # something strange behind the people (studio.mystery)
            mystery.draw(img, self.mystery, t, s)
        order = sorted((c for c in plan.chars.values() if not c.spec.get("hidden") and c.name not in hide),
                       key=lambda c: (c.draw_pos(t)[1], c.draw_pos(t)[0]))
        anchors = {}
        states = {}
        def prep_char(c):
            return self._prep(c, t, states)

        prep = {}
        for c in order:
            if c.state_at(t).get("visible", True):
                prep[c.name] = prep_char(c)

        def draw_char(c):
            P = prep.get(c.name) or prep_char(c)
            for gl, (gx, gy) in self._smear(c, t, P):     # cine: a fast hand leaves a faint trail behind it
                img.paste(gl, (gx, gy), gl)
            r = render_ops(P["ops"], s, self.W, self.H)
            if r:
                layer, (ox, oy) = r
                if self.bd25 is not None:           # 2.5D: the set's light falls on the people (colour, shadow side, rim)
                    ldir = self.bd25.light.get("dir", -1) * (-1 if self._view25(t)["mirror"] else 1)
                    layer = shading.volume(layer, s * P["k"], ldir, self._tint25)
                img.paste(layer, (ox, oy), layer)
            anchors[c.name] = P["an"]
            rf = P["rf"]
            if rf and rf["inside"] and rf["obj"].kind in objects.SPLIT:      # the body in front of the driver
                self._paste_object(img, rf["obj"], t, "front")

        if self.shadows:                            # soft contact shadows first, so none covers a neighbour
            for c in order:
                P = prep.get(c.name)
                if P and not P["rf"]:
                    self._contact_shadow(img, P)

        # everybody except the riders of a vehicle that is in front; then front objects; then those vehicles with their riders
        in_front = [c for c in order if self._front_rider(c, t)]
        floor = [] if shot and shot.get("no_floor") else sorted(
            self.sets.floor(t) + self._foreground(t)
            + [(o.y, None, o, 0) for o in plan.objects.values()     # a thela / counter somebody stands behind
               if getattr(o, "depth_sort", False) and not o.front and o.visible(t) and o.kind not in skip],
            key=lambda f: f[0])   # set pieces and the place's own front props (bed, sofa, tree, street
        # poles...) depth-sorted with the people

        def put(f):
            if f[1] is None:
                self._paste_object(img, f[2], t, "all")
            else:
                img.paste(f[1], (f[2], f[3]), f[1])
        fi = 0
        for c in order:
            while fi < len(floor) and floor[fi][0] <= c.draw_pos(t)[1]:
                put(floor[fi])
                fi += 1
            if c not in in_front and c.state_at(t).get("visible", True):
                for m in self.mascots:              # the easter egg peeks out from behind this person
                    if m["who"] == c.name and m["t0"] <= t <= m["t1"]:
                        self._draw_mascot(img, c, t, m)
                draw_char(c)
        for f in floor[fi:]:
            put(f)
        self._draw_objects(img, t, True, skip)
        if shot is not None and shot.get("edge"):  # the reverse shot: the counter's edge blurred in front of us
            z, vl, vt, vw, vh = self._cam_view(t)
            edge = self._counter_edge()
            w_ = int(vw * 1.3)
            e2 = edge.resize((w_, max(1, int(edge.height * w_ / edge.width))), Image.BILINEAR)
            img.paste(e2, (int(vl + vw / 2 - w_ / 2), int(vt + vh - e2.height * 0.62)), e2)
        for o in plan.objects.values():
            riders = [c for c in in_front if c.ride_frame(t)["obj"] is o]
            if riders and o.visible(t):
                self._paste_object(img, o, t, "back" if o.kind in objects.SPLIT else "all")
                if o.kind == "cycle":
                    self._draw_crank(img, o, t)
                for c in riders:
                    draw_char(c)
        if self.bd25 is not None:                   # 2.5D: blurred things right in front of the lens
            self.bd25.paste_front(img, t, self._view25(t))

        self.fx.draw_world(img, t, anchors, plan.chars)     # sweat, ?, POW, glowing eyes, thrown objects...
        if light < 0.995:
            img = self._darken(img, light, t)
        # rain, fog, lightning, spotlight...: over the whole scene but under bubbles and captions
        img = self.fx.draw_screen(img, t, {n: (a["head_center"][0] * s, a["head_center"][1] * s)
                                           for n, a in anchors.items()})
        if self._theme:                             # the video's colour mood (under the bubbles and captions)
            img = theme.grade(img, self._theme)
        if self.mystery:
            img = mystery.post(img, self.mystery, t)
        if self._look is not None:                  # the place's look: grade, glow, dark corners, grain
            img = self._look.apply(img, int(t * self.plan.fps))

        # camera first, so the speech bubbles can be kept inside the visible part of the frame
        z, vl, vt, vw, vh = self._cam_view(t)
        zb = max(1.0, z * 0.8)          # a bubble never grows more than ~1.25x on screen when the camera zooms
        sb = s / zb
        mar = 22 * s / max(z, 1.0)      # margin to the edge of the visible part (pre-zoom pixels)
        roll = camera_roll(plan, t) if z > 1.001 else 0.0
        if roll:                        # a tilted frame swings its corners in: keep the bubble clear of them
            mar += 0.5 * vh * abs(math.sin(math.radians(roll)))

        # labels + bubbles
        for c in ([] if clean else order):
            if c.name not in anchors:
                continue
            st, an = states[c.name], anchors[c.name]
            hx, hy = an["head_top"]
            top = hy
            if st["label"]:
                key = st["label"]
                if key not in self._label_cache:
                    self._label_cache[key] = styled_box(key, "tag", s)
                lab = self._label_cache[key]
                paste_rgba(img, lab, hx * s, hy * s - lab.height / 2 - 18 * s)
                top = hy - (lab.height / s) - 30
            sp = st["talking"]
            if sp and sp.get("bubble") == "thought":
                self.fx._thought(img, {"text": sp["text"], "_seed": 0}, t - sp["start"], 1.0, an)
            elif sp and sp.get("bubble", True):
                lt = 1.0 if sp.get("frozen") else t - sp["start"]     # said over a freeze frame: already open
                im0, _ = bubble_image(sp["text"], sb, 0)
                left = clamp(hx * s - im0.width * 0.35, max(24 * s, vl + mar), min(self.W - im0.width - 24 * s,
                                                                                     vl + vw - im0.width - mar))
                im, (tipx, tipy) = bubble_image(sp["text"], sb, int(hx * s - left))
                tx, ty = left + tipx, top * s - 12 * s
                sc = 0.55 + 0.45 * ease_out_back(lt / 0.22)
                paste_rgba(img, im, tx, ty, sc, 1.0, anchor=(tipx, tipy))
                if z > 1.001 and ty - tipy < vt + mar:          # bubble would be cut off at the top: tilt the camera up
                    vt = clamp(ty - tipy - mar, 0, self.H - vh)

        # camera crop
        if roll:                                    # cine: a tilted frame on an angry / scared line
            img = _rolled_crop(img, vl, vt, vw, vh, roll, self.W, self.H)
        elif z > 1.001:                             # (cine is always a little zoomed: bicubic keeps it as crisp
            img = img.resize((self.W, self.H),      # as an untouched frame; classic stays as it was)
                             Image.BICUBIC if getattr(plan, "camera", "") == "cine" else Image.BILINEAR,
                             box=(vl, vt, vl + vw, vt + vh))
        t_prev = camera_whip(plan, t, 1.0 / plan.fps) if getattr(plan, "camera", "") == "cine" and not bare else None
        if t_prev is not None:                      # cine: the camera swings to somebody else: streak the picture
            _z0, l0, _t0, w0, _h0 = self._cam_view(t_prev)
            k = int(min(abs((vl + vw / 2.0) - (l0 + w0 / 2.0)) * z * 0.5, 0.07 * self.W))
            if k >= max(3, int(0.012 * self.W)):
                img = img.resize((max(1, self.W // k), self.H), Image.BOX).resize((self.W, self.H), Image.BILINEAR)

        if bare:
            return img
        if self._vig is not None:                   # lens vignette: screen-fixed, under the captions
            img = ImageChops.multiply(img.convert("RGB"), self._vig)
        self.overlay_layer.draw(img, plan.overlays, t)    # captions stay screen-fixed (not zoomed)

        # fades
        f = 1.0
        if plan.fade_in and t < plan.fade_in:
            f = min(f, t / plan.fade_in)
        if plan.fade_out and t > plan.duration - plan.fade_out:
            f = min(f, (plan.duration - t) / plan.fade_out)
        if f < 0.999:
            img = Image.blend(Image.new("RGB", img.size, (0, 0, 0)), img, clamp(f))
        return img


LOOP_WHIP = 0.32            # LOOP: the last moment whips back into the opening frame
MASCOT_R = {"bhoot": 56.0, "billi": 46.0, "chooha": 34.0}      # head radius, logical px at a person's size
MASCOT_SLIDE = 0.28


def mascot_anchor(kind, x, y, k, side, level=None):
    """Where the mascot's head is when it is still hidden behind a person standing at (x, y) at size k: a bhoot
    over the shoulder, a billi at the knee, a chooha at the feet (level "high" = shoulder height for any)."""
    if level == "high" or kind == "bhoot":
        return x + side * 70.0 * k, y - 610.0 * k
    if kind == "billi":
        return x + side * 45.0 * k, y - 200.0 * k
    return x + side * 36.0 * k, y - 40.0 * k


_SPRITES = {}


def mascot_sprite(kind, r, look, blink):
    """RGBA picture of the mascot's head (+ the paws that hold on to the edge it peeks round); r in frame px."""
    key = (kind, int(r * 4), look, blink)
    if key in _SPRITES:
        return _SPRITES[key]
    SS = 3
    R = max(4.0, r) * SS
    W = int(R * 3.2)
    im = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = cy = W / 2.0
    ink, lw = (20, 20, 24, 255), max(2, int(R * 0.09))
    eye_dx = R * 0.36 + look * R * 0.08
    if kind == "bhoot":
        body = (246, 248, 255, 238)
        d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=body, outline=ink, width=lw)
        d.rectangle([cx - R + lw / 2, cy, cx + R - lw / 2, cy + R * 1.05], fill=body)
        for i in range(3):                          # the wavy hem
            bx = cx - R + R * (2 * i + 1) / 3.0
            d.ellipse([bx - R / 3, cy + R * 0.75, bx + R / 3, cy + R * 1.35], fill=body)
        d.line([(cx - R, cy), (cx - R, cy + R * 1.05)], fill=ink, width=lw)
        d.line([(cx + R, cy), (cx + R, cy + R * 1.05)], fill=ink, width=lw)
        for (ex, ey) in ((cx - eye_dx + look * R * 0.1, cy - R * 0.1), (cx + eye_dx * 0.6 + look * R * 0.1, cy - R * 0.1)):
            if blink:
                d.line([(ex - R * 0.14, ey), (ex + R * 0.14, ey)], fill=ink, width=lw)
            else:
                d.ellipse([ex - R * 0.13, ey - R * 0.2, ex + R * 0.13, ey + R * 0.2], fill=ink)
        d.ellipse([cx - R * 0.1 + look * R * 0.1, cy + R * 0.3, cx + R * 0.1 + look * R * 0.1, cy + R * 0.52],
                  fill=ink)                         # "o"
    else:
        fur = (232, 150, 70, 255) if kind == "billi" else (150, 150, 160, 255)
        inner = (246, 170, 180, 255)
        if kind == "billi":
            for sx in (-1, 1):
                d.polygon([(cx + sx * R * 0.85, cy - R * 0.25), (cx + sx * R * 0.75, cy - R * 1.35),
                           (cx + sx * R * 0.15, cy - R * 0.8)], fill=fur, outline=ink)
                d.polygon([(cx + sx * R * 0.72, cy - R * 0.45), (cx + sx * R * 0.68, cy - R * 1.05),
                           (cx + sx * R * 0.35, cy - R * 0.78)], fill=inner)
        else:
            for sx in (-1, 1):
                ex_, ey_ = cx + sx * R * 0.85, cy - R * 0.8
                d.ellipse([ex_ - R * 0.6, ey_ - R * 0.6, ex_ + R * 0.6, ey_ + R * 0.6], fill=fur, outline=ink, width=lw)
                d.ellipse([ex_ - R * 0.35, ey_ - R * 0.35, ex_ + R * 0.35, ey_ + R * 0.35], fill=inner)
        d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=fur, outline=ink, width=lw)
        eye = (110, 200, 90, 255) if kind == "billi" else ink
        for ex in (cx - eye_dx, cx + eye_dx):
            ex += look * R * 0.12
            if blink:
                d.line([(ex - R * 0.16, cy - R * 0.1), (ex + R * 0.16, cy - R * 0.1)], fill=ink, width=lw)
            else:
                d.ellipse([ex - R * 0.17, cy - R * 0.3, ex + R * 0.17, cy + R * 0.08], fill=eye, outline=ink)
                if kind == "billi":
                    d.line([(ex, cy - R * 0.26), (ex, cy + R * 0.04)], fill=ink, width=max(1, lw // 2))
        nx = cx + look * R * 0.15
        d.polygon([(nx - R * 0.12, cy + R * 0.18), (nx + R * 0.12, cy + R * 0.18), (nx, cy + R * 0.32)], fill=inner,
                  outline=ink)
        for sy in (0.22, 0.36):                     # whiskers
            for sx in (-1, 1):
                d.line([(nx + sx * R * 0.25, cy + R * sy), (nx + sx * R * 1.05, cy + R * (sy - 0.1 + 0.12 * sy))],
                       fill=ink, width=max(1, lw // 2))
        for sx in (-1, 1):                          # the paws holding on
            px = cx + sx * R * 0.55
            d.ellipse([px - R * 0.28, cy + R * 0.78, px + R * 0.28, cy + R * 1.12], fill=fur, outline=ink, width=lw)
    im = im.resize((max(1, W // SS), max(1, W // SS)), Image.LANCZOS)
    _SPRITES[key] = im
    return im


def place_mascot(parts, spec, seed, loop=False):
    """Hide the mascot in the video: during one line in the middle of the story it peeks out from behind someone the
    camera is showing at that moment (never on the first line or the punch line); with LOOP it peeks once more in
    the very last second ("bhai end me kya tha?"). Same video, same place; another video, another place."""
    kind = mascot_kind(spec)
    if not kind:
        return []
    people = lambda p: [c for c in p.plan.chars.values()                      # noqa: E731
                        if not c.spec.get("hidden") and not c.spec.get("kind")]
    lines = [(p, sp) for p in parts for sp in p.plan.speech
             if sp["who"] in p.plan.chars and p.plan.chars[sp["who"]] in people(p) and sp["end"] - sp["start"] > 0.9]
    pool = lines[1:-1] if len(lines) >= 3 else lines
    placed = []

    def seen(p, c, t, side, level):
        """Is the hidden spot (and the spot it slides out to) inside what the camera shows at t?"""
        z, vl, vt, vw, vh = p._cam_view(t)
        x, y = c.draw_pos(t)
        k = c.draw_scale(t)
        ax, ay = mascot_anchor(kind, x, y, k, side, level)
        r = MASCOT_R[kind] * k
        pts = [(ax, ay - r), (ax + side * 2.8 * r, ay + r)]
        m = 0.04 * vw
        return all(vl + m <= px * p.s <= vl + vw - m and vt + m <= py * p.s <= vt + vh - m for px, py in pts)

    def try_at(p, c, t0, t1, checks=None):
        others = [o.draw_pos(t0)[0] for o in people(p) if o is not c and o.state_at(t0).get("visible", True)]
        x = c.draw_pos(t0)[0]
        near = min(others, key=lambda ox: abs(ox - x)) if others else None
        sides = [(-1 if near > x else 1)] if near is not None else [1 if seed % 2 else -1]
        sides.append(-sides[0])
        for level in (None, "high"):
            for side in sides:
                if all(seen(p, c, t, side, level) for t in (checks or (t0, (t0 + t1) / 2, t1))):
                    return {"kind": kind, "who": c.name, "t0": t0, "t1": t1, "side": side, "level": level}
        return None

    for j in range(len(pool)):
        p, sp = pool[(seed + j) % len(pool)]
        t0 = sp["start"] + 0.25
        m = try_at(p, p.plan.chars[sp["who"]], t0, min(sp["end"], t0 + 1.9))
        if m:
            p.mascots = list(p.mascots) + [m]
            placed.append(m)
            break
    if loop and parts:
        p = parts[-1]
        t1 = p.plan.duration - LOOP_WHIP - 0.1
        t0 = t1 - 0.7
        z, cx, cy, _dx, _dy = camera_at(p.plan, t1)                # whoever the camera ends on (the reaction)
        cands = sorted((c for c in people(p) if c.state_at(t1).get("visible", True)),
                       key=lambda c: abs(c.draw_pos(t1)[0] - cx))
        for c in cands:
            m = try_at(p, c, t0, t1, ((t0 + t1) / 2, t1))
            if m:
                p.mascots = list(p.mascots) + [m]
                placed.append(m)
                break
    return placed


class Looped(Output):
    """LOOP: the reel's last moment whips back into its own first frame, so when Instagram plays it again there is
    no seam (people watch it twice before they notice). Wraps a Renderer / Sequence."""

    def __init__(self, video):
        self.v = video
        for key in ("W", "H", "fps", "duration", "n_frames", "speech", "sfx", "music"):
            setattr(self, key, getattr(video, key))
        self.ambience = getattr(video, "ambience", [])
        self.parts = getattr(video, "parts", [video])
        self.loop_fade = LOOP_WHIP
        self._first = None

    def frame(self, t):
        img = self.v.frame(t)
        start = self.duration - LOOP_WHIP
        if t < start:
            return img
        if self._first is None:
            self._first = self.v.frame(0.0)
        last = (self.n_frames - 1) / float(self.fps)
        e = ease_in_out(clamp((t - start) / max(1e-6, last - start)))      # the very last frame IS the first one
        off = int(round(self.W * e))
        canvas = Image.new("RGB", img.size)
        canvas.paste(img, (-off, 0))
        canvas.paste(self._first, (self.W - off, 0))
        k = int(0.06 * self.W * math.sin(math.pi * e))                      # a whip streaks the picture
        if k >= 3:
            canvas = canvas.resize((max(1, self.W // k), self.H), Image.BOX).resize((self.W, self.H), Image.BILINEAR)
        return canvas


PAN_SPEED = {False: 400.0, True: 820.0}    # one-take walk between places: walking / running pace, logical px/s
PAN_MIN = {False: 2.2, True: 1.7}          # ... and its shortest time (the camera has a whole picture to cross)


def pan_geometry(prev, sub):
    """The walk of sub["pan"]["who"] from the end of the shot `prev` (a Renderer) into the scene `sub`:
    where they start / stop, which way, how far and how long. None when it cannot be done."""
    pan = sub.get("pan")
    who = pan.get("who") if isinstance(pan, dict) else None
    if who not in prev.plan.chars or who not in sub.get("characters", {}) or prev.plan.chars[who].spec.get("hidden"):
        return None
    c = prev.plan.chars[who]
    t0 = prev.plan.duration
    xa, ya = c.pos_at(t0)
    xa = clamp(xa, -150.0, LW + 150.0)
    dirn = -1 if pan.get("dir") == "left" else 1
    xb = start_xs(sub).get(who, LW / 2.0)
    dist = max(300.0, LW + dirn * (xb - xa))
    run = bool(pan.get("run"))
    dur = clamp(dist / (PAN_SPEED[run] * 0.8), PAN_MIN[run], 4.5)
    return dict(who=who, t0=t0, xa=xa, ya=ya, xb=xb, dirn=dirn, dist=dist, run=run, dur=round(dur, 3),
                title=pan.get("title"))


def link_pan(prev, part, g):
    """Both shots act out the walk: the one leaving walks out of `prev` after its end, and walks into `part` (whose
    story waits g["dur"] seconds for them). Both cameras show the whole picture while it happens."""
    who, t0, dur, dirn, dist, run = g["who"], g["t0"], g["dur"], g["dirn"], g["dist"], g["run"]
    side = "right" if dirn > 0 else "left"
    ca, cb = prev.plan.chars[who], part.plan.chars[who]
    end_a = ca.state_at(t0)
    ca.events.append({"t": t0, "action": "idle", "facing": side})
    ca.moves.append((t0, t0 + dur, g["xa"], g["ya"], g["xa"] + dirn * dist, g["ya"], run, "pan"))
    prev.plan.wide = list(getattr(prev.plan, "wide", [])) + [(t0, t0 + dur + 60.0, 0.8, 0.0)]
    xb = cb.x
    cb.moves.insert(0, (0.0, dur, xb - dirn * dist, cb.y, xb, cb.y, run, "pan"))
    cb.events[:0] = [{"t": 0.0, "facing": side, "expression": end_a["expression"], "prop": end_a["prop"]},
                     {"t": dur, "facing": cb.spec.get("facing", "front")}]     # (what they carry, they still carry)
    cb.events.sort(key=lambda e: e["t"])
    cb.travel0 = prev._travel(ca, t0)               # the feet keep their step from one place into the next
    part.plan.wide = list(getattr(part.plan, "wide", [])) + [(-1.0, dur, 0.0, 0.9)]
    for name, vol, at in (("whoosh", 0.5, 0.05), ("footsteps", 0.5, 0.15), ("footsteps", 0.45, 1.6)):
        if (name == "whoosh") != run and name == "whoosh":
            continue
        path = audio.sfx_path(name)
        if path and at < dur:
            part.sfx.append(dict(t=at, path=path, volume=vol))
    g["k"] = (ca.draw_scale(t0), cb.draw_scale(dur))


class Sequence(Output):
    """Several scenes back to back + whole-video music and overlays."""

    def __init__(self, scene, width=1080, use_tts=True, fps=None, tts_provider=None):
        meta = scene.get("meta", {})
        fps = int(fps or meta.get("fps", 30))
        subs = split_scenes(scene)
        voices = prepare_voice(subs, use_tts, tts_provider)      # one Gemini request for ALL scenes
        self.parts, self.pans = [], []
        for sub, v in zip(subs, voices):
            g = pan_geometry(self.parts[-1], sub) if self.parts and sub.get("pan") else None
            if g:                                   # one take: this scene waits while they walk in
                sub = dict(sub, lead_in=max(float(sub.get("lead_in", 0.0)), g["dur"]))
                if g["title"]:                      # the place's title while they walk in (gone before anyone talks)
                    sub["overlays"] = list(sub.get("overlays", [])) + [
                        {"text": g["title"], "style": "card", "pos": "upper", "from": max(0.3, g["dur"] - 1.5),
                         "to": g["dur"] + 0.1, "color": [40, 40, 48]}]
            part = Renderer(sub, width, use_tts, fps, tts_provider, v)
            if g:
                link_pan(self.parts[-1], part, g)
            self.parts.append(part)
            self.pans.append(g)
        self.W, self.H = self.parts[0].W, self.parts[0].H
        self.s = self.W / float(LW)
        self.fps = fps
        self.transition = scene.get("transition", meta.get("transition", "fade"))
        self.offsets, off = [], 0.0
        for p in self.parts:
            self.offsets.append(off)
            off += p.duration
        self.duration = round(off, 3)
        self.n_frames = int(round(self.duration * fps))
        self.speech = [dict(sp, start=sp["start"] + o) for p, o in zip(self.parts, self.offsets) for sp in p.speech]
        self.sfx = [dict(fx, t=fx["t"] + o) for p, o in zip(self.parts, self.offsets) for fx in p.sfx]
        self.ambience = [dict(a, start=a["start"] + o) for p, o in zip(self.parts, self.offsets) for a in p.ambience]
        self.music = compile_music(scene.get("music") or meta.get("music"), self.duration)
        self.sound = scene.get("_sound")
        self.overlays = static_overlays(scene)
        self.overlay_layer = OverlayLayer(self.s)
        self.fade_in, self.fade_out = float(meta.get("fade_in", 0)), float(meta.get("fade_out", 0))

    def _part_at(self, t):
        i = 0
        while i + 1 < len(self.parts) and t >= self.offsets[i + 1]:
            i += 1
        return i

    def _pan_frame(self, i, tau):
        """The one take: the camera travels with the one walking, out of the last place and into this one.
        Both places are drawn without them, side by side, sliding by; they are drawn on top, stepping with the
        ground (their feet stay planted on it as it slides)."""
        prev, part, g = self.parts[i - 1], self.parts[i], self.pans[i]
        who, dirn, dist, dur = g["who"], g["dirn"], g["dist"], g["dur"]
        u = clamp(tau / dur)
        x = g["xa"] + dirn * dist * ease_travel(u)                  # the walker, in the last place's coordinates
        on_screen = lerp(g["xa"], g["xb"], ease_in_out(u))        # ... and where the camera keeps them
        miss = dirn * LW - (g["xa"] + dirn * dist - g["xb"])       # (0 unless the walk had to be lengthened)
        cam = x - on_screen + miss * ease_in_out(u)
        off_a = int(round(-cam * self.s))
        off_b = off_a + dirn * self.W
        t_a = g["t0"] + tau
        img = Image.new("RGB", (self.W, self.H))
        img.paste(prev.story_frame(t_a, hide=(who,), bare=True), (off_a, 0))
        img.paste(part.story_frame(tau, hide=(who,), bare=True), (off_b, 0))
        self._seam(img, off_a + (self.W if dirn > 0 else 0), dirn, clamp(u / 0.15) * clamp((1.0 - u) / 0.15))
        in_prev = (x < LW) if dirn > 0 else (x > 0)
        src, ts, off = (prev, t_a, off_a) if in_prev else (part, tau, off_b)
        k = lerp(g["k"][0], g["k"][1], ease_in_out(u))
        r = src.actor(who, ts, k)
        if r:
            layer, (ox, oy), P = r
            if src.shadows:
                src._contact_shadow(img, dict(P, x=P["x"] + off / self.s))
            img.paste(layer, (ox + off, oy), layer)
        if part._vig is not None:
            img = ImageChops.multiply(img, part._vig)
        part.overlay_layer.draw(img, part.plan.overlays, tau)
        return img

    def _seam(self, img, x, dirn, alpha=1.0):
        """Where one place meets the next: the edge of a wall (a corner, with its shadow on the far side). It
        fades in / out at the frame edges, where the take starts and lands on an ordinary shot."""
        w = max(4, int(0.03 * self.W))
        if x + w < 0 or x - w > self.W or alpha <= 0.0:
            return
        band = Image.new("RGBA", (2 * w, self.H), (0, 0, 0, 0))
        d = ImageDraw.Draw(band)
        for i in range(2 * w):                      # the wall's edge, lit on one side
            f = i / (2.0 * w - 1)
            c = int(lerp(178, 118, f)) if dirn > 0 else int(lerp(118, 178, f))
            d.line([(i, 0), (i, self.H)], fill=(c, c - 6, c - 16, 255))
        d.line([(0, 0), (0, self.H)], fill=(16, 16, 16, 255), width=max(2, w // 6))
        d.line([(2 * w - 1, 0), (2 * w - 1, self.H)], fill=(16, 16, 16, 255), width=max(2, w // 6))
        if alpha < 1.0:
            band.putalpha(band.getchannel("A").point(lambda a_: int(a_ * alpha)))
        img.paste(band, (x - w, 0), band)
        sh = Image.new("L", (3 * w, self.H), 0)     # its soft shadow on the next place
        ds = ImageDraw.Draw(sh)
        for i in range(3 * w):
            ds.line([(i, 0), (i, self.H)], fill=int(70 * alpha * (1 - i / (3.0 * w))))
        if dirn < 0:
            sh = ImageOps.mirror(sh)
        dark = Image.new("RGB", sh.size, (0, 0, 0))
        img.paste(dark, (x + w if dirn > 0 else x - 4 * w, 0), sh)

    def frame(self, t):
        i = self._part_at(t)
        part, lt = self.parts[i], t - self.offsets[i]
        pan = self.pans[i]
        img = self._pan_frame(i, lt) if pan and lt < pan["dur"] else part.frame(lt)
        D = 0.28
        cut_in = bool(part.plan.cut_in or pan)                              # a CUT shot / one take: no whip / fade
        cut_out = i + 1 < len(self.parts) and bool(self.parts[i + 1].plan.cut_in or self.pans[i + 1])
        if i > 0 and lt < D and self.transition == "whip" and not cut_in:
            prev = self.parts[i - 1]
            old = prev.frame(prev.duration - 1.0 / self.fps)
            e = ease_in_out(lt / D)
            canvas = Image.new("RGB", img.size)
            canvas.paste(old, (int(-self.W * e), 0))
            canvas.paste(img, (int(self.W * (1 - e)), 0))
            img = canvas
        elif self.transition == "fade":
            f = 1.0
            if i > 0 and lt < D / 2 and not cut_in:
                f = lt / (D / 2)
            if i + 1 < len(self.parts) and part.duration - lt < D / 2 and not cut_out:
                f = min(f, (part.duration - lt) / (D / 2))
            if f < 0.999:
                img = Image.blend(Image.new("RGB", img.size, (0, 0, 0)), img, clamp(f))
        self.overlay_layer.draw(img, self.overlays, t)
        f = 1.0
        if self.fade_in and t < self.fade_in:
            f = t / self.fade_in
        if self.fade_out and t > self.duration - self.fade_out:
            f = min(f, (self.duration - t) / self.fade_out)
        if f < 0.999:
            img = Image.blend(Image.new("RGB", img.size, (0, 0, 0)), img, clamp(f))
        return img


def make_video(scene, width=1080, use_tts=True, fps=None, tts_provider=None, dialogue=None, hook=None, style=None,
               loop=None, mascot=None):
    """loop: True = LOOP mode (the reel runs round without a seam); mascot: bhoot | billi | chooha | off (hidden
    easter egg). Both also come from the script (`LOOP: on`, `MASCOT: billi`) / the scene ("loop", "mascot")."""
    scene = gemini_music.prepare(scene, use_tts)        # `MUSIC: gemini ...`: the song (or the beat if Gemini cannot)
    scene = sound.prepare(scene, use_tts)               # `SOUND: ...`: the lines timed to a viral sound (its voice)
    if scene.get("_sound"):
        use_tts, hook = False, (None if hook == "first" else hook)    # the sound starts with the first frame
    if dialogue or hook:
        scene = apply_options(scene, dialogue, hook)
    if style:                                       # "2d" / "2.5d" from the command line / web page wins
        scene = dict(scene, style=styles.normalize(style))
    if loop or (scene.get("loop") and not scene.get("_looped")):
        scene = apply_loop(scene)
    if mascot is not None:
        scene = dict(scene, mascot=mascot)
    mood = scene["music"].get("style") if isinstance(scene.get("music"), dict) else None
    if mood and "mood" not in scene.get("meta", {}):    # the music's mood colours every place (studio.look)
        scene = dict(scene, meta=dict(scene.get("meta", {}), mood=mood))
    if scene.get("scenes"):
        v = Sequence(scene, width, use_tts, fps, tts_provider)
        parts = v.parts
    else:
        v = Renderer(scene, width, use_tts, fps, tts_provider)
        parts = [v]
    if scene.get("mascot"):
        seed = zlib.crc32(str(scene.get("hook") or scene.get("name") or "reel").encode("utf-8"))
        place_mascot(parts, scene["mascot"], seed, bool(scene.get("loop")))
    mystery.place_mystery(parts, mystery.seed_of(scene), scene.get("mystery", "auto"))
    return Looped(v) if scene.get("loop") else v


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render a scene.json to mp4")
    ap.add_argument("scene")
    ap.add_argument("-o", "--out", default=None, help="output .mp4 (or .png with --frame)")
    ap.add_argument("--width", type=int, default=1080, help="output width in px (height is 16:9 portrait)")
    ap.add_argument("--fps", type=int, default=None)
    ap.add_argument("--no-tts", action="store_true", help="skip speech synthesis (estimated timing, silent voice)")
    ap.add_argument("--tts", choices=["auto", "gemini", "elevenlabs", "edge"], default=None,
                    help="voice engine: gemini = the WHOLE video's script in ONE Gemini request, then split per line "
                         "(needs GEMINI_API_KEY); elevenlabs = ElevenLabs per line (needs ELEVENLABS_API_KEY; falls back "
                         "to gemini / edge if it fails); edge = edge-tts per line; auto (default) = gemini if a key is set")
    ap.add_argument("--frame", type=float, default=None, help="render one PNG frame at this time (seconds)")
    ap.add_argument("--dialogue", choices=DIALOGUE_MODES, default=None,
                    help="spoken words: bubble (default) | subtitle (at the bottom) | both | none (voice only)")
    ap.add_argument("--style", choices=["2d", "2.5d"], default=None,
                    help="look: 2d (default) | 2.5d (kitchen, gully, chai_tapri, kirana, terrace as layered sets)")
    ap.add_argument("--cover", action="store_true", help="save the cover picture (PNG) instead of the video")
    ap.add_argument("--color", default=None, help="colour mood: auto | classic | golden | cool | rose | teal_orange | "
                                                   "punchy | lime (default: the script's COLOR line / its own)")
    ap.add_argument("--cta", choices=["card", "sticker", "caption"], default=None,
                    help="CTA: card (end card) | sticker (small, during the punch line) | caption (only in the post)")
    ap.add_argument("--loop", action="store_true",
                    help="LOOP mode: no end card, the last moment whips back into the first frame (watched twice)")
    ap.add_argument("--mascot", choices=["bhoot", "billi", "chooha", "off"], default=None,
                    help="hide a little mascot (easter egg) in the video; off = none even if the script asks")
    ap.add_argument("--silent-copy", action="store_true",
                    help="sound mode: also write <out>.insta.mp4 without the sound (to add it inside Instagram)")
    ap.add_argument("--hook", choices=HOOK_MODES, default=None, dest="hook_mode",
                    help="hook card: over (over the first line, default) | first (hook card, then the story) | off")
    args = ap.parse_args(argv)

    scene = load_scene(args.scene)
    name = os.path.splitext(os.path.basename(args.scene))[0]
    if args.color:
        import copy
        scene = theme.apply(copy.deepcopy(scene), theme.resolve(args.color) or theme.auto(scene.get("hook")))
    if args.cta:
        scene = apply_cta(scene, args.cta)
    r = make_video(scene, args.width, use_tts=not args.no_tts, fps=args.fps, tts_provider=args.tts,
                   dialogue=args.dialogue, hook=args.hook_mode, style=args.style, loop=args.loop or None,
                   mascot=args.mascot)
    if args.cover:
        from .cover import make_cover
        out = args.out or os.path.join("out", name + ".cover.png")
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        make_cover(r, scene if args.mascot is None else dict(scene, mascot=args.mascot)).save(out)
        print("saved", out)
        return
    if args.frame is not None:
        out = args.out or os.path.join("out", name + ".png")
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        r.frame(args.frame).save(out)
        print("saved", out)
        return
    out = args.out or os.path.join("out", name + ".mp4")
    if getattr(r, "sound", None) and args.silent_copy:     # sound mode: also a copy without the sound
        insta = os.path.splitext(out)[0] + ".insta.mp4"
        r.with_sound = False
        r.render_video(insta)
        with_sound(insta, r.sound["path"], out)
        print("saved %s (with the sound) and %s (without it)" % (out, insta))
        return
    r.render_video(out)                             # (sound mode: the sound is in it, from the first frame)


def with_sound(video, sound_path, out):
    """The video + the sound mixed in from 0:00 (video copied as it is)."""
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-i", sound_path, "-filter_complex",
           "[1:a]aresample=44100,aformat=channel_layouts=stereo[s];[0:a][s]amix=inputs=2:normalize=0:duration=first,"
           "alimiter=limit=0.95[a]", "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
           "-movflags", "+faststart", out]
    if subprocess.run(cmd).returncode:
        raise SystemExit("ffmpeg could not add the sound")


if __name__ == "__main__":
    main()

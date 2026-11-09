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

import numpy as np
from PIL import Image, ImageChops, ImageOps

from . import actions, audio, gemini_music, objects, rides, styles, ui
from .backgrounds import Background
from .characters import LA, UA, DEFAULT_POSE, build_character, render_ops, skeleton
from .scene import (DIALOGUE_MODES, GROUND_Y, HOOK_MODES, apply_options, camera_at, compile_music, compile_scene,
                    prepare_voice, split_scenes, static_overlays)
from .animals import ANIMALS, build_animal
from .effects import Effects, Patch
from .sets import Sets
from .style25d import shading
from .text import bubble_image, chat_image, styled_box
from .util import LH, LW, clamp, ease_in_out, ease_out, ease_out_back, load_scene

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
        key = json.dumps([o.get("text"), o.get("style"), o.get("color"), o.get("size"), o.get("max_w")], default=str)
        if key not in self._cache:
            self._cache[key] = styled_box(str(o.get("text", "")), o.get("style", "caption_box"), self.s,
                                          o.get("color"), o.get("size"), o.get("max_w"))
        return self._cache[key]

    def _chat(self, o, shown, typing=None):
        key = (id(o), shown, typing)
        if key not in self._cache:
            self._cache[key] = chat_image(o["chat"], shown, self.s, typing=typing)
        return self._cache[key]

    UI_DUR = {"notification": 3.0, "loading": 3.0, "counter": 3.0, "timecard": 1.6, "chapter": 2.2}
    UI_POS = {"notification": (540, 150), "loading": (540, 900), "counter": (540, 720), "chapter": (540, 330)}

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
        mus = None
        if self.music:
            if not self.music["generated"]:
                cmd += ["-stream_loop", "-1"]
            cmd += ["-i", self.music["path"]]
            filters.append("[%d:a]aresample=44100,aformat=channel_layouts=mono,atrim=0:%.2f,volume=%.2f[mus]"
                           % (idx, self.duration, self.music["volume"]))
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
        self.bg = Background(bg_spec, int(self.W * ang["zoom"] + 0.5), int(self.H * ang["zoom"] + 0.5))
        self.bd25 = self._backdrop25(preset, scene) if preset else None
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
        vig_default = 0.0 if own_picture else 0.16
        if self.bd25:
            vig_default = float(self.bd25.light.get("vignette", vig_default))
        self._vig = _vignette(self.W, self.H, float(meta.get("vignette", vig_default)))   # 0 = off
        self._tint25 = tuple(self.bd25.light["ambient"]) if self.bd25 and self.bd25.light.get("ambient") else None

    # ------------------------------------------------------------ helpers
    def _lip_open(self, sp, t):
        fps = self.plan.fps
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
        if sp.get("audio"):
            if id(sp) not in self._lip:
                self._lip[id(sp)] = audio.lip_envelope(sp["audio"], self.plan.fps)
            env = self._lip[id(sp)]
            if env is not None and len(env):
                fps = self.plan.fps
                i = int((t - sp["start"]) * fps)
                seg = env[max(0, i - int(0.35 * fps)):max(1, i + 2)]
                return float(sum(seg) / len(seg)) if len(seg) else 0.0
        return 0.5 + 0.2 * math.sin(t * 2.1) * math.sin(t * 0.9 + 1.0)

    # ------------------------------------------------------------ 2.5D sets
    def _backdrop25(self, preset, scene):
        from .locations import grade
        from .style25d.scenery import StudioBackdrop
        time = (scene.get("background") or {}).get("time")
        native = styles.NATIVE_TIME.get(preset)
        same = time in (None, "", "day", native) or (native == "sunset" and time == "evening")
        cams = [sg[3] for sg in self.plan.cam_segments] + ([1.05] if self.plan.shakes else [])
        zmax = self.plan.angle["zoom"] * max([1.0] + cams)
        extra = []
        if preset.startswith("auto:") and self.bg.ambient:
            from .style25d.scenery import Layer
            bg = self.bg

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
                              extra=extra)

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
        z, cx, cy, dx, dy = camera_at(self.plan, t)
        if dx or dy:
            z = max(z, 1.05)
        vw, vh = self.W / max(z, 1.0), self.H / max(z, 1.0)
        mirror = ang["mirror"] and self.bd25.preset not in styles.NO_MIRROR
        v = dict(za=za, La=int(left) / (s * za), Ta=int(top) / (s * za), zc=max(z, 1.0), mirror=mirror,
                 vl=clamp((cx + dx) * s - vw / 2, 0, self.W - vw), vt=clamp((cy + dy) * s - vh / 2, 0, self.H - vh))
        self._view25_t, self._view25_v = t, v
        return v

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
        if self.bd25 is not None and not self._auto25:
            return self.bd25.floor_items(self._view25(t))
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

    def _draw_objects(self, img, t, front):
        """Set objects (vehicles, bins, bags...): `front` ones over the characters, the rest behind them.
        (A `front` vehicle with somebody in it is drawn later, together with its riders.)"""
        for o in self.plan.objects.values():
            if not o.visible(t):
                continue
            riders = self._riders_of(o, t)
            if o.front and riders:                  # drawn together with its riders, over everybody
                continue
            if o.front != front:
                continue
            self._paste_object(img, o, t, "back" if (riders and o.kind in objects.SPLIT) else "all")
            if o.kind == "cycle":
                self._draw_crank(img, o, t)

    # ------------------------------------------------------------ one frame
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
            fy = skeleton(p_)["fy"]                 # hips sit this high above the feet
            pose["lift"] = pose.get("lift", 0.0) + fy - (seat / k + 14.0)
        return pose

    SHADOW_W = {"dog": 0.75, "cat": 0.55, "cow": 1.5, "crow": 0.3, "parrot": 0.3}

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

    @staticmethod
    def _key(E):
        return (E["action"], round(E["a_t0"], 4), E["dr"], E["st"].get("on"), bool(E["rf"]))

    def _build_pose(self, c, t, E):
        st, x, action, a_t0 = E["st"], E["x"], E["action"], E["a_t0"]
        opts = dict(st["opts"], _x=x, _bpm=self.plan.bpm, _prop=st["prop"], _dir=E["dr"], _facing=st["facing"],
                    _expr=st["expression"], _amp=self._amp(st["talking"], t) if st["talking"] else 0.0)
        pose = actions.pose_for(action, t - a_t0 if action not in ("walk", "run") else t, st["speed"],
                                st["intensity"], c.phase, opts)
        if E["rf"]:                                 # on a vehicle: the seat decides the pose
            pose = dict(E["rf"]["pose"])
        elif st.get("on"):
            pose = self._seated(c, t, st, action, pose, opts)
        elif E["listen"]:
            self._react(c, t, E, pose)
        return pose

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
    _NUM_DEFAULTS = {"dx": 0.0, "head_dx": 0.0, "head_dy": 0.0, "th_k": 1.0, "sh_k": 1.0, "arm_k": 1.0,
                     "la_k1": 1.0, "la_k2": 1.0, "ra_k1": 1.0, "ra_k2": 1.0,
                     "lift": 0.0, "shift": 0.0, "tilt": 0.0, "head_tilt": 0.0, "look_x": 0.0, "look_y": 0.0}

    def _blend_from_previous(self, c, t, E, pose, end=None, depth=0):
        """If the action (or its direction) changed less than BLEND seconds ago, cross-fade from the previous
        action's pose (still moving) to the new one. Back-to-back changes chain: a new blend starts from the
        half-finished blend that was on screen, not from the raw previous pose."""
        B = self.BLEND
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
        Eo = self._eff(c, lo)
        if Eo["rf"]:
            return pose
        Eo["x"], Eo["y"] = E["x"], E["y"]
        old = self._build_pose(c, t, Eo)
        if depth < 2:
            old = self._blend_from_previous(c, t, Eo, old, end=lo, depth=depth + 1)
        w = clamp((t - hi) / B)
        w = w * w * (3 - 2 * w)
        out = dict(pose)
        for kk in set(old) | set(pose):
            if kk.startswith("_"):
                continue
            va = old.get(kk, DEFAULT_POSE.get(kk, self._NUM_DEFAULTS.get(kk)))
            vb = pose.get(kk, DEFAULT_POSE.get(kk, self._NUM_DEFAULTS.get(kk)))
            num = (isinstance(va, (int, float)) and isinstance(vb, (int, float)) and not isinstance(va, bool)
                   and not isinstance(vb, bool))
            if num:
                if kk in self._ANGLES:
                    dlt = ((vb - va + 180.0) % 360.0) - 180.0
                    out[kk] = va + dlt * w
                else:
                    out[kk] = va + (vb - va) * w
            elif w < 0.5:
                out[kk] = va
        # arms: move the elbow and hand along straight lines (angle blending can flip direction near 180 deg)
        sy = skeleton(DEFAULT_POSE)["shR"][1]       # shoulder height of the rig
        for side, shx in (("la", -56.0), ("ra", 56.0)):
            pts = []
            for src in (old, pose):
                a1 = src.get(side + "1", DEFAULT_POSE[side + "1"])
                a2 = src.get(side + "2", DEFAULT_POSE[side + "2"])
                k_ = src.get("arm_k", 1.0)
                l1 = UA * k_ * src.get(side + "_k1", 1.0)
                l2 = LA * k_ * src.get(side + "_k2", 1.0)
                ex, ey = shx + l1 * math.sin(math.radians(a1)), sy + l1 * math.cos(math.radians(a1))
                pts.append((ex, ey, ex + l2 * math.sin(math.radians(a2)), ey + l2 * math.cos(math.radians(a2))))
            (e0x, e0y, h0x, h0y), (e1x, e1y, h1x, h1y) = pts
            ex, ey = e0x + (e1x - e0x) * w, e0y + (e1y - e0y) * w
            hx, hy = h0x + (h1x - h0x) * w, h0y + (h1y - h0y) * w
            ak = out.get("arm_k", 1.0)
            out[side + "1"] = math.degrees(math.atan2(ex - shx, ey - sy))
            out[side + "2"] = math.degrees(math.atan2(hx - ex, hy - ey))
            out[side + "_k1"] = math.hypot(ex - shx, ey - sy) / (UA * ak)
            out[side + "_k2"] = math.hypot(hx - ex, hy - ey) / (LA * ak)
        return out

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

    def story_frame(self, t):
        plan, s = self.plan, self.s
        img = self._background(t)
        self._draw_objects(img, t, False)
        light = self._light_level(t)
        for im_, (px_, py_) in self.sets.wall(t, power=light >= 0.5):     # doors, windows, clocks, fans...
            img.paste(im_, (px_, py_), im_)
        order = sorted((c for c in plan.chars.values() if not c.spec.get("hidden")),
                       key=lambda c: (c.draw_pos(t)[1], c.draw_pos(t)[0]))
        anchors = {}
        states = {}
        def prep_char(c):
            """Everything about this character at time t (pose, drawing ops, anchors); painted by draw_char."""
            E = self._eff(c, t)
            st, x, y, action, a_t0, mv, rf = E["st"], E["x"], E["y"], E["action"], E["a_t0"], E["mv"], E["rf"]
            states[c.name] = st
            pose = self._build_pose(c, t, E)
            if not rf and not c.spec.get("kind"):
                pose = self._blend_from_previous(c, t, E, pose)     # one action flows into the next
            singing = action in actions.SING_ACTIONS and not st["talking"]
            self._smooth_gaze(c, t, E, pose)        # eyes and face glide to a new target; a new face hides in a blink
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
            prop = st["prop"] or ("mic" if singing else None) or pose.get("prop")
            if st["prop"] == "" or pose.get("hide_prop"):
                prop = None
            expr = pose.get("face") or st["expression"]      # some actions bring their own face (yawn, sneeze...)
            speaking = bool(st["talking"]) and st["talking"].get("bubble") != "thought"   # thoughts: lips shut
            if spec.get("kind") in ANIMALS:          # dog, cat, cow, crow, parrot: their own rig
                running = bool(mv and len(mv) > 6 and mv[6])
                dirn = -1 if st["facing"] == "left" else 1
                k_an = c.draw_scale(t) * (0.82 if spec["kind"] in ("dog", "cat", "cow") else 1.0)   # next to these people
                ops, an = build_animal(spec, action, t - a_t0, t, x, y, k_an, dirn, bool(mv), running,
                                       mouth_open if speaking else 0.0, expr)
            else:
                ops, an = build_character(spec, pose, expr, mouth_open, t, x, y, c.draw_scale(t),
                                          blink=blink, prop=prop, talking=speaking or singing or chewing,
                                          tear_phase=(t * 1.1) % 1.0)
            return dict(ops=ops, an=an, rf=rf, pose=pose, x=x, y=y, k=c.draw_scale(t), animal=spec.get("kind"))

        prep = {}
        for c in order:
            if c.state_at(t).get("visible", True):
                prep[c.name] = prep_char(c)

        def draw_char(c):
            P = prep.get(c.name) or prep_char(c)
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
        floor = sorted(self.sets.floor(t) + self._foreground(t), key=lambda f: f[0])   # set pieces and the place's
        # own front props (bed, sofa, tree, street poles...) depth-sorted with the people
        fi = 0
        for c in order:
            while fi < len(floor) and floor[fi][0] <= c.draw_pos(t)[1]:
                img.paste(floor[fi][1], (floor[fi][2], floor[fi][3]), floor[fi][1])
                fi += 1
            if c not in in_front and c.state_at(t).get("visible", True):
                draw_char(c)
        for _d, im_, px_, py_ in floor[fi:]:
            img.paste(im_, (px_, py_), im_)
        self._draw_objects(img, t, True)
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

        # camera first, so the speech bubbles can be kept inside the visible part of the frame
        z, cx, cy, dx, dy = camera_at(plan, t)
        if dx or dy:
            z = max(z, 1.05)
        vw, vh = self.W / max(z, 1.0), self.H / max(z, 1.0)
        vl = clamp((cx + dx) * s - vw / 2, 0, self.W - vw)
        vt = clamp((cy + dy) * s - vh / 2, 0, self.H - vh)
        zb = max(1.0, z * 0.8)          # a bubble never grows more than ~1.25x on screen when the camera zooms
        sb = s / zb
        mar = 22 * s / max(z, 1.0)      # margin to the edge of the visible part (pre-zoom pixels)

        # labels + bubbles
        for c in order:
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
        if z > 1.001:
            img = img.resize((self.W, self.H), Image.BILINEAR, box=(vl, vt, vl + vw, vt + vh))

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


class Sequence(Output):
    """Several scenes back to back + whole-video music and overlays."""

    def __init__(self, scene, width=1080, use_tts=True, fps=None, tts_provider=None):
        meta = scene.get("meta", {})
        fps = int(fps or meta.get("fps", 30))
        subs = split_scenes(scene)
        voices = prepare_voice(subs, use_tts, tts_provider)      # one Gemini request for ALL scenes
        self.parts = [Renderer(sub, width, use_tts, fps, tts_provider, v) for sub, v in zip(subs, voices)]
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
        self.overlays = static_overlays(scene)
        self.overlay_layer = OverlayLayer(self.s)
        self.fade_in, self.fade_out = float(meta.get("fade_in", 0)), float(meta.get("fade_out", 0))

    def _part_at(self, t):
        i = 0
        while i + 1 < len(self.parts) and t >= self.offsets[i + 1]:
            i += 1
        return i

    def frame(self, t):
        i = self._part_at(t)
        part, lt = self.parts[i], t - self.offsets[i]
        img = part.frame(lt)
        D = 0.28
        cut_in = bool(part.plan.cut_in)                                     # a CUT shot: no whip / fade into it
        cut_out = i + 1 < len(self.parts) and bool(self.parts[i + 1].plan.cut_in)
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


def make_video(scene, width=1080, use_tts=True, fps=None, tts_provider=None, dialogue=None, hook=None, style=None):
    scene = gemini_music.prepare(scene, use_tts)        # `MUSIC: gemini ...`: the song (or the beat if Gemini cannot)
    if dialogue or hook:
        scene = apply_options(scene, dialogue, hook)
    if style:                                       # "2d" / "2.5d" from the command line / web page wins
        scene = dict(scene, style=styles.normalize(style))
    if scene.get("scenes"):
        return Sequence(scene, width, use_tts, fps, tts_provider)
    return Renderer(scene, width, use_tts, fps, tts_provider)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render a scene.json to mp4")
    ap.add_argument("scene")
    ap.add_argument("-o", "--out", default=None, help="output .mp4 (or .png with --frame)")
    ap.add_argument("--width", type=int, default=1080, help="output width in px (height is 16:9 portrait)")
    ap.add_argument("--fps", type=int, default=None)
    ap.add_argument("--no-tts", action="store_true", help="skip speech synthesis (estimated timing, silent voice)")
    ap.add_argument("--tts", choices=["auto", "gemini", "edge"], default=None,
                    help="voice engine: gemini = the WHOLE video's script in ONE Gemini request, then split per line "
                         "(needs GEMINI_API_KEY); edge = edge-tts per line; auto (default) = gemini if a key is set")
    ap.add_argument("--frame", type=float, default=None, help="render one PNG frame at this time (seconds)")
    ap.add_argument("--dialogue", choices=DIALOGUE_MODES, default=None,
                    help="spoken words: bubble (default) | subtitle (at the bottom) | both | none (voice only)")
    ap.add_argument("--style", choices=["2d", "2.5d"], default=None,
                    help="look: 2d (default) | 2.5d (kitchen, gully, chai_tapri, kirana, terrace as layered sets)")
    ap.add_argument("--hook", choices=HOOK_MODES, default=None, dest="hook_mode",
                    help="hook card: over (over the first line, default) | first (hook card, then the story) | off")
    args = ap.parse_args(argv)

    scene = load_scene(args.scene)
    name = os.path.splitext(os.path.basename(args.scene))[0]
    r = make_video(scene, args.width, use_tts=not args.no_tts, fps=args.fps, tts_provider=args.tts,
                   dialogue=args.dialogue, hook=args.hook_mode, style=args.style)
    if args.frame is not None:
        out = args.out or os.path.join("out", name + ".png")
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        r.frame(args.frame).save(out)
        print("saved", out)
        return
    out = args.out or os.path.join("out", name + ".mp4")
    r.render_video(out)


if __name__ == "__main__":
    main()

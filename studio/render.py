"""scene.json -> mp4.

    python -m studio.render scenes/my_scene.json -o out/my_scene.mp4
    python -m studio.render scenes/my_scene.json --frame 2.5 -o out/preview.png
"""
import argparse
import json
import math
import os
import subprocess
import sys
import time

import numpy as np
from PIL import Image, ImageChops

from . import actions, audio, ui
from .backgrounds import Background
from .effects import Effects, Patch
from .objects import VEHICLES, Objects
from .animals import ANIMALS, build_animal
from .characters import build_character, render_ops
from .scene import camera_at, compile_scene
from .text import bubble_image, styled_box
from .util import LH, LW, clamp, ease_out, ease_out_back, load_scene

INF = float("inf")

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
            if rate > 0 and s0 <= ts < s0 + rate * ln:
                return r0 + (ts - s0) / rate
        r0, s0, _r, _l, _s = self.pieces[-1]
        return r0 + (ts - s0)


def build_ffmpeg_cmd(W, H, fps, duration, speech, sfx, musics, out):
    """speech: [(path, start)], sfx: [(path, t, volume)], musics: [dict(path, start, dur, volume, loop)].
    Speech ducks the music; everything is mixed and limited."""
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", "%dx%d" % (W, H), "-r", str(fps), "-i", "-"]
    idx = 1
    speech_lbl, fx_lbl, mus_lbl, filters = [], [], [], []
    for path, start in speech:
        cmd += ["-i", path]
        filters.append("[%d:a]aresample=44100,aformat=channel_layouts=mono,adelay=%d:all=1,volume=1.0[s%d]"
                       % (idx, int(start * 1000), idx))
        speech_lbl.append("[s%d]" % idx)
        idx += 1
    for path, t, vol in sfx:
        cmd += ["-i", path]
        filters.append("[%d:a]aresample=44100,aformat=channel_layouts=mono,adelay=%d:all=1,volume=%.2f[f%d]"
                       % (idx, int(t * 1000), vol, idx))
        fx_lbl.append("[f%d]" % idx)
        idx += 1
    for m in musics:
        if m.get("loop"):
            cmd += ["-stream_loop", "-1"]
        cmd += ["-i", m["path"]]
        filters.append("[%d:a]aresample=44100,aformat=channel_layouts=mono,atrim=0:%.2f,adelay=%d:all=1,volume=%.2f[m%d]"
                       % (idx, m["dur"], int(m.get("start", 0) * 1000), m["volume"], idx))
        mus_lbl.append("[m%d]" % idx)
        idx += 1

    def merge(lbls, name):
        if len(lbls) > 1:
            filters.append("%samix=inputs=%d:normalize=0:duration=longest[%s]" % ("".join(lbls), len(lbls), name))
        else:
            filters.append("%sanull[%s]" % (lbls[0], name))
        return "[%s]" % name

    mus = merge(mus_lbl, "mus") if mus_lbl else None
    mix_in = []
    if speech_lbl:
        sp = merge(speech_lbl, "sp")
        if mus:
            filters.append("%sasplit=2[spa][spb]" % sp)
            filters.append("%s[spa]sidechaincompress=threshold=0.03:ratio=8:attack=15:release=300[duck]" % mus)
            mix_in += ["[spb]", "[duck]"]
        else:
            mix_in.append(sp)
    elif mus:
        mix_in.append(mus)
    if fx_lbl:
        mix_in.append(merge(fx_lbl, "fx"))
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
            "-r", str(fps), "-c:a", "aac", "-b:a", "160k", "-ac", "2",
            "-t", "%.3f" % duration, "-movflags", "+faststart", out]
    return cmd


def render_frames(r, out):
    """Pipe r.frame_at(T) for every frame into ffmpeg. r: Renderer or MultiRenderer."""
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    cmd = build_ffmpeg_cmd(r.W, r.H, r.fps, r.duration, *r.audio_items(), out)
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = r.n_frames
    t0 = time.time()
    try:
        for i in range(n):
            img = r.frame_at(i / float(r.fps))
            proc.stdin.write(img.tobytes())
            if i % 30 == 0:
                print("  frame %d/%d  (%.1fs)" % (i, n, time.time() - t0), flush=True)
        proc.stdin.close()
    except BrokenPipeError:
        pass
    rc = proc.wait()
    if rc != 0:
        raise SystemExit("ffmpeg failed (exit %d)" % rc)
    print("done: %s  (%d frames, %.1fs video, %.0fs render)" % (out, n, r.duration, time.time() - t0))


POS = {"top": (540, 330), "center": (540, 960), "lower": (540, 1450), "bottom": (540, 1560),
       "upper": (540, 520)}


class Renderer:
    def __init__(self, scene, width=1080, use_tts=True, fps=None):
        self.scene = scene
        self.plan = compile_scene(scene, use_tts=use_tts, fps=fps)
        self.W = int(width) - int(width) % 2
        self.H = int(round(self.W * LH / LW))
        self.H -= self.H % 2
        self.s = self.W / float(LW)
        self.bg = Background(self.plan.background, self.W, self.H)
        meta = scene.get("meta", {})
        self.shadows = bool(meta.get("shadows", True))         # soft contact shadow under each character
        self.depth = float(meta.get("depth", 0.3))             # 0 = off; how much smaller far-away characters get
        self._shadow = _shadow_sprite() if self.shadows else None
        self._vig = _vignette(self.W, self.H, float(meta.get("vignette", 0.18)))   # 0 = off
        self.fps = self.plan.fps
        self.warp = TimeWarp(self.plan.warps, self.plan.duration)
        self.duration = round(self.warp.duration, 3)
        self.n_frames = int(round(self.duration * self.fps))
        self.fx = Effects(self.plan.effects, self.s, self.W, self.H, self.plan.fps)
        self.objects = Objects(self.plan.objects, self.plan.obj_events, self.s, self.W, self.H)
        self._ov_cache = {}
        self._lip = {}
        self._label_cache = {}

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

    def _paste_rgba(self, img, rgba, cx, cy, scale=1.0, alpha=1.0, anchor=None):
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

    def _draw_shadow(self, img, x, y, k, height, stretch=1.0):
        """Soft ellipse on the ground at logical (x, y). `height` = how far the body is lifted (logical px):
        a jumping character gets a smaller, fainter shadow."""
        h = max(0.0, height)
        shrink = 1.0 / (1.0 + h / 260.0)
        w = max(2, int(2 * 118 * k * shrink * stretch * self.s))
        hh = max(2, int(2 * 20 * k * shrink * self.s))
        sp = self._shadow.resize((w, hh), Image.BILINEAR)
        a = 1.0 / (1.0 + h / 200.0)
        sp.putalpha(sp.getchannel("A").point([int(v * a) for v in range(256)]))
        img.paste(sp, (int(x * self.s - w / 2), int(y * self.s - hh / 2)), sp)

    def _ride_geom(self, riding, c, x, y, t, st):
        """Vehicle seat / handlebar / pedals in the rider's body coordinates (facing right)."""
        vid, seat = riding
        ob = self.objects.objs[vid]
        V = VEHICLES[ob["type"]]
        _vx, _vy, dirn, dist = self.objects.pos(vid, t)
        e = -1 if (bool(ob.get("flip")) != (dirn < 0)) else 1
        sc = float(ob.get("scale", 1.0))
        k = c.scale * self.bg.depth_scale(y, self.depth)
        f = sc / k
        seats = V["seats"]
        sx, hip_h = seats.get(seat) or next(iter(seats.values()))
        g = {"dir": e, "hip_h": hip_h * f, "lean": 3 if not V["enclosed"] else 0}
        if seat == "driver" and V.get("hands"):
            hx, hh = V["hands"]
            g["hands"] = ((hx - sx) * f, -(hh - hip_h) * f)
        fe = V.get("feet")
        if seat == "driver" and fe:
            if fe[0] == "crank":
                _c, cx, ch, r = fe
                wr = V["wheels"][0][1]
                g["crank"] = ((cx - sx) * f, (hip_h - ch) * f, r * f, dist / max(1.0, wr * sc) * 1.6)
            else:
                g["pegs"] = ((fe[0] - sx) * f, (hip_h - fe[1]) * f)
        elif fe and not V["enclosed"]:
            g["pegs"] = ((0 - sx) * f * 0.3, (hip_h - 90) * f)
        return g

    def _light_level(self, t):
        lvl = 1.0
        prev_t, prev = 0.0, 1.0
        for (t0, v) in sorted(self.plan.lights):
            if t < t0:
                break
            prev, lvl, prev_t = lvl, v, t0
        if t - prev_t < 0.18:             # quick fade between levels
            lvl = prev + (lvl - prev) * (t - prev_t) / 0.18
        return lvl

    def _darken(self, img, level, t):
        """Lights off: the room goes dark blue; lamps, TVs and tubelights that are on keep glowing."""
        k = clamp(level)
        tint = (int(255 * k * 0.85), int(255 * k * 0.9), int(255 * min(1.0, k * 1.35)))
        img = ImageChops.multiply(img, Image.new("RGB", img.size, tint))
        for (x, y, typ, sc) in self.objects.lights_on(t):
            if typ == "tubelight" and level < 0.5:
                continue
            cy = {"lamp": y - 650 * sc, "tv": y - 460 * sc, "tubelight": y - 1150 * sc}[typ]
            r = {"lamp": 420, "tv": 380, "tubelight": 600}[typ] * sc
            col = (255, 226, 150) if typ != "tv" else (170, 200, 255)
            p = Patch(x, cy, r, r, self.s, 1)
            for i in range(10):
                rr = r * (1 - i / 10.0)
                p.ellipse(x, cy, rr, rr, col + (int(16 + i * 2),), None)
            small = p.im
            base = img.convert("RGBA")
            base.alpha_composite(small, (int(round(p.ox * self.s)), int(round(p.oy * self.s))))
            img = base.convert("RGB")
        return img

    # ------------------------------------------------------------ overlays
    def _overlay_image(self, o):
        key = json.dumps([o.get("text"), o.get("style"), o.get("color"), o.get("size"), o.get("max_w")], default=str)
        if key not in self._ov_cache:
            self._ov_cache[key] = styled_box(str(o.get("text", "")), o.get("style", "caption_box"), self.s,
                                             o.get("color"), o.get("size"), o.get("max_w"))
        return self._ov_cache[key]

    UI_DUR = {"notification": 3.0, "loading": 3.0, "counter": 3.0, "timecard": 1.6, "chapter": 2.2}
    UI_POS = {"chat": (540, 980), "notification": (540, 150), "loading": (540, 900), "counter": (540, 720),
              "chapter": (540, 330)}

    def _draw_ui(self, img, o, t, t0, t1):
        typ = o["type"]
        lt = t - t0
        dur = (t1 - t0) if t1 < 1e8 else 3.0
        im = ui.render(o, lt, self.s, dur, (self.W, self.H))
        if im is None:
            return img
        fade = clamp(lt / 0.2) * (clamp((t1 - t) / 0.25) if t1 < 1e8 else 1.0)
        if fade < 0.999:
            im.putalpha(im.getchannel("A").point([int(v * fade) for v in range(256)]))
        if typ in ("timecard", "endcard"):
            base = img.convert("RGBA")
            base.alpha_composite(im)
            return base.convert("RGB")
        pos = o.get("pos", self.UI_POS.get(typ, (540, 900)))
        px, py = POS[pos] if isinstance(pos, str) else pos
        if typ == "notification":           # slides down from the top, and back up at the end
            py = py - 260 * (1 - ease_out(lt / 0.3)) - (260 * (1 - clamp((t1 - t) / 0.3)) if t1 < 1e8 else 0)
        elif typ == "chat":
            py += 120 * (1 - ease_out(lt / 0.3))
        self._paste_rgba(img, im, px * self.s, py * self.s)
        return img

    def _draw_overlays(self, img, t):
        for o in self.plan.overlays:
            t0 = float(o.get("from", 0.0))
            t1 = o.get("to")
            dflt = self.UI_DUR.get(o.get("type"))
            t1 = float(t1) if t1 is not None else (t0 + float(o["dur"]) if "dur" in o else
                                                   (t0 + dflt if dflt else 1e9))
            if not (t0 <= t < t1):
                continue
            if o.get("type") in ui.TYPES:
                img = self._draw_ui(img, o, t, t0, t1)
                continue
            im = self._overlay_image(o)
            pos = o.get("pos", "top")
            px, py = POS[pos] if isinstance(pos, str) else pos
            default_anim = "fade" if o.get("style") in ("lyric", "subtitle") else "pop"
            anim = o.get("anim", default_anim)
            lt = t - t0
            sc, al = 1.0, 1.0
            if anim == "pop":
                sc = 0.35 + 0.65 * ease_out_back(lt / 0.32)
                al = clamp(lt / 0.12)
            elif anim == "fade":
                al = clamp(lt / 0.3)
            elif anim == "slide":
                py += (1 - ease_out(lt / 0.35)) * 120
                al = clamp(lt / 0.2)
            if t1 < 1e8:
                al *= clamp((t1 - t) / 0.2)
            self._paste_rgba(img, im, px * self.s, py * self.s, sc, al)
        return img

    # ------------------------------------------------------------ one frame
    def frame(self, t):
        plan, s = self.plan, self.s
        img = self.bg.frame(t).convert("RGB")
        light = self._light_level(t)
        for im, (px, py) in self.objects.wall(t, power=light >= 0.5):     # doors, windows, clocks, fans...
            img.paste(im, (px, py), im)
        order = sorted(plan.chars.values(), key=lambda c: (c.pos_at(t)[1], c.pos_at(t)[0]))
        anchors = {}
        states = {}

        # pass 1: state, pose and depth-scaled size of every character
        prep = {}
        for c in order:
            st = c.state_at(t)
            states[c.name] = st
            x, y = c.pos_at(t)
            action, a_t0 = st["action"], st["action_t0"]
            riding = c.ride_at(t) if c.rides else None
            if riding:
                riding = self._ride_geom(riding, c, x, y, t, st)
                action = "ride"
            mv = None if riding else next((m for m in c.moves if m[0] <= t < m[1]), None)
            if mv and action in ("idle", "none", "stand", "talk"):
                action, a_t0 = ("run" if mv[6] else "walk"), 0.0
            if mv and st["facing"] == "front" and abs(mv[4] - mv[2]) > 1:
                st["facing"] = "right" if mv[4] > mv[2] else "left"      # face the way you walk
            # which way the character acts: toward its `look` target, else its facing, else toward screen centre
            look = st["look"]
            if "dir" in st["opts"] and st["opts"]["dir"] in (1, -1, "left", "right"):
                dr = st["opts"]["dir"]
                dr = -1 if dr in (-1, "left") else 1
            elif isinstance(look, str) and look in plan.chars and look != c.name:
                dr = 1 if plan.chars[look].pos_at(t)[0] >= x else -1
            elif st["facing"] in ("left", "right"):
                dr = -1 if st["facing"] == "left" else 1
            else:
                dr = 1 if x <= LW / 2 else -1
            if riding:
                dr = riding["dir"]
                st["facing"] = "right" if dr > 0 else "left"
            opts = dict(st["opts"], _x=x, _dir=dr, _facing=st["facing"], _ride=riding)
            if c.spec.get("kind") in ANIMALS:
                pose = {}
            else:
                pose = actions.pose_for(action, t - a_t0 if action not in ("walk", "run") else t, st["speed"],
                                        st["intensity"], c.phase, opts)
            pose["_anim"] = (action, t - a_t0, bool(mv), bool(mv and mv[6]), dr)
            k = c.scale * self.bg.depth_scale(y, self.depth)
            seat = self.objects.seat_height(st.get("on")) if st.get("on") else None
            if seat is not None and action not in ("sit", "lie_down", "lie", "sleep_lie", "rofl") and \
                    c.spec.get("kind") not in ANIMALS:
                # an upper-body action while seated (drink, talk, phone...): keep the sitting legs
                legs = actions.pose_for("sit", 0.0, 1.0, 1.0, c.phase, opts)
                for kk in ("ll1", "ll2", "rl1", "rl2", "th_k"):
                    if kk in legs:
                        pose[kk] = legs[kk]
                for kk in ("tilt", "lift", "shift", "dx"):
                    pose.pop(kk, None)
                action = "sit"
            if seat is not None:
                if action in ("sit",):          # line the hips up with the seat top
                    natural = 208.0 if st["facing"] == "front" else 166.0
                    pose["lift"] = pose.get("lift", 0.0) + natural - seat / k
                elif action in ("lie_down", "lie", "sleep_lie", "rofl"):
                    pose["lift"] = pose.get("lift", 0.0) - seat / k
            prep[c.name] = (st, x, y, pose, k)

        # pass 2: contact shadows go under *all* characters so they never cover a neighbour
        if self.shadows:
            for c in order:
                _st, x, y, pose, k = prep[c.name]
                if not _st.get("visible", True):
                    continue
                lean = math.sin(math.radians(pose.get("tilt", 0.0)))
                if abs(lean) > 0.5:      # lying / falling: the shadow follows the body along the floor
                    self._draw_shadow(img, x + (pose.get("dx", 0.0) + lean * 380) * k, y + 6 * k, k, 0.0,
                                      stretch=1.0 + 2.2 * abs(lean))
                else:
                    self._draw_shadow(img, x + (pose.get("shift", 0.0) + pose.get("dx", 0.0)) * k, y + 6 * k, k,
                                      -pose.get("lift", 0.0) * k)

        # pass 3: characters, with foreground props woven in by depth (a prop covers characters standing behind it)
        fg = sorted(self.bg.foreground(t) + self.objects.floor(t), key=lambda f: f[0])
        fi = 0
        for c in order:
            st, x, y, pose, k = prep[c.name]
            while fi < len(fg) and fg[fi][0] <= y:
                img.paste(fg[fi][1], (fg[fi][2], fg[fi][3]), fg[fi][1])
                fi += 1
            if not st.get("visible", True):
                continue
            look = st["look"]
            if isinstance(look, str) and look in plan.chars:
                ox, _oy = plan.chars[look].pos_at(t)
                pose["look_x"] = clamp((ox - x) / 350.0, -1, 1)
            elif look == "left":
                pose["look_x"] = -1
            elif look == "right":
                pose["look_x"] = 1
            elif isinstance(look, (int, float)):
                pose["look_x"] = float(look)
            mouth_open = 0.0
            talking = bool(st["talking"]) and st["talking"].get("bubble") != "thought"   # thoughts: lips shut
            if talking:
                mouth_open = self._lip_open(st["talking"], t)
            elif pose.get("chew") is not None:          # eating: chewing mouth
                mouth_open, talking = float(pose["chew"]), pose["chew"] > 0.1
            blink = ((t + c.phase * 1.7) % 3.6) < 0.12
            spec = dict(c.spec)
            spec["facing"] = st["facing"]
            if pose.get("prop_hand"):
                spec["prop_hand"] = pose["prop_hand"]
            expr = pose.get("face") or st["expression"]   # some actions carry their own face (yawn, sneeze...)
            prop = st["prop"] if st["prop"] is not None else pose.get("prop")
            if st["prop"] == "" or pose.get("hide_prop"):
                prop = None
            if spec.get("kind") in ANIMALS:
                a_act, a_at, a_mv, a_run, a_dir = pose["_anim"]
                ops, an = build_animal(spec, a_act, a_at, t, x, y, k, a_dir, a_mv, a_run,
                                       mouth_open if talking else 0.0, expr)
            else:
                ops, an = build_character(spec, pose, expr, mouth_open, t, x, y, k,
                                          blink=blink, prop=prop, talking=talking,
                                          tear_phase=(t * 1.1) % 1.0)
            r = render_ops(ops, s, self.W, self.H)
            if r:
                layer, (ox, oy) = r
                img.paste(layer, (ox, oy), layer)
            anchors[c.name] = an
        for _d, part, fx, fy in fg[fi:]:      # props in front of everybody
            img.paste(part, (fx, fy), part)

        self.fx.draw_world(img, t, anchors, plan.chars)     # sweat, ?, POW, glowing eyes, thrown objects...
        if light < 0.995:
            img = self._darken(img, light, t)
        # rain, fog, lightning, spotlight...: over the whole scene but under bubbles and captions
        img = self.fx.draw_screen(img, t, {n: (a["head_center"][0] * s, a["head_center"][1] * s)
                                           for n, a in anchors.items()})

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
                self._paste_rgba(img, lab, hx * s, hy * s - lab.height / 2 - 18 * s)
                top = hy - (lab.height / s) - 30
            sp = st["talking"]
            if sp and sp.get("bubble") == "thought":
                self.fx._thought(img, {"text": sp["text"], "_seed": 0}, t - sp["start"], 1.0, an)
            elif sp and sp.get("bubble", True):
                lt = t - sp["start"]
                im0, _ = bubble_image(sp["text"], s, 0)
                left = clamp(hx * s - im0.width * 0.35, 24 * s, self.W - im0.width - 24 * s)
                im, (tipx, tipy) = bubble_image(sp["text"], s, int(hx * s - left))
                tx, ty = left + tipx, top * s - 12 * s
                sc = 0.55 + 0.45 * ease_out_back(lt / 0.22)
                self._paste_rgba(img, im, tx, ty, sc, 1.0, anchor=(tipx, tipy))

        # camera
        z, cx, cy, dx, dy = camera_at(plan, t)
        if dx or dy:
            z = max(z, 1.05)
        l, tp, vw, vh = 0.0, 0.0, float(self.W), float(self.H)
        if z > 1.001:
            vw, vh = self.W / z, self.H / z
            ccx, ccy = (cx + dx) * s, (cy + dy) * s
            l = clamp(ccx - vw / 2, 0, self.W - vw)
            tp = clamp(ccy - vh / 2, 0, self.H - vh)
            img = img.resize((self.W, self.H), Image.BILINEAR, box=(l, tp, l + vw, tp + vh))


        if self._vig is not None:      # lens vignette: screen-fixed, under the captions
            img = ImageChops.multiply(img, self._vig)

        img = self._draw_overlays(img, t)    # captions stay screen-fixed (not zoomed)

        # fades
        f = 1.0
        if plan.fade_in and t < plan.fade_in:
            f = min(f, t / plan.fade_in)
        if plan.fade_out and t > plan.duration - plan.fade_out:
            f = min(f, (plan.duration - t) / plan.fade_out)
        if f < 0.999:
            img = Image.blend(Image.new("RGB", img.size, (0, 0, 0)), img, clamp(f))
        return img

    # ------------------------------------------------------------ real time (slow motion / freeze aware)
    def frame_at(self, T):
        ts, style = self.warp.at(T)
        img = self.frame(min(ts, self.plan.duration - 1e-3))
        if style == "grey":
            img = Image.blend(img, img.convert("L").convert("RGB"), 0.85)
        return img

    def audio_items(self, offset=0.0, with_music=True):
        """Speech / sfx / music placed in REAL time (+ offset)."""
        w = self.warp
        speech = [(sp["audio"], offset + w.real(sp["start"])) for sp in self.plan.speech if sp.get("audio")]
        sfx = [(fx["path"], offset + w.real(fx["t"]), fx["volume"]) for fx in self.plan.sfx]
        musics = []
        if with_music and self.plan.music:
            m = self.plan.music
            musics.append(dict(path=m["path"], start=offset, dur=self.duration, volume=m["volume"],
                               loop=not m["generated"]))
        for a in getattr(self.plan, "ambience", []):
            musics.append(dict(path=a["path"], start=offset, dur=self.duration, volume=a["volume"], loop=True))
        return speech, sfx, musics

    def ffmpeg_cmd(self, out):
        return build_ffmpeg_cmd(self.W, self.H, self.fps, self.duration, *self.audio_items(), out)

    def render_video(self, out):
        render_frames(self, out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render a stickman scene.json to mp4")
    ap.add_argument("scene")
    ap.add_argument("-o", "--out", default=None, help="output .mp4 (or .png with --frame)")
    ap.add_argument("--width", type=int, default=1080, help="output width in px (height is 16:9 portrait)")
    ap.add_argument("--fps", type=int, default=None)
    ap.add_argument("--no-tts", action="store_true", help="skip speech synthesis (estimated timing, silent voice)")
    ap.add_argument("--frame", type=float, default=None, help="render one PNG frame at this time (seconds)")
    args = ap.parse_args(argv)

    scene = load_scene(args.scene)
    name = os.path.splitext(os.path.basename(args.scene))[0]
    from .lint import lint
    for wmsg in lint(scene):                    # typos would otherwise fall back silently
        print("  [warn] " + wmsg, file=sys.stderr)
    if "scenes" in scene:                       # multi-scene video (cuts, transitions, split-screen)
        from .multi import MultiRenderer
        r = MultiRenderer(scene, args.width, use_tts=not args.no_tts, fps=args.fps)
    else:
        r = Renderer(scene, args.width, use_tts=not args.no_tts, fps=args.fps)
    if args.frame is not None:
        out = args.out or os.path.join("out", name + ".png")
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        r.frame_at(args.frame).save(out)
        print("saved", out)
        return
    out = args.out or os.path.join("out", name + ".mp4")
    r.render_video(out)


if __name__ == "__main__":
    main()

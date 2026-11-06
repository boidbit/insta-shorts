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

from . import actions, audio
from .backgrounds import Background
from .characters import build_character, render_ops
from .scene import camera_at, compile_scene
from .text import bubble_image, styled_box
from .util import LH, LW, clamp, ease_out, ease_out_back, load_scene

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

    def _draw_shadow(self, img, x, y, k, height):
        """Soft ellipse on the ground at logical (x, y). `height` = how far the body is lifted (logical px):
        a jumping character gets a smaller, fainter shadow."""
        h = max(0.0, height)
        shrink = 1.0 / (1.0 + h / 260.0)
        w = max(2, int(2 * 118 * k * shrink * self.s))
        hh = max(2, int(2 * 20 * k * shrink * self.s))
        sp = self._shadow.resize((w, hh), Image.BILINEAR)
        a = 1.0 / (1.0 + h / 200.0)
        sp.putalpha(sp.getchannel("A").point([int(v * a) for v in range(256)]))
        img.paste(sp, (int(x * self.s - w / 2), int(y * self.s - hh / 2)), sp)

    # ------------------------------------------------------------ overlays
    def _overlay_image(self, o):
        key = json.dumps([o.get("text"), o.get("style"), o.get("color"), o.get("size"), o.get("max_w")], default=str)
        if key not in self._ov_cache:
            self._ov_cache[key] = styled_box(str(o.get("text", "")), o.get("style", "caption_box"), self.s,
                                             o.get("color"), o.get("size"), o.get("max_w"))
        return self._ov_cache[key]

    def _draw_overlays(self, img, t):
        for o in self.plan.overlays:
            t0 = float(o.get("from", 0.0))
            t1 = o.get("to")
            t1 = float(t1) if t1 is not None else (t0 + float(o["dur"]) if "dur" in o else 1e9)
            if not (t0 <= t < t1):
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

    # ------------------------------------------------------------ one frame
    def frame(self, t):
        plan, s = self.plan, self.s
        img = self.bg.frame(t).convert("RGB")
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
            moving = any(t0 <= t < t1 for (t0, t1, *_r) in c.moves)
            if moving and action in ("idle", "none", "stand"):
                action, a_t0 = "walk", 0.0
            opts = dict(st["opts"], _x=x)
            pose = actions.pose_for(action, t - a_t0 if action != "walk" else t, st["speed"], st["intensity"],
                                    c.phase, opts)
            k = c.scale * self.bg.depth_scale(y, self.depth)
            prep[c.name] = (st, x, y, pose, k)

        # pass 2: contact shadows go under *all* characters so they never cover a neighbour
        if self.shadows:
            for c in order:
                _st, x, y, pose, k = prep[c.name]
                self._draw_shadow(img, x + pose.get("shift", 0.0) * k, y + 6 * k, k, -pose.get("lift", 0.0) * k)

        # pass 3: characters, with foreground props woven in by depth (a prop covers characters standing behind it)
        fg, fi = self.bg.foreground(t), 0
        for c in order:
            st, x, y, pose, k = prep[c.name]
            while fi < len(fg) and fg[fi][0] <= y:
                img.paste(fg[fi][1], (fg[fi][2], fg[fi][3]), fg[fi][1])
                fi += 1
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
            if st["talking"]:
                mouth_open = self._lip_open(st["talking"], t)
            blink = ((t + c.phase * 1.7) % 3.6) < 0.12
            spec = dict(c.spec)
            spec["facing"] = st["facing"]
            ops, an = build_character(spec, pose, st["expression"], mouth_open, t, x, y, k,
                                      blink=blink, prop=st["prop"], talking=bool(st["talking"]),
                                      tear_phase=(t * 1.1) % 1.0)
            r = render_ops(ops, s, self.W, self.H)
            if r:
                layer, (ox, oy) = r
                img.paste(layer, (ox, oy), layer)
            anchors[c.name] = an
        for _d, part, fx, fy in fg[fi:]:      # props in front of everybody
            img.paste(part, (fx, fy), part)

        # labels + bubbles
        for c in order:
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
            if sp and sp.get("bubble", True):
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
        if z > 1.001:
            vw, vh = self.W / z, self.H / z
            ccx, ccy = (cx + dx) * s, (cy + dy) * s
            l = clamp(ccx - vw / 2, 0, self.W - vw)
            tp = clamp(ccy - vh / 2, 0, self.H - vh)
            img = img.resize((self.W, self.H), Image.BILINEAR, box=(l, tp, l + vw, tp + vh))

        if self._vig is not None:      # lens vignette: screen-fixed, under the captions
            img = ImageChops.multiply(img, self._vig)

        self._draw_overlays(img, t)    # captions stay screen-fixed (not zoomed)

        # fades
        f = 1.0
        if plan.fade_in and t < plan.fade_in:
            f = min(f, t / plan.fade_in)
        if plan.fade_out and t > plan.duration - plan.fade_out:
            f = min(f, (plan.duration - t) / plan.fade_out)
        if f < 0.999:
            img = Image.blend(Image.new("RGB", img.size, (0, 0, 0)), img, clamp(f))
        return img

    # ------------------------------------------------------------ audio graph
    def ffmpeg_cmd(self, out):
        plan = self.plan
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
               "-s", "%dx%d" % (self.W, self.H), "-r", str(plan.fps), "-i", "-"]
        idx = 1
        speech_lbl, fx_lbl, filters = [], [], []
        for sp in plan.speech:
            if sp.get("audio"):
                cmd += ["-i", sp["audio"]]
                ms = int(sp["start"] * 1000)
                filters.append("[%d:a]aresample=44100,aformat=channel_layouts=mono,adelay=%d:all=1,volume=1.0[s%d]"
                               % (idx, ms, idx))
                speech_lbl.append("[s%d]" % idx)
                idx += 1
        for fx in plan.sfx:
            cmd += ["-i", fx["path"]]
            ms = int(fx["t"] * 1000)
            filters.append("[%d:a]aresample=44100,aformat=channel_layouts=mono,adelay=%d:all=1,volume=%.2f[f%d]"
                           % (idx, ms, fx["volume"], idx))
            fx_lbl.append("[f%d]" % idx)
            idx += 1
        mus = None
        if plan.music:
            if not plan.music["generated"]:
                cmd += ["-stream_loop", "-1"]
            cmd += ["-i", plan.music["path"]]
            filters.append("[%d:a]aresample=44100,aformat=channel_layouts=mono,atrim=0:%.2f,volume=%.2f[mus]"
                          % (idx, plan.duration, plan.music["volume"]))
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
                "-r", str(plan.fps), "-c:a", "aac", "-b:a", "160k", "-ac", "2",
                "-t", "%.3f" % plan.duration, "-movflags", "+faststart", out]
        return cmd

    def render_video(self, out):
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        cmd = self.ffmpeg_cmd(out)
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        n = self.plan.n_frames
        t0 = time.time()
        try:
            for i in range(n):
                img = self.frame(i / float(self.plan.fps))
                proc.stdin.write(img.tobytes())
                if i % 30 == 0:
                    el = time.time() - t0
                    print("  frame %d/%d  (%.1fs)" % (i, n, el), flush=True)
            proc.stdin.close()
        except BrokenPipeError:
            pass
        rc = proc.wait()
        if rc != 0:
            raise SystemExit("ffmpeg failed (exit %d)" % rc)
        print("done: %s  (%d frames, %.1fs video, %.0fs render)" % (out, n, self.plan.duration, time.time() - t0))


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
    r = Renderer(scene, args.width, use_tts=not args.no_tts, fps=args.fps)
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

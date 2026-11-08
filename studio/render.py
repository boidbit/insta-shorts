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
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from . import actions, audio, fx
from .backgrounds import Background
from .characters import build_character, render_ops
from .scene import GROUND_Y, camera_at, compile_scene
from .text import bubble_image, styled_box
from .util import LH, LW, clamp, ease_out, ease_out_back, load_scene

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
        self.bg = Background(self.plan.background, self.W, self.H, zmax=self.plan.zmax)
        self._ov_cache = {}
        self._lip = {}
        self._label_cache = {}
        # lighting: background preset defaults < scene "light"
        self.light = dict(self.bg.light)
        self.light.update(self.plan.light)
        self.horizon = self.light.get("horizon", self.bg.horizon) if self.plan.perspective else None
        self._shadow = self._make_shadow()
        self._glow = self._make_glow()
        self._vig = self._make_vignette(float(self.light.get("vignette", 0.0)))
        self._objs = {o["id"]: o for o in self.plan.objects}
        self._sprite_cache, self._sprite_key = {}, {}

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

    def _make_shadow(self):
        s = self.s
        w, h = int(340 * s) + 8, int(80 * s) + 8
        im = Image.new("L", (w * 2, h * 2), 0)
        ImageDraw.Draw(im).ellipse([w * 0.5, h * 0.62, w * 1.5, h * 1.38], fill=200)
        im = im.filter(ImageFilter.GaussianBlur(14 * s))
        sh = Image.new("RGBA", im.size, (10, 6, 20, 0))
        sh.putalpha(im)
        return sh

    def _make_glow(self):
        """Warm light sprite (RGB on black) for screen-blending around sparks / blasts."""
        n = max(16, int(320 * self.s))
        yy, xx = np.mgrid[0:n, 0:n]
        r = np.sqrt((xx - n / 2.0) ** 2 + (yy - n / 2.0) ** 2) / (n / 2.0)
        a = np.clip(1 - r, 0, 1) ** 2.2
        rgb = np.stack([a * 255, a * 196, a * 110], -1).astype(np.uint8)
        return Image.fromarray(rgb, "RGB")

    def _make_vignette(self, strength):
        if strength <= 0:
            return None
        h, w = self.H // 4, self.W // 4
        yy, xx = np.mgrid[0:h, 0:w]
        r = np.sqrt(((xx - w / 2.0) / (w / 2.0)) ** 2 * 0.9 + ((yy - h / 2.0) / (h / 2.0)) ** 2 * 0.75)
        a = np.clip((r - 0.45) / 0.75, 0, 1) ** 1.6 * strength * 255
        return Image.fromarray(a.astype(np.uint8), "L").resize((self.W, self.H), Image.BILINEAR)

    def _screen_light(self, img, cx, cy, size, power=1.0):
        """Additive-ish warm light at output pixel (cx, cy) with diameter `size` px."""
        d = int(size)
        if d < 4 or power <= 0.01:
            return
        g = self._glow.resize((d, d), Image.BILINEAR)
        if power < 1.0:
            g = Image.eval(g, lambda v: int(v * power))
        x0, y0 = int(cx - d / 2), int(cy - d / 2)
        bx0, by0 = max(0, x0), max(0, y0)
        bx1, by1 = min(self.W, x0 + d), min(self.H, y0 + d)
        if bx1 <= bx0 or by1 <= by0:
            return
        reg = img.crop((bx0, by0, bx1, by1))
        gg = g.crop((bx0 - x0, by0 - y0, bx1 - x0, by1 - y0))
        img.paste(ImageChops.screen(reg, gg), (bx0, by0))

    def _persp(self, y):
        """Things farther up the floor (closer to the horizon) are smaller."""
        hz = self.horizon
        if hz is None:
            return 1.0
        return max(0.25, (y - hz) / float(GROUND_Y - hz))

    def view_at(self, t):
        """Camera as (zoom, left, top) in logical units."""
        z, cx, cy, dx, dy = camera_at(self.plan, t)
        if dx or dy:
            z = max(z, 1.05)
        z = max(1.0, z)
        vw, vh = LW / z, LH / z
        L = clamp(cx + dx - vw / 2, 0, LW - vw)
        T = clamp(cy + dy - vh / 2, 0, LH - vh)
        return (z, L, T)

    @staticmethod
    def _xf(p, view):
        z, L, T = view
        return ((p[0] - L) * z, (p[1] - T) * z)

    @staticmethod
    def _xf_ops(ops, view):
        z, L, T = view
        if z == 1.0 and L == 0 and T == 0:
            return ops
        out = []
        for op in ops:
            o = dict(op)
            o["pts"] = [((x - L) * z, (y - T) * z) for x, y in op["pts"]]
            o["w"] = op["w"] * z
            out.append(o)
        return out

    def _draw_ops(self, img, ops, view, tint=True, alpha=1.0, blur=0):
        r = render_ops(self._xf_ops(ops, view), self.s, self.W, self.H)
        if not r:
            return
        layer, (ox, oy) = r
        if blur:
            pad = int(blur * 3 * self.s * view[0]) + 2
            big = Image.new("RGBA", (layer.width + 2 * pad, layer.height + 2 * pad), (0, 0, 0, 0))
            big.paste(layer, (pad, pad))
            layer = big.filter(ImageFilter.GaussianBlur(blur * self.s * view[0]))
            ox, oy = ox - pad, oy - pad
        amb = self.light.get("ambient")
        if tint and amb:
            rgb = ImageChops.multiply(layer.convert("RGB"), Image.new("RGB", layer.size, tuple(amb)))
            rgb.putalpha(layer.getchannel("A"))
            layer = rgb
        if alpha < 0.999:
            layer.putalpha(layer.getchannel("A").point(lambda v: int(v * alpha)))
        img.paste(layer, (ox, oy), layer)

    def _draw_sprite(self, img, sp, view):
        z, L, T = view
        sc = z * self.s / sp.k
        key = (id(sp), round(sc, 4))
        if self._sprite_key.get(id(sp)) != key:
            w, h = max(1, int(round(sp.im.width * sc))), max(1, int(round(sp.im.height * sc)))
            self._sprite_cache[id(sp)] = sp.im.resize((w, h), Image.BILINEAR) if sc != 1.0 else sp.im
            self._sprite_key[id(sp)] = key
        im = self._sprite_cache[id(sp)]
        img.paste(im, (int(round((sp.x0 - L) * z * self.s)), int(round((sp.y0 - T) * z * self.s))), im)

    def _draw_shadow(self, img, x, ground_y, lift, k, view):
        z = view[0]
        sx, sy = self._xf((x, ground_y), view)
        shrink = 1.0 / (1.0 + max(0.0, lift) / 260.0)
        self._paste_rgba(img, self._shadow, sx * self.s, sy * self.s, k * z * shrink * 0.5, 0.85 * shrink)

    def _anchor(self, ref, anchors):
        if isinstance(ref, (list, tuple)):
            return (float(ref[0]), float(ref[1]))
        if isinstance(ref, str):
            if "." in ref:
                who, key = ref.split(".", 1)
                return (anchors.get(who) or {}).get(key)
            a = anchors.get(ref) or {}
            return a.get("fuse") or a.get("prop_tip") or a.get("head_center")
        return None

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
        view = self.view_at(t)
        z = view[0]
        img = self.bg.frame_cam(t, view)
        ldir = float(self.light.get("dir", -1))

        # ---- build everything that stands on the floor (characters + objects) ----
        items = []
        anchors = {}
        states = {}
        for c in plan.chars.values():
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
            look = st["look"]
            if isinstance(look, str) and look in plan.chars:
                ox, _oy = plan.chars[look].pos_at(t)
                pose["look_x"] = clamp((ox - x) / 350.0, -1, 1)
            elif isinstance(look, str) and look in self._objs:
                pose["look_x"] = clamp((float(self._objs[look]["x"]) - x) / 350.0, -1, 1)
                pose["look_y"] = 0.6
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
            spec["_light"] = ldir
            k = c.scale * self._persp(y)
            ops, an = build_character(spec, pose, st["expression"], mouth_open, t, x, y, k,
                                      blink=blink, prop=st["prop"], talking=bool(st["talking"]),
                                      tear_phase=(t * 1.1) % 1.0)
            anchors[c.name] = an
            lift = y - an["feet"][1]
            items.append((y, x, ops, lift, k))
        for o in plan.objects:
            k = float(o.get("scale", 1.0)) * self._persp(float(o["y"]))
            ops, an = fx.build_object(o, t, k)
            anchors[o["id"]] = an          # anchors stay valid after the object is hidden (e.g. a blast)
            if fx.visible(o, t):
                items.append((float(o["y"]), float(o["x"]), ops, 0.0, k * 0.45))
        for sp in self.bg.sprites:          # set pieces that people can stand behind / in front of
            items.append((sp.ground_y, sp.x0, sp, None, None))
        items.sort(key=lambda it: (it[0], it[1]))

        for (y, x, ops, lift, k) in items:
            if lift is not None:
                self._draw_shadow(img, x, y, lift, k, view)
        for (y, x, ops, lift, k) in items:
            if lift is None:
                self._draw_sprite(img, ops, view)
            else:
                self._draw_ops(img, ops, view)

        # ---- effects (sparks, blasts, smoke) ----
        flash = 0.0
        for f in plan.fx:
            age = t - f["t"]
            if age < 0 or age >= f["dur"]:
                continue
            at = self._anchor(f.get("at"), anchors)
            typ = f.get("type", "sparks")
            if typ == "flash":
                flash = max(flash, 1.0 - age / max(0.05, f.get("dur", 0.3)))
                continue
            if at is None:
                continue
            if typ == "sparks":
                pw = float(f.get("power", 1.0))
                self._draw_ops(img, fx.sparks_ops(at[0], at[1], t, pw), view, tint=False)
                sx, sy = self._xf(at, view)
                flick = 0.75 + 0.25 * math.sin(t * 37) * math.sin(t * 23)
                self._screen_light(img, sx * s, sy * s, 420 * s * z * pw, 0.85 * flick)
            elif typ == "boom":
                for ops, al, bl in fx.boom_groups(at[0], at[1], age, float(f.get("scale", 1.0))):
                    self._draw_ops(img, ops, view, tint=False, alpha=al, blur=bl)
                sx, sy = self._xf(at, view)
                if age < 0.6:
                    self._screen_light(img, sx * s, sy * s, 1400 * s * z, 1.0 - age / 0.6)
                if age < 0.18:
                    flash = max(flash, 0.85 * (1 - age / 0.18))

        # ---- foreground layers (in front of everyone) ----
        self.bg.front(img, t, view)

        # ---- labels + bubbles (screen-sized, follow the camera) ----
        for c in sorted(plan.chars.values(), key=lambda c_: c_.pos_at(t)[1]):
            st, an = states[c.name], anchors[c.name]
            hx, hy = self._xf(an["head_top"], view)
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
                ty = max(ty, tipy + 470 * s)        # keep clear of the top caption
                sc = 0.55 + 0.45 * ease_out_back(lt / 0.22)
                self._paste_rgba(img, im, tx, ty, sc, 1.0, anchor=(tipx, tipy))

        if self._vig is not None:
            img.paste((0, 0, 0), (0, 0, self.W, self.H), self._vig)
        if flash > 0.01:
            img = Image.blend(img, Image.new("RGB", img.size, (255, 246, 226)), clamp(flash))

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
        for sx in plan.sfx:
            cmd += ["-i", sx["path"]]
            ms = int(sx["t"] * 1000)
            filters.append("[%d:a]aresample=44100,aformat=channel_layouts=mono,adelay=%d:all=1,volume=%.2f[f%d]"
                           % (idx, ms, sx["volume"], idx))
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

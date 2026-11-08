"""scene.json -> mp4 (both styles).

    python -m studio.render scenes/2d/tag_karo_demo.json -o out/tag_karo.mp4
    python -m studio.render scenes/25d/gali_25d_demo.json --frame 2.5 -o out/preview.png
    python -m studio.render scenes/x.json --print-style          # prints 2d or 2.5d

The scene's "style" ("2d" = classic stickman, default; "2.5d" = layered parallax look) picks the
renderer: studio.style2d.renderer.Renderer2D or studio.style25d.renderer.Renderer25D. This module only
holds what both share (speech/lip-sync, captions, the ffmpeg audio graph, the CLI).
"""
import argparse
import json
import math
import os
import subprocess
import time

from PIL import Image

from . import audio, styles
from .scene import compile_scene
from .text import styled_box
from .util import LH, LW, clamp, ease_out, ease_out_back, load_scene

POS = {"top": (540, 330), "center": (540, 960), "lower": (540, 1450), "bottom": (540, 1560),
       "upper": (540, 520)}


class BaseRenderer:
    """Shared by both styles. Subclasses implement frame(t)."""

    def __init__(self, scene, width=1080, use_tts=True, fps=None):
        self.scene = scene
        self.plan = compile_scene(scene, use_tts=use_tts, fps=fps)
        self.W = int(width) - int(width) % 2
        self.H = int(round(self.W * LH / LW))
        self.H -= self.H % 2
        self.s = self.W / float(LW)
        self._ov_cache = {}
        self._lip = {}
        self._label_cache = {}

    def frame(self, t):
        raise NotImplementedError

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


def Renderer(scene, width=1080, use_tts=True, fps=None):
    """Make the right renderer for the scene's style (keeps the old `Renderer(scene, ...)` call working)."""
    return styles.renderer_class(styles.scene_style(scene))(scene, width, use_tts=use_tts, fps=fps)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render a scene.json (2d or 2.5d style) to mp4")
    ap.add_argument("scene")
    ap.add_argument("-o", "--out", default=None, help="output .mp4 (or .png with --frame)")
    ap.add_argument("--width", type=int, default=1080, help="output width in px (height is 16:9 portrait)")
    ap.add_argument("--fps", type=int, default=None)
    ap.add_argument("--no-tts", action="store_true", help="skip speech synthesis (estimated timing, silent voice)")
    ap.add_argument("--frame", type=float, default=None, help="render one PNG frame at this time (seconds)")
    ap.add_argument("--print-style", action="store_true", help="only print the scene's style (2d / 2.5d)")
    args = ap.parse_args(argv)

    scene = load_scene(args.scene)
    try:
        if args.print_style:
            print(styles.scene_style(scene))
            return
        r = Renderer(scene, args.width, use_tts=not args.no_tts, fps=args.fps)
    except ValueError as e:              # style mix-ups etc.: a clear one-line error instead of a traceback
        raise SystemExit("error: %s" % e)
    name = os.path.splitext(os.path.basename(args.scene))[0]
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

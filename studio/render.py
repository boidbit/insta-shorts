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

from PIL import Image

from . import actions, audio
from .backgrounds import Background
from .characters import build_character, render_ops
from .scene import camera_at, compile_music, compile_scene, prepare_voice, split_scenes, static_overlays
from .text import bubble_image, styled_box
from .util import LH, LW, clamp, ease_in_out, ease_out, ease_out_back, load_scene

POS = {"top": (540, 330), "center": (540, 960), "lower": (540, 1450), "bottom": (540, 1560),
       "upper": (540, 520)}
TRANSITIONS = ("fade", "whip", "cut")


def frame_size(width):
    W = int(width) - int(width) % 2
    H = int(round(W * LH / LW))
    return W, H - H % 2


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

    def draw(self, img, overlays, t):
        for o in overlays:
            t0 = float(o.get("from", 0.0))
            t1 = o.get("to")
            t1 = float(t1) if t1 is not None else (t0 + float(o["dur"]) if "dur" in o else 1e9)
            if not (t0 <= t < t1):
                continue
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
            if t1 < 1e8:
                al *= clamp((t1 - t) / 0.2)
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
                filters.append("[%d:a]aresample=44100,aformat=channel_layouts=mono,adelay=%d:all=1,volume=1.0[s%d]"
                               % (idx, ms, idx))
                speech_lbl.append("[s%d]" % idx)
                idx += 1
        for fx in self.sfx:
            cmd += ["-i", fx["path"]]
            ms = int(fx["t"] * 1000)
            filters.append("[%d:a]aresample=44100,aformat=channel_layouts=mono,adelay=%d:all=1,volume=%.2f[f%d]"
                           % (idx, ms, fx["volume"], idx))
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
        self.bg = Background(self.plan.background, self.W, self.H)
        self.overlay_layer = OverlayLayer(self.s)
        self._lip = {}
        self._label_cache = {}
        self.fps, self.duration, self.n_frames = self.plan.fps, self.plan.duration, self.plan.n_frames
        self.speech, self.sfx, self.music = self.plan.speech, self.plan.sfx, self.plan.music

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

    # ------------------------------------------------------------ one frame
    def frame(self, t):
        plan, s = self.plan, self.s
        img = self.bg.frame(t).convert("RGB")
        order = sorted(plan.chars.values(), key=lambda c: (c.draw_pos(t)[1], c.draw_pos(t)[0]))
        anchors = {}
        states = {}
        for c in order:
            st = c.state_at(t)
            states[c.name] = st
            x, y = c.draw_pos(t)
            action, a_t0 = st["action"], st["action_t0"]
            moving = any(t0 <= t < t1 for (t0, t1, *_r) in c.moves)
            if moving and action in ("idle", "none", "stand"):
                action, a_t0 = "walk", 0.0
            opts = dict(st["opts"], _x=x, _bpm=plan.bpm)
            pose = actions.pose_for(action, t - a_t0 if action != "walk" else t, st["speed"], st["intensity"],
                                    c.phase, opts)
            singing = action in actions.SING_ACTIONS and not st["talking"]
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
            elif singing:                       # sings along to the music: believable mouth movement
                mouth_open = self._lip_open({}, t)
            blink = ((t + c.phase * 1.7) % 3.6) < 0.12
            spec = dict(c.spec)
            spec["facing"] = st["facing"]
            prop = st["prop"] or ("mic" if singing else None)
            ops, an = build_character(spec, pose, st["expression"], mouth_open, t, x, y, c.draw_scale(t),
                                      blink=blink, prop=prop, talking=bool(st["talking"]) or singing,
                                      tear_phase=(t * 1.1) % 1.0)
            r = render_ops(ops, s, self.W, self.H)
            if r:
                layer, (ox, oy) = r
                img.paste(layer, (ox, oy), layer)
            anchors[c.name] = an

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
            if sp and sp.get("bubble", True):
                lt = t - sp["start"]
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
        if i > 0 and lt < D and self.transition == "whip":
            prev = self.parts[i - 1]
            old = prev.frame(prev.duration - 1.0 / self.fps)
            e = ease_in_out(lt / D)
            canvas = Image.new("RGB", img.size)
            canvas.paste(old, (int(-self.W * e), 0))
            canvas.paste(img, (int(self.W * (1 - e)), 0))
            img = canvas
        elif self.transition == "fade":
            f = 1.0
            if i > 0 and lt < D / 2:
                f = lt / (D / 2)
            if i + 1 < len(self.parts) and part.duration - lt < D / 2:
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


def make_video(scene, width=1080, use_tts=True, fps=None, tts_provider=None):
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
    args = ap.parse_args(argv)

    scene = load_scene(args.scene)
    name = os.path.splitext(os.path.basename(args.scene))[0]
    r = make_video(scene, args.width, use_tts=not args.no_tts, fps=args.fps, tts_provider=args.tts)
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

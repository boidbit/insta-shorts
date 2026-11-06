"""Multi-scene videos: several scenes in a row with transitions, and split-screen.

{
  "meta": { "fps": 30 },
  "music": { "type": "beat", "bpm": 96, "volume": 0.2 },       # optional: one track across the whole video
  "transition": { "type": "fade", "dur": 0.4 },                 # default transition between scenes
  "overlays": [ ... ], "caption": "...",                        # optional: shown over the whole video
  "scenes": [
    { ...a normal scene (may use "extends") ... },
    { "transition": { "type": "wipe" }, ...next scene... },
    { "file": "scenes/other.json", "transition": "whip" },
    { "split": [ { ...top scene... }, { ...bottom scene... } ], "transition": "fade" }
  ]
}

Transitions: cut, fade, dip (through black), wipe, wipe_left, slide, whip, zoom, iris.
During a transition both scenes keep playing (they overlap by the transition length).
"""
import copy
import math

from PIL import Image, ImageDraw, ImageFilter

from .render import Renderer
from .util import LH, LW, clamp, ease_in_out, expand_scene

TRANSITIONS = ("cut", "fade", "dip", "wipe", "wipe_left", "slide", "whip", "zoom", "iris")
DEFAULT_DUR = {"cut": 0.0, "fade": 0.45, "dip": 0.7, "wipe": 0.45, "wipe_left": 0.45, "slide": 0.4, "whip": 0.3,
               "zoom": 0.45, "iris": 0.6}


def _tr(v):
    if not v:
        return {"type": "cut", "dur": 0.0}
    tr = {"type": v} if isinstance(v, str) else dict(v)
    tr.setdefault("type", "fade")
    tr.setdefault("dur", DEFAULT_DUR.get(tr["type"], 0.4))
    return tr


def blend(a, b, p, typ, W, H):
    """Frame halfway through a transition from a to b (p = 0..1)."""
    e = ease_in_out(p)
    if typ == "fade":
        return Image.blend(a, b, e)
    if typ == "dip":
        black = Image.new("RGB", a.size, (0, 0, 0))
        return Image.blend(a, black, e * 2) if e < 0.5 else Image.blend(black, b, (e - 0.5) * 2)
    if typ in ("wipe", "wipe_left"):
        x = int(W * e)
        out = a.copy()
        if typ == "wipe":
            out.paste(b.crop((0, 0, x, H)), (0, 0))
        else:
            out.paste(b.crop((W - x, 0, W, H)), (W - x, 0))
        ImageDraw.Draw(out).rectangle([x - 4, 0, x + 4, H] if typ == "wipe" else [W - x - 4, 0, W - x + 4, H],
                                      fill=(255, 255, 255))
        return out
    if typ in ("slide", "whip"):
        out = Image.new("RGB", a.size)
        off = int(W * e)
        out.paste(a, (-off, 0))
        out.paste(b, (W - off, 0))
        if typ == "whip":
            r = 40 * math.sin(math.pi * p) * W / LW
            if r > 0.5:
                small = out.resize((max(1, W // 6), H))       # cheap horizontal motion blur
                out = small.resize((W, H), Image.BILINEAR).filter(ImageFilter.BoxBlur(r / 6))
        return out
    if typ == "zoom":
        z = 1 + 0.8 * e
        vw, vh = W / z, H / z
        za = a.resize((W, H), Image.BILINEAR, box=((W - vw) / 2, (H - vh) / 2, (W + vw) / 2, (H + vh) / 2))
        return Image.blend(za, b, e)
    if typ == "iris":
        mask = Image.new("L", (W, H), 0)
        R = math.hypot(W, H) / 2 * e
        ImageDraw.Draw(mask).ellipse([W / 2 - R, H / 2 - R, W / 2 + R, H / 2 + R], fill=255)
        return Image.composite(b, a, mask)
    return b


class Segment:
    def __init__(self, renderers, start, dur, tr):
        self.renderers, self.start, self.dur, self.tr = renderers, start, dur, tr


class MultiRenderer:
    def __init__(self, doc, width=1080, use_tts=True, fps=None):
        meta = doc.get("meta", {})
        self.fps = int(fps or meta.get("fps", 30))
        global_music = doc.get("music") or meta.get("music")
        default_tr = doc.get("transition", "cut")
        self.segs = []
        t = 0.0
        for i, raw in enumerate(doc.get("scenes", [])):
            tr = _tr(raw.get("transition", default_tr) if i else None)
            parts = raw["split"][:2] if "split" in raw else [raw]
            rs = []
            for part in parts:
                sc = expand_scene(copy.deepcopy(part))
                sc.pop("transition", None)
                if global_music:                      # one track across the whole video instead
                    sc.pop("music", None)
                    sc.setdefault("meta", {}).pop("music", None)
                if "split" in raw:
                    sc.setdefault("meta", {}).setdefault("vignette", 0)
                rs.append(Renderer(sc, width, use_tts=use_tts, fps=self.fps))
            dur = max(r.duration for r in rs)
            td = 0.0
            if self.segs and tr["type"] != "cut":
                td = min(float(tr["dur"]), dur * 0.5, self.segs[-1].dur * 0.5)
            tr["dur"] = td
            start = t - td
            self.segs.append(Segment(rs, start, dur, tr))
            t = start + dur
        if not self.segs:
            raise SystemExit("multi-scene file has no \"scenes\"")
        self.duration = round(t, 3)
        self.n_frames = int(round(self.duration * self.fps))
        self.W, self.H = self.segs[0].renderers[0].W, self.segs[0].renderers[0].H
        self.s = self.W / float(LW)
        top = {"background": {"type": "plain"}, "meta": {"duration": self.duration, "fps": self.fps, "vignette": 0},
               "characters": {}, "timeline": [], "overlays": doc.get("overlays", [])}
        if doc.get("caption"):
            top["caption"] = doc["caption"]
        if global_music:
            top["music"] = global_music
        self.top = Renderer(top, width, use_tts=False, fps=self.fps)

    def _seg_frame(self, seg, T):
        lt = clamp(T - seg.start, 0.0, seg.dur - 1e-3)
        if len(seg.renderers) == 1:
            return seg.renderers[0].frame_at(lt)
        # split-screen: the middle band of each scene (where the characters are), stacked
        s = self.s
        y0, y1 = int(760 * s), int(760 * s) + self.H // 2
        out = Image.new("RGB", (self.W, self.H))
        for i, r in enumerate(seg.renderers):
            fr = r.frame_at(min(lt, r.duration - 1e-3))
            out.paste(fr.crop((0, y0, self.W, y1)), (0, i * (self.H // 2)))
        ImageDraw.Draw(out).rectangle([0, self.H // 2 - int(5 * s), self.W, self.H // 2 + int(5 * s)],
                                      fill=(255, 255, 255))
        return out

    def frame_at(self, T):
        T = min(T, self.duration - 1e-3)
        cur = None
        for i, seg in enumerate(self.segs):
            if seg.start <= T:
                cur = i
        seg = self.segs[cur]
        img = self._seg_frame(seg, T)
        if cur > 0 and seg.tr["dur"] > 0 and T < seg.start + seg.tr["dur"]:
            prev = self.segs[cur - 1]
            p = (T - seg.start) / seg.tr["dur"]
            img = blend(self._seg_frame(prev, T), img, p, seg.tr["type"], self.W, self.H)
        return self.top._draw_overlays(img, T)

    def frame(self, T):
        return self.frame_at(T)

    def audio_items(self):
        speech, sfx, musics = [], [], []
        for seg in self.segs:
            for r in seg.renderers:
                a, b, c = r.audio_items(seg.start)
                speech += a
                sfx += b
                musics += [dict(m, dur=min(m["dur"], seg.dur)) for m in c]
        _a, _b, gm = self.top.audio_items(0.0)
        return speech, sfx, musics + gm

    def render_video(self, out):
        from .render import render_frames
        render_frames(self, out)

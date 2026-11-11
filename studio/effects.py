"""Cartoon + atmosphere effects.

Timeline:   { "t": 2.0, "who": "A", "fx": "sweat" }
            { "t": 2.0, "fx": { "type": "glow_eyes", "pos": [820, 1250], "dur": 3 } }
            { "t": 0.0, "fx": { "type": "rain" } }                     # screen-wide, whole video
Scene:      "effects": [ { "type": "fireflies", "from": 0, "to": 8 } ]

Kinds:
  attached to a character (anchor = head unless "at" says hand_r / hand_l / feet / mouth):
      sweat, anger, sparkle, dizzy, question, exclaim, zzz, hearts, bulb, tears_spray, dust, speed,
      steam, thought (needs "text")
  placed in the world ("pos": [x, y] logical, or "who" to use that character):
      pow (optional "text"), glow_eyes, fire, smoke, projectile (from/to characters, "prop")
  screen-wide (drawn on top of the scene, under the captions):
      rain, snow, fog, fireflies, leaves, confetti, lightning, flash, spotlight (needs "who"), focus_lines
"""
import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .text import font, is_deva, text_block
from .util import LH, LW, clamp, ease_out, ease_out_back

ATTACHED = {"sweat", "anger", "sparkle", "dizzy", "question", "exclaim", "zzz", "hearts", "bulb",
            "tears_spray", "dust", "speed", "steam", "thought"}
WORLD = {"pow", "glow_eyes", "fire", "smoke", "projectile"}
SCREEN = {"rain", "snow", "fog", "fireflies", "leaves", "confetti", "lightning", "flash", "spotlight",
          "focus_lines"}
ALL = ATTACHED | WORLD | SCREEN

DEFAULT_DUR = {"sweat": 2.0, "anger": 1.6, "sparkle": 1.6, "dizzy": 2.5, "question": 1.6, "exclaim": 1.0,
               "zzz": 3.0, "hearts": 2.0, "bulb": 1.6, "tears_spray": 2.0, "dust": 0.7, "speed": 1.0,
               "steam": 1e9, "thought": 2.5, "pow": 0.7, "glow_eyes": 3.0, "fire": 1e9, "smoke": 1e9,
               "projectile": 0.6, "rain": 1e9, "snow": 1e9, "fog": 1e9, "fireflies": 1e9, "leaves": 1e9,
               "confetti": 4.0, "lightning": 1.0, "flash": 0.35, "spotlight": 3.0, "focus_lines": 1.0}
INK = (16, 16, 16, 255)


def normalize(raw, t_default):
    """Event value -> effect dict with type/from/to."""
    fx = {"type": raw} if isinstance(raw, str) else dict(raw)
    fx.setdefault("from", t_default)
    if fx.get("to") is None:
        fx["to"] = fx["from"] + float(fx.get("dur", DEFAULT_DUR.get(fx.get("type"), 2.0)))
    return fx


# ---------------------------------------------------------------- tiny 2x-supersampled drawing patch
class Patch:
    """Draw in LOGICAL coordinates into a small supersampled RGBA patch around (cx, cy)."""

    def __init__(self, cx, cy, hw, hh, s, ss=2):
        self.s, self.ss = s, ss
        self.ox, self.oy = cx - hw, cy - hh
        self.k = s * ss
        w, h = max(2, int(2 * hw * self.k)), max(2, int(2 * hh * self.k))
        self.im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im, "RGBA")

    def P(self, x, y):
        return ((x - self.ox) * self.k, (y - self.oy) * self.k)

    def pts(self, pp):
        return [self.P(x, y) for x, y in pp]

    def W(self, w):
        return max(1, int(w * self.k))

    def poly(self, pp, fill=None, outline=None, w=4):
        q = self.pts(pp)
        if fill is not None:
            self.d.polygon(q, fill=fill)
        if outline is not None:
            self.d.line(q + q[:2], fill=outline, width=self.W(w), joint="curve")

    def line(self, pp, color=INK, w=4):
        self.d.line(self.pts(pp), fill=color, width=self.W(w), joint="curve")

    def ellipse(self, cx, cy, rx, ry, fill=None, outline=None, w=4):
        a, b = self.P(cx - rx, cy - ry), self.P(cx + rx, cy + ry)
        self.d.ellipse([a, b], fill=fill, outline=outline, width=self.W(w) if outline else 0)

    def text(self, x, y, txt, size, fill=(255, 255, 255, 255), stroke=6, stroke_fill=INK):
        f = font(size * self.k, "deva" if any(is_deva(ch) for ch in str(txt)) else "main")   # चमगादड़ on a board
        self.d.text(self.P(x, y), txt, font=f, fill=fill, anchor="mm", stroke_width=self.W(stroke),
                    stroke_fill=stroke_fill)

    def paste(self, img, alpha=1.0):
        small = self.im.reduce(self.ss)
        if alpha < 0.999:
            small.putalpha(small.getchannel("A").point([int(v * alpha) for v in range(256)]))
        img.paste(small, (int(round(self.ox * self.s)), int(round(self.oy * self.s))), small)


def _star(cx, cy, r_out, r_in, n=4, rot=0.0):
    pts = []
    for i in range(n * 2):
        r = r_out if i % 2 == 0 else r_in
        a = rot + math.pi * i / n - math.pi / 2
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _heart(cx, cy, size):
    pts = []
    for i in range(36):
        t = 2 * math.pi * i / 36
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((cx + x * size / 16.0, cy + y * size / 16.0))
    return pts


def _drop(cx, cy, r):
    """Teardrop: pointed top, round bottom centred at (cx, cy)."""
    pts = [(cx, cy - 2.2 * r)]
    for i in range(19):
        a = math.radians(-25 + 230 * i / 18)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


# ---------------------------------------------------------------- the effect renderer
class Effects:
    def __init__(self, effects, s, W, H, fps=30):
        self.list = []
        for i, fx in enumerate(effects):
            fx = dict(fx)
            fx["_seed"] = 1000 + i * 37
            self.list.append(fx)
        self.s, self.W, self.H = s, W, H
        self._fog = None
        self._dark = {}

    def active(self, t, kinds):
        for fx in self.list:
            if fx.get("type") in kinds and fx["from"] <= t < fx["to"]:
                yield fx

    # ---------------- character-attached + world effects (inside the camera)
    def draw_world(self, img, t, anchors, chars):
        for fx in self.active(t, ATTACHED | WORLD):
            lt = t - fx["from"]
            dur = fx["to"] - fx["from"]
            fade = clamp(lt / 0.15) * (clamp((fx["to"] - t) / 0.25) if dur < 1e8 else 1.0)
            kind = fx["type"]
            who = fx.get("who")
            an = anchors.get(who) if who else None
            if kind in ATTACHED and an is None:
                continue
            fn = getattr(self, "_" + kind, None)
            if fn:
                fn(img, fx, lt, fade, an, anchors, chars)

    def _anchor(self, fx, an, default="head_top"):
        if fx.get("pos"):
            return tuple(fx["pos"])
        return an.get(fx.get("at", default), an["head_top"])

    def _sweat(self, img, fx, lt, fade, an, *_):
        hx, hy = an["head_center"]
        p = Patch(hx, hy, 170, 170, self.s)
        rng = random.Random(fx["_seed"])
        for i in range(3):
            ph = (lt * 0.9 + i / 3.0) % 1.0
            side = 1 if i != 1 else -1
            x = hx + side * (92 + rng.uniform(-6, 10))
            y = hy - 50 + ph * 90 + i * 8
            r = 12 - i * 2
            p.poly(_drop(x, y, r), (150, 205, 245, int(255 * (1 - ph * 0.6))), INK, 3)
        p.paste(img, fade)

    def _anger(self, img, fx, lt, fade, an, *_):
        hx, hy = an["head_top"]
        cx, cy = hx + 70, hy + 6
        sc = 1.0 + 0.18 * abs(math.sin(lt * 9))
        p = Patch(cx, cy, 60, 60, self.s)
        red = (220, 40, 50, 255)
        for a in (45, 135, 225, 315):
            r = math.radians(a)
            ux, uy = math.cos(r), math.sin(r)
            q = (cx + ux * 30 * sc, cy + uy * 30 * sc)
            o = (cx + ux * 8 * sc, cy + uy * 8 * sc)
            p.line([o, (o[0] + (q[0] - o[0]) * 0.5 + uy * 6, o[1] + (q[1] - o[1]) * 0.5 - ux * 6), q], red, 9)
        p.paste(img, fade)

    def _sparkle(self, img, fx, lt, fade, an, *_):
        cx, cy = self._anchor(fx, an, "head_center")
        p = Patch(cx, cy, 230, 260, self.s)
        rng = random.Random(fx["_seed"])
        for i in range(7):
            ox, oy = rng.uniform(-190, 190), rng.uniform(-220, 220)
            tw = abs(math.sin(lt * 4 + i * 1.7))
            r = 10 + 20 * tw
            p.poly(_star(cx + ox, cy + oy, r, r * 0.3, 4, lt * 0.5), (255, 236, 120, int(255 * tw)), None)
        p.paste(img, fade)

    def _dizzy(self, img, fx, lt, fade, an, *_):
        hx, hy = an["head_top"]
        p = Patch(hx, hy, 150, 70, self.s)
        for i in range(4):
            a = lt * 5 + i * math.pi / 2
            x, y = hx + 110 * math.cos(a), hy - 6 + 26 * math.sin(a)
            p.poly(_star(x, y, 20, 8, 5, a), (255, 222, 70, 255), INK, 3)
        p.paste(img, fade)

    def _mark(self, img, fx, lt, fade, an, ch, size=150, color=(255, 255, 255, 255)):
        hx, hy = an["head_top"]
        pop = ease_out_back(lt / 0.25)
        bob = 8 * math.sin(lt * 5)
        p = Patch(hx + 40, hy - 90, 110, 110, self.s)
        p.text(hx + 40, hy - 80 + bob, ch, size * max(0.2, pop), color, 9)
        p.paste(img, fade)

    def _question(self, img, fx, lt, fade, an, *_):
        self._mark(img, fx, lt, fade, an, "?", 150, (255, 255, 255, 255))

    def _exclaim(self, img, fx, lt, fade, an, *_):
        self._mark(img, fx, lt, fade, an, "!", 160, (255, 220, 60, 255))

    def _zzz(self, img, fx, lt, fade, an, *_):
        hx, hy = an["head_top"]
        p = Patch(hx + 120, hy - 120, 160, 160, self.s)
        for i in range(3):
            ph = (lt * 0.5 + i / 3.0) % 1.0
            x = hx + 60 + ph * 120 + 14 * math.sin(ph * 6)
            y = hy - 10 - ph * 200
            p.text(x, y, "Z", 40 + 50 * ph, (255, 255, 255, int(255 * (1 - ph))), 5)
        p.paste(img, fade)

    def _hearts(self, img, fx, lt, fade, an, *_):
        hx, hy = an["head_top"]
        p = Patch(hx, hy - 120, 200, 200, self.s)
        for i in range(4):
            ph = (lt * 0.6 + i / 4.0) % 1.0
            x = hx + (i - 1.5) * 60 + 18 * math.sin(ph * 7 + i)
            y = hy + 10 - ph * 260
            p.poly(_heart(x, y, 18 + 10 * ph), (230, 60, 90, int(255 * (1 - ph))), INK, 3)
        p.paste(img, fade)

    def _bulb(self, img, fx, lt, fade, an, *_):
        hx, hy = an["head_top"]
        cx, cy = hx + 10, hy - 110
        pop = ease_out_back(lt / 0.3)
        p = Patch(cx, cy, 130, 130, self.s)
        on = 0.6 + 0.4 * abs(math.sin(lt * 6))
        for i in range(8):
            a = i * math.pi / 4
            p.line([(cx + 70 * math.cos(a) * pop, cy + 70 * math.sin(a) * pop),
                    (cx + 100 * math.cos(a) * pop, cy + 100 * math.sin(a) * pop)], (255, 220, 60, int(255 * on)), 7)
        p.ellipse(cx, cy - 6, 46 * pop, 50 * pop, (255, 236, 120, 255), INK, 5)
        p.poly([(cx - 20 * pop, cy + 36 * pop), (cx + 20 * pop, cy + 36 * pop), (cx + 18 * pop, cy + 62 * pop),
                (cx - 18 * pop, cy + 62 * pop)], (170, 170, 176, 255), INK, 4)
        p.paste(img, fade)

    def _tears_spray(self, img, fx, lt, fade, an, *_):
        hx, hy = an["head_center"]
        p = Patch(hx, hy + 60, 260, 200, self.s)
        for side in (-1, 1):
            for j in range(6):
                ph = (lt * 2.2 + j / 6.0) % 1.0
                x = hx + side * (40 + ph * 200)
                y = hy - 4 - 80 * math.sin(math.pi * ph * 0.8) + ph * 120
                p.ellipse(x, y, 11, 14, (140, 200, 245, 230), INK, 2)
        p.paste(img, fade)

    def _dust(self, img, fx, lt, fade, an, *_):
        fx_, fy_ = an["feet"]
        p = Patch(fx_, fy_ - 30, 220, 90, self.s)
        e = ease_out(lt / max(0.1, fx["to"] - fx["from"]))
        for i, ox in enumerate((-120, -60, 0, 60, 120)):
            r = 26 + 34 * e + (i % 2) * 8
            p.ellipse(fx_ + ox * (0.6 + e), fy_ - 20 - 20 * e, r, r * 0.75, (225, 215, 195, int(220 * (1 - e))), None)
        p.paste(img, fade)

    def _speed(self, img, fx, lt, fade, an, *_):
        cx, cy = an["head_center"]
        d = fx.get("dir", 1)
        p = Patch(cx - d * 260, cy + 200, 260, 360, self.s)
        rng = random.Random(fx["_seed"] + int(lt * 12))
        for i in range(9):
            y = cy - 80 + i * 70 + rng.uniform(-10, 10)
            x0 = cx - d * (110 + rng.uniform(0, 40))
            L = 140 + rng.uniform(0, 120)
            p.line([(x0, y), (x0 - d * L, y)], (40, 40, 40, 170), 5)
        p.paste(img, fade)

    def _steam(self, img, fx, lt, fade, an, *_):
        cx, cy = self._anchor(fx, an, "hand_r")
        cy -= 40
        p = Patch(cx, cy - 110, 70, 130, self.s)
        for j in range(3):
            ph = (lt * 0.6 + j / 3.0) % 1.0
            pts = [(cx - 20 + j * 20 + 10 * math.sin(ph * 6 + i * 0.8), cy - i * 18 - ph * 60) for i in range(7)]
            p.line(pts, (255, 255, 255, int(200 * (1 - ph))), 6)
        p.paste(img, fade)

    def _thought(self, img, fx, lt, fade, an, *_):
        hx, hy = an["head_top"]
        im = thought_image(str(fx.get("text", "...")), self.s)
        sc = 0.6 + 0.4 * ease_out_back(lt / 0.3)
        w, h = max(1, int(im.width * sc)), max(1, int(im.height * sc))
        im = im.resize((w, h), Image.BILINEAR)
        side = fx.get("side", 1 if hx < LW / 2 else -1)
        bx = clamp(hx * self.s + side * 40 * self.s - w / 2, 16 * self.s, self.W - w - 16 * self.s)
        by = max(10, hy * self.s - h - 70 * self.s)
        if fade < 0.999:
            im.putalpha(im.getchannel("A").point([int(v * fade) for v in range(256)]))
        img.paste(im, (int(bx), int(by)), im)
        p = Patch(hx, hy - 40, 120, 60, self.s)                      # little trail circles
        for i, r in enumerate((10, 15)):
            p.ellipse(hx + side * (20 + i * 26), hy - 20 - i * 34, r, r, (255, 255, 255, 255), INK, 4)
        p.paste(img, fade)

    def _pow(self, img, fx, lt, fade, an, anchors, chars):
        cx, cy = self._anchor(fx, an, "head_center") if an else tuple(fx.get("pos", (540, 900)))
        sc = ease_out_back(lt / 0.2)
        p = Patch(cx, cy, 230, 200, self.s)
        p.poly(_star(cx, cy, 190 * sc, 110 * sc, 12, 0.2), tuple(fx.get("color", (255, 214, 60))) + (255,), INK, 6)
        p.poly(_star(cx, cy, 130 * sc, 80 * sc, 12, 0.5), (240, 80, 60, 255), None)
        p.text(cx, cy + 4, str(fx.get("text", "POW!")), 64 * sc, (255, 255, 255, 255), 7)
        p.paste(img, fade)

    def _glow_eyes(self, img, fx, lt, fade, an, anchors, chars):
        cx, cy = tuple(fx["pos"]) if fx.get("pos") else self._anchor(fx, an, "head_center")
        col = tuple(fx.get("color", (255, 236, 90)))
        sp = float(fx.get("spacing", 70))
        blink = (lt % 2.6) > 2.45
        p = Patch(cx, cy, sp + 90, 90, self.s)
        pulse = 0.8 + 0.2 * math.sin(lt * 3)
        for side in (-1, 1):
            ex = cx + side * sp / 2
            for r, a in ((70, 30), (48, 50), (32, 80)):
                p.ellipse(ex, cy, r * pulse, r * 0.7 * pulse, col + (a,), None)
            if blink:
                p.line([(ex - 22, cy), (ex + 22, cy)], col + (255,), 6)
            else:
                p.poly([(ex - 24, cy - 2), (ex, cy - 14), (ex + 24, cy - 2), (ex, cy + 12)], col + (255,), None)
                p.ellipse(ex, cy, 5, 10, (20, 20, 10, 255), None)
        p.paste(img, fade)

    def _fire(self, img, fx, lt, fade, an, anchors, chars):
        cx, cy = tuple(fx["pos"]) if fx.get("pos") else an["feet"]
        sz = float(fx.get("size", 1.0))
        p = Patch(cx, cy - 120 * sz, 140 * sz, 150 * sz, self.s)
        for layer, (col, scale) in enumerate((((236, 80, 40, 230), 1.0), ((250, 160, 50, 240), 0.72),
                                              ((255, 236, 120, 255), 0.42))):
            pts = []
            for i in range(9):
                a = math.pi * i / 8
                flick = 1 + 0.25 * math.sin(lt * 14 + i * 2.1 + layer)
                r = 90 * sz * scale
                pts.append((cx + r * math.cos(a + math.pi), cy - r * 0.15 * math.sin(a)))
            tip_h = 220 * sz * scale * (1 + 0.15 * math.sin(lt * 11 + layer))
            pts = [(cx - 90 * sz * scale, cy)] + [(cx - 60 * sz * scale + 20 * math.sin(lt * 9 + layer), cy - tip_h * 0.55),
                                                  (cx + 6 * math.sin(lt * 13 + layer), cy - tip_h),
                                                  (cx + 50 * sz * scale + 18 * math.sin(lt * 10 + layer), cy - tip_h * 0.5),
                                                  (cx + 90 * sz * scale, cy)]
            p.poly(pts, col, INK if layer == 0 else None, 4)
        p.paste(img, fade)

    def _smoke(self, img, fx, lt, fade, an, anchors, chars):
        cx, cy = tuple(fx["pos"]) if fx.get("pos") else an["head_top"]
        p = Patch(cx, cy - 220, 200, 260, self.s)
        for j in range(6):
            ph = (lt * 0.35 + j / 6.0) % 1.0
            x = cx + 40 * math.sin(ph * 5 + j)
            y = cy - ph * 420
            r = 30 + 90 * ph
            g = int(fx.get("shade", 150))
            p.ellipse(x, y, r, r * 0.85, (g, g, g + 6, int(170 * (1 - ph))), None)
        p.paste(img, fade)

    def _projectile(self, img, fx, lt, fade, an, anchors, chars):
        a, b = anchors.get(fx.get("src")), anchors.get(fx.get("dst"))
        if not a or not b:
            return
        from .characters import Sketch, _draw_prop, render_ops
        p0 = a.get("hand_r")
        p1 = b.get(fx.get("hit_at", "head_center"))
        u = clamp(lt / max(0.05, fx["to"] - fx["from"]))
        x = p0[0] + (p1[0] - p0[0]) * u
        y = p0[1] + (p1[1] - p0[1]) * u - float(fx.get("arc", 160)) * math.sin(math.pi * u)
        ang = (fx.get("spin", 900) * u) if fx.get("spin", True) else 0
        S = Sketch(x, y, 1.0, 0, 0, 0, 0)
        _draw_prop(S, fx.get("prop", "chappal"), (-40, 0), ang, None)
        r = render_ops(S.ops, self.s, self.W, self.H)
        if r:
            layer, (ox, oy) = r
            img.paste(layer, (ox, oy), layer)

    # ---------------- screen-wide (after the camera)
    def draw_screen(self, img, t, anchors_screen):
        for fx in self.active(t, SCREEN):
            lt = t - fx["from"]
            dur = fx["to"] - fx["from"]
            fade = clamp(lt / 0.4) * (clamp((fx["to"] - t) / 0.4) if dur < 1e8 else 1.0)
            img = getattr(self, "_s_" + fx["type"])(img, fx, t, lt, fade, anchors_screen)
        return img

    def _layer(self):
        return Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))

    def _comp(self, img, layer):
        base = img.convert("RGBA")
        base.alpha_composite(layer)
        return base.convert("RGB")

    def _s_rain(self, img, fx, t, lt, fade, _a):
        n = int(fx.get("density", 140))
        layer = self._layer()
        d = ImageDraw.Draw(layer, "RGBA")
        rng = random.Random(fx["_seed"])
        s = self.s
        for i in range(n):
            x0, sp_ = rng.uniform(-200, LW + 200), rng.uniform(1700, 2300)
            ph = rng.random()
            y = ((ph * (LH + 300) + t * sp_) % (LH + 300)) - 150
            x = x0 - (y + 150) * 0.18
            L = rng.uniform(40, 80)
            d.line([(x * s, y * s), ((x - L * 0.18) * s, (y + L) * s)], fill=(200, 215, 235, int(150 * fade)),
                   width=max(1, int(3 * s)))
        dim = Image.new("RGBA", (self.W, self.H), (40, 50, 70, int(50 * fade)))
        dim.alpha_composite(layer)
        return self._comp(img, dim)

    def _s_snow(self, img, fx, t, lt, fade, _a):
        n = int(fx.get("density", 90))
        layer = self._layer()
        d = ImageDraw.Draw(layer, "RGBA")
        rng = random.Random(fx["_seed"])
        s = self.s
        for i in range(n):
            x0, sp_, r = rng.uniform(0, LW), rng.uniform(80, 180), rng.uniform(4, 10)
            y = ((rng.random() * (LH + 100) + t * sp_) % (LH + 100)) - 50
            x = x0 + 30 * math.sin(t * 1.3 + i)
            d.ellipse([(x - r) * s, (y - r) * s, (x + r) * s, (y + r) * s], fill=(255, 255, 255, int(230 * fade)))
        return self._comp(img, layer)

    def _s_fog(self, img, fx, t, lt, fade, _a):
        if self._fog is None:
            rng = np.random.RandomState(7)
            w, h = max(8, self.W // 8), max(8, self.H // 8)
            noise = rng.rand(h, w * 2).astype("float32")
            im = Image.fromarray((noise * 255).astype("uint8"), "L").resize((self.W * 2, self.H), Image.BICUBIC)
            im = im.filter(ImageFilter.GaussianBlur(40 * self.s))
            a = np.asarray(im).astype("float32") / 255.0
            a = np.clip((a - 0.35) * 2.2, 0, 1)
            yy = np.linspace(0, 1, self.H)[:, None]
            a = a * (0.35 + 0.65 * yy)               # thicker near the ground
            self._fog = a
        strength = float(fx.get("strength", 0.55)) * fade
        off = int((t * 30 * self.s) % self.W)
        a = self._fog[:, off:off + self.W]
        alpha = Image.fromarray((a * 255 * strength).astype("uint8"), "L")
        col = Image.new("RGBA", (self.W, self.H), tuple(fx.get("color", (220, 226, 236))) + (255,))
        col.putalpha(alpha)
        return self._comp(img, col)

    def _s_fireflies(self, img, fx, t, lt, fade, _a):
        layer = self._layer()
        d = ImageDraw.Draw(layer, "RGBA")
        rng = random.Random(fx["_seed"])
        s = self.s
        for i in range(int(fx.get("count", 22))):
            bx, by = rng.uniform(60, LW - 60), rng.uniform(900, 1650)
            x = bx + 70 * math.sin(t * 0.5 + i * 1.3)
            y = by + 40 * math.sin(t * 0.7 + i * 2.1)
            glow = max(0.0, math.sin(t * 2 + i * 1.7))
            for r, a in ((26, 40), (14, 90), (6, 255)):
                d.ellipse([(x - r) * s, (y - r) * s, (x + r) * s, (y + r) * s],
                          fill=(255, 240, 130, int(a * glow * fade)))
        return self._comp(img, layer)

    def _s_leaves(self, img, fx, t, lt, fade, _a):
        layer = self._layer()
        d = ImageDraw.Draw(layer, "RGBA")
        rng = random.Random(fx["_seed"])
        s = self.s
        cols = [(214, 130, 50), (196, 90, 50), (226, 180, 70), (120, 150, 60)]
        for i in range(int(fx.get("count", 24))):
            x0, sp_ = rng.uniform(0, LW), rng.uniform(90, 170)
            y = ((rng.random() * (LH + 100) + t * sp_) % (LH + 100)) - 50
            x = x0 + 60 * math.sin(t * 1.4 + i)
            a = t * 2 + i
            c = cols[i % 4]
            pts = [(x + 22 * math.cos(a), y + 22 * math.sin(a) * 0.5), (x + 8 * math.cos(a + 1.6), y + 8 * math.sin(a + 1.6)),
                   (x - 22 * math.cos(a), y - 22 * math.sin(a) * 0.5), (x - 8 * math.cos(a + 1.6), y - 8 * math.sin(a + 1.6))]
            d.polygon([(px * s, py * s) for px, py in pts], fill=c + (int(235 * fade),))
        return self._comp(img, layer)

    def _s_confetti(self, img, fx, t, lt, fade, _a):
        layer = self._layer()
        d = ImageDraw.Draw(layer, "RGBA")
        rng = random.Random(fx["_seed"])
        s = self.s
        cols = [(236, 80, 90), (90, 160, 236), (250, 210, 70), (110, 200, 120), (190, 110, 220)]
        for i in range(int(fx.get("count", 80))):
            x0, sp_ = rng.uniform(0, LW), rng.uniform(300, 600)
            y = -40 + lt * sp_ - rng.uniform(0, 600)
            if y < -40 or y > LH:
                continue
            x = x0 + 40 * math.sin(lt * 3 + i)
            a = lt * 6 + i
            w_, h_ = 16, 9 * abs(math.cos(a))
            pts = [(x - w_ * math.cos(a) - h_ * math.sin(a), y - w_ * math.sin(a) + h_ * math.cos(a)),
                   (x + w_ * math.cos(a) - h_ * math.sin(a), y + w_ * math.sin(a) + h_ * math.cos(a)),
                   (x + w_ * math.cos(a) + h_ * math.sin(a), y + w_ * math.sin(a) - h_ * math.cos(a)),
                   (x - w_ * math.cos(a) + h_ * math.sin(a), y - w_ * math.sin(a) - h_ * math.cos(a))]
            d.polygon([(px * s, py * s) for px, py in pts], fill=cols[i % 5] + (255,))
        return self._comp(img, layer)

    def _s_lightning(self, img, fx, t, lt, fade, _a):
        flash = max(0.0, 1 - lt / 0.12) + (max(0.0, 1 - abs(lt - 0.25) / 0.08) * 0.7)
        if flash <= 0.01:
            return img
        layer = self._layer()
        d = ImageDraw.Draw(layer, "RGBA")
        d.rectangle([0, 0, self.W, self.H], fill=(235, 240, 255, int(150 * flash)))
        rng = random.Random(fx["_seed"])
        x, y = rng.uniform(250, 830), 0
        pts = [(x, y)]
        while y < 900:
            y += rng.uniform(60, 120)
            x += rng.uniform(-70, 70)
            pts.append((x, y))
        d.line([(px * self.s, py * self.s) for px, py in pts], fill=(255, 255, 255, int(255 * flash)),
               width=max(2, int(9 * self.s)), joint="curve")
        return self._comp(img, layer)

    def _s_flash(self, img, fx, t, lt, fade, _a):
        k = max(0.0, 1 - lt / max(0.05, fx["to"] - fx["from"]))
        return Image.blend(img, Image.new("RGB", img.size, (255, 255, 255)), 0.85 * k)

    def _s_spotlight(self, img, fx, t, lt, fade, anchors_screen):
        c = anchors_screen.get(fx.get("who"))
        if c is None:
            return img
        cx, cy = c                                   # head centre on screen; the body hangs ~800 px below it
        r = float(fx.get("radius", 330)) * self.s
        mask = Image.new("L", (self.W, self.H), int(200 * fade))
        ImageDraw.Draw(mask).ellipse([cx - r, cy - 240 * self.s, cx + r, cy + 860 * self.s], fill=0)
        mask = mask.filter(ImageFilter.GaussianBlur(30 * self.s))
        dark = Image.new("RGB", img.size, (8, 8, 14))
        return Image.composite(dark, img, mask)

    def _s_focus_lines(self, img, fx, t, lt, fade, anchors_screen):
        c = anchors_screen.get(fx.get("who")) or (self.W / 2, self.H / 2)
        layer = self._layer()
        d = ImageDraw.Draw(layer, "RGBA")
        rng = random.Random(fx["_seed"] + int(t * 15))
        R = math.hypot(self.W, self.H)
        for i in range(70):
            a = rng.uniform(0, 2 * math.pi)
            r0 = rng.uniform(0.32, 0.5) * self.W
            w_ = rng.uniform(0.004, 0.012)
            p0 = (c[0] + r0 * math.cos(a), c[1] + r0 * math.sin(a))
            pa = (c[0] + R * math.cos(a - w_), c[1] + R * math.sin(a - w_))
            pb = (c[0] + R * math.cos(a + w_), c[1] + R * math.sin(a + w_))
            d.polygon([p0, pa, pb], fill=(20, 20, 20, int(200 * fade)))
        return self._comp(img, layer)


# ---------------------------------------------------------------- thought bubble (cloud)
def thought_image(text, s, size=44, max_w=560):
    tb = text_block(text, size * s, max_w * s, fill=(14, 14, 14))
    px, py = int(46 * s), int(36 * s)
    w, h = tb.width + 2 * px, tb.height + 2 * py
    SS = 2
    pad = int(30 * s)
    W, H = w + 2 * pad, h + 2 * pad
    im = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = W / 2, H / 2
    rx, ry = w / 2, h / 2
    bumps = max(8, int((w + h) / (70 * s)))
    circles = []
    for i in range(bumps):
        a = 2 * math.pi * i / bumps
        bx, by = cx + rx * 0.92 * math.cos(a), cy + ry * 0.88 * math.sin(a)
        r = min(rx, ry) * 0.42 + 8 * s
        circles.append((bx, by, r))
    ow = max(2, int(5 * s)) * SS
    for bx, by, r in circles:
        d.ellipse([(bx - r) * SS - ow, (by - r) * SS - ow, (bx + r) * SS + ow, (by + r) * SS + ow], fill=(16, 16, 16))
    d.ellipse([(cx - rx) * SS - ow, (cy - ry) * SS - ow, (cx + rx) * SS + ow, (cy + ry) * SS + ow], fill=(16, 16, 16))
    for bx, by, r in circles:
        d.ellipse([(bx - r) * SS, (by - r) * SS, (bx + r) * SS, (by + r) * SS], fill=(255, 255, 255))
    d.ellipse([(cx - rx) * SS, (cy - ry) * SS, (cx + rx) * SS, (cy + ry) * SS], fill=(255, 255, 255))
    im = im.reduce(SS)
    im.alpha_composite(tb, (int(cx - tb.width / 2), int(cy - tb.height / 2)))
    return im

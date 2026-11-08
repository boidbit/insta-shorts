"""2.5D style renderer: layered parallax backgrounds, toon bodies, a real camera (characters are
redrawn at the zoom, never stretched), perspective scaling, ground shadows, lighting, sprites and fx."""
import math

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from .. import actions
from ..characters import build_character, render_ops
from ..render import BaseRenderer
from ..scene import GROUND_Y, camera_at
from ..text import bubble_image, styled_box
from ..util import LH, LW, clamp, ease_out_back
from . import fx
from .body import TOON
from .scenery import Backdrop


class Renderer25D(BaseRenderer):
    style = "2.5d"

    def __init__(self, scene, width=1080, use_tts=True, fps=None):
        super().__init__(scene, width, use_tts=use_tts, fps=fps)
        self.bg = Backdrop(self.plan.background, self.W, self.H, zmax=self.plan.zmax)
        # lighting: background preset defaults < scene "light"
        self.light = dict(self.bg.light)
        self.light.update(self.plan.light)
        self.horizon = self.light.get("horizon", self.bg.horizon) if self.plan.perspective else None
        self._shadow = self._make_shadow()
        self._glow = self._make_glow()
        self._vig = self._make_vignette(float(self.light.get("vignette", 0.0)))
        self._objs = {o["id"]: o for o in self.plan.objects}
        self._sprite_cache, self._sprite_key = {}, {}

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
                                      tear_phase=(t * 1.1) % 1.0, body=TOON)
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

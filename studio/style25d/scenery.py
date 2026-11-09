"""Layered "2.5D" backgrounds: painted depth layers + parallax + depth-of-field + glowing lights.

A layered background is a stack of Layer objects, far -> near. Each layer has a depth `d`:
  d = 0    infinitely far (sky): does not move with the camera
  d = 1    the plane the characters stand on: moves exactly with the characters
  d > 1    foreground, in front of the characters (drawn after them)
When the camera zooms/pans, every layer is moved by its own amount -> parallax, which is what
makes a flat drawing read as 3D. Far layers are pre-blurred (depth of field).
"""
import math
import random

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

from ..util import LH, LW, clamp

WARM = (255, 206, 120)


# ------------------------------------------------------------------ drawing helpers
class Cv:
    """RGBA canvas addressed in logical (1080x1920) units at k pixels per unit.

    blend=True: semi-transparent shapes are alpha-blended onto what is already there (instead of
    replacing the pixels, which would punch see-through holes into an opaque layer)."""

    def __init__(self, k, fill=(0, 0, 0, 0), w=LW, h=LH, blend=False):
        self.k = k
        self.blend = blend
        self.im = Image.new("RGBA", (max(1, int(round(w * k))), max(1, int(round(h * k)))), fill)
        self.d = ImageDraw.Draw(self.im)

    def P(self, pts):
        return [(x * self.k, y * self.k) for x, y in pts]

    def _draw(self, fn, pts_px, color, pad):
        """Run fn(draw, pts) directly, or on a small temp layer that is alpha-composited (blend mode)."""
        if not (self.blend and color is not None and len(color) == 4 and color[3] < 255):
            fn(self.d, pts_px)
            return
        xs = [p[0] for p in pts_px]
        ys = [p[1] for p in pts_px]
        x0, y0 = max(0, int(min(xs) - pad - 2)), max(0, int(min(ys) - pad - 2))
        x1, y1 = min(self.im.width, int(max(xs) + pad + 3)), min(self.im.height, int(max(ys) + pad + 3))
        if x1 <= x0 or y1 <= y0:
            return
        tmp = Image.new("RGBA", (x1 - x0, y1 - y0), tuple(color[:3]) + (0,))
        fn(ImageDraw.Draw(tmp), [(x - x0, y - y0) for x, y in pts_px])
        self.im.alpha_composite(tmp, dest=(x0, y0))

    def poly(self, pts, fill=None, outline=None, w=0):
        if fill is not None:
            self._draw(lambda d, q: d.polygon(q, fill=fill), self.P(pts), fill, 0)
        if outline is not None and w:
            self.line(list(pts) + [pts[0]], outline, w)

    def rect(self, x0, y0, x1, y1, fill=None, outline=None, w=0):
        self.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], fill, outline, w)

    def ell(self, cx, cy, rx, ry, fill=None, outline=None, w=0):
        k = self.k
        box = [((cx - rx) * k, (cy - ry) * k), ((cx + rx) * k, (cy + ry) * k)]
        wd = max(1, int(round(w * k))) if outline is not None else 0
        self._draw(lambda d, q: d.ellipse([q[0][0], q[0][1], q[1][0], q[1][1]], fill=fill, outline=outline,
                                          width=wd), box, fill if fill is not None else outline, wd)

    def line(self, pts, color, w):
        wd = max(1, int(round(w * self.k)))
        self._draw(lambda d, q: d.line(q, fill=color, width=wd, joint="curve"), self.P(pts), color, wd)

    def erase(self, pts):
        """Punch a fully transparent hole (e.g. a window you can see the far layer through)."""
        self.d.polygon(self.P(pts), fill=(0, 0, 0, 0))

    def blur(self, r):
        if r > 0:
            self.im = self.im.filter(ImageFilter.GaussianBlur(r * self.k))
            self.d = ImageDraw.Draw(self.im)

    def over(self, other):
        if other.im.size != self.im.size:
            other_im = other.im.resize(self.im.size, Image.BILINEAR)
        else:
            other_im = other.im
        self.im.alpha_composite(other_im)
        self.d = ImageDraw.Draw(self.im)

    def glow(self, x, y, r, color, a=120, steps=9):
        """Soft radial glow (concentric discs, brighter in the middle)."""
        for i in range(steps):
            rr = r * (1 - i / float(steps))
            self.ell(x, y, rr, rr, color + (int(a * (i + 1) / steps),))


def mix(c0, c1, u):
    return tuple(int(round(c0[i] + (c1[i] - c0[i]) * u)) for i in range(3))


def mul(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c[:3])


def vgrad(k, stops, w=LW, h=LH):
    """Opaque vertical gradient. stops: [(y_logical, (r,g,b)), ...]"""
    W, H = max(1, int(round(w * k))), max(1, int(round(h * k)))
    ys = np.arange(H) / k
    cols = np.stack([np.interp(ys, [p for p, _ in stops], [c[i] for _, c in stops]) for i in range(3)], -1)
    arr = np.repeat(cols[:, None, :], W, axis=1).astype(np.uint8)
    return Image.fromarray(arr, "RGB").convert("RGBA")


def noise_tex(size, cell, seed, lo=0.86, hi=1.1):
    """Mottled texture multiplier (H, W) in [lo, hi]."""
    W, H = size
    rs = np.random.RandomState(seed)
    small = rs.rand(max(2, H // cell + 2), max(2, W // cell + 2))
    im = Image.fromarray((small * 255).astype(np.uint8), "L").resize((W, H), Image.BICUBIC)
    fine = rs.rand(H, W) * 0.35 + 0.65
    a = np.asarray(im, dtype=np.float32) / 255.0 * 0.75 + fine * 0.25
    return lo + (hi - lo) * a


def textured(im, tex):
    """Multiply the RGB of an RGBA image by a (H, W) texture."""
    arr = np.asarray(im).astype(np.float32)
    arr[..., :3] = np.clip(arr[..., :3] * tex[..., None], 0, 255)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def catenary(x0, y0, x1, y1, sag, n=40):
    pts = []
    for i in range(n + 1):
        u = i / float(n)
        pts.append((x0 + (x1 - x0) * u, y0 + (y1 - y0) * u + sag * 4 * u * (1 - u)))
    return pts


def along(pts, step):
    """Points every `step` units along a polyline."""
    out, acc = [], 0.0
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        L = math.hypot(bx - ax, by - ay)
        while acc <= L:
            u = acc / L if L else 0
            out.append((ax + (bx - ax) * u, ay + (by - ay) * u))
            acc += step
        acc -= L
    return out


def toward(p, vp, f):
    """Move point p a fraction f of the way to the vanishing point (= push it back in depth)."""
    return (p[0] + (vp[0] - p[0]) * f, p[1] + (vp[1] - p[1]) * f)


def lerp2(a, b, u):
    return (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)


def quad_pt(q, u, v):
    """Point inside quad q = (tl, tr, br, bl) at u (left->right), v (top->bottom)."""
    top = lerp2(q[0], q[1], u)
    bot = lerp2(q[3], q[2], u)
    return lerp2(top, bot, v)


def sub_quad(q, u0, v0, u1, v1):
    return [quad_pt(q, u0, v0), quad_pt(q, u1, v0), quad_pt(q, u1, v1), quad_pt(q, u0, v1)]


def fill_tex(cv, pts, stops, seed=1, cell=24, lo=0.9, hi=1.07, axis="y"):
    """Fill a polygon with a gradient (stops along y or x, logical units) times a mottled texture."""
    k = cv.k
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, y0 = max(0, int(min(xs) * k)), max(0, int(min(ys) * k))
    x1, y1 = min(cv.im.width, int(max(xs) * k) + 1), min(cv.im.height, int(max(ys) * k) + 1)
    if x1 <= x0 or y1 <= y0:
        return
    W, H = x1 - x0, y1 - y0
    if isinstance(stops, tuple):
        stops = [(-1e5, stops), (1e5, stops)]
    if axis == "y":
        pos = (np.arange(H) + y0) / k
    else:
        pos = (np.arange(W) + x0) / k
    cols = np.stack([np.interp(pos, [p for p, _ in stops], [c[i] for _, c in stops]) for i in range(3)], -1)
    arr = np.repeat(cols[:, None, :], W, axis=1) if axis == "y" else np.repeat(cols[None, :, :], H, axis=0)
    if hi != lo:
        arr = arr * noise_tex((W, H), max(3, int(cell * k)), seed, lo, hi)[..., None]
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).polygon([(x * k - x0, y * k - y0) for x, y in pts], fill=255)
    cv.im.paste(im, (x0, y0), mask)
    cv.d = ImageDraw.Draw(cv.im)


def quad_image(cv, img, quad):
    """Warp an RGBA image (a signboard, a poster...) onto quad = (tl, tr, br, bl) in logical units."""
    k = cv.k
    dst = [(x * k, y * k) for x, y in quad]
    xs, ys = [p[0] for p in dst], [p[1] for p in dst]
    x0, y0 = int(math.floor(min(xs))), int(math.floor(min(ys)))
    w, h = int(math.ceil(max(xs))) - x0 + 1, int(math.ceil(max(ys))) - y0 + 1
    src = [(0, 0), (img.width, 0), (img.width, img.height), (0, img.height)]
    A, B = [], []
    for (X, Y), (u, v) in zip([(x - x0, y - y0) for x, y in dst], src):
        A.append([X, Y, 1, 0, 0, 0, -u * X, -u * Y])
        B.append(u)
        A.append([0, 0, 0, X, Y, 1, -v * X, -v * Y])
        B.append(v)
    coeffs = np.linalg.solve(np.array(A, float), np.array(B, float))
    warped = img.transform((w, h), Image.PERSPECTIVE, tuple(coeffs), Image.BICUBIC)
    cx0, cy0 = max(0, -x0), max(0, -y0)
    warped = warped.crop((cx0, cy0, min(w, cv.im.width - x0), min(h, cv.im.height - y0)))
    if warped.width > 0 and warped.height > 0:
        cv.im.alpha_composite(warped, dest=(x0 + cx0, y0 + cy0))
    cv.d = ImageDraw.Draw(cv.im)


def sign_image(text, bg, fg, w=900, h=180, border=(40, 30, 30)):
    """Flat signboard image (to be warped with quad_image)."""
    from ..text import font
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=int(h * 0.12), fill=bg + (255,), outline=border + (255,),
                        width=max(3, h // 20))
    size = int(h * 0.56)
    f = font(size)
    while f.getlength(text) > w * 0.9 and size > 10:
        size -= 2
        f = font(size)
    tw = f.getlength(text)
    d.text(((w - tw) / 2, (h - size * 1.15) / 2), text, font=f, fill=fg + (255,))
    return im


def steam(sources, k, n=7, color=(250, 250, 250)):
    """fn for a dynamic layer: puffs of steam rising from sources [(x, y, size, speed), ...]."""
    def fn(_im, t):
        cv = Cv(k, fill=color + (0,))
        for (x, y, sz, sp) in sources:
            for i in range(n):
                ph = (t * sp + i / float(n)) % 1.0
                px = x + math.sin(t * 1.7 + i * 2.1) * 10 * sz * ph
                py = y - ph * 150 * sz
                r = (7 + 26 * ph) * sz
                cv.ell(px, py, r, r * 0.9, color + (int(130 * (1 - ph) * min(1.0, ph * 6)),))
        cv.blur(5)
        return cv.im
    return fn


def motes(region, k, n=46, seed=3):
    """fn for a dynamic (screen) layer: dust specks floating in a light beam. region = (p_from, p_to, width)."""
    rnd = random.Random(seed)
    parts = [(rnd.random(), rnd.uniform(-0.5, 0.5), rnd.uniform(0, 6.28), rnd.uniform(0.6, 1.6)) for _ in range(n)]
    (ax, ay), (bx, by), wid = region

    def fn(_im, t):
        cv = Cv(k, fill=(255, 240, 200, 0))
        for (u, v, ph, sz) in parts:
            uu = (u + t * 0.012 * sz) % 1.0
            x = ax + (bx - ax) * uu + v * wid + math.sin(t * 0.7 + ph) * 12
            y = ay + (by - ay) * uu + math.cos(t * 0.5 + ph) * 10
            a = int(170 * (0.5 + 0.5 * math.sin(t * 1.3 + ph * 3)))
            cv.ell(x, y, 2.2 * sz, 2.2 * sz, (255, 246, 214, a))
        cv.blur(0.6)
        return cv.im
    return fn


def birds(k, n=6, seed=8, y0=420, y1=760):
    """fn for a dynamic sky layer: a few birds gliding/flapping across."""
    rnd = random.Random(seed)
    fl = [(rnd.uniform(0, 1), rnd.uniform(y0, y1), rnd.uniform(18, 32), rnd.uniform(0.6, 1.2), rnd.uniform(0, 6.28))
          for _ in range(n)]

    def fn(im, t):
        out = im.copy()
        cv = Cv(k, fill=(40, 30, 40, 0))
        for (u, y, w, sp, ph) in fl:
            x = ((u + t * 0.018 * sp) % 1.2) * LW * 1.0 - 60
            flap = math.sin(t * 7 * sp + ph)
            yy = y + math.sin(t * 0.8 + ph) * 8
            cv.line([(x - w, yy - 6 * flap), (x - w * 0.4, yy - 2 - 4 * flap), (x, yy + 2),
                     (x + w * 0.4, yy - 2 - 4 * flap), (x + w, yy - 6 * flap)], (46, 34, 44, 230), 3.2)
        out.alpha_composite(cv.im)
        return out
    return fn


class Sprite:
    """A piece of the set that must be depth-sorted with the characters (e.g. a tea stall counter a
    character can stand behind). im covers the logical rect starting at (x0, y0) at k px per unit."""

    def __init__(self, im, k, x0, y0, ground_y, name=""):
        self.im, self.k, self.x0, self.y0, self.ground_y, self.name = im, k, x0, y0, ground_y, name


# ------------------------------------------------------------------ layer stack
class Layer:
    def __init__(self, im, k, d, fn=None, name="", mode="normal"):
        self.im, self.k, self.d, self.fn, self.name, self.mode = im, k, d, fn, name, mode
        self._cache_key = None
        self._cache = None

    def image_at(self, t):
        return self.fn(self.im, t) if self.fn else self.im


class Layered:
    """Holds back layers (behind characters) and front layers (d > 1, in front of characters)."""

    def __init__(self, back, front, light=None, horizon=None, ground=None, sprites=None):
        self.back, self.front = back, front
        self.light = light or {}
        self.horizon = horizon
        self.ground = ground
        self.sprites = sprites or []

    @staticmethod
    def _part(ly, t, view, W, H):
        z, L, T = view
        zl = max(1.0, 1.0 + (z - 1.0) * ly.d)
        cx, cy = L + LW / (2.0 * z), T + LH / (2.0 * z)
        clx, cly = LW / 2.0 + (cx - LW / 2.0) * ly.d, LH / 2.0 + (cy - LH / 2.0) * ly.d
        vw, vh = LW / zl, LH / zl
        l = clamp(clx - vw / 2.0, 0, LW - vw)
        tp = clamp(cly - vh / 2.0, 0, LH - vh)
        key = (round(l, 2), round(tp, 2), round(vw, 3))
        if ly.fn is None and ly._cache_key == key:
            return ly._cache
        k = ly.k
        im = ly.image_at(t)
        box = (l * k, tp * k, min(im.width, (l + vw) * k), min(im.height, (tp + vh) * k))
        part = im.resize((W, H), Image.BILINEAR, box=box)
        if ly.fn is None:
            ly._cache_key, ly._cache = key, part
        return part

    def compose(self, t, view, W, H, layers=None, base=None):
        out = base
        for ly in (self.back if layers is None else layers):
            part = self._part(ly, t, view, W, H)
            if out is None:
                out = part.copy()
            elif ly.mode == "screen":         # lights add brightness instead of painting over
                prem = Image.composite(part.convert("RGB"), Image.new("RGB", part.size, 0), part.getchannel("A"))
                out = ImageChops.screen(out.convert("RGB"), prem).convert("RGBA")
            else:
                out.alpha_composite(part)
        return out


def twinkle(groups, speed=0.9, static=None):
    """fn for a glow layer whose alpha breathes (two interleaved groups of bulbs)."""
    a_img, b_img = groups

    def fn(_im, t):
        u = 0.5 + 0.5 * math.sin(2 * math.pi * speed * t)
        fa, fb = 0.55 + 0.45 * u, 0.55 + 0.45 * (1 - u)
        out = static.copy() if static is not None else Image.new("RGBA", a_img.size, (255, 190, 110, 0))
        aa = a_img.copy()
        aa.putalpha(a_img.getchannel("A").point(lambda v: int(v * fa)))
        out.alpha_composite(aa)
        bb = b_img.copy()
        bb.putalpha(b_img.getchannel("A").point(lambda v: int(v * fb)))
        out.alpha_composite(bb)
        return out
    return fn


# ------------------------------------------------------------------ Diwali rooftop
PAL_BULB = [(255, 214, 120), (255, 236, 170), (255, 170, 90), (255, 120, 150), (140, 220, 255), (170, 255, 150)]


def _fireworks(sky_im, k):
    rnd = random.Random(11)
    bursts = []
    tt = 0.3
    while tt < 120:
        bursts.append(dict(t=tt, x=rnd.uniform(120, 960), y=rnd.uniform(180, 640),
                           col=rnd.choice([(255, 210, 90), (255, 110, 140), (120, 220, 255), (180, 255, 140),
                                           (255, 160, 70), (230, 150, 255)]),
                           n=rnd.randint(26, 40), r=rnd.uniform(90, 150), seed=rnd.randint(0, 9999)))
        tt += rnd.uniform(0.9, 1.9)

    def fn(im, t):
        live = [b for b in bursts if 0 <= t - b["t"] < 1.7]
        if not live:
            return im
        fw = Cv(k, fill=(255, 220, 160, 0))
        for b in live:
            age = t - b["t"]
            e = 1 - (1 - min(1.0, age / 0.9)) ** 3
            fade = clamp(1.0 - (age - 0.5) / 1.2)
            r = b["r"] * e
            rr = random.Random(b["seed"])
            if age < 0.35:
                fw.glow(b["x"], b["y"], 120 * (1 - age / 0.35) + 30, b["col"], int(150 * (1 - age / 0.35)))
            for i in range(b["n"]):
                a = 2 * math.pi * i / b["n"] + rr.uniform(-0.08, 0.08)
                rj = r * rr.uniform(0.82, 1.0)
                drop = 40 * age * age
                px, py = b["x"] + rj * math.cos(a), b["y"] + rj * math.sin(a) + drop
                qx, qy = b["x"] + rj * 0.72 * math.cos(a), b["y"] + rj * 0.72 * math.sin(a) + drop * 0.7
                al = int(255 * fade)
                fw.line([(qx, qy), (px, py)], b["col"] + (int(al * 0.7),), 2.6)
                fw.ell(px, py, 3.6, 3.6, mix(b["col"], (255, 255, 240), 0.45) + (al,))
        fw.blur(1.2)
        out = im.copy()
        out.alpha_composite(fw.im)
        return out
    return fn


def _sky(k):
    sky = Cv(k)
    sky.im = vgrad(k, [(0, (6, 8, 30)), (520, (20, 22, 66)), (900, (56, 42, 96)), (1080, (124, 70, 92)),
                       (1300, (150, 84, 80)), (LH, (150, 84, 80))])
    sky.d = ImageDraw.Draw(sky.im)
    rnd = random.Random(5)
    for _ in range(170):
        x, y = rnd.uniform(0, LW), rnd.uniform(0, 860)
        r = rnd.choice((1.2, 1.4, 1.8, 2.4))
        a = int(rnd.uniform(90, 255) * (1 - y / 1100.0))
        sky.ell(x, y, r, r, (255, 248, 225, a))
    g = Cv(k, fill=(255, 150, 90, 0))
    g.ell(540, 1080, 820, 220, (255, 140, 90, 70))
    g.blur(80)
    sky.over(g)
    return sky


def _far_city(k):
    cv = Cv(k, fill=(40, 36, 70, 0))
    bok = Cv(k, fill=(255, 200, 120, 0))
    rnd = random.Random(21)
    x = -30.0
    while x < LW + 30:
        w = rnd.uniform(70, 150)
        top = rnd.uniform(800, 940)
        col = mix((40, 34, 70), (64, 50, 92), rnd.random())
        cv.rect(x, top, x + w, 1300, col + (255,))
        cv.rect(x - 3, top - 7, x + w + 3, top, mul(col, 1.18) + (255,))
        if rnd.random() < 0.45:
            tx = x + rnd.uniform(8, w - 34)
            cv.rect(tx, top - 30, tx + 26, top - 7, mul(col, 0.75) + (255,))
        wy = top + 20
        while wy < 1180:
            wx = x + 10
            while wx < x + w - 18:
                if rnd.random() < 0.36:
                    wc = rnd.choice([(255, 206, 128), (255, 226, 160), (255, 180, 100), (240, 240, 255)])
                else:
                    wc = mul(col, 0.7)
                cv.rect(wx, wy, wx + 12, wy + 16, wc + (255,))
                wx += 25
            wy += 33
        # festive lights: string along the top + a few vertical "jhalar" strands
        c = rnd.choice(PAL_BULB)
        for (bx, by) in along([(x, top - 3), (x + w, top - 3)], 13):
            bok.ell(bx, by, 4.2, 4.2, c + (230,))
        if rnd.random() < 0.6:
            for sx in np.arange(x + 10, x + w - 6, rnd.uniform(14, 22)):
                L = rnd.uniform(90, 260)
                c2 = rnd.choice(PAL_BULB)
                for (bx, by) in along([(sx, top), (sx, top + L)], 11):
                    bok.ell(bx, by, 3.4, 3.4, c2 + (220,))
        x += w + rnd.uniform(-12, 4)
    # mobile tower with a red light
    cv.line([(820, 940), (836, 700), (852, 940)], (30, 28, 50, 255), 5)
    bok.ell(836, 700, 6, 6, (255, 70, 70, 255))
    cv.blur(2.2)
    # atmospheric haze: push toward the sky colour
    arr = np.asarray(cv.im).astype(np.float32)
    arr[..., :3] = arr[..., :3] * 0.72 + np.array([92, 64, 110], np.float32) * 0.28
    cv.im = Image.fromarray(arr.astype(np.uint8), "RGBA")
    bglow = bok.im.filter(ImageFilter.GaussianBlur(9 * k))
    bok.blur(1.1)
    cv.im.alpha_composite(bglow)
    cv.im.alpha_composite(bok.im)
    return cv


def _mid_buildings(k):
    cv = Cv(k, fill=(50, 40, 70, 0))
    bok = Cv(k, fill=(255, 200, 120, 0))

    def building(x0, x1, top, col, win=(34, 44), gap=(26, 34), seed=0):
        r = random.Random(seed)
        cv.rect(x0, top, x1, 1400, col + (255,))
        cv.rect(x0 - 6, top - 10, x1 + 6, top, mul(col, 1.2) + (255,))
        # balcony slabs every floor
        fy = top + 30
        while fy < 1250:
            wx = x0 + 22
            while wx < x1 - win[0] - 10:
                lit = r.random() < 0.5
                wc = r.choice([(255, 200, 120), (255, 222, 150), (255, 176, 96)]) if lit else mul(col, 0.62)
                cv.rect(wx - 4, fy - 4, wx + win[0] + 4, fy + win[1] + 4, mul(col, 0.8) + (255,))
                cv.rect(wx, fy, wx + win[0], fy + win[1], wc + (255,))
                cv.line([(wx + win[0] / 2, fy), (wx + win[0] / 2, fy + win[1])], mul(col, 0.7) + (255,), 3)
                wx += win[0] + gap[0]
            cv.rect(x0, fy + win[1] + 12, x1, fy + win[1] + 20, mul(col, 1.15) + (255,))
            fy += win[1] + gap[1] + 20
        # jhalar strands down the facade
        c = r.choice(PAL_BULB)
        xs = np.arange(x0 + 14, x1 - 8, 26)
        for i, sx in enumerate(xs):
            L = 170 + 60 * math.sin(i * 0.9) + r.uniform(0, 80)
            cc = PAL_BULB[(i + seed) % len(PAL_BULB)] if r.random() < 0.5 else c
            for (bx, by) in along([(sx, top + 4), (sx, top + 4 + L)], 15):
                bok.ell(bx, by, 4.6, 4.6, cc + (235,))
        for (bx, by) in along(catenary(x0, top - 2, x1, top - 2, 24), 16):
            bok.ell(bx, by, 5, 5, c + (240,))

    building(-40, 270, 600, (58, 46, 80), seed=1)
    building(330, 520, 860, (66, 50, 86), win=(28, 36), seed=2)
    building(640, 900, 690, (54, 44, 78), seed=3)
    # a small temple top on the far right
    cv.poly([(930, 900), (975, 760), (1020, 900)], (70, 54, 88, 255))
    cv.rect(915, 900, 1035, 1100, (64, 50, 84, 255))
    bok.ell(975, 752, 7, 7, (255, 220, 140, 255))
    for (bx, by) in along([(930, 900), (975, 762), (1020, 900)], 14):
        bok.ell(bx, by, 4, 4, (255, 210, 120, 230))
    cv.blur(1.3)
    arr = np.asarray(cv.im).astype(np.float32)
    arr[..., :3] = arr[..., :3] * 0.86 + np.array([90, 62, 104], np.float32) * 0.14
    cv.im = Image.fromarray(arr.astype(np.uint8), "RGBA")
    bglow = bok.im.filter(ImageFilter.GaussianBlur(12 * k))
    bok.blur(0.9)
    cv.im.alpha_composite(bglow)
    cv.im.alpha_composite(bok.im)
    return cv


def _diya(cv, x, y, s=1.0, glow=None, grp=None):
    """Clay diya standing on y (bottom), with flame. Glow goes to the given glow canvas."""
    cv.poly([(x - 24 * s, y - 16 * s), (x + 24 * s, y - 16 * s), (x + 16 * s, y - 2 * s), (x - 16 * s, y - 2 * s)],
            (176, 84, 42, 255), (40, 20, 14, 255), 3 * s)
    cv.ell(x, y - 16 * s, 24 * s, 6 * s, (120, 54, 30, 255), (40, 20, 14, 255), 2.5 * s)
    cv.poly([(x + 14 * s, y - 20 * s), (x + 30 * s, y - 22 * s), (x + 22 * s, y - 14 * s)], (176, 84, 42, 255))
    fx, fy = x + 20 * s, y - 24 * s
    cv.poly([(fx, fy - 30 * s), (fx + 8 * s, fy - 8 * s), (fx, fy), (fx - 8 * s, fy - 8 * s)], (255, 170, 60, 255))
    cv.poly([(fx, fy - 18 * s), (fx + 4 * s, fy - 6 * s), (fx, fy - 2 * s), (fx - 4 * s, fy - 6 * s)],
            (255, 248, 210, 255))
    if glow is not None:
        glow.glow(fx, fy - 10 * s, 120 * s, (255, 170, 80), 150)
        glow.glow(fx, fy - 10 * s, 36 * s, (255, 230, 170), 180)


def _rooftop(k, kg):
    """The rooftop the characters stand on (d = 1). Returns (layer canvas, glowA, glowB, static glow)."""
    cv = Cv(k, blend=True)
    gA = Cv(kg, fill=(255, 190, 110, 0))
    gB = Cv(kg, fill=(255, 190, 110, 0))
    gS = Cv(kg, fill=(255, 190, 110, 0))
    rnd = random.Random(7)
    WALL_TOP, WALL_BOT = 1062, 1218

    # ---- floor ----
    floor = vgrad(k, [(0, (150, 112, 102)), (WALL_BOT, (150, 112, 102)), (1500, (118, 92, 100)),
                      (LH, (74, 66, 86))])
    tex = noise_tex(floor.size, max(4, int(30 * k)), 3, 0.88, 1.08)
    floor = textured(floor, tex)
    mask = Image.new("L", floor.size, 0)
    ImageDraw.Draw(mask).rectangle([0, WALL_BOT * k, floor.width, floor.height], fill=255)
    cv.im.paste(floor, (0, 0), mask)
    cv.d = ImageDraw.Draw(cv.im)
    vp = (540, 760)
    for x in range(-1400, 2600, 190):          # perspective joints
        y1 = LH
        x1 = vp[0] + (x - vp[0]) * (y1 - vp[1]) / (WALL_BOT - vp[1])
        cv.line([(x, WALL_BOT), (x1, y1)], (60, 48, 62, 70), 3)
    for yy in (1290, 1395, 1545, 1760):
        cv.line([(0, yy), (LW, yy)], (60, 48, 62, 60), 3)
    for _ in range(9):                          # cracker paper bits
        bx, by = rnd.uniform(60, 1020), rnd.uniform(1300, 1880)
        a = rnd.uniform(0, math.pi)
        L = rnd.uniform(10, 18)
        cv.poly([(bx + L * math.cos(a) - 5 * math.sin(a), by + L * math.sin(a) * 0.5 + 5 * math.cos(a)),
                 (bx + L * math.cos(a) + 5 * math.sin(a), by + L * math.sin(a) * 0.5 - 5 * math.cos(a)),
                 (bx - L * math.cos(a) + 5 * math.sin(a), by - L * math.sin(a) * 0.5 - 5 * math.cos(a)),
                 (bx - L * math.cos(a) - 5 * math.sin(a), by - L * math.sin(a) * 0.5 + 5 * math.cos(a))],
                (200, 50, 46, 255), (60, 20, 20, 255), 2)

    # rangoli (in perspective) in the front
    rcx, rcy, rx, ry = 430, 1858, 210, 58
    for i, (f, col) in enumerate([(1.0, (230, 70, 90)), (0.82, (255, 190, 60)), (0.64, (80, 170, 220)),
                                  (0.46, (250, 120, 40)), (0.28, (255, 240, 220)), (0.14, (220, 60, 120))]):
        cv.ell(rcx, rcy, rx * f, ry * f, col + (235,))
    for i in range(12):
        a = 2 * math.pi * i / 12
        px, py = rcx + rx * 0.9 * math.cos(a), rcy + ry * 0.9 * math.sin(a)
        cv.ell(px, py, 22, 7, (255, 255, 240, 230))

    # ---- parapet wall ----
    wall = vgrad(k, [(0, (176, 136, 124)), (WALL_TOP, (176, 136, 124)), (WALL_BOT, (128, 98, 102)),
                     (LH, (128, 98, 102))])
    wall = textured(wall, noise_tex(wall.size, max(4, int(18 * k)), 9, 0.84, 1.1))
    wm = Image.new("L", wall.size, 0)
    ImageDraw.Draw(wm).rectangle([0, WALL_TOP * k, wall.width, WALL_BOT * k], fill=255)
    cv.im.paste(wall, (0, 0), wm)
    cv.d = ImageDraw.Draw(cv.im)
    for _ in range(14):                          # rain stains
        sx = rnd.uniform(0, LW)
        cv.rect(sx, WALL_TOP + 22, sx + rnd.uniform(6, 22), WALL_TOP + rnd.uniform(60, 140), (110, 84, 88, 60))
    cv.rect(-10, WALL_TOP - 20, LW + 10, WALL_TOP + 4, (198, 160, 146, 255), (70, 50, 54, 255), 2)
    cv.rect(-10, WALL_TOP + 4, LW + 10, WALL_TOP + 14, (96, 72, 80, 160))
    cv.rect(-10, WALL_BOT - 4, LW + 10, WALL_BOT + 8, (80, 62, 72, 200))

    # ---- stairwell room (mumty) on the right with an open, lit door ----
    RX = 846
    room = vgrad(k, [(0, (170, 128, 118)), (560, (170, 128, 118)), (WALL_BOT, (140, 104, 104)),
                     (LH, (140, 104, 104))])
    room = textured(room, noise_tex(room.size, max(4, int(22 * k)), 13, 0.86, 1.1))
    rm = Image.new("L", room.size, 0)
    ImageDraw.Draw(rm).rectangle([RX * k, 560 * k, room.width, WALL_BOT * k], fill=255)
    cv.im.paste(room, (0, 0), rm)
    cv.d = ImageDraw.Draw(cv.im)
    cv.rect(RX - 40, 530, LW + 10, 566, (196, 156, 142, 255), (70, 50, 54, 255), 2)
    cv.rect(RX - 40, 566, LW + 10, 580, (90, 66, 74, 170))
    cv.line([(RX, 580), (RX, WALL_BOT)], (100, 74, 80, 255), 4)
    # door opening with warm light inside
    dx0, dx1, dy0 = 900, 1040, 800
    inside = vgrad(k, [(0, (255, 214, 150)), (dy0, (255, 214, 150)), (WALL_BOT, (232, 150, 90)), (LH, (232, 150, 90))])
    dm = Image.new("L", inside.size, 0)
    ImageDraw.Draw(dm).rectangle([dx0 * k, dy0 * k, dx1 * k, WALL_BOT * k], fill=255)
    cv.im.paste(inside, (0, 0), dm)
    cv.d = ImageDraw.Draw(cv.im)
    cv.poly([(dx0 + 20, dy0 + 60), (dx0 + 70, dy0 + 140), (dx0 + 70, WALL_BOT), (dx0 + 20, WALL_BOT)],
            (210, 120, 70, 140))         # stairs shadow inside
    cv.rect(dx0 - 12, dy0 - 12, dx1 + 12, WALL_BOT, None, (78, 46, 32, 255), 12)
    cv.poly([(dx0 - 6, dy0), (dx0 - 70, dy0 + 30), (dx0 - 70, WALL_BOT + 26), (dx0 - 6, WALL_BOT)],
            (122, 70, 42, 255), (54, 30, 20, 255), 4)       # door leaf swung open
    cv.line([(dx0 - 56, dy0 + 200), (dx0 - 56, dy0 + 240)], (220, 180, 90, 255), 5)
    # light spill on the floor + bulb over the door
    spill = Cv(k * 0.25, fill=(255, 190, 110, 0))
    spill.poly([(dx0, WALL_BOT), (dx1, WALL_BOT), (dx1 - 40, 1560), (dx0 - 260, 1560)], (255, 196, 120, 90))
    spill.blur(30)
    cv.over(spill)
    cv.rect(960, 770, 980, 780, (60, 50, 50, 255))
    cv.ell(970, 790, 11, 13, (255, 246, 210, 255))
    gS.glow(970, 790, 210, (255, 200, 120), 170)
    gS.glow(970, 1000, 260, (255, 190, 110), 70)

    # ---- bamboo pole + paper lantern (akash kandil) on the left ----
    PX = 70
    cv.line([(PX, WALL_TOP - 14), (PX - 6, 470)], (60, 40, 30, 255), 16)
    cv.line([(PX, WALL_TOP - 14), (PX - 6, 470)], (150, 110, 64, 255), 10)
    for yy in (600, 760, 920):
        cv.line([(PX - 8, yy), (PX + 6, yy)], (90, 62, 38, 255), 4)
    cv.line([(PX - 4, 520), (PX + 110, 512)], (120, 86, 52, 255), 7)
    LX, LY = PX + 104, 660
    cv.line([(LX, 514), (LX, LY - 66)], (40, 30, 26, 255), 2)
    star = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        r = 66 if i % 2 == 0 else 30
        star.append((LX + r * math.cos(a), LY + r * math.sin(a)))
    cv.poly(star, (236, 84, 52, 255), (90, 30, 20, 255), 4)
    inner = [(LX + (x - LX) * 0.55, LY + (y - LY) * 0.55) for x, y in star]
    cv.poly(inner, (255, 196, 92, 255))
    cv.ell(LX, LY, 14, 14, (255, 244, 200, 255))
    for i, tx in enumerate((-26, -12, 2, 16, 30)):
        L = 120 + 20 * math.sin(i * 1.7)
        cv.line([(LX + tx * 0.6, LY + 28), (LX + tx, LY + 28 + L)], (240, 120, 60, 255) if i % 2 else (255, 210, 90, 255), 6)
    gS.glow(LX, LY, 240, (255, 140, 70), 160)
    gS.glow(LX, LY, 80, (255, 220, 150), 170)

    # ---- fairy lights from the pole to the stairwell ----
    strings = [catenary(PX - 4, 540, RX - 30, 600, 150), catenary(PX - 4, 560, -40, 640, 40),
               catenary(PX - 2, 900, RX, 980, 50)]
    bi = 0
    for pts in strings:
        cv.line(pts, (30, 30, 26, 255), 2.5)
        for (bx, by) in along(pts, 30):
            col = PAL_BULB[bi % len(PAL_BULB)] if bi % 3 else (255, 220, 140)
            cv.ell(bx, by + 5, 6.5, 8, col + (255,))
            cv.ell(bx - 1.5, by + 3, 2.5, 3, (255, 255, 245, 255))
            g = gA if bi % 2 else gB
            g.glow(bx, by + 5, 46, col, 120)
            bi += 1

    # ---- plants + tulsi planter by the wall ----
    def pot(x, y, h=70, w=58, col=(180, 86, 50)):
        cv.poly([(x - w / 2, y - h), (x + w / 2, y - h), (x + w * 0.36, y), (x - w * 0.36, y)], col + (255,),
                (50, 24, 16, 255), 3)
        cv.rect(x - w / 2 - 5, y - h - 12, x + w / 2 + 5, y - h, mul(col, 1.1) + (255,), (50, 24, 16, 255), 3)
        return y - h - 10

    def leaves(x, y, n, spread, size, col, seed):
        r = random.Random(seed)
        for i in range(n):
            a = -math.pi / 2 + r.uniform(-spread, spread)
            L = r.uniform(0.4, 1.0) * size * 2.2
            ex, ey = x + L * math.cos(a), y + L * math.sin(a)
            cv.line([(x, y), (ex, ey)], (50, 80, 40, 255), 3)
            ang = math.degrees(a)
            lw, lh = size * 0.55, size * 0.24
            pts = []
            for j in range(16):
                b = 2 * math.pi * j / 16
                px_, py_ = lw * math.cos(b), lh * math.sin(b)
                ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
                pts.append((ex + px_ * ca - py_ * sa, ey + px_ * sa + py_ * ca))
            cv.poly(pts, mix(col, (120, 170, 80), r.random() * 0.5) + (255,), (30, 50, 24, 255), 2)

    top = pot(250, WALL_BOT + 6, 74, 62)
    leaves(250, top, 14, 1.0, 36, (70, 130, 60), 3)
    # tulsi vrindavan (square planter)
    tx = 690
    cv.rect(tx - 50, WALL_BOT - 100, tx + 50, WALL_BOT + 8, (226, 196, 170, 255), (80, 56, 50, 255), 3)
    cv.rect(tx - 60, WALL_BOT - 116, tx + 60, WALL_BOT - 100, (236, 206, 180, 255), (80, 56, 50, 255), 3)
    cv.poly([(tx - 18, WALL_BOT - 70), (tx, WALL_BOT - 88), (tx + 18, WALL_BOT - 70), (tx, WALL_BOT - 52)],
            (220, 70, 60, 255))
    leaves(tx, WALL_BOT - 116, 18, 1.1, 26, (60, 120, 54), 8)

    # ---- diyas on the parapet ----
    for i, x in enumerate((140, 300, 450, 590, 760)):
        _diya(cv, x, WALL_TOP - 20, 1.0, gA if i % 2 else gB)
    for x in (260, 640):
        _diya(cv, x - 60, WALL_BOT + 22, 1.15, gS)
    # warm wash on the wall below the diyas
    for x in (140, 300, 450, 590, 760):
        gS.glow(x + 20, WALL_TOP + 50, 120, (255, 170, 90), 60)
    gS.glow(640, WALL_BOT + 80, 400, (255, 170, 100), 40)
    cv.blur(0.35)
    for g in (gA, gB):
        g.blur(7)
    gS.blur(16)
    return cv, gA, gB, gS


def _foreground(k):
    """Out-of-focus things very close to the lens (d > 1)."""
    cv = Cv(k, fill=(255, 170, 90, 0))
    g = Cv(k, fill=(255, 170, 90, 0))
    # big blurred diya + marigolds, bottom-left corner
    _diya(cv, 40, 1990, 3.2, g)
    for i, (mx, my) in enumerate(((170, 1930), (210, 1985), (130, 1975), (250, 1950))):
        cv.ell(mx, my, 34, 30, (255, 150 + 20 * (i % 2), 30, 255))
        cv.ell(mx, my, 18, 15, (240, 110, 20, 255))
    cv.blur(9)
    g.blur(14)
    cv.im.alpha_composite(g.im)
    return cv


def diwali_rooftop(s, zmax=1.0):
    kb = 0.5 * s                      # far layers are blurred anyway: low resolution is fine
    kr = s * max(1.0, zmax)           # the character plane stays sharp up to the max zoom
    kg = 0.32 * s
    sky = _sky(kb)
    far = _far_city(0.6 * s)
    mid = _mid_buildings(0.7 * s)
    roof, gA, gB, gS = _rooftop(kr, kg)
    stat = gS.im
    gA_im = gA.im
    gB_im = gB.im
    fg = _foreground(0.5 * s)
    back = [
        Layer(sky.im, kb, 0.0, _fireworks(sky.im, kb), "sky"),
        Layer(far.im, 0.6 * s, 0.12, None, "far"),
        Layer(mid.im, 0.7 * s, 0.32, None, "mid"),
        Layer(roof.im, kr, 1.0, None, "roof"),
        Layer(gA_im, kg, 1.0, twinkle((gA_im, gB_im), 0.8, static=stat), "roof_glow", mode="screen"),
    ]
    front = [Layer(fg.im, 0.5 * s, 1.35, None, "foreground")]
    light = {"ambient": [244, 224, 214], "dir": -1, "vignette": 0.42}
    return Layered(back, front, light=light, horizon=760, ground=1218)


def _lazy(module, fn_name):
    def build(s, zmax=1.0):
        import importlib
        return getattr(importlib.import_module("." + module, __package__), fn_name)(s, zmax)
    return build


PRESETS = {
    "diwali_rooftop": diwali_rooftop,
    "kitchen_25d": _lazy("scenery_kitchen", "kitchen_25d"),
    "gali_25d": _lazy("scenery_gali", "gali_25d"),
    "room_25d": _lazy("scenery_home", "room_25d"),
    "classroom_25d": _lazy("scenery_home", "classroom_25d"),
}


# ------------------------------------------------------------------ the studio's 2.5d set
SUNLIT = {"sunlight", "dust", "chalk dust"}         # light layers that come from the sun (they fade at night)


def _fade(im, f):
    out = im.copy()
    out.putalpha(im.getchannel("A").point(lambda v: int(v * f)))
    return out


class StudioBackdrop:
    """A 2.5D preset as the studio renderer uses it.

    The studio draws everything into a frame and then crops/zooms it for the camera. So every layer is
    painted into that frame *already corrected* for the camera: after the crop the floor layer (d = 1)
    lands exactly where the flat background would, while far layers zoom and slide less (parallax) and
    the blurred foreground (d > 1) more. view = dict(za, La, Ta, zc, vl, vt, mirror): the shot angle
    (zoom za, left/top in logical units) and the in-shot camera (zoom zc, crop window left/top in px).
    """

    def __init__(self, preset, out_w, out_h, zmax=1.0, time=None, grade=None, extra=None):
        self.preset = preset
        self.W, self.H = out_w, out_h
        self.s = out_w / float(LW)
        if preset.startswith("auto:"):              # any studio place, split into depth layers automatically
            from .autoset import build_auto
            self.layered = build_auto(preset[5:], self.s, zmax, time)
        else:
            self.layered = PRESETS[preset](self.s, zmax)
        for ly in extra or []:                      # e.g. the place's moving clouds / birds (far) and traffic (near)
            back = self.layered.back
            back.insert(next((i for i, b in enumerate(back) if b.d > ly.d), len(back)), ly)
        self._cache = {}
        self._sprite_cache = {}
        if time and grade:
            self._regrade(time, grade)
        sky = self.layered.back[0].im
        self.fill = sky.getpixel((0, 0))[:3] + (255,)

    @property
    def light(self):
        return self.layered.light

    def _regrade(self, time, grade):
        """Re-light the painted layers for another time of day; glowing lights (screen layers) stay bright."""
        def regrade(im):
            rgb = grade(im.convert("RGB"), time)
            rgb.putalpha(im.getchannel("A"))
            return rgb
        dark = time in ("night", "rain")
        for ly in self.layered.back + self.layered.front:
            if ly.mode != "screen" and ly.im.width > 8:
                ly.im = regrade(ly.im)
            elif ly.mode != "screen" and ly.fn is not None:          # moving parts (a ceiling fan) too
                ly.fn = (lambda fn: lambda im, t: regrade(fn(im, t)))(ly.fn)
            elif dark and ly.name in SUNLIT:                         # no sunbeam at night
                if ly.fn is not None:
                    ly.fn = (lambda fn: lambda im, t: _fade(fn(im, t), 0.18))(ly.fn)
                else:
                    ly.im = _fade(ly.im, 0.18)
        for sp in self.layered.sprites:
            sp.im = regrade(sp.im)

    def _total(self, view):
        za, zc = view["za"], max(1.0, view["zc"])
        Z = za * zc
        return Z, view["La"] + view["vl"] / (self.s * za), view["Ta"] + view["vt"] / (self.s * za)

    def _paste(self, canvas, ly, t, view, Z, L, T, V):
        zl = max(1.0, 1.0 + (Z - 1.0) * ly.d)
        cx, cy = L + LW / (2.0 * Z), T + LH / (2.0 * Z)
        clx, cly = LW / 2.0 + (cx - LW / 2.0) * ly.d, LH / 2.0 + (cy - LH / 2.0) * ly.d
        vwl, vhl = LW / zl, LH / zl
        Ll = clamp(clx - vwl / 2.0, 0, LW - vwl)
        Tl = clamp(cly - vhl / 2.0, 0, LH - vhl)
        zc = max(1.0, view["zc"])
        im = ly.image_at(t)
        k = ly.k
        a = zl * self.s / (zc * k)                     # frame px per layer px
        bx, by = V[0] - Ll * zl * self.s / zc, V[1] - Tl * zl * self.s / zc
        qx0, qy0 = max(0.0, -bx / a), max(0.0, -by / a)
        qx1, qy1 = min(float(im.width), (self.W - bx) / a), min(float(im.height), (self.H - by) / a)
        if qx1 - qx0 < 1 or qy1 - qy0 < 1:
            return
        dx0, dy0 = int(round(bx + qx0 * a)), int(round(by + qy0 * a))
        dx1, dy1 = int(round(bx + qx1 * a)), int(round(by + qy1 * a))
        if dx1 <= dx0 or dy1 <= dy0:
            return
        key = (id(ly), round(qx0, 1), round(qy0, 1), round(qx1, 1), round(qy1, 1), dx1 - dx0, dy1 - dy0)
        if ly.fn is None and key in self._cache:
            part = self._cache[key]
        else:
            part = im.resize((dx1 - dx0, dy1 - dy0), Image.BILINEAR, box=(qx0, qy0, qx1, qy1))
            if ly.fn is None:
                if len(self._cache) > 64:
                    self._cache.clear()
                self._cache[key] = part
        if ly.mode == "screen":                         # lights add brightness instead of painting over
            region = canvas.crop((dx0, dy0, dx1, dy1)).convert("RGB")
            prem = Image.composite(part.convert("RGB"), Image.new("RGB", part.size, 0), part.getchannel("A"))
            canvas.paste(ImageChops.screen(region, prem), (dx0, dy0))
        else:
            canvas.alpha_composite(part, dest=(dx0, dy0))

    def _canvas(self, layers, t, view, fill):
        Z, L, T = self._total(view)
        zc = max(1.0, view["zc"])
        vw = self.W / zc
        vx = self.W - view["vl"] - vw if view["mirror"] else view["vl"]
        canvas = Image.new("RGBA", (self.W, self.H), fill)
        for ly in layers:
            self._paste(canvas, ly, t, view, Z, L, T, (vx, view["vt"]))
        return ImageOps.mirror(canvas) if view["mirror"] else canvas

    def image(self, t, view):
        """The set behind the people, as an RGB frame (before the camera crop)."""
        return self._canvas(self.layered.back, t, view, self.fill).convert("RGB")

    def paste_front(self, img, t, view):
        """Blurred things right in front of the lens, over the people."""
        if self.layered.front:
            front = self._canvas(self.layered.front, t, view, (0, 0, 0, 0))
            img.paste(front, (0, 0), front)
        return img

    def floor_items(self, view):
        """Set pieces depth-sorted with the people (e.g. the chai counter): [(depth y, image, x, y)] in px."""
        out = []
        za = view["za"]
        for sp in self.layered.sprites:
            sc = self.s * za / sp.k
            key = (id(sp), round(sc, 4), view["mirror"])
            if key not in self._sprite_cache:
                im = sp.im.resize((max(1, int(round(sp.im.width * sc))), max(1, int(round(sp.im.height * sc)))),
                                  Image.BILINEAR)
                self._sprite_cache[key] = ImageOps.mirror(im) if view["mirror"] else im
            im = self._sprite_cache[key]
            x = (sp.x0 - view["La"]) * za * self.s
            y = (sp.y0 - view["Ta"]) * za * self.s
            if view["mirror"]:
                x = self.W - x - im.width
            out.append((sp.ground_y, im, int(round(x)), int(round(y))))
        return out

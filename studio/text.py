"""Text, captions, speech bubbles and emoji rendering (Pillow)."""
import functools
import glob
import math
import os

from PIL import Image, ImageDraw, ImageFont

from .util import ROOT

MAIN_FONTS = [
    os.path.join(ROOT, "assets", "fonts", "main.ttf"),
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
DEVA_FONTS = [
    os.path.join(ROOT, "assets", "fonts", "devanagari.ttf"),
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansDevanagari-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
    "/usr/share/fonts/truetype/lohit-devanagari/Lohit-Devanagari.ttf",
]
EMOJI_FONTS = [
    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
    "/usr/share/fonts/noto/NotoColorEmoji.ttf",
    "/usr/share/fonts/truetype/noto-color-emoji/NotoColorEmoji.ttf",
]


def _first(paths):
    for p in paths:
        if os.path.isfile(p):
            return p
    for p in paths:
        hits = glob.glob(p)
        if hits:
            return hits[0]
    return None


@functools.lru_cache(maxsize=64)
def font(size, kind="main"):
    size = max(8, int(round(size)))
    path = _first(DEVA_FONTS if kind == "deva" else MAIN_FONTS)
    if path is None:
        return ImageFont.load_default()
    return ImageFont.truetype(path, size)


def is_emoji(ch):
    o = ord(ch)
    return (o >= 0x1F000 or 0x2600 <= o <= 0x27BF or o in (0x2B50, 0x2B55, 0x2764, 0x203C, 0x2049)
            )


def is_deva(ch):
    return 0x0900 <= ord(ch) <= 0x097F


def runs(text):
    """Split into ('text'|'deva'|'emoji', str) runs. Variation selectors/ZWJ are dropped."""
    out = []
    for ch in text:
        if ord(ch) in (0xFE0F, 0x200D):
            continue
        kind = "emoji" if is_emoji(ch) else ("deva" if is_deva(ch) else "text")
        if out and out[-1][0] == kind and kind != "emoji":
            out[-1] = (kind, out[-1][1] + ch)
        else:
            out.append((kind, ch))
    return out


# ---------------------------------------------------------------- emoji
@functools.lru_cache(maxsize=64)
def emoji_image(ch, px):
    px = max(8, int(px))
    path = _first(EMOJI_FONTS)
    if path:
        try:
            f = ImageFont.truetype(path, 109)
            im = Image.new("RGBA", (136, 128), (0, 0, 0, 0))
            ImageDraw.Draw(im).text((0, 0), ch, font=f, embedded_color=True)
            bbox = im.getbbox()
            if bbox:
                im = im.crop(bbox)
                h = px
                w = max(1, int(im.width * h / im.height))
                return im.resize((w, h), Image.LANCZOS)
        except Exception:
            pass
    return _vector_emoji(ch, px)


def _vector_emoji(ch, px):
    """Tiny fallback when no colour-emoji font is installed."""
    SS = 4
    n = px * SS
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if ch in "❤\U0001F496\U0001F495":
        pts = []
        for i in range(60):
            t = 2 * math.pi * i / 60
            x = 16 * math.sin(t) ** 3
            y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
            pts.append((n / 2 + x * n / 36, n / 2 + y * n / 36 - n * 0.03))
        d.polygon(pts, fill=(224, 40, 60))
        return im.resize((px, px), Image.LANCZOS)
    d.ellipse([2, 2, n - 3, n - 3], fill=(255, 205, 60), outline=(200, 140, 20), width=SS)
    cx, cy = n / 2, n / 2
    if ch in "\U0001F602\U0001F923":      # laughing with tears
        for sx in (-1, 1):
            d.arc([cx + sx * n * 0.22 - n * 0.1, cy - n * 0.2, cx + sx * n * 0.22 + n * 0.1, cy], 200, 340,
                  fill=(60, 40, 20), width=SS * 2)
            d.ellipse([cx + sx * n * 0.32 - n * 0.06, cy - n * 0.02, cx + sx * n * 0.32 + n * 0.06, cy + n * 0.16],
                      fill=(110, 190, 240))
        d.pieslice([cx - n * 0.28, cy - n * 0.02, cx + n * 0.28, cy + n * 0.42], 0, 180, fill=(120, 40, 40))
    elif ch in "\U0001F62D\U0001F622":
        for sx in (-1, 1):
            d.ellipse([cx + sx * n * 0.22 - n * 0.05, cy - n * 0.15, cx + sx * n * 0.22 + n * 0.05, cy - n * 0.05],
                      fill=(60, 40, 20))
            d.rectangle([cx + sx * n * 0.22 - n * 0.03, cy, cx + sx * n * 0.22 + n * 0.03, cy + n * 0.3], fill=(110, 190, 240))
        d.arc([cx - n * 0.2, cy + n * 0.15, cx + n * 0.2, cy + n * 0.45], 200, 340, fill=(60, 40, 20), width=SS * 2)
    elif ch in "\U0001F621\U0001F620":
        d.ellipse([2, 2, n - 3, n - 3], fill=(236, 90, 60), outline=(150, 40, 30), width=SS)
        for sx in (-1, 1):
            d.line([cx + sx * n * 0.32, cy - n * 0.22, cx + sx * n * 0.1, cy - n * 0.12], fill=(60, 20, 20), width=SS * 2)
            d.ellipse([cx + sx * n * 0.2 - n * 0.04, cy - n * 0.08, cx + sx * n * 0.2 + n * 0.04, cy], fill=(60, 20, 20))
        d.arc([cx - n * 0.2, cy + n * 0.15, cx + n * 0.2, cy + n * 0.45], 200, 340, fill=(60, 20, 20), width=SS * 2)
    elif ch in "\U0001F631":
        for sx in (-1, 1):
            d.ellipse([cx + sx * n * 0.22 - n * 0.09, cy - n * 0.22, cx + sx * n * 0.22 + n * 0.09, cy - n * 0.02],
                      fill=(255, 255, 255), outline=(60, 40, 20), width=SS)
        d.ellipse([cx - n * 0.1, cy + n * 0.12, cx + n * 0.1, cy + n * 0.42], fill=(120, 40, 40))
    else:                                  # generic smile
        for sx in (-1, 1):
            d.ellipse([cx + sx * n * 0.2 - n * 0.05, cy - n * 0.2, cx + sx * n * 0.2 + n * 0.05, cy - n * 0.08],
                      fill=(60, 40, 20))
        d.arc([cx - n * 0.26, cy - n * 0.05, cx + n * 0.26, cy + n * 0.38], 20, 160, fill=(60, 40, 20), width=SS * 2)
    return im.resize((px, px), Image.LANCZOS)


# ---------------------------------------------------------------- text blocks
def _run_width(kind, s, size):
    if kind == "emoji":
        return size * 1.08 * len(s)
    return font(size, "deva" if kind == "deva" else "main").getlength(s)


def _line_width(text, size):
    return sum(_run_width(k, v, size) for k, v in runs(text))


def wrap(text, size, max_w):
    lines = []
    for para in str(text).split("\n"):
        words = para.split(" ")
        cur = ""
        for w in words:
            trial = (cur + " " + w).strip() if cur else w
            if cur and _line_width(trial, size) > max_w:
                lines.append(cur)
                cur = w
            else:
                cur = trial
        lines.append(cur)
    return lines


def text_block(text, size, max_w, fill=(15, 15, 15), stroke=0, stroke_fill=(0, 0, 0), line_gap=1.14,
               align="center", fit_lines=None):
    """Render wrapped text into a tight transparent RGBA image."""
    size = float(size)
    lines = wrap(text, size, max_w)
    # shrink to respect fit_lines or an over-wide single token
    guard = 0
    while guard < 12 and ((fit_lines and len(lines) > fit_lines) or
                          max(_line_width(l, size) for l in lines) > max_w * 1.02):
        size *= 0.92
        lines = wrap(text, size, max_w)
        guard += 1
    pad = int(stroke) + 2
    lh = int(size * line_gap)
    widths = [_line_width(l, size) for l in lines]
    W = int(max(widths)) + pad * 2 + 2
    H = lh * len(lines) + int(size * 0.35) + pad * 2
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, line in enumerate(lines):
        base = pad + int(size * 0.98) + i * lh
        if align == "center":
            x = (W - widths[i]) / 2.0
        elif align == "left":
            x = pad
        else:
            x = W - widths[i] - pad
        for kind, s in runs(line):
            if kind == "emoji":
                for ch in s:
                    e = emoji_image(ch, int(size * 1.0))
                    im.alpha_composite(e, (int(x), int(base - size * 0.88)))
                    x += size * 1.08
            else:
                f = font(size, "deva" if kind == "deva" else "main")
                d.text((x, base), s, font=f, fill=fill, anchor="ls",
                       stroke_width=int(stroke), stroke_fill=stroke_fill)
                x += f.getlength(s)
    return im


def _rrect_layer(w, h, radius, fill, outline=None, ow=0, shadow=0):
    SS = 3
    pad = shadow + 2
    im = Image.new("RGBA", ((w + pad * 2) * SS, (h + pad * 2) * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if shadow:
        d.rounded_rectangle([pad * SS, (pad + shadow) * SS, (pad + w) * SS, (pad + h + shadow) * SS],
                            radius=radius * SS, fill=(0, 0, 0, 55))
    d.rounded_rectangle([pad * SS, pad * SS, (pad + w) * SS, (pad + h) * SS], radius=radius * SS,
                        fill=fill, outline=outline, width=int(ow * SS))
    return im.resize((w + pad * 2, h + pad * 2), Image.LANCZOS), pad


STYLES = {
    # size, pad_x, pad_y, radius, bg, fg, border, stroke
    "caption_box": dict(size=64, px=38, py=26, r=16, bg=(255, 255, 255), fg=(14, 14, 14), border=None, ow=0,
                        stroke=0, shadow=5, max_w=860),
    "card": dict(size=60, px=44, py=30, r=34, bg=(236, 90, 70), fg=(255, 255, 255), border=(16, 16, 16), ow=6,
                 stroke=0, shadow=6, max_w=800),
    "tag": dict(size=40, px=26, py=14, r=22, bg=(255, 255, 255), fg=(14, 14, 14), border=(16, 16, 16), ow=5,
                stroke=0, shadow=3, max_w=420),
    "title": dict(size=104, px=0, py=0, r=0, bg=None, fg=(255, 255, 255), border=None, ow=0, stroke=9,
                  shadow=0, max_w=960),
    "lyric": dict(size=74, px=0, py=0, r=0, bg=None, fg=(255, 255, 255), border=None, ow=0, stroke=5,
                  shadow=0, max_w=900),
    "subtitle": dict(size=56, px=0, py=0, r=0, bg=None, fg=(255, 255, 255), border=None, ow=0, stroke=7,
                     shadow=0, max_w=900),
}


def styled_box(text, style, s, color=None, size=None, max_w=None):
    """Render text in a named style at output scale s. Returns RGBA image."""
    st = dict(STYLES.get(style, STYLES["caption_box"]))
    if color:
        st["bg"] = tuple(color) if isinstance(color, (list, tuple)) else st["bg"]
    if size:
        st["size"] = size
    if max_w:
        st["max_w"] = max_w
    tb = text_block(text, st["size"] * s, (st["max_w"] - 2 * st["px"]) * s, fill=st["fg"],
                    stroke=st["stroke"] * s, stroke_fill=(0, 0, 0))
    if st["bg"] is None:
        return tb
    w = tb.width + int(2 * st["px"] * s)
    h = tb.height + int(2 * st["py"] * s)
    box, pad = _rrect_layer(w, h, int(st["r"] * s), st["bg"], st["border"], st["ow"] * s,
                            int(st["shadow"] * s))
    box.alpha_composite(tb, (pad + int(st["px"] * s), pad + int(st["py"] * s)))
    return box


# ---------------------------------------------------------------- speech bubble
@functools.lru_cache(maxsize=256)
def bubble_image(text, s, tail_x, size=46, max_w=600, tail_h=58):
    """White speech bubble with a tail whose tip is at (tail_x, bottom). tail_x in output px."""
    tb = text_block(text, size * s, max_w * s, fill=(14, 14, 14))
    px, py = int(30 * s), int(20 * s)
    w, h = tb.width + 2 * px, tb.height + 2 * py
    th = int(tail_h * s)
    SS = 3
    pad = int(6 * s) + 2
    W, H = w + 2 * pad, h + th + 2 * pad
    im = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ow = max(3, int(5 * s)) * SS
    box = [pad * SS, pad * SS, (pad + w) * SS, (pad + h) * SS]
    tip = min(max(tail_x, 40 * s + pad), w + pad - 40 * s) * SS
    base_l, base_r = tip - 26 * s * SS, tip + 8 * s * SS
    tri = [(base_l, (pad + h - 3) * SS), (base_r, (pad + h - 3) * SS), (tip, (pad + h + th) * SS)]
    d.rounded_rectangle(box, radius=int(30 * s) * SS, fill=(255, 255, 255), outline=(16, 16, 16), width=ow)
    d.polygon(tri, fill=(255, 255, 255))
    d.line([tri[0], tri[2], tri[1]], fill=(16, 16, 16), width=ow, joint="curve")
    # cover the bubble outline where the tail joins
    d.line([(base_l + ow, (pad + h) * SS), (base_r - ow, (pad + h) * SS)], fill=(255, 255, 255), width=ow + 2)
    im = im.resize((W, H), Image.LANCZOS)
    im.alpha_composite(tb, (pad + px, pad + py))
    return im, (tip / SS, H)   # tail tip x (in image px), tail tip y (== bottom)

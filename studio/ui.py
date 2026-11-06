"""Screen UI overlays (drawn over everything, not zoomed by the camera).

{ "type": "chat", "title": "Mummy", "from": 1, "to": 8,
  "messages": [ {"side": "them", "text": "Kahan ho?", "at": 0.5}, {"side": "me", "text": "Library me 📚", "at": 2} ] }
{ "type": "notification", "app": "Bank", "title": "Rs 5 credited", "text": "Balance: Rs 7", "from": 2, "dur": 3 }
{ "type": "loading", "label": "Dimaag loading...", "from": 1, "dur": 3 }
{ "type": "counter", "label": "Rotis khayi", "start": 0, "end": 14, "from": 1, "dur": 3 }
{ "type": "timecard", "text": "3 ghante baad...", "from": 4, "dur": 1.5 }
{ "type": "chapter", "text": "Chapter 2", "subtitle": "Exam ka din", "from": 0, "dur": 2 }
{ "type": "endcard", "text": "Follow for more", "sub": "@yourpage", "from": 9 }
"""
import math

from PIL import Image, ImageDraw

from .text import font, text_block
from .util import LH, LW, clamp, ease_out, ease_out_back

TYPES = ("chat", "notification", "loading", "counter", "timecard", "chapter", "endcard")
INK = (16, 16, 16)


def _rr(d, box, r, fill, outline=None, w=0):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=w)


def _canvas(w, h):
    im = Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


# ---------------------------------------------------------------- chat
def chat(o, lt, s):
    W, H = 860 * s, 1180 * s
    im, d = _canvas(W, H)
    _rr(d, [0, 0, W - 1, H - 1], 44 * s, (236, 229, 218), INK, max(2, int(6 * s)))
    _rr(d, [0, 0, W - 1, 150 * s], 44 * s, tuple(o.get("color", (24, 120, 104))))
    d.rectangle([0, 100 * s, W - 1, 150 * s], fill=tuple(o.get("color", (24, 120, 104))))
    d.ellipse([40 * s, 34 * s, 122 * s, 116 * s], fill=(210, 220, 226))
    name = str(o.get("title", "Chat"))
    tb = text_block(name, 46 * s, 520 * s, fill=(255, 255, 255))
    im.alpha_composite(tb, (int(146 * s), int(44 * s)))
    sub = text_block("online", 30 * s, 300 * s, fill=(210, 236, 230))
    im.alpha_composite(sub, (int(146 * s), int(100 * s)))
    y = 190 * s
    msgs = o.get("messages", [])
    shown = [m for m in msgs if float(m.get("at", 0)) <= lt]
    typing = next((m for m in msgs if float(m.get("at", 0)) - 0.9 <= lt < float(m.get("at", 0))
                   and m.get("side", "them") == "them"), None)
    blocks = []
    for m in shown:
        me = m.get("side", "them") == "me"
        tb = text_block(str(m.get("text", "")), 40 * s, 560 * s, fill=INK)
        blocks.append((me, tb, lt - float(m.get("at", 0))))
    total = sum(b[1].height + 70 * s for b in blocks)
    y = max(170 * s, H - 120 * s - total) if total > H - 300 * s else 190 * s
    for me, tb, age in blocks:
        bw, bh = tb.width + 50 * s, tb.height + 36 * s
        x = W - bw - 34 * s if me else 34 * s
        pop = ease_out_back(age / 0.25)
        bub, bd = _canvas(bw, bh + 4)
        _rr(bd, [0, 0, bw - 1, bh - 1], 24 * s, (220, 248, 198) if me else (255, 255, 255))
        bub.alpha_composite(tb, (int(25 * s), int(16 * s)))
        if pop < 0.999:
            bub = bub.resize((max(1, int(bw * pop)), max(1, int((bh + 4) * pop))))
        im.alpha_composite(bub, (int(x + (0 if not me else bw * (1 - pop))), int(y)))
        y += bh + 22 * s
    if typing:
        bw, bh = 140 * s, 70 * s
        _rr(d, [34 * s, y, 34 * s + bw, y + bh], 24 * s, (255, 255, 255))
        for i in range(3):
            up = 8 * s * max(0.0, math.sin(lt * 8 - i))
            cx = 34 * s + 40 * s + i * 30 * s
            d.ellipse([cx - 9 * s, y + bh / 2 - 9 * s - up, cx + 9 * s, y + bh / 2 + 9 * s - up], fill=(150, 150, 150))
    _rr(d, [24 * s, H - 100 * s, W - 120 * s, H - 28 * s], 36 * s, (255, 255, 255))
    d.ellipse([W - 104 * s, H - 104 * s, W - 28 * s, H - 28 * s], fill=tuple(o.get("color", (24, 120, 104))))
    return im


# ---------------------------------------------------------------- notification
def notification(o, lt, s):
    W, H = 940 * s, 190 * s
    im, d = _canvas(W, H + 10)
    _rr(d, [0, 0, W - 1, H - 1], 36 * s, (250, 250, 252, 245), (200, 200, 206), max(1, int(3 * s)))
    d.ellipse([28 * s, 40 * s, 128 * s, 140 * s], fill=tuple(o.get("color", (70, 130, 220))))
    icon = str(o.get("icon", (str(o.get("app", "?"))[:1] or "?").upper()))
    ib = text_block(icon, 50 * s, 100 * s, fill=(255, 255, 255))
    im.alpha_composite(ib, (int(78 * s - ib.width / 2), int(90 * s - ib.height / 2)))
    app = text_block(str(o.get("app", "Message")).upper() + "  •  now", 28 * s, 700 * s, fill=(120, 120, 128))
    im.alpha_composite(app, (int(156 * s), int(26 * s)))
    title = text_block(str(o.get("title", o.get("app", ""))), 40 * s, 740 * s, fill=INK)
    im.alpha_composite(title, (int(156 * s), int(64 * s)))
    body = text_block(str(o.get("text", "")), 34 * s, 740 * s, fill=(60, 60, 66))
    im.alpha_composite(body.crop((0, 0, body.width, min(body.height, int(70 * s)))), (int(156 * s), int(112 * s)))
    return im


# ---------------------------------------------------------------- loading / counter
def loading(o, lt, s, dur):
    W, H = 820 * s, 230 * s
    im, d = _canvas(W, H)
    lab = text_block(str(o.get("label", "Loading...")), 50 * s, W, fill=(255, 255, 255), stroke=6 * s)
    im.alpha_composite(lab, (int(W / 2 - lab.width / 2), 0))
    k = clamp(lt / max(0.2, dur * float(o.get("fill", 0.9))))
    if o.get("stuck"):                    # comedic: stops at 99%
        k = min(k, 0.99)
    y0 = 100 * s
    _rr(d, [0, y0, W - 1, y0 + 80 * s], 40 * s, (40, 40, 46), (255, 255, 255), max(2, int(5 * s)))
    if k > 0.01:
        _rr(d, [8 * s, y0 + 8 * s, 8 * s + (W - 16 * s) * k, y0 + 72 * s], 32 * s, tuple(o.get("color", (90, 200, 120))))
    pct = text_block("%d%%" % int(k * 100), 40 * s, W, fill=(255, 255, 255), stroke=5 * s)
    im.alpha_composite(pct, (int(W / 2 - pct.width / 2), int(y0 + 40 * s - pct.height / 2)))
    return im


def counter(o, lt, s, dur):
    a, b = float(o.get("start", 0)), float(o.get("end", 100))
    k = ease_out(lt / max(0.2, dur * 0.8))
    v = a + (b - a) * k
    num = ("%d" % round(v)) if float(b).is_integer() and float(a).is_integer() else ("%.1f" % v)
    num = str(o.get("prefix", "")) + num + str(o.get("suffix", ""))
    big = text_block(num, 150 * s, 900 * s, fill=tuple(o.get("color", (255, 220, 70))), stroke=10 * s)
    lab = text_block(str(o.get("label", "")), 52 * s, 900 * s, fill=(255, 255, 255), stroke=6 * s)
    W = max(big.width, lab.width)
    im, _d = _canvas(W, big.height + lab.height + 10 * s)
    im.alpha_composite(lab, (int(W / 2 - lab.width / 2), 0))
    pop = 1 + 0.08 * abs(math.sin(lt * 18)) * (1 - k)
    bb = big.resize((max(1, int(big.width * pop)), max(1, int(big.height * pop))))
    im.alpha_composite(bb.crop((0, 0, min(bb.width, W), bb.height)), (int(W / 2 - min(bb.width, W) / 2), int(lab.height + 6 * s)))
    return im


# ---------------------------------------------------------------- full-screen cards
def timecard(o, lt, s, size):
    W, H = size
    im = Image.new("RGBA", (W, H), tuple(o.get("color", (60, 120, 210))) + (255,))
    d = ImageDraw.Draw(im, "RGBA")                         # blend the rays, don't punch holes
    for i in range(14):                                    # sunburst
        a0 = i * 2 * math.pi / 14 + lt * 0.4
        pts = [(W / 2, H / 2), (W / 2 + 2000 * math.cos(a0), H / 2 + 2000 * math.sin(a0)),
               (W / 2 + 2000 * math.cos(a0 + 0.22), H / 2 + 2000 * math.sin(a0 + 0.22))]
        d.polygon(pts, fill=(255, 255, 255, 34))
    tb = text_block(str(o.get("text", "Kuch der baad...")), 96 * s, W - 120 * s, fill=(255, 240, 120), stroke=10 * s)
    sc = 0.6 + 0.4 * ease_out_back(lt / 0.35)
    tb = tb.resize((max(1, int(tb.width * sc)), max(1, int(tb.height * sc))))
    im.alpha_composite(tb, (int(W / 2 - tb.width / 2), int(H / 2 - tb.height / 2)))
    return im


def chapter(o, lt, s):
    W = 960 * s
    t1 = text_block(str(o.get("text", "Chapter 1")), 86 * s, W, fill=(255, 255, 255), stroke=8 * s)
    t2 = text_block(str(o.get("subtitle", "")), 50 * s, W, fill=(255, 220, 90), stroke=6 * s) if o.get("subtitle") else None
    H = t1.height + (t2.height + 20 * s if t2 else 0) + 60 * s
    im, d = _canvas(W, H)
    k = ease_out(lt / 0.4)
    d.rectangle([W / 2 - W / 2 * k, H - 16 * s, W / 2 + W / 2 * k, H - 6 * s], fill=(255, 220, 90))
    im.alpha_composite(t1, (int(W / 2 - t1.width / 2), int(10 * s)))
    if t2:
        im.alpha_composite(t2, (int(W / 2 - t2.width / 2), int(t1.height + 24 * s)))
    return im


def endcard(o, lt, s, size):
    W, H = size
    im = Image.new("RGBA", (W, H), (10, 10, 18, int(200 * clamp(lt / 0.4))))
    d = ImageDraw.Draw(im)
    tb = text_block(str(o.get("text", "Follow for more")), 92 * s, W - 140 * s, fill=(255, 255, 255), stroke=8 * s)
    sc = 0.5 + 0.5 * ease_out_back(lt / 0.4)
    tb = tb.resize((max(1, int(tb.width * sc)), max(1, int(tb.height * sc))))
    im.alpha_composite(tb, (int(W / 2 - tb.width / 2), int(H * 0.36)))
    if o.get("sub"):
        sb = text_block(str(o["sub"]), 54 * s, W - 140 * s, fill=(255, 220, 90))
        im.alpha_composite(sb, (int(W / 2 - sb.width / 2), int(H * 0.36 + tb.height + 30 * s)))
    bw, bh = 520 * s, 130 * s
    pulse = 1 + 0.05 * math.sin(lt * 6)
    bx, by = W / 2 - bw * pulse / 2, H * 0.58
    _rr(d, [bx, by, bx + bw * pulse, by + bh * pulse], 65 * s, tuple(o.get("color", (230, 60, 80))))
    lab = text_block(str(o.get("button", "FOLLOW")), 60 * s, bw, fill=(255, 255, 255))
    im.alpha_composite(lab, (int(W / 2 - lab.width / 2), int(by + bh * pulse / 2 - lab.height / 2)))
    for i in range(6):                                     # floating hearts
        ph = (lt * 0.5 + i / 6.0) % 1.0
        x = W * (0.15 + 0.14 * i)
        y = H * (0.9 - 0.5 * ph)
        r = (18 + 8 * (i % 2)) * s
        col = (240, 80, 110, int(255 * (1 - ph)))
        d.ellipse([x - r, y - r, x, y], fill=col)
        d.ellipse([x, y - r, x + r, y], fill=col)
        d.polygon([(x - r, y - r / 2), (x + r, y - r / 2), (x, y + r)], fill=col)
    return im


def render(o, lt, s, dur, size):
    """RGBA image for overlay o at local time lt, or None. Full-screen types return a frame-sized image."""
    t = o.get("type")
    if t == "chat":
        return chat(o, lt, s)
    if t == "notification":
        return notification(o, lt, s)
    if t == "loading":
        return loading(o, lt, s, dur)
    if t == "counter":
        return counter(o, lt, s, dur)
    if t == "timecard":
        return timecard(o, lt, s, size)
    if t == "chapter":
        return chapter(o, lt, s)
    if t == "endcard":
        return endcard(o, lt, s, size)
    return None

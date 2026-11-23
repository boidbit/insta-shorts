"""Desi set dressing of the busiest places (the new camera; `CAMERA: classic` keeps the old drawings).

The little things every Indian viewer knows: electric wires sagging over the lane with a crow on them, a painted wall
advert, a calendar on the wall, a switchboard with its wire running up, a bucket, a pair of chappals by the door, a
red gas cylinder, a DTH dish. Each place has its own fixed set (always the same: a series' home place is
recognisable from one episode to the next). Placed on the walls above the heads, at the edges and along the walls,
never where people stand. Nothing religious."""
from .backgrounds import INK, G
from .locations import _txt
from .util import LW


def wires(g, y, sag=40, birds=(), n=3):
    for i in range(n):
        y0 = y + i * 26
        pts = [(x, y0 + sag * (1 - ((x - LW / 2) / (LW / 2)) ** 2)) for x in range(-20, LW + 41, 40)]
        g.line(pts, (34, 34, 38), 4)
    for bx in birds:                                  # a crow sitting on the top wire
        by = y + sag * (1 - ((bx - LW / 2) / (LW / 2)) ** 2)
        g.ellipse(bx - 22, by - 30, bx + 18, by - 2, (40, 40, 46), INK, 3)
        g.circle(bx + 16, by - 32, 11, (40, 40, 46), INK, 3)
        g.poly([(bx + 26, by - 34), (bx + 40, by - 30), (bx + 26, by - 27)], (90, 90, 96), INK, 2)
        g.poly([(bx - 20, by - 18), (bx - 44, by - 6), (bx - 18, by - 8)], (40, 40, 46), INK, 3)
        g.line([(bx - 4, by - 3), (bx - 4, by + 4)], INK, 3)
        g.line([(bx + 6, by - 3), (bx + 6, by + 4)], INK, 3)


def wall_ad(g, x0, y0, x1, y1, lines, bg=(250, 214, 70), fg=(190, 30, 40)):
    """A painted advert straight on the wall, a little faded, a phone number under it."""
    g.rect(x0, y0, x1, y1, bg, None)
    g.rect(x0 + 8, y0 + 8, x1 - 8, y1 - 8, None, fg, 4)
    h = (y1 - y0) / (len(lines) + 0.4)
    for i, (txt, size) in enumerate(lines):
        _txt(g, (x0 + x1) / 2, y0 + h * (i + 0.7), txt, size, fg if i == 0 else INK)


def calendar(g, x, y, w=120, h=170, accent=(210, 50, 50)):
    """A hanging wall calendar: a nail, a red header, a picture, the month's grid."""
    g.circle(x, y - 14, 5, INK)
    g.line([(x, y - 14), (x - w / 2 + 10, y)], INK, 2)
    g.line([(x, y - 14), (x + w / 2 - 10, y)], INK, 2)
    g.rect(x - w / 2, y, x + w / 2, y + h, (250, 248, 240), INK, 4)
    g.rect(x - w / 2, y, x + w / 2, y + 26, accent, INK, 4)
    g.rect(x - w / 2 + 12, y + 36, x + w / 2 - 12, y + 92, (120, 180, 220), INK, 3)
    g.poly([(x - w / 2 + 14, y + 90), (x - 10, y + 54), (x + 14, y + 76), (x + 30, y + 62), (x + w / 2 - 14, y + 90)],
           (90, 150, 90))
    for r in range(4):
        for c in range(5):
            cx = x - w / 2 + 16 + c * (w - 32) / 4
            g.rect(cx - 5, y + 104 + r * 15, cx + 5, y + 112 + r * 15, (200, 60, 60) if c == 4 else (120, 120, 120))


def switchboard(g, x, y, up=None):
    """A white switchboard with four switches and a plug point; its wire runs up the wall."""
    if up is not None:
        g.line([(x + 30, y), (x + 30, up)], (240, 240, 236), 7)
        g.line([(x + 30, y), (x + 30, up)], (140, 140, 140), 2)
    g.rrect(x - 60, y, x + 60, y + 80, 6, (246, 246, 240), INK, 4)
    for i in range(4):
        g.rect(x - 48 + i * 22, y + 14, x - 34 + i * 22, y + 38, (230, 230, 226), INK, 2)
        g.circle(x - 41 + i * 22, y + 46, 3, (220, 70, 60) if i == 1 else (150, 150, 150))
    g.circle(x + 42, y + 30, 11, (232, 232, 228), INK, 2)
    for dx in (-4, 4):
        g.circle(x + 42 + dx, y + 27, 2, INK)
    g.circle(x + 42, y + 35, 2, INK)


def bucket(g, x, y, col=(60, 120, 200)):
    g.poly([(x - 40, y - 70), (x + 40, y - 70), (x + 30, y), (x - 30, y)], col, INK, 4)
    g.ellipse(x - 40, y - 80, x + 40, y - 60, tuple(int(c * 0.7) for c in col), INK, 4)
    g.line([(x - 38, y - 72), (x, y - 110), (x + 38, y - 72)], INK, 3)


def mug(g, x, y, col=(230, 80, 80)):
    g.rect(x - 16, y - 34, x + 16, y, col, INK, 3)
    g.line([(x + 16, y - 26), (x + 26, y - 22), (x + 26, y - 12), (x + 16, y - 8)], INK, 3)


def chappals(g, x, y, col=(70, 130, 200)):
    for dx, tilt in ((-22, -6), (22, 8)):
        cx = x + dx
        g.ellipse(cx - 15, y - 9 + tilt * 0.2, cx + 15, y + 9 + tilt * 0.2, col, INK, 3)
        g.line([(cx - 10, y - 2), (cx, y - 12), (cx + 10, y - 2)], (240, 240, 240), 3)


def cylinder(g, x, y):
    """The red LPG cylinder."""
    g.rrect(x - 46, y - 150, x + 46, y, 30, (200, 40, 40), INK, 5)
    g.rect(x - 46, y - 92, x + 46, y - 80, (170, 30, 30), None)
    g.rect(x - 18, y - 178, x + 18, y - 150, (150, 150, 150), INK, 4)
    g.rect(x - 30, y - 190, x + 30, y - 176, (70, 70, 70), INK, 3)


def dish(g, x, y):
    """A DTH dish on a bracket on the wall."""
    g.line([(x, y), (x + 40, y - 10)], (120, 120, 120), 8)
    g.ellipse(x + 20, y - 70, x + 90, y + 30, (236, 236, 230), INK, 4)
    g.line([(x + 55, y - 20), (x + 100, y - 40)], (90, 90, 90), 4)
    g.circle(x + 100, y - 40, 7, (60, 60, 60), INK, 2)


def stool(g, x, y, col=(220, 60, 60)):
    """A plastic stool."""
    g.poly([(x - 50, y - 90), (x + 50, y - 90), (x + 40, y), (x + 24, y), (x + 26, y - 70), (x - 26, y - 70),
            (x - 24, y), (x - 40, y)], col, INK, 4)
    g.ellipse(x - 54, y - 100, x + 54, y - 82, tuple(min(255, int(c * 1.1)) for c in col), INK, 4)


def meter(g, x, y):
    """The electricity meter box with its wires."""
    g.rect(x - 40, y, x + 40, y + 90, (230, 230, 220), INK, 4)
    g.rect(x - 28, y + 14, x + 28, y + 42, (60, 70, 60), INK, 3)
    g.circle(x, y + 64, 9, (40, 40, 40), INK, 2)
    for dx in (-16, 0, 16):
        g.line([(x + dx, y), (x + dx, y - 120)], (30, 30, 34), 3)


ADS = {
    "gully": [("SHARMA TENT HOUSE", 25), ("shaadi • party • function", 19), ("98XXX 45XXX", 18)],
}

# place -> [(piece, args)] in logical 1080 x 1920 coordinates
PLACES = {
    "gully": [("wires", dict(y=150, sag=60, birds=(300,))), ("wall_ad", dict(x0=372, y0=640, x1=708, y1=830,
                                                                                lines=ADS["gully"])),
              ("meter", dict(x=860, y=980)), ("bucket", dict(x=980, y=1260, col=(230, 120, 40)))],
    "gaon": [("wires", dict(y=240, sag=30, birds=(760,), n=2)), ("chappals", dict(x=250, y=1250)),
             ("bucket", dict(x=430, y=1250, col=(60, 120, 200))), ("dish", dict(x=420, y=700))],
    "handpump": [("wires", dict(y=220, sag=26, birds=(560,), n=2)), ("chappals", dict(x=200, y=1250))],
    "room": [("calendar", dict(x=930, y=220)), ("switchboard", dict(x=330, y=1010)),
             ("chappals", dict(x=360, y=1290, col=(200, 70, 60)))],
    "kitchen": [("calendar", dict(x=160, y=280, accent=(40, 110, 200))), ("cylinder", dict(x=80, y=1390))],
    "kachcha_ghar": [("calendar", dict(x=920, y=640, accent=(220, 140, 40))), ("bucket", dict(x=1010, y=1300)),
                     ("chappals", dict(x=260, y=1290, col=(120, 80, 50)))],
    "chaupal": [("chappals", dict(x=420, y=1270, col=(60, 60, 60))), ("bucket", dict(x=900, y=1270))],
    "chai_tapri": [("wires", dict(y=120, sag=50, birds=(820,))), ("stool", dict(x=120, y=1330))],
    "clinic": [("calendar", dict(x=640, y=700, accent=(40, 150, 90)))],
    "podcast": [("mug", dict(x=470, y=1222))],
}
DRAW = {"wires": wires, "wall_ad": wall_ad, "calendar": calendar, "switchboard": switchboard, "bucket": bucket,
        "chappals": chappals, "cylinder": cylinder, "dish": dish, "stool": stool, "meter": meter, "mug": mug}


def dress(img, kind):
    """The place with its own desi dressing drawn on (a new RGB image), or the same image."""
    items = PLACES.get(kind)
    if not items:
        return img
    w, h = img.size
    s = w / float(LW)
    g = G(s, color=(0, 0, 0, 0), mode="RGBA")
    for name, kw in items:
        DRAW[name](g, **kw)
    layer = g.done()
    if layer.size != (w, h):
        layer = layer.resize((w, h))
    out = img.convert("RGBA")
    out.alpha_composite(layer)
    return out.convert("RGB")

"""Small pictures of every look for the web page's character picker (assets/looks/<look>.png).

    python -m studio.thumbs          # after changing a look in characters.py
"""
import os

from PIL import Image

from .characters import LOOKS, build_character, render_ops
from .util import ROOT

OUT = os.path.join(ROOT, "assets", "looks")
SIZE = (120, 150)                   # head and shoulders, transparent background


def thumb(spec):
    s = 0.36
    ops, an = build_character(spec, {}, "smile", 0.0, 0.0, 540, 1700, blink=False)
    layer, (ox, oy) = render_ops(ops, s, 1080, 1920)
    top = an["head_top"][1] * s - oy - 6
    cx = an["head_center"][0] * s - ox
    w, h = SIZE
    crop = layer.crop((int(cx - w / 2), int(top), int(cx + w / 2), int(top + h)))
    out = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    out.paste(crop, (0, 0), crop)
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    for look in sorted(LOOKS):
        path = os.path.join(OUT, look + ".png")
        thumb({"look": look}).save(path, optimize=True)
        print(path)


if __name__ == "__main__":
    main()

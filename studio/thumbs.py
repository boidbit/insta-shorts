"""Small pictures for the web page: every look for the character picker (assets/looks/<look>.png) and every place
for the builder's place picker (assets/places/<place>.jpg).

    python -m studio.thumbs          # after changing a look in characters.py or a place
"""
import os

from PIL import Image

from .characters import LOOKS, build_character, render_ops
from .util import ROOT

OUT = os.path.join(ROOT, "assets", "looks")
SIZE = (120, 150)                   # head and shoulders, transparent background
PLACES_OUT = os.path.join(ROOT, "assets", "places")
PLACE_SIZE = (108, 192)             # a small 9:16 picture of the empty place


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


def face_chart():
    """One picture of every face-card choice, each labelled with the word that goes in the script
    (assets/faces/chart.png, shown on the page's face card)."""
    from PIL import ImageDraw
    from .characters import FACE_PARTS, HAIR_STYLES, MARKS, face_word
    from .text import font
    items = []
    girl_parts = {"lips", "eyes"}
    for part, vals in FACE_PARTS.items():
        for v in vals:
            base = {"look": "college_girl" if part in girl_parts else "boy"}
            if part == "moustache" and v == "none":
                base = {"look": "police"}
            items.append((face_word(part, v), dict(base, **{part: v})))
    for m in MARKS:
        items.append((m, {"look": "dada" if m == "age_lines" else "boy", "marks": [m]}))
    items += [("blush", {"look": "girl", "cheeks": "blush"}), ("lashes", {"look": "girl", "lashes": True})]
    for h in HAIR_STYLES:
        items.append((h, {"look": "college_girl" if h in ("long", "braid", "bun", "ponytail", "bob", "two_plaits",
                                                         "side_braid", "curly_open") else "boy", "hair": h}))
    cols, cw, ch, lab = 8, 120, 150, 24
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cw, rows * (ch + lab)), (244, 246, 250))
    d = ImageDraw.Draw(sheet)
    for i, (word, spec) in enumerate(items):
        x, y = (i % cols) * cw, (i // cols) * (ch + lab)
        im = thumb(spec)
        sheet.paste(im, (x, y), im)
        f = font(13 if len(word) < 15 else 10.5, "main")
        d.text((x + cw / 2, y + ch + lab / 2), word, font=f, fill=(30, 30, 40), anchor="mm")
    return sheet


def place_thumb(place):
    from .backgrounds import Background
    im = Background({"type": place}, 360, 640).frame(0.5).convert("RGB")
    return im.resize(PLACE_SIZE, Image.LANCZOS)


def main():
    os.makedirs(OUT, exist_ok=True)
    for look in sorted(LOOKS):
        path = os.path.join(OUT, look + ".png")
        thumb({"look": look}).save(path, optimize=True)
        print(path)
    faces = os.path.join(ROOT, "assets", "faces")
    os.makedirs(faces, exist_ok=True)
    path = os.path.join(faces, "chart.png")
    face_chart().quantize(colors=128).save(path, optimize=True)
    print(path)
    from .script import BACKGROUNDS
    os.makedirs(PLACES_OUT, exist_ok=True)
    for place in BACKGROUNDS:
        path = os.path.join(PLACES_OUT, place + ".jpg")
        place_thumb(place).save(path, quality=80, optimize=True)
        print(path)


if __name__ == "__main__":
    main()

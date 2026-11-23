"""The finishing pass over a painted place (the new camera; `CAMERA: classic` keeps the old flat look).

A drawn place is flat colour: walls of one colour, a floor of one colour, nothing where the wall meets the floor.
This pass adds what makes a painting feel lived in, the same way on every place:

- contact shadow: a soft dark band where the wall meets the floor (and the ground meets the houses), so nothing
  seems to float;
- texture: big soft blotches on walls (old plaster, sun-faded paint) and on the floor (wear, dirt), a fine grain;
  never on the sky;
- light: indoors a little warm light from above, darker towards the floor; everywhere a soft vignette that keeps the
  eye in the middle, where the people are.

Deterministic: the same place always gets the same texture (a video looks the same each time it is made)."""
import zlib

import numpy as np
from PIL import Image, ImageFilter

INDOOR_EXTRA = {"podcast", "clinic", "kachcha_ghar", "sarkari_daftar", "kirana", "chai_tapri_inside"}
FALLBACK_HORIZON = {"room": 1260, "living_room": 1260, "kitchen": 1300, "school": 1280, "classroom": 1280,
                    "office": 1270, "street": 1250, "bus_stop": 1250, "hospital": 1280}
SKIP = {"plain", "image", "night_road"}


def horizon_of(kind):
    from .locations import LOC_HORIZON
    return LOC_HORIZON.get(kind) or FALLBACK_HORIZON.get(kind)


def _indoor(kind):
    from .decor import INDOOR
    return kind in INDOOR or kind in INDOOR_EXTRA


def _blotches(rng, h, w, cell):
    """Soft noise in [-1, 1]: random values on a coarse grid, smoothly enlarged."""
    gh, gw = max(2, h // cell + 2), max(2, w // cell + 2)
    small = Image.fromarray(((rng.random((gh, gw)) * 255)).astype(np.uint8), "L")
    big = small.resize((w + cell, h + cell), Image.BICUBIC).crop((cell // 2, cell // 2, cell // 2 + w, cell // 2 + h))
    return np.asarray(big, dtype=np.float32) / 127.5 - 1.0


def finish(img, kind, logical_h=1920):
    """The finished place (a new RGB image of the same size)."""
    if kind in SKIP:
        return img
    rgb = np.asarray(img.convert("RGB"), dtype=np.float32)
    h, w = rgb.shape[:2]
    s = h / float(logical_h)
    rng = np.random.default_rng(zlib.crc32(("finish|" + kind).encode("utf-8")))
    indoor = _indoor(kind)
    hz = horizon_of(kind)
    y = (np.arange(h, dtype=np.float32) / s)[:, None]           # logical y of each row
    x = (np.arange(w, dtype=np.float32) / s)[None, :]
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    sky = (b > r + 18) & (b >= g) & (y < (hz or 1920))          # (no texture on the sky)

    # texture: big soft blotches (plaster, wear) + a finer layer + grain
    k = np.ones((h, w), np.float32)
    tex = 0.65 * _blotches(rng, h, w, max(8, int(150 * s))) + 0.35 * _blotches(rng, h, w, max(4, int(46 * s)))
    amp = np.where(y < (hz or 1300), 0.045 if indoor else 0.03, 0.06).astype(np.float32) * np.ones((1, w), np.float32)
    amp[sky] = 0.0
    k *= 1.0 + amp * tex
    grain = rng.normal(0.0, 1.0, (h, w)).astype(np.float32)
    grain = np.asarray(Image.fromarray(np.clip(grain * 40 + 128, 0, 255).astype(np.uint8), "L")
                       .filter(ImageFilter.GaussianBlur(0.6 * max(1.0, s))), np.float32) / 128.0 - 1.0
    k *= 1.0 + np.where(sky, 0.004, 0.014) * grain

    # contact shadow where the wall / the houses meet the floor
    if hz:
        up = np.clip((hz - y) / 46.0, 0, None)
        down = np.clip((y - hz) / 80.0, 0, None)
        band = np.where(y < hz, 0.13 * np.exp(-up), 0.17 * np.exp(-down))
        if not indoor:
            band = np.where(y < hz, 0.0, band * 0.55)               # outdoors: only on the ground, softer
        k *= (1.0 - band) * np.ones((1, w), np.float32)

    # light: indoors warm from above, darker towards the near floor; a soft vignette everywhere
    if indoor:
        top = np.clip(1.0 - y / 1920.0, 0, 1)
        warm = np.stack([1.0 + 0.035 * top, 1.0 + 0.012 * top, 1.0 - 0.02 * top], axis=-1)
        rgb = rgb * warm
        k *= 1.0 - 0.08 * np.clip((y - 1500.0) / 420.0, 0, 1)
    cx, cy = 540.0, 900.0
    rr = np.sqrt(((x - cx) / 620.0) ** 2 + ((y - cy) / 1100.0) ** 2)
    k *= 1.0 - 0.17 * np.clip((rr - 0.62) / 0.55, 0, 1) ** 1.6

    out = np.clip(rgb * k[..., None], 0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGB")

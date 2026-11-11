"""A colour mood per video, so a page's reels do not all look alike: the hook card's colours, the CTA card's colour,
a light colour grade over the picture and a nudge to the place's own colours (walls, buildings; the sky stays
blue). Script: `COLOR: golden` (auto = every video its own, picked from its hook); scene: meta["theme"].
`CAMERA: classic` keeps the old look (no theme)."""
import zlib

from PIL import Image

# hook card bg / text, CTA card, grade (r, g, b gains + "contrast" / "split" extras), place hue shift (PIL 0..255)
THEMES = {
    "classic": dict(hook=(255, 212, 0), hook_fg=(14, 14, 14), card=(236, 90, 70), gain=None, extra=None, hue=0),
    "golden": dict(hook=(255, 150, 40), hook_fg=(24, 14, 6), card=(196, 64, 40), gain=(1.05, 1.0, 0.9), extra=None,
                   hue=-8),
    "cool": dict(hook=(70, 214, 255), hook_fg=(8, 22, 34), card=(38, 104, 214), gain=(0.95, 1.0, 1.07), extra=None,
                 hue=10),
    "rose": dict(hook=(255, 84, 150), hook_fg=(255, 255, 255), card=(140, 60, 200), gain=(1.04, 0.97, 1.02),
                 extra=None, hue=-14),
    "teal_orange": dict(hook=(16, 168, 160), hook_fg=(255, 255, 255), card=(255, 120, 40), gain=(1.0, 1.0, 1.0),
                        extra="split", hue=6),
    "punchy": dict(hook=(22, 22, 26), hook_fg=(255, 226, 0), card=(228, 40, 60), gain=(1.0, 1.0, 1.0),
                   extra="contrast", hue=0),
    "lime": dict(hook=(170, 238, 40), hook_fg=(14, 14, 14), card=(70, 60, 200), gain=(1.0, 1.03, 0.95), extra=None,
                 hue=14),
}
AUTO = [k for k in THEMES]                      # (classic too: the old yellow is one mood among the others)
ALIASES = {"gold": "golden", "warm": "golden", "sunehra": "golden", "blue": "cool", "neela": "cool", "pink": "rose",
           "gulabi": "rose", "teal": "teal_orange", "orange": "teal_orange", "dark": "punchy", "black": "punchy",
           "green": "lime", "hara": "lime", "yellow": "classic", "peela": "classic"}


def resolve(name):
    """`golden` / `Pink` / ... -> a theme name, or None."""
    n = str(name or "").strip().lower().replace("-", "_").replace(" ", "_")
    n = ALIASES.get(n, n)
    return n if n in THEMES else None


def auto(seed_text):
    """The theme a video gets when the script does not choose one: the same hook gives the same colours."""
    return AUTO[zlib.crc32(("theme|" + (seed_text or "reel")).encode("utf-8")) % len(AUTO)]


def apply(scene, name):
    """Give a scene (a script's or a JSON scene) a theme, in place: the meta, the hook card and the CTA card."""
    T = THEMES[name]
    meta = scene.setdefault("meta", {})
    meta["theme"], meta["cta_color"] = name, list(T["card"])
    for o in scene.get("overlays", []):
        if o.get("style") == "hook":
            o["color"], o["fg"] = list(T["hook"]), list(T["hook_fg"])
    for sc in scene.get("scenes") or [scene]:
        for ev in sc.get("timeline", []):
            o = ev.get("overlay")
            if isinstance(o, dict) and (o.get("cta") or o.get("cta_sticker")):
                o["color"] = list(T["card"])
    return scene


_LUTS = {}


def grade_lut(name):
    """Per-channel lookup table (768 values) for a theme's grade, or None for no grade."""
    if name in _LUTS:
        return _LUTS[name]
    th = THEMES.get(name)
    if not th or (th["gain"] is None and th["extra"] is None):
        _LUTS[name] = None
        return None
    lut = []
    for ch in range(3):
        g = th["gain"][ch] if th["gain"] else 1.0
        for v in range(256):
            x = v / 255.0
            if th["extra"] == "contrast":                   # a little more bite
                x = 0.5 + (x - 0.5) * 1.12
            elif th["extra"] == "split":                    # teal in the shadows, orange in the light
                if ch == 0:
                    x += 0.06 * x * x
                elif ch == 2:
                    x += 0.07 * (1.0 - x) ** 2 - 0.04 * x * x
            x *= g
            lut.append(max(0, min(255, int(round(x * 255)))))
    _LUTS[name] = lut
    return lut


def grade(img, name):
    """The theme's colour grade over a finished picture (RGB). Classic / none: unchanged."""
    lut = grade_lut(name)
    return img.point(lut) if lut else img


def shift_place(img, name):
    """Nudge a painted place's hues (walls, buildings, floors) by the theme's amount; the sky's blues and anything
    grey stay as they are. Done once per scene."""
    th = THEMES.get(name)
    dh = int(th["hue"]) if th else 0
    if not dh:
        return img
    rgba = img.mode == "RGBA"
    alpha = img.getchannel("A") if rgba else None
    h, s, v = img.convert("RGB").convert("HSV").split()
    keep = range(122, 182)                                  # sky blues (about 172-257 degrees)
    h = h.point([x if x in keep else (x + dh) % 256 for x in range(256)])
    out = Image.merge("HSV", (h, s, v)).convert("RGB")
    if rgba:
        out.putalpha(alpha)
    return out

"""The look of a place: a colour grade per kind of place and per mood, so a hospital, a dhaba, a shaadi and a
haunted house do not come out of the same camera, and two videos do not look alike.

    place  -> a look (clinic: cold and clean; dhaba / gaon: golden dust; shaadi: rich and glowing; haunted: sick
              green, dark corners, grain; jail: bleached; office: tired grey-blue; night: blue shadows, warm lamps)
    mood   -> on top of it, from the music (`MUSIC: sad` drains the colour, `suspense` darkens, `festive` enriches)
    time   -> `SCENE: kitchen night`: lamps glow

Script: `LOOK: auto` (default) | `LOOK: off` | `LOOK: <name>` for the whole video (a name from LOOKS).
It is part of the new camera's look: `CAMERA: classic` keeps the old picture exactly (like the colour themes).
Every frame: one colour matrix (saturation), one lookup table (contrast, fade, split toning), and where the look
asks for it a glow around the lights, darker corners and film grain.
"""
import zlib

import numpy as np
from PIL import Image, ImageChops, ImageFilter

# sat: colour (1 = as painted); contrast: S-curve around the middle; fade: lifted blacks (0..0.1); gamma < 1
# brightens; gain: r, g, b; shadows / lights: colour pushed into the dark / the bright parts (r, g, b in -1..1);
# bloom: glow around lights (0..1); vig: darker corners (0..1); grain: film grain (0..1)
NEUTRAL = dict(sat=1.0, contrast=1.0, fade=0.0, gamma=1.0, gain=(1.0, 1.0, 1.0), shadows=(0.0, 0.0, 0.0),
               lights=(0.0, 0.0, 0.0), bloom=0.0, vig=0.0, grain=0.0)
LOOKS = {
    "ghar": dict(sat=1.1, contrast=1.04, gain=(1.05, 1.0, 0.93), lights=(0.04, 0.02, -0.03)),      # warm home
    "rasoi": dict(sat=1.14, contrast=1.05, gain=(1.06, 1.01, 0.9), lights=(0.05, 0.03, -0.04)),    # sunny kitchen
    "clinic": dict(sat=0.86, contrast=0.96, fade=0.04, gamma=0.94, gain=(0.94, 1.03, 1.05),         # cold and clean
                   shadows=(-0.03, 0.02, 0.03)),
    "daftar": dict(sat=0.78, contrast=1.02, fade=0.03, gain=(0.95, 0.99, 1.06), shadows=(-0.02, 0.0, 0.04)),
    "padhai": dict(sat=0.94, contrast=1.03, fade=0.03, gain=(1.05, 1.0, 0.9), lights=(0.03, 0.02, -0.04)),
    "sunehra": dict(sat=1.12, contrast=1.08, gain=(1.07, 1.01, 0.88), shadows=(0.02, -0.01, -0.03),  # golden dust
                    lights=(0.04, 0.02, -0.04), vig=0.18),
    "bazaar": dict(sat=1.24, contrast=1.08, gain=(1.04, 1.0, 0.94), lights=(0.03, 0.01, -0.02)),   # loud colours
    "sadak": dict(sat=1.06, contrast=1.08, gain=(1.0, 1.0, 1.0), shadows=(-0.03, 0.01, 0.04),      # teal / orange
                  lights=(0.05, 0.02, -0.04)),
    "utsav": dict(sat=1.2, contrast=1.08, gain=(1.06, 0.98, 1.0), shadows=(0.03, -0.02, 0.04),     # shaadi, party
                  lights=(0.05, 0.03, -0.02), bloom=0.5, vig=0.15),
    "raat": dict(sat=1.05, contrast=1.1, gain=(0.94, 0.98, 1.1), shadows=(-0.04, -0.01, 0.07),     # the city at night
                 lights=(0.07, 0.04, -0.05), bloom=0.45, vig=0.25),
    "darr": dict(sat=0.66, contrast=1.14, fade=0.02, gain=(0.92, 1.02, 1.0), shadows=(-0.05, 0.03, 0.04),   # horror
                 lights=(-0.01, 0.02, 0.0), bloom=0.25, vig=0.5, grain=0.4),
    "hawalat": dict(sat=0.55, contrast=1.2, gain=(0.97, 1.0, 1.05), shadows=(-0.02, 0.0, 0.03), vig=0.35,    # bleached
                    grain=0.3),
    "kudrat": dict(sat=1.2, contrast=1.06, gain=(0.97, 1.04, 0.98), shadows=(-0.02, 0.02, 0.02)),            # greens
    "samundar": dict(sat=1.18, contrast=1.04, gamma=0.94, gain=(1.0, 1.02, 1.06), lights=(0.04, 0.03, 0.0)),
    "registan": dict(sat=1.08, contrast=1.1, gamma=0.95, gain=(1.1, 1.0, 0.8), lights=(0.06, 0.03, -0.06),
                     vig=0.15),
    "pahad": dict(sat=0.96, contrast=1.08, gain=(0.94, 1.0, 1.08), shadows=(-0.03, 0.0, 0.05)),              # crisp air
    "safar": dict(sat=1.02, contrast=1.06, fade=0.03, gain=(1.03, 1.0, 0.95), shadows=(-0.02, 0.01, 0.03),
                  lights=(0.04, 0.02, -0.03)),
    "chamak": dict(sat=1.12, contrast=1.1, gain=(1.0, 1.0, 1.03), bloom=0.25),                               # shops, mall
    "cinema": dict(sat=0.9, contrast=1.14, gain=(0.95, 0.98, 1.08), shadows=(-0.03, 0.0, 0.06), bloom=0.4,
                   vig=0.4),
    # not places: asked for by name (`LOOK: yaad`) or by the script's own words
    "yaad": dict(sat=0.35, contrast=1.02, fade=0.07, gain=(1.1, 1.0, 0.82), vig=0.4, grain=0.45),            # a memory
    "sapna": dict(sat=1.15, contrast=0.92, fade=0.06, gamma=0.9, gain=(1.03, 0.98, 1.06), bloom=0.7, vig=0.2),
    "noir": dict(sat=0.0, contrast=1.25, vig=0.45, grain=0.5),
}
PLACE_LOOK = {
    "room": "ghar", "living_room": "ghar", "bedroom": "ghar", "balcony": "ghar", "bathroom": "clinic",
    "kitchen": "rasoi", "terrace": "utsav",
    "hospital": "clinic", "medical_store": "clinic", "bank": "daftar", "office": "daftar", "meeting_room": "daftar",
    "school": "padhai", "classroom": "padhai", "coaching": "padhai", "exam_hall": "padhai", "library": "padhai",
    "hostel": "padhai", "school_ground": "kudrat",
    "gully": "sunehra", "chai_tapri": "sunehra", "kirana": "sunehra", "gaon": "sunehra", "dhaba": "sunehra",
    "canteen": "sunehra", "cricket_ground": "kudrat",
    "market": "bazaar", "mithai_shop": "bazaar", "salon": "chamak", "mobile_shop": "chamak", "mall": "chamak",
    "gym": "chamak", "cinema": "cinema",
    "street": "sadak", "bus_stop": "sadak", "railway": "safar", "train": "safar", "bus": "safar", "metro": "safar",
    "plane": "safar", "car": "safar", "auto": "safar",
    "festival_street": "utsav", "mandap": "utsav", "party": "utsav",
    "night_road": "raat", "haunted_house": "darr", "graveyard": "darr", "jungle": "kudrat",
    "jail": "hawalat", "police_station": "hawalat", "court": "daftar",
    "ghar_darwaza": "ghar", "lift": "daftar", "park": "kudrat", "atm": "chamak", "petrol_pump": "sadak",
    "signal": "sadak", "buffet": "utsav", "restaurant": "sunehra", "interview_room": "daftar", "call_center": "daftar",
    "startup_office": "chamak",
    "beach": "samundar", "desert": "registan", "mountain_road": "pahad",
}
# the music's mood on top of the place (multiplies / adds to the place's look)
MOODS = {
    "sad": dict(sat=0.72, contrast=0.97, fade=0.04, gain=(0.97, 1.0, 1.05), vig=0.2),
    "suspense": dict(sat=0.8, contrast=1.12, gain=(0.94, 1.0, 1.04), shadows=(-0.02, 0.02, 0.03), vig=0.35,
                     grain=0.12),
    "festive": dict(sat=1.12, contrast=1.03, bloom=0.2),
    "comedy": dict(sat=1.08, contrast=1.03),
    "pop": dict(sat=1.1, contrast=1.05),
    "lofi": dict(sat=0.9, contrast=0.95, fade=0.05, gain=(1.03, 1.0, 0.97)),
    "soft": dict(sat=0.96, contrast=0.97, fade=0.02),
}
NIGHT = dict(sat=1.0, contrast=1.05, gain=(0.96, 0.99, 1.07), shadows=(-0.03, 0.0, 0.05), lights=(0.05, 0.03, -0.04),
             bloom=0.35, vig=0.2)
TIME_MOD = {"night": NIGHT, "fireflies": NIGHT,
            "rain": dict(sat=0.86, contrast=1.02, fade=0.03, gain=(0.95, 1.0, 1.05)),
            "fog": dict(sat=0.8, contrast=0.92, fade=0.06),
            "snow": dict(sat=0.88, contrast=1.0, gamma=0.95, gain=(0.97, 1.0, 1.05)),
            "sunset": dict(sat=1.1, gain=(1.08, 0.99, 0.9), lights=(0.05, 0.01, -0.04)),
            "evening": dict(sat=1.05, gain=(1.05, 1.0, 0.93), lights=(0.04, 0.01, -0.03)),
            "dawn": dict(sat=0.95, fade=0.03, gain=(1.03, 0.99, 1.02))}
ALIASES = {"home": "ghar", "warm": "ghar", "hospital": "clinic", "office": "daftar", "golden": "sunehra",
           "festive": "utsav", "shaadi": "utsav", "night": "raat", "horror": "darr", "bhoot": "darr", "jail": "hawalat",
           "flashback": "yaad", "memory": "yaad", "purana": "yaad", "sepia": "yaad", "dream": "sapna",
           "bw": "noir", "blackwhite": "noir", "black_white": "noir"}
OFF = ("off", "none", "nahi", "no", "plain")
ALREADY_NIGHT = ("raat", "darr", "utsav", "cinema")       # these looks are lit for the night already


def resolve(word):
    """`LOOK: horror` -> "darr"; "auto" / "off" as they are; None for an unknown word."""
    w = str(word or "").strip().lower().replace("-", "_").replace(" ", "_")
    if w in ("auto", "on", "haan") or w in OFF:
        return "off" if w in OFF else "auto"
    w = ALIASES.get(w, w)
    return w if w in LOOKS else None


def _mix(a, b):
    """Look a with modifier b on top: factors multiply, colours and amounts add."""
    out = dict(NEUTRAL, **a)
    for k, v in b.items():
        if k in ("sat", "contrast", "gamma"):
            out[k] = out[k] * v
        elif k == "gain":
            out[k] = tuple(x * y for x, y in zip(out[k], v))
        elif k in ("shadows", "lights"):
            out[k] = tuple(x + y for x, y in zip(out[k], v))
        elif k in ("bloom", "vig", "grain"):
            out[k] = min(1.0, max(out[k], v) + 0.3 * min(out[k], v))
        else:
            out[k] = out[k] + v
    return out


def choose(place, time=None, mood=None, asked="auto"):
    """(name, parameters) of the look of one place in one video, or (None, None) for no grade.
    asked: "auto" (by the place), "off", or a look's name for every place of the video."""
    asked = asked or "auto"
    if asked == "off":
        return None, None
    name = asked if asked in LOOKS else PLACE_LOOK.get(str(place or ""))
    p = dict(NEUTRAL, **LOOKS[name]) if name else dict(NEUTRAL)
    if time in TIME_MOD and not (time in ("night", "fireflies") and name in ALREADY_NIGHT):
        p = _mix(p, TIME_MOD[time])
    if mood in MOODS:
        p = _mix(p, MOODS[mood])
    if p == NEUTRAL:
        return None, None
    return "+".join(x for x in (name, time if time in TIME_MOD else None, mood if mood in MOODS else None) if x), p


class Grade:
    """A look made ready for one picture size: apply(img, frame number) -> the graded picture."""

    def __init__(self, params, w, h, seed=0):
        p = dict(NEUTRAL, **params)
        self.p, self.w, self.h = p, w, h
        s = p["sat"]                                     # saturation: every channel towards / away from the grey
        r, g, b = 0.299 * (1 - s), 0.587 * (1 - s), 0.114 * (1 - s)
        self.matrix = None if abs(s - 1.0) < 1e-3 else (r + s, g, b, 0, r, g + s, b, 0, r, g, b + s, 0)
        x = np.arange(256) / 255.0
        lut = []
        for ch in range(3):
            y = x ** p["gamma"]
            c = p["contrast"]
            if abs(c - 1.0) > 1e-3:                      # an S-curve: more / less bite without clipping hard
                k = (c - 1.0) * 4.0
                y = y + k * (y - 0.5) * y * (1 - y) * 2.0
            y = y * p["gain"][ch]
            y = y + p["shadows"][ch] * (1 - y) ** 2 + p["lights"][ch] * y ** 2
            y = p["fade"] + y * (1 - p["fade"])
            lut += [int(round(v)) for v in np.clip(y, 0, 1) * 255]
        self.lut = lut
        self.vig = self._vignette(p["vig"]) if p["vig"] > 0.01 else None
        self.noise = self._grain(p["grain"], seed) if p["grain"] > 0.01 else None
        self.bloom = p["bloom"]

    def _vignette(self, k):
        yy, xx = np.mgrid[0:self.h, 0:self.w].astype(np.float32)
        d = np.hypot((xx - self.w / 2) / (self.w * 0.75), (yy - self.h / 2) / (self.h * 0.75))
        m = 1.0 - k * 0.75 * np.clip(d - 0.35, 0, 1) ** 1.6 * 1.9
        return Image.fromarray((np.clip(m, 0, 1) * 255).astype(np.uint8), "L").convert("RGB")

    def _grain(self, k, seed):
        rng = np.random.default_rng(seed)
        amp = 2.0 + 4.0 * k
        tiles = []
        for _ in range(4):                               # four soft plates, played round (cheap for the video file)
            n = rng.normal(0.0, amp, (self.h // 3 + 1, self.w // 3 + 1))
            im = Image.fromarray(np.clip(n + 128, 0, 255).astype(np.uint8), "L").resize((self.w, self.h), Image.BILINEAR)
            tiles.append(im.convert("RGB"))
        return tiles

    def apply(self, img, n=0):
        if self.matrix:
            img = img.convert("RGB", self.matrix)
        img = img.point(self.lut)
        if self.bloom > 0.01:                            # the bright parts glow (lamps, windows, the moon)
            small = img.resize((max(1, self.w // 8), max(1, self.h // 8)), Image.BILINEAR)
            small = small.point([0 if v < 168 else int((v - 168) * 2.2 * self.bloom) for v in range(256)] * 3)
            glow = small.filter(ImageFilter.GaussianBlur(max(1.5, self.w / 8 / 26.0))).resize((self.w, self.h),
                                                                                           Image.BILINEAR)
            img = ImageChops.screen(img, glow)
        if self.vig is not None:
            img = ImageChops.multiply(img, self.vig)
        if self.noise is not None:
            img = ImageChops.add(img, self.noise[(n // 3) % len(self.noise)], 1.0, -128)   # a new plate every 3rd frame
        return img


def for_scene(scene, plan, w, h):
    """The Grade of one scene (one place of a video) or None: its place, the time of its SCENE line, the music's
    mood and what `LOOK:` asked for."""
    meta = scene.get("meta", {}) or {}
    bg = plan.background if isinstance(plan.background, dict) else {"type": plan.background}
    music = scene.get("music") if isinstance(scene.get("music"), dict) else {}
    mood = meta.get("mood") or music.get("style")
    name, p = choose(bg.get("type"), bg.get("time"), mood, meta.get("look", "auto"))
    if not p:
        return None
    g = Grade(p, w, h, seed=zlib.crc32(str(name).encode("utf-8")))
    g.name = name
    return g

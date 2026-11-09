"""Video styles.

    "2d"   (default) the studio's normal look: every place, every feature, exactly as before.
    "2.5d" the same people, script format and features, drawn with depth: every place becomes layered
           (sky / skyline / window views move slower than the floor when the camera moves, depth blur,
           glowing lights, a blurred foreground). The PREMIUM places below are hand-made 2.5D sets with
           even more depth; all the others are made automatically from their 2D drawing (studio.style25d.
           autoset). Only your own picture (image), plain and night_road stay flat.

A scene picks its style with "style": "2.5d" (a script with `STYLE: 2.5d`; the render command and the
web page can also set it).
"""
DEFAULT = "2d"
STYLES = ("2d", "2.5d")
_ALIASES = {"2d": "2d", "flat": "2d", "2.5d": "2.5d", "25d": "2.5d", "2_5d": "2.5d", "2.5": "2.5d"}

# studio place -> hand-made 2.5D preset (studio.style25d.scenery.PRESETS); every other place is made automatically
PLACES_25D = {
    "kitchen": "kitchen_25d",
    "gully": "gali_25d",
    "chai_tapri": "gali_25d",
    "kirana": "gali_25d",
    "terrace": "diwali_rooftop",
    "room": "room_25d",
    "living_room": "room_25d",
    "school": "classroom_25d",
    "classroom": "classroom_25d",
}
# sets with writing on them (shop signs, menus, boards) are never mirrored for a reverse shot (the text would read
# backwards). The 2d look mirrors every place, as it always has.
NO_MIRROR = {"gali_25d", "classroom_25d"} | {
    "auto:" + p for p in ("bus_stop", "railway", "canteen", "exam_hall", "library", "coaching", "party", "gym",
                          "hospital", "police_station", "bank")}
# the light each preset is painted in; another SCENE time (night, rain...) re-lights it
NATIVE_TIME = {"kitchen_25d": "day", "gali_25d": "sunset", "diwali_rooftop": "night", "room_25d": "day",
               "classroom_25d": "day"}


def normalize(value):
    key = str(value).strip().lower()
    if key not in _ALIASES:
        raise ValueError("unknown style %r: use \"2d\" or \"2.5d\"" % (value,))
    return _ALIASES[key]


def scene_style(scene):
    meta = scene.get("meta") or {}
    return normalize(scene.get("style") or meta.get("style") or DEFAULT)


FLAT_IN_25D = {"image", "plain", "night_road"}       # stay as they are in 2.5D too


def has_depth(kind):
    """True when this place is drawn with depth in 2.5D (a hand-made set, or made automatically from its drawing)."""
    if kind in PLACES_25D:
        return True
    if not kind or kind in FLAT_IN_25D:
        return False
    from .style25d.autoset import place_function
    return bool(place_function(kind))


def preset_for(scene):
    """The 2.5D set this (single-place) scene uses: a hand-made preset name, "auto:<place>", or None (2d style,
    or a place that stays flat)."""
    if scene_style(scene) != "2.5d":
        return None
    bg = scene.get("background") or {}
    kind = bg.get("type") if isinstance(bg, dict) else bg
    if kind in PLACES_25D:
        return PLACES_25D[kind]
    return "auto:" + kind if has_depth(kind) else None

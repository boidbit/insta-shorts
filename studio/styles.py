"""Video styles.

    "2d"   (default) the studio's normal look: every place, every feature, exactly as before.
    "2.5d" the same people, script format and features, but these places are drawn as layered 2.5D sets
           (parallax between far and near layers when the camera moves, depth blur, glowing lights, a
           blurred foreground). Every other place still looks like 2d.

A scene picks its style with "style": "2.5d" (a script with `STYLE: 2.5d`; the render command and the
web page can also set it).
"""
DEFAULT = "2d"
STYLES = ("2d", "2.5d")
_ALIASES = {"2d": "2d", "flat": "2d", "2.5d": "2.5d", "25d": "2.5d", "2_5d": "2.5d", "2.5": "2.5d"}

# studio place -> 2.5D preset (studio.style25d.scenery.PRESETS)
PLACES_25D = {
    "kitchen": "kitchen_25d",
    "gully": "gali_25d",
    "chai_tapri": "gali_25d",
    "kirana": "gali_25d",
    "terrace": "diwali_rooftop",
}
# sets with writing on them (shop signs) are never mirrored for a reverse shot (the text would read backwards)
NO_MIRROR = {"gali_25d"}
# the light each preset is painted in; another SCENE time (night, rain...) re-lights it
NATIVE_TIME = {"kitchen_25d": "day", "gali_25d": "sunset", "diwali_rooftop": "night"}


def normalize(value):
    key = str(value).strip().lower()
    if key not in _ALIASES:
        raise ValueError("unknown style %r: use \"2d\" or \"2.5d\"" % (value,))
    return _ALIASES[key]


def scene_style(scene):
    meta = scene.get("meta") or {}
    return normalize(scene.get("style") or meta.get("style") or DEFAULT)


def preset_for(scene):
    """The 2.5D preset this (single-place) scene uses, or None (2d style, or a place without a 2.5D set)."""
    if scene_style(scene) != "2.5d":
        return None
    bg = scene.get("background") or {}
    kind = bg.get("type") if isinstance(bg, dict) else bg
    return PLACES_25D.get(kind)

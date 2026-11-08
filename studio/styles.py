"""The two video styles and the rules that keep them apart.

    "style": "2d"    classic desi stickman on flat backgrounds (the default: old scenes never change)
    "style": "2.5d"  layered parallax backgrounds, toon bodies, real camera, lighting, objects + fx

Shared by both (studio core): scene format + timeline, Hindi TTS + lip-sync, music/sfx, captions and
speech bubbles, actions, faces/expressions, hair/accessories, props, the ffmpeg pipeline, the AI director.
Only in 2d:   studio/style2d/   (stick body, flat backgrounds, crop-zoom camera)
Only in 2.5d: studio/style25d/  (toon body, layered scenery, objects, fx, lighting, perspective)
"""
DEFAULT = "2d"
_ALIASES = {"2d": "2d", "flat": "2d", "2.5d": "2.5d", "25d": "2.5d", "2_5d": "2.5d", "2.5": "2.5d"}

BACKGROUNDS = {
    "2d": ("kitchen", "room", "street", "school", "night_road", "plain", "image"),
    "2.5d": ("diwali_rooftop", "kitchen_25d", "gali_25d", "plain", "image"),
}
BODY = {"2d": "stick", "2.5d": "toon"}
ONLY_25D_SCENE_KEYS = ("objects", "light", "perspective")
ONLY_25D_EVENT_KEYS = ("fx", "fx_stop", "object")


def normalize(value):
    key = str(value).strip().lower()
    if key not in _ALIASES:
        raise ValueError("unknown style %r: use \"2d\" or \"2.5d\"" % (value,))
    return _ALIASES[key]


def scene_style(scene):
    """Style of a loaded scene dict: top-level "style" (or meta.style); default 2d."""
    meta = scene.get("meta") or {}
    return normalize(scene.get("style", meta.get("style", DEFAULT)))


def problems(scene):
    """Human-readable reasons why the scene mixes the two styles (empty list = clean)."""
    try:
        st = scene_style(scene)
    except ValueError as e:
        return [str(e)]
    out = []
    bg = scene.get("background", {"type": "plain"})
    bgt = bg.get("type", "plain") if isinstance(bg, dict) else bg
    if bgt not in BACKGROUNDS[st]:
        other = [s for s in BACKGROUNDS if s != st and bgt in BACKGROUNDS[s]]
        hint = " (that is a %s background: set \"style\": \"%s\")" % (other[0], other[0]) if other else ""
        out.append("background %r is not available in style %s%s; use one of: %s"
                   % (bgt, st, hint, ", ".join(BACKGROUNDS[st])))
    for name, spec in (scene.get("characters") or {}).items():
        body = spec.get("body")
        if body is not None and body != BODY[st]:
            out.append("character %s: body %r belongs to the other style (style %s uses %r; just leave \"body\" out)"
                       % (name, body, st, BODY[st]))
    if st == "2d":
        for key in ONLY_25D_SCENE_KEYS:
            if key in scene:
                out.append("%r is a 2.5d feature; set \"style\": \"2.5d\" or remove it" % key)
        for ev in scene.get("timeline", []) or []:
            for key in ONLY_25D_EVENT_KEYS:
                if key in ev:
                    out.append("timeline %r is a 2.5d feature; set \"style\": \"2.5d\" or remove it" % key)
                    break
    return out


def check(scene):
    probs = problems(scene)
    if probs:
        raise ValueError("style check failed: " + "; ".join(probs))
    return scene_style(scene)


def renderer_class(style):
    style = normalize(style)
    if style == "2d":
        from .style2d.renderer import Renderer2D
        return Renderer2D
    from .style25d.renderer import Renderer25D
    return Renderer25D

"""Scene checker: finds typos and unknown names before rendering (unknown names otherwise fall back silently).

    python -m studio.lint scenes/my_scene.json
"""
import os
import sys

from . import actions, audio, effects, multi, objects, ui
from .animals import ANIMALS
from .backgrounds import FG_PROPS
from .characters import (ACCESSORIES, EXPRESSIONS, HAIR_STYLES, OUTFITS, PALETTE, PRESETS, PROPS, SKIN_TONES)
from .locations import LOCATIONS
from .text import STYLES
from .util import asset_path, expand_scene, load_scene

BACKGROUNDS = sorted({"kitchen", "room", "living_room", "street", "school", "classroom", "night_road", "plain",
                      "image"} | set(LOCATIONS))
TIMES = ("day", "night", "evening", "sunset", "dawn", "rain")
ANIMAL_ACTIONS = {"idle", "walk", "run", "sit", "lie_down", "lie", "sleep", "sleep_lie", "jump", "bark", "meow", "moo",
                  "speak", "caw", "wag", "eat", "fly", "peck", "shock", "none", "stand"}
STATES = {"door": ("open", "closed"), "window": ("day", "night"), "tv": ("on", "off"), "lamp": ("on", "off"),
          "tubelight": ("on", "off"), "fan": ("on", "off"), "fridge": ("open", "closed"),
          "cupboard": ("open", "closed"), "phone": ("ringing", "idle"), "bush": ("rustle", "idle")}
EVENT_KEYS = {"t", "who", "wait", "hold", "say", "speak", "voice", "tts", "duration", "bubble", "move", "sfx", "volume",
              "overlay", "camera", "fx", "object", "state", "lights", "slowmo", "freeze", "at", "throw_prop", "flight",
              "arc", "hit", "hit_sfx", "hit_text", "seat", "on_dx", "emotion", "action", "expression", "prop", "label",
              "look", "facing", "style", "point", "dir", "lean", "speed", "intensity", "hands", "tint", "on", "visible",
              "ride", "interrupt", "comment", "_comment"}
CHAR_KEYS = {"color", "slot", "x", "y", "scale", "facing", "accessories", "cap_color", "voice", "prop", "prop_hand",
             "expression", "look", "phase", "preset", "hair", "hair_color", "skin", "body", "head_k", "outfit",
             "outfit_color", "barefoot", "kind", "turban_color", "moustache_color", "visible", "flies", "comment"}
SCENE_KEYS = {"name", "about", "vars", "extends", "meta", "background", "music", "characters", "caption", "overlays",
              "timeline", "objects", "effects", "ambience", "transition", "file", "scenes", "split", "comment"}


def _sfx_ok(name):
    return name in audio.SFX_NAMES or os.path.isfile(asset_path(name) or "")


def lint(scene, where=""):
    """Return a list of human-readable warnings for one scene dict (already expanded)."""
    W = []
    pre = (where + ": ") if where else ""

    def w(msg):
        W.append(pre + msg)

    if "scenes" in scene:
        for k in scene:
            if k not in SCENE_KEYS:
                w("unknown top-level key %r" % k)
        for i, raw in enumerate(scene["scenes"]):
            tr = raw.get("transition")
            if tr:
                typ = tr if isinstance(tr, str) else tr.get("type")
                if typ not in multi.TRANSITIONS:
                    w("scene %d: unknown transition %r (have: %s)" % (i + 1, typ, ", ".join(multi.TRANSITIONS)))
            parts = raw["split"] if "split" in raw else [raw]
            for j, part in enumerate(parts):
                try:
                    sub = expand_scene(dict(part))
                except Exception as e:      # noqa: BLE001
                    w("scene %d: cannot load (%s)" % (i + 1, e))
                    continue
                sub.pop("transition", None)
                W += lint(sub, "scene %d%s" % (i + 1, "" if len(parts) == 1 else "/%s" % "ab"[j]))
        return W

    for k in scene:
        if k not in SCENE_KEYS:
            w("unknown key %r" % k)
    bg = scene.get("background", {})
    bg = {"type": bg} if isinstance(bg, str) else (bg or {})
    if bg.get("type", "plain") not in BACKGROUNDS:
        w("unknown background %r" % bg.get("type"))
    if bg.get("time") and bg["time"] not in TIMES:
        w("unknown background time %r (have: %s)" % (bg["time"], ", ".join(TIMES)))
    fg = bg.get("foreground", [])
    for f in ([fg] if isinstance(fg, str) else fg or []):
        if f not in FG_PROPS:
            w("unknown foreground prop %r" % f)
    m = scene.get("music") or {}
    if isinstance(m, dict) and m.get("type") == "beat" and m.get("style", m.get("mood", "desi")) not in audio.MOODS:
        w("unknown music style %r (have: %s)" % (m.get("style"), ", ".join(audio.MOODS)))
    amb = scene.get("ambience")
    for a in (amb if isinstance(amb, list) else [amb] if amb else []):
        a = a if isinstance(a, str) else a.get("type")
        if a not in audio.AMBIENCE:
            w("unknown ambience %r (have: %s)" % (a, ", ".join(audio.AMBIENCE)))

    chars = scene.get("characters", {}) or {}
    kinds = {}
    for name, c in chars.items():
        for k in c:
            if k not in CHAR_KEYS:
                w("character %s: unknown key %r" % (name, k))
        if c.get("preset") and c["preset"] not in PRESETS:
            w("character %s: unknown preset %r (have: %s)" % (name, c["preset"], ", ".join(PRESETS)))
        kind = c.get("kind")
        kinds[name] = kind
        if kind and kind not in ANIMALS and kind != "monkey":
            w("character %s: unknown kind %r (have: monkey, %s)" % (name, kind, ", ".join(ANIMALS)))
        col = c.get("color")
        if isinstance(col, str) and col not in PALETTE:
            w("character %s: unknown color %r" % (name, col))
        if c.get("hair") and c["hair"] not in HAIR_STYLES:
            w("character %s: unknown hair %r (have: %s)" % (name, c["hair"], ", ".join(HAIR_STYLES)))
        if isinstance(c.get("skin"), str) and c["skin"] not in SKIN_TONES:
            w("character %s: unknown skin %r (have: %s)" % (name, c["skin"], ", ".join(SKIN_TONES)))
        for a in c.get("accessories", []):
            if a not in ACCESSORIES:
                w("character %s: unknown accessory %r" % (name, a))
        out = c.get("outfit", [])
        for o in ([out] if isinstance(out, str) else out):
            if o not in OUTFITS:
                w("character %s: unknown outfit %r" % (name, o))
        if c.get("prop") and c["prop"] not in PROPS:
            w("character %s: unknown prop %r" % (name, c["prop"]))

    objs = {}
    for i, ob in enumerate(scene.get("objects", [])):
        oid = ob.get("id", "%s%d" % (ob.get("type", "obj"), i + 1))
        objs[oid] = ob.get("type")
        if ob.get("type") not in objects.SPEC:
            w("object %s: unknown type %r" % (oid, ob.get("type")))
        st = ob.get("state")
        if st and ob.get("type") in STATES and st not in STATES[ob["type"]]:
            w("object %s: unknown state %r (have: %s)" % (oid, st, ", ".join(STATES[ob["type"]])))

    for o in scene.get("overlays", []) + ([scene["caption"]] if isinstance(scene.get("caption"), dict) else []):
        if o.get("type") and o["type"] not in ui.TYPES:
            w("overlay: unknown type %r (have: %s)" % (o["type"], ", ".join(ui.TYPES)))
        if o.get("style") and o["style"] not in STYLES:
            w("overlay: unknown style %r (have: %s)" % (o["style"], ", ".join(STYLES)))
    for fx in scene.get("effects", []):
        typ = fx if isinstance(fx, str) else fx.get("type")
        if typ not in effects.ALL:
            w("effect: unknown type %r" % typ)

    names = set(chars)
    for i, ev in enumerate(scene.get("timeline", [])):
        at = "timeline[%d]%s" % (i, (" t=%s" % ev["t"]) if "t" in ev else "")
        for k in ev:
            if k not in EVENT_KEYS:
                w("%s: unknown key %r" % (at, k))
        who = ev.get("who")
        whos = list(names) if who in (None, "all", "everyone") else ([who] if isinstance(who, str) else list(who))
        for n in whos:
            if n not in names:
                w("%s: unknown character %r" % (at, n))
        act = ev.get("action")
        if act:
            for n in whos:
                if n in names and kinds.get(n) in ANIMALS:
                    if act not in ANIMAL_ACTIONS:
                        w("%s: %s is a %s; action %r not available (have: %s)" % (
                            at, n, kinds[n], act, ", ".join(sorted(ANIMAL_ACTIONS))))
                elif act not in actions.ACTIONS:
                    w("%s: unknown action %r" % (at, act))
        ex = ev.get("expression", ev.get("emotion"))
        if ex and ex not in EXPRESSIONS:
            w("%s: unknown expression %r" % (at, ex))
        if ev.get("prop") and ev["prop"] not in PROPS:
            w("%s: unknown prop %r" % (at, ev["prop"]))
        if "say" in ev and not ev.get("speak") and ev.get("tts", True):
            w("%s: line %r has no 'speak' (Devanagari for the Hindi voice)" % (at, str(ev["say"])[:30]))
        if ev.get("sfx") and not _sfx_ok(ev["sfx"]):
            w("%s: unknown sfx %r" % (at, ev["sfx"]))
        for fx in (ev["fx"] if isinstance(ev.get("fx"), list) else [ev["fx"]] if ev.get("fx") else []):
            typ = fx if isinstance(fx, str) else fx.get("type")
            if typ not in effects.ALL:
                w("%s: unknown fx %r" % (at, typ))
        for key in ("at", "look"):
            v = ev.get(key)
            if isinstance(v, str) and v not in names and v not in ("left", "right"):
                w("%s: %s %r is not a character" % (at, key, v))
        if ev.get("on") and ev["on"] not in objs:
            w("%s: on %r is not an object id" % (at, ev["on"]))
        if ev.get("ride"):
            if ev["ride"] not in objs:
                w("%s: ride %r is not an object id" % (at, ev["ride"]))
            elif objs[ev["ride"]] not in objects.VEHICLES:
                w("%s: %r is a %s, not a vehicle" % (at, ev["ride"], objs[ev["ride"]]))
        if "object" in ev:
            for oid in (ev["object"] if isinstance(ev["object"], list) else [ev["object"]]):
                if oid not in objs:
                    w("%s: object %r not in \"objects\"" % (at, oid))
                elif ev.get("state") and objs[oid] in STATES and ev["state"] not in STATES[objs[oid]]:
                    w("%s: object %s has no state %r (have: %s)" % (at, oid, ev["state"], ", ".join(STATES[objs[oid]])))
        if isinstance(ev.get("overlay"), dict):
            o = ev["overlay"]
            if o.get("type") and o["type"] not in ui.TYPES:
                w("%s: unknown overlay type %r" % (at, o["type"]))
            if o.get("style") and o["style"] not in STYLES:
                w("%s: unknown overlay style %r" % (at, o["style"]))
    return W


def vocabulary():
    """Markdown list of every name the renderer understands (appended to the AI director prompt)."""
    acts = sorted(actions.ACTIONS)
    return "\n".join([
        "# Full vocabulary (generated from the code - use ONLY these names)",
        "- backgrounds: " + ", ".join(BACKGROUNDS) + ". background.time: " + ", ".join(TIMES),
        "- foreground props (background.foreground): " + ", ".join(sorted(FG_PROPS)),
        "- actions (people/monkey): " + ", ".join(acts),
        "- animal kinds: " + ", ".join(ANIMALS) + " (actions: " + ", ".join(sorted(ANIMAL_ACTIONS)) + "); monkey uses people actions",
        "- expressions: " + ", ".join(EXPRESSIONS),
        "- held props: " + ", ".join(PROPS),
        "- character presets: " + ", ".join(PRESETS) + "; hair: " + ", ".join(HAIR_STYLES) + "; skin: " +
        ", ".join(SKIN_TONES) + "; body: slim, belly; outfit: " + ", ".join(OUTFITS) + "; accessories: " +
        ", ".join(ACCESSORIES) + "; colors: " + ", ".join(PALETTE),
        "- objects (scene \"objects\", by id): " + ", ".join(sorted(objects.SPEC)) + ". States: " +
        "; ".join("%s=%s" % (k, "/".join(v)) for k, v in STATES.items()),
        "- vehicles (objects you can \"ride\"): " + ", ".join(objects.VEHICLES),
        "- effects (\"fx\"): " + ", ".join(sorted(effects.ALL)),
        "- sfx: " + ", ".join(audio.SFX_NAMES),
        "- music styles: " + ", ".join(audio.MOODS) + "; ambience: " + ", ".join(audio.AMBIENCE),
        "- overlay styles: " + ", ".join(STYLES) + "; UI overlay types: " + ", ".join(ui.TYPES),
        "- transitions (multi-scene): " + ", ".join(multi.TRANSITIONS),
    ])


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    bad = 0
    for path in argv:
        ws = lint(load_scene(path))
        for x in ws:
            print("%s: %s" % (path, x))
        bad += len(ws)
        if not ws:
            print("%s: ok" % path)
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()

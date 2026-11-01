import copy
import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Logical canvas: everything is authored for 1080x1920 and scaled at render time.
LW, LH = 1080, 1920


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def lerp(a, b, t):
    return a + (b - a) * t


def ease_out(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_in(t):
    t = clamp(t)
    return t * t


def ease_in_out(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def ease_out_back(t, s=1.9):
    t = clamp(t) - 1
    return t * t * ((s + 1) * t + s) + 1


def deep_merge(base, over):
    """Dicts merge recursively, everything else (lists, scalars) is replaced."""
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def subst(obj, variables):
    """Replace {name} in every string with variables[name]."""
    if isinstance(obj, str):
        for k, v in variables.items():
            obj = obj.replace("{" + k + "}", str(v))
        return obj
    if isinstance(obj, list):
        return [subst(x, variables) for x in obj]
    if isinstance(obj, dict):
        return {k: subst(v, variables) for k, v in obj.items()}
    return obj


def _read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_template(name):
    if os.path.isfile(name):
        return name
    for cand in (os.path.join(ROOT, "templates", name),
                 os.path.join(ROOT, "templates", name + ".json")):
        if os.path.isfile(cand):
            return cand
    raise FileNotFoundError("template not found: %s" % name)


def load_scene(path):
    """Load a scene file. If it has "extends", merge it over that template and
    substitute {vars} (template defaults < scene vars)."""
    scene = _read_json(path)
    if "extends" in scene:
        tpl = _read_json(resolve_template(scene["extends"]))
        variables = dict(tpl.get("vars", {}))
        variables.update(scene.get("vars", {}))
        merged = deep_merge(tpl, {k: v for k, v in scene.items() if k != "extends"})
        merged["vars"] = variables
        scene = subst(merged, variables)
        scene.pop("extends", None)
    else:
        variables = scene.get("vars", {})
        if variables:
            scene = subst(scene, variables)
    return scene


def asset_path(p):
    """Resolve an asset path relative to the repo root unless absolute."""
    if not p:
        return None
    if os.path.isabs(p):
        return p
    return os.path.join(ROOT, p)

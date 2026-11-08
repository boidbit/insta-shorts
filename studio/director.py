"""AI director: plain-language instruction -> scene.json (via the Anthropic API).

    export ANTHROPIC_API_KEY=...
    python -m studio.director "3 dost, ek ko chai pe bill dena hai" -o scenes/generated/chai.json
    python -m studio.director --style 2.5d "gali me chai wala udhaar" -o scenes/generated/gali.json

Each style has its own prompt (DIRECTOR_PROMPT.md for 2d, DIRECTOR_PROMPT_25D.md for 2.5d), so the model
only ever sees the options of the style you asked for.
"""
import argparse
import json
import os
import re
import sys

from . import actions, styles
from .characters import EXPRESSIONS, PALETTE
from .scene import compile_scene
from .util import ROOT, load_scene

DEFAULT_MODEL = "claude-sonnet-5-5"
PROMPTS = {"2d": "DIRECTOR_PROMPT.md", "2.5d": "DIRECTOR_PROMPT_25D.md"}


def extract_json(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    a, b = text.find("{"), text.rfind("}")
    if a < 0 or b < a:
        raise ValueError("no JSON object in model output")
    return json.loads(text[a:b + 1])


def problems(scene_dict, tmp_path, style="2d"):
    """Return a list of human-readable problems (empty list = good)."""
    out = []
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(scene_dict, f, ensure_ascii=False)
        scene = load_scene(tmp_path)
    except Exception as e:  # noqa: BLE001
        return ["scene does not load: %r" % (e,)]
    mix = styles.problems(scene)
    if mix:
        return mix
    got = styles.scene_style(scene)
    if got != styles.normalize(style):
        return ["this must be a %s scene but it is %s%s" % (style, got,
                ' (add "style": "2.5d")' if styles.normalize(style) == "2.5d" else ' (remove "style")')]
    try:
        plan = compile_scene(scene, use_tts=False)
    except Exception as e:  # noqa: BLE001
        return ["scene does not compile: %r" % (e,)]
    for name, c in plan.chars.items():
        col = c.spec.get("color", "blue")
        if isinstance(col, str) and col not in PALETTE:
            out.append("character %s: unknown color %r" % (name, col))
        for ev in c.events:
            if "action" in ev and ev["action"] not in actions.ACTIONS:
                out.append("character %s: unknown action %r" % (name, ev["action"]))
            if "expression" in ev and ev["expression"] not in EXPRESSIONS:
                out.append("character %s: unknown expression %r" % (name, ev["expression"]))
    if plan.duration > 40:
        out.append("video too long (%.0fs); keep it under 25s" % plan.duration)
    for raw in scene.get("timeline", []):
        if "say" in raw and not raw.get("speak"):
            out.append("line %r has no 'speak' (Devanagari) text" % raw["say"][:30])
    return out


def call_model(client, model, system, messages):
    resp = client.messages.create(model=model, max_tokens=6000, system=system, messages=messages)
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


def direct(instruction, model=DEFAULT_MODEL, client=None, tmp_path=None, max_tries=3, style="2d"):
    style = styles.normalize(style)
    with open(os.path.join(ROOT, PROMPTS[style]), encoding="utf-8") as f:
        system = f.read()
    if client is None:
        import anthropic
        client = anthropic.Anthropic()
    tmp_path = tmp_path or os.path.join(ROOT, ".cache", "_director_check.json")
    os.makedirs(os.path.dirname(tmp_path), exist_ok=True)
    messages = [{"role": "user", "content": instruction}]
    last = None
    for attempt in range(max_tries):
        text = call_model(client, model, system, messages)
        try:
            scene = extract_json(text)
            probs = problems(scene, tmp_path, style)
        except Exception as e:  # noqa: BLE001
            scene, probs = None, ["output was not valid JSON: %r" % (e,)]
        if not probs:
            return scene
        last = probs
        print("  [director] attempt %d had problems: %s" % (attempt + 1, "; ".join(probs)), file=sys.stderr)
        messages += [{"role": "assistant", "content": text},
                     {"role": "user", "content": "Fix these problems and return the full corrected JSON only:\n- "
                      + "\n- ".join(probs)}]
    raise SystemExit("director could not produce a valid scene: %s" % last)


def slug(text):
    s = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return (s[:40] or "scene")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("instruction")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--model", default=os.environ.get("DIRECTOR_MODEL", DEFAULT_MODEL))
    ap.add_argument("--style", default="2d", help="2d (classic stickman, default) or 2.5d")
    args = ap.parse_args(argv)
    scene = direct(args.instruction, args.model, style=args.style)
    out = args.out or os.path.join(ROOT, "scenes", "generated", slug(args.instruction) + ".json")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(scene, f, ensure_ascii=False, indent=2)
    print(out)


if __name__ == "__main__":
    main()

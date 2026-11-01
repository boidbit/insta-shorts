"""AI director: plain-language idea (or a script) -> scene.json, or -> a readable script.

    export ANTHROPIC_API_KEY=...        # or GEMINI_API_KEY=... (Google AI Studio free tier)
    python -m studio.director "3 dost, ek ko chai pe bill dena hai" -o scenes/generated/chai.json
    python -m studio.director --hook pov "mummy ne doodh mangaya"
    python -m studio.director --count 3            # no idea given: AI picks topics, 3 different hooks
    python -m studio.director --script-only "dadi aur naya phone" -o draft.txt    # script for a human to approve

Every result is checked (loads, compiles, known looks/actions/expressions, hook in
the first second, length) and sent back to the model with the problems until it
is clean. Next to every scene a `.post.txt` with the Instagram caption + hashtags
is written.
"""
import argparse
import json
import os
import random
import re
import sys
import urllib.error
import urllib.request

from . import actions, hooks
from .characters import ACCESSORIES, EXPRESSIONS, HAIR_STYLES, LOOKS, OUTFITS, PALETTE
from .scene import compile_scene, split_scenes, static_overlays
from .util import ROOT, load_scene

DEFAULT_MODEL = "claude-sonnet-5-5"
GEMINI_MODELS = ["gemini-flash-latest", "gemini-2.5-flash", "gemini-2.0-flash"]   # first that exists wins
BACKGROUNDS = {"kitchen", "room", "street", "school", "night_road", "plain", "image"}
MAX_SECONDS = 30.0


# ------------------------------------------------------------------ model providers
def _adopt_generic_key():
    """AI_API_KEY may hold either kind of key: route it by its prefix."""
    k = os.environ.get("AI_API_KEY", "").strip()
    if k.startswith("sk-ant-") and not os.environ.get("ANTHROPIC_API_KEY"):
        os.environ["ANTHROPIC_API_KEY"] = k
    elif k.startswith("AIza") and not os.environ.get("GEMINI_API_KEY"):
        os.environ["GEMINI_API_KEY"] = k


def provider_name(explicit=None):
    _adopt_generic_key()
    p = explicit or os.environ.get("DIRECTOR_PROVIDER")
    if p:
        return p
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        return "gemini"
    return None


class AnthropicLLM:
    def __init__(self, model=None, client=None):
        self.model = model or os.environ.get("DIRECTOR_MODEL", DEFAULT_MODEL)
        if client is None:
            import anthropic
            client = anthropic.Anthropic()
        self.client = client

    def __call__(self, system, messages, json_mode=True):
        resp = self.client.messages.create(model=self.model, max_tokens=8000, system=system, messages=messages)
        return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


class GeminiLLM:
    URL = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent"

    def __init__(self, model=None, key=None):
        chosen = model or os.environ.get("GEMINI_MODEL")
        self.models = [chosen] if chosen else list(GEMINI_MODELS)
        self.key = key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not self.key:
            raise SystemExit("GEMINI_API_KEY is not set")

    def __call__(self, system, messages, json_mode=True):
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
                         for m in messages],
            "generationConfig": {"responseMimeType": "application/json" if json_mode else "text/plain",
                                 "maxOutputTokens": 8192, "temperature": 0.9},
        }
        while True:
            req = urllib.request.Request(self.URL % self.models[0], data=json.dumps(body).encode("utf-8"),
                                         headers={"Content-Type": "application/json", "x-goog-api-key": self.key})
            try:
                with urllib.request.urlopen(req, timeout=180) as r:
                    data = json.loads(r.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as e:
                if e.code == 404 and len(self.models) > 1:     # model retired / renamed: try the next one
                    self.models.pop(0)
                    continue
                raise SystemExit("Gemini error %d (%s): %s" % (e.code, self.models[0],
                                                              e.read().decode("utf-8", "replace")[:400]))
        parts = (data.get("candidates") or [{}])[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts)


def make_llm(provider=None, model=None):
    p = provider_name(provider)
    if p == "anthropic":
        return AnthropicLLM(model)
    if p == "gemini":
        return GeminiLLM(model)
    raise SystemExit("No AI key: set ANTHROPIC_API_KEY, or GEMINI_API_KEY (free key at aistudio.google.com)")


# ------------------------------------------------------------------ checking
def extract_json(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    a, b = text.find("{"), text.rfind("}")
    if a < 0 or b < a:
        raise ValueError("no JSON object in model output")
    return json.loads(text[a:b + 1])


def extract_script(text):
    text = re.sub(r"^```\w*\s*|\s*```$", "", text.strip())
    a = text.upper().find("HOOK:")
    return (text[a:] if a > 0 else text).strip() + "\n"


def _char_problems(name, spec):
    out = []
    checks = (("look", LOOKS), ("hair", HAIR_STYLES), ("outfit", OUTFITS))
    for key, known in checks:
        if key in spec and spec[key] not in known:
            out.append("character %s: unknown %s %r" % (name, key, spec[key]))
    for key in ("color", "accent", "pants", "cap_color"):
        v = spec.get(key)
        if isinstance(v, str) and v not in PALETTE:
            out.append("character %s: unknown %s color %r" % (name, key, v))
    for a in spec.get("accessories", []):
        if a not in ACCESSORIES:
            out.append("character %s: unknown accessory %r" % (name, a))
    return out


def problems(scene_dict, tmp_path):
    """Return a list of human-readable problems (empty list = good)."""
    out = []
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(scene_dict, f, ensure_ascii=False)
        scene = load_scene(tmp_path)
        subs = split_scenes(scene)
        plans = [compile_scene(s, use_tts=False) for s in subs]
    except Exception as e:  # noqa: BLE001
        return ["scene does not load/compile: %r" % (e,)]

    for i, (sub, plan) in enumerate(zip(subs, plans)):
        where = "scene %d: " % (i + 1) if len(subs) > 1 else ""
        bg = sub.get("background", {})
        bgt = bg.get("type") if isinstance(bg, dict) else bg
        if bgt and bgt not in BACKGROUNDS:
            out.append(where + "unknown background %r" % bgt)
        if len(plan.chars) > 3:
            out.append(where + "more than 3 characters")
        for name, c in plan.chars.items():
            out += [where + p for p in _char_problems(name, c.spec)]
            for ev in c.events:
                if "action" in ev and ev["action"] not in actions.ACTIONS:
                    out.append(where + "character %s: unknown action %r" % (name, ev["action"]))
                if "expression" in ev and ev["expression"] not in EXPRESSIONS:
                    out.append(where + "character %s: unknown expression %r" % (name, ev["expression"]))
        for raw in sub.get("timeline", []):
            if "say" in raw and not raw.get("speak"):
                out.append(where + "line %r has no 'speak' (Devanagari) text" % str(raw["say"])[:30])

    total = sum(p.duration for p in plans)
    if total > MAX_SECONDS:
        out.append("video too long (%.0fs); keep it between 10 and 25 seconds" % total)

    # hook: text + a hook overlay at t=0 + something happening in the first second
    if not scene.get("hook"):
        out.append("missing top-level 'hook' text")
    first = static_overlays(scene) + plans[0].overlays
    if not any(o.get("style") == "hook" and float(o.get("from", 0)) <= 0.3 for o in first):
        out.append("no overlay with style 'hook' starting at t=0 (the hook must be on screen in the first second)")
    p0 = plans[0]
    first_line = min([sp["start"] for sp in p0.speech] or [99])
    busy = any(ev["t"] <= 0.6 and ev.get("action") not in (None, "idle", "none", "stand")
               for c in p0.chars.values() for ev in c.events)
    if first_line > 1.2 and not busy:
        out.append("nothing happens in the first second: start the first line by t=0.6 or open on a big action + sfx")

    post = scene.get("post") or {}
    if not post.get("caption"):
        out.append("missing post.caption (Instagram caption)")
    return out


def script_problems(text, tmp_path):
    """Problems of a plain-text script (format + everything `problems` checks)."""
    from .script import parse_script
    try:
        scene, warnings = parse_script(text)
    except Exception as e:  # noqa: BLE001
        return ["script could not be read: %s" % e]
    out = list(warnings)
    if not re.search(r"^CAPTION:", text, re.M | re.I):
        out.append("missing CAPTION: line")
    if not re.search(r"^CTA:", text, re.M | re.I):
        out.append("missing CTA: line")
    return out + [p for p in problems(scene, tmp_path) if "post.caption" not in p]


# ------------------------------------------------------------------ directing
def request_text(instruction, topic=None):
    if instruction and instruction.strip():
        return instruction.strip()
    return ("Koi idea nahi diya. Topic: %s. Is topic pe ek original, relatable desi comedy short khud socho "
            "(purane cliche jokes se bacho)." % topic)


def _iterate(llm, system, first_msg, parse, check, json_mode, log, max_tries):
    messages = [{"role": "user", "content": first_msg}]
    last = None
    for attempt in range(max_tries):
        text = llm(system, messages, json_mode=json_mode)
        try:
            result = parse(text)
            probs = check(result)
        except Exception as e:  # noqa: BLE001
            result, probs = None, ["output could not be read: %r" % (e,)]
        if not probs:
            return result
        last = probs
        log("  [director] attempt %d had problems: %s" % (attempt + 1, "; ".join(probs)))
        messages += [{"role": "assistant", "content": text},
                     {"role": "user", "content": "Fix these problems and return the full corrected %s only:\n- "
                      % ("JSON" if json_mode else "script") + "\n- ".join(probs)}]
    raise SystemExit("director could not produce a valid result: %s" % last)


def _setup(hook_style, llm, tmp_path, rng, log, prompt_file, fmt):
    rng = rng or random.Random()
    log = log or (lambda m: print(m, file=sys.stderr))
    with open(os.path.join(ROOT, prompt_file), encoding="utf-8") as f:
        base = f.read()
    key, _hook = hooks.pick(hook_style, rng)
    log("  [director] hook style: %s" % key)
    tmp_path = tmp_path or os.path.join(ROOT, ".cache", "_director_check_%d.json" % os.getpid())
    os.makedirs(os.path.dirname(tmp_path), exist_ok=True)
    return base + "\n\n" + hooks.prompt_block(key, fmt), key, llm or make_llm(), tmp_path, rng, log


def direct(instruction="", hook_style="auto", llm=None, tmp_path=None, max_tries=3, rng=None, log=None):
    """Return a checked scene dict. `llm(system, messages, json_mode) -> text`."""
    system, key, llm, tmp_path, rng, log = _setup(hook_style, llm, tmp_path, rng, log, "DIRECTOR_PROMPT.md", "json")
    scene = _iterate(llm, system, request_text(instruction, hooks.random_topic(rng)), extract_json,
                     lambda s: problems(s, tmp_path), True, log, max_tries)
    scene.setdefault("meta", {})["hook_style"] = key
    return scene


def write_script(instruction="", hook_style="auto", llm=None, tmp_path=None, max_tries=3, rng=None, log=None):
    """Return a checked plain-text script (for a human to read, edit and approve)."""
    system, _key, llm, tmp_path, rng, log = _setup(hook_style, llm, tmp_path, rng, log, "SCRIPT_PROMPT.md", "script")
    return _iterate(llm, system, request_text(instruction, hooks.random_topic(rng)), extract_script,
                    lambda t: script_problems(t, tmp_path), False, log, max_tries)


def post_text(scene):
    post = scene.get("post") or {}
    tags = post.get("hashtags") or []
    if isinstance(tags, str):
        tags = tags.split()
    lines = [post.get("caption", scene.get("hook", ""))]
    if tags:
        lines += ["", " ".join(tags)]
    return "\n".join(lines).strip() + "\n"


def save(scene, out):
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(scene, f, ensure_ascii=False, indent=2)
    with open(os.path.splitext(out)[0] + ".post.txt", "w", encoding="utf-8") as f:
        f.write(post_text(scene))
    return out


def slug(text):
    s = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return (s[:40] or "scene")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Idea or script -> checked scene.json (+ .post.txt) or script .txt")
    ap.add_argument("instruction", nargs="?", default="", help="idea or script; empty = AI picks a topic")
    ap.add_argument("-o", "--out", default=None, help="output file (with --count > 1: _1, _2... are added)")
    ap.add_argument("--hook", default="auto", choices=["auto"] + sorted(hooks.HOOKS))
    ap.add_argument("--count", type=int, default=1, help="how many different videos to write")
    ap.add_argument("--script-only", action="store_true", help="write a readable script (.txt) instead of a scene")
    ap.add_argument("--provider", default=None, choices=["anthropic", "gemini"])
    ap.add_argument("--model", default=None)
    args = ap.parse_args(argv)

    llm = make_llm(args.provider, args.model)
    rng = random.Random()
    if args.script_only:
        text = write_script(args.instruction, args.hook, llm, rng=rng)
        out = args.out or os.path.join(ROOT, "scripts", "generated", slug(args.instruction or "auto") + ".txt")
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(text)
        print(out)
        return
    used = []
    base = args.out or os.path.join(ROOT, "scenes", "generated", slug(args.instruction or "auto") + ".json")
    for i in range(max(1, args.count)):
        style = args.hook
        if style == "auto" and args.count > 1:
            style, _h = hooks.pick("auto", rng, avoid=used)
            used.append(style)
        scene = direct(args.instruction, style, llm, rng=rng)
        out = base if args.count == 1 else "%s_%d.json" % (os.path.splitext(base)[0], i + 1)
        print(save(scene, out))


if __name__ == "__main__":
    main()

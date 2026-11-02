"""Roman (Hinglish) lines -> Devanagari, so the Hindi voice reads them right.

A script written on the page's Builder (or by hand) may have lines without ` | देवनागरी`. Before the video is made,
every such line goes to the AI in ONE text request ("write it in Devanagari as it is spoken"); the answer is cached in
.cache/hindi/. No AI key, or the AI is down: the lines stay as they are (the voice then reads the Roman letters).

    python -m studio.script my_script.txt -o scene.json        # fills the Devanagari by itself
"""
import hashlib
import json
import os
import re
import sys

from .util import ROOT

DEVANAGARI = re.compile(r"[ऀ-ॿ]")
CACHE = os.path.join(ROOT, ".cache", "hindi")

SYSTEM = """You turn Hinglish (Hindi written in Latin letters, mixed with English words) into Devanagari for a Hindi
text-to-speech voice. For every input line, write exactly the same words, in the same order, as they are spoken, in
Devanagari script. English words stay English words, written in Devanagari the way an Indian speaker says them
(phone -> फ़ोन, insurance -> इंश्योरेंस). Numbers become Hindi words (10 hazar -> दस हज़ार). Keep the punctuation
(? ! . , ...). Drop emojis. Do not translate, explain, add or remove words. Return ONLY a JSON array of strings: one
string per input line, same order, same count."""


def needs_hindi(text):
    return bool(text and text.strip()) and not DEVANAGARI.search(text)


def _spoken(scene):
    """Every event with a line that a voice speaks, in the whole video."""
    parts = scene.get("scenes") or [scene]
    for part in parts:
        for ev in part.get("timeline", []):
            if "say" in ev and ev.get("tts", True):
                yield ev


def missing(scene):
    return [ev for ev in _spoken(scene) if needs_hindi(str(ev.get("speak", ev["say"])))]


def _key(lines):
    return hashlib.sha1(json.dumps(lines, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def _clean(text):
    return re.sub(r"[\U0001F000-\U0001FFFF☀-➿️]", "", text).strip()


def quick(llm):
    """A helper must never hold the video up: one try per model, short timeout, two models at most (then Roman)."""
    if hasattr(llm, "models"):
        llm.TRIES, llm.timeout, llm.temperature = 1, 40, 0.2
        llm.models = llm.models[:2]
    return llm


def transliterate(lines, llm):
    """[roman] -> [devanagari] (None where the answer was unusable)."""
    raw = llm(SYSTEM, [{"role": "user", "content": json.dumps(lines, ensure_ascii=False)}], json_mode=True)
    m = re.search(r"\[.*\]", raw, re.S)
    out = json.loads(m.group(0) if m else raw)
    if not isinstance(out, list) or len(out) != len(lines):
        raise ValueError("expected %d lines, got %r" % (len(lines), out if not isinstance(out, list) else len(out)))
    return [s.strip() if isinstance(s, str) and DEVANAGARI.search(s) else None for s in out]


def fill_hindi(scene, llm=None, log=None):
    """Give every Roman-only spoken line a Devanagari `speak`. Returns how many lines were filled."""
    log = log or (lambda m: print(m, file=sys.stderr))
    todo = missing(scene)
    if not todo:
        return 0
    lines = [_clean(str(ev.get("speak", ev["say"]))) for ev in todo]
    path = os.path.join(CACHE, _key(lines) + ".json")
    hindi = None
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            hindi = json.load(f)
    else:
        try:
            if llm is None:
                from .director import make_llm, provider_name
                if not provider_name():
                    log("  [hindi] %d line(s) without Devanagari and no AI key: the voice reads the Roman letters"
                        % len(lines))
                    return 0
                llm = quick(make_llm())
            hindi = transliterate(lines, llm)
        except (Exception, SystemExit) as e:        # noqa: BLE001  (GeminiLLM gives up with SystemExit)
            log("  [hindi] could not get Devanagari (%s): the voice reads the Roman letters" % str(e)[:200])
            return 0
        os.makedirs(CACHE, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(hindi, f, ensure_ascii=False)
    n = 0
    for ev, h in zip(todo, hindi):
        if h:
            ev["speak"] = h
            n += 1
    log("  [hindi] Devanagari for %d/%d line(s)" % (n, len(lines)))
    return n

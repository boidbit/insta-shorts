"""A viral sound as the voice of a reel ("sound mode").

The script names the sound (`SOUND: sound-ab12cd 0:05-0:20`, or a file path) and gives every line of it to a
character, with the time it is said (`A (angry, @1.8): Ye kya hai?`). The studio does not speak: the sound is the
voice and stays in the video, the lines are placed exactly where they are said in it, the mouths move with it and the
acting follows the voice (Gemini hears the words, who says them and how).

    python -m studio.sound draft --event "$GITHUB_EVENT_PATH" -o draft.txt   # the web page's 🎵 Sound tab
    python -m studio.sound unpack --event "$GITHUB_EVENT_PATH"                            # before a video is made
    python -m studio.sound analyze my_sound.m4a                                           # what Gemini hears (JSON)
"""
import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys

import numpy as np

from .util import ROOT

SOUND_DIR = os.path.join(ROOT, "sounds")
CACHE = os.path.join(ROOT, ".cache", "sound")
SR = 16000                       # analysis rate
EXTS = ("ogg", "opus", "webm", "m4a", "mp4", "mp3", "wav", "aac")


class SoundError(RuntimeError):
    pass


# ------------------------------------------------------------------ the file
def resolve(src):
    """`sound-ab12cd` -> sounds/sound-ab12cd.<ext>; a path -> itself. None when it is not there."""
    if not src:
        return None
    for p in (src, os.path.join(ROOT, src)):
        if os.path.isfile(p):
            return p
    for ext in EXTS:
        p = os.path.join(SOUND_DIR, "%s.%s" % (src, ext))
        if os.path.isfile(p):
            return p
    return None


def cut(path, start=0.0, end=None):
    """The part of the sound the reel uses, as a mono 44.1 kHz wav (cached)."""
    key = hashlib.sha1(("%s|%s|%s|%s" % (os.path.abspath(path), os.path.getmtime(path), start, end)).encode()).hexdigest()[:16]
    out = os.path.join(CACHE, key + ".wav")
    if os.path.isfile(out):
        return out
    os.makedirs(CACHE, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-ss", "%.3f" % float(start or 0.0)]
    if end:
        cmd += ["-to", "%.3f" % float(end)]
    cmd += ["-i", path, "-vn", "-ac", "1", "-ar", "44100", out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode or not os.path.isfile(out):
        raise SoundError("sound file nahi khuli (%s): %s" % (os.path.basename(path), r.stderr.strip()[:200]))
    return out


def samples(path, sr=SR):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(sr), "-"],
                       capture_output=True)
    if r.returncode:
        raise SoundError("sound file nahi padhi ja saki")
    return np.frombuffer(r.stdout, dtype=np.float32)


def duration(path):
    return len(samples(path)) / float(SR)


# ------------------------------------------------------------------ when every line is said
def _rms(x, sr=SR):
    hop = int(sr * 0.01)
    m = len(x) // hop
    return np.sqrt((x[: m * hop].reshape(m, hop) ** 2).mean(axis=1)) if m else np.zeros(0)


def _quiet_runs(rms, thr, min_len=8):
    runs, a = [], None
    for i, q in enumerate(rms < thr):
        if q and a is None:
            a = i
        elif not q and a is not None:
            if i - a >= min_len:
                runs.append((a, i))
            a = None
    return runs


def segments(x, texts, ats, sr=SR):
    """[(start, end)] in seconds for every line. The breaks between lines are chosen among the pauses in the sound,
    all at once: a break should sit near the written time of the next line (`@1.8`, e.g. what Gemini heard), be a
    real pause (a long one more likely than a comma inside a line) and leave every line about as long as its words.
    Lines start where the voice starts after their break."""
    n = len(texts)
    total = len(x) / float(sr)
    rms = _rms(x, sr)
    if n == 0:
        return []
    thr = max(float(np.percentile(rms, 95)) * 0.05, 1e-4) if len(rms) else 1e-4
    voiced = np.flatnonzero(rms >= thr) if len(rms) else np.zeros(0, dtype=int)
    if voiced.size == 0:                               # silence: the written times or an even spread
        starts = [a if a is not None else total * i / n for i, a in enumerate(ats)]
        return [(round(a, 3), round(max(a + 0.25, (starts[i + 1] - 0.05) if i + 1 < n else total), 3))
                for i, a in enumerate(starts)]
    first, last = int(voiced[0]) * 0.01, (int(voiced[-1]) + 1) * 0.01
    gaps = [(a * 0.01, b * 0.01) for a, b in _quiet_runs(rms, thr) if a * 0.01 > first and b * 0.01 < last]
    weights = np.array([max(3, len(re.sub(r"[\W_]+", "", t))) for t in texts], dtype=float)
    expect = (last - first) * weights / weights.sum()
    timed = any(a is not None for a in ats)
    cuts = None
    m = len(gaps)
    if n == 1:
        cuts = []
    elif m >= n - 1:
        INF = 1e18
        ga = np.array([g[0] for g in gaps])
        gb = np.array([g[1] for g in gaps])
        bonus = 0.6 * np.log(np.maximum(gb - ga, 0.01) / 0.15)
        w_len = 0.35 if timed else 1.0

        def at_cost(k, onset):
            return ((onset - ats[k]) / 0.45) ** 2 if ats[k] is not None else 0.0
        cost = np.full((n - 1, m), INF)
        back = np.zeros((n - 1, m), dtype=int)
        for i in range(m):
            d = max(ga[i] - first, 0.05)
            cost[0][i] = w_len * np.log(d / expect[0]) ** 2 + at_cost(1, gb[i]) - bonus[i]
        for k in range(1, n - 1):
            for i in range(k, m):
                prev = np.arange(k - 1, i)
                d = np.maximum(ga[i] - gb[prev], 0.05)
                c = cost[k - 1][prev] + w_len * np.log(d / expect[k]) ** 2
                j = int(np.argmin(c))
                cost[k][i] = c[j] + at_cost(k + 1, gb[i]) - bonus[i]
                back[k][i] = prev[j]
        d_last = np.maximum(last - gb, 0.05)
        final = cost[n - 2] + w_len * np.log(d_last / expect[n - 1]) ** 2
        i = int(np.argmin(final))
        if final[i] < INF / 2:
            cuts = [i]
            for k in range(n - 2, 0, -1):
                i = int(back[k][i])
                cuts.append(i)
            cuts = [gaps[j] for j in reversed(cuts)]
    if cuts is None:                                   # too few pauses: the written times, else the word lengths
        cum = np.concatenate([[0.0], np.cumsum(expect)[:-1]])
        starts = [ats[k] if ats[k] is not None else first + cum[k] for k in range(n)]
        starts = [max(s_, starts[k - 1] + 0.2) if k else max(0.0, s_) for k, s_ in enumerate(starts)]
        ends = [starts[k + 1] - 0.05 for k in range(n - 1)] + [min(total, last + 0.1)]
    else:
        starts = [max(0.0, first - 0.03)] + [g[1] - 0.03 for g in cuts]
        ends = [g[0] + 0.08 for g in cuts] + [min(total, last + 0.1)]
    return [(round(a, 3), round(max(a + 0.25, b), 3)) for a, b in zip(starts, ends)]


def _parts(scene):
    return scene["scenes"] if scene.get("scenes") else [scene]


def prepare(scene, use_tts=True):
    """Before a video is built: a scene with a SOUND gets its lines timed to the sound and the sound as its voice.
    Other scenes pass through. Raises SystemExit when the sound file is missing."""
    snd = scene.get("sound") if isinstance(scene, dict) else None
    if not snd:
        return scene
    import copy
    scene = copy.deepcopy(scene)
    path = resolve(snd.get("src"))
    if not path:
        raise SystemExit("SOUND %r ki file nahi mili. Page pe 🎵 Sound se reel se sound dobara chuno (ya sounds/ me "
                         "file rakho)." % snd.get("src"))
    wav = cut(path, snd.get("start") or 0.0, snd.get("end"))
    x = samples(wav)
    total = len(x) / float(SR)
    says = [ev for part in _parts(scene) for ev in part.get("timeline", []) if "say" in ev]
    segs = segments(x, [str(ev["say"]) for ev in says], [ev.get("sound_at") for ev in says])
    for ev, (a, b) in zip(says, segs):
        ev["t"], ev["duration"], ev["tts"], ev["lip_src"] = a, round(b - a, 3), False, wav
    dropped = False
    for part in _parts(scene):
        for ev in part.get("timeline", []):
            for k in ("slowmo", "freeze"):              # the sound cannot slow down or stop
                if ev.pop(k, None) is not None:
                    dropped = True
        part.pop("lead_in", None)                     # the sound starts with the video
        part.setdefault("timeline", []).append({"t": round(total, 3), "wait": 0.0})   # as long as the sound at least
    if dropped:
        print("  [sound] slowmo / freeze chhod diye: sound ki timing nahi badal sakti", file=sys.stderr)
    scene.pop("music", None)
    scene.pop("loop", None)
    scene["_sound"] = {"path": wav, "duration": round(total, 3)}
    print("  [sound] %d line(s) on a %.1f s sound" % (len(says), total), file=sys.stderr)
    return scene


# ------------------------------------------------------------------ the web page's sound
def unpack(event_path):
    """The sound the page sent with the run (inputs.sound = "<id>;<ext>;<base64>") -> sounds/<id>.<ext>.
    It is read from the event file, never from an environment variable, so it does not land in the run's log."""
    with open(event_path, encoding="utf-8") as f:
        ev = json.load(f)
    raw = ((ev.get("inputs") or {}).get("sound") or "").strip()
    if not raw:
        return None
    try:
        sid, ext, data = raw.split(";", 2)
    except ValueError:
        raise SystemExit("sound input samajh nahi aaya")
    if not re.fullmatch(r"sound-[a-z0-9]{4,24}", sid) or ext not in EXTS:
        raise SystemExit("sound input ka naam galat hai: %r" % sid)
    os.makedirs(SOUND_DIR, exist_ok=True)
    out = os.path.join(SOUND_DIR, "%s.%s" % (sid, ext))
    with open(out, "wb") as f:
        f.write(base64.b64decode(data))
    print("sound: %s (%.1f KB)" % (out, os.path.getsize(out) / 1024.0), file=sys.stderr)
    return out


# ------------------------------------------------------------------ what Gemini hears
MIME = {"ogg": "audio/ogg", "opus": "audio/ogg", "webm": "audio/webm", "m4a": "audio/mp4", "mp4": "audio/mp4",
        "mp3": "audio/mp3", "wav": "audio/wav", "aac": "audio/aac"}


def listen_prompt():
    from .script import vocab
    v = vocab()
    return """You listen to a short viral sound from Instagram reels (Hindi / Hinglish / English dialogue, a song or
music) for a desi cartoon studio. The studio will animate cartoon characters lip-syncing to EXACTLY this sound, and the
joke of the reel comes from a new situation shown on screen. Write down precisely what is in the sound.

Return ONLY JSON:
{"kind": "dialogue" | "song" | "music",
 "summary": "<what is said / sung, one line>",
 "meme": "<how people use this sound in reels, one line>",
 "speakers": [{"id": "S1", "gender": "male|female|child", "age": "kid|young|adult|old", "voice": "<how it sounds>",
               "role": "<one word from ROLES>"}],
 "lines": [{"start": 0.0, "end": 1.4, "speaker": "S1", "roman": "<exactly the words, Hinglish in Roman letters>",
            "devanagari": "<the same words in Devanagari>", "feeling": "<one word from FEELINGS>",
            "action": "<one word from ACTIONS or empty>", "extras": ["<0-2 words from EXTRAS>"]}],
 "place": "<one word from PLACES>",
 "ideas": [{"hook": "<4-8 words, e.g. POV: ...>", "situation": "<the new situation on screen>", "place": "<PLACES>",
            "roles": {"S1": "<ROLES>", "S2": "<ROLES>"}, "caption": "<post caption>", "cta": "<tag karo ...>"}]}

Rules: one entry in "lines" per sentence or short phrase as it is spoken, in order, with its real start / end time in
seconds from the beginning of the audio (as exact as you can hear it). Do not translate, correct or shorten the words.
Feelings from the voice (angry, shout, shock, laugh, cry, smug, sly, sad, nervous, excited...); the action is a
gesture that fits the words and the feeling. Extras follow the emotion: "shake" when the voice shouts or hits hard,
"close" on the strongest / funniest line, a matching sound or effect (boing, thud, record_scratch, ding, sweat, anger,
hearts, question...). Not on every line. At most 3 speakers. A song: one line per sung line, action "sing". Only music,
no words: "lines" empty.
Give 3 ideas: different everyday desi situations where this sound fits as a joke (office, ghar, school, shaadi, dost...)%s.

ROLES: %s
PLACES: %s
FEELINGS: %s
ACTIONS: %s
EXTRAS: %s
""" % ("%s", ", ".join(sorted(set(v["roles"]) | set(v["looks"]))), ", ".join(v["places"]),
       ", ".join(v["expressions"]), ", ".join(sorted(set(v["actions"]))[:110]), ", ".join(extra_words()))


def extra_words():
    """Words a line may get for its emotion: camera shake / close, a sound, an effect around the character."""
    from .script import vocab
    v = vocab()
    return ["shake", "close", "zoom"] + sorted(set(v["sfx"])) + sorted(set(v["fx"]) & set(
        ["sweat", "question", "exclaim", "anger", "hearts", "stars", "sparkle", "steam", "fire", "lightning", "bulb",
         "tears_spray", "dizzy", "zzz", "pow", "confetti", "spotlight", "glow_eyes", "focus_lines"]))


def analyze(path, context="", llm=None):
    """The sound file -> what is in it (dict). Needs GEMINI_API_KEY (Gemini hears audio)."""
    if llm is None:
        from .director import GeminiLLM
        llm = GeminiLLM()
        llm.temperature = 0.4
    ext = os.path.splitext(path)[1].lstrip(".").lower()
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("ascii")
    ask = listen_prompt() % ((" (the user wants: %s)" % context.strip()) if context.strip() else "")
    raw = llm("You transcribe and describe audio precisely. Answer with JSON only.",
              [{"role": "user", "content": [{"inline_data": {"mime_type": MIME.get(ext, "audio/ogg"), "data": data}},
                                            {"text": ask}]}], json_mode=True)
    from .director import extract_json
    info = extract_json(raw)
    if not isinstance(info, dict) or not info.get("lines") and info.get("kind") != "music":
        raise SoundError("Gemini ne sound me koi line nahi batayi")
    return info


# ------------------------------------------------------------------ a draft script from it
FALLBACK_ROLE = {("male", "kid"): "kid", ("female", "kid"): "kid_girl", ("child", "kid"): "kid",
                 ("male", "old"): "dada", ("female", "old"): "dadi", ("male", "adult"): "uncle",
                 ("female", "adult"): "aunty", ("male", "young"): "college_boy", ("female", "young"): "college_girl"}


HINGLISH_FEEL = {"gussa": "angry", "ghussa": "angry", "hasi": "laugh", "akad": "smug", "chalak": "sly", "chilla": "shout",
                 "hairan": "surprised", "rona": "cry", "dukhi": "sad", "khush": "smile", "darr": "scared", "soch": "think",
                 "pyaar": "love", "sharam": "shy", "happy": "smile", "funny": "laugh", "sarcastic": "smug"}


def _clean_words(s):
    return re.sub(r"\s+", " ", str(s or "")).replace("|", "/").strip()


def draft(info, sound_id, context="", start=0.0, end=None):
    """What Gemini heard -> (a SOUND-mode script, the ideas as text). Every word is checked against the studio's
    lists; anything unknown is left out (the script must read cleanly)."""
    from .script import FEEL_WORDS, vocab
    v = vocab()
    roles = set(v["roles"]) | set(v["looks"])
    places, feels, acts = set(v["places"]), set(v["expressions"]), set(v["actions"])
    ideas = [i for i in (info.get("ideas") or []) if isinstance(i, dict)]
    idea = ideas[0] if ideas else {}
    speakers = [s for s in (info.get("speakers") or []) if isinstance(s, dict) and s.get("id")][:3]
    ids = {}
    cast = []
    for n, sp in enumerate(speakers):
        role = str((idea.get("roles") or {}).get(sp["id"]) or sp.get("role") or "").strip().lower().replace(" ", "_")
        if role not in roles:
            role = FALLBACK_ROLE.get((str(sp.get("gender", "")).lower(), str(sp.get("age", "")).lower()),
                                     "college_girl" if str(sp.get("gender", "")).lower() == "female" else "college_boy")
        letter = "ABC"[n]
        ids[sp["id"]] = letter
        cast.append("%s = %s" % (letter, role))
    place = str(idea.get("place") or info.get("place") or "").strip().lower()
    if place not in places:
        place = "room"
    rng = ""
    if start or end:
        fmt = lambda t: "%d:%04.1f" % (int(t // 60), t % 60)    # noqa: E731
        rng = " %s-%s" % (fmt(start or 0.0), fmt(end)) if end else " %s-9:59" % fmt(start)
    extras_ok = set(extra_words())
    lines = []
    for ln in info.get("lines") or []:
        if not isinstance(ln, dict):
            continue
        words = _clean_words(ln.get("roman"))
        if not words:
            continue
        who = ids.get(ln.get("speaker"), "NARRATOR" if not cast else "A")
        acting = []
        feel = str(ln.get("feeling") or "").strip().lower()
        feel = HINGLISH_FEEL.get(feel) or FEEL_WORDS.get(feel, feel)
        act = str(ln.get("action") or "").strip().lower()
        if act in acts and act not in feels and who != "NARRATOR":
            acting.append(act)
        if feel in feels and who != "NARRATOR":
            acting.append(feel)
        ex = ln.get("extras") or []
        for w in ([ex] if isinstance(ex, str) else ex)[:2]:         # the emotion: shake / close / a sound / an effect
            w = str(w).strip().lower()
            if w in extras_ok and w not in acting and (who != "NARRATOR" or w not in ("shake", "close", "zoom")):
                acting.append(w)
        try:
            acting.append("@%.1f" % max(0.0, float(ln.get("start"))))
        except (TypeError, ValueError):
            pass
        lines.append("%s (%s): %s" % (who, ", ".join(acting), words) if acting else "%s: %s" % (who, words))
    if not lines:                                     # only music (no words): everybody dances to it
        moves = ["dance excited", "bhangra laugh", "thumka smug", "dance_walk grin"]
        for n, letter in enumerate([c.split(" = ")[0] for c in cast] or ["A"]):
            lines.append("%s -> %s" % (letter, moves[n % len(moves)]))
        if not cast:
            cast.append("A = college_boy")
    hook = _clean_words(idea.get("hook")) or _clean_words(info.get("summary"))[:50] or "Ye sound sun ke 😂"
    out = ["HOOK: " + hook, "SOUND: " + sound_id + rng]
    if cast:
        out.append("CAST: " + ", ".join(cast))
    out.append("SCENE: " + place)
    out += lines
    out += ["CTA_STYLE: caption",                     # no end card: the reel ends with the sound
            "CTA: " + (_clean_words(idea.get("cta")) or "Tag karo us dost ko 👇"),
            "CAPTION: " + (_clean_words(idea.get("caption")) or hook),
            "HASHTAGS: #trendingaudio #desicomedy #funnyreels #relatable"]
    notes = []
    if info.get("meme"):
        notes.append("Ye sound kaise chalta hai: " + _clean_words(info["meme"]))
    for k, i in enumerate(ideas[:3], 1):
        notes.append("%d. %s: %s" % (k, _clean_words(i.get("hook")), _clean_words(i.get("situation"))))
    return "\n".join(out) + "\n", "\n".join(notes)


IDEAS_MARK = "<!-- ideas -->"


def main(argv=None):
    ap = argparse.ArgumentParser(description="A viral sound as a reel's voice")
    sub = ap.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("unpack", help="write the sound the web page sent (inputs.sound) into sounds/")
    u.add_argument("--event", required=True)
    d = sub.add_parser("draft", help="unpack + Gemini listens + a draft script for the page")
    d.add_argument("--event", required=True)
    d.add_argument("--context", default="")
    d.add_argument("--no-ideas", action="store_true", help="only the script (straight to the video)")
    d.add_argument("-o", "--out", required=True)
    a = sub.add_parser("analyze", help="what Gemini hears in a sound file (JSON)")
    a.add_argument("file")
    a.add_argument("--context", default="")
    args = ap.parse_args(argv)
    if args.cmd == "unpack":
        unpack(args.event)
        return
    if args.cmd == "analyze":
        print(json.dumps(analyze(args.file, args.context), ensure_ascii=False, indent=1))
        return
    path = unpack(args.event)
    if not path:
        raise SystemExit("sound nahi mila: page pe 🎵 Sound se reel me file chuno")
    sid = os.path.splitext(os.path.basename(path))[0]
    try:
        info = analyze(path, args.context)
    except SoundError as e:
        raise SystemExit(str(e))
    script, notes = draft(info, sid, args.context)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(script + ("\n%s\n%s\n" % (IDEAS_MARK, notes) if notes and not args.no_ideas else ""))
    print(script)
    print(notes)


if __name__ == "__main__":
    main()

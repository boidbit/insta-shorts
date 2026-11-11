"""ElevenLabs voices: very natural Hindi (multilingual model), one request per spoken line, every character their own
voice. Key: ELEVENLABS_API_KEY (GitHub: a repository secret of that name; a few other spellings work too).

Chosen with `--tts elevenlabs` (studio page: Awaaz -> ElevenLabs). Voices: the account's own voices are listed once
(an Indian / Hindi voice is preferred when the account has one), else ElevenLabs' standard voices. A character can
name one: {"voice": {"eleven": "<voice id>"}}; ELEVENLABS_VOICES_MALE / ELEVENLABS_VOICES_FEMALE (comma separated
ids) set the pool. Model: ELEVENLABS_MODEL (default eleven_multilingual_v2). Every line is cached on disk, so a
re-render costs no credits. Only the standard library is used.
"""
import hashlib
import json
import os
import re
import sys
import subprocess
import urllib.error
import urllib.request

ENDPOINT = "https://api.elevenlabs.io/v1/text-to-speech/%s?output_format=mp3_44100_128"
VOICES_URL = "https://api.elevenlabs.io/v1/voices"
DEFAULT_MODEL = "eleven_multilingual_v2"
CACHE_DIR = os.path.join(".cache", "tts", "eleven")
KEY_NAMES = ("ELEVEN_LAB_1", "ELEVENLABS_API_KEY", "ELEVEN_LABS_API_KEY", "ELEVENLABS_KEY", "ELEVEN_API_KEY", "XI_API_KEY", "ELEVENLAB_API_KEY",
             "ELEVENLAB_KEY")
# ElevenLabs' standard (premade) voices, available to every account
MALE = ["pNInz6obpgDQGcFmaJgB", "TxGEqnHWrfWFTfGW9XjX", "onwK4e9ZLuTAKqWW03F9", "nPczCjzI2devNBz1zQrb",
        "JBFqnCBsd6RMkjVDRZzb", "VR6AewLTigWG4xSOukaG"]
FEMALE = ["21m00Tcm4TlvDq8ikWAM", "EXAVITQu4vr4xnSDxMaL", "XrExE9yKIg1WjnnlVkGX", "pFZP5JQG7iQjIQuC4Bku",
          "cgSgspJ2msm6clMCkdW9", "MF3mGyEYCl7XYWbV9V5O"]
LOUD = {"angry", "shout", "excited", "shock", "scared", "laugh", "lol", "surprised", "evil"}
SOFT = {"sad", "cry", "hurt", "sleepy", "shy", "nervous", "dead", "bored"}
PLAN_ONLY = re.compile(r"HTTP 402|paid_plan_required|library voices", re.I)    # this voice needs a paid plan


class ElevenLabsError(RuntimeError):
    pass


def api_key():
    for name in KEY_NAMES:
        if os.environ.get(name):
            return os.environ[name].strip()
    return ""


def is_female(spec):
    """A character's voice dict (edge-tts name / gemini voice) -> female?"""
    spec = spec or {}
    name = "%s %s" % (spec.get("name") or "", spec.get("gemini") or "")
    return bool(re.search(r"Swara|Female|Neerja|Kore|Aoede|Leda|Zephyr|Callirrhoe|Despina", name, re.I))


def settings_for(expression):
    """Voice settings: an angry / excited line is more expressive, a sad one steadier and softer."""
    if expression in LOUD:
        return {"stability": 0.3, "similarity_boost": 0.8, "style": 0.55, "use_speaker_boost": True}
    if expression in SOFT:
        return {"stability": 0.6, "similarity_boost": 0.8, "style": 0.3, "use_speaker_boost": True}
    return {"stability": 0.45, "similarity_boost": 0.8, "style": 0.35, "use_speaker_boost": True}


def _request(url, key, body=None, timeout=120):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if body is not None else "GET",
                                 headers={"xi-api-key": key, "Content-Type": "application/json",
                                          "Accept": "audio/mpeg" if body is not None else "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        try:
            msg = e.read().decode("utf-8", "replace")[:300]
        except Exception:
            msg = ""
        raise ElevenLabsError("HTTP %d %s" % (e.code, msg))
    except (urllib.error.URLError, OSError) as e:
        raise ElevenLabsError("network: %s" % e)


def _env_ids(name):
    return [v.strip() for v in os.environ.get(name, "").split(",") if v.strip()]


def voice_pools(key):
    """(male ids, female ids): env lists first, then the account's Indian / Hindi voices, then the standard ones."""
    male, female = _env_ids("ELEVENLABS_VOICES_MALE"), _env_ids("ELEVENLABS_VOICES_FEMALE")
    try:
        voices = json.loads(_request(VOICES_URL, key, timeout=30).decode("utf-8")).get("voices", [])
    except Exception:
        voices = []
    for v in voices:                                    # the account's own Indian voices go first
        labels = {k: str(x).lower() for k, x in (v.get("labels") or {}).items()}
        if "indian" in labels.get("accent", "") or "hindi" in (labels.get("language", "") + v.get("name", "").lower()):
            (female if labels.get("gender") == "female" else male).append(v["voice_id"])
    return male + [m for m in MALE if m not in male], female + [f for f in FEMALE if f not in female]


def synth_lines(items, model=None, cache_dir=None, key=None):
    """items: [{"text", "who", "spec" (voice dict), "expression"}] in speaking order -> [mp3 path per item].
    Each character keeps one voice for the whole video, and no two characters share one."""
    if not items:
        return []
    key = key or api_key()
    if not key:
        raise ElevenLabsError("no ELEVENLABS_API_KEY")
    model = model or os.environ.get("ELEVENLABS_MODEL") or DEFAULT_MODEL
    cache_dir = cache_dir or CACHE_DIR
    os.makedirs(cache_dir, exist_ok=True)
    pools = None
    chosen, taken, blocked = {}, set(), set()

    def pick(spec):
        """The next voice for a new character: one nobody else in the video has, and not one the plan refused."""
        nonlocal pools
        if pools is None:
            pools = voice_pools(key)
        pool = pools[1] if is_female(spec) else pools[0]
        free = [v for v in pool if v not in blocked and v not in taken] or [v for v in pool if v not in blocked]
        if not free:
            raise ElevenLabsError("no voice this plan can use")
        taken.add(free[0])
        return free[0]

    paths = []
    for it in items:
        spec = it.get("spec") or {}
        who = it.get("who") or "?"
        if who not in chosen:
            chosen[who] = str(spec["eleven"]) if spec.get("eleven") else pick(spec)
        for _attempt in range(10):
            voice = chosen[who]
            body = {"text": it["text"], "model_id": model, "voice_settings": settings_for(it.get("expression"))}
            if re.search(r"v2_5|flash|turbo|v3", model):
                body["language_code"] = "hi"        # (only these models take a language)
            h = hashlib.sha1(json.dumps([voice, body], ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]
            path = os.path.join(cache_dir, h + ".mp3")
            if os.path.isfile(path) and os.path.getsize(path) > 1000:
                break
            print("  [eleven] %s: %s" % (who, it["text"][:40]), file=sys.stderr)
            try:
                data = _request(ENDPOINT % voice, key, body)
            except ElevenLabsError as e:
                if not PLAN_ONLY.search(str(e)):
                    raise
                # a free plan cannot use a Voice Library voice through the API: take a standard voice instead
                print("  [eleven] voice %s needs a paid plan -> a standard voice" % voice, file=sys.stderr)
                blocked.add(voice)
                chosen[who] = pick(spec)
                continue
            if len(data) < 1000:
                raise ElevenLabsError("the audio is only %d bytes" % len(data))
            with open(path, "wb") as f:
                f.write(data)
            break
        else:
            raise ElevenLabsError("no voice this plan can use")
        paths.append(_kid_voice(os.path.abspath(path), it.get("pitch")))
    return paths


def _kid_voice(path, pitch):
    """A child (a pitch of +18 Hz or more in the cast) gets the grown-up voice raised a little; others stay untouched."""
    from .gemini_tts import semitones
    st = semitones(pitch)
    if st < 2.5:
        return path
    r = 2.0 ** (min(st, 5.0) / 12.0)
    dst = path[:-4] + "_kid%d.mp3" % round(st * 10)
    if os.path.isfile(dst) and os.path.getsize(dst) > 1000:
        return dst
    try:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-af",
                        "asetrate=%d,aresample=44100,atempo=%.5f" % (round(44100 * r), 1.0 / r), dst],
                       check=True, timeout=60, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return dst
    except Exception as e:
        print("  [eleven] kid voice skipped: %s" % str(e)[:100], file=sys.stderr)
        return path

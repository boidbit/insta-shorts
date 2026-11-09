"""Songs from Gemini (Lyria): your lyrics in, a full song (music + vocals) out. Same GEMINI_API_KEY as the voice.

A script asks for it with a MUSIC line:
    MUSIC: gemini <style words>        30-second clip (lyria-3-clip-preview)
    MUSIC: gemini full <style words>   a full-length song (lyria-3.5, a couple of minutes)
  * in a lyrics-only script the lyrics you wrote are SUNG (the reel is as long as the song, the lines are spread
    over it);
  * in a story script (CAST / SCENE) it is instrumental background music.
If this key cannot make music (free plan without access, quota, no key, network) the studio's own beat plays
instead and the video is still made: music never stops a render.

The API (Gemini docs, "Generate music with Lyria 3"): POST /v1beta/interactions with the header Api-Revision and the
body {"model": ..., "input": "<prompt>"}; the audio comes back base64 in
steps[type=model_output].content[type=audio].data (MP3 unless a WAV is asked for). Only the stdlib is used.
"""
import base64
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

from . import audio
from .gemini_tts import api_key

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/interactions"
API_REVISION = "2026-05-20"
CLIP_MODEL, FULL_MODEL = "lyria-3-clip-preview", "lyria-3.5"
DEFAULT_STYLE = "catchy Hindi Bollywood-style pop"
CACHE_DIR = os.path.join(".cache", "tts", "music")    # inside the folder the workflow already caches
TIMEOUT = 300
MIN_SECONDS = 4.0                                      # a shorter "song" is a cut-off answer
SECTION = re.compile(r"^\[[^\]\n]{1,40}\]$")           # [Verse] [Chorus 2] [Bridge]


class MusicError(RuntimeError):
    pass


class MusicUnavailable(MusicError):
    """This key / plan cannot make music (no key, no access, quota). Trying again will not help."""


# ------------------------------------------------------------------ what to ask for
def is_section(line):
    return bool(SECTION.match(line.strip()))


def build_prompt(style, lyrics=None):
    """The musical direction first, the lyrics after it (the docs: keep them apart). lyrics = lines to sing (with
    optional [Verse] / [Chorus] lines); None = instrumental."""
    style = (style or DEFAULT_STYLE).strip()
    if not lyrics:
        return "Create an instrumental track in this style: %s. Instrumental only, no vocals." % style
    lines = [l.strip() for l in lyrics if l.strip()]
    if not any(is_section(l) for l in lines):
        lines.insert(0, "[Verse]")
    return ("Create a song in this style: %s. Sing the lyrics below exactly as written, in Hindi, in this order.\n\n%s"
            % (style, "\n".join(lines)))


def music_spec(value, lyrics=None):
    """`MUSIC: gemini [clip|full] <style words>` -> the scene's music dict (the studio beat is kept as the fallback)."""
    words = (value or "").split()[1:]
    model = CLIP_MODEL
    if words and words[0].lower() in ("clip", "full", "pro"):
        model = FULL_MODEL if words[0].lower() in ("full", "pro") else CLIP_MODEL
        words = words[1:]
    style = " ".join(words) or DEFAULT_STYLE
    sung = bool(lyrics)
    return {"type": "gemini", "model": model, "style": style, "prompt": build_prompt(style, lyrics),
            "vocals": sung, "volume": 0.85 if sung else 0.3,
            "fallback": ({"type": "beat", "bpm": 76, "style": "soft", "volume": 0.45} if sung
                         else {"type": "beat", "bpm": 100, "volume": 0.2})}


# ------------------------------------------------------------------ the API
def extract_audio(resp):
    """(audio bytes, [text blocks]) from an interactions answer."""
    texts = []
    for step in (resp.get("steps") or []) if isinstance(resp, dict) else []:
        if not isinstance(step, dict) or step.get("type") != "model_output":
            continue
        for block in step.get("content") or []:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "audio" and block.get("data"):
                return base64.b64decode(block["data"]), texts
            if block.get("type") == "text":
                texts.append(str(block.get("text", "")))
    keys = sorted(resp) if isinstance(resp, dict) else type(resp).__name__
    raise MusicError("the answer has no audio (keys: %s)" % (keys,))


def _error_text(err):
    try:
        body = err.read().decode("utf-8", "replace")
    except Exception:
        return ""
    try:
        return str(json.loads(body)["error"]["message"])[:300]
    except Exception:
        return body.strip()[:300]


def _post(model, prompt, key, wav=False):
    body = {"model": model, "input": prompt}
    if wav and model == FULL_MODEL:
        body["response_format"] = {"type": "audio"}
    req = urllib.request.Request(
        ENDPOINT, data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"x-goog-api-key": key, "Api-Revision": API_REVISION, "Content-Type": "application/json"})
    last = None
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            text = _error_text(e)
            if e.code < 500:                           # no access / quota / a bad request: asking again will not help
                raise MusicUnavailable("HTTP %d %s" % (e.code, text))
            last = MusicError("HTTP %d %s" % (e.code, text))
        except (urllib.error.URLError, OSError, ValueError) as e:
            last = MusicError("network: %s" % e)
        time.sleep(3)
    raise last


def song_path(prompt, model, cache_dir=CACHE_DIR, key=None):
    """The song for this prompt as a file (asks Gemini once; the same prompt later is served from the cache)."""
    h = hashlib.sha1(json.dumps([model, prompt], ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
    for ext in (".mp3", ".wav"):
        p = os.path.join(cache_dir, h + ext)
        if os.path.isfile(p) and os.path.getsize(p) > 2000:
            print("  [music] cached song (no API call)", file=sys.stderr)
            return os.path.abspath(p)
    key = key or api_key()
    if not key:
        raise MusicUnavailable("no GEMINI_API_KEY")
    print("  [music] asking Gemini (%s) for a song ..." % model, file=sys.stderr)
    data, texts = extract_audio(_post(model, prompt, key))
    if len(data) < 2000:
        raise MusicError("the audio is only %d bytes" % len(data))
    p = os.path.join(cache_dir, h + (".wav" if data[:4] == b"RIFF" else ".mp3"))
    os.makedirs(cache_dir, exist_ok=True)
    with open(p, "wb") as f:
        f.write(data)
    if texts:
        print("  [music] Gemini's notes: %s" % " ".join(texts)[:240].replace("\n", " "), file=sys.stderr)
    return os.path.abspath(p)


# ------------------------------------------------------------------ the studio's hook
def prepare(scene, use_tts=True):
    """Before a video is built: a scene whose music is `gemini` gets its song (a file path) - or the studio beat if
    Gemini cannot make one. A lyrics reel is re-timed to the song's real length. Other scenes pass through."""
    m = scene.get("music") if isinstance(scene, dict) else None
    if not (isinstance(m, dict) and m.get("type") == "gemini"):
        return scene
    fallback = m.get("fallback") or {"type": "beat", "bpm": 100, "volume": 0.2}
    if not use_tts:                                     # frame previews and tests never call the network
        return dict(scene, music=fallback)
    try:
        path = song_path(m["prompt"], m.get("model", CLIP_MODEL))
        seconds = audio.audio_duration(path)
        if not seconds or seconds < MIN_SECONDS:
            os.remove(path)                             # a cut-off answer must not stay in the cache
            raise MusicError("the song is only %s s long" % (round(seconds, 1) if seconds else "?"))
    except MusicError as e:
        print("  [music] Gemini could not make the song (%s) -> studio beat instead" % str(e)[:240], file=sys.stderr)
        return dict(scene, music=fallback)
    song = {"path": path, "volume": float(m.get("volume", 0.85 if m.get("vocals") else 0.3))}
    print("  [music] song ready: %.1f s" % seconds, file=sys.stderr)
    if m.get("lyrics_lines"):                           # lyrics reel: as long as the song, lines spread over it
        from . import script
        meta = dict(m.get("lyrics_meta") or {}, SECONDS="%.2f" % seconds, MUSIC="none")
        new, _warnings = script.parse_lyrics(meta, list(m["lyrics_lines"]))
        new["music"] = song
        return new
    return dict(scene, music=song)

"""Gemini TTS for a whole scene in ONE API request, split back into per-line clips.

Why: the free Gemini key has a tiny request quota, so we must not call the API once per line.
Flow:  all lines -> one request -> one long wav -> cut at the pauses between lines -> one wav per line.

Only the stdlib + numpy are used (no google SDK), the key is read from GEMINI_API_KEY (or GOOGLE_API_KEY).
"""
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import wave

import numpy as np

SR = 24000                                    # Gemini TTS returns 24 kHz, 16-bit, mono PCM
DEFAULT_MODEL = "gemini-2.5-flash-preview-tts"
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent"
DEFAULT_MALE, DEFAULT_FEMALE = "Puck", "Kore"
DEFAULT_STYLE = ("Read this as a natural, lively everyday Hindi conversation between friends. "
                 "Leave a clear silent pause of about one second between the lines.")


class GeminiTTSError(RuntimeError):
    pass


class QuotaExceeded(GeminiTTSError):
    pass


def api_key():
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""


# ------------------------------------------------------------------ voices
def voice_for(spec):
    """Gemini prebuilt voice name for a character `voice` dict.

    Use {"gemini": "Kore"} to choose explicitly; otherwise an edge-tts name is mapped by gender.
    """
    spec = spec or {}
    if spec.get("gemini"):
        return str(spec["gemini"])
    name = str(spec.get("name") or "")
    return DEFAULT_FEMALE if re.search(r"Swara|Female|Neerja", name, re.I) else DEFAULT_MALE


def semitones(pitch):
    """edge-tts style pitch ('+22Hz', '-6Hz', '+2st') -> semitones (rough; 130 Hz reference voice)."""
    if isinstance(pitch, (int, float)):
        return float(pitch)
    m = re.match(r"^\s*([+-]?\d+(?:\.\d+)?)\s*(Hz|st)?\s*$", str(pitch or ""), re.I)
    if not m:
        return 0.0
    v = float(m.group(1))
    if (m.group(2) or "Hz").lower() == "st":
        return v
    return max(-6.0, min(6.0, 12.0 * np.log2(max(10.0, 130.0 + v) / 130.0)))


def rate_factor(rate):
    """'+8%' -> 1.08"""
    m = re.match(r"^\s*([+-]?\d+(?:\.\d+)?)\s*%?\s*$", str(rate or "0"))
    return max(0.6, min(1.6, 1.0 + (float(m.group(1)) / 100.0 if m else 0.0)))


# ------------------------------------------------------------------ wav / pcm helpers
def pcm_to_float(pcm):
    return np.frombuffer(pcm[: len(pcm) // 2 * 2], dtype="<i2").astype(np.float32) / 32768.0


def write_wav(path, x, sr=SR):
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def read_wav(path):
    with wave.open(path, "rb") as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
    return x, sr


# ------------------------------------------------------------------ the single API call
def build_payload(lines, style=DEFAULT_STYLE):
    """lines: [{"voice": "Kore", "text": "..."}] in speaking order. 1 voice -> single-speaker request,
    2 voices -> multi-speaker request (Gemini allows at most 2 speakers)."""
    voices = []
    for ln in lines:
        if ln["voice"] not in voices:
            voices.append(ln["voice"])
    if len(voices) > 2:
        raise ValueError("Gemini TTS supports at most 2 distinct voices per request")
    if len(voices) == 1:
        body = "\n\n".join(ln["text"] for ln in lines)
        speech = {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voices[0]}}}
    else:
        label = {v: "Speaker%d" % (i + 1) for i, v in enumerate(voices)}
        body = "\n\n".join("%s: %s" % (label[ln["voice"]], ln["text"]) for ln in lines)
        speech = {"multiSpeakerVoiceConfig": {"speakerVoiceConfigs": [
            {"speaker": label[v], "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": v}}} for v in voices]}}
    text = (style.strip() + "\n\n" + body) if style else body
    return {"contents": [{"parts": [{"text": text}]}],
            "generationConfig": {"responseModalities": ["AUDIO"], "speechConfig": speech}}


def _retry_delay(body):
    m = re.search(r'"retryDelay"\s*:\s*"(\d+(?:\.\d+)?)s"', body) or re.search(r"retry in (\d+(?:\.\d+)?)s", body)
    return float(m.group(1)) if m else None


def request_audio(payload, model=DEFAULT_MODEL, key=None, attempts=3, timeout=240):
    """POST once (retrying only transient errors) and return float32 mono samples at SR."""
    key = key or api_key()
    if not key:
        raise GeminiTTSError("GEMINI_API_KEY is not set")
    req_data = json.dumps(payload).encode("utf-8")
    last = None
    for attempt in range(attempts):
        req = urllib.request.Request(ENDPOINT % model, data=req_data, method="POST",
                                     headers={"Content-Type": "application/json", "x-goog-api-key": key})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                resp = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            if e.code == 429:
                delay = _retry_delay(body)
                if delay is not None and delay <= 120:
                    # a short wait = a per-minute limit. (The body of such an error often names the daily metric
                    # too, so the word "PerDay" alone does not mean the day's quota is gone.)
                    wait = min(65.0, delay + 1.0)
                elif re.search(r"PerDay|per day|daily", body, re.I):
                    raise QuotaExceeded("Gemini free quota looks used up for today (no short retry time given); "
                                        "try again later or use another key") from None
                else:
                    wait = 20.0
            elif e.code in (500, 502, 503, 504):
                wait = 4.0 * (attempt + 1)
            else:
                msg = re.search(r'"message"\s*:\s*"([^"]{0,300})', body)
                raise GeminiTTSError("Gemini HTTP %d: %s" % (e.code, msg.group(1) if msg else body[:200])) from None
            last = "HTTP %d" % e.code
            if attempt + 1 < attempts:
                print("  [gemini] %s, retrying in %.0fs" % (last, wait), file=sys.stderr)
                time.sleep(wait)
            continue
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last = "network: %s" % str(e)[:120]
            if attempt + 1 < attempts:
                time.sleep(3.0 * (attempt + 1))
            continue
        parts = ((resp.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
        for p in parts:
            inline = p.get("inlineData") or p.get("inline_data")
            if inline and inline.get("data"):
                mime = inline.get("mimeType") or inline.get("mime_type") or ""
                m = re.search(r"rate=(\d+)", mime)
                if m and int(m.group(1)) != SR:
                    raise GeminiTTSError("unexpected sample rate in %r" % mime)
                return pcm_to_float(base64.b64decode(inline["data"]))
        reason = (resp.get("candidates") or [{}])[0].get("finishReason")
        last = "no audio in response (finishReason=%s)" % reason     # happens now and then; retry
        time.sleep(2.0)
    raise GeminiTTSError("Gemini TTS failed: %s" % last)


# ------------------------------------------------------------------ splitting one long take into lines
def _silence_runs(rms, thr, min_len):
    runs, start = [], None
    for i, s in enumerate(rms < thr):
        if s and start is None:
            start = i
        elif not s and start is not None:
            if i - start >= min_len:
                runs.append((start, i))
            start = None
    return runs


def split_audio(x, texts, sr=SR, pad=0.12):
    """Cut one long take into len(texts) clips at the pauses between lines.

    Returns ([(t0, t1), ...] in seconds, method). method is 'pauses' (longest N-1 silences, sanity-checked
    against the text lengths) or 'proportional' (fallback: text-length guess snapped to the nearest quiet spot).
    """
    n = len(texts)
    hop = int(sr * 0.01)
    m = len(x) // hop
    if m < 5:
        raise GeminiTTSError("audio too short to split")
    rms = np.sqrt((x[: m * hop].reshape(m, hop) ** 2).mean(axis=1))
    thr = max(float(np.percentile(rms, 95)) * 0.05, 1e-4)
    voiced = np.flatnonzero(rms >= thr)
    if voiced.size == 0:
        raise GeminiTTSError("Gemini returned silence")
    first, last = int(voiced[0]), int(voiced[-1]) + 1
    if n == 1:
        return [(max(0.0, first * 0.01 - pad), min(len(x) / sr, last * 0.01 + pad))], "pauses"

    weights = np.array([max(3, len(re.sub(r"[\W_]+", "", t))) for t in texts], dtype=float)

    def clips_from(gaps):
        bounds, prev = [], first * 0.01
        for (a, b) in gaps:
            bounds.append((max(0.0, prev - pad), min(a + pad, (a + b) / 2.0)))
            prev = b
        bounds.append((max(prev - pad, (gaps[-1][0] + gaps[-1][1]) / 2.0), min(len(x) / sr, last * 0.01 + pad)))
        return bounds

    def usable(runs):
        return [(a * 0.01, b * 0.01) for (a, b) in runs if a > first and b <= last]

    cands = usable(_silence_runs(rms, thr, 8))                  # every pause >= 0.08 s is a possible cut
    if len(cands) >= n - 1:
        picked = _align(cands, weights, first * 0.01, last * 0.01, n)
        if picked is not None:
            return clips_from(picked), "pauses"

    # fallback: where would the boundaries be if speaking speed were constant? then snap to quiet spots
    total = (last - first) * 0.01
    cum = np.cumsum(weights)[:-1] / weights.sum()
    all_gaps = usable(_silence_runs(rms, thr, 8))
    chosen, lo = [], first * 0.01
    for c in cum:
        target = first * 0.01 + c * total
        window = max(0.8, 0.15 * total)
        cands = [g for g in all_gaps if g[0] > lo and abs((g[0] + g[1]) / 2 - target) <= window]
        if cands:
            g = min(cands, key=lambda g_: abs((g_[0] + g_[1]) / 2 - target))
        else:
            i0, i1 = int(max(lo * 100 + 1, (target - 0.4) * 100)), int(min(last - 1, (target + 0.4) * 100))
            i = i0 + int(np.argmin(rms[i0:max(i1, i0 + 1)])) if i1 > i0 else int(target * 100)
            g = (i * 0.01, (i + 1) * 0.01)
        chosen.append(g)
        lo = g[1]
    return clips_from(chosen), "proportional"


def _align(gaps, weights, t_first, t_last, n):
    """Choose n-1 of the pauses as the cuts between lines. The longest pauses are not always the line breaks: a
    comma inside a long line can pause longer than the break before the next speaker (the dog's line was cut at
    its comma and its second half played in the boy's shot). So every choice is scored on both: how long its pauses
    are, and how well every line's length matches its text (speaking speed is about constant in one take).
    Dynamic programming over the pauses in order; returns the chosen gaps or None."""
    m = len(gaps)
    a = np.array([g[0] for g in gaps])
    b = np.array([g[1] for g in gaps])
    glen = np.maximum(b - a, 0.01)
    speech = (t_last - t_first) - 0.0                          # (pauses inside lines are part of a line's length)
    expect = speech * weights / weights.sum()
    gap_bonus = 0.6 * np.log(glen / 0.15)                      # a long pause is likely a line break
    INF = 1e18
    # cost[k][i]: best cost with the k-th cut (0-based) at gap i
    cost = np.full((n - 1, m), INF)
    back = np.zeros((n - 1, m), dtype=int)
    d0 = a - t_first                                           # line 0 runs from the first voice to gap i
    cost[0] = np.log(np.maximum(d0, 0.05) / expect[0]) ** 2 - gap_bonus
    for k in range(1, n - 1):
        for i in range(k, m):
            prev = np.arange(k - 1, i)
            d = a[i] - b[prev]                                 # line k runs from gap prev to gap i
            c = cost[k - 1][prev] + np.log(np.maximum(d, 0.05) / expect[k]) ** 2
            j = int(np.argmin(c))
            cost[k][i] = c[j] - gap_bonus[i]
            back[k][i] = prev[j]
    d_last = t_last - b                                        # the last line runs from the last cut to the end
    final = cost[n - 2] + np.log(np.maximum(d_last, 0.05) / expect[n - 1]) ** 2
    i = int(np.argmin(final))
    if final[i] >= INF / 2:
        return None
    chosen = [i]
    for k in range(n - 2, 0, -1):
        i = int(back[k][i])
        chosen.append(i)
    return [gaps[j] for j in reversed(chosen)]


# ------------------------------------------------------------------ public: one call for the whole script
def _shape(src, dst, st, rate):
    """Per-character pitch (semitones) + speed on a clip via ffmpeg. Writes dst; returns the path to use."""
    if abs(st) < 0.05 and abs(rate - 1.0) < 0.01:
        return src
    r = 2.0 ** (st / 12.0)
    flt = "asetrate=%d,aresample=%d,atempo=%.5f" % (round(SR * r), SR, max(0.5, min(2.0, rate / r)))
    try:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-af", flt, dst],
                       check=True, timeout=60, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return dst
    except Exception as e:
        print("  [gemini] pitch/rate shaping skipped: %s" % str(e)[:100], file=sys.stderr)
        return src


def synth_script(items, model=DEFAULT_MODEL, style=DEFAULT_STYLE, cache_dir=".cache/tts"):
    """items: [{"text": str, "voice": gemini voice name, "pitch": '+0Hz', "rate": '+0%'}] in speaking order.

    Returns [wav path per item]. Exactly ONE API request is made per distinct script (cached on disk).
    """
    if not items:
        return []
    # Gemini allows 2 speakers per request: extra voices share the 2 first ones (pitch/rate keep them apart)
    voices = []
    for it in items:
        if it["voice"] not in voices:
            voices.append(it["voice"])
    remap = {v: voices[i if i < 2 else i % 2] for i, v in enumerate(voices)}
    lines = [{"voice": remap[it["voice"]], "text": it["text"]} for it in items]

    key = hashlib.sha1(json.dumps([model, style, lines], ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
    d = os.path.join(cache_dir, "gemini_" + key)
    os.makedirs(d, exist_ok=True)
    full = os.path.join(d, "full.wav")
    if os.path.isfile(full) and os.path.getsize(full) > 2000:
        x, _ = read_wav(full)
        print("  [gemini] using cached voice (%d lines, no API call)" % len(items), file=sys.stderr)
    else:
        print("  [gemini] 1 request for %d lines (%s)" % (len(items), model), file=sys.stderr)
        x = request_audio(build_payload(lines, style), model)
        peak = float(np.abs(x).max()) if x.size else 0.0
        if peak > 1e-4:
            x = x * (0.9 / peak)                                   # one gain for the whole take
        write_wav(full, x)
    spans, method = split_audio(x, [it["text"] for it in items])
    if method != "pauses":
        print("  [gemini] pauses unclear, split lines by text length instead (check lip-sync)", file=sys.stderr)
    paths = []
    for i, ((t0, t1), it) in enumerate(zip(spans, items)):
        print("  [gemini] line %d  %5.2f-%5.2fs  %s" % (i + 1, t0, t1, it["text"][:40]), file=sys.stderr)
        raw = os.path.join(d, "line_%03d.wav" % i)
        write_wav(raw, x[int(t0 * SR): int(t1 * SR)])
        tag = hashlib.sha1(("%s|%s" % (it.get("pitch"), it.get("rate"))).encode()).hexdigest()[:6]
        paths.append(_shape(raw, os.path.join(d, "line_%03d_%s.wav" % (i, tag)),
                            semitones(it.get("pitch")), rate_factor(it.get("rate"))))
    return paths

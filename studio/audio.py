"""Audio helpers: Hindi TTS (edge-tts), generated SFX, a synthesized beat, lip-sync envelope."""
import hashlib
import math
import os
import subprocess
import sys
import wave

import numpy as np

from .util import ROOT, asset_path

SR = 44100
CACHE = os.path.join(ROOT, ".cache")


def _cache(sub):
    p = os.path.join(CACHE, sub)
    os.makedirs(p, exist_ok=True)
    return p


# ------------------------------------------------------------------ tts
DEFAULT_VOICE = "hi-IN-MadhurNeural"


def resolve_provider(requested=None, cfg=None):
    """-> (provider, explicit). provider is 'gemini' or 'edge'.

    Order: argument / --tts, env TTS_PROVIDER, scene meta.tts.provider, else 'auto'
    (auto = Gemini when GEMINI_API_KEY is set, otherwise edge-tts). `explicit` means the user asked for it
    by name, so a failure should stop the render instead of silently switching voice.
    """
    from . import gemini_tts
    p = str(requested or os.environ.get("TTS_PROVIDER") or (cfg or {}).get("provider") or "auto").lower()
    if p == "auto":
        return ("gemini" if gemini_tts.api_key() else "edge"), False
    if p in ("gemini", "edge"):
        return p, True
    raise SystemExit("unknown TTS provider %r (use auto | gemini | edge)" % p)


def have_tts():
    try:
        import edge_tts  # noqa: F401
        return True
    except Exception:
        return False


def synth_tts(text, voice=None, rate="+0%", pitch="+0Hz"):
    """Return path of an mp3 or None if synthesis is unavailable."""
    voice = voice or DEFAULT_VOICE
    key = hashlib.sha1(("%s|%s|%s|%s" % (text, voice, rate, pitch)).encode("utf-8")).hexdigest()[:16]
    out = os.path.join(_cache("tts"), key + ".mp3")
    if os.path.isfile(out) and os.path.getsize(out) > 1000:
        return out
    if not have_tts():
        return None
    cmd = [sys.executable, "-m", "edge_tts", "--voice", voice, "--text", text,
           "--rate=%s" % rate, "--pitch=%s" % pitch, "--write-media", out]
    try:
        subprocess.run(cmd, check=True, timeout=90, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    except Exception as e:  # network blocked, bad voice, timeout...
        print("  [tts] failed for %r: %s" % (text[:40], str(e)[:120]), file=sys.stderr)
        if os.path.isfile(out):
            os.remove(out)
        return None
    return out if os.path.isfile(out) and os.path.getsize(out) > 1000 else None


def audio_duration(path):
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                            "default=nw=1:nk=1", path], capture_output=True, text=True, timeout=30)
        return float(r.stdout.strip())
    except Exception:
        return None


def estimate_duration(text):
    return max(1.2, len(text) * 0.125 + 0.65)    # fitted on edge-tts hi-IN lines


def lip_envelope(path, fps):
    """Per-video-frame mouth openness (0..1) from the audio amplitude."""
    try:
        r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
                           capture_output=True, timeout=60)
        x = np.frombuffer(r.stdout, dtype=np.float32)
    except Exception:
        return None
    if x.size < 100:
        return None
    win = int(16000 / fps)
    n = x.size // win
    rms = np.sqrt((x[: n * win].reshape(n, win) ** 2).mean(axis=1))
    ref = np.percentile(rms, 92) + 1e-6
    env = np.clip(rms / ref, 0, 1) ** 0.8
    env = np.convolve(env, [0.25, 0.5, 0.25], mode="same")
    return env


# ------------------------------------------------------------------ sfx
def _write_wav(path, data):
    data = np.clip(data, -1, 1)
    pcm = (data * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def _t(d):
    return np.arange(int(SR * d)) / SR


def _env(t, a=0.005, decay=6.0):
    return np.minimum(1, t / a) * np.exp(-decay * t)


def _gen_sfx(name):
    rng = np.random.RandomState(5)
    if name == "pop":
        t = _t(0.12)
        f = 700 * np.exp(-14 * t) + 160
        return 0.8 * np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(t, 0.002, 28)
    if name == "boing":
        t = _t(0.7)
        f = 260 + 170 * np.sin(2 * np.pi * 9 * t) * np.exp(-3.2 * t) + 160 * np.exp(-5 * t)
        return 0.7 * np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(t, 0.004, 4.2)
    if name == "whoosh":
        t = _t(0.45)
        n = rng.randn(t.size)
        y = np.zeros_like(n)
        a = 0.12
        for i in range(1, n.size):
            y[i] = y[i - 1] + a * (n[i] - y[i - 1])
        env = np.sin(np.pi * np.clip(t / 0.45, 0, 1)) ** 2
        return 1.6 * y * env
    if name == "ding":
        t = _t(0.9)
        return 0.5 * (np.sin(2 * np.pi * 1318 * t) + 0.5 * np.sin(2 * np.pi * 1975 * t)) * _env(t, 0.002, 5)
    if name == "thud":
        t = _t(0.35)
        f = 110 * np.exp(-9 * t) + 38
        body = np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(t, 0.002, 11)
        noise = rng.randn(t.size) * _env(t, 0.001, 45) * 0.25
        return 0.95 * (body + noise)
    if name == "clap":
        t = _t(0.18)
        return 0.7 * rng.randn(t.size) * _env(t, 0.001, 30)
    if name == "beep":
        t = _t(0.45)
        return 0.35 * np.sin(2 * np.pi * 1000 * t) * np.minimum(1, (0.45 - t) / 0.01)
    if name == "laugh_track":
        t = _t(1.2)
        y = np.zeros_like(t)
        for k in range(7):
            c = 0.1 + k * 0.14
            g = np.exp(-((t - c) ** 2) / (2 * 0.03 ** 2))
            y += g * np.sin(2 * np.pi * (330 + 40 * (k % 2)) * t)
        return 0.4 * y
    return None


def sfx_path(name):
    """name can be a builtin sfx name or a path to an audio file."""
    if os.path.isfile(asset_path(name) or ""):
        return asset_path(name)
    out = os.path.join(_cache("sfx"), name + ".wav")
    if not os.path.isfile(out):
        data = _gen_sfx(name)
        if data is None:
            return None
        _write_wav(out, data)
    return out


# ------------------------------------------------------------------ beat
def _kick(n):
    t = _t(0.28)
    f = 130 * np.exp(-22 * t) + 46
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(t, 0.001, 9)
    return y


def _noise_hit(dur, decay, hp=True, seed=1):
    rng = np.random.RandomState(seed)
    t = _t(dur)
    n = rng.randn(t.size)
    if hp:
        n = np.concatenate([[0], np.diff(n)])
    return n * _env(t, 0.001, decay)


def _tone(freq, dur, decay=5.0, kind="saw"):
    t = _t(dur)
    if kind == "saw":
        y = 2 * ((t * freq) % 1.0) - 1
        y = np.convolve(y, np.ones(6) / 6, mode="same")
    elif kind == "tri":
        y = 2 * np.abs(2 * ((t * freq) % 1.0) - 1) - 1
    else:
        y = np.sin(2 * np.pi * freq * t)
    return y * _env(t, 0.004, decay)


def beat_path(bpm, duration, style="desi"):
    """Synthesized loopable-ish beat (kick/clap/hat/bass/pluck). Original, royalty free."""
    key = "beat_%s_%d_%d" % (style, int(bpm), int(math.ceil(duration)))
    out = os.path.join(_cache("music"), key + ".wav")
    if os.path.isfile(out):
        return out
    step = 60.0 / bpm / 4.0
    bars = int(math.ceil(duration / (step * 16))) + 1
    total = int(SR * (bars * 16 * step + 1.0))
    mix = np.zeros(total)

    def put(sig, pos, g=1.0):
        i = int(pos * SR)
        j = min(total, i + sig.size)
        if i < total:
            mix[i:j] += g * sig[: j - i]

    kick, clap, hat = _kick(0), _noise_hit(0.2, 22, False, 2), _noise_hit(0.06, 55, True, 3)
    open_hat = _noise_hit(0.2, 14, True, 4)
    dhol = _tone(92, 0.22, 12, "sine")
    bass_notes = [55.0, 55.0, 65.4, 73.4]               # A1 A1 C2 D2
    lead = [440.0, 523.3, 587.3, 659.3, 784.0]
    k_pat = "x..x..x...x.x..." if style == "desi" else "x...x...x...x..."
    c_pat = "....x.......x..."
    h_pat = "x.xxx.xxx.xxx.xx"
    rng = np.random.RandomState(11)
    for b in range(bars):
        base = b * 16 * step
        bn = bass_notes[b % len(bass_notes)]
        for i in range(16):
            tpos = base + i * step
            if k_pat[i] == "x":
                put(kick, tpos, 0.9)
            if c_pat[i] == "x":
                put(clap, tpos, 0.45)
            if h_pat[i] == "x":
                put(hat, tpos, 0.16)
            if i in (6, 14):
                put(open_hat, tpos, 0.1)
            if style == "desi" and i in (2, 10, 11):
                put(dhol, tpos, 0.35)
            if i % 4 in (0, 3):
                put(_tone(bn * (2 if i % 8 == 3 else 1), step * 3.2, 3.5, "saw"), tpos, 0.30)
            if i % 2 == 0 and rng.rand() < 0.75:
                put(_tone(lead[rng.randint(0, len(lead))], step * 2.5, 6.0, "tri"), tpos, 0.14)
    mix = mix[: int(SR * (duration + 0.5))]
    peak = np.abs(mix).max() + 1e-9
    _write_wav(out, mix / peak * 0.7)
    return out

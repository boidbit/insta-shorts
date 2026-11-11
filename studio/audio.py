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
    """-> (provider, explicit). provider is 'gemini', 'elevenlabs' or 'edge'.

    Order: argument / --tts, env TTS_PROVIDER, scene meta.tts.provider, else 'auto'
    (auto = Gemini when GEMINI_API_KEY is set, otherwise edge-tts). `explicit` means the user asked for it
    by name, so a Gemini failure stops the render instead of silently switching voice (ElevenLabs falls back to
    Gemini / edge with a warning: a used-up quota should not cost the whole video).
    """
    from . import gemini_tts
    p = str(requested or os.environ.get("TTS_PROVIDER") or (cfg or {}).get("provider") or "auto").lower()
    p = {"eleven": "elevenlabs", "11labs": "elevenlabs", "eleven_labs": "elevenlabs", "free": "edge"}.get(p, p)
    if p == "auto":
        return ("gemini" if gemini_tts.api_key() else "edge"), False
    if p in ("gemini", "edge", "elevenlabs"):
        return p, True
    raise SystemExit("unknown TTS provider %r (use auto | gemini | elevenlabs | edge)" % p)


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


def trim_silence(path):
    """Cut the dead air a voice has before and after a line (it adds up to long pauses between lines)."""
    # keyed by the CONTENT of the line: a Gemini line file is rewritten in place when the take is split again,
    # and a trim cached by file name alone handed back the old, wrongly cut voice
    with open(path, "rb") as f:
        tag = hashlib.sha1(f.read()).hexdigest()[:12]
    out = os.path.splitext(path)[0] + ".trim-%s.wav" % tag
    if os.path.isfile(out) and os.path.getsize(out) > 1000:
        return out
    flt = ("silenceremove=start_periods=1:start_threshold=-40dB:start_silence=0.03,areverse,"
           "silenceremove=start_periods=1:start_threshold=-40dB:start_silence=0.06,areverse")
    try:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-af", flt, "-ar", "24000", "-ac", "1", out],
                       check=True, timeout=60, capture_output=True)
    except Exception:
        return path
    if not (os.path.isfile(out) and os.path.getsize(out) > 1000):
        return path
    d0, d1 = audio_duration(path), audio_duration(out)
    if d0 and d1 is not None and d1 < 0.35 * d0:       # trimmed away the words themselves: keep the original
        return path
    return out


def shift_value(val, delta, unit):
    """'+10%' + 5 -> '+15%';  '-8Hz' + 6 -> '-2Hz'."""
    try:
        n = int(round(float(str(val).replace(unit, "").strip() or 0)))
    except ValueError:
        n = 0
    n += int(round(delta))
    return "%s%d%s" % ("+" if n >= 0 else "-", abs(n), unit)


# How a line is delivered (edge-tts) for each expression: (rate % change, pitch Hz change)
EMOTION_VOICE = {
    "angry": (8, 4), "shout": (10, 8), "determined": (5, 0), "disgust": (2, -4),
    "smile": (3, 4), "grin": (4, 5), "laugh": (6, 10), "lol": (6, 10), "excited": (9, 12), "love": (-2, 6),
    "wink": (2, 4), "blush": (0, 6), "sad": (-10, -8), "cry": (-8, -2), "hurt": (-6, -4), "bored": (-12, -6),
    "sleepy": (-14, -8), "scared": (10, 12), "nervous": (8, 8), "shock": (8, 14), "surprised": (6, 12),
    "smug": (-3, -4), "sly": (-4, -3), "proud": (-2, -2), "evil": (-6, -8), "think": (-6, -2), "confused": (-3, 4),
}


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
    if name in SFX2:
        d = SFX2[name]()
        return d / max(1e-6, float(np.abs(d).max())) * 0.85
    if name == "laugh_track":
        t = _t(1.2)
        y = np.zeros_like(t)
        for k in range(7):
            c = 0.1 + k * 0.14
            g = np.exp(-((t - c) ** 2) / (2 * 0.03 ** 2))
            y += g * np.sin(2 * np.pi * (330 + 40 * (k % 2)) * t)
        return 0.4 * y
    return None


# ------------------------------------------------------------------ more synthesized sfx
def _lp(x, cut):
    """One-pole low-pass (cut in Hz)."""
    a = math.exp(-2 * math.pi * cut / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(x.size):
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    return y


def _hp(x, cut):
    return x - _lp(x, cut)


def _bp(x, f0, q=4.0):
    """Biquad band-pass."""
    w0 = 2 * math.pi * f0 / SR
    al = math.sin(w0) / (2 * q)
    b0, b2 = al, -al
    a0, a1, a2 = 1 + al, -2 * math.cos(w0), 1 - al
    y = np.zeros_like(x)
    x1 = x2 = y1 = y2 = 0.0
    for i in range(x.size):
        v = (b0 * x[i] + b2 * x2 - a1 * y1 - a2 * y2) / a0
        x2, x1 = x1, x[i]
        y2, y1 = y1, v
        y[i] = v
    return y


def _sweep(f, dur):
    """Tone whose frequency follows f(t) (array of Hz)."""
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def _place(total, parts):
    out = np.zeros(int(SR * total))
    for start, sig in parts:
        i = int(start * SR)
        j = min(out.size, i + sig.size)
        out[i:j] += sig[: j - i]
    return out


def _noise(d, seed=0):
    return np.random.RandomState(seed).randn(int(SR * d))


def _s_slap():
    t = _t(0.25)
    return 0.9 * _hp(_noise(0.25, 1), 1200) * _env(t, 0.0005, 38) + 0.35 * np.sin(2 * np.pi * 180 * t) * _env(t, 0.001, 30)


def _s_punch():
    t = _t(0.35)
    f = 120 * np.exp(-14 * t) + 45
    return 1.0 * _sweep(f, 0.35) * _env(t, 0.001, 12) + 0.4 * _lp(_noise(0.35, 2), 900) * _env(t, 0.0005, 50)


def _s_knock():
    t = _t(0.12)
    k = (_bp(_noise(0.12, 3), 380, 6) * 3 + 0.5 * np.sin(2 * np.pi * 220 * t)) * _env(t, 0.0005, 45)
    return _place(0.75, [(0.0, k), (0.2, k * 0.9), (0.4, k)])


def _tone_h(freq, d, decay, harm=(1, 0.5, 0.25)):
    t = _t(d)
    return sum(a * np.sin(2 * np.pi * freq * (i + 1) * t) for i, a in enumerate(harm)) * _env(t, 0.003, decay)


def _s_doorbell():
    return 0.4 * _place(1.8, [(0.0, _tone_h(660, 1.0, 3)), (0.55, _tone_h(523, 1.2, 2.6))])


def _s_ring():
    t = _t(0.45)
    burst = 0.35 * (np.sin(2 * np.pi * 440 * t) + np.sin(2 * np.pi * 480 * t)) * (0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 20 * t)))
    burst *= np.minimum(1, t / 0.01) * np.minimum(1, (0.45 - t) / 0.02)
    return _place(1.7, [(0.0, burst), (0.6, burst), (1.2, burst * 0.0)])


def _s_vibrate():
    t = _t(0.4)
    b = 0.5 * np.sign(np.sin(2 * np.pi * 160 * t)) * np.minimum(1, t / 0.01) * np.minimum(1, (0.4 - t) / 0.02)
    return _lp(_place(1.1, [(0.0, b), (0.6, b)]), 1500)


def _s_horn():
    t = _t(0.7)
    vib = 1 + 0.01 * np.sin(2 * np.pi * 6 * t)
    h = np.sign(np.sin(2 * np.pi * 400 * vib * t)) + np.sign(np.sin(2 * np.pi * 505 * vib * t))
    return 0.25 * _lp(h, 2500) * np.minimum(1, t / 0.02) * np.minimum(1, (0.7 - t) / 0.05)


def _s_footsteps():
    t = _t(0.16)
    st = (_lp(_noise(0.16, 4), 600) * 2.5 + 0.4 * np.sin(2 * np.pi * 90 * t)) * _env(t, 0.002, 28)
    return 0.7 * _place(1.5, [(i * 0.36, st * (0.8 + 0.2 * (i % 2))) for i in range(4)])


def _s_scream():
    t = _t(1.1)
    f = 520 + 380 * np.minimum(1, t / 0.25) + 18 * np.sin(2 * np.pi * 7 * t)
    saw = 2 * ((np.cumsum(f) / SR) % 1.0) - 1
    v = _bp(saw, 950, 3) * 2.2 + _bp(saw, 2400, 4) * 1.2
    return 0.8 * v * np.minimum(1, t / 0.05) * np.minimum(1, (1.1 - t) / 0.25)


def _s_heartbeat():
    t = _t(0.18)
    th = np.sin(2 * np.pi * 55 * t) * _env(t, 0.004, 22)
    return 1.0 * _place(2.5, [(0.0, th), (0.22, th * 0.7), (0.85, th), (1.07, th * 0.7), (1.7, th), (1.92, th * 0.7)])


def _s_record_scratch():
    t = _t(0.55)
    f = 300 + 700 * np.abs(np.sin(2 * np.pi * 2.2 * t)) + 200 * np.sin(2 * np.pi * 30 * t)
    tone = _sweep(f, 0.55)
    n = _bp(_noise(0.55, 5), 1800, 2)
    return 0.6 * (tone * 0.5 + n * 2.0) * (0.4 + 0.6 * np.abs(np.sin(2 * np.pi * 4.4 * t))) * np.minimum(1, (0.55 - t) / 0.05)


def _s_sad_trombone():
    parts = []
    for i, (f, d) in enumerate(((233.1, 0.42), (220.0, 0.42), (207.7, 0.42), (196.0, 1.3))):
        t = _t(d)
        vib = 1 + (0.03 * np.sin(2 * np.pi * 6 * t) if i == 3 else 0)
        saw = 2 * ((np.cumsum(f * vib) / SR) % 1.0) - 1
        env = np.minimum(1, t / 0.04) * np.minimum(1, (d - t) / 0.08)
        parts.append((i * 0.45, _lp(saw, 900) * env * 0.7))
    return _place(2.7, parts)


def _s_rooster():
    parts = []
    for (st, d, f0, f1) in ((0.0, 0.18, 520, 720), (0.22, 0.18, 620, 760), (0.44, 0.2, 700, 820), (0.68, 0.7, 820, 560)):
        t = _t(d)
        f = f0 + (f1 - f0) * (t / d) + 30 * np.sin(2 * np.pi * 12 * t)
        saw = 2 * ((np.cumsum(f) / SR) % 1.0) - 1
        parts.append((st, _bp(saw, 1300, 2.5) * 2 * np.minimum(1, t / 0.02) * np.minimum(1, (d - t) / 0.05)))
    return 0.8 * _place(1.5, parts)


def _s_thunder():
    t = _t(3.0)
    rumble = _lp(_noise(3.0, 6), 120) * 9 * np.minimum(1, t / 0.05) * np.exp(-1.1 * t) * (1 + 0.5 * np.sin(2 * np.pi * 1.3 * t))
    crack = _hp(_noise(3.0, 7), 2000) * np.exp(-30 * t) * 0.8
    return np.clip(rumble + crack, -1, 1)


def _s_wind():
    t = _t(3.0)
    return 2.5 * _bp(_noise(3.0, 8), 500, 1.2) * (0.4 + 0.6 * np.sin(np.pi * t / 3.0)) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.7 * t))


def _s_crowd_cheer():
    t = _t(2.6)
    v = sum(_bp(_noise(2.6, 20 + i), 500 + i * 230, 3) * (0.8 + 0.2 * np.sin(2 * np.pi * (3 + i) * t)) for i in range(5))
    env = np.minimum(1, t / 0.3) * np.minimum(1, (2.6 - t) / 0.8)
    return 1.6 * v * env + 0.5 * _s_applause()[: t.size] * env


def _s_bat_hit():
    t = _t(0.3)
    return 0.7 * (np.sin(2 * np.pi * 1250 * t) + 0.6 * np.sin(2 * np.pi * 2180 * t)) * _env(t, 0.0005, 26) +         0.5 * _hp(_noise(0.3, 9), 3000) * _env(t, 0.0003, 120)


def _s_crickets():
    t = _t(0.05)
    chirp = np.sin(2 * np.pi * 4500 * t) * np.sin(np.pi * t / 0.05)
    parts = []
    for k in range(4):
        for j in range(3):
            parts.append((k * 0.55 + j * 0.06, chirp * 0.3))
    return _place(2.4, parts)


def _s_drumroll():
    hits = []
    tt = 0.0
    gap = 0.09
    while tt < 1.4:
        h = _hp(_noise(0.08, int(tt * 1000)), 1500) * _env(_t(0.08), 0.0005, 45) * (0.4 + 0.4 * tt)
        hits.append((tt, h))
        tt += gap
        gap = max(0.035, gap * 0.93)
    t = _t(1.2)
    crash = _hp(_noise(1.2, 77), 3000) * np.exp(-3 * t) * 0.7
    return _place(2.8, hits + [(1.45, crash)])


def _s_cash():
    t = _t(0.9)
    bell = 0.35 * (np.sin(2 * np.pi * 1480 * t) + 0.7 * np.sin(2 * np.pi * 2350 * t) + 0.4 * np.sin(2 * np.pi * 3700 * t)) * _env(t, 0.002, 4)
    rattle = _hp(_noise(0.25, 10), 4000) * _env(_t(0.25), 0.001, 14) * 0.4
    return _place(1.3, [(0.0, rattle), (0.2, bell)])


def _s_whistle():
    t = _t(0.7)
    f = 2800 * (1 + 0.04 * np.sign(np.sin(2 * np.pi * 28 * t)))
    return 0.35 * _sweep(f, 0.7) * np.minimum(1, t / 0.01) * np.minimum(1, (0.7 - t) / 0.05)


def _s_tick():
    t = _t(0.05)
    k = _hp(_noise(0.05, 11), 3000) * _env(t, 0.0003, 160)
    return _place(2.0, [(i * 0.5, k * (1 if i % 2 == 0 else 0.7)) for i in range(4)])


def _s_applause():
    parts = []
    rng = np.random.RandomState(12)
    for i in range(160):
        c = _hp(_noise(0.04, 100 + i), 900) * _env(_t(0.04), 0.0005, 70) * rng.uniform(0.2, 0.5)
        parts.append((rng.uniform(0, 2.4), c))
    return _place(2.6, parts)


def _s_cooker():
    """Pressure cooker whistle: hiss building up, then the shrill whistle (synthesized, royalty free)."""
    t = _t(1.6)
    hiss = _bp(_noise(1.6, 21), 3200, 1.5) * np.minimum(1, t / 0.5) * 0.35
    tw = _t(0.9)
    f = 1650 + 120 * np.sin(2 * np.pi * 7 * tw) + 260 * np.minimum(1, tw / 0.15)
    whistle = (0.45 * _sweep(f, 0.9) + 0.25 * _sweep(f * 2.01, 0.9)) * np.minimum(1, tw / 0.06) * np.minimum(1, (0.9 - tw) / 0.12)
    whistle += 0.3 * _bp(_noise(0.9, 22), 2400, 3) * np.minimum(1, tw / 0.06) * np.minimum(1, (0.9 - tw) / 0.12)
    return _place(1.8, [(0.0, hiss), (0.75, whistle)])


def _s_siren():
    """Ambulance / police siren: two tones going up and down."""
    t = _t(2.4)
    f = 760 + 280 * (np.sin(2 * np.pi * 0.9 * t) > 0)
    f = _lp(f.astype(float), 18)
    y = 0.4 * (_sweep(f, 2.4) + 0.4 * _sweep(f * 2, 2.4) + 0.2 * _sweep(f * 3, 2.4))
    return y * np.minimum(1, t / 0.05) * np.minimum(1, (2.4 - t) / 0.2)


def _s_train_horn():
    """A long train horn: a low chord of three notes."""
    t = _t(1.8)
    env = np.minimum(1, t / 0.08) * np.minimum(1, (1.8 - t) / 0.3)
    y = sum(a * np.sign(np.sin(2 * np.pi * f * t)) for f, a in ((233, 0.18), (277, 0.15), (349, 0.12)))
    return _lp(y, 1600) * env * 1.6


def _s_dhol():
    """Dhol: deep bass hits and sharp high slaps in a bhangra rhythm."""
    def hit(f0, d, dec, seed):
        tt = _t(d)
        f = f0 * (1 + 0.6 * np.exp(-30 * tt))
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(tt, 0.001, dec) + \
            0.25 * _bp(_noise(d, seed), f0 * 4, 2) * _env(tt, 0.0005, dec * 3)
    low, high = hit(70, 0.5, 8, 31) * 0.9, hit(330, 0.2, 22, 32) * 0.6
    beat = 0.32
    parts = []
    for bar in range(2):
        b0 = bar * beat * 4
        parts += [(b0, low), (b0 + beat * 1.5, high), (b0 + beat * 2, low), (b0 + beat * 2.5, high),
                  (b0 + beat * 3, high), (b0 + beat * 3.5, high)]
    return _place(2.8, parts)


def _s_shehnai():
    """A shehnai-like reed phrase (wedding / sad moment), a few bent notes."""
    notes = [(587, 0.35), (659, 0.3), (698, 0.5), (659, 0.3), (587, 0.7)]
    parts, at = [], 0.0
    for f0, d in notes:
        tt = _t(d)
        f = f0 * (1 + 0.012 * np.sin(2 * np.pi * 5.5 * tt)) * (1 - 0.02 * np.exp(-20 * tt))
        ph = np.cumsum(f) / SR
        y = 0.5 * np.sin(2 * np.pi * ph) + 0.35 * np.sin(4 * np.pi * ph) + 0.25 * np.sin(6 * np.pi * ph) + \
            0.15 * np.sin(8 * np.pi * ph)
        y *= np.minimum(1, tt / 0.04) * np.minimum(1, (d - tt) / 0.06)
        parts.append((at, 0.5 * _lp(y, 3200)))
        at += d * 0.95
    return _place(at + 0.2, parts)


def _s_baby_cry():
    """A baby crying: wailing 'waa' cries rising and falling."""
    parts = []
    for i, (d, f0) in enumerate(((0.8, 420), (0.6, 460), (1.0, 440))):
        tt = _t(d)
        f = f0 * (1 + 0.25 * np.sin(np.pi * tt / d)) * (1 + 0.03 * np.sin(2 * np.pi * 9 * tt))
        ph = np.cumsum(f) / SR
        y = sum(a * np.sin(2 * np.pi * k * ph) for k, a in ((1, 0.5), (2, 0.4), (3, 0.3), (4, 0.15)))
        y = _bp(y, 1100, 1.2) * 1.5 + 0.2 * y
        y *= np.minimum(1, tt / 0.06) * np.minimum(1, (d - tt) / 0.15)
        parts.append((sum(x for x, _ in ((0.8, 0), (0.6, 0), (1.0, 0))[:i]) + 0.15 * i, 0.45 * y))
    return _place(2.9, parts)


def _s_glass_break():
    """Glass breaking: a sharp crack and tinkling pieces."""
    t = _t(0.3)
    crack = _hp(_noise(0.3, 41), 2500) * _env(t, 0.0003, 30) * 0.9
    parts = [(0.0, crack)]
    rng = np.random.RandomState(42)
    for i in range(18):
        tt = _t(0.25)
        f = rng.uniform(2500, 6000)
        tink = np.sin(2 * np.pi * f * tt) * _env(tt, 0.0005, rng.uniform(18, 40)) * rng.uniform(0.1, 0.3)
        parts.append((0.03 + rng.uniform(0, 0.7) * (i / 18.0) ** 0.7, tink))
    return _place(1.2, parts)


SFX2 = {"slap": _s_slap, "punch": _s_punch, "knock": _s_knock, "doorbell": _s_doorbell, "ring": _s_ring,
        "vibrate": _s_vibrate, "horn": _s_horn, "footsteps": _s_footsteps, "scream": _s_scream,
        "heartbeat": _s_heartbeat, "record_scratch": _s_record_scratch, "sad_trombone": _s_sad_trombone,
        "rooster": _s_rooster, "thunder": _s_thunder, "wind": _s_wind, "crowd_cheer": _s_crowd_cheer,
        "bat_hit": _s_bat_hit, "crickets": _s_crickets, "drumroll": _s_drumroll, "cash": _s_cash,
        "whistle": _s_whistle, "tick": _s_tick, "applause": _s_applause, "cooker": _s_cooker, "siren": _s_siren,
        "train_horn": _s_train_horn, "dhol": _s_dhol, "shehnai": _s_shehnai, "baby_cry": _s_baby_cry,
        "glass_break": _s_glass_break}
SFX_NAMES = ("pop", "boing", "whoosh", "ding", "thud", "clap", "beep", "laugh_track") + tuple(SFX2)


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


# Mood presets for the generated music.  scale = semitone steps from the root; chords = root offsets per bar.
MOODS = {
    "desi":     dict(kick="x..x..x...x.x...", clap="....x.......x...", hat="x.xxx.xxx.xxx.xx", dhol=True, root=110.0,
                     scale=(0, 3, 5, 7, 10), chords=(0, 0, 3, 5), lead="tri", lead_p=0.75, bass=True),
    "soft":     dict(kick="x...x...x...x...", clap="....x.......x...", hat="x.x.x.x.x.x.x.x.", root=110.0,
                     scale=(0, 3, 5, 7, 10), chords=(0, 0, 3, 5), lead="tri", lead_p=0.6, bass=True),
    "pop":      dict(kick="x...x...x...x...", clap="....x.......x...", hat="xxxxxxxxxxxxxxxx", root=130.8,
                     scale=(0, 2, 4, 7, 9), chords=(0, 7, 9, 5), lead="tri", lead_p=0.7, bass=True),
    "comedy":   dict(kick="x.......x.......", clap="....x.......x...", hat="", root=130.8, scale=(0, 2, 4, 5, 7, 9, 11),
                     chords=(0, 5, 7, 0), lead="pluck", lead_p=0.85, bass="oompah", staccato=True),
    "suspense": dict(kick="x...............", clap="", hat="..x...x...x...x.", root=55.0, scale=(0, 1, 3, 6, 7),
                     chords=(0, 0, 1, 0), lead="pad", lead_p=0.25, bass="drone", boom=True),
    "sad":      dict(kick="", clap="", hat="", root=110.0, scale=(0, 2, 3, 5, 7, 8, 10), chords=(0, 8, 3, 10),
                     lead="piano", lead_p=0.5, bass="pad", arp=True),
    "festive":  dict(kick="x.x.x..xx.x.x..x", clap="....x..x....x..x", hat="x.xxx.xxx.xxx.xx", dhol=True, root=130.8,
                     scale=(0, 2, 4, 5, 7, 9, 10), chords=(0, 0, 5, 7), lead="shehnai", lead_p=0.8, bass=True),
    "lofi":     dict(kick="x......x..x.....", clap="....x.......x...", hat="x.x.x.x.x.x.x.x.", root=98.0,
                     scale=(0, 3, 5, 7, 10), chords=(0, 5, 3, 8), lead="piano", lead_p=0.35, bass="pad", crackle=True,
                     swing=0.18),
}


def _note(root, steps, deg, octave=0):
    n = len(steps)
    return root * 2 ** ((steps[deg % n] + 12 * (deg // n + octave)) / 12.0)


def _inst(kind, f, dur):
    t = _t(dur)
    if kind == "pluck":
        return (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)) * _env(t, 0.002, 14)
    if kind == "piano":
        return (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(4 * np.pi * f * t) + 0.15 * np.sin(6 * np.pi * f * t)) * _env(t, 0.004, 3.2)
    if kind == "pad":
        return (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.005 * t)) * np.minimum(1, t / 0.3) * \
            np.minimum(1, np.maximum(0, dur - t) / 0.3)
    if kind == "shehnai":
        vib = 1 + 0.012 * np.sin(2 * np.pi * 6 * t)
        saw = 2 * ((np.cumsum(f * vib) / SR) % 1.0) - 1
        return _lp(saw, 2600) * np.minimum(1, t / 0.03) * np.minimum(1, np.maximum(0, dur - t) / 0.05)
    return _tone(f, dur, 6.0, "tri")


def beat_path(bpm, duration, style="desi", seed=None):
    """Synthesized background music in a mood (see MOODS). Original, royalty free.
    seed changes the melody, so two videos with the same mood/bpm don't sound identical."""
    M = MOODS.get(style, MOODS["soft"])
    if seed is None:
        seed = 11
    key = "music_%s_%d_%d_%s" % (style, int(bpm), int(math.ceil(duration)), seed)
    out = os.path.join(_cache("music"), key + ".wav")
    if os.path.isfile(out):
        return out
    step = 60.0 / bpm / 4.0
    bars = int(math.ceil(duration / (step * 16))) + 1
    total = int(SR * (bars * 16 * step + 2.0))
    mix = np.zeros(total)

    def put(sig, pos, g=1.0):
        i = int(pos * SR)
        j = min(total, i + sig.size)
        if 0 <= i < total:
            mix[i:j] += g * sig[: j - i]

    kick, clap, hat = _kick(0), _noise_hit(0.2, 22, False, 2), _noise_hit(0.06, 55, True, 3)
    open_hat = _noise_hit(0.2, 14, True, 4)
    dhol = _tone(92, 0.22, 12, "sine")
    rng = np.random.RandomState(int(seed) % (2 ** 31))
    root, scale = M["root"], M["scale"]
    swing = M.get("swing", 0.0)
    deg = 0
    for b in range(bars):
        base = b * 16 * step
        ch = M["chords"][b % len(M["chords"])]
        broot = root * 2 ** (ch / 12.0)
        if M.get("bass") == "drone" and b % 2 == 0:
            put(_inst("pad", broot / 2, step * 32), base, 0.32)
        if M.get("bass") == "pad":
            for semi in (0, 3 if 3 in scale else 4, 7):
                put(_inst("pad", broot * 2 ** (semi / 12.0), step * 16), base, 0.09)
        if M.get("boom") and b % 2 == 1:
            put(_tone(42, 1.2, 2.2, "sine"), base, 0.5)
        for i in range(16):
            tpos = base + i * step + (swing * step if i % 2 else 0.0)
            if M["kick"] and M["kick"][i] == "x":
                put(kick, tpos, 0.9)
            if M["clap"] and M["clap"][i] == "x":
                put(clap, tpos, 0.45)
            if M["hat"] and M["hat"][i] == "x":
                put(hat, tpos, 0.16)
            if M["hat"] and i in (6, 14):
                put(open_hat, tpos, 0.1)
            if M.get("dhol") and i in (2, 10, 11):
                put(dhol, tpos, 0.35)
            if M.get("bass") is True and i % 4 in (0, 3):
                put(_tone(broot / 2 * (2 if i % 8 == 3 else 1), step * 3.2, 3.5, "saw"), tpos, 0.30)
            if M.get("bass") == "oompah" and i % 4 == 0:
                put(_inst("pluck", broot / 2 if i % 8 == 0 else broot * 0.75, step * 2), tpos, 0.45)
            if M.get("arp") and i % 2 == 0:
                put(_inst("piano", _note(broot, scale, (i // 2) % 4 * 2), step * 6), tpos, 0.16)
            every = 2 if M["lead"] not in ("pad",) else 8
            if i % every == 0 and rng.rand() < M["lead_p"]:
                deg = int(np.clip(deg + rng.choice([-2, -1, 1, 1, 2, 3]), 0, len(scale) * 2 - 1))
                ln = step * (2.5 if not M.get("staccato") else 1.2) * (4 if M["lead"] == "pad" else 1)
                put(_inst(M["lead"], _note(broot * 2, scale, deg), ln), tpos, 0.14 if M["lead"] != "pad" else 0.1)
    if M.get("crackle"):
        cr = np.zeros(total)
        idx = rng.randint(0, total, size=int(total / SR * 30))
        cr[idx] = rng.uniform(-0.4, 0.4, size=idx.size)
        mix += cr
    mix = mix[: int(SR * (duration + 0.5))]
    peak = np.abs(mix).max() + 1e-9
    _write_wav(out, mix / peak * 0.7)
    return out


# ------------------------------------------------------------------ ambience beds (looped by ffmpeg)
AMBIENCE = ("rain", "street", "office", "night", "jungle", "crowd", "wind", "sea", "train", "engine", "cabin")


def ambience_path(kind):
    out = os.path.join(_cache("ambience"), kind + ".wav")
    if os.path.isfile(out):
        return out
    d = 8.0
    t = _t(d)
    rng = np.random.RandomState(abs(hash(kind)) % 1000)
    if kind == "rain":
        sig = _bp(_noise(d, 31), 2500, 0.8) * 0.8 + _lp(_noise(d, 32), 400) * 0.6
        drops = np.zeros(t.size)
        for i in rng.randint(0, t.size - 2000, 260):
            drops[i:i + 400] += _hp(_noise(400 / SR, int(i % 97)), 3000)[:400] * np.exp(-np.arange(400) / 60.0) * 0.5
        sig += drops
    elif kind == "street":
        sig = _lp(_noise(d, 33), 250) * 3.0
        for st in (1.2, 5.1):
            sig += _place(d, [(st, _s_horn() * 0.25)])
        sig += _bp(_noise(d, 34), 700, 1.5) * 0.5 * (0.6 + 0.4 * np.sin(2 * np.pi * 0.3 * t))
    elif kind == "office":
        sig = 0.15 * np.sin(2 * np.pi * 120 * t) + _lp(_noise(d, 35), 800) * 0.8
        k = _hp(_noise(0.03, 36), 2500) * _env(_t(0.03), 0.0003, 150) * 0.6
        sig += _place(d, [(x, k) for x in np.cumsum(rng.uniform(0.08, 0.35, 40)) if x < d - 0.1])
    elif kind == "night":
        ch = _s_crickets()
        sig = _place(d, [(0.0, ch), (2.6, ch * 0.8), (5.3, ch)]) + _bp(_noise(d, 37), 400, 1) * 0.2
    elif kind == "jungle":
        sig = _place(d, [(0.0, _s_crickets() * 0.6), (4.0, _s_crickets() * 0.5)])
        for st in rng.uniform(0, d - 0.5, 9):
            tt = _t(0.25)
            f = 2200 + 900 * np.sin(2 * np.pi * 9 * tt)
            sig += _place(d, [(st, _sweep(f, 0.25) * np.sin(np.pi * tt / 0.25) * 0.25)])
        sig += _bp(_noise(d, 38), 500, 1) * 0.25
    elif kind == "crowd":
        sig = sum(_bp(_noise(d, 40 + i), 400 + i * 260, 3) * (0.7 + 0.3 * np.sin(2 * np.pi * (0.5 + i * 0.3) * t)) for i in range(5))
    elif kind == "sea":
        sig = _lp(_noise(d, 41), 700) * 2.5 * (0.35 + 0.65 * np.sin(np.pi * ((t / 4.0) % 1.0)) ** 2)
    elif kind == "train":                # rumble + the clack of the wheels over the rail joints
        sig = _lp(_noise(d, 42), 160) * 3.0 + 0.2 * np.sin(2 * np.pi * 55 * t)
        clack = _bp(_noise(0.05, 43), 900, 2) * _env(_t(0.05), 0.001, 70)
        sig += _place(d, [(i * 0.62 + dt, clack * 1.2) for i in range(int(d / 0.62)) for dt in (0.0, 0.11)])
    elif kind == "engine":               # a bus / car / auto engine and the road
        sig = (0.35 * np.sin(2 * np.pi * 38 * t) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.4 * t))
               + _lp(_noise(d, 44), 300) * 2.0 + _bp(_noise(d, 45), 1200, 1.2) * 0.25)
    elif kind == "cabin":                # a plane's steady hum
        sig = _lp(_noise(d, 46), 500) * 2.2 + 0.12 * np.sin(2 * np.pi * 110 * t)
    else:  # wind
        sig = _s_wind()
        sig = np.concatenate([sig, sig[::-1], sig])[: t.size]
    fade = int(SR * 0.3)                 # soft loop seam
    sig[:fade] *= np.linspace(0, 1, fade)
    sig[-fade:] *= np.linspace(1, 0, fade)
    _write_wav(out, sig / (np.abs(sig).max() + 1e-9) * 0.6)
    return out

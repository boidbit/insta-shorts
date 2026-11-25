"""Where each line really ends in a Gemini take: speech recognition (faster-whisper) listens to the take and the
script's words are matched to what was heard.

Why: cutting a take at its pauses cannot tell a comma from a line break. Gappu's "Jab gharwale aur duniya aap pe
haste the, toh aapne haar kyun nahi maani?" was cut at the comma; "toh aapne haar..." went into Reelesh's first clip
(the camera on Reelesh, Gappu's words heard) and every later Reelesh clip was a line behind.

Optional: without faster-whisper (or its model) this returns None and the pause cut is used as before.
"""
import difflib
import os
import re
import sys

import numpy as np

MODEL = os.environ.get("ALIGN_MODEL", "small")
_model = [None]

# a sound skeleton of Hindi: aspirated = plain consonant, no vowel signs / nukta / nasal marks, so the script's
# "घरवाले" and the recogniser's "गर्वाले" read the same
_SAME = str.maketrans({"घ": "ग", "ध": "द", "भ": "ब", "थ": "त", "ख": "क", "छ": "च", "झ": "ज", "ठ": "ट",
                       "ढ": "ड", "फ": "प", "ण": "न", "श": "स", "ष": "स", "ऋ": "र", "व": "ब", "ङ": "न", "ञ": "न"})
_DROP = re.compile(r"[ऀ-ःऺ-ॏ॑-ॗॢॣ॰ॱ\s\W_\d]+")
_VOWELS = re.compile(r"[ऄ-औॠॡ]")


def skeleton(text):
    s = str(text).translate(_SAME)
    s = _VOWELS.sub("", s)
    return _DROP.sub("", s).lower()


def _load():
    if _model[0] is None:
        from faster_whisper import WhisperModel
        _model[0] = WhisperModel(MODEL, device="cpu", compute_type="int8")
    return _model[0]


def words(x, sr):
    """[(start, end, word)] heard in the take (seconds)."""
    a = np.asarray(x, dtype=np.float32)
    if sr != 16000:
        a = np.interp(np.arange(0, len(a), sr / 16000.0), np.arange(len(a)), a).astype(np.float32)
    segs, _ = _load().transcribe(a, language="hi", beam_size=1, word_timestamps=True, vad_filter=False,
                                 condition_on_previous_text=False)
    out = []
    for s in segs:
        for w in (s.words or []):
            out.append((float(w.start), float(w.end), w.word))
    return out


def boundaries(heard, texts):
    """Time of each line break (len(texts)-1 values, or None where the match is unsure) from the heard words."""
    chars, times = [], []                           # every heard skeleton letter with its time
    for (w0, w1, w) in heard:
        sk = skeleton(w)
        for i, ch in enumerate(sk):
            chars.append(ch)
            times.append(w0 + (w1 - w0) * (i + 0.5) / len(sk))
    want, starts = "", []
    for t in texts:
        starts.append(len(want))
        want += skeleton(t)
    if not chars or not want:
        return None
    sm = difflib.SequenceMatcher(None, want, "".join(chars), autojunk=False)
    pairs = [(b.a + k, b.b + k) for b in sm.get_matching_blocks() for k in range(b.size)]
    if len(pairs) < 0.5 * len(want):                # heard something else: do not trust it
        return None
    a_idx = np.array([p[0] for p in pairs])
    out = []
    for k in range(1, len(texts)):
        e = starts[k]
        before = [i for i in range(len(a_idx)) if e - 6 <= a_idx[i] < e]       # the last letters of the line
        after = [i for i in range(len(a_idx)) if e <= a_idx[i] < e + 6]        # the first letters of the next
        if not before or not after:
            out.append(None)
            continue
        t_end = times[pairs[before[-1]][1]]
        t_next = times[pairs[after[0]][1]]
        out.append((t_end + t_next) / 2.0 if t_next >= t_end else None)
    return out


def pauses(x, sr, min_len=8):
    """Every pause in the take (>= 0.08 s, the same measure as the pause cut) as (start, end) seconds."""
    from . import gemini_tts as G
    hop = int(sr * 0.01)
    m = len(x) // hop
    if m < 5:
        return []
    rms = np.sqrt((np.asarray(x[: m * hop], dtype=np.float64).reshape(m, hop) ** 2).mean(axis=1))
    thr = max(float(np.percentile(rms, 95)) * 0.05, 1e-4)
    return [(a * 0.01, b * 0.01) for (a, b) in G._silence_runs(rms, thr, min_len)]


def fix_spans(x, sr, texts, spans, tol=0.35, pad=0.12):
    """The pause cut checked by ear: where a heard line break is more than `tol` s away from the cut, the cut moves
    to the quietest spot by the heard break. Returns (spans, number of cuts moved) - the spans unchanged when the
    recogniser is not there or not sure."""
    if len(texts) < 2:
        return spans, 0
    try:
        heard = words(x, sr)
    except Exception as e:                          # not installed / model not downloadable: the pause cut stays
        print("  [align] no speech recognition (%s): pause cut kept" % str(e)[:120], file=sys.stderr)
        return spans, 0
    cuts = boundaries(heard, texts)
    if cuts is None:
        print("  [align] the take did not match its script well enough: pause cut kept", file=sys.stderr)
        return spans, 0
    # the recogniser's word times are off by up to ~a second, so it does not place the cut: it says WHICH pause is
    # the line break (a comma's pause or the real break), and the cut goes in the middle of that pause
    gaps = pauses(x, sr)
    old = [(spans[k - 1][1] + spans[k][0]) / 2.0 for k in range(1, len(spans))]
    cut, moved = [], 0
    for o, tb in zip(old, cuts):
        if tb is None or not gaps:
            cut.append(o)
            continue
        g = min(gaps, key=lambda g_: max(0.0, g_[0] - tb, tb - g_[1]) + 0.05 * abs((g_[0] + g_[1]) / 2 - tb))
        if g[0] - 0.05 <= o <= g[1] + 0.05 or abs(tb - o) <= tol:
            cut.append(o)                           # the pause cut already is in that pause
        else:
            cut.append((g[0] + g[1]) / 2.0)
            moved += 1
    if not moved:
        return spans, 0
    end = len(x) / float(sr)
    edges = [spans[0][0]] + cut + [spans[-1][1]]
    for i in range(1, len(edges)):                  # in order, every line at least 0.2 s
        edges[i] = max(edges[i], edges[i - 1] + 0.2)
    if edges[-1] > end:
        return spans, 0
    new = [(spans[0][0] if k == 0 else max(0.0, edges[k] - pad * 0.5),
            spans[-1][1] if k == len(spans) - 1 else min(end, edges[k + 1] + pad * 0.5)) for k in range(len(spans))]
    return new, moved

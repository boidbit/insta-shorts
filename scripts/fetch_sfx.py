"""Fetch a real CC0 sound effect from Freesound into the studio, the same way every time.

    python scripts/fetch_sfx.py <name> "<search words>" --list          # show the best CC0 matches, change nothing
    python scripts/fetch_sfx.py <name> "<search words>" [--id N] [--max S] [--loud L] [--filter F] [--dur A-B]

<name>   script word, lowercase a-z 0-9 _ (e.g. vine_boom). Becomes assets/sfx/<name>.ogg and is then usable in a
         script line like any other sound: `A (shock, vine_boom): ...`. A builtin name (boing, thud...) is replaced
         by the recording.
--max    keep at most S seconds (default 3.0)       --loud   loudness target LUFS (default -16; hits -14, beds -22)
--filter extra ffmpeg filter                        --dur    allowed source length, default 0.2-30

Only CC0 (public domain) sounds are taken: safe for monetised reels, no credit needed (listed in CREDITS.md anyway).
It trims leading silence, fades, normalises loudness, writes mono OGG Vorbis, adds the CREDITS row and refreshes
the word lists (SCRIPT_PROMPT.md sound line, index.html vocab) so tests stay green.
Auth: FREESOUND_API_KEY (GitHub secret; the "Fetch sounds" workflow runs this). In a Claude cloud session with a
Freesound network secret the proxy adds the key by itself.
Needs curl and ffmpeg.
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SFX_DIR = os.path.join(ROOT, "assets", "sfx")
CC0 = "publicdomain/zero"
FIELDS = "id,name,username,license,url,duration,avg_rating,num_downloads,previews"


def api(path):
    cmd = ["curl", "-s", "--max-time", "30"]
    if os.environ.get("FREESOUND_API_KEY"):
        cmd += ["-H", "Authorization: Token " + os.environ["FREESOUND_API_KEY"]]
    out = subprocess.run(cmd + ["https://freesound.org/apiv2/" + path], capture_output=True, text=True).stdout
    data = json.loads(out or "{}")
    if "detail" in data:
        sys.exit("Freesound: %s (API key set up?)" % data["detail"])
    return data


def search(query, dur):
    a, b = dur.split("-")
    q = urllib.parse.urlencode({"query": query, "filter": 'license:"Creative Commons 0" duration:[%s TO %s]' % (a, b),
                                "sort": "rating_desc", "page_size": 10, "fields": FIELDS})
    res = api("search/text/?" + q).get("results", [])
    return sorted(res, key=lambda s: -s["avg_rating"] * math.log10(10 + s["num_downloads"]))


def show(s):
    return "%8d %5.1fs r%.1f dl%6d  %s  [%s]" % (s["id"], s["duration"], s["avg_rating"], s["num_downloads"],
                                                  s["name"][:60], s["username"])


def refresh_word_lists():
    """SCRIPT_PROMPT.md's sound line and the page's vocab follow studio.script (tests compare them)."""
    sys.path.insert(0, ROOT)
    for m in [k for k in list(sys.modules) if k.startswith("studio")]:
        del sys.modules[m]
    from studio import script
    prompt = os.path.join(ROOT, "SCRIPT_PROMPT.md")
    t = open(prompt, encoding="utf-8").read()
    t = re.sub(r"(?m)^(  - optional sound: ).*$", lambda m: m.group(1) + ", ".join(script.SFX), t, count=1)
    open(prompt, "w", encoding="utf-8").write(t)
    page = os.path.join(ROOT, "index.html")
    h = open(page, encoding="utf-8").read()
    h = re.sub(r'(<script type="application/json" id="vocab">)(.*?)(</script>)',
               lambda m: m.group(1) + json.dumps(script.vocab(), ensure_ascii=False, separators=(",", ":")) + m.group(3), h, count=1, flags=re.S)
    open(page, "w", encoding="utf-8").write(h)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("query", nargs="?", default="")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--id", type=int)
    ap.add_argument("--max", type=float, default=3.0)
    ap.add_argument("--loud", type=float, default=-16.0)
    ap.add_argument("--filter")
    ap.add_argument("--dur", default="0.2-30")
    a = ap.parse_args()
    if not re.fullmatch(r"[a-z0-9_]+", a.name) or not (a.query or a.id):
        ap.error("name = a-z 0-9 _ and give search words or --id")
    if a.id:
        snd = api("sounds/%d/?fields=%s" % (a.id, FIELDS))
    else:
        found = search(a.query, a.dur)
        if not found:
            sys.exit('No CC0 sound for "%s". Try other words or a wider --dur.' % a.query)
        if a.list:
            print('CC0 matches for "%s":' % a.query)
            for s in found:
                print(show(s))
            return
        snd = found[0]
    if CC0 not in snd["license"]:
        sys.exit("Sound %s is not CC0 (%s): only CC0 is allowed." % (snd["id"], snd["license"]))
    print("Using " + show(snd))
    fade = max(0.05, min(0.5, a.max * 0.15))
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "src.mp3")
        subprocess.run(["curl", "-s", "-L", "--max-time", "120", "-o", src, snd["previews"]["preview-hq-mp3"]], check=True)
        filters = ",".join(["silenceremove=start_periods=1:start_threshold=-45dB"] + ([a.filter] if a.filter else []) +
                           ["atrim=0:%s" % a.max, "afade=t=in:d=0.01", "areverse,afade=t=in:d=%s,areverse" % fade,
                            "loudnorm=I=%s:TP=-1.5:LRA=11" % a.loud, "alimiter=limit=0.84:level=false"])
        out = os.path.join(SFX_DIR, a.name + ".ogg")
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", src, "-af", filters, "-ar", "44100",
                        "-ac", "1", "-c:a", "libvorbis", "-q:a", "5", out], check=True)
    secs = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out],
                                capture_output=True, text=True).stdout)
    print("Wrote assets/sfx/%s.ogg (%.2f s)" % (a.name, secs))
    credits = os.path.join(SFX_DIR, "CREDITS.md")
    t = open(credits, encoding="utf-8").read()
    row = "| `%s` | Freesound #%s `%s` | %s (CC0 1.0) | %s |" % (a.name, snd["id"], snd["name"].replace("|", "/"),
                                                               snd["username"], snd["url"])
    pat = re.compile(r"(?m)^\| `%s` \|.*$" % re.escape(a.name))
    if pat.search(t):
        t = pat.sub(lambda m: row, t)
    else:
        rows = list(re.finditer(r"(?m)^\| `[a-z0-9_]+` \|.*$", t))
        at = rows[-1].end() if rows else len(t)
        t = t[:at] + "\n" + row + t[at:]
    open(credits, "w", encoding="utf-8").write(t)
    refresh_word_lists()
    print('Done. Use it in a script: `A (shock, %s): ...`' % a.name)


if __name__ == "__main__":
    main()

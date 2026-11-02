"""Plain-text script -> scene.json, no AI needed.

    python -m studio.script my_script.txt -o scenes/my_video.json

Script format (one thing per line):

    HOOK: Mummy ka ek kaam... aur hum 😭
    CAST: M = mummy, R = college_boy, D = boy cap
    SCENE: room
    M (think, point): Beta, jaldi se doodh le aana! | बेटा, जल्दी से दूध ले आना!
    R (grin): Haan mummy, bas 2 minute!
    R -> exit right
    SCENE: street | Raste me... 🚶
    R -> enter left
    D (wave, ball): Bhai! Ek match ho jaye?
    ALL -> jump laugh
    CTA: Tag karo us dost ko 👇
    CAPTION: Instagram post caption (not shown in the video)
    HASHTAGS: #desicomedy #mummy

- `NAME (words): Roman text | देवनागरी` is a spoken line. The part after `|` is what the
  Hindi voice reads; without it the voice reads the Roman text (pronunciation may be off).
  Words in brackets can be expressions, actions, props, point directions, sfx, "shake".
- `NAME -> ...` is an action without speech: enter/exit left|right, walk left|center|right,
  any action / expression.  `ALL -> ...` does it for everybody in the scene.
- `SCENE: background | title` starts a new place (kitchen, room, street, school, market, office, bus_stop, night_road,
  plain), or your own picture: `SCENE: gali` uses assets/backgrounds/gali.png (.jpg/.webp), or a path `SCENE: assets/backgrounds/gali.jpg`.
- `wait 1.5` (or `...`) pauses.
- Shots: `CUT` starts a new shot in the same place (a hard cut) and shows only the characters who speak or act in it;
  `CUT wide` = everybody small so a whole vehicle fits, `CUT inside` = the inside of a vehicle (the driver big, in
  the middle), `CUT medium` (default) = people big. `SCENE: place | title | wide` sets the framing of a scene too.
  A shot with a vehicle is "wide" by itself. One scale for the whole world: a vehicle is always in proportion to the
  people next to it, a rider is as big as somebody standing.
- Camera (optional, the camera already cuts in on every speaker by itself): `wide`, `medium`, `close`,
  `two_shot` in the brackets of a line, e.g. `A (shock, close): ...` or `A -> shock close`.
- Vehicles: `A -> ride bike` (also truck, car, auto, scooter, cycle; `ride auto back` = the second seat) hops A on,
  `A -> getoff` (or `getoff left|right`) hops off. `A -> ride truck enter left to center` = the vehicle drives in
  from the left with A already inside. The vehicle is made bigger while somebody rides it.
- Depth: `near` (step towards the camera, bigger), `far` (step back, smaller), `mid` (back to normal),
  e.g. `B -> near smug`.

Just a chat (a separate, tiny format - not part of the story format):

    CHAT: Mummy ❤️
    < Beta khana kha liya?
    > Haan mummy 😅
    < Jhooth mat bol, ghar aa!
    CTA: Tag karo 👇

`<` = the other person (left, with a "typing..." moment first), `>` = you (right). Optional: HOOK, CTA, CAPTION,
HASHTAGS, MUSIC. No characters, no voice.

Just lyrics (no format at all): if the text has no CAST/SCENE line, no `A = ...`, no `A -> ...` and no
`NAME: ...` speaker line, every line is a lyric shown on screen while one singer walks down a night road:

    Raat lambi hai, raasta khamosh
    Chalta hu bina manzil ke
    Chaand bhi saath chal raha hai

Optional lines still work in that mode: `SECONDS: 60` (total length; default 3.2 s per lyric), `MUSIC: beat 76` /
`MUSIC: none` / `MUSIC: path`, `HOOK:`, `CTA:`, `CAPTION:`, `HASHTAGS:`.
"""
import argparse
import os
import re

from . import actions, audio, objects, rides
from .characters import ACCESSORIES, EXPRESSIONS, HAIR_COLORS, HAIR_STYLES, LOOKS, OUTFITS, PALETTE, SKIN_TONES
from .util import asset_path
from .scene import DEPTHS, SHOT_ALIASES, SHOT_ZOOM, SLOTS, chat_length

HEADERS = ("HOOK", "CAST", "SCENE", "CTA", "CAPTION", "HASHTAGS", "MUSIC", "TRANSITION")
BACKGROUNDS = ("kitchen", "room", "street", "school", "market", "office", "bus_stop", "night_road", "plain")
PROPS = ("spoon", "phone", "mic", "cup", "ball", "stick", "bag")
SFX = ("pop", "boing", "whoosh", "ding", "thud", "clap", "beep", "laugh_track")
NARRATION_NAMES = ("narrator", "vo", "narration", "voiceover", "voice_over")   # a voice with no body
NARRATOR_SPEC = {"hidden": True, "voice": {"name": "hi-IN-MadhurNeural", "pitch": "-12Hz", "rate": "-4%",
                                           "gemini": "Charon"}}
GETOFF_WORDS = ("getoff", "utar", "dismount")
FRAMINGS = ("wide", "medium", "inside")
SHOTS = tuple(SHOT_ZOOM) + tuple(SHOT_ALIASES)       # camera: wide, medium, close, two_shot (+ spellings)
DEPTH_WORDS = tuple(DEPTHS)                         # near / mid / far: step towards or away from the camera
DIRECTIONS = ("left", "right", "up", "down", "up_left", "up_right")
ROLE_LOOKS = {
    "mummy": "aunty", "mom": "aunty", "maa": "aunty", "mother": "aunty", "chachi": "aunty", "padosan": "aunty",
    "papa": "uncle", "dad": "uncle", "father": "uncle", "chacha": "uncle", "padosi": "uncle", "uncle": "uncle",
    "aunty": "aunty", "dadi": "dadi", "nani": "dadi", "dada": "dada", "nana": "dada",
    "dost": "boy", "friend": "boy", "bhai": "college_boy", "brother": "college_boy", "beta": "college_boy",
    "behen": "college_girl", "sister": "college_girl", "beti": "college_girl", "didi": "college_girl",
    "teacher": "office_guy", "boss": "office_guy", "bachcha": "kid", "student": "kid",
}
FEMALE_LOOKS = {"girl", "college_girl", "aunty", "dadi", "kid_girl", "office_girl"}
PITCHES = ["+0Hz", "+14Hz", "-8Hz", "+24Hz", "-14Hz"]
BUILDS = ("slim", "normal", "chubby")
GENDER_WORDS = ("female", "woman", "ladki", "aurat", "male", "man", "ladka", "aadmi")
MOVE_WORDS = ("enter", "exit", "walk", "left", "right", "center", "up", "down", "up_left", "up_right",
              "pump", "swing", "cheer", "disco", "shake", "drop", "noprop")


def vocab():
    """Every word the script format understands (the web page keeps a copy for its checker)."""
    return {
        "places": sorted(BACKGROUNDS),
        "looks": sorted(LOOKS), "roles": sorted(ROLE_LOOKS),
        "extras": sorted(set(ACCESSORIES) | set(HAIR_STYLES) | set(OUTFITS) | set(SKIN_TONES) | set(BUILDS)
                         | set(GENDER_WORDS) | set(PALETTE) | set(HAIR_COLORS)),
        "expressions": sorted(EXPRESSIONS), "actions": sorted(actions.ACTIONS),
        "props": sorted(PROPS), "sfx": sorted(SFX), "moves": sorted(MOVE_WORDS),
        "shots": sorted(SHOTS), "depth": sorted(DEPTH_WORDS),
        "objects": sorted(set(objects.OBJECTS) | set(objects.ALIASES)),
        "object_words": ["center", "enter", "exit", "front", "go", "left", "right", "to"],
        "rides": sorted(rides.RIDES), "ride_words": sorted(("ride", "back", "driver") + GETOFF_WORDS),
        "framings": sorted(FRAMINGS),
    }


def _words(s):
    """'shock | point, [tshirt]' -> ['shock', 'point', 'tshirt']"""
    words = (w.strip("[](){}'\"") for w in re.split(r"[\s,|]+", s.strip().lower()))
    return [w for w in words if w]


def cast_spec(words, index, unknown=None):
    """'aunty chubby glasses maroon female' -> character spec (with a voice).
    Words that mean nothing here are added to `unknown`."""
    spec, acc = {}, []
    female = None
    for w in words:
        if w in LOOKS and "look" not in spec:
            spec["look"] = w
        elif w in ROLE_LOOKS and "look" not in spec:
            spec["look"] = ROLE_LOOKS[w]
        elif w in ACCESSORIES:
            acc.append(w)
        elif w in HAIR_STYLES:
            spec["hair"] = w
        elif w in OUTFITS:
            spec["outfit"] = w
        elif w in SKIN_TONES:
            spec["skin"] = w
        elif w in ("slim", "normal", "chubby"):
            spec["build"] = w
        elif w in ("female", "woman", "ladki", "aurat"):
            female = True
        elif w in ("male", "man", "ladka", "aadmi"):
            female = False
        elif w in PALETTE and "color" not in spec:
            spec["color"] = w
        elif w in HAIR_COLORS and "hair_color" not in spec:
            spec["hair_color"] = w
        elif unknown is not None and w not in LOOKS and w not in ROLE_LOOKS and w not in PALETTE:
            unknown.append(w)
    spec.setdefault("look", "college_girl" if female else "boy")
    if acc:
        spec["accessories"] = sorted(set(LOOKS[spec["look"]].get("accessories", [])) | set(acc))
    if female is None:
        female = spec["look"] in FEMALE_LOOKS
    voice = {"name": "hi-IN-SwaraNeural" if female else "hi-IN-MadhurNeural",
             "pitch": PITCHES[index % len(PITCHES)], "rate": "+0%"}
    if spec["look"] in ("kid", "kid_girl"):
        voice.update(pitch="+30Hz", rate="+8%")
    elif spec["look"] in ("dada", "dadi"):
        voice.update(pitch="-10Hz", rate="-8%")
    spec["voice"] = voice
    return spec


def _stage(tokens, ev, scene_cast, who):
    """Apply bracket / arrow words to an event dict.
    Returns (move request or None, unknown words, words that were overridden)."""
    move = None
    unknown, acts, exprs = [], [], []
    i = 0
    while i < len(tokens):
        w = tokens[i]
        nxt = tokens[i + 1] if i + 1 < len(tokens) else None
        if w == "ride":
            kind = objects.resolve_kind(nxt) if nxt else None
            if kind and rides.rideable(kind):
                spec = {"kind": kind}
                i += 1
                while i + 1 < len(tokens):                  # back | driver | enter left|right | to left|center|right
                    t1, t2 = tokens[i + 1], tokens[i + 2] if i + 2 < len(tokens) else None
                    if t1 in ("back", "driver"):
                        spec["seat"] = t1
                        i += 1
                    elif t1 == "enter" and t2 in ("left", "right"):
                        spec["enter"] = t2
                        i += 2
                    elif t1 == "to" and t2 in ("left", "center", "right"):
                        spec["at"] = t2
                        i += 2
                    else:
                        break
                ev["ride"] = spec
            else:
                unknown.append("ride %s (%s)" % (nxt or "?", ", ".join(sorted(rides.RIDES))))
                i += 1 if nxt else 0
        elif w in GETOFF_WORDS:
            spec = {}
            if nxt in ("left", "right"):
                spec["side"] = nxt
                i += 1
            ev["getoff"] = spec
        elif w in ("enter", "exit") and nxt in ("left", "right"):
            move = (w, nxt)
            i += 1
        elif w == "walk" and nxt in ("left", "center", "right"):
            move = ("walk", nxt)
            i += 1
        elif w == "point":
            ev["action"] = "point"
            acts.append(w)
            if nxt in DIRECTIONS:
                ev["point"] = nxt
                i += 1
        # laugh / shock / cry are also expressions and clap is also a sound: once the line has
        # an action, such a word becomes the face (or the sound) instead
        elif w in actions.ACTIONS and not (acts and (w in EXPRESSIONS or w in SFX)):
            ev["action"] = w
            acts.append(w)
            if w == "dance" and nxt in ("pump", "swing", "cheer", "disco"):
                ev["style"] = nxt
                i += 1
        elif w in EXPRESSIONS:
            ev["expression"] = w
            exprs.append(w)
        elif w in PROPS or w in ("drop", "noprop"):
            ev["prop"] = "" if w in ("drop", "noprop") else w
        elif w in SFX:
            ev["sfx"] = w
            ev["volume"] = 0.6
        elif w == "shake":
            ev["camera"] = {"shake": 0.6}
        elif w in SHOTS:
            ev["shot"] = SHOT_ALIASES.get(w, w)
        elif w in DEPTH_WORDS:
            ev["depth"] = w
        elif w in ("left", "right") and "facing" not in ev:
            ev["facing"] = w
        else:
            unknown.append(w)
        i += 1
    if ev.get("action") == "point" and "point" not in ev and who in scene_cast:
        ev["point"] = "right" if scene_cast.index(who) < len(scene_cast) / 2.0 else "left"
    lost = acts[:-1] + exprs[:-1]       # only the last action / expression of a line is used
    return move, unknown, lost


def _slot_x(cast, name):
    n = len(cast)
    slots = SLOTS.get(n, SLOTS[3])
    names = ["center"] if n == 1 else (["left", "right"] if n == 2 else ["left", "center", "right"])
    return slots[names[min(cast.index(name), len(names) - 1)]], names[min(cast.index(name), len(names) - 1)]


LYRIC_META = ("HOOK", "CTA", "CAPTION", "HASHTAGS", "MUSIC", "SECONDS")
LYRIC_STEP = 3.2          # seconds each lyric stays on screen when SECONDS is not given


def _split_lyrics(text):
    """(meta, lyric lines) if `text` is just lyrics, else None (it is a structured script)."""
    meta, lyrics = {}, []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        m = re.match(r"^([A-Za-z_]+)\s*:\s*(.*)$", line)
        if m and m.group(1).upper() in LYRIC_META:
            meta[m.group(1).upper()] = m.group(2).strip()
            continue
        if (m and m.group(1).upper() in HEADERS) \
                or re.match(r"^[A-Za-z_]\w*\s*(=|->)\s*\S", line) \
                or re.match(r"^(?:wait\s*[\d.]+|\.\.\.+)$", line, re.I) \
                or re.match(r"^[A-Za-z_]\w*\s*(?:\([^)]*\))?\s*:\s*\S", line):
            return None
        lyrics.append(line.partition("|")[0].strip() or line)     # `Roman | देवनागरी`: show the first part
    return (meta, lyrics) if lyrics else None


def parse_lyrics(meta, lyrics):
    """Plain lyrics -> a one-singer night-road reel (same look as templates/song_reel.json)."""
    warnings = []
    try:
        total = float(meta["SECONDS"]) if meta.get("SECONDS") else len(lyrics) * LYRIC_STEP + 1.0
    except ValueError:
        warnings.append("SECONDS: %r number nahi hai, default length use hui" % meta["SECONDS"])
        total = len(lyrics) * LYRIC_STEP + 1.0
    total = max(6.0, min(total, 180.0))
    step = (total - 1.0) / len(lyrics)
    if step < 1.6:
        warnings.append("%d lyrics %.0f sec me bahut tez hain (har line %.1f sec): SECONDS badhao ya lines kam karo"
                        % (len(lyrics), total, step))
    overlays = [{"text": t, "style": "lyric", "pos": [540, 610],
                 "from": round(0.3 + i * step, 2), "to": round(0.3 + (i + 1) * step - 0.1, 2)}
                for i, t in enumerate(lyrics)]
    hook = meta.get("HOOK", "")
    if hook:
        overlays.append({"text": hook, "style": "hook", "pos": [540, 330], "from": 0.0, "to": 2.0})
    if meta.get("CTA"):
        overlays.append({"text": meta["CTA"], "style": "card", "pos": [540, 1000], "color": [236, 90, 70],
                         "from": round(total - 2.6, 2)})
    timeline = [{"t": 0.0, "who": "M", "action": "walk", "hands": "pockets", "expression": "smug",
                 "speed": 0.9, "look": "right"}]
    for i in range(1, len(lyrics), 2):          # a smile every other line, so the face is not frozen
        timeline.append({"t": round(0.3 + i * step, 2), "who": "M", "expression": "smile" if i % 4 == 1 else "smug"})
    mv = meta.get("MUSIC", "").strip()
    if mv.lower() == "none":
        music = None
    elif mv and not mv.lower().startswith("beat"):
        music = {"path": mv, "volume": 0.55}
    else:
        bpm = re.findall(r"\d+", mv)
        music = {"type": "beat", "bpm": int(bpm[0]) if bpm else 76, "style": "soft", "volume": 0.45}
    scene = {
        "hook": hook,
        "meta": {"fps": 30, "duration": round(total, 1), "fade_in": 0.6, "fade_out": 0.8},
        "background": {"type": "night_road", "scroll": 220},
        "characters": {"M": {"look": "college_boy", "outfit": "kurta", "color": "teal", "pants": "white",
                             "hair": "side_part", "accessories": ["beard"], "slot": "center",
                             "facing": "right", "y": 1690}},
        "overlays": overlays,
        "timeline": timeline,
        "post": {"caption": meta.get("CAPTION") or hook or lyrics[0],
                 "hashtags": meta.get("HASHTAGS", "#songreel #desivibes #indianreels").split()},
    }
    if music:
        scene["music"] = music
    return scene, warnings


IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp")


def resolve_background(raw):
    """`street` / `gali` (= assets/backgrounds/gali.png) / `assets/backgrounds/x.jpg` -> (background dict, warning)."""
    name = raw.strip()
    low = name.lower().replace(" ", "_")
    if low in BACKGROUNDS:
        return {"type": low}, None
    is_path = name.lower().endswith(IMAGE_EXT)
    stems = [name, name.replace(" ", "_"), low]
    tries = [name] if is_path else [os.path.join("assets", "backgrounds", st + ext) for st in dict.fromkeys(stems)
                                    for ext in IMAGE_EXT]
    for t in tries:
        if os.path.isfile(asset_path(t)):
            return {"type": "image", "path": t.replace(os.sep, "/")}, None
    if is_path:
        return {"type": "room"}, "SCENE %r: ye image nahi mili (file assets/backgrounds/ me daalo) -> using room" % name
    return {"type": "room"}, "unknown place %r -> using room" % low


def parse_obj(rest):
    """`truck enter left to right` -> ({"kind": "truck", "enter": "left", "at": "right"}, [problems])."""
    raw = rest.split()
    spec, bad = {}, []
    if not raw:
        return None, ["OBJ: ke baad object ka naam likho (%s)" % ", ".join(sorted(objects.OBJECTS))]
    kind = objects.resolve_kind(raw[0])
    if not kind:
        return None, ["OBJ %r: ye object nahi hai (%s, ya apni .png)" % (raw[0], ", ".join(sorted(objects.OBJECTS)))]
    spec["kind"] = kind if kind in objects.OBJECTS else raw[0]
    i = 1
    while i < len(raw):
        w = raw[i].lower()
        nxt = raw[i + 1].lower() if i + 1 < len(raw) else None
        if w in ("enter", "exit", "go") and nxt in ("left", "right", "center"):
            spec[w] = nxt
            i += 1
        elif w == "to" and nxt in ("left", "right", "center"):
            spec["at"] = nxt
            i += 1
        elif w in ("left", "right", "center"):
            spec["at"] = w
        elif w == "front":
            spec["front"] = True
        elif w in ("big", "small"):
            spec["scale"] = 1.35 if w == "big" else 0.7
        elif w in PALETTE:
            spec["color"] = w
        else:
            bad.append(w)
        i += 1
    if spec.get("enter") == "center" or spec.get("exit") == "center":
        return None, ["OBJ %s: enter/exit sirf left ya right se hota hai" % raw[0]]
    if spec.get("go") and not spec.get("at"):
        spec["at"] = spec["go"]
    return spec, ["OBJ %s: %s samajh nahi aaye" % (raw[0], ", ".join(repr(b) for b in bad))] if bad else []


CHAT_META = ("HOOK", "CTA", "CAPTION", "HASHTAGS", "MUSIC", "CHAT", "SECONDS")


def _split_chat(text):
    """(meta, title, messages) if `text` is a chat (lines starting with < or >), else None."""
    meta, msgs, title = {}, [], ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        m = re.match(r"^([A-Za-z_]+)\s*:\s*(.*)$", line)
        if m and m.group(1).upper() in CHAT_META:
            if m.group(1).upper() == "CHAT":
                title = m.group(2).strip()
            else:
                meta[m.group(1).upper()] = m.group(2).strip()
            continue
        m = re.match(r"^([<>])\s*(.*)$", line) or re.match(r"^CHAT\s+(left|right)\s*:\s*(.*)$", line, re.I)
        if not m:
            return None                     # a story script (or lyrics) with a stray line: not a chat
        side = "left" if m.group(1) in ("<", "left") or m.group(1).lower() == "left" else "right"
        msgs.append({"side": side, "text": m.group(2).partition("|")[0].strip()})
    return (meta, title, msgs) if msgs else None


def parse_chat(meta, title, msgs):
    """Just a phone chat (no characters, no voice): `< other person` / `> me`, optional HOOK / CTA / CAPTION."""
    warnings = []
    kept = []
    for m in msgs:
        if m["text"]:
            kept.append(m)
        else:
            warnings.append("chat: khali message chhod diya")
    if len(kept) > 12:
        warnings.append("chat bahut lambi hai (%d messages): purane messages upar se nikal jaayenge" % len(kept))
    chat = {"title": title or "Chat", "messages": kept}
    length = chat_length(len(kept), chat)
    hook = meta.get("HOOK", "")
    overlays = [{"text": hook, "style": "hook", "pos": [540, 190], "from": 0.0, "to": 2.2}] if hook else []
    timeline = [{"wait": round(length, 2)}]
    if meta.get("CTA"):
        timeline.append({"hold": 2.0, "sfx": "pop", "volume": 0.5,
                         "overlay": {"text": meta["CTA"], "style": "card", "pos": [540, 1350], "color": [236, 90, 70]}})
    mv = meta.get("MUSIC", "").strip()
    music = None
    if mv.lower().startswith("beat"):
        bpm = re.findall(r"\d+", mv)
        music = {"type": "beat", "bpm": int(bpm[0]) if bpm else 90, "style": "soft", "volume": 0.3}
    elif mv and mv.lower() != "none":
        music = {"path": mv, "volume": 0.4}
    scene = {"hook": hook, "meta": {"fps": 30, "tail": 0.6}, "background": {"type": "plain"}, "characters": {},
             "overlays": overlays, "timeline": timeline, "chat": chat,
             "post": {"caption": meta.get("CAPTION") or hook or (kept[0]["text"] if kept else ""),
                      "hashtags": meta.get("HASHTAGS", "#chat #funny #relatable").split()}}
    if music:
        scene["music"] = music
    return scene, warnings


def parse_script(text):
    """Return (scene dict, warnings)."""
    cht = _split_chat(text)
    if cht:
        return parse_chat(*cht)
    lyr = _split_lyrics(text)
    if lyr:
        return parse_lyrics(*lyr)
    meta = {}
    cast = {}
    scenes = []
    warnings = []
    cur = None

    def new_scene(bg="room", title=None):
        sc = {"background": bg if isinstance(bg, dict) else {"type": bg}, "lines": [], "title": title}
        scenes.append(sc)
        return sc

    def add_cast(name, words):
        if name not in cast:
            unknown = []
            cast[name] = cast_spec(words, len(cast), unknown)
            if unknown:
                warnings.append("CAST %s: %s samajh nahi aaye. Sirf look/role + extras likho, "
                                "jaise 'A = college_girl earrings saree'" % (name, ", ".join(repr(u) for u in unknown)))

    declared = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        m = re.match(r"^([A-Za-z_]+)\s*:\s*(.*)$", line)
        if m and m.group(1).upper() in HEADERS:
            key, val = m.group(1).upper(), m.group(2).strip()
            if key == "CAST":
                declared = True
                # split before every "NAME =", so commas inside a character's words don't break it
                for part in re.split(r",\s*(?=[A-Za-z_]\w*\s*=)", val):
                    if "=" in part:
                        n, w = part.split("=", 1)
                        add_cast(n.strip(), _words(w))
            elif key == "SCENE":
                bg, _, rest = val.partition("|")
                title, _, frame = rest.partition("|")
                bg, warn = resolve_background(bg.strip() or "room")
                if warn:
                    warnings.append(warn)
                frame = frame.strip().lower()
                if frame and frame not in FRAMINGS:
                    warnings.append("SCENE framing %r: wide / medium / inside" % frame)
                    frame = ""
                cur = new_scene(bg, title.strip() or None)
                cur["framing"] = frame or None
            else:
                meta[key] = val
            continue
        m = re.match(r"^([A-Za-z_][\w]*)\s*=\s*(.+)$", line)
        if m:
            declared = True
            add_cast(m.group(1), _words(m.group(2)))
            continue
        if cur is None:
            cur = new_scene()
        if re.match(r"^(CHAT\b|[<>]\s*\S)", line, re.I):
            warnings.append("chat alag format hai, story script me nahi chalta (chat ke liye alag text likho: "
                            "'< samne wala' / '> aap'): %r" % line[:40])
            continue
        m = re.match(r"^(?:CUT|SHOT)\b\s*:?\s*(\w*)\s*$", line, re.I)
        if m:                                       # a new shot in the same place: a hard cut, its own set of characters
            frame = m.group(1).lower()
            if frame and frame not in FRAMINGS:
                warnings.append("CUT %r: framing wide / medium / inside likho" % frame)
                frame = ""
            cur = new_scene(dict(cur["background"]), None)
            cur["cut_in"], cur["framing"] = True, frame or None
            continue
        m = re.match(r"^OBJ\s*:\s*(.*)$", line, re.I)
        if m:
            spec, probs = parse_obj(m.group(1))
            warnings += probs
            if spec:
                cur["lines"].append(("obj", spec))
            continue
        m = re.match(r"^(?:wait\s*([\d.]+)|\.\.\.+)$", line, re.I)
        if m:
            cur["lines"].append(("wait", float(m.group(1) or 1.0)))
            continue
        m = re.match(r"^([A-Za-z_][\w]*)\s*->\s*(.+)$", line)
        if m:
            cur["lines"].append(("do", m.group(1), _words(m.group(2)), line))
            continue
        m = re.match(r"^([A-Za-z_][\w]*)\s*(?:\(([^)]*)\))?\s*:\s*(.+)$", line)
        if m:
            say, _, speak = m.group(3).partition("|")
            bracket = m.group(2) or ""
            if re.search(r"[?!]", bracket) or len(_words(bracket)) > 5:
                warnings.append("line %r: brackets me dialogue likha hai. Brackets me sirf acting words aate hain, "
                                "jaise (shock, point); dialogue ':' ke baad likho" % line[:50])
                bracket = ""
            who_ = "NARRATOR" if m.group(1).lower() in NARRATION_NAMES else m.group(1)
            cur["lines"].append(("say", who_, _words(bracket), say.strip(), speak.strip(), line))
            continue
        warnings.append("line not understood: %r" % line[:60])

    if not scenes:
        raise ValueError("script has no lines")

    # ---- build timelines ----
    out_scenes = []
    for si, sc in enumerate(scenes):
        order = []
        for ln in sc["lines"]:
            if ln[0] in ("do", "say") and ln[1].upper() not in ("ALL", "NARRATOR") and ln[1] not in order:
                order.append(ln[1])
        narrated = any(ln[0] == "say" and ln[1] == "NARRATOR" for ln in sc["lines"])
        for name in order:
            if declared and name not in cast:
                warnings.append("%s CAST me nahi hai: CAST line me '%s = <role/look>' jodo" % (name, name))
            add_cast(name, [])
        chars = {}
        for name in order:
            x, slot = _slot_x(order, name)
            facing = "front" if len(order) != 2 else ("right" if slot == "left" else "left")
            chars[name] = {"slot": slot, "facing": facing}
        tl = [{"t": 0.0, "who": "all", "action": "idle", "expression": "smile"}]
        if si == 0:
            tl.append({"t": 0.0, "sfx": "whoosh", "volume": 0.7, "camera": {"shake": 0.5}})
        first = True
        for ln in sc["lines"]:
            if ln[0] == "wait":
                tl.append({"wait": ln[1]})
                continue
            if ln[0] == "obj":
                oev = {"obj": ln[1]}
                if first:
                    oev["t"] = 0.1
                    first = False
                tl.append(oev)
                continue
            who = "all" if ln[1].upper() == "ALL" else ln[1]
            ev = {"who": who}
            if first:
                ev["t"] = 0.3 if si == 0 else 0.2
            move, unknown, lost = _stage(ln[2], ev, order, who)
            if unknown:
                warnings.append("line %r: %s samajh nahi aaye (acting words ki list dekho)"
                                % (ln[-1][:50], ", ".join(repr(u) for u in unknown)))
            if lost:
                warnings.append("line %r: ek line me ek hi action aur ek hi expression chalta hai; %s ignore hue"
                                % (ln[-1][:50], ", ".join(repr(u) for u in lost)))
            if move and who != "all":
                x, _slot = _slot_x(order, who)
                kind, side = move
                if kind == "enter":
                    chars[who]["x"] = -140 if side == "left" else 1200
                    chars[who]["facing"] = "right" if side == "left" else "left"
                    ev["move"] = {"x": x, "dur": 1.1}
                    ev.setdefault("hold", 1.1)
                elif kind == "exit":
                    ev["facing"] = side
                    ev["move"] = {"x": -160 if side == "left" else 1240, "dur": 1.1}
                    ev.setdefault("hold", 1.1)
                else:
                    ev["move"] = {"x": SLOTS[3][side], "dur": 1.0}
                    ev.setdefault("hold", 1.0)
            if ln[0] == "say":
                ev["say"], ev["speak"] = ln[3], ln[4] or ln[3]
                if not ln[4] and not re.search(r"[ऀ-ॿ]", ln[3]):
                    warnings.append("no Devanagari for %r: the voice will read Roman letters" % ln[3][:30])
                others = [o for o in order if o != who]
                if who == "NARRATOR":
                    ev["bubble"], ev["subtitle"] = False, True
                    for key in ("action", "expression", "prop", "move", "camera", "sfx", "volume", "facing", "look"):
                        ev.pop(key, None)                       # a voice has no body to act with
                elif len(order) == 2 and others:
                    ev.setdefault("look", others[0])
            elif ev.get("action") in actions.DANCES:
                ev.setdefault("hold", 2.0 if ev["action"] in ("kamar_dard", "fail") else 1.6)
            elif "action" not in ev and "move" not in ev and "expression" not in ev:
                ev.setdefault("hold", 0.6)
            tl.append(ev)
            first = False
        last = {"hold": 1.0}
        if si == len(scenes) - 1 and meta.get("CTA"):
            last = {"hold": 2.0, "sfx": "pop", "volume": 0.5,
                    "overlay": {"text": meta["CTA"], "style": "card",
                                "pos": [540, 640], "color": [236, 90, 70]}}
        tl.append(last)
        item = {"background": sc["background"], "cast": order + (["NARRATOR"] if narrated else []),
                "characters": chars, "timeline": tl}
        if narrated:
            item["characters"]["NARRATOR"] = {}
            cast.setdefault("NARRATOR", dict(NARRATOR_SPEC))

        if sc["title"]:
            item["title"] = sc["title"]
        if sc.get("framing"):
            item["framing"] = sc["framing"]
        if sc.get("cut_in"):
            item["cut_in"] = True
        out_scenes.append(item)

    hook = meta.get("HOOK") or ""
    if not hook:
        warnings.append("no HOOK: line - the first second has no hook text")
    music = {"type": "beat", "bpm": 100, "volume": 0.2}
    mv = meta.get("MUSIC", "").strip()
    if mv.lower() == "none":
        music = None
    elif mv.lower().startswith("beat"):
        bpm = re.findall(r"\d+", mv)
        music["bpm"] = int(bpm[0]) if bpm else 100
    elif mv:
        music = {"path": mv, "volume": 0.3}
    scene = {
        "hook": hook,
        "meta": {"fps": 30, "line_gap": 0.3},
        "transition": (meta.get("TRANSITION") or "whip").lower(),
        "characters": cast,
        "overlays": [{"text": hook, "style": "hook", "pos": [540, 420], "from": 0.0, "to": 2.0}] if hook else [],
        "scenes": out_scenes,
        "post": {"caption": meta.get("CAPTION") or hook,
                 "hashtags": meta.get("HASHTAGS", "#desicomedy #funny #indianreels").split()},
    }
    if music:
        scene["music"] = music
    if len([n for n in cast if n != "NARRATOR"]) > 3:
        warnings.append("more than 3 characters: the screen gets crowded")
    est = sum(audio.estimate_duration(ln[3]) + 0.3 for sc in scenes for ln in sc["lines"] if ln[0] == "say")
    if est > 28:
        warnings.append("script is long (~%.0fs of talking): reels work best under 25s" % est)
    return scene, warnings


def main(argv=None):
    ap = argparse.ArgumentParser(description="Plain-text script -> scene.json (no AI)")
    ap.add_argument("script")
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args(argv)
    with open(args.script, encoding="utf-8") as f:
        scene, warnings = parse_script(f.read())
    for w in warnings:
        print("  [script] " + w)
    from .director import save
    out = args.out or os.path.splitext(args.script)[0] + ".json"
    print(save(scene, out))     # + .post.txt (Instagram caption + hashtags)


if __name__ == "__main__":
    main()

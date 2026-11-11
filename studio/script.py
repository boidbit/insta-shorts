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
- `STYLE: 2.5d` (optional, after HOOK) = the 2.5D look: kitchen, gully, chai_tapri, kirana and terrace become layered
  sets with depth (parallax, depth blur, glowing lights). Default `STYLE: 2d` = the normal look.
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
import zlib

from . import actions, audio, gemini_music, objects, rides, styles
from .characters import (ACCESSORIES, EXPRESSIONS, FACE_WORDS, HAIR_COLORS, HAIR_STYLES, LOOKS, OUTFITS, PALETTE,
                         SKIN_TONES)
from .util import asset_path
from .scene import DEPTHS, ENTRY_HOLD, SHOT_ALIASES, SHOT_ZOOM, SLOTS, chat_length

HEADERS = ("HOOK", "CAST", "SCENE", "CTA", "CAPTION", "HASHTAGS", "MUSIC", "TRANSITION", "STYLE", "CAMERA")
from .locations import LOCATIONS as _LOC   # noqa: E402

BACKGROUNDS = tuple(dict.fromkeys(("kitchen", "room", "street", "school", "market", "office", "bus_stop", "night_road",
                                   "plain", "living_room", "classroom") + tuple(_LOC)))
TIMES = ("day", "night", "evening", "sunset", "dawn", "rain")      # SCENE: <place> night
WEATHER = ("snow", "fog", "fireflies", "leaves")                    # SCENE: <place> fog
from .characters import PROPS as _HELD   # noqa: E402

PROPS = tuple(_HELD)
SFX = audio.SFX_NAMES        # pop, boing, whoosh, ding, thud, clap, beep, laugh_track, slap, knock, doorbell, horn...
MOOD_BPM = {"desi": 100, "soft": 96, "pop": 110, "comedy": 108, "suspense": 84, "sad": 72, "festive": 118, "lofi": 80}
from .effects import ALL as _FX   # noqa: E402

FX_ALIASES = {"stars": "dizzy", "sweating": "sweat", "pasina": "sweat", "gussa": "anger", "idea": "bulb",
              "lightbulb": "bulb", "heart": "hearts", "dhuan": "smoke", "aag": "fire", "baarish": "rain",
              "barish": "rain", "ankhen": "glow_eyes", "eyes": "glow_eyes", "flash_bang": "flash"}
FX = tuple(sorted(set(_FX) - {"projectile", "thought"})) + tuple(FX_ALIASES)
from . import sets as _sets   # noqa: E402

# set pieces for OBJ: lines (table / dustbin stay the OBJ objects they already were)
SET_TYPES = tuple(sorted(k for k in _sets.SPEC if k not in ("table", "dustbin")))
SET_STATES = ("open", "closed", "on", "off", "ringing", "idle", "rustle", "night", "day")
SET_X = {"far_left": 120, "left": 230, "center": 540, "right": 850, "far_right": 960}
SEAT_ACTIONS = ("sit", "lie_down", "lie", "sleep_lie", "rofl")


def parse_set(raw, placed):
    """`door right` / `sofa left big` / `tv right on` / `signboard center CHAI POINT` / `door open`.
    Returns (kind, spec, problems): kind "place" (new piece) or "state" (a piece already in this place)."""
    words = raw.split()
    typ = words[0].lower()
    rest = words[1:]
    state = next((w.lower() for w in rest if w.lower() in SET_STATES), None)
    pos = next((w.lower() for w in rest if w.lower() in SET_X), None)
    flags = {w.lower() for w in rest}
    if typ in placed and pos is None and state is not None:
        return "state", {"set": typ if placed.get(typ) else typ, "state": state}, []
    spec = {"type": typ, "x": SET_X.get(pos, 540 if typ in ("fan", "tubelight", "clock") else 760)}
    if state:
        spec["state"] = state
    if "big" in flags:
        spec["scale"] = 1.25
    if "small" in flags:
        spec["scale"] = 0.75
    spec["y"] = 1560 if "back" in flags else 1820 if "front" in flags else 1700
    if "flip" in flags:
        spec["flip"] = True
    known = set(SET_STATES) | set(SET_X) | {"big", "small", "back", "front", "flip"}
    text = [w for w in rest if w.lower() not in known]
    sid = typ if typ not in placed else "%s%d" % (typ, sum(1 for k in placed if k.startswith(typ)) + 1)
    spec["id"] = sid                                # (also when a word is unknown: the piece is still placed)
    if typ in ("signboard", "blackboard") and text:
        spec["text"] = " ".join(text)
    elif text:
        return "place", spec, ["OBJ %s: %s samajh nahi aaye" % (typ, ", ".join(repr(w) for w in text))]
    return "place", spec, []
NARRATION_NAMES = ("narrator", "vo", "narration", "voiceover", "voice_over")   # a voice with no body
NARRATOR_SPEC = {"hidden": True, "voice": {"name": "hi-IN-MadhurNeural", "pitch": "-12Hz", "rate": "-4%",
                                           "gemini": "Charon"}}
GETOFF_WORDS = ("getoff", "utar", "dismount")
FRAMINGS = ("wide", "medium", "inside", "ots")
ANGLE_WORDS = ("reverse",)
OTS_WORDS = ("over", "shoulder", "over_shoulder")
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
    "pujari": "pandit", "panditji": "pandit", "policewala": "police", "inspector": "police", "havaldar": "police",
    "daroga": "police", "dactor": "doctor", "chaiwale": "chaiwala", "groom": "dulha", "bride": "dulhan",
    "netaji": "neta", "mantri": "neta", "politician": "neta", "sarpanch": "neta", "mla": "neta",
    "kaidi": "chor", "prisoner": "chor", "thief": "chor", "sasu": "saas", "saasu": "saas", "bhabhi": "bahu",
    "patni": "bahu", "biwi": "bahu", "headmaster": "principal", "barber": "nai", "hajjam": "nai",
}
FEMALE_LOOKS = {"girl", "college_girl", "aunty", "dadi", "kid_girl", "office_girl", "madam", "dulhan", "nurse",
                "saas", "bahu"}
PITCHES = ["+0Hz", "+14Hz", "-8Hz", "+24Hz", "-14Hz"]
BUILDS = ("slim", "normal", "chubby")
GENDER_WORDS = ("female", "woman", "ladki", "aurat", "male", "man", "ladka", "aadmi")
MOVE_WORDS = ("enter", "exit", "walk", "left", "right", "center", "up", "down", "up_left", "up_right", "fast",
              "pump", "swing", "cheer", "disco", "shake", "drop", "noprop", "interrupt", "beech_me",
              "freeze", "slowmo", "slow_motion", "zoom", "reveal")


def vocab():
    """Every word the script format understands (the web page keeps a copy for its checker)."""
    return {
        "places": sorted(BACKGROUNDS),
        "looks": sorted(LOOKS), "roles": sorted(ROLE_LOOKS),
        "extras": sorted(set(ACCESSORIES) | set(HAIR_STYLES) | set(OUTFITS) | set(SKIN_TONES) | set(BUILDS)
                         | set(GENDER_WORDS) | set(PALETTE) | set(HAIR_COLORS) | set(FACE_WORDS)),
        "expressions": sorted(EXPRESSIONS), "actions": sorted(actions.ACTIONS),
        "props": sorted(PROPS), "sfx": sorted(SFX), "moves": sorted(MOVE_WORDS), "fx": sorted(FX),
        "times": sorted(TIMES + WEATHER),
        "sets": sorted(SET_TYPES), "set_words": sorted(set(SET_STATES) | set(SET_X) | {"big", "small", "back", "front", "flip"}),
        "seat_actions": sorted(SEAT_ACTIONS), "animals": sorted(ANIMAL_WORDS),
        "moods": sorted(audio.MOODS), "ambience": sorted(audio.AMBIENCE),
        "shots": sorted(SHOTS), "depth": sorted(DEPTH_WORDS),
        "objects": sorted(set(objects.OBJECTS) | set(objects.ALIASES)),
        "object_words": ["center", "enter", "exit", "front", "go", "left", "right", "to"],
        "rides": sorted(rides.RIDES), "ride_words": sorted(("ride", "back", "driver") + GETOFF_WORDS),
        "framings": sorted(FRAMINGS), "angle_words": sorted(ANGLE_WORDS + OTS_WORDS),
        # the page's Builder pickers
        "role_looks": sorted([r, l] for r, l in ROLE_LOOKS.items()), "hair": list(HAIR_STYLES),
        "skin": list(SKIN_TONES), "outfits": list(OUTFITS), "colors": sorted(PALETTE), "accessories": list(ACCESSORIES),
        "builds": list(BUILDS),
    }


def _words(s):
    """'shock | point, [tshirt]' -> ['shock', 'point', 'tshirt']"""
    words = (w.strip("[](){}'\"") for w in re.split(r"[\s,|]+", s.strip().lower()))
    return [w for w in words if w]


ANIMAL_WORDS = {"dog": "dog", "kutta": "dog", "doggy": "dog", "cat": "cat", "billi": "cat", "cow": "cow",
                "gaay": "cow", "gai": "cow", "crow": "crow", "kauwa": "crow", "kaua": "crow", "parrot": "parrot",
                "tota": "parrot", "totaa": "parrot", "monkey": "monkey", "bandar": "monkey"}


def cast_spec(words, index, unknown=None):
    """'aunty chubby glasses maroon female' -> character spec (with a voice).
    Words that mean nothing here are added to `unknown`."""
    spec, acc = {}, []
    female = None
    for w in words:
        if w in ANIMAL_WORDS and "kind" not in spec:       # A = kutta brown: a dog (talks too)
            spec["kind"] = ANIMAL_WORDS[w]
        elif spec.get("kind") not in (None, "monkey") and w in PALETTE and "color" not in spec:
            spec["color"] = w                          # kutta brown: the fur, not a skin tone
        elif w in LOOKS and "look" not in spec:
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
        elif w in FACE_WORDS:                          # round_face, big_eyes, button_nose, thick_brows...
            spec[FACE_WORDS[w][0]] = FACE_WORDS[w][1]
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
    if spec.get("kind") in ANIMAL_WORDS.values() and spec["kind"] != "monkey":
        if isinstance(spec.get("color"), str) and spec["color"] in PALETTE:
            spec["color"] = list(PALETTE[spec["color"]])  # the animal rig takes an RGB colour
        voice.update(pitch="+20Hz" if spec["kind"] in ("cat", "parrot", "crow") else "-6Hz")
    spec["voice"] = voice
    return spec


MALE_HAIR = ("short", "side_part", "curly", "spiky", "balding")
FEMALE_HAIR = ("ponytail", "bun", "long", "braid")
SKIN_ORDER = ("wheatish", "brown", "fair", "dark")
SHIRT_ORDER = ("blue", "mustard", "red", "teal", "purple", "orange", "green", "maroon")


def vary_cast(cast):
    """Characters that share a look (two college_boys...) would be twins. Give each a different hair style and
    skin tone, unless the script chose them. Only what the script left open is changed."""
    seen = {}                                   # look -> [(hair, skin), ...] already on screen
    colors = []                                 # shirt colours already on screen
    for name, spec in cast.items():
        if spec.get("hidden") or spec.get("kind"):    # a voice / an animal: nothing to vary
            continue
        look = spec.get("look", "boy")
        base = LOOKS.get(look, {})
        hair, skin = spec.get("hair", base.get("hair")), spec.get("skin", base.get("skin"))
        taken = seen.setdefault(look, [])
        if (hair, skin) in taken:
            female = look in FEMALE_LOOKS or spec.get("voice", {}).get("name", "").startswith("hi-IN-Swara")
            if "hair" not in spec and hair not in ("bald",):
                options = [h for h in (FEMALE_HAIR if female else MALE_HAIR) if all(h != t[0] for t in taken)]
                if options:
                    hair = spec["hair"] = options[0]
            if (hair, skin) in taken or "skin" not in spec:
                options = [k for k in SKIN_ORDER if k != skin and (hair, k) not in taken]
                if "skin" not in spec and options:
                    skin = spec["skin"] = options[(len(taken) - 1) % len(options)]
        taken.append((hair, skin))
        color = spec.get("color", base.get("color", "blue"))
        if color in colors and "color" not in spec:          # same shirt as somebody else: pick a free colour
            free = [c for c in SHIRT_ORDER if c not in colors]
            if free:
                color = spec["color"] = free[0]
        colors.append(color)
    return cast


def ots_back(sc, before, order, cast):
    """Whose back is in front of the camera in an over-the-shoulder shot: the name after `CUT ots`, else the one
    who is spoken to (the second character of the shot), else whoever spoke last before this shot."""
    if sc.get("back"):
        return sc["back"] if sc["back"] in cast or sc["back"] in order else None
    if len(order) >= 2:
        return order[1]
    for prev in reversed(before):
        for ln in reversed(prev["lines"]):
            if ln[0] in ("say", "do") and ln[1] not in order and ln[1].upper() not in ("ALL", "NARRATOR"):
                return ln[1]
    others = [n for n in cast if n not in order and n != "NARRATOR" and not cast[n].get("hidden")]
    return others[0] if others else None


def _stage(tokens, ev, scene_cast, who):
    """Apply bracket / arrow words to an event dict.
    Returns (move request or None, unknown words, words that were overridden)."""
    move = None
    unknown, acts, exprs = [], [], []
    # words that are both an action and a face (think, shock, laugh, scared...) are the face when the line
    # already has a clear action ("think, point" = thinking face + pointing)
    action_only = any(w2 == "point" or (w2 in actions.ACTIONS and w2 not in EXPRESSIONS and w2 not in SFX)
                      for w2 in tokens)
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
        elif w in SEAT_ACTIONS and nxt in SET_TYPES:                 # A -> sit sofa / sleep_lie bed
            ev["action"] = w
            ev["on"] = nxt
            acts.append(w)
            i += 1
        elif w == "throw" and nxt and any(c.lower() == nxt and c != who for c in scene_cast):   # A -> throw B
            ev["action"] = "throw"
            ev["at"] = next(c for c in scene_cast if c.lower() == nxt)
            acts.append(w)
            i += 1
        elif w in GETOFF_WORDS:
            spec = {}
            if nxt in ("left", "right"):
                spec["side"] = nxt
                i += 1
            ev["getoff"] = spec
        elif w in ("enter", "exit") and nxt in ("left", "right"):
            move = (w, nxt)
            i += 1
            how = tokens[i + 1] if i + 1 < len(tokens) else None
            if how == "fast" or (w == "enter" and how == "peek"):      # enter left fast / enter right peek / exit left fast
                move = (w, nxt, how)
                i += 1
        elif w == "enter" and nxt in ("back", "pop"):                  # enter back [left|right] / enter pop
            side = tokens[i + 2] if i + 2 < len(tokens) and tokens[i + 2] in ("left", "right") else None
            move = ("enter", side, nxt)
            i += 2 if side else 1
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
        elif w in actions.ACTIONS and not ((acts or action_only) and (w in EXPRESSIONS or w in SFX)):
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
        elif w in FX and not (w in actions.ACTIONS or w in EXPRESSIONS):
            fxn = FX_ALIASES.get(w, w)
            ev.setdefault("fx", []).append(fxn if fxn != "glow_eyes" else {"type": "glow_eyes", "dur": 3.0})
        elif w == "shake":
            ev["camera"] = dict(ev.get("camera", {}), shake=0.6)
        elif w == "freeze":                         # the picture stops (grey) with a record scratch
            ev["freeze"] = {"dur": 1.2}
            ev.setdefault("sfx", "record_scratch")
            ev.setdefault("volume", 0.6)
        elif w in ("slowmo", "slow_motion"):        # the next second of the story at 0.4x (2.5 s on screen)
            ev["slowmo"] = {"rate": 0.4, "dur": 1.0}
        elif w == "zoom":                           # snap zoom onto this face for the line
            ev["camera"] = dict(ev.get("camera", {}), punch=who if who in scene_cast else None)   # stays close
        elif w == "reveal":                         # start close on the face, pull back to the whole place
            ev["camera"] = dict(ev.get("camera", {}), reveal=who if who in scene_cast else True)
        elif w in ("interrupt", "beech_me"):        # B (interrupt, angry): ... cuts A off mid-sentence
            ev["interrupt"] = True
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
    if acts and not exprs and ev.get("action") in EXPRESSIONS:
        ev["expression"] = ev["action"]        # "A (shock): ..." also gets the shocked face
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
    meta, lyrics, sung = {}, [], []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        if gemini_music.is_section(line):               # [Verse] / [Chorus]: for the singer, not for the screen
            sung.append(line)
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
        sung.append(line.partition("|")[2].strip() or lyrics[-1])   # ...and sing the Devanagari part (like the voice)
    meta["_sung"] = sung
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
    elif mv.lower().startswith("gemini"):                # MUSIC: gemini <style>: your lyrics, sung as a full song
        music = gemini_music.music_spec(mv, meta.get("_sung") or lyrics)
        music["lyrics_lines"] = list(lyrics)
        music["lyrics_meta"] = {k: v for k, v in meta.items() if not k.startswith("_") and k not in ("SECONDS", "MUSIC")}
        if meta.get("SECONDS"):
            warnings.append("SECONDS: gaana ban jaane par video gaane jitni lambi hoti hai, SECONDS use nahi hota")
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


UI_WORDS = ("NOTIFY", "NOTIFICATION", "LOADING", "COUNTER", "TIMECARD", "CHAPTER", "ENDCARD")


def ui_line(key, val):
    """`NOTIFY: Bank | Rs 5 credited | Balance: Rs 7`, `LOADING: Dimaag loading...`, `COUNTER: Rotiyan | 0 | 14`,
    `TIMECARD: 3 ghante baad...`, `CHAPTER: Chapter 2 | Exam ka din`, `ENDCARD: Follow karo | @page`
    -> (overlay spec, seconds the story waits, warning)."""
    parts = [p.strip() for p in val.split("|")]
    if not parts[0]:
        return None, 0, "%s: ke baad text likho" % key
    if key in ("NOTIFY", "NOTIFICATION"):
        app, title, text = (["", parts[0], ""] if len(parts) == 1 else
                            [parts[0], parts[1], ""] if len(parts) == 2 else parts[:3])
        return {"type": "notification", "app": app or "Message", "title": title, "text": text}, 1.4, None
    if key == "LOADING":
        return {"type": "loading", "label": parts[0]}, 2.6, None
    if key == "COUNTER":
        nums = [p for p in parts[1:] if re.match(r"^-?\d+$", p)]
        if not nums:
            m = re.match(r"^(.*?)\s+(-?\d+)\s*(?:->|to|se)\s*(-?\d+)$", parts[0])
            if m:
                parts, nums = [m.group(1)], [m.group(2), m.group(3)]
        if not nums:
            return None, 0, "COUNTER: 'COUNTER: Rotiyan | 0 | 14' likho (label | shuru | aakhri number)"
        a, b = (0, int(nums[0])) if len(nums) == 1 else (int(nums[0]), int(nums[1]))
        return {"type": "counter", "label": parts[0], "start": a, "end": b}, 2.6, None
    if key == "TIMECARD":
        return {"type": "timecard", "text": parts[0]}, 1.6, None
    if key == "CHAPTER":
        spec = {"type": "chapter", "text": parts[0]}
        if len(parts) > 1:
            spec["subtitle"] = parts[1]
        return spec, 2.0, None
    spec = {"type": "endcard", "text": parts[0]}          # ENDCARD
    if len(parts) > 1:
        spec["sub"] = parts[1]
    return spec, 2.4, None


def resolve_background(raw):
    """`street` / `gali` (= assets/backgrounds/gali.png) / `assets/backgrounds/x.jpg` -> (background dict, warning)."""
    name = raw.strip()
    low = name.lower().replace(" ", "_")
    if low in BACKGROUNDS:
        return {"type": low}, None
    words = name.lower().split()
    if len(words) > 1 and all(w in TIMES or w in WEATHER for w in words[1:]):   # "gully night fog"
        bg, warn = resolve_background(words[0])
        for w in words[1:]:
            if w in TIMES:
                bg["time"] = w
            else:
                bg.setdefault("weather", []).append(w)
        return bg, warn
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


HEADER_WORDS = ("HOOK", "CAST", "SCENE", "CTA", "CAPTION", "HASHTAGS", "MUSIC", "TRANSITION", "STYLE", "CAMERA", "OBJ",
                "NARRATOR",
                "LIGHTS", "AMBIENCE", "NOTIFY", "LOADING", "COUNTER", "TIMECARD", "CHAPTER", "ENDCARD")


def unflatten(text):
    """A script whose line breaks were lost (GitHub's one-line "Run workflow" box, some phone apps): put every
    HOOK: / CAST: / SCENE: / CUT / CTA: ... and every "A (shock): ..." / "B -> ..." line back on its own line.
    Returns (text, True if it had to be split)."""
    if text.count("\n") >= 3 or not re.search(r"\b(HOOK|CAST|SCENE)\s*:", text):
        return text, False
    t = re.sub(r"\s+(?=(?:%s)\s*:)" % "|".join(HEADER_WORDS), "\n", text.strip())
    t = re.sub(r"\s+(?=(?:CUT|SHOT)\b(?:\s+(?:%s|reverse|over|[A-Z]\w*))*\s+[A-Z]\w*\s*[(:\-])"
               % "|".join(FRAMINGS), "\n", t)
    names = []
    m = re.search(r"^CAST\s*:\s*(.*)$", t, re.M)
    if m:
        names = re.findall(r"([A-Za-z_]\w*)\s*=", m.group(1))
    for n in sorted(set(names) | {"ALL"}, key=len, reverse=True):
        t = re.sub(r"(?<!^)[ \t]+(?=%s\s*(?:\([^)]*\))?\s*(?::|->))" % re.escape(n), "\n", t, flags=re.M)
    t = re.sub(r"[ \t]+((?:CUT|SHOT)\b[^\n]*?)[ \t]*$", r"\n\1", t, flags=re.M)     # a CUT at the end of a line
    return (t, True) if t.count("\n") > text.strip().count("\n") else (text, False)


def parse_script(text):
    """Return (scene dict, warnings)."""
    text, flat = unflatten(text)
    if flat:
        scene, warns = parse_script(text)
        return scene, ["script ek hi line me aaya tha (line break kho gaye); lines apne aap alag ki"] + warns
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
        m = re.match(r"^(?:CUT|SHOT)\b\s*:?\s*([\w\s,]*)$", line, re.I)
        if m:                                       # a new shot in the same place: a hard cut, its own set of characters
            frame, reverse, back = "", False, None
            for w in re.split(r"[\s,]+", m.group(1).strip()):
                lw = w.lower()
                if not w:
                    continue
                if lw in FRAMINGS and not frame:
                    frame = lw
                elif lw in OTS_WORDS and not frame:
                    frame = "ots"
                elif lw in ANGLE_WORDS:
                    reverse = True
                elif w in cast or (frame == "ots" and re.match(r"^[A-Z]\w*$", w) and back is None):
                    back = w
                else:
                    warnings.append("CUT %r: framing wide / medium / inside / ots (+ reverse) likho" % w)
            shot_no = cur.get("shot", 0) + 1
            prev_sets = {k: dict(v) for k, v in cur.get("sets", {}).items()}
            prev_lights = cur.get("lights", "on")
            prev_amb = cur.get("ambience")
            cur = new_scene(dict(cur["background"]), None)
            if prev_amb is not None:
                cur["ambience"] = prev_amb              # same place: the same sound around
            cur["sets"] = prev_sets                 # same place: the door / sofa / fan are still there
            cur["lights"] = cur["lights_start"] = prev_lights     # ... and the lights stay as they were
            cur["cut_in"], cur["framing"], cur["shot"] = True, frame or None, shot_no
            if reverse:
                cur["reverse"] = True
            if frame == "ots":
                cur["back"] = back
            continue
        m = re.match(r"^(NOTIFY|NOTIFICATION|LOADING|COUNTER|TIMECARD|CHAPTER|ENDCARD)\s*:\s*(.*)$", line, re.I)
        if m:
            if cur is None:
                cur = new_scene()
            spec, hold, warn = ui_line(m.group(1).upper(), m.group(2).strip())
            if warn:
                warnings.append(warn)
            if spec:
                cur["lines"].append(("ui", spec, hold))
            continue
        m = re.match(r"^AMBIENCE\s*:\s*(.*)$", line, re.I)
        if m:
            if cur is None:
                cur = new_scene()
            kinds = [w for w in _words(m.group(1)) if w != "none"]
            bad = [w for w in kinds if w not in audio.AMBIENCE]
            if bad:
                warnings.append("AMBIENCE: %s nahi hai (%s)" % (", ".join(bad), ", ".join(audio.AMBIENCE)))
            cur["ambience"] = [w for w in kinds if w in audio.AMBIENCE]
            continue
        m = re.match(r"^LIGHTS?\s*:\s*(on|off|dim)\s*$", line, re.I)
        if m:
            if cur is None:
                cur = new_scene()
            cur["lines"].append(("lights", m.group(1).lower()))
            cur["lights"] = m.group(1).lower()
            continue
        m = re.match(r"^OBJ\s*:\s*(\S+)(.*)$", line, re.I)
        if m and m.group(1).lower() in SET_TYPES:
            if cur is None:
                cur = new_scene()
            placed = cur.setdefault("sets", {})
            kind, spec, probs = parse_set(m.group(1) + m.group(2), placed)
            warnings += probs
            if kind == "place":
                placed[spec["id"]] = spec
            else:
                spec["prev"] = placed[spec["set"]].get("state")
                placed[spec["set"]]["state"] = spec["state"]
                cur["lines"].append(("set", spec))
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
        back = None
        if sc.get("framing") == "ots":
            back = ots_back(sc, scenes[:si], order, cast)
            if back is None:
                warnings.append("CUT ots: peeche se kaun dikhe? 'CUT ots B' likho (shot me ek aur character chahiye)")
                sc["framing"] = None
        chars = {}
        fronts = [n for n in order if n != back]
        for name in fronts:
            x, slot = _slot_x(fronts, name)
            facing = "front" if len(fronts) != 2 else ("right" if slot == "left" else "left")
            chars[name] = {"slot": slot, "facing": facing}
        if back:                                    # over the shoulder: back's back big in the near corner
            side = "left" if sc.get("shot", 0) % 2 == 0 else "right"
            chars[back] = {"slot": side, "view": "back"}
            for name in fronts:
                chars[name]["facing"] = side        # the speaker talks to the one in front of the camera
            if back not in order:
                order.append(back)
        tl = [{"t": 0.0, "who": "all", "action": "idle", "expression": "smile"}]
        if si == 0:
            tl.append({"t": 0.0, "sfx": "whoosh", "volume": 0.7, "camera": {"shake": 0.5}})
        # the story starts a moment in; a `wait`, a screen card or a set change before the first line now really
        # comes first (they used to be skipped because the first line had a fixed start time)
        tl.append({"wait": 0.3 if si == 0 else 0.2})
        first = True
        for ln in sc["lines"]:
            if ln[0] == "wait":
                tl.append({"wait": ln[1]})
                continue
            if ln[0] == "set":
                tl.append({"set": ln[1]["set"], "state": ln[1]["state"]})
                continue
            if ln[0] == "lights":
                tl.append({"lights": ln[1]})
                continue
            if ln[0] == "ui":
                tl.append({"overlay": dict(ln[1]), "hold": ln[2]})
                continue
            if ln[0] == "obj":
                oev = {"obj": ln[1]}
                first = False
                tl.append(oev)
                continue
            who = "all" if ln[1].upper() == "ALL" else ln[1]
            ev = {"who": who}
            move, unknown, lost = _stage(ln[2], ev, order, who)
            if unknown:
                warnings.append("line %r: %s samajh nahi aaye (acting words ki list dekho)"
                                % (ln[-1][:50], ", ".join(repr(u) for u in unknown)))
            if lost:
                warnings.append("line %r: ek line me ek hi action aur ek hi expression chalta hai; %s ignore hue"
                                % (ln[-1][:50], ", ".join(repr(u) for u in lost)))
            if move and who != "all":
                x, _slot = _slot_x(order, who)
                kind, side, *how = move
                if kind == "enter" and how:             # back / pop / fast / peek: the studio stages it
                    ev["entry"] = {"style": how[0], "x": x}
                    if side:
                        ev["entry"]["side"] = side
                    ev.setdefault("hold", ENTRY_HOLD[how[0]])
                elif kind == "exit" and how:            # exit left fast
                    ev["leave"] = {"style": "fast", "side": side}
                    ev.setdefault("hold", 0.7)
                elif kind == "enter":
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
                    warnings.append("no Devanagari for %r: made by the AI when the video is made (GEMINI_API_KEY), "
                                    "else the voice reads Roman letters" % ln[3][:30])
                others = [o for o in order if o != who]
                if who == "NARRATOR":
                    ev["bubble"], ev["subtitle"] = False, True
                    for key in ("action", "expression", "prop", "move", "camera", "sfx", "volume", "facing", "look"):
                        ev.pop(key, None)                       # a voice has no body to act with
                elif len(order) == 2 and others:
                    ev.setdefault("look", others[0])
            elif ev.get("slowmo"):
                ev.setdefault("hold", 1.0)              # the slow-motion part plays out before the next line
            elif ev.get("freeze"):
                ev.setdefault("hold", 0.0)              # the next line (a narrator...) is said over the frozen picture
            elif ev.get("action") == "throw":
                ev.setdefault("hold", 1.15)             # wind-up, flight and the hit before the next line
            elif ev.get("on"):
                ev.setdefault("hold", 0.8)              # sits down / lies down
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
                                "pos": [540, 1460 if any(ln[0] == "ui" and ln[1]["type"] == "endcard"
                                                         for ln in sc["lines"]) else 640],   # below an end card
                                "color": [236, 90, 70], "cta": True}}
        tl.append(last)
        sc_sets = []
        if sc.get("sets"):
            start = {}                              # the state each piece had when this shot started
            for ln in sc["lines"]:
                if ln[0] == "set" and ln[1]["set"] not in start:
                    start[ln[1]["set"]] = ln[1].get("prev")
            for sid, spec in sc["sets"].items():
                spec = dict(spec)
                if sid in start:
                    if start[sid] is None:
                        spec.pop("state", None)
                    else:
                        spec["state"] = start[sid]
                sc_sets.append(spec)
        item = {"background": sc["background"], "cast": order + (["NARRATOR"] if narrated else []),
                "characters": chars, "timeline": tl}
        if narrated:
            item["characters"]["NARRATOR"] = {}
            cast.setdefault("NARRATOR", dict(NARRATOR_SPEC))

        if sc_sets:
            item["sets"] = sc_sets
        if sc.get("lights_start", "on") != "on":
            item["lights"] = sc["lights_start"]
        if sc.get("ambience") is not None:
            item["ambience"] = sc["ambience"]
        if sc["title"]:
            item["title"] = sc["title"]
        if sc.get("framing"):
            item["framing"] = sc["framing"]
        if sc.get("cut_in"):
            item["cut_in"] = True
        if sc.get("shot"):
            item["angle"] = sc["shot"]
        if sc.get("reverse"):
            item["reverse"] = True
        out_scenes.append(item)

    vary_cast(cast)
    hook = meta.get("HOOK") or ""
    if not hook:
        warnings.append("no HOOK: line - the first second has no hook text")
    music = {"type": "beat", "bpm": 100, "volume": 0.2}
    mv = meta.get("MUSIC", "").strip()
    mood = mv.split()[0].lower() if mv else ""
    if mv.lower() == "none":
        music = None
    elif mood == "gemini":                                # MUSIC: gemini <style>: instrumental music from Gemini
        music = gemini_music.music_spec(mv)
    elif mood == "beat" or mood in audio.MOODS:           # MUSIC: beat 110 / MUSIC: sad / MUSIC: suspense 90
        bpm = re.findall(r"\d+", mv)
        music["bpm"] = int(bpm[0]) if bpm else MOOD_BPM.get(mood, 100)
        if mood in audio.MOODS:
            music["style"] = mood
    elif mv:
        music = {"path": mv, "volume": 0.3}
    if music and music.get("type") == "beat":            # every video gets its own tune
        music["seed"] = zlib.crc32((hook or "reel").encode("utf-8")) % 997
    if music and music.get("type") == "gemini":
        music["fallback"]["seed"] = zlib.crc32((hook or "reel").encode("utf-8")) % 997
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
    if meta.get("STYLE"):
        try:
            scene["style"] = styles.normalize(meta["STYLE"])
        except ValueError:
            warnings.append("STYLE %r: 2d ya 2.5d likho" % meta["STYLE"])
    if meta.get("CAMERA"):                              # CAMERA: classic = the old camera; cine (default) = the new one
        cam = meta["CAMERA"].strip().lower()
        if cam in ("classic", "old", "purana"):
            scene["meta"]["camera"] = "classic"
        elif cam not in ("cine", "new", "naya"):
            warnings.append("CAMERA %r: cine (naya, default) ya classic (purana) likho" % meta["CAMERA"])
    if scene.get("style") == "2.5d":
        flat = sorted({str(sc["background"].get("type")) for sc in scenes
                       if not styles.has_depth(sc["background"].get("type"))})
        if flat:
            warnings.append("STYLE 2.5d: %s 2.5D me flat dikhegi (baaki har jagah 2.5D me gehraai ke saath banti hai)"
                            % ", ".join(flat))
    if len([n for n in cast if n != "NARRATOR"]) > 3:
        warnings.append("more than 3 characters: the screen gets crowded")
    return scene, warnings


def main(argv=None):
    ap = argparse.ArgumentParser(description="Plain-text script -> scene.json (no AI)")
    ap.add_argument("script", nargs="?")
    ap.add_argument("--sync-page", action="store_true",
                    help="copy the current word list into index.html (the studio page's script checker)")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--no-hindi", action="store_true",
                    help="do not ask the AI for Devanagari of Roman-only lines (the voice reads them as they are)")
    args = ap.parse_args(argv)
    if args.sync_page:
        import json
        page = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "index.html")
        with open(page, encoding="utf-8") as f:
            html = f.read()
        new = json.dumps(vocab(), ensure_ascii=False, separators=(",", ":"))
        html = re.sub(r'(<script type="application/json" id="vocab">).*?(</script>)',
                      lambda m: m.group(1) + new + m.group(2), html, count=1, flags=re.S)
        with open(page, "w", encoding="utf-8") as f:
            f.write(html)
        print("index.html word list updated")
        if not args.script:
            return
    if not args.script:
        ap.error("a script file is needed (or --sync-page)")
    with open(args.script, encoding="utf-8") as f:
        scene, warnings = parse_script(f.read())
    if not args.no_hindi:
        from .hindi import fill_hindi
        if fill_hindi(scene):
            warnings = [w for w in warnings if not w.startswith("no Devanagari")]
    for w in warnings:
        print("  [script] " + w)
    from .director import save
    out = args.out or os.path.splitext(args.script)[0] + ".json"
    print(save(scene, out))     # + .post.txt (Instagram caption + hashtags)


if __name__ == "__main__":
    main()

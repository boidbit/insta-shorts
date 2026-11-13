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

from . import actions, audio, crowd, decor, drive, gemini_music, look, mystery, objects, rides, styles, theme, vehicles
from .characters import (ACCESSORIES, EXPRESSIONS, FACE_PARTS, FACE_WORDS, HAIR_COLORS, HAIR_STYLES, HAIR_WORDS,
                         LOOKS, MARKS, OUTFITS, PALETTE, face_word,
                         SKIN_TONES)
from .util import asset_path
from .scene import (CTA_STYLES, DEPTHS, ENTRY_HOLD, SHOT_ALIASES, SHOT_ZOOM, SLOTS, apply_cta, apply_loop, auto_slots,
                    chat_length, slots_for,
                    mascot_kind)

HEADERS = ("HOOK", "CAST", "SOUND", "SCENE", "CTA", "CAPTION", "HASHTAGS", "MUSIC", "TRANSITION", "STYLE", "CAMERA", "LOOP",
           "MASCOT", "COLOR", "CTA_STYLE", "HANDLE", "COVER", "CROWD", "LOOK", "MYSTERY", "SERIES")
OPENINGS = ("plain", "reveal", "close")     # the first shot of a video: as it comes / starts on a face and pulls back /
                                            # a close-up (each video gets one, picked from its hook)
ON_WORDS, OFF_WORDS = ("on", "yes", "haan", "true", "1"), ("off", "no", "nahi", "false", "0", "none")
from .locations import LOCATIONS as _LOC   # noqa: E402

BACKGROUNDS = tuple(dict.fromkeys(("kitchen", "room", "street", "school", "market", "office", "bus_stop", "night_road",
                                   "plain", "living_room", "classroom") + tuple(_LOC) +
                                  tuple(k for k, v in vehicles.VEHICLES.items() if not v.get("pov"))))
# inside a vehicle people sit on its seats, except these (they work there and stand)
STANDING_LOOKS = ("tt", "air_hostess", "conductor")
# actions that make a seated person get up (anything else is done sitting: talk, point, eat, phone...)
STAND_UP = ("walk", "run", "jog", "sneak", "limp", "crouch", "jump", "jump_over", "climb", "slide", "slip", "trip",
            "skid", "fall", "get_up", "spin", "cartwheel", "moonwalk", "lie_down", "sleep_lie", "sit_floor", "faint",
            "celebrate", "jumping_jacks", "squat", "pushup", "lift_weights", "race_start", "bat", "bowl", "kick",
            "stomp", "bow", "turn_around", "hide", "dodge", "push", "tug", "drag", "carry", "hug")
TIMES = ("day", "night", "evening", "sunset", "dawn", "rain")      # SCENE: <place> night
WEATHER = ("snow", "fog", "fireflies", "leaves")                    # SCENE: <place> fog
PAN_WORDS = ("pan", "follow")      # SCENE: street pan = one take: whoever just left walks on into the next place
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
SET_TYPES = tuple(sorted(k for k in _sets.SPEC if k not in ("table", "dustbin") and k not in _sets.VEHICLE_SEATS
                         and k not in _sets.DECOR))      # (seats come with the vehicles, decor with DRESS lines)
SET_STATES = ("open", "closed", "on", "off", "ringing", "idle", "rustle", "night", "day", "broken")
# the jail's barred door is a set piece over the painted one: `OBJ: jail_door broken` / `OBJ: jail_door open`
JAIL_DOOR = {"id": "jail_door", "type": "jail_door", "x": 930, "y": 1290, "fit": True}
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
    "teacher": "master_ji", "masterji": "master_ji", "master": "master_ji", "sir": "master_ji",
    "boss": "boss", "manager": "boss", "malik_sahab": "boss", "bachcha": "kid",
    "student": "school_boy", "schoolboy": "school_boy", "chhatra": "school_boy", "schoolgirl": "school_girl",
    "chhatra_girl": "school_girl", "school_wali": "school_girl",
    "army": "fauji", "soldier": "fauji", "faujii": "fauji", "jawan": "fauji",
    "nri": "nri_mama", "mama": "nri_mama", "videshi_mama": "nri_mama", "canada_wala": "nri_mama",
    "sardar": "sardar_ji", "sardarji": "sardar_ji", "paaji": "sardar_ji", "paji": "sardar_ji",
    "bearer": "waiter", "mistri": "mechanic", "garage_wala": "mechanic",
    "sweeper": "safai_wala", "safaiwala": "safai_wala", "safai_karmachari": "safai_wala",
    "sadhu": "baba", "babaji": "baba", "jyotishi": "baba", "swami": "baba", "tantrik": "baba",
    "pujari": "pandit", "panditji": "pandit", "policewala": "police", "inspector": "police", "havaldar": "police",
    "daroga": "police", "dactor": "doctor", "groom": "dulha", "bride": "dulhan",
    "netaji": "neta", "mantri": "neta", "politician": "neta", "sarpanch": "neta", "mla": "neta",
    "kaidi": "chor", "prisoner": "chor", "thief": "chor", "sasu": "saas", "saasu": "saas", "bhabhi": "bahu",
    "patni": "bahu", "biwi": "bahu", "headmaster": "principal", "barber": "nai", "hajjam": "nai",
    "delivery": "delivery_boy", "deliverywala": "delivery_boy", "autowala": "driver", "cabwala": "driver",
    "taxiwala": "driver", "guard": "watchman", "chowkidar": "watchman", "security": "watchman",
    "makaan_malik": "landlord", "malik": "landlord", "youtuber": "influencer", "vlogger": "influencer",
    "milkman": "doodhwala", "ticket_checker": "tt", "ghost": "bhoot", "hostess": "air_hostess",
    "busconductor": "conductor",
    "kulche_wala": "kulchewala", "matar_kulche_wala": "kulchewala", "kulchawala": "kulchewala",
    "thele_wala": "thelewala", "thelawala": "thelewala", "thela_wala": "thelewala", "rehriwala": "thelewala",
    "rehri_wala": "thelewala", "rehdiwala": "thelewala", "chaatwala": "thelewala", "momowala": "thelewala",
    "golgappewala": "thelewala", "panipuriwala": "thelewala", "phalwala": "thelewala", "fruitwala": "thelewala",
    "foodblogger": "food_blogger", "food_vlogger": "food_blogger", "foodie": "food_blogger",
    "food_bloggerni": "food_blogger_girl", "vloggerni": "food_blogger_girl", "youtuber_girl": "food_blogger_girl",
    "shopkeeper": "dukaandaar", "dukandar": "dukaandaar", "dukaandar": "dukaandaar", "lala": "dukaandaar",
    "lalaji": "dukaandaar", "kiranawala": "dukaandaar", "mobilewala": "dukaandaar", "mithaiwala": "halwai",
    "medicalwala": "chemist", "pharmacist": "chemist", "cashier": "clerk", "babu": "clerk", "munshi": "clerk",
    "judge_sahab": "judge", "jaj": "judge", "receptionist": "office_girl", "thanedaar": "police",
    "gawah": "boy", "witness": "boy", "canteenwala": "chaiwala", "chaiwale": "chaiwala",
}
FEMALE_LOOKS = {"food_blogger_girl", "air_hostess", "girl", "college_girl", "aunty", "dadi", "kid_girl", "office_girl", "madam", "dulhan", "nurse",
                "saas", "bahu", "school_girl"}
PITCHES = ["+0Hz", "+14Hz", "-8Hz", "+24Hz", "-14Hz"]
BUILDS = ("slim", "normal", "chubby")
BUILD_WORDS = {"mota": "chubby", "moti": "chubby", "fat": "chubby", "patla": "slim", "patli": "slim", "thin": "slim"}
HEIGHT_WORDS = {"tall": "tall", "lamba": "tall", "lambi": "tall", "nata": "short", "nati": "short"}
# body types handed out so that the people of one video do not all have the same height and weight
BODIES = (("normal", "normal"), ("tall", "slim"), ("short", "chubby"), ("tall", "normal"), ("normal", "slim"),
          ("short", "normal"), ("normal", "chubby"))
GENDER_WORDS = ("female", "woman", "ladki", "aurat", "male", "man", "ladka", "aadmi")
TURN_WORDS = {"side": "side", "profile": "side", "mud": "side", "mudke": "side", "saamne": "front",
              "samne": "front", "seedha": "front"}
MOVE_WORDS = ("enter", "exit", "walk", "left", "right", "center", "up", "down", "up_left", "up_right", "fast",
              "pump", "swing", "cheer", "disco", "shake", "drop", "noprop", "interrupt", "beech_me",
              "freeze", "slowmo", "slow_motion", "zoom", "reveal") + tuple(TURN_WORDS)


def vocab():
    """Every word the script format understands (the web page keeps a copy for its checker)."""
    return {
        "places": sorted(BACKGROUNDS),
        "looks": sorted(LOOKS), "roles": sorted(ROLE_LOOKS),
        "extras": sorted(set(ACCESSORIES) | set(HAIR_STYLES) | set(HAIR_WORDS) | set(OUTFITS) | set(SKIN_TONES)
                         | set(BUILDS)
                         | set(BUILD_WORDS) | set(HEIGHT_WORDS)
                         | set(GENDER_WORDS) | set(PALETTE) | set(HAIR_COLORS) | set(FACE_WORDS) | set(BEHIND_WORDS)),
        "expressions": sorted(EXPRESSIONS), "actions": sorted(actions.ACTIONS),
        "props": sorted(PROPS), "sfx": sorted(SFX), "moves": sorted(MOVE_WORDS), "fx": sorted(FX),
        "times": sorted(TIMES + WEATHER), "pan_words": list(PAN_WORDS),
        "themes": sorted(set(theme.THEMES) | set(theme.ALIASES)), "cta_styles": list(CTA_STYLES),
        "vehicles": sorted({k for k, v in vehicles.VEHICLES.items() if not v.get("pov")} | set(vehicles.ALIASES)), "views": sorted(vehicles.VIEW_WORDS),
        "dress": sorted(set(decor.PACKS) | set(decor.PACK_WORDS) | set(decor.PIECES) | {"none"}),
        "feel_words": sorted([k, v] for k, v in FEEL_WORDS.items()),
        "sets": sorted(SET_TYPES), "set_words": sorted(set(SET_STATES) | set(SET_X) | {"big", "small", "back", "front", "flip"}),
        "seat_actions": sorted(SEAT_ACTIONS), "animals": sorted(ANIMAL_WORDS),
        "moods": sorted(audio.MOODS), "ambience": sorted(audio.AMBIENCE),
        "shots": sorted(SHOTS), "depth": sorted(DEPTH_WORDS),
        "objects": sorted(set(objects.OBJECTS) | set(objects.ALIASES)),
        "object_words": ["center", "enter", "exit", "front", "go", "left", "right", "to"],
        "rides": sorted(rides.RIDES), "ride_words": sorted(("ride", "back", "driver") + GETOFF_WORDS),
        "framings": sorted(FRAMINGS), "angle_words": sorted(ANGLE_WORDS + OTS_WORDS),
        "drive_words": sorted(drive.POV_WORDS), "crowd_words": sorted(crowd.AMOUNT),
        # the page's Builder pickers
        "role_looks": sorted([r, l] for r, l in ROLE_LOOKS.items()), "hair": list(HAIR_STYLES),
        "face_parts": {k: [[v, face_word(k, v)] for v in vals] for k, vals in FACE_PARTS.items()},
        "thela_words": sorted(set(objects.THELA_WORDS) | set(objects.SHOP_WORDS)),
        "marks": list(MARKS),
        "skin": list(SKIN_TONES), "outfits": list(OUTFITS), "colors": sorted(PALETTE), "accessories": list(ACCESSORIES),
        "builds": list(BUILDS),
    }


def _words(s):
    """'shock | point, [tshirt]' -> ['shock', 'point', 'tshirt']"""
    words = (w.strip("[](){}'\"") for w in re.split(r"[\s,|]+", s.strip().lower()))
    return [w for w in words if w]


ANIMAL_WORDS = {"dog": "dog", "kutta": "dog", "doggy": "dog", "cat": "cat", "billi": "cat", "cow": "cow",
                "gaay": "cow", "gai": "cow", "crow": "crow", "kauwa": "crow", "kaua": "crow", "parrot": "parrot",
                "tota": "parrot", "totaa": "parrot", "monkey": "monkey", "bandar": "monkey", "goat": "goat",
                "bakri": "goat", "bakra": "goat", "rooster": "rooster", "murga": "rooster", "murgi": "rooster",
                "hen": "rooster", "lizard": "lizard", "chhipkali": "lizard", "chipkali": "lizard",
                "mosquito": "mosquito", "machhar": "mosquito", "macchar": "mosquito", "machchhar": "mosquito"}


BEHIND_WORDS = {"peeche": True, "piche": True, "behind": True, "counter_peeche": True, "aage": False,
                "front_side": False}


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
            if w not in LOOKS:
                spec["role"] = w                       # (a cashier / receptionist / gawah goes behind their counter)
        elif w in ROLE_LOOKS and w not in LOOKS:       # `W = girl gawah`: the look stays, the role is kept
            spec["role"] = w
        elif w in BEHIND_WORDS:                        # peeche: behind the nearest counter / thela; aage: in front
            spec["behind"] = BEHIND_WORDS[w]
        elif w in ACCESSORIES:
            acc.append(w)
        elif w in HAIR_STYLES:
            spec["hair"] = w
        elif w in HAIR_WORDS:                          # do_choti, takla...
            spec["hair"] = HAIR_WORDS[w]
        elif w in OUTFITS:
            spec["outfit"] = w
        elif w in SKIN_TONES:
            spec["skin"] = w
        elif w in ("slim", "normal", "chubby"):
            spec["build"] = w
        elif w in BUILD_WORDS:                         # mota / patla / fat / thin
            spec["build"] = BUILD_WORDS[w]
        elif w in HEIGHT_WORDS:                        # tall / lamba / nata
            spec["height"] = HEIGHT_WORDS[w]
        elif w in FACE_WORDS:                          # round_face, big_eyes, button_nose, thick_brows, mole...
            key_, val_ = FACE_WORDS[w]
            if key_ == "marks":
                spec["marks"] = sorted(set(spec.get("marks", [])) | {val_})
            else:
                spec[key_] = val_
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
    elif spec["look"] in ("school_boy", "school_girl"):
        voice.update(pitch="+20Hz", rate="+5%")
    elif spec["look"] in ("baba", "master_ji"):
        voice.update(pitch="-12Hz", rate="-6%")
    elif spec["look"] in ("boss", "fauji"):
        voice.update(pitch="-6Hz")
    elif spec["look"] in ("dada", "dadi"):
        voice.update(pitch="-10Hz", rate="-8%")
    if spec.get("kind") in ANIMAL_WORDS.values() and spec["kind"] != "monkey":
        if isinstance(spec.get("color"), str) and spec["color"] in PALETTE:
            spec["color"] = list(PALETTE[spec["color"]])  # the animal rig takes an RGB colour
        voice.update(pitch="+20Hz" if spec["kind"] in ("cat", "parrot", "crow") else "-6Hz")
        if spec["kind"] in ("mosquito", "lizard"):
            voice.update(pitch="+40Hz", rate="+12%")      # tiny: a thin, quick voice
        elif spec["kind"] in ("goat", "rooster"):
            voice.update(pitch="+12Hz")
    spec["voice"] = voice
    return spec


MALE_HAIR = ("short", "side_part", "curly", "spiky", "balding")
FEMALE_HAIR = ("ponytail", "bun", "long", "braid")
SKIN_ORDER = ("wheatish", "brown", "fair", "dark")
SHIRT_ORDER = ("blue", "mustard", "red", "teal", "purple", "orange", "green", "maroon")


def _classic_env():
    from .scene import camera_style
    return camera_style({}) == "classic"


OLD_LOOKS = ("dada", "dadi", "principal", "landlord", "neta", "saas", "pandit")
LIP_CYCLE = {True: ("full", "normal", "full", "thin"), False: ("normal", "thin", "normal", "smirk", "full")}
EAR_CYCLE = ("normal", "big", "normal", "small", "normal")


def vary_faces(cast):
    """Every person gets a few small things of their own on top of the face shape, eyes, nose and brows: their lips,
    ears, lashes (women), lines on the face (the old), now and then a mole, dimples or freckles. What the script
    or the look already says is kept. (`CAMERA: classic`: not used, the faces stay as they were.)"""
    i = 0
    for name, spec in cast.items():
        if spec.get("hidden") or spec.get("kind"):
            continue
        look = spec.get("look", "boy")
        base = LOOKS.get(look, {})
        female = look in FEMALE_LOOKS or str(spec.get("voice", {}).get("name", "")).startswith("hi-IN-Swara")
        h = zlib.crc32(("face|" + name).encode("utf-8"))

        def put(key, val):
            if key not in spec and key not in base and val not in (None, "normal"):
                spec[key] = val
        put("lips", LIP_CYCLE[female][(i + h) % len(LIP_CYCLE[female])])
        put("ears", EAR_CYCLE[(i * 2 + h) % len(EAR_CYCLE)])
        if female:
            put("lashes", True)
        marks = list(spec.get("marks", base.get("marks", [])))
        if look in OLD_LOOKS and "age_lines" not in marks:
            marks.append("age_lines")
        extra = ("mole", "dimple", None, "freckles", None, None, "dimple")[(h >> 4) % 7]
        if extra == "freckles" and look in OLD_LOOKS:
            extra = None
        if extra and extra not in marks and "marks" not in spec:
            marks.append(extra)
        if marks and "marks" not in spec:
            spec["marks"] = marks
        i += 1
    return cast


def vary_bodies(cast):
    """People are not all the same height and weight: everybody the script left open gets a body type (tall and
    slim, short and chubby...), each one different from the others in the video. A look that has its own build
    (uncle chubby, dada slim) keeps it and only gets a height; children and the old keep their size."""
    used = []
    for name, spec in cast.items():
        if spec.get("hidden") or spec.get("kind"):
            continue
        base = LOOKS.get(spec.get("look", "boy"), {})
        fixed_build = "build" in spec or "build" in base
        fixed_height = "height" in spec or float(base.get("scale", 1.0)) != 1.0
        if fixed_build and fixed_height:
            continue
        start = zlib.crc32(name.encode("utf-8")) % len(BODIES)
        for i in range(len(BODIES)):
            h, b = BODIES[(start + i) % len(BODIES)]
            hh = spec.get("height", "normal" if fixed_height else h)
            bb = spec.get("build", base.get("build", b))
            if (hh, bb) not in used:
                break
        used.append((hh, bb))
        if not fixed_height and hh != "normal":
            spec["height"] = hh
        if not fixed_build and bb != "normal":
            spec["build"] = bb
    return cast


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


# plain words a writer (or a chat AI) often uses for a feeling or an action -> the studio's own word, so a script
# written with "happy", "gussa", "running" still acts (the writer prompt then needs fewer rules)
FEEL_WORDS = {
    "staring": "stare", "judging": "side_eye", "sideeye": "side_eye",
    "laar": "drool", "drooling": "drool", "lalach": "money_eyes", "paisa": "money_eyes", "sharminda": "embarrassed",
    "happy": "smile", "khush": "smile", "cheerful": "smile", "smiling": "smile", "gusse": "angry", "ghussa": "angry",
    "naraz": "angry", "naraaz": "angry", "irritated": "angry", "annoyed": "angry", "frustrated": "angry",
    "furious": "angry", "mad": "angry", "dukhi": "sad", "upset": "sad", "udaas": "sad", "udas": "sad",
    "worried": "nervous", "tension": "nervous", "tense": "nervous", "anxious": "nervous", "ghabraya": "nervous",
    "darr": "scared", "dara": "scared", "afraid": "scared", "hairan": "surprised", "shocked": "shock",
    "amazed": "surprised", "confident": "proud", "tired": "sleepy", "thaka": "sleepy",
    "sharma": "shy", "sarcastic": "smug", "naughty": "sly", "mischievous": "sly", "serious": "neutral",
    "calm": "relaxed", "chill": "relaxed", "crying": "cry", "rona": "cry", "laughing": "laugh", "hasna": "laugh",
    "thinking": "think", "soch": "think", "romantic": "love", "pyaar": "love", "disgusted": "disgust",
    "shouting": "shout", "chillana": "shout", "whispering": "whisper", "running": "run", "bhaag": "run",
    "bhaago": "run", "walking": "walk", "dancing": "dance", "naach": "dance", "nachna": "dance", "sitting": "sit",
    "baith": "sit", "baitho": "sit", "jumping": "jump", "kood": "jump", "pointing": "point", "waving": "wave",
    "clapping": "clap", "taali": "clap", "sleeping": "sleep", "khaana": "eat", "drinking": "drink",
    "peena": "drink", "reading": "read", "padhna": "read", "writing": "write", "likhna": "write", "falling": "fall",
    "gira": "fall", "girna": "fall", "hugging": "hug", "shrugging": "shrug", "nodding": "nod", "slapping": "slap",
    "thappad": "slap", "punching": "punch", "kicking": "kick", "throwing": "throw", "singing": "sing",
    "texting": "text", "cooking": "cook", "sweeping": "sweep", "jhadu": "sweep", "hiding": "hide", "peeking": "peek",
    "jhaank": "peek",
}


SOUND_RANGE = re.compile(r"^((?:\d+:)?\d+(?:\.\d+)?)\s*-\s*((?:\d+:)?\d+(?:\.\d+)?)$")


def _secs(v):
    m, _, s_ = v.rpartition(":")
    return int(m or 0) * 60 + float(s_)


def parse_sound(val):
    """`SOUND: sound-ab12cd 0:05-0:20` / `SOUND: assets/music/x.mp3` -> ({"src", "start", "end"}, warning)."""
    words = val.split()
    if not words:
        return None, "SOUND: ke baad sound ka naam likho (page pe 🎵 Sound se reel)"
    spec = {"src": words[0], "start": 0.0, "end": None}
    rest = " ".join(words[1:])
    if rest:
        m = SOUND_RANGE.match(rest.replace(" ", ""))
        if not m:
            return spec, "SOUND %r: hissa aise likho: 0:05-0:20 (shuru-aakhir)" % rest
        spec["start"], spec["end"] = _secs(m.group(1)), _secs(m.group(2))
        if spec["end"] <= spec["start"]:
            return dict(spec, end=None), "SOUND: aakhir shuru ke baad hona chahiye (%s)" % rest
    return spec, None


SOUND_AT = re.compile(r"^@(?:(\d+):)?(\d+(?:\.\d+)?)$")


def sound_time(word):
    """'@1.8' -> 1.8, '@0:03.2' -> 3.2 (seconds into the SOUND), else None."""
    m = SOUND_AT.match(word or "")
    return None if not m else int(m.group(1) or 0) * 60 + float(m.group(2))


def _stage(tokens, ev, scene_cast, who):
    """Apply bracket / arrow words to an event dict.
    Returns (move request or None, unknown words, words that were overridden)."""
    at = [sound_time(w) for w in tokens if sound_time(w) is not None]
    if at:                                          # (sound mode) when this line is said in the sound
        ev["sound_at"] = at[0]
        tokens = [w for w in tokens if sound_time(w) is None]
    tokens = [FEEL_WORDS.get(w, w) for w in tokens]
    if "gussa" in tokens and not any(w in EXPRESSIONS for w in tokens):
        tokens.append("angry")                      # (gussa) = the 💢 mark AND an angry face, as a writer means it
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
        elif w in TURN_WORDS:                       # side: turned to the one they talk to (profile); saamne: back
            ev["view"] = TURN_WORDS[w]
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
        elif w in ("reveal", "open_reveal"):        # start close on the face, pull back to the whole place
            ev["camera"] = dict(ev.get("camera", {}), reveal=who if who in scene_cast else True)
            if w == "open_reveal":                  # (the studio's own opening, not the writer's camera)
                ev["camera"]["auto"] = True
        elif w == "open_close":                     # the studio's own opening: the first line close
            w = "close"
            ev["shot"] = "close"
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


def _drive_base(kind):
    """"car" / "auto" for a car / an auto and its driving shots (studio.drive), else None."""
    kind = str(kind or "")
    if kind in ("car", "auto"):
        return kind
    return drive.POV[kind][0] if kind in drive.POV else None


def split_drives(scenes, cast):
    """A car / an auto scene written without CUT: the studio cuts the drive like a film: it opens outside, from the
    side; then from in front and inside by turns, a passenger's line from the driver's eyes now and then; the punch
    line in the rear-view mirror."""
    groups = {}
    for sc in scenes:
        groups.setdefault(sc.get("place_no", id(sc)), []).append(sc)
    out = []
    for sc in scenes:
        kind = sc["background"].get("type")
        if vehicles.resolve(kind) in ("car", "auto") and kind not in drive.POV:
            sc["background"]["type"] = vehicles.resolve(kind)       # a taxi is a car, a rickshaw an auto
    for sc in scenes:
        group = groups[sc.get("place_no", id(sc))]
        base = _drive_base(sc["background"].get("type"))
        if not base or sc.get("cut_in") or sc.get("directed") or len(group) > 1 or \
                sc["background"].get("type") != base:
            if base:
                sc["drive"] = True
            out.append(_cabin(sc))
            continue
        says = [i for i, ln in enumerate(sc["lines"]) if ln[0] == "say" and ln[1] in cast]
        riders = _drive_order([n for n in cast if any(ln[0] in ("say", "do") and ln[1] == n for ln in sc["lines"])],
                              cast, base)
        driver = riders[0] if riders else None
        front_seat = riders[1] if len(riders) > 1 else None
        if len(says) < 2:
            sc["drive"] = True
            out.append(_cabin(sc))
            continue
        cuts = [0] + says[1:]
        povs = []
        for k, i in enumerate(says):
            who = sc["lines"][i][1]
            if k == 0:
                povs.append("side")                 # it opens outside: the car going down the road
            elif k == len(says) - 1 and len(says) >= 4:
                povs.append("mirror")               # the punch line, close, in the rear-view mirror
            elif k >= 2 and "pov" not in povs[-2:] and (who == driver or (base == "car" and who == front_seat)):
                povs.append("pov")                  # from the driver's eyes: his own voice, or the one beside him
            else:                                   # from in front and from inside, by turns
                last = next((p_ for p_ in reversed(povs) if p_ in ("front", "inside")), "inside")
                pick = "inside" if last == "front" else "front"
                if pick == "inside" and base == "auto" and who == driver:     # (in the auto he sits in front)
                    pick = next(p_ for p_ in ("front", "pov", "side") if p_ != povs[-1])
                povs.append(pick)
        for k, (a, pov) in enumerate(zip(cuts, povs)):
            b = cuts[k + 1] if k + 1 < len(cuts) else len(sc["lines"])
            part = dict(sc, lines=sc["lines"][a:b], background=dict(sc["background"]), drive=True)
            part["background"]["type"] = base if pov == "inside" else "%s_%s" % (base, pov)
            part["sets"] = {} if pov != "inside" else dict(sc.get("sets") or {})
            if k:
                part.update(cut_in=True, shot=k, title=None)
            out.append(_cabin(part))
    return out


DRIVER_LOOKS = ("driver", "autowala", "taxiwala")


def _drive_order(names, cast, base=None):
    """Who sits where in a car / an auto: a driver (CAST: A = driver / autowala / taxiwala) drives, else the first
    in CAST; the others in CAST order. An auto always has its driver: the cast's autowala / driver sits in front
    even when he does not say anything."""
    def drives(n):
        spec = cast.get(n) or {}
        return spec.get("look") in DRIVER_LOOKS or spec.get("role") in DRIVER_LOOKS

    names = list(names)
    if base == "auto" and names and not any(drives(n) for n in names):
        hired = next((n for n in cast if drives(n) and not (cast.get(n) or {}).get("hidden")), None)
        if hired:
            names.append(hired)

    def key(n):
        spec = cast.get(n) or {}
        drives = spec.get("look") in DRIVER_LOOKS or spec.get("role") in DRIVER_LOOKS
        return (0 if drives else 1, list(cast).index(n) if n in cast else 99)
    return sorted(names, key=key)


def _cabin(sc):
    """The new camera's inside of a car is the cabin from the dashboard (studio.drive): the two front seats, the back
    seat behind them; not the row of seats of the vehicle engine (that stays for CAMERA: classic)."""
    if sc.get("drive") and sc["background"].get("type") == "car":
        sc["background"]["type"] = "car_cabin"
        sc["sets"] = {}
    return sc


def _slot_x(cast, name):
    n = len(cast)
    slots = slots_for(n)
    names = auto_slots(n)
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


UI_WORDS = ("NOTIFY", "NOTIFICATION", "LOADING", "COUNTER", "TIMECARD", "CHAPTER", "ENDCARD", "WHATSAPP", "INSTA",
            "ORDER", "UPI")
APP_COLORS = {"zomato": [226, 55, 68], "swiggy": [252, 128, 25], "blinkit": [248, 203, 70], "zepto": [90, 30, 150],
              "amazon": [35, 47, 62], "flipkart": [40, 116, 240]}


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
    if key == "WHATSAPP":                               # WHATSAPP: Mummy | < Kahan ho? | > Library me | < Photo bhejo
        msgs = []
        for p in parts[1:]:
            if not p:
                continue
            me = p.startswith(">")
            msgs.append({"side": "me" if me else "them", "text": p.lstrip("<>").strip(), "at": 0.4 + 1.1 * len(msgs)})
        if not msgs:
            return None, 0, "WHATSAPP: 'WHATSAPP: Mummy | < Kahan ho? | > Library me' likho (< unka, > apna message)"
        hold = 0.4 + 1.1 * len(msgs) + 1.0
        return {"type": "phone_chat", "title": parts[0], "messages": msgs, "dur": hold + 0.3}, hold, None
    if key == "INSTA":                                  # INSTA: bittu_official | 2 | Exam ke pehle chill 😎 | 🏖️
        likes = re.sub(r"[^\d]", "", parts[1]) if len(parts) > 1 else ""
        spec = {"type": "insta", "user": parts[0].lstrip("@"), "likes": int(likes or 0),
                "caption": parts[2] if len(parts) > 2 else "", "dur": 3.0}
        if len(parts) > 3 and parts[3]:
            spec["emoji"] = parts[3]
        return spec, 2.7, None
    if key == "ORDER":                                  # ORDER: Zomato | Paneer Butter Masala | Rs 349 | Delivered
        spec = {"type": "order", "app": parts[0], "item": parts[1] if len(parts) > 1 else "",
                "price": parts[2] if len(parts) > 2 else "", "status": parts[3] if len(parts) > 3 else
                "Out for delivery", "eta": parts[4] if len(parts) > 4 else "", "dur": 3.2}
        if parts[0].strip().lower() in APP_COLORS:
            spec["color"] = APP_COLORS[parts[0].strip().lower()]
        return spec, 2.9, None
    if key == "UPI":                                    # UPI: Rs 2000 | Sharma ji | Payment successful (or failed)
        spec = {"type": "upi", "amount": parts[0], "payee": parts[1] if len(parts) > 1 else "",
                "status": parts[2] if len(parts) > 2 else "Payment successful", "dur": 2.4}
        return spec, 2.1, None
    if key == "CHAPTER":
        spec = {"type": "chapter", "text": parts[0]}
        if len(parts) > 1:
            spec["subtitle"] = parts[1]
        return spec, 2.0, None
    spec = {"type": "endcard", "text": parts[0]}          # ENDCARD
    if len(parts) > 1:
        spec["sub"] = parts[1]
    return spec, 2.4, None


def pan_traveler(prev, who=None):
    """`SCENE: <place> pan`: who walks from the scene `prev` into the next one, and which way. The one whose
    `X -> exit left|right` comes last in prev (or `who`, if named). None if nobody."""
    for ln in reversed(prev["lines"]):
        if ln[0] != "do" or (who and ln[1] != who):
            continue
        words = [w.lower() for w in ln[2]]
        if "exit" in words:
            i = words.index("exit")
            side = words[i + 1] if i + 1 < len(words) and words[i + 1] in ("left", "right") else "right"
            return {"who": ln[1], "dir": side}
    return {"who": who, "dir": "right"} if who else None


PLACE_WORDS = {"sweet_shop": "mithai_shop", "halwai_shop": "mithai_shop", "mithai_ki_dukaan": "mithai_shop",
               "mobile_store": "mobile_shop", "phone_shop": "mobile_shop", "chemist": "medical_store",
               "pharmacy": "medical_store", "medical": "medical_store", "dawai_ki_dukaan": "medical_store"}
from .places_plus import SHOPS as SHOP_PLACES   # noqa: E402  (a shop brings its counter: `SCENE: mithai_shop`)


# a seller whose place has no counter of its own brings his stall (thelewala: the one his lines talk about)
SELLER_STALL = {"kulchewala": "thela_kulche", "chaiwala": "thela_chai", "sabziwala": "thela", "thelewala": None,
                "halwai": "counter_mithai", "dukaandaar": "counter", "chemist": "counter_medical"}


PARKED = {"y": 1540.0, "scale": 0.82}      # a thela parked by the side of the road / lane: a step back from the people
PARK_X = {None: 700.0, "center": 700.0, "right": 700.0, "left": 380.0}


def _seller_of(names, place, cast):
    """The person of these who sells / works behind a counter here, or None."""
    from . import counters
    for n in names:
        spec = cast.get(n, {})
        if spec.get("look") in SELLER_STALL or spec.get("behind") is True:
            return n
        if any(counters._wants(spec, info) for info in counters.PLACES.get(place, [])):
            return n
    return None


def bring_stalls(scenes, cast):
    """A place with a seller is one fixed set, filmed by the studio:
    - the CUTs a writer put into a conversation across a counter are taken out (the studio cuts it like a film
      itself: the people stay where they are, only the camera changes);
    - every shot of the place keeps its thela / counter: the one a line put there, else the seller's own (a
      kulchewala without a thela is just a man in a lane), parked by the side of the road, not in the middle.
    Not where the place has its own counter (chai_tapri, kirana, market...), in the shops or inside a vehicle."""
    from . import counters
    groups = {}
    for sc in scenes:
        groups.setdefault(sc.get("place_no", id(sc)), []).append(sc)
    for shots in groups.values():
        bg = shots[0].get("background") or {}
        place = bg.get("type") if isinstance(bg, dict) else bg
        if vehicles.resolve(place):
            continue
        names = []
        for sc in shots:
            for ln in sc["lines"]:
                if ln[0] in ("say", "do") and ln[1] in cast and ln[1] not in names \
                        and not cast[ln[1]].get("hidden") and not cast[ln[1]].get("kind"):
                    names.append(ln[1])
        seller = _seller_of(names, place, cast)
        if seller is not None and len(names) > 1 and len(shots) > 1 and not any(sc.get("pan") for sc in shots[1:]):
            first = shots[0]                        # one set, one take: the studio does the cutting
            for sc in shots[1:]:
                first["lines"] += sc["lines"]
                scenes.remove(sc)
            first.pop("framing", None)
            first.pop("reverse", None)
            first.pop("back", None)
            shots = [first]
        if place in counters.PLACES or place in SHOP_PLACES or any(sc.get("pan") for sc in shots):
            continue                                # (a one-take walk into the place keeps its own timing)

        def counter_line(sc):
            return next((ln for ln in sc["lines"] if ln[0] == "obj"
                         and objects.resolve_kind(ln[1].get("kind", "")) in objects.COUNTERS), None)

        def park(spec):                             # a thela stands by the side of the road
            if objects.resolve_kind(spec.get("kind", "")) in objects.THELAS and not spec.get("enter") \
                    and spec.get("at") in PARK_X and "y" not in spec:
                spec["at"] = PARK_X[spec.get("at")]
                spec.update(PARKED)
            return spec
        first = next((i for i, sc in enumerate(shots) if counter_line(sc)), None)
        if first is not None:                       # the writer's own: parked in the later shots too
            spec = park(counter_line(shots[first])[1])
            if spec.get("exit"):
                continue
            keep = {"kind": spec["kind"], "at": spec.get("at") or spec.get("go") or "center", "carried": True}
            for k in ("color", "scale", "front", "y"):
                if k in spec:
                    keep[k] = spec[k]
            for sc in shots[first + 1:]:
                if not counter_line(sc):
                    sc["lines"].insert(0, ("obj", dict(keep)))
            continue
        if seller is None or cast[seller].get("look") not in SELLER_STALL:
            continue
        kind = SELLER_STALL[cast[seller]["look"]]
        if kind is None:                            # thelewala: what do the lines talk about? (chaat, momos...)
            said = " ".join(str(ln[3]) for sc in shots for ln in sc["lines"] if ln[0] == "say" and len(ln) > 3)
            kind = next((objects.thela_kind(w) for w in re.findall(r"[a-z_]+", said.lower())
                         if objects.thela_kind(w)), "thela")
        for sc in shots:
            sc["lines"].insert(0, ("obj", park({"kind": kind, "at": "center", "auto": True})))


def resolve_background(raw):
    """`street` / `gali` (= assets/backgrounds/gali.png) / `assets/backgrounds/x.jpg` -> (background dict, warning)."""
    name = raw.strip()
    low = name.lower().replace(" ", "_")
    low = PLACE_WORDS.get(low, low)
    if low in BACKGROUNDS:
        return {"type": low}, None
    words = name.lower().split()
    veh = vehicles.resolve(words[0]) if words else None
    if veh and all(w in TIMES or w in WEATHER or w in vehicles.VIEW_WORDS for w in words[1:]):
        bg = {"type": veh}                          # "train gaon night": inside the train, fields going past
        for w in words[1:]:
            if w in vehicles.VIEW_WORDS:
                bg["view"] = vehicles.VIEW_WORDS[w]
            elif w in TIMES:
                bg["time"] = w
            else:
                bg.setdefault("weather", []).append(w)
        return bg, None
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
        elif spec["kind"] == "thela" and objects.thela_kind(w):     # `OBJ: thela kulche enter left`
            spec["kind"] = objects.thela_kind(w)
        elif spec["kind"] == "counter" and objects.counter_kind(w):  # `OBJ: counter mithai center`
            spec["kind"] = objects.counter_kind(w)
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


HEADER_WORDS = ("HOOK", "CAST", "SOUND", "SCENE", "CTA", "CAPTION", "HASHTAGS", "MUSIC", "TRANSITION", "STYLE", "CAMERA", "OBJ",
                "DRESS",
                "LOOP", "MASCOT", "COLOR", "CTA_STYLE", "HANDLE", "COVER", "CROWD", "LOOK", "MYSTERY", "SERIES",
                "NARRATOR",
                "LIGHTS", "AMBIENCE", "NOTIFY", "LOADING", "COUNTER", "TIMECARD", "CHAPTER", "ENDCARD", "WHATSAPP",
                "INSTA", "ORDER", "UPI")


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


SAVED_FILE = "characters.json"
SAVED_RE = re.compile(r"@([A-Za-z_][\w]*)")


def saved_characters(path=None):
    """Your saved characters, {name: "cast words"}, from characters.json (or $STUDIO_CHARACTERS):
    {"raju": "uncle mohawk handlebar_moustache big_ears", "pinky": "girl bob lashes mole"}. A missing file = none."""
    import json
    path = path or os.environ.get("STUDIO_CHARACTERS") or asset_path(SAVED_FILE)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k).strip().lstrip("@").lower(): " ".join(v) if isinstance(v, list) else str(v)
            for k, v in data.items()}


def expand_saved(words, saved, warnings):
    """`R = @raju` -> R = the words saved for raju (an unknown name is dropped with a warning)."""
    def sub(m):
        name = m.group(1).lower()
        if name in saved:
            return " " + saved[name] + " "
        warnings.append("@%s: ye saved character nahi mila. Page par 💾 se save karo, ya characters.json me likho "
                        "(\"%s\": \"uncle mohawk big_ears\")" % (m.group(1), name))
        return " "
    return SAVED_RE.sub(sub, words)


SERIES_DIR = "series"
SERIES_RE = re.compile(r"^\s*SERIES\s*:\s*([A-Za-z0-9_\-]+)(?:\s+(?:part|ep|episode|#)?\s*(\d+))?\s*$", re.I | re.M)
SPEAKER_RE = re.compile(r"^\s*([A-Za-z][\w]*)\s*(?:\(|:|->)", re.M)


def load_series(name):
    """series/<name>.json -> dict, or None. {"title", "cast": {letter: "cast words"}, "names", "place", "color",
    "hashtag", "handle"}."""
    import json
    path = asset_path(os.path.join(SERIES_DIR, name.strip().lower() + ".json"))
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and isinstance(data.get("cast"), dict) else None


def series_words(series, letter, words):
    """The cast words of a series character with its face pinned (face shape, eyes, nose, brows, height), chosen
    from the series and the letter: the same face in every episode, whoever else is in it. Words the series file
    already gives win."""
    v = vocab()["face_parts"]
    have = set(words.lower().split())
    h = zlib.crc32(("series|%s|%s" % (series, letter)).encode("utf-8"))
    add = []
    for i, part in enumerate(("face", "eyes", "nose", "brows")):
        opts = [w for _val, w in v[part]]
        if not have & set(opts) and not have & {val for val, _w in v[part]}:
            add.append(opts[(h >> (4 * i)) % len(opts)])
    small = have & {"kid", "kid_girl", "bachcha", "dada", "dadi", "nani", "nana", "school_boy", "school_girl"}
    if not small and not have & {"tall", "lamba", "lambi", "nata", "nati", "short"}:
        hw = ("", "lamba", "", "nata")[(h >> 16) % 4]
        if hw:
            add.append(hw)
    return " ".join([words] + add)


def apply_series(text):
    """`SERIES: sharma_parivar 3`: the same family in every episode. The series' people who act in this script join
    its CAST (a letter the script casts itself keeps the script's words), and its colours, handle and first place
    come in when the script does not set them. Returns (text, series info or None, warnings)."""
    m = SERIES_RE.search(text)
    if not m:
        return text, None, []
    name, part = m.group(1).lower(), int(m.group(2)) if m.group(2) else None
    data = load_series(name)
    if not data:
        return text, None, ["SERIES %r: series/%s.json nahi mili (series/ folder me family ki file banao)" % (name, name)]
    cast = {str(k): series_words(name, str(k), str(v)) for k, v in data["cast"].items()}
    speakers = set(SPEAKER_RE.findall(text))
    used = [k for k in cast if k in speakers] or list(cast)        # always in the series' own order
    cast_line = re.search(r"^\s*CAST\s*:\s*(.*)$", text, re.M | re.I)
    have = set()
    if cast_line:
        have = {p.split("=")[0].strip() for p in cast_line.group(1).split(",") if "=" in p}
    extra = ["%s = %s" % (k, cast[k]) for k in used if k not in have]
    add = []
    if extra and cast_line:
        text = text[:cast_line.end()] + (", " if cast_line.group(1).strip() else "") + ", ".join(extra) + \
            text[cast_line.end():]
    elif extra:
        add.append("CAST: " + ", ".join(extra))
    for key, field in (("COLOR", "color"), ("HANDLE", "handle")):
        if data.get(field) and not re.search(r"^\s*%s\s*:" % key, text, re.M | re.I):
            add.append("%s: %s" % (key, data[field]))
    if data.get("place") and not re.search(r"^\s*SCENE\s*:", text, re.M | re.I):
        add.append("SCENE: %s" % data["place"])
    if add:
        text = text[:m.end()] + "\n" + "\n".join(add) + text[m.end():]
    info = {"name": name, "title": data.get("title") or name.replace("_", " ").title(), "part": part,
            "hashtag": data.get("hashtag")}
    return text, info, []


def parse_script(text):
    """Return (scene dict, warnings)."""
    text, flat = unflatten(text)
    if flat:
        scene, warns = parse_script(text)
        return scene, ["script ek hi line me aaya tha (line break kho gaye); lines apne aap alag ki"] + warns
    text, series_info, series_warn = apply_series(text)
    if series_info or series_warn:
        scene, warns = _parse_script(text)
        if series_info:
            _series_badge(scene, series_info)
        return scene, series_warn + warns
    return _parse_script(text)


def _series_badge(scene, info):
    """The series' name (and the part) as a small tag at the top of the first seconds, its hashtag in the post."""
    label = info["title"] + (" • Part %d" % info["part"] if info["part"] else "")
    scene["series"] = dict(info, label=label)
    scene.setdefault("overlays", []).append({"text": label, "style": "tag", "size": 30, "max_w": 700,
                                             "pos": [540, 92], "from": 0.0, "to": 3.2, "anim": "pop", "series": True})
    post = scene.setdefault("post", {})
    tags = post.setdefault("hashtags", [])
    if info.get("hashtag") and info["hashtag"] not in tags:
        tags.insert(0, info["hashtag"])
    if info["part"] and post.get("caption") and "Part" not in post["caption"]:
        post["caption"] = post["caption"] + " (Part %d)" % info["part"]


def _parse_script(text):
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
    sound_mode = bool(re.search(r"^\s*SOUND\s*:", text, re.M | re.I))     # a viral sound: one place, one take
    told = set()

    def once(key, msg):
        if key not in told:
            told.add(key)
            warnings.append(msg)

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
                        if "@" in w:                # a saved character: `R = @raju` (+ more words if you like)
                            w = expand_saved(w, saved_characters(), warnings)
                        add_cast(n.strip(), _words(w))
            elif key == "SCENE" and sound_mode and cur is not None:
                once("scene", "SOUND ke saath ek hi jagah: doosri SCENE line chhod di (sound bina ruke chalta hai)")
            elif key == "SCENE":
                bg, _, rest = val.partition("|")
                title, _, frame = rest.partition("|")
                bgw, pan = bg.split(), None
                pi = next((i for i, w in enumerate(bgw) if w.lower() in PAN_WORDS), None)
                if pi is not None and pi > 0:       # `SCENE: street pan` / `SCENE: street pan C`
                    nxt = bgw[pi + 1] if pi + 1 < len(bgw) else None
                    named = nxt if nxt and (nxt in cast or re.match(r"^[A-Z]\w*$", nxt)) else None
                    pan = {"who": named}
                    bgw = bgw[:pi] + bgw[pi + (2 if named else 1):]
                    bg = " ".join(bgw)
                bg, warn = resolve_background(bg.strip() or "room")
                if warn:
                    warnings.append(warn)
                frame = frame.strip().lower()
                if frame and frame not in FRAMINGS:
                    warnings.append("SCENE framing %r: wide / medium / inside" % frame)
                    frame = ""
                cur = new_scene(bg, title.strip() or None)
                cur["place_no"] = len(scenes)
                cur["framing"] = frame or None
                if pan:
                    cur["pan"] = pan
                if bg.get("type") == "jail":
                    cur["sets"] = {"jail_door": dict(JAIL_DOOR)}
                if bg.get("type") in SHOP_PLACES:   # the shop's counter, its shopkeeper goes behind it
                    cur["lines"].append(("obj", {"kind": SHOP_PLACES[bg["type"]], "at": "center", "auto": True}))
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
        if m and sound_mode:                        # one take: the camera cuts to the speakers by itself
            once("cut", "SOUND ke saath CUT ki zarurat nahi: camera khud har bolne wale pe jaata hai (CUT chhod diye)")
            continue
        if m:                                       # a new shot in the same place: a hard cut, its own set of characters
            frame, reverse, back, pov = "", False, None, None
            drive_base = _drive_base(cur["background"].get("type"))
            for w in re.split(r"[\s,]+", m.group(1).strip()):
                lw = w.lower()
                if not w:
                    continue
                if drive_base and lw in drive.POV_WORDS and not pov:      # a car / an auto: from where we see it
                    pov = drive.POV_WORDS[lw]
                    if lw in FRAMINGS and not frame:
                        frame = lw                  # (`CUT inside`: the driver big in the middle, as before)
                elif lw in FRAMINGS and not frame:
                    frame = lw
                elif lw in OTS_WORDS and not frame:
                    frame = "ots"
                elif lw in ANGLE_WORDS:
                    reverse = True
                elif w in cast or (frame == "ots" and re.match(r"^[A-Z]\w*$", w) and back is None):
                    back = w
                else:
                    warnings.append("CUT %r: framing wide / medium / inside / ots (+ reverse) likho" % w)
            if pov and not cur["lines"]:            # SCENE: car + CUT front before anybody speaks: it starts so
                cur["framing"] = frame or cur.get("framing")
            else:
                shot_no = cur.get("shot", 0) + 1
                prev_sets = {k: dict(v) for k, v in cur.get("sets", {}).items()}
                prev_lights = cur.get("lights", "on")
                prev_amb, prev_dress, place_no = cur.get("ambience"), cur.get("dress"), cur.get("place_no", 0)
                cur = new_scene(dict(cur["background"]), None)
                cur["place_no"] = place_no              # same place: dressed the same
                if prev_dress is not None:
                    cur["dress"] = prev_dress
                if prev_amb is not None:
                    cur["ambience"] = prev_amb              # same place: the same sound around
                cur["sets"] = prev_sets                 # same place: the door / sofa / fan are still there
                cur["lights"] = cur["lights_start"] = prev_lights     # ... and the lights stay as they were
                cur["cut_in"], cur["framing"], cur["shot"] = True, frame or None, shot_no
            if pov:                                 # the same drive, seen from somewhere else
                cur["background"]["type"] = drive_base if pov == "inside" else "%s_%s" % (drive_base, pov)
                cur["drive"] = cur["directed"] = True    # (the writer cuts this drive: the studio does not)
                cur["sets"] = {}
            if reverse:
                cur["reverse"] = True
            if frame == "ots":
                cur["back"] = back
            continue
        m = re.match(r"^(NOTIFY|NOTIFICATION|LOADING|COUNTER|TIMECARD|CHAPTER|ENDCARD|WHATSAPP|INSTA|ORDER|UPI)\s*:\s*(.*)$",
                     line, re.I)
        if m:
            if cur is None:
                cur = new_scene()
            spec, hold, warn = ui_line(m.group(1).upper(), m.group(2).strip())
            if warn:
                warnings.append(warn)
            if spec:
                cur["lines"].append(("ui", spec, hold))
            continue
        m = re.match(r"^DRESS\s*:\s*(.*)$", line, re.I)
        if m:                                       # DRESS: shaadi / poster, plant / none: dress up the place
            if cur is None:
                cur = new_scene()
            words = _words(m.group(1))
            _items, bad = decor.words_to_items(words)
            if bad:
                warnings.append("DRESS: %s nahi hai (packs: %s; pieces: %s)"
                                % (", ".join(bad), ", ".join(decor.PACKS), ", ".join(decor.PIECES)))
            cur["dress"] = [w for w in words if w not in bad]
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
                if spec.get("kind") in objects.SHOP_COUNTERS:     # your own counter replaces the shop's own one
                    cur["lines"] = [ln for ln in cur["lines"] if not (ln[0] == "obj" and ln[1].get("auto"))]
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
    classic = meta.get("CAMERA", "").strip().lower() in ("classic", "old", "purana") or _classic_env()
    if not classic:                                 # every video opens on its own kind of first shot
        first = next((ln for ln in scenes[0]["lines"] if ln[0] == "say" and ln[1] != "NARRATOR"), None)
        camera_words = set(SHOTS) | {"zoom", "reveal"}
        if first and len(first[3]) >= 18 and not any(w in camera_words for w in first[2]):   # (not on quick banter)
            pick = OPENINGS[zlib.crc32(("open|" + (meta.get("HOOK") or "reel")).encode("utf-8")) % len(OPENINGS)]
            if pick != "plain":                     # (marked as the studio's own: it gives way to a directed scene)
                first[2].append("open_" + pick)

    if not classic:                                 # a seller brings his thela / counter; it stays through the CUTs
        bring_stalls(scenes, cast)

    # ---- build timelines ----
    out_scenes = []
    if not classic and not sound_mode:              # a car / an auto with no CUT: the studio cuts its drive itself
        scenes[:] = split_drives(scenes, cast)
    riders = {}                                     # who is in each car / auto (CAST order: the first one drives)
    for sc in scenes:
        if sc.get("drive") or _drive_base(sc["background"].get("type")):
            got = riders.setdefault(sc.get("place_no", id(sc)), [])
            for ln in sc["lines"]:
                if ln[0] in ("do", "say") and ln[1] in cast and ln[1] not in got and not cast[ln[1]].get("hidden"):
                    got.append(ln[1])
    for k_ in riders:
        kinds_ = [_drive_base(sc["background"].get("type")) for sc in scenes if sc.get("place_no", id(sc)) == k_]
        riders[k_] = _drive_order(riders[k_], cast, next((b for b in kinds_ if b), None))
    for si, sc in enumerate(scenes):
        order = []
        for ln in sc["lines"]:
            if ln[0] in ("do", "say") and ln[1].upper() not in ("ALL", "NARRATOR") and ln[1] not in order:
                order.append(ln[1])
        if sc.get("place_no", id(sc)) in riders and riders[sc.get("place_no", id(sc))]:
            order = list(riders[sc.get("place_no", id(sc))])          # everybody in the vehicle is in every shot
        narrated = any(ln[0] == "say" and ln[1] == "NARRATOR" for ln in sc["lines"])
        pan = None
        if sc.get("pan") and si:
            pan = pan_traveler(scenes[si - 1], sc["pan"].get("who"))
            if pan is None:
                warnings.append("SCENE pan: pichhle scene se kaun chalkar aaye? Pichhla scene `C -> exit right` par "
                                "khatam karo, ya `SCENE: <jagah> pan C` likho")
            else:                                   # they come in on the side they walked towards
                if pan["who"] in order:
                    order.remove(pan["who"])
                order.insert(0 if pan["dir"] == "right" else len(order), pan["who"])
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
        pov_place = drive.PLACES.get(sc["background"].get("type"))
        if pov_place:                               # a driving shot: the driver at the wheel, the others beside / behind
            speaker = next((ln[1] for ln in sc["lines"] if ln[0] == "say" and ln[1] in chars), None)
            xs = pov_place["xs"]
            for i, name in enumerate(fronts):
                x_ = xs[i] if i < len(xs) else None
                if pov_place.get("only_speaker"):
                    x_ = xs[0] if name == speaker else None
                if x_ is None:                      # the driver is the camera / not in the mirror
                    chars[name] = {"hidden": True}
                    continue
                chars[name] = {"x": x_, "facing": pov_place["facing"]}
                if pov_place.get("view"):
                    chars[name]["view"] = pov_place["view"]
                ys, ks = pov_place.get("ys") or (), pov_place.get("ks") or ()
                y_ = ys[i] if i < len(ys) and not pov_place.get("only_speaker") else pov_place.get("y")
                if y_:
                    chars[name]["y"] = y_
                if i < len(ks) and ks[i] != 1:      # a back seat: further from the camera
                    chars[name]["depth_k"] = ks[i]
        steer_who = None
        if pov_place and pov_place.get("steer") and fronts and not chars[fronts[0]].get("hidden"):
            steer_who = fronts[0]                   # both hands on the wheel (actions.steer)
        if not pov_place and sc.get("drive") and sc["background"].get("type") == "auto" and len(fronts) > 1 \
                and not classic:
            chars[fronts[0]] = {"hidden": True}     # inside the auto: the passengers' bench; he sits in front
            fronts = fronts[1:]
            for name in fronts:
                x, slot = _slot_x(fronts, name)
                chars[name] = {"slot": slot, "facing": "front" if len(fronts) != 2 else
                               ("right" if slot == "left" else "left")}
        if back:                                    # over the shoulder: back's back big in the near corner
            side = "left" if sc.get("shot", 0) % 2 == 0 else "right"
            chars[back] = {"slot": side, "view": "back"}
            for name in fronts:
                chars[name]["facing"] = side        # the speaker talks to the one in front of the camera
            if back not in order:
                order.append(back)
        tl = [{"t": 0.0, "who": "all", "action": "idle", "expression": "smile"}]
        if steer_who:
            tl.append({"t": 0.0, "who": steer_who, "action": "steer"})
        if si == 0:
            tl.append({"t": 0.0, "sfx": "whoosh", "volume": 0.7, "camera": {"shake": 0.5}})
        # the story starts a moment in; a `wait`, a screen card or a set change before the first line now really
        # comes first (they used to be skipped because the first line had a fixed start time)
        for name in fronts:                         # a look with its own face keeps it (the bhoot grins)
            face = LOOKS.get(cast.get(name, {}).get("look", ""), {}).get("expression")
            if face and "expression" not in cast.get(name, {}):
                tl.append({"t": 0.0, "who": name, "expression": face})
        seated = {}
        veh = vehicles.resolve(sc["background"].get("type"))
        if veh and not vehicles.VEHICLES[veh].get("seat"):
            veh = None                              # a driving shot: no seats of its own
        if veh:                                     # inside a vehicle: everybody starts on a seat at their place
            for name in fronts:
                spec_ = cast.get(name, {})
                if spec_.get("kind") or spec_.get("hidden") or spec_.get("look") in STANDING_LOOKS:
                    continue
                x, _slot = _slot_x(fronts, name)
                sid = "seat_" + re.sub(r"\W", "", name.lower())
                piece = {"id": sid, "type": vehicles.VEHICLES[veh]["seat"], "x": x, "y": 1700}
                if len(fronts) >= 3:
                    piece["scale"] = 0.8
                sc.setdefault("sets", {})[sid] = piece
                seated[name] = sid
                tl.append({"t": 0.0, "who": name, "action": "sit", "on": sid})
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
            if who in seated:                           # inside a vehicle, seated
                act = ev.get("action")
                if move or "entry" in ev or "leave" in ev or act in STAND_UP:
                    seated.pop(who, None)               # gets up
                elif act:
                    ev["on"] = seated[who]              # pointing, eating, on the phone... still seated
            if ln[0] == "say" and who == steer_who:
                ev.pop("action", None)                  # the driver talks with his hands on the wheel
            if ln[0] == "say":
                ev["say"], ev["speak"] = ln[3], ln[4] or ln[3]
                if sound_mode:
                    ev["tts"] = False                   # the SOUND is the voice
                elif not ln[4] and not re.search(r"[ऀ-ॿ]", ln[3]):
                    warnings.append("no Devanagari for %r: made by the AI when the video is made (GEMINI_API_KEY), "
                                    "else the voice reads Roman letters" % ln[3][:30])
                others = [o for o in order if o != who]
                if who == "NARRATOR":
                    ev["bubble"], ev["subtitle"] = False, True
                    for key in ("action", "expression", "prop", "move", "camera", "sfx", "volume", "facing", "look"):
                        ev.pop(key, None)                       # a voice has no body to act with
                elif (pov_place or sc.get("drive")) and (chars.get(who) or {}).get("hidden"):
                    ev["bubble"], ev["subtitle"] = False, True  # a driving shot: the voice of one out of the shot
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
        if sc.get("dress") is not None:
            item["dress"] = sc["dress"]
        elif not classic:                           # every video dresses its places a little differently
            item["dress"] = "auto"
        if "dress" in item:
            item["dress_seed"] = zlib.crc32(("%s|%d" % (meta.get("HOOK") or "reel", sc.get("place_no", si)))
                                            .encode("utf-8")) % 997
        if sc["title"]:
            item["title"] = sc["title"]
        if pan:
            item["pan"] = pan
        if sc.get("framing"):
            item["framing"] = sc["framing"]
        if sc.get("cut_in"):
            item["cut_in"] = True
        if sc.get("shot"):
            item["angle"] = sc["shot"]
        if sc.get("reverse"):
            item["reverse"] = True
        if pov_place:                               # a driving shot is composed: the camera stays on it whole
            item["meta"] = {"people_scale": pov_place["scale"], "auto_camera": False}
            item["angle"] = {"zoom": 1.0, "x": 540.0, "mirror": False}
        out_scenes.append(item)

    vary_cast(cast)
    if not classic:
        vary_bodies(cast)                           # (`CAMERA: classic`: everybody as before)
        vary_faces(cast)
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
    if sound_mode:
        snd, warn = parse_sound(meta.get("SOUND", ""))
        if warn:
            warnings.append(warn)
        if snd:
            scene["sound"] = snd
            music = None                            # the sound is the music too
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
    th = theme.resolve(meta.get("COLOR")) if meta.get("COLOR") else None
    if meta.get("COLOR") and not th and meta["COLOR"].strip().lower() != "auto":
        warnings.append("COLOR %r: %s ya auto likho" % (meta["COLOR"], ", ".join(theme.THEMES)))
    if not classic:                                 # every video its own colours (the hook card, the CTA, the picture)
        theme.apply(scene, th or theme.auto(hook))
    if meta.get("COVER"):                           # the big words on the cover picture (default: the hook)
        scene["cover"] = meta["COVER"].strip()
    if meta.get("HANDLE"):                          # @page in a corner of every frame
        handle = meta["HANDLE"].strip()
        handle = handle if handle.startswith("@") else "@" + handle
        scene["handle"] = handle
        scene["overlays"].append({"text": handle, "style": "tag", "size": 28, "max_w": 520, "pos": [42, 1120],
                                  "rotate": 90, "from": 0.0, "anim": "none", "alpha": 0.7, "handle": True})
    if meta.get("CROWD"):                           # CROWD: none | kam | zyada: people in the background
        v = meta["CROWD"].strip().lower()
        if v in crowd.AMOUNT:
            scene["crowd"] = v
        else:
            warnings.append("CROWD %r: none, kam ya zyada likho" % meta["CROWD"])
    if meta.get("MYSTERY"):                         # MYSTERY: auto | off | ufo, aadmi, saaya, tasveer...
        v = mystery.resolve(meta["MYSTERY"])
        if v is None:
            warnings.append("MYSTERY %r: auto, off ya inme se ek likho: %s" % (meta["MYSTERY"], ", ".join(mystery.KINDS)))
        elif v != "auto":
            scene["mystery"] = v
    if meta.get("LOOK"):                            # LOOK: auto | off | a look's name (darr, yaad, utsav...)
        v = look.resolve(meta["LOOK"])
        if v is None:
            warnings.append("LOOK %r: auto, off ya inme se ek likho: %s" % (meta["LOOK"], ", ".join(sorted(look.LOOKS))))
        elif v != "auto":
            scene.setdefault("meta", {})["look"] = v
    cs = (meta.get("CTA_STYLE") or "").strip().lower()
    if cs:                                          # CTA_STYLE: card (end card) | sticker | caption
        cs = {"end": "card", "endcard": "card", "chhota": "sticker", "small": "sticker", "off": "caption",
              "none": "caption", "nahi": "caption"}.get(cs, cs)
        if cs in CTA_STYLES:
            scene = apply_cta(scene, cs)
        else:
            warnings.append("CTA_STYLE %r: card, sticker ya caption likho" % meta["CTA_STYLE"])
    if meta.get("LOOP") and sound_mode:
        warnings.append("SOUND ke saath LOOP nahi chalta (sound apni lambai ka hai): LOOP chhod diya")
    elif meta.get("LOOP"):                              # LOOP: on = the reel runs round without a visible end
        v = meta["LOOP"].strip().lower()
        if v in ON_WORDS:
            scene = apply_loop(scene)
        elif v not in OFF_WORDS:
            warnings.append("LOOP %r: on ya off likho" % meta["LOOP"])
    if meta.get("MASCOT"):                              # MASCOT: bhoot | billi | chooha: the hidden easter egg
        v = meta["MASCOT"].strip().lower()
        if mascot_kind(v):
            scene["mascot"] = {"kind": mascot_kind(v)}
        elif v not in OFF_WORDS:
            warnings.append("MASCOT %r: bhoot, billi, chooha ya off likho" % meta["MASCOT"])
    if len([n for n in cast if n != "NARRATOR"]) > 4:
        warnings.append("more than 4 characters: the screen gets crowded")
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

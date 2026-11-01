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
- `SCENE: background | title` starts a new place (kitchen, room, street, school, night_road, plain).
- `wait 1.5` (or `...`) pauses.
"""
import argparse
import os
import re

from . import actions, audio
from .characters import ACCESSORIES, EXPRESSIONS, HAIR_COLORS, HAIR_STYLES, LOOKS, OUTFITS, PALETTE, SKIN_TONES
from .scene import SLOTS

HEADERS = ("HOOK", "CAST", "SCENE", "CTA", "CAPTION", "HASHTAGS", "MUSIC", "TRANSITION")
BACKGROUNDS = ("kitchen", "room", "street", "school", "night_road", "plain")
PROPS = ("spoon", "phone", "mic", "cup", "ball", "stick")
SFX = ("pop", "boing", "whoosh", "ding", "thud", "clap", "beep", "laugh_track")
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
        if w in ("enter", "exit") and nxt in ("left", "right"):
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


def parse_script(text):
    """Return (scene dict, warnings)."""
    meta = {}
    cast = {}
    scenes = []
    warnings = []
    cur = None

    def new_scene(bg="room", title=None):
        sc = {"background": {"type": bg}, "lines": [], "title": title}
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
                bg, _, title = val.partition("|")
                bg = bg.strip().lower().replace(" ", "_") or "room"
                if bg not in BACKGROUNDS:
                    warnings.append("unknown place %r -> using room" % bg)
                    bg = "room"
                cur = new_scene(bg, title.strip() or None)
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
            cur["lines"].append(("say", m.group(1), _words(bracket), say.strip(), speak.strip(), line))
            continue
        warnings.append("line not understood: %r" % line[:60])

    if not scenes:
        raise ValueError("script has no lines")

    # ---- build timelines ----
    out_scenes = []
    for si, sc in enumerate(scenes):
        order = []
        for ln in sc["lines"]:
            if ln[0] in ("do", "say") and ln[1].upper() != "ALL" and ln[1] not in order:
                order.append(ln[1])
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
                if len(order) == 2 and others:
                    ev.setdefault("look", others[0])
            elif "action" not in ev and "move" not in ev and "expression" not in ev:
                ev.setdefault("hold", 0.6)
            tl.append(ev)
            first = False
        last = {"hold": 1.0}
        if si == len(scenes) - 1 and meta.get("CTA"):
            last = {"hold": 2.0, "sfx": "pop", "volume": 0.5,
                    "overlay": {"text": meta["CTA"], "style": "card", "pos": [540, 640], "color": [236, 90, 70]}}
        tl.append(last)
        item = {"background": sc["background"], "cast": order, "characters": chars, "timeline": tl}
        if sc["title"]:
            item["title"] = sc["title"]
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
    if len(cast) > 3:
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

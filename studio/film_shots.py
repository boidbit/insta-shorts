"""A conversation directed like a film (`CAMERA: film`, the default of the new camera).

The plain camera looks at the place from one spot and zooms; in its close-ups a person turns to the lens and seems
to talk to us. A film cuts instead, and the camera goes to the person, who keeps looking at the one they talk to:

- the opening: wide, everybody in the place (the plain camera, which also takes any walk, fall or ride);
- over the shoulder (OTS): the listener's back big in a near corner, the speaker three-quarter towards them;
- a clean single: the speaker alone, three-quarter, looking across the frame at the one they talk to, room in
  front of the face, the place behind out of focus;
- the reverse angle: shots onto the person on the right see the other side of the place (the background mirrored
  and blurred), so the cut reads as the camera moving round;
- the 180 degree rule: whoever stands left looks right in every shot, and the other way round;
- a reaction shot: somebody's silent reaction (shock, facepalm, a double take...) gets their own single;
- low angle for swagger (smug, proud, evil, determined), high angle for the small and scared (scared, sad, cry...);
- an insert: a line about what the speaker holds (phone, injection, chai...) opens on it, close, for a moment;
- the punch line: a single that slowly pushes in.

Every shot is a fixed camera with people moved / turned / hidden (Char.ov), the same mechanism as the counter
conversation (studio.counter_shots), which keeps its own shots where there is a counter."""

HEAD_FROM_FEET = 704.0      # a person of scale 1: from the feet up to the middle of the head
HEAD_R = 103.0
OPEN = 1.6                  # seconds the opening wide shot holds the first line before the first cut
MIN_SHOT = 0.6              # a shot shorter than this is merged into the one before
LOW = {"swag", "smug", "proud", "evil", "determined", "angry_proud"}
HIGH = {"scared", "nervous", "cry", "sad", "hurt", "embarrassed"}
REACT = {"shock", "facepalm", "double_take", "laugh", "rofl", "cry", "eye_roll", "ghoorna", "slow_clap", "scared",
         "cringe", "shrug", "head_shake", "shake_head", "think", "scratch_head", "nod", "shy", "sulk", "proud",
         "kaan_pakad", "collar_up", "mic_drop"}
WIDE = {"fall", "faint", "trip", "slip", "skid", "jump", "dance", "dance2", "dance3", "naagin", "bhangra", "run",
        "cartwheel", "spin", "push", "kick", "slap", "punch", "hug", "throw", "lie_down", "sleep", "sit"}
INSERT = {"phone": ("phone", "fone", "mobile", "call", "message", "whatsapp"),
          "injection": ("injection", "injekshan", "sui", "teeka"),
          "chai": ("chai", "chay", "tea"), "cup": ("chai", "coffee", "cup"),
          "money": ("paise", "paisa", "rupaye", "rupees", "note", "hafta", "₹"),
          "letter": ("letter", "chitthi", "khat"), "report_card": ("report", "result", "marks", "number"),
          "vlog_cam": ("live", "camera", "video", "reel", "vlog", "content"),
          "samosa": ("samosa",), "mithai": ("mithai", "laddoo", "laddu"), "plate": ("plate", "golgappe", "chaat")}


def _head(c, t):
    x, y = c.draw_pos(t)
    k = c.draw_scale(t)
    if c.spec.get("kind"):                          # an animal: the camera looks where its head is
        fx, fy = c.focus_at(t)
        return fx, fy, k
    return x, y - HEAD_FROM_FEET * k, k


def _moving(c, t0, t1):
    return any(m[0] < t1 and m[1] > t0 and (m[2] != m[4] or m[3] != m[5]) for m in c.moves) or bool(c.rides)


def _on_stage(c):
    return not c.spec.get("hidden") and c.spec.get("view") != "back"


def plan_shots(plan, own_camera=False, style="film"):
    """[{t0, t1, kind, cam, ov, ...}] for a conversation of two or three people, or [] (the plain camera)."""
    if getattr(plan, "camera", "") != "cine" or style != "film" or own_camera or plan.framing != "medium":
        return []
    if getattr(plan, "counter_shots", None):        # a counter conversation keeps its own shots
        return []
    chars = plan.chars
    people = [c for c in chars.values() if _on_stage(c)]
    if not 2 <= len(people) <= 3 or any(c.rides for c in people):
        return []
    speech = sorted((sp for sp in plan.speech if sp.get("who") in chars and _on_stage(chars[sp["who"]])),
                    key=lambda sp: sp["start"])
    if len(speech) < 2 or len({sp["who"] for sp in speech}) < 2:
        return []
    open_end = min(plan.duration, max(1.6, speech[0]["start"] + OPEN))
    cuts = [(0.0, "free", None, None)]
    turns, last_other = {}, {}
    for i, sp in enumerate(speech):
        who = sp["who"]
        c = chars[who]
        prev = next((s_["who"] for s_ in reversed(speech[:i]) if s_["who"] != who), None)
        nxt = next((s_["who"] for s_ in speech[i + 1:] if s_["who"] != who), None)
        other = prev or nxt or last_other.get(who)
        if other is None:
            other = min((p.name for p in people if p is not c), key=lambda n: abs(chars[n].x - c.x))
        last_other[who] = other
        t0 = max(sp["start"] - 0.04, open_end)
        if t0 >= plan.duration - 0.2:
            continue
        st = c.state_at(sp["start"] + 0.05)
        expr, act = st.get("expression"), st.get("action")
        lst = chars[other]
        if act in WIDE or _moving(c, sp["start"], sp["end"]) or _moving(lst, sp["start"], sp["end"]):
            kind = "free"
        elif i == len(speech) - 1:
            kind = "punch"
        elif expr in LOW:
            kind = "low"
        elif expr in HIGH:
            kind = "high"
        else:
            n = turns.get(who, 0)
            turns[who] = n + 1
            animal = c.spec.get("kind") or lst.spec.get("kind")
            kind = "single" if (animal or n % 2 == 1) else "ots"
        prop = st.get("prop")
        words = INSERT.get(prop or "", ())
        text = str(sp.get("text", "")).lower()
        if kind not in ("free", "punch") and words and any(w in text for w in words) and sp["end"] - sp["start"] > 1.6:
            cuts.append((t0, "insert", who, other))
            t0 = t0 + 0.9
        cuts.append((t0, kind, who, other))
    # silent reactions between the lines: the one who reacts gets a single
    for c in people:
        for e in c.events:
            a = e.get("action")
            if a in REACT and "say" not in e and open_end < e["t"] < plan.duration - 0.3 \
                    and not any(sp["start"] - 0.05 <= e["t"] < sp["end"] for sp in speech):
                other = last_other.get(c.name) or next((p.name for p in people if p is not c), None)
                cuts.append((e["t"], "react", c.name, other))
            elif a in WIDE and e["t"] > open_end and not any(sp["start"] <= e["t"] < sp["end"] for sp in speech):
                cuts.append((e["t"], "free", c.name, None))
    cuts.sort(key=lambda x: x[0])
    merged = []
    for cut in cuts:
        if merged and merged[-1][1:3] == cut[1:3]:
            continue
        short = MIN_SHOT if merged and merged[-1][1] != "react" else 0.3     # a reaction may be quick
        if merged and cut[0] - merged[-1][0] < short and merged[-1][1] != "free" or \
                (merged and cut[0] - merged[-1][0] < 0.05):
            merged[-1] = (merged[-1][0],) + cut[1:]
            continue
        merged.append(cut)
    shots = []
    for i, (t0, kind, who, other) in enumerate(merged):
        t1 = merged[i + 1][0] if i + 1 < len(merged) else plan.duration + 1.0
        if t1 - t0 < 0.05:
            continue
        if kind == "free" or who is None or other is None:
            shots.append(dict(t0=t0, t1=t1, kind="free"))
            continue
        mid = min(t1, plan.duration) * 0.5 + t0 * 0.5
        shots.append(_shot(kind, t0, t1, mid, chars[who], chars[other], people, plan))
    return shots if any(s["kind"] != "free" for s in shots) else []


def _shot(kind, t0, t1, t, c, lst, people, plan):
    sx, sy, sk = _head(c, t)
    lx = lst.draw_pos(t)[0]
    side = 1.0 if lx >= c.draw_pos(t)[0] else -1.0     # where the listener is, seen from the speaker
    face = "right" if side > 0 else "left"
    right_one = side < 0                               # the speaker is the one on the right: the reverse angle
    ov, hide = {}, [p.name for p in people if p is not c]
    look = dict(facing=face, look_x=side * 0.9)
    if c.spec.get("kind"):
        look["view"] = "turn"                          # a dog: the body side on, the head turned
    else:
        look.update(view="front", turn34=1.0)         # three-quarter: the face turned well towards the listener
    ov[c.name] = look
    extra = dict(blur=True, mirror=right_one, soft=True)
    if kind == "ots" and not lst.spec.get("kind"):
        z = min(2.0, max(1.35, 1920.0 * 0.40 / (0.55 * 807.0 * sk)))
        vw, vh = 1080.0 / z, 1920.0 / z
        cx = sx + side * vw * 0.14                     # the speaker a little to the side, the shoulder in the other corner
        cy = sy + vh * 0.14
        k = vh * 0.15 / HEAD_R                         # the back of the listener's head and shoulder in the near corner
        hx, hy = cx + side * vw * 0.38, cy + vh * 0.25
        ov[lst.name] = dict(view="back", x=hx, y=hy + HEAD_FROM_FEET * k, k=k)
        hide = [p.name for p in people if p is not c and p is not lst]
        cam = (z, cx, cy)
    elif kind == "insert":                             # what they hold, close: the camera finds the hand when drawing
        cam = (2.6, sx, sy + 330.0 * sk)
        extra["insert"] = c.name
    else:
        z = {"single": 1.55, "punch": 1.45, "react": 1.6, "low": 1.45, "high": 1.5}.get(kind, 1.5)
        animal = bool(c.spec.get("kind"))
        if animal:                                     # a dog is a third of a person: closer, framed on its body
            z = min(2.4, z + 0.55)
        vw, vh = 1080.0 / z, 1920.0 / z
        cx = sx + side * vw * 0.16                     # room in front of the face, towards the one they look at
        cy = sy + vh * (0.02 if animal else 0.16)
        if kind == "low":                              # from below: the head near the top, big, the floor gone
            cy = sy + vh * (0.14 if animal else 0.30)
            ov[c.name]["k"] = c.draw_scale(t) * 1.08
            ov[c.name]["x"], ov[c.name]["y"] = c.draw_pos(t)
            extra["angle"] = "low"
        elif kind == "high":                           # from above: small in the frame, the floor around them
            cy = sy + vh * 0.02
            extra["angle"] = "high"
        cam = (z, cx, cy)
        if kind == "punch":                            # the punch line: a slow push in
            z1 = z + 0.35
            extra["cam1"] = (z1, sx + side * (1080.0 / z1) * 0.12, sy + (1920.0 / z1) * 0.14)
    for n in hide:
        ov.setdefault(n, {})["hidden"] = True
    shot = dict(t0=t0, t1=t1, kind=kind, cam=cam, ov=ov, side=side)
    shot.update(extra)
    return shot

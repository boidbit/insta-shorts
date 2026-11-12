"""A conversation across a counter, directed like a film (new camera only).

Seen straight from the front, a customer who talks to the shopkeeper behind a counter seems to talk to us. So such a
scene is cut into shots:

- the opening (wide): the customer's back to us, facing the counter, the shopkeeper behind it facing us;
- the shopkeeper speaks: over the customer's shoulder (the back of the customer's head big in a near corner);
- the customer speaks: the reverse shot, from the counter's side: the customer faces us, which is now natural (we are
  where the shopkeeper is), the place behind them out of focus, the edge of the counter blurred in front;
- now and then, when the shopkeeper is near (a thela, a shop counter): a two-shot from the side, the customer turned
  to the shopkeeper (side view), the shopkeeper's head and eyes turned to the customer.

Every person keeps looking at the one they talk to. The renderer applies a shot: a fixed camera, people moved /
turned / hidden for its duration (Char.ov), the place blurred and the counter edge in front for a reverse shot."""

import re

# a line said to the audience (a vlogger to his camera): that one looks at us, every other line at the seller
AUDIENCE = re.compile(r"\b(dosto|doston|dost log|guys|friends|viewers|subscribe|subscriber|followers|"
                      r"like karo|like kar do|comment karo|share karo)\b", re.I)
HEAD_FROM_FEET = 704.0      # a person of scale 1: from the feet up to the middle of the head
HEAD_R = 103.0              # ... and the head's radius
OPEN = 1.4                  # seconds the opening wide shot holds the first line before the first cut


def _head(c, t):
    x, y = c.draw_pos(t)
    k = c.draw_scale(t)
    return x, y - HEAD_FROM_FEET * k, k


def _moving(c, t0, t1):
    return any(m[0] < t1 and m[1] > t0 and (m[2] != m[4] or m[3] != m[5]) for m in c.moves)


def plan_shots(plan, own_camera=False):
    """[{t0, t1, kind, cam, ov, hide, ...}] for a counter conversation, or [] (the normal camera)."""
    if getattr(plan, "camera", "") != "cine" or plan.framing != "medium" or own_camera:
        return []
    chars = plan.chars
    sellers = [c for c in chars.values() if getattr(c, "behind", None) is not None and not c.spec.get("hidden")]
    if not sellers:
        return []
    seller = sellers[0]
    fronts = [c for c in chars.values() if c not in sellers and not c.spec.get("hidden") and not c.spec.get("kind")
              and c.spec.get("view") != "back" and not c.rides]
    speech = sorted((sp for sp in plan.speech if sp.get("who") in chars and not chars[sp["who"]].spec.get("hidden")),
                    key=lambda sp: sp["start"])
    talkers = [sp["who"] for sp in speech]
    customers = [c for c in fronts if c.name in talkers]
    if not customers or seller.name not in talkers:
        return []
    main = customers[0]
    near_seller = not isinstance(seller.behind, dict) or seller.draw_scale(5.0) >= 0.6 * main.draw_scale(5.0)
    obj = seller.behind if not isinstance(seller.behind, dict) else None

    # the cuts: the opening, then a shot for every change of speaker
    first = speech[0]["start"]
    open_end = min(plan.duration, max(1.6, first + OPEN))
    opener = speech[0]
    if chars[opener["who"]] in fronts and AUDIENCE.search(str(opener.get("text", ""))):
        cuts = [(0.0, "vlog", opener["who"])]       # a vlogger opens to his camera: that is the first shot
    else:
        cuts = [(0.0, "open", None)]
    turns = {}
    for sp in speech:
        t0 = max(sp["start"] - 0.04, open_end)
        if t0 >= plan.duration - 0.2:
            continue
        who = sp["who"]
        if who == seller.name:
            kind = "ots"
        elif chars[who] in fronts and AUDIENCE.search(str(sp.get("text", ""))):
            kind = "vlog"                           # said to the audience (his own camera): he looks at us
        elif chars[who] in fronts:
            n = turns.get(who, 0)
            turns[who] = n + 1
            kind = "profile" if (near_seller and n % 2 == 1) else "reverse"
        else:
            kind = "open"
        if cuts and cuts[-1][1] == kind and cuts[-1][2] == who:
            continue
        if cuts and t0 - cuts[-1][0] < 0.5:          # a very quick change: no cut for a blink-long shot
            if cuts[-1][1] == "open":
                continue
            cuts[-1] = (cuts[-1][0], kind, who)
            continue
        cuts.append((t0, kind, who))
    shots = []
    for i, (t0, kind, who) in enumerate(cuts):
        t1 = cuts[i + 1][0] if i + 1 < len(cuts) else plan.duration + 1.0
        if t1 - t0 < 0.05:
            continue
        mid = min(t1, plan.duration) * 0.5 + t0 * 0.5
        talker = chars.get(who) if who else main
        if kind not in ("open", "vlog") and any(_moving(c, t0, t1) for c in [seller] + fronts):
            shots.append(dict(t0=t0, t1=t1, kind="free"))           # somebody walks: the normal camera
            continue
        shots.append(_shot(kind, t0, t1, mid, seller, talker if talker in fronts else main, fronts, obj))
    return shots


def _side(a, b):
    """-1 when a stands left of b, else 1."""
    return -1.0 if a.x <= b.x else 1.0


def _shot(kind, t0, t1, t, seller, cust, fronts, obj):
    sx, sy, sk = _head(seller, t)
    cx_, cy_, ck = _head(cust, t)
    side = _side(cust, seller)                     # where the customer is, seen from the counter
    face_seller = "right" if side < 0 else "left"
    ov, hide, extra = {}, [], {}
    if kind == "vlog":                             # to his own camera: the vlogger faces us, the stall behind him
        ov[cust.name] = dict(view="front", facing="front", look_x=0.0)
        ov[seller.name] = dict(facing="left" if side < 0 else "right", look_x=side * 0.8)
        z = 1.12                                   # wide enough for the stall and its seller behind him
        cam = (z, cx_ + (sx - cx_) * 0.5, min(cy_, sy) + 1920.0 / z * 0.18)
        hide = [c.name for c in fronts if c is not cust]
    elif kind == "open":                           # wide: the customers' backs to us, the seller facing us
        for c in fronts:
            ov[c.name] = dict(view="back")
        ov[seller.name] = dict(facing="front", look_x=-side * 0.8)
        cam = (1.0, 540.0, 960.0)
    elif kind == "ots":                            # over the customer's shoulder onto the seller
        z = min(2.0, max(1.3, 1920.0 * 0.40 / (0.55 * 807.0 * sk)))
        vw, vh = 1080.0 / z, 1920.0 / z
        cx = sx + side * vw * 0.14                 # the seller a little to the side, the shoulder in the other corner
        cy = sy + vh * 0.14
        k = vh * 0.20 / HEAD_R                     # the back of the head big in the near corner
        hx, hy = cx + side * vw * 0.34, cy + vh * 0.30
        ov[cust.name] = dict(view="back", x=hx, y=hy + HEAD_FROM_FEET * k, k=k)
        ov[seller.name] = dict(facing="front", look_x=side * 0.7)
        hide = [c.name for c in fronts if c is not cust]
        cam = (z, cx, cy)
    elif kind == "reverse":                        # from the counter's side: the customer faces us
        z = min(1.8, max(1.3, 1920.0 * 0.40 / (0.55 * 807.0 * ck)))
        vw, vh = 1080.0 / z, 1920.0 / z
        cam = (z, cx_ - side * vw * 0.12, cy_ + vh * 0.12)
        ov[cust.name] = dict(view="front", facing=face_seller, look_x=-side * 0.9)
        hide = [seller.name] + [c.name for c in fronts if c is not cust]
        extra = dict(blur=True, edge=True, hide_objects=[obj.kind] if obj is not None else [], no_floor=True)
    else:                                          # profile two-shot: the customer turned to the seller
        x = cust.draw_pos(t)[0]                    # where they stand (the same in every shot)
        ov[cust.name] = dict(view="side", facing=face_seller, x=x, y=cust.draw_pos(t)[1], k=ck)
        ov[seller.name] = dict(facing="left" if side < 0 else "right", look_x=side * 0.8)
        hide = [c.name for c in fronts if c is not cust]
        z = 1.25
        cam = (z, (sx + x) / 2.0, min(sy, cy_) + 1920.0 / z * 0.18)
    for n in hide:
        ov.setdefault(n, {})["hidden"] = True
    shot = dict(t0=t0, t1=t1, kind=kind, cam=cam, ov=ov, side=side)
    shot.update(extra)
    return shot

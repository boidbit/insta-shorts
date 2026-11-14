"""Counters: things a person stands BEHIND, so that the customer stands in front, like in real life: a thela, a shop
counter (`OBJ: counter mithai`), a table, and the counters painted into the places (the chai stall, the kirana
counter, the bank counter, the hospital reception, the judge's bench, the canteen counter, the police desk, the
market stalls).

Who stands behind: the seller / shopkeeper of the place by himself (kulchewala behind his thela, chaiwala behind the
chai stall, the judge behind the bench, ...), or anybody the script sends there (`CAST: X = boy peeche`). `aage`
keeps somebody in front. The counter is drawn over the person's legs; a person behind a painted counter is as far
away (and as big) as the counter in the picture. New camera only: `CAMERA: classic` draws everybody as before."""
import math

from . import objects

H1 = 807.0              # a character of scale 1 is this tall (logical px)
PERSON_M = 1.7          # ... and that is 1.7 m
INFLATE = 1.08          # people are drawn a little bigger than the painted place (but must still fit the counter)

SELLERS = ("kulchewala", "thelewala", "sabziwala", "chaiwala", "dukaandaar", "halwai", "chemist")
SHOP_ROLES = ("shopkeeper", "dukandar", "dukaandar", "lala", "lalaji", "kiranawala", "mithaiwala", "mobilewala",
              "medicalwala", "pharmacist")
# who goes behind an OBJ counter by himself
OBJ_WHO = {"thela": dict(looks=("kulchewala", "thelewala", "sabziwala", "chaiwala", "halwai"), roles=()),
           "counter": dict(looks=SELLERS, roles=SHOP_ROLES), "table": dict(looks=(), roles=()),
           # a desk (OBJ: desk): the people who work at one sit behind it by themselves
           "desk": dict(looks=("clerk", "boss", "principal", "judge", "doctor", "master_ji", "office_guy"),
                        roles=("babu", "cashier", "munshi", "receptionist", "manager", "headmaster", "teacher"))}
DESK_SETS = ("desk", "table")
BEHIND_OBJ = (0.95, -55.0)      # (size, feet offset): one step behind the cart / the counter

# The counters painted into the places. shapes = the counter's front (logical px of the picture): it is drawn again
# over whoever stands behind it. x, y = where that person stands (feet); px / m = the counter's height in the picture
# and in real life (how big a person is there).
R, RR, P = "rect", "rrect", "poly"


def _glasses(x0, n, step, y0=950, y1=990):
    return [(P, [(x, y0), (x + 30, y0), (x + 26, y1), (x + 4, y1)]) for x in (x0 + i * step for i in range(n))]


PLACES = {
    "chai_tapri": [dict(shapes=[(R, 100, 990, 750, 1300), (R, 170, 940, 330, 990), (RR, 190, 850, 300, 945, 20)]
                        + _glasses(420, 6, 48),
                        x=560, y=1296, px=310, m=1.0, looks=("chaiwala", "thelewala"), roles=("chaiwale",))],
    "kirana": [dict(shapes=[(R, 100, 1060, 980, 1300), (R, 820, 960, 940, 1060)]
                    + [(RR, x, 970, x + 90, 1062, 14) for x in (200, 370, 540, 710)]
                    + [(R, x + 10, 950, x + 80, 972) for x in (200, 370, 540, 710)],
                    x=670, y=1296, px=240, m=0.95, looks=("dukaandaar", "sabziwala", "halwai"), roles=SHOP_ROLES)],
    "bank": [dict(shapes=[(R, 20, 880, 1060, 1100)], x=200, y=1096, px=220, m=1.05, looks=("clerk",),
                  roles=("cashier", "babu", "clerk"))],
    "hospital": [dict(shapes=[(RR, 300, 990, 780, 1080, 12), (R, 320, 1080, 760, 1280), (R, 380, 940, 460, 990)],
                      x=600, y=1276, px=290, m=1.05, looks=(), roles=("receptionist",))],
    "court": [dict(shapes=[(R, 260, 500, 820, 900)], x=540, y=896, px=400, m=1.3, looks=("judge",),
                   roles=("judge_sahab", "jaj")),
              dict(shapes=[(R, 40, 700, 220, 1100)], x=130, y=1096, px=400, m=1.15, looks=(),
                   roles=("gawah", "witness")),
              dict(shapes=[(R, 860, 960, 1060, 1100)], x=960, y=1096, px=140, m=0.75, looks=("clerk",),
                   roles=("munshi",))],
    "canteen": [dict(shapes=[(R, 640, 800, 1080, 1280)], x=870, y=1276, px=480, m=1.05,
                     looks=("chaiwala", "thelewala", "halwai", "kulchewala"), roles=("canteenwala",))],
    "police_station": [dict(shapes=[(R, 60, 1000, 560, 1280), (R, 140, 940, 300, 1000)], x=330, y=1276, px=280,
                            m=0.8, looks=("police",), roles=("thanedaar", "inspector", "daroga"))],
    "market": [dict(shapes=[(RR, x + 8, 1150, x + 312, 1300, 14)]
                    + [("circle", x + 40 + j * 58, 1128, 28) for j in range(5)],
                    x=x + 160, y=1296, px=150, m=0.8, looks=("sabziwala", "thelewala", "dukaandaar", "kulchewala"),
                    roles=("phalwala", "fruitwala") + SHOP_ROLES) for x in (20, 380, 740)],
}
COUNTER_PLACES = tuple(PLACES)
LW_HALF = 540.0
# 2.5D: chai_tapri and kirana are the hand-made gali set, whose chai counter is already a piece the people are
# depth-sorted with (style25d.scenery_gali._tapri): only where the person stands there (no shapes to cut out).
_TAPRI = dict(x=990, y=1290, px=235, m=1.0)
PRESET_PLACES = {
    "chai_tapri": [dict(_TAPRI, looks=PLACES["chai_tapri"][0]["looks"], roles=PLACES["chai_tapri"][0]["roles"])],
    "kirana": [dict(_TAPRI, looks=PLACES["kirana"][0]["looks"], roles=PLACES["kirana"][0]["roles"])],
    # the hand-made bazaar (style25d.scenery_road.market_25d): three stalls whose counters are depth-sorted pieces
    "market": [dict(x=x + 160, y=1296, px=150, m=0.8, looks=PLACES["market"][0]["looks"],
                    roles=PLACES["market"][0]["roles"]) for x in (20, 380, 740)],
}
# the hand-made hospital, bank, police station, court and canteen (style25d.scenery_civic) keep their counters where
# the 2D picture has them, as pieces the people are depth-sorted with: only where the person stands
PRESET_PLACES.update({p: [{k: v for k, v in c.items() if k != "shapes"} for c in PLACES[p]]
                      for p in ("hospital", "bank", "police_station", "court", "canteen")})


def painted(place, mode):
    """The painted counters of a place drawn in this mode: "2d" / "auto" (the place's own drawing, flat or split into
    2.5D layers) or "preset" (a hand-made 2.5D set)."""
    if mode == "preset":
        return PRESET_PLACES.get(place, [])
    return PLACES.get(place, []) if mode in ("2d", "auto") else []


def person_scale(c):
    """How big a person stands at this painted counter (character scale)."""
    return PERSON_M * c["px"] / float(c["m"]) / H1 * INFLATE


def frame_point(x, y, angle):
    """A point of the painted place -> where it is in this shot (angle zoom / side / mirror), logical px."""
    z = float(angle.get("zoom", 1.0)) if angle else 1.0
    if z > 1.001:
        ax = float(angle.get("x", 540.0))
        left = min(max(ax * z - 540.0, 0.0), 1080.0 * z - 1080.0)
        x, y = x * z - left, 1700.0 + (y - 1700.0) * z
    if angle and angle.get("mirror"):
        x = 1080.0 - x
    return x, y


def _wants(spec, who):
    return spec.get("look") in who.get("looks", ()) or spec.get("role") in who.get("roles", ())


def place_behind(plan, place, cine, mode="2d", mirror=True):
    """Put the seller / shopkeeper / judge (or whoever the script sent `peeche`) behind the counters of this shot.
    plan: the compiled shot (chars, objects, angle, world). mode: how the place is drawn ("2d", "auto" 2.5D layers,
    "preset" hand-made 2.5D set, None = no painted counters). mirror: the set is mirrored for a reverse shot (a 2.5D
    set with writing on it is not). Returns the painted counters in use (indices into painted(place, mode))."""
    angle = dict(plan.angle or {}, mirror=bool(mirror and (plan.angle or {}).get("mirror")))
    if not cine or plan.framing in ("inside", "wide"):   # (over the shoulder: the seller is still behind it)
        return []
    people = [c for c in plan.chars.values() if not c.spec.get("hidden") and not c.spec.get("kind")
              and c.spec.get("behind") is not False and not c.spec.get("view") == "back" and not c.rides]
    taken, used = set(), []
    spots = []                                      # (kind, ref, x) of every counter in this shot
    for o in plan.objects.values():
        base = "thela" if o.kind in objects.THELAS else ("counter" if o.kind in objects.SHOP_COUNTERS else
                                                         ("table" if o.kind == "table" else None))
        if base:
            spots.append(("obj", o, OBJ_WHO[base], o.rest))
    for ob in getattr(plan, "sets", None) or []:     # a desk / table piece of furniture (`OBJ: desk center`)
        if ob.get("type") in DESK_SETS:
            spots.append(("set", ob, OBJ_WHO["desk"] if ob["type"] == "desk" else OBJ_WHO["table"],
                          float(ob.get("x", 540))))
    for i, c in enumerate(painted(place, mode)):
        spots.append(("paint", i, c, frame_point(c["x"], c["y"], angle)[0]))
    if not spots:
        return []

    def assign(c, spot):
        kind, ref, info, x = spot
        taken.add(c.name)
        if kind == "obj":
            _behind_object(c, ref)
        elif kind == "set":
            _behind_desk(c, ref)
        else:
            _behind_painted(c, info, plan, angle)
            used.append(ref)

    free = list(spots)
    for c in sorted(people, key=lambda c_: c_.x):   # sent there by the script: the nearest free counter
        if c.spec.get("behind") is True and free and not _walks(c):
            spot = min(free, key=lambda sp: abs(sp[3] - c.x))
            free.remove(spot)
            assign(c, spot)
    for spot in list(free):                         # the place's own people go behind by themselves
        who = next((c for c in people if c.name not in taken and _wants(c.spec, spot[2]) and not _walks(c)), None)
        if who is not None:
            free.remove(spot)
            assign(who, spot)
    _by_the_cart(plan, taken, spots)
    _make_room(plan, taken)
    return used


def _by_the_cart(plan, behind, spots):
    """A customer stands at the open end of a parked thela (not in the middle of the road, not in front of the
    seller): the same place in every shot, so nobody jumps when the camera cuts."""
    cart = next((sp[1] for sp in spots if sp[0] == "obj" and sp[1].kind in objects.THELAS), None)
    if cart is None or not behind:
        return
    side = -1.0 if cart.rest >= LW_HALF else 1.0
    half = objects.SPRITE_LEN.get(cart.kind, 560) * 0.5 * cart.scale * 0.78
    front = sorted((c for c in plan.chars.values() if c.name not in behind and not c.spec.get("hidden")
                    and not c.spec.get("kind") and c.spec.get("view") != "back" and not _walks(c)),
                   key=lambda c_: c_.x * -side)
    for i, c in enumerate(front):
        c.x = min(max(cart.rest + side * (half + 40.0 + 230.0 * i), 110.0), 970.0)


def _walks(c):
    """Somebody the script walks / brings in (they keep their own way)."""
    return any(m[2] != m[4] for m in c.moves)


def _make_room(plan, behind):
    """Nobody stands right in front of the person behind the counter: a customer there steps a little aside."""
    backs = [getattr(plan.chars[n], "behind_x", plan.chars[n].x) for n in behind]
    gap = 380.0 * plan.world / 1.22                 # a person's width and a bit (bigger people need more room)
    for c in plan.chars.values():
        if c.name in behind or c.spec.get("hidden") or _walks(c) or c.spec.get("view") == "back":
            continue
        if all(abs(c.x - bx) >= gap for bx in backs):
            continue
        spots = [110.0 + 10.0 * i for i in range(87)]                  # 110..970: the nearest place in the clear
        clear = [x for x in spots if all(abs(x - bx) >= gap for bx in backs)]
        c.x = min(clear, key=lambda x: abs(x - c.x)) if clear else \
            max(spots, key=lambda x: min(abs(x - bx) for bx in backs))


def _behind_desk(c, ob):
    """Behind a desk / table: in the middle of it, one step back, so the desk covers the legs (a babu at work)."""
    k, dy = BEHIND_OBJ
    dy = (float(ob.get("y", 1700)) + dy + 10.0) - c.y
    c.x = float(ob.get("x", 540))
    c.depth.append((0.0, k, dy, k, dy, 0.01))
    c.depth.sort(key=lambda d: d[0])
    c.behind_x = c.x


def _behind_object(c, o):
    """Behind a thela / counter / table. A cart that is pushed in: its seller pushes it (at the handle), then steps
    round behind it."""
    k, dy = BEHIND_OBJ
    k *= getattr(o, "depth_k", 1.0)                 # a cart parked a step back: its seller as far back as it
    dy = (o.y + dy + 20.0) - c.y                    # just behind the cart, whatever line the shot puts people on
    half = objects.SPRITE_LEN.get(o.kind, 440) * 0.5 * o.scale * 0.9
    variant = "sabzi" if o.kind == "thela" else o.kind[6:] if o.kind.startswith("thela_") else None
    flipped = bool(o.flips and o.flips[-1][1])
    spot = objects.THELA_SPOT.get(variant, 0) * o.scale * (-1.0 if flipped else 1.0)   # where the things are low
    entering = o.moves and o.moves[0][2] in objects.OFFSCREEN.values()
    if entering and not c.moves:
        t0, t1, xa, xb = o.moves[0][:4]
        side = -1.0 if xb > xa else 1.0             # the handle is at the back, the side it comes from
        c.x = xa + side * half
        c.moves.append((t0, t1, xa + side * half, c.y, xb + side * half, c.y))
        c.moves.append((t1 + 0.1, t1 + 0.7, xb + side * half, c.y, xb + spot, c.y))
        c.depth.append((t1 + 0.1, 1.0, 0.0, k, dy, 0.6))
    else:
        c.x = o.rest + spot
        c.depth.append((0.0, k, dy, k, dy, 0.01))
    c.depth.sort(key=lambda d: d[0])
    c.behind, c.behind_x = o, o.rest + spot
    o.depth_sort = True                             # drawn among the people by depth (over the one behind it)


def _behind_painted(c, info, plan, angle):
    x, y = frame_point(info["x"], info["y"], angle)
    z = float(angle.get("zoom", 1.0))
    k = person_scale(info) * z / max(plan.world, 1e-3)
    c.x = x
    c.depth.append((0.0, k, y - c.y, k, y - c.y, 0.01))
    c.depth.sort(key=lambda d: d[0])
    c.behind, c.behind_x = info, x


def counter_overlays(place, used, static, s):
    """[(depth y, RGBA picture, x, y)]: the front of each painted counter in use, cut out of the place's own picture
    (so it matches it exactly), to be drawn over whoever stands behind it. static: the place's picture at scale s
    (2D: the flat place; 2.5D: its "set" layer, the one the people stand in)."""
    from PIL import Image, ImageDraw
    out = []
    for i in used:
        c = PLACES[place][i]
        xs, ys = [], []
        for sh in c["shapes"]:
            if sh[0] == P:
                xs += [p[0] for p in sh[1]]
                ys += [p[1] for p in sh[1]]
            elif sh[0] == "circle":
                xs += [sh[1] - sh[3], sh[1] + sh[3]]
                ys += [sh[2] - sh[3], sh[2] + sh[3]]
            else:
                xs += [sh[1], sh[3]]
                ys += [sh[2], sh[4]]
        x0, y0 = int(math.floor(min(xs) * s)) - 3, int(math.floor(min(ys) * s)) - 3
        x1, y1 = int(math.ceil(max(xs) * s)) + 3, int(math.ceil(max(ys) * s)) + 3
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, static.width), min(y1, static.height)
        mask = Image.new("L", (x1 - x0, y1 - y0), 0)
        d = ImageDraw.Draw(mask)
        pad = 3 * s                                 # the outline (ink) of the painted counter too
        for sh in c["shapes"]:
            if sh[0] == P:
                d.polygon([(px * s - x0, py * s - y0) for px, py in sh[1]], fill=255, outline=255,
                          width=max(1, int(pad * 2)))
            elif sh[0] == "circle":
                r = sh[3] * s + pad
                d.ellipse([sh[1] * s - x0 - r, sh[2] * s - y0 - r, sh[1] * s - x0 + r, sh[2] * s - y0 + r], fill=255)
            else:
                box = [sh[1] * s - x0 - pad, sh[2] * s - y0 - pad, sh[3] * s - x0 + pad, sh[4] * s - y0 + pad]
                if sh[0] == RR:
                    d.rounded_rectangle(box, radius=sh[5] * s, fill=255)
                else:
                    d.rectangle(box, fill=255)
        piece = static.crop((x0, y0, x1, y1)).convert("RGBA")
        piece.putalpha(mask)
        out.append((c["y"] + 12, piece, x0, y0))     # (just in front of the person's feet)
    return out


def counter_sprites(place, used, set_layer, k):
    """2.5D (a place split into layers automatically): the same counter fronts, cut out of the set layer, as pieces
    the people are depth-sorted with (style25d Sprite: picture, k px a unit, left / top in logical units)."""
    from .style25d.scenery import Sprite
    return [Sprite(im, k, x / float(k), y / float(k), d, "counter")
            for d, im, x, y in counter_overlays(place, used, set_layer, k)]

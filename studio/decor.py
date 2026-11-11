"""Dressing a place: what hangs on its walls and stands in its corners, so the same kitchen does not look the same in
every video, and an occasion shows (a wedding, a birthday, 15 August, the monsoon...).

Script: a line in a SCENE, `DRESS: shaadi` (a pack), `DRESS: poster, calendar, plant` (pieces), or both;
`DRESS: none` = nothing. Without a DRESS line every video's indoor places get a few pieces of their own (the same
video always the same ones). The pieces are set pieces that go with the painted place (`fit`), so they line up with
it in every shot. Nothing religious."""
import random
import zlib

PACKS = {
    "shaadi": [("garland", {}), ("fairy_lights", {}), ("banner", {"text": "Shaadi Mubarak", "color": [200, 40, 70]})],
    "birthday": [("bunting", {}), ("balloons", {}), ("banner", {"text": "Happy Birthday", "color": [240, 80, 120]})],
    "new_year": [("fairy_lights", {}), ("balloons", {}), ("banner", {"text": "Happy New Year", "color": [60, 60, 160]})],
    "party": [("fairy_lights", {}), ("bunting", {}), ("balloons", {})],
    "independence": [("bunting", {"style": "tiranga"}), ("flag_stand", {}), ("poster", {"text": "Jai Hind",
                                                                                         "color": [255, 153, 51]})],
    "monsoon": [("umbrella", {}), ("puddle", {})],
    "cricket": [("bunting", {"color": [40, 90, 200]}), ("poster", {"text": "INDIA", "color": [40, 90, 200]})],
    "exam": [("poster", {"text": "EXAM!!", "color": [220, 60, 60]}), ("calendar", {}), ("wall_shelf", {})],
}
PACK_WORDS = {"wedding": "shaadi", "shadi": "shaadi", "bday": "birthday", "janamdin": "birthday",
              "newyear": "new_year", "15august": "independence", "15_august": "independence",
              "republic_day": "independence", "26january": "independence", "26_january": "independence",
              "baarish": "monsoon", "barish": "monsoon", "rain": "monsoon", "match": "cricket", "pariksha": "exam"}
PIECES = ("poster", "calendar", "photo_frame", "fairy_lights", "bunting", "garland", "balloons", "banner", "ac",
          "wall_shelf", "flag_stand", "umbrella", "puddle", "plant", "box", "cooler", "clock")
STRINGS = ("fairy_lights", "bunting", "garland", "banner")       # hang across the top of the picture
FLOOR = ("flag_stand", "umbrella", "puddle", "plant", "box", "cooler")
# where a wall piece can hang without covering a painted window or door (x, logical px); default: the two sides
WALL_SLOTS = {
    "kitchen": (190, 900), "room": (150, 930), "living_room": (150, 930), "bedroom": (930, 160),
    "office": (160, 920), "meeting_room": (160, 920), "classroom": (930, 150), "school": (930, 150),
    "hospital": (170, 910), "police_station": (160, 920), "bank": (160, 920), "hostel": (900, 170),
    "coaching": (930, 150), "library": (540, 160), "canteen": (160, 920), "gym": (180, 900), "party": (180, 900),
}
INDOOR = set(WALL_SLOTS) | {"bathroom", "exam_hall", "cinema", "court", "salon", "mall", "dhaba"}
NO_AUTO = {"kitchen", "room", "living_room", "classroom", "school", "terrace", "gully", "chai_tapri", "kirana",
           "jail", "train", "bus", "metro", "plane", "car", "auto"}     # rich already / no wall to dress
AUTO_POOL = ("poster", "calendar", "photo_frame", "wall_shelf", "ac", "clock", "plant")
FLOOR_X = (90, 990)


def words_to_items(words):
    """`shaadi, poster, plant` -> ([(piece, extra)...], unknown words)."""
    items, unknown = [], []
    for w in words:
        w = str(w).strip().lower()
        if not w:
            continue
        w = PACK_WORDS.get(w, w)
        if w in PACKS:
            items += PACKS[w]
        elif w in PIECES:
            items.append((w, {}))
        elif w not in ("none", "off", "nahi"):
            unknown.append(w)
    return items, unknown


def pieces_for(place, dress, seed=0):
    """Set pieces dressing `place`: dress = a list of words (packs / pieces), [] = nothing, "auto" = a few of its own.
    Each piece is a set piece dict that sits with the painted place (`fit`)."""
    if dress in (None, [], ""):
        return []
    rnd = random.Random(zlib.crc32(("%s|%s" % (place, seed)).encode("utf-8")))
    if dress == "auto":
        if place not in INDOOR or place in NO_AUTO:
            return []
        items = [(k, {}) for k in rnd.sample(AUTO_POOL, 2)]
    else:
        items, _unknown = words_to_items(dress if isinstance(dress, (list, tuple)) else str(dress).split(","))
    slots = list(WALL_SLOTS.get(place, (180, 900)))
    floors = list(FLOOR_X)
    out, seen = [], set()
    for k, extra in items:
        if k in seen and k in STRINGS:
            continue
        seen.add(k)
        piece = {"id": "decor_%s_%d" % (k, len(out)), "type": k, "y": 1700, "fit": True, "decor": True}
        piece.update(extra)
        if k in STRINGS:
            piece["x"] = 540
        elif k in FLOOR:
            if not floors:
                continue
            piece["x"], piece["y"] = floors.pop(0), 1560
            piece["scale"] = 0.8
        else:
            if not slots:
                continue
            piece["x"] = slots.pop(0)
        out.append(piece)
    return out

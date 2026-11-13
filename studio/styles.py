"""Video styles.

    "2d"   (default) the studio's normal look: every place, every feature, exactly as before.
    "2.5d" the same people, script format and features, drawn with depth: every place becomes layered
           (sky / skyline / window views move slower than the floor when the camera moves, depth blur,
           glowing lights, a blurred foreground). The PREMIUM places below are hand-made 2.5D sets with
           even more depth; all the others are made automatically from their 2D drawing (studio.style25d.
           autoset). Only your own picture (image), plain and night_road stay flat.

A scene picks its style with "style": "2.5d" (a script with `STYLE: 2.5d`; the render command and the
web page can also set it).
"""
DEFAULT = "2d"
STYLES = ("2d", "2.5d")
_ALIASES = {"2d": "2d", "flat": "2d", "2.5d": "2.5d", "25d": "2.5d", "2_5d": "2.5d", "2.5": "2.5d"}

# studio place -> hand-made 2.5D preset (studio.style25d.scenery.PRESETS); every other place is made automatically
PLACES_25D = {
    "kitchen": "kitchen_25d",
    "gully": "gali_25d",
    "chai_tapri": "gali_25d",
    "kirana": "gali_25d",
    "terrace": "diwali_rooftop",
    "room": "room_25d",
    "living_room": "room_25d",
    "school": "classroom_25d",
    "classroom": "classroom_25d",
    "office": "office_25d",
    "meeting_room": "meeting_25d",
    "jungle": "jungle_25d",
    "haunted_house": "haunted_25d",
    "bedroom": "bedroom_25d",
    "street": "street_25d",
    "bus_stop": "busstop_25d",
    "market": "market_25d",
    "festival_street": "festival_25d",
    "railway": "railway_25d",
    "gaon": "gaon_25d",
    "hospital": "hospital_25d",
    "bank": "bank_25d",
    "police_station": "police_25d",
    "court": "court_25d",
    "canteen": "canteen_25d",
    "dhaba": "dhaba_25d",
    "mithai_shop": "mithai_25d",
    "mobile_shop": "mobile_25d",
    "medical_store": "medical_25d",
    "salon": "salon_25d",
    "mall": "mall_25d",
    "cinema": "cinema_25d",
    "balcony": "balcony_25d",
    "bathroom": "bathroom_25d",
    "hostel": "hostel_25d",
    "library": "library_25d",
    "coaching": "coaching_25d",
    "exam_hall": "exam_hall_25d",
    "gym": "gym_25d",
    "party": "party_25d",
    "jail": "jail_25d",
    "beach": "beach_25d",
    "desert": "desert_25d",
    "mountain_road": "mountain_road_25d",
    "cricket_ground": "cricket_ground_25d",
    "school_ground": "school_ground_25d",
    "mandap": "mandap_25d",
    "graveyard": "graveyard_25d",
    "night_road": "night_road_25d",
    "train": "train_25d",
    "bus": "bus_25d",
    "metro": "metro_25d",
    "plane": "plane_25d",
    "car": "car_25d",
    "auto": "auto_25d",
    "ghar_darwaza": "ghar_darwaza_25d",
    "lift": "lift_25d",
    "park": "park_25d",
    "atm": "atm_25d",
    "petrol_pump": "petrol_pump_25d",
    "signal": "signal_25d",
    "buffet": "buffet_25d",
    "restaurant": "restaurant_25d",
    "interview_room": "interview_room_25d",
    "call_center": "call_center_25d",
    "startup_office": "startup_office_25d",
}
# sets that light themselves for the scene's time (a vehicle's view is re-lit by the vehicle engine, its inside keeps
# its own lights): no re-grading on top
OWN_TIME = {"train_25d", "bus_25d", "metro_25d", "plane_25d", "car_25d", "auto_25d"} | {
    k + "_25d" for k in ("car_front", "car_side", "car_pov", "car_mirror", "car_cabin", "auto_front", "auto_side",
                         "auto_pov", "auto_mirror")}
# sets with writing on them (shop signs, menus, boards) are never mirrored for a reverse shot (the text would read
# backwards). The 2d look mirrors every place, as it always has.
NO_MIRROR = {"ghar_darwaza_25d", "lift_25d", "atm_25d", "petrol_pump_25d", "signal_25d", "buffet_25d",
             "restaurant_25d", "interview_room_25d", "call_center_25d", "startup_office_25d", "park_25d",
             "gali_25d", "classroom_25d", "office_25d", "meeting_25d", "street_25d", "busstop_25d", "market_25d",
             "festival_25d", "railway_25d", "street_road_25d", "busstop_road_25d", "hospital_25d", "bank_25d",
             "police_25d", "court_25d", "canteen_25d",
             "dhaba_25d", "mithai_25d", "mobile_25d", "medical_25d", "salon_25d", "mall_25d", "cinema_25d",
             "library_25d", "coaching_25d", "exam_hall_25d", "gym_25d", "party_25d", "mountain_road_25d",
             "cricket_ground_25d", "school_ground_25d", "graveyard_25d"} | {
    "auto:" + p for p in ("bus_stop", "railway", "canteen", "exam_hall", "library", "coaching", "party", "gym",
                          "hospital", "police_station", "bank")}
# hand-made road sets: the people stand on the footpath in front, the road runs behind them and its traffic is in
# proportion to them (a car on the road behind is a little smaller than somebody on the footpath, as far away as it is)


def _traffic(lane_y, horizon, period):
    from .backgrounds import road_traffic                  # (each vehicle as big as its lane's distance makes it)
    return road_traffic(lane_y, horizon, period)


# preset -> the moving life drawn over it: clouds and birds far away, the traffic on its road (2D keeps its own)
SET_AMBIENT = {
    "street_25d": [("cloud", 190, 14, 1.0), ("cloud", 450, 9, 0.75), ("birds", 330, 60, 3), _traffic(1470, 860, 9.0)],
    "busstop_25d": [("cloud", 220, 11, 1.0), ("cloud", 460, 7, 0.7), ("birds", 360, 55, 2), _traffic(1470, 860, 7.5)],
    "mountain_road_25d": [("birds", 300, 40, 2), _traffic(1440, 1000, 12.0)],
    # a scene with a vehicle in it: the people on the road next to it, the traffic on the far lane behind them
    "street_road_25d": [("cloud", 190, 14, 1.0), ("cloud", 450, 9, 0.75), ("birds", 330, 60, 3),
                        _traffic(1500, 900, 9.0)],
    "busstop_road_25d": [("cloud", 220, 11, 1.0), ("cloud", 460, 7, 0.7), ("birds", 360, 55, 2),
                         _traffic(1500, 900, 7.5)],
}
ROAD_WITH_VEHICLE = {"street": "street_road_25d", "bus_stop": "busstop_road_25d", "night_road": None}


def on_the_road(scene):
    """True when a road place's scene has a vehicle in it (`OBJ: auto`, `A -> ride bike`): then the people stay on
    the road next to it (both looks), instead of on the footpath."""
    bg = scene.get("background") or {}
    if (bg.get("type") if isinstance(bg, dict) else bg) not in ROAD_WITH_VEHICLE:
        return False
    from . import objects
    for raw in scene.get("timeline", []):
        for key in ("obj", "ride"):
            d = raw.get(key)
            if isinstance(d, dict) and objects.resolve_kind(d.get("kind", "")) in objects.VEHICLES:
                return True
    return False
KEEP_AMBIENT = set(SET_AMBIENT)
# the light each preset is painted in; another SCENE time (night, rain...) re-lights it
NATIVE_TIME = {"kitchen_25d": "day", "gali_25d": "sunset", "diwali_rooftop": "night", "room_25d": "day",
               "classroom_25d": "day", "office_25d": "day", "meeting_25d": "day", "jungle_25d": "day",
               "haunted_25d": "night", "bedroom_25d": "day", "street_25d": "day", "busstop_25d": "day",
               "market_25d": "day", "festival_25d": "night", "railway_25d": "day", "gaon_25d": "day",
               "hospital_25d": "day", "bank_25d": "day", "police_25d": "day", "court_25d": "day", "canteen_25d": "day",
               "dhaba_25d": "sunset", "mithai_25d": "day", "mobile_25d": "day", "medical_25d": "day",
               "salon_25d": "day", "mall_25d": "day", "cinema_25d": "night", "balcony_25d": "day",
               "bathroom_25d": "day", "hostel_25d": "day", "library_25d": "day", "coaching_25d": "day",
               "exam_hall_25d": "day", "gym_25d": "day", "party_25d": "day", "jail_25d": "day", "beach_25d": "day",
               "desert_25d": "day", "mountain_road_25d": "day", "cricket_ground_25d": "day",
               "school_ground_25d": "day", "street_road_25d": "day", "busstop_road_25d": "day",
               "mandap_25d": "night", "graveyard_25d": "night", "night_road_25d": "night",
               "ghar_darwaza_25d": "day", "lift_25d": "day", "park_25d": "day", "atm_25d": "day",
               "petrol_pump_25d": "day", "signal_25d": "day", "buffet_25d": "night", "restaurant_25d": "evening",
               "interview_room_25d": "day", "call_center_25d": "night", "startup_office_25d": "day"}


def normalize(value):
    key = str(value).strip().lower()
    if key not in _ALIASES:
        raise ValueError("unknown style %r: use \"2d\" or \"2.5d\"" % (value,))
    return _ALIASES[key]


def scene_style(scene):
    meta = scene.get("meta") or {}
    return normalize(scene.get("style") or meta.get("style") or DEFAULT)


FLAT_IN_25D = {"image", "plain"}       # stay as they are in 2.5D too (your own photo, the plain colour)


def has_depth(kind):
    """True when this place is drawn with depth in 2.5D (a hand-made set, or made automatically from its drawing)."""
    if kind in PLACES_25D:
        return True
    if not kind or kind in FLAT_IN_25D:
        return False
    from . import vehicles
    if vehicles.resolve(kind):
        return True
    from .style25d.autoset import place_function
    return bool(place_function(kind))


def preset_for(scene):
    """The 2.5D set this (single-place) scene uses: a hand-made preset name, "auto:<place>", or None (2d style,
    or a place that stays flat)."""
    if scene_style(scene) != "2.5d":
        return None
    bg = scene.get("background") or {}
    kind = bg.get("type") if isinstance(bg, dict) else bg
    if kind in ROAD_WITH_VEHICLE and on_the_road(scene):
        return ROAD_WITH_VEHICLE[kind]
    if kind in PLACES_25D:
        return PLACES_25D[kind]
    from . import vehicles
    if vehicles.resolve(kind):                     # taxi, cab, rickshaw, flight...: the vehicle's own set
        v = vehicles.resolve(kind)                  # (a driving shot, car_front...: its own set, studio.drive)
        return PLACES_25D.get(v, v + "_25d")
    return "auto:" + kind if has_depth(kind) else None

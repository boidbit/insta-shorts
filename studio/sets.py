"""Set pieces with states (door, bed, sofa, fan, TV, lamp, tree, bush...).

Script:    OBJ: door right        OBJ: door open        A -> sit sofa        LIGHTS: off

Scene:     "sets": [ { "id": "door1", "type": "door", "x": 880, "y": 1700, "state": "closed" },
                        { "id": "c1", "type": "chair", "x": 300, "y": 1700 } ]
Timeline:  { "t": 2.0, "set": "door1", "state": "open" }
           { "t": 3.0, "who": "A", "action": "sit", "on": "c1" }     # snaps A onto the chair seat

x, y = where the object touches the floor (logical px). "scale", "flip" (mirror), and for some types
"text" (signboard), "color", "w" (fence width), "view" ("front"/"side" for chair).
Wall pieces (door, window, clock, tubelight, fan, painting) are always behind the characters; floor
pieces are depth-sorted with the characters by y.
"""
import math

from PIL import Image

from .effects import Patch

INK = (16, 16, 16, 255)
WOOD, WOOD_D, WOOD_L = (176, 124, 78, 255), (130, 90, 56, 255), (206, 160, 108, 255)

# type -> (half width, height above floor, below-floor margin, wall?, seat height or None, emits light when on?)
SPEC = {
    "door": (180, 960, 10, True, None, False),
    "window": (190, 940, 10, True, None, False),
    "clock": (80, 1080, 0, True, None, False),
    "painting": (150, 1000, 0, True, None, False),
    "tubelight": (220, 1180, 0, True, None, True),
    "fan": (300, 1700, 0, True, None, False),
    "tv": (220, 650, 20, False, None, True),
    "fridge": (190, 790, 20, False, None, False),
    "cupboard": (200, 850, 20, False, None, False),
    "bed": (510, 450, 30, False, 262, False),
    "chair": (120, 490, 20, False, 200, False),
    "stool": (90, 220, 20, False, 205, False),
    "table": (290, 360, 30, False, None, False),
    "desk": (290, 360, 30, False, None, False),
    "sofa": (350, 360, 30, False, 182, False),
    "bench": (330, 320, 30, False, 190, False),
    "stairs": (300, 460, 10, False, None, False),
    "tree": (330, 900, 20, False, None, False),
    "bush": (220, 270, 20, False, None, False),
    "rock": (160, 150, 20, False, None, False),
    "fence": (320, 260, 20, False, None, False),
    "dustbin": (90, 230, 20, False, None, False),
    "signboard": (200, 700, 20, False, None, False),
    "lamp": (90, 760, 20, False, None, True),
    "phone": (90, 260, 20, False, None, False),
    "plant": (110, 380, 20, False, None, False),
    "box": (110, 200, 20, False, None, False),
    "bucket": (80, 160, 20, False, None, False),
    "khaat": (430, 330, 30, False, 205, False),          # charpai: sit or lie on it like a bed
    "matka": (80, 330, 20, False, None, False),
    "chulha": (130, 360, 20, False, None, False),        # mud stove, the fire flickers (`OBJ: chulha off` = cold)
    "blackboard": (230, 860, 20, False, None, False),    # on a stand: `OBJ: blackboard center चमगादड़` writes on it
    "drip": (90, 960, 20, False, None, False),           # hospital glucose stand
    "wheelchair": (170, 470, 20, False, 205, False),
    "cooler": (160, 560, 20, False, None, False),
    "washing_machine": (160, 470, 20, False, None, False),   # `OBJ: washing_machine on` spins and shakes
    "mirror": (120, 800, 20, False, None, False),
    "jail_door": (150, 1110, 10, True, None, False),     # barred cell door: closed / open / broken (kicked down)
    # seats inside the vehicles (placed by the script reader for SCENE: train / bus / metro / plane / car / auto)
    "berth": (210, 400, 20, False, 205, False),
    "bus_seat": (175, 450, 20, False, 200, False),
    "metro_seat": (230, 300, 20, False, 195, False),
    "plane_seat": (135, 560, 20, False, 205, False),
    "car_seat": (140, 560, 20, False, 205, False),
    "auto_seat": (230, 330, 20, False, 200, False),
}
VEHICLE_SEATS = ("berth", "bus_seat", "metro_seat", "plane_seat", "car_seat", "auto_seat")
# decor: what dresses a place up (studio.decor places them; script `DRESS: shaadi` / `DRESS: poster, plant`)
SPEC.update({
    "poster": (100, 1150, 0, True, None, False), "calendar": (80, 1100, 0, True, None, False),
    "photo_frame": (110, 1160, 0, True, None, False), "fairy_lights": (540, 1420, 0, True, None, False),
    "bunting": (540, 1480, 0, True, None, False), "garland": (540, 1540, 0, True, None, False),
    "balloons": (120, 1320, 0, True, None, False), "banner": (380, 1330, 0, True, None, False),
    "ac": (170, 1340, 0, True, None, False), "wall_shelf": (170, 1060, 0, True, None, False),
    "flag_stand": (90, 720, 20, False, None, False), "umbrella": (110, 250, 20, False, None, False),
    "puddle": (220, 40, 30, False, None, False),
})
DECOR = ("poster", "calendar", "photo_frame", "fairy_lights", "bunting", "garland", "balloons", "banner", "ac",
         "wall_shelf", "flag_stand", "umbrella", "puddle")
TIRANGA = ((255, 153, 51, 255), (255, 255, 255, 255), (19, 136, 8, 255))
PARTY = ((240, 80, 90, 255), (250, 200, 60, 255), (80, 170, 240, 255), (120, 200, 110, 255), (200, 110, 220, 255))

ALL = set(SPEC)


class O:
    """Draw relative to the object's floor point; dy < 0 is up. Mirrors x when flipped."""

    def __init__(self, p, x, y, sc, flip):
        self.p, self.x, self.y, self.sc, self.sx = p, x, y, sc, (-1 if flip else 1)

    def X(self, dx, dy):
        return (self.x + self.sx * dx * self.sc, self.y + dy * self.sc)

    def poly(self, pts, fill=None, outline=INK, w=5):
        self.p.poly([self.X(a, b) for a, b in pts], fill, outline, w * self.sc)

    def rect(self, x0, y0, x1, y1, fill=None, outline=INK, w=5):
        self.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], fill, outline, w)

    def line(self, pts, color=INK, w=5):
        self.p.line([self.X(a, b) for a, b in pts], color, w * self.sc)

    def ellipse(self, cx, cy, rx, ry, fill=None, outline=INK, w=5):
        c = self.X(cx, cy)
        self.p.ellipse(c[0], c[1], rx * self.sc, ry * self.sc, fill, outline, w * self.sc)

    def text(self, cx, cy, txt, size, fill=(20, 20, 20, 255)):
        c = self.X(cx, cy)
        self.p.text(c[0], c[1], txt, size * self.sc, fill, 0.6, fill)

    def rrect(self, x0, y0, x1, y1, r, fill=None, outline=INK, w=5):
        """A rectangle with rounded corners (as a polygon)."""
        r = max(0.0, min(r, (x1 - x0) / 2.0, (y1 - y0) / 2.0))
        pts = []
        for (cx, cy, a0) in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
            for i in range(7):
                a = math.radians(a0 + i * 15)
                pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        self.poly(pts, fill, outline, w)

    def shadow(self, hw, h=22):
        self.ellipse(0, 4, hw, h, (0, 0, 0, 55), None)


# ---------------------------------------------------------------- drawings
def d_door(o, st, t, ob):
    o.rect(-170, -950, 170, 0, WOOD_D)
    if st == "open":
        o.rect(-145, -925, 145, 0, (36, 30, 28, 255))
        o.poly([(-145, -925), (-80, -960), (-80, 30), (-145, 0)], WOOD_L)
    else:
        o.rect(-145, -925, 145, 0, WOOD)
        o.rect(-110, -880, 110, -540, None, WOOD_D, 6)
        o.rect(-110, -470, 110, -60, None, WOOD_D, 6)
        o.ellipse(105, -480, 14, 14, (230, 200, 90, 255))


def d_window(o, st, t, ob):
    o.rect(-180, -930, 180, -460, (250, 250, 248, 255), INK, 8)
    sky = (30, 34, 70, 255) if st == "night" else (170, 214, 238, 255)
    o.rect(-160, -910, 160, -480, sky, None)
    if st == "night":
        o.ellipse(80, -820, 34, 34, (250, 244, 210, 255), None)
    else:
        o.poly([(-160, -560), (-60, -640), (40, -580), (160, -660), (160, -480), (-160, -480)], (150, 200, 150, 255), None)
    o.line([(0, -910), (0, -480)], INK, 7)
    o.line([(-160, -700), (160, -700)], INK, 7)
    o.rect(-200, -470, 200, -440, (230, 226, 216, 255))


def d_clock(o, st, t, ob):
    o.ellipse(0, -1000, 64, 64, (255, 255, 255, 255), INK, 7)
    sp = float(ob.get("speed", 6.0))
    a = math.radians(t * sp)
    o.line([(0, -1000), (40 * math.sin(a), -1000 - 40 * math.cos(a))], INK, 5)
    o.line([(0, -1000), (24, -1014)], INK, 7)


def d_painting(o, st, t, ob):
    o.rect(-140, -1000, 140, -780, (250, 246, 236, 255), INK, 8)
    o.rect(-120, -980, 120, -800, (232, 180, 90, 255), None)
    o.poly([(-120, -800), (-40, -900), (20, -840), (120, -930), (120, -800)], (120, 150, 190, 255), None)


def d_tubelight(o, st, t, ob):
    on = st != "off"
    if on:
        o.ellipse(0, -1150, 230, 70, (255, 255, 230, 60), None)
    o.rect(-200, -1166, 200, -1138, (255, 255, 240, 255) if on else (190, 190, 196, 255), INK, 4)
    o.rect(-212, -1170, -196, -1134, (120, 120, 126, 255), INK, 3)
    o.rect(196, -1170, 212, -1134, (120, 120, 126, 255), INK, 3)


def d_fan(o, st, t, ob):
    top = -1700
    o.line([(0, top), (0, top + 120)], (90, 90, 96, 255), 10)
    o.ellipse(0, top + 136, 40, 24, (140, 140, 150, 255))
    spin = (t * 10.0) if st != "off" else 0.3
    for i in range(3):
        a = spin + i * 2 * math.pi / 3
        ex = 260 * math.cos(a)
        ey = 30 * math.sin(a)
        o.poly([(0, top + 136), (ex * 0.95 - 12, top + 136 + ey - 10), (ex, top + 136 + ey),
                (ex * 0.95 + 12, top + 136 + ey + 10)], (176, 176, 186, 255), INK, 3)


def d_tv(o, st, t, ob):
    o.shadow(200)
    o.rect(-190, -250, 190, 0, WOOD)
    o.line([(0, -240), (0, -10)], WOOD_D, 5)
    o.rect(-30, -290, 30, -250, (40, 40, 46, 255))
    o.rect(-210, -640, 210, -290, (30, 30, 34, 255))
    if st == "on":
        cols = [(80, 160, 230, 255), (230, 110, 80, 255), (120, 200, 120, 255), (240, 210, 90, 255)]
        k = int(t * 1.5) % 4
        o.rect(-190, -620, 190, -310, cols[k], None)
        o.ellipse(-40 + 30 * math.sin(t * 2), -470, 70, 90, cols[(k + 1) % 4], None)
        o.ellipse(90, -520 + 20 * math.cos(t * 3), 40, 40, (255, 255, 255, 200), None)
    else:
        o.rect(-190, -620, 190, -310, (52, 56, 64, 255), None)
        o.line([(-150, -580), (-60, -600)], (90, 96, 110, 255), 6)


def d_fridge(o, st, t, ob):
    o.shadow(170)
    if st == "open":
        o.rect(-160, -780, 160, 0, (210, 230, 240, 255))
        for y in (-600, -420, -240):
            o.line([(-150, y), (150, y)], (150, 170, 180, 255), 5)
        o.rect(-110, -590, -40, -500, (230, 90, 80, 255), INK, 3)
        o.rect(20, -410, 120, -330, (250, 220, 120, 255), INK, 3)
        o.poly([(160, -780), (230, -740), (230, 40), (160, 0)], (236, 236, 240, 255))
    else:
        o.rect(-160, -780, 160, 0, (236, 238, 242, 255))
        o.line([(-160, -520), (160, -520)], INK, 5)
        o.line([(120, -700), (120, -580)], (150, 150, 156, 255), 10)
        o.line([(120, -460), (120, -300)], (150, 150, 156, 255), 10)


def d_cupboard(o, st, t, ob):
    o.shadow(190)
    body = (120, 140, 160, 255)
    o.rect(-180, -840, 180, 0, body)
    if st == "open":
        o.rect(-160, -820, 160, -20, (60, 60, 70, 255))
        for i, c in enumerate([(220, 90, 90, 255), (90, 140, 220, 255), (240, 200, 90, 255), (120, 190, 120, 255)]):
            o.rect(-140 + i * 70, -760, -90 + i * 70, -420, c, INK, 3)
        o.line([(-160, -400), (160, -400)], (150, 150, 156, 255), 6)
    else:
        o.line([(0, -840), (0, 0)], INK, 5)
        o.line([(-24, -470), (-24, -380)], (220, 220, 226, 255), 9)
        o.line([(24, -470), (24, -380)], (220, 220, 226, 255), 9)


def d_bed(o, st, t, ob):
    o.shadow(470)
    o.rect(-500, -440, -460, 0, WOOD_D)                        # headboard (pillow end, left unless flipped)
    o.rect(460, -300, 490, 0, WOOD_D)
    o.rect(-480, -200, 480, -80, WOOD)
    o.rect(-470, -262, 470, -198, (250, 250, 248, 255))
    o.ellipse(-370, -288, 84, 32, (246, 246, 252, 255))
    o.poly([(-200, -266), (470, -266), (474, -150), (-196, -150)], tuple(ob.get("color", (110, 150, 210))) + (255,))


def d_chair(o, st, t, ob):
    o.shadow(110, 16)
    if ob.get("view") == "side":
        o.rect(-90, -210, 90, -186, WOOD)
        o.rect(-90, -480, -66, -186, WOOD_D)
        o.line([(-80, -186), (-80, 0)], WOOD_D, 12)
        o.line([(80, -186), (80, 0)], WOOD_D, 12)
        return
    o.rect(-96, -480, -76, -200, WOOD_D)
    o.rect(76, -480, 96, -200, WOOD_D)
    o.rect(-96, -480, 96, -420, WOOD)
    o.rect(-96, -330, 96, -300, WOOD)
    o.rect(-104, -212, 104, -186, WOOD)
    o.line([(-88, -186), (-88, 0)], WOOD_D, 13)
    o.line([(88, -186), (88, 0)], WOOD_D, 13)


def d_stool(o, st, t, ob):
    o.shadow(80, 14)
    o.ellipse(0, -205, 82, 18, WOOD)
    o.line([(-60, -195), (-72, 0)], WOOD_D, 11)
    o.line([(60, -195), (72, 0)], WOOD_D, 11)
    o.line([(0, -195), (0, 0)], WOOD_D, 11)


def _table(o, ob, top=(214, 172, 120, 255), drawer=False):
    o.shadow(280)
    o.line([(-240, -320), (-240, 0)], WOOD_D, 16)
    o.line([(240, -320), (240, 0)], WOOD_D, 16)
    if drawer:
        o.rect(60, -320, 230, -200, WOOD)
        o.ellipse(145, -260, 10, 10, (230, 200, 90, 255))
    o.rect(-280, -350, 280, -316, top)
    if ob.get("cloth"):
        o.poly([(-280, -350), (280, -350), (290, -250), (-290, -250)], tuple(ob["cloth"]) + (255,))


def d_table(o, st, t, ob):
    _table(o, ob)


def d_desk(o, st, t, ob):
    _table(o, ob, (160, 110, 68, 255), drawer=True)


def d_sofa(o, st, t, ob):
    o.shadow(330)
    c = tuple(ob.get("color", (150, 60, 66))) + (255,)
    dk = tuple(int(v * 0.82) for v in c[:3]) + (255,)
    o.rect(-320, -350, 320, -150, c)
    o.rect(-330, -190, 330, -110, dk)
    o.rect(-350, -260, -280, -20, dk)
    o.rect(280, -260, 350, -20, dk)
    o.rect(-300, -110, 300, -20, dk)
    o.line([(0, -340), (0, -190)], INK, 4)


def d_bench(o, st, t, ob):
    o.shadow(320)
    for lx in (-280, 260):
        o.rect(lx, -190, lx + 24, 0, (96, 100, 108, 255))
    for y in (-320, -280, -240):
        o.rect(-310, y, 310, y + 28, WOOD)
    o.rect(-320, -200, 320, -168, WOOD_D)


def d_stairs(o, st, t, ob):
    n = 6
    for i in range(n):
        x0 = -300 + i * 100
        o.rect(x0, -(i + 1) * 75, 300, -i * 75, (200, 190, 176, 255), INK, 4)
    o.line([(-300, -260), (300, -710)], (110, 80, 54, 255), 10)
    for i in range(0, n, 2):
        x = -300 + i * 100 + 50
        o.line([(x, -(i + 1) * 75), (x, -(i + 1) * 75 - 190)], (110, 80, 54, 255), 6)


def d_tree(o, st, t, ob):
    o.shadow(220, 26)
    o.rect(-34, -520, 34, 0, (118, 84, 54, 255))
    g = tuple(ob.get("color", (86, 160, 84))) + (255,)
    sway = 6 * math.sin(t * 1.2)
    for cx, cy, r in ((-150 + sway, -540, 160), (150 + sway, -550, 160), (sway, -700, 210)):
        o.ellipse(cx, cy, r, r * 0.9, g)


def d_bush(o, st, t, ob):
    g = tuple(ob.get("color", (60, 120, 64))) + (255,)
    dk = tuple(int(v * 0.8) for v in g[:3]) + (255,)
    rustle = 5 * math.sin(t * 14) if st == "rustle" else 0
    for cx, cy, r in ((-140, -90, 90), (140, -90, 90), (-60, -160, 110), (70, -170, 110), (0, -90, 120)):
        o.ellipse(cx + rustle, cy, r, r * 0.85, g if cx % 2 else dk)


def d_rock(o, st, t, ob):
    o.shadow(150, 16)
    o.poly([(-150, 0), (-130, -90), (-50, -145), (60, -130), (140, -70), (155, 0)], (150, 150, 156, 255))
    o.line([(-40, -110), (10, -60)], (110, 110, 116, 255), 5)


def d_fence(o, st, t, ob):
    w = float(ob.get("w", 600))
    n = max(2, int(w / 60))
    x0 = -w / 2
    o.rect(x0, -170, x0 + w, -150, WOOD_D)
    o.rect(x0, -80, x0 + w, -60, WOOD_D)
    for i in range(n + 1):
        x = x0 + i * w / n
        o.poly([(x - 18, 0), (x - 18, -210), (x, -240), (x + 18, -210), (x + 18, 0)], WOOD_L, INK, 4)


def d_dustbin(o, st, t, ob):
    o.shadow(80, 14)
    o.poly([(-70, -200), (70, -200), (56, 0), (-56, 0)], (60, 150, 90, 255))
    o.rect(-80, -226, 80, -198, (50, 120, 74, 255))
    o.line([(-24, -226), (-24, -240), (24, -240), (24, -226)], INK, 6)


def d_signboard(o, st, t, ob):
    o.line([(-150, 0), (-150, -480)], (90, 90, 96, 255), 12)
    o.line([(150, 0), (150, -480)], (90, 90, 96, 255), 12)
    c = tuple(ob.get("color", (250, 210, 70))) + (255,)
    o.rect(-190, -690, 190, -470, c, INK, 8)
    txt = str(ob.get("text", "SHOP"))
    size = min(90, 640 / max(3, len(txt)))
    o.text(0, -580, txt, size)


def d_lamp(o, st, t, ob):
    on = st == "on"
    if on:
        o.ellipse(0, -650, 200, 160, (255, 230, 150, 50), None)
        o.ellipse(0, -650, 120, 100, (255, 230, 150, 60), None)
    o.shadow(70, 12)
    o.ellipse(0, -8, 60, 14, (40, 40, 44, 255))
    o.line([(0, -8), (0, -600)], INK, 10)
    o.poly([(-80, -580), (80, -580), (56, -720), (-56, -720)], (255, 230, 140, 255) if on else (220, 200, 150, 255))


def d_phone(o, st, t, ob):
    o.shadow(80, 12)
    o.line([(-60, -150), (-70, 0)], WOOD_D, 9)
    o.line([(60, -150), (70, 0)], WOOD_D, 9)
    o.rect(-80, -170, 80, -146, WOOD)
    sh = 6 * math.sin(t * 60) if st == "ringing" else 0
    o.poly([(-60 + sh, -170), (60 + sh, -170), (46 + sh, -230), (-46 + sh, -230)], (210, 60, 60, 255))
    o.rect(-66 + sh, -256, 66 + sh, -228, (190, 50, 50, 255))
    if st == "ringing":
        for i, r in enumerate((90, 120, 150)):
            if (t * 4 + i) % 3 < 2:
                for side in (-1, 1):
                    a0 = -0.6 if side > 0 else math.pi - 0.6
                    pts = [(side * 0 + r * math.cos(a0 + j * 0.12), -230 + r * math.sin(a0 + j * 0.12) * 0.8)
                           for j in range(11)]
                    o.line(pts, INK, 5)


def d_plant(o, st, t, ob):
    o.shadow(80, 14)
    o.poly([(-70, -140), (70, -140), (54, 0), (-54, 0)], (190, 104, 70, 255))
    for (c, d) in ((-60, -300), (10, -360), (70, -290)):
        o.line([(0, -140), (c, d)], (70, 130, 70, 255), 10)
        o.ellipse(c, d - 20, 36, 46, (90, 160, 84, 255), INK, 4)


def d_box(o, st, t, ob):
    o.shadow(100, 14)
    o.rect(-100, -190, 100, 0, (196, 150, 100, 255))
    o.line([(-100, -150), (100, -150)], (150, 110, 70, 255), 4)
    o.rect(-20, -190, 20, -150, (230, 210, 160, 255), None)


def d_bucket(o, st, t, ob):
    o.shadow(70, 12)
    o.poly([(-70, -150), (70, -150), (54, 0), (-54, 0)], (70, 130, 210, 255))
    o.line([(-70, -150), (0, -210), (70, -150)], INK, 5)
    o.ellipse(0, -150, 70, 14, (130, 190, 240, 255))


def d_khaat(o, st, t, ob):
    o.shadow(420)
    for lx in (-410, 382):                                      # turned wooden legs
        o.rect(lx, -250, lx + 28, 0, WOOD_D)
        o.ellipse(lx + 14, -120, 20, 14, WOOD, INK, 3)
    rope = (222, 196, 136, 255)
    o.poly([(-400, -300), (400, -300), (424, -236), (-424, -236)], rope)        # the woven top
    for i in range(-8, 9):                                      # the criss-cross of the rope
        x = i * 46
        o.line([(x - 22, -298), (x + 22, -238)], (186, 156, 96, 255), 3)
        o.line([(x + 22, -298), (x - 22, -238)], (186, 156, 96, 255), 3)
    o.poly([(-400, -300), (400, -300), (424, -236), (-424, -236)], None, INK, 5)
    o.rect(-436, -240, 436, -208, WOOD)                         # the side rail


def d_matka(o, st, t, ob):
    o.shadow(70, 12)
    o.poly([(-60, 0), (60, 0), (46, -40), (-46, -40)], (90, 70, 50, 255))   # a little stand
    clay = (194, 104, 66, 255)
    o.ellipse(0, -150, 78, 100, clay)
    o.line([(-60, -170), (60, -170)], (150, 76, 46, 255), 5)
    o.rect(-34, -268, 34, -236, clay)
    o.ellipse(0, -268, 42, 10, (150, 76, 46, 255))
    o.rect(-20, -320, 20, -268, (206, 208, 216, 255))         # a steel glass upside down on the mouth


def d_chulha(o, st, t, ob):
    o.shadow(120, 14)
    mud = (178, 120, 82, 255)
    o.poly([(-120, 0), (120, 0), (104, -170), (-104, -170)], mud)
    o.ellipse(0, -60, 50, 50, (40, 26, 22, 255))               # the fire mouth
    if st not in ("off", "closed"):
        for i, (dx, h) in enumerate(((-18, 70), (0, 96), (18, 66))):
            k = 1 + 0.18 * math.sin(t * 13 + i * 2.1)
            o.poly([(dx - 18, -40), (dx + 18, -40), (dx + 4 * math.sin(t * 9 + i), -40 - h * k)],
                   ((255, 170, 60, 255), (255, 226, 110, 255), (255, 140, 50, 255))[i], None)
        o.ellipse(0, -60, 90, 70, (255, 180, 80, 40), None)
    o.ellipse(0, -176, 96, 18, (120, 110, 104, 255))            # a pot on top
    o.poly([(-80, -176), (80, -176), (70, -250), (-70, -250)], (60, 56, 60, 255))
    for x in (-70, 0, 70):                                      # sticks of firewood
        o.line([(x - 10, 6), (x + 40, -30)], (110, 80, 54, 255), 10)


def d_blackboard(o, st, t, ob):
    leg = (130, 90, 56, 255)
    o.line([(-150, 0), (-110, -840)], leg, 14)                  # the easel
    o.line([(150, 0), (110, -840)], leg, 14)
    o.line([(0, -40), (0, -820)], leg, 12)
    o.rect(-220, -820, 220, -360, (150, 104, 66, 255), INK, 8)
    o.rect(-200, -800, 200, -380, (36, 52, 46, 255), INK, 3)
    txt = str(ob.get("text", ""))
    if txt:
        size = min(110, 640 / max(3, len(txt)))
        o.text(0, -590, txt, size, (240, 240, 232, 255))
    o.rect(-120, -372, -60, -360, (240, 240, 232, 255), None)   # chalk on the ledge


def d_drip(o, st, t, ob):
    steel = (170, 172, 180, 255)
    for dx in (-70, 0, 70):                                     # wheeled base
        o.line([(0, -20), (dx, 0)], steel, 8)
        o.ellipse(dx, 0, 9, 9, (50, 50, 56, 255))
    o.line([(0, -20), (0, -900)], steel, 9)
    o.line([(-60, -900), (60, -900)], steel, 7)
    o.poly([(-50, -890), (-10, -890), (-12, -740), (-48, -740)], (226, 240, 250, 255))     # the bottle
    o.rect(-46, -820, -14, -748, (200, 230, 246, 255), None)
    level = -820 + (t * 3) % 60                                 # the level drops slowly
    o.line([(-44, level), (-16, level)], (150, 200, 230, 255), 3)
    o.line([(-30, -740), (-30, -700), (40, -560), (60, -380)], (160, 200, 220, 255), 4)
    drop = -730 + (t * 160) % 30
    o.ellipse(-30, drop, 4, 6, (150, 200, 240, 255), None)


def d_wheelchair(o, st, t, ob):
    o.shadow(150, 16)
    o.ellipse(-30, -150, 150, 150, None, (60, 62, 70, 255), 12)            # the big wheel
    for a in range(0, 180, 30):
        r = math.radians(a)
        o.line([(-30 - 140 * math.cos(r), -150 - 140 * math.sin(r)), (-30 + 140 * math.cos(r), -150 + 140 * math.sin(r))],
               (150, 152, 160, 255), 3)
    o.ellipse(140, -30, 30, 30, (60, 62, 70, 255))                         # the small wheel
    o.rect(-120, -230, 150, -190, (40, 90, 160, 255))                       # the seat
    o.rect(-140, -460, -100, -200, (40, 90, 160, 255))                      # the back
    o.line([(-120, -460), (-170, -470)], (60, 62, 70, 255), 10)             # handle
    o.line([(150, -190), (170, -40)], (150, 152, 160, 255), 8)              # foot rest
    o.line([(150, -40), (200, -40)], (60, 62, 70, 255), 10)


def d_cooler(o, st, t, ob):
    o.shadow(150)
    body = (236, 232, 222, 255)
    o.rect(-150, -540, 150, -40, body)
    o.rect(-150, -40, 150, 0, (120, 120, 126, 255))
    o.rect(-120, -500, 120, -200, (70, 80, 90, 255))           # the grille
    for y in range(-488, -200, 16):
        o.line([(-120, y), (120, y)], (190, 196, 204, 255), 4)
    o.ellipse(0, -350, 90, 90, None, (40, 44, 50, 255), 5)
    o.rect(-120, -170, 120, -70, (210, 206, 196, 255))          # side pads
    for x in range(-110, 120, 22):
        o.line([(x, -168), (x, -72)], (180, 170, 150, 255), 3)


def d_washing_machine(o, st, t, ob):
    on = st == "on"
    jig = 4 * math.sin(t * 40) if on else 0.0
    o.shadow(150)
    o.rect(-150 + jig, -460, 150 + jig, 0, (240, 242, 246, 255))
    o.rect(-150 + jig, -460, 150 + jig, -390, (210, 214, 222, 255))
    o.ellipse(70 + jig, -425, 16, 16, (90, 160, 220, 255))
    o.ellipse(jig, -200, 110, 110, (180, 184, 192, 255))
    o.ellipse(jig, -200, 86, 86, (120, 170, 220, 255))
    if on:                                                       # clothes going round
        for i, col in enumerate(((230, 80, 80, 255), (250, 210, 70, 255), (70, 150, 90, 255))):
            a = t * 9 + i * 2.1
            o.ellipse(jig + 40 * math.cos(a), -200 + 40 * math.sin(a), 30, 18, col, None)
    o.ellipse(jig - 30, -240, 26, 14, (255, 255, 255, 140), None)


def d_mirror(o, st, t, ob):
    o.shadow(110, 14)
    o.rect(-120, -260, 120, 0, WOOD)                            # dressing table
    o.rect(-100, -220, 100, -140, WOOD_L)
    o.ellipse(0, -180, 8, 8, INK)
    o.ellipse(0, -530, 110, 270, WOOD_D)
    o.ellipse(0, -530, 92, 252, (196, 222, 236, 255))
    o.line([(-40, -680), (20, -740)], (255, 255, 255, 255), 8)
    o.line([(-30, -620), (40, -700)], (255, 255, 255, 255), 5)


def _bench(o, back, seat, frame, x0, x1, top, legs=True):
    o.shadow(x1 - 10, 16)
    o.rrect(x0 + 10, top, x1 - 10, -205, 22, back)
    o.rrect(x0, -218, x1, -176, 16, seat)
    if legs:
        for lx in (x0 + 40, x1 - 60):
            o.rect(lx, -180, lx + 20, 0, frame)


def d_berth(o, st, t, ob):                    # train: a blue cushioned berth
    _bench(o, (60, 94, 152, 255), (78, 116, 176, 255), (120, 120, 126, 255), -210, 210, -400)
    for x in (-110, 0, 110):
        o.line([(x, -390), (x, -215)], (44, 70, 120, 255), 4)


def d_bus_seat(o, st, t, ob):                 # bus: a maroon double seat with a steel grab bar on top
    _bench(o, (130, 40, 54, 255), (150, 50, 64, 255), (130, 130, 136, 255), -175, 175, -440)
    o.rrect(-170, -456, 170, -432, 10, (196, 198, 204, 255))


def d_metro_seat(o, st, t, ob):               # metro: a steel bench
    _bench(o, (196, 200, 208, 255), (176, 180, 190, 255), (150, 152, 160, 255), -230, 230, -300)
    for x in (-115, 0, 115):
        o.line([(x, -296), (x, -210)], (150, 154, 162, 255), 4)


def d_plane_seat(o, st, t, ob):               # plane: a tall blue seat, a white headrest cover, armrests
    _bench(o, (42, 70, 138, 255), (54, 86, 160, 255), (110, 110, 116, 255), -125, 125, -560)
    o.rrect(-85, -540, 85, -470, 14, (244, 244, 240, 255))
    for x in (-135, 112):
        o.rrect(x, -270, x + 24, -236, 8, (90, 90, 96, 255))


def d_car_seat(o, st, t, ob):                 # car: a black bucket seat with a headrest
    o.rrect(-60, -560, 60, -496, 18, (36, 36, 40, 255))
    o.line([(-30, -500), (-30, -476)], (150, 150, 156, 255), 6)
    o.line([(30, -500), (30, -476)], (150, 150, 156, 255), 6)
    _bench(o, (40, 40, 44, 255), (52, 52, 56, 255), (30, 30, 34, 255), -140, 140, -480, legs=False)
    o.rect(-120, -176, 120, 0, (30, 30, 34, 255))


def d_auto_seat(o, st, t, ob):                # auto: a black rexine bench with a yellow edge
    _bench(o, (30, 30, 32, 255), (40, 40, 42, 255), (40, 120, 70, 255), -230, 230, -330)
    o.rect(-230, -182, 230, -170, (240, 200, 40, 255))


def _oval(o, x0, y0, x1, y1, fill=None, outline=INK, w=5):
    """An ellipse given by its box (O.ellipse takes the centre and the radii)."""
    o.ellipse((x0 + x1) / 2.0, (y0 + y1) / 2.0, abs(x1 - x0) / 2.0, abs(y1 - y0) / 2.0, fill, outline, w)


def _col(ob, default):
    c = ob.get("color")
    return tuple(c) + (255,) if isinstance(c, (list, tuple)) and len(c) == 3 else default


def d_poster(o, st, t, ob):
    c = _col(ob, (230, 90, 70, 255))
    o.rect(-90, -1140, 90, -880, (250, 248, 240, 255), INK, 5)
    o.rect(-76, -1126, 76, -950, c, None)
    _oval(o, -30, -1090, 30, -1030, (255, 230, 120, 255), None)
    o.poly([(-76, -950), (-20, -1010), (30, -970), (76, -1020), (76, -950)], (60, 60, 70, 180), None)
    if ob.get("text"):
        o.text(0, -914, str(ob["text"])[:14], 30, (20, 20, 20, 255))


def d_calendar(o, st, t, ob):
    o.rect(-70, -1090, 70, -900, (252, 252, 250, 255), INK, 4)
    o.rect(-70, -1090, 70, -1050, (220, 50, 50, 255), INK, 4)
    for i in range(1, 5):
        o.line([(-60, -1050 + i * 30), (60, -1050 + i * 30)], (190, 190, 190, 255), 2)
    for j in range(1, 6):
        o.line([(-70 + j * 23, -1045), (-70 + j * 23, -905)], (190, 190, 190, 255), 2)
    _oval(o, 10, -1000, 40, -970, None, (220, 50, 50, 255), 4)            # a date circled


def d_photo_frame(o, st, t, ob):
    o.rect(-100, -1150, 100, -930, WOOD_D, INK, 5)
    o.rect(-84, -1134, 84, -946, (190, 220, 236, 255), None)
    for x, r in ((-40, 22), (0, 26), (40, 20)):                              # a family smiling
        _oval(o, x - r, -1060 - r, x + r, -1060 + r, (222, 176, 134, 255), INK, 3)
        o.rect(x - r, -1036, x + r, -950, (120, 150, 200, 255), INK, 3)


def _string(o, y, color_fn, n=16, sag=60, hw=520, kind="dot"):
    pts = [(-hw + 2 * hw * i / 30.0, y + sag * math.sin(math.pi * i / 30.0)) for i in range(31)]
    o.line(pts, (60, 60, 60, 255), 3)
    for i in range(n):
        u = (i + 0.5) / n
        x, yy = -hw + 2 * hw * u, y + sag * math.sin(math.pi * u)
        c = color_fn(i)
        if kind == "flag":
            o.poly([(x - 26, yy), (x + 26, yy), (x, yy + 52)], c, INK, 2)
        elif kind == "bead":
            for k in range(3):
                _oval(o, x - 12, yy + k * 22 - 12, x + 12, yy + k * 22 + 12, c if k % 2 == 0 else (250, 200, 60, 255), None)
        else:
            _oval(o, x - 10, yy + 4, x + 10, yy + 24, c, INK, 2)


def d_fairy_lights(o, st, t, ob):
    tw = lambda i: PARTY[(i + int(t * 3)) % len(PARTY)] if ob.get("twinkle", True) else PARTY[i % len(PARTY)]  # noqa
    _string(o, -1400, tw, n=18, sag=50)


def d_bunting(o, st, t, ob):
    cols = TIRANGA if ob.get("style") == "tiranga" else PARTY
    _string(o, -1460, lambda i: cols[i % len(cols)], n=14, sag=70, kind="flag")


def d_garland(o, st, t, ob):
    _string(o, -1520, lambda i: (246, 140, 30, 255), n=12, sag=80, kind="bead")


def d_balloons(o, st, t, ob):
    for i, (x, y) in enumerate(((-50, -1250), (30, -1280), (-5, -1200))):
        c = PARTY[(i + int(ob.get("x", 0))) % len(PARTY)]
        o.line([(x, y + 50), (0, -1000)], (90, 90, 90, 255), 2)
        _oval(o, x - 42, y - 50, x + 42, y + 50, c, INK, 3)
        _oval(o, x - 20, y - 34, x - 6, y - 14, (255, 255, 255, 120), None)


def d_banner(o, st, t, ob):
    c = _col(ob, (240, 80, 120, 255))
    o.line([(-380, -1320), (-360, -1290)], (60, 60, 60, 255), 3)
    o.line([(380, -1320), (360, -1290)], (60, 60, 60, 255), 3)
    o.rect(-360, -1300, 360, -1180, c, INK, 5)
    o.text(0, -1240, str(ob.get("text") or "")[:24], 58, (255, 255, 255, 255))


def d_ac(o, st, t, ob):
    o.rrect(-160, -1330, 160, -1220, 22, (246, 246, 244, 255), INK, 4)
    o.line([(-130, -1240), (130, -1240)], (170, 170, 170, 255), 4)
    _oval(o, 120, -1310, 134, -1296, (60, 200, 90, 255), None)


def d_wall_shelf(o, st, t, ob):
    o.rect(-160, -900, 160, -880, WOOD_D, INK, 4)
    cols = ((200, 70, 64, 255), (70, 110, 180, 255), (230, 190, 70, 255), (90, 160, 100, 255))
    x = -150
    for i in range(7):
        h = 70 + (i * 23) % 40
        o.rect(x, -900 - h, x + 26, -900, cols[i % 4], INK, 2)
        x += 30
    o.rrect(70, -980, 140, -900, 10, (236, 230, 210, 255), INK, 3)        # a jar


def d_flag_stand(o, st, t, ob):
    o.shadow(60, 12)
    o.rect(-40, -40, 40, 0, (120, 120, 126, 255), INK, 4)
    o.line([(0, -40), (0, -700)], (150, 150, 156, 255), 8)
    wave = 8 * math.sin(t * 4)
    for k, c in enumerate(TIRANGA):
        o.poly([(4, -690 + k * 50), (210, -690 + k * 50 + wave), (210, -640 + k * 50 + wave), (4, -640 + k * 50)],
               c, INK, 2)
    _oval(o, 95, -625 + wave, 125, -595 + wave, None, (0, 0, 128, 255), 3)   # the chakra


def d_umbrella(o, st, t, ob):
    c = _col(ob, (60, 120, 220, 255))
    o.shadow(100, 12)
    o.poly([(-110, -40), (-80, -200), (0, -250), (80, -200), (110, -40)], c, INK, 4)
    for x in (-55, 0, 55):
        o.line([(0, -250), (x, -40)], INK, 2)
    o.line([(0, -40), (20, 0)], (90, 70, 50, 255), 6)


def d_puddle(o, st, t, ob):
    _oval(o, -210, -30, 210, 24, (110, 150, 200, 170), None)
    r = 40 + (t * 60) % 120
    _oval(o, -r, -12 - r * 0.12, r, -12 + r * 0.12, None, (220, 236, 250, 200), 2)


BARS, BARS_L, CORRIDOR = (150, 152, 160, 255), (200, 202, 210, 255), (64, 66, 72, 255)


def d_jail_door(o, st, t, ob):
    """The jail's barred door (in the jail it sits exactly over the painted one): closed, open (swung back into the
    corridor) or broken (kicked off its hinges, lying in the corridor, the lock on the floor)."""
    o.rect(-150, -1110, 150, 0, CORRIDOR, None)
    if st == "open":
        for i in range(6):
            dx = 150 - 10 * i
            o.line([(dx, -1080 + 10 * i), (dx, -20 - 6 * i)], BARS, 12)
        for dy in (-1050, -550, -60):
            o.line([(100, dy + 40), (150, dy)], BARS, 14)
        o.rect(96, -600, 116, -520, (120, 100, 60, 255), INK, 3)
        return
    if st == "broken":
        o.line([(140, -1110), (140, -700), (112, -560)], BARS, 14)          # a bar left hanging off the hinge
        o.line([(136, -1110), (136, -700)], BARS_L, 4)
        lo, hi = (-150, -8, 150, -8), (-104, -190, 112, -190)               # the door, lying on the corridor floor
        for i in range(6):
            f = i / 5.0
            o.line([(lo[0] + (lo[2] - lo[0]) * f, lo[1]), (hi[0] + (hi[2] - hi[0]) * f, hi[1])], BARS, 12)
        for f in (0.04, 0.5, 0.96):
            ax, bx = lo[0] + (hi[0] - lo[0]) * f, lo[2] + (hi[2] - lo[2]) * f
            y = lo[1] + (hi[1] - lo[1]) * f
            o.line([(ax, y), (bx, y)], BARS, 14)
        o.poly([(-128, -40), (-82, -52), (-74, -10), (-120, 2)], (120, 100, 60, 255), INK, 3)   # the lock
        return
    for i in range(6):
        dx = -130 + 56 * i
        o.line([(dx, -1110), (dx, 0)], BARS, 16)
        o.line([(dx - 4, -1110), (dx - 4, 0)], BARS_L, 4)
    for dy in (-1070, -550, -50):
        o.line([(-150, dy), (150, dy)], BARS, 18)
    o.rect(-110, -590, -50, -500, (120, 100, 60, 255), INK, 4)


DRAW = {k: globals()["d_" + k] for k in SPEC}


# ---------------------------------------------------------------- things that lie on a surface (a desk, a bed...)
# `OBJ: desk center file chai thappa` puts them there; `A -> put bag desk` / `A -> take file` move them (the script
# and scene modules turn those into "add" / "remove" set events). The table top is at dy = -350.
SURFACE = {"table": -350, "desk": -350, "bed": -300, "khaat": -232, "sofa": -195, "bench": -205, "stool": -222,
           "box": -200, "chair": -205, "cupboard": -850, "fridge": -790, "counter": -350}
PAPER, PAPER_D = (250, 248, 238, 255), (210, 206, 190, 255)


def i_file(o, x):                  # a sarkari file: a khaki folder with papers sticking out and a string
    o.rect(x - 78, -26, x + 78, 0, (214, 184, 120, 255), INK, 4)
    for dy in (-34, -30):
        o.rect(x - 70, dy, x + 66, dy + 8, PAPER, INK, 2)
    o.line([(x, -26), (x + 8, -8), (x - 6, 0)], (180, 40, 40, 255), 3)


def i_files(o, x):                 # a pile of files
    for k, dx in enumerate((-6, 8, -2, 6, 0)):
        o.rect(x - 80 + dx, -18 * (k + 1), x + 80 + dx, -18 * k, ((214, 184, 120, 255), (190, 160, 100, 255))[k % 2],
               INK, 3)


def i_chai(o, x):                  # a cutting-chai glass
    o.poly([(x - 20, -62), (x + 20, -62), (x + 15, 0), (x - 15, 0)], (240, 236, 226, 200), INK, 3)
    o.poly([(x - 18, -44), (x + 18, -44), (x + 15, 0), (x - 15, 0)], (196, 130, 70, 255), None)


def i_thappa(o, x):                # a rubber stamp on its ink pad
    o.rect(x - 52, -14, x + 52, 0, (40, 40, 120, 255), INK, 3)
    o.rect(x - 22, -40, x + 22, -14, (120, 80, 50, 255), INK, 3)
    o.ellipse(x, -58, 18, 18, (150, 30, 30, 255), INK, 3)


def i_pathar(o, x):                # a big stone
    o.poly([(x - 62, 0), (x - 70, -30), (x - 34, -64), (x + 22, -70), (x + 66, -40), (x + 60, 0)],
           (150, 146, 140, 255), INK, 4)
    o.line([(x - 20, -46), (x + 10, -30)], (110, 106, 100, 255), 3)


def i_paperweight(o, x):           # a glass paperweight
    o.ellipse(x, -26, 30, 26, (170, 220, 240, 200), INK, 3)
    o.ellipse(x - 8, -34, 8, 6, (255, 255, 255, 220), None)


def i_notes(o, x):                 # a bundle of notes with its band
    for k in range(3):
        o.rect(x - 60, -14 * (k + 1), x + 60, -14 * k, (150, 200, 150, 255), INK, 2)
    o.rect(x - 12, -44, x + 12, 0, (240, 220, 120, 255), None)


def i_bag(o, x):                   # a big bag (the one that holds the file down)
    o.rrect(x - 90, -120, x + 90, 0, 22, (60, 60, 70, 255), INK, 5)
    o.line([(x - 40, -120), (x - 30, -160), (x + 30, -160), (x + 40, -120)], INK, 8)
    o.rect(x - 60, -80, x + 60, -60, (90, 90, 100, 255), None)


def i_laptop(o, x):
    o.poly([(x - 90, 0), (x + 90, 0), (x + 100, -10), (x - 100, -10)], (150, 154, 162, 255), INK, 3)
    o.poly([(x - 80, -10), (x + 80, -10), (x + 74, -110), (x - 74, -110)], (60, 64, 72, 255), INK, 3)
    o.poly([(x - 66, -20), (x + 66, -20), (x + 62, -100), (x - 62, -100)], (120, 190, 235, 255), None)


def i_phone(o, x):
    o.rect(x - 34, -10, x + 34, 0, (40, 44, 52, 255), INK, 2)


def i_book(o, x):
    o.rect(x - 60, -22, x + 60, 0, (180, 60, 60, 255), INK, 3)
    o.rect(x - 54, -18, x + 60, -4, PAPER, None)


def i_register(o, x):              # the clerk's big register
    o.rect(x - 90, -28, x + 90, 0, (90, 60, 40, 255), INK, 3)
    o.rect(x - 84, -24, x + 90, -6, PAPER_D, None)


def i_plate(o, x):
    o.ellipse(x, -6, 70, 12, (250, 250, 246, 255), INK, 3)
    o.ellipse(x, -14, 40, 12, (220, 160, 80, 255), None)


def i_tiffin(o, x):
    for k in range(3):
        o.rect(x - 40, -30 * (k + 1), x + 40, -30 * k, (200, 204, 210, 255), INK, 3)
    o.line([(x - 46, -96), (x - 46, -110), (x + 46, -110), (x + 46, -96)], INK, 4)


def i_bottle(o, x):
    o.rect(x - 18, -90, x + 18, 0, (170, 214, 236, 200), INK, 3)
    o.rect(x - 10, -110, x + 10, -90, (60, 120, 200, 255), INK, 2)


def i_pen_stand(o, x):
    o.rect(x - 24, -50, x + 24, 0, (60, 60, 66, 255), INK, 3)
    for dx, c in ((-10, (40, 80, 200, 255)), (4, (200, 40, 40, 255)), (12, INK)):
        o.line([(x + dx, -50), (x + dx + 4, -86)], c, 4)


def i_chalk_box(o, x):
    o.rect(x - 40, -26, x + 40, 0, (240, 240, 236, 255), INK, 3)
    for dx in (-24, -8, 8, 24):
        o.line([(x + dx, -26), (x + dx, -40)], (250, 250, 250, 255), 6)


def i_newspaper(o, x):
    o.poly([(x - 80, 0), (x + 80, 0), (x + 70, -14), (x - 70, -14)], PAPER_D, INK, 3)
    o.line([(x - 60, -8), (x + 50, -8)], (120, 120, 120, 255), 2)


def i_gift(o, x):
    o.rect(x - 50, -80, x + 50, 0, (200, 50, 80, 255), INK, 3)
    o.line([(x, -80), (x, 0)], (250, 220, 90, 255), 8)


def i_lota(o, x):
    o.ellipse(x, -36, 34, 34, (196, 140, 70, 255), INK, 3)
    o.rect(x - 14, -84, x + 14, -62, (196, 140, 70, 255), INK, 3)


def i_glass(o, x):
    o.poly([(x - 22, -70), (x + 22, -70), (x + 17, 0), (x - 17, 0)], (210, 230, 240, 170), INK, 3)


ITEMS = {k[2:]: v for k, v in list(globals().items()) if k.startswith("i_") and callable(v)}
ITEM_WORDS = {"file": "file", "files": "files", "fileon": "files", "chai": "chai", "cup": "chai", "thappa": "thappa",
              "stamp": "thappa", "mohar": "thappa", "pathar": "pathar", "patthar": "pathar", "stone": "pathar",
              "paperweight": "paperweight", "notes": "notes", "gaddi": "notes", "money": "notes", "paisa": "notes",
              "rishwat": "notes", "bag": "bag", "thaila": "bag", "laptop": "laptop", "phone": "phone",
              "mobile": "phone", "book": "book", "kitaab": "book", "register": "register", "plate": "plate",
              "tiffin": "tiffin", "bottle": "bottle", "pen_stand": "pen_stand", "pen": "pen_stand",
              "chalk": "chalk_box", "chalk_box": "chalk_box", "newspaper": "newspaper", "akhbaar": "newspaper",
              "gift": "gift", "lota": "lota", "glass": "glass"}
# what a character holds while carrying an item (the hand props of characters.py)
HELD_AS = {"file": "file", "files": "box", "chai": "chai", "thappa": "thappa", "pathar": "pathar",
           "paperweight": "pathar", "notes": "money", "bag": "bag", "laptop": "laptop", "phone": "phone",
           "book": "book", "register": "notebook", "plate": "plate", "tiffin": "tiffin", "bottle": "bottle",
           "pen_stand": "pen", "chalk_box": "chalk", "newspaper": "newspaper", "gift": "gift", "lota": "lota",
           "glass": "glass"}


def draw_items(o, typ, items, hw):
    """Lay the items out on the surface of a piece (left to right, a little apart)."""
    top = SURFACE.get(typ)
    if top is None or not items:
        return
    n = len(items)
    span = min(hw * 0.75, 70.0 * n)
    if n > 1:                                   # the newest (just put down) in the middle, where it is seen
        rest = list(items[:-1])
        mid = n // 2
        items = rest[:mid] + [items[-1]] + rest[mid:]
    for k, it in enumerate(items):
        fn = ITEMS.get(it)
        if fn is None:
            continue
        x = 0.0 if n == 1 else -span + 2 * span * k / (n - 1)
        fn(_Shift(o, top), x)


class _Shift:
    """An O that draws with dy measured from the surface (dy <= 0 above it)."""

    def __init__(self, o, top):
        self.o, self.top = o, top

    def __getattr__(self, name):
        fn = getattr(self.o, name)

        def call(*a, **k):
            if name in ("rect",):
                x0, y0, x1, y1 = a[:4]
                return fn(x0, y0 + self.top, x1, y1 + self.top, *a[4:], **k)
            if name == "rrect":
                x0, y0, x1, y1 = a[:4]
                return fn(x0, y0 + self.top, x1, y1 + self.top, *a[4:], **k)
            if name in ("poly", "line"):
                return fn([(px, py + self.top) for px, py in a[0]], *a[1:], **k)
            if name == "ellipse":
                cx, cy = a[:2]
                return fn(cx, cy + self.top, *a[2:], **k)
            return fn(*a, **k)
        return call


def obj_pos(ob, events, oid, t):
    """(x, y, direction, distance travelled) of an object at time t, following its "move" events."""
    x, y = float(ob.get("x", 540)), float(ob.get("y", 1700))
    dirn, dist = 1, 0.0
    for ev in events:
        if ev["t"] > t:
            break
        if ev.get("set") != oid or not ev.get("move"):
            continue
        m = ev["move"]
        x1, y1 = float(m.get("x", x)), float(m.get("y", y))
        dur = max(1e-3, float(m.get("dur", 2.0)))
        u = min(1.0, (t - ev["t"]) / dur)
        if m.get("ease", True):
            u = u * u * (3 - 2 * u)
        nx, ny = x + (x1 - x) * u, y + (y1 - y) * u
        if abs(x1 - x) > 1:
            dirn = 1 if x1 > x else -1
        dist += math.hypot(nx - x, ny - y)
        x, y = nx, ny
    return x, y, dirn, dist


class Sets:
    def __init__(self, objs, events, s, W, H):
        self.s, self.W, self.H = s, W, H
        self.objs = {}
        for i, ob in enumerate(objs):
            ob = dict(ob)
            ob.setdefault("id", "%s%d" % (ob.get("type", "obj"), i + 1))
            self.objs[ob["id"]] = ob
        self.events = sorted(events, key=lambda e: e["t"])
        self._cache = {}

    def pos(self, oid, t):
        return obj_pos(self.objs[oid], self.events, oid, t)

    def state(self, oid, t):
        ob = self.objs[oid]
        st = ob.get("state", "on" if ob.get("type") in ("tubelight", "fan") else "idle")
        for ev in self.events:
            if ev["t"] > t:
                break
            if ev["set"] == oid and ev.get("state") is not None:
                st = ev["state"]
        x, y, _d, _dist = self.pos(oid, t)
        return st, x, y

    def items(self, oid, t):
        """What lies on this piece at time t: its own items, then what was put down / taken away."""
        ob = self.objs[oid]
        out = list(ob.get("items", []))
        for ev in self.events:
            if ev["t"] > t:
                break
            if ev["set"] != oid:
                continue
            if ev.get("add"):
                out.append(ev["add"])
            if ev.get("remove") and ev["remove"] in out:
                out.remove(ev["remove"])
        return out

    def seat_height(self, oid):
        ob = self.objs.get(oid)
        if not ob:
            return None
        h = SPEC.get(ob.get("type"), (0, 0, 0, False, None))[4]
        return None if h is None else h * float(ob.get("scale", 1.0))

    def _image(self, ob, st, t):
        typ = ob.get("type")
        hw, h_up, h_dn, _wall, _seat, _light = SPEC[typ]
        sc = float(ob.get("scale", 1.0))
        x, y, dirn, dist = self.pos(ob["id"], t)
        animated = typ in ("clock", "fan", "tv", "tree", "bush", "phone", "chulha", "drip", "washing_machine",
                           "fairy_lights", "flag_stand", "puddle")
        items = tuple(self.items(ob["id"], t)) if typ in SURFACE else ()
        key = (ob["id"], st, items) if not animated else None
        if key and key in self._cache:
            return self._cache[key]
        extra = 180 if items else 0                     # room above the top for what lies on it
        cy = y - (h_up + extra - h_dn) * sc / 2
        p = Patch(x, cy, hw * sc + 10, (h_up + extra + h_dn) * sc / 2 + 10, self.s)
        oo = O(p, x, y, sc, bool(ob.get("flip")))
        DRAW[typ](oo, st, t, ob)
        draw_items(oo, typ, list(items), hw)
        small = p.im.reduce(p.ss)
        res = (small, (int(round(p.ox * self.s)), int(round(p.oy * self.s))))
        if key:
            self._cache[key] = res
        return res

    def wall(self, t, power=True):
        """[(image, (px, py))] of wall-mounted pieces (always behind the characters).
        power=False (lights off) switches fans and tubelights off."""
        out = []
        for oid, ob in self.objs.items():
            if SPEC.get(ob.get("type"), (0, 0, 0, False))[3]:
                st, _x, _y = self.state(oid, t)
                if not power and ob.get("type") in ("fan", "tubelight"):
                    st = "off"
                out.append(self._image(ob, st, t))
        return out

    def floor(self, t):
        """[(depth y, image, px, py)] of floor pieces, depth-sorted with the characters."""
        out = []
        for oid, ob in self.objs.items():
            if ob.get("type") in SPEC and not SPEC[ob["type"]][3]:
                st, _x, y = self.state(oid, t)
                im, (px, py) = self._image(ob, st, t)
                out.append((y, im, px, py))
        return sorted(out, key=lambda f: f[0])

    def lights_on(self, t):
        """Light-emitting pieces that are currently on: [(x, y, kind)]."""
        out = []
        for oid, ob in self.objs.items():
            typ = ob.get("type")
            if typ in SPEC and SPEC[typ][5]:
                st, x, y = self.state(oid, t)
                if (typ == "tubelight" and st != "off") or (typ != "tubelight" and st == "on"):
                    out.append((x, y, typ, float(ob.get("scale", 1.0))))
        return out

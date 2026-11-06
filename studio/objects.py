"""Placeable set pieces with states.

Scene:     "objects": [ { "id": "door1", "type": "door", "x": 880, "y": 1700, "state": "closed" },
                        { "id": "c1", "type": "chair", "x": 300, "y": 1700 } ]
Timeline:  { "t": 2.0, "object": "door1", "state": "open" }
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
    "cycle": (260, 360, 20, False, None, False),
    "bike": (290, 400, 20, False, None, False),
    "auto": (320, 790, 20, False, None, False),
    "car": (380, 600, 20, False, None, False),
    "bus": (580, 790, 20, False, None, False),
    "train": (700, 720, 20, False, None, False),
}

# Default size of each vehicle next to a (big-headed, ~860 px tall) character; "scale" multiplies this.
VEHICLE_SIZE = {"cycle": 1.3, "bike": 1.35, "auto": 1.45, "car": 1.5, "bus": 1.35, "train": 1.0}

# Riding geometry, for a vehicle facing right (x relative to the vehicle, h = height above the ground).
# seats: name -> (x, hip height). hands: (x, h) of the handlebar / steering wheel for the driver.
# feet: "crank" (pedalling around (x, h, r)) or (x, h) foot pegs; None = legs hidden inside the body.
VEHICLES = {
    "cycle": dict(seats={"driver": (-40, 262), "back": (-150, 250)}, hands=(122, 312), feet=("crank", 10, 76, 46),
                  enclosed=False, wheels=((-150, 70), (150, 70))),
    "bike": dict(seats={"driver": (-30, 280), "back": (-140, 288)}, hands=(150, 350), feet=(10, 110),
                 enclosed=False, wheels=((-175, 76), (175, 76))),
    "auto": dict(seats={"driver": (80, 250), "passenger": (-150, 240), "back": (-150, 240)}, hands=(200, 330),
                 feet=None, enclosed=True, wheels=((-170, 62), (220, 56))),
    "car": dict(seats={"driver": (70, 196), "passenger": (-110, 196), "back": (-110, 196)}, hands=(170, 290),
                feet=None, enclosed=True, wheels=((-215, 62), (215, 62))),
    "bus": dict(seats={"driver": (430, 330), "passenger": (100, 330), "back": (-250, 330)}, hands=(520, 410),
                feet=None, enclosed=True, wheels=((-360, 72), (360, 72))),
    "train": dict(seats={}, hands=None, feet=None, enclosed=True, wheels=()),
}
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


def _wheel(o, x, r, ang, hub=(170, 170, 176, 255)):
    o.ellipse(x, -r, r, r, (40, 40, 44, 255), INK, 5)
    o.ellipse(x, -r, r * 0.62, r * 0.62, hub, INK, 4)
    for i in range(3):
        a = ang + i * math.pi / 3
        o.line([(x - r * 0.6 * math.cos(a), -r - r * 0.6 * math.sin(a)),
                (x + r * 0.6 * math.cos(a), -r + r * 0.6 * math.sin(a))], (90, 90, 96, 255), 4)


def d_cycle(o, st, t, ob):
    ang = ob.get("_wheel", 0.0)
    c = tuple(ob.get("color", (200, 50, 50))) + (255,)
    o.shadow(230, 16)
    for x in (-150, 150):
        o.ellipse(x, -70, 70, 70, None, (40, 40, 44, 255), 10)
        for i in range(4):
            a = ang + i * math.pi / 4
            o.line([(x - 64 * math.cos(a), -70 - 64 * math.sin(a)), (x + 64 * math.cos(a), -70 + 64 * math.sin(a))],
                   (150, 150, 156, 255), 2)
    crank = (10, -76)
    o.line([(-150, -70), crank, (-40, -240), (-150, -70)], c, 9)
    o.line([crank, (110, -250), (-40, -240)], c, 9)
    o.line([(110, -250), (150, -70)], c, 9)
    o.line([(110, -250), (122, -312), (90, -322)], INK, 7)
    o.rect(-80, -262, 0, -244, (40, 40, 44, 255), INK, 3)
    ca = ang * 1.6
    o.line([(crank[0] - 46 * math.cos(ca), crank[1] - 46 * math.sin(ca)),
            (crank[0] + 46 * math.cos(ca), crank[1] + 46 * math.sin(ca))], (60, 60, 64, 255), 7)


def d_bike(o, st, t, ob):
    ang = ob.get("_wheel", 0.0)
    c = tuple(ob.get("color", (40, 90, 170))) + (255,)
    o.shadow(260, 18)
    _wheel(o, -175, 76, ang)
    _wheel(o, 175, 76, ang)
    o.poly([(-200, -150), (-60, -140), (60, -170), (120, -150), (100, -110), (-170, -100)], (70, 70, 76, 255))
    o.poly([(-120, -250), (40, -250), (60, -200), (-110, -190)], (40, 40, 44, 255))         # seat
    o.poly([(30, -270), (130, -270), (140, -200), (40, -190)], c)                            # tank
    o.line([(120, -260), (175, -76)], (90, 90, 96, 255), 10)
    o.line([(120, -280), (150, -350), (110, -360)], INK, 8)
    o.ellipse(170, -290, 24, 20, (250, 236, 150, 255))
    o.poly([(-230, -170), (-150, -170), (-160, -140), (-240, -150)], c)                       # rear fender


def d_auto(o, st, t, ob):
    ang = ob.get("_wheel", 0.0)
    o.shadow(300, 20)
    yel, grn = (250, 210, 50, 255), (40, 140, 80, 255)
    o.poly([(-280, -770), (180, -770), (230, -640), (-280, -640)], (30, 30, 34, 255))         # canopy
    o.line([(-270, -640), (-270, -300)], (30, 30, 34, 255), 12)
    o.line([(170, -640), (210, -300)], (30, 30, 34, 255), 10)
    o.poly([(-290, -300), (-30, -300), (-30, -110), (-290, -110)], grn)                       # rear body
    o.poly([(-30, -300), (180, -300), (250, -240), (250, -110), (-30, -110)], yel)            # front cowl
    o.line([(-30, -300), (-30, -110)], INK, 5)
    o.ellipse(240, -200, 18, 16, (250, 236, 150, 255))
    _wheel(o, -170, 62, ang)
    _wheel(o, 220, 56, ang)


def d_car(o, st, t, ob):
    ang = ob.get("_wheel", 0.0)
    c = tuple(ob.get("color", (210, 60, 60))) + (255,)
    o.shadow(340, 20)
    o.poly([(-230, -290), (-170, -570), (130, -570), (210, -290)], (180, 220, 240, 70), INK, 6)   # glass
    o.line([(-30, -570), (-20, -290)], c, 14)
    o.line([(-170, -570), (-230, -290)], c, 12)
    o.line([(130, -570), (210, -290)], c, 12)
    o.line([(-170, -570), (130, -570)], c, 14)
    o.poly([(-340, -290), (330, -290), (360, -200), (350, -90), (-350, -90), (-360, -200)], c)
    o.line([(-20, -280), (-20, -100)], INK, 4)
    o.ellipse(340, -230, 18, 14, (250, 236, 150, 255))
    o.rect(-360, -230, -334, -200, (220, 60, 50, 255), INK, 3)
    _wheel(o, -215, 62, ang)
    _wheel(o, 215, 62, ang)


def d_bus(o, st, t, ob):
    ang = ob.get("_wheel", 0.0)
    c = tuple(ob.get("color", (60, 120, 200))) + (255,)
    o.shadow(560, 24)
    o.rect(-560, -780, 560, -110, c, INK, 7)
    o.rect(-560, -260, 560, -230, (250, 250, 250, 255), None)
    for i in range(6):
        x = -520 + i * 150
        o.rect(x, -730, x + 120, -460, (180, 220, 240, 70), INK, 4)
    o.rect(440, -730, 540, -380, (180, 220, 240, 70), INK, 4)                                # windshield
    o.rect(380, -440, 430, -120, (60, 70, 90, 255), INK, 4)                                  # door
    o.ellipse(540, -180, 20, 16, (250, 236, 150, 255))
    _wheel(o, -360, 72, ang)
    _wheel(o, 360, 72, ang)


def d_train(o, st, t, ob):
    n = int(ob.get("coaches", 4))
    c = tuple(ob.get("color", (150, 50, 40))) + (255,)
    o.rect(-60, -40, 0, 0, None, None)
    for i in range(n + 1):
        x1 = 600 - i * 1240
        x0 = x1 - 1200
        if i == 0:                                         # engine
            o.poly([(x0, -680), (x1 - 160, -680), (x1, -520), (x1, -80), (x0, -80)], (60, 70, 110, 255), INK, 7)
            o.rect(x1 - 300, -620, x1 - 170, -470, (180, 220, 240, 255), INK, 5)
            o.ellipse(x1 - 30, -200, 26, 22, (250, 236, 150, 255))
        else:
            o.rect(x0, -680, x1, -80, c, INK, 7)
            for j in range(7):
                wx = x0 + 60 + j * 160
                o.rect(wx, -600, wx + 110, -460, (180, 220, 240, 255), INK, 4)
            o.rect(x0 + 20, -330, x1 - 20, -300, (240, 200, 80, 255), None)
        for wx in (x0 + 140, x0 + 300, x1 - 300, x1 - 140):
            o.ellipse(wx, -60, 56, 56, (40, 40, 44, 255), INK, 5)
        o.rect(x1, -260, x1 + 40, -220, (40, 40, 44, 255), INK, 3)


DRAW = {k: globals()["d_" + k] for k in SPEC}


def obj_pos(ob, events, oid, t):
    """(x, y, direction, distance travelled) of an object at time t, following its "move" events."""
    x, y = float(ob.get("x", 540)), float(ob.get("y", 1700))
    dirn, dist = 1, 0.0
    for ev in events:
        if ev["t"] > t:
            break
        if ev["object"] != oid or not ev.get("move"):
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


class Objects:
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
            if ev["object"] == oid and ev.get("state") is not None:
                st = ev["state"]
        x, y, _d, _dist = self.pos(oid, t)
        return st, x, y

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
        vehicle = typ in VEHICLES
        animated = vehicle or typ in ("clock", "fan", "tv", "tree", "bush", "phone")
        key = (ob["id"], st) if not animated else None
        if key and key in self._cache:
            return self._cache[key]
        cy = y - (h_up - h_dn) * sc / 2
        if typ == "train":                     # very long: draw only what is on screen, no supersampling
            p = Patch(540, cy, 620, (h_up + h_dn) * sc / 2 + 10, self.s, 1)
        else:
            p = Patch(x, cy, hw * sc + 10, (h_up + h_dn) * sc / 2 + 10, self.s)
        flip = bool(ob.get("flip")) != (dirn < 0)
        if vehicle:
            wr = VEHICLES[typ]["wheels"][0][1] if VEHICLES[typ]["wheels"] else 60
            ob = dict(ob, _wheel=-dist / max(1.0, wr * sc) * (-1 if flip else 1))
        DRAW[typ](O(p, x, y, sc, flip), st, t, ob)
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
        """[(depth y, image, px, py)] of floor pieces, depth-sorted like foreground props.
        Enclosed vehicles sort just in front of their riders, cycles/bikes just behind them."""
        out = []
        for oid, ob in self.objs.items():
            if ob.get("type") in SPEC and not SPEC[ob["type"]][3]:
                st, _x, y = self.state(oid, t)
                im, (px, py) = self._image(ob, st, t)
                v = VEHICLES.get(ob["type"])
                depth = y + (2.0 if v and v["enclosed"] else -0.5 if v else 0.0)   # riders stand at y + 1
                out.append((depth, im, px, py))
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

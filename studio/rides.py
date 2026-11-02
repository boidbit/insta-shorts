"""Characters riding vehicles: where they sit, how their arms / legs reach the handles and pedals (2-link IK),
and the hop onto / off the vehicle.

    A -> ride bike              A hops on the bike (it is created next to A if it is not in the scene yet)
    B -> ride truck back        B takes the second seat (default seat: the driver's)
    A -> getoff                 A hops off, on the side of the screen centre (or `getoff left` / `getoff right`)

All numbers below are in the vehicle's own units (the sprite drawn at scale 1, facing right, ground at y = 0, up is
negative). A rider is the normal character, drawn small (`r` = size relative to a standing character) and posed so that
the hands are on the handlebar and the feet on the pedals / pegs.
"""
import math

from .characters import DEFAULT_POSE, LA, SH, TH, UA, skeleton
from .util import clamp, ease_in_out, lerp

RIDE_HOP = 0.6                                  # seconds a hop onto / off a vehicle takes
SHOULDER = {"L": (-56.0, -268.0), "R": (56.0, -268.0)}
ARM_K = 1.35                                    # riders' arms are this much longer, so they reach the handlebar
HIP = {"L": (-32.0, 0.0), "R": (32.0, 0.0)}

# seat = hip position, rider size r, hands [near, far] (or None = rest on the lap), feet [near, far] or "pedals"
RIDES = {
    "bike": {"driver": dict(hip=(-34, -146), r=0.42, hands=[(100, -204), (94, -202)], feet=[(34, -62), (26, -60)]),
             "back": dict(hip=(-112, -146), r=0.4, hands=[(-62, -178), (-66, -172)], feet=[(-4, -66), (-12, -64)])},
    "scooter": {"driver": dict(hip=(-30, -186), r=0.42, hands=[(76, -236), (70, -234)], feet=[(30, -98), (22, -96)])},
    "cycle": {"driver": dict(hip=(-6, -186), r=0.42, hands=[(90, -208), (84, -206)], feet="pedals")},
    "auto": {"driver": dict(hip=(72, -134), r=0.24, hands=[(116, -206), (108, -204)], feet=[(118, -70), (108, -68)]),
             "back": dict(hip=(-90, -134), r=0.24, hands=[(-62, -160), (-66, -156)], feet=[(-40, -70), (-50, -68)])},
    "car": {"driver": dict(hip=(66, -80), r=0.2, hands=[(108, -96), (102, -94)], feet=[(96, -52), (88, -50)]),
            "back": dict(hip=(-52, -80), r=0.2, hands=None, feet=[(-18, -52), (-26, -50)])},
    "truck": {"driver": dict(hip=(204, -96), r=0.24, hands=[(246, -110), (240, -108)], feet=[(240, -64), (232, -62)]),
              "back": dict(hip=(146, -96), r=0.24, hands=None, feet=[(182, -64), (174, -62)])},
}
# how big a vehicle is when somebody rides it (so the rider is not tiny next to a standing character)
RIDE_SCALE = {"bike": 1.8, "scooter": 1.8, "cycle": 1.8, "auto": 1.6, "car": 1.5, "truck": 1.3}
HALF_LENGTH = {"bike": 170, "scooter": 150, "cycle": 170, "auto": 190, "car": 260, "truck": 320}
CRANK = dict(bb=(0, -58), length=40)


def rideable(kind):
    return kind in RIDES


def seat_for(kind, seat):
    seats = RIDES[kind]
    return seats.get(seat) or seats["driver"]


def crank_angle(obj, t):
    """Angle of the right pedal (radians): the crank turns as the cycle rolls; it rests at a fixed angle when parked."""
    return obj.x_at(t) / (60.0 * obj.scale) * 0.5 + 0.5


def _ik(origin, target, l1, l2, bend):
    """Two-link IK in the skeleton's convention (angle 0 = down, +90 = right). bend=+1: the middle joint (knee)
    points forward / up, bend=-1: elbow down / back. Returns (angle1, angle2) in degrees."""
    dx, dy = target[0] - origin[0], target[1] - origin[1]
    d = clamp(math.hypot(dx, dy), abs(l1 - l2) + 1e-3, l1 + l2 - 1e-3)
    theta = math.degrees(math.atan2(dx, dy))
    cos_phi = clamp((l1 * l1 + d * d - l2 * l2) / (2.0 * l1 * d), -1.0, 1.0)
    a1 = theta + bend * math.degrees(math.acos(cos_phi))
    ex = origin[0] + l1 * math.sin(math.radians(a1))
    ey = origin[1] + l1 * math.cos(math.radians(a1))
    a2 = math.degrees(math.atan2(target[0] - ex, target[1] - ey))
    return a1, a2


def _rel(pt, seat, o_scale=None):
    """A point of the vehicle (its own units) -> skeleton units relative to the rider's hip. (World distance is
    local * obj.scale and the rider is r * obj.scale big, so the vehicle's scale cancels out.)"""
    return ((pt[0] - seat["hip"][0]) / seat["r"], (pt[1] - seat["hip"][1]) / seat["r"])


def mirror_pose(p):
    """The same pose seen from the other side (the vehicle drives to the left)."""
    q = dict(p)
    for a, b in (("la1", "ra1"), ("la2", "ra2"), ("ll1", "rl1"), ("ll2", "rl2")):
        q[a], q[b] = -p[b], -p[a]
    for k in ("tilt", "head_tilt", "shift", "look_x"):
        q[k] = -p.get(k, 0.0)
    return q


def ride_pose(obj, seat, t):
    """Pose of a rider sitting in `seat` of `obj` at time t, for a vehicle facing right."""
    pose = dict(DEFAULT_POSE)
    hands = seat.get("hands")
    if hands:
        pose["arm_k"] = ARM_K
        pose["la1"], pose["la2"] = _ik(SHOULDER["L"], _rel(hands[1], seat), UA * ARM_K, LA * ARM_K, -1)
        pose["ra1"], pose["ra2"] = _ik(SHOULDER["R"], _rel(hands[0], seat), UA * ARM_K, LA * ARM_K, -1)
    else:                                                       # hands resting on the knees
        pose.update(la1=-8, la2=14, ra1=8, ra2=-14)
    feet = seat["feet"]
    if feet == "pedals":
        a = crank_angle(obj, t)
        bb = CRANK["bb"]
        near = (bb[0] + CRANK["length"] * math.cos(a), bb[1] + CRANK["length"] * math.sin(a))
        far = (bb[0] - CRANK["length"] * math.cos(a), bb[1] - CRANK["length"] * math.sin(a))
        feet = [near, far]
    pose["ll1"], pose["ll2"] = _ik(HIP["L"], _rel(feet[1], seat), TH, SH, +1)
    pose["rl1"], pose["rl2"] = _ik(HIP["R"], _rel(feet[0], seat), TH, SH, +1)
    pose["look_x"] = 0.55
    return pose


def _lerp_pose(a, b, e):
    out = dict(b)
    for k, v in a.items():
        if isinstance(v, (int, float)) and isinstance(b.get(k), (int, float)):
            out[k] = lerp(v, b[k], e)
    return out


_STAND_FY = skeleton(DEFAULT_POSE)["fy"]


def frame(c, t):
    """None if the character is not on a vehicle at time t, else a dict:
    x, y (feet, where the character is drawn), scale, pose, obj (the vehicle), phase, hip (world)."""
    if not c.rides:
        return None
    r = c.ride_at(t)
    if r is None:
        return None
    ride, phase, p = r
    obj = c.world.get(ride["obj"])
    if obj is None or not obj.visible(t) and phase == "riding":
        return None
    seat = seat_for(obj.kind, ride["seat"])
    flip = obj.flip_at(t)
    sgn = -1.0 if flip else 1.0
    rs = seat["r"] * obj.scale
    seat_hip = (obj.x_at(t) + sgn * seat["hip"][0] * obj.scale,
                obj.y + obj.bob_at(t) + seat["hip"][1] * obj.scale)
    pose = ride_pose(obj, seat, t)
    if flip:
        pose = mirror_pose(pose)
    scale, hip = rs, seat_hip
    if phase in ("on", "off"):
        e = ease_in_out(p)
        if phase == "on":
            gx, gy, gscale = c.ground_state(ride["t0"])
        else:
            gx, gy, gscale = ride["land_x"], ride["land_y"], c.scale * ride.get("land_k", 1.0)
        stand_hip = (gx, gy - _STAND_FY * gscale)
        stand_pose = dict(DEFAULT_POSE)
        if phase == "on":
            a_hip, b_hip, a_scale, b_scale, a_pose, b_pose = stand_hip, seat_hip, gscale, rs, stand_pose, pose
        else:
            a_hip, b_hip, a_scale, b_scale, a_pose, b_pose = seat_hip, stand_hip, rs, gscale, pose, stand_pose
        hop = math.sin(math.pi * e) * 150.0 * lerp(a_scale, b_scale, e) / 0.5
        hip = (lerp(a_hip[0], b_hip[0], e), lerp(a_hip[1], b_hip[1], e) - hop)
        scale = lerp(a_scale, b_scale, e)
        pose = _lerp_pose(a_pose, b_pose, e)
    fy = skeleton(pose)["fy"]
    return dict(x=hip[0], y=hip[1] + fy * scale, scale=scale, pose=pose, obj=obj, phase=phase, hip=hip, seat=seat,
                inside=(phase == "riding" or (phase == "on" and p >= 0.5) or (phase == "off" and p < 0.5)))

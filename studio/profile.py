"""A person seen from the side (profile): used when somebody turns to the one they talk to (`A -> side`, and the
counter conversations: the customer facing the shopkeeper).

The body is the same person (skin, hair, clothes, build, height, face parts, props) drawn turned: the legs one in
front of the other, the far arm behind the body, one eye, the nose sticking out, the ear in the middle of the head,
the hair over the back of it. The poses of the actions still work: an arm the front view raises to the side is
raised forward, the legs of a walk swing forward and back."""
import math

from .characters import (ARM_W, BLUSH, BROW_STYLES, BUILDS, EAR_STYLES, EXPRESSIONS, FACE, FACE_SHAPES, GOLD,
                         HAIR_COLORS, HAIR_TOP, HEAD_RX, HEAD_RY, HEAD_SCALE, INK, LA, LEG_W, MOUTH_IN, NECK_H,
                         NO_BLINK, OUTLINE, SH, TEAR, TEARS, TH, TONGUE, TORSO_H, UA, WHITE, Sketch, _draw_prop,
                         _hand, _mix, add, bezier, closed_ellipse, color_of, ellipse_pts, rot, shade, vec)

LONG_HAIR = ("long", "braid", "bun", "ponytail", "bob", "two_plaits", "side_braid", "curly_open")


def draw_side(o, p, cols, expr, mouth_open, t, x0, ground_y, k, blink=False, prop=None, talking=False,
              tear_phase=0.0, f=1):
    """(ops, anchors) of the person `o` (resolved spec) seen from the side, facing right (f=1) or left (f=-1)."""
    f = 1 if f >= 0 else -1
    outfit = o.get("outfit", "tshirt")
    build = o.get("build", "normal")
    bw, belly = BUILDS.get(build, BUILDS["normal"])
    skin, main, accent, pants = cols["skin"], cols["main"], cols["accent"], cols["pants"]
    hair = o.get("hair", "short")
    hcol = color_of(o.get("hair_color", "black"), "black", HAIR_COLORS)
    acc = o.get("accessories", [])
    lk = float(o.get("leg_k", 1.0))
    sitting = p.get("th_k", 1.0) < 0.6

    # ---- joints (hips at 0, 0; x towards where the person faces) ----
    def A(a):                                  # a front-view angle -> the same swing forward / back
        return f * a

    th, sh_ = TH * lk, SH * lk
    if sitting:                                # the thighs point forward: the seat shows from the side
        thigh_n, thigh_f, shin_n, shin_f = A(86), A(80), A(4), A(-4)
    else:
        thigh_n, thigh_f = A(p["rl1"]), A(p["ll1"])
        shin_n, shin_f = A(p["rl2"]), A(p["ll2"])
    hip = (0.0, 0.0)
    knee_n, knee_f = add(hip, vec(thigh_n, th)), add(hip, vec(thigh_f, th))
    foot_n, foot_f = add(knee_n, vec(shin_n, sh_)), add(knee_f, vec(shin_f, sh_))
    fy = max(foot_n[1], foot_f[1]) + 12
    S = Sketch(x0, ground_y, k, p["tilt"], p["shift"], p["lift"], fy, p.get("dx", 0.0))

    top = -TORSO_H + 6
    shoulder = (f * 4.0, -TORSO_H + 34)
    def fwd(a, lo=-30.0):                      # an arm swings back only a little (no twisted shoulders)
        return f * max(lo, a)
    ua_n = fwd(p["ra1"] - 10)
    fa_n = fwd(p["ra2"] - 2, -40.0)
    ua_f = fwd(p["la1"] + 10)
    fa_f = fwd(p["la2"] + 6, -40.0)
    elb_n = add(shoulder, vec(ua_n, UA * p.get("arm_k", 1.0)))
    hand_n = add(elb_n, vec(fa_n, LA * p.get("arm_k", 1.0)))
    elb_f = add(shoulder, vec(ua_f, UA * p.get("arm_k", 1.0)))
    hand_f = add(elb_f, vec(fa_f, LA * p.get("arm_k", 1.0)))
    hc = add((f * 6.0, -TORSO_H + 4), rot((0.0, -(NECK_H + HEAD_RY * 0.8 * HEAD_SCALE)), math.radians(p["head_tilt"])))
    hc = (hc[0] + p.get("head_dx", 0.0) * f, hc[1] + p.get("head_dy", 0.0))

    long_top = outfit in ("kurta", "salwar", "kurta_jacket")
    hem = {"vest": 10, "blazer": 30, "kurta": 130, "kurta_jacket": 130, "salwar": 120}.get(outfit, 18)

    def X(pts):                                # profile points drawn for f=1 -> mirrored for f=-1
        return [(f * x, y) for x, y in pts]

    # ---- the far arm, behind everything ----
    far_skin, far_main = shade(skin, 0.86), shade(main, 0.84)
    S.limb([shoulder, elb_f, hand_f], [ARM_W, ARM_W - 3, ARM_W - 7], far_skin)
    _side_sleeve(S, outfit, shoulder, elb_f, hand_f, far_main)
    _hand(S, hand_f, fa_f, "L" if f > 0 else "R", far_skin)

    # ---- legs and feet ----
    if outfit != "saree":
        w = LEG_W + (10 if outfit == "salwar" else 0)
        S.limb([hip, knee_f, add(foot_f, (0, -10))], [w + 4, w, w - 5], shade(pants, 0.86))
        S.limb([hip, knee_n, add(foot_n, (0, -10))], [w + 4, w, w - 5], pants)
    for foot, dark in ((foot_f, True), (foot_n, False)):
        _side_foot(S, foot, f, o.get("shoes", "black"), shade(skin, 0.86) if dark else skin, dark)

    # ---- neck, body, clothes ----
    S.tube([(f * 4, top + 20), add(hc, (0, HEAD_RY * 0.55 * HEAD_SCALE))], 30, skin)
    back_x, front_x = -44 * bw, 50 * bw
    if outfit == "saree":
        foot_y = fy - 30
        skirt = X([(back_x - 2, -120), (back_x - 12, foot_y), (front_x + 22, foot_y), (front_x + belly * 0.8, -120)])
        S.poly(skirt, main, INK, OUTLINE)
        S.line(X([(back_x - 8, foot_y - 12), (front_x + 18, foot_y - 12)]), 12, accent)
        S.poly(X(_torso(top, -118, back_x, front_x, belly * 0.6)), skin, INK, OUTLINE)       # the midriff
        S.poly(X(_torso(top, -190, back_x, front_x, 0)), accent, INK, OUTLINE)            # the blouse
        S.poly(X([(front_x + 4, -126), (front_x - 6, top + 70), (8, top - 2), (back_x - 6, top + 10),
                  (back_x - 30, -30), (back_x - 8, -40), (back_x + 4, top + 60)]), main, INK, OUTLINE)   # pallu
    else:
        body = _torso(top, hem, back_x - (6 if long_top else 0), front_x + (8 if long_top else 0), belly)
        S.poly(X(body), main, INK, OUTLINE)
        if outfit == "stripes":
            for y in range(int(top + 34), int(hem - 8), 44):
                S.line(X([(back_x + 4, y), (front_x + belly * 0.5 - 2, y)]), 18, WHITE)
            S.poly(X(body), None, INK, OUTLINE)
        if outfit == "kurta_jacket":
            S.poly(X(_torso(top - 2, -36, back_x - 2, front_x + 2, belly)), accent, INK, OUTLINE)
        if outfit in ("shirt", "uniform", "kurta"):
            S.line(X([(front_x - 6, top + 14), (front_x + belly * 0.4 - 6, min(hem - 6, top + 160))]), 4,
                   shade(main, 0.72))
            S.poly(X([(4, top + 2), (24, top - 6), (30, top + 22)]), shade(main, 1.05), INK, 4)   # the collar
        if outfit == "blazer":
            S.poly(X([(front_x - 2, top + 8), (front_x + 2, top + 116), (14, top + 6)]), WHITE, INK, 4)
            S.line(X([(18, top + 4), (front_x - 6, top + 70), (front_x + belly * 0.4, top + 130)]), 5)
        if outfit == "vest":
            S.poly(X([(6, top - 2), (front_x - 2, top + 4), (front_x - 8, top + 50)]), skin, INK, 4)
        if outfit == "salwar":                 # the dupatta down the back
            S.tube(X([(back_x + 4, top + 10), (back_x - 16, -30)]), 26, accent)

    # ---- the near arm, its hand and what it holds ----
    S.limb([shoulder, elb_n, hand_n], [ARM_W, ARM_W - 3, ARM_W - 7], skin)
    _side_sleeve(S, outfit, shoulder, elb_n, hand_n, main)
    _hand(S, hand_n, fa_n, "R" if f > 0 else "L", skin, finger=bool(p.get("finger")))
    held = [(nm, hs) for nm, hs in (p.get("props") or [])]
    if prop:
        held.append((prop, "R"))
    for nm, _side in held:
        if nm == "vlog_cam":                   # the selfie stick held up over the head, the camera turned to the face
            top_ = (hc[0] - f * 70, hc[1] - HEAD_RY * HEAD_SCALE - 60)
            S.line([hand_n, top_], 10, (40, 40, 46))
            S.poly([(top_[0] - 40, top_[1] - 26), (top_[0] + 40, top_[1] - 26), (top_[0] + 40, top_[1] + 26),
                    (top_[0] - 40, top_[1] + 26)], (40, 42, 48), INK, 5)
            S.dot((top_[0] + f * 40, top_[1]), 14, (24, 24, 28), (150, 150, 160), 4)
            continue
        _draw_prop(S, nm, add(hand_n, vec(fa_n, 11)), fa_n, main)

    # ---- the head ----
    shape = o.get("face", "oval")
    sx, sy = FACE_SHAPES.get(shape, (1.0, 1.0))

    def HH(q):
        return (hc[0] + f * q[0] * HEAD_SCALE * sx, hc[1] + q[1] * HEAD_SCALE * sy)

    def HF(q):
        return (hc[0] + f * q[0] * FACE * HEAD_SCALE, hc[1] + q[1] * FACE * HEAD_SCALE)

    def hline(pts, w, col=INK):
        S.line([HF(q) for q in pts], w * FACE * HEAD_SCALE, col)

    def hpoly(pts, fill=None, outline=None, w=OUTLINE):
        S.poly([HF(q) for q in pts], fill, outline, w * FACE * HEAD_SCALE)

    covered = "turban" in acc or "cap" in acc or "beanie" in acc
    if not covered:
        _hair_behind(S, HH, hair, hcol, accent)
    S.poly([HH(q) for q in closed_ellipse(0, 0, HEAD_RX * 1.02, HEAD_RY, 64)], skin, INK, OUTLINE + 1)
    nose_tip = 116 + {"long": 8, "big": 4, "button": -8}.get(o.get("nose"), 0)
    hpoly([(84, -6), (nose_tip, 24), (88, 32)], skin, None)                       # the nose
    hline([(92, -4), (nose_tip, 24), (90, 32)], 5)
    erx, ery = EAR_STYLES.get(o.get("ears"), (14, 21))
    S.poly([HH(q) for q in closed_ellipse(-8, 10, erx, ery, 20)], skin, INK, 5)
    S.line([HH(q) for q in ellipse_pts(-8, 10, erx * 0.5, ery * 0.55, 8, -60, 120)], 3, shade(skin, 0.7))

    eyes, mouth, brows = EXPRESSIONS.get(expr, EXPRESSIONS["neutral"])
    if blink and eyes not in NO_BLINK:
        eyes = "closed"
    ex, ey = 52.0, -6.0
    look = 4.0 * max(-1.0, min(1.0, p.get("look_y", 0.0)))
    if eyes in ("wide",) or o.get("eyes") in ("big", "round", "almond"):
        r = 15 if eyes == "wide" else 12
        hpoly(closed_ellipse(ex, ey, r * 0.85, r, 20), WHITE, INK, 4)
        hpoly(closed_ellipse(ex + 4, ey + look, 7.5, 8.5, 14), INK, None)
    elif eyes in ("happy",):
        hline(ellipse_pts(ex, ey + 8, 13, 11, 10, 200, 340), 6)
    elif eyes in ("relaxed", "closed", "half"):
        hline(ellipse_pts(ex, ey - 2, 12, 7, 10, 15, 165), 6)
    elif eyes == "x":
        hline([(ex - 9, ey - 9), (ex + 9, ey + 9)], 6)
        hline([(ex - 9, ey + 9), (ex + 9, ey - 9)], 6)
    elif eyes == "heart":
        hpoly(closed_ellipse(ex, ey, 11, 10, 16), (214, 50, 70), INK, 3)
    else:
        r = 7.5 if o.get("eyes") in ("small", "narrow", "sleepy") else 10.0
        hpoly(closed_ellipse(ex + 1, ey + look, r * 0.85, r * 1.15, 18), INK, None)
        hpoly(closed_ellipse(ex - 1, ey - 4 + look, 3, 3, 10), WHITE, None)
    if o.get("lashes") and eyes not in ("x", "heart"):
        for j in range(2):
            hline([(ex + 6 + 5 * j, ey - 11), (ex + 14 + 6 * j, ey - 18 + 2 * j)], 4)
    bc = hcol if hcol != HAIR_COLORS["white"] else (150, 150, 150)
    bwid = BROW_STYLES.get(o.get("brows"), 9)
    back_y, front_y = {"angry": (-40, -22), "sad": (-26, -42), "up": (-44, -46)}.get(brows, (-30, -32))
    hline([(ex - 20, ey + back_y + 6), (ex + 18, ey + front_y + 6)], bwid, bc)

    if expr in BLUSH or o.get("cheeks") == "blush":
        hpoly(closed_ellipse(44, 32, 16, 8, 14), (240, 150, 160), None)
    if expr in TEARS:
        ty = ey + 14 + ((tear_phase % 1.0) * 60)
        hpoly(closed_ellipse(ex - 2, ty, 6, 10, 12), TEAR, INK, 3)
    marks = o.get("marks") or ()
    marks = [marks] if isinstance(marks, str) else marks
    line_c = shade(skin, 0.68)
    if "age_lines" in marks:
        for y in (-64, -76):
            hline([(30, y), (48, y - 3), (66, y)], 3, line_c)
        hline([(ex - 18, ey - 2), (ex - 28, ey + 6)], 3, line_c)
        hline(bezier((70, 28), (58, 44), (60, 62), 8), 3.5, line_c)
    if "mole" in marks:
        hpoly(closed_ellipse(60, 40, 4.5, 4.5, 10), (70, 46, 36), None)
    if "freckles" in marks:
        for (x, y) in ((60, 18), (70, 22), (52, 24), (64, 28)):
            hpoly(closed_ellipse(x, y, 2.3, 2.3, 8), shade(skin, 0.72), None)

    # beard under the mouth (the mouth shows on it)
    beard = "none" if o.get("shave") else (o.get("beard") or ("full" if "beard" in acc else "none"))
    if beard in ("full", "stubble"):                   # a band along the jaw, from the ear round the chin
        col = hcol if beard == "full" else _mix(skin, hcol, 0.3)
        outer = ellipse_pts(0, 0, 98 * sx, 113 * sy, 18, 112, 22)
        inner = ellipse_pts(4, -6, 74 * sx, 84 * sy, 18, 22, 112)
        hpoly(outer + inner, col, INK if beard == "full" else None, 4)
        hpoly(closed_ellipse(70, 56, 20, 15, 16), skin, None)
    elif beard == "goatee":
        hpoly(closed_ellipse(70, 86, 18, 16, 16), hcol, INK, 3)

    # mouth
    my = 54.0
    if talking:
        if mouth_open > 0.1:
            mouth = "talk"
        elif mouth in ("open", "shout", "laugh", "grin", "o", "open_small"):
            mouth = "smile"
    lips = o.get("lips") or ("full" if o.get("lip_color") else "normal")
    if mouth in ("talk", "open", "shout", "laugh", "o", "yawn", "open_small"):
        a = {"talk": max(0.0, min(1.0, mouth_open)), "open": 0.8, "shout": 1.0, "laugh": 1.0, "o": 0.6,
             "yawn": 1.0, "open_small": 0.4}[mouth]
        hpoly(closed_ellipse(70, my + 4 + 6 * a, 10 + 6 * a, 5 + 16 * a, 18), MOUTH_IN, INK, 5)
        if a > 0.5:
            hpoly(closed_ellipse(72, my + 8 + 10 * a, 7, 5 * a, 12), TONGUE, None)
    elif mouth == "grin":
        hpoly([(54, my - 2), (86, my - 6)] + ellipse_pts(70, my - 2, 16, 14, 10, 0, 180)[::-1], WHITE, INK, 5)
    elif mouth in ("smile", "smirk"):
        hline(bezier((52, my - 2), (66, my + 12), (86, my - 8), 10), 6)
    elif mouth == "frown":
        hline(bezier((54, my + 8), (68, my - 4), (84, my + 6), 10), 6)
    elif mouth == "wavy":
        hline([(54 + i * 6, my + (3 if i % 2 else -3)) for i in range(6)], 5)
    else:
        hline([(54, my + 2), (84, my)], 6)
    if lips == "full" and mouth in ("flat", "neutral", "smile", "smirk"):
        lc = tuple(color_of(o.get("lip_color"), "red")) if o.get("lip_color") else shade(skin, 0.75)
        hpoly(closed_ellipse(72, my + 4, 12, 6, 12), lc, None)

    # moustache
    mst = "none" if o.get("shave") else (o.get("moustache") or ("normal" if "moustache" in acc else "none"))
    if mst != "none":
        if mst == "thin":
            hline([(70, 40), (92, 38)], 4.5, hcol)
        else:
            rx_, ry_ = (32, 13) if mst == "thick" else (24, 9)
            hpoly(closed_ellipse(76, 40, rx_, ry_, 16, -8), hcol, None)
            if mst == "handlebar":
                hline(bezier((98, 42), (116, 44), (112, 26), 8), 6, hcol)

    # hair over the head, caps, glasses...
    if not covered:
        _hair_cap(S, HH, hair, hcol)
    if "cap" in acc:
        cc = color_of(o.get("cap_color", "red"), "red")
        crown = ellipse_pts(0, 0, HEAD_RX + 5, HEAD_RY + 6, 24, 170, 340)
        S.poly([HH(q) for q in crown + [(HEAD_RX * 0.9, -40), (-HEAD_RX, -30)]], cc, INK, 6)
        S.poly([HH(q) for q in [(HEAD_RX * 0.55, -44), (HEAD_RX * 1.35, -34), (HEAD_RX * 1.3, -24),
                                (HEAD_RX * 0.6, -30)]], shade(cc, 0.78), INK, 5)
    elif "turban" in acc:
        tc = color_of(o.get("turban_color", o.get("cap_color", "saffron")), "saffron")
        crown = ellipse_pts(-4, -8, HEAD_RX + 14, HEAD_RY + 22, 24, 160, 345)
        S.poly([HH(q) for q in crown + [(HEAD_RX + 2, -26), (-HEAD_RX - 10, 18)]], tc, INK, 6)
        for j in range(3):
            S.line([HH(q) for q in bezier((-HEAD_RX, -10 - j * 26), (0, -70 - j * 22), (HEAD_RX - 4, -40 - j * 18),
                                          10)], 4, shade(tc, 0.75))
    elif "beanie" in acc:
        bcol = color_of(o.get("cap_color", "black"), "black")
        dome = ellipse_pts(0, -6, HEAD_RX + 6, HEAD_RY + 8, 24, 175, 345)
        S.poly([HH(q) for q in dome + [(HEAD_RX * 0.92, -30), (-HEAD_RX - 6, -24)]], bcol, INK, 6)
    if "topi" in acc:
        tcol = color_of(o.get("cap_color", "white"), "white")
        S.poly([HH(q) for q in [(-HEAD_RX * 0.9, -40), (-HEAD_RX * 0.6, -HEAD_RY - 18), (HEAD_RX * 0.5, -HEAD_RY - 22),
                                (HEAD_RX * 0.85, -46), (0, -36)]], tcol, INK, 5)
    if "nurse_cap" in acc:
        S.poly([HH(q) for q in [(-30, -HEAD_RY + 4), (-24, -HEAD_RY - 26), (34, -HEAD_RY - 26), (40, -HEAD_RY + 4)]],
               WHITE, INK, 5)
    if "glasses" in acc or "sunglasses" in acc:
        sun = "sunglasses" in acc
        hpoly(closed_ellipse(ex + 4, ey, 22, 20, 20), (22, 22, 28) if sun else None, INK, 5)
        hline([(ex - 18, ey - 4), (-6, ey - 2)], 5)
    if "earrings" in acc:
        S.dot(HH((-8, 34)), 7, GOLD, INK, 3)
    if "bindi" in acc:
        hpoly(closed_ellipse(86, -36, 5, 6, 12), (200, 30, 50), None)
    if "tilak" in acc:
        hpoly([(84, -58), (90, -58), (90, -22), (86, -22)], (220, 70, 40), None)

    top_extra = HAIR_TOP.get(hair, 8)
    if "turban" in acc:
        top_extra = 26
    near, far = (hand_n, hand_f)
    anchors = dict(head_top=S.T(HH((0, -HEAD_RY - top_extra))), head_center=S.T(HH((0, 0))),
                   mouth=S.T(HF((70, 56))), feet=S.T((0, fy)),
                   hand_l=S.T(far if f > 0 else near), hand_r=S.T(near if f > 0 else far))
    return S.ops, anchors


def _torso(top, hem, back_x, front_x, belly):
    """The body from the side (facing right): back straight, chest and belly in front."""
    back = [(back_x + 10, top), (back_x, top + 30)] + bezier((back_x, top + 30), (back_x - 6, (top + hem) / 2.0),
                                                             (back_x - 2, hem), 10)[1:]
    front = bezier((front_x + belly * 0.4, hem), (front_x + belly * 1.5, (top + hem) / 2.0 + 30),
                   (front_x, top + 40), 12) + [(front_x - 12, top + 2)]
    return back + front


def _side_sleeve(S, outfit, sh, elb, hand, col):
    if outfit == "vest":
        return
    if outfit in ("tshirt", "uniform", "saree", "stripes"):
        S.limb([sh, _mix2(sh, elb, 0.55)], [ARM_W + 14, ARM_W + 16], col)
    else:
        S.limb([sh, elb, _mix2(elb, hand, 0.82)], [ARM_W + 10, ARM_W + 7, ARM_W + 6], col)


def _mix2(p, q, t):
    return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)


def _side_foot(S, foot, f, shoes, skin, dark):
    c = (foot[0] + f * 16, foot[1] - 4)
    if shoes == "chappal":
        S.poly(closed_ellipse(c[0], c[1] + 6, 36, 8, 20), (120, 80, 50) if not dark else (100, 66, 42), INK, 4)
        S.poly(closed_ellipse(c[0] - f * 2, c[1] - 2, 28, 11, 20), skin, INK, 4)
    else:
        col = color_of(shoes, "black")
        S.poly(closed_ellipse(c[0], c[1], 36, 14, 24), shade(col, 0.86) if dark else col, INK, 5)


def _hair_behind(S, HH, style, hc, accent):
    """Long hair hanging down the back, a braid, a bun, a ponytail (behind the head and neck)."""
    if style in ("long", "curly_open"):
        pts = ellipse_pts(0, 0, HEAD_RX + 8, HEAD_RY + 8, 20, 95, 280) + [(-HEAD_RX * 0.2, 160), (-HEAD_RX - 14, 170)]
        S.poly([HH(q) for q in pts], hc, INK, OUTLINE)
        if style == "curly_open":
            for i in range(8):
                a = math.radians(110 + 150 * i / 7)
                S.dot(HH(((HEAD_RX + 26) * math.cos(a), (HEAD_RY + 30) * math.sin(a))), 24, hc, INK, 5)
    elif style == "bob":
        pts = ellipse_pts(0, 0, HEAD_RX + 12, HEAD_RY + 10, 20, 100, 280) + [(-HEAD_RX * 0.3, 74), (-HEAD_RX - 12, 76)]
        S.poly([HH(q) for q in pts], hc, INK, OUTLINE)
    elif style in ("braid", "two_plaits", "side_braid"):
        for i in range(7):
            S.poly(closed_ellipse(*HH((-HEAD_RX * 0.75 - i * 3, 40 + i * 30)), 16, 20, 18), hc, INK, 4)
        S.dot(HH((-HEAD_RX * 0.75 - 21, 40 + 7 * 30)), 10, accent, INK, 4)
    elif style == "ponytail":
        S.poly([HH(q) for q in bezier((-HEAD_RX * 0.7, -40), (-HEAD_RX * 1.8, 0), (-HEAD_RX * 1.3, 120), 12)
                + bezier((-HEAD_RX * 1.1, 110), (-HEAD_RX * 1.3, 10), (-HEAD_RX * 0.6, -10), 10)], hc, INK, OUTLINE)
    elif style == "bun":
        S.dot(HH((-HEAD_RX * 0.85, -HEAD_RY * 0.45)), 36, hc, INK, OUTLINE)
    elif style == "man_bun":
        S.dot(HH((-HEAD_RX * 0.35, -HEAD_RY - 12)), 26, hc, INK, OUTLINE)


def _hair_cap(S, HH, style, hc):
    """The hair over the top and the back of the head, the fringe at the front."""
    if style == "bald":
        S.line([HH((HEAD_RX * 0.1, -HEAD_RY + 18)), HH((HEAD_RX * 0.35, -HEAD_RY + 12))], 5, WHITE)
        return
    if style == "balding":                             # a ring over the ear and round the back
        S.poly([HH(q) for q in ellipse_pts(0, 0, HEAD_RX + 4, HEAD_RY + 5, 14, 120, 215)
                + [(-HEAD_RX * 0.55, -26), (-HEAD_RX * 0.2, 4)]], hc, INK, 4)
        S.line([HH((HEAD_RX * 0.1, -HEAD_RY + 18)), HH((HEAD_RX * 0.35, -HEAD_RY + 12))], 5, WHITE)
        return
    long_ = style in LONG_HAIR
    front = 300 if long_ else 288
    arc = ellipse_pts(0, 0, HEAD_RX + 5, HEAD_RY + 6, 30, 150, front)
    inner = [(HEAD_RX * 0.42, -HEAD_RY * (0.62 if long_ else 0.7)), (HEAD_RX * 0.12, -HEAD_RY * 0.52),
             (-HEAD_RX * 0.18, -HEAD_RY * 0.22), (-HEAD_RX * 0.42, HEAD_RY * 0.08), (-HEAD_RX * 0.72, HEAD_RY * 0.36)]
    if style == "mohawk":
        arc = ellipse_pts(0, 0, HEAD_RX + 2, HEAD_RY + 3, 30, 160, 300)
        S.poly([HH(q) for q in arc + inner], shade(hc, 1.3) if sum(hc) < 150 else hc, INK, 4)
        spikes = []
        for i in range(9):
            a = math.radians(205 + 95 * i / 8)
            r = (HEAD_RX + (40 if i % 2 else 6), HEAD_RY + (44 if i % 2 else 6))
            spikes.append((r[0] * math.cos(a), r[1] * math.sin(a)))
        S.poly([HH(q) for q in spikes + [(HEAD_RX * 0.3, -HEAD_RY * 0.7), (-HEAD_RX * 0.6, -HEAD_RY * 0.6)]], hc, INK,
               OUTLINE)
        return
    S.poly([HH(q) for q in arc + inner], hc, INK, OUTLINE)
    if style == "spiky":
        spikes = []
        for i in range(9):
            a = math.radians(190 + 120 * i / 8)
            r = (HEAD_RX + (30 if i % 2 else 4), HEAD_RY + (34 if i % 2 else 4))
            spikes.append((r[0] * math.cos(a), r[1] * math.sin(a)))
        S.poly([HH(q) for q in spikes + [(HEAD_RX * 0.4, -HEAD_RY * 0.5), (-HEAD_RX * 0.6, -HEAD_RY * 0.3)]], hc, INK,
               OUTLINE)
    elif style in ("curly", "curly_open"):
        for i in range(7):
            a = math.radians(160 + 150 * i / 6)
            S.dot(HH(((HEAD_RX + 4) * math.cos(a), (HEAD_RY + 4) * math.sin(a))), 22, hc, INK, 5)
    elif style == "side_part":
        S.line([HH((HEAD_RX * 0.2, -HEAD_RY - 2)), HH((HEAD_RX * 0.45, -HEAD_RY * 0.62))], 4, shade(hc, 1.6))
    elif style == "bob":
        S.line([HH((HEAD_RX * 0.62, -HEAD_RY * 0.38)), HH((HEAD_RX * 0.7, -HEAD_RY * 0.1))], 10, hc)

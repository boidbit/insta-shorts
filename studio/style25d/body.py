"""2.5D style body: "toon" cartoon person on the same skeleton as the stickman (so every action works):
thick outlined limbs, kurta-pajama, chappals, cel shading, ears, a bigger head and big eyes."""
import math

from ..characters import (HEAD_R, INK, OUTLINE, TORSO_H, _rgb, add, bezier, closed_ellipse, ellipse_pts, shade,
                          vec)

TOON_OUT = 7.0
TOON_LEG_W = 60.0
TOON_ARM_W = 44.0
TOON_WRIST_W = 26.0
SOLE = (96, 60, 40)


def _thick(S, pts, w, color, light, ow=TOON_OUT, hi=True):
    """A fat cartoon limb: ink outline, shadow tone, then a highlight pushed toward the light."""
    S.line(pts, w + 2 * ow, INK)
    S.line(pts, w, shade(color, 0.8) if hi else color)
    if hi:
        ox, oy = light * w * 0.15, -w * 0.06
        S.line([(x + ox, y + oy) for x, y in pts], w * 0.6, color)


class ToonBody:
    name = "toon"
    head_scale = 1.28
    big_eyes = True

    @staticmethod
    def draw_body(S, sk, p, spec, color, skin, light):
        pj = _rgb(spec.get("pants"), (236, 230, 214))

        # ---- legs: chappal + skin foot, then pajama ----
        for side, hip, knee, foot in (("L", sk["hipL"], sk["kneeL"], sk["footL"]),
                                      ("R", sk["hipR"], sk["kneeR"], sk["footR"])):
            sgn = -1 if side == "L" else 1
            S.poly(closed_ellipse(foot[0] + sgn * 18, foot[1] - 4, 48, 13, 24), SOLE, INK, 5)
            S.poly(closed_ellipse(foot[0] + sgn * 16, foot[1] - 17, 38, 16, 24), skin, INK, 5)
            S.line([(foot[0] - 6 + sgn * 6, foot[1] - 26), (foot[0] + sgn * 30, foot[1] - 10)], 10, SOLE)
            ankle = (knee[0] + (foot[0] - knee[0]) * 0.78, knee[1] + (foot[1] - knee[1]) * 0.78)
            _thick(S, [(hip[0] * 0.8, hip[1] - 10), knee, ankle], TOON_LEG_W, pj, light)

        # ---- neck ----
        S.line([(0.0, -TORSO_H + 30), (0.0, -TORSO_H - 20)], 44 + 2 * TOON_OUT, INK)
        S.line([(0.0, -TORSO_H + 30), (0.0, -TORSO_H - 20)], 44, shade(skin, 0.86))

        # ---- kurta ----
        half = [(-30, -TORSO_H + 30), (-62, -TORSO_H + 40), (-86, -TORSO_H + 56), (-96, -TORSO_H + 86),
                (-98, -200), (-100, -100), (-106, 0), (-114, 70), (-118, 112), (-90, 122), (-50, 127), (0, 129)]
        body = half + [(-x, y) for (x, y) in reversed(half[:-1])]
        S.poly(body, shade(color, 0.78), None)
        lit = [(x if x * light >= 0 else x * 0.55, y) for (x, y) in body]
        S.poly(lit, color, None)
        S.poly(body, None, INK, TOON_OUT)
        # collar band + placket with buttons + a couple of cloth folds
        S.line(ellipse_pts(0, -TORSO_H + 30, 34, 14, 12, 10, 170), 6, shade(color, 0.6))
        S.line([(0, -TORSO_H + 44), (0, -170)], 5, shade(color, 0.6))
        for by in (-TORSO_H + 64, -228, -192):
            S.dot((6, by), 5, shade(color, 0.5))
        S.line(bezier((-70, 40), (-60, 84), (-78, 118)), 4, shade(color, 0.62))
        S.line(bezier((62, 50), (54, 88), (70, 120)), 4, shade(color, 0.62))
        S.line(bezier((-40, -40), (-20, -10), (-46, 30)), 4, shade(color, 0.68))

        # ---- arms: skin wrist, sleeve over it, then the hand ----
        for side, sh, elb, hand, a2 in (("L", sk["shL"], sk["elbL"], sk["handL"], p["la2"]),
                                        ("R", sk["shR"], sk["elbR"], sk["handR"], p["ra2"])):
            sgn = -1 if side == "L" else 1
            sh2 = (sh[0] + sgn * 26, sh[1] + 4)
            wrist = (elb[0] + (hand[0] - elb[0]) * 0.7, elb[1] + (hand[1] - elb[1]) * 0.7)
            _thick(S, [wrist, hand], TOON_WRIST_W, skin, light, hi=False)
            _thick(S, [sh2, elb, wrist], TOON_ARM_W, color, light)
            d = vec(a2, 1.0)
            n = (-d[1] * sgn, d[0] * sgn)
            S.poly(closed_ellipse(hand[0] + n[0] * 16 - d[0] * 4, hand[1] + n[1] * 16 - d[1] * 4, 10, 10, 14),
                   skin, INK, 5)
            S.poly(closed_ellipse(hand[0] + d[0] * 4, hand[1] + d[1] * 4, 21, 19, 22,
                                  math.degrees(math.atan2(d[1], d[0]))), skin, INK, 5)
            if p.get("finger") == side:
                tipp = add(hand, vec(a2, 50))
                S.line([hand, tipp], 13 + 10, INK)
                S.line([hand, tipp], 13, skin)

    @staticmethod
    def draw_head(hpoly, hline, skin, facing, light):
        # ears, then a cel-shaded head: shadow tone + lit disc pushed toward the light + ink rim
        for sgn in (-1, 1):
            ex = sgn * (HEAD_R - 4) + facing * -6
            hpoly(closed_ellipse(ex, 10, 22, 27, 24), skin, INK, TOON_OUT)
            hline(ellipse_pts(ex - sgn * 2, 12, 10, 14, 10, 100 - sgn * 60, 260 - sgn * 60), 4, shade(skin, 0.7))
        hpoly(closed_ellipse(0, 0, HEAD_R, HEAD_R, 64), shade(skin, 0.84), None)
        hpoly(closed_ellipse(light * HEAD_R * 0.1, -HEAD_R * 0.06, HEAD_R * 0.9, HEAD_R * 0.92, 64), skin, None)
        hpoly(closed_ellipse(0, 0, HEAD_R, HEAD_R, 64), None, INK, OUTLINE + 1)


TOON = ToonBody()

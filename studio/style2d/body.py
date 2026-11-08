"""2D style body: the classic desi stickman (bean torso, thin black limbs, plain round head)."""
import math

from ..characters import (ARM_W, HEAD_R, INK, LEG_W, OUTLINE, TORSO_H, TORSO_W, add, closed_ellipse, vec)


class StickBody:
    name = "stick"
    head_scale = 1.0
    big_eyes = False

    @staticmethod
    def draw_body(S, sk, p, spec, color, skin, light):
        # ---- legs (+ shoes) ----
        for side, hip, knee, foot in (("L", sk["hipL"], sk["kneeL"], sk["footL"]),
                                      ("R", sk["hipR"], sk["kneeR"], sk["footR"])):
            S.line([hip, knee, foot], LEG_W)
            sgn = -1 if side == "L" else 1
            S.poly(closed_ellipse(foot[0] + sgn * 16, foot[1] - 6, 32, 15, 24), INK, None)

        # ---- torso (bean, slightly wider at the bottom) ----
        torso = []
        for i in range(48):
            a = 2 * math.pi * i / 48
            rx = (TORSO_W / 2) * (1 + 0.14 * math.sin(a))
            torso.append((rx * math.cos(a), (-TORSO_H / 2 + 4) + (TORSO_H / 2 + 14) * math.sin(a)))
        S.poly(torso, color, INK, OUTLINE)

        # ---- arms ----
        for side, sh, elb, hand, a1, a2 in (("L", sk["shL"], sk["elbL"], sk["handL"], p["la1"], p["la2"]),
                                            ("R", sk["shR"], sk["elbR"], sk["handR"], p["ra1"], p["ra2"])):
            S.line([sh, elb, hand], ARM_W)
            S.dot(hand, 15, INK)
            if p.get("finger") == side:
                S.line([hand, add(hand, vec(a2, 44))], 9)

    @staticmethod
    def draw_head(hpoly, hline, skin, facing, light):
        hpoly(closed_ellipse(0, 0, HEAD_R, HEAD_R, 64), skin, INK, OUTLINE + 1)


STICK = StickBody()

"""2.5D sets for the two places drawn for the kirdaar (studio/places_studio), on their own drawings split into depth
layers (autoset), with their own life and something blurred in front of the lens.

clinic_25d   Doctor Paglet's clinic: dust drifting in the sunlight from the open door, the tube light's faint
             flicker; a blurred medicine bottle and a syringe in front.
podcast_25d  the Gappcast studio: the neon mic breathing, the ON AIR light blinking, the pendant lamp's warm pool;
             blurred leaves of a plant in front.
"""
import math

from .scenery import Layer, motes
from .scenery_2026 import EMPTY, INK, _anim, _blur_front, _set


def clinic_25d(s, zmax=1.0):
    k = 0.5 * s

    def tube(cv, t):                                    # the tube light hums: now and then a soft flicker
        f = 1.0 - (0.25 if (t * 0.7) % 3.0 < 0.08 else 0.0)
        cv.glow(510, 300, 240, (236, 248, 255), int(60 * f))
    life = [_anim(k, tube, "tube", "screen"),
            Layer(EMPTY, 0.3 * s, 1.0, motes(((20, 400), (420, 1300), 240), 0.3 * s, 30, 52), "dust", mode="screen")]

    def front(cv):
        cv.rect(900, 1650, 990, 1900, (150, 80, 40, 255), (110, 56, 30, 255), 6)     # a medicine bottle
        cv.rect(910, 1610, 980, 1650, (240, 240, 236, 255))
        cv.rect(-40, 1800, 300, 1840, (220, 236, 246, 255), (120, 140, 160, 255), 4)  # a syringe at the lens
        cv.line([(300, 1820), (380, 1820)], (150, 150, 160, 255), 5)
    return _set("clinic", s, zmax, life, _blur_front(k, front), {"ambient": [255, 250, 236], "dir": -1,
                "vignette": 0.22}, 820, 1270)


def podcast_25d(s, zmax=1.0):
    k = 0.5 * s

    def neon(cv, t):                                    # the neon mic breathes, the lamp's warm pool
        f = 0.8 + 0.2 * math.sin(t * 2.2)
        cv.glow(540, 520, 230, (255, 170, 60), int(90 * f))
        cv.glow(540, 300, 260, (255, 210, 130), 60)

    def on_air(cv, t):                                  # the ON AIR light blinks slowly
        lit = (t % 1.6) < 1.1
        cv.rect(440, 800, 640, 856, (200, 40, 40, 255) if lit else (90, 30, 30, 255), INK, 4)
        if lit:
            cv.glow(540, 828, 130, (255, 80, 60), 70)
    life = [_anim(k, neon, "neon", "screen"), _anim(k, on_air, "on_air")]

    def front(cv):
        for (x, y, r) in ((-20, 1760, 120), (90, 1850, 100), (1080, 1780, 130), (980, 1870, 100)):  # leaves at the lens
            cv.ell(x, y, r, r * 0.45, (70, 140, 70, 255))
    return _set("podcast", s, zmax, life, _blur_front(k, front), {"ambient": [255, 226, 210], "dir": 1,
                "vignette": 0.3}, 820, 1300)


SETS = {"clinic_25d": clinic_25d, "podcast_25d": podcast_25d}

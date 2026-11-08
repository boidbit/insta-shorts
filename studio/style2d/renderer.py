"""2D style renderer: the classic stickman pipeline, frame-for-frame the same as before 2.5D existed
(flat background, characters drawn on it, then the whole frame is cropped/zoomed for the camera)."""
from PIL import Image

from .. import actions
from ..characters import build_character, render_ops
from ..render import BaseRenderer
from ..scene import camera_at
from ..text import bubble_image, styled_box
from ..util import clamp, ease_out_back
from .backgrounds import Background
from .body import STICK


class Renderer2D(BaseRenderer):
    style = "2d"

    def __init__(self, scene, width=1080, use_tts=True, fps=None):
        super().__init__(scene, width, use_tts=use_tts, fps=fps)
        self.bg = Background(self.plan.background, self.W, self.H)

    # ------------------------------------------------------------ one frame
    def frame(self, t):
        plan, s = self.plan, self.s
        img = self.bg.frame(t).convert("RGB")
        order = sorted(plan.chars.values(), key=lambda c: (c.pos_at(t)[1], c.pos_at(t)[0]))
        anchors = {}
        states = {}
        for c in order:
            st = c.state_at(t)
            states[c.name] = st
            x, y = c.pos_at(t)
            action, a_t0 = st["action"], st["action_t0"]
            moving = any(t0 <= t < t1 for (t0, t1, *_r) in c.moves)
            if moving and action in ("idle", "none", "stand"):
                action, a_t0 = "walk", 0.0
            opts = dict(st["opts"], _x=x)
            pose = actions.pose_for(action, t - a_t0 if action != "walk" else t, st["speed"], st["intensity"],
                                    c.phase, opts)
            look = st["look"]
            if isinstance(look, str) and look in plan.chars:
                ox, _oy = plan.chars[look].pos_at(t)
                pose["look_x"] = clamp((ox - x) / 350.0, -1, 1)
            elif look == "left":
                pose["look_x"] = -1
            elif look == "right":
                pose["look_x"] = 1
            elif isinstance(look, (int, float)):
                pose["look_x"] = float(look)
            mouth_open = 0.0
            if st["talking"]:
                mouth_open = self._lip_open(st["talking"], t)
            blink = ((t + c.phase * 1.7) % 3.6) < 0.12
            spec = dict(c.spec)
            spec["facing"] = st["facing"]
            ops, an = build_character(spec, pose, st["expression"], mouth_open, t, x, y, c.scale,
                                      blink=blink, prop=st["prop"], talking=bool(st["talking"]),
                                      tear_phase=(t * 1.1) % 1.0, body=STICK)
            r = render_ops(ops, s, self.W, self.H)
            if r:
                layer, (ox, oy) = r
                img.paste(layer, (ox, oy), layer)
            anchors[c.name] = an

        # labels + bubbles
        for c in order:
            st, an = states[c.name], anchors[c.name]
            hx, hy = an["head_top"]
            top = hy
            if st["label"]:
                key = st["label"]
                if key not in self._label_cache:
                    self._label_cache[key] = styled_box(key, "tag", s)
                lab = self._label_cache[key]
                self._paste_rgba(img, lab, hx * s, hy * s - lab.height / 2 - 18 * s)
                top = hy - (lab.height / s) - 30
            sp = st["talking"]
            if sp and sp.get("bubble", True):
                lt = t - sp["start"]
                im0, _ = bubble_image(sp["text"], s, 0)
                left = clamp(hx * s - im0.width * 0.35, 24 * s, self.W - im0.width - 24 * s)
                im, (tipx, tipy) = bubble_image(sp["text"], s, int(hx * s - left))
                tx, ty = left + tipx, top * s - 12 * s
                sc = 0.55 + 0.45 * ease_out_back(lt / 0.22)
                self._paste_rgba(img, im, tx, ty, sc, 1.0, anchor=(tipx, tipy))

        # camera
        z, cx, cy, dx, dy = camera_at(plan, t)
        if dx or dy:
            z = max(z, 1.05)
        if z > 1.001:
            vw, vh = self.W / z, self.H / z
            ccx, ccy = (cx + dx) * s, (cy + dy) * s
            l = clamp(ccx - vw / 2, 0, self.W - vw)
            tp = clamp(ccy - vh / 2, 0, self.H - vh)
            img = img.resize((self.W, self.H), Image.BILINEAR, box=(l, tp, l + vw, tp + vh))

        self._draw_overlays(img, t)    # captions stay screen-fixed (not zoomed)

        # fades
        f = 1.0
        if plan.fade_in and t < plan.fade_in:
            f = min(f, t / plan.fade_in)
        if plan.fade_out and t > plan.duration - plan.fade_out:
            f = min(f, (plan.duration - t) / plan.fade_out)
        if f < 0.999:
            img = Image.blend(Image.new("RGB", img.size, (0, 0, 0)), img, clamp(f))
        return img

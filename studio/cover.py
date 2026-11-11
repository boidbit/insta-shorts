"""The reel's cover picture (Instagram: Edit cover -> upload it): the punch line as a close-up of the speaker, the hook
in big words, the hook's emoji as a sticker, the mascot peeking, the video's own colours. Everything that matters
sits inside the middle 3:4 (the profile grid crops the top and the bottom of a 9:16 cover).

    python -m studio.render scene.json --cover -o out/x.cover.png
"""
import re

from PIL import Image, ImageDraw, ImageFilter

from . import theme
from .text import text_block

EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐⭕⌚-⌛⏩-⏺]")
SAFE_TOP, SAFE_BOTTOM = 240, 1680            # the 3:4 window of a 1080 x 1920 cover (logical px)


def cover_words(scene):
    """The big words: the script's COVER line, else the hook (without its emoji), in capitals."""
    text = str(scene.get("cover") or scene.get("hook") or "").strip()
    text = EMOJI.sub("", text).replace("️", "").strip(" -:|")
    return re.sub(r"\s+", " ", text).upper()


def cover_emoji(scene):
    for src in (scene.get("cover"), scene.get("hook")):
        m = EMOJI.search(str(src or ""))
        if m:
            return m.group(0)
    return None


def punch_moment(parts):
    """(part, speaker, time) of the last line a visible person says: the punch line, the funniest face."""
    for p in reversed(parts):
        for sp in reversed(p.plan.speech):
            c = p.plan.chars.get(sp["who"])
            if c is not None and not c.spec.get("hidden") and not c.spec.get("kind"):
                return p, c, sp["start"] + min(0.7, 0.5 * (sp["end"] - sp["start"]))
    p = parts[-1]
    people = [c for c in p.plan.chars.values() if not c.spec.get("hidden")]
    return p, (people[0] if people else None), p.plan.duration * 0.6


def _sticker(im, outline, color=(255, 255, 255, 255)):
    """A white die-cut edge round an RGBA picture (a sticker)."""
    pad = outline + 2
    big = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    big.paste(im, (pad, pad), im)
    edge = big.getchannel("A").filter(ImageFilter.MaxFilter(2 * (outline // 2) + 1))
    out = Image.new("RGBA", big.size, color)
    out.putalpha(edge)
    out.alpha_composite(big)
    return out


def make_cover(video, scene):
    """The cover picture (RGB, the video's size) of a video made by render.make_video from `scene`."""
    from .render import Looped, mascot_kind, mascot_sprite
    base = video.v if isinstance(video, Looped) else video
    parts = getattr(base, "parts", [base])
    p, c, t = punch_moment(parts)
    if c is not None:                                   # a close-up on the speaker, the face below the words
        fx, fy = c.focus_at(t)
        p.cam_override = (1.5, fx, fy - 170.0)
    try:
        img = p.story_frame(t, bare=True, clean=True).convert("RGB")
    finally:
        p.cam_override = None
    W, H = img.size
    s = W / 1080.0
    meta = scene.get("meta") or {}
    th = theme.THEMES[theme.resolve(meta.get("theme")) or "classic"]
    hook_c, ink = tuple(th["hook"]), tuple(th["hook_fg"])

    shade = Image.new("L", (1, H), 0)                   # a dark band behind the words, fading down
    for y in range(H):
        f = y / float(H)
        shade.putpixel((0, y), int(215 * max(0.0, min(1.0, (0.5 - f) / 0.26))))
    img = Image.composite(Image.new("RGB", (W, H), (14, 14, 18)), img, shade.resize((W, H)))

    words = cover_words(scene)
    if words:
        tb = text_block(words, 124 * s, 940 * s, fill=hook_c if sum(hook_c) > 200 else (255, 255, 255),
                        stroke=13 * s, stroke_fill=(0, 0, 0), fit_lines=3)
        img.paste(tb, (int((W - tb.width) / 2), int(SAFE_TOP * s + 50 * s)), tb)
        y_text = SAFE_TOP * s + 50 * s + tb.height
    else:
        y_text = SAFE_TOP * s
    emo = cover_emoji(scene)
    if emo:                                             # the hook's emoji as a big tilted sticker
        eb = _sticker(text_block(emo, 210 * s, 400 * s), int(14 * s)).rotate(-12, expand=True, resample=Image.BICUBIC)
        img.paste(eb, (int(W - eb.width - 40 * s), int(y_text + 6 * s)), eb)        # just under the words
    kind = mascot_kind(scene.get("mascot"))
    if kind:                                            # the mascot peeks in at the bottom corner
        ms = mascot_sprite(kind, 80 * s, 1, False)
        img.paste(ms, (int(40 * s), int(SAFE_BOTTOM * s - ms.height * 0.9)), ms)
    if scene.get("handle"):
        hb = text_block(str(scene["handle"]), 40 * s, 600 * s, fill=(255, 255, 255), stroke=5 * s)
        img.paste(hb, (int((W - hb.width) / 2), int(SAFE_BOTTOM * s - hb.height - 24 * s)), hb)
    d = ImageDraw.Draw(img)                             # the video's colour as a frame
    bw = int(16 * s)
    d.rectangle([bw // 2, bw // 2, W - bw // 2 - 1, H - bw // 2 - 1], outline=hook_c, width=bw)
    return img

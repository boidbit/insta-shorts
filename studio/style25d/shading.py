"""2.5D look for the people: the flat 2D character drawing gets volume from the set's light.

Only the 2.5D style calls this (the 2d look draws people exactly as before). Everything is worked out from the
drawn silhouette, so it fits every look, pose, prop and animal without knowing how they were drawn:
  - the set's light colour falls on the whole body (multiply),
  - the side away from the light falls into a soft, cool shadow,
  - a thin warm rim of light runs just inside the outline on the lit side,
  - the legs get a little darker towards the floor (the floor is in shadow under them).
"""
from PIL import Image, ImageChops, ImageFilter

SHADOW = (172, 178, 204)        # multiply colour of the shadow side (cool)
RIM = (255, 238, 206)           # screen colour of the rim light (warm)


def _shifted(a, dx):
    out = Image.new("L", a.size, 0)
    out.paste(a, (int(dx), 0))
    return out


def volume(layer, s, light_dir=-1, tint=None, shadow=0.62, rim=0.28, floor=0.16):
    """Shade one character sprite (RGBA, s px per logical unit). light_dir -1: the light comes from the left of the
    frame, 1: from the right."""
    w, h = layer.size
    if w < 8 or h < 8:
        return layer
    a = layer.getchannel("A")
    rgb = layer.convert("RGB")
    if tint:
        rgb = ImageChops.multiply(rgb, Image.new("RGB", rgb.size, tuple(tint)))
    side = 1 if light_dir >= 0 else -1
    d = max(2, int(round(34 * s)))
    # the shadow side: inside the shape, where the shape ends within d px going away from the light
    band = ImageChops.subtract(a, _shifted(a, d * side))
    small = band.resize((max(1, w // 2), max(1, h // 2)), Image.BILINEAR).filter(ImageFilter.GaussianBlur(d * 0.3))
    band = ImageChops.multiply(small.resize((w, h), Image.BILINEAR), a)
    rgb = Image.composite(ImageChops.multiply(rgb, Image.new("RGB", rgb.size, SHADOW)), rgb,
                          band.point(lambda v: int(v * shadow)))
    # the rim on the lit side, just inside the dark outline
    r0, r1 = max(1, int(round(8 * s))), max(2, int(round(17 * s)))
    if r1 > r0:
        rim_band = ImageChops.subtract(_shifted(a, -r0 * side), _shifted(a, -r1 * side))
        rim_band = ImageChops.multiply(rim_band, a).filter(ImageFilter.GaussianBlur(max(0.6, s * 2.0)))
        rgb = Image.composite(ImageChops.screen(rgb, Image.new("RGB", rgb.size, RIM)), rgb,
                              rim_band.point(lambda v: int(v * rim)))
    # towards the floor: from 70% of the height down to the feet
    if floor:
        ramp = Image.linear_gradient("L").resize((1, h), Image.BILINEAR)
        ramp = ramp.point(lambda v: 0 if v < 178 else int((v - 178) / 77.0 * 255 * floor)).resize((w, h))
        rgb = Image.composite(ImageChops.multiply(rgb, Image.new("RGB", rgb.size, SHADOW)), rgb, ramp)
    rgb.putalpha(a)
    return rgb

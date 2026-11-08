"""Golden-frame tests: make sure neither style's look changes by accident.

    python -m tests.golden check                 # render every case, compare with tests/golden/ (tolerant)
    python -m tests.golden update                # re-create tests/golden/ (only after an intended look change)
    python -m tests.golden compare-base --base DIR
        # render the 2d cases with the code in DIR (e.g. a checkout of main) AND with this code, in the
        # same environment, and require pixel-identical frames. This is the "2.5d never changes 2d" guard
        # that CI runs; it does not depend on fonts/OS because both sides render on the same machine.

Frames are rendered without TTS (estimated timing, no network) at 360 px wide. Failures write
side-by-side images (expected | got | difference) to tests/out/.
"""
import argparse
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GOLDEN = os.path.join(HERE, "golden")
OUT = os.path.join(HERE, "out")
WIDTH = 360

# (style folder, scene file, times). Times hit dialogue, labels, camera shake, scrolling bg, fx...
CASES = [
    ("2d", "scenes/2d/tag_karo_demo.json", [0.5, 2.0, 6.0]),
    ("2d", "scenes/2d/dost_types_demo.json", [1.0, 2.6, 5.0]),
    ("2d", "scenes/2d/dialogue_demo.json", [2.0, 9.0, 13.0]),
    ("2d", "scenes/2d/kaun_sahi_demo.json", [1.0, 3.0]),
    ("2d", "scenes/2d/song_reel_demo.json", [1.0, 3.0, 6.0]),
    ("25d", "scenes/25d/diwali_3d_demo.json", [1.0, 3.5, 11.5]),
    ("25d", "scenes/25d/kitchen_25d_demo.json", [1.0, 4.0]),
    ("25d", "scenes/25d/gali_25d_demo.json", [1.0, 5.0]),
]

# Renders all times of one scene in a single process using the `studio` package found in code_dir.
_RUNNER = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
from studio.util import load_scene
from studio.render import Renderer
scene_path, width, out_dir, times = sys.argv[2], int(sys.argv[3]), sys.argv[4], json.loads(sys.argv[5])
r = Renderer(load_scene(scene_path), width, use_tts=False)
for name, t in times:
    r.frame(float(t)).save(out_dir + "/" + name)
"""


def frame_name(scene, t):
    return "%s_%s.png" % (os.path.splitext(os.path.basename(scene))[0], t)


def render_cases(code_dir, out_root, styles=("2d", "25d")):
    """Render the cases with the code in code_dir. Returns {style: [png names]}."""
    done = {}
    for style, scene, times in CASES:
        if style not in styles:
            continue
        out_dir = os.path.join(out_root, style)
        os.makedirs(out_dir, exist_ok=True)
        names = [(frame_name(scene, t), t) for t in times]
        env = dict(os.environ, PYTHONPATH=os.path.abspath(code_dir))
        subprocess.run([sys.executable, "-c", _RUNNER, os.path.abspath(code_dir), os.path.join(ROOT, scene),
                        str(WIDTH), out_dir, json.dumps(names)], check=True, cwd=os.path.abspath(code_dir), env=env)
        done.setdefault(style, []).extend(n for n, _ in names)
    return done


def compare(expected_path, got_path, strict):
    """Returns (ok, message)."""
    a = np.asarray(Image.open(expected_path).convert("RGB")).astype(np.int16)
    b = np.asarray(Image.open(got_path).convert("RGB")).astype(np.int16)
    if a.shape != b.shape:
        return False, "size %s != %s" % (a.shape[:2], b.shape[:2])
    d = np.abs(a - b).max(axis=2)
    changed = float((d > 0).mean())
    if strict:
        return changed == 0.0, "%.3f%% pixels differ" % (100 * changed)
    big = float((d > 40).mean())          # tolerant: ignore tiny anti-aliasing/font-version noise
    return big <= 0.0015, "%.3f%% pixels differ strongly (limit 0.15%%)" % (100 * big)


def save_diff(expected_path, got_path, name):
    os.makedirs(OUT, exist_ok=True)
    a, b = Image.open(expected_path).convert("RGB"), Image.open(got_path).convert("RGB")
    d = ImageChops.difference(a, b).point(lambda v: min(255, v * 4))
    sheet = Image.new("RGB", (a.width * 3 + 12, a.height), (255, 255, 255))
    for i, im in enumerate((a, b, d)):
        sheet.paste(im, (i * (a.width + 6), 0))
    p = os.path.join(OUT, name.replace("/", "_").replace(".png", "_DIFF.png"))
    sheet.save(p)
    return p


def run_compare(expected_root, got_root, rendered, strict):
    fails = 0
    for style, names in rendered.items():
        for n in names:
            e, g = os.path.join(expected_root, style, n), os.path.join(got_root, style, n)
            if not os.path.isfile(e):
                print("  MISSING golden %s/%s (run: python -m tests.golden update)" % (style, n))
                fails += 1
                continue
            ok, msg = compare(e, g, strict)
            print("  %-4s %-4s %-28s %s" % ("ok" if ok else "FAIL", style, n, msg))
            if not ok:
                fails += 1
                print("       diff image: %s" % save_diff(e, g, style + "/" + n))
    return fails


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["check", "update", "compare-base"])
    ap.add_argument("--base", help="compare-base: directory with the other code version (e.g. a main checkout)")
    ap.add_argument("--style", choices=["2d", "25d", "all"], default="all")
    ap.add_argument("--strict", action="store_true", help="check: require pixel-identical frames")
    args = ap.parse_args(argv)
    styles = ("2d", "25d") if args.style == "all" else (args.style,)

    if args.cmd == "update":
        rendered = render_cases(ROOT, GOLDEN, styles)
        print("updated %d golden frames in %s" % (sum(len(v) for v in rendered.values()), GOLDEN))
        return 0

    if args.cmd == "check":
        got = os.path.join(OUT, "current")
        rendered = render_cases(ROOT, got, styles)
        fails = run_compare(GOLDEN, got, rendered, args.strict)
    else:
        if not args.base:
            ap.error("compare-base needs --base DIR")
        styles = ("2d",) if args.style == "all" else styles
        base_out, head_out = os.path.join(OUT, "base"), os.path.join(OUT, "head")
        print("rendering with base code: %s" % args.base)
        render_cases(args.base, base_out, styles)
        print("rendering with this code: %s" % ROOT)
        rendered = render_cases(ROOT, head_out, styles)
        fails = run_compare(base_out, head_out, rendered, strict=True)

    print("FAILED: %d frame(s) changed" % fails if fails else "PASSED: no unexpected change")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

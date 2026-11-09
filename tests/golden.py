"""Golden frames: make sure neither look changes by accident.

    python tests/golden.py compare-base --base DIR
        Render the 2d cases with the code in DIR (a checkout of desi-toons-studio) AND with this code, on the
        same machine, and require pixel-identical frames: 2.5D work must never change the 2d look. Fonts / OS do
        not matter because both sides render in the same place. CI runs this.
    python tests/golden.py check      # render every case, compare with tests/golden/ (small font noise allowed)
    python tests/golden.py update     # re-create tests/golden/ (only after an intended look change)

Frames are rendered without TTS (estimated timing, no network) at 360 px wide. Failures write
side-by-side images (expected | got | difference x4) to tests/out/.
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

# (look, file, times). Scripts are turned into scenes by each code version's own studio.script.
CASES = [
    ("2d", "scripts/chai_bill.txt", [1.0, 3.0, 6.0]),
    ("2d", "scripts/dadi_phone.txt", [1.0, 4.0]),
    ("2d", "scripts/doodh_story.txt", [1.0, 5.0, 9.0]),
    ("2d", "scripts/shaadi_dance.txt", [1.0, 4.0]),
    ("2d", "scenes/tag_karo_demo.json", [1.0, 4.0]),
    ("2d", "scenes/dialogue_demo.json", [2.0, 6.0]),
    ("2d", "scenes/kaun_sahi_demo.json", [2.0]),
    ("25d", "scripts/25d/gali_udhaar.txt", [1.0, 4.0, 9.0]),
    ("25d", "scripts/25d/kitchen_mummy.txt", [1.0, 4.0]),
    ("25d", "scripts/25d/diwali_terrace.txt", [1.0, 4.0]),
    ("25d", "scripts/25d/ghar_remote.txt", [1.0, 5.0]),
    ("25d", "scripts/25d/class_test.txt", [1.0, 5.0]),
    ("25d", "scripts/25d/shaadi_pandit.txt", [1.0, 5.0]),
]

_RUNNER = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
from studio.render import make_video
from studio.util import load_scene
path, width, out_dir, times = sys.argv[2], int(sys.argv[3]), sys.argv[4], json.loads(sys.argv[5])
if path.endswith(".txt"):
    from studio.script import parse_script
    with open(path, encoding="utf-8") as f:
        scene, _warnings = parse_script(f.read())
else:
    scene = load_scene(path)
v = make_video(scene, width, use_tts=False)
for name, t in times:
    v.frame(min(float(t), v.duration - 0.05)).save(out_dir + "/" + name)
"""


def frame_name(path, t):
    return "%s_%s.png" % (os.path.splitext(os.path.basename(path))[0], t)


def render_cases(code_dir, out_root, looks):
    done = {}
    code_dir = os.path.abspath(code_dir)
    for look, path, times in CASES:
        if look not in looks:
            continue
        out_dir = os.path.join(out_root, look)
        os.makedirs(out_dir, exist_ok=True)
        names = [(frame_name(path, t), t) for t in times]
        env = dict(os.environ, PYTHONPATH=code_dir)
        subprocess.run([sys.executable, "-c", _RUNNER, code_dir, os.path.join(ROOT, path), str(WIDTH), out_dir,
                        json.dumps(names)], check=True, cwd=code_dir, env=env)
        done.setdefault(look, []).extend(n for n, _ in names)
    return done


def compare(expected, got, strict):
    a = np.asarray(Image.open(expected).convert("RGB")).astype(np.int16)
    b = np.asarray(Image.open(got).convert("RGB")).astype(np.int16)
    if a.shape != b.shape:
        return False, "size %s != %s" % (a.shape[:2], b.shape[:2])
    d = np.abs(a - b).max(axis=2)
    if strict:
        changed = float((d > 0).mean())
        return changed == 0.0, "%.3f%% pixels differ" % (100 * changed)
    big = float((d > 40).mean())          # tolerant: ignore tiny anti-aliasing / font-version noise
    return big <= 0.0015, "%.3f%% pixels differ strongly (limit 0.15%%)" % (100 * big)


def save_diff(expected, got, name):
    os.makedirs(OUT, exist_ok=True)
    a, b = Image.open(expected).convert("RGB"), Image.open(got).convert("RGB")
    d = ImageChops.difference(a, b).point(lambda v: min(255, v * 4))
    sheet = Image.new("RGB", (a.width * 3 + 12, a.height), (255, 255, 255))
    for i, im in enumerate((a, b, d)):
        sheet.paste(im, (i * (a.width + 6), 0))
    p = os.path.join(OUT, name.replace("/", "_").replace(".png", "_DIFF.png"))
    sheet.save(p)
    return p


def run_compare(expected_root, got_root, rendered, strict):
    fails = 0
    for look, names in rendered.items():
        for n in names:
            e, g = os.path.join(expected_root, look, n), os.path.join(got_root, look, n)
            if not os.path.isfile(e):
                print("  MISSING golden %s/%s (run: python tests/golden.py update)" % (look, n))
                fails += 1
                continue
            ok, msg = compare(e, g, strict)
            print("  %-4s %-4s %-28s %s" % ("ok" if ok else "FAIL", look, n, msg))
            if not ok:
                fails += 1
                print("       diff image: %s" % save_diff(e, g, look + "/" + n))
    return fails


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["check", "update", "compare-base"])
    ap.add_argument("--base", help="compare-base: the other code version (e.g. a desi-toons-studio checkout)")
    ap.add_argument("--look", choices=["2d", "25d", "all"], default="all")
    ap.add_argument("--strict", action="store_true", help="check: require pixel-identical frames")
    args = ap.parse_args(argv)
    looks = ("2d", "25d") if args.look == "all" else (args.look,)

    if args.cmd == "update":
        rendered = render_cases(ROOT, GOLDEN, looks)
        print("updated %d golden frames in %s" % (sum(len(v) for v in rendered.values()), GOLDEN))
        return 0
    if args.cmd == "check":
        got = os.path.join(OUT, "current")
        rendered = render_cases(ROOT, got, looks)
        fails = run_compare(GOLDEN, got, rendered, args.strict)
    else:
        if not args.base:
            ap.error("compare-base needs --base DIR")
        base_out, head_out = os.path.join(OUT, "base"), os.path.join(OUT, "head")
        print("rendering 2d with the base code: %s" % args.base)
        render_cases(args.base, base_out, ("2d",))
        print("rendering 2d with this code: %s" % ROOT)
        rendered = render_cases(ROOT, head_out, ("2d",))
        fails = run_compare(base_out, head_out, rendered, strict=True)
    print("FAILED: %d frame(s) changed" % fails if fails else "PASSED: no unexpected change")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

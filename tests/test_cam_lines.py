"""CAM: lines (the directed camera of the chat / cine mode)."""
import os
import tempfile

from studio import scene as S
from studio import script as SC


SCRIPT = """HOOK: Udhaar wala dost phir aaya
CAST: A = dost curly green tshirt, B = uncle moustache kurta
SCENE: chai_tapri
CAM: push A 1.6 1.5
A (grin, wave): Chotu bhaiya, ek cutting chai dena, udhaar pe! | छोटू भैया, एक कटिंग चाय देना, उधार पे!
CAM: whip B
B (sly): Pichhla udhaar kab chukayega beta? | पिछला उधार कब चुकाएगा बेटा?
CAM: dutch -6 1.2
CAM: snap A
A (smug, shrug): Wo bhi agle mahine! | वो भी अगले महीने!
CAM: pull
"""


def test_cam_spec_words():
    cast = {"A", "B"}
    assert SC.cam_spec("push B", cast)[0] == {"zoom": 1.7, "focus": "B", "dur": 1.8}
    assert SC.cam_spec("snap A 2.4", cast)[0]["zoom"] == 2.4
    assert SC.cam_spec("pull", cast)[0] == {"zoom": 1.0, "dur": 1.4}
    assert SC.cam_spec("dutch -5 1", cast)[0] == {"roll": -5.0, "dur": 1.0}
    assert SC.cam_spec("frame 540 900", cast)[0]["focus"] == [540.0, 900.0]
    assert SC.cam_spec("push", cast)[1]          # who?
    assert SC.cam_spec("bogus", cast)[1]


def test_cam_lines_direct_the_shot(tmp_path):
    src = tmp_path / "x.txt"
    src.write_text(SCRIPT, encoding="utf-8")
    out = tmp_path / "x.json"
    import subprocess, sys, json
    subprocess.run([sys.executable, "-m", "studio.script", str(src), "-o", str(out)], check=True,
                   cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    doc = json.loads(out.read_text(encoding="utf-8"))
    sub = S.split_scenes(doc)[0]
    assert sub.get("drift") is True
    cams = [e["camera"] for e in sub["timeline"] if "camera" in e]
    assert not any(c.get("reveal") for c in cams)          # no studio opening shot in a directed scene
    plan = S.compile_scene(sub, use_tts=False)
    assert plan.drift
    assert any(r[2] == -6.0 for r in plan.rolls)
    zooms = [seg[3] for seg in plan.cam_segments]
    assert zooms[0] == 1.6 and 2.1 in zooms and zooms[-1] == 1.0

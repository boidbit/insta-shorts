# Desi Toons Studio (insta-shorts): Indian cartoon comedy reels, 1080x1920

The owner writes in Hinglish (Roman Hindi); reply in Hinglish, short and clear. They work from an office laptop /
phone browser only: never ask them to install tools or run commands locally.

## What to do in a new chat
- **Owner pastes a script, dialogue or idea (even with no other words) → use skill `cine-reel`.** Chat = the
  "zinda" (cinematic) mode: Claude directs every shot with `CAM:` / `CUT` lines, builds missing assets, previews,
  pushes, renders on GitHub. The quick "flat" mode is the studio web page (index.html); it stays as it is.
- Skills (`.claude/skills/`): `cine-reel` (script → directed reel → preview → render), `alive-frames` (camera
  language + "never a dead frame" rules for this engine), `desi-assets` (find / reuse / build places, props,
  looks, kirdaar, animals, sounds), `reel-render-check` (GitHub render + checks + caption).
- Anything else: answer directly; read only what you need (big files: grep, offset).

## Project map
- Script format: `SCRIPT_PROMPT.md` (HOOK / STYLE / CAST / SCENE / lines `A (feeling, action): Roman | देवनागरी` /
  `A -> action` / `CUT ...` / `CAM: ...` / CTA / CAPTION / HASHTAGS). `studio/script.py` turns it into scene JSON.
- Engine (Python + Pillow): `studio/scene.py` (compile, camera), `render.py`, `characters.py`, `actions.py`,
  places in `locations.py`, `places_*.py`, 2.5D sets in `sets.py` / `style25d/` / `styles.py`, props `objects.py`,
  `animals.py`, `vehicles.py`, `effects.py`, sounds `audio.py` + `assets/sfx/` (CC0, `CREDITS.md`).
- Recurring characters: `kirdaar/*.json`; series: `series/*.json`.
- `.github/workflows/render.yml`: renders (input `file: scripts/<path>.txt`), publishes release `reel-<id>`, the
  studio page plays it. `golden.yml`: the 2D look must stay pixel-identical (`tests/golden.py`).
- Default branch for work: `desi-toons-studio`.

## Rules
- Never change the default (flat) look by accident: new behaviour is opt-in (a new word / `CAM:` line).
- Sounds: only CC0 / licences that allow monetised use. No copyrighted meme clips or film dialogue audio.
- Comedy: never mock religion, caste, disability or real people by name; nothing graphic.

## Testing
`pip install -r requirements.txt` (+ pytest), `python -m pytest -q tests`, `python tests/golden.py check`.
Preview a frame: `python -m studio.render scene.json --no-tts --frame 2.5 -o x.png --width 360`.

## Usage limits
The owner is on a limited plan: one contact sheet per reel, no re-reading large files, batch fixes, short replies.

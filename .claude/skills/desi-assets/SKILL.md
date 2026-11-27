---
name: desi-assets
description: Use when a reel needs a place, prop, look, animal, vehicle, recurring character or sound. Finds what the studio already has and, if missing, builds it in the engine's style, registers it in the script words and tests it so later reels reuse it.
---

# Reuse first, build once

## Find (cheap: grep, never read whole files)
- Script words the writer can use: `python -c "import studio.script as s; print(s.vocab())"`, and
  grep `SCRIPT_PROMPT.md` (places, actions, props, looks lists) and `studio/script.py` word tables.
- Places: `locations.py`, `places_plus.py`, `places_gaon.py`, `places_2026.py`, `places_studio.py`; 2.5D sets:
  `sets.py`, `style25d/`, mapping in `styles.py`. Props: `objects.py` (SPOTS, THELA, SHOP...), set pieces
  `sets.py`; looks: `look.py` + `assets/looks/`; animals `animals.py`; vehicles `vehicles.py`; effects
  `effects.py`; recurring characters `kirdaar/*.json`.
- Can an existing thing do it with a word (time, weather, variant, dress pack, OBJ, look words)? Prefer that.

## Build (same style as the neighbours)
- A place: a draw function next to similar places (layers sky / far / window so 2.5D gets depth), people stand
  around y = 1700 on the 1080x1920 canvas; give it built-in life (something that moves / flickers / passes).
  Register it where the others are (grep an existing place name across `studio/` to see every table to touch:
  places list, styles mapping, SCRIPT_PROMPT places list, words, tests).
- A prop / object / look / animal: copy the closest existing one's pattern and tables.
- A recurring character: `kirdaar/<name>.json` (copy `sultan.json` fields).
- Add or extend a test in `tests/` (grep a test of a similar asset), run `python -m pytest -q tests` and
  `python tests/golden.py check`: the default look must not change.
- Render one frame with it and include it in the contact sheet.

## Sounds
`assets/sfx/<name>.ogg` replaces the made sound of the same name (`audio.py` SFX names). Only CC0 (or licences
that allow monetised use), credited in `assets/sfx/CREDITS.md`; never copyrighted meme clips. Freesound CC0 is
reachable from the cloud environment (key injected by the proxy).

Tell the owner one line per new asset ("Naya: `kabadi_shop` — taraazu hilta hai, aage bhi kaam aayega").

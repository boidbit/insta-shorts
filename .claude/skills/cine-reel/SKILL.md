---
name: cine-reel
description: Use whenever the owner pastes a comedy script, dialogue lines or a reel idea in chat (even with no other words). Turns it into a directed, cinematic ("zinda") reel - beats, shot list, CAM/CUT lines, lively staging, new assets if needed - previews it, pushes and renders it on GitHub.
---

# Cinematic reel from chat

Chat = "zinda" mode. Do not ask what to do: start. Ask only if something blocks (e.g. the idea is one word).

## 1. Script
- Idea only → write the script yourself in the format of `SCRIPT_PROMPT.md` (grep the parts you need: places
  list, actions, feelings, props, CAST words; do not read all of it). Comedy rules from it apply (one flavour, punch
  last, short lines, max 4 people).
- Owner's script → keep their words and order. Roman lines without Devanagari: add `| देवनागरी` yourself.
- Save as `scripts/cine/<id>.txt` (`<id>` = short kebab-case of the hook).

## 2. Beat sheet (in your head, 1 line each)
hook (first 1-2 s: action + face, never a walk-in) → setup → escalation (each line worse) → punch → reaction /
button. For each beat pick: shot size, angle, camera move, who reacts, what moves in the background, sound.
Use skill `alive-frames` for the choices.

## 3. Direct it in the script
- `CUT` lines for new angles: `CUT ots B`, `CUT reverse`, `CUT wide`, `CUT close B`, `CUT two_shot`.
- `CAM:` lines (put right before the line they belong to; the camera move starts there):
  `CAM: push B [zoom] [secs]`, `CAM: snap B`, `CAM: whip B`, `CAM: follow B`, `CAM: pull [zoom] [secs]`,
  `CAM: frame X Y [zoom] [secs]`, `CAM: dutch [deg] [secs]`, `CAM: shake [amount]`.
  A shot with CAM lines is fully yours: the automatic camera stays out of it, the studio's opening shot too, and
  a slow camera breath keeps it alive. So in a CAM shot direct every speaker change (whip / push / snap).
- Staging: people move (`A -> walk center`, `near` / `far`, `enter back`, `exit left fast`), act on every line
  (feeling + action words), use props and set pieces; listeners react (`B -> facepalm`).
- World: weather / time words on SCENE (`SCENE: gully rain`, `night`), `MUSIC:` mood, sfx words on hits
  (boing, thud, whoosh, slap, ...), `slowmo` / `freeze` for one big beat.

## 4. Missing assets → skill `desi-assets` (build, register, test). Missing sounds → ask before adding.

## 5. Check + preview (one contact sheet)
```
python -m studio.script scripts/cine/<id>.txt -o <scratch>/<id>.json      # warnings = fix the script
python -m studio.render <scratch>/<id>.json --no-tts --frame T -o <scratch>/f_T.png --width 270
```
6-8 frames (hook, each beat's peak, punch, end), `ffmpeg ... hstack/tile` into one sheet in the scratchpad.
Look at it yourself first: faces covered? dead frame (same framing twice)? fix, then show the owner.

## 6. After the owner's OK
Commit `scripts/cine/<id>.txt` (+ assets) on a branch, PR into `desi-toons-studio`, merge when the owner allows,
then skill `reel-render-check`.

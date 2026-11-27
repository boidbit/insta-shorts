---
name: alive-frames
description: Use when directing a reel in this repo (CAM/CUT lines, staging, background life) or fixing a reel that looks flat or dead. Camera language, comedy timing and "always something moving" rules, mapped to this engine's script words.
---

# Never a dead frame (Desi Toons engine)

## 4 layers, all the time
1. **Camera moves**: every shot has a move (`CAM: push` slow on talk, `whip` to the listener, `snap` on shock,
   `pull` for a reveal / ending). CAM shots breathe by themselves. Never two shots in a row with the same framing.
2. **People act**: feeling + action on every line, listeners react, somebody moves at least every ~3 s (walk,
   near/far, turn `side`/`saamne`, sit/stand, prop use). Big moments: anticipation then action (`B (shock) -> jump`).
3. **World lives**: pick places with built-in life (street / bus_stop traffic, railway train, market flags, fans,
   TV flicker, chai steam), add weather/time (`rain`, `fog`, `leaves`, `fireflies`, `night`), OBJ set pieces,
   a crowd or passers-by; 2.5D (`STYLE: 2.5d`) for parallax depth.
4. **Sound marks motion**: sfx words on hits and entrances, `MUSIC:` mood that fits (suspense for a build, comedy
   for banter), ambience from the place.

## Camera language → words
| Need | Use |
|---|---|
| tension, realisation, emotion rising | `CAM: push B 1.7 2` (slow) |
| shock, comic hit | `CAM: snap B` + `shake` / sfx |
| reaction, face-off ping-pong | `CAM: whip B`, `CUT ots B`, `CUT reverse` |
| power / looming boss, mummy, police | `CUT close B` + `B -> near`, low framing via `enter back` |
| small / helpless | `CAM: pull 1.0` with the person alone, `far` |
| chaos, fear, anger | `CAM: dutch 7 1.2`, `shake` |
| discovery of a thing | `CAM: frame X Y 2.2 0.4` on the prop (≤1 s), then `CAM: snap` on the face |
| journey, chase | `exit right` + `SCENE: <place> pan`, `CAM: follow A` |
| big entrance | `enter back` / `enter pop` + `CAM: snap` |
| ending / button | `CUT wide` or `CAM: pull`, everybody reacts, loop-friendly last frame |

## Comedy timing
- Hook in 1 s: the weirdest image + the first line already spoken.
- Rule of three: two normal beats, the third breaks; cut faster as it escalates (1-1.5 s shots).
- Punch: a beat of silence is added before it; then `snap` or a held deadpan face (no move = the joke).
- Reaction shot after every punch; `freeze` + NARRATOR for one "yup, that's me" moment max.
- End on a reaction or exit, not on the line.

## Self-check before the contact sheet
Each beat: camera move? who acts, who reacts? what moves behind them? sound? framing different from the last?

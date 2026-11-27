---
name: reel-render-check
description: Use after a cine reel script is pushed, or when the owner asks to render or check a reel. Triggers the GitHub "render.yml" workflow with the script file, then checks the release video, timing and sound, and gives the caption + hashtags.
---

# Render on GitHub and check

1. Trigger (GitHub MCP `actions_run_trigger`, repo `boidbit/insta-shorts`, workflow `render.yml`, ref = the branch
   with the script): inputs `{ stage: "video", file: "scripts/cine/<id>.txt", width: "1080", voice: "true" }`.
   Leave the other inputs at their defaults (tts auto = Gemini when the secret is set).
2. Wait without tight polling (check every few minutes). Failure: read only the failing step log, fix, re-run.
3. Result: release `reel-<run id>` (mp4, cover png, `*.post.txt` caption, script, scene json); the studio page
   plays it. Download the mp4 to the scratchpad and check: length (`ffprobe`), loudness
   (`ffmpeg -af volumedetect`: max below -1 dB, voice not buried by music), 3-4 frames (faces visible, subtitles
   not over faces).
4. Tell the owner (short Hinglish): release link, length, anything fixed, and the caption + hashtags from
   `*.post.txt` (improve the hook line if it is weak: curiosity, no spoiler of the punch).

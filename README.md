# Stickman Studio

`scene.json` likho → GitHub Action `.mp4` bana deta hai (1080x1920 reel). Hindi voice, lip-sync, beat music, captions. Video ke **2 style** hain, aur dono ek hi repo me alag-alag rehte hain:

| Style | Kaisa dikhta hai | Kab use karo |
|---|---|---|
| `"style": "2d"` (default) | Classic desi stickman, flat backgrounds (kitchen/room/street/school/night road) | Roz ke meme reels: halka aur tez |
| `"style": "2.5d"` | Layered parallax background, depth blur, kurta-pajama wale toon characters, asli camera, roshni, objects + effects | Tyohar ya special posts: zyada "3D type" feel |

Scene file me `"style"` na likho to wo **2d** hai. Isliye purani saari scenes aur templates bina chhede pehle jaisi hi videos dete hain.

## 1-minute start

```bash
pip install -r requirements.txt        # + ffmpeg system me chahiye
python -m studio.render scenes/2d/tag_karo_demo.json -o out/tag_karo.mp4 --width 720
python -m studio.render scenes/25d/gali_25d_demo.json -o out/gali.mp4 --width 720
python -m studio.render scenes/2d/tag_karo_demo.json --frame 1.5 -o out/preview.png   # sirf ek frame (fast)
python -m studio.render scenes/25d/gali_25d_demo.json --print-style                   # -> 2.5d
```

`--no-tts` laga do to voice skip hoti hai (testing ke liye).

## Folder ka naksha

```
studio/            core: dono style isi ko share karte hain
                   (scene format + timeline, Hindi TTS + lip-sync, music/sfx, captions/bubbles,
                    actions, chehra/expressions, baal/accessories, props, ffmpeg, AI director)
studio/styles.py   dono style ke niyam: kaunsa background/feature kis style ka hai
studio/style2d/    sirf 2d: stickman body, flat backgrounds, purana crop-zoom camera
studio/style25d/   sirf 2.5d: toon body, layered scenery, objects + fx, roshni, perspective
templates/2d/      templates/25d/        scenes/2d/      scenes/25d/
tests/golden.py    golden-frame tests (neeche dekho)
```

**Mix nahi hota:** 2d scene me 2.5d cheez (jaise `kitchen_25d`, `"body": "toon"`, `objects`, `fx`) likh doge to render saaf error ke saath ruk jaata hai, aur sahi style ka hint deta hai. Isi tarah 2.5d scene me flat `kitchen`/`street` nahi chalega.

## Templates

**2d** (`templates/2d/`):

| Template | Kya hai | Kya badalna hai (`vars`) |
|---|---|---|
| `tag_karo` | Loop meme: 3 stickmen dance + upar caption | `caption`, `bg` |
| `dost_types` | 3 dost, har ek ka label + line + Hindi voice | `label_a/b/c`, `line_a/b/c`, `speak_a/b/c`, `outro` |
| `dialogue` | 2 stickmen ki 4-line baat-cheet | `l1..l4`, `s1..s4`, `caption`, `bg` |
| `kaun_sahi` | Poll: sawal + 2 option cards | `question`, `option_a/b`, `cta` |
| `song_reel` | Night road pe musafir + lyric lines | `l1..l4`, music (`music.path`) |

**2.5d** (`templates/25d/`):

| Template | Kya hai | Kya badalna hai (`vars`) |
|---|---|---|
| `diwali_bomb` | Diwali ki raat, chhat: bomb jalana → phuss → BOOM | `caption`, `l1..l6`, `s1..s6`, `cta` |
| `kitchen_mummy` | Din ka kitchen: beta khana maange, mummy belan ke saath kaam pakda de | `caption`, `l1..l3`, `s1..s3`, `cta` |
| `gali_udhaar` | Golden-hour gali: chai tapri par udhaar | `caption`, `l1..l4`, `s1..s4`, `cta` |

Scene file chhoti hoti hai (style template se aata hai):

```json
{ "extends": "tag_karo", "vars": { "caption": "Aapke group me bhi aisa dost hai? Tag karo! 😂" } }
{ "extends": "gali_udhaar", "vars": { "caption": "Har gali me ek aisa dost 😂" } }
```

Poora control chahiye to template ke upar kuch bhi override karo (`characters`, `timeline`, `background`...). `timeline` list override karne par poori replace hoti hai. Bina template ke 2.5d scene likhni ho to upar `"style": "2.5d"` likhna mat bhoolna.

## Voice (Hindi) ka ek zaroori rule

Bubble me dikhne wala text Roman Hinglish me hota hai (`say`), lekin TTS ko **Devanagari** chahiye (`speak`), warna uchcharan galat aata hai:

```json
{ "who": "A", "say": "Bhai chai pila de", "speak": "भाई चाय पिला दे" }
```

Voices: `hi-IN-MadhurNeural` (male), `hi-IN-SwaraNeural` (female). Har character ko alag `pitch`/`rate` do (`"voice": {"name": "...", "pitch": "+20Hz", "rate": "+8%"}`) to alag-alag awaaz lagti hai. Mooh ka khulna-band hona awaaz ki loudness se sync hota hai.

2.5d me har voice clip ke aage-peeche ka silence apne aap kat jaata hai, isliye dialogue tez chalta hai. 2d me purani timing hi rehti hai. Chaho to kisi bhi scene me `"meta": {"trim_voice": true}` (ya `false`) likh ke badal sakte ho.

## GitHub Actions

1. Repo GitHub pe push karo.
2. **Actions → Render stickman video → Run workflow**.
   - `scene`: koi bhi `scenes/2d/*.json` / `scenes/25d/*.json` (ya `all`)
   - `style`: `all` ke saath kaunsa style chahiye (`2d` / `2.5d` / `all`). AI director ke liye bhi yahi style use hota hai.
   - `width`: 1080 (full) ya 720 (fast)
   - `voice`: Hindi voice on/off
3. Run ke baad **Artifacts → stickman-videos** me `out/2d/...` aur `out/25d/...` folders me `.mp4` aur preview `.png` milti hai.
4. `scenes/**/*.json` push karne par bhi apne aap render hota hai.

### AI Director (optional)

Secret `ANTHROPIC_API_KEY` add karo (Settings → Secrets → Actions). Phir Run workflow me `instruction` me idea likho aur `style` chuno, jaise:

> 3 dost, ek ko chai ka bill dena hai, baaki bahaane bana rahe hain

Har style ka apna prompt hai (`DIRECTOR_PROMPT.md` = 2d, `DIRECTOR_PROMPT_25D.md` = 2.5d), to AI ko sirf usi style ke options dikhte hain. Galti ho jaaye (galat action, ya dono style mix) to director khud sudharwata hai. Local me:

```bash
python -m studio.director "idea" -o scenes/generated/x.json                 # 2d
python -m studio.director --style 2.5d "idea" -o scenes/generated/y.json    # 2.5d
```

## Golden-frame tests (2d kabhi galti se na badle)

```bash
python -m tests.golden check                      # dono style ke frames tests/golden/ se compare
python -m tests.golden compare-base --base ../main-checkout   # 2d frames: main ke code vs is code, pixel-identical?
python -m tests.golden update                     # look jaan-boojh ke badla ho tabhi: golden PNG dobara banao
```

GitHub par **Golden frames** workflow har push aur PR par `compare-base` chalata hai: 2d demo frames `main` ke code aur naye code dono se usi machine par render hote hain, aur ek bhi pixel alag hua to check fail ho jaata hai. Diff images **Artifacts → golden-diffs** me milti hain. `check` wala step sirf jaankari ke liye hai, kyunki alag machine par fonts thode alag ho sakte hain.

## Scene schema (short)

Poora schema `DIRECTOR_PROMPT.md` (2d) aur `DIRECTOR_PROMPT_25D.md` (2.5d) me hai. Yaad rakhne layak:

- **Dono style me:** `characters` (`color`, `slot`/`x`, `accessories`: glasses, cap, tuft, moustache, beard, bindi, hair_short, hair_curly, hair_bun, earrings; `voice`), timeline (`t`, `who`, `action`, `expression`, `prop`, `label`, `say` + `speak`, `look`, `move`, `sfx`, `camera`, `overlay`, `hold`)
- **actions**: idle, talk, dance (`style`: pump/swing/cheer/disco), point, laugh, shock, jump, wave, clap, cry, fall, walk, facepalm, shrug, sway, sleep, reach, cover_ears
- **expressions**: neutral, smile, smug, sly, shock, shout, laugh, grin, cry, angry, surprised, think, wink, dead, love, sleepy, sad, nervous, scared, burnt
- **props**: spoon, phone, mic, cup, ball, stick, agarbatti, phuljhadi, belan, kettle, chai_glass. **sfx**: pop, boing, whoosh, ding, thud, clap, beep, laugh_track, fizz, boom, whistle
- **2d backgrounds**: kitchen, room, street, school, night_road (scrolling), plain, ya apna `image`
- **2.5d backgrounds**: `diwali_rooftop` (raat, chhat, jhalar, patakhe), `kitchen_25d` (din, khidki ke bahar ka nazara, jaali wali dhoop, dhool, cooker ki bhaap), `gali_25d` (golden hour, kirana dukaan, khamba + taar, chai tapri), plain, apna `image`
- **Sirf 2.5d:** character `y` = gehrai (peeche = chhota), `pants`/`skin`, `objects` (bomb, anaar, diya), `{"object": "bomb", "burn": 5}` / `stop` / `hide`, `{"fx": {"type": "sparks" | "boom" | "flash", "at": ...}}`, `light`. Camera me `"focus"` object par bhi, `"head"`, `"dx"`. Zoom 2x tak sharp rehta hai. Chai counter jaise set pieces ke aage ya peeche character khada ho sakta hai (chaiwala `x 990, y 1268`).
- Camera me `"dur": 0` = seedha cut (dono style).

Speed: 2.5d 1080p par lagbhag 0.25 sec/frame (17 sec ki reel ~2 minute). 2d isse kaafi tez hai.

## Apna asset daalna

- Background: PNG/JPG `assets/backgrounds/` me rakho → `"background": {"type": "image", "path": "assets/backgrounds/mera.png"}` (9:16 best). Ye dono style me chalta hai, lekin ek single image hone ki wajah se isme parallax nahi hota.
- Music: `"music": {"path": "assets/music/gaana.mp3", "volume": 0.4}` (generated beat bina copyright wala hai; kisi gaane ka use apni zimmedari pe).
- Font: `assets/fonts/main.ttf` rakho to caption/bubble usi me banenge (Devanagari ke liye `assets/fonts/devanagari.ttf`).

## Limits (sach me)

- Characters code se bane hain (stickman ya toon); haath se bane ya AI art jaisi detail nahi hogi. Naye look ke liye `studio/style2d/` / `studio/style25d/` badlo ya apni PNG backgrounds do.
- 2.5d asli 3D nahi hai: camera zoom/pan/shake kar sakta hai, lekin character ke chaaron taraf ghoom nahi sakta.
- 2.5d ke parallax backgrounds abhi code se bane 3 presets hain.
- Bubble ke andar emoji ke liye `fonts-noto-color-emoji` chahiye (workflow khud install karta hai).
- Hindi voice `edge-tts` (Microsoft online service) se aati hai, isliye internet chahiye; bina internet ke `--no-tts`.

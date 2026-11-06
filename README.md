# Stickman Studio

`scene.json` likho → GitHub Action `.mp4` bana deta hai (1080x1920 reel). Desi stickman format: upar caption box, 3 stickmen, kitchen/room/street/school/night-road backgrounds, Hindi voice, lip-sync, beat music.

## 1-minute start

```bash
pip install -r requirements.txt        # + ffmpeg system me chahiye
python -m studio.render scenes/tag_karo_demo.json -o out/tag_karo.mp4 --width 720
python -m studio.render scenes/tag_karo_demo.json --frame 1.5 -o out/preview.png   # sirf ek frame (fast)
```

`--no-tts` laga do to voice skip hoti hai (testing ke liye).

## Templates (`templates/`)

| Template | Kya hai | Kya badalna hai (`vars`) |
|---|---|---|
| `tag_karo` | Loop meme: 3 stickmen dance + upar caption | `caption`, `bg` |
| `dost_types` | 3 dost, har ek ka label + line + Hindi voice | `label_a/b/c`, `line_a/b/c`, `speak_a/b/c`, `outro` |
| `dialogue` | 2 stickmen ki 4-line baat-cheet | `l1..l4`, `s1..s4`, `caption`, `bg` |
| `kaun_sahi` | Poll: sawal + 2 option cards | `question`, `option_a/b`, `cta` |
| `song_reel` | Night road pe musafir + lyric lines | `l1..l4`, music (`music.path`) |

Scene file chhoti hoti hai:

```json
{ "extends": "tag_karo", "vars": { "caption": "Aapke group me bhi aisa dost hai? Tag karo! 😂" } }
```

Poora control chahiye to template ke upar kuch bhi override karo (`characters`, `timeline`, `background`...). `timeline` list override karne par poori replace hoti hai.

## Look / depth (optional, `meta` me)

Default me ye teen cheezein on hain; band karne ya adjust karne ke liye scene ke `meta` me likho:

```json
"meta": { "shadows": true, "depth": 0.3, "vignette": 0.18 }
```

- `shadows`: har character ke pairon ke neeche soft shadow; jump karne par chhota + halka ho jata hai.
- `depth`: `0` = off. Character `y` ke hisaab se chhota/bada hota hai (`y` jitna upar/door, utna chhota). Default ground `y=1700` par size 1.0 hi rehta hai, to purane scenes nahi badalte. Background ki `horizon` (floor kahan se shuru) badalni ho: `"background": {"type": "room", "horizon": 1200}`.
- `vignette`: `0` = off. Kone halke dark/warm (captions par asar nahi).

`room` background me window ki dhoop ka halka patch floor par bana hua hai.

`night_road` ab parallax ke saath scroll hota hai: taare/chaand bahut dheere, door ki pahadiyan dheere, paas ki pahadiyan thoda tez, aur sadak + lamp post poori `scroll` speed se. Purana "sab ek speed" look chahiye to `"background": {"type": "night_road", "scroll": 220, "parallax": 0}` (default `1`; `0.5` = aadha asar).

## Foreground props (character ke aage/peeche)

Background me `foreground` do to kuch cheezein characters ke **upar** draw hoti hain. Har cheez ki ek depth `y` hoti hai: jo character us `y` se upar (door/peeche) khada hai wo cheez ke peeche chhupta hai, jo neeche (paas) hai wo aage dikhta hai. Default ground `y=1700` par character hamesha aage rehta hai; peeche khada karne ke liye `"y": 1540` do (ya `move`).

```json
"background": { "type": "kitchen", "foreground": ["island"] },
"characters": { "B": { "x": 540, "y": 1540 } }
```

| Prop | Kahan ka | Depth |
|---|---|---|
| `table` | room (coffee table) | 1620 |
| `island` | kitchen (solid counter, peeche khade ke pair chhup jaate hain) | 1620 |
| `desk` | school | 1620 |
| `bench` | street | 1620 |
| `poles` | night_road: tez guzarte ped ke tane, sabse aage | - |

Koi bhi prop kisi bhi background par laga sakte ho. `night_road` par `poles` default hain; band karne ke liye `"foreground": []`. Camera zoom foreground ke saath hota hai, captions/bubbles hamesha upar rehte hain.

## Voice (Hindi) ka ek zaroori rule

Bubble me dikhne wala text Roman Hinglish me hota hai (`say`), lekin TTS ko **Devanagari** chahiye (`speak`), warna uchcharan galat aata hai:

```json
{ "who": "A", "say": "Bhai chai pila de", "speak": "भाई चाय पिला दे" }
```

Voices: `hi-IN-MadhurNeural` (male), `hi-IN-SwaraNeural` (female). Har character ko alag `pitch`/`rate` do (`"voice": {"name": "...", "pitch": "+20Hz", "rate": "+8%"}`) to alag-alag awaaz lagti hai. Mooh ka khulna-band hona awaaz ki loudness se sync hota hai.

## GitHub Actions

1. Repo GitHub pe push karo.
2. **Actions → Render stickman video → Run workflow**.
   - `scene`: koi bhi `scenes/*.json` (ya `all`)
   - `width`: 1080 (full) ya 720 (fast)
   - `voice`: Hindi voice on/off
3. Run ke baad **Artifacts → stickman-videos** me `.mp4` aur preview `.png` milti hai.
4. `scenes/*.json` push karne par bhi apne aap render hota hai.

### AI Director (optional)

Secret `ANTHROPIC_API_KEY` add karo (Settings → Secrets → Actions). Phir Run workflow me `instruction` me bas idea likho, jaise:

> 3 dost, ek ko chai ka bill dena hai, baaki bahaane bana rahe hain

`studio/director.py` Claude se scene JSON banwata hai (`DIRECTOR_PROMPT.md` rules ke saath), galat action/expression ho to khud sudharwata hai, aur phir render ho jata hai. Local me: `python -m studio.director "idea" -o scenes/generated/x.json`.

## Scene schema (short)

Poora schema `DIRECTOR_PROMPT.md` me hai. Yaad rakhne layak:

- **characters**: `color`, `slot` (`left|center|right`), `accessories` (`glasses, cap, tuft, moustache, beard, bindi`), `voice`
- **timeline events**: `t`, `who`, `action`, `expression`, `prop`, `label`, `say` + `speak`, `look`, `move`, `sfx`, `camera`, `overlay`, `hold`
- **actions**: idle, talk, dance (`style`: pump/swing/cheer/disco), point, laugh, shock, jump, wave, clap, cry, fall, walk, facepalm, shrug, sway, sleep
- **expressions**: neutral, smile, smug, sly, shock, shout, laugh, grin, cry, angry, surprised, think, wink, dead, love, sleepy, sad
- **backgrounds**: kitchen, room, street, school, night_road (scrolling), plain, ya apna `image`

## Apna asset daalna

- Background: PNG/JPG `assets/backgrounds/` me rakho → `"background": {"type": "image", "path": "assets/backgrounds/mera.png"}` (9:16 best).
- Music: `"music": {"path": "assets/music/gaana.mp3", "volume": 0.4}` (generated beat bina copyright wala hai; kisi gaane ka use apni zimmedari pe).
- Font: `assets/fonts/main.ttf` rakho to caption/bubble usi me banenge (Devanagari ke liye `assets/fonts/devanagari.ttf`).

## Limits (sach me)

- Characters code se bane flat stickmen hain; AI-generated art jaisi detail nahi hogi. Naye look ke liye `studio/characters.py` / `studio/backgrounds.py` badlo ya apni PNG backgrounds do.
- Bubble ke andar emoji ke liye `fonts-noto-color-emoji` chahiye (workflow khud install karta hai).
- Hindi voice `edge-tts` (Microsoft online service) se aati hai, isliye internet chahiye; bina internet ke `--no-tts`.

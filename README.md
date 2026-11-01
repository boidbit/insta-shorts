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

## Voice (Hindi) ka ek zaroori rule

Bubble me dikhne wala text Roman Hinglish me hota hai (`say`), lekin TTS ko **Devanagari** chahiye (`speak`), warna uchcharan galat aata hai:

```json
{ "who": "A", "say": "Bhai chai pila de", "speak": "भाई चाय पिला दे" }
```

Voices: `hi-IN-MadhurNeural` (male), `hi-IN-SwaraNeural` (female). Har character ko alag `pitch`/`rate` do (`"voice": {"name": "...", "pitch": "+20Hz", "rate": "+8%"}`) to alag-alag awaaz lagti hai. Mooh ka khulna-band hona awaaz ki loudness se sync hota hai.

### Gemini voice (realistic) - poori script ek hi request me

Free Gemini key ka quota kam hota hai, isliye **ek scene ki saari lines ek hi API request me** bheji jaati hain, ek lambi audio aati hai, aur use lines ke beech ke pause pe kaat kar har line ka alag clip banta hai (lip-sync/timing waise hi chalte hain).

```bash
export GEMINI_API_KEY=...            # https://aistudio.google.com/apikey  (GitHub: Settings -> Secrets -> GEMINI_API_KEY)
python -m studio.render scenes/dost_types_demo.json -o out/x.mp4 --tts gemini
```

- `--tts auto` (default): key set hai to Gemini, warna edge-tts. Auto me Gemini fail ho (quota/network) to edge-tts pe girta hai; `--tts gemini` me fail hone pe render ruk jata hai (awaaz chupke se nahi badalti).
- Result `.cache/tts/gemini_*` me save hota hai: dobara render / preview frame / GitHub Action re-run = **0 extra requests** (jab tak script same hai). Script ka ek akshar badla to nayi request lagegi.
- Gemini ek request me max **2 awaazein** deta hai. Do se zyada characters ho to wo in 2 awaazon ko share karte hain; `pitch`/`rate` (ffmpeg se) unhe alag banate hain.
- Voice chunna ho: `"voice": {"gemini": "Kore"}` (female: Kore, Leda, Aoede...; male: Puck, Charon, Fenrir...). Na do to Swara -> Kore, baaki -> Puck.
- Style badalna ho: scene `meta.tts` me `{"model": "...", "style": "..."}`.
- Split pause pe tika hai: Gemini se lines ke beech ~1s ka pause maanga jaata hai. Agar ek line ke andar lamba pause aa gaya to split galat ho sakta hai; render log me har line ka `start-end` aur text print hota hai, wahan check kar lo. Same script dobara bhejna hai to `.cache/tts/gemini_*` delete karo.

Tests: `python -m unittest discover -s tests` (network/key nahi chahiye).

## GitHub Actions

1. Repo GitHub pe push karo.
2. **Actions → Render stickman video → Run workflow**.
   - `scene`: koi bhi `scenes/*.json` (ya `all`)
   - `width`: 1080 (full) ya 720 (fast)
   - `voice`: Hindi voice on/off
   - `tts`: `auto` / `gemini` / `edge` (Gemini ke liye secret `GEMINI_API_KEY`)
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

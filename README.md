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

## 2.5D / "3D type" look (naya)

`scenes/diwali_3d_demo.json` dekho. Ye asli 3D nahi hai: 2D cartoon ko teen cheezon se depth milti hai:

- **Layered background** (`"background": {"type": "diwali_rooftop"}`): aasmaan, door ka shehar, beech ki buildings, chhat aur saamne ki cheezein alag-alag parton me hain. Camera hilta hai to har parat alag speed se khiskti hai (parallax). Door wali parton par blur (depth of field) hai, jhalar ki lights tim-timaati hain aur aasmaan me patakhe phat-te hain. Naya preset `studio/scenery.py` me banta hai (`PRESETS`).
- **3 preset:** `diwali_rooftop` (raat, chhat), `kitchen_25d` (din, khidki ke bahar ka nazara alag parat me, jaali wali dhoop, dhool ke kann, cooker ki bhaap), `gali_25d` (golden hour, kirana dukaan, khamba aur uljhe taar, chai tapri). Demo: `scenes/kitchen_25d_demo.json`, `scenes/gali_25d_demo.json`. Purane flat `kitchen` / `street` waise hi hain.
- **Depth-sorted set pieces:** background me aisi cheezein ho sakti hain jinke aage ya peeche character khada ho (jaise chai ka counter: chaiwala `x 990, y 1268` par counter ke peeche, customer aage).
- **Toon body** (`"body": "toon"`): moti outline wale haath-pair, kurta-pajama, chappal, light/shadow shading, bada sir. `"pants"`, `"skin"`, `"hair_short"` / `"hair_curly"` / `"hair_bun"` / `"earrings"` bhi de sakte ho. Naye props: `belan`, `kettle`, `chai_glass`, `agarbatti`, `phuljhadi`. Saare purane actions isme bhi chalte hain.
- **Asli camera**: zoom (2x tak) par bhi character sharp rehta hai, kyunki wo zoom ke hisaab se dobara draw hota hai, image ko stretch nahi kiya jaata. Har character ke neeche parchhaai, scene ki roshni ka rang aur vignette bhi lagte hain. Jo character peeche khada hai (`"y": 1330`), wo apne aap chhota dikhta hai.
- **Objects + effects**: `"objects"` (bomb, anaar, diya), timeline me `{"object": "bomb", "burn": 5}`, `{"fx": {"type": "sparks", "at": "bomb"}}`, `{"fx": {"type": "boom", "at": "bomb"}}`, sfx `fizz` / `boom` / `whistle` (cooker ki seeti). Camera me `"dur": 0` = seedha cut.
- Hindi voice clips ke aage-peeche ka silence ab apne aap kat jaata hai, isliye dialogue tez chalta hai.

Speed: 1080p par lagbhag 0.25 sec/frame, yaani 17 sec ki reel ~2 minute me.

## Apna asset daalna

- Background: PNG/JPG `assets/backgrounds/` me rakho → `"background": {"type": "image", "path": "assets/backgrounds/mera.png"}` (9:16 best).
- Music: `"music": {"path": "assets/music/gaana.mp3", "volume": 0.4}` (generated beat bina copyright wala hai; kisi gaane ka use apni zimmedari pe).
- Font: `assets/fonts/main.ttf` rakho to caption/bubble usi me banenge (Devanagari ke liye `assets/fonts/devanagari.ttf`).

## Limits (sach me)

- Characters code se bane hain (stickman ya `toon`); hath se bane / AI art jaisi detail nahi hogi. Naye look ke liye `studio/characters.py` / `studio/scenery.py` badlo ya apni PNG backgrounds do.
- 2.5D hai, asli 3D nahi: camera zoom/pan/shake kar sakta hai, lekin character ke chaaron taraf ghoom nahi sakta.
- 2.5D backgrounds abhi code se bane presets hain (3); apni AI/PNG image wale background me abhi parallax nahi hai.
- Bubble ke andar emoji ke liye `fonts-noto-color-emoji` chahiye (workflow khud install karta hai).
- Hindi voice `edge-tts` (Microsoft online service) se aati hai, isliye internet chahiye; bina internet ke `--no-tts`.

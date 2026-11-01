# Desi Toons Studio

Idea ya script do → 1080x1920 Instagram reel ban jati hai: Indian cartoon log (kurta, saree, uncle, aunty, dadi...), Hindi awaaz + lip-sync, pehle second me hook, ek video me kai jagah (ghar → sadak → ghar), beat music, aur Instagram caption + hashtags.

## Sabse aasaan: webpage

```bash
pip install -r requirements.txt        # + ffmpeg system me chahiye
python -m studio.web                   # browser me kholo: http://127.0.0.1:7860
```

Page pe 3 tareeke hain:

| Tab | Kya karta hai | AI key chahiye? |
|---|---|---|
| 💡 Idea do | "mummy ne doodh mangaya, beta cricket khelne chala gaya" → AI poori kahani, hook, acting, caption bana deta hai. Khali chhodo to AI khud topic chunta hai. | Haan (`GEMINI_API_KEY` free hai, ya `ANTHROPIC_API_KEY`) |
| 📝 Apni script | Aapki likhi script, bilkul usi line-order me | Nahi |
| ⚙️ JSON | Poora control (neeche schema) | Nahi |

"Banao" dabao → progress bar → video, download button, caption copy button.

AI key ke saath chalana: `GEMINI_API_KEY=xxxx python -m studio.web` (key: aistudio.google.com → Get API key). Model badalna ho to `GEMINI_MODEL` / `DIRECTOR_MODEL`.

## Script format (bina AI)

```
HOOK: Mummy ka ek kaam... aur hum 😭
CAST: M = mummy, R = college_boy, D = dost cap
SCENE: room
M (think, point): Beta, jaldi se doodh le aana! | बेटा, जल्दी से दूध ले आना!
R (grin): Haan mummy, bas 2 minute! | हाँ मम्मी, बस दो मिनट!
R -> exit right
SCENE: street | Raste me... 🚶
R -> enter left
D (wave, ball): Bhai! Ek match ho jaye? | भाई! एक मैच हो जाए?
ALL -> jump laugh clap
SCENE: room | 3 ghante baad... ⏰
M (shout, point, boing, shake): Doodh kahan hai?! | दूध कहाँ है?!
CTA: Tag karo us dost ko 👇
CAPTION: Instagram caption (video me nahi dikhta)
HASHTAGS: #desicomedy #mummy
```

- `NAAM (shabd): Roman line | देवनागरी line` = bolne wali line. `|` ke baad wala hissa awaaz padhti hai. Na do to awaaz Roman padhegi (uchcharan bigad sakta hai).
- Bracket ke shabd: expression (`angry, shock, laugh, sly...`), action (`point, shrug, facepalm, dance, jump, fall...`), cheez (`phone, cup, ball, mic...`), sfx (`boing, thud, whoosh...`), `shake`.
- `NAAM -> enter left | exit right | walk center | dance | facepalm ...` = bina bole action. `ALL ->` sab ke liye.
- `SCENE: jagah | title`: kitchen, room, street, school, night_road, plain. Title ek card ki tarah 1.4s dikhta hai.
- CAST me role likh sakte ho (mummy, papa, dadi, dada, dost, bhai, behen, teacher, boss, bachcha) ya look naam + extra: `chubby glasses beard bindi saree red ...`.
- `wait 1.5` = ruko.

Command line se: `python -m studio.script scripts/doodh_story.txt -o scenes/doodh.json` phir render.

## Characters

Ready looks: `boy, girl, college_boy, college_girl, uncle, aunty, dada, dadi, kid, kid_girl, office_guy, office_girl`. Har cheez badal sakte ho:

```json
"R": { "look": "uncle", "outfit": "kurta", "color": "saffron", "accessories": ["turban", "beard"], "build": "chubby" }
```

- `skin`: fair, wheatish, brown, dark · `hair`: short, side_part, spiky, curly, balding, bald, long, braid, bun, ponytail · `hair_color`: black, brown, grey, white, henna
- `outfit`: tshirt, shirt, kurta, salwar (dupatta ke saath), saree, uniform, blazer, vest · `color` / `accent` (dupatta, blouse, tie) / `pants` / `shoes` (black, white, chappal)
- `build`: slim, normal, chubby · `scale` (bachche ~0.72) · `accessories`: glasses, cap, turban, moustache, beard, bindi, tilak, earrings
- 17 expressions, 17 actions (walk, talk, dance, point, laugh, shock, jump, wave, clap, cry, fall, facepalm, shrug, sway, sleep...)

## Ek video me kai jagah (multi-scene)

```json
{
  "hook": "Mummy ka ek kaam... aur hum 😭",
  "transition": "whip",
  "characters": { "M": { "look": "aunty" }, "R": { "look": "college_boy" } },
  "overlays": [ { "text": "Mummy ka ek kaam... aur hum 😭", "style": "hook", "pos": [540, 420], "to": 2.0 } ],
  "scenes": [
    { "background": { "type": "room" }, "cast": ["M", "R"], "timeline": [ ... ] },
    { "title": "Raste me...", "background": { "type": "street" }, "cast": ["R"],
      "characters": { "R": { "x": -140 } }, "timeline": [ { "t": 0, "who": "R", "move": { "x": 540, "dur": 1.2 } } ] }
  ],
  "post": { "caption": "...", "hashtags": ["#desicomedy"] }
}
```

Poora example: `scenes/doodh_story_demo.json`. Poora schema: `DIRECTOR_PROMPT.md`. Music aur upar wale overlays (hook, caption) poori video pe chalte hain; transition `whip | fade | cut`.

## Hook styles (pehla second)

`pattern_interrupt` (Ruko!), `pov`, `relatable` (Agar tum bhi...), `curiosity` (end tak dekho), `list` (3 types ke...), `question` (kaun sahi?), `cold_open` (jhagde ke beech se), `expectation` (expectation vs reality). AI ko style do ya `auto`. Director check karta hai ki hook t=0 pe screen pe hai aur pehle second me kuch ho raha hai, warna khud sudharwata hai.

## Templates (`templates/`)

`tag_karo`, `dost_types`, `dialogue`, `kaun_sahi`, `song_reel`: chhoti scene file se `{ "extends": "dost_types", "vars": { "hook": "...", "line_a": "..." } }`.

## Command line

```bash
python -m studio.render scenes/doodh_story_demo.json -o out/doodh.mp4 --width 720
python -m studio.render scenes/doodh_story_demo.json --frame 8 -o out/preview.png     # ek frame (fast)
python -m studio.director "dadi aur naya smartphone" --hook pov                        # AI -> scenes/generated/*.json + .post.txt
python -m studio.director --count 3                                                   # AI khud 3 topic, 3 alag hooks
python -m unittest discover -s tests                                                  # checks
```

`--no-tts` = awaaz skip (testing).

## GitHub Actions

**Actions → Render video → Run workflow**: `instruction` (AI idea) + `hook` + `count`, ya `script` (scripts/*.txt), ya `scene`. Artifacts → `videos` me `.mp4`, preview `.png` aur `.post.txt` (caption + hashtags). `scenes/*.json` ya `scripts/*.txt` push karne par bhi apne aap render hota hai. AI ke liye secret `GEMINI_API_KEY` ya `ANTHROPIC_API_KEY` (Settings → Secrets → Actions).

## GitHub Pages wala page (render GitHub pe)

`index.html` (repo root) GitHub Pages pe chalta hai: https://boidbit.github.io/insta-shorts/

1. Page pe "⚙️ GitHub connection" kholo → fine-grained token banao (sirf is repo ke liye, **Actions: Read and write**, **Contents: Read-only**) → paste → Save. Token sirf aapke browser me rehta hai.
2. Idea likho (AI) ya script paste karo → **Banao**. Page `render.yml` workflow chalata hai aur har step ki progress dikhata hai (~4-6 min).
3. Video GitHub **Release** (`reel-…`) me publish hoti hai; page wahi chalata hai, download + caption copy deta hai. "Pichli reels" me sab purani videos.

Branch: page us branch pe workflow chalata hai jo settings me likha hai (default `desi-toons-studio`). Repo public hai to releases (videos) bhi public dikhte hain.

## Webpage ko apne server pe daalna

Repo me `Dockerfile` hai. Hugging Face Space (Docker, free CPU) ya Render/Railway pe deploy karo, Space settings me secret `GEMINI_API_KEY` aur `STUDIO_PASSWORD` daalo (password ke bina koi bhi aapke page se video bana sakta hai). Free CPU pe 20s ki 720p video ~1-2 min me banti hai.

## Apna asset daalna

- Background: PNG/JPG `assets/backgrounds/` me → `"background": {"type": "image", "path": "assets/backgrounds/mera.png"}` (9:16 best).
- Music: `"music": {"path": "assets/music/gaana.mp3", "volume": 0.4}` (generated beat copyright-free hai; kisi gaane ka use apni zimmedari pe).
- Font: `assets/fonts/main.ttf` (Devanagari ke liye `assets/fonts/devanagari.ttf`).

## Limits (sach me)

- Characters code se bane flat cartoon hain: AI-generated art jaisi detail nahi. Naye kapde/baal `studio/characters.py` me jodo.
- Gaana: character gaa nahi sakta (TTS sirf bolta hai); lyrics + apna mp3 + jhoomna ho sakta hai (`song_reel`).
- Hindi voice `edge-tts` (Microsoft online service) se aati hai, internet chahiye.

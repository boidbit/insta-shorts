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
- `SCENE: jagah | title`: kitchen, room, street, school, market, office, bus_stop, night_road, plain. street/bus_stop/school me badal, parinde aur peeche se gaadiyan apne aap chalte hain. Title ek card ki tarah 1.4s dikhta hai.
- CAST me role likh sakte ho (mummy, papa, dadi, dada, dost, bhai, behen, teacher, boss, bachcha) ya look naam + extra: `chubby glasses beard bindi saree red ...`.
- `wait 1.5` = ruko.

Command line se: `python -m studio.script scripts/doodh_story.txt -o scenes/doodh.json` phir render.

## Gaana / lyrics (bilkul bina format ke)

Script ka format yaad nahi rakhna? Page ke **"📝 Apni script"** tab me (ya `scripts/x.txt` me) bas lyrics likho, har line ek lyric:

```
SECONDS: 60
Raat lambi hai, raasta khamosh
Chalta hu bina manzil ke
Chaand bhi saath chal raha hai
```

Agar text me `CAST:` / `SCENE:` / `A -> ...` / `NAME: ...` wali koi line nahi hai, to ye lyrics mode hai: ek kurta wala akela musafir night road pe chalta hai aur lyrics ek-ek karke aate hain. Kuch aur nahi likhna.

- `SECONDS: 60` = video kitne second ka (nahi likha to har lyric 3.2 sec). Lines jitni zyada, utni lambi; 17 lines = ~60 sec.
- Optional: `HOOK:`, `CTA:`, `CAPTION:`, `HASHTAGS:`, `MUSIC: beat 76` / `MUSIC: none` / `MUSIC: <apni audio ka path>`.
- **Awaaz nahi gaati.** Is mode me koi voice hai hi nahi: sirf lyrics + halka beat. Asli gaana: `MUSIC: none` rakho aur gaana Instagram me upar se daalo (copyright wahi sambhalta hai). Lyrics ki timing gaane se match nahi hogi, to `SECONDS` aur lines gaane ke hisaab se adjust karo.
- Page ka checker ("HOOK/CTA nahi hai") lyrics pe dikkat dikha sakta hai: confirm me "Phir bhi banau" dabao.

## Camera, objects aur naye formats

- **Camera apne aap:** har bolne wali line par speaker pe cut-in + halka push-in, punchline pe sabse tight shot + shake, phir wide reaction. Band karna ho: JSON me `"meta": {"auto_camera": false}`. Apni marzi: line ke brackets me `wide`, `medium`, `close`, `two_shot` (jaise `A (shock, close): ...` ya `ALL -> wide`).
- **Depth:** `B -> near` (character camera ki taraf aata hai, bada), `far` (peeche, chhota), `mid` (normal). `near` ke saath `close` mat milao: shot bahut tight ho jaata hai.
- **Objects:** `OBJ: truck enter left to right` (gaadi aati hai aur right pe ruk jaati hai), `OBJ: dustbin left`, `OBJ: truck exit right`. Objects: truck (kachra gaadi), auto, car, scooter, cow, dustbin, bags, table; rang (`OBJ: car red ...`), `front` (characters ke aage), `big`/`small`. Apni PNG: `OBJ: assets/objects/x.png right`. Gaadi ke aane tak kahani ruki rehti hai. Jahan character khade hain wahan gaadi mat roko (wo chhup jaati hai), ya `front` lagao.
- **Apni image se background:** 9:16 (1080x1920) image `assets/backgrounds/gali.png` me daalo, phir script me `SCENE: gali | title` (ya poora path `SCENE: assets/backgrounds/gali.jpg`). Character neeche ki taraf (zameen/sadak ~ neeche ke 35%) khade hote hain, to image me wahan khaali jagah rakho. Image main bana nahi sakta: kisi AI image tool se banwao ya free-licence image lo (flat cartoon style character ke saath mel khaati hai).
- **Naye props/looks:** prop `bag`, accessory `sunglasses`, action `salute`.
- **Voice-over:** `NARRATOR: Ek din ki baat hai | एक दिन की बात है`. Koi character nahi dikhta, bas awaaz aur neeche subtitle. CAST me likhna nahi padta.
- **"Expectation vs Reality" / comparison:** do `SCENE:` likho, title card me `Expectation 😎` aur `Reality 😭`, beech me `TRANSITION: whip`. Alag split-screen abhi nahi hai.
- **Camera se baat karna (monologue):** ek hi character, ek ke baad ek lines. Auto camera use alag-alag close shots me kaat deta hai.

## Chat video (alag, chhota format)

Texting wale jokes ke liye. Story format se bilkul alag hai: koi character, voice ya CAST nahi. "Apni script" box me (ya `scripts/x.txt` me) bas ye likho:

```
HOOK: Mummy ka message 📱
CHAT: Mummy ❤️
< Beta khana kha liya?
> Haan mummy 😅
< Jhooth mat bol, ghar aa!
> Abhi aaya, 5 minute!
CTA: Tag karo 👇
```

- `<` = samne wala (left; message se pehle ~1 sec "typing..." ke teen dot aate hain, aur aane ki `ding` awaaz), `>` = aap (right, `pop` awaaz).
- Optional: `HOOK:`, `CTA:`, `CAPTION:`, `HASHTAGS:`, `MUSIC: beat 90`. 12 se zyada messages ho to purane upar se nikal jaate hain.
- Chat ko story ke andar mat milao: story script me `<` / `>` / `CHAT` lines ek warning ke saath ignore hoti hain.
- Awaaz nahi hoti, to Gemini ka quota kharch nahi hota.

## Characters

Ready looks: `boy, girl, college_boy, college_girl, uncle, aunty, dada, dadi, kid, kid_girl, office_guy, office_girl`. Har cheez badal sakte ho:

```json
"R": { "look": "uncle", "outfit": "kurta", "color": "saffron", "accessories": ["turban", "beard"], "build": "chubby" }
```

- `skin`: fair, wheatish, brown, dark · `hair`: short, side_part, spiky, curly, balding, bald, long, braid, bun, ponytail · `hair_color`: black, brown, grey, white, henna
- `outfit`: tshirt, shirt, kurta, salwar (dupatta ke saath), saree, uniform, blazer, vest · `color` / `accent` (dupatta, blouse, tie) / `pants` / `shoes` (black, white, chappal)
- `build`: slim, normal, chubby · `scale` (bachche ~0.72) · `accessories`: glasses, cap, turban, moustache, beard, bindi, tilak, earrings
- 17 expressions, 17 actions (walk, talk, dance, point, laugh, shock, jump, wave, clap, cry, fall, facepalm, shrug, sway, sleep...)
- **Desi dance pack** (music ki beat pe chalta hai, `MUSIC: beat 110`): `naagin` (haath maathe pe phan), `bhangra`, `aeroplane` (uncle special), `thumka`, `dance_walk` (chalte-chalte dance, `night_road` pe best), `kamar_dard` (hero dance… phir kamar jawab de deti hai), `sing` (mic apne aap haath me, mooh gaata hai). Example: `scripts/shaadi_dance.txt`.
- Asli gaana: video `MUSIC: none` se banao aur gaana Instagram ke andar "Add audio" se lagao (copyright safe, trending audio ki reach). Hindi voice gaa nahi sakti; gaane ke jokes ke liye `sing` + ek line + baaki logon ka "besura" reaction.

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

### Gemini voice (realistic) - poori script ek hi request me

Free Gemini key ka quota kam hota hai, isliye **poore video ki saari lines (saare scenes milake) ek hi API request me** bheji jaati hain, ek lambi audio aati hai, aur use lines ke beech ke pause pe kaat kar har line ka alag clip banta hai (lip-sync/timing waise hi chalte hain).

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

**Actions → Render video → Run workflow**: `instruction` (AI idea) + `hook` + `count`, ya `script` (scripts/*.txt), ya `scene`. Artifacts → `videos` me `.mp4`, preview `.png` aur `.post.txt` (caption + hashtags). `scenes/*.json` ya `scripts/*.txt` push karne par bhi apne aap render hota hai. AI ke liye secret `GEMINI_API_KEY` ya `ANTHROPIC_API_KEY` (Settings → Secrets → Actions). Voice engine: `tts` = `auto` (default: `GEMINI_API_KEY` hai to Gemini voice, warna edge-tts) / `gemini` / `edge`. Web page `tts` nahi bhejta, to wo `auto` pe chalta hai.

## GitHub Pages wala page (render GitHub pe)

`index.html` (repo root) GitHub Pages pe chalta hai: https://boidbit.github.io/insta-shorts/

1. Page pe "⚙️ GitHub connection" kholo → fine-grained token banao (sirf is repo ke liye, **Actions: Read and write**, **Contents: Read-only**) → paste → Save. Token sirf aapke browser me rehta hai.
2. **Idea tab** → idea likho → **Script likho ✍️**. AI sirf script likhta hai (~1 min, workflow `stage=script`, pre-release `draft-…`), video nahi.
3. Script **Apni script** tab me aa jati hai: padho, jo badalna ho badlo → **✅ Approve: Video banao 🎬** (`stage=video`, ~4-6 min). Apni likhi script bhi seedha yahin se approve kar sakte ho, ya "AI se sudharo" se pehle AI ka version dekh sakte ho.
4. Video GitHub **Release** (`reel-…`) me publish hoti hai; page wahi chalata hai, download + caption copy deta hai. Approve hua draft apne aap hat jata hai. "Pichli reels" me sab purani videos.

**Doosre AI (ChatGPT, Claude, Gemini app) se script:** koi code nahi chahiye, script sirf simple text hai. Page pe "🤖 … prompt copy karo" dabao → us AI me paste karo (aakhri line me apna idea) → jo script mile wo "📝 Apni script" me paste karo. Page turant check karta hai (brackets me dialogue, anjaan shabd, Devanagari missing, CAST me naam nahi…) aur galti ho to Approve se pehle batata hai. Prompt file: `SCRIPT_PROMPT.md`.

**AI key kahan daalni hai:** repo → Settings → Secrets and variables → Actions → **Repository secrets** → New repository secret → Name `GEMINI_API_KEY` (ya `ANTHROPIC_API_KEY`). `GOOGLE_API_KEY`, `GEMINI_KEY`, `AI_API_KEY` naam bhi chalte hain. *Environment* (`github-pages`), Codespaces ya Dependabot secrets workflow ko nahi dikhte.

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

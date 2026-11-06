# Stickman Studio

`scene.json` likho → GitHub Action `.mp4` bana deta hai (1080x1920 reel). Desi stickman format: Hindi voice + lip-sync, ~130 actions, 38 locations, objects (darwaza, TV, bed, gaadi...), janwar, effects, chat/notification UI, multi-scene kahaniyan with transitions, mood music aur sound effects.

Demo: `scenes/jungle_mystery_demo.json` (multi-scene kahani), `scenes/chai_tapri_demo.json`, `scenes/power_cut_demo.json`.

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

`studio/director.py` Claude se scene JSON banwata hai (`DIRECTOR_PROMPT.md` rules + code se bani poori vocabulary ke saath), `lint` ki har galti khud sudharwata hai, aur phir render ho jata hai. Lambi script (kuch minute) do to multi-scene file banti hai. Local me: `python -m studio.director "idea ya poori script" -o scenes/generated/x.json`.

## Kya-kya bana sakte ho (reference)

Poora schema + har naam ki list `DIRECTOR_PROMPT.md` aur `python -m studio.lint` se milti hai. **Galat naam (typo) silently ignore nahi hota**: render ke time `[warn]` dikhta hai, aur `python -m studio.lint scenes/x.json` se pehle hi check kar sakte ho.

### Characters

```json
"characters": {
  "A": { "preset": "aunty" },
  "B": { "preset": "boy", "hair": "curly", "skin": "brown", "outfit": ["tie"], "accessories": ["glasses"] },
  "D": { "kind": "dog", "x": 800 }
}
```

- **preset**: boy, girl, woman, aunty, kid, elder, uncle, teacher, police, doctor (look + voice ready; jo likhoge wo override hoga)
- **hair**: short, side_part, spiky, curly, bun, ponytail, long, bald, bald_sides (+ `hair_color`); **skin**: light, fair, wheat, tan, brown, dark; **body**: slim, belly; `barefoot`
- **outfit**: saree, dupatta, skirt, tie, stethoscope; **accessories**: glasses, cap, tuft, moustache, beard, bindi, turban, topi, police_cap, bow, earrings, headband
- **janwar** (`kind`): dog, cat, cow, crow, parrot (actions: walk/run, sit, sleep, jump, bark/meow/moo/caw, wag, eat, fly, peck); `monkey` insaan wale saare actions karta hai
- `"visible": false/true` timeline me = character gayab / wapas (darwaze se aana-jaana)

### Actions (~130)

Har action right-facing likha hai aur khud mirror hota hai; character `look` (dusra character) ya `facing` ki taraf karta hai. Chalte waqt apne aap chalne ki disha me mudta hai; `"move": {"x": 900, "run": true}` = daud.

- **chalna**: walk, run, jog, sneak/tiptoe, limp, crouch, hide, peek, climb, jump_over, slide, skid, moonwalk, cartwheel, spin, turn_around (peeth)
- **baithna/letna**: sit (`"on": "chair1"` se kursi/sofa/bench par), sit_floor, lie_down, sleep_lie, get_up, wake_up, faint, slip, trip, fall, rofl
- **reaction**: nod, shake_head, look_back, look_around, look_up/down, scratch_head, yawn, sneeze, scared, shiver, stomp, celebrate, fist_pump, sulk, arms_crossed, cringe, proud, hands_on_hips, think, listen, shh, thumbs_up, salute, namaste, bow, rub_hands, flex, stretch, whisper, shy, dizzy, hit_react, facepalm, shrug, cry, laugh, shock
- **roz ka kaam**: eat, drink, phone_call, text, read, write, count_money, wash_hands, sweep, cook, brush_teeth, drive, ride
- **do logon wale**: throw (`"at": "B"` → cheez udti hai, B ko lagti hai), catch, kick, slap, punch, box, push, dodge, high_five, handshake, hug, pat_back, carry, drag, tug, argue
- **khel/dance**: bat, bowl, race_start, jumping_jacks, squat, pushup, lift_weights, bhangra, garba, hookstep, floss, thumka, nagin, dance (+ purane)
- **expressions** (~38): neutral, smile, grin, laugh, lol, sad, cry, angry, shock, scared, nervous, cringe, confused, think, sly, evil, proud, shy, blush, love, kiss, dizzy, sleepy, yawn, bored, hurt, excited...
- **haath me props** (~37): chai, cup, plate, samosa, chappal, phone, book, laptop, umbrella, broom, belan, money, newspaper, bag, gift, balloon, trophy, torch, bat, dumbbell, box...
- Baithe-baithe kuch karna: action ke saath `"on": "bench1"` do (jaise `"action": "drink", "on": "bench1"`) to pair baithe hi rehte hain.

### Jagah (locations) + samay

`"background": {"type": "chai_tapri", "time": "night"}` — `time`: day, night, evening, sunset, dawn, rain (rain me baarish khud aati hai)

kitchen, room, street, school, night_road, chai_tapri, gully, kirana, market, bus_stop, railway, terrace, balcony, bedroom, bathroom, canteen, hostel, office, meeting_room, exam_hall, library, coaching, mandap, party, festival_street, cricket_ground, gym, jungle, haunted_house, graveyard, beach, mountain_road, desert, hospital, police_station, cinema, bank, plain, ya apni `image`

### Objects (cheezein) + unki state

```json
"objects": [ { "id": "door1", "type": "door", "x": 880, "y": 1700 }, { "id": "c1", "type": "chair", "x": 300 } ],
"timeline": [ { "t": 2, "object": "door1", "state": "open" }, { "t": 3, "who": "A", "action": "sit", "on": "c1" },
              { "t": 5, "lights": "off" } ]
```

door, window, clock, painting, tubelight, fan, tv, fridge, cupboard, bed, chair, stool, table, desk, sofa, bench, stairs, tree, bush, rock, fence, dustbin, signboard (`text`), lamp, phone, plant, box, bucket.
States: door open/closed, tv/lamp/fan/tubelight on/off, fridge/cupboard open, phone ringing, bush rustle, window night. `"lights": "off"` = bijli gayi (kamra andhera, lamp/TV chamakte rehte hain).

### Gaadiyan

cycle, bike, auto, car, bus, train — `{"object": "car1", "move": {"x": 900, "dur": 3}}` se chalti hain (pahiye ghoomte hain), `{"who": "A", "ride": "car1", "seat": "driver|passenger|back"}` se baitho, `"ride": ""` se utro.

### Effects (`"fx"`)

`{ "t": 2, "who": "A", "fx": "sweat" }` ya `{"fx": {"type": "glow_eyes", "pos": [800, 1300], "dur": 3}}`

- character par: sweat, anger, sparkle, dizzy, question, exclaim, zzz, hearts, bulb, tears_spray, dust, speed, steam, thought
- jagah par: pow (`"text": "DHISHOOM!"`), glow_eyes, fire, smoke
- poori screen: rain, snow, fog, fireflies, leaves, confetti, lightning, flash, spotlight, focus_lines
- `"say": "...", "bubble": "thought"` = soch wala cloud bubble

### Screen UI (`overlays` me `type`)

chat (messages apne time pe aate hain + typing...), notification, loading (`"stuck": true` = 99% pe atak), counter, timecard ("3 ghante baad..."), chapter, endcard ("Follow for more").

### Lambi kahani: multi-scene

```json
{ "transition": {"type": "fade"}, "music": {...},
  "scenes": [ {scene 1}, {"transition": "wipe", ...scene 2...}, {"split": [{upar}, {neeche}]} ],
  "overlays": [ {"type": "endcard", "from": 20} ] }
```

Har scene ki apni jagah/characters/timeline. Transitions: cut, fade, dip, wipe, wipe_left, slide, whip, zoom, iris. `split` = do scene upar-neeche (phone call). `{"file": "scenes/x.json"}` se purani scene file bhi jod sakte ho.

### Camera + time

- `{"camera": {"punch": "B", "back": 0.8}}` = chehre pe jhatke se zoom; `{"camera": {"reveal": "A", "from": 2.2}}` = paas se peeche
- `{"slowmo": {"rate": 0.3, "dur": 1}}` slow motion; `{"freeze": {"dur": 1, "style": "grey"}}` freeze frame (+ `"sfx": "record_scratch"`)

### Awaaz

- **sfx**: pop, boing, whoosh, ding, thud, clap, beep, laugh_track, slap, punch, knock, doorbell, ring, vibrate, horn, footsteps, scream, heartbeat, record_scratch, sad_trombone, rooster, thunder, wind, crowd_cheer, bat_hit, crickets, drumroll, cash, whistle, tick, applause (ya apni file ka path)
- **music**: `{"type": "beat", "style": "comedy", "seed": 4}` — style: desi, soft, pop, comedy, suspense, sad, festive, lofi; `seed` badlo to dhun badalti hai
- **ambience**: `"ambience": "rain"` — rain, street, office, night, jungle, crowd, wind, sea

## Apna asset daalna

- Background: PNG/JPG `assets/backgrounds/` me rakho → `"background": {"type": "image", "path": "assets/backgrounds/mera.png"}` (9:16 best).
- Music: `"music": {"path": "assets/music/gaana.mp3", "volume": 0.4}` (generated beat bina copyright wala hai; kisi gaane ka use apni zimmedari pe).
- Font: `assets/fonts/main.ttf` rakho to caption/bubble usi me banenge (Devanagari ke liye `assets/fonts/devanagari.ttf`).

## Limits (sach me)

- Characters code se bane flat stickmen hain; AI-generated art jaisi detail nahi hogi. Naye look ke liye `studio/characters.py` / `studio/locations.py` badlo ya apni PNG backgrounds do.
- Har action ek "pose" hai; do actions ek saath nahi (exception: baithe-baithe upper-body action `"on"` ke saath). Script me jo action list me nahi hai, uska sabse paas wala use karo (AI director yahi karta hai).
- Bade sar wale stickmen ke saath gaadiyan thodi "cartoon" size ki hain; bus/train frame se badi hain.
- Synthesized sounds (scream, rooster, crowd) cartoon jaise hain; asli awaaz chahiye to apni file ka path do.
- Bubble ke andar emoji ke liye `fonts-noto-color-emoji` chahiye (workflow khud install karta hai).
- Hindi voice `edge-tts` (Microsoft online service) se aati hai, isliye internet chahiye; bina internet ke `--no-tts`.

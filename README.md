# Desi Toons Studio

Idea ya script do → 1080x1920 Instagram reel ban jati hai: Indian cartoon log (kurta, saree, uncle, aunty, dadi...), Hindi awaaz + lip-sync, pehle second me hook, ek video me kai jagah (ghar → sadak → ghar), beat music, aur Instagram caption + hashtags.

## Sabse aasaan: webpage

GitHub Pages wala studio page (mobile pe bhi):
- **📝 Apni script** pehla tab hai aur box khali milta hai. Format yaad na ho to "📄 Example script daalo" dabao.
- **💡 Idea do (AI)** doosra tab hai.
- GitHub token upar kone me chhote **GitHub** button me hai (sirf zarurat pe khulta hai).
- Video options ek grid me hain: Quality, Dialogue text, Hook card, Loop, Mascot, Awaaz (Gemini default), Rang, CTA, Handle, Hindi awaaz.

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

## 2 style: 2D (normal) aur 2.5D ✨

Har video ke liye style chuno: GitHub Pages wale page pe sabse upar **Style: 2D / 2.5D** (page yaad rakhta hai), local page (`python -m studio.web`) me **Style** dropdown.

| Style | Kya hota hai |
|---|---|
| **2D** (default) | Studio ka normal look, bilkul pehle jaisa (koi farq nahi: `tests/golden.py` har bar pixel-by-pixel check karta hai). |
| **2.5D** | Wahi log, wahi script, wahi saare shabd. **Har jagah gehrai ke saath** banti hai: aasmaan, door ki imaaratein / ped / pahad / samundar aur khidki ka nazara alag parat me (auto 2.5D: har jagah ki apni 2D drawing se). Camera zoom/shot badalne pe door ki cheezein dheere aur paas ki tez khiskti hain (parallax), door ka hissa halka blur, khidki aur jhalar chamakti hain, andar ki jagah me aage ek blur paudha. Logon pe us jagah ki roshni: ek taraf parchhai, doosri taraf halki chamak. **Premium sets** (haath se bane, sabse zyada gehrai): `kitchen` (din ki rasoi, khidki ke bahar ka nazara, jaali wali dhoop, cooker ki bhaap), `gully` / `chai_tapri` / `kirana` (golden-hour gali: kirana dukaan, bijli ka khamba + taar, chai tapri), `terrace` (Diwali ki raat ki chhat: jhalar, diye, patakhe), `room` / `living_room` (ghar ka kamra: sofa, TV ki jhilmil, ghoomta pankha, kaleen, dhoop me dhool), `school` / `classroom` (blackboard pe chalk se likha, teacher ki table + globe, bench, do pankhe, chalk ki dhool). Sirf apni photo, `plain` aur `night_road` flat rehti hain. |

- Script me: `HOOK:` ke baad `STYLE: 2.5d` likho (na likho = 2D). Page ka Style button aur script ki ye line saath-saath badalte hain.
- Time word bhi chalta hai: `SCENE: kitchen night` / `SCENE: gully rain` (set ka rang badalta hai, lights jalti rehti hain). `terrace` hamesha raat hai.
- Gali ke signboard pe likha hai, isliye reverse shot (CUT) me gali kabhi ulti (mirror) nahi hoti.
- Example: `scripts/25d/gali_udhaar.txt`, `scripts/25d/kitchen_mummy.txt`, `scripts/25d/diwali_terrace.txt`.
- Command line: `python -m studio.render scene.json --style 2.5d` (ya `2d`): script ki STYLE line se zyada chalta hai.

### 🎭 Builder: jagah aur characters chuno, dialogue saade text me

"Idea do" tab me upar **"Jagah aur characters khud chuno"** kholo:

- **Jagah** (kamra, rasoi, bazaar, office…) aur max 3 **characters**: naam, kaun (papa, mummy, dost… har ek ki chhoti photo), baal, rang, kapde, colour, body, extra (chashma, mooch, topi…). Na chuno to "auto". Ye choice browser me yaad rehti hai.
- Neeche box me **idea** likho → AI inhi characters aur jagah ke saath script likhta hai.
- Ya seedha **dialogue** likho, har line `Naam: baat`:
  ```
  Papa: Sarkari gaadi se aana!
  Beta: Ji papa ji!
  Papa (gussa): Aur time pe aana.
  ```
  Button "📝 Script banao (bina AI)" ban jata hai: page khud poori script banata hai (HOOK, CAST, SCENE, shots, CTA, caption) aur "Apni script" tab me dikhata hai → padho → Approve.
- Emotion: box ke neeche chips (😠 gussa, 😲 hairan, 😏 akad, 😂 hasi…) jis line pe cursor hai usme jud jaate hain. Na do to `?!` = hairan, 😂 = hasi apne aap.
- Shots: khali line = naya shot. Na do to har baar bolne wala badalne pe CUT, aur do logon ki baat me zyada tar `CUT ots` (face-off).
- **Devanagari likhne ki zarurat nahi:** video banate waqt workflow saari Roman lines ek hi AI request me Devanagari me badal deta hai (`GEMINI_API_KEY`), taaki Hindi awaaz sahi padhe. Bubble me aapka Roman text hi dikhta hai. Key na ho to awaaz Roman padhegi.

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

#### 🎵 Apni lyrics se poora gaana (Gemini, `MUSIC: gemini`)

Lyrics likho, Gemini (Lyria) **music + gaane wali awaaz** ke saath gaana bana deta hai, wahi `GEMINI_API_KEY` se jo voice ke liye lagi hai.

```
HOOK: Mummy ka gussa 🎤
MUSIC: gemini funny bollywood item song, dhol, male and female vocals
[Verse]
Mummy naraaz hui, maine kaha kal karunga | मम्मी नाराज़ हुई, मैंने कहा कल करूँगा
Kal kal karte karte, sink bhar gaya beta | कल कल करते करते, सिंक भर गया बेटा
[Chorus]
Mummy naraaz hui re, ab main bhaaga re | मम्मी नाराज़ हुई रे, अब मैं भागा रे
```

- `MUSIC: gemini <style ke shabd>` = 30 second ka gaana (`lyria-3-clip-preview`). `MUSIC: gemini full <style>` = poora lamba gaana (`lyria-3.5`, kuch minute; key ko is model ka access chahiye).
- **Gaaya wahi jaata hai jo `|` ke baad Devanagari me likha hai** (na likho to Roman wali line). Screen pe Roman wali line dikhti hai. `[Verse]`, `[Chorus]`, `[Bridge]` wali line gaane ko structure deti hai, screen pe nahi dikhti.
- Video **gaane jitni lambi** ho jaati hai aur lyrics uspe barabar failti hain (`SECONDS` kaam nahi karta). Gemini line-wise time nahi batata, isliye lyrics ka sync andaaza hai: kabhi ek-do second aage-peeche ho sakta hai.
- **Kahani wali script** (`CAST` / `SCENE`) me `MUSIC: gemini lofi` sirf background music (bina awaaz) banata hai.
- **Kuch na ban paye** (free plan me access nahi, quota khatam, key nahi, network) **to studio ka apna beat lag jata hai aur video phir bhi banti hai.** Log me `[music] Gemini could not make the song (...)` likha aata hai, wahi wajah hai.
- Wahi lyrics + style dobara ho to gaana cache se aata hai (API dobara nahi lagti). Har gaane me Google ka SynthID watermark hota hai (sunai nahi deta). Free key me ye chalega ya nahi, Google ne docs me nahi likha: pehli baar chalake dekho.

## Camera, objects aur naye formats

- **Camera apne aap (naya "cine" direction):** har bolne wali line par speaker pe cut-in + halka push-in, punchline pe sabse tight shot + shake. Uske upar ab:
  - **Camera saath chalta hai:** jis par camera hai wo chale, bhaage ya paas/door jaye to camera uske saath khiskta hai. Koi lamba chale / andar aaye / bahar jaye (aur koi bol na raha ho) to camera usi ke saath ho jata hai.
  - **Kabhi poora rukta nahi:** ruke hue shot me bhi bahut halki saans jaisi harkat (zoom ~1%, kuch pixel).
  - **Reaction shot:** shot ki aakhri line ke baad camera wide pe nahi jata; **sunne wale ke chehre** pe jata hai (ya uspe jo line ke baad action karta hai, jaise `B -> facepalm`). Script ne sunne wale ko koi reaction nahi diya to chehra khud badalta hai (gusse wali line → ghabraya, mazaak → bore...). Band: `"meta": {"auto_react": false}`. Koi chala gaya (exit) to camera jo bacha uspe. Aakhri "Tag karo" card ke saath chehra card ke neeche rehta hai.
  - **Tez behas ek frame me:** 3+ chhoti lines baari-baari (har ek ~2 sec tak) → dono ek two-shot me, har line pe cut nahi. Punchline phir bhi tight.
  - **Halka tedha frame:** `angry`, `shout`, `evil`, `scared` wali line pe frame 3.5° jhukta hai.
  - **Whip:** ek se doosre pe jaate waqt tasveer me halka dhundhla streak.
  - **Frame se bahar nahi:** koi behosh ho / gire / zameen pe lete (`faint`, `fall`, `slip`, `trip`, `lie_down`...) to camera wide hoke dekhta hai aur gira hua shareer frame ke andar khisak jaata hai. Bed (ya sofa) pe leta insaan uthte hi (`get_up` ya koi bhi agla action) frame ke andar sabse paas ki khaali jagah pe aa jaata hai.
  - **"Tag karo" card chehre pe nahi:** aakhri card ab upar (chehron ke upar) aata hai; card ke saath close shot thoda dheela, chehra card ke neeche.
  - **Purana camera chahiye?** Script me `CAMERA: classic` (JSON: `"meta": {"camera": "classic"}`): camera bilkul pehle jaisa. Golden guard isi mode me live code se pixel-by-pixel milata hai.
  Band karna ho: JSON me `"meta": {"auto_camera": false}`. Apni marzi: line ke brackets me `wide`, `medium`, `close`, `two_shot` (jaise `A (shock, close): ...` ya `ALL -> wide`).
- **Lambi lines:** AI writer ko chhoti lines likhne ko kaha jaata hai (zyada tar 60 akshar tak, sab milake ~350). AI fir bhi bahut lambi likhe to use **ek baar** chhota karne ko kaha jaata hai; lambai ki wajah se video kabhi fail nahi hoti.
- **Entry / exit ke naye tareeke** (kinare se chal ke aana ab bhi hai: `A -> enter left`):
  - `A -> enter back` = jagah ke peeche se camera ki taraf aata hai (chhota → bada). `enter back left|right` = kis taraf se.
  - `A -> enter pop` = neeche se uchhal ke frame me (boing).
  - `A -> enter left fast` / `enter right fast` = tezi se aake fisal ke rukta hai (dhool + whoosh).
  - `A -> enter left peek` / `enter right peek` = kinare se jhaankta hai, phir andar aata hai.
  - `A -> exit left fast` / `exit right fast` = palak jhapakte bhaag jata hai.
  - Sabse achha: **video shuru hote hi sab apni jagah pe hon** (pehla second hook ka hai), aur naya banda `CUT` ke baad seedha maujood ho. AI writer ka prompt ab yahi sikhata hai.
- **Depth:** `B -> near` (character camera ki taraf aata hai, bada), `far` (peeche, chhota), `mid` (normal). `near` ke saath `close` mat milao: shot bahut tight ho jaata hai.
- **Objects:** `OBJ: truck enter left to right` (gaadi aati hai aur right pe ruk jaati hai), `OBJ: dustbin left`, `OBJ: truck exit right`. Objects: truck (kachra gaadi), auto, car, scooter, cow, dustbin, bags, table; rang (`OBJ: car red ...`), `front` (characters ke aage), `big`/`small`. Apni PNG: `OBJ: assets/objects/x.png right`. Gaadi ke aane tak kahani ruki rehti hai. Jahan character khade hain wahan gaadi mat roko (wo chhup jaati hai), ya `front` lagao.
- **Apni image se background:** 9:16 (1080x1920) image `assets/backgrounds/gali.png` me daalo, phir script me `SCENE: gali | title` (ya poora path `SCENE: assets/backgrounds/gali.jpg`). Character neeche ki taraf (zameen/sadak ~ neeche ke 35%) khade hote hain, to image me wahan khaali jagah rakho. Image main bana nahi sakta: kisi AI image tool se banwao ya free-licence image lo (flat cartoon style character ke saath mel khaati hai).
- **Gaadi chalana / chadhna-utarna (rides):** `A -> ride bike` (bike, scooter, cycle, auto, car, truck; `B -> ride auto back` = doosri seat) character gaadi par hop karke baithta hai, `A -> getoff` (ya `getoff left|right`) se utarta hai. Gaadi chalane ke liye `OBJ: bike go right` (ya `enter left to center`), rider saath chalta hai; cycle me pedal ghoomte hain, mudne par rider mirror hota hai. Cycle/bike/scooter/auto me poora rider dikhta hai, car/truck me khidki me sirf sar dikhta hai (truck ka design wahi hai, khidki thodi badi). Rider ke haath handle tak pahunchne ke liye thode lambe hote hain. Jis gaadi par koi baitha ho wo sabke aage aati hai. Gaadi ka size character se hi nikalta hai (ek scale), isliye truck jaisi badi gaadi ke saath wala shot `CUT wide` hota hai (log chhote) ya `CUT inside` (cab bada). Example:
  ```
  A -> ride truck enter left to center     (gaadi bahar se aati hai, A pehle se andar)
  A (smug, close): Le aaya sarkari gaadi! | ले आया सरकारी गाड़ी!
  A -> getoff                                (utarta hai)
  OBJ: truck exit right                      (khaali gaadi chali jaati hai)
  ```
  Pehle se khade vehicle par chadhna ho to `OBJ: bike left`, phir `A -> ride bike` (hop karke baithta hai).
- **Naye props/looks:** prop `bag`, accessory `sunglasses`, action `salute`.
- **Voice-over:** `NARRATOR: Ek din ki baat hai | एक दिन की बात है`. Koi character nahi dikhta, bas awaaz aur neeche subtitle. CAST me likhna nahi padta.
- **"Expectation vs Reality" / comparison:** do `SCENE:` likho, title card me `Expectation 😎` aur `Reality 😭`, beech me `TRANSITION: whip`. Alag split-screen abhi nahi hai.
- **Camera se baat karna (monologue):** ek hi character, ek ke baad ek lines. Auto camera use alag-alag close shots me kaat deta hai.

## Aur shabd: jagah, set, jaanwar, screen cards, sound, slow-motion

Ye sab script me seedhe chalte hain (page ka checker bhi inhe jaanta hai), aur AI writer (`SCRIPT_PROMPT.md`) ko bhi ye sab shabd pata hain. Ek test (`tests/test_prompt_words.py`) dhyan rakhta hai ki prompt me koi aisa shabd na ho jo studio na samjhe.

- **Zyada acting:** ~140 actions (`run, sit, lie_down, eat, drink, phone_call, slap, hug, high_five, pushup, garba, hookstep, moonwalk...`), 38 expressions (`scared, nervous, cringe, confused, proud, dizzy, evil, blush...`) aur ~37 cheezein haath me (`chai, samosa, laptop, umbrella, chappal, belan, book...`). Poori list page ke word list me hai (`python -m studio.script --sync-page` usse code se banata hai).
- **Bolte waqt haath feeling ke hisaab se:** gussa = ungli dikhana, khushi = khule haath, dukh = chhote neeche haath, dar = seene pe haath, smug = kamar pe haath, soch = thodi pe haath. Sunne wale bolne wale ko dekhte hain, sir hilate hain, gusse se peeche hat-te hain, sawaal pe sir tedha karte hain. Ek pose doosre me smooth badalta hai, aankhen random time pe jhapakti hain.
- **Jagah + waqt + mausam:** 40 jagah (`bedroom, bathroom, balcony, terrace, classroom, exam_hall, hospital, bank, police_station, railway, jungle, beach, graveyard, haunted_house, mandap, gym, kirana, chai_tapri...`), phir waqt `day, night, evening, sunset, dawn, rain` aur mausam `fog, snow, fireflies, leaves`: `SCENE: jungle night fog`. Baarish wali jagah pe baarish ki awaaz apne aap.
- **Set (cheezein jo jagah me rehti hain):** `OBJ: sofa left`, `OBJ: door right`, `OBJ: tv right on`, `OBJ: signboard center CHAI POINT`. Kahani ke beech: `OBJ: door open`, `OBJ: tv off`, `OBJ: fan on`. Baithna/letna: `A -> sit sofa`, `A -> lie_down bed`. CUT ke baad set waisa hi rehta hai. 28 cheezein: bed, bench, box, bucket, bush, chair, clock, cupboard, desk, door, fan, fence, fridge, lamp, painting, phone, plant, rock, signboard, sofa, stairs, stool, tree, tubelight, tv, window...
- **Nayi set cheezein:** `khaat` (charpai: `A -> sit khaat`, `A -> lie_down khaat`), `matka`, `chulha` (aag jalti hai; `OBJ: chulha off`), `blackboard` (stand wala board: `OBJ: blackboard center चमगादड़` us pe likh deta hai; signboard pe bhi Hindi ab sahi dikhti hai), `drip` (glucose stand), `wheelchair` (`A -> sit wheelchair`), `cooler`, `washing_machine` (`OBJ: washing_machine on` ghoomti hai), `mirror`.
- **Nayi jagahein:** `jail` (lockup ke andar: salakhon wali khidki, kaidi ka chabutra, salakhon wala darwaza), `gaon` (gaon ka aangan: kachcha ghar, neem + chabutra, hand pump, khet), `school_ground` (school ka maidaan). 2D aur 2.5D dono me.
- **Naye props:** `cooker`, `thali`, `lota`, `tiffin`, `mithai`, `report_card`, `injection`, `stethoscope` (jaise `A (proud, report_card): ...`).
- **Batti:** `LIGHTS: off` (kamra andhera, lamp/TV chamakte rehte hain), `LIGHTS: dim`, `LIGHTS: on`. Agle CUT me bhi waisa hi.
- **Effects (line ke brackets me):** `sweat, question, exclaim, bulb, anger, hearts, dizzy, zzz, sparkle, steam, smoke, fire, lightning, confetti, tears_spray, pow, spotlight, glow_eyes...`: `A (scared, sweat): ...`
- **Phenkna:** `A -> throw B` = chappal udti hai, THAK!, camera dono ko dikhata hai, agli line hit ke baad.
- **Jaanwar:** `CAST: B = kutta brown` (billi, gaay, kauwa, tota, bandar bhi; English me dog, cat, cow, crow, parrot, monkey). Bolte bhi hain. Acting: `bark, meow, moo, caw, wag, fly, peck, sit, eat, jump`.
- **Screen cards (apni line pe):** `NOTIFY: Bank | Salary credited | Balance: Rs 12` (phone notification upar se aata hai), `LOADING: Dimaag loading...`, `COUNTER: Balance | 50000 | 12`, `TIMECARD: 3 ghante baad...`, `CHAPTER: Chapter 2 | Exam ka din`, `ENDCARD: Follow karo | @page`.
- **Music ka mood:** `MUSIC: sad`, `MUSIC: suspense 90`, `festive, lofi, comedy, pop, soft, desi` (har video ki dhun alag). `MUSIC: beat 110` aur `MUSIC: none` pehle jaise.
- **Aas-paas ki awaaz:** `AMBIENCE: rain` (`street, office, night, jungle, crowd, wind, sea`).
- **Naye sound:** `slap, punch, knock, doorbell, ring, vibrate, horn, footsteps, scream, heartbeat, record_scratch, sad_trombone, rooster, thunder, wind, crowd_cheer, bat_hit, crickets, drumroll, cash, whistle, tick, applause`.
- **Aur sound (code se bane, copyright-free):** `cooker` (cooker ki seeti), `siren` (ambulance/police), `train_horn`, `dhol`, `shehnai`, `baby_cry`, `glass_break`.
- **Slow-motion / freeze:** `A -> fall slowmo thud` (agla 1 second 0.4x speed me, camera peeche hat-ta hai). `A -> freeze` (tasveer grey me ruk jaati hai + record scratch); turant baad wali `NARRATOR:` line ruki hui tasveer pe bolti hai ("Haan, ye main hoon").
- **Camera:** `(zoom)` = us chehre pe jhatke se zoom aur wapas, `(reveal)` = close se shuru, peeche hat ke poori jagah.
- **Beech me kaatna:** `B (interrupt, angry): ...` = B, A ki baat poori hone se pehle bolta hai; A ki awaaz wahin ruk jaati hai.
- **Awaaz tight:** har line ke aage-peeche ki khamoshi kat jaati hai; edge-tts me gusse wali line thodi tez, dukhi wali dheemi aur neechi.

## Video options (page / command line)

Page pe "Approve: Video banao" ke upar ye options hain (page yaad rakhta hai):

| Option | Kya karta hai | Command line |
|---|---|---|
| Dialogue text | `Bubble me` (pehle jaisa), `Neeche subtitle` (bubble nahi, shabd neeche, Instagram caption se upar), `Bubble + subtitle`, `Koi text nahi` (sirf awaaz) | `--dialogue bubble/subtitle/both/none` |
| Hook card | `Pehli line ke saath` (pehle jaisa), `Pehle hook, phir baat` (hook card 1.7s akela, phir kahani), `Hook card nahi` | `--hook over/first/off` |

GitHub Actions me ye `dialogue` aur `intro` inputs hain. Style ka input `style`: `auto` (script ki `STYLE:` line, warna 2D) / `2d` / `2.5d`; page apna chuna hua style bhejta hai.

### Loop 🔁 aur Mascot 👻 (watch time ke liye)

| Option | Kya karta hai | Script line | Command line |
|---|---|---|---|
| Loop | Video ka end ek whip ke saath seedha pehle frame me ghus jaata hai (aakhri frame = pehla frame), music bhi wahin dheema hota hai. Instagram reel dobara chalaye to jod pata nahi chalta, log 2 baar dekhte hain. CTA ka end card nahi aata (end card "the end" bolta hai); CTA ka text caption me chala jaata hai. | `LOOP: on` | `--loop` |
| Mascot | Ek chhota mascot (chhotu bhoot 👻 / billi 🐱 / chooha 🐭) kahani ke beech ki ek line pe bolne wale ke peeche se jhaankta hai, aankh jhapakata hai, wapas chhup jaata hai. Pehli line aur punch line pe kabhi nahi. Loop ke saath aakhri second me ek baar aur ("bhai end me kya tha?"). Har video me alag jagah, wahi video dobara banao to wahi jagah. | `MASCOT: bhoot` (billi, chooha, off) | `--mascot bhoot` |

Page pe ye dono video options me hain. Approve karne pe page `LOOP: on` / `MASCOT: ...` line script ke saath bhej deta hai; script me apni line ho to wahi chalti hai. JSON me: `"loop": true`, `"mascot": "billi"`.

### Har video alag dikhe 🎨 (rang, pehla shot, cover, handle)

Instagram grid me saari reels ek jaisi na lagein, isliye har video ka apna look hota hai:

| Cheez | Kya hota hai | Page option | Script line |
|---|---|---|---|
| Rang (colour mood) | Hook card aur CTA ka rang, poori tasveer pe halki colour grading (sunehri, thandi neeli, gulabi, teal-orange, punchy, lime, classic peela), aur jagah ki deewaron/imaaraton ke rang thode alag (aasmaan neela hi rehta hai). **Auto** = har video ka apna rang, kahani (hook) se chuna hua; wahi video dobara = wahi rang. | Rang 🎨 | `COLOR: golden` (classic, golden, cool, rose, teal_orange, punchy, lime; gulabi, neela, peela... bhi) |
| Pehla shot | Har video alag tarah khulti hai: kabhi seedha, kabhi bolne wale ke chehre se shuru hoke peeche khinchta camera (reveal), kabhi close-up. Jaldi-jaldi wali baat-cheet pe nahi lagta. | (apne aap) | (pehli line pe `close` / `reveal` likho to wahi) |
| Cover | Har video ke saath ek **cover picture**: punch line pe bolne wale ka bada chehra, upar bade shabd (hook, ya `COVER:` line), hook ka emoji sticker ki tarah, mascot, aapka handle aur video ke rang ka border. Sab kuch beech ke 3:4 hisse me (profile grid wahi dikhata hai). Page pe "🖼️ Cover download"; Instagram pe upload karte waqt **Edit cover → Add from camera roll**. Pichli reels ki gallery bhi ab cover dikhati hai. | (apne aap) | `COVER: BAS 5 MINUTE 😭` |
| Handle | Aapka `@page` video ke baayein kinare pe halka sa, khada (watermark). | Handle 🏷️ | `HANDLE: @desitoons` |

`CAMERA: classic` me sab pehle jaisa (koi rang/pehla shot nahi). Command line: `--color golden`, `--cover` (cover PNG banata hai).

### CTA: end card, sticker ya sirf caption 📣

CTA ab zaruri nahi: `CTA:` line na likho to video punch line ke baad khatam. Likho to page pe **CTA 📣** se chuno kaise dikhe:
- **End card** (pehle jaisa, ~2 s)
- **Sticker**: punch line ke saath chhota sa upar, video lambi nahi hoti
- **Sirf caption**: video me nahi, post ke caption me

Script me `CTA_STYLE: sticker` (card / sticker / caption), command line `--cta sticker`. Loop on ho to end card kabhi nahi aata.

### Chhota prompt (ChatGPT / Gemini app ke liye)

"📋 prompt copy" ab sirf wahi copy karta hai jo aapke idea ko chahiye. Hamesha jaata hai: format, shabd aur likhne ke niyam (~12.7k akshar, pehle ~24k). Baaki hisse tabhi judte hain jab idea me unke shabd hon:

| Hissa | Kab judta hai |
|---|---|
| Gaadi | gaadi, bike, auto, truck... |
| Dance / gaana | dance, shaadi, gaana, gym, cricket... |
| Ek take (pan) | bhaag, peecha, raste, jail, nikla... |
| Screen cards | notification, salary, bank, "baad"... |
| Camera tricks | slow, freeze, entry... |
| Kapde / chehra | baal, dadhi, mota, patla... |
| Dark comedy | Tone dark/satire/absurd, ya maut, EMI, bhoot... |
| Loop | Loop option on ho to |

"Poora prompt" tick karo to sab kuch jaata hai. Copy ke baad page batata hai ki prompt kitna lamba hai aur kya-kya juda. Studio ka apna AI writer (key ke saath) hamesha poora prompt use karta hai.

Prompt chhota rakhne ke liye ye kaam ab studio khud karta hai, prompt me nahi likhna padta:
- camera chalana;
- logon ke chehre, lambai aur wazan;
- style, dialogue text, hook card, loop, mascot (page ke options);
- aam shabd samajhna: `happy` → smile, `gussa`/`naraz` → angry, `worried` → nervous, `tired` → sleepy, `running`/`bhaag` → run, `baith` → sit, `naach` → dance... AI aise shabd likhe to bhi script chalti hai.

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

## Shots (CUT): sab ek hi frame me nahi

Ek film ki tarah likho: jab camera kisi aur par jaaye to `CUT` likho. Har shot me **sirf wahi characters** dikhte hain jo us shot me bolte ya kuch karte hain, aur cut seedha hota hai (fade/whip nahi).

```
SCENE: street
S (angry): Sun ladke! Sarkari gaadi se aana! | ...      <- baap pehle bolta hai (baap + beti ek frame me)
B (shock): Papa!? | ...
CUT
L (grin): Ji sasur ji! | ...                              <- ab sirf ladka
L -> exit left
CUT wide
S (smug): Dekhte hain... | ...                            <- wide: sab chhote, poori gaadi dikhti hai
L -> ride truck enter left to center
CUT inside
L -> ride truck                                           <- gaadi ke andar: driver bada, cab ke saath
L (smug): Le aaya sarkari gaadi! | ...
CUT
S (shock): Yeh kya hai?? | ...
```

- `CUT wide` / `CUT inside` / `CUT medium` (default). `SCENE: jagah | title | wide` se bhi framing de sakte ho. Gaadi wala shot apne aap wide hota hai.
- **Har CUT ek naya angle:** ek jagah ke andar har CUT par background alag hissa dikhata hai (paas se, ek side se, ya ulti taraf se = mirror), jaise camera ghooma ho. `CUT reverse` = jagah ko doosri taraf se dikhao.
- **`CUT ots` (over the shoulder):** sunne wale ki peeth (sir + kandhe) bade size me aage kone me, bolne wala camera ki taraf. Peeche kaun dikhe: `CUT ots B`; na likho to shot ka doosra character, ya pichhle shot me jo bola tha. Do `CUT ots` aage-peeche = face-off (side apne aap badalti hai).
- **Ek hi scale:** gaadi hamesha insaan ke anupaat me hoti hai (truck insaan se ~2 guna ooncha, car/auto lagbhag insaan jitni), aur rider khade character jitna hi bada hota hai. Wide shot me log chhote hote hain taaki poori gaadi frame me aaye; bade chehre ke liye `CUT inside` ya `CUT medium`.
- Shot ek doosre ka state yaad nahi rakhte: jis shot me ladka gaadi me dikhna hai usme `L -> ride truck` dobara likho.
- Auto camera sirf `medium` shots me zoom karta hai (wide aur inside "composed" shots hain).

## Characters

Ready looks: `boy, girl, college_boy, college_girl, uncle, aunty, dada, dadi, kid, kid_girl, office_guy, office_girl, pandit, police, doctor, chaiwala, madam, dulha, dulhan, gym_bro, neta, chor, nurse, saas, bahu, principal, sabziwala, nai` (roles bhi: `pujari`, `policewala`, `inspector`, `havaldar`, `daroga`, `groom`, `bride`...). Har cheez badal sakte ho:

- **`neta`**: safed kurta-pyjama, upar Nehru jacket (`kurta_jacket`) aur safed **Gandhi topi** (`topi`). Pehle `neta` likhne pe studio ise samajhta nahi tha aur `boy` bana deta tha; `cap` likhne pe cricket wali topi lagti thi. Roles: `netaji`, `mantri`, `sarpanch`, `mla`, `politician`.
- **`chor`** (dhaari wale kaidi kapde `stripes` + `beanie` topi; roles `kaidi`, `prisoner`, `thief`), **`nurse`** (`nurse_cap`), **`saas`** (`sasu`), **`bahu`** (`bhabhi`, `patni`, `biwi`), **`principal`** (`headmaster`), **`sabziwala`**, **`nai`** (`barber`, `hajjam`).
- Nayi extras: `topi` (Gandhi topi), `beanie`, `nurse_cap`, kapde `kurta_jacket`, `stripes`. `cap` = khel wali topi.

```json
"R": { "look": "uncle", "outfit": "kurta", "color": "saffron", "accessories": ["turban", "beard"], "build": "chubby" }
```

- `skin`: fair, wheatish, brown, dark · `hair`: short, side_part, spiky, curly, balding, bald, long, braid, bun, ponytail · `hair_color`: black, brown, grey, white, henna
- `outfit`: tshirt, shirt, kurta, salwar (dupatta ke saath), saree, uniform, blazer, vest · `color` / `accent` (dupatta, blouse, tie) / `pants` / `shoes` (black, white, chappal)
- **Chehra** (face): `face` oval, round, long, square · `eyes` dot, big, small · `nose` hook, button, long, big · `brows` normal, thick, thin. Script me CAST words: `round_face big_eyes button_nose thick_brows`. Na likho to studio har character ko apna alag chehra deta hai (pehla character classic chehra), aur ek jaise do characters (do `college_boy`) ko alag baal, rang (skin) aur shirt ka colour.
- **Lambai aur wazan**: sab ek jaise nahi lagte: studio har video me logon ko alag body deta hai (koi lamba-patla, koi nata-mota...). Khud chunna ho to CAST me `mota / moti` (chubby), `patla / patli` (slim), `lamba / lambi` (tall), `nata / nati` (short; `short` akela baal ka style hai). JSON: `"height": "tall" | "short"`, `"build"`. `CAMERA: classic` me sab pehle jaise.
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

### Lambi duniya: ek hi take me ek jagah se doosri jagah (`pan`) 🎥

Pehle naya SCENE = camera cut. Ab koi bhi character chalta / bhaagta hua agli jagah tak jaa sakta hai aur **camera bina cut ke saath chalta hai**: purani jagah side se nikal jaati hai, nayi andar aati hai, beech me deewar ka kona, aur character ke pair zameen pe tike rehte hain.

```
SCENE: room
M (angry): Raju, doodh le aa! | राजू, दूध ले आ!
R -> exit right            <- (exit right fast = bhaagta hai)
SCENE: street pan           <- R chalta hua sadak tak, ek hi shot me
S: Aao Raju, chai piyoge? | आओ राजू, चाय पियोगे?
R -> exit right fast
SCENE: jail pan             <- phir sadak se jail (koi bhi jagah, kitni bhi baar)
```

- Kaun jaata hai: pichhle scene ka aakhri `X -> exit left|right`; ya naam do: `SCENE: school pan A`.
- Nayi jagah ke log tab tak apni jagah khade rehte hain; unki baat chalne wale ke pahunchne ke baad shuru hoti hai. Scene ka title (`| Bazaar`) chalte waqt hi chhota card ban kar dikhta hai (beech me poori screen ka card nahi).
- JSON me: agle scene me `"pan": {"who": "R", "run": true}`.
- Demo: `scripts/demo/jail_se_ghar.txt` (chor jail ka darwaza todta hai, phir jail → sadak → ghar ek hi take me).

**Jail ka darwaza**: har `SCENE: jail` me salakhon wala darwaza (`jail_door`) apne aap hota hai: `C -> kick` phir `OBJ: jail_door broken` = dhadaam se girta hai (awaaz + camera jhatka); `OBJ: jail_door open` = khul jaata hai.

## Hook styles (pehla second)

`pattern_interrupt` (Ruko!), `pov`, `relatable` (Agar tum bhi...), `curiosity` (end tak dekho), `list` (3 types ke...), `question` (kaun sahi?), `cold_open` (jhagde ke beech se), `expectation` (expectation vs reality). AI ko style do ya `auto`. Director check karta hai ki hook t=0 pe screen pe hai aur pehle second me kuch ho raha hai, warna khud sudharwata hai.

## Tone: light, dark, satire, absurd (AI writer ke liye)

Page ke "Idea do (AI)" tab me **Tone** dropdown hai (ya idea me ek line `TONE: dark` likho, ya command line me `--tone dark`):

| Tone | Matlab |
|---|---|
| `auto` (default) | Idea dekh kar AI khud chunta hai (aur dark/ajeeb idea ko "light" nahi banata). Bina idea ke random mix. |
| `light` | Family/relatable, halka-phulka. |
| `dark` 💀 | Halat grim (maut, qarz, system, kismat), andaaz deadpan. Darkness implied: cut, awaaz, `dead` expression; kuch graphic nahi. |
| `satire` | Aisi ajeeb cheez jo sab pehchaante hain (daftar, bill, rules), kaalpanik log aur sansthan. |
| `absurd` | Ek namumkin cheez sach hai aur sab use normal maante hain. |
| `twist` | Meetha shuru, aakhir me tez twist. |

- Har tone ke saath AI ko ek chhota example (exact format me) milta hai, jisse style samajh aati hai.
- Length: default 5-8 lines / 15-30 sec (setup wali kahani 10 lines / 40 sec tak); line itni lambi jitni baat saaf samjhane ke liye chahiye (~100 characters tak). AI flow lambi script ko rokta nahi.
- **Kya chalta hai:** adult double-meaning / chhed-chhaad wale jokes (kuch explicit nahi, aur bachchon wale characters ke saath kabhi nahi), mashhoor logon ke public bayan / kaam par satire (jab saaf mazaak ho; jhoothe ilzaam sach bata ke nahi), maut, qarz, bhrasht daftar, bhoot, kismat. **Sirf do cheezein band:** kisi ko uske dharm, jaati, kshetra, gender, shareer ya disability ki wajah se mazaak banana; aur khud ko ya doosron ko nuksaan pahunchane ya jurm sikhane wali baat. Gemini/Claude aisi cheezein waise bhi mana kar dete hain, aur Instagram aise reel hata deta hai.

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

`--no-tts` = awaaz skip (testing). `--dialogue subtitle` / `--hook first` = upar wale video options.

### Awaaz kaun banaye: Gemini ya ElevenLabs 🎙️

Page pe video options me **Awaaz**: `Gemini (default)` (Gemini fail ho to free awaaz) · `ElevenLabs` · `Free (Edge)`. Page ise yaad rakhta hai. Command line: `--tts auto|gemini|elevenlabs|edge` (`auto` = Gemini key ho to Gemini; `gemini` = sirf Gemini, fail ho to render ruk jaata hai).

**ElevenLabs** (bahut natural Hindi, `eleven_multilingual_v2`):
- Key: repo → Settings → Secrets and variables → Actions → **Repository secret** `ELEVENLABS_API_KEY`. Ye naam bhi chalte hain: `ELEVEN_LAB_1` (is repo me yahi hai), `ELEVEN_LABS_API_KEY`, `ELEVENLABS_KEY`, `ELEVEN_API_KEY`, `ELEVENLABS`, `XI_API_KEY`.
- Har line ki alag request jaati hai. Har character ki apni awaaz hoti hai aur poori video me wahi rehti hai; do characters ki ek awaaz nahi hoti. Aurat/aadmi cast se pata chalta hai; bachche ki awaaz thodi patli kar di jaati hai.
- Aapke ElevenLabs account me koi Indian/Hindi voice judi ho (Voice Library se "Add"), to wo pehle try hoti hai. **Free plan** pe ElevenLabs API se Voice Library ki awaaz nahi chalne deta; tab studio apne aap ElevenLabs ki standard awaazein use karta hai (wo free plan pe bhi chalti hain). Warna seedhe standard awaazein lagti hain.
- Apni pasand ki voice: `ELEVENLABS_VOICES_MALE` / `ELEVENLABS_VOICES_FEMALE` (comma se voice ids, repo variables/secrets), ya JSON me `"voice": {"eleven": "<voice id>"}`. Model badalna: `ELEVENLABS_MODEL` (jaise `eleven_flash_v2_5`, sasta).
- Gusse / excitement wali line zyada expressive banti hai, udaas line dheemi aur naram.
- Har line cache hoti hai (`.cache/tts/eleven`), isliye dobara render ya preview frame me **credits kharch nahi** hote.
- ElevenLabs fail ho (galat key, credits khatam), to video phir bhi banti hai: Gemini key ho to Gemini ki awaaz, warna free awaaz. GitHub run me iski chetavni (warning) dikhti hai.

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

**Doosre AI (ChatGPT, Claude, Gemini app) se script:** koi code nahi chahiye, script sirf simple text hai. Page pe do button hain: **📋 2D prompt copy** aur **📋 2.5D prompt copy** → jo style chahiye uska prompt us AI me paste karo (aakhri line me apna idea) → jo script mile wo "📝 Apni script" me paste karo. Page turant check karta hai (brackets me dialogue, anjaan shabd, Devanagari missing, CAST me naam nahi…) aur galti ho to Approve se pehle batata hai. 2.5D prompt se bani script me `STYLE: 2.5d` line hoti hai, to paste karte hi page ka Style 2.5D ho jata hai. Prompt files: `SCRIPT_PROMPT.md` (2D) aur 2.5D = `SCRIPT_PROMPT.md` + `SCRIPT_PROMPT_25D.md` (sirf 2.5D wala hissa alag file me, taaki dono prompt kabhi alag-alag purane na pade). Page ke "Script likho" (AI) me bhi chuna hua style jata hai: workflow AI ko wahi prompt deta hai.

**AI key kahan daalni hai:** repo → Settings → Secrets and variables → Actions → **Repository secrets** → New repository secret → Name `GEMINI_API_KEY` (ya `ANTHROPIC_API_KEY`). `GOOGLE_API_KEY`, `GEMINI_KEY`, `AI_API_KEY` naam bhi chalte hain. *Environment* (`github-pages`), Codespaces ya Dependabot secrets workflow ko nahi dikhte.

Branch: page us branch pe workflow chalata hai jo settings me likha hai (default `desi-toons-studio`). Repo public hai to releases (videos) bhi public dikhte hain.

**2D na badle, iski guarantee:** workflow **Golden frames** har push / PR pe `desi-toons-studio` ka code aur naya code dono se 2D frames banata hai aur pixel-by-pixel milata hai (`python tests/golden.py compare-base --base <checkout>`). 2.5D ke frames `tests/golden/25d/` se milaye jaate hain (`python tests/golden.py check`).

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

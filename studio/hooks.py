"""Hook styles: how the first 2 seconds of a short grab the viewer.

The director gets one of these (or picks one when the style is "auto") and must
open the video with it. Topics feed the "auto idea" mode (no instruction given).
"""
import random
import re

HOOKS = {
    "pattern_interrupt": dict(
        name="Ruko! (pattern interrupt)",
        how="Open on a loud surprise at t=0: a character shocks/shouts, sfx 'boing' + camera shake. "
            "The hook text is a command or warning.",
        examples=["Ruko! Ye galti mat karna 😳", "Bas! Ab aur nahi 😤"],
    ),
    "pov": dict(
        name="POV",
        how="Hook text starts with 'POV:' and drops the viewer into a relatable moment. "
            "The first spoken line (t<=0.4) is already in the middle of the situation.",
        examples=["POV: Mummy ne 'ek minute' bola 😭", "POV: Result aane wala hai 😬"],
    ),
    "relatable": dict(
        name="Agar tum bhi...",
        how="Call out a habit the viewer has ('Agar tum bhi...'). End with a tag / comment call to action.",
        examples=["Agar tum bhi ye karte ho to tum pakke desi ho 😂", "Har ghar me ye hota hai 👀"],
    ),
    "curiosity": dict(
        name="Curiosity gap",
        how="Promise a payoff that only comes at the very end ('aakhri wala...', 'end tak dekho'). "
            "Keep the punch line for the last 2 seconds.",
        examples=["Aakhri wale ne to hadd kar di 😂", "End tak dekho, twist hai 👀"],
    ),
    "list": dict(
        name="Numbered types",
        how="'3 types ke ...': one character per type, a label on each head, one short line each.",
        examples=["3 types ke dost 😂", "Har shaadi ke 3 log 👀"],
    ),
    "question": dict(
        name="Sawal / poll",
        how="Ask a debate question at t=0, show both sides, ask viewers to vote in the comments.",
        examples=["Kaun sahi hai? 🤔", "Tum kis team me ho? 👇"],
    ),
    "cold_open": dict(
        name="Cold open (beech se shuru)",
        how="Start in the middle of a fight / drama: the first line is spoken at t<=0.3 and is already "
            "heated. The hook text repeats that shouted line.",
        examples=["'Doodh kahan hai?!' 😤", "'Phone kisne toda?!' 😱"],
    ),
    "expectation": dict(
        name="Expectation vs reality",
        how="Two scenes with transition 'whip': scene 1 titled 'Expectation' (everything perfect), "
            "scene 2 titled 'Reality' (disaster, same people).",
        examples=["Expectation vs Reality: Diwali ki safai 😭", "Gym ka pehla din: soch vs sach 😂"],
    ),
}

TOPICS = [
    "mummy aur ghar ke kaam", "papa aur bijli ka bill", "dost aur udhaar", "college exam ki raat",
    "shaadi me rishtedaar", "office ki Monday meeting", "traffic aur auto wala", "cricket match aur padosi",
    "chai aur gossip", "bhai-behen ki ladai", "online shopping aur delivery", "gym ka pehla din",
    "dadi aur naya smartphone", "hostel ka khana", "Diwali ki safai", "school ka homework",
    "WhatsApp family group", "barish me bahar jaana", "result ka din", "sabzi wale se mol-bhaav",
    "sarkari daftar aur line", "EMI aur maut ke baad ka loan", "bhoot jo ghar kiraye pe rehta hai",
    "kismat ka last minute twist", "shaadi ka kharcha aur qarz", "interview me jhoot ka ulta asar",
    "ghar ka wifi aur bhoot", "garib banda, ameer sapna", "sabse bura boss aur uski karma",
    "bank ka manager aur KYC", "dost jo hamesha ghayab ho jaata hai", "rishtedaar jo pet me baat rakhta nahi",
]


# ------------------------------------------------------------------ tone: how dark / sharp / strange the joke is
TONES = {
    "light": dict(
        name="Light, relatable",
        how="Warm everyday comedy: a small problem gets blown up by a very desi reaction. Gentle, family-safe.",
        script="""HOOK: Mummy ne bola "ek minute" 😭
CAST: M = mummy maroon, K = beta tshirt
SCENE: kitchen
M (think, point): Beta, bas ek minute ruk, chai bana ke aati hoon. | बेटा, बस एक मिनट रुक, चाय बना के आती हूँ।
K (sleepy): Mummy, aapka ek minute kal subah tak chalta hai. | मम्मी, आपका एक मिनट कल सुबह तक चलता है।
M (shock): Kal subah? Abhi to shaam hai! | कल सुबह? अभी तो शाम है!
K (smug, phone): Dekho, chalis minute ho gaye. | देखो, चालीस मिनट हो गए।
M -> shrug sly pop
CTA: Tag karo us ko jiska "ek minute" kabhi khatam nahi hota 👇
CAPTION: Mummy ka ek minute = ek nayi duniya 😂
HASHTAGS: #desicomedy #mummy #relatable #family #funny""",
    ),
    "dark": dict(
        name="Dark comedy",
        how="The SITUATION is grim (death, debt, ruin, a cruel system, fate turning on someone) and the telling is dead "
            "straight and funny. Keep the darkness implied: cut away, a sound, a reaction instead of showing it. A "
            "deadpan character who treats the horrible thing as paperwork is the engine. The twist makes it worse in a "
            "way nobody saw coming. The butt of the joke is the situation / the system / the character's own folly.",
        script="""HOOK: Marne ke baad bhi line nahi chhoot'ti 💀
CAST: B = office_guy glasses, D = dada white
SCENE: office
B (angry, point): Pension chahiye? Pehle zinda hone ka certificate laao! | पेंशन चाहिए? पहले ज़िंदा होने का सर्टिफिकेट लाओ!
D (sad): Beta, main to teen saal pehle... | बेटा, मैं तो तीन साल पहले...
B (smug): Teen saal pehle? To teen saal ka late fine bhi lagega. | तीन साल पहले? तो तीन साल का लेट फाइन भी लगेगा।
D (shock): Fine kitna? | फाइन कितना?
B (sly): Bas utna, jitni teen saal ki pension banti. | बस उतना, जितनी तीन साल की पेंशन बनती।
D -> dead thud shake
CTA: Tag karo us dost ko jiska sarkari kaam atka hai 👇
CAPTION: Sarkari daftar me bhoot bhi line me lagte hain 💀
HASHTAGS: #darkcomedy #sarkari #relatable #desicomedy #funny""",
    ),
    "satire": dict(
        name="Satire",
        how="Hold a mirror to a very recognisable absurdity (offices, government work, bills, rules, show-offs). "
            "Fictional people and institutions only. The character in charge is completely sure he is right; "
            "his own logic is what destroys him.",
        script="""HOOK: Pul ban gaya, bas nadi banna baaki hai 🌉
CAST: N = boss blazer, J = padosi kurta
SCENE: street
N (smug, point): Janta ke liye naya pul, sirf teen saal me taiyaar! | जनता के लिए नया पुल, सिर्फ़ तीन साल में तैयार!
J (think): Sahab, par yahan nadi to hai hi nahi. | साहब, पर यहाँ नदी तो है ही नहीं।
N (sly): Isiliye to pehle pul, phir nadi aayegi. | इसीलिए तो पहले पुल, फिर नदी आएगी।
J (think): Aur nadi kab aayegi? | और नदी कब आएगी?
N (smug): Agle pul ke baad. | अगले पुल के बाद।
J -> facepalm dead thud
CTA: Tag karo us ko jisne aisa pul dekha hai 👇
CAPTION: Pehle pul, phir nadi 😂
HASHTAGS: #satire #desicomedy #relatable #funny #sarkari""",
    ),
    "absurd": dict(
        name="Absurd / surreal",
        how="One impossible thing is true and everybody treats it as normal. Escalate the logic, never explain it. "
            "The last line is the most unreasonable and the most logical one.",
        script="""HOOK: Mere ghar ke wifi me bhoot hai 👻
CAST: A = boy, B = dadi
SCENE: room
A (shock): Dadi, wifi bahut slow chal raha hai! | दादी, वाईफाई बहुत स्लो चल रहा है!
B (smug): Bhoot ji ne download laga rakha hai. | भूत जी ने डाउनलोड लगा रखा है।
A (surprised): Kaun sa bhoot?! | कौन सा भूत?!
B (grin, phone): Wahi, jo tumhari ex ke message padh raha hai. | वही, जो तुम्हारी एक्स के मैसेज पढ़ रहा है।
A -> dead thud shake
CTA: Tag karo apne ghar ke wifi wale bhoot ko 👇
CAPTION: Dadi ko sab pata hai 👻
HASHTAGS: #absurd #desicomedy #bhoot #funny #relatable""",
    ),
    "twist": dict(
        name="Sweet start, savage twist",
        how="Start warm and loving so the viewer relaxes, then the last line turns it into something savage or "
            "shocking. The setup lines must really sound sweet.",
        script="""HOOK: Papa ne itne pyaar se bulaya, aur phir... 😳
CAST: P = papa kurta, K = beta tshirt
SCENE: room
P (smile): Beta, aao, aaj papa tumhe ek raaz batayenge. | बेटा, आओ, आज पापा तुम्हें एक राज़ बताएँगे।
K (love): Papa, aap kitne achhe ho! | पापा, आप कितने अच्छे हो!
P (sly, point): Mummy ki sabzi ka namak... maine badla tha. | मम्मी की सब्ज़ी का नमक... मैंने बदला था।
K (shock): Papa!! Isiliye sabzi itni meethi thi?! | पापा!! इसीलिए सब्ज़ी इतनी मीठी थी?!
P -> shrug grin pop
CTA: Tag karo us ko jo ghar me chupke se khel karta hai 👇
CAPTION: Papa ka raaz 😂
HASHTAGS: #twist #desicomedy #papa #funny #relatable""",
    ),
}
# when nobody picks a tone and there is no idea, these are the odds
TONE_ODDS = {"light": 3, "dark": 3, "satire": 2, "absurd": 2, "twist": 2}


def split_tone(instruction):
    """('TONE: dark\nmy idea' -> ('dark', 'my idea')). The tone is None when the text names none."""
    text = instruction or ""
    m = re.search(r"^\s*TONE\s*:\s*([A-Za-z_]+)\s*$", text, re.M | re.I)
    if not m:
        return None, text.strip()
    rest = (text[:m.start()] + text[m.end():]).strip()
    key = m.group(1).lower()
    return (key if key in TONES else None), rest


def pick_tone(style="auto", idea="", rng=None):
    """Return a tone key, or "auto" (an idea was given and no tone: the writer picks what fits the idea)."""
    rng = rng or random
    if style in TONES:
        return style
    if idea and idea.strip():
        return "auto"
    keys = list(TONE_ODDS)
    return rng.choices(keys, [TONE_ODDS[k] for k in keys])[0]


def tone_block(key):
    if key == "auto":
        return ("# Tone for THIS video: your choice\nChoose the tone that fits the idea best and commit to it fully "
                "(%s). Do not water a dark, ironic or absurd idea down into a light one; do not make a light idea "
                "needlessly grim.\nExamples of each tone, only to show the style (never copy their jokes):\n\n%s"
                % (", ".join(TONES), "\n\n".join("[%s]\n%s" % (k, t["script"]) for k, t in TONES.items())))
    t = TONES[key]
    return ("# Tone for THIS video: %s (%s)\n%s\nAn example of this tone in the exact format, only to show the style "
            "(never copy its joke):\n\n%s" % (t["name"], key, t["how"], t["script"]))


def pick(style="auto", rng=None, avoid=()):
    """Return (key, hook dict). 'auto' picks a random style (not in `avoid` if possible)."""
    rng = rng or random
    if style in HOOKS:
        return style, HOOKS[style]
    keys = [k for k in HOOKS if k not in avoid] or list(HOOKS)
    k = rng.choice(keys)
    return k, HOOKS[k]


def prompt_block(key, fmt="json"):
    h = HOOKS[key]
    where = ("Put the hook text in the top-level \"hook\" field AND show it as an overlay with style \"hook\" "
             "from t=0 to about 2 seconds." if fmt == "json" else "Write it on the HOOK: line.")
    return ("# Hook for THIS video: %s (%s)\n%s\nExample hook texts (write your own, do not copy): %s\n%s"
            % (h["name"], key, h["how"], " | ".join(h["examples"]), where))


def random_topic(rng=None):
    return (rng or random).choice(TOPICS)

"""Hook styles: how the first 2 seconds of a short grab the viewer.

The director gets one of these (or picks one when the style is "auto") and must
open the video with it. Topics feed the "auto idea" mode (no instruction given).
"""
import random

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
]


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

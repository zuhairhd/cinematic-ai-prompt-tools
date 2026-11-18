#!/usr/bin/env python3
"""
Timed Storyboard Prompt Generator
=================================
Based on IDALL AI - Part 2 "Make It Cinematic" - L2 Timed Storyboard.

Builds a GPT Image 2 (ChatGPT) prompt for a 3x3 timed storyboard that becomes
the blueprint for a Seedance 2.0 video. It follows the lesson's formula:
  format line -> panel contents -> reference lock -> preserve list ->
  scene concept -> 9 timed beats -> quality/continuity -> layout -> avoid list

Main rule from the lesson: the character, outfit, world and lighting stay
the same. Only the story progresses (calm -> tension -> action).

AI Story Director (new): type a simple message ("even in hard times there is hope") and the app
interprets it, plans 9 cinematic beats with an LLM (structured JSON, validated), computes the
timecodes in Python and compiles the final storyboard prompt. See README_AI_STORY_DIRECTOR.md.

Run:   python storyboard_prompt_generator.py            (GUI, needs tkinter)
CLI:   python storyboard_prompt_generator.py --list
       python storyboard_prompt_generator.py --preset "The Sand Awakens" --duration 15
       python storyboard_prompt_generator.py --project my_story.json
       python storyboard_prompt_generator.py --ai "There is always hope" --save hope.json
Manual mode needs no external packages (Python 3.8+). AI mode needs `pip install openai`
and the OPENAI_API_KEY environment variable.
"""

import json
import os
import sys
import argparse
import threading
import queue
from copy import deepcopy

from storyboard_ai.constants import (BEAT_WEIGHTS, SHOT_TYPES, PRESERVE_ITEMS, AVOID_DEFAULT,  # noqa: F401
                                     TEMPLATE_BEATS, TEMPLATE_CONCEPT, REFERENCE_ROLES,
                                     DURATION_CHOICES, MIN_DURATION, MAX_DURATION, STORY_TYPES, VISUAL_STYLES)
from storyboard_ai.timing import fmt_time, compute_timecodes, check_duration, TimingError  # noqa: F401
from storyboard_ai.prompt_compiler import MODES as PROMPT_MODES, compile_prompt, preserve_phrase

APP_TITLE = "Timed Storyboard Prompt Generator - IDALL AI L2"

# --------------------------------------------------------------------------
# Lesson reference data  (BEAT_WEIGHTS, SHOT_TYPES, PRESERVE_ITEMS, AVOID_DEFAULT
# live in storyboard_ai/constants.py and are re-exported here)
# --------------------------------------------------------------------------

BEAT_PURPOSE = [
    "Establish world & scale - calm",
    "Atmosphere starts moving",
    "Emotional moment - character notices",
    "Small detail reacts - something is coming",
    "Environment gets heavier",
    "Tease the threat - don't fully reveal",
    "Character turns toward the movement",
    "Big action beat - the reveal",
    "Iconic hero payoff",
]



def _b(title, shot, action):
    return {"title": title, "shot": shot, "action": action}


PRESETS = {
    "Generic (Lesson Template)": {
        "concept": TEMPLATE_CONCEPT,
        "beats": deepcopy(TEMPLATE_BEATS),
    },
    "The Sand Awakens (Lesson Example)": {
        "concept": ("A mysterious desert oracle stands alone in alien dunes. The wind rises. She senses "
                    "something under the sand. A mechanical shape moves beneath the dunes. Dust explodes "
                    "behind her. A massive sand serpent breaks through the desert. She remains calm inside "
                    "the storm."),
        "beats": [
            _b("DESERT SILENCE", "Extreme wide shot",
               "The oracle stands alone in vast alien dunes, showing the world and its scale. Calm and silent."),
            _b("THE WIND RISES", "Medium shot",
               "Her cloak starts moving as the wind picks up. The atmosphere becomes more tense."),
            _b("SHE SENSES IT", "Close-up portrait",
               "Her eyes shift subtly. She feels something beneath the sand."),
            _b("SAND VIBRATION", "Detail shot",
               "Sand grains, jewelry and fabric tremble - something is coming."),
            _b("LOW RUMBLE", "Low-angle or dramatic medium shot",
               "The camera drops low; the dunes feel heavier and unstable around her."),
            _b("SHADOW UNDER THE DUNES", "Wide shot",
               "A dark mechanical shape moves beneath the dunes, not fully revealed."),
            _b("DUST WALL", "Side profile or cinematic angle",
               "A wall of dust rises behind her as she slowly turns toward the movement."),
            _b("THE REVEAL", "Wide action shot",
               "A massive mechanical sand serpent breaks through the dunes in an explosion of sand."),
            _b("HERO ENDING", "Low-angle hero shot",
               "She stands calm and iconic inside the storm as the serpent towers behind her."),
        ],
    },
    "Storm at Sea": {
        "concept": ("A lone captain stands on the deck of an old ship on a dark ocean. The sea goes still, "
                    "then the wind turns. Something huge moves beneath the waves. Lightning splits the sky "
                    "as a colossal sea creature rises. The captain holds the wheel, unshaken."),
        "beats": [
            _b("STILL WATER", "Extreme wide shot", "The ship sits alone on a calm, dark ocean under heavy clouds."),
            _b("THE WIND TURNS", "Medium shot", "Sails snap and rain begins to slant across the deck."),
            _b("THE CAPTAIN LISTENS", "Close-up portrait", "The captain's eyes narrow toward the horizon."),
            _b("ROPES TIGHTEN", "Detail shot", "Wet ropes creak and the compass needle spins."),
            _b("SWELL RISES", "Low-angle or dramatic medium shot", "Waves grow taller and the deck tilts."),
            _b("SHAPE BENEATH", "Wide shot", "A vast dark shadow glides under the water near the ship."),
            _b("LIGHTNING FLASH", "Side profile or cinematic angle", "Lightning lights the captain's profile as they turn."),
            _b("THE LEVIATHAN", "Wide action shot", "A colossal sea creature erupts from the waves beside the ship."),
            _b("HOLD THE WHEEL", "Low-angle hero shot", "The captain grips the wheel, calm and defiant in the storm."),
        ],
    },
    "Neon City Pursuit": {
        "concept": ("A cyberpunk courier stands on a rooftop above a rain-soaked neon city. The signs flicker. "
                    "They notice they are being tracked. Drones gather in the fog. A giant security mech rises "
                    "between the towers. The courier stays cool, ready to jump."),
        "beats": [
            _b("NEON SILENCE", "Extreme wide shot", "The courier stands on a rooftop above an endless neon skyline in the rain."),
            _b("SIGNS FLICKER", "Medium shot", "Neon signs glitch and steam drifts around the courier."),
            _b("TRACKED", "Close-up portrait", "A red scan line crosses the courier's face; their eyes sharpen."),
            _b("PULSE ON THE WRIST", "Detail shot", "A wrist device vibrates and rain beads shake on the jacket."),
            _b("CITY HUM", "Low-angle or dramatic medium shot", "Lights dim block by block; the air feels charged."),
            _b("DRONES IN THE FOG", "Wide shot", "Red drone lights gather inside the fog between towers."),
            _b("SEARCHLIGHTS", "Side profile or cinematic angle", "Searchlights sweep past as the courier turns."),
            _b("THE MECH RISES", "Wide action shot", "A giant security mech rises between the skyscrapers."),
            _b("READY TO JUMP", "Low-angle hero shot", "The courier stands at the edge, calm and iconic in the neon storm."),
        ],
    },
    "Frozen Forest Guardian": {
        "concept": ("A hooded guardian stands in a silent snow forest at blue hour. Snow begins to fall faster. "
                    "She hears ice cracking. Frost spreads across the ground. Glowing eyes appear between the "
                    "trees. A giant ice wolf steps out. She raises her staff, perfectly calm."),
        "beats": [
            _b("WHITE SILENCE", "Extreme wide shot", "The guardian stands alone among tall frozen pines at blue hour."),
            _b("SNOW QUICKENS", "Medium shot", "Snowfall thickens and her cloak lifts in the cold wind."),
            _b("SHE HEARS IT", "Close-up portrait", "Frost on her lashes; her eyes move toward a distant crack."),
            _b("FROST SPREADS", "Detail shot", "Ice crystals creep across the ground and her staff's runes glow."),
            _b("BRANCHES BEND", "Low-angle or dramatic medium shot", "Heavy snow-laden branches bend and groan above her."),
            _b("EYES IN THE TREES", "Wide shot", "Pale glowing eyes appear deep between the trees."),
            _b("WHITEOUT", "Side profile or cinematic angle", "A gust of snow surges as she turns her head."),
            _b("THE ICE WOLF", "Wide action shot", "A giant wolf of ice and mist steps out of the forest."),
            _b("STAFF RAISED", "Low-angle hero shot", "She raises her staff, calm and iconic in the swirling snow."),
        ],
    },
    "Volcanic Awakening": {
        "concept": ("An armored warrior stands on black volcanic rock under an ash-filled sky. Embers begin "
                    "to drift. The ground trembles. Lava glows through cracks. A fire titan climbs out of the "
                    "crater. The warrior stands firm, sword lowered."),
        "beats": [
            _b("ASH SKY", "Extreme wide shot", "The warrior stands alone on black rock beneath a dark ash sky."),
            _b("EMBERS DRIFT", "Medium shot", "Glowing embers float past the armor."),
            _b("THE WARRIOR FEELS IT", "Close-up portrait", "Behind the visor, the warrior's eyes lift toward the crater."),
            _b("CRACKS GLOW", "Detail shot", "Thin lines of lava glow between the stones under the boots."),
            _b("GROUND SHAKES", "Low-angle or dramatic medium shot", "Rocks tremble and smoke thickens around the warrior."),
            _b("FIRE IN THE CRATER", "Wide shot", "A massive glowing silhouette shifts inside the distant crater."),
            _b("HEAT WAVE", "Side profile or cinematic angle", "A wave of heat and ash surges as the warrior turns."),
            _b("THE FIRE TITAN", "Wide action shot", "A towering titan of lava and stone climbs out of the volcano."),
            _b("STAND FIRM", "Low-angle hero shot", "The warrior stands firm and iconic against the burning sky."),
        ],
    },
    "Arabian Night Market": {
        "concept": ("A cloaked storyteller stands in an empty old souq at night under hanging lanterns. The "
                    "lanterns sway. She hears a whisper in the wind. Brass lamps tremble on the stalls. Smoke "
                    "takes shape above the rooftops. A giant djinn of smoke and gold rises over the market. "
                    "She stays calm, holding an ancient lamp."),
        "beats": [
            _b("LANTERN SILENCE", "Extreme wide shot", "The storyteller stands alone in an empty souq lit by warm lanterns."),
            _b("LANTERNS SWAY", "Medium shot", "Lanterns swing and fabric awnings ripple in a sudden breeze."),
            _b("A WHISPER", "Close-up portrait", "Her kohl-lined eyes shift as she hears a whisper."),
            _b("BRASS TREMBLES", "Detail shot", "Brass lamps and her bracelets tremble on the stall."),
            _b("SMOKE GATHERS", "Low-angle or dramatic medium shot", "Incense smoke thickens and coils around her."),
            _b("SHAPE OVER THE ROOFS", "Wide shot", "A huge smoky shape forms above the distant rooftops."),
            _b("GOLDEN WIND", "Side profile or cinematic angle", "Golden dust swirls as she turns toward the sky."),
            _b("THE DJINN", "Wide action shot", "A giant djinn of smoke and gold rises over the market."),
            _b("KEEPER OF THE LAMP", "Low-angle hero shot", "She holds the ancient lamp, calm and iconic beneath the djinn."),
        ],
    },
}

LESSON_GUIDE = """L2 - TIMED STORYBOARD: QUICK GUIDE

ONE BEAUTIFUL IMAGE IS NOT A VIDEO.
Decide what happens second by second before you animate. A great clip isn't random; it's planned.

MAIN RULE (CONTINUITY)
  The character stays the same.
  The outfit stays the same.
  The world stays the same.
  The lighting stays the same.
  Only the story progresses: calm -> tension -> action.

WORKFLOW
  1. Upload your Lesson 1 character image into ChatGPT.
  2. Paste the prompt generated by this tool.
  3. GPT Image 2 creates a 3x3 storyboard: 9 panels, each with a timecode,
     a shot title, and one short action description.

THE 9-BEAT ARC (15 s)
  1 OPENING SILENCE          extreme wide      establish world & scale
  2 THE SHIFT BEGINS         medium            atmosphere starts moving
  3 THE CHARACTER SENSES IT  close-up          emotional moment
  4 SMALL DETAIL MOVES       detail            something is coming
  5 TENSION BUILDS           low angle         environment gets heavier
  6 HIDDEN FORCE             wide              tease the threat, no full reveal
  7 ATMOSPHERE SURGES        side profile      character turns toward it
  8 THE REVEAL               wide action       the big event
  9 HERO ENDING              low-angle hero    calm & iconic inside the storm

  Timing: beats 1-7 = 1.5 s each, reveal = 2 s, hero ending = 2.5 s.

TIPS
  - Name YOUR world in the concept (e.g. "alien dunes", "sand serpent").
  - Make beat 4 a detail your character really wears (jewelry, cloak, armor).
  - Tease in beat 6, reveal in beat 8. Don't reveal early.
  - One short, motion-ready action per panel (rises, turns, breaks through).
  - If continuity breaks: re-upload the ORIGINAL image and keep the preserve
    and avoid lists unchanged.
  - Keep the storyboard: it's the blueprint for L3 (Storyboard -> Motion
    in Seedance 2.0).

HOMEWORK
  Post your original character image + your 3x3 timed storyboard in the community.

REFERENCES
  IDALL AI Classroom - L2 Timed Storyboard (lesson video + notes)
  https://www.skool.com/idall-lite-1529/classroom/66800446
"""


# --------------------------------------------------------------------------
# Core logic (no GUI)
# --------------------------------------------------------------------------

# fmt_time / compute_timecodes come from storyboard_ai.timing: same output as before for valid
# cases, but rounding can no longer produce zero-length panels (e.g. 3 s or 4 s clips).

def beat_weights(beats):
    """Per-beat pacing weights if every beat carries one (AI storyboards), else None (lesson timing)."""
    w = [b.get("weight") for b in beats]
    return w if len(w) == 9 and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in w) else None


def is_ai_cfg(cfg):
    return cfg.get("mode") == "ai" and isinstance(cfg.get("story"), dict)


def build_prompt(cfg, mode="image"):
    """cfg keys: duration, model, ref_mode, character_desc, concept, beats, preserve,
    avoid, style_notes, borders, extra_notes  (+ mode/story/reference_roles for AI storyboards).

    mode="image": the prompt for the 3x3 storyboard image (manual projects keep the lesson format);
    mode="director": the detailed Director's Storyboard, compiled from the same project state."""
    beats = cfg.get("beats") or []
    if len(beats) != 9:
        raise ValueError(f"A storyboard needs exactly 9 beats (found {len(beats)}).")
    if mode not in PROMPT_MODES:
        raise ValueError(f"Unknown prompt mode {mode!r}.")
    if is_ai_cfg(cfg) or mode == "director":
        return compile_prompt(cfg, mode)
    duration = int(cfg.get("duration", 15))
    model = (cfg.get("model") or "Seedance 2.0").strip() or "Seedance 2.0"
    tcs = compute_timecodes(duration, beat_weights(beats))
    use_image = cfg.get("ref_mode", "image") == "image"

    p = []
    basis = "based on the uploaded image" if use_image else "based on the character description below"
    p.append(f"Create a cinematic 3x3 timed storyboard for a {duration}-second {model} video sequence {basis}.")
    p.append("The storyboard must look like a professional film pre-production board, similar to a cinematic "
             "commercial storyboard. It must contain 9 panels in a clean 3x3 grid.")
    p.append("Each panel must include:\n• panel number\n• timecode\n• short cinematic shot title\n"
             "• one short action description")

    # Missing key -> lesson defaults; an explicitly empty selection stays empty (no preserve sentence).
    preserve = cfg.get("preserve")
    if preserve is None:
        preserve = PRESERVE_ITEMS
    preserve_txt = preserve_phrase(preserve) if preserve else ""
    if use_image:
        p.append("Use the uploaded image as the main character reference.")
        if preserve_txt:
            p.append(f"Preserve the same {preserve_txt} from the uploaded image.")
    else:
        desc = (cfg.get("character_desc") or "").strip() or "[describe your character, outfit and world here]"
        p.append(f"Main character and world:\n{desc}")
        if preserve_txt:
            p.append(f"Keep the same {preserve_txt} in every panel.")

    # The lesson concept appears only when the project itself contains it (Generic preset);
    # an empty concept is never silently replaced by the generic template.
    concept = (cfg.get("concept") or "").strip()
    if concept:
        p.append(f"The scene concept:\n{concept}")

    lines = ["Storyboard timing and panels:"]
    for tc, b in zip(tcs, beats):
        title = (b.get("title") or "").strip().upper() or "UNTITLED BEAT"
        shot = (b.get("shot") or "").strip().rstrip(".")
        action = (b.get("action") or "").strip()
        if action and action[-1] not in ".!?":
            action += "."
        lines.append(f"({tc}) {title} — {shot}. {action}")
    p.append("\n\n".join(lines))

    p.append("Make every panel feel like a real frame from the same expensive cinematic sequence. The storyboard "
             "must have strong visual continuity. The character, outfit, environment, lighting direction, "
             "atmosphere, color palette, and cinematic style must remain consistent across all 9 panels.")

    style = (cfg.get("style_notes") or "").strip()
    if style:
        p.append(f"Visual style notes: {style}")

    layout = "The composition should feel premium, clean, readable, and cinematic. "
    if cfg.get("borders", True):
        layout += "Use black borders between panels like a professional storyboard. "
    layout += "Keep the timecodes and titles small but readable. The images should be the main focus."
    p.append(layout)

    extra = (cfg.get("extra_notes") or "").strip()
    if extra:
        p.append(extra)

    # Missing key -> lesson avoid list; an avoid list the user cleared on purpose stays empty.
    avoid = cfg.get("avoid")
    avoid = (AVOID_DEFAULT if avoid is None else avoid).strip().rstrip(".")
    if avoid:
        p.append(f"Avoid {avoid}.")
    return "\n\n".join(p)


def _md_cell(s):
    return str(s or "").replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def build_beat_sheet_md(cfg, title):
    tcs = compute_timecodes(int(cfg.get("duration", 15)), beat_weights(cfg["beats"]))
    out = [f"# {title} - Timed Storyboard Plan", "",
           f"**Duration:** {cfg.get('duration', 15)} s  |  **Video model:** {cfg.get('model', 'Seedance 2.0')}", ""]
    if is_ai_cfg(cfg):
        st, ai = cfg["story"], cfg.get("ai") or {}
        if ai.get("original_message"):
            out += ["## Original message", "", "> " + ai["original_message"].replace("\n", "\n> "), ""]
        out += ["## Creative brief", "",
                f"- **Core message:** {st.get('core_message', '')}",
                f"- **Story type:** {STORY_TYPES.get(st.get('story_type'), (st.get('story_type', ''),))[0]}",
                f"- **Emotional goal:** {st.get('emotional_goal', '')}",
                f"- **Viewer takeaway:** {st.get('viewer_takeaway', '')}",
                f"- **Structure:** {' → '.join(st.get('narrative_structure') or [])}", ""]
        if ai.get("model"):
            out += [f"_Generated with {ai.get('provider', '')} · {ai['model']} · {ai.get('generated_at', '')}_", ""]
    out += ["## Scene concept", cfg.get("concept", ""), "",
            "## Beat sheet", "", "| # | Timecode | Shot title | Shot type | Action | Purpose |",
            "|---|---|---|---|---|---|"]
    for i, (tc, b) in enumerate(zip(tcs, cfg["beats"])):
        purpose = b.get("purpose") or ("" if is_ai_cfg(cfg) else BEAT_PURPOSE[i])
        out.append(f"| {i + 1} | {tc} | {_md_cell(b['title'])} | {_md_cell(b['shot'])} | {_md_cell(b['action'])} "
                   f"| {_md_cell(purpose)} |")
    if is_ai_cfg(cfg):
        cont = cfg["story"].get("continuity") or {}
        out += ["", "## Continuity", "", "**Fixed:**"] + [f"- {f}" for f in cont.get("fixed_attributes") or []]
        if cont.get("intentional_changes"):
            out += ["", "**Intentional changes:**"] + [
                f"- {c.get('attribute', '')}: {c.get('change', '')} ({c.get('panels', '')})"
                for c in cont["intentional_changes"]]
    out += ["", "## GPT Image 2 prompt", "", "```text", build_prompt(cfg), "```", ""]
    return "\n".join(out)


def default_cfg(preset_name="Generic (Lesson Template)"):
    pr = PRESETS[preset_name]
    return {"story_title": preset_name.split(" (")[0], "duration": 15, "model": "Seedance 2.0",
            "ref_mode": "image", "character_desc": "", "concept": pr["concept"],
            "beats": deepcopy(pr["beats"]), "preserve": list(PRESERVE_ITEMS),
            "avoid": AVOID_DEFAULT, "style_notes": "", "borders": True, "extra_notes": "",
            "mode": "manual"}


# --------------------------------------------------------------------------
# GUI
# --------------------------------------------------------------------------

STORY_TYPE_LABELS = ["Automatic"] + [label for label, _ in STORY_TYPES.values()]
LANG_OPTIONS = ["English (recommended for image models)", "Same as my message"]


def _story_type_key(label):
    return next((k for k, (lb, _) in STORY_TYPES.items() if lb == label), "auto")


def _parse_changes(text):
    """'attribute: change (panels)' per line -> list of intentional-change dicts."""
    out = []
    for line in text.splitlines():
        line = line.strip().lstrip("•-* ").strip()
        if not line:
            continue
        attr, sep, rest = line.partition(":")
        if not sep:
            attr, rest = "change", line
        panels = ""
        if rest.rstrip().endswith(")") and "(" in rest:
            i = rest.rfind("(")
            panels, rest = rest[i + 1:].rstrip().rstrip(")").strip(), rest[:i]
        out.append({"attribute": attr.strip(), "change": rest.strip(), "panels": panels})
    return out


def _format_changes(changes):
    return "\n".join(f"{c.get('attribute', '')}: {c.get('change', '')}"
                     + (f" ({c['panels']})" if c.get("panels") else "") for c in changes or [])


def build_app(root, provider_factory=None):
    """Build the whole GUI inside `root` and return a namespace of widgets/actions (used by tests)."""
    import tkinter as tk
    from types import SimpleNamespace
    from tkinter import ttk, filedialog, messagebox

    from storyboard_ai import ai_provider
    from storyboard_ai.ai_provider import AIProviderError, OpenAIProvider
    from storyboard_ai.director import StoryDirector, normalize_settings
    from storyboard_ai.project_io import ProjectError, load_project, save_project
    from storyboard_ai.story_interpreter import InputError, detect_language
    from storyboard_ai.storyboard_planner import StoryboardGenerationError
    from storyboard_ai.storyboard_validator import review_text, validate_cfg

    # dialogs are attributes so tests can replace them
    ui = SimpleNamespace(askyesno=messagebox.askyesno, askyesnocancel=messagebox.askyesnocancel,
                         showerror=messagebox.showerror, showwarning=messagebox.showwarning,
                         showinfo=messagebox.showinfo, asksave=filedialog.asksaveasfilename,
                         askopen=filedialog.askopenfilename)

    root.title(APP_TITLE)
    root.geometry("1220x840")
    root.minsize(1000, 660)

    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    ACC = "#B5651D"
    style.configure("Head.TLabel", font=("Segoe UI", 15, "bold"), foreground=ACC)
    style.configure("Sub.TLabel", foreground="#666")
    style.configure("Bold.TLabel", font=("Segoe UI", 10, "bold"))
    style.configure("Big.TLabel", font=("Segoe UI", 12, "bold"))
    style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))

    # ---- state vars
    v_preset = tk.StringVar(value="The Sand Awakens (Lesson Example)")
    v_title = tk.StringVar()
    v_duration = tk.IntVar(value=15)
    v_model = tk.StringVar(value="Seedance 2.0")
    v_ref = tk.StringVar(value="image")
    role_vars = {k: tk.BooleanVar(value=False) for k in REFERENCE_ROLES}  # what the uploaded image shows
    v_pmode = tk.StringVar(value=PROMPT_MODES["image"])
    MODE_KEYS = {v: k for k, v in PROMPT_MODES.items()}
    v_borders = tk.BooleanVar(value=True)
    preserve_vars = {item: tk.BooleanVar(value=True) for item in PRESERVE_ITEMS}
    beat_widgets = []  # (tc_label, title_var, shot_var, action_text, purpose_var)
    beat_extra = [dict() for _ in range(9)]  # purpose/visual/camera/lighting/continuity/weight per beat
    # mode/story/ai: AI storyboard metadata; baseline: snapshot used to detect user edits
    state = {"mode": "manual", "story": None, "ai": None, "last_generated": "", "baseline": None,
             "busy": False, "cancel": None, "last_settings": None, "last_message": ""}
    status = tk.StringVar(value="Type your message in the AI Story Director, or pick a preset, then Generate.")

    # ---- header
    top = ttk.Frame(root, padding=(14, 10, 14, 4))
    top.pack(fill="x")
    ttk.Label(top, text="Timed Storyboard Prompt Generator", style="Head.TLabel").pack(side="left")
    ttk.Label(top, text="   AI Story Director · IDALL AI L2 · 3x3 storyboard for GPT Image 2 -> Seedance 2.0",
              style="Sub.TLabel").pack(side="left")

    nb = ttk.Notebook(root)

    def get_duration():
        try:
            return check_duration(v_duration.get())
        except (tk.TclError, TimingError):
            return None

    # ================= Tab 0: AI Story Director =================
    t0 = ttk.Frame(nb, padding=12)
    nb.add(t0, text="  ★ AI Story Director  ")
    t0.columnconfigure(0, weight=1)
    ttk.Label(t0, text="What message or story do you want to communicate?", style="Big.TLabel").grid(
        row=0, column=0, sticky="w")
    ttk.Label(t0, text="Write in English or العربية — a single sentence is enough. "
                       "The AI builds the story, 9 shots, timing and continuity for you.",
              style="Sub.TLabel").grid(row=1, column=0, sticky="w", pady=(0, 4))
    msg_frame = ttk.Frame(t0)
    msg_frame.grid(row=2, column=0, sticky="nsew")
    msg_frame.columnconfigure(0, weight=1)
    txt_msg = tk.Text(msg_frame, height=5, wrap="word", font=("Segoe UI", 11), undo=True)
    txt_msg.grid(row=0, column=0, sticky="nsew")
    msb = ttk.Scrollbar(msg_frame, orient="vertical", command=txt_msg.yview)
    msb.grid(row=0, column=1, sticky="ns")
    txt_msg.configure(yscrollcommand=msb.set)

    def on_msg_key(_e=None):
        rtl = detect_language(txt_msg.get("1.0", "end")) == "ar"
        txt_msg.tag_configure("dir", justify="right" if rtl else "left")
        txt_msg.tag_add("dir", "1.0", "end")
    txt_msg.bind("<KeyRelease>", on_msg_key)

    opts = ttk.LabelFrame(t0, text=" Optional settings (sensible defaults) ", padding=8)
    opts.grid(row=3, column=0, sticky="ew", pady=8)
    for c in (1, 3):
        opts.columnconfigure(c, weight=1)
    v_story_type = tk.StringVar(value="Automatic")
    v_vstyle = tk.StringVar(value="Automatic")
    v_audience = tk.StringVar()
    v_lang = tk.StringVar(value=LANG_OPTIONS[0])
    v_ai_model = tk.StringVar(value=os.environ.get("STORYBOARD_AI_MODEL") or ai_provider.DEFAULT_MODEL)
    v_review = tk.BooleanVar(value=True)

    ttk.Label(opts, text="Story type", style="Bold.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=2)
    ttk.Combobox(opts, textvariable=v_story_type, values=STORY_TYPE_LABELS, state="readonly",
                 width=28).grid(row=0, column=1, sticky="w")
    ttk.Label(opts, text="Video duration (s)", style="Bold.TLabel").grid(row=0, column=2, sticky="w", padx=(16, 6))
    ttk.Spinbox(opts, from_=MIN_DURATION, to=MAX_DURATION, textvariable=v_duration, width=6).grid(
        row=0, column=3, sticky="w")
    ttk.Label(opts, text="Visual style", style="Bold.TLabel").grid(row=1, column=0, sticky="w", pady=2)
    ttk.Combobox(opts, textvariable=v_vstyle, values=VISUAL_STYLES, width=34).grid(row=1, column=1, sticky="w")
    ttk.Label(opts, text="Target audience", style="Bold.TLabel").grid(row=1, column=2, sticky="w", padx=(16, 6))
    ttk.Entry(opts, textvariable=v_audience, width=34).grid(row=1, column=3, sticky="w")
    ttk.Label(opts, text="Reference image shows", style="Bold.TLabel").grid(row=2, column=0, sticky="w", pady=2)
    rr = ttk.Frame(opts)
    rr.grid(row=2, column=1, sticky="w")
    ttk.Radiobutton(rr, text="No image", value="text", variable=v_ref,
                    command=lambda: on_ref_mode()).pack(side="left")
    for _k, _lbl in REFERENCE_ROLES.items():
        ttk.Checkbutton(rr, text=_lbl.split(" /")[0], variable=role_vars[_k],
                        command=lambda: on_role_toggle()).pack(side="left", padx=2)
    ttk.Label(opts, text="Storyboard language", style="Bold.TLabel").grid(row=2, column=2, sticky="w", padx=(16, 6))
    ttk.Combobox(opts, textvariable=v_lang, values=LANG_OPTIONS, state="readonly", width=34).grid(
        row=2, column=3, sticky="w")
    ttk.Label(opts, text="Character / product\n(optional, kept exactly)", style="Bold.TLabel").grid(
        row=3, column=0, sticky="nw", pady=2)
    txt_subject = tk.Text(opts, height=2, wrap="word", font=("Segoe UI", 10))
    txt_subject.grid(row=3, column=1, columnspan=3, sticky="ew", pady=2)
    ttk.Label(opts, text="AI model (story planning)", style="Bold.TLabel").grid(row=4, column=0, sticky="w", pady=2)
    mrow = ttk.Frame(opts)
    mrow.grid(row=4, column=1, columnspan=3, sticky="w")
    ttk.Combobox(mrow, textvariable=v_ai_model, values=ai_provider.MODEL_SUGGESTIONS, width=18).pack(side="left")
    ttk.Checkbutton(mrow, text="AI creative review (subjective, extra request)", variable=v_review).pack(
        side="left", padx=10)
    v_key = tk.StringVar()
    ttk.Label(mrow, textvariable=v_key, style="Sub.TLabel").pack(side="left", padx=6)

    def refresh_key_status():
        if not ai_provider.openai_sdk_available() and provider_factory is None:
            v_key.set("⚠ 'openai' package missing — run: pip install -r requirements.txt (manual mode works)")
        elif ai_provider.api_key_available() or provider_factory is not None:
            v_key.set("✓ API key detected (OPENAI_API_KEY)" if provider_factory is None else "✓ test provider")
        else:
            v_key.set("⚠ OPENAI_API_KEY not set — AI generation disabled; manual tabs still work")
    refresh_key_status()

    act = ttk.Frame(t0)
    act.grid(row=4, column=0, sticky="ew")
    btn_gen = ttk.Button(act, text="✦ Generate AI Storyboard", style="Accent.TButton",
                         command=lambda: start_ai_generation())
    btn_gen.pack(side="left")
    btn_regen = ttk.Button(act, text="Regenerate complete storyboard", command=lambda: start_ai_generation(regen=True))
    btn_regen.pack(side="left", padx=6)
    ttk.Separator(act, orient="vertical").pack(side="left", fill="y", padx=6)
    ttk.Label(act, text="Scene").pack(side="left")
    v_scene = tk.IntVar(value=1)
    ttk.Spinbox(act, from_=1, to=9, textvariable=v_scene, width=3, state="readonly").pack(side="left", padx=3)
    v_scene_note = tk.StringVar()
    ttk.Entry(act, textvariable=v_scene_note, width=26).pack(side="left", padx=3)
    btn_scene = ttk.Button(act, text="Regenerate scene", command=lambda: start_scene_regen(v_scene.get() - 1))
    btn_scene.pack(side="left", padx=3)

    act2 = ttk.Frame(t0)
    act2.grid(row=5, column=0, sticky="ew", pady=(6, 0))
    ttk.Button(act2, text="Generate final prompt  ->", style="Accent.TButton",
               command=lambda: generate()).pack(side="left")
    ttk.Combobox(act2, textvariable=v_pmode, values=list(PROMPT_MODES.values()), state="readonly",
                 width=34).pack(side="left", padx=6)
    ttk.Button(act2, text="Copy prompt", command=lambda: copy_prompt()).pack(side="left", padx=6)
    ttk.Button(act2, text="Save project…", command=lambda: save_story()).pack(side="left", padx=6)
    ttk.Button(act2, text="Load project…", command=lambda: open_story()).pack(side="left", padx=6)
    ttk.Label(act2, text="  Tip: scene note is optional, e.g. 'make it a close-up of her hands'",
              style="Sub.TLabel").pack(side="left")

    prog_row = ttk.Frame(t0)
    prog_row.grid(row=6, column=0, sticky="ew", pady=6)
    prog = ttk.Progressbar(prog_row, mode="indeterminate", length=220)
    prog.pack(side="left")
    v_prog = tk.StringVar(value="")
    ttk.Label(prog_row, textvariable=v_prog).pack(side="left", padx=8)
    btn_cancel = ttk.Button(prog_row, text="Cancel", command=lambda: cancel_task(), state="disabled")
    btn_cancel.pack(side="right")

    res_frame = ttk.Frame(t0)
    res_frame.grid(row=7, column=0, sticky="nsew")
    t0.rowconfigure(7, weight=1)
    t0.rowconfigure(2, weight=0)
    res_frame.columnconfigure(0, weight=1)
    res_frame.rowconfigure(0, weight=1)
    txt_result = tk.Text(res_frame, height=8, wrap="word", font=("Consolas", 9), background="#FBF7F1",
                         state="disabled")
    txt_result.grid(row=0, column=0, sticky="nsew")
    rsb = ttk.Scrollbar(res_frame, orient="vertical", command=txt_result.yview)
    rsb.grid(row=0, column=1, sticky="ns")
    txt_result.configure(yscrollcommand=rsb.set)

    def show_result(text):
        txt_result.configure(state="normal")
        txt_result.delete("1.0", "end")
        txt_result.insert("1.0", text)
        txt_result.configure(state="disabled")

    # ================= Tab 1: Story =================
    t1 = ttk.Frame(nb, padding=14)
    nb.add(t1, text="  1 · Story  ")
    t1.columnconfigure(1, weight=1)

    ttk.Label(t1, text="Story preset", style="Bold.TLabel").grid(row=0, column=0, sticky="w", pady=4)
    pre_row = ttk.Frame(t1)
    pre_row.grid(row=0, column=1, sticky="ew")
    cb = ttk.Combobox(pre_row, textvariable=v_preset, values=list(PRESETS), state="readonly", width=40)
    cb.pack(side="left")
    ttk.Button(pre_row, text="Load preset", command=lambda: load_preset()).pack(side="left", padx=6)
    ttk.Label(pre_row, text="(loads concept + 9 beats; you can edit everything)", style="Sub.TLabel").pack(side="left")

    ttk.Label(t1, text="Story title", style="Bold.TLabel").grid(row=1, column=0, sticky="w", pady=4)
    ttk.Entry(t1, textvariable=v_title, width=50).grid(row=1, column=1, sticky="w")

    ttk.Label(t1, text="Duration", style="Bold.TLabel").grid(row=2, column=0, sticky="w", pady=4)
    dur_row = ttk.Frame(t1)
    dur_row.grid(row=2, column=1, sticky="w")
    for d in DURATION_CHOICES:
        ttk.Radiobutton(dur_row, text=f"{d} s", value=d, variable=v_duration).pack(side="left", padx=4)
    ttk.Label(dur_row, text="  Custom:").pack(side="left")
    ttk.Spinbox(dur_row, from_=MIN_DURATION, to=MAX_DURATION, textvariable=v_duration, width=5).pack(side="left")
    ttk.Label(dur_row, text=f"s ({MIN_DURATION}-{MAX_DURATION})   Lesson default = 15 s (timecodes scale automatically)",
              style="Sub.TLabel").pack(side="left")

    ttk.Label(t1, text="Video model", style="Bold.TLabel").grid(row=3, column=0, sticky="w", pady=4)
    ttk.Combobox(t1, textvariable=v_model, values=["Seedance 2.0", "Kling", "Veo", "Runway", "Sora", "Hailuo"],
                 width=20).grid(row=3, column=1, sticky="w")

    ttk.Label(t1, text="Reference image", style="Bold.TLabel").grid(row=4, column=0, sticky="nw", pady=4)
    ref_row = ttk.Frame(t1)
    ref_row.grid(row=4, column=1, sticky="w")
    ttk.Radiobutton(ref_row, text="Uploaded image (lesson method) — it shows:", value="image",
                    variable=v_ref, command=lambda: on_ref_mode()).pack(side="left")
    for _k, _lbl in REFERENCE_ROLES.items():
        ttk.Checkbutton(ref_row, text=_lbl, variable=role_vars[_k],
                        command=lambda: on_role_toggle()).pack(side="left", padx=2)
    ttk.Radiobutton(ref_row, text="No image (text description)", value="text",
                    variable=v_ref, command=lambda: on_ref_mode()).pack(side="left", padx=8)

    ttk.Label(t1, text="Character / world\ndescription", style="Bold.TLabel").grid(row=5, column=0, sticky="nw", pady=4)
    txt_desc = tk.Text(t1, height=5, wrap="word", font=("Segoe UI", 10))
    txt_desc.grid(row=5, column=1, sticky="ew", pady=4)

    ttk.Label(t1, text="Scene concept", style="Bold.TLabel").grid(row=6, column=0, sticky="nw", pady=4)
    txt_concept = tk.Text(t1, height=7, wrap="word", font=("Segoe UI", 10))
    txt_concept.grid(row=6, column=1, sticky="nsew", pady=4)
    t1.rowconfigure(6, weight=1)
    v_mode_lbl = tk.StringVar()
    ttk.Label(t1, textvariable=v_mode_lbl, style="Sub.TLabel").grid(row=7, column=1, sticky="w")

    def on_role_toggle():
        v_ref.set("image" if any(v.get() for v in role_vars.values()) else "text")
        toggle_desc()

    def on_ref_mode():
        if v_ref.get() == "text":
            for v in role_vars.values():
                v.set(False)
        elif not any(v.get() for v in role_vars.values()):
            status.set("Tick what the reference image shows (Character, Product, Environment or Style).")
        toggle_desc()

    def toggle_desc():
        # AI storyboards use the description as supporting notes even in image mode.
        on = v_ref.get() == "text" or state["mode"] == "ai"
        txt_desc.configure(state="normal" if on else "disabled", background="white" if on else "#EEE")

    def refresh_mode_label():
        if state["mode"] == "ai":
            v_mode_lbl.set("AI storyboard — every field is editable; the final prompt is compiled from your edits.")
        else:
            v_mode_lbl.set("Tip: one paragraph, calm -> tension -> action. Name your world and the big reveal.")

    # ================= Tab 2: Beats =================
    t2 = ttk.Frame(nb, padding=(10, 10))
    nb.add(t2, text="  2 · 9 Beats  ")
    hdr = ttk.Frame(t2)
    hdr.pack(fill="x")
    for col, (txt, w) in enumerate([("#", 3), ("Timecode", 13), ("Shot title", 26), ("Shot type", 28),
                                    ("Action (one short line)", 44), ("", 14)]):
        ttk.Label(hdr, text=txt, style="Bold.TLabel", width=w).grid(row=0, column=col, sticky="w", padx=3)

    canvas = tk.Canvas(t2, highlightthickness=0)
    sb = ttk.Scrollbar(t2, orient="vertical", command=canvas.yview)
    inner = ttk.Frame(canvas)
    inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=sb.set)
    canvas.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")

    def on_wheel(e):
        if nb.select() == str(t2):  # only scroll the beat list while its tab is visible
            canvas.yview_scroll(int(-e.delta / 120), "units")
    canvas.bind_all("<MouseWheel>", on_wheel)

    for i in range(9):
        ttk.Label(inner, text=str(i + 1), style="Bold.TLabel", width=3).grid(row=i * 2, column=0, sticky="nw", padx=3, pady=(8, 0))
        tc = ttk.Label(inner, text="", width=13, foreground=ACC)
        tc.grid(row=i * 2, column=1, sticky="nw", padx=3, pady=(8, 0))
        tv = tk.StringVar()
        ttk.Entry(inner, textvariable=tv, width=26).grid(row=i * 2, column=2, sticky="nw", padx=3, pady=(6, 0))
        sv = tk.StringVar()
        ttk.Combobox(inner, textvariable=sv, values=SHOT_TYPES, width=28).grid(row=i * 2, column=3, sticky="nw", padx=3, pady=(6, 0))
        at = tk.Text(inner, height=2, width=46, wrap="word", font=("Segoe UI", 9))
        at.grid(row=i * 2, column=4, sticky="nw", padx=3, pady=(6, 0))
        bb = ttk.Frame(inner)
        bb.grid(row=i * 2, column=5, sticky="nw", padx=3, pady=(6, 0))
        ttk.Button(bb, text="Details…", width=8, command=lambda k=i: edit_details(k)).pack(side="left")
        ttk.Button(bb, text="AI Regen", width=8, command=lambda k=i: start_scene_regen(k)).pack(side="left", padx=2)
        pv = tk.StringVar(value="Purpose: " + BEAT_PURPOSE[i])
        ttk.Label(inner, textvariable=pv, style="Sub.TLabel", wraplength=820).grid(
            row=i * 2 + 1, column=2, columnspan=4, sticky="w", padx=3)
        beat_widgets.append((tc, tv, sv, at, pv))

    beat_btns = ttk.Frame(t2)
    beat_btns.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-4)

    def set_beat_row(i, b):
        _, tv, sv, at, _ = beat_widgets[i]
        tv.set(b.get("title", "")); sv.set(b.get("shot", ""))
        at.delete("1.0", "end"); at.insert("1.0", b.get("action", ""))
        beat_extra[i] = {k: b[k] for k in ("purpose", "visual", "camera", "lighting", "continuity", "weight")
                         if b.get(k) not in (None, "")}
        refresh_purpose(i)

    def refresh_purpose(i):
        ex = beat_extra[i]
        txt = "Purpose: " + (ex.get("purpose") or BEAT_PURPOSE[i])
        if ex.get("visual"):
            vis = ex["visual"]
            txt += "   ·   Draw: " + (vis if len(vis) < 140 else vis[:137] + "…")
        beat_widgets[i][4].set(txt)

    def reset_beats_to_template():
        if is_dirty() and not ui.askyesno("Reset beats", "Replace all 9 beats with the lesson template?\n"
                                                         "Your edits to the beats will be lost."):
            return
        for i, b in enumerate(TEMPLATE_BEATS):
            set_beat_row(i, b)
        refresh_timecodes()
    ttk.Button(beat_btns, text="Reset beats to lesson template", command=reset_beats_to_template).pack()

    def refresh_timecodes(*_):
        d = get_duration()
        if d is None:
            for w in beat_widgets:
                w[0].configure(text="(invalid)")
            return
        weights = [beat_extra[i].get("weight") for i in range(9)]
        codes = compute_timecodes(d, weights if all(isinstance(w, (int, float)) for w in weights) else None)
        for (tc, *_), code in zip(beat_widgets, codes):
            tc.configure(text=code)
    v_duration.trace_add("write", refresh_timecodes)

    def edit_details(i):
        win = tk.Toplevel(root)
        win.title(f"Beat {i + 1} details")
        win.transient(root)
        frm = ttk.Frame(win, padding=12)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(1, weight=1)
        ex = dict(beat_extra[i])
        fields = [("purpose", "Narrative purpose", 2), ("visual", "Visual description (what to draw)", 5),
                  ("camera", "Camera framing / angle", 2), ("lighting", "Lighting & atmosphere", 2),
                  ("continuity", "Continuity notes", 2)]
        boxes = {}
        for r, (k, label, h) in enumerate(fields):
            ttk.Label(frm, text=label, style="Bold.TLabel").grid(row=r, column=0, sticky="nw", pady=3, padx=(0, 8))
            t = tk.Text(frm, height=h, width=70, wrap="word", font=("Segoe UI", 10))
            t.insert("1.0", ex.get(k, ""))
            t.grid(row=r, column=1, sticky="ew", pady=3)
            boxes[k] = t
        ttk.Label(frm, text="Pacing weight", style="Bold.TLabel").grid(row=len(fields), column=0, sticky="w")
        v_w = tk.StringVar(value="" if ex.get("weight") is None else str(ex["weight"]))
        ttk.Entry(frm, textvariable=v_w, width=8).grid(row=len(fields), column=1, sticky="w")
        ttk.Label(frm, text="Relative screen time (1.0 = average). Leave empty on all beats to use lesson timing.",
                  style="Sub.TLabel").grid(row=len(fields) + 1, column=1, sticky="w")

        def ok():
            new = {k: boxes[k].get("1.0", "end").strip() for k in boxes}
            new = {k: v for k, v in new.items() if v}
            w = v_w.get().strip()
            if w:
                try:
                    wf = float(w)
                    assert wf > 0
                    new["weight"] = wf
                except (ValueError, AssertionError):
                    ui.showerror("Pacing weight", "Pacing weight must be a positive number.", parent=win)
                    return
            beat_extra[i] = new
            refresh_purpose(i)
            refresh_timecodes()
            win.destroy()
        br = ttk.Frame(frm)
        br.grid(row=len(fields) + 2, column=1, sticky="e", pady=(8, 0))
        ttk.Button(br, text="Cancel", command=win.destroy).pack(side="right")
        ttk.Button(br, text="Save", style="Accent.TButton", command=ok).pack(side="right", padx=6)

    # ================= Tab 3: Continuity & Style =================
    t3 = ttk.Frame(nb, padding=14)
    nb.add(t3, text="  3 · Continuity & Style  ")
    t3.columnconfigure(0, weight=1)
    t3.columnconfigure(1, weight=1)
    ttk.Label(t3, text="Preserve across all 9 panels (the main rule: only the story progresses)",
              style="Bold.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
    pf = ttk.Frame(t3)
    pf.grid(row=1, column=0, columnspan=2, sticky="w", pady=6)
    for k, item in enumerate(PRESERVE_ITEMS):
        ttk.Checkbutton(pf, text=item, variable=preserve_vars[item]).grid(row=k // 4, column=k % 4, sticky="w", padx=8, pady=2)

    ttk.Label(t3, text="Fixed attributes — AI storyboards (one per line)", style="Bold.TLabel").grid(
        row=2, column=0, sticky="w", pady=(6, 0))
    ttk.Label(t3, text="Intentional changes — allowed progression (attribute: from -> to (panels))",
              style="Bold.TLabel").grid(row=2, column=1, sticky="w", pady=(6, 0), padx=(8, 0))
    txt_fixed = tk.Text(t3, height=5, wrap="word", font=("Segoe UI", 9))
    txt_fixed.grid(row=3, column=0, sticky="ew", pady=4)
    txt_changes = tk.Text(t3, height=5, wrap="word", font=("Segoe UI", 9))
    txt_changes.grid(row=3, column=1, sticky="ew", pady=4, padx=(8, 0))

    ttk.Label(t3, text="Visual style notes (optional, e.g. 'anamorphic 2.39:1 feel, warm golden-hour grading')",
              style="Bold.TLabel").grid(row=4, column=0, columnspan=2, sticky="w", pady=(10, 0))
    txt_style = tk.Text(t3, height=3, wrap="word", font=("Segoe UI", 10))
    txt_style.grid(row=5, column=0, columnspan=2, sticky="ew", pady=4)

    ttk.Checkbutton(t3, text="Black borders between panels (professional storyboard look)",
                    variable=v_borders).grid(row=6, column=0, sticky="w", pady=4)

    ttk.Label(t3, text="Avoid list (negative prompt; leave empty for none)", style="Bold.TLabel").grid(
        row=7, column=0, columnspan=2, sticky="w", pady=(10, 0))
    txt_avoid = tk.Text(t3, height=4, wrap="word", font=("Segoe UI", 10))
    txt_avoid.grid(row=8, column=0, columnspan=2, sticky="ew", pady=4)
    ttk.Button(t3, text="Restore lesson avoid list",
               command=lambda: (txt_avoid.delete("1.0", "end"), txt_avoid.insert("1.0", AVOID_DEFAULT))).grid(row=9, column=0, sticky="w")

    ttk.Label(t3, text="Extra instructions (optional, added before the avoid list)",
              style="Bold.TLabel").grid(row=10, column=0, columnspan=2, sticky="w", pady=(10, 0))
    txt_extra = tk.Text(t3, height=3, wrap="word", font=("Segoe UI", 10))
    txt_extra.grid(row=11, column=0, columnspan=2, sticky="ew", pady=4)

    # ================= Tab 4: Prompt =================
    t4 = ttk.Frame(nb, padding=10)
    nb.add(t4, text="  4 · Prompt  ")
    bar = ttk.Frame(t4)
    bar.pack(fill="x", pady=(0, 6))
    out = tk.Text(t4, wrap="word", font=("Consolas", 10), background="#FBF7F1", undo=True)
    osb = ttk.Scrollbar(t4, orient="vertical", command=out.yview)
    out.configure(yscrollcommand=osb.set)
    out.pack(side="left", fill="both", expand=True)
    osb.pack(side="right", fill="y")
    v_count = tk.StringVar()
    ttk.Label(bar, textvariable=v_count, style="Sub.TLabel").pack(side="right")
    ttk.Combobox(bar, textvariable=v_pmode, values=list(PROMPT_MODES.values()), state="readonly",
                 width=34).pack(side="right", padx=6)

    # ================= Tab 5: Lesson guide =================
    t5 = ttk.Frame(nb, padding=10)
    nb.add(t5, text="  Lesson Guide  ")
    g = tk.Text(t5, wrap="word", font=("Consolas", 10), background="#FFFDF9")
    g.insert("1.0", LESSON_GUIDE)
    g.configure(state="disabled")
    g.pack(fill="both", expand=True)

    # ---- cfg <-> widgets
    def collect_cfg():
        beats = []
        for i, (_, tv, sv, at, _) in enumerate(beat_widgets):
            b = {"title": tv.get(), "shot": sv.get(), "action": at.get("1.0", "end").strip()}
            b.update(beat_extra[i])
            beats.append(b)
        d = get_duration()
        c = {"story_title": v_title.get(), "duration": d if d is not None else v_duration_raw(),
             "model": v_model.get(), "ref_mode": v_ref.get(), "character_desc": txt_desc.get("1.0", "end").strip(),
             "concept": txt_concept.get("1.0", "end").strip(), "beats": beats,
             "preserve": [k for k in PRESERVE_ITEMS if preserve_vars[k].get()],
             "avoid": txt_avoid.get("1.0", "end").strip(), "style_notes": txt_style.get("1.0", "end").strip(),
             "borders": v_borders.get(), "extra_notes": txt_extra.get("1.0", "end").strip(),
             "mode": state["mode"], "story": deepcopy(state["story"]), "ai": deepcopy(state["ai"]),
             "reference_roles": [k for k, v in role_vars.items() if v.get()] if v_ref.get() == "image" else [],
             "prompt_mode": prompt_mode()}
        if c["story"] is not None:
            c["story"].setdefault("continuity", {})
            c["story"]["continuity"]["fixed_attributes"] = [
                ln.strip().lstrip("•-* ").strip() for ln in txt_fixed.get("1.0", "end").splitlines() if ln.strip()]
            c["story"]["continuity"]["intentional_changes"] = _parse_changes(txt_changes.get("1.0", "end"))
            c["story"]["title"] = c["story_title"]
        return c

    def v_duration_raw():
        try:
            return root.globalgetvar(str(v_duration))
        except tk.TclError:
            return ""

    def set_text(w, val):
        prev = str(w.cget("state"))
        w.configure(state="normal"); w.delete("1.0", "end"); w.insert("1.0", val or ""); w.configure(state=prev)

    def comparable(c):
        return json.dumps({k: c.get(k) for k in ("story_title", "duration", "ref_mode", "character_desc", "concept",
                                                 "beats", "preserve", "avoid", "style_notes", "extra_notes", "story",
                                                 "reference_roles")},
                          sort_keys=True, ensure_ascii=False, default=str)

    def is_dirty():
        return state["baseline"] is not None and comparable(collect_cfg()) != state["baseline"]

    def load_cfg(c):
        state["mode"] = c.get("mode") if c.get("mode") == "ai" and isinstance(c.get("story"), dict) else "manual"
        state["story"] = deepcopy(c.get("story")) if state["mode"] == "ai" else None
        state["ai"] = deepcopy(c.get("ai")) if isinstance(c.get("ai"), dict) else None
        v_title.set(c.get("story_title", "")); v_duration.set(int(c.get("duration", 15)))
        v_model.set(c.get("model", "Seedance 2.0")); v_ref.set(c.get("ref_mode", "image"))
        roles = c.get("reference_roles")
        if roles is None and c.get("ref_mode", "image") == "image" and state["mode"] == "manual":
            roles = ["character"]  # presets / v1 projects: the lesson's character image
        for k, v in role_vars.items():
            v.set(k in (roles or []))
        if c.get("prompt_mode") in PROMPT_MODES:
            v_pmode.set(PROMPT_MODES[c["prompt_mode"]])
        v_borders.set(c.get("borders", True))
        set_text(txt_desc, c.get("character_desc", "")); set_text(txt_concept, c.get("concept", ""))
        set_text(txt_style, c.get("style_notes", ""))
        set_text(txt_avoid, AVOID_DEFAULT if c.get("avoid") is None else c.get("avoid"))
        set_text(txt_extra, c.get("extra_notes", ""))
        cont = (state["story"] or {}).get("continuity") or {}
        set_text(txt_fixed, "\n".join(cont.get("fixed_attributes") or []))
        set_text(txt_changes, _format_changes(cont.get("intentional_changes")))
        keep = set(PRESERVE_ITEMS if c.get("preserve") is None else c["preserve"])
        for k, v in preserve_vars.items():
            v.set(k in keep)
        for i, b in enumerate(c["beats"]):
            set_beat_row(i, b)
        toggle_desc(); refresh_timecodes(); refresh_mode_label()
        state["baseline"] = comparable(collect_cfg())

    def load_preset():
        if is_dirty() and not ui.askyesno("Load preset", "Loading a preset replaces your current storyboard.\n"
                                                         "Unsaved edits will be lost. Continue?"):
            return
        load_cfg(default_cfg(v_preset.get()))
        status.set(f"Loaded preset: {v_preset.get()}")

    def checked_cfg():
        """Current cfg after deterministic validation; None (with an error dialog) if invalid."""
        c = collect_cfg()
        rep = validate_cfg(c)
        if not rep.ok:
            ui.showerror("Storyboard is not valid", "Please fix:\n\n" + "\n".join("• " + e for e in rep.errors))
            return None, rep
        return c, rep

    def generate(switch=True):
        c, rep = checked_cfg()
        if c is None:
            return None
        if not c["preserve"] and not ((c.get("story") or {}).get("continuity") or {}).get("fixed_attributes"):
            if not ui.askyesno("Continuity", "No continuity items are selected - continuity is the main rule.\n"
                                             "Generate the prompt without a preserve list?"):
                return None
        try:
            text = build_prompt(c, prompt_mode())
        except (ValueError, TimingError) as e:
            ui.showerror("Generate prompt", str(e))
            return None
        out.delete("1.0", "end"); out.insert("1.0", text)
        out.edit_reset()
        state["last_generated"] = text
        v_count.set(f"{len(text.split())} words · {len(text)} characters")
        status.set("Prompt generated." + (f"  ⚠ {len(rep.warnings)} warning(s): " + rep.warnings[0]
                                           if rep.warnings else ""))
        if switch:
            nb.select(t4)
        return text

    def prompt_mode():
        return MODE_KEYS.get(v_pmode.get(), "image")

    def hand_edited():
        shown = out.get("1.0", "end").strip()
        return bool(shown) and shown != (state["last_generated"] or "").strip()

    def refresh_prompt(_e=None):
        """Live view: rebuild the prompt from the current state unless the user hand-edited it.
        Silent (no dialogs); invalid storyboards simply keep the last prompt."""
        if hand_edited():
            return None
        c = collect_cfg()
        if not validate_cfg(c).ok:
            return None
        try:
            text = build_prompt(c, prompt_mode())
        except (ValueError, TimingError):
            return None
        if text != out.get("1.0", "end").strip():
            out.delete("1.0", "end"); out.insert("1.0", text); out.edit_reset()
        state["last_generated"] = text
        v_count.set(f"{len(text.split())} words · {len(text)} characters")
        return text

    def on_tab(_e=None):
        if nb.select() == str(t4):
            refresh_prompt()

    def copy_prompt():
        shown = out.get("1.0", "end").strip()
        text = None
        if shown and state["last_generated"] and shown != state["last_generated"].strip():
            ans = ui.askyesnocancel("Copy prompt", "The prompt text was edited by hand.\n\n"
                                                   "Yes = copy your hand-edited text\n"
                                                   "No = regenerate from the current storyboard and copy that")
            if ans is None:
                return None
            if ans:
                text = shown
        if text is None:
            text = generate(switch=False)  # always fresh: reflects every edit made since the last generate
        if text:
            root.clipboard_clear(); root.clipboard_append(text)
            status.set("Prompt copied. Upload your reference image in ChatGPT, then paste.")
        return text

    def safe_name():
        name = (v_title.get().strip() or "storyboard").replace(" ", "_")
        return "".join(ch for ch in name if ch.isalnum() or ch in "_-") or "storyboard"

    def save_txt():
        text = generate(switch=False)
        if not text: return
        f = ui.asksave(defaultextension=".txt", initialfile=safe_name() + "_prompt.txt",
                       filetypes=[("Text", "*.txt")])
        if f:
            with open(f, "w", encoding="utf-8") as fh:
                fh.write(text)
            status.set(f"Saved prompt: {f}")

    def save_md():
        if not generate(switch=False): return
        f = ui.asksave(defaultextension=".md", initialfile=safe_name() + "_storyboard_plan.md",
                       filetypes=[("Markdown", "*.md")])
        if f:
            with open(f, "w", encoding="utf-8") as fh:
                fh.write(build_beat_sheet_md(collect_cfg(), v_title.get() or "Storyboard"))
            status.set(f"Saved beat sheet: {f}")

    def save_story(path=None):
        c, _ = checked_cfg()
        if c is None:
            return None
        f = path or ui.asksave(defaultextension=".json", initialfile=safe_name() + ".json",
                               filetypes=[("Story file", "*.json")])
        if not f:
            return None
        shown = out.get("1.0", "end").strip()
        try:
            # never save a stale prompt: rebuild from the current state unless the user hand-edited it
            final = shown if (hand_edited() and prompt_mode() == "image") else build_prompt(c, "image")
            director = shown if (hand_edited() and prompt_mode() == "director") else build_prompt(c, "director")
            save_project(c, f, final_prompt=final, director_prompt=director)
        except (OSError, ValueError) as e:
            ui.showerror("Save project", f"Could not save the project:\n{e}")
            return None
        state["baseline"] = comparable(c)
        status.set(f"Saved project: {f}")
        return f

    def open_story(path=None):
        if is_dirty() and not ui.askyesno("Open project", "Opening a project replaces your current storyboard.\n"
                                                          "Unsaved edits will be lost. Continue?"):
            return None
        f = path or ui.askopen(filetypes=[("Story file", "*.json")])
        if not f:
            return None
        try:
            c = load_project(f)
        except ProjectError as e:
            ui.showerror("Open project", f"Could not load this file:\n{e}")
            return None
        load_cfg(c)
        ai = c.get("ai") or {}
        if ai.get("original_message"):
            set_text(txt_msg, ai["original_message"]); on_msg_key()
            state["last_message"] = ai["original_message"]
            state["last_settings"] = ai.get("settings")
        fresh = build_prompt(c, prompt_mode())
        out.delete("1.0", "end"); out.insert("1.0", fresh)  # always compiled from the loaded state
        state["last_generated"] = fresh
        if c.get("migrated_from"):
            status.set(f"Project upgraded from schema v{c['migrated_from']}.")
        show_result(describe_ai(c) if c.get("mode") == "ai" else "Loaded a manual (non-AI) storyboard project.")
        status.set(f"Loaded project: {f}")
        return c

    # ---- AI actions (worker thread + polling, the Tk main loop never blocks)
    action_buttons = [btn_gen, btn_regen, btn_scene]

    def collect_settings():
        return {"story_type": _story_type_key(v_story_type.get()), "duration": get_duration(),
                "visual_style": v_vstyle.get().strip() or "Automatic", "audience": v_audience.get().strip(),
                "subject_desc": txt_subject.get("1.0", "end").strip(), "ref_mode": v_ref.get(),
                "reference_roles": [k for k, v in role_vars.items() if v.get()] if v_ref.get() == "image" else [],
                "output_language": "same" if v_lang.get() == LANG_OPTIONS[1] else "en",
                "model": v_model.get().strip() or "Seedance 2.0"}

    def make_provider():
        if provider_factory is not None:
            return provider_factory()
        return OpenAIProvider(model=v_ai_model.get().strip() or None)

    def set_busy(busy, label=""):
        state["busy"] = busy
        for b in action_buttons:
            b.configure(state="disabled" if busy else "normal")
        btn_cancel.configure(state="normal" if busy else "disabled")
        if busy:
            prog.start(12); v_prog.set(label)
        else:
            prog.stop(); v_prog.set(label)

    def run_task(label, work, on_done):
        q = queue.Queue()
        cancel = threading.Event()
        state["cancel"] = cancel

        def progress(msg):
            q.put(("progress", msg))

        def worker():
            try:
                q.put(("done", work(progress, cancel)))
            except BaseException as e:  # reported in the UI thread
                q.put(("error", e))

        def poll():
            try:
                while True:
                    kind, payload = q.get_nowait()
                    if kind == "progress":
                        v_prog.set(payload)
                        continue
                    if cancel.is_set():
                        set_busy(False, "Cancelled — nothing was changed.")
                        return
                    set_busy(False, "")
                    if kind == "error":
                        report_error(payload)
                    else:
                        on_done(payload)
                    return
            except queue.Empty:
                pass
            root.after(100, poll)

        set_busy(True, label)
        threading.Thread(target=worker, daemon=True).start()
        root.after(100, poll)

    def cancel_task():
        if state["cancel"] is not None:
            state["cancel"].set()
            v_prog.set("Cancelling… (the current request will be discarded)")

    def report_error(e):
        if isinstance(e, InputError):
            ui.showwarning("AI Story Director", str(e))
        elif isinstance(e, AIProviderError):
            if e.kind != "cancelled":
                ui.showerror("AI Story Director", e.user_message() + "\n\nYour project was not changed.")
        elif isinstance(e, StoryboardGenerationError):
            ui.showerror("AI Story Director", e.user_message())
        elif isinstance(e, TimingError):
            ui.showerror("AI Story Director", str(e))
        else:
            ui.showerror("AI Story Director", f"Unexpected error: {type(e).__name__}: {e}\n\nYour project was not changed.")
        status.set("AI generation failed — your project was not changed.")

    def describe_ai(c, result=None):
        ai = c.get("ai") or {}
        st = c.get("story") or {}
        brief = ai.get("brief") or {}
        lines = [f"STORY: {c.get('story_title', '')}   ·   type: "
                 f"{STORY_TYPES.get(st.get('story_type'), (st.get('story_type', '?'),))[0]}   ·   "
                 f"{c.get('duration')} s   ·   model: {ai.get('model', '?')}",
                 f"Core message: {st.get('core_message', '')}",
                 f"Viewer takeaway: {st.get('viewer_takeaway', '')}",
                 f"Structure: {' → '.join(st.get('narrative_structure') or [])}"]
        if brief.get("creative_decisions"):
            lines.append("AI creative decisions: " + "; ".join(brief["creative_decisions"]))
        if brief.get("factual_cautions"):
            lines.append("Factual cautions: " + "; ".join(brief["factual_cautions"]))
        lines.append("")
        val = ai.get("validation") or {}
        lines.append("DETERMINISTIC CHECKS: " + ("PASSED" if not val.get("errors") else "FAILED"))
        lines += [f"  ! {w}" for w in val.get("warnings") or []]
        vc = validate_cfg(c)
        lines += [f"  ! {w}" for w in vc.warnings]
        if vc.notes:
            lines.append("PROMPT CONSISTENCY (resolved automatically):")
            lines += [f"  ✓ {n}" for n in vc.notes]
        lines.append("")
        if ai.get("review"):
            lines.append(review_text(ai["review"]))
        elif result is not None and result.review_error:
            lines.append(f"AI creative review unavailable: {result.review_error}")
        lines.append("\nNext: review the 1 · Story and 2 · 9 Beats tabs, edit anything, then Generate final prompt.")
        return "\n".join(lines)

    def start_ai_generation(regen=False):
        if state["busy"]:
            return
        if regen and state["last_message"]:
            message, settings = state["last_message"], dict(state["last_settings"] or collect_settings())
            settings["duration"] = get_duration() or settings.get("duration")
        else:
            message, settings = txt_msg.get("1.0", "end").strip(), collect_settings()
        if not message:
            ui.showwarning("AI Story Director", "Please type the message or story you want to communicate.")
            return
        if settings["duration"] is None:
            ui.showwarning("AI Story Director", f"Duration must be {MIN_DURATION}-{MAX_DURATION} seconds.")
            return
        try:
            normalize_settings(settings)
        except InputError as e:
            ui.showwarning("AI Story Director", str(e))
            return
        try:
            provider = make_provider()
        except AIProviderError as e:
            ui.showerror("AI Story Director", e.user_message() + "\n\nManual mode (tabs 1-4) works without an API key.")
            return
        if is_dirty() and not ui.askyesno("Replace storyboard?",
                                          "Generating a new AI storyboard will replace your current story and beats.\n"
                                          "Unsaved edits will be lost (save the project first if needed).\n\nContinue?"):
            return
        before = comparable(collect_cfg())
        base = collect_cfg()
        run_review = v_review.get()

        def work(progress, cancel):
            d = StoryDirector(provider, run_review=run_review, progress=progress, cancel_event=cancel)
            return d.generate(message, settings, base_cfg=base)

        def done(result):
            if comparable(collect_cfg()) != before and not ui.askyesno(
                    "Apply AI storyboard?", "You edited the storyboard while the AI was working.\n"
                                            "Replace it with the new AI storyboard?"):
                status.set("AI storyboard discarded; your edits were kept.")
                return
            load_cfg(result.cfg)
            state["last_message"], state["last_settings"] = message, result.cfg["ai"]["settings"]
            out.delete("1.0", "end"); state["last_generated"] = ""
            show_result(describe_ai(result.cfg, result))
            status.set("AI storyboard ready — review/edit the Story and 9 Beats tabs, then Generate final prompt.")
        run_task("Starting AI Story Director…", work, done)

    def start_scene_regen(index):
        if state["busy"]:
            return
        c, _ = checked_cfg()
        if c is None:
            return
        try:
            provider = make_provider()
        except AIProviderError as e:
            ui.showerror("Regenerate scene", e.user_message())
            return
        base_beats = json.loads(state["baseline"])["beats"] if state["baseline"] else None
        edited = base_beats is not None and json.dumps(base_beats[index], sort_keys=True) != \
            json.dumps(c["beats"][index], sort_keys=True)
        msg = f"Replace scene {index + 1} with a newly generated version? All other scenes stay unchanged."
        if edited:
            msg += "\n\nYou edited this scene — those edits will be replaced."
        if not ui.askyesno("Regenerate scene", msg):
            return
        note = v_scene_note.get().strip()
        settings = dict(state["last_settings"] or collect_settings())
        settings["duration"] = c["duration"]

        def work(progress, cancel):
            d = StoryDirector(provider, progress=progress, cancel_event=cancel)
            return d.regenerate_scene(c, index, note, settings)

        def done(new_cfg):
            nbeat = new_cfg["beats"][index]
            set_beat_row(index, nbeat)
            refresh_timecodes()
            if state["ai"] is not None and new_cfg.get("ai"):
                state["ai"]["generated_beats"] = new_cfg["ai"].get("generated_beats")
            if state["baseline"]:  # the regenerated scene counts as a fresh (unedited) AI scene
                bl = json.loads(state["baseline"])
                bl["beats"][index] = collect_cfg()["beats"][index]
                state["baseline"] = json.dumps(bl, sort_keys=True, ensure_ascii=False, default=str)
            status.set(f"Scene {index + 1} regenerated. Other scenes were not changed.")
            nb.select(t2)
        run_task(f"Regenerating scene {index + 1}…", work, done)

    ttk.Button(bar, text="Generate", style="Accent.TButton", command=generate).pack(side="left")
    ttk.Button(bar, text="Copy to clipboard", command=copy_prompt).pack(side="left", padx=4)
    ttk.Button(bar, text="Save prompt .txt", command=save_txt).pack(side="left", padx=4)
    ttk.Button(bar, text="Save beat sheet .md", command=save_md).pack(side="left", padx=4)

    # ---- bottom bar
    bottom = ttk.Frame(root, padding=(12, 4, 12, 10))
    bottom.pack(side="bottom", fill="x")
    nb.pack(fill="both", expand=True, padx=10, pady=6)
    ttk.Button(bottom, text="Generate prompt  ->", style="Accent.TButton", command=generate).pack(side="right")
    ttk.Button(bottom, text="Copy", command=copy_prompt).pack(side="right", padx=6)
    ttk.Button(bottom, text="Open story...", command=open_story).pack(side="left")
    ttk.Button(bottom, text="Save story...", command=save_story).pack(side="left", padx=6)
    ttk.Label(bottom, textvariable=status, style="Sub.TLabel").pack(side="left", padx=12)

    nb.bind("<<NotebookTabChanged>>", on_tab)
    v_pmode.trace_add("write", lambda *_: refresh_prompt())
    load_cfg(default_cfg(v_preset.get()))
    on_msg_key()

    return SimpleNamespace(**{k: v for k, v in locals().items() if not k.startswith("_")})


def run_gui():
    import tkinter as tk
    root = tk.Tk()
    build_app(root)
    root.mainloop()


# --------------------------------------------------------------------------
# Entry
# --------------------------------------------------------------------------

def _cli_ai(a):
    from storyboard_ai.ai_provider import AIProviderError, OpenAIProvider
    from storyboard_ai.director import StoryDirector
    from storyboard_ai.project_io import save_project
    from storyboard_ai.story_interpreter import InputError
    from storyboard_ai.storyboard_planner import StoryboardGenerationError
    from storyboard_ai.storyboard_validator import review_text
    settings = {"story_type": a.story_type, "duration": a.duration, "visual_style": a.style or "Automatic",
                "audience": a.audience or "", "subject_desc": a.subject or "",
                "ref_mode": a.ref or ("image" if a.ref_role else "text"), "reference_roles": a.ref_role or [],
                "output_language": a.lang, "model": a.video_model}
    try:
        director = StoryDirector(OpenAIProvider(model=a.ai_model), run_review=not a.no_review,
                                 progress=lambda m: print(m, file=sys.stderr))
        result = director.generate(a.ai, settings, base_cfg=default_cfg())
    except InputError as e:
        sys.exit(f"Input error: {e}")
    except AIProviderError as e:
        sys.exit(f"AI error: {e.user_message()}")
    except StoryboardGenerationError as e:
        sys.exit(f"Generation failed: {e.user_message()}")
    cfg = result.cfg
    text = build_prompt(cfg, a.mode)
    if result.report and result.report.warnings:
        print("\n".join("warning: " + w for w in result.report.warnings), file=sys.stderr)
    if result.review:
        print(review_text(result.review), file=sys.stderr)
    if a.save:
        save_project(cfg, a.save, final_prompt=build_prompt(cfg, "image"),
                     director_prompt=build_prompt(cfg, "director"))
        print(f"Saved project: {a.save}", file=sys.stderr)
    print(build_beat_sheet_md(cfg, cfg["story_title"]) if a.md else text)


def main(argv=None):
    ap = argparse.ArgumentParser(description=APP_TITLE)
    ap.add_argument("--list", action="store_true", help="list story presets")
    ap.add_argument("--preset", help="print the prompt for a preset (no GUI)")
    ap.add_argument("--duration", type=int, default=15, help=f"video length in seconds ({MIN_DURATION}-{MAX_DURATION})")
    ap.add_argument("--md", action="store_true", help="print a markdown beat sheet instead")
    ap.add_argument("--project", help="print the prompt of a saved project .json (no GUI)")
    ap.add_argument("--ai", metavar="MESSAGE", help="generate an AI storyboard from a message (needs OPENAI_API_KEY)")
    ap.add_argument("--story-type", default="auto", choices=["auto"] + list(STORY_TYPES))
    ap.add_argument("--style", help="visual style for --ai")
    ap.add_argument("--audience", help="target audience for --ai")
    ap.add_argument("--subject", help="character/product description to preserve for --ai")
    ap.add_argument("--ref", choices=["image", "text"],
                    help="reference image mode for --ai (default: image if --ref-role is given, else text)")
    ap.add_argument("--ref-role", action="append", choices=list(REFERENCE_ROLES),
                    help="what the uploaded reference image shows (repeatable), e.g. --ref-role character")
    ap.add_argument("--mode", default="image", choices=list(PROMPT_MODES),
                    help="image = optimized image-generation prompt; director = detailed director's storyboard")
    ap.add_argument("--lang", default="en", choices=["en", "same"], help="storyboard language for --ai")
    ap.add_argument("--video-model", default="Seedance 2.0", help="target video model named in the prompt")
    ap.add_argument("--ai-model", help="story-planning LLM (default: STORYBOARD_AI_MODEL or gpt-5-mini)")
    ap.add_argument("--no-review", action="store_true", help="skip the optional AI creative review")
    ap.add_argument("--save", help="with --ai: save the generated project to this .json file")
    a = ap.parse_args(argv)
    try:
        check_duration(a.duration)
    except TimingError as e:
        ap.error(str(e))
    if a.list:
        print("\n".join(PRESETS)); return
    if a.preset:
        name = next((k for k in PRESETS if k.lower().startswith(a.preset.lower())), None)
        if not name:
            sys.exit(f"Unknown preset. Options:\n" + "\n".join(PRESETS))
        c = default_cfg(name); c["duration"] = a.duration
        print(build_beat_sheet_md(c, c["story_title"]) if a.md else build_prompt(c, a.mode)); return
    if a.project:
        from storyboard_ai.project_io import ProjectError, load_project
        try:
            c = load_project(a.project)
        except ProjectError as e:
            sys.exit(f"Could not load project: {e}")
        print(build_beat_sheet_md(c, c["story_title"] or "Storyboard") if a.md else build_prompt(c, a.mode)); return
    if a.ai:
        _cli_ai(a); return
    try:
        run_gui()
    except ImportError:
        sys.exit("tkinter is not available. On Linux: sudo apt install python3-tk  "
                 "(Windows/macOS python.org installers include it). Or use --preset for CLI mode.")


if __name__ == "__main__":
    main()

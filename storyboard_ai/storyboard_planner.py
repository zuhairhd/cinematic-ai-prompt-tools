"""Storyboard Planner: creative brief -> nine structured cinematic beats (with bounded repair)."""

import json

from .ai_provider import AIProviderError
from .constants import STORY_TYPES
from .schema import BEAT_SCHEMA, STORYBOARD_SCHEMA, validate
from .storyboard_validator import validate_storyboard, validate_beat

MAX_REPAIRS = 2


class StoryboardGenerationError(Exception):
    """Generation failed after bounded retries. Never falls back to the generic template."""

    def __init__(self, message, errors=None):
        super().__init__(message)
        self.errors = list(errors or [])

    def user_message(self):
        detail = "\n".join(f"  • {e}" for e in self.errors[:12])
        more = f"\n  … and {len(self.errors) - 12} more" if len(self.errors) > 12 else ""
        return f"{self}\n\n{detail}{more}".strip()


SYSTEM = """You are a professional cinematic storyboard director. You design 9-panel timed storyboards
(3x3 grid) that an AI image model will draw as one storyboard sheet, and that later guide a video.

Your storyboard must COMMUNICATE THE USER'S MESSAGE. Every panel must earn its place in the story.

Narrative structure: choose stages that fit the story type. Guidelines (adapt, don't copy blindly):
{structures}

Panel rules:
- Exactly 9 beats, panel numbers 1-9 in chronological order, connected cause -> effect.
- Vary shot sizes and angles purposefully (establishing, medium, close-up, detail, reaction, payoff).
  Never repeat the same shot type + camera angle in consecutive panels.
- visual_description: concrete, renderable details (subjects, positions, props, textures, background,
  expressions). No vague words like "something", "epic scene", "beautiful moment" without specifics.
- action: one short, present-tense, motion-ready line (max ~18 words). This text is printed on the panel.
- title: 1-5 words, UPPERCASE.
- No unnecessary visual effects, no unrelated cinematic elements, no on-screen text except a brief
  call to action or product name when the story type truly needs it.
- relative_weight: relative screen time (1.0 = average; use 0.6-2.5). Give key moments and the
  ending more time. Python converts weights into exact timecodes; do not write timecodes.
- Panel 9 must land the message with a meaningful, visually clear ending.
- Commit to ONE concrete choice per panel. Never offer alternatives ("X or Y", "choose whichever",
  "either ... or"): the image model cannot choose consistently.
- This is a still-image storyboard: describe only what is visible. No sound, music, dialogue or
  voice-over descriptions.
- The avoid list is for the drawn image content. Never put panel numbers, timecodes, shot titles,
  captions or "on-screen text/titles" in it: each panel must show its number, timecode, title and
  action line.

Continuity:
- character/product/environment: specific, consistent descriptions. If the user supplied a
  character or product description, copy its details faithfully (same name, colors, features).
- If there is no person in the story, set character.present=false and do not add one.
- continuity.fixed_attributes: everything that must stay identical (identity, outfit, product design,
  location, style, ...), at least 3 items, specific.
- continuity.intentional_changes: deliberate story-driven evolutions (e.g. lighting from storm to
  sunrise, expression from despair to hope). Only list real changes the panels show; anything
  not listed is assumed fixed.

Factual safety: do not invent facts, endorsements, statistics or claims about real people, brands,
products or events.

{language_rule}"""


def _structures():
    return "\n".join(f"  - {k} ({label}): {guide}" for k, (label, guide) in STORY_TYPES.items())


def _language_rule(settings, brief):
    lang = brief.get("detected_language") or "en"
    if settings.get("output_language") == "same" and lang == "ar":
        return ("Language: write title, action, concept and all descriptions in Arabic (the user's language). "
                "Keep JSON keys and enum values in English.")
    return "Language: write all storyboard text in English (image models render English captions most reliably)."


def build_plan_prompt(brief, message, settings):
    from .story_interpreter import brief_text
    parts = [
        f"ORIGINAL USER MESSAGE:\n<<<\n{message}\n>>>",
        f"CREATIVE BRIEF:\n{brief_text(brief)}",
        f"Video duration: {settings.get('duration', 15)} seconds. Target video model: {settings.get('model', 'Seedance 2.0')}.",
    ]
    if settings.get("story_type", "auto") != "auto":
        parts.append(f"Use story_type = {settings['story_type']} (selected by the user).")
    else:
        parts.append(f"Use story_type = {brief.get('story_type', 'general')} unless clearly wrong.")
    if settings.get("visual_style") and settings["visual_style"] != "Automatic":
        parts.append(f"Visual style (user choice, keep it): {settings['visual_style']}")
    if settings.get("audience"):
        parts.append(f"Target audience: {settings['audience']}")
    if settings.get("subject_desc"):
        parts.append("USER-SPECIFIED CHARACTER / PRODUCT (preserve every detail, do not rename or redesign):\n"
                     + settings["subject_desc"])
    if settings.get("ref_mode") == "image":
        parts.append("The user will upload a reference image of the main character/subject. Panels must "
                     "keep that exact identity; describe it as 'the character from the reference image' plus "
                     "any user-given details. Do not invent conflicting facial features.")
    return "\n\n".join(parts)


def _repair_prompt(base_prompt, previous, errors):
    prev = previous if isinstance(previous, str) else json.dumps(previous, ensure_ascii=False)
    return (base_prompt + "\n\nYOUR PREVIOUS ANSWER FAILED VALIDATION. Return a corrected, complete storyboard "
            "JSON that fixes every problem below while keeping the parts that were fine.\n"
            "Problems:\n" + "\n".join(f"- {e}" for e in errors[:30]) +
            "\n\nPrevious answer:\n" + prev[:20000])


def plan(provider, brief, message, settings, max_repairs=MAX_REPAIRS, progress=None):
    """Return (storyboard_dict, report). Raises StoryboardGenerationError after bounded retries."""
    system = SYSTEM.format(structures=_structures(), language_rule=_language_rule(settings, brief))
    base = build_plan_prompt(brief, message, settings)
    prompt, last_errors = base, []
    for attempt in range(max_repairs + 1):
        if attempt and progress:
            progress(f"Repairing storyboard (attempt {attempt + 1} of {max_repairs + 1})…")
        try:
            sb = provider.generate_json(system, prompt, STORYBOARD_SCHEMA, "storyboard")
        except AIProviderError as e:
            if e.kind != "bad_response":
                raise
            last_errors = [str(e)]
            prompt = _repair_prompt(base, "(unparseable output)", last_errors)
            continue
        errors = validate(sb, STORYBOARD_SCHEMA, "storyboard")
        report = None
        if not errors:
            report = validate_storyboard(sb, settings)
            errors = report.errors
        if not errors:
            return sb, report
        last_errors = errors
        prompt = _repair_prompt(base, sb, errors)
    raise StoryboardGenerationError(
        f"The AI storyboard did not pass validation after {max_repairs + 1} attempts. "
        "Nothing was changed in your project.", last_errors)


# ---------------------------------------------------------------- single-scene regeneration
SCENE_SYSTEM = """You are a professional cinematic storyboard director revising ONE panel of an approved
9-panel storyboard. Keep the overall story, message, character identity, product, world, visual style and
continuity exactly as given. Only redesign the requested panel so it connects smoothly with the panel
before and after it, avoids repeating their shot type/angle, and still fulfils its narrative purpose
(unless the user's note asks for a different purpose). Return only that one beat.
{language_rule}"""


def regenerate_scene(provider, storyboard, index, note="", settings=None, max_repairs=MAX_REPAIRS):
    """Return a new beat dict for panel index (0-based). Other beats are never modified."""
    settings = settings or {}
    if not 0 <= index < 9:
        raise ValueError("Scene index must be 0-8.")
    panel = index + 1
    ctx = {k: v for k, v in storyboard.items() if k not in ("beats",)}
    beats_ctx = []
    for i, b in enumerate(storyboard["beats"]):
        tag = "TO REGENERATE" if i == index else "APPROVED - do not change"
        beats_ctx.append({"status": tag, **b})
    prompt = (f"STORYBOARD CONTEXT:\n{json.dumps(ctx, ensure_ascii=False, indent=1)}\n\n"
              f"ALL PANELS:\n{json.dumps(beats_ctx, ensure_ascii=False, indent=1)}\n\n"
              f"Regenerate panel {panel} only. Set panel={panel}.")
    if note.strip():
        prompt += f"\n\nUser direction for the new panel: {note.strip()}"
    lang = {"detected_language": (storyboard.get("_language") or "en")}
    system = SCENE_SYSTEM.format(language_rule=_language_rule(settings, lang))
    base, last = prompt, []
    for attempt in range(max_repairs + 1):
        try:
            beat = provider.generate_json(system, prompt, BEAT_SCHEMA, "storyboard_beat")
        except AIProviderError as e:
            if e.kind != "bad_response":
                raise
            last = [str(e)]
            prompt = _repair_prompt(base, "(unparseable output)", last)
            continue
        if isinstance(beat, dict):
            beat["panel"] = panel
        errors = validate(beat, BEAT_SCHEMA, f"panel{panel}")
        if not errors:
            others = [b for i, b in enumerate(storyboard["beats"]) if i != index]
            errors = validate_beat(beat, panel, others)
        if not errors:
            return beat
        last = errors
        prompt = _repair_prompt(base, beat, errors)
    raise StoryboardGenerationError(
        f"Could not regenerate panel {panel} after {max_repairs + 1} attempts. The panel was left unchanged.", last)

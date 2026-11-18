"""Story Interpreter: user message (English or Arabic) -> structured creative brief."""

import json
import re

from .constants import STORY_TYPES
from .schema import BRIEF_SCHEMA, validate

_ARABIC = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]")
MAX_MESSAGE_CHARS = 6000


class InputError(ValueError):
    pass


def detect_language(text):
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return "unknown"
    arabic = sum(1 for c in letters if _ARABIC.match(c))
    return "ar" if arabic / len(letters) >= 0.3 else "en"


def check_message(message):
    msg = (message or "").strip()
    if not msg:
        raise InputError("Please describe the message or story you want to communicate.")
    if len(re.findall(r"\w+", msg)) < 3:
        raise InputError("Please write at least a short sentence (3+ words) so the AI understands your intent.")
    if len(msg) > MAX_MESSAGE_CHARS:
        raise InputError(f"The message is too long ({len(msg)} characters). Please keep it under "
                         f"{MAX_MESSAGE_CHARS} characters.")
    return msg


SYSTEM = """You are a senior creative director and story analyst for short cinematic videos.
You turn a user's simple message into a precise creative brief for a 9-panel timed storyboard.

Rules:
- Understand the INTENDED MESSAGE first; the story exists to communicate it.
- The user may write in Arabic or English. Understand it fully, but write the brief in English.
- Preserve every explicit user requirement (characters, products, places, style, audience, events) exactly.
  List them in explicit_requirements. Never replace a user-specified character or product.
- If details are missing, make confident, reasonable creative decisions and list them in creative_decisions.
  Do not ask questions.
- Do not invent factual claims about real people, real products, brands or real events. If they are
  mentioned, note in factual_cautions how to depict them without fabricated claims.
- Choose the story_type whose narrative approach best serves the message. Available types:
{types}
- Keep everything concrete and visual: things a camera can see."""


def build_user_prompt(message, settings):
    lines = [f"USER MESSAGE (original language preserved):\n<<<\n{message}\n>>>"]
    st = settings.get("story_type") or "auto"
    if st != "auto":
        lines.append(f"REQUIRED story_type: {st} (the user selected it manually).")
    if settings.get("audience"):
        lines.append(f"Target audience (from the user): {settings['audience']}")
    if settings.get("subject_desc"):
        lines.append("Character / product description supplied by the user (must be preserved exactly):\n"
                     f"{settings['subject_desc']}")
    if settings.get("visual_style") and settings["visual_style"] != "Automatic":
        lines.append(f"Visual style requested: {settings['visual_style']}")
    if settings.get("ref_mode") == "image":
        lines.append("The user will upload a reference image of the main character/subject in the image tool. "
                     "Do not contradict it; describe appearance only where the user gave details.")
    lines.append(f"Video length: {settings.get('duration', 15)} seconds, 9 storyboard panels.")
    return "\n\n".join(lines)


def interpret(provider, message, settings):
    """Return (brief, errors). The brief is validated against BRIEF_SCHEMA."""
    msg = check_message(message)
    types = "\n".join(f"  - {k}: {label} ({guide})" for k, (label, guide) in STORY_TYPES.items())
    brief = provider.generate_json(SYSTEM.format(types=types), build_user_prompt(msg, settings),
                                   BRIEF_SCHEMA, "creative_brief")
    errors = validate(brief, BRIEF_SCHEMA, "brief")
    st = settings.get("story_type") or "auto"
    if not errors and st != "auto" and brief.get("story_type") != st:
        brief["story_type"] = st  # manual selection wins
    brief["detected_language"] = detect_language(msg)
    return brief, errors


def brief_text(brief):
    return json.dumps({k: v for k, v in brief.items() if k != "detected_language"}, ensure_ascii=False, indent=1)

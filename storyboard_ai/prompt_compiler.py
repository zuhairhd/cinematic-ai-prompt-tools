"""Prompt compiler: validated, user-edited AI storyboard cfg -> final 3x3 storyboard image prompt.

Pure, deterministic Python (no AI calls). Keeps the lesson's output format (3x3 grid, 9 numbered,
timecoded, titled panels with one short action line) and adds the structured story, continuity
and per-panel direction. Intentional changes are stated explicitly so the continuity rules never
forbid the story's own progression.
"""

from .constants import STORY_TYPES
from .timing import compute_timecodes


def _sentence(s):
    s = (s or "").strip()
    return s if not s or s[-1] in ".!?" else s + "."


def _weights(beats):
    w = [b.get("weight") for b in beats]
    return w if len(w) == 9 and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in w) else None


def preserve_phrase(preserve):
    preserve = list(preserve)
    if len(preserve) == 1:
        return preserve[0]
    if len(preserve) == 2:
        return f"{preserve[0]} and {preserve[1]}"
    return ", ".join(preserve[:-1]) + ", and " + preserve[-1]


def compile_ai_prompt(cfg):
    beats = cfg.get("beats") or []
    if len(beats) != 9:
        raise ValueError(f"A storyboard needs exactly 9 beats (found {len(beats)}).")
    duration = int(cfg.get("duration", 15))
    model = (cfg.get("model") or "").strip() or "Seedance 2.0"
    tcs = compute_timecodes(duration, _weights(beats))
    use_image = cfg.get("ref_mode", "image") == "image"
    story = cfg.get("story") or {}
    ch, pr = story.get("character") or {}, story.get("product") or {}
    subject = "character" if ch.get("present", True) else ("product" if pr.get("present") else "subject")

    p = []
    basis = "based on the uploaded reference image" if use_image else "based on the descriptions below"
    p.append(f"Create a professional cinematic 3x3 timed storyboard for a {duration}-second {model} video "
             f"sequence {basis}.")
    p.append("The storyboard must look like a professional film pre-production board. It must contain exactly "
             "9 panels in a clean 3x3 grid, read in chronological order left to right, top to bottom "
             "(panels 1-3 top row, 4-6 middle row, 7-9 bottom row).")
    p.append("Each panel must include:\n• panel number\n• timecode\n• short cinematic shot title\n"
             "• one short action description\n"
             "Print only these four items as text on each panel. The shot, visual and lighting directions "
             "below describe what to draw; do not print them.")

    title = (cfg.get("story_title") or story.get("title") or "").strip()
    head = [f'Story: "{title}".' if title else ""]
    if story.get("core_message"):
        head.append(f"Core message: {_sentence(story['core_message'])}")
    if story.get("story_type") in STORY_TYPES:
        head.append(f"Story type: {STORY_TYPES[story['story_type']][0]}.")
    if story.get("emotional_goal"):
        head.append(f"Emotional journey: {_sentence(story['emotional_goal'])}")
    if story.get("viewer_takeaway"):
        head.append(f"The final panel must leave the viewer with this idea: {_sentence(story['viewer_takeaway'])}")
    head = " ".join(h for h in head if h)
    if head:
        p.append(head)

    preserve = cfg.get("preserve")
    if preserve is None:
        preserve = []
    desc = (cfg.get("character_desc") or "").strip()
    if use_image:
        p.append(f"Use the uploaded image as the main {subject} reference.")
        if preserve:
            p.append(f"Preserve the same {preserve_phrase(preserve)} from the uploaded image.")
        if desc:
            p.append(f"Character and world notes (the uploaded image takes priority if anything differs):\n{desc}")
    else:
        p.append(f"Main character and world:\n{desc or '[describe your character, outfit and world here]'}")
        if preserve:
            p.append(f"Keep the same {preserve_phrase(preserve)} in every panel.")

    if (cfg.get("concept") or "").strip():
        p.append(f"The scene concept:\n{cfg['concept'].strip()}")

    lines = ["Storyboard timing and panels:"]
    for i, (tc, b) in enumerate(zip(tcs, beats), 1):
        t = (b.get("title") or "").strip().upper() or "UNTITLED BEAT"
        shot = (b.get("shot") or "").strip().rstrip(".")
        cam = (b.get("camera") or "").strip().rstrip(".")
        block = [f"PANEL {i} ({tc}) {t} — {shot}{', ' + cam if cam else ''}."]
        block.append(f"Action: {_sentence(b.get('action'))}")
        if (b.get("visual") or "").strip():
            block.append(f"Draw: {_sentence(b['visual'])}")
        if (b.get("lighting") or "").strip():
            block.append(f"Lighting: {_sentence(b['lighting'])}")
        if (b.get("continuity") or "").strip():
            block.append(f"Continuity: {_sentence(b['continuity'])}")
        lines.append("\n".join(block))
    p.append("\n\n".join(lines))

    cont = story.get("continuity") or {}
    fixed = [f.strip().rstrip(".") for f in cont.get("fixed_attributes") or [] if f.strip()]
    changes = [c for c in cont.get("intentional_changes") or [] if (c.get("change") or "").strip()]
    if fixed:
        p.append("Keep fixed in all 9 panels:\n" + "\n".join(f"• {f}" for f in fixed))
    if changes:
        p.append("Intentional story progression (these changes are planned and required — do not undo them):\n"
                 + "\n".join(f"• {c.get('attribute', '').strip()}: {c['change'].strip()}"
                             + (f" ({c['panels'].strip()})" if (c.get("panels") or "").strip() else "")
                             for c in changes))

    consistency = ("Make every panel feel like a real frame from the same expensive cinematic sequence, with "
                   "strong visual continuity: the same "
                   + ("character, outfit, " if ch.get("present", True) else "")
                   + ("product design, " if pr.get("present") else "")
                   + "world, visual style and camera language in all 9 panels")
    consistency += ", except for the intentional progression listed above." if changes else \
        ", with consistent lighting direction, atmosphere and color palette."
    p.append(consistency)

    style = (cfg.get("style_notes") or "").strip()
    if style:
        p.append(f"Visual style: {style}")

    layout = "The composition should feel premium, clean, readable, and cinematic. "
    if cfg.get("borders", True):
        layout += "Use black borders between panels like a professional storyboard. "
    layout += "Keep the timecodes and titles small but readable. The images should be the main focus."
    p.append(layout)

    extra = (cfg.get("extra_notes") or "").strip()
    if extra:
        p.append(extra)

    avoid = (cfg.get("avoid") or "").strip().rstrip(".")
    if avoid:
        p.append(f"Avoid {avoid}.")
    return "\n\n".join(p)

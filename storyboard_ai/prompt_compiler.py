"""Prompt compiler: Storyboard Prompt Specification -> final text. Pure, deterministic Python.

Three instruction layers:
  A  universal storyboard rules (fixed: grid, 9 panels, order, labels, sequence, continuity, no artifacts)
  B  dynamic story content (everything else comes from the approved, user-edited storyboard)
  C  conditional instructions (reference roles, text-only subjects, product, intentional changes)

Two output modes render the SAME spec:
  "image"     Image Generation Prompt — optimized for producing the 3x3 storyboard image
  "director"  Director's Storyboard — detailed production document for planning and editing
"""

import re

from .constants import REFERENCE_ROLES
from .prompt_spec import build_spec

MODES = {"image": "Image Generation Prompt — Optimized", "director": "Director's Storyboard — Detailed"}
_GENERIC_NAME = re.compile(r"^(the )?(protagonist|hero|heroine|main character|character|man|woman|boy|girl|"
                           r"worker|person|narrator|customer|owner|employee)$", re.I)
_EXCEPT = re.compile(r"\s*\(except the planned change: [^)]*\)$")


def _sentence(s):
    s = (s or "").strip()
    return s if not s or s[-1] in ".!?" else s + "."


def _join(items, conj="and"):
    items = [i for i in items if i]
    if len(items) <= 1:
        return "".join(items)
    if len(items) == 2:
        return f"{items[0]} {conj} {items[1]}"
    return ", ".join(items[:-1]) + f" {conj} " + items[-1]


def preserve_phrase(preserve):
    """Lesson phrasing for the legacy manual prompt: 'a, b, and c' / 'a and b'."""
    preserve = list(preserve)
    if len(preserve) == 1:
        return preserve[0]
    if len(preserve) == 2:
        return f"{preserve[0]} and {preserve[1]}"
    return ", ".join(preserve[:-1]) + ", and " + preserve[-1]


# ---------------------------------------------------------------- lock phrasing
def _lock_phrases(locks, story):
    """Group lock items into readable phrases, e.g. "Mara's identity, facial structure and outfit"."""
    out, exceptions, char = [], [], []
    for lk in locks:
        text = lk["text"]
        m = _EXCEPT.search(text)
        if m:
            exceptions.append(m.group(0).strip())
            text = text[:m.start()]
        if lk["subject"] == "character":
            char.append(text)
        else:
            out.append(text)
    if char:
        name = story.get("character_name") or ""
        who = f"{name}'s" if name and not _GENERIC_NAME.match(name) else \
            f"the {name.lower()}'s" if name else "the character's"
        out.insert(0, f"{who} {_join(char)}" + (f" {exceptions[0]}" if exceptions else ""))
    return out


def _covered(lk, fixed, story):
    """A generic subject lock is redundant when the story's own fixed attributes already name that subject."""
    if lk.get("source") != "generic":
        return False
    name = story.get("character_name") if lk["subject"] == "character" else \
        story.get("product_name") if lk["subject"] == "product" else ""
    return bool(name) and any(name.lower() in f.lower() for f in fixed)


def _role_phrase(role, story):
    if role == "character":
        return "the main character" + (f" ({story['character_name']})" if story.get("character_name") else "")
    if role == "product":
        return "the product" + (f" ({story['product_name']})" if story.get("product_name") else "")
    if role == "environment":
        return "the location / environment"
    return "the visual style only (rendering, lighting treatment and color grading), not its subjects"


def _reference_lines(spec):
    ref, story = spec["reference"], spec["story"]
    lines = []
    all_locks = [lk for k in ("identity_lock", "appearance_lock", "environment_lock", "style_lock") for lk in ref[k]]
    if ref["enabled"]:
        if ref["role_unknown"] or not ref["roles"]:
            lines.append("Visual reference: an uploaded reference image is provided. Use it only where the panel "
                         "descriptions below agree with it.")
            return lines
        roles = [_role_phrase(r, story) for r in ref["roles"]]
        lines.append(f"Visual reference: use the uploaded reference image as the primary visual reference for "
                     f"{_join(roles)}.")
        from_ref = _lock_phrases([lk for lk in all_locks if lk["from_reference"]], story)
        if from_ref:
            lines.append("From the reference, preserve " + "; ".join(from_ref) +
                         ". Apply this only in panels where that subject is visible.")
        free = []
        if "environment" not in ref["roles"]:
            free.append("environment")
        if "style" not in ref["roles"]:
            free.append("lighting")
        free += ["camera angle", "composition"]
        lines.append(f"{_join(free).capitalize()} follow the panel descriptions below, not the reference image.")
    else:
        if story["character_present"] and any(lk["subject"] == "character" for lk in all_locks):
            lines.append("Maintain the character appearance defined in the character description.")
        if story["product_present"]:
            lines.append("Preserve the product's design, proportions, colors and distinguishing visual features "
                         "exactly as described.")
    return lines


def _continuity_items(spec):
    ref, story = spec["reference"], spec["story"]
    locks = [lk for k in ("identity_lock", "appearance_lock", "environment_lock", "style_lock")
             for lk in ref[k] if not lk["from_reference"]]
    fixed = [f["text"] for f in spec["continuity"]["fixed_attributes"]]
    if not ref["enabled"]:  # text mode: subject locks are covered by the description sentence
        locks = [lk for lk in locks if lk["subject"] not in ("character", "product")]
    locks = [lk for lk in locks if not _covered(lk, fixed, story)]
    items = fixed + _lock_phrases(locks, story)
    seen, out = set(), []
    for i in items:
        k = i.lower()
        if k not in seen:
            seen.add(k)
            out.append(i)
    return out


def _changes_lines(spec):
    return [f"• {c.get('attribute', '').strip()}: {c['change'].strip()}"
            + (f" ({c['panels'].strip()})" if (c.get("panels") or "").strip() else "")
            for c in spec["continuity"]["intentional_changes"]]


# ---------------------------------------------------------------- Layer A (universal)
def _format_block(spec, detailed=False):
    f = spec["format"]
    basis = " using the uploaded reference image" if spec["reference"]["enabled"] else ""
    head = (f"Create a professional cinematic 3x3 timed storyboard for a {f['duration']}-second {f['video_model']} "
            f"video sequence{basis}.")
    rules = ("The storyboard must look like a professional film pre-production board with exactly 9 panels in a "
             "clean 3x3 grid, read in chronological order left to right, top to bottom (panels 1-3 top row, 4-6 "
             "middle row, 7-9 bottom row).")
    labels = ("Each panel must include:\n• panel number\n• timecode\n• short cinematic shot title\n"
              "• one short action description\n"
              "Print only these four items as text on each panel; all other directions describe what to draw. "
              "Follow the panel sequence exactly, keep logical continuity from panel to panel, render everything in "
              "the visual style below, and do not add unrelated objects or visual artifacts.")
    return [head, rules, labels]


# ---------------------------------------------------------------- image mode
def render_image(spec):
    s, p = spec["story"], []
    p += _format_block(spec)
    ident = []
    if s["title"]:
        ident.append(f'Story: "{s["title"]}".')
    if s["core_message"]:
        ident.append(f"Core message: {_sentence(s['core_message'])}")
    if s["story_type_label"]:
        ident.append(f"Story type: {s['story_type_label']}.")
    if s["emotional_progression"]:
        ident.append(f"Emotional progression: {_sentence(s['emotional_progression'])}")
    if s["viewer_takeaway"]:
        ident.append(f"Final impression: {_sentence(s['viewer_takeaway'])}")
    if ident:
        p.append(" ".join(ident))
    p += _reference_lines(spec)
    if spec["subjects_text"]:
        label = "Characters, subjects and world"
        if spec["reference"]["enabled"] and spec["reference"]["roles"]:
            label += " (the reference image takes priority for the preserved attributes)"
        p.append(f"{label}:\n{spec['subjects_text']}")
    if s["scene_concept"]:
        p.append(f"The scene concept:\n{s['scene_concept']}")

    lines, prev_light = ["Storyboard timing and panels:"], None
    for b in spec["beats"]:
        block = [f"PANEL {b['panel']} ({b['timecode']}) {b['title']} — {b['shot']}"
                 f"{', ' + b['camera'] if b['camera'] else ''}."]
        block.append(f"Action: {_sentence(b['action'])}")
        if b["visual"]:
            block.append(f"Draw: {_sentence(b['visual'])}")
        if b["lighting"] and b["lighting"].lower() != (prev_light or "").lower():
            block.append(f"Lighting: {_sentence(b['lighting'])}")
        prev_light = b["lighting"] or prev_light
        lines.append("\n".join(block))
    p.append("\n\n".join(lines))

    cont = _continuity_items(spec)
    if cont:
        p.append("Keep consistent in every panel where visible:\n" + "\n".join(f"• {c}" for c in cont))
    ch = _changes_lines(spec)
    if ch:
        p.append("Intentional story progression (planned and required — do not keep these fixed):\n" + "\n".join(ch))
    p.append(_quality(spec))
    if spec["extra_notes"]:
        p.append(spec["extra_notes"])
    if spec["negatives"]:
        short = [n["text"] for n in spec["negatives"] if not _is_sentence(n["text"])]
        long_ = [n["text"] for n in spec["negatives"] if _is_sentence(n["text"])]
        neg = [f"Avoid {_join(short, 'or')}."] if short else []
        if long_:
            neg.append("Also:\n" + "\n".join(f"• {_sentence(t[0].upper() + t[1:])}" for t in long_))
        p.append("\n".join(neg))
    return "\n\n".join(p)


def _is_sentence(t):
    return len(t.split()) > 7 or "," in t or re.match(r"(do not|don't|never|no|avoid)\b", t, re.I) is not None


def _quality(spec):
    q = []
    if spec["visual_style"]["notes"]:
        q.append(f"Visual style: {_sentence(spec['visual_style']['notes'])}")
    q.append("Make every panel a frame from the same cinematic sequence with consistent camera language.")
    q.append("The composition should feel premium, clean and readable.")
    if spec["format"]["borders"]:
        q.append("Use black borders between panels like a professional storyboard.")
    q.append("Keep the panel numbers, timecodes and titles small but readable; the images are the main focus.")
    return " ".join(q)


# ---------------------------------------------------------------- director mode
def render_director(spec):
    s, f, out = spec["story"], spec["format"], []
    out.append(f"DIRECTOR'S STORYBOARD — {s['title'] or 'Untitled'}")
    out.append(f"Format: cinematic 3x3 timed storyboard · 9 panels · {f['duration']} s · target video model: "
               f"{f['video_model']} · reading order left to right, top to bottom.")
    sec = ["STORY"]
    for label, val in (("Original message", s["original_message"]), ("Core message", s["core_message"]),
                       ("Story type", s["story_type_label"]), ("Genre", s["genre"]),
                       ("Narrative structure", " → ".join(s["narrative_structure"])),
                       ("Emotional progression", s["emotional_progression"]),
                       ("Intended final impression", s["viewer_takeaway"])):
        if val:
            sec.append(f"  {label}: {val}")
    out.append("\n".join(sec))
    if s["scene_concept"]:
        out.append("SCENE CONCEPT\n  " + s["scene_concept"])
    if spec["subjects_text"]:
        out.append("CHARACTERS, SUBJECTS & WORLD\n" + "\n".join("  " + ln for ln in spec["subjects_text"].splitlines()))
    ref = _reference_lines(spec)
    roles = spec["reference"]["roles"]
    head = "VISUAL REFERENCE" + (f" (image role: {', '.join(REFERENCE_ROLES[r] for r in roles)})" if roles else
                                 "" if spec["reference"]["enabled"] else " (none — text descriptions only)")
    out.append(head + ("\n" + "\n".join("  " + r for r in ref) if ref else ""))
    if spec["visual_style"]["notes"]:
        out.append("VISUAL STYLE\n  " + spec["visual_style"]["notes"])

    panels = ["TIMED SCENES"]
    for b in spec["beats"]:
        blk = [f"PANEL {b['panel']} — {b['title']}  ({b['timecode']}, {b['length']:g} s)"]
        for label, val in (("Purpose", b["purpose"]), ("Shot & camera", _join([b["shot"], b["camera"]], ";")
                                                           .replace(" ; ", "; ")),
                           ("Subject & action", b["action"]), ("Visual description", b["visual"]),
                           ("Lighting & atmosphere", b["lighting"]), ("Continuity", b["continuity"])):
            if val:
                blk.append(f"  {label}: {val}")
        if b["panel"] < 9:
            blk.append(f"  Transition → panel {b['panel'] + 1}: {b['transition'] or 'cut'}")
        panels.append("\n".join(blk))
    out.append("\n\n".join(panels))

    cont = _continuity_items(spec)
    if cont:
        out.append("CONTINUITY (fixed)\n" + "\n".join(f"  • {c}" for c in cont))
    ch = _changes_lines(spec)
    if ch:
        out.append("INTENTIONAL PROGRESSION\n" + "\n".join("  " + c for c in ch))
    out.append("LAYOUT & QUALITY\n  " + _quality(spec))
    if spec["extra_notes"]:
        out.append("EXTRA INSTRUCTIONS\n  " + spec["extra_notes"])
    if spec["negatives"]:
        out.append("NEGATIVE INSTRUCTIONS\n" + "\n".join(f"  • {n['text']}" for n in spec["negatives"]))
    c = spec["consistency"]
    if c["resolved"] or c["unresolved"]:
        rep = ["CONSISTENCY REPORT"]
        rep += [f"  ✗ UNRESOLVED: {m}" for m in c["unresolved"]]
        rep += [f"  ✓ auto-resolved: {m}" for m in c["resolved"]]
        out.append("\n".join(rep))
    return "\n\n".join(out)


def compile_prompt(cfg, mode="image"):
    if mode not in MODES:
        raise ValueError(f"Unknown prompt mode {mode!r}; use one of {list(MODES)}.")
    spec = build_spec(cfg)
    return render_director(spec) if mode == "director" else render_image(spec)


def compile_ai_prompt(cfg):  # backward-compatible name
    return compile_prompt(cfg, "image")

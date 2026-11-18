"""Conversion between the AI storyboard structure and the editable project cfg used by the GUI/CLI.

cfg is the single source of truth after generation: users edit it, prompts are compiled from it,
and scene regeneration rebuilds the storyboard context from it (so user edits are respected).
"""

import re
from copy import deepcopy
from datetime import datetime, timezone

from . import SCHEMA_VERSION
from .constants import AVOID_DEFAULT, PRESERVE_ITEMS, REFERENCE_ROLES
from .storyboard_validator import CHANGE_GROUPS, change_groups
from .timing import compute_timeline

AVOID_ITEMS = [s.strip() for s in AVOID_DEFAULT.replace(", or ", ", ").split(",")]
_ANIMATED = re.compile(r"anim|cartoon|anime|illustrat|watercolou?r|2d|3d|hand-drawn|comic|clay|pixar", re.I)
_FORBIDS_PANEL_LABELS = re.compile(r"\b(on-?screen (text|titles?)|titles?|timecodes?|panel numbers?|captions?)\b",
                                   re.I)
_CHARACTER_ONLY_PRESERVE =("character identity", "facial structure", "outfit")


def join_list(items):
    items = [i for i in items if i]
    if len(items) <= 1:
        return "".join(items)
    if len(items) == 2:
        return f"{items[0]} or {items[1]}"
    return ", ".join(items[:-1]) + ", or " + items[-1]


def adapt_avoid(story):
    """Lesson avoid list adapted to this story so it never forbids what the story needs."""
    ch, pr = story.get("character", {}), story.get("product", {})
    groups = change_groups(story.get("continuity", {}).get("intentional_changes"))
    blocked = {a for g in groups for a in CHANGE_GROUPS[g][2]}
    items = []
    for it in AVOID_ITEMS:
        if it in blocked:
            continue
        if not ch.get("present") and it in ("redesigning the character", "changing the outfit",
                                            "changing the face", "plastic skin"):
            continue
        if it == "adding extra characters":
            if ch.get("supporting_characters"):
                it = "adding characters beyond those described"
            elif not ch.get("present"):
                it = "adding people or characters"
        if it == "logos" and pr.get("present"):
            it = "unrelated or invented logos"
        if it in ("cartoon style", "CGI look") and _ANIMATED.search(story.get("visual_style", "")):
            continue
        items.append(it)
    if pr.get("present"):
        items.insert(0, "redesigning the product")
    for extra in story.get("avoid", []):
        e = extra.strip().rstrip(".")
        if _FORBIDS_PANEL_LABELS.search(e):  # would contradict the required panel number/timecode/title
            continue
        if e and e.lower() not in {i.lower() for i in items}:
            items.append(e[0].lower() + e[1:] if e[:2] != e[:2].upper() else e)
    return join_list(items)


def adapt_preserve(story):
    ch = story.get("character", {})
    groups = change_groups(story.get("continuity", {}).get("intentional_changes"))
    blocked = {p for g in groups for p in CHANGE_GROUPS[g][1]}
    out = []
    for p in PRESERVE_ITEMS:
        if p in blocked or (not ch.get("present") and p in _CHARACTER_ONLY_PRESERVE):
            continue
        out.append(p)
    return out


def subject_text(story):
    ch, pr, env = story.get("character", {}), story.get("product", {}), story.get("environment", {})
    lines = []
    if ch.get("present"):
        who = " — ".join(x for x in (ch.get("name", "").strip(), ch.get("description", "").strip().rstrip("."))
                         if x)
        lines.append(f"Main character: {who or 'the character from the reference image'}.")
        if ch.get("outfit"):
            lines.append(f"Outfit: {ch['outfit'].strip().rstrip('.')}.")
        if ch.get("accessories"):
            lines.append(f"Accessories: {ch['accessories'].strip().rstrip('.')}.")
    else:
        lines.append("No main human character: the story is told through the subject, objects and environment.")
    if ch.get("supporting_characters"):
        lines.append("Supporting characters: " + "; ".join(ch["supporting_characters"]) + ".")
    if pr.get("present"):
        who = " — ".join(x for x in (pr.get("name", "").strip(), pr.get("description", "").strip().rstrip("."))
                         if x)
        lines.append(f"Product: {who}.")
    if env:
        lines.append(f"World: {env.get('location', '').strip()} — {env.get('description', '').strip().rstrip('.')}.")
        if env.get("time_of_day"):
            lines.append(f"Time / weather at the start: {env['time_of_day'].strip().rstrip('.')}.")
        if env.get("key_objects"):
            lines.append("Key objects: " + ", ".join(env["key_objects"]) + ".")
    return "\n".join(lines)


def story_meta(sb):
    keys = ("title", "core_message", "story_type", "narrative_structure", "emotional_goal", "viewer_takeaway",
            "visual_style", "color_palette", "character", "product", "environment", "continuity", "avoid")
    return {k: deepcopy(sb.get(k)) for k in keys if k in sb}


def beat_from_ai(b):
    out = {"title": b["title"].strip().upper(), "shot": b["shot_type"].strip(), "action": b["action"].strip(),
            "purpose": b.get("purpose", "").strip(), "visual": b.get("visual_description", "").strip(),
            "camera": b.get("camera", "").strip(), "lighting": b.get("lighting", "").strip(),
            "continuity": b.get("continuity_notes", "").strip(), "transition": (b.get("transition") or "").strip(),
            "weight": float(b.get("relative_weight", 1.0))}
    if not out["transition"]:
        del out["transition"]  # same shape as a saved/reloaded beat (empty text fields are omitted)
    return out


def beat_to_ai(b, panel):
    w = b.get("weight")
    return {"panel": panel, "title": b.get("title", ""), "purpose": b.get("purpose", ""),
            "shot_type": b.get("shot", ""), "camera": b.get("camera", ""),
            "visual_description": b.get("visual", "") or b.get("action", ""), "action": b.get("action", ""),
            "lighting": b.get("lighting", ""), "continuity_notes": b.get("continuity", ""),
            "transition": b.get("transition", ""),
            "relative_weight": float(w) if isinstance(w, (int, float)) and not isinstance(w, bool) else 1.0}


def attach_timing(sb, duration, message=""):
    """Full storyboard document: AI structure + Python-computed timing + original message."""
    doc = deepcopy(sb)
    tl = compute_timeline(duration, [b["relative_weight"] for b in doc["beats"]])
    for b, t in zip(doc["beats"], tl):
        b.update(start_seconds=t["start"], end_seconds=t["end"], timecode=t["timecode"])
    doc["duration_seconds"] = int(duration)
    doc["original_message"] = message
    return doc


def storyboard_to_cfg(sb, settings, base_cfg=None, brief=None, message="", provider_info=None,
                      report=None, review=None):
    base = base_cfg or {}
    roles = [r for r in (settings.get("reference_roles") or []) if r in REFERENCE_ROLES]
    story = story_meta(sb)
    style = sb.get("visual_style", "").strip().rstrip(".")
    palette = sb.get("color_palette", "").strip().rstrip(".")
    cfg = {
        "schema_version": SCHEMA_VERSION,
        "mode": "ai",
        "story_title": sb.get("title", "").strip(),
        "duration": int(settings.get("duration", base.get("duration", 15))),
        "model": settings.get("model") or base.get("model", "Seedance 2.0"),
        "ref_mode": "image" if roles else "text",
        "reference_roles": roles,
        "character_desc": subject_text(story),
        "concept": sb.get("concept", "").strip(),
        "beats": [beat_from_ai(b) for b in sb["beats"]],
        "preserve": adapt_preserve(story),
        "avoid": adapt_avoid(story),
        "style_notes": f"{style}. Color palette: {palette}." if palette else (style + "." if style else ""),
        "borders": base.get("borders", True),
        "extra_notes": "",  # never inherit free-text notes from the previous project
        "prompt_mode": base.get("prompt_mode", "image"),
        "story": story,
        "ai": {
            "original_message": message,
            "settings": {k: v for k, v in settings.items() if k not in ("api_key",)},
            "brief": deepcopy(brief) if brief else None,
            "generated_storyboard": attach_timing(sb, settings.get("duration", 15), message),
            "generated_beats": [beat_from_ai(b) for b in sb["beats"]],
            "provider": (provider_info or {}).get("provider", ""),
            "model": (provider_info or {}).get("model", ""),
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "validation": report.to_dict() if report else None,
            "review": review,
        },
        "final_prompt": "",
    }
    return cfg


def cfg_to_storyboard(cfg):
    """Rebuild a storyboard dict (AI schema shape) from the current, possibly user-edited cfg."""
    story = deepcopy(cfg.get("story") or {})
    if not story:  # legacy / manual project: derive minimal context
        story = {"title": cfg.get("story_title", ""), "core_message": cfg.get("concept", ""),
                 "story_type": "cinematic_fantasy", "narrative_structure": [], "emotional_goal": "",
                 "viewer_takeaway": "", "visual_style": cfg.get("style_notes", ""), "color_palette": "",
                 "character": {"present": True, "name": "", "description":
                               cfg.get("character_desc", "") or "the character from the reference image",
                               "outfit": "", "accessories": "", "supporting_characters": []},
                 "product": {"present": False, "name": "", "description": ""},
                 "environment": {"location": "", "description": cfg.get("concept", ""), "time_of_day": "",
                                 "key_objects": []},
                 "continuity": {"fixed_attributes": list(cfg.get("preserve") or PRESERVE_ITEMS),
                                "intentional_changes": []},
                 "avoid": []}
    story["title"] = cfg.get("story_title") or story.get("title", "")
    story["concept"] = cfg.get("concept", "")
    story["current_character_and_world"] = cfg.get("character_desc", "")
    story["beats"] = [beat_to_ai(b, i + 1) for i, b in enumerate(cfg.get("beats", []))]
    story["_language"] = ((cfg.get("ai") or {}).get("brief") or {}).get("detected_language", "en")
    return story


def storyboard_document(cfg):
    """User-edited storyboard with Python timing, for project files and exports."""
    sb = cfg_to_storyboard(cfg)
    sb.pop("_language", None)
    weights = [b.get("weight") for b in cfg.get("beats", [])]
    use_w = weights if all(isinstance(w, (int, float)) for w in weights) else None
    tl = compute_timeline(cfg.get("duration", 15), use_w)
    for b, t in zip(sb["beats"], tl):
        b.update(start_seconds=t["start"], end_seconds=t["end"], timecode=t["timecode"])
    sb["duration_seconds"] = int(cfg.get("duration", 15))
    sb["original_message"] = (cfg.get("ai") or {}).get("original_message", "")
    return sb

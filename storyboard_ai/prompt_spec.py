"""Storyboard Prompt Specification.

A structured, render-independent description of exactly what the final prompt must say, built
deterministically from the single authoritative project state (cfg = the user's current edits):

  story        title, core message, scene concept, type, genre, emotional progression, takeaway
  subjects     who/what appears (character / product / supporting) + the editable description
  reference    whether an image is uploaded, its user-selected roles, and the identity / appearance /
               environment / style locks taken from it
  continuity   fixed attributes + intentional changes (planned progression is never locked)
  beats        9 timed panels (timecodes computed in Python)
  negatives    concise, story-relevant exclusions
  consistency  conflicts that were resolved automatically, and ones the user must decide

prompt_compiler renders this spec as the optimized image prompt or the detailed director document.
"""

import re

from .constants import PRESERVE_ITEMS, REFERENCE_ROLES, STORY_TYPES
from .prompt_consistency import resolve
from .timing import compute_timeline

SPEC_VERSION = 1

# preserve checkbox -> (lock category, change groups that release it, phrase)
LOCK_MAP = {
    "character identity": ("identity", (), "identity"),
    "facial structure": ("identity", (), "facial structure"),
    "outfit": ("appearance", ("outfit",), "outfit"),
    "materials": ("appearance", ("outfit",), "materials"),
    "colors": ("appearance", (), "colors"),
    "accessories": ("appearance", (), "accessories"),
    "environment": ("environment", ("environment",), "the location's layout, architecture and landmarks"),
    "lighting direction": ("style", ("lighting",), "the lighting direction"),
    "atmosphere": ("style", ("atmosphere",), "the atmosphere"),
    "cinematic color grading": ("style", ("color grading", "lighting"), "the color grading"),
    "visual style": ("style", (), "the rendering style and level of realism"),
}


def _paren_split(text):
    """Split a comma list without breaking parenthesised parts."""
    items, depth, cur = [], 0, ""
    for ch in text:
        depth += ch == "("
        depth -= ch == ")"
        if ch in ",;" and depth <= 0:
            items.append(cur)
            cur = ""
        else:
            cur += ch
    items.append(cur)
    out = []
    for it in items:
        it = re.sub(r"^\s*(or|and)\s+", "", it.strip()).strip().rstrip(".").strip()
        if it:
            out.append(it)
    return out


def _norm(s):
    return re.sub(r"\s+", " ", s.strip().lower().rstrip("."))


def _generic_negatives():
    from .convert import AVOID_ITEMS
    return {_norm(x) for x in AVOID_ITEMS + ["adding characters beyond those described", "adding people or characters",
                                             "unrelated or invented logos", "redesigning the product"]}


def reference_roles(cfg):
    """User-selected roles of the uploaded image. None = image enabled but role unknown."""
    if cfg.get("ref_mode", "image") != "image":
        return []
    roles = cfg.get("reference_roles")
    if roles is None:
        # legacy manual projects: the lesson method always uploaded a character image
        return None if cfg.get("mode") == "ai" else ["character"]
    return [r for r in roles if r in REFERENCE_ROLES]


def build_spec(cfg):
    story_cfg = cfg.get("story") or {}
    is_ai = cfg.get("mode") == "ai" and bool(story_cfg)
    ai = cfg.get("ai") or {}
    brief = ai.get("brief") or {}
    ch, pr = story_cfg.get("character") or {}, story_cfg.get("product") or {}
    character_present = ch.get("present", True) if is_ai else True
    product_present = bool(pr.get("present")) if is_ai else False

    beats_cfg = cfg.get("beats") or []
    if len(beats_cfg) != 9:
        raise ValueError(f"A storyboard needs exactly 9 beats (found {len(beats_cfg)}).")
    weights = [b.get("weight") for b in beats_cfg]
    use_w = weights if all(isinstance(w, (int, float)) and not isinstance(w, bool) for w in weights) else None
    timeline = compute_timeline(int(cfg.get("duration", 15)), use_w)
    beats = []
    for i, (b, t) in enumerate(zip(beats_cfg, timeline)):
        beats.append({"panel": i + 1, "timecode": t["timecode"], "start": t["start"], "end": t["end"],
                      "length": t["length"], "title": (b.get("title") or "").strip().upper() or "UNTITLED BEAT",
                      "shot": (b.get("shot") or "").strip().rstrip("."),
                      "camera": (b.get("camera") or "").strip().rstrip("."),
                      "action": (b.get("action") or "").strip(), "visual": (b.get("visual") or "").strip(),
                      "lighting": (b.get("lighting") or "").strip(), "purpose": (b.get("purpose") or "").strip(),
                      "continuity": (b.get("continuity") or "").strip(),
                      "transition": (b.get("transition") or "").strip()})

    st = story_cfg.get("story_type", "")
    story = {
        "title": (cfg.get("story_title") or story_cfg.get("title") or "").strip(),
        "core_message": (story_cfg.get("core_message") or "").strip(),
        "scene_concept": (cfg.get("concept") or "").strip(),
        "story_type": st, "story_type_label": STORY_TYPES.get(st, ("",))[0] if is_ai else "",
        "genre": (brief.get("genre") or "").strip(),
        "narrative_structure": list(story_cfg.get("narrative_structure") or []),
        "emotional_progression": (story_cfg.get("emotional_goal") or "").strip(),
        "viewer_takeaway": (story_cfg.get("viewer_takeaway") or "").strip(),
        "original_message": (ai.get("original_message") or "").strip(),
        "character_present": character_present, "product_present": product_present,
        "character_name": (ch.get("name") or "").strip(), "product_name": (pr.get("name") or "").strip(),
        "supporting": list(ch.get("supporting_characters") or []),
    }

    roles = reference_roles(cfg)
    enabled = cfg.get("ref_mode", "image") == "image"
    reference = {"enabled": enabled, "roles": roles or [], "role_unknown": enabled and roles is None,
                 "identity_lock": [], "appearance_lock": [], "environment_lock": [], "style_lock": []}

    # ---- lock candidates (generic: from the preserve checkboxes / subject type)
    preserve = cfg.get("preserve")
    preserve = list(PRESERVE_ITEMS) if preserve is None else list(preserve)
    # AI projects: a lesson default that the story adaptation removed can only be present because the
    # user put it back -> it is a user requirement (kept and reported, never silently dropped).
    from .convert import adapt_avoid, adapt_preserve
    adapted_pres = set(adapt_preserve(story_cfg)) if is_ai else set(PRESERVE_ITEMS)
    adapted_avoid = {_norm(x) for x in _paren_split(adapt_avoid(story_cfg))} if is_ai else None

    def pres_src(p):
        return "generic" if p in adapted_pres else "user"
    locks = []
    if character_present:
        for p in preserve:
            if p in LOCK_MAP and LOCK_MAP[p][0] in ("identity", "appearance"):
                cat, grp, phrase = LOCK_MAP[p]
                locks.append({"text": phrase, "category": cat, "groups": grp, "subject": "character",
                              "from_reference": enabled and "character" in reference["roles"], "source": pres_src(p)})
    if product_present:
        for cat, phrase in (("identity", "the product's design, shape and proportions"),
                            ("appearance", "the product's colors, materials, finish, logo and distinguishing details")):
            locks.append({"text": phrase, "category": cat, "groups": (), "subject": "product",
                          "from_reference": enabled and "product" in reference["roles"], "source": "generic"})
    for p in preserve:
        if p in LOCK_MAP and LOCK_MAP[p][0] in ("environment", "style"):
            cat, grp, phrase = LOCK_MAP[p]
            role = "environment" if cat == "environment" else "style"
            locks.append({"text": phrase, "category": cat, "groups": grp, "subject": role,
                          "from_reference": enabled and role in reference["roles"], "source": pres_src(p)})

    # ---- fixed attributes (story) / negatives (generic | ai | user)
    cont = story_cfg.get("continuity") or {}
    gen_fixed = {_norm(x) for x in ((ai.get("generated_storyboard") or {}).get("continuity") or {})
                 .get("fixed_attributes", [])}
    fixed = [{"text": f.strip().rstrip("."), "source": "ai" if (_norm(f) in gen_fixed or not gen_fixed) else "user"}
             for f in cont.get("fixed_attributes") or [] if f.strip()]
    changes = [c for c in cont.get("intentional_changes") or [] if (c.get("change") or "").strip()]

    generic = _generic_negatives()
    ai_whole = [a.strip().rstrip(".").strip() for a in story_cfg.get("avoid") or [] if a.strip()]
    ai_items = {_norm(x) for a in ai_whole for x in [a, *_paren_split(a)]}
    avoid_raw = cfg.get("avoid")
    avoid_raw = avoid_raw if isinstance(avoid_raw, str) else ""
    # AI avoid items are full sentences that may contain commas: protect them before splitting the list
    held = {}
    for i, whole in enumerate(sorted(ai_whole, key=len, reverse=True)):
        if "," in whole and whole in avoid_raw:
            key = f"\x00{i}\x00"
            held[key] = whole
            avoid_raw = avoid_raw.replace(whole, key)
    negatives = []
    for it in _paren_split(avoid_raw):
        for key, whole in held.items():
            it = it.replace(key, whole)
        n = _norm(it)
        src = "generic" if n in generic else ("ai" if n in ai_items else "user")
        if src == "generic" and adapted_avoid is not None and n not in adapted_avoid:
            src = "user"  # re-added after the story adaptation removed it
        negatives.append({"text": it, "source": src})

    negatives, locks, fixed, rep = resolve({
        "negatives": negatives, "locks": locks, "fixed": fixed, "changes": changes, "beats": beats,
        "story": story, "style_notes": cfg.get("style_notes") or "", "extra_notes": cfg.get("extra_notes") or "",
        "subjects_text": cfg.get("character_desc") or "", "reference": reference, "is_ai": is_ai})
    if reference["role_unknown"]:
        rep.flag("A reference image is enabled but its role is not selected (character, product, environment "
                 "or style). Select what the image shows.")
    if is_ai and not story["scene_concept"]:
        rep.flag("The scene concept is empty. Write this story's concept (the generic lesson concept is never "
                 "substituted).")

    for lk in locks:
        key = {"identity": "identity_lock", "appearance": "appearance_lock", "environment": "environment_lock",
               "style": "style_lock"}[lk["category"]]
        reference[key].append(lk)

    # de-duplicate negatives, keep order
    seen, negs = set(), []
    for n in negatives:
        if _norm(n["text"]) not in seen:
            seen.add(_norm(n["text"]))
            negs.append(n)

    return {
        "spec_version": SPEC_VERSION,
        "is_ai": is_ai,
        "format": {"duration": int(cfg.get("duration", 15)), "video_model": (cfg.get("model") or "").strip()
                   or "Seedance 2.0", "panels": 9, "grid": "3x3", "borders": bool(cfg.get("borders", True))},
        "story": story,
        "subjects_text": (cfg.get("character_desc") or "").strip(),
        "reference": reference,
        "continuity": {"fixed_attributes": fixed, "intentional_changes": changes},
        "visual_style": {"notes": (cfg.get("style_notes") or "").strip(),
                         "palette": (story_cfg.get("color_palette") or "").strip()},
        "beats": beats,
        "negatives": negs,
        "extra_notes": (cfg.get("extra_notes") or "").strip(),
        "consistency": rep.to_dict(),
    }

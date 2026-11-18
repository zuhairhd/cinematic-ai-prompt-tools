"""Storyboard validation.

Deterministic checks (errors block acceptance, warnings are shown) are kept strictly separate from the
optional AI semantic review, which is a subjective opinion and never a guarantee.
"""

import json
import re

from .schema import STORYBOARD_SCHEMA, REVIEW_SCHEMA, validate
from .timing import TimingError, compute_timeline, validate_timeline

N = 9

# Intentional-change keyword groups -> preserve items / avoid phrases they would contradict.
CHANGE_GROUPS = {
    "lighting": (r"\b(light|lighting|sun|sunrise|sunset|dawn|dusk|night|daylight|time of day)\b",
                 # a planned light change (storm -> sunrise) also changes the grade
                 ["lighting direction", "cinematic color grading"],
                 ["changing the lighting style", "changing the lighting"]),
    "color grading": (r"\b(colou?rs?|grad(e|ing)|palette|hue|saturation)\b",
                      ["cinematic color grading"], ["changing the color grading"]),
    "atmosphere": (r"\b(weather|storm|rain|fog|mist|atmosphere|mood|sky|clouds?|snow)\b",
                   ["atmosphere"], ["changing the atmosphere"]),
    "outfit": (r"\b(outfit|clothes|clothing|costume|wardrobe|dress|uniform)\b",
               ["outfit"], ["changing the outfit"]),
    "environment": (r"\b(environment|location|setting|place|scenery|landscape|world|terrain)\b",
                    ["environment"], ["changing the environment"]),
    # planned changes to a character's look: identity stays locked, but with an explicit exception
    "appearance": (r"\b(hair|hairstyle|makeup|scars?|tattoos?|ages?|aging|ageing|older|younger|appearance|"
                   r"beard|body|transforms?|transformation)\b", [], []),
}

VAGUE_PHRASES = ["something happens", "epic scene", "beautiful moment", "cinematic scene", "amazing shot",
                 "stuff", "etc.", "and so on", "some things", "various things",
                 "choose whichever", "whichever the", "either one"]

_STOP = set("""about above after again against also among another because been before being below between both
could does doing down during each from further have having here into itself just more most must other over
same should some such than that their them then there these they this those through under until very wears
wearing what when where which while will with would your yours a an the and or of in on at to for is are was
were be by his her its it he she has had who whom whose made make look looks like very really""".split())


class ValidationReport:
    def __init__(self):
        self.errors, self.warnings, self.notes = [], [], []  # notes: automatic, reported resolutions

    @property
    def ok(self):
        return not self.errors

    def to_dict(self):
        return {"errors": list(self.errors), "warnings": list(self.warnings)}

    def text(self):
        out = ["DETERMINISTIC CHECKS: " + ("PASSED" if self.ok else f"FAILED ({len(self.errors)} errors)")]
        out += [f"  ✗ {e}" for e in self.errors]
        out += [f"  ! {w}" for w in self.warnings]
        return "\n".join(out)


def _nonempty(v, n=1):
    return isinstance(v, str) and len(v.strip()) >= n


def validate_beat(beat, panel, others=()):
    """Errors for one beat (also used for single-scene regeneration)."""
    errs = []
    p = f"Panel {panel}"
    if beat.get("panel") != panel:
        errs.append(f"{p}: panel number is {beat.get('panel')!r}, expected {panel}.")
    for key, n in (("title", 2), ("shot_type", 3), ("camera", 5), ("action", 8),
                   ("visual_description", 25), ("lighting", 5), ("purpose", 5)):
        if not _nonempty(beat.get(key), n):
            errs.append(f"{p}: '{key}' is missing or too short.")
    w = beat.get("relative_weight")
    if isinstance(w, bool) or not isinstance(w, (int, float)) or not w > 0:
        errs.append(f"{p}: relative_weight must be a positive number.")
    vis = (beat.get("visual_description") or "").strip().lower()
    for o in others:
        if vis and vis == (o.get("visual_description") or "").strip().lower():
            errs.append(f"{p}: visual description duplicates panel {o.get('panel')}.")
        if _nonempty(beat.get("action")) and beat["action"].strip().lower() == (o.get("action") or "").strip().lower():
            errs.append(f"{p}: action duplicates panel {o.get('panel')}.")
    return errs


def _tokens(text):
    return [t for t in re.findall(r"[A-Za-z][A-Za-z'-]{3,}", text or "") if t.lower() not in _STOP]


def check_subject_preserved(subject_desc, sb):
    """User-specified character/product details must survive into the storyboard.
    Returns (errors, warnings)."""
    subject_desc = (subject_desc or "").strip()
    if not subject_desc:
        return [], []
    hay = json.dumps({k: sb.get(k) for k in ("character", "product", "concept", "continuity", "title")},
                     ensure_ascii=False).lower()
    hay += " " + " ".join((b.get("visual_description", "") + " " + b.get("action", "")).lower()
                          for b in sb.get("beats", []))
    latin = _tokens(subject_desc)
    if not latin:
        if re.search(r"[؀-ۿ]", subject_desc) and not re.search(r"[؀-ۿ]", hay):
            return [], ["The character/product description is in Arabic and the storyboard is in English, so the "
                        "automatic preservation check could not compare them. Please review it manually."]
        return [], []
    errs = []
    sentence_starts = {m.group(1) for m in re.finditer(r"(?:^|[.!?]\s+)([A-Z][a-z]+)", subject_desc)}
    names = {t for t in re.findall(r"\b[A-Z][A-Za-z0-9-]{2,}\b", subject_desc)
             if t not in sentence_starts and t.lower() not in _STOP}
    for name in sorted(names):
        if name.lower() not in hay:
            errs.append(f"User-specified name '{name}' is missing from the storyboard (character/product replaced?).")
    words = {t.lower() for t in latin}
    found = {w for w in words if w in hay or w.rstrip("s") in hay}
    ratio = len(found) / len(words)
    if ratio < 0.6:
        missing = ", ".join(sorted(words - found)[:10])
        errs.append(f"Only {ratio:.0%} of the user's character/product details appear in the storyboard "
                    f"(missing: {missing}).")
    return errs, []


def validate_storyboard(sb, settings=None, message=""):
    """Deterministic validation of an AI storyboard dict (before timing is attached)."""
    settings = settings or {}
    rep = ValidationReport()
    rep.errors += validate(sb, STORYBOARD_SCHEMA, "storyboard")
    beats = sb.get("beats") if isinstance(sb.get("beats"), list) else []
    if len(beats) != N:
        rep.errors.append(f"Storyboard has {len(beats)} scenes; exactly {N} are required.")
    if rep.errors:
        return rep
    for i, b in enumerate(beats):
        rep.errors += validate_beat(b, i + 1, beats[:i])
    # repetition (warnings)
    for i in range(1, N):
        a, b = beats[i - 1], beats[i]
        if a["shot_type"].strip().lower() == b["shot_type"].strip().lower() and \
                a["camera"].strip().lower() == b["camera"].strip().lower():
            rep.warnings.append(f"Panels {i} and {i + 1} use the same shot type and camera (repetitive).")
    titles = [b["title"].strip().upper() for b in beats]
    for t in sorted({t for t in titles if titles.count(t) > 1}):
        rep.warnings.append(f"Shot title '{t}' is used more than once.")
    for b in beats:
        if len(b["action"].split()) > 25:
            rep.warnings.append(f"Panel {b['panel']}: action line is long ({len(b['action'].split())} words); "
                                "image models print short captions more cleanly.")
        low = b["visual_description"].lower()
        for v in VAGUE_PHRASES:
            if v in low:
                rep.warnings.append(f"Panel {b['panel']}: vague wording '{v}' in the visual description.")
    # timing
    try:
        tl = compute_timeline(settings.get("duration", 15), [b["relative_weight"] for b in beats])
        rep.errors += validate_timeline(tl, int(settings.get("duration", 15)))
    except TimingError as e:
        rep.errors.append(f"Timing: {e}")
    # continuity
    fixed = [f for f in sb["continuity"]["fixed_attributes"] if _nonempty(f, 3)]
    if len(fixed) < 3:
        rep.errors.append("Continuity: at least 3 specific fixed attributes are required.")
    ch = sb["character"]
    if ch["present"] and not (_nonempty(ch["description"], 3) or settings.get("ref_mode") == "image"):
        rep.errors.append("Continuity: the main character is present but has no description.")
    if sb["product"]["present"] and not _nonempty(sb["product"]["description"], 3):
        rep.errors.append("Continuity: the product is present but has no appearance description.")
    e, w = check_subject_preserved(settings.get("subject_desc", ""), sb)
    rep.errors += e
    rep.warnings += w
    # story-specific avoid items that forbid an intentional change
    for msg in _avoid_vs_changes(sb["avoid"], sb["continuity"]["intentional_changes"]):
        rep.warnings.append(msg)
    e, w = check_contamination(sb, message, settings.get("subject_desc", ""))
    rep.errors += e
    rep.warnings += w
    return rep


_MENACE = re.compile(r"\b(monsters?|creatures?|beasts?|demons?|serpents?|dragons?|titans?|leviathans?|hidden force|"
                     r"mysterious (shape|force|presence|figure)|shadowy (figure|creature|shape)|looming threat)\b", re.I)
_REVEAL = re.compile(r"\b(the reveal|big reveal|dramatic reveal|hidden force|suspense)\b", re.I)


def check_contamination(sb, message="", subject_desc=""):
    """Generic lesson-template text or unrelated genre elements that the user never asked for.
    Returns (errors, warnings); errors trigger a bounded AI repair."""
    from .constants import TEMPLATE_BEATS, TEMPLATE_CONCEPT
    errs, warns = [], []
    concept = sb.get("concept", "").lower()
    for sent in (x.strip().lower() for x in TEMPLATE_CONCEPT.split(".") if len(x.strip()) > 15):
        if sent in concept:
            errs.append("The concept copies the generic lesson template; write this story's own concept.")
            break
    template_actions = {b["action"].strip().lower() for b in TEMPLATE_BEATS}
    for b in sb.get("beats", []):
        if b.get("action", "").strip().lower() in template_actions:
            errs.append(f"Panel {b.get('panel')}: action is generic lesson-template text; write it for this story.")
    allowed = f"{message} {subject_desc}".lower()
    st = sb.get("story_type")
    for b in sb.get("beats", []):
        text = f"{b.get('title', '')} {b.get('visual_description', '')} {b.get('action', '')}"
        m = _MENACE.search(text)
        if m and st != "cinematic_fantasy" and m.group(0).lower() not in allowed:
            errs.append(f"Panel {b.get('panel')}: '{m.group(0)}' is unrelated to the user's message for a "
                        f"{st} story; remove invented threats or creatures.")
        r = _REVEAL.search(text)
        if r and st in ("educational", "documentary", "product_showcase") and r.group(0).lower() not in allowed:
            warns.append(f"Panel {b.get('panel')}: '{r.group(0)}' adds forced suspense to a {st} story.")
    return errs, warns


def change_groups(changes):
    """Names of CHANGE_GROUPS touched by a list of intentional-change dicts."""
    hit = set()
    for c in changes or []:
        text = f"{c.get('attribute', '')} {c.get('change', '')}".lower()
        for g, (rx, _, _) in CHANGE_GROUPS.items():
            if re.search(rx, text):
                hit.add(g)
    return hit


def _avoid_vs_changes(avoid_items, changes):
    msgs = []
    for g in change_groups(changes):
        for item in avoid_items:
            if re.search(CHANGE_GROUPS[g][0], item.lower()) and re.search(r"\b(chang|alter|different|shift)", item.lower()):
                msgs.append(f"Avoid item '{item}' contradicts the intentional {g} change.")
    return msgs


def check_cfg_contradictions(cfg):
    """Warnings for an editable project cfg: preserve/avoid lists vs intentional changes."""
    story = cfg.get("story") or {}
    changes = (story.get("continuity") or {}).get("intentional_changes") or []
    out = []
    groups = change_groups(changes)
    avoid = (cfg.get("avoid") or "").lower()
    for g in sorted(groups):
        _, preserve_items, avoid_phrases = CHANGE_GROUPS[g]
        for p in preserve_items:
            if p in (cfg.get("preserve") or []):
                out.append(f"'{p}' is marked to preserve, but the story intentionally changes {g}.")
        for a in avoid_phrases:  # phrases may overlap ("changing the lighting [style]"): report once
            if a in avoid:
                out.append(f"The avoid list forbids '{a}', but the story intentionally changes {g}.")
                break
    return out


def validate_cfg(cfg):
    """Deterministic checks on an edited project (manual or AI). Returns ValidationReport."""
    rep = ValidationReport()
    beats = cfg.get("beats")
    if not isinstance(beats, list) or len(beats) != N:
        rep.errors.append(f"Exactly {N} beats are required (found {len(beats) if isinstance(beats, list) else 0}).")
        return rep
    for i, b in enumerate(beats, 1):
        if not isinstance(b, dict):
            rep.errors.append(f"Beat {i} is not a valid object.")
            continue
        if not _nonempty(b.get("title")):
            rep.errors.append(f"Beat {i}: shot title is empty.")
        if not _nonempty(b.get("shot")):
            rep.errors.append(f"Beat {i}: shot type is empty.")
        if not _nonempty(b.get("action")):
            rep.errors.append(f"Beat {i}: action is empty.")
    weights = [b.get("weight") for b in beats if isinstance(b, dict)]
    use_w = weights if len(weights) == N and all(w is not None for w in weights) else None
    try:
        tl = compute_timeline(cfg.get("duration", 15), use_w)
        rep.errors += validate_timeline(tl, int(cfg.get("duration", 15)))
    except TimingError as e:
        rep.errors.append(f"Timing: {e}")
    if cfg.get("mode") == "ai":
        if not (cfg.get("concept") or "").strip():
            rep.errors.append("The scene concept is empty. Write this story's concept "
                              "(the generic lesson concept is never substituted).")
        if cfg.get("ref_mode") == "image" and not cfg.get("reference_roles"):
            rep.errors.append("A reference image is selected but not what it shows. Tick Character, Product, "
                              "Environment or Style — or choose 'No reference image'.")
        fixed = ((cfg.get("story") or {}).get("continuity") or {}).get("fixed_attributes") or []
        if not fixed and not cfg.get("preserve"):
            rep.warnings.append("No continuity rules: add fixed attributes or preserve items.")
    if rep.ok:
        from .prompt_spec import build_spec  # local import: prompt_spec depends on this module
        cons = build_spec(cfg)["consistency"]
        rep.warnings += [m for m in cons["unresolved"] if m not in rep.errors]
        rep.notes += cons["resolved"]
    return rep


# ---------------------------------------------------------------- AI semantic review (subjective)
REVIEW_SYSTEM = """You are a demanding storyboard editor. Review the 9-panel storyboard against the user's
original message. Rate 1-5 (5 = excellent) and be specific and honest. This is a subjective creative
opinion. For 'repetition', 5 means no unnecessary repetition."""


def ai_review(provider, storyboard, message):
    """Subjective AI review. Returns dict (validated) or raises AIProviderError / ValueError."""
    user = (f"ORIGINAL MESSAGE:\n<<<\n{message}\n>>>\n\nSTORYBOARD:\n"
            f"{json.dumps(storyboard, ensure_ascii=False, indent=1)}")
    r = provider.generate_json(REVIEW_SYSTEM, user, REVIEW_SCHEMA, "storyboard_review")
    errs = validate(r, REVIEW_SCHEMA, "review")
    if errs:
        raise ValueError("AI review returned invalid data: " + "; ".join(errs[:5]))
    return r


def review_text(review):
    if not review:
        return ""
    lines = ["AI CREATIVE REVIEW (subjective opinion, not a guarantee of quality):"]
    for k in ("message_alignment", "story_progression", "visual_clarity", "scene_consistency",
              "ending_strength", "repetition"):
        r = review[k]
        lines.append(f"  {k.replace('_', ' ').title():20s} {r['rating']}/5  {r['comment']}")
    for c in review.get("contradictions", []):
        lines.append(f"  Contradiction: {c}")
    for s in review.get("suggestions", []):
        lines.append(f"  Suggestion: {s}")
    lines.append(f"  Summary: {review['summary']}")
    return "\n".join(lines)

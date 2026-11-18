"""Prompt consistency validator.

Detects contradictions between the instructions that will go into the final prompt and the approved
story, then resolves them by priority instead of blindly deleting rules:

  1. explicit user instructions (typed avoid items, extra notes)        -> kept; conflict reported
  2. approved story content (scenes, intentional changes, style)        -> never rewritten
  3. AI-generated negatives / fixed attributes                          -> rewritten or dropped (reported)
  4. generic lesson defaults (preserve checkboxes, lesson avoid list)    -> rewritten or dropped (reported)

Everything is deterministic and works on structured data. Each instruction carries a `source`
('generic' | 'ai' | 'user' | 'story') so the resolver knows what it may change.
"""

import re

from .constants import TEMPLATE_BEATS, TEMPLATE_CONCEPT
from .storyboard_validator import CHANGE_GROUPS

_CHANGE_VERB = re.compile(r"\b(chang\w*|alter\w*|different|shift\w*|modif\w*|swap\w*|redesign\w*|replac\w*)\b", re.I)
_CROWD_BAN = re.compile(r"\b((extra|additional|other|more|new) (characters?|people|persons|figures)|"
                        r"adding (people|characters|extra characters|other people)|crowds?)\b", re.I)
_PEOPLE_NEEDED = re.compile(r"\b(crowd|crowds|people|audience|customers?|clients?|commuters?|passengers?|family|"
                            r"friends|children|kids|team|colleagues|coworkers|co-workers|group of|passers?-?by|"
                            r"neighbou?rs?|coach|teacher|students?|shoppers?|staff)\b", re.I)
_TEXT_BAN = re.compile(r"\b(text|texts|captions?|lettering|signs?|signage|labels?|words|typography|logos?|"
                       r"ui elements|interface|screens?)\b", re.I)
_BLANKET_TEXT = re.compile(r"^\s*(any |all |no )?(text|texts|words|lettering|typography)\s*$", re.I)
_TEXT_QUALIFIED =re.compile(r"\b(messy|unreadable|illegible|unrelated|invented|random|garbled|distorted|"
                             r"watermarks?|extra|fake|misspelled)\b", re.I)
_TEXT_NEEDED = re.compile(r"\b(signs?|signage|logos?|labels?|headline|title card|banner|poster|slogan|"
                          r"brand name|reading ['\"]|text reading|written|call to action)\b", re.I)
_UI_NEEDED = re.compile(r"\b(screens?|app|apps|interface|ui|dashboard|display|monitors?|notification\w*|"
                        r"waveform|tablet|smartphone|phone)\b", re.I)
_PHOTOREAL = re.compile(r"\b(photo-?real\w*|realistic|realism|live-action|film still|documentary)\b", re.I)
_PAINTERLY = re.compile(r"\b(painterly|painted|watercolou?r|oil painting|cartoon\w*|anime|illustrat\w*|"
                        r"sketch\w*|comic[- ]book|cel-shaded)\b", re.I)
_ANIMATED_STYLE = re.compile(r"anim|cartoon|anime|illustrat|watercolou?r|2d|3d|hand-drawn|comic|clay|pixar", re.I)
_STATIONARY = re.compile(r"\b(stationary|stays? in (one|the same) (place|spot|position)|same position|does not move|"
                         r"doesn't move|remains? (still|in place)|never moves)\b", re.I)
_TRAVEL = re.compile(r"\b(walks? (to|into|through|across|toward)|travels?|journey|arrives?|runs? (to|through|"
                     r"across)|drives?|flies|climbs?|leaves? the|enters?|crosses|rides?)\b", re.I)
_HEROIC = re.compile(r"\bhero(ic)?\b|\btriumph\w*|\bvictor(y|ious)\b|\biconic payoff\b", re.I)
_OPEN_ENDING = re.compile(r"\b(unresolved|open[- ]ended|open question|ambiguous|uncertain\w*|wonders?|"
                          r"wondering|no answer|undecided|question(s|ing)? (whether|if))\b", re.I)
_REFERENCE_WORDS = re.compile(r"\b(reference image|uploaded (image|photo)|the reference)\b", re.I)

_TEMPLATE_SENTENCES = [s.strip().lower() for s in TEMPLATE_CONCEPT.split(".") if len(s.strip()) > 15]
_TEMPLATE_ACTIONS = {b["action"].strip().lower() for b in TEMPLATE_BEATS}
_TEMPLATE_TITLES = {b["title"] for b in TEMPLATE_BEATS} - {"THE REVEAL"}


class Report:
    def __init__(self):
        self.resolved, self.unresolved = [], []

    def fix(self, msg):
        if msg not in self.resolved:
            self.resolved.append(msg)

    def flag(self, msg):
        if msg not in self.unresolved:
            self.unresolved.append(msg)

    def to_dict(self):
        return {"resolved": list(self.resolved), "unresolved": list(self.unresolved)}


def _beats_text(beats, keys=("visual", "action", "title")):
    return " ".join(str(b.get(k, "")) for b in beats for k in keys)


def _changed_groups(changes):
    hit = {}
    for c in changes:
        text = f"{c.get('attribute', '')} {c.get('change', '')}".lower()
        for g, (rx, _, _) in CHANGE_GROUPS.items():
            if re.search(rx, text):
                hit.setdefault(g, c)
    return hit


def _handle(rep, item, conflict_msg, rewrite=None):
    """Apply source priority to one conflicting instruction. Returns the (possibly rewritten) item or None."""
    src = item.get("source", "generic")
    if src == "user":
        rep.flag(f"{conflict_msg} Your instruction '{item['text']}' was kept (user requirements win); "
                 "edit it or the scenes to remove the contradiction.")
        return item
    if rewrite:
        rep.fix(f"{conflict_msg} Rewrote {src} instruction '{item['text']}' -> '{rewrite}'.")
        return dict(item, text=rewrite)
    rep.fix(f"{conflict_msg} Removed {src} instruction '{item['text']}'.")
    return None


def resolve(ctx):
    """ctx keys: negatives, locks, fixed (lists of {text, source, ...}), changes, beats, story, style_notes,
    extra_notes, subjects_text, reference ({enabled, roles}), is_ai.
    Returns (negatives, locks, fixed, report)."""
    rep = Report()
    negatives, locks, fixed = list(ctx["negatives"]), list(ctx["locks"]), list(ctx["fixed"])
    changes, beats, story = ctx["changes"], ctx["beats"], ctx.get("story") or {}
    groups = _changed_groups(changes)
    scene_text = _beats_text(beats)
    story_text = " ".join([scene_text, story.get("scene_concept", ""), ctx.get("subjects_text", "")])

    # 1) preservation locks vs intentional changes ------------------------------------------------
    out = []
    for lk in locks:
        g = next((x for x in lk.get("groups", ()) if x in groups and x != "appearance"), None)
        if g and lk.get("source") == "user":
            rep.flag(f"Conflict: you asked to preserve '{lk['text']}', but the story intentionally changes {g} "
                     f"({groups[g].get('change', '')}). Your instruction was kept; untick it or edit the change.")
        elif g:
            c = groups[g]
            rep.fix(f"Story intentionally changes {g} ({c.get('change', '')}); the '{lk['text']}' lock "
                    "was released instead of freezing it.")
            continue
        if lk.get("category") in ("identity", "appearance") and "appearance" in groups and \
                lk.get("subject") == "character":
            c = groups["appearance"]
            text = f"{lk['text']} (except the planned change: {c.get('attribute', '')} {c.get('change', '')})"
            rep.fix(f"Identity lock kept with an explicit exception for the planned {c.get('attribute', '')} change.")
            lk = dict(lk, text=text)
        out.append(lk)
    locks = out

    # 2) negatives vs intentional changes ---------------------------------------------------------
    out = []
    for n in negatives:
        low = n["text"].lower()
        keep = n
        for g, c in groups.items():
            if re.search(CHANGE_GROUPS[g][0], low) and _CHANGE_VERB.search(low):
                keep = _handle(rep, n, f"Conflict: avoid '{n['text']}' vs planned {g} change "
                                       f"({c.get('change', '')}).")
                break
        if keep:
            out.append(keep)
    negatives = out

    # 3) fixed attributes vs intentional changes (rewrite with an exception, never delete) ---------
    out = []
    for f in fixed:
        low = f["text"].lower()
        for g, c in groups.items():
            if g != "appearance" and re.search(CHANGE_GROUPS[g][0], low):
                new = f"{f['text']} (until the planned {g} change: {c.get('change', '')})"
                if f.get("source") == "user":
                    rep.flag(f"Fixed attribute '{f['text']}' conflicts with the planned {g} change.")
                else:
                    rep.fix(f"Fixed attribute '{f['text']}' overlaps the planned {g} change; added an exception.")
                    f = dict(f, text=new)
                break
        out.append(f)
    fixed = out

    # 4) 'no extra characters' vs scenes that need people ------------------------------------------
    supporting = (story.get("supporting") or [])
    people_hit = _PEOPLE_NEEDED.search(scene_text)
    if supporting or people_hit:
        who = ", ".join(supporting) if supporting else people_hit.group(0)
        out = []
        for n in negatives:
            if _CROWD_BAN.search(n["text"]) and not re.search(r"beyond|other than|not described|except",
                                                                 n["text"], re.I):
                n = _handle(rep, n, f"Conflict: avoid '{n['text']}' but the scenes require people ({who}).",
                            rewrite="adding characters who are not in the panel descriptions")
            if n:
                out.append(n)
        negatives = out

    # 5) blanket 'no text / logos / UI' vs scenes that need them -----------------------------------
    product = story.get("product_present")
    text_needed = _TEXT_NEEDED.search(scene_text) or (product and re.search(r"\blogo", story_text, re.I))
    ui_needed = _UI_NEEDED.search(scene_text)
    out = []
    for n in negatives:
        t = n["text"]
        if _TEXT_BAN.search(t) and not _TEXT_QUALIFIED.search(t):
            is_ui = re.search(r"\b(ui|interface|screens?)\b", t, re.I)
            is_logo = re.search(r"\blogos?\b", t, re.I)
            if is_ui and ui_needed:
                n = _handle(rep, n, f"Conflict: avoid '{t}' but the scenes show {ui_needed.group(0)} content.",
                            rewrite="unrelated or random UI elements")
            elif is_logo and text_needed:
                n = _handle(rep, n, f"Conflict: avoid '{t}' but the story shows a logo/brand.",
                            rewrite="unrelated or invented logos")
            elif not is_ui and not is_logo and (text_needed or _BLANKET_TEXT.match(t)):
                # a blanket 'text' ban would also forbid the panel number/timecode/title labels
                need = text_needed.group(0) if text_needed else "panel number, timecode and title labels"
                n = _handle(rep, n, f"Conflict: avoid '{t}' but the storyboard requires text ({need}).",
                            rewrite="unrelated or unreadable text inside the images")
        if n:
            out.append(n)
    negatives = out

    # 6) style vs scene descriptions / negatives ---------------------------------------------------
    style = ctx.get("style_notes", "")
    if _PHOTOREAL.search(style):
        for b in beats:
            m = _PAINTERLY.search(f"{b.get('visual', '')} {b.get('action', '')}")
            if m:
                rep.flag(f"Style conflict: the visual style is photorealistic but panel {b['panel']} asks for "
                         f"'{m.group(0)}' imagery. Edit the panel or the style.")
    if _ANIMATED_STYLE.search(style):
        out = []
        for n in negatives:
            if re.search(r"\b(cartoon style|cgi look|cartoon)\b", n["text"], re.I):
                n = _handle(rep, n, f"Conflict: avoid '{n['text']}' vs the chosen animated style.")
            if n:
                out.append(n)
        negatives = out

    # 7) stationary instruction vs travel / location change ----------------------------------------
    rules = [*fixed, *negatives, {"text": ctx.get("extra_notes", ""), "source": "user"}]
    travel = _TRAVEL.search(scene_text) or ("environment" in groups and "a location change")
    for r in rules:
        if r["text"] and _STATIONARY.search(r["text"]) and travel:
            moving = travel.group(0) if hasattr(travel, "group") else travel
            rep.flag(f"Conflict: '{r['text']}' keeps the subject stationary, but the story has movement "
                     f"('{moving}').")

    # 8) heroic ending vs open / philosophical ending ----------------------------------------------
    last = beats[-1] if beats else {}
    ending_text = " ".join([story.get("viewer_takeaway", ""), story.get("emotional_progression", ""),
                            story.get("scene_concept", ""), last.get("action", ""), last.get("visual", "")])
    if _OPEN_ENDING.search(ending_text):
        for label, text in (("panel 9 shot", last.get("shot", "")), ("panel 9 title", last.get("title", "")),
                            ("extra instructions", ctx.get("extra_notes", ""))):
            if text and _HEROIC.search(text):
                rep.flag(f"Ending conflict: the {label} ('{text}') implies a heroic payoff, but the story ends "
                         "on an open question. Consider a quieter framing.")

    # 9) generic lesson template contamination (AI projects) ---------------------------------------
    if ctx.get("is_ai"):
        concept = story.get("scene_concept", "").lower()
        if any(s in concept for s in _TEMPLATE_SENTENCES):
            rep.flag("The scene concept contains the generic lesson template text; replace it with this "
                     "story's own concept.")
        for b in beats:
            if b.get("action", "").strip().lower() in _TEMPLATE_ACTIONS or \
                    (b.get("title", "").strip().upper() in _TEMPLATE_TITLES and story.get("story_type") !=
                     "cinematic_fantasy"):
                rep.flag(f"Panel {b['panel']} still contains generic lesson-template text "
                         f"('{b.get('title', '')}'); rewrite it for this story.")

    # 10) reference role vs story subjects ---------------------------------------------------------
    ref = ctx.get("reference") or {}
    if ref.get("enabled"):
        if "character" in ref.get("roles", []) and not story.get("character_present"):
            rep.flag("The reference image is marked as a CHARACTER, but this story has no main character.")
        if "product" in ref.get("roles", []) and not story.get("product_present"):
            rep.flag("The reference image is marked as a PRODUCT, but this story has no product.")
    elif _REFERENCE_WORDS.search(ctx.get("subjects_text", "")) and ctx.get("is_ai"):
        rep.flag("The character/world description mentions a reference image, but no reference image is "
                 "selected. Select the reference role or edit the description.")
    return negatives, locks, fixed, rep

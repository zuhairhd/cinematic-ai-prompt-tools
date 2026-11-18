"""JSON schemas for the AI pipeline plus a small, dependency-free JSON-Schema validator.

The same schema dicts are (a) sent to the model as structured-output schemas (via to_strict())
and (b) enforced locally with validate(), because providers may ignore length/count limits.
"""

from copy import deepcopy

from .constants import STORY_TYPES

STORY_TYPE_KEYS = list(STORY_TYPES)
SUBJECT_KINDS = ["human", "animal", "product", "object", "environment", "abstract"]


def _s(desc, min_len=1):
    return {"type": "string", "description": desc, "minLength": min_len}


def _arr(items, desc, min_items=0, max_items=None):
    a = {"type": "array", "items": items, "description": desc, "minItems": min_items}
    if max_items is not None:
        a["maxItems"] = max_items
    return a


def _obj(props, desc=""):
    return {"type": "object", "description": desc, "properties": props,
            "required": list(props), "additionalProperties": False}


# ---------------------------------------------------------------- creative brief (interpreter)
BRIEF_SCHEMA = _obj({
    "input_language": _s("ISO code of the user's message language, e.g. 'en' or 'ar'"),
    "core_message": _s("The user's intended message in one clear English sentence"),
    "storytelling_objective": _s("What the video must make the viewer feel, understand or do"),
    "target_audience": {"type": "string", "description": "Audience if stated or clearly implied, else ''"},
    "story_type": {"type": "string", "enum": STORY_TYPE_KEYS, "description": "Best narrative approach"},
    "story_type_reason": _s("Why this approach communicates the message best"),
    "genre": _s("Genre / register"),
    "emotional_tone": _s("Emotional tone and how it evolves"),
    "narrative_theme": _s("Underlying theme"),
    "main_subject": _obj({
        "kind": {"type": "string", "enum": SUBJECT_KINDS},
        "description": _s("Who or what the story follows; keep user-specified details verbatim"),
    }),
    "visual_environment": _s("Where the story happens, concrete and visual"),
    "beginning": _s("Opening situation"),
    "progression": _s("How the story develops"),
    "ending": _s("Final image / resolution that lands the message"),
    "viewer_takeaway": _s("The single idea the viewer should leave with"),
    "explicit_requirements": _arr({"type": "string"}, "Every explicit user requirement, preserved exactly"),
    "creative_decisions": _arr({"type": "string"}, "Assumptions you made to fill gaps"),
    "factual_cautions": _arr({"type": "string"},
                             "Real people/brands/events mentioned and how to avoid inventing facts about them"),
}, "Creative brief interpreted from the user's message")

# ---------------------------------------------------------------- storyboard (planner)
BEAT_SCHEMA = _obj({
    "panel": {"type": "integer", "minimum": 1, "maximum": 9, "description": "Panel number 1-9"},
    "title": {"type": "string", "minLength": 2, "maxLength": 40,
              "description": "Short cinematic shot title, 1-5 words, UPPERCASE"},
    "purpose": _s("Narrative purpose of this beat within the structure", 5),
    "shot_type": _s("Shot size, e.g. Extreme wide shot, Close-up, Detail shot", 3),
    "camera": _s("Camera framing, angle, lens feel and movement", 5),
    "visual_description": _s("Concrete, renderable description of everything visible in the frame", 25),
    "action": _s("ONE short, motion-ready action line printed on the panel (max ~18 words)", 8),
    "lighting": _s("Lighting and atmosphere for this panel", 5),
    "continuity_notes": _s("What must match other panels, or what intentionally changes here", 3),
    "transition": {"type": "string",
                   "description": "How this panel leads into the next (e.g. 'match cut on the hand', 'hard cut', "
                                  "'slow dissolve'); '' for panel 9"},
    "relative_weight": {"type": "number", "minimum": 0.3, "maximum": 4.0,
                        "description": "Relative screen time (1.0 = average beat). Python converts to timecodes."},
}, "One storyboard panel")

INTENTIONAL_CHANGE_SCHEMA = _obj({
    "attribute": _s("What changes, e.g. lighting, weather, character expression, product state"),
    "change": _s("From -> to, e.g. 'cold stormy blue -> warm golden sunrise'"),
    "panels": _s("Where it happens, e.g. 'panels 1-4 -> 7-9'"),
})

STORYBOARD_SCHEMA = _obj({
    "title": _s("Short story title"),
    "core_message": _s("The message the storyboard communicates"),
    "story_type": {"type": "string", "enum": STORY_TYPE_KEYS},
    "narrative_structure": _arr({"type": "string"}, "Ordered stage names used for the 9 beats", 3, 9),
    "emotional_goal": _s("Emotional journey for the viewer"),
    "viewer_takeaway": _s("What the viewer should remember"),
    "concept": _s("One-paragraph scene concept of the whole sequence", 40),
    "visual_style": _s("Rendering style, film look, lens and grading", 10),
    "color_palette": _s("Key colors and how they are used"),
    "character": _obj({
        "present": {"type": "boolean", "description": "True if a main human/animal character appears"},
        "name": {"type": "string", "description": "Name or role, '' if none"},
        "description": {"type": "string", "description": "Identity and appearance, '' if none"},
        "outfit": {"type": "string", "description": "Outfit, '' if none"},
        "accessories": {"type": "string", "description": "Accessories, '' if none"},
        "supporting_characters": _arr({"type": "string"}, "Other characters that are allowed to appear"),
    }),
    "product": _obj({
        "present": {"type": "boolean"},
        "name": {"type": "string", "description": "Product name as given by the user, '' if none"},
        "description": {"type": "string", "description": "Exact product appearance, '' if none"},
    }),
    "environment": _obj({
        "location": _s("Location"),
        "description": _s("Concrete environment description", 10),
        "time_of_day": _s("Time of day / weather at the start"),
        "key_objects": _arr({"type": "string"}, "Important recurring objects"),
    }),
    "continuity": _obj({
        "fixed_attributes": _arr({"type": "string"}, "Details that must stay identical in all 9 panels", 3),
        "intentional_changes": _arr(INTENTIONAL_CHANGE_SCHEMA, "Deliberate story-driven changes"),
    }),
    "beats": _arr(BEAT_SCHEMA, "Exactly nine beats in chronological order", 9, 9),
    "avoid": _arr({"type": "string"}, "Story-specific things the image model must avoid"),
}, "Complete nine-beat cinematic storyboard")

# ---------------------------------------------------------------- semantic review (optional)
_RATING = _obj({
    "rating": {"type": "integer", "minimum": 1, "maximum": 5},
    "comment": _s("One or two sentences"),
})
REVIEW_SCHEMA = _obj({
    "message_alignment": _RATING,
    "story_progression": _RATING,
    "visual_clarity": _RATING,
    "scene_consistency": _RATING,
    "ending_strength": _RATING,
    "repetition": _RATING,
    "contradictions": _arr({"type": "string"}, "Contradictory instructions found, if any"),
    "suggestions": _arr({"type": "string"}, "Concrete improvement suggestions", 0, 6),
    "summary": _s("Overall subjective assessment"),
}, "Subjective creative review")

# ---------------------------------------------------------------- validator
_TYPES = {
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "array": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
    "null": lambda v: v is None,
}


def validate(data, schema, path="$"):
    """Validate `data` against the supported JSON-Schema subset. Returns a list of error strings."""
    errs = []
    t = schema.get("type")
    if t:
        types = t if isinstance(t, list) else [t]
        if not any(_TYPES[x](data) for x in types):
            return [f"{path}: expected {'/'.join(types)}, got {type(data).__name__}"]
    if "enum" in schema and data not in schema["enum"]:
        errs.append(f"{path}: {data!r} is not one of {schema['enum']}")
    if isinstance(data, str):
        if len(data.strip()) < schema.get("minLength", 0):
            errs.append(f"{path}: text is empty or too short (min {schema['minLength']} characters)")
        if "maxLength" in schema and len(data) > schema["maxLength"]:
            errs.append(f"{path}: text is too long (max {schema['maxLength']} characters)")
    if _TYPES["number"](data):
        if "minimum" in schema and data < schema["minimum"]:
            errs.append(f"{path}: {data} is below minimum {schema['minimum']}")
        if "maximum" in schema and data > schema["maximum"]:
            errs.append(f"{path}: {data} is above maximum {schema['maximum']}")
    if isinstance(data, list):
        if len(data) < schema.get("minItems", 0):
            errs.append(f"{path}: needs at least {schema['minItems']} items, got {len(data)}")
        if "maxItems" in schema and len(data) > schema["maxItems"]:
            errs.append(f"{path}: allows at most {schema['maxItems']} items, got {len(data)}")
        if "items" in schema:
            for i, item in enumerate(data):
                errs += validate(item, schema["items"], f"{path}[{i}]")
    if isinstance(data, dict):
        props = schema.get("properties", {})
        for k in schema.get("required", []):
            if k not in data:
                errs.append(f"{path}: missing required field '{k}'")
        if schema.get("additionalProperties") is False:
            for k in data:
                if k not in props:
                    errs.append(f"{path}: unexpected field '{k}'")
        for k, sub in props.items():
            if k in data:
                errs += validate(data[k], sub, f"{path}.{k}")
    return errs


_STRICT_UNSUPPORTED = ("minLength", "maxLength", "minItems", "maxItems", "minimum", "maximum")


def to_strict(schema):
    """Copy of `schema` restricted to keywords every structured-output implementation accepts.
    Limits are still enforced locally by validate()."""
    s = deepcopy(schema)

    def walk(node):
        if isinstance(node, dict):
            for k in _STRICT_UNSUPPORTED:
                node.pop(k, None)
            if node.get("type") == "object":
                node["additionalProperties"] = False
                node["required"] = list(node.get("properties", {}))
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(s)
    return s

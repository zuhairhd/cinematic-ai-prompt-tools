"""Project save/load with validation and backward compatibility.

Schema v1 (original app): the flat cfg dict. Schema v2 adds: schema_version, mode, story (AI structure
metadata), ai (original message, creative brief, generated storyboard, model info, validation, review),
storyboard (user-edited structure with timing) and final_prompt. v1 files load unchanged; old app
versions can still open v2 files because all v1 keys are kept at the top level.
Credentials are never written: any key that looks like a secret is removed recursively.
"""

import json
import os
import re
import tempfile
from datetime import datetime, timezone

from . import SCHEMA_VERSION
from .constants import AVOID_DEFAULT, PRESERVE_ITEMS
from .timing import TimingError, check_duration

_SECRET = re.compile(r"(api[_-]?key|secret|token|password|authorization)", re.I)
_STR_KEYS = ("story_title", "model", "character_desc", "concept", "avoid", "style_notes", "extra_notes",
             "final_prompt")
_BEAT_TEXT = ("title", "shot", "action", "purpose", "visual", "camera", "lighting", "continuity")


class ProjectError(ValueError):
    pass


def scrub_secrets(obj):
    if isinstance(obj, dict):
        return {k: scrub_secrets(v) for k, v in obj.items() if not _SECRET.search(str(k))}
    if isinstance(obj, list):
        return [scrub_secrets(v) for v in obj]
    return obj


def normalize_project(data):
    """Validate + upgrade a loaded project dict. Raises ProjectError with a readable message."""
    if not isinstance(data, dict):
        raise ProjectError("The file is not a storyboard project (top level must be a JSON object).")
    ver = data.get("schema_version", 1)
    if not isinstance(ver, int) or ver < 1:
        raise ProjectError(f"Invalid schema_version: {ver!r}.")
    if ver > SCHEMA_VERSION:
        raise ProjectError(f"This project was saved by a newer version of the app (schema {ver}). "
                           f"This version supports up to schema {SCHEMA_VERSION}.")
    beats = data.get("beats")
    if not isinstance(beats, list):
        raise ProjectError("The project has no 'beats' list.")
    if len(beats) != 9:
        raise ProjectError(f"The project must contain exactly 9 beats (found {len(beats)}).")
    clean_beats = []
    for i, b in enumerate(beats, 1):
        if not isinstance(b, dict):
            raise ProjectError(f"Beat {i} is not an object.")
        nb = {}
        for k in _BEAT_TEXT:
            v = b.get(k, "")
            if v is None:
                v = ""
            if not isinstance(v, str):
                raise ProjectError(f"Beat {i}: '{k}' must be text.")
            if k in ("title", "shot", "action") or v:
                nb[k] = v
        w = b.get("weight")
        if w is not None:
            if isinstance(w, bool) or not isinstance(w, (int, float)) or w <= 0:
                raise ProjectError(f"Beat {i}: 'weight' must be a positive number.")
            nb["weight"] = float(w)
        clean_beats.append(nb)
    has_w = [("weight" in b) for b in clean_beats]
    if any(has_w) and not all(has_w):
        for b in clean_beats:
            b.pop("weight", None)
    try:
        duration = check_duration(data.get("duration", 15))
    except TimingError as e:
        raise ProjectError(str(e))
    cfg = {"schema_version": SCHEMA_VERSION, "duration": duration, "beats": clean_beats}
    for k in _STR_KEYS:
        v = data.get(k, "")
        cfg[k] = v if isinstance(v, str) else ("" if v is None else str(v))
    if "avoid" not in data:
        cfg["avoid"] = AVOID_DEFAULT
    cfg["model"] = cfg["model"] or "Seedance 2.0"
    cfg["ref_mode"] = data.get("ref_mode") if data.get("ref_mode") in ("image", "text") else "image"
    pres = data.get("preserve", list(PRESERVE_ITEMS))
    if not isinstance(pres, list) or not all(isinstance(p, str) for p in pres):
        raise ProjectError("'preserve' must be a list of text items.")
    cfg["preserve"] = pres
    cfg["borders"] = bool(data.get("borders", True))
    cfg["mode"] = data.get("mode") if data.get("mode") in ("ai", "manual") else "manual"
    story = data.get("story")
    cfg["story"] = story if isinstance(story, dict) else None
    ai = data.get("ai")
    cfg["ai"] = scrub_secrets(ai) if isinstance(ai, dict) else None
    if cfg["mode"] == "ai" and not cfg["story"]:
        cfg["mode"] = "manual"
    return cfg


def load_project(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ProjectError(f"The file is not valid JSON (line {e.lineno}, column {e.colno}: {e.msg}).")
    except OSError as e:
        raise ProjectError(f"Could not read the file: {e}")
    return normalize_project(data)


def project_payload(cfg, final_prompt=""):
    from .convert import storyboard_document
    data = dict(cfg)
    data["schema_version"] = SCHEMA_VERSION
    data["final_prompt"] = final_prompt or cfg.get("final_prompt", "")
    try:
        data["storyboard"] = storyboard_document(cfg)
    except Exception:  # structure export is informational; never block saving the editable cfg
        data["storyboard"] = None
    data["saved_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return scrub_secrets(data)


def save_project(cfg, path, final_prompt=""):
    data = project_payload(cfg, final_prompt)
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".storyboard_", suffix=".json", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    return data

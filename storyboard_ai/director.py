"""AI Story Director: orchestrates interpreter -> planner -> validator -> cfg, and scene regeneration.

GUI-independent and thread-safe to call from a worker thread (it never touches Tkinter).
"""

from copy import deepcopy

from .ai_provider import AIProviderError
from .constants import STORY_TYPES
from .convert import beat_from_ai, cfg_to_storyboard, storyboard_to_cfg
from .schema import validate as schema_validate
from .story_interpreter import InputError, check_message, interpret
from .storyboard_planner import StoryboardGenerationError, plan, regenerate_scene as _regen
from .storyboard_validator import ai_review
from .timing import check_duration

DEFAULT_SETTINGS = {
    "story_type": "auto", "duration": 15, "visual_style": "Automatic", "audience": "",
    "subject_desc": "", "ref_mode": "image", "output_language": "en", "model": "Seedance 2.0",
}


def normalize_settings(settings):
    s = dict(DEFAULT_SETTINGS)
    s.update({k: v for k, v in (settings or {}).items() if v is not None})
    s["duration"] = check_duration(s["duration"])
    if s["story_type"] not in STORY_TYPES:
        s["story_type"] = "auto"
    if s["ref_mode"] not in ("image", "text"):
        s["ref_mode"] = "image"
    if s["output_language"] not in ("en", "same"):
        s["output_language"] = "en"
    for k in ("audience", "subject_desc", "visual_style", "model"):
        s[k] = str(s[k]).strip()
    return s


class DirectorResult:
    def __init__(self, cfg, brief, storyboard, report, review=None, review_error=None):
        self.cfg, self.brief, self.storyboard = cfg, brief, storyboard
        self.report, self.review, self.review_error = report, review, review_error


class StoryDirector:
    def __init__(self, provider, run_review=True, progress=None, cancel_event=None):
        self.provider = provider
        self.run_review = run_review
        self._progress = progress
        self._cancel = cancel_event

    def _step(self, msg):
        if self._cancel is not None and self._cancel.is_set():
            raise AIProviderError("cancelled", "Generation was cancelled.")
        if self._progress:
            self._progress(msg)

    def generate(self, message, settings, base_cfg=None):
        settings = normalize_settings(settings)
        message = check_message(message)
        self._step("Step 1/3 · Interpreting your message…")
        brief, errs = interpret(self.provider, message, settings)
        if errs:  # one bounded retry for a malformed brief
            self._step("Step 1/3 · Re-reading your message (the first brief was incomplete)…")
            brief, errs = interpret(self.provider, message, settings)
            if errs:
                raise StoryboardGenerationError("The AI could not produce a valid creative brief.", errs)
        self._step("Step 2/3 · Planning nine cinematic beats…")
        sb, report = plan(self.provider, brief, message, settings, progress=self._step)
        review, review_error = None, None
        if self.run_review:
            self._step("Step 3/3 · AI creative review (subjective)…")
            try:
                review = ai_review(self.provider, sb, message)
            except (AIProviderError, ValueError) as e:  # review is optional; never blocks a valid storyboard
                if isinstance(e, AIProviderError) and e.kind == "cancelled":
                    raise
                review_error = str(e)
        self._step("Building the editable storyboard…")
        cfg = storyboard_to_cfg(sb, settings, base_cfg=base_cfg, brief=brief, message=message,
                                provider_info=self.provider.describe(), report=report, review=review)
        return DirectorResult(cfg, brief, sb, report, review, review_error)

    def regenerate_scene(self, cfg, index, note="", settings=None):
        """Return a NEW cfg where only beat `index` is replaced. Timing weight of the scene is kept so
        approved scenes keep their timecodes."""
        settings = normalize_settings(settings or (cfg.get("ai") or {}).get("settings") or
                                      {"duration": cfg.get("duration", 15), "ref_mode": cfg.get("ref_mode")})
        settings["duration"] = check_duration(cfg.get("duration", settings["duration"]))
        self._step(f"Regenerating scene {index + 1}…")
        sb = cfg_to_storyboard(cfg)
        new_beat = _regen(self.provider, sb, index, note, settings)
        out = deepcopy(cfg)
        nb = beat_from_ai(new_beat)
        old_w = cfg["beats"][index].get("weight")
        if old_w is None:
            nb.pop("weight", None)
        else:
            nb["weight"] = old_w
        out["beats"][index] = nb
        if out.get("ai") and isinstance(out["ai"].get("generated_beats"), list) and \
                len(out["ai"]["generated_beats"]) == 9:
            out["ai"]["generated_beats"][index] = dict(nb)
        return out


__all__ = ["StoryDirector", "DirectorResult", "normalize_settings", "InputError", "AIProviderError",
           "StoryboardGenerationError", "schema_validate"]

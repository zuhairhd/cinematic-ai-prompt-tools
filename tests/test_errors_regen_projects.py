"""Invalid AI output, API failures, scene regeneration and project persistence."""

import json
import os

import openai
import pytest

import storyboard_prompt_generator as app
from storyboard_ai.ai_provider import AIProviderError, MockProvider, OpenAIProvider
from storyboard_ai.director import StoryDirector
from storyboard_ai.project_io import ProjectError, load_project, save_project
from storyboard_ai.storyboard_planner import StoryboardGenerationError
import sb_fixtures as F

MSG = "Even during difficult times, there is always hope."


def generated_cfg(**kw):
    sb = F.storyboard(changes=F.HOPE_CHANGES, lighting=F.HOPE_LIGHTING, **kw)
    return StoryDirector(MockProvider([F.brief(), sb]), run_review=False).generate(MSG, {}).cfg


# ---------------------------------------------------------------- 9. invalid AI responses
def test_malformed_json_is_repaired_within_retry_limit():
    prov = MockProvider([F.brief(), '{"title": "broken', F.storyboard()])
    res = StoryDirector(prov, run_review=False).generate(MSG, {})
    assert len(res.cfg["beats"]) == 9
    assert len(prov.calls) == 3 and "FAILED VALIDATION" in prov.calls[2]["user"]


def test_wrong_beat_count_is_repaired():
    bad = F.storyboard()
    bad["beats"] = bad["beats"][:7]
    prov = MockProvider([F.brief(), bad, F.storyboard()])
    res = StoryDirector(prov, run_review=False).generate(MSG, {})
    assert len(res.cfg["beats"]) == 9
    assert "at least 9" in prov.calls[2]["user"]


def test_persistently_invalid_output_fails_without_template_fallback():
    bad = F.storyboard()
    bad["beats"] = bad["beats"][:8]
    prov = MockProvider([F.brief(), bad, bad, bad, F.storyboard()])
    with pytest.raises(StoryboardGenerationError) as ei:
        StoryDirector(prov, run_review=False).generate(MSG, {})
    assert "after 3 attempts" in str(ei.value) and ei.value.errors
    assert len(prov.calls) == 4  # brief + 3 bounded attempts, then stop (no 4th storyboard call)
    assert "OPENING SILENCE" not in ei.value.user_message()


def test_duplicate_scenes_and_empty_fields_are_rejected():
    bad = F.storyboard()
    bad["beats"][5]["visual_description"] = bad["beats"][4]["visual_description"]
    bad["beats"][2]["panel"] = 7
    from storyboard_ai.storyboard_validator import validate_storyboard
    errs = "\n".join(validate_storyboard(bad).errors)
    assert "duplicates panel 5" in errs and "expected 3" in errs


def test_invalid_brief_twice_raises():
    bad = F.brief()
    del bad["core_message"]
    with pytest.raises(StoryboardGenerationError):
        StoryDirector(MockProvider([bad, bad]), run_review=False).generate(MSG, {})


# ---------------------------------------------------------------- 10. API timeout / failures
class FakeResponses:
    def __init__(self, effects):
        self.effects = list(effects)
        self.calls = 0

    def create(self, **kw):
        self.calls += 1
        self.kw = kw
        e = self.effects.pop(0)
        if isinstance(e, Exception):
            raise e
        return e


class FakeClient:
    def __init__(self, effects):
        self.responses = FakeResponses(effects)


class FakeResp:
    status = "completed"
    output = []

    def __init__(self, text):
        self.output_text = text


def _httpx():
    """The OpenAI SDK's HTTP library (httpx, or httpx2 in newer SDK releases)."""
    try:
        import httpx2 as h
    except ImportError:
        import httpx as h
    return h


def _req():
    httpx = _httpx()
    return httpx.Request("POST", "https://api.openai.com/v1/responses")


def _status_err(cls, code, msg="boom"):
    httpx = _httpx()
    return cls(msg, response=httpx.Response(code, request=_req()), body={"error": {"message": msg}})


def test_api_timeout_retries_then_reports_clear_error():
    client = FakeClient([openai.APITimeoutError(request=_req())] * 4)
    sleeps = []
    prov = OpenAIProvider(model="m", client=client, max_retries=3, sleep=sleeps.append)
    with pytest.raises(AIProviderError) as ei:
        prov.generate_json("s", "u", {"type": "object", "properties": {}}, "x")
    assert ei.value.kind == "timeout" and client.responses.calls == 4 and len(sleeps) == 3
    assert "timed out" in ei.value.user_message()


def test_timeout_then_success():
    client = FakeClient([openai.APITimeoutError(request=_req()), FakeResp('{"ok": 1}')])
    prov = OpenAIProvider(model="m", client=client, sleep=lambda s: None)
    assert prov.generate_json("s", "u", {"type": "object", "properties": {}}, "x") == {"ok": 1}
    fmt = client.responses.kw["text"]["format"]
    assert fmt["type"] == "json_schema" and fmt["strict"] is True


def test_rate_limit_then_success_and_auth_not_retried():
    client = FakeClient([_status_err(openai.RateLimitError, 429), FakeResp('{"ok": 2}')])
    assert OpenAIProvider(client=client, sleep=lambda s: None).generate_json("s", "u", {}, "x") == {"ok": 2}
    client = FakeClient([_status_err(openai.AuthenticationError, 401, "bad key")] * 3)
    with pytest.raises(AIProviderError) as ei:
        OpenAIProvider(client=client, sleep=lambda s: None).generate_json("s", "u", {}, "x")
    assert ei.value.kind == "auth" and client.responses.calls == 1


def test_quota_exhausted_not_retried():
    client = FakeClient([_status_err(openai.RateLimitError, 429, "You exceeded your current quota")] * 3)
    with pytest.raises(AIProviderError) as ei:
        OpenAIProvider(client=client, sleep=lambda s: None).generate_json("s", "u", {}, "x")
    assert ei.value.kind == "rate_limit" and client.responses.calls == 1


def test_network_error_classified():
    client = FakeClient([openai.APIConnectionError(request=_req())] * 2)
    with pytest.raises(AIProviderError) as ei:
        OpenAIProvider(client=client, max_retries=1, sleep=lambda s: None).generate_json("s", "u", {}, "x")
    assert ei.value.kind == "network"


def test_missing_api_key_is_a_config_error(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(AIProviderError) as ei:
        OpenAIProvider()
    assert ei.value.kind == "config" and "OPENAI_API_KEY" in ei.value.user_message()


def test_director_propagates_timeout_and_leaves_no_partial_result():
    prov = MockProvider([F.brief(), AIProviderError("timeout", "The AI request timed out.", True)])
    with pytest.raises(AIProviderError) as ei:
        StoryDirector(prov).generate(MSG, {})
    assert ei.value.kind == "timeout"


def test_cancel_between_steps():
    import threading
    ev = threading.Event()
    ev.set()
    with pytest.raises(AIProviderError) as ei:
        StoryDirector(MockProvider([F.brief()]), cancel_event=ev).generate(MSG, {})
    assert ei.value.kind == "cancelled"


# ---------------------------------------------------------------- 11. regenerate one scene
def test_regenerate_one_scene_preserves_everything_else():
    cfg = generated_cfg()
    cfg["beats"][1]["action"] = "USER EDIT: she shields her face."  # approved user edit elsewhere
    before = json.loads(json.dumps(cfg))
    prov = MockProvider([F.new_beat(panel=2)])  # wrong panel number from AI is corrected
    new = StoryDirector(prov).regenerate_scene(cfg, 3, note="make it about her hands")
    assert new["beats"][3]["title"] == "HANDS ON THE COMPASS"
    for i in range(9):
        if i != 3:
            assert new["beats"][i] == before["beats"][i]
    assert new["beats"][3]["weight"] == before["beats"][3]["weight"]  # timing of approved scenes unchanged
    assert app.compute_timecodes(15, [b["weight"] for b in new["beats"]]) == \
        app.compute_timecodes(15, [b["weight"] for b in before["beats"]])
    assert cfg == before  # input not mutated
    user = prov.calls[0]["user"]
    assert "USER EDIT: she shields her face." in user and "APPROVED" in user and "her hands" in user
    assert new["story"] == before["story"]


def test_regenerated_scene_that_duplicates_another_is_repaired():
    cfg = generated_cfg()
    dup = F.new_beat(visual=cfg["beats"][0]["visual"])
    prov = MockProvider([dup, F.new_beat()])
    new = StoryDirector(prov).regenerate_scene(cfg, 3)
    assert new["beats"][3]["visual"] != cfg["beats"][0]["visual"] and len(prov.calls) == 2


def test_failed_scene_regeneration_raises():
    cfg = generated_cfg()
    bad = F.new_beat()
    bad["action"] = ""
    with pytest.raises(StoryboardGenerationError):
        StoryDirector(MockProvider([bad, bad, bad])).regenerate_scene(cfg, 3)


def test_regenerate_scene_in_manual_preset_keeps_lesson_timing():
    cfg = app.default_cfg("Storm at Sea")
    new = StoryDirector(MockProvider([F.new_beat()])).regenerate_scene(cfg, 3)
    assert "weight" not in new["beats"][3]
    assert app.build_prompt(new).count("(0:04.5–0:06)") == 1


# ---------------------------------------------------------------- 12. save + reopen projects
def test_save_and_reopen_generated_project(tmp_path):
    cfg = generated_cfg()
    cfg["ai"]["settings"]["api_key"] = "sk-SHOULD-NOT-BE-SAVED"
    cfg["beats"][0]["action"] = "Edited by the user."
    prompt = app.build_prompt(cfg)
    p = tmp_path / "hope.json"
    save_project(cfg, str(p), final_prompt=prompt)
    raw = p.read_text(encoding="utf-8")
    assert "sk-SHOULD-NOT-BE-SAVED" not in raw and "api_key" not in raw
    data = json.loads(raw)
    assert data["schema_version"] == 3 and data["final_prompt"] == prompt
    assert data["ai"]["original_message"] == MSG and data["ai"]["brief"]["core_message"]
    assert data["ai"]["model"] == "mock-model"
    assert data["storyboard"]["beats"][0]["action"] == "Edited by the user."
    assert data["storyboard"]["beats"][8]["end_seconds"] == 15
    loaded = load_project(str(p))
    assert app.build_prompt(loaded) == prompt
    assert loaded["beats"] == cfg["beats"] and loaded["story"] == cfg["story"]
    assert loaded["final_prompt"] == prompt


def test_legacy_v1_project_still_loads(tmp_path):
    v1 = {"story_title": "Old", "duration": 12, "model": "Kling", "ref_mode": "text", "character_desc": "A monk",
          "concept": "c", "beats": app.default_cfg()["beats"], "preserve": ["outfit"], "avoid": "x",
          "style_notes": "", "borders": False, "extra_notes": ""}
    p = tmp_path / "old.json"
    p.write_text(json.dumps(v1), encoding="utf-8")
    c = load_project(str(p))
    assert c["mode"] == "manual" and c["schema_version"] == 3
    expected = dict(v1)
    assert app.build_prompt(c) == app.build_prompt(expected)


def test_v2_project_remains_readable_by_v1_loader_logic(tmp_path):
    cfg = generated_cfg()
    p = tmp_path / "v2.json"
    save_project(cfg, str(p))
    c = json.load(open(p, encoding="utf-8"))
    assert len(c["beats"]) == 9 and all(k in c["beats"][0] for k in ("title", "shot", "action"))


@pytest.mark.parametrize("content,needle", [
    ("not json", "not valid JSON"),
    ("[]", "JSON object"),
    ('{"beats": []}', "exactly 9 beats"),
    ('{"beats": [1,2,3,4,5,6,7,8,9]}', "not an object"),
    ('{"schema_version": 99, "beats": []}', "newer version"),
])
def test_malformed_projects_report_clear_errors(tmp_path, content, needle):
    p = tmp_path / "bad.json"
    p.write_text(content, encoding="utf-8")
    with pytest.raises(ProjectError) as ei:
        load_project(str(p))
    assert needle in str(ei.value)


def test_project_bad_duration_and_beat_types(tmp_path):
    base = app.default_cfg()
    for mutate, needle in ((lambda c: c.update(duration=0), "between"),
                           (lambda c: c["beats"][2].update(title=5), "must be text"),
                           (lambda c: c["beats"][2].update(weight=-1), "positive")):
        c = json.loads(json.dumps(base))
        mutate(c)
        p = tmp_path / "x.json"
        p.write_text(json.dumps(c), encoding="utf-8")
        with pytest.raises(ProjectError) as ei:
            load_project(str(p))
        assert needle in str(ei.value)


def test_empty_preserve_selection_survives_save_and_load(tmp_path):
    cfg = app.default_cfg()
    cfg["preserve"] = []
    p = tmp_path / "e.json"
    save_project(cfg, str(p))
    loaded = load_project(str(p))
    assert loaded["preserve"] == []
    assert "Preserve the same" not in app.build_prompt(loaded)


def test_save_is_atomic_and_leaves_no_temp_files(tmp_path):
    save_project(app.default_cfg(), str(tmp_path / "a.json"))
    assert os.listdir(tmp_path) == ["a.json"]

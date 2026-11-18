"""End-to-end AI Story Director scenarios with mocked AI responses (no paid API calls)."""

import pytest

import storyboard_prompt_generator as app
from storyboard_ai.ai_provider import MockProvider
from storyboard_ai.director import StoryDirector
from storyboard_ai.storyboard_validator import validate_cfg
from storyboard_ai.timing import compute_timecodes
import sb_fixtures as F


def run(message, brief, sb, settings=None, review=True):
    responses = [brief, sb] + ([F.review()] if review else [])
    prov = MockProvider(responses)
    res = StoryDirector(prov, run_review=review).generate(message, settings or {}, base_cfg=app.default_cfg())
    return res, prov


def common_asserts(res, message):
    cfg = res.cfg
    assert cfg["mode"] == "ai" and len(cfg["beats"]) == 9
    assert all(b["title"] and b["shot"] and b["action"] and b["visual"] and b["camera"] for b in cfg["beats"])
    assert cfg["ai"]["original_message"] == message
    assert validate_cfg(cfg).ok, validate_cfg(cfg).errors
    prompt = app.build_prompt(cfg)
    assert "3x3" in prompt and "exactly 9 panels" in prompt
    for i in range(1, 10):
        assert f"PANEL {i} (" in prompt
    weights = [b["weight"] for b in cfg["beats"]]
    for tc in compute_timecodes(cfg["duration"], weights):
        assert tc in prompt
    assert prompt.index("PANEL 1 (") < prompt.index("PANEL 9 (")
    gs = cfg["ai"]["generated_storyboard"]
    assert gs["beats"][0]["start_seconds"] == 0 and gs["beats"][-1]["end_seconds"] == cfg["duration"]
    return prompt


def test_short_motivational_message():
    msg = "I want viewers to understand that even during difficult times, there is always hope."
    sb = F.storyboard(changes=F.HOPE_CHANGES, lighting=F.HOPE_LIGHTING)
    res, prov = run(msg, F.brief(), sb)
    prompt = common_asserts(res, msg)
    assert res.cfg["story"]["story_type"] == "motivational"
    assert "Keep going; light returns." in prompt
    assert res.review["message_alignment"]["rating"] == 5
    assert [c["schema_name"] for c in prov.calls] == ["creative_brief", "storyboard", "storyboard_review"]
    assert msg in prov.calls[0]["user"]


def test_detailed_cinematic_fantasy():
    msg = ("A lone knight in a silver helm and fur cloak stands on a frozen mountain ridge under an aurora. "
           "Her runed sword starts glowing as an ancient ice dragon awakens and lands before her. She faces it.")
    sb = F.storyboard("cinematic_fantasy", "THE ICE DRAGON", spec=F.FANTASY_SPEC, character={
        "present": True, "name": "The Knight", "description": "Scarred female knight, silver helm",
        "outfit": "Silver plate armor, fur cloak", "accessories": "Runed sword", "supporting_characters": []},
        fixed=["Silver helm and fur cloak", "Runed sword", "Snowy ridge under aurora"])
    res, _ = run(msg, F.brief("cinematic_fantasy", subject="knight"), sb,
                 {"subject_desc": "A lone knight in a silver helm and fur cloak with a runed sword"})
    prompt = common_asserts(res, msg)
    assert "THE ICE DRAGON" in prompt and "Cinematic / fantasy" in prompt


def test_product_advertising_message():
    msg = "Advertise our AquaPure insulated bottle: it keeps water ice cold all day for runners."
    product = {"present": True, "name": "AquaPure", "description": "Matte teal stainless-steel bottle with a "
                                                                   "white wave logo and bamboo lid"}
    sb = F.storyboard("advertising", "STAY COLD", spec=F.AD_SPEC, product=product,
                      fixed=["AquaPure teal bottle with white wave logo", "Runner's outfit", "City running track"])
    res, _ = run(msg, F.brief("advertising", kind="product", subject="AquaPure bottle"), sb,
                 {"subject_desc": "AquaPure: matte teal stainless-steel bottle with a white wave logo"})
    prompt = common_asserts(res, msg)
    assert "Product: AquaPure" in prompt
    assert "redesigning the product" in prompt and "unrelated or invented logos" in prompt
    assert "Advertising / marketing" in prompt


def test_educational_explanation():
    msg = "Explain to kids how photosynthesis works."
    sb = F.storyboard("educational", "HOW LEAVES EAT LIGHT", spec=F.EDU_SPEC,
                      style="Animated 3D feature-film style, soft rounded shapes")
    res, _ = run(msg, F.brief("educational"), sb, {"story_type": "educational", "audience": "children 8-12"})
    prompt = common_asserts(res, msg)
    assert "Educational" in prompt
    assert "cartoon style" not in prompt and "CGI look" not in prompt  # would contradict the chosen style


def test_arabic_story_description():
    msg = "أريد قصة عن أب يعلّم ابنه الصيد على شاطئ البحر عند الغروب، ويتعلم الابن الصبر."
    res, prov = run(msg, F.brief("emotional", lang="ar"), F.storyboard("emotional"))
    common_asserts(res, msg)
    assert res.brief["detected_language"] == "ar"
    assert msg in prov.calls[0]["user"]
    assert "English" in prov.calls[1]["system"]  # default output language English for image models
    # Arabic output requested -> planner instructed to write Arabic
    res2, prov2 = run(msg, F.brief("emotional", lang="ar"), F.storyboard("emotional"), {"output_language": "same"})
    assert "Arabic" in prov2.calls[1]["system"]


def test_story_without_human_character():
    msg = "Show that life always finds a way, even in the driest place."
    sb = F.storyboard("general", "THE DESERT FLOWER", spec=F.SEED_SPEC,
                      character={"present": False, "name": "", "description": "", "outfit": "", "accessories": "",
                                 "supporting_characters": []},
                      fixed=["The same seed/plant", "Cracked desert ground", "Photoreal macro look"])
    res, _ = run(msg, F.brief("general", kind="object", subject="a seed"), sb, {"ref_mode": "text"})
    prompt = common_asserts(res, msg)
    cfg = res.cfg
    assert "character identity" not in cfg["preserve"] and "facial structure" not in cfg["preserve"]
    assert "adding people or characters" in prompt
    assert "redesigning the character" not in prompt and "changing the face" not in prompt
    assert "No main human character" in prompt


def test_story_with_existing_character_reference():
    msg = "Captain Layla flies her old plane through a storm to deliver medicine to a mountain village."
    subject = "Captain Layla, a pilot with a red scarf and silver aviator goggles"
    char = {"present": True, "name": "Captain Layla", "description": "Pilot from the reference image",
            "outfit": "Brown leather flight jacket, red scarf", "accessories": "Silver aviator goggles",
            "supporting_characters": []}
    sb = F.storyboard("cinematic_fantasy", "MEDICINE RUN", character=char,
                      fixed=["Captain Layla's face from the reference image", "Red scarf", "Silver aviator goggles"])
    res, prov = run(msg, F.brief("cinematic_fantasy", subject=subject), sb,
                    {"ref_mode": "image", "reference_roles": ["character"], "subject_desc": subject})
    prompt = common_asserts(res, msg)
    assert "primary visual reference for the main character (Captain Layla)" in prompt
    assert "Captain Layla" in prompt and "reference image takes priority" in prompt
    assert "Environment, lighting, camera angle and composition follow the panel descriptions" in prompt
    assert "reference image" in prov.calls[1]["user"]


def test_character_replacement_is_rejected():
    """No accidental replacement of user-specified characters: a storyboard that renames them is repaired."""
    subject = "Captain Layla, a pilot with a red scarf and silver aviator goggles"
    wrong = F.storyboard()  # 'Mara the fisherwoman' instead of Captain Layla
    char = {"present": True, "name": "Captain Layla", "description": "Pilot with red scarf",
            "outfit": "Leather jacket, red scarf", "accessories": "Silver aviator goggles",
            "supporting_characters": []}
    right = F.storyboard(character=char)
    prov = MockProvider([F.brief(), wrong, right])
    res = StoryDirector(prov, run_review=False).generate("Captain Layla delivers medicine through a storm.",
                                                         {"subject_desc": subject})
    assert res.cfg["story"]["character"]["name"] == "Captain Layla"
    assert "Layla" in prov.calls[2]["user"] and "FAILED VALIDATION" in prov.calls[2]["user"]


def test_intentional_lighting_change_is_not_forbidden():
    msg = "Even during difficult times, there is always hope."
    sb = F.storyboard(changes=F.HOPE_CHANGES, lighting=F.HOPE_LIGHTING)
    res, _ = run(msg, F.brief(), sb)
    cfg = res.cfg
    prompt = app.build_prompt(cfg)
    assert "Intentional story progression" in prompt
    assert "cold blue storm light -> warm golden sunrise" in prompt
    assert "changing the lighting style" not in prompt
    assert "lighting direction" not in cfg["preserve"]
    assert "do not keep these fixed" in prompt
    assert "consistent lighting direction" not in prompt
    assert validate_cfg(cfg).warnings == []
    # If the user re-adds a contradictory rule, it is reported (not silently changed).
    cfg["avoid"] += ", changing the lighting style"
    cfg["preserve"].append("lighting direction")
    warns = validate_cfg(cfg).warnings
    assert len(warns) == 2 and all("lighting" in w for w in warns)


def test_manual_story_type_overrides_ai_choice():
    res, prov = run("Make people laugh about Monday mornings at the office.", F.brief("emotional"),
                    F.storyboard("comedy"), {"story_type": "comedy"}, review=False)
    assert res.brief["story_type"] == "comedy"
    assert "REQUIRED story_type: comedy" in prov.calls[0]["user"]


def test_pacing_weights_drive_timecodes():
    sb = F.storyboard(weights=[0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 2, 3])
    res, _ = run("There is always hope after the storm.", F.brief(), sb, {"duration": 10}, review=False)
    tl = res.cfg["ai"]["generated_storyboard"]["beats"]
    assert tl[-1]["end_seconds"] == 10
    assert tl[8]["end_seconds"] - tl[8]["start_seconds"] > tl[0]["end_seconds"] - tl[0]["start_seconds"]


def test_review_failure_does_not_block_valid_storyboard():
    prov = MockProvider([F.brief(), F.storyboard(), "{not json"])
    res = StoryDirector(prov).generate("Even in hard times there is hope.", {})
    assert res.review is None and "malformed JSON" in res.review_error
    assert len(res.cfg["beats"]) == 9


def test_beat_sheet_md_for_ai_storyboard():
    msg = "Even during difficult times, there is always hope."
    res, _ = run(msg, F.brief(), F.storyboard(changes=F.HOPE_CHANGES))
    md = app.build_beat_sheet_md(res.cfg, res.cfg["story_title"])
    assert "## Original message" in md and msg in md and "## Continuity" in md
    assert md.count("\n| ") >= 10


@pytest.mark.parametrize("bad", ["", "   ", "hope", "a b"])
def test_input_validation(bad):
    from storyboard_ai.story_interpreter import InputError
    with pytest.raises(InputError):
        StoryDirector(MockProvider([])).generate(bad, {})


def test_cli_ai_end_to_end_with_mock(monkeypatch, tmp_path, capsys):
    import storyboard_ai.ai_provider as ap
    responses = [F.brief(), F.storyboard(changes=F.HOPE_CHANGES), F.review()]
    monkeypatch.setattr(ap, "OpenAIProvider", lambda model=None: MockProvider(responses))
    out = tmp_path / "hope.json"
    app.main(["--ai", "There is always hope after the storm", "--duration", "12", "--save", str(out)])
    printed = capsys.readouterr().out
    assert "PANEL 9" in printed and "12-second" in printed
    from storyboard_ai.project_io import load_project
    assert app.build_prompt(load_project(str(out))).strip() == printed.strip()


def test_story_avoid_items_never_forbid_panel_labels():
    sb = F.storyboard(avoid=["on-screen text, titles, or voiceover narration", "readable brand logos"])
    sb["character"]["description"] = "Young fisherwoman, minimal makeup."
    res, _ = run("Even during difficult times, there is always hope.", F.brief(), sb, review=False)
    prompt = app.build_prompt(res.cfg)
    assert "on-screen text" not in prompt and "readable brand logos" in prompt
    assert "makeup.." not in prompt and "short cinematic shot title" in prompt


def test_undecided_visuals_are_flagged():
    from storyboard_ai.storyboard_validator import validate_storyboard
    sb = F.storyboard()
    sb["beats"][0]["visual_description"] += ", choose whichever the reference emphasizes"
    assert any("choose whichever" in w for w in validate_storyboard(sb).warnings)

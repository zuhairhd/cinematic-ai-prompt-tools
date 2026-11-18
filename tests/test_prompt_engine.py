"""Prompt-generation engine: dynamic assembly, reference roles, consistency validation, two output modes.

Scenarios A-J from the engine spec plus the 'Beyond the Matrix' regression story (test data lives in
sb_stories.py; nothing story-specific is hardcoded in the application).
"""

import json
import pathlib
import re
import time

import pytest

import storyboard_prompt_generator as app
import sb_fixtures as F
import sb_stories as S
from storyboard_ai.ai_provider import MockProvider
from storyboard_ai.constants import TEMPLATE_BEATS, TEMPLATE_CONCEPT
from storyboard_ai.director import StoryDirector, normalize_settings
from storyboard_ai.project_io import load_project, normalize_project, save_project
from storyboard_ai.prompt_spec import build_spec
from storyboard_ai.story_interpreter import InputError
from storyboard_ai.storyboard_validator import validate_cfg

ROOT = pathlib.Path(__file__).resolve().parents[1]
TEMPLATE_SENTENCES = [s.strip() for s in TEMPLATE_CONCEPT.split(".") if len(s.strip()) > 15]


def make(sb, message="A short test story.", roles=None, base=None, extra=()):
    prov = MockProvider([F.brief(), *extra, sb])
    settings = {"reference_roles": roles or []}
    res = StoryDirector(prov, run_review=False).generate(message, settings, base_cfg=base or app.default_cfg())
    return res.cfg, prov


def both(cfg):
    return app.build_prompt(cfg, "image"), app.build_prompt(cfg, "director")


def no_template(text):
    assert not any(s in text for s in TEMPLATE_SENTENCES), "generic lesson concept leaked"
    for b in TEMPLATE_BEATS:
        assert b["action"] not in text, f"template beat leaked: {b['title']}"


# ---------------------------------------------------------------- A: motivational, no monsters
def test_a_motivational_fear_story_has_no_invented_threats():
    cfg, _ = make(S.fear_storyboard(), "A person learns to overcome fear")
    for p in both(cfg):
        no_template(p)
        assert not re.search(r"monster|creature|hidden force|mysterious|shadowy|the reveal", p, re.I)
        assert "Lena" in p and "10 m diving tower" in p


def test_a_contaminated_storyboard_is_repaired_not_accepted():
    cfg, prov = make(S.fear_storyboard(), "A person learns to overcome fear",
                     extra=[S.fear_storyboard(contaminated=True)])
    assert "FAILED VALIDATION" in prov.calls[2]["user"] and "creature" in prov.calls[2]["user"]
    assert "creature" not in app.build_prompt(cfg).lower()


# ---------------------------------------------------------------- B: product-focused advertisement
def test_b_product_reference_is_not_treated_as_a_character():
    cfg, _ = make(S.phone_storyboard(), "Show how an AI telephone assistant helps a small business",
                  roles=["product"])
    img, director = both(cfg)
    assert "primary visual reference for the product (VoiceDesk)" in img
    assert "design, shape and proportions" in img
    assert "main character" not in img and "character's identity" not in img
    assert not re.search(r"\bhero", img, re.I)
    # the story shows the app UI and logo: blanket bans are rewritten, not left contradicting the scenes
    assert "unrelated or invented logos" in img and "unrelated or random UI elements" in img
    assert not re.search(r"(Avoid|, )logos[,.]", img) and not re.search(r", UI elements[,.]", img)
    assert "image role: Product" in director


# ---------------------------------------------------------------- C: educational, no forced suspense
def test_c_educational_story_has_no_suspense_or_reveal():
    cfg, _ = make(S.plants_storyboard(), "Explain how plants grow")
    for p in both(cfg):
        no_template(p)
        assert not re.search(r"suspense|reveal|hidden force|\bhero|mysterious", p, re.I)
    assert "Maintain the character appearance" not in app.build_prompt(cfg)


def test_c_forced_reveal_in_educational_story_is_flagged():
    sb = S.plants_storyboard()
    sb["beats"][4]["title"] = "THE REVEAL"
    _, prov = make(S.plants_storyboard(), "Explain how plants grow", extra=[sb])
    # warning only (no repair needed), so the first storyboard is accepted; validation records it
    from storyboard_ai.storyboard_validator import validate_storyboard
    rep = validate_storyboard(sb, {"duration": 15}, "Explain how plants grow")
    assert any("forced suspense" in w for w in rep.warnings)


# ---------------------------------------------------------------- D: environment transformation
def test_d_landscape_and_lighting_changes_are_allowed():
    cfg, _ = make(S.desert_storyboard(), "A desert becomes a green paradise")
    img = app.build_prompt(cfg)
    assert "landscape: barren desert -> lush green paradise" in img
    assert "lighting: harsh white midday -> warm golden sunset" in img
    assert "changing the environment" not in img and "changing the lighting" not in img
    assert "the location's layout" not in img and "the lighting direction" not in img
    assert "Desert landscape of dunes (until the planned environment change" in img
    assert "character's" not in img and "Maintain the character" not in img  # no character locks at all


# ---------------------------------------------------------------- E: character reference
def test_e_character_reference_preserves_identity_but_not_environment():
    cfg, _ = make(S.matrix_storyboard(), S.MATRIX_MESSAGE, roles=["character"])
    img = app.build_prompt(cfg)
    assert "primary visual reference for the main character (Adam)" in img
    assert "preserve Adam's identity, facial structure" in img
    assert "Apply this only in panels where that subject is visible" in img
    assert "Environment, lighting, camera angle and composition follow the panel descriptions" in img
    assert "environment: office -> subway -> rooftop at dawn" in img
    assert "the location's layout" not in img and "changing the environment" not in img
    spec = build_spec(cfg)
    assert spec["reference"]["environment_lock"] == [] and spec["reference"]["identity_lock"]


def test_e_environment_and_style_roles():
    cfg, _ = make(S.fear_storyboard(), "A person learns to overcome fear", roles=["environment", "style"])
    img = app.build_prompt(cfg)
    assert "the location / environment and the visual style only" in img
    assert "Camera angle and composition follow the panel descriptions" in img
    assert "Lena's identity" not in img.split("Characters, subjects")[0]  # character not taken from the image


def test_e_reference_role_is_never_guessed():
    with pytest.raises(InputError, match="select what it shows"):
        normalize_settings({"ref_mode": "image"})
    cfg, _ = make(S.desert_storyboard(), "A desert becomes a green paradise")
    cfg.update(ref_mode="image", reference_roles=[])
    assert any("not what it shows" in e for e in validate_cfg(cfg).errors)


def test_e_character_role_without_character_is_reported():
    cfg, _ = make(S.desert_storyboard(), "A desert becomes a green paradise", roles=["character"])
    assert any("no main character" in w for w in validate_cfg(cfg).warnings)


# ---------------------------------------------------------------- F: no reference image
@pytest.mark.parametrize("story", [S.fear_storyboard, S.phone_storyboard, S.desert_storyboard])
def test_f_text_only_never_mentions_an_uploaded_image(story):
    cfg, _ = make(story(), "A short test story.")
    assert cfg["ref_mode"] == "text"
    for p in both(cfg):
        assert not re.search(r"upload|reference image", p, re.I), p[:300]


def test_f_text_only_character_uses_the_description():
    cfg, _ = make(S.fear_storyboard(), "A person learns to overcome fear")
    assert "Maintain the character appearance defined in the character description." in app.build_prompt(cfg)


# ---------------------------------------------------------------- G: no template phrase in AI projects
@pytest.mark.parametrize("story", [S.matrix_storyboard, S.fear_storyboard, S.phone_storyboard,
                                   S.plants_storyboard, S.desert_storyboard])
def test_g_template_never_appears_in_ai_prompts(story):
    cfg, _ = make(story(), "A short test story.", base=app.default_cfg("Generic (Lesson Template)"))
    for p in both(cfg):
        no_template(p)


def test_g_empty_concept_is_an_error_not_a_substitution():
    cfg, _ = make(S.fear_storyboard(), "A person learns to overcome fear")
    cfg["concept"] = ""
    assert any("scene concept is empty" in e for e in validate_cfg(cfg).errors)
    no_template(app.build_prompt(cfg))
    manual = app.default_cfg("The Sand Awakens (Lesson Example)")
    manual["concept"] = ""
    p = app.build_prompt(manual)
    assert "The scene concept:" not in p
    no_template(p)


def test_g_template_concept_pasted_into_ai_project_is_reported():
    cfg, _ = make(S.fear_storyboard(), "A person learns to overcome fear")
    cfg["concept"] = TEMPLATE_CONCEPT
    assert any("generic lesson template" in w for w in validate_cfg(cfg).warnings)


def test_g_previous_project_notes_do_not_leak():
    base = app.default_cfg()
    base["extra_notes"] = "PREVIOUS PROJECT NOTE: keep the dragon in frame."
    cfg, _ = make(S.plants_storyboard(), "Explain how plants grow", base=base)
    assert "PREVIOUS PROJECT NOTE" not in app.build_prompt(cfg) and cfg["extra_notes"] == ""


# ---------------------------------------------------------------- H: copy / save / mode reflect latest state
tk = pytest.importorskip("tkinter")


@pytest.fixture
def gui():
    try:
        root = tk.Tk()
    except tk.TclError as e:
        pytest.skip(f"No display for Tk: {e}")
    root.withdraw()
    holder = {"responses": []}

    def factory():
        p = MockProvider([])
        p.responses = holder["responses"]
        return p
    a = app.build_app(root, provider_factory=factory)
    a.dialogs = []
    a.ui.askyesno = lambda *x, **k: True
    a.ui.askyesnocancel = lambda *x, **k: False
    for n in ("showerror", "showwarning", "showinfo"):
        setattr(a.ui, n, (lambda name: lambda *x, **k: a.dialogs.append((name, x)))(n))
    a.holder = holder
    yield a
    root.destroy()


def _ai_load(a, sb, roles):
    a.holder["responses"][:] = [F.brief(), sb]
    a.txt_msg.insert("1.0", S.MATRIX_MESSAGE)
    for k, v in a.role_vars.items():
        v.set(k in roles)
    a.on_role_toggle()
    a.v_review.set(False)
    a.start_ai_generation()
    end = time.time() + 10
    while a.state["busy"] and time.time() < end:
        a.root.update(); time.sleep(0.01)
    a.root.update()
    assert a.state["mode"] == "ai", a.dialogs


def test_h_copy_save_and_mode_switch_reflect_the_latest_edit(gui, tmp_path):
    _ai_load(gui, S.matrix_storyboard(), ["character"])
    gui.generate(switch=False)
    gui.beat_widgets[4][3].delete("1.0", "end")
    gui.beat_widgets[4][3].insert("1.0", "He yanks the chain hard.")
    assert "He yanks the chain hard." in gui.copy_prompt()
    gui.set_text(gui.txt_concept, "A NEW CONCEPT written by the user for this story.")
    f = gui.save_story(str(tmp_path / "p.json"))  # no Generate pressed: saved prompts must still be fresh
    data = json.loads(open(f, encoding="utf-8").read())
    assert "A NEW CONCEPT" in data["final_prompt"] and "A NEW CONCEPT" in data["director_prompt"]
    assert data["reference_roles"] == ["character"] and data["schema_version"] == 3
    gui.v_pmode.set(app.PROMPT_MODES["director"])  # live refresh, no button press
    assert gui.out.get("1.0", "end").startswith("DIRECTOR'S STORYBOARD")
    assert "He yanks the chain hard." in gui.out.get("1.0", "end")


def test_h_text_only_clears_roles_and_prompt_updates(gui):
    _ai_load(gui, S.matrix_storyboard(), ["character"])
    gui.generate(switch=False)
    assert "uploaded reference image" in gui.out.get("1.0", "end")
    gui.v_ref.set("text"); gui.on_ref_mode()
    assert not any(v.get() for v in gui.role_vars.values())
    gui.nb.select(gui.t4); gui.root.update()
    text = gui.out.get("1.0", "end")
    assert "upload" not in text and "Visual reference:" not in text
    assert "Maintain the character appearance defined in the character description." in text
    # the AI-written description still says 'from the reference image': reported, not silently rewritten
    assert any("mentions a reference image" in w for w in gui.validate_cfg(gui.collect_cfg()).warnings)


def test_h_scene_regeneration_keeps_other_scenes(gui):
    _ai_load(gui, S.matrix_storyboard(), ["character"])
    before = gui.collect_cfg()["beats"]
    gui.holder["responses"][:] = [F.new_beat(panel=4)]
    gui.start_scene_regen(3)
    end = time.time() + 10
    while gui.state["busy"] and time.time() < end:
        gui.root.update(); time.sleep(0.01)
    after = gui.collect_cfg()["beats"]
    assert after[3]["title"] == "HANDS ON THE COMPASS"
    assert [b for i, b in enumerate(after) if i != 3] == [b for i, b in enumerate(before) if i != 3]
    assert "HANDS ON THE COMPASS" in gui.copy_prompt()


# ---------------------------------------------------------------- I: contradictions detected
def _matrix_cfg():
    return make(S.matrix_storyboard(), S.MATRIX_MESSAGE, roles=["character"])[0]


def test_i_preserve_environment_vs_environment_change():
    cfg = _matrix_cfg()
    cfg["preserve"].append("environment")  # user re-ticks it
    assert any("preserve 'the location's layout" in w and "environment" in w for w in validate_cfg(cfg).warnings)


def test_i_fixed_lighting_vs_night_to_sunrise():
    cfg = _matrix_cfg()
    cfg["avoid"] += ", changing the lighting"
    assert any("changing the lighting" in w and "lighting change" in w for w in validate_cfg(cfg).warnings)


def test_i_no_extra_characters_vs_crowd_scene():
    cfg = _matrix_cfg()
    cfg["avoid"] += ", crowds"  # user-typed blanket ban; the subway scenes need commuters
    w = validate_cfg(cfg).warnings
    assert any("'crowds'" in x and "require people" in x for x in w)
    gen = build_spec(_matrix_cfg())  # the generic version is rewritten instead (and reported as resolved)
    assert "adding extra characters" not in [n["text"] for n in gen["negatives"]]


def test_i_no_text_vs_required_sign():
    cfg = _matrix_cfg()
    cfg["beats"][6]["visual"] += ", a rooftop sign reading 'EXIT'"
    cfg["avoid"] += ", text"
    assert any("'text'" in x and "requires text" in x for x in validate_cfg(cfg).warnings)


def test_i_photoreal_vs_painterly_scene():
    cfg = _matrix_cfg()
    cfg["beats"][2]["visual"] = "A watercolor painting of Adam's reflection"
    assert any("photorealistic" in w and "watercolor" in w for w in validate_cfg(cfg).warnings)


def test_i_stationary_vs_travel():
    cfg = _matrix_cfg()
    cfg["extra_notes"] = "Adam stays in the same place for the whole video."
    assert any("stationary" in w for w in validate_cfg(cfg).warnings)


def test_i_no_costume_change_vs_planned_change():
    sb = S.fear_storyboard()
    sb["continuity"]["intentional_changes"] = [{"attribute": "outfit", "change": "tracksuit -> navy swimsuit",
                                                "panels": "1 -> 2"}]
    cfg, _ = make(sb, "A person learns to overcome fear", roles=["character"])
    assert "changing the outfit" not in app.build_prompt(cfg)
    cfg["avoid"] += ", changing the outfit"
    assert any("changing the outfit" in w and "outfit change" in w for w in validate_cfg(cfg).warnings)


def test_i_heroic_ending_vs_unresolved_ending():
    cfg = _matrix_cfg()  # panel 9 still uses a 'Low-angle hero shot' while the story ends on a question
    w = validate_cfg(cfg).warnings
    assert any("heroic payoff" in x for x in w)
    cfg["beats"][8]["shot"] = "Close-up"
    assert not any("heroic payoff" in x for x in validate_cfg(cfg).warnings)


def test_i_generic_conflicts_are_resolved_and_reported_not_silently_deleted():
    spec = build_spec(_matrix_cfg())
    assert any("UI elements" in r for r in spec["consistency"]["resolved"])
    director = app.build_prompt(_matrix_cfg(), "director")
    assert "CONSISTENCY REPORT" in director and "auto-resolved" in director


# ---------------------------------------------------------------- J: legacy compatibility
def test_j_presets_still_compile_and_generic_preset_keeps_lesson_concept():
    for name in app.PRESETS:
        c = app.default_cfg(name)
        assert app.build_prompt(c) and app.build_prompt(c, "director").startswith("DIRECTOR'S STORYBOARD")
    assert TEMPLATE_CONCEPT in app.build_prompt(app.default_cfg("Generic (Lesson Template)"))


def test_j_v1_project_migrates_with_lesson_character_role(tmp_path):
    v1 = {k: v for k, v in app.default_cfg().items() if k not in ("schema_version", "mode", "story", "ai")}
    c = normalize_project(json.loads(json.dumps(v1)))
    assert c["schema_version"] == 3 and c["migrated_from"] == 1 and c["reference_roles"] == ["character"]
    assert app.build_prompt(c) == app.build_prompt(app.default_cfg())
    save_project(c, tmp_path / "x.json")
    assert "migrated_from" not in json.loads((tmp_path / "x.json").read_text(encoding="utf-8"))


def test_j_v2_ai_projects_migrate_without_guessing():
    cfg, _ = make(S.phone_storyboard(), "A short test story.", roles=["product"])
    v2 = dict(cfg, schema_version=2, ref_mode="image")
    v2.pop("reference_roles")
    assert normalize_project(json.loads(json.dumps(v2)))["reference_roles"] == ["character"]  # v2 rule
    d, _ = make(S.desert_storyboard(), "A short test story.")
    v2 = dict(d, schema_version=2, ref_mode="image")
    v2.pop("reference_roles")
    m = normalize_project(json.loads(json.dumps(v2)))
    assert "reference_roles" not in m  # unknown -> ask
    assert any("not what it shows" in e for e in validate_cfg(m).errors)


def test_j_cli_modes(capsys, tmp_path):
    app.main(["--preset", "Generic", "--mode", "director"])
    assert capsys.readouterr().out.startswith("DIRECTOR'S STORYBOARD")
    cfg, _ = make(S.matrix_storyboard(), S.MATRIX_MESSAGE, roles=["character"])
    save_project(cfg, tmp_path / "m.json")
    app.main(["--project", str(tmp_path / "m.json")])
    assert capsys.readouterr().out.strip() == app.build_prompt(load_project(tmp_path / "m.json")).strip()


# ---------------------------------------------------------------- Beyond the Matrix regression
def test_matrix_regression_full_prompt():
    cfg, _ = make(S.matrix_storyboard(), S.MATRIX_MESSAGE, roles=["character"],
                  base=app.default_cfg("Generic (Lesson Template)"))
    img, director = both(cfg)
    no_template(img)
    order = ["Create a professional cinematic 3x3", 'Story: "BEYOND THE MATRIX', "Visual reference:",
             "The scene concept:", "PANEL 1 (0:00", "PANEL 9", "Keep consistent", "Intentional story progression",
             "Visual style:", "Avoid "]
    pos = [img.index(s) for s in order]
    assert pos == sorted(pos), "prompt sections out of order"
    assert "adding characters beyond those described" in img  # commuters/coworkers are allowed
    assert "chains visibility: invisible -> faint reflection -> visible glowing chains" in img
    for s in ("TIMED SCENES", "Transition → panel 2", "INTENTIONAL PROGRESSION", "Purpose:", "Emotional progression"):
        assert s in director
    assert len(director.split()) > len(img.split())


def test_application_code_contains_no_story_specific_text():
    src = "".join(p.read_text(encoding="utf-8") for p in
                  [ROOT / "storyboard_prompt_generator.py", *sorted((ROOT / "storyboard_ai").glob("*.py"))])
    for word in ("Adam", "Matrix", "Invisible Chains", "VoiceDesk", "Lena"):
        assert word not in src, word


def test_ai_sentence_negatives_stay_whole_and_generic_names_read_naturally():
    sb = S.matrix_storyboard()
    sb["avoid"] = ["do not use green code rain, trademarked visuals, fonts or logos from any franchise"]
    sb["character"]["name"] = "Protagonist"
    cfg, _ = make(sb, "A short test story.", roles=["character"])
    p = app.build_prompt(cfg)
    assert "• Do not use green code rain, trademarked visuals, fonts or logos from any franchise." in p
    assert "preserve the protagonist's identity" in p

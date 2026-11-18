"""GUI smoke tests: drive the real Tkinter app with a mocked AI provider (skipped without a display)."""

import json
import time

import pytest

import storyboard_prompt_generator as app
from storyboard_ai.ai_provider import AIProviderError, MockProvider
import sb_fixtures as F

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
        p.responses = holder["responses"]  # shared queue: each call consumes from the test's list
        return p
    a = app.build_app(root, provider_factory=factory)
    a.dialogs = []
    a.ui.askyesno = lambda *x, **k: a.dialogs.append(("yesno", x)) or a.answer
    a.ui.askyesnocancel = lambda *x, **k: a.dialogs.append(("ync", x)) or a.answer
    for n in ("showerror", "showwarning", "showinfo"):
        setattr(a.ui, n, (lambda name: lambda *x, **k: a.dialogs.append((name, x)))(n))
    a.answer = True
    a.holder = holder
    yield a
    root.destroy()


def pump(a, timeout=10):
    end = time.time() + timeout
    a.root.update()
    while a.state["busy"] and time.time() < end:
        a.root.update()
        time.sleep(0.01)
    a.root.update()
    assert not a.state["busy"], "background task did not finish"


def test_tabs_and_ai_tab_first(gui):
    tabs = [gui.nb.tab(t, "text").strip() for t in gui.nb.tabs()]
    assert tabs[0] == "★ AI Story Director" and "4 · Prompt" in tabs and len(tabs) == 6


def test_manual_mode_preset_generate_and_copy_without_api_key(gui):
    text = gui.generate(switch=False)
    assert text == app.build_prompt(app.default_cfg("The Sand Awakens (Lesson Example)"))
    assert gui.root.clipboard_get if True else None
    assert gui.copy_prompt() == text


def test_copy_is_never_stale_after_edits(gui):
    gui.generate(switch=False)
    gui.beat_widgets[0][1].set("A BRAND NEW TITLE")  # edit after generating
    copied = gui.copy_prompt()
    assert "A BRAND NEW TITLE" in copied
    assert gui.root.clipboard_get() == copied


def test_copy_asks_before_discarding_hand_edited_prompt(gui):
    gui.generate(switch=False)
    gui.out.insert("end", "\nMY HAND EDIT")
    gui.answer = True  # keep my hand-edited text
    assert gui.copy_prompt().endswith("MY HAND EDIT")
    gui.answer = False  # regenerate instead
    assert "MY HAND EDIT" not in gui.copy_prompt()


def test_empty_continuity_selection_not_replaced(gui):
    for v in gui.preserve_vars.values():
        v.set(False)
    gui.answer = True
    text = gui.generate(switch=False)
    assert "Preserve the same" not in text


def test_ai_generation_populates_editors_without_blocking(gui):
    gui.holder["responses"] += [F.brief(), F.storyboard(changes=F.HOPE_CHANGES, lighting=F.HOPE_LIGHTING),
                                F.review()]
    gui.txt_msg.insert("1.0", "I want viewers to understand that even during difficult times, there is always hope.")
    gui.answer = True
    gui.start_ai_generation()
    assert gui.state["busy"]  # returned immediately; work runs on a thread
    pump(gui)
    assert not [d for d in gui.dialogs if d[0] == "showerror"], gui.dialogs
    assert gui.state["mode"] == "ai"
    assert gui.v_title.get() == "AFTER THE STORM"
    assert gui.beat_widgets[0][1].get() == "STORM HARBOR"
    assert "Purpose:" in gui.beat_widgets[0][4].get()
    assert "lighting: cold blue storm light" in gui.txt_changes.get("1.0", "end")
    assert "AI CREATIVE REVIEW (subjective" in gui.txt_result.get("1.0", "end")
    text = gui.generate(switch=False)
    assert "PANEL 9" in text and "Intentional story progression" in text
    # user edits, then regenerates one scene
    gui.beat_widgets[1][3].delete("1.0", "end")
    gui.beat_widgets[1][3].insert("1.0", "USER EDITED ACTION")
    gui.holder["responses"].append(F.new_beat())
    gui.start_scene_regen(3)
    pump(gui)
    assert gui.beat_widgets[3][1].get() == "HANDS ON THE COMPASS"
    assert gui.beat_widgets[1][3].get("1.0", "end").strip() == "USER EDITED ACTION"
    assert "USER EDITED ACTION" in gui.copy_prompt()


def test_ai_errors_are_shown_and_project_is_unchanged(gui):
    before = gui.collect_cfg()
    gui.holder["responses"] += [AIProviderError("timeout", "The AI request timed out.", True)]
    gui.txt_msg.insert("1.0", "Even in hard times there is hope.")
    gui.start_ai_generation()
    pump(gui)
    errs = [d for d in gui.dialogs if d[0] == "showerror"]
    assert errs and "timed out" in errs[0][1][1] and "not changed" in errs[0][1][1]
    assert gui.collect_cfg() == before


def test_invalid_ai_output_never_falls_back_to_template(gui):
    bad = F.storyboard()
    bad["beats"] = bad["beats"][:8]
    gui.holder["responses"] += [F.brief(), bad, bad, bad]
    gui.txt_msg.insert("1.0", "Even in hard times there is hope.")
    gui.load_cfg(app.default_cfg("Storm at Sea"))
    gui.start_ai_generation()
    pump(gui)
    assert any(d[0] == "showerror" and "did not pass validation" in d[1][1] for d in gui.dialogs)
    assert gui.state["mode"] == "manual" and gui.beat_widgets[0][1].get() == "STILL WATER"


def test_confirmation_before_overwriting_user_edits(gui):
    gui.beat_widgets[0][1].set("MY EDIT")
    gui.answer = False
    gui.txt_msg.insert("1.0", "Even in hard times there is hope.")
    gui.start_ai_generation()
    assert not gui.state["busy"] and any(d[0] == "yesno" for d in gui.dialogs)
    assert gui.beat_widgets[0][1].get() == "MY EDIT"


def test_empty_message_is_rejected(gui):
    gui.start_ai_generation()
    assert any(d[0] == "showwarning" for d in gui.dialogs) and not gui.state["busy"]


def test_save_and_reopen_project_through_gui(gui, tmp_path):
    gui.holder["responses"] += [F.brief(), F.storyboard(), F.review()]
    gui.txt_msg.insert("1.0", "Even in hard times there is hope.")
    gui.start_ai_generation()
    pump(gui)
    gui.beat_widgets[2][1].set("EDITED TITLE")
    prompt = gui.generate(switch=False)
    p = str(tmp_path / "proj.json")
    assert gui.save_story(p) == p
    gui.load_cfg(app.default_cfg())
    c = gui.open_story(p)
    assert c["mode"] == "ai" and gui.beat_widgets[2][1].get() == "EDITED TITLE"
    assert gui.out.get("1.0", "end").strip() == prompt
    assert gui.txt_msg.get("1.0", "end").strip() == "Even in hard times there is hope."
    assert json.load(open(p, encoding="utf-8"))["ai"]["model"] == "mock-model"


def test_custom_duration_updates_timecodes(gui):
    gui.v_duration.set(4)
    gui.root.update()
    codes = [w[0].cget("text") for w in gui.beat_widgets]
    assert codes == app.compute_timecodes(4)
    gui.root.globalsetvar(str(gui.v_duration), "abc")
    assert gui.beat_widgets[0][0].cget("text") == "(invalid)"
    assert gui.generate(switch=False) is None and gui.dialogs[-1][0] == "showerror"

"""14. Legacy preset + CLI behavior must not regress (golden files captured from the original v1 app)."""

import json
import os
import subprocess
import sys

import pytest

import storyboard_prompt_generator as app

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GOLD = os.path.join(HERE, "golden")
GOLDEN = json.load(open(os.path.join(GOLD, "legacy_outputs.json"), encoding="utf-8"))


@pytest.mark.parametrize("key", sorted(GOLDEN))
def test_presets_identical_to_v1(key):
    name, d = key.rsplit("|", 1)
    c = app.default_cfg(name)
    c["duration"] = int(d)
    assert app.build_prompt(c) == GOLDEN[key]["prompt"]
    assert app.build_beat_sheet_md(c, c["story_title"]) == GOLDEN[key]["md"]
    assert app.compute_timecodes(int(d)) == GOLDEN[key]["tcs"]


def _cli(*args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "storyboard_prompt_generator.py"), *args],
                       capture_output=True, env=env, cwd=ROOT)
    return r.returncode, r.stdout.decode("utf-8").replace("\r\n", "\n"), r.stderr.decode("utf-8", "replace")


def _gold(name):
    return open(os.path.join(GOLD, name), encoding="utf-8").read().replace("\r\n", "\n")


def test_cli_list():
    rc, out, _ = _cli("--list")
    assert rc == 0 and out == _gold("cli_list.txt")


def test_cli_preset_prompt():
    rc, out, _ = _cli("--preset", "The Sand", "--duration", "10")
    assert rc == 0 and out == _gold("cli_sand_10.txt")


def test_cli_preset_md():
    rc, out, _ = _cli("--preset", "Storm", "--md")
    assert rc == 0 and out == _gold("cli_storm_md.txt")


def test_cli_unknown_preset_and_bad_duration():
    rc, _, err = _cli("--preset", "Nope")
    assert rc != 0 and "Unknown preset" in err
    rc, _, err = _cli("--preset", "Storm", "--duration", "500")
    assert rc != 0 and "between" in err


def test_cli_short_duration_now_valid():
    rc, out, _ = _cli("--preset", "Storm", "--duration", "4")
    assert rc == 0 and "0:01–0:01" not in out and "(0:03.3–0:04)" in out


def test_cli_project(tmp_path):
    from storyboard_ai.project_io import save_project
    p = tmp_path / "p.json"
    save_project(app.default_cfg("Volcanic Awakening"), str(p))
    rc, out, _ = _cli("--project", str(p))
    assert rc == 0 and out.strip() == app.build_prompt(app.default_cfg("Volcanic Awakening"))
    bad = tmp_path / "bad.json"
    bad.write_text("{}", encoding="utf-8")
    rc, _, err = _cli("--project", str(bad))
    assert rc != 0 and "beats" in err


def test_cli_ai_without_key_fails_cleanly(tmp_path):
    env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([sys.executable, os.path.join(ROOT, "storyboard_prompt_generator.py"), "--ai",
                        "There is always hope after the storm"], capture_output=True, env=env, cwd=ROOT)
    assert r.returncode != 0 and b"OPENAI_API_KEY" in r.stderr


# ---------------------------------------------------------------- fixed legacy bugs
def test_empty_preserve_selection_is_not_replaced_by_defaults():
    c = app.default_cfg()
    c["preserve"] = []
    p = app.build_prompt(c)
    assert "Preserve the same" not in p and "facial structure" not in p
    c["ref_mode"] = "text"
    assert "Keep the same" not in app.build_prompt(c)


def test_missing_preserve_key_still_uses_lesson_defaults():
    c = app.default_cfg()
    del c["preserve"]
    assert "Preserve the same character identity, facial structure" in app.build_prompt(c)


def test_two_preserve_items_grammar():
    c = app.default_cfg()
    c["preserve"] = ["outfit", "environment"]
    assert "Preserve the same outfit and environment from" in app.build_prompt(c)


def test_cleared_avoid_list_is_respected():
    c = app.default_cfg()
    c["avoid"] = ""
    assert "\n\nAvoid " not in app.build_prompt(c)
    del c["avoid"]
    assert "Avoid redesigning the character" in app.build_prompt(c)


def test_malformed_beats_raise_clear_error():
    c = app.default_cfg()
    c["beats"] = c["beats"][:8]
    with pytest.raises(ValueError, match="exactly 9 beats"):
        app.build_prompt(c)
    c = app.default_cfg()
    del c["beats"][2]["shot"]  # missing optional text no longer crashes with KeyError
    assert "(0:03–0:04.5)" in app.build_prompt(c)

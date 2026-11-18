import pytest

from storyboard_ai.constants import DURATION_CHOICES, MAX_DURATION, MIN_DURATION
from storyboard_ai.schema import BRIEF_SCHEMA, STORYBOARD_SCHEMA, to_strict, validate
from storyboard_ai.timing import (TimingError, compute_timecodes, compute_timeline, fmt_time,
                                  validate_timeline)
import sb_fixtures as F


# ---------------------------------------------------------------- 13. all supported durations
@pytest.mark.parametrize("duration", range(MIN_DURATION, MAX_DURATION + 1))
def test_every_duration_gives_valid_timeline(duration):
    for weights in (None, [1] * 9, [0.3, 4, 0.3, 4, 0.3, 4, 0.3, 4, 0.3], [4] * 8 + [0.3]):
        tl = compute_timeline(duration, weights)
        assert validate_timeline(tl, duration) == []
        assert tl[0]["start"] == 0 and tl[-1]["end"] == duration
        assert all(b["length"] > 0 for b in tl)
        starts = [b["timecode"].split("–")[0] for b in tl]
        assert len(set(starts)) == 9  # displayed starts strictly distinct


def test_lesson_15s_timing_unchanged():
    assert compute_timecodes(15) == ['0:00–0:01.5', '0:01.5–0:03', '0:03–0:04.5', '0:04.5–0:06', '0:06–0:07.5',
                                     '0:07.5–0:09', '0:09–0:10.5', '0:10.5–0:12.5', '0:12.5–0:15']


@pytest.mark.parametrize("d", DURATION_CHOICES)
def test_standard_choices_use_half_second_grid(d):
    for b in compute_timeline(d):
        assert (b["start"] * 2).is_integer() and (b["end"] * 2).is_integer()


def test_short_clips_no_longer_produce_zero_length_panels():
    # The original implementation displayed "0:01–0:01" for 4 s.
    for d in (3, 4):
        codes = compute_timecodes(d)
        assert all(a != b for a, b in (c.split("–") for c in codes)), codes


@pytest.mark.parametrize("bad", [0, 2, 121, -5, "abc", 7.5, None, True])
def test_invalid_durations_rejected(bad):
    with pytest.raises(TimingError):
        compute_timeline(bad)


def test_invalid_weights_rejected():
    with pytest.raises(TimingError):
        compute_timeline(15, [1] * 8)
    with pytest.raises(TimingError):
        compute_timeline(15, [1] * 8 + [0])
    with pytest.raises(TimingError):
        compute_timeline(15, [1] * 8 + ["x"])


def test_validate_timeline_detects_problems():
    tl = compute_timeline(10)
    tl[3] = dict(tl[3], end=tl[3]["start"])
    errs = validate_timeline(tl, 10)
    assert any("non-positive" in e for e in errs)
    tl = compute_timeline(10)
    tl[5] = dict(tl[5], start=tl[5]["start"] + 0.5)
    assert any("gap" in e for e in validate_timeline(tl, 10))
    assert any("ends at" in e for e in validate_timeline(compute_timeline(10), 12))


def test_fmt_time():
    assert fmt_time(0) == "0:00"
    assert fmt_time(1.5) == "0:01.5"
    assert fmt_time(65) == "1:05"
    assert fmt_time(0.3, 0.1) == "0:00.3"


# ---------------------------------------------------------------- schema
def test_valid_fixture_passes_schema():
    assert validate(F.storyboard(), STORYBOARD_SCHEMA) == []
    assert validate(F.brief(), BRIEF_SCHEMA) == []


def test_schema_catches_structural_errors():
    sb = F.storyboard()
    sb["beats"] = sb["beats"][:8]
    del sb["continuity"]["fixed_attributes"]
    sb["story_type"] = "opera"
    sb["beats"][0]["action"] = ""
    sb["extra"] = 1
    errs = "\n".join(validate(sb, STORYBOARD_SCHEMA))
    for needle in ("at least 9", "fixed_attributes", "opera", "too short", "unexpected field 'extra'"):
        assert needle in errs


def test_strict_schema_is_provider_compatible():
    s = to_strict(STORYBOARD_SCHEMA)

    def walk(n):
        if isinstance(n, dict):
            assert not {"minItems", "maxItems", "minLength", "maxLength", "minimum", "maximum"} & set(n)
            if n.get("type") == "object":
                assert n["additionalProperties"] is False
                assert set(n["required"]) == set(n["properties"])
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)
    walk(s)
    assert "minItems" in STORYBOARD_SCHEMA["properties"]["beats"]  # original untouched

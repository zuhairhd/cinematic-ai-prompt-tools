"""Optional REAL API smoke test (costs a few cents). Runs only when explicitly enabled:

    set STORYBOARD_LIVE_API_TEST=1 and OPENAI_API_KEY, then: python -m pytest tests/test_live_api.py -s
"""

import os

import pytest

import storyboard_prompt_generator as app

pytestmark = pytest.mark.skipif(
    os.environ.get("STORYBOARD_LIVE_API_TEST") != "1" or not os.environ.get("OPENAI_API_KEY"),
    reason="live API test disabled (set STORYBOARD_LIVE_API_TEST=1 and OPENAI_API_KEY)")


def test_live_generation_end_to_end():
    from storyboard_ai.ai_provider import OpenAIProvider
    from storyboard_ai.director import StoryDirector
    from storyboard_ai.storyboard_validator import validate_cfg
    res = StoryDirector(OpenAIProvider(), run_review=True, progress=print).generate(
        "I want viewers to understand that even during difficult times, there is always hope.", {"duration": 15})
    assert len(res.cfg["beats"]) == 9 and validate_cfg(res.cfg).ok
    prompt = app.build_prompt(res.cfg)
    assert "PANEL 9" in prompt
    print(prompt)

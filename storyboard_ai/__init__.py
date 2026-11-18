"""AI Story Director for the Timed Storyboard Prompt Generator.

Pipeline:  user message -> story_interpreter (creative brief)
                        -> storyboard_planner (9 structured beats, JSON-schema validated)
                        -> storyboard_validator (deterministic checks + optional AI review)
                        -> convert (storyboard -> editable project cfg, Python-controlled timing)
                        -> prompt_compiler (final 3x3 storyboard image prompt)

The AI only writes the story; Python owns timecodes, validation and prompt compilation.
"""

SCHEMA_VERSION = 2

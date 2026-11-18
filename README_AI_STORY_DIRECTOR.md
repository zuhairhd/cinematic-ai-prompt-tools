# AI Timed Storyboard Prompt Generator

Type a simple message, for example *"I want viewers to understand that even during difficult times,
there is always hope."*, and the app builds a complete, editable 9-panel cinematic storyboard. From that
storyboard it compiles a prompt for a 3x3 timed storyboard image that you can paste into ChatGPT
Images or another image generator.

The original manual workflow, with its presets, nine-beat editor, TXT/MD/JSON export and CLI, still
works without an API key or any extra packages.

## Install & launch

```bat
cd Z:\zuhairhd\Backup\prompt
venv\Scripts\activate
pip install -r requirements.txt          :: openai SDK (only needed for AI mode)
set OPENAI_API_KEY=sk-...                :: or set it permanently in Windows environment variables
python storyboard_prompt_generator.py    :: GUI
```

## Configuration (environment variables, never saved in project files)

| Variable | Purpose | Default |
|---|---|---|
| `OPENAI_API_KEY` | API key for story planning | (required for AI mode) |
| `STORYBOARD_AI_MODEL` | Story-planning LLM (text model, **not** an image model) | `gpt-5-mini` |
| `STORYBOARD_AI_TIMEOUT` | Seconds per request | `120` |
| `STORYBOARD_AI_API` | `responses` (default) or `chat` for Chat-Completions-only compatible servers | `responses` |
| `OPENAI_BASE_URL` | Optional compatible endpoint (read by the OpenAI SDK) | — |

You can also change the model in the GUI field **AI model (story planning)**. The image-generation model
is a separate setting: the prompt names your *video* model (Seedance, Kling, …), and you choose the
image model yourself in ChatGPT.

## Using the GUI

1. **★ AI Story Director** (first tab): write your message in English or Arabic, then adjust the
   optional settings (story type, duration 3–120 s, visual style, audience, character/product
   description, what the reference image shows, storyboard language).
   **Reference image:** choose *No image*, or tick what your uploaded image shows: Character, Product,
   Environment or Style (several are allowed). The app never guesses the role. A character reference
   preserves identity and outfit only; the environment, lighting and composition still follow the scenes.
2. Click **Generate AI Storyboard**. The work runs on a background thread, so the window stays
   responsive, and you can press **Cancel**.
3. The Story, 9 Beats, and Continuity & Style tabs are filled in. You can edit anything. Use
   **Details…** on a beat to edit its visual description, camera, lighting, continuity notes and pacing
   weight.
4. **Regenerate scene** (AI tab) or **AI Regen** on a beat replaces only that panel. The other panels,
   the character and the timing stay the same. You can add an optional note, for example "make it a
   close-up of her hands".
5. Choose the output mode: **Image Generation Prompt — Optimized** (paste it into the image tool) or
   **Director's Storyboard — Detailed** (a production document with purpose, camera, lighting,
   continuity, transitions, timing and a consistency report). Both are compiled from the same project.
6. Click **Generate final prompt**, then **Copy prompt**. Copy, Save and opening the 4 · Prompt tab always
   rebuild the prompt from your current edits. If you edited the prompt text by hand, the app asks which
   version to keep.
7. **Save project / Load project**: JSON schema v3, which stores both prompts. Older v1 and v2 projects
   are upgraded on load.

The app asks for confirmation before anything would overwrite your edits (a new AI storyboard,
loading a preset or project, or regenerating an edited scene).

## CLI

```bat
python storyboard_prompt_generator.py --list
python storyboard_prompt_generator.py --preset "The Sand Awakens" --duration 15 [--md]
python storyboard_prompt_generator.py --project my_story.json [--md]
python storyboard_prompt_generator.py --ai "There is always hope" --duration 15 --save hope.json
     [--story-type motivational] [--style "Anime"] [--audience "teens"] [--subject "..."]
     [--ref-role character|product|environment|style ...] [--lang en|same] [--ai-model gpt-5]
     [--no-review] [--md]
python storyboard_prompt_generator.py --project my_story.json --mode director   :: detailed director's storyboard
```

## How AI generation works

```
message ─► story_interpreter  (LLM #1, JSON schema "creative_brief")
        ─► storyboard_planner (LLM #2, JSON schema "storyboard": 9 beats + continuity)
             └─ deterministic validation ─► on failure: repair prompt with the errors (max 3 attempts)
        ─► optional AI creative review (LLM #3, subjective; shown separately, never blocks)
        ─► convert: Python computes timecodes from relative pacing weights, adapts preserve/avoid lists
        ─► GUI editors (you edit)
        ─► prompt_spec   (Storyboard Prompt Specification built from the current project state)
        ─► prompt_consistency (detects contradictions, resolves them by priority, reports the rest)
        ─► prompt_compiler (pure Python) ─► image prompt | director's storyboard
```

### How the prompt is assembled

Every prompt is built from three layers:

* **A — universal rules:** 9 panels in a 3x3 grid, reading order, the four labels printed on each
  panel, following the sequence, continuity, the selected style, and no unrelated objects or artifacts.
* **B — story content:** title, core message, concept, the nine timed scenes, continuity and
  progression. All of it comes from your project. The generic lesson concept is never substituted:
  an empty concept is a validation error in AI projects, and manual projects simply omit it.
* **C — conditional instructions:** reference-image wording follows the roles you selected. With no
  image, nothing mentions an upload. Product locks appear only when the story has a product, and
  planned changes are never locked.

**Consistency priority:** your explicit instructions come first, then the approved story, then
AI-generated rules, then the generic lesson defaults. A generic rule that contradicts the story is
rewritten or removed, and the change is reported. For example, "UI elements" becomes "unrelated or
random UI elements" when a scene shows an app. A conflict that involves your own instruction is kept
and reported for you to decide. The checks cover:

* preserving the environment vs. a planned location change
* fixed lighting vs. a lighting change
* no extra characters vs. crowd scenes
* no text vs. signs or logos
* photorealistic style vs. painterly scenes
* stationary vs. travel
* no costume change vs. a planned outfit change
* a heroic panel 9 vs. an open ending
* leftover lesson-template text
* a reference role that doesn't match the story

* **Timing:** the AI only suggests relative weights. Python computes every timecode. Panels are
  contiguous, start at 0:00 and end exactly at the selected duration. Rounding can never create a
  zero-length panel.
* **Continuity:** *fixed attributes* must stay identical, while *intentional changes* are planned
  progressions (for example, storm light → sunrise). Lesson preserve and avoid rules that would forbid
  a planned change are removed automatically. If you add them back by hand, the app warns you.
* **Failures:** the app never falls back to the generic template silently. Authentication, timeout,
  network, rate-limit and invalid-output errors are reported clearly, and your project stays unchanged.

## Package layout

| File | Role |
|---|---|
| `storyboard_prompt_generator.py` | GUI (`build_app`), CLI, legacy `build_prompt` / beat sheet |
| `storyboard_ai/ai_provider.py` | Provider abstraction, OpenAI (Responses API, strict JSON schema), retries, `MockProvider` |
| `storyboard_ai/story_interpreter.py` | Message → creative brief, language detection, input checks |
| `storyboard_ai/storyboard_planner.py` | Brief → 9 beats with bounded repair; single-scene regeneration |
| `storyboard_ai/storyboard_validator.py` | Deterministic checks, contradiction checks, optional AI review |
| `storyboard_ai/prompt_spec.py` | Project cfg → Storyboard Prompt Specification (story, reference locks, continuity, timed beats, negatives) |
| `storyboard_ai/prompt_consistency.py` | Contradiction detection and priority-based resolution |
| `storyboard_ai/prompt_compiler.py` | Spec → image prompt or director's storyboard |
| `storyboard_ai/convert.py` | AI storyboard ↔ editable project cfg |
| `storyboard_ai/timing.py` | Deterministic timecodes and validation |
| `storyboard_ai/schema.py` | JSON schemas + dependency-free validator |
| `storyboard_ai/project_io.py` | Project v3 save/load, v1/v2 migration, secret scrubbing, atomic writes |
| `storyboard_ai/director.py` | Orchestration (thread-safe, GUI-independent) |

## Tests

```bat
pip install -r requirements-dev.txt
python -m pytest                     :: mocked AI, no paid calls
set STORYBOARD_LIVE_API_TEST=1 && python -m pytest tests/test_live_api.py -s   :: optional real API smoke test
```

`tests/golden/` holds outputs captured from the original v1 app. The legacy preset and CLI output must
stay byte-identical to them.

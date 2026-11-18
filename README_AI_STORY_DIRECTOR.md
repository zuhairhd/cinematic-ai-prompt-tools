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
   description, reference-image mode, storyboard language).
2. Click **Generate AI Storyboard**. The work runs on a background thread, so the window stays
   responsive, and you can press **Cancel**.
3. The Story, 9 Beats, and Continuity & Style tabs are filled in. You can edit anything. Use
   **Details…** on a beat to edit its visual description, camera, lighting, continuity notes and pacing
   weight.
4. **Regenerate scene** (AI tab) or **AI Regen** on a beat replaces only that panel. The other panels,
   the character and the timing stay the same. You can add an optional note, for example "make it a
   close-up of her hands".
5. Click **Generate final prompt**, then **Copy prompt**. Copy always rebuilds the prompt from your
   current edits. If you edited the prompt text by hand, it asks which version to copy.
6. **Save project / Load project**: JSON schema v2. Projects saved by the old app still load.

The app asks for confirmation before anything would overwrite your edits (a new AI storyboard,
loading a preset or project, or regenerating an edited scene).

## CLI

```bat
python storyboard_prompt_generator.py --list
python storyboard_prompt_generator.py --preset "The Sand Awakens" --duration 15 [--md]
python storyboard_prompt_generator.py --project my_story.json [--md]
python storyboard_prompt_generator.py --ai "There is always hope" --duration 15 --save hope.json
     [--story-type motivational] [--style "Anime"] [--audience "teens"] [--subject "..."]
     [--ref image|text] [--lang en|same] [--ai-model gpt-5] [--no-review] [--md]
```

## How AI generation works

```
message ─► story_interpreter  (LLM #1, JSON schema "creative_brief")
        ─► storyboard_planner (LLM #2, JSON schema "storyboard": 9 beats + continuity)
             └─ deterministic validation ─► on failure: repair prompt with the errors (max 3 attempts)
        ─► optional AI creative review (LLM #3, subjective; shown separately, never blocks)
        ─► convert: Python computes timecodes from relative pacing weights, adapts preserve/avoid lists
        ─► GUI editors (you edit)  ─► prompt_compiler (pure Python) ─► final prompt
```

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
| `storyboard_ai/prompt_compiler.py` | Storyboard cfg → final image prompt |
| `storyboard_ai/convert.py` | AI storyboard ↔ editable project cfg |
| `storyboard_ai/timing.py` | Deterministic timecodes and validation |
| `storyboard_ai/schema.py` | JSON schemas + dependency-free validator |
| `storyboard_ai/project_io.py` | Project v2 save/load, v1 upgrade, secret scrubbing, atomic writes |
| `storyboard_ai/director.py` | Orchestration (thread-safe, GUI-independent) |

## Tests

```bat
pip install -r requirements-dev.txt
python -m pytest                     :: mocked AI, no paid calls
set STORYBOARD_LIVE_API_TEST=1 && python -m pytest tests/test_live_api.py -s   :: optional real API smoke test
```

`tests/golden/` holds outputs captured from the original v1 app. The legacy preset and CLI output must
stay byte-identical to them.

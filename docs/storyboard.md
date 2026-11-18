# Timed Storyboard Prompt Generator (+ AI Story Director)

**File:** `storyboard_prompt_generator.py` · **Package:** `storyboard_ai/`

Builds a prompt for a **cinematic 3×3 timed storyboard**: 9 panels, each with a panel number, a
timecode, a shot title and a one-line action. You paste the prompt into ChatGPT Images (or a similar
tool) to get a storyboard sheet, which then becomes the blueprint for a video model such as
Seedance 2.0, Kling, Veo, Runway or Sora.

## Two ways to use it

### 1. AI Story Director (needs an OpenAI key)
Type one sentence, for example *“Even during difficult times, there is always hope.”* (English or
Arabic). The AI then:
- interprets your message and picks a narrative approach (motivational, advertising, educational,
  documentary, comedy, fantasy, …)
- designs 9 connected beats with shot types, camera, lighting and pacing
- defines continuity: what must stay fixed, and what changes on purpose (for example, storm light → sunrise)
- validates everything, while Python computes the exact timecodes

Then you review and edit, regenerate any single scene, and copy the final prompt. Choose either the
optimized **image-generation prompt** or the detailed **director's storyboard**; both come from the same
project and always reflect your latest edits.

If you will upload a reference image, tick what it shows (Character, Product, Environment or Style).
A character reference keeps the person's identity, but the location and lighting still follow your
scenes. Without an image, the prompt never mentions one.

### 2. Manual mode (no key, no extra packages)
Choose one of the 7 story presets (*The Sand Awakens*, *Storm at Sea*, *Neon City Pursuit*, *Frozen
Forest Guardian*, *Volcanic Awakening*, *Arabian Night Market*, or the generic lesson template).
Edit the concept and the 9 beats, choose what to preserve and avoid, and generate the prompt.

## Install

```bash
pip install -r requirements.txt     # only for AI mode
setx OPENAI_API_KEY "sk-..."        # Windows, AI mode only; reopen the terminal afterwards
python storyboard_prompt_generator.py
```

Optional settings: `STORYBOARD_AI_MODEL` (default `gpt-5-mini`), `STORYBOARD_AI_TIMEOUT`,
`STORYBOARD_AI_API=chat`, `OPENAI_BASE_URL`.

## GUI tabs

| Tab | Purpose |
|---|---|
| ★ AI Story Director | Your message, optional settings, Generate / Regenerate / Regenerate scene, results and AI review |
| 1 · Story | Preset, title, duration (5/8/10/12/15 s or custom 3–120 s), video model, reference image role(s), character/world, concept |
| 2 · 9 Beats | Title, shot type and action per beat. **Details…** edits visual, camera, lighting and pacing; **AI Regen** rewrites one beat |
| 3 · Continuity & Style | Preserve checkboxes, fixed attributes, intentional changes, style notes, avoid list |
| 4 · Prompt | Output mode (image prompt / director's storyboard), generate, copy, save `.txt`, save beat sheet `.md` |
| Lesson Guide | Quick reference for the 9-beat method |

Projects are saved as `.json`. The AI's original message, creative brief, model and edits are all kept,
and API keys are never saved.

## CLI

```bash
python storyboard_prompt_generator.py --list
python storyboard_prompt_generator.py --preset "Storm" --duration 10 [--md]
python storyboard_prompt_generator.py --project my_story.json [--mode director]
python storyboard_prompt_generator.py --ai "There is always hope" --duration 15 --save hope.json
python storyboard_prompt_generator.py --ai "..." --ref-role product          # reference image shows a product
```

## How to use the result

1. In ChatGPT, upload your character (or product) reference image.
2. Paste the prompt and generate. You get a 3×3 storyboard sheet.
3. If continuity breaks, re-upload the **original** image and regenerate with the same prompt.
4. Use the panels and timecodes as the shot list for your video model.

For the technical design, see [README_AI_STORY_DIRECTOR.md](../README_AI_STORY_DIRECTOR.md).

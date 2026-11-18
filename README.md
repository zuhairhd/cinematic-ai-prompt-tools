# Cinematic AI Prompt Tools

**Repository:** https://github.com/zuhairhd/cinematic-ai-prompt-tools

Four Python desktop tools (Tkinter) that write high-quality prompts for AI image, video and chat
models. Every tool has a graphical interface and runs on Windows, macOS and Linux.

| Tool | What it makes | Needs an API key? | Docs |
|---|---|---|---|
| **[Timed Storyboard Prompt Generator](storyboard_prompt_generator.py)** + **AI Story Director** | A 3×3 timed storyboard prompt (9 cinematic beats with timecodes) for GPT Image / ChatGPT Images, as the blueprint for a Seedance/Kling/Veo video. The AI mode turns one sentence into a full storyboard. | Only for AI mode (OpenAI) | [docs/storyboard.md](docs/storyboard.md) · [AI details](README_AI_STORY_DIRECTOR.md) |
| **[Cinematic Character Prompt Builder](cinematic_character_prompt_builder.py)** | A 9:16 cinematic character portrait prompt built with the 9-layer method | No | [docs/character-builder.md](docs/character-builder.md) |
| **[Cinematic Prompt Studio](CinematicPromptStudio/)** | Analyzes a reference image and turns it into a 33-decision shot plan plus an image prompt | Optional (OpenAI or local Ollama) | [docs/cinematic-prompt-studio.md](docs/cinematic-prompt-studio.md) |
| **[War Room Prompt Builder](war_room_prompt_builder.py)** | A “War Room” debate prompt (Arabic or English) for any chatbot: experts argue before they answer | No | [docs/war-room.md](docs/war-room.md) |

## Quick start

1. Install **Python 3.10+** from [python.org](https://www.python.org/downloads/). On Windows, select
   *“Add Python to PATH”* and *“tcl/tk”*. On Linux, also run `sudo apt install python3-tk`.
2. Get the code:
   ```bash
   git clone https://github.com/zuhairhd/cinematic-ai-prompt-tools.git
   cd cinematic-ai-prompt-tools
   python -m venv venv
   venv\Scripts\activate            # Windows   (macOS/Linux: source venv/bin/activate)
   pip install -r requirements.txt  # openai SDK, only needed for the storyboard AI mode
   ```
3. Run a tool:
   ```bash
   python storyboard_prompt_generator.py          # storyboard + AI Story Director
   python cinematic_character_prompt_builder.py   # 9:16 character prompt
   python war_room_prompt_builder.py              # War Room chatbot prompt
   pip install -r CinematicPromptStudio/requirements.txt && python CinematicPromptStudio/app.py
   ```

## Typical workflow (image → storyboard → video)

1. **Character Builder** (or **Prompt Studio** from a reference photo): generate your hero character
   image in ChatGPT Images.
2. **Storyboard Generator**: upload that image in ChatGPT, paste the storyboard prompt, and get a 3×3
   timed storyboard.
3. Use the storyboard as the shot-by-shot blueprint in your video model (Seedance 2.0, Kling, Veo, …).

## API keys

Only the storyboard **AI Story Director** and Prompt Studio's *Analyze* feature call an AI service.
Set your key as an environment variable. Never put it in code or project files.

```bat
setx OPENAI_API_KEY "sk-..."     :: Windows, then open a NEW terminal
export OPENAI_API_KEY="sk-..."   # macOS / Linux
```

All other features work offline without a key.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest                                        # storyboard tools (mocked AI, no paid calls)
cd CinematicPromptStudio && python -m unittest discover -s tests -v
```

## Repository layout

```
storyboard_prompt_generator.py   Storyboard GUI + CLI
storyboard_ai/                   AI Story Director package (interpreter, planner, validator, compiler…)
tests/                           pytest suite + golden files for the storyboard tools
cinematic_character_prompt_builder.py
war_room_prompt_builder.py
CinematicPromptStudio/           Reference-image shot-plan studio (own README.txt, tests, installer)
docs/                            One page per tool
```

## Notes

- These tools **write prompts**. They don't generate images or video themselves.
- The storyboard and character tools follow the method taught in the *IDALL AI* course (Part 2,
  Lessons 1–2). The course material itself is not included in this repository.

## License

[MIT](LICENSE) © 2026 zuhairhd

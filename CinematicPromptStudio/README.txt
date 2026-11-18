CINEMATIC PROMPT STUDIO 1.0.0

A Python desktop app that turns a reference image into an editable cinematic shot plan and a complete image-generation prompt.

WINDOWS: INSTALL IN YOUR REQUESTED FOLDER
1. Install Python 3.10 or newer from https://www.python.org/downloads/windows/ if needed. Include Tcl/Tk and choose Add Python to PATH.
2. Extract the entire ZIP into a normal folder first. Do not run it from inside the ZIP viewer.
3. Make sure your Z: drive is connected. Run as your normal Windows user; mapped drives may disappear when running as Administrator.
4. Double-click INSTALL_TO_Z_DRIVE.cmd.
5. The installer copies the program to Z:\zuhairhd\Backup\prompt, installs Pillow and launches the app.
6. Next time, double-click Z:\zuhairhd\Backup\prompt\START.cmd.

The installer keeps Python's virtual environment on your local disk at %LOCALAPPDATA%\CinematicPromptStudio\venv. Source files are in your requested Z: folder. Existing matching app files are backed up in _previous_install_TIMESTAMP before replacement; unrelated files are left alone.

If the Z: drive is unavailable, reconnect it. You can also install elsewhere from a terminal:
py -3 install_windows.py "C:\Users\YOUR_NAME\CinematicPromptStudio"

FIRST USE
1. Choose image.
2. Open AI connection and choose one provider:
   OpenAI: paste your API key; gpt-4.1 is the initial editable model name. The selected model must accept images and structured output. API access/usage follows your OpenAI account's billing and permissions.
   Ollama (local): use http://localhost:11434 and the exact installed vision-model name. qwen2.5vl:7b is an example, not a model downloaded by this app. Install Ollama and a compatible local vision model separately. A larger capable model may follow the shot-plan schema better. Increase the timeout if needed.
3. Choose Match reference style or Cinematic reinterpretation.
4. Add an optional creative brief, such as: "Use this lighting style for a business owner answering a phone. Keep space on the right for a headline."
5. Set aspect ratio, then Analyze image & build prompt.
6. Review Evidence & estimates. Open 33 shot choices to edit specific instructions, then Apply choice.
7. Copy prompt or Export TXT. Attach your source reference in the image generator yourself.
8. Save project stores editable choices, observations and explanations in JSON. Open project restores them later.

GUIDED OPTIONS (NO IMAGE OR KEY NEEDED)
New guided plan creates a complete 33-decision plan from the lesson defaults (01-Anatomy_of_Realism_Study_Notes.pdf). In 33 shot choices, select a decision, pick from its Choose option list (about 5 options each: lights, lighting patterns, lenses, apertures, distances, grades, grain and more), then Apply choice. The help panel shows the tip for that decision, when to use the option, and which related decisions to re-check. Starter kit applies a coherent lesson setup in one click (Rembrandt 85mm close-up, after-hours split light, 35mm f/4 environmental, friendly loop commercial). You can still type your own instruction instead of an option. Options also work on an analyzed or saved plan.

NO KEY YET?
Open example lets you learn, edit, copy, save and export a complete hand-authored shot plan offline. It is clearly marked as an example; it is never presented as analysis of your upload.

WHAT IT COVERS
Subject, wardrobe, pose, setting, story, framing, placement, camera position, capture format, lens, camera distance, aperture, focus, shutter, ISO, white balance, key source, key direction, light quality, light temperature, lighting pattern, fill, rim, practicals, shadows, catchlights, palette, grade, skin, materials, grain, atmosphere and continuity constraints.

33 fields are required and validated. An incomplete response is rejected rather than padded with silent stock settings. A field can explicitly state an absent element, for example no additional rim light. The prompt compiler includes every completed field. This does not prove all choices are correct or make an image generator deterministic.

PRIVACY AND NETWORK BEHAVIOR
- No network request on launch, image selection, example loading, editing, saving, copying or export.
- Analyze in OpenAI mode sends one resized JPEG and your brief/instructions to https://api.openai.com/v1/responses using your key. The image is limited to a 1600 px long edge and EXIF/GPS metadata is removed. store=false is used; this is not a promise of zero provider retention. Provider policies still apply.
- Analyze in local mode sends to a loopback Ollama address. The app rejects obvious cloud models and remote model metadata. Use a fully local installed model.
- Keys stay in memory for the session, or are read from OPENAI_API_KEY. They are not saved to project files or logs. Settings must be entered again after restart unless the key is supplied through your own environment.
- Saved projects include image filename, dimensions and a hash, but no image bytes or full image path. Keep your source image separately.
- Cancel result discards any later response. It does not abort the provider's computation or guarantee avoidance of charges. No automatic retries are made.
- Installer uses pip to download Pillow; app usage is separate.

TROUBLESHOOTING
Python not found: install Python, including Tcl/Tk, and rerun the installer.
No module named PIL: run the installer again, or pip install -r requirements.txt in your own environment.
HTTP 401: check API key.
HTTP 429: check API quota/billing or retry later.
HTTP 400: the selected model may not support images or the structured schema.
HTTP 404: check model name and account access, or install the named Ollama model.
Local timeout: check Ollama is running; increase timeout; choose a model suitable for your hardware.
Incomplete shot plan: the model missed fields or returned a truncated result; try a stronger compatible vision model. No fake replacement analysis is inserted.
Changing the brief or mode affects the next analysis. After changing only ratio, review crop and distance; after editing a shot choice, review related choices for consistency.

LINUX / MACOS OR YOUR OWN VENV
python3 -m venv .venv
Activate your venv, then:
python -m pip install -r requirements.txt
python app.py
Linux may need your distribution's python3-tk package and a working desktop display.

DEVELOPER CHECKS
python -m unittest discover -s tests -p test_core.py -v
With a desktop display:
python -m unittest discover -s tests -p test_gui.py -v
Core tests use mocked provider responses and a real local HTTP test server. GUI tests exercise the real Tk widgets and successful/error/canceled analysis flows with a fake analyzer. They never call a paid API.

DELIVERY VALIDATION
See TEST_REPORT.txt in this package for the checks run before delivery. Real provider credentials and a Windows Z: drive were not available in the build workspace; Windows installation and real paid/local inference must be verified on your machine.

FILES
app.py                 Native GUI
choices.py             Guided option lists, help, starter kits
core.py                Image preparation, provider clients, validation, compiler, project format
install_windows.py     Windows installation logic
INSTALL_TO_Z_DRIVE.cmd  Installer launcher
START.cmd              App launcher
LEARNING_GUIDE.txt      In-app lesson and exercise
example_project.json   Clearly labeled hand-authored demo
tests/                 Automated verification

This tool writes image prompts. It does not generate images or video and cannot guarantee exact original camera settings, perfect realism or identical faces across generations.

# Cinematic Prompt Studio

**Folder:** `CinematicPromptStudio/` · **Needs:** Python 3.10+, Pillow · **Optional:** OpenAI key or a local Ollama vision model

Turns a **reference image** into an editable **33-decision cinematic shot plan** and a complete
image-generation prompt. The decisions cover subject, wardrobe, pose, setting, framing, lens,
distance, aperture, shutter, ISO, white balance, key/fill/rim light, lighting pattern, practicals,
palette, grade, skin, grain, atmosphere and continuity.

The full manual is in [`CinematicPromptStudio/README.txt`](../CinematicPromptStudio/README.txt),
and the lesson exercise is in [`LEARNING_GUIDE.txt`](../CinematicPromptStudio/LEARNING_GUIDE.txt).

## Install & run

**Any OS (your own venv):**
```bash
cd CinematicPromptStudio
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

**Windows one-click installer:** double-click `INSTALL_TO_Z_DRIVE.cmd`, then use `START.cmd` after
that. The installer targets `Z:\zuhairhd\Backup\prompt` by default. For a different folder, run
`py -3 install_windows.py "C:\path\to\folder"`.

## How to use

1. **Choose image** (your reference photo).
2. **AI connection**: choose **OpenAI** (API key, vision model such as `gpt-4.1`) or **Ollama**
   (`http://localhost:11434` with an installed vision model, for example `qwen2.5vl:7b`).
3. Choose a mode: **Match reference style** or **Cinematic reinterpretation**. You can add a brief
   (*“business owner answering a phone, space on the right for a headline”*).
4. Set the aspect ratio, then click **Analyze image & build prompt**.
5. Review **Evidence & estimates**, adjust any of the **33 shot choices**, then click **Apply choice**.
6. **Copy prompt** or **Export TXT**. **Save project** keeps your edits as JSON.

### No key? No image?
- **New guided plan** builds all 33 decisions from the lesson defaults, with about 5 options per
  decision and tips.
- **Starter kits** set up a coherent look in one click (Rembrandt 85mm close-up, after-hours split
  light, 35mm environmental, friendly commercial).
- **Open example** loads a hand-authored demo project.

## Privacy
There are no network calls except **Analyze**. Images are resized to 1600 px with EXIF/GPS removed
before upload. Keys are never saved, and projects store only an image hash, not the image.

## Tests
```bash
cd CinematicPromptStudio
python -m unittest discover -s tests -v
```

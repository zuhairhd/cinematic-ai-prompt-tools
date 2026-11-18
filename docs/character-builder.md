# Cinematic Character Prompt Builder

**File:** `cinematic_character_prompt_builder.py` · **Needs:** Python + tkinter only (no key, no pip)

Builds a professional **9:16 cinematic character portrait prompt** for GPT Image / ChatGPT Images,
Midjourney or any other image model. It uses the **9-layer method**:

| # | Layer | Example |
|---|---|---|
| 1 | Character identity | a mysterious desert oracle in her 30s |
| 2 | Skin realism | natural pores, subtle freckles, real texture |
| 3 | Fashion styling | layered sand-colored robes, brass jewelry |
| 4 | Emotional energy | calm, quietly powerful gaze |
| 5 | Environment | vast alien dunes |
| 6 | Atmosphere | drifting dust, heat haze |
| 7 | Cinematic lighting | low golden-hour side light |
| 8 | Camera language | 85mm portrait, shallow depth of field |
| 9 | Film genre / reference + negative instructions | epic sci-fi; avoid plastic skin, CGI look… |

## Install & run

```bash
python cinematic_character_prompt_builder.py
```
On Linux you may need `sudo apt install python3-tk`.

## How to use

1. For each layer, you can:
   - **type** your own text,
   - **pick** a ready-made phrase from the drop-down, or
   - click **Help me**, answer simple questions (man/woman, age, outfit, …), then click **Use this**.
2. Optional: **Load example (Desert Oracle)** to see a complete prompt, or **Surprise me** for a
   random combination.
3. Layer 9 (negative instructions) is always included. Use **Also avoid** to add extras such as
   *extra fingers* or *over-smoothed face*.
4. Click **Create Prompt**, then **Copy** or **Save .txt**.
5. Paste the prompt into your image generator. Use the resulting image as the character reference for
   the **Storyboard Generator**.

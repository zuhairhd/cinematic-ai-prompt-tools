"""
Cinematic Character Prompt Builder
----------------------------------
Builds a professional 9:16 cinematic character prompt for GPT Image 2 (or any
image model) using the 9-layer method from IDALL AI - Part 2, Lesson 1.

Each field can be:
  * typed directly,
  * picked from the drop-down list of ready-made phrases, or
  * built with the "Help me" button, which asks simple questions
    (man or woman, age, outfit, etc.) and writes the phrase for you.

Press "Create Prompt" to assemble the final prompt, then Copy or Save it.

Requires only the Python standard library (tkinter). Run:
    python cinematic_character_prompt_builder.py
"""

import random
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

APP_TITLE = "Cinematic Character Prompt Builder - 9:16"

DEFAULT_NEGATIVE = (
    "plastic skin, CGI look, cartoon style, distorted anatomy, blurry face, "
    "random objects, extra characters, text, logos, captions, watermarks, or UI elements"
)
EXTRA_NEGATIVES = [
    "over-smoothed face", "extra fingers", "deformed hands", "doll-like eyes",
    "oversaturated colors", "harsh HDR look", "duplicate faces", "cropped head",
]


# --------------------------------------------------------------------------- #
# Small text helpers
# --------------------------------------------------------------------------- #
def join_words(items):
    """['a','b','c'] -> 'a, b and c'"""
    items = [i.strip() for i in items if i and i.strip()]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def clean(text):
    return " ".join(str(text).split()).strip(" ,.")


def article(word):
    word = word.strip()
    if not word:
        return ""
    return "an" if word[0].lower() in "aeiou" else "a"


def pronoun(gender):
    g = gender.lower()
    if "woman" in g or "girl" in g or "female" in g or "lady" in g:
        return "her"
    if "man" in g or "boy" in g or "male" in g:
        return "his"
    return "their"


# --------------------------------------------------------------------------- #
# Field + helper-wizard definitions
#   Each question: (key, question text, "single" | "multi", [options])
#   Single questions use an editable drop-down (free text allowed).
#   Multi questions use tick boxes plus an "other" box.
# --------------------------------------------------------------------------- #
def compose_identity(a):
    gender = a.get("gender") or "woman"
    role = a.get("role", "")
    # skip the gender word when the role already names it (fisherman, queen...)
    gendered = ("man", "woman", "queen", "king", "lady", "girl", "boy", "prince", "princess")
    noun = "" if role and role.lower().split()[-1].endswith(gendered) else (a.get("gender") or "")
    head = " ".join(x for x in [a.get("descriptor"), role, noun] if x)
    text = f"{article(head)} {head}"
    age = a.get("age")
    if age:
        text += f" in {pronoun(gender)} {age}"
    feats = join_words(a.get("features", []))
    extras = [x for x in [feats, a.get("hair")] if x]
    if extras:
        text += " with " + join_words(extras)
    if a.get("energy"):
        text += (", and " if extras else " with ") + a["energy"]
    return clean(text)


def compose_skin(a):
    parts = list(a.get("texture", []))
    if a.get("tone"):
        parts.insert(0, a["tone"])
    return clean(join_words(parts))


def compose_styling(a):
    garment = a.get("garment") or "outfit"
    head = " ".join(x for x in [a.get("silhouette"), a.get("color"), garment] if x)
    text = f"{article(head)} {head}"
    mats = join_words(a.get("materials", []))
    if mats:
        text += f" of {mats}"
    details = a.get("details", []) + a.get("accessories", [])
    if details:
        text += " with " + join_words(details)
    return clean(text)


def compose_emotion(a):
    text = join_words(a.get("emotions", []))
    if a.get("gaze"):
        text += f", {a['gaze']}" if text else a["gaze"]
    return clean(text)


def compose_environment(a):
    head = " ".join(x for x in [a.get("scale"), a.get("setting")] if x)
    text = f"{article(head)} {head}" if head else ""
    if a.get("time"):
        text += f" at {a['time']}"
    return clean(text)


def compose_atmosphere(a):
    parts = a.get("atmo", []) + a.get("story", [])
    return clean(join_words(parts))


def compose_lighting(a):
    parts = [x for x in [a.get("base"), a.get("key")] if x]
    text = " with ".join(parts) if len(parts) == 2 else (parts[0] if parts else "")
    if a.get("effects"):
        text += (", " if text else "") + join_words(a["effects"])
    return clean(text)


def compose_camera(a):
    parts = []
    if a.get("lens"):
        lens = f"{a['lens']} lens feeling"
        parts.append(f"{article(lens)} {lens}")
    if a.get("framing"):
        parts.append(a["framing"])
    parts += a.get("extras", [])
    return clean(join_words(parts))


def compose_genre(a):
    text = a.get("genre", "")
    if a.get("crossed"):
        text += f" crossed with {article(a['crossed'])} {a['crossed']}"
    if a.get("mood"):
        text += f", with {a['mood']}"
    return clean(text)


FIELDS = [
    {
        "key": "identity", "layer": "1. Character identity",
        "hint": "Age, facial structure, presence and energy",
        "presets": [
            "a mysterious desert oracle woman in her early 30s with sharp elegant facial features and calm powerful energy",
            "a weathered Bedouin falconer man in his late 50s with deep-set eyes, a silver beard and quiet commanding presence",
            "a young cyberpunk courier woman in her mid 20s with high cheekbones, a shaved undercut and restless electric energy",
            "a battle-worn royal knight man in his 40s with a strong jawline, faint scars and stoic heroic presence",
        ],
        "questions": [
            ("gender", "Man or woman?", "single", ["woman", "man", "girl", "boy", "elderly woman", "elderly man", "person"]),
            ("age", "Age?", "single", ["early 20s", "mid 20s", "late 20s", "early 30s", "late 30s", "40s", "50s", "60s", "70s"]),
            ("descriptor", "One word that defines them?", "single",
             ["mysterious", "fierce", "regal", "weathered", "elegant", "rebellious", "wise", "haunted", "young", "battle-worn"]),
            ("role", "Who / what are they?", "single",
             ["desert oracle", "Bedouin falconer", "cyberpunk courier", "royal knight", "space explorer", "street musician",
              "sea captain", "Omani fisherman", "fashion icon", "warrior queen", "detective", "scientist", "monk"]),
            ("features", "Facial features (pick any)", "multi",
             ["sharp elegant facial features", "high cheekbones", "strong jawline", "deep-set eyes", "piercing eyes",
              "freckles", "a short trimmed beard", "a silver beard", "faint scars", "weathered laugh lines", "full lips"]),
            ("hair", "Hair?", "single",
             ["long dark flowing hair", "a tight braid", "short cropped hair", "a shaved head", "curly windswept hair",
              "silver hair tied back", "hair hidden under a head wrap", "a shaved undercut"]),
            ("energy", "Presence / energy?", "single",
             ["calm powerful energy", "quiet commanding presence", "restless electric energy", "stoic heroic presence",
              "gentle warm energy", "dangerous predatory calm", "regal untouchable aura"]),
        ],
        "compose": compose_identity,
    },
    {
        "key": "skin", "layer": "2. Skin realism",
        "hint": "Pores, texture, imperfections, highlights",
        "presets": [
            "visible pores, natural skin texture, subtle imperfections and soft glossy highlights",
            "sun-kissed skin with visible pores, fine freckles, subtle imperfections and realistic shadows",
            "weathered skin with deep natural texture, visible pores, fine lines and a light sweat sheen",
        ],
        "questions": [
            ("tone", "Skin tone?", "single",
             ["fair skin", "olive skin", "warm tan skin", "golden brown skin", "deep brown skin", "dark ebony skin", "sun-kissed skin"]),
            ("texture", "Realism details (pick several)", "multi",
             ["visible pores", "natural skin texture", "subtle imperfections", "soft glossy highlights", "realistic shadows",
              "fine freckles", "fine lines", "light stubble", "a light sweat sheen", "faint scars", "peach fuzz catching the light"]),
        ],
        "compose": compose_skin,
    },
    {
        "key": "styling", "layer": "3. Fashion styling",
        "hint": "Materials, silhouette, colours, accessories, details",
        "presets": [
            "a sculptural ivory desert cloak of heavy textured linen and translucent layered fabric with sand-worn edges and minimal antique gold jewelry",
            "a structured black trench coat of matte leather and wool with brushed steel buckles and a high collar",
            "an elegant flowing emerald gown of silk and chiffon with hand embroidery and delicate pearl earrings",
        ],
        "questions": [
            ("silhouette", "Silhouette / cut?", "single",
             ["sculptural", "flowing", "structured", "oversized", "tailored", "layered", "minimal", "armored"]),
            ("color", "Main colour?", "single",
             ["ivory", "black", "deep crimson", "emerald", "sand-beige", "midnight blue", "charcoal", "burnt orange", "white", "olive"]),
            ("garment", "Main garment?", "single",
             ["desert cloak", "trench coat", "gown", "tailored suit", "dishdasha", "abaya", "kaftan", "flight suit",
              "leather jacket", "armor", "hooded robe", "kimono"]),
            ("materials", "Materials (pick any)", "multi",
             ["heavy textured linen", "translucent layered fabric", "matte leather", "raw silk", "chiffon", "wool",
              "brushed metal plates", "denim", "velvet", "technical nylon", "hand-woven cotton"]),
            ("details", "Details (pick any)", "multi",
             ["sand-worn edges", "hand embroidery", "a high collar", "frayed hems", "geometric patterns",
              "visible stitching", "subtle wear and dust", "glowing seams", "pleated folds"]),
            ("accessories", "Accessories (pick any)", "multi",
             ["minimal antique gold jewelry", "a silver khanjar", "delicate pearl earrings", "a leather belt with pouches",
              "a falcon glove", "round sunglasses", "a woven head wrap", "rings on every finger", "a wristwatch"]),
        ],
        "compose": compose_styling,
    },
    {
        "key": "emotion", "layer": "4. Emotional energy",
        "hint": "The expression that gives presence",
        "presets": [
            "calm, confident and mysterious",
            "fierce and determined, looking straight into the camera",
            "melancholic and vulnerable, gazing into the distance",
        ],
        "questions": [
            ("emotions", "Emotion (pick 2-3)", "multi",
             ["calm", "confident", "mysterious", "powerful", "vulnerable", "elegant", "fierce", "melancholic",
              "determined", "serene", "defiant", "playful", "haunted"]),
            ("gaze", "Gaze?", "single",
             ["looking straight into the camera", "gazing into the distance", "eyes half-closed", "glancing over the shoulder",
              "looking down in thought"]),
        ],
        "compose": compose_emotion,
    },
    {
        "key": "environment", "layer": "5. Environment",
        "hint": "The world that turns a portrait into a scene",
        "presets": [
            "a massive alien desert",
            "a rain-soaked neon city street at night",
            "the ruins of an ancient Omani mountain fort",
            "a windswept ocean cliff at dawn",
        ],
        "questions": [
            ("scale", "Scale?", "single", ["massive", "vast", "intimate", "towering", "endless", "abandoned"]),
            ("setting", "Where?", "single",
             ["alien desert", "neon city street", "ancient Omani fort", "ocean cliff", "snowy mountain pass",
              "spaceship interior", "misty forest", "old souq alley", "salt flat", "palace hall", "wadi canyon"]),
            ("time", "Time / weather?", "single",
             ["golden hour", "sunset", "dawn", "night", "blue hour", "a stormy afternoon", "midday heat"]),
        ],
        "compose": compose_environment,
    },
    {
        "key": "atmosphere", "layer": "5b. Atmosphere & story details",
        "hint": "Haze, particles and story props in the scene",
        "presets": [
            "golden haze, monumental dunes and faint futuristic ruins",
            "drifting fog, glowing puddle reflections and distant holographic signs",
            "swirling sand, scattered ancient pottery and a lone falcon circling above",
        ],
        "questions": [
            ("atmo", "Atmosphere (pick any)", "multi",
             ["golden haze", "drifting sand", "rolling fog", "light rain", "falling snow", "floating dust",
              "drifting embers", "low clouds", "steam rising"]),
            ("story", "Story details (pick any)", "multi",
             ["monumental dunes", "faint futuristic ruins", "distant mountains", "a lone falcon circling above",
              "abandoned machinery", "glowing puddle reflections", "ancient carvings", "a distant caravan",
              "towering stone pillars", "wind-blown fabric"]),
        ],
        "compose": compose_atmosphere,
    },
    {
        "key": "lighting", "layer": "6. Cinematic lighting",
        "hint": "Golden hour, rim light, shadows, dust, reflections",
        "presets": [
            "golden hour light with a warm rim light, dust particles and soft contrast",
            "moody neon night light with a cool blue backlight, wet reflections and high contrast",
            "soft overcast light with gentle wrap-around shadows",
        ],
        "questions": [
            ("base", "Main light?", "single",
             ["golden hour light", "blue hour light", "soft overcast light", "moody neon night light", "cold moonlight",
              "harsh midday sun", "warm candlelight", "stormy diffused light"]),
            ("key", "Light on the character?", "single",
             ["a warm rim light", "a soft key light", "a dramatic side light", "a strong backlight", "a cool blue backlight",
              "Rembrandt lighting"]),
            ("effects", "Effects (pick any)", "multi",
             ["dust particles", "reflections", "high contrast", "soft contrast", "volumetric light rays",
              "subtle lens flare", "deep shadows", "glowing haze"]),
        ],
        "compose": compose_lighting,
    },
    {
        "key": "camera", "layer": "7. Camera language",
        "hint": "Lens, framing, depth of field, composition",
        "presets": [
            "a 35mm lens feeling with editorial framing, shallow depth of field and cinematic composition",
            "an 85mm lens feeling, close-up portrait framing, creamy bokeh and subtle film grain",
            "a 24mm lens feeling, low-angle full-body hero shot and deep cinematic composition",
        ],
        "questions": [
            ("lens", "Lens?", "single", ["24mm", "35mm", "50mm", "85mm", "135mm", "anamorphic"]),
            ("framing", "Framing?", "single",
             ["editorial framing", "full-body shot", "medium shot", "close-up portrait framing",
              "low-angle hero shot", "over-the-shoulder shot"]),
            ("extras", "Extras (pick any)", "multi",
             ["shallow depth of field", "cinematic composition", "creamy bokeh", "subtle film grain",
              "rule-of-thirds placement", "anamorphic bokeh", "slight motion in fabric"]),
        ],
        "compose": compose_camera,
    },
    {
        "key": "genre", "layer": "8. Film genre / reference",
        "hint": "What film or style it should feel like",
        "presets": [
            "a high-budget sci-fi film still crossed with a luxury fashion editorial",
            "a neo-noir thriller film still",
            "an epic fantasy film still with painterly realism",
        ],
        "questions": [
            ("genre", "Genre?", "single",
             ["high-budget sci-fi film still", "epic fantasy film still", "neo-noir thriller film still",
              "period drama film still", "post-apocalyptic film still", "documentary photograph", "luxury fashion editorial"]),
            ("crossed", "Crossed with?", "single",
             ["luxury fashion editorial", "documentary photograph", "National Geographic portrait", "music video frame",
              "magazine cover shoot"]),
            ("mood", "Overall look?", "single",
             ["painterly realism", "muted earthy palette", "teal and orange grade", "desaturated cold palette",
              "rich warm palette"]),
        ],
        "compose": compose_genre,
    },
]


# --------------------------------------------------------------------------- #
# Helper wizard dialog
# --------------------------------------------------------------------------- #
class HelperDialog(tk.Toplevel):
    def __init__(self, master, field, on_done):
        super().__init__(master)
        self.field = field
        self.on_done = on_done
        self.title(f"Help: {field['layer']}")
        self.transient(master)
        self.grab_set()
        self.resizable(True, True)

        outer = ttk.Frame(self, padding=14)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text=field["layer"], style="H.TLabel").pack(anchor="w")
        ttk.Label(outer, text="Answer what you like. Drop-downs also accept your own text.",
                  foreground="#666").pack(anchor="w", pady=(0, 8))

        self.single_vars, self.multi_vars, self.other_vars = {}, {}, {}
        for key, question, kind, options in field["questions"]:
            box = ttk.LabelFrame(outer, text=question, padding=8)
            box.pack(fill="x", pady=4)
            if kind == "single":
                var = tk.StringVar()
                cb = ttk.Combobox(box, textvariable=var, values=options, width=60)
                cb.pack(fill="x")
                var.trace_add("write", lambda *_: self.update_preview())
                self.single_vars[key] = var
            else:
                grid = ttk.Frame(box)
                grid.pack(fill="x")
                vars_ = []
                for i, opt in enumerate(options):
                    v = tk.BooleanVar()
                    ttk.Checkbutton(grid, text=opt, variable=v, command=self.update_preview).grid(
                        row=i // 3, column=i % 3, sticky="w", padx=4, pady=1)
                    vars_.append((opt, v))
                self.multi_vars[key] = vars_
                row = ttk.Frame(box)
                row.pack(fill="x", pady=(4, 0))
                ttk.Label(row, text="Other (comma separated):").pack(side="left")
                ov = tk.StringVar()
                ttk.Entry(row, textvariable=ov).pack(side="left", fill="x", expand=True, padx=4)
                ov.trace_add("write", lambda *_: self.update_preview())
                self.other_vars[key] = ov

        ttk.Label(outer, text="Result:", style="B.TLabel").pack(anchor="w", pady=(8, 0))
        self.preview = tk.Text(outer, height=3, wrap="word", font=("Segoe UI", 10), background="#f6f4ee")
        self.preview.pack(fill="x")

        btns = ttk.Frame(outer)
        btns.pack(fill="x", pady=(10, 0))
        ttk.Button(btns, text="Use this", style="Accent.TButton", command=self.apply).pack(side="right")
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right", padx=6)
        self.update_preview()

    def answers(self):
        a = {k: clean(v.get()) for k, v in self.single_vars.items()}
        for k, opts in self.multi_vars.items():
            picked = [o for o, v in opts if v.get()]
            other = [clean(x) for x in self.other_vars[k].get().split(",") if clean(x)]
            a[k] = picked + other
        return a

    def update_preview(self):
        text = self.field["compose"](self.answers())
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", text)

    def apply(self):
        text = clean(self.preview.get("1.0", "end"))
        if not text:
            messagebox.showwarning("Nothing selected", "Answer at least one question first.", parent=self)
            return
        self.on_done(text)
        self.destroy()


# --------------------------------------------------------------------------- #
# Main application
# --------------------------------------------------------------------------- #
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1100x860")
        self.minsize(900, 700)
        self._style()

        main = ttk.Frame(self, padding=14)
        main.pack(fill="both", expand=True)

        ttk.Label(main, text="Cinematic Character Prompt Builder", style="Title.TLabel").pack(anchor="w")
        ttk.Label(main, text="Type, pick from the list, or press  Help me  to answer simple questions. "
                             "Then press  Create Prompt.", foreground="#555").pack(anchor="w", pady=(0, 10))

        form = ttk.Frame(main)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)

        self.vars = {}
        for r, f in enumerate(FIELDS):
            lab = ttk.Frame(form)
            lab.grid(row=r, column=0, sticky="nw", padx=(0, 10), pady=4)
            ttk.Label(lab, text=f["layer"], style="B.TLabel").pack(anchor="w")
            ttk.Label(lab, text=f["hint"], foreground="#777", font=("Segoe UI", 8)).pack(anchor="w")
            var = tk.StringVar()
            ttk.Combobox(form, textvariable=var, values=f["presets"]).grid(row=r, column=1, sticky="ew", pady=4)
            ttk.Button(form, text="Help me", command=lambda f=f: self.open_helper(f)).grid(
                row=r, column=2, padx=(8, 0), pady=4)
            self.vars[f["key"]] = var

        # Negative instructions
        neg = ttk.LabelFrame(main, text="9. Negative instructions (always included)", padding=8)
        neg.pack(fill="x", pady=(10, 0))
        ttk.Label(neg, text="Avoid " + DEFAULT_NEGATIVE + ".", wraplength=1000, foreground="#444").pack(anchor="w")
        extra_row = ttk.Frame(neg)
        extra_row.pack(fill="x", pady=(4, 0))
        self.neg_vars = []
        for i, item in enumerate(EXTRA_NEGATIVES):
            v = tk.BooleanVar(value=item == "over-smoothed face")
            ttk.Checkbutton(extra_row, text=item, variable=v).grid(row=0 if i < 4 else 1, column=i % 4, sticky="w", padx=4)
            self.neg_vars.append((item, v))
        row = ttk.Frame(neg)
        row.pack(fill="x", pady=(4, 0))
        ttk.Label(row, text="Also avoid:").pack(side="left")
        self.neg_other = tk.StringVar()
        ttk.Entry(row, textvariable=self.neg_other).pack(side="left", fill="x", expand=True, padx=4)

        # Action buttons
        actions = ttk.Frame(main)
        actions.pack(fill="x", pady=10)
        ttk.Button(actions, text="Create Prompt", style="Accent.TButton", command=self.create).pack(side="left")
        ttk.Button(actions, text="Load example (Desert Oracle)", command=self.load_example).pack(side="left", padx=6)
        ttk.Button(actions, text="Surprise me", command=self.randomize).pack(side="left")
        ttk.Button(actions, text="Clear", command=self.clear).pack(side="left", padx=6)
        ttk.Button(actions, text="Save .txt", command=self.save).pack(side="right")
        ttk.Button(actions, text="Copy", command=self.copy).pack(side="right", padx=6)

        self.output = tk.Text(main, wrap="word", font=("Consolas", 11), height=12,
                              background="#1e1e1e", foreground="#f0e6d2", insertbackground="white",
                              padx=10, pady=10)
        self.output.pack(fill="both", expand=True)
        self.status = ttk.Label(main, text="", foreground="#2b7a3d")
        self.status.pack(anchor="w", pady=(4, 0))

    # ---------------------------------------------------------------- style
    def _style(self):
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        s.configure("Title.TLabel", font=("Segoe UI", 16, "bold"))
        s.configure("H.TLabel", font=("Segoe UI", 13, "bold"))
        s.configure("B.TLabel", font=("Segoe UI", 10, "bold"))
        s.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), foreground="white", background="#b5651d")
        s.map("Accent.TButton", background=[("active", "#8f4f16")])

    # -------------------------------------------------------------- actions
    def open_helper(self, field):
        HelperDialog(self, field, lambda text, k=field["key"]: self.vars[k].set(text))

    def value(self, key):
        return clean(self.vars[key].get())

    def negatives(self):
        items = [DEFAULT_NEGATIVE.replace(", or UI elements", ", UI elements")]
        items += [i for i, v in self.neg_vars if v.get()]
        items += [clean(x) for x in self.neg_other.get().split(",") if clean(x)]
        text = ", ".join(items)
        # put "or" before the last item for natural phrasing
        head, _, last = text.rpartition(", ")
        return f"{head}, or {last}" if head else text

    def build_prompt(self):
        v = {f["key"]: self.value(f["key"]) for f in FIELDS}
        missing = [f["layer"] for f in FIELDS if not v[f["key"]]]
        if missing:
            return None, missing
        lines = [
            f"Create a vertical 9:16 ultra-realistic cinematic image of {v['identity']}.",
            f"The character has {v['skin']} and wears {v['styling']}.",
            f"The character's emotional energy is {v['emotion']}.",
            f"The scene takes place in {v['environment']}, with {v['atmosphere']}.",
            f"Use {v['lighting']}, realistic shadows, atmospheric depth, natural color grading, and {v['camera']}.",
            f"The image should feel like {v['genre']}.",
            f"Avoid {self.negatives()}.",
        ]
        return "\n".join(lines), []

    def create(self):
        prompt, missing = self.build_prompt()
        if missing:
            messagebox.showwarning(
                "Missing layers",
                "Please fill these layers (type, pick, or use Help me):\n\n- " + "\n- ".join(missing))
            return
        self.output.delete("1.0", "end")
        self.output.insert("1.0", prompt)
        self.status.config(text=f"Prompt created - {len(prompt.split())} words. Copy it into ChatGPT (GPT Image 2).")

    def copy(self):
        text = self.output.get("1.0", "end").strip()
        if not text:
            self.create()
            text = self.output.get("1.0", "end").strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.status.config(text="Copied to clipboard.")

    def save(self):
        text = self.output.get("1.0", "end").strip()
        if not text:
            messagebox.showinfo("Nothing to save", "Create a prompt first.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt", initialfile="cinematic_character_prompt.txt",
                                            filetypes=[("Text file", "*.txt"), ("All files", "*.*")])
        if path:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text + "\n")
            self.status.config(text=f"Saved to {path}")

    def load_example(self):
        for f in FIELDS:
            self.vars[f["key"]].set(f["presets"][0])
        self.create()

    def randomize(self):
        for f in FIELDS:
            self.vars[f["key"]].set(random.choice(f["presets"]))
        self.create()

    def clear(self):
        for var in self.vars.values():
            var.set("")
        self.neg_other.set("")
        self.output.delete("1.0", "end")
        self.status.config(text="")


if __name__ == "__main__":
    App().mainloop()

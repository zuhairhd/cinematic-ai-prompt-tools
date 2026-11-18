"""Cinematic Prompt Studio - native Tkinter desktop GUI, Python 3.10+."""
from __future__ import annotations

import copy
import json
import os
import queue
import threading
import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from PIL import Image, ImageTk

from core import (APP_VERSION, FIELD_GROUPS, FIELDS, MODES, PROVIDERS, RATIOS, TARGETS,
                  StudioError, analyze_image, atomic_write, build_evidence, build_prompt,
                  load_project, prepare_image, save_project, validate_analysis)
from choices import PRESETS, RELATED, TIPS, build_guided_plan, find_option, option_record, options_for

ROOT = Path(__file__).resolve().parent
BG, PANEL, INK, MUTED, ACCENT, ENTRY = "#101820", "#18242e", "#e9eef2", "#a6b6c3", "#e3b676", "#223440"


class Studio(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Cinematic Prompt Studio")
        self.geometry("1280x880")
        self.minsize(1080, 760)
        self.configure(background=BG)
        self.prepared = None
        self.analysis = None
        self.image_meta = {}
        self.provenance = {}
        self.dirty = False
        self.busy = False
        self.job_id = 0
        self.events = queue.Queue()
        self.selected_key = None
        self.provider = "OpenAI"
        self.model = "gpt-4.1"
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        self.ollama_url = "http://localhost:11434"
        self.timeout = 300
        self.ratio = tk.StringVar(value="4:5")
        self.target = tk.StringVar(value="Universal")
        self.mode = tk.StringVar(value=MODES[0])
        self.status = tk.StringVar(value="Choose a reference image, or open the example to explore the controls.")
        self.connection = tk.StringVar(value="OpenAI  /  gpt-4.1")
        self._styles()
        self._layout()
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.poll_id = self.after(100, self.poll)

    def _styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background=BG, foreground=INK, font=("Segoe UI", 10))
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=INK)
        style.configure("Card.TLabel", background=PANEL)
        style.configure("Muted.TLabel", foreground=MUTED)
        style.configure("Title.TLabel", font=("Segoe UI", 23, "bold"))
        style.configure("Section.TLabel", font=("Segoe UI", 11, "bold"), foreground=ACCENT)
        style.configure("TButton", background=ENTRY, foreground=INK, padding=(12, 8), borderwidth=0)
        style.map("TButton", background=[("active", "#334b5a"), ("disabled", "#26313a")])
        style.configure("Accent.TButton", background=ACCENT, foreground=BG, font=("Segoe UI", 10, "bold"))
        style.map("Accent.TButton", background=[("active", "#f1ca94"), ("disabled", "#766b5a")])
        style.configure("TEntry", fieldbackground=ENTRY, foreground=INK, insertcolor=INK)
        style.configure("TCombobox", fieldbackground=ENTRY, foreground=INK, arrowcolor=ACCENT, padding=5)
        style.map("TCombobox", fieldbackground=[("readonly", ENTRY)], foreground=[("readonly", INK)])
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL, padding=(14, 10), foreground=MUTED)
        style.map("TNotebook.Tab", background=[("selected", ENTRY)], foreground=[("selected", ACCENT)])
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=INK, rowheight=28, borderwidth=0)
        style.configure("Treeview.Heading", background=ENTRY, foreground=INK, padding=6)
        style.map("Treeview", background=[("selected", "#385265")])
        style.configure("Horizontal.TProgressbar", background=ACCENT, troughcolor=PANEL)
        self.option_add("*TCombobox*Listbox.background", ENTRY)
        self.option_add("*TCombobox*Listbox.foreground", INK)

    def text_widget(self, parent, **kwargs):
        return ScrolledText(parent, wrap="word", bg=PANEL, fg=INK, insertbackground=INK,
                            selectbackground="#385265", relief="flat", borderwidth=0,
                            padx=14, pady=12, font=("Segoe UI", 11), **kwargs)

    @staticmethod
    def put(widget, text, readonly=True):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        if readonly:
            widget.configure(state="disabled")

    def _layout(self):
        header = ttk.Frame(self, padding=(24, 20, 24, 16))
        header.pack(fill="x")
        ttk.Label(header, text="CINEMATIC PROMPT STUDIO", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text="Read the light. Choose the shot. Write with intention.", style="Muted.TLabel").pack(anchor="w", pady=(4, 0))
        body = ttk.Frame(self, padding=(24, 0, 24, 0))
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)
        sidebar = ttk.Frame(body, width=324)
        sidebar.grid(row=0, column=0, sticky="ns", padx=(0, 20))
        sidebar.grid_propagate(False)
        self.sidebar_canvas = tk.Canvas(sidebar, bg=BG, width=304, highlightthickness=0)
        sidebar_scroll = ttk.Scrollbar(sidebar, orient="vertical", command=self.sidebar_canvas.yview)
        self.sidebar_canvas.configure(yscrollcommand=sidebar_scroll.set)
        self.sidebar_canvas.pack(side="left", fill="both", expand=True)
        sidebar_scroll.pack(side="right", fill="y")
        left = ttk.Frame(self.sidebar_canvas, width=304)
        self.sidebar_canvas.create_window((0, 0), window=left, anchor="nw", width=304)
        left.bind("<Configure>", lambda event: self.sidebar_canvas.configure(scrollregion=self.sidebar_canvas.bbox("all")))
        def sidebar_wheel(event):
            widget = event.widget
            while widget is not None:
                if widget == sidebar:
                    delta = (-1 if event.num == 4 else 1) if getattr(event, "num", None) in (4, 5) else (-1 if event.delta > 0 else 1)
                    self.sidebar_canvas.yview_scroll(delta * 3, "units")
                    break
                widget = getattr(widget, "master", None)
        self.bind_all("<MouseWheel>", sidebar_wheel, add="+")
        self.bind_all("<Button-4>", sidebar_wheel, add="+")
        self.bind_all("<Button-5>", sidebar_wheel, add="+")
        left.grid_columnconfigure(0, weight=1)
        ttk.Label(left, text="01  REFERENCE", style="Section.TLabel").grid(row=0, sticky="w", pady=(8, 10))
        self.canvas = tk.Canvas(left, width=302, height=208, bg=PANEL, highlightthickness=0)
        self.canvas.grid(row=1, sticky="ew")
        self.placeholder()
        self.image_label = ttk.Label(left, text="JPEG / PNG / WebP  •  max 40 MP", style="Muted.TLabel", wraplength=300)
        self.image_label.grid(row=2, sticky="w", pady=(7, 8))
        ttk.Button(left, text="Choose image…", command=self.choose_image).grid(row=3, sticky="ew")
        ttk.Label(left, text="02  DIRECTION", style="Section.TLabel").grid(row=4, sticky="w", pady=(20, 8))
        ttk.Combobox(left, textvariable=self.mode, values=MODES, state="readonly").grid(row=5, sticky="ew")
        ttk.Label(left, text="Optional brief — new subject, setting or purpose", style="Muted.TLabel", wraplength=300).grid(row=6, sticky="w", pady=(10, 5))
        self.brief = self.text_widget(left, height=3, undo=True)
        self.brief.grid(row=7, sticky="ew")
        ttk.Label(left, text="Mode and brief apply on the next analysis.", style="Muted.TLabel", font=("Segoe UI", 9)).grid(row=8, sticky="w", pady=(4, 8))
        controls = ttk.Frame(left)
        controls.grid(row=9, sticky="ew")
        controls.grid_columnconfigure((0, 1), weight=1)
        ttk.Label(controls, text="Aspect ratio").grid(row=0, column=0, sticky="w")
        ttk.Label(controls, text="Prompt format").grid(row=0, column=1, sticky="w", padx=(10, 0))
        ratio = ttk.Combobox(controls, textvariable=self.ratio, values=RATIOS, state="readonly", width=9)
        ratio.grid(row=1, column=0, sticky="ew", pady=5)
        target = ttk.Combobox(controls, textvariable=self.target, values=TARGETS, state="readonly", width=12)
        target.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=5)
        ratio.bind("<<ComboboxSelected>>", self.output_changed)
        target.bind("<<ComboboxSelected>>", self.output_changed)
        self.analyze_button = ttk.Button(left, text="Analyze image & build prompt", style="Accent.TButton", command=self.start_analysis)
        self.analyze_button.grid(row=10, sticky="ew", pady=(12, 6))
        self.cancel_button = ttk.Button(left, text="Cancel result", command=self.cancel, state="disabled")
        self.cancel_button.grid(row=11, sticky="ew")
        ttk.Button(left, text="AI connection…", command=self.settings).grid(row=12, sticky="ew", pady=(12, 4))
        ttk.Label(left, textvariable=self.connection, style="Muted.TLabel", wraplength=300).grid(row=13, sticky="w")
        self.privacy = ttk.Label(left, text="Analyze sends a resized image + brief to OpenAI. API usage may be billed. Your key is kept in memory only.", style="Muted.TLabel", wraplength=300, font=("Segoe UI", 9))
        self.privacy.grid(row=14, sticky="w", pady=(5, 0))

        right = ttk.Frame(body)
        right.grid(row=0, column=1, sticky="nsew")
        toolbar = ttk.Frame(right)
        toolbar.pack(fill="x", pady=(0, 10))
        for title, action in (("New guided plan", self.guided), ("Open project", self.open_saved), ("Save project", self.save),
                              ("Open example", self.demo), ("Copy prompt", self.copy_prompt), ("Export TXT", self.export)):
            ttk.Button(toolbar, text=title, command=action).pack(side="left", padx=(0, 6))
        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill="both", expand=True)
        prompt_tab, edit_tab, evidence_tab, learn_tab = [ttk.Frame(self.notebook) for _ in range(4)]
        for tab, label in zip((prompt_tab, edit_tab, evidence_tab, learn_tab), ("Full prompt", "33 shot choices", "Evidence & estimates", "Learn the method")):
            self.notebook.add(tab, text=label)
        self.output = self.text_widget(prompt_tab)
        self.output.pack(fill="both", expand=True)
        self.put(self.output, "YOUR REFERENCE → A DELIBERATE SHOT PLAN\n\n1. Choose an image.\n2. Set your AI connection and direction.\n3. Analyze the image.\n4. Review all 33 choices, then copy the prompt.\n\nEach field separates what is visible from what is estimated or proposed. No exact camera settings can be recovered from a picture alone.\n\nUse Open example to try editing and exporting without an API key. It is a hand-authored teaching example, not an analysis of your image.")
        ttk.Label(prompt_tab, text="This app writes prompts. Generate the image in your chosen image tool with the same reference attached.", style="Muted.TLabel", wraplength=760).pack(anchor="w", pady=(8, 4))
        self._editor(edit_tab)
        self.evidence = self.text_widget(evidence_tab)
        self.evidence.pack(fill="both", expand=True)
        self.put(self.evidence, "Evidence and reasoning will appear after analysis.")
        learn = self.text_widget(learn_tab)
        learn.pack(fill="both", expand=True)
        self.put(learn, (ROOT / "LEARNING_GUIDE.txt").read_text(encoding="utf-8"))
        footer = ttk.Frame(self, padding=(24, 12, 24, 14))
        footer.pack(fill="x")
        self.progress = ttk.Progressbar(footer, mode="indeterminate", length=110)
        self.progress.pack(side="right", padx=(16, 0))
        ttk.Label(footer, textvariable=self.status, style="Muted.TLabel", wraplength=1000).pack(side="left", fill="x", expand=True)

    def placeholder(self, text="Choose a visual reference\nLight • Lens • Texture • Color"):
        self.canvas.delete("all")
        self.canvas.create_rectangle(20, 20, 282, 188, outline="#3b4f5c", dash=(5, 4))
        self.canvas.create_text(151, 104, text=text, fill=MUTED, font=("Segoe UI", 12), justify="center", width=255)

    def _editor(self, parent):
        ttk.Label(parent, text="Select a row, pick an option from the list (or type your own instruction), then Apply choice. No image yet? Click New guided plan. Rebuilding is local and uses no API.", style="Muted.TLabel", wraplength=760).pack(anchor="w", pady=8)
        table_frame = ttk.Frame(parent)
        table_frame.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(table_frame, columns=("basis", "choice"), height=8)
        self.tree.heading("#0", text="Shot decision")
        self.tree.heading("basis", text="Basis")
        self.tree.heading("choice", text="Chosen instruction")
        self.tree.column("#0", width=205, minwidth=150)
        self.tree.column("basis", width=80, minwidth=70, stretch=False)
        self.tree.column("choice", width=400, minwidth=180)
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.select_field)
        self.field_title = ttk.Label(parent, text="Select a shot decision", style="Section.TLabel")
        self.field_title.pack(anchor="w", pady=(14, 4))
        self.field_help = ttk.Label(parent, text="", style="Muted.TLabel", wraplength=760)
        self.field_help.pack(anchor="w", pady=(0, 5))
        parent.bind("<Configure>", lambda event: self.field_help.configure(wraplength=max(300, event.width - 12)))
        picker = ttk.Frame(parent)
        picker.pack(fill="x", pady=(0, 6))
        ttk.Label(picker, text="Choose option").pack(side="left")
        self.option_choice = tk.StringVar()
        self.option_box = ttk.Combobox(picker, textvariable=self.option_choice, state="readonly", width=32)
        self.option_box.pack(side="left", padx=(8, 20))
        self.option_box.bind("<<ComboboxSelected>>", self.option_selected)
        ttk.Label(picker, text="Starter kit").pack(side="left")
        self.kit_choice = tk.StringVar(value=next(iter(PRESETS)))
        ttk.Combobox(picker, textvariable=self.kit_choice, values=list(PRESETS), state="readonly", width=34).pack(side="left", padx=8)
        ttk.Button(picker, text="Apply kit", command=self.apply_kit).pack(side="left")
        self.edit = self.text_widget(parent, height=3, undo=True)
        self.edit.pack(fill="x")
        ttk.Button(parent, text="Apply choice & rebuild prompt", command=self.apply_choice, style="Accent.TButton").pack(anchor="w", pady=8)
        info = ttk.Frame(parent)
        info.pack(fill="x")
        info.grid_columnconfigure((0, 1), weight=1, uniform="info")
        self.option_guide = self.text_widget(info, height=5)
        self.option_guide.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.put(self.option_guide, "Help for the selected decision and option will appear here.")
        self.field_evidence = self.text_widget(info, height=5)
        self.field_evidence.grid(row=0, column=1, sticky="ew")
        self.put(self.field_evidence, "The visible evidence and reason for the selected choice will appear here.")

    def idle_required(self):
        if self.busy:
            messagebox.showinfo("Analysis running", "Wait for the analysis to finish, or click Cancel result.")
            return False
        return True

    def okay_to_replace(self):
        if not self.idle_required():
            return False
        if self.dirty:
            choice = messagebox.askyesnocancel("Save project?", "Save your current project before replacing it?")
            if choice is None:
                return False
            if choice and not self.save():
                return False
        return True

    def choose_image(self):
        if not self.okay_to_replace():
            return
        filename = filedialog.askopenfilename(title="Choose a reference image", filetypes=[("Images", "*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff"), ("All files", "*.*")])
        if not filename:
            return
        try:
            prepared = prepare_image(filename)
        except (StudioError, OSError) as exc:
            messagebox.showerror("Image could not be opened", str(exc))
            return
        self.clear_analysis()
        self.prepared = prepared
        self.image_meta = prepared.metadata
        self.render_image()
        self.status.set("Image loaded. Set your direction, then analyze. No image has been sent yet.")

    def render_image(self):
        preview = self.prepared.preview.copy()
        preview.thumbnail((302, 208), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(preview)
        self.canvas.delete("all")
        self.canvas.create_image(151, 104, image=self.tk_image)
        w, h = self.prepared.metadata["original_size"]
        self.image_label.configure(text=f"{self.image_meta['filename']}  •  {w} × {h}")

    def clear_analysis(self):
        self.analysis = None
        self.provenance = {}
        self.selected_key = None
        self.dirty = False
        self.tree.delete(*self.tree.get_children())
        self.put(self.output, "Ready to analyze your reference image.")
        self.put(self.evidence, "No analysis for this image yet.")
        self.put(self.edit, "", readonly=False)
        self.field_title.configure(text="Select a shot decision")
        self.field_help.configure(text="")
        self.option_box.configure(values=())
        self.option_choice.set("")
        self.put(self.option_guide, "")
        self.put(self.field_evidence, "")

    def settings(self):
        if not self.idle_required():
            return
        window = tk.Toplevel(self)
        window.title("AI connection")
        window.configure(bg=BG)
        window.geometry("600x490")
        window.transient(self)
        window.grab_set()
        frame = ttk.Frame(window, padding=24)
        frame.pack(fill="both", expand=True)
        provider = tk.StringVar(value=self.provider)
        model = tk.StringVar(value=self.model)
        key = tk.StringVar(value=self.api_key)
        endpoint = tk.StringVar(value=self.ollama_url)
        timeout = tk.StringVar(value=str(self.timeout))
        variables = [("Analysis provider", provider), ("Vision model name (editable)", model),
                     ("OpenAI API key — memory only", key), ("Ollama local address", endpoint),
                     ("Request timeout in seconds (30–1800)", timeout)]
        for i, (label, variable) in enumerate(variables):
            ttk.Label(frame, text=label).grid(row=i * 2, column=0, sticky="w", pady=(5, 4))
            if i == 0:
                entry = ttk.Combobox(frame, textvariable=variable, values=PROVIDERS, state="readonly")
                entry.bind("<<ComboboxSelected>>", lambda e: model.set("gpt-4.1" if provider.get() == "OpenAI" else "qwen2.5vl:7b"))
            else:
                entry = ttk.Entry(frame, textvariable=variable, show="*" if i == 2 else "")
            entry.grid(row=i * 2 + 1, column=0, sticky="ew")
        frame.grid_columnconfigure(0, weight=1)
        ttk.Label(frame, text="OpenAI: image analysis requires an API key and API access.\nOllama: install a local vision model first; no models are downloaded here.\nSettings and keys are not written to disk.", style="Muted.TLabel", wraplength=545).grid(row=10, sticky="w", pady=12)

        def apply():
            from core import local_endpoint
            try:
                seconds = int(timeout.get())
                if not 30 <= seconds <= 1800:
                    raise ValueError
                if not model.get().strip():
                    raise StudioError("Enter a model name.")
                if provider.get() != "OpenAI":
                    local_endpoint(endpoint.get())
            except (StudioError, ValueError) as exc:
                messagebox.showerror("Check connection settings", str(exc) or "Timeout must be between 30 and 1800 seconds.", parent=window)
                return
            self.provider, self.model = provider.get(), model.get().strip()
            self.api_key, self.ollama_url, self.timeout = key.get().strip(), endpoint.get().strip(), seconds
            self.connection.set(f"{self.provider}  /  {self.model}")
            self.privacy.configure(text=("Analyze sends a resized image + brief to OpenAI. API usage may be billed. Your key is kept in memory only."
                                         if self.provider == "OpenAI" else "Analyze sends the image to your local Ollama service. Use an installed local vision model; processing may take several minutes."))
            window.destroy()
        ttk.Button(frame, text="Use these settings", style="Accent.TButton", command=apply).grid(row=11, sticky="ew")

    def options(self):
        return {"ratio": self.ratio.get(), "target": self.target.get(), "mode": self.mode.get(),
                "brief": self.brief.get("1.0", "end").strip()}

    def start_analysis(self):
        if not self.idle_required():
            return
        if self.prepared is None:
            messagebox.showinfo("Choose an image", "Choose a reference image before analyzing.")
            return
        if self.provider == "OpenAI" and not self.api_key:
            self.settings()
            return
        if self.analysis and not self.okay_to_replace():
            return
        # Snapshot all Tk state before the worker. Workers never access widgets.
        options = self.options()
        params = dict(prepared=self.prepared, provider=self.provider, model=self.model,
                      api_key=self.api_key, ollama_url=self.ollama_url, mode=options["mode"],
                      ratio=options["ratio"], brief=options["brief"], timeout=self.timeout)
        provenance = {"provider": self.provider, "model": self.model,
                      "analyzed_at": datetime.now(timezone.utc).isoformat(), "demo": False}
        self.job_id += 1
        job = self.job_id
        self.set_busy(True)
        self.status.set("Analyzing light, composition, optics and texture… You can cancel the result; provider processing may continue.")

        def worker():
            try:
                analysis, usage = analyze_image(**params)
                self.events.put((job, "success", (analysis, usage, options, provenance)))
            except Exception as exc:
                message = str(exc) if isinstance(exc, StudioError) else "The provider response could not be processed. Check the model and try again."
                self.events.put((job, "error", message))
        threading.Thread(target=worker, daemon=True).start()

    def set_busy(self, busy):
        self.busy = busy
        self.analyze_button.configure(state="disabled" if busy else "normal")
        self.cancel_button.configure(state="normal" if busy else "disabled")
        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()

    def cancel(self):
        if self.busy:
            self.job_id += 1
            self.set_busy(False)
            self.status.set("Result canceled. The in-flight provider request may still finish and incur usage. Any existing project is unchanged.")

    def poll(self):
        if getattr(self, "poll_id", None):
            self.after_cancel(self.poll_id)
        try:
            while True:
                job, kind, payload = self.events.get_nowait()
                if job != self.job_id:
                    continue
                self.set_busy(False)
                if kind == "error":
                    self.status.set("Analysis failed. Any previous project remains unchanged.")
                    messagebox.showerror("Analysis failed", payload)
                    continue
                analysis, usage, options, provenance = payload
                self.analysis, self.provenance = analysis, provenance
                self.apply_options(options)
                self.dirty = True
                self.refresh()
                self.notebook.select(0)
                self.status.set(f"{len(FIELDS)}/{len(FIELDS)} choices completed. Review estimates and edit any choice before generating your image.")
        except queue.Empty:
            pass
        self.poll_id = self.after(100, self.poll)

    def destroy(self):
        if getattr(self, "poll_id", None):
            self.after_cancel(self.poll_id)
            self.poll_id = None
        super().destroy()

    def apply_options(self, options):
        self.ratio.set(options["ratio"])
        self.target.set(options["target"])
        self.mode.set(options["mode"])
        self.put(self.brief, options.get("brief", ""), readonly=False)

    def refresh(self):
        if not self.analysis:
            return
        self.put(self.output, build_prompt(self.analysis, self.ratio.get(), self.target.get()))
        label = "HAND-AUTHORED TEACHING EXAMPLE — NOT IMAGE ANALYSIS\n\n" if self.provenance.get("demo") else ""
        self.put(self.evidence, label + build_evidence(self.analysis))
        keep = self.selected_key
        self.tree.delete(*self.tree.get_children())
        for group, rows in FIELD_GROUPS.items():
            parent = self.tree.insert("", "end", text=group, open=True)
            for key, title, _ in rows:
                row = self.analysis["fields"][key]
                self.tree.insert(parent, "end", iid=key, text=title, values=(row["basis"], row["choice"]))
        if keep in FIELDS:
            self.tree.selection_set(keep)

    def output_changed(self, event=None):
        if self.analysis:
            self.refresh()
            self.dirty = True
            self.status.set("Prompt format updated locally. If you changed the aspect ratio, review framing, placement and camera distance.")

    def select_field(self, event=None):
        selected = self.tree.selection()
        if not selected or selected[0] not in FIELDS or not self.analysis:
            return
        key = self.selected_key = selected[0]
        row = self.analysis["fields"][key]
        _, title, help_text = FIELDS[key]
        self.field_title.configure(text=title)
        self.field_help.configure(text=help_text)
        self.put(self.edit, row["choice"], readonly=False)
        self.put(self.field_evidence, f"BASIS: {row['basis']}\nVISIBLE: {row['observation']}\nWHY: {row['reason']}")
        options = options_for(key)
        self.option_box.configure(values=[label for label, _, _ in options])
        current = next((label for label, text, _ in options if text == row["choice"]), "")
        self.option_choice.set(current)
        self.show_guide(key, current)

    def related_text(self, key):
        related = RELATED.get(key)
        return ("\nCHECK ALSO: " + ", ".join(FIELDS[k][1] for k in related)) if related else ""

    def show_guide(self, key, label=""):
        lines = ["TIP: " + TIPS[key]]
        option = find_option(key, label) if label else None
        if option:
            lines.append(f"OPTION — {label}: {option[2]}")
        else:
            lines.append("OPTIONS: " + " | ".join(f"{name}: {guide}" for name, _, guide in options_for(key)))
        self.put(self.option_guide, "\n".join(lines) + self.related_text(key))

    def option_selected(self, event=None):
        if not self.selected_key:
            return
        option = find_option(self.selected_key, self.option_choice.get())
        if option:
            self.put(self.edit, option[1], readonly=False)
            self.show_guide(self.selected_key, option[0])
            self.status.set("Option loaded into the instruction box. Edit it if you like, then Apply choice.")

    def apply_choice(self):
        if not self.idle_required() or not self.analysis or not self.selected_key:
            return
        key = self.selected_key
        value = self.edit.get("1.0", "end").strip()
        candidate = copy.deepcopy(self.analysis)
        row = candidate["fields"][key]
        option = next((o for o in options_for(key) if o[1] == value), None)
        if option:
            row.update(choice=value, basis="user", reason=option_record(key, option[0])["reason"])
        else:
            row.update(choice=value, basis="user", reason="Manually chosen by you. Review related fields for consistency; no new AI analysis was run.")
        try:
            candidate = validate_analysis(candidate)
        except StudioError as exc:
            messagebox.showerror("Choice needs attention", str(exc))
            return
        self.analysis = candidate
        self.dirty = True
        self.refresh()
        related = RELATED.get(key)
        hint = ("Now check: " + ", ".join(FIELDS[k][1] for k in related) + ".") if related else "Check related choices for consistency."
        self.status.set("Choice applied and prompt rebuilt. " + hint)

    def apply_kit(self):
        if not self.idle_required() or not self.require_plan():
            return
        name = self.kit_choice.get()
        candidate = copy.deepcopy(self.analysis)
        for key, label in PRESETS[name].items():
            record = option_record(key, label)
            record["observation"] = candidate["fields"][key]["observation"]
            candidate["fields"][key] = record
        self.analysis = validate_analysis(candidate)
        self.dirty = True
        self.refresh()
        if self.selected_key:
            self.select_field()
        self.status.set(f"Starter kit '{name}' applied to {len(PRESETS[name])} decisions. Review subject, setting and story for your shot.")

    def guided(self):
        if not self.okay_to_replace():
            return
        self.clear_analysis()
        self.analysis = build_guided_plan()
        self.provenance = {"provider": "Guided options", "model": "None",
                           "analyzed_at": datetime.now(timezone.utc).isoformat(), "demo": False}
        if self.prepared is None:
            self.placeholder("Guided plan\nPick every decision from the option lists")
            self.image_label.configure(text="No reference image needed for a guided plan.")
        self.refresh()
        self.dirty = True
        self.notebook.select(1)
        self.tree.selection_set("subject")
        self.tree.see("subject")
        self.status.set("Guided plan created from the lesson's defaults. Select each decision and choose from its options, or apply a starter kit.")

    def require_plan(self):
        if self.analysis:
            return True
        messagebox.showinfo("No shot plan yet", "Analyze an image, open a saved project, or open the teaching example first.")
        return False

    def copy_prompt(self):
        if not self.require_plan():
            return
        self.clipboard_clear()
        self.clipboard_append(build_prompt(self.analysis, self.ratio.get(), self.target.get()))
        self.update_idletasks()
        self.status.set("Full prompt copied. Attach your reference image in the image generator as well.")

    def export(self):
        if not self.require_plan():
            return
        path = filedialog.asksaveasfilename(title="Export the complete prompt", defaultextension=".txt", initialfile="cinematic_prompt.txt", filetypes=[("Text", "*.txt")])
        if not path:
            return
        try:
            atomic_write(path, build_prompt(self.analysis, self.ratio.get(), self.target.get()))
            self.status.set("Prompt exported. Use Save project to retain editable choices and evidence.")
        except OSError as exc:
            messagebox.showerror("Could not export", str(exc))

    def save(self):
        if not self.require_plan():
            return False
        path = filedialog.asksaveasfilename(title="Save editable shot plan", defaultextension=".json", initialfile="cinematic_project.json", filetypes=[("Studio project", "*.json")])
        if not path:
            return False
        try:
            save_project(path, self.analysis, self.options(), self.image_meta, self.provenance)
        except (StudioError, OSError) as exc:
            messagebox.showerror("Could not save", str(exc))
            return False
        self.dirty = False
        self.status.set("Project saved with editable choices and evidence. Image bytes and API keys are not included.")
        return True

    def open_saved(self):
        if not self.okay_to_replace():
            return
        path = filedialog.askopenfilename(title="Open a Studio project", filetypes=[("Studio project", "*.json")])
        if path:
            self.load_path(path)

    def load_path(self, path):
        try:
            project = load_project(path)
        except (StudioError, OSError) as exc:
            messagebox.showerror("Cannot open project", str(exc))
            return
        self.clear_analysis()
        self.analysis = project["analysis"]
        self.provenance = project.get("provenance", {})
        self.image_meta = project.get("image", {})
        self.prepared = None
        self.placeholder("Teaching example" if self.provenance.get("demo") else "Saved shot plan\nReference image not embedded")
        self.image_label.configure(text="Example scene: a studio portrait" if self.provenance.get("demo") else "Reselect the source image for a fresh analysis.")
        self.apply_options(project["options"])
        self.refresh()
        self.notebook.select(0)
        self.dirty = False
        self.status.set("Teaching example loaded; no AI analysis was performed." if self.provenance.get("demo") else "Project opened. Choices remain editable without an API call.")

    def demo(self):
        if self.okay_to_replace():
            self.load_path(ROOT / "example_project.json")

    def close(self):
        if self.busy and not messagebox.askyesno("Analysis in progress", "Close now? The provider request may continue and incur usage."):
            return
        if self.dirty:
            choice = messagebox.askyesnocancel("Save project?", "Save your current shot plan before closing?")
            if choice is None or (choice and not self.save()):
                return
        self.job_id += 1
        self.destroy()


def main():
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass
    Studio().mainloop()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
War Room Prompt Builder  |  مولّد برومت «قاعة العمليات»
------------------------------------------------------
Enter a goal or problem, choose Arabic or English, and get a ready-to-paste
"War Room" prompt for any AI chatbot (Claude, ChatGPT, Gemini, ...).

Uses only the Python standard library (tkinter) -> no pip installs needed.
Recommended: Python 3.13 (works on 3.10+).
"""

import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

RECOMMENDED = (3, 13)

# --------------------------------------------------------------------------
# Prompt templates. {goal} is replaced with the user's text.
# --------------------------------------------------------------------------
TEMPLATE_AR = """🧠 البرومت النهائي «قاعة العمليات»

الهدف/المشكلة:
{goal}

أنت لست مساعداً ولن تعطيني إجابة الآن. أنت "مُسجِّل" ينقل حرفياً حواراً حياً داخل قاعة عمليات مغلقة. لا توجد إجابة مسبقة.

أعضاء القاعة (أعطهم أسماء لتسهيل التسجيل):
1. "المهندس": يبني الهيكل الأساسي للحل.
2. "محامي الشيطان": ناقد شرس مهمته تدمير الافتراضات واصطياد الثغرات.
3. "الزبون الغبي": مستخدم نهائي ساخر، يكره التعقيد، ويفهم الأمور بأسوأ طريقة ممكنة.
4. "الخبير المتخصص": (حلّل هدفي أولاً، واستدعِ أفضل خبير عالمي يناسب هذه المشكلة تحديداً للمجلس).
5. "المايسترو": صامت تماماً في هذه المرحلة. يراقب فقط.

المهمة الآن:
قم بتوليد نص المداولة (حوار مباشر). استدعِ الخبير أولاً، ثم دع المهندس يطرح خطته، ولتبدأ المعركة بينهم.
ممنوع منعاً باتاً تقديم أي استنتاج، تلخيص، أو إجابة نهائية في هذه المرحلة.

قوانين المداولة (تُنفَّذ كقيود حتمية أثناء الحوار):
* حظر المجاملة: "محامي الشيطان" و"الزبون الغبي" ملزمان برفض المسودة الأولى واستخراج "عيب قاتل" واحد على الأقل.
* المبادئ الأولى والعواقب: يجب على الخبير المتخصص تفكيك الفكرة لجذورها وتوقّع الكوارث المستقبلية (Second-order effects).
* التطور الإجباري: يجب أن تتصادم الآراء وتتعدّل الخطة بناءً على النقد داخل الحوار. لا توافقوا بسرعة.

❇️ مرحلة المايسترو (القرار النهائي):
(فقط بعد أن يستنزف الخبراء حججهم وتُعالَج العيوب القاتلة في الحوار، يُسمح للمايسترو بالتدخل).
وظيفة المايسترو: لا تقم بتلخيص ما حدث. بناءً حصرياً على المداولة السابقة وما نتج عنها من حلول وتصحيحات، قم بهندسة "الإجابة النهائية الشاملة".
قدّم لي الحل النهائي، النظيف، والجاهز للتنفيذ فوراً.
"""

TEMPLATE_EN = """🧠 The Final "War Room" Prompt

Goal / Problem:
{goal}

You are NOT an assistant, and you will NOT give me an answer yet. You are a "Recorder" transcribing, word for word, a live debate inside a closed war room. There is no predetermined answer.

War Room members (give each a name to make the transcript easy to follow):
1. "The Engineer": builds the core structure of the solution.
2. "The Devil's Advocate": a fierce critic whose job is to destroy assumptions and hunt for loopholes.
3. "The Clueless Customer": a sarcastic end user who hates complexity and understands everything in the worst possible way.
4. "The Domain Expert": (analyze my goal first, then summon the world's best expert for this specific problem to join the council).
5. "The Maestro": completely silent at this stage. Observes only.

Your task now:
Generate the deliberation transcript (direct dialogue). Summon the Expert first, then let the Engineer present his plan, and let the battle begin.
You are strictly forbidden from giving any conclusion, summary, or final answer at this stage.

Rules of deliberation (enforced as hard constraints throughout the dialogue):
* No flattery: The Devil's Advocate and the Clueless Customer MUST reject the first draft and expose at least one "fatal flaw".
* First principles & consequences: The Domain Expert MUST break the idea down to its roots and predict future disasters (second-order effects).
* Forced evolution: Opinions MUST clash, and the plan MUST be revised based on the criticism inside the dialogue. Do not agree quickly.

❇️ The Maestro Phase (Final Decision):
(Only after the experts have exhausted their arguments and the fatal flaws have been resolved in the dialogue may the Maestro step in.)
The Maestro's job: Do NOT summarize what happened. Based exclusively on the preceding deliberation and the solutions and corrections it produced, engineer the "comprehensive final answer".
Give me the final, clean solution, ready for immediate execution.
"""

UI = {
    "ar": {
        "title": "مولّد برومت «قاعة العمليات»",
        "subtitle": "اكتب هدفك أو مشكلتك، وسيُكتب لك برومت احترافي جاهز للنسخ",
        "input": "الهدف / المشكلة:",
        "output": "البرومت الجاهز:",
        "generate": "⚙ توليد البرومت",
        "copy": "📋 نسخ إلى الحافظة",
        "save": "💾 حفظ كملف",
        "clear": "🗑 مسح",
        "lang": "لغة البرومت:",
        "copied": "✔ تم النسخ إلى الحافظة",
        "empty": "الرجاء كتابة الهدف أو المشكلة أولاً.",
        "nothing": "لا يوجد برومت لنسخه. اضغط «توليد» أولاً.",
        "saved": "✔ تم الحفظ: ",
        "ready": "جاهز  •  Ctrl+Enter للتوليد",
        "chars": "حرف",
    },
    "en": {
        "title": "War Room Prompt Builder",
        "subtitle": "Describe your goal or problem and get a professional prompt, ready to copy",
        "input": "Goal / Problem:",
        "output": "Generated prompt:",
        "generate": "⚙ Generate Prompt",
        "copy": "📋 Copy to Clipboard",
        "save": "💾 Save as File",
        "clear": "🗑 Clear",
        "lang": "Prompt language:",
        "copied": "✔ Copied to clipboard",
        "empty": "Please enter your goal or problem first.",
        "nothing": "Nothing to copy yet. Click Generate first.",
        "saved": "✔ Saved: ",
        "ready": "Ready  •  Ctrl+Enter to generate",
        "chars": "chars",
    },
}


def build_prompt(goal: str, lang: str = "ar") -> str:
    """Return the full War Room prompt with the user's goal inserted."""
    goal = goal.strip()
    template = TEMPLATE_AR if lang == "ar" else TEMPLATE_EN
    return template.format(goal=goal)


class App(tk.Tk):
    BG = "#0f172a"        # slate-900
    PANEL = "#1e293b"     # slate-800
    FG = "#e2e8f0"        # slate-200
    MUTED = "#94a3b8"     # slate-400
    ACCENT = "#22c55e"    # green-500
    ACCENT2 = "#3b82f6"   # blue-500

    def __init__(self):
        super().__init__()
        self.lang = tk.StringVar(value="ar")
        self.geometry("1000x760")
        self.minsize(760, 560)
        self.configure(bg=self.BG)
        self._font = ("Segoe UI", 11)
        self._mono = ("Segoe UI", 11)
        self._build_styles()
        self._build_ui()
        self._apply_language()
        self.bind_all("<Control-Return>", lambda e: self.generate())
        self.bind_all("<Control-Shift-C>", lambda e: self.copy())
        self.input_box.focus_set()

    # ---------------- UI construction ----------------
    def _build_styles(self):
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        s.configure("TFrame", background=self.BG)
        s.configure("TLabel", background=self.BG, foreground=self.FG, font=self._font)
        s.configure("Title.TLabel", font=("Segoe UI", 20, "bold"))
        s.configure("Sub.TLabel", foreground=self.MUTED, font=("Segoe UI", 11))
        s.configure("Status.TLabel", foreground=self.MUTED, font=("Segoe UI", 10))
        s.configure("TRadiobutton", background=self.BG, foreground=self.FG, font=self._font)
        s.map("TRadiobutton", background=[("active", self.BG)])
        for name, color in (("Gen", self.ACCENT2), ("Copy", self.ACCENT), ("Plain", "#475569")):
            s.configure(f"{name}.TButton", background=color, foreground="white",
                        font=("Segoe UI", 11, "bold"), padding=(14, 8), borderwidth=0)
            s.map(f"{name}.TButton", background=[("active", color), ("pressed", self.PANEL)])

    def _text(self, parent, height):
        t = tk.Text(parent, wrap="word", height=height, undo=True,
                    bg=self.PANEL, fg=self.FG, insertbackground=self.FG,
                    relief="flat", padx=12, pady=10, font=self._mono,
                    selectbackground=self.ACCENT2)
        sb = ttk.Scrollbar(parent, orient="vertical", command=t.yview)
        t.configure(yscrollcommand=sb.set)
        return t, sb

    def _build_ui(self):
        root = ttk.Frame(self, padding=18)
        root.pack(fill="both", expand=True)

        self.lbl_title = ttk.Label(root, style="Title.TLabel")
        self.lbl_title.pack(fill="x")
        self.lbl_sub = ttk.Label(root, style="Sub.TLabel")
        self.lbl_sub.pack(fill="x", pady=(2, 12))

        # language switch
        bar = ttk.Frame(root)
        bar.pack(fill="x", pady=(0, 8))
        self.lbl_lang = ttk.Label(bar)
        self.lbl_lang.pack(side="left")
        ttk.Radiobutton(bar, text="العربية", value="ar", variable=self.lang,
                        command=self._on_lang).pack(side="left", padx=8)
        ttk.Radiobutton(bar, text="English", value="en", variable=self.lang,
                        command=self._on_lang).pack(side="left")

        # input
        self.lbl_input = ttk.Label(root)
        self.lbl_input.pack(fill="x")
        f_in = ttk.Frame(root)
        f_in.pack(fill="x", pady=(4, 10))
        self.input_box, sb1 = self._text(f_in, 5)
        sb1.pack(side="right", fill="y")
        self.input_box.pack(side="left", fill="both", expand=True)

        # buttons
        btns = ttk.Frame(root)
        btns.pack(fill="x", pady=(0, 10))
        self.btn_gen = ttk.Button(btns, style="Gen.TButton", command=self.generate)
        self.btn_copy = ttk.Button(btns, style="Copy.TButton", command=self.copy)
        self.btn_save = ttk.Button(btns, style="Plain.TButton", command=self.save)
        self.btn_clear = ttk.Button(btns, style="Plain.TButton", command=self.clear)
        for b in (self.btn_gen, self.btn_copy, self.btn_save, self.btn_clear):
            b.pack(side="left", padx=(0, 8))

        # output
        self.lbl_output = ttk.Label(root)
        self.lbl_output.pack(fill="x")
        f_out = ttk.Frame(root)
        f_out.pack(fill="both", expand=True, pady=(4, 6))
        self.output_box, sb2 = self._text(f_out, 18)
        sb2.pack(side="right", fill="y")
        self.output_box.pack(side="left", fill="both", expand=True)

        self.status = ttk.Label(root, style="Status.TLabel")
        self.status.pack(fill="x")

        for box in (self.input_box, self.output_box):
            box.tag_configure("rtl", justify="right")
            box.tag_configure("ltr", justify="left")

    # ---------------- behaviour ----------------
    def t(self, key):
        return UI[self.lang.get()][key]

    def _apply_language(self):
        lang = self.lang.get()
        self.title(self.t("title"))
        anchor = "e" if lang == "ar" else "w"
        for lbl, key in ((self.lbl_title, "title"), (self.lbl_sub, "subtitle"),
                         (self.lbl_input, "input"), (self.lbl_output, "output"),
                         (self.lbl_lang, "lang")):
            lbl.configure(text=self.t(key), anchor=anchor)
        self.btn_gen.configure(text=self.t("generate"))
        self.btn_copy.configure(text=self.t("copy"))
        self.btn_save.configure(text=self.t("save"))
        self.btn_clear.configure(text=self.t("clear"))
        self._align(self.input_box)
        self._align(self.output_box)
        self._set_status(self.t("ready"))

    def _align(self, box):
        tag = "rtl" if self.lang.get() == "ar" else "ltr"
        box.tag_remove("rtl", "1.0", "end")
        box.tag_remove("ltr", "1.0", "end")
        box.tag_add(tag, "1.0", "end")

    def _on_lang(self):
        self._apply_language()
        if self.output_box.get("1.0", "end").strip():
            self.generate()  # re-render existing prompt in the new language

    def _set_status(self, msg):
        self.status.configure(text=msg, anchor="e" if self.lang.get() == "ar" else "w")

    def generate(self):
        goal = self.input_box.get("1.0", "end").strip()
        if not goal:
            messagebox.showwarning(self.t("title"), self.t("empty"))
            return "break"
        prompt = build_prompt(goal, self.lang.get())
        self.output_box.delete("1.0", "end")
        self.output_box.insert("1.0", prompt)
        self._align(self.output_box)
        self._set_status(f"{len(prompt):,} {self.t('chars')}")
        return "break"

    def copy(self):
        text = self.output_box.get("1.0", "end").strip()
        if not text:
            messagebox.showinfo(self.t("title"), self.t("nothing"))
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()  # keep clipboard content after the app closes
        self._set_status(self.t("copied"))

    def save(self):
        text = self.output_box.get("1.0", "end").strip()
        if not text:
            messagebox.showinfo(self.t("title"), self.t("nothing"))
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt", initialfile="war_room_prompt.txt",
            filetypes=[("Text", "*.txt"), ("Markdown", "*.md"), ("All files", "*.*")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            self._set_status(self.t("saved") + path)

    def clear(self):
        self.input_box.delete("1.0", "end")
        self.output_box.delete("1.0", "end")
        self._set_status(self.t("ready"))
        self.input_box.focus_set()


def main():
    if sys.version_info[:2] != RECOMMENDED:
        print(f"[info] Running on Python {sys.version.split()[0]}. "
              f"Recommended: {RECOMMENDED[0]}.{RECOMMENDED[1]} "
              f"(run with:  py -3.13 war_room_prompt_builder.py)")
    App().mainloop()


if __name__ == "__main__":
    main()

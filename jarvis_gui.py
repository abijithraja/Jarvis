"""
Tier-A Jarvis GUI — waveform + chat + skills panel + Ctrl+J hotkey
"""
import tkinter as tk
from tkinter import ttk, scrolledtext
from threading import Thread
import sys, io, time, math

BG=      "#0d0d0e"
BG2=     "#141416"
ACCENT=  "#00e5a0"
ACCENT2= "#7c6ef7"
TEXT=    "#d4d2c8"
MUTED=   "#555552"
DANGER=  "#e25c5c"
FONT_MONO=  ("Courier New", 10)
FONT_TITLE= ("Courier New", 18, "bold")
FONT_SMALL= ("Courier New", 9)
FONT_MED=   ("Courier New", 11)

class JarvisGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("J.A.R.V.I.S")
        self.root.geometry("820x620")
        self.root.configure(bg=BG)
        self.root.resizable(True, True)
        self._running   = False
        self._listening = False
        self._wave_phase= 0
        self._build_ui()
        self._animate_wave()
        self.root.bind_all("<Control-j>", lambda e: self._toggle_jarvis())
        sys.stdout = _LogRedirector(self)

    def _build_ui(self):
        self.root.grid_columnconfigure(0, weight=3)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
        self._build_header()
        self._build_chat()
        self._build_sidebar()
        self._build_footer()

    def _build_header(self):
        hdr = tk.Frame(self.root, bg=BG, pady=10)
        hdr.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16)
        tk.Label(hdr, text="JARVIS", fg=ACCENT, bg=BG, font=FONT_TITLE).pack(side=tk.LEFT)
        self.status_var = tk.StringVar(value="● idle")
        self.status_lbl = tk.Label(hdr, textvariable=self.status_var, fg=MUTED, bg=BG, font=FONT_SMALL)
        self.status_lbl.pack(side=tk.LEFT, padx=12)
        self.wave_canvas = tk.Canvas(hdr, width=220, height=36, bg=BG, highlightthickness=0)
        self.wave_canvas.pack(side=tk.LEFT, padx=12)
        tk.Label(hdr, text="Ctrl+J to toggle", fg=MUTED, bg=BG, font=FONT_SMALL).pack(side=tk.RIGHT)

    def _build_chat(self):
        frame = tk.Frame(self.root, bg=BG2)
        frame.grid(row=1, column=0, sticky="nsew", padx=(16,8), pady=8)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        self.chat = scrolledtext.ScrolledText(
            frame, bg=BG2, fg=TEXT, font=FONT_MONO,
            insertbackground=ACCENT, relief="flat", bd=0,
            wrap=tk.WORD, state=tk.DISABLED,
        )
        self.chat.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        self.chat.tag_config("user",   foreground=ACCENT2, font=("Courier New",10,"bold"))
        self.chat.tag_config("jarvis", foreground=ACCENT,  font=("Courier New",10,"bold"))
        self.chat.tag_config("system", foreground=MUTED,   font=FONT_SMALL)
        self.chat.tag_config("error",  foreground=DANGER)
        self.chat.tag_config("body",   foreground=TEXT)

    def _build_sidebar(self):
        side = tk.Frame(self.root, bg=BG)
        side.grid(row=1, column=1, sticky="nsew", padx=(0,16), pady=8)
        tk.Label(side, text="skills", fg=MUTED, bg=BG, font=FONT_SMALL).pack(anchor="w", pady=(4,8))
        self._skill_vars = {}
        skills = [
            ("Weather",     "weather"),
            ("Reminders",   "reminder"),
            ("News",        "news"),
            ("Spotify",     "spotify"),
            ("File ops",    "file_ops"),
            ("Code runner", "code_runner"),
            ("Web search",  "web_search"),
            ("Screen OCR",  "screen_ocr"),
        ]
        for label, key in skills:
            var = tk.BooleanVar(value=True)
            self._skill_vars[key] = var
            tk.Checkbutton(
                side, text=label, variable=var,
                bg=BG, fg=TEXT, selectcolor=BG2,
                activebackground=BG, activeforeground=ACCENT,
                font=FONT_SMALL,
            ).pack(anchor="w")
        tk.Frame(side, bg=MUTED, height=1).pack(fill="x", pady=10)
        tk.Label(side, text="voice", fg=MUTED, bg=BG, font=FONT_SMALL).pack(anchor="w")
        self.voice_var = tk.StringVar(value="guy")
        voices = ["guy","davis","tony","aria","ryan","sonia"]
        vm = ttk.Combobox(side, textvariable=self.voice_var, values=voices, width=10, state="readonly")
        vm.pack(anchor="w", pady=4)
        vm.bind("<<ComboboxSelected>>", lambda e: self._on_voice_change())
        tk.Frame(side, bg=MUTED, height=1).pack(fill="x", pady=10)
        tk.Label(side, text="memory", fg=MUTED, bg=BG, font=FONT_SMALL).pack(anchor="w")
        self.mem_label = tk.Label(side, text="—", fg=TEXT, bg=BG, font=FONT_SMALL, justify="left")
        self.mem_label.pack(anchor="w")
        self.root.after(3000, self._update_mem_stats)

    def _build_footer(self):
        foot = tk.Frame(self.root, bg=BG, pady=8)
        foot.grid(row=2, column=0, columnspan=2, sticky="ew", padx=16)
        self.start_btn = tk.Button(
            foot, text="▶  START", command=self._toggle_jarvis,
            bg="#003d2a", fg=ACCENT, font=FONT_MED,
            relief="flat", padx=18, pady=6, cursor="hand2",
            activebackground="#004d35", activeforeground=ACCENT,
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0,8))
        tk.Button(foot, text="CLEAR", command=self._clear_chat,
                  bg=BG2, fg=MUTED, font=FONT_MED, relief="flat",
                  padx=12, pady=6, cursor="hand2").pack(side=tk.LEFT, padx=4)
        tk.Button(foot, text="✕  QUIT", command=self.root.quit,
                  bg="#2a0000", fg=DANGER, font=FONT_MED,
                  relief="flat", padx=12, pady=6, cursor="hand2").pack(side=tk.RIGHT)
        self.text_input = tk.Entry(foot, bg=BG2, fg=TEXT, font=FONT_MONO,
                                   relief="flat", insertbackground=ACCENT)
        self.text_input.pack(side=tk.LEFT, fill="x", expand=True, padx=8)
        self.text_input.insert(0, "type a command...")
        self.text_input.bind("<Return>", self._on_text_submit)
        self.text_input.bind("<FocusIn>", lambda e: self.text_input.delete(0, tk.END)
                             if self.text_input.get()=="type a command..." else None)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _toggle_jarvis(self):
        if not self._running:
            self._running = True
            self.start_btn.config(text="■  STOP", bg="#3a0000", fg=DANGER)
            self._set_status("● active", ACCENT)
            Thread(target=self._run_loop, daemon=True).start()
        else:
            self._running = False
            self.start_btn.config(text="▶  START", bg="#003d2a", fg=ACCENT)
            self._set_status("● idle", MUTED)

    def _run_loop(self):
        from main import run_jarvis_once
        self.log_system("Jarvis started. Listening...\n")
        while self._running:
            try:
                self._listening = True
                self._set_status("● listening", "#4fc3f7")
                run_jarvis_once(gui=self)
                self._listening = False
                if self._running:
                    self._set_status("● active", ACCENT)
            except Exception as e:
                self._listening = False
                self.log_error(f"Error: {e}\n")
                time.sleep(1)

    def _on_text_submit(self, event=None):
        text = self.text_input.get().strip()
        if not text or text == "type a command...":
            return
        self.text_input.delete(0, tk.END)
        self.log_user(text)
        Thread(target=self._text_query, args=(text,), daemon=True).start()

    def _text_query(self, text):
        from main import process_text
        self._set_status("● thinking", ACCENT2)
        response = process_text(text)
        self.log_jarvis(response)
        from src.tts.speaker import speak
        speak(response)
        self._set_status("● idle", MUTED)

    def _on_voice_change(self):
        from src.tts.speaker import set_voice
        set_voice(self.voice_var.get())
        self.log_system(f"Voice → {self.voice_var.get()}\n")

    def _clear_chat(self):
        self.chat.config(state=tk.NORMAL)
        self.chat.delete("1.0", tk.END)
        self.chat.config(state=tk.DISABLED)

    # ── Logging ───────────────────────────────────────────────────────────────

    def log_user(self, text):
        self._append("\n🧑  You: ", "user")
        self._append(text + "\n", "body")

    def log_jarvis(self, text):
        self._append("🤖  Jarvis: ", "jarvis")
        self._append(text + "\n", "body")

    def log_system(self, text):
        self._append(text, "system")

    def log_error(self, text):
        self._append(text, "error")

    def _append(self, text, tag="body"):
        def _do():
            self.chat.config(state=tk.NORMAL)
            self.chat.insert(tk.END, text, tag)
            self.chat.see(tk.END)
            self.chat.config(state=tk.DISABLED)
        self.root.after(0, _do)

    def append_log(self, text):
        if "You:" in text:
            self.log_user(text.split("You:", 1)[-1].strip())
        elif "Jarvis:" in text:
            self.log_jarvis(text.split("Jarvis:", 1)[-1].strip())
        elif text.strip():
            self.log_system(text)

    def _set_status(self, text, color):
        self.root.after(0, lambda: (self.status_var.set(text), self.status_lbl.config(fg=color)))

    def _animate_wave(self):
        c = self.wave_canvas
        c.delete("all")
        w, h, mid = 220, 36, 18
        amp = 12 if self._listening else 2
        pts = []
        for i in range(61):
            x = i * (w / 60)
            y = mid + amp * math.sin((i / 60) * 4 * math.pi + self._wave_phase)
            pts += [x, y]
        if len(pts) >= 4:
            c.create_line(pts, fill=ACCENT if self._listening else MUTED, width=1.5, smooth=True)
        self._wave_phase += 0.14
        self.root.after(35, self._animate_wave)

    def _update_mem_stats(self):
        try:
            from src.memory.memory_system import get_recent_memories
            mems = get_recent_memories(3)
            text = f"{len(mems)} recent\n" + "\n".join(f"• {m[:28]}..." for m in mems[:2])
        except Exception:
            text = "—"
        self.mem_label.config(text=text)
        self.root.after(10000, self._update_mem_stats)

    def get_enabled_skills(self):
        return {k for k, v in self._skill_vars.items() if v.get()}


class _LogRedirector(io.TextIOBase):
    def __init__(self, gui):
        self.gui = gui
    def write(self, text):
        if text and text.strip():
            self.gui.root.after(0, self.gui.append_log, text)
        return len(text)
    def flush(self):
        pass


def main():
    root = tk.Tk()
    JarvisGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()

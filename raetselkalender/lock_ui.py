"""A single text input for a four-digit code, including leading zeros."""
import tkinter as tk
from .board_canvas import BoardEntry

PAPER = "#fffef9"
INK = "#233a32"
ACCENT = "#27644c"
MUTED = "#63736a"


class LockUI:
    def render_lock(self):
        view = self.puzzle.view
        self.canvas.create_text(28, 24, text="DIE HINWEISE", anchor="nw", fill=MUTED,
                                font=("Helvetica", 10, "bold"))
        y = 65
        for (guess, score), hint in zip(view["lock_clues"], view["hint_texts"]):
            self.canvas.create_text(28, y, text="".join(map(str, guess)), anchor="nw", fill=INK,
                                    font=("Courier", 19, "bold"))
            item = self.canvas.create_text(140, y+3, text=hint, anchor="nw", width=490,
                                           fill=INK, font=("Helvetica", 12))
            y = max(y+30, self.canvas.bbox(item)[3])+25
        item = self.canvas.create_text(28, y+5, text=view["expression"], anchor="nw", width=615,
                                       fill=INK, font=("Helvetica", 12))
        y = self.canvas.bbox(item)[3]+40
        self.canvas.create_text(28, y, text="Dein vierstelliger Code", anchor="nw", fill=INK,
                                font=("Helvetica", 12, "bold"))
        var = tk.StringVar()
        validate = self.root.register(lambda text: len(text) <= 4 and all("0" <= c <= "9" for c in text))
        entry = BoardEntry(self.canvas, textvariable=var, justify="center", relief="flat",
                         bg=PAPER, fg=ACCENT, insertbackground=ACCENT,
                         font=("Courier", 24, "bold"), highlightthickness=1,
                         highlightbackground="#d1d8cf", highlightcolor=ACCENT,
                         validate="key", validatecommand=(validate, "%P"))
        self.canvas.create_window(118, y+54, window=entry, width=180, height=52)
        self.vars["Code"], self.entries["Code"] = var, entry
        var.trace_add("write", lambda *args: self.on_change("Code"))
        self.register_input_commit("Code",entry)
        self.canvas.create_text(28, y+96, text="Führende Nullen bitte mit eingeben.", anchor="nw",
                                fill=MUTED, font=("Helvetica", 10))
        self.canvas.configure(scrollregion=(0, 0, 665, y+135))

    def lock_solution(self):
        return "".join(str(self.puzzle.solution[key]) for key in self.puzzle.view["code_keys"])

    def on_lock_change(self):
        text = self.vars["Code"].get()
        entry = self.entries["Code"]
        entry.configure(bg=PAPER, fg=ACCENT)
        if len(text) != 4 or any(c < "0" or c > "9" for c in text):
            self.hide_success(reset=True)
            self.dismiss_error(reset=True)
        if len(text) > 4 or any(c < "0" or c > "9" for c in text):
            self.status.configure(text="Bitte genau vier Ziffern von 0 bis 9 eingeben.", foreground="#9a3c30")
        elif len(text) < 4:
            self.status.configure(text=f"{len(text)} von 4 Ziffern eingegeben · der vollständige Code wird automatisch geprüft.", foreground=MUTED)
        else:
            values = dict(zip(self.puzzle.view["code_keys"], map(int, text)))
            state, wrong = self.puzzle.check(values)
            if state == "correct":
                self.show_success()
            else:
                self.show_error_count(len(wrong))

    def toggle_lock_solution(self):
        self.showing_solution = not self.showing_solution
        self.updating = True
        entry, var = self.entries["Code"], self.vars["Code"]
        if self.showing_solution:
            self.saved_code = var.get()
            var.set(self.lock_solution())
            entry.configure(state="readonly", readonlybackground="#e6eee5", fg=INK)
            self.solution_button.configure(text="Zurück zu meinen Eingaben")
            self.reset_button.configure(state="disabled")
            self.status.configure(text="Lösungsansicht · dein eingegebener Code bleibt erhalten.", foreground=INK)
        else:
            entry.configure(state="normal")
            var.set(self.saved_code)
            self.solution_button.configure(text="Lösung ansehen")
            self.reset_button.configure(state="normal")
        self.updating = False
        if not self.showing_solution:
            self.on_lock_change()

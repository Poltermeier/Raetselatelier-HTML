"""Mouse marks for nonograms; unmarked cells can remain empty at completion."""
from tkinter import ttk

from .picture_nonogram import LIVES

INK, PAPER, RED = "#233a32", "#fffef9", "#a62531"


class NonogramUI:
    def setup_picture_nonogram_toolbar(self):
        self.nonogram_toolbar = ttk.Frame(self.main)
        self.nonogram_fill_button = ttk.Button(self.nonogram_toolbar, text="Ausmalen",
                                              command=lambda: self.select_nonogram_mark("1"))
        self.nonogram_cross_button = ttk.Button(self.nonogram_toolbar, text="Kreuz setzen",
                                               command=lambda: self.select_nonogram_mark("0"))
        self.nonogram_lives_label = ttk.Label(self.nonogram_toolbar, font=("Helvetica", 11, "bold"))
        for button in (self.nonogram_fill_button, self.nonogram_cross_button):
            button.pack(side="left", padx=(0, 7))
        self.nonogram_lives_label.pack(side="left")

    def reset_nonogram_lives(self):
        self.nonogram_lives = LIVES if self.puzzle.view["kind"] == "picture-nonogram" else None
        self.nonogram_mark = "1"
        self.nonogram_mistake = None
        self.nonogram_won = False

    def select_nonogram_mark(self, mark):
        self.nonogram_mark = mark
        self.refresh_nonogram_toolbar()

    def refresh_nonogram_toolbar(self):
        if self.nonogram_lives is None:
            return
        state = "disabled" if self.busy or self.showing_solution or self.nonogram_won or not self.nonogram_lives else "normal"
        for tool, button in (("1", self.nonogram_fill_button), ("0", self.nonogram_cross_button)):
            style = "DifficultyOn.TButton" if self.nonogram_mark == tool else "TButton"
            button.configure(style=style, state=state)
        label = f"{self.nonogram_lives} von {LIVES} Leben" if self.nonogram_lives else "Verloren · 0 Leben"
        self.nonogram_lives_label.configure(text=label, foreground=RED if self.nonogram_lives < LIVES else INK)

    def cancel_nonogram_clicks(self):
        for job in getattr(self, 'nonogram_click_jobs', {}).values():
            self.root.after_cancel(job)
        self.nonogram_click_jobs = {}

    def nonogram_cell_at(self, event):
        left, top, step, rows, cols = self.nonogram_geometry
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        r, c = int((y-top)//step), int((x-left)//step)
        return f'{r},{c}' if 0 <= r < rows and 0 <= c < cols else None

    def click_nonogram(self, event, *, cross=False):
        if self.showing_solution or self.busy:
            return
        key = self.nonogram_cell_at(event)
        if key is None:
            return
        self.canvas.focus_set()
        value = "0" if cross else self.nonogram_mark
        self.mark_nonogram(key, value)
        return 'break'

    def mark_nonogram(self, key, value):
        if self.showing_solution or self.busy or key not in self.vars or self.nonogram_lives == 0 or self.nonogram_won:
            return
        if self.note_mode:
            if self.vars[key].get():
                return
            self.note_vars[key].set('' if self.note_vars[key].get() else 'x')
        else:
            if self.nonogram_lives is not None and value == "0" and self.puzzle.solution[key] == 1:
                self.nonogram_lives -= 1
                self.nonogram_mistake = key
                if not self.nonogram_lives:
                    self.close_assistance()
                self.on_change()
                return
            self.nonogram_mistake = None
            self.updating = True
            self.note_vars[key].set('')
            self.vars[key].set('' if self.vars[key].get() == value else value)
            self.updating = False
            self.on_change()

    def paint_nonogram(self):
        values = {k: int(var.get() == '1') for k, var in self.vars.items()}
        clean = self.showing_solution or (self.nonogram_lives != 0 and not self.note_mode
                                          and self.puzzle.check(values)[0] == 'correct')
        self.canvas.delete('nonogram-cross')
        left, top, step, _, _ = self.nonogram_geometry
        for key, var in self.vars.items():
            mistake = self.nonogram_mistake == key and not self.showing_solution
            fill = "#ffe6e7" if mistake else INK if values[key] else PAPER
            tag = f"cell:{key}"
            if self.nonogram_paints.get(key) != fill:
                self.canvas.itemconfigure(tag, fill=fill)
                self.nonogram_paints[key] = fill
            note = not var.get() and self.note_vars[key].get()
            if not clean and (mistake or var.get() == '0' or note):
                r, c = map(int, key.split(','))
                x, y = left + (c+.5)*step, top + (r+.5)*step
                span = min(8, step/4)
                color = RED if mistake else '#9a8f70' if note else '#63736a'
                for dy in (-span, span):
                    self.canvas.create_line(x-span, y-dy, x+span, y+dy, fill=color, width=1.5,
                                            tags=('nonogram-cross', f'nonogram-cross:{key}'))
        self.show_nonogram_result(clean)
        return clean

    def update_picture_nonogram(self):
        self.nonogram_won = self.paint_nonogram()
        self.refresh_nonogram_toolbar()
        if self.nonogram_won:
            self.show_success()
            self.status.configure(text=f"Richtig gelöst! · {self.puzzle.result}", foreground=INK)
            return
        self.hide_success(reset=True)
        self.dismiss_error(reset=True)
        if not self.nonogram_lives:
            text = "Verloren · Keine Leben mehr. Setze die Eingaben zurück oder starte ein neues Rätsel."
        elif self.nonogram_mistake:
            text = "Falsches Kreuz · Ein Leben verloren."
        else:
            marked = sum(var.get() == "1" for var in self.vars.values())
            required = sum(self.puzzle.solution.values())
            text = f"{marked} von {required} Bildfeldern ausgemalt."
        self.status.configure(text=text, foreground=RED if self.nonogram_mistake else INK)

    def show_nonogram_result(self, visible):
        self.canvas.itemconfigure("puzzle-result", text=f"Ergebnis: {self.puzzle.result}" if visible else "")

"""Circle inputs, ordered arithmetic and touch-friendly block rotations."""
import tkinter as tk

from .new_puzzles import inverse_turns, rotate_block

NEW_ACTIVITY_MODES = {"friedman", "twiddle"}
INK, MUTED, ACCENT = "#233a32", "#63736a", "#27644c"
TWIDDLE_START = 28


class NewPuzzlesUI:
    def render_distance(self):
        points = self.puzzle.view["points"]
        step = 69
        width, height = 28 + step*self.puzzle.view["cols"], 28 + step*self.puzzle.view["rows"]
        self.canvas.create_rectangle(12, 12, width-12, height-12, fill="#d9f0ed", outline="#8baea4", width=2)
        for x, y in points:
            key = f"{y},{x}"
            cx, cy = 14+(x+.5)*step, 14+(y+.5)*step
            self.cell_bgs[key] = "#fffef9"
            self.canvas.create_oval(cx-23, cy-23, cx+23, cy+23, fill=self.cell_bgs[key], outline="#477e73",
                                    width=2, tags=(f"cell:{key}",))
            self.add_entry(key, cx, cy, 31, borderless=True, font_size=17)
        self.canvas.configure(scrollregion=(0, 0, width, height))

    def initial_new_activity(self):
        if self.puzzle.view["mode"] == "friedman":
            return {"expression": ""}
        return {"board": self.puzzle.view["initial"], "moves": []}

    def render_new_activity(self):
        if self.puzzle.view["mode"] == "friedman":
            self.workshop_entries_ui = {}
            self.friedman_variable = tk.StringVar()
            self.friedman_entry = self.workshop_entry(206, 189, 368, self.friedman_variable, self.edit_friedman, key="expression")
            self.friedman_entry.bind("<Return>", lambda event: self.submit_friedman() or "break")
            self.activity_button("Ausdruck prüfen", self.submit_friedman, 206, 246)
        else:
            self.twiddle_direction = 1
            self.twiddle_step = 0
            self.twiddle_replay = ()
            self.twiddle_buttons = {}
            size, block = self.puzzle.view["size"], self.puzzle.view["block"]
            self.twiddle_cell_size = 84 if size == 3 else 75
            bottom = TWIDDLE_START+size*self.twiddle_cell_size
            self.twiddle_directions = [
                self.activity_button(label, lambda turn=turn: self.set_twiddle_direction(turn),
                                     x, bottom+38, 150, tags=("twiddle-play",), style="TButton")
                for x, label, turn in ((91, "↶ Links", -1), (251, "↻ Rechts", 1))
            ]
            for r in range(size-block+1):
                for c in range(size-block+1):
                    x, y = self.twiddle_center(r, c)
                    if block == 3:
                        x += 22
                        y += 22
                    button_size = 28 if block == 3 else 34
                    self.twiddle_buttons[r, c] = self.activity_button(
                        "↻", lambda r=r, c=c: self.play_twiddle(r, c), x, y, button_size,
                        height=button_size, style="TButton", tags=("twiddle-play",))
            self.twiddle_navigation = [
                self.activity_button(label, lambda op=op: self.navigate_twiddle(op),
                                     56+i*79, bottom+38, 74, tags=("twiddle-replay",), style="TButton")
                for i, (label, op) in enumerate((("Anfang", 0), ("Zurück", -1), ("Weiter", 1), ("Ziel", 2)))
            ]
            self.canvas.bind("<Button-3>", lambda event: self.click_twiddle(event, reverse=True))
            self.canvas.bind("<Button-1>", self.click_twiddle)
        self.paint_new_activity()

    def edit_friedman(self):
        if not self.updating and not self.showing_solution and not self.busy:
            self.activity_state["expression"] = self.friedman_variable.get()
            self.on_change()

    def submit_friedman(self):
        if self.busy or self.showing_solution:
            return
        state, message = self.puzzle.check_expression(self.activity_state["expression"])
        if state == "correct":
            self.show_success()
        else:
            self.show_error_popup(message)

    def twiddle_center(self, r, c):
        step = self.twiddle_cell_size
        offset = self.puzzle.view["block"] / 2
        return TWIDDLE_START+(c+offset)*step, TWIDDLE_START+(r+offset)*step

    def set_twiddle_direction(self, direction):
        if not self.busy and not self.showing_solution:
            self.twiddle_direction = direction
            self.paint_activity()

    def click_twiddle(self, event, reverse=False):
        if self.busy or self.showing_solution:
            return
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        width = self.twiddle_cell_size
        for r, c in self.twiddle_buttons:
            cx, cy = self.twiddle_center(r, c)
            if abs(cx-x) <= width/2 and abs(cy-y) <= width/2:
                self.play_twiddle(r, c, -self.twiddle_direction if reverse else self.twiddle_direction)
                break

    def play_twiddle(self, r, c, direction=None):
        if self.busy or self.showing_solution or self.activity_state["board"] == self.puzzle.view["target"]:
            return
        action = r, c, self.twiddle_direction if direction is None else direction
        view = self.puzzle.view
        self.activity_state["board"] = rotate_block(self.activity_state["board"], view["size"], view["block"], action)
        self.activity_state["moves"].append(action)
        self.on_change()

    def prepare_new_activity_solution(self):
        if self.puzzle.view["mode"] == "friedman":
            self.activity_state = {"expression": self.puzzle.result}
        else:
            view = self.puzzle.view
            replay = [view["initial"]]
            for action in self.puzzle.solution.values():
                replay.append(rotate_block(replay[-1], view["size"], view["block"], action))
            self.twiddle_replay = tuple(replay)
            self.twiddle_step = 0

    def navigate_twiddle(self, operator):
        last = len(self.twiddle_replay)-1
        if self.showing_solution and not self.busy:
            self.twiddle_step = {0: 0, -1: max(0, self.twiddle_step-1), 1: min(last, self.twiddle_step+1), 2: last}[operator]
            self.paint_activity()
            self.status.configure(text=f"Lösungsweg · {self.twiddle_step} von {last} Drehungen", foreground=INK)

    def twiddle_hint(self):
        view = self.puzzle.view
        board = self.activity_state["board"]
        if board == view["target"]:
            return "Alle Zahlen stehen richtig."
        sample = view["initial"]
        for action in self.puzzle.solution.values():
            if sample == board:
                break
            sample = rotate_block(sample, view["size"], view["block"], action)
        else:
            action = inverse_turns(self.activity_state["moves"])[0]
        r, c, direction = action
        x, y = self.twiddle_center(r, c)
        radius = view["block"]*self.twiddle_cell_size/2
        self.outline_assist((x-radius, y-radius, x+radius, y+radius), hint=True)
        return f"Drehe den markierten Block nach {'rechts' if direction == 1 else 'links'}."

    def paint_new_activity(self):
        if self.puzzle.view["mode"] == "friedman":
            expression = self.activity_state["expression"]
            if self.friedman_variable.get() != expression:
                old = self.updating
                self.updating = True
                self.friedman_variable.set(expression)
                self.updating = old
            self.word_text(22, 24, "Zielzahl", size=13, bold=True)
            self.canvas.create_text(206, 102, text=str(self.puzzle.view["number"]), fill=INK,
                                    font=("Helvetica", 46, "bold"), tags=("activity-board",))
            self.word_text(22, 142, "Beispiellösung" if self.showing_solution else "Dein Ausdruck", size=12)
            if not self.showing_solution:
                self.word_text(22, 297, "+  −  ×  /  ^  ( )", size=14, color=MUTED)
            self.canvas.configure(scrollregion=(0, 0, 412, 349), cursor="")
            self.update_activity_controls()
            return

        view = self.puzzle.view
        board = self.twiddle_replay[self.twiddle_step] if self.showing_solution else self.activity_state["board"]
        step, size = self.twiddle_cell_size, view["size"]
        for index, value in enumerate(board):
            r, c = divmod(index, size)
            x, y = TWIDDLE_START+c*step, TWIDDLE_START+r*step
            self.canvas.create_rectangle(x, y, x+step, y+step, fill="#f1f5ed" if index % 2 else "#e6efe5",
                                         outline="#96b09b", width=2, tags=("activity-board", f"twiddle-tile:{index}"))
            inset = 6 if not self.showing_solution and view["block"] == 3 and (r-1, c-1) in self.twiddle_buttons else 0
            self.canvas.create_text(x+step/2-inset, y+step/2-inset, text=str(value), fill=INK,
                                    font=("Helvetica", 25, "bold"), tags=("activity-board",))
        following = self.puzzle.solution.get(self.twiddle_step) if self.showing_solution else None
        if following:
            r, c, _ = following
            x, y = TWIDDLE_START+c*step, TWIDDLE_START+r*step
            span = view["block"]*step
            self.canvas.create_rectangle(x+3, y+3, x+span-3, y+span-3, outline="#17619b", width=4,
                                         tags=("activity-board", "twiddle-next-block"))
        for index, control in enumerate(self.twiddle_directions):
            active = self.twiddle_direction == (-1, 1)[index]
            control.configure(style="Accent.TButton" if active else "TButton")
        for button in self.twiddle_buttons.values():
            button.configure(text="↻" if self.twiddle_direction == 1 else "↶")
        self.update_activity_controls()
        self.canvas.itemconfigure("twiddle-play", state="hidden" if self.showing_solution else "normal")
        self.update_activity_solution_navigation("twiddle-replay", self.twiddle_navigation,
                                                 self.twiddle_step, len(self.twiddle_replay)-1)
        text = (f"Lösungsweg · {self.twiddle_step} von {len(self.twiddle_replay)-1} Drehungen" if self.showing_solution
                else f"Drehungen · {len(self.activity_state['moves'])}")
        if following:
            text += " · weiter nach " + ("rechts" if following[-1] == 1 else "links")
        self.word_text(28, TWIDDLE_START+size*step+71, text, size=12, color=MUTED)
        self.canvas.configure(scrollregion=(0, 0, 363, TWIDDLE_START+size*step+105), cursor="hand2")

    def on_new_activity_change(self):
        self.paint_activity()
        if self.puzzle.view["mode"] == "friedman":
            solved = self.puzzle.check_expression(self.activity_state["expression"])[0] == "correct"
            text = "Setze die Ziffern in der vorgegebenen Reihenfolge ein."
        else:
            solved = self.activity_state["board"] == self.puzzle.view["target"]
            text = f"{len(self.activity_state['moves'])} Drehungen · ordne die Zahlen zeilenweise."
        if solved:
            self.show_success()
        else:
            self.hide_success(reset=True)
            self.dismiss_error(reset=True)
            self.status.configure(text=text, foreground=INK)

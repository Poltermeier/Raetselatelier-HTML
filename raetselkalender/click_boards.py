"""Mouse input for binary boards and bridges; unmarked positions mean zero."""
import tkinter as tk

INK = "#233a32"
ACCENT = "#27644c"


class ClickBoardUI:
    def is_click_board(self):
        return bool(self.puzzle and (self.puzzle.type_id in ("kistenguck", "pontifex-hashikake", "camping", "nonogramm", 'kaesekaestchen', 'osternest-sudoku')
            or self.puzzle.view['kind'] in ('routes','matrix','cats','mines','binary-symbols','treasure')))

    def register_click_value(self, key):
        self.vars[key] = tk.StringVar()
        self.note_vars[key] = tk.StringVar()
        self.vars[key].trace_add("write", lambda *args: self.on_change())
        self.note_vars[key].trace_add("write", lambda *args: self.on_change())

    def paint_click_board(self):
        if self.puzzle.view['kind'] in ('cats','matrix'):
            self.paint_matrix()
        elif self.puzzle.view['kind']=='routes':
            self.paint_routes()
        elif self.puzzle.view['kind']=='mines':
            self.paint_mines()
        elif self.puzzle.view['kind']=='binary-symbols':
            self.paint_symbol_grid()
        elif self.puzzle.view['kind']=='treasure':
            self.paint_treasure()
        elif self.puzzle.type_id == "kistenguck":
            self.paint_boxes()
        elif self.puzzle.type_id == "camping":
            self.paint_camping()
        elif self.puzzle.type_id == "nonogramm":
            self.paint_nonogram()
        elif self.puzzle.type_id == 'kaesekaestchen':
            self.paint_cheese()
        elif self.puzzle.type_id == 'osternest-sudoku':
            self.paint_nest()
        else:
            self.paint_hashi()

    def on_click_board_change(self):
        values, invalid = {}, []
        for key, var in self.vars.items():
            try:
                value = int(var.get()) if var.get() else 0
                if value not in self.puzzle.model.domains[key]:
                    invalid.append(key)
                values[key] = value
            except ValueError:
                invalid.append(key)
        self.paint_click_board()
        if self.note_mode:
            self.hide_success()
            self.dismiss_error()
            self.note_status()
            return
        if invalid:
            self.hide_success(reset=True)
            self.dismiss_error(reset=True)
            self.status.configure(text="Ungültiger Wert im Diagramm.", foreground="#9a3c30")
            return
        if self.puzzle.type_id == 'kaesekaestchen':
            count = sum(bool(var.get()) for var in self.vars.values())
            ready = count == len(self.vars)
            progress = f'{count} von {len(self.vars)} Kästchen ausgefüllt · klicken für X oder O.'
        elif self.puzzle.type_id == "nonogramm":
            count = sum(values.values())
            target = sum(sum(hint) for hint in self.puzzle.view['row_hints'])
            ready = count >= target or all(var.get() for var in self.vars.values())
            progress = f"{count} von {target} Bildfeldern ausgemalt · übrige Felder zählen als frei."
        elif self.puzzle.type_id in ("kistenguck", "camping", 'osternest-sudoku','minesweeper'):
            count = sum(values.values())
            target = {'kistenguck': 7, 'osternest-sudoku': 12,'minesweeper':self.puzzle.view.get('mine_count')}.get(self.puzzle.type_id, len(self.puzzle.view.get('trees', [])))
            noun = {'kistenguck': 'Kisten', 'osternest-sudoku': 'Ostereier', 'camping': 'Zelte','minesweeper':'Minen'}[self.puzzle.type_id]
            ready = count == target
            progress = f"{count} von {target} {noun} platziert · leere Felder zählen als frei."
        else:
            totals = [sum(values[k] for k, a, b in self.puzzle.view["edges"] if island in (a, b))
                      for island, _ in self.puzzle.view["islands"]]
            targets = [total for _, total in self.puzzle.view["islands"]]
            ready = totals == targets
            progress = f"{sum(a == b for a, b in zip(totals, targets))} von {len(targets)} Inselzahlen erfüllt · Zwischenräume anklicken."
        if not ready:
            self.hide_success(reset=True)
            self.dismiss_error(reset=True)
            self.status.configure(text=progress, foreground=INK)
            return
        state, wrong = self.puzzle.check(values)
        if state == "correct":
            self.show_success()
        else:
            self.show_error_count(len(wrong))

    def toggle_click_solution(self):
        if not self.showing_solution:
            self.pause_notes_for_solution()
        self.updating = True
        self.showing_solution = not self.showing_solution
        if self.showing_solution:
            self.saved_values = {k: var.get() for k, var in self.vars.items()}
            for key, var in self.vars.items():
                var.set(str(self.puzzle.solution[key]))
            self.solution_button.configure(text="Zurück zu meinen Eingaben")
            self.status.configure(text="Lösungsansicht · deine Eingaben und Notizen bleiben erhalten.", foreground=INK)
        else:
            for key, var in self.vars.items():
                var.set(self.saved_values[key])
            self.solution_button.configure(text="Lösung ansehen")
        self.reset_button.configure(state="disabled" if self.showing_solution else "normal")
        self.updating = False
        self.paint_click_board()
        if not self.showing_solution:
            self.resume_notes_after_solution()
            self.on_change()
        self.update_notes_button()

    def render_boxes(self):
        self.box_step, self.box_margin = 78, 28
        self.box_xy = lambda key: (28+(int(key.split(',')[1])+.5)*78, 28+(int(key.split(',')[0])+.5)*78)
        for r in range(4):
            for c in range(4):
                key = f"{r},{c}"
                x, y = self.box_xy(key)
                self.canvas.create_rectangle(x-39, y-39, x+39, y+39,
                    fill="#e6ebdf" if key in self.puzzle.view["labels"] else "#fffef9", outline="#aebdb1",
                    tags=("box-cell", f"box-cell:{key}"))
                if key in self.puzzle.view["labels"]:
                    self.canvas.create_text(x, y, text=str(self.puzzle.view["labels"][key]),
                        fill=INK, font=("Helvetica", 23, "bold"))
                else:
                    self.register_click_value(key)
        self.canvas.create_text(28, 364, text="Klicken: Kiste setzen / entfernen.\nNotizen: freie Felder durchstreichen.",
            anchor="nw", fill=INK, font=("Helvetica", 11))
        self.canvas.configure(scrollregion=(0, 0, 380, 425))
        self.canvas.bind("<Button-1>", self.click_box)
        self.canvas.configure(cursor="hand2")

    def click_box(self, event):
        if self.showing_solution or self.busy:
            return
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        r, c = int((y-self.box_margin)//self.box_step), int((x-self.box_margin)//self.box_step)
        key = f"{r},{c}"
        if key not in self.vars:
            return
        self.toggle_click_cell(key)

    def toggle_click_cell(self, key):
        if self.showing_solution or self.busy or key not in self.vars:
            return
        if self.note_mode:
            if self.vars[key].get() == "1":
                return
            self.note_vars[key].set("" if self.note_vars[key].get() else "x")
        else:
            self.updating = True
            self.note_vars[key].set("")
            self.vars[key].set("" if self.vars[key].get() == "1" else "1")
            self.updating = False
            self.on_change()

    def paint_boxes(self):
        self.canvas.delete("box-mark")
        for key, var in self.vars.items():
            x, y = self.box_xy(key)
            self.canvas.itemconfigure(f"box-cell:{key}", fill="#fffef9")
            if var.get() == "1":
                tags = ("box-mark", "crate", f"crate:{key}")
                self.canvas.create_rectangle(x-21, y-19, x+21, y+21, fill="#deb887", outline="#80552f", width=2, tags=tags)
                self.canvas.create_line(x-21, y-19, x+21, y+21, fill="#80552f", width=3, tags=tags)
                self.canvas.create_line(x+21, y-19, x-21, y+21, fill="#80552f", width=3, tags=tags)
            elif self.note_vars[key].get() and not self.showing_solution:
                tags = ("box-mark", "box-cross", f"box-cross:{key}")
                self.canvas.create_line(x-22, y-22, x+22, y+22, fill="#8b9491", width=2, tags=tags)
                self.canvas.create_line(x+22, y-22, x-22, y+22, fill="#8b9491", width=2, tags=tags)

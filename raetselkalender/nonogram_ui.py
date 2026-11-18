"""Mouse marks for nonograms; unmarked cells can remain empty at completion."""


class NonogramUI:
    def cancel_nonogram_clicks(self):
        for job in getattr(self, 'nonogram_click_jobs', {}).values():
            self.root.after_cancel(job)
        self.nonogram_click_jobs = {}

    def nonogram_cell_at(self, event):
        left, top, step, rows, cols = self.nonogram_geometry
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        r, c = int((y-top)//step), int((x-left)//step)
        return f'{r},{c}' if 0 <= r < rows and 0 <= c < cols else None

    def click_nonogram(self, event):
        if self.showing_solution or self.busy:
            return
        key = self.nonogram_cell_at(event)
        if key is None:
            return
        self.canvas.focus_set()
        self.mark_nonogram(key,'1')
        return 'break'

    def mark_nonogram(self, key, value):
        if self.showing_solution or self.busy or key not in self.vars:
            return
        if self.note_mode:
            if self.vars[key].get():
                return
            self.note_vars[key].set('' if self.note_vars[key].get() else 'x')
        else:
            self.updating = True
            self.note_vars[key].set('')
            self.vars[key].set('' if self.vars[key].get() == value else value)
            self.updating = False
            self.on_change()

    def paint_nonogram(self):
        values = {k: int(var.get() == '1') for k, var in self.vars.items()}
        clean = self.showing_solution or (not self.note_mode and self.puzzle.check(values)[0] == 'correct')
        self.canvas.delete('nonogram-cross')
        left, top, step, rows, cols = self.nonogram_geometry
        for key, var in self.vars.items():
            self.canvas.itemconfigure(f'cell:{key}', fill='#233a32' if var.get() == '1' else '#fffef9')
            if not clean and (var.get() == '0' or not var.get() and self.note_vars[key].get()):
                r, c = map(int, key.split(','))
                x, y = left+(c+.5)*step, top+(r+.5)*step
                color = '#63736a' if var.get() == '0' else '#9a8f70'
                for dy in (-8, 8):
                    self.canvas.create_line(x-8, y-dy, x+8, y+dy, fill=color, width=1.5,
                                            tags=('nonogram-cross', f'nonogram-cross:{key}'))
        self.show_nonogram_result(clean)

    def show_nonogram_result(self, visible):
        self.canvas.itemconfigure("puzzle-result", text=f"Ergebnis: {self.puzzle.result}" if visible else "")

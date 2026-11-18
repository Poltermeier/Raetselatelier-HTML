"""Editable pour instructions and finite, cancellable water-level animations."""
import tkinter as tk
from tkinter import ttk

from .board_canvas import BoardCombobox
from .pouring import ACTIONS, LETTERS, pour

PAPER, INK, ACCENT = '#fffef9', '#233a32', '#27644c'


class PouringUI:
    def cancel_pour_animation(self):
        job = getattr(self, 'pour_job', None)
        if job is not None:
            self.root.after_cancel(job)
        self.pour_job = None
        self.pour_animating = False
        self.pour_epoch = getattr(self, 'pour_epoch', 0)+1

    def pour_row_values(self):
        return [tuple(var.get() for var in pair) for pair in getattr(self, 'pour_rows', [])]

    def render_pouring(self):
        view = self.puzzle.view
        self.pour_preview_moves = ()
        self.canvas.create_text(28, 24, text='Ausgangslage: '+self.volume_text(view['initial']),
                                anchor='nw', fill=INK, font=('Helvetica', 12, 'bold'))
        self.canvas.create_text(28, 51, text='Ziel: '+self.volume_text(view['target']),
                                anchor='nw', fill=ACCENT, font=('Helvetica', 13, 'bold'))
        self.pour_vessels = []
        for i, capacity in enumerate(view['capacities']):
            x, bottom = 115+200*i, 300
            height = 180*capacity/max(view['capacities'])
            top = bottom-height
            self.pour_vessels.append((x, top, bottom, height))
            self.canvas.create_line(x-33, top, x-33, bottom, x+33, bottom, x+33, top,
                                    fill=INK, width=3, tags=('pour-outline',))
            self.canvas.create_text(x, top-20, text=f'{LETTERS[i]} · {capacity} L',
                                    fill=INK, font=('Helvetica', 14, 'bold'))
        self.canvas.create_text(28, 350, text='Deine Umfüllfolge', anchor='nw', fill=INK, font=('Helvetica', 14, 'bold'))
        self.set_pour_rows([('', '')])
        self.paint_pouring(view['initial'])

    @staticmethod
    def volume_text(values):
        return '   ·   '.join(f'{letter} = {value} L' for letter, value in zip(LETTERS, values))

    def set_pour_rows(self, values):
        previous = self.updating
        self.updating = True
        for widget in getattr(self, 'pour_widgets', []):
            widget.destroy()
        self.pour_widgets = []
        self.canvas.delete('pour-controls')
        self.pour_rows = []
        self.pour_combos, self.pour_remove_buttons = [], []
        for i, (source, target) in enumerate(values):
            y = 400+i*50
            variables = tk.StringVar(value=source), tk.StringVar(value=target)
            self.pour_rows.append(variables)
            self.canvas.create_text(42, y, text=f'{i+1}.', fill=INK, font=('Helvetica', 12), tags=('pour-controls',))
            for x, var in zip((145, 350), variables):
                combo = BoardCombobox(self.canvas, textvariable=var, values=LETTERS,
                                      state='readonly', justify='center', font=('Helvetica', 12, 'bold'))
                self.canvas.create_window(x, y, window=combo, width=130, height=36, tags=('pour-controls',))
                self.pour_combos.append(combo)
                self.pour_widgets.append(combo)
                var.trace_add('write', lambda *args: self.on_change())
            self.canvas.create_text(248, y, text='in', fill=INK, font=('Helvetica', 14), tags=('pour-controls',))
            button = ttk.Button(self.canvas, text='-', command=lambda row=i: self.remove_pour_row(row))
            self.canvas.create_window(465, y, window=button, width=45, height=36, tags=('pour-controls',))
            self.pour_remove_buttons.append(button)
            self.pour_widgets.append(button)
        y = 410+len(values)*50
        self.pour_plus_button = ttk.Button(self.canvas, text='+', command=self.add_pour_row)
        self.pour_finish_button = ttk.Button(self.canvas, text='Fertig - Ziel prüfen',
                                           command=self.evaluate_pours, style='Accent.TButton')
        for x, width, button in ((90, 65, self.pour_plus_button), (315, 310, self.pour_finish_button)):
            self.canvas.create_window(x, y, window=button, width=width, height=42, tags=('pour-controls',))
            self.pour_widgets.append(button)
        self.canvas.configure(scrollregion=(0, 0, 660, y+55))
        self.updating = previous
        self.update_pour_controls()

    def update_pour_controls(self):
        disabled = self.showing_solution or self.busy or getattr(self, 'pour_animating', False)
        for combo in getattr(self, 'pour_combos', []):
            combo.configure(state='disabled' if disabled else 'readonly')
        for button in getattr(self, 'pour_remove_buttons', [])+[self.pour_plus_button, self.pour_finish_button]:
            button.configure(state='disabled' if disabled else 'normal')
        if len(self.pour_rows) == 1:
            self.pour_remove_buttons[0].configure(state='disabled')

    def add_pour_row(self):
        if self.busy or self.showing_solution or self.pour_animating:
            return
        self.set_pour_rows(self.pour_row_values()+[('', '')])
        self.on_change()
        self.canvas.yview_moveto(1)

    def remove_pour_row(self, row):
        if self.busy or self.showing_solution or self.pour_animating or len(self.pour_rows) < 2:
            return
        values = self.pour_row_values()
        values.pop(row)
        self.set_pour_rows(values)
        self.on_change()

    def on_pour_change(self):
        self.hide_success(reset=True)
        self.dismiss_error(reset=True)
        self.sync_pour_preview(animate=not self.history_restoring)

    def preview_pours(self):
        """Only a complete, executable prefix changes the displayed amounts."""
        states = [tuple(self.puzzle.view['initial'])]
        moves, blocked = [], None
        for row, (a, b) in enumerate(self.pour_row_values()):
            if a not in LETTERS or b not in LETTERS:
                break
            action = LETTERS.index(a), LETTERS.index(b)
            following = pour(self.puzzle.view['capacities'], states[-1], *action)
            if following is None:
                blocked = row+1
                break
            moves.append(action)
            states.append(following)
        return tuple(moves), states, blocked

    def sync_pour_preview(self, *, animate=True):
        previous = self.pour_preview_moves
        self.cancel_pour_animation()
        moves, states, blocked = self.preview_pours()
        self.pour_preview_moves = moves
        common = 0
        while common < min(len(previous), len(moves)) and previous[common] == moves[common]:
            common += 1

        def finish():
            self.pour_job = None
            self.pour_animating = False
            self.paint_pouring(states[-1])
            self.update_pour_controls()
            text = (f'Schritt {blocked} ist mit diesen Füllständen nicht möglich.' if blocked else
                    f'Aktueller Füllstand nach {len(moves)} Umfüllvorgängen. + ergänzt einen Schritt; Fertig prüft das Ziel.')
            self.status.configure(text=text, foreground=INK)

        if not animate or common == len(moves):
            finish()
            return
        self.pour_animating = True
        self.update_pour_controls()
        self.canvas.yview_moveto(0)
        epoch = self.pour_epoch

        def frame(step, number=0):
            self.pour_job = None
            if epoch != self.pour_epoch:
                return
            if step == len(moves):
                finish()
                return
            factor = number/12
            amounts = tuple(a+(b-a)*factor for a, b in zip(states[step], states[step+1]))
            self.paint_pouring(amounts, moves[step], number)
            a, b = moves[step]
            self.status.configure(text=f'Schritt {step+1}: {LETTERS[a]} in {LETTERS[b]}', foreground=INK)
            self.pour_job = (self.root.after(30, lambda: frame(step, number+1)) if number < 12
                             else self.root.after(100, lambda: frame(step+1)))
        frame(common)

    def paint_pouring(self, volumes, action=None, frame=0):
        self.pour_display = tuple(volumes)
        self.canvas.delete('pour-liquid')
        self.canvas.delete('pour-current')
        self.canvas.delete('pour-stream')
        for i, (x, top, bottom, height) in enumerate(self.pour_vessels):
            fill_top = bottom-height*volumes[i]/self.puzzle.view['capacities'][i]
            if volumes[i] > 0:
                self.canvas.create_rectangle(x-30, fill_top, x+30, bottom-2, outline='',
                                             fill='#80b8d2', tags=('pour-liquid', f'pour-liquid:{LETTERS[i]}'))
            text = f'{volumes[i]:.1f}'.rstrip('0').rstrip('.') if not float(volumes[i]).is_integer() else str(int(volumes[i]))
            self.canvas.create_text(x, bottom+27, text=text.replace('.', ',')+' L', fill=INK,
                                    font=('Helvetica', 16, 'bold'), tags=('pour-current',))
        self.canvas.tag_lower('pour-liquid', 'pour-outline')
        if action is not None:
            a, b = action
            sx, sy, _, _ = self.pour_vessels[a]
            tx, ty, _, _ = self.pour_vessels[b]
            direction = 1 if tx > sx else -1
            above = min(vessel[1] for vessel in self.pour_vessels)-42
            self.canvas.create_line(sx+33*direction, sy+8, sx+58*direction, above,
                tx-58*direction, above, tx-33*direction, ty+8,
                smooth=True, arrow='last', fill='#3683a7', width=4,
                dash=(6, 4), dashoffset=frame, tags=('pour-stream',))

    def evaluate_pours(self):
        if self.busy or self.showing_solution or self.pour_animating:
            return
        rows = self.pour_row_values()
        if not rows or any(a not in LETTERS or b not in LETTERS for a, b in rows):
            self.show_error_popup('Vervollständige bitte alle Umfüllbausteine.')
            self.status.configure(text='Die Zugliste ist noch unvollständig.', foreground=INK)
            return
        moves = [(LETTERS.index(a), LETTERS.index(b)) for a, b in rows]
        outcome, states = self.puzzle.check_moves(moves)
        self.cancel_pour_animation()
        self.hide_success()
        self.dismiss_error()
        self.paint_pouring(states[-1])
        self.update_pour_controls()
        if outcome == 'correct':
            self.show_success()
        else:
            messages = {'invalid': 'Die Folge enthält einen ungültigen Umfüllvorgang.',
                        'wrong': 'Die Zielverteilung wurde noch nicht erreicht.',
                        'nonoptimal': 'Ziel erreicht – aber es geht mit weniger Umfüllvorgängen.'}
            self.show_error_popup(messages[outcome])
            self.status.configure(text='Umfüllfolge geprüft.', foreground=INK)

    def toggle_pour_solution(self):
        self.updating = True
        self.showing_solution = not self.showing_solution
        if self.showing_solution:
            self.saved_pour_rows = self.pour_row_values()
            rows = [tuple(LETTERS[i] for i in ACTIONS[self.puzzle.solution[k]]) for k in self.puzzle.editable]
            self.set_pour_rows(rows)
            self.paint_pouring(self.puzzle.view['target'])
            self.solution_button.configure(text='Zurück zu meinen Eingaben')
            self.status.configure(text='Eine kürzeste Umfüllfolge · deine Zugliste bleibt erhalten.', foreground=INK)
        else:
            self.set_pour_rows(self.saved_pour_rows)
            self.sync_pour_preview(animate=False)
            self.solution_button.configure(text='Lösung ansehen')
        self.reset_button.configure(state='disabled' if self.showing_solution else 'normal')
        self.updating = False
        self.update_pour_controls()
        if not self.showing_solution:
            self.status.configure(text='Deine Zugliste und ihre Füllstände sind wiederhergestellt. Fertig prüft das Ziel.', foreground=INK)

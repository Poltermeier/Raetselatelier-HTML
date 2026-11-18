"""Undo user edits across numeric, note, click and border input."""
from copy import deepcopy


class HistoryUI:
    def init_history(self):
        self.undo_stack = []
        self.history_state = None
        self.history_restoring = False
        self.border_drag_active = False
        self.route_drag_active = False

    def capture_history(self):
        rectangles = self.puzzle and self.puzzle.view["kind"] == "rectangles"
        hashi = self.puzzle and self.puzzle.view["kind"] == "hashi"
        state = dict(values={} if rectangles else {k: v.get() for k, v in self.vars.items()},
                    notes={k: v.get() for k, v in self.note_vars.items()},
                    borders=set(self.borders) if rectangles else set(),
                    directions=dict(self.hashi_directions) if hashi else {})
        if self.puzzle and self.puzzle.view['kind'] == 'pouring':
            state['pour_rows'] = self.pour_row_values()
        if self.puzzle and self.puzzle.view['kind']=='jump':
            state['jump_path']=self.jump_path.copy()
        if self.puzzle and self.puzzle.view['kind']=='chess':
            state['chess_move']=self.chess_move
        if self.puzzle and self.puzzle.view['kind']=='activity':
            state['activity']=deepcopy(self.activity_state)
        return state

    def update_undo_button(self):
        if hasattr(self, "undo_button"):
            active = bool(self.undo_stack) and not self.busy and not self.showing_solution
            self.undo_button.configure(state="normal" if active else "disabled")

    def record_history(self):
        if (self.history_state is None or self.updating or self.showing_solution
                or self.history_restoring or self.route_drag_active):
            return
        state = self.capture_history()
        if state != self.history_state:
            self.undo_stack.append(self.history_state)
            self.history_state = state
        self.update_undo_button()

    def undo_last(self, event=None):
        if self.busy or self.showing_solution:
            return "break"
        if getattr(self,'pentomino_drag',None) is not None:
            self.cancel_pentomino_drag();return 'break'
        if self.route_drag_active:
            self.finish_route_drag(cancel=True)
            return 'break'
        if getattr(self, 'nonogram_click_jobs', {}):
            self.cancel_nonogram_clicks()
            return "break"
        self.cancel_validation()
        if self.puzzle and self.puzzle.view['kind']=='activity':
            self.cancel_pour_animation();self.activity_selected=None
        if self.puzzle and self.puzzle.view['kind'] == 'pouring':
            self.cancel_pour_animation()
            if not self.undo_stack:
                self.on_pour_change()
                return 'break'
        if self.border_drag_active:
            self.finish_rectangle_drag()
            return "break"
        if not self.undo_stack:
            return "break"
        state = self.undo_stack.pop()
        self.close_chess_menu()
        active_notes = self.note_mode
        self.history_restoring = True
        self.updating = True
        if active_notes:
            self.set_note_mode(False)
        if self.puzzle.view['kind'] == 'pouring':
            self.set_pour_rows(state['pour_rows'])
        if self.puzzle.view['kind']=='jump':
            self.jump_path=state['jump_path'].copy()
        if self.puzzle.view['kind']=='chess':
            self.chess_move=state['chess_move'];self.chess_selected=None
        if self.puzzle.view['kind']=='activity':self.activity_state=deepcopy(state['activity'])
        for key, value in state["values"].items():
            self.vars[key].set(value)
        for key, value in state["notes"].items():
            self.note_vars[key].set(value)
        if self.puzzle.view["kind"] == "rectangles":
            self.borders = set(state["borders"])
            self.refresh_borders()
        if self.puzzle.view["kind"] == "hashi":
            self.hashi_directions = dict(state["directions"])
        self.updating = False
        if active_notes:
            self.set_note_mode(True)
        self.history_state = state
        self.on_change()
        self.history_restoring = False
        self.update_undo_button()
        return "break"

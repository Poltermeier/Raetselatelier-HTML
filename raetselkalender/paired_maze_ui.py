"""Keyboard and touch controls for the atelier's two-piece mazes."""
from .paired_maze import DOWN, LEFT, MINOTAUR, MOVE_NAMES, RIGHT, UP, WAIT, shortest_moves

CELL = 42
MARGIN = 14
TOP = 141
INK = "#233a32"
PANEL = "#faf8ef"
WALL = "#456657"
DUAL_PALETTES = (("#285c83", "#dcecf7"), ("#764692", "#eee1f4"))
KEYS = {"<Up>": UP, "<Right>": RIGHT, "<Down>": DOWN, "<Left>": LEFT}
ACTION_TEXT = ("↑", "→", "↓", "←", "Warten")


class PairedMazeUI:
    def render_maze_game(self):
        self.maze_game = self.puzzle.view["maze"]
        self.maze_state = self.maze_game.start
        self.maze_history = [self.maze_state]
        self.maze_wide = None
        self.maze_frames = []
        self.activity_controls = []
        self.maze_action_buttons = {}
        self.maze_caption = self.canvas.create_text(0, 14, fill=INK, font=("Helvetica", 11, "bold"))
        directions = (UP, LEFT, DOWN, RIGHT)
        actions = directions + (WAIT,) if self.maze_game.variant == MINOTAUR else directions
        for action in actions:
            button = self.activity_button(
                ACTION_TEXT[action], lambda a=action: self.move_maze(a), 0, 0, 74 if action == WAIT else 62,
                tags=(f"maze-control:{action}",), height=45 if action == WAIT else 52, style="TButton",
            )
            self.maze_action_buttons[action] = button
        history_width = 104 if WAIT in actions else 120
        self.maze_undo_button = self.activity_button(
            "Zug zurück", self.undo_maze, 0, 0, history_width, tags=("maze-undo",), height=45, style="TButton")
        self.maze_restart_button = self.activity_button(
            "Neu starten", self.restart_maze, 0, 0, history_width, tags=("maze-restart",), height=45, style="TButton")
        for widget in (self.canvas, *self.activity_controls):
            for key, action in KEYS.items():
                widget.bind(key, lambda event, a=action: self.maze_key(a))
        if WAIT in actions:
            self.canvas.bind("<KeyPress-space>", lambda event: self.maze_key(WAIT))
        self.canvas.focus_set()
        self.layout_maze_game()
        self.update_maze_status()

    def layout_maze_game(self):
        if self.puzzle is None or self.puzzle.view["kind"] != "maze-game":
            return
        boards = self.maze_game.boards
        wide = len(boards) == 2 and self.canvas.winfo_width() >= 610
        if self.maze_wide == wide:
            return
        if self.maze_wide is not None:
            self.clear_hint()
        self.maze_wide = wide
        lane_width = max(316, max(board.width for board in boards) * CELL + 2 * MARGIN)
        gap = 14
        width = lane_width * len(boards) + gap if wide else lane_width
        center = width / 2
        self.canvas.coords(self.maze_caption, center, 14)
        for action, offset in zip(self.maze_action_buttons, (-105, -35, 35, 105)):
            self.canvas.coords(f"maze-control:{action}", center + offset, 51)
        if self.maze_game.variant == MINOTAUR:
            self.canvas.coords(f"maze-control:{WAIT}", center - 112, 109)
            self.canvas.coords("maze-undo", center - 15, 109)
            self.canvas.coords("maze-restart", center + 99, 109)
        else:
            self.canvas.coords("maze-undo", center - 66, 109)
            self.canvas.coords("maze-restart", center + 66, 109)
        self.canvas.delete("maze-board")
        self.maze_origins = []
        y = TOP
        for index, board in enumerate(boards):
            x = (lane_width - board.width * CELL) // 2
            if wide:
                x += index * (lane_width + gap)
            if len(boards) == 2:
                caption = ("1 · Links", "2 · Rechts")[index]
                self.canvas.create_text(x, y + 9, text=caption, anchor="w", fill=DUAL_PALETTES[index][0],
                                        font=("Helvetica", 11, "bold"), tags=("maze-board",))
            top = y + (24 if len(boards) == 2 else 8)
            self.maze_origins.append((x, top))
            self.draw_maze_board(index, board, x, top)
            bottom = top + board.height * CELL
            if not wide:
                y = bottom + 12
        self.canvas.configure(scrollregion=(0, 0, width, bottom + 16))
        self.paint_maze_pieces()

    def draw_maze_board(self, index, board, left, top):
        tag = ("maze-board",)
        for position, steps in enumerate(board.steps):
            r, c = divmod(position, board.width)
            x, y = left + c * CELL, top + r * CELL
            self.canvas.create_rectangle(
                x, y, x + CELL, y + CELL, fill=PANEL, outline="#e3e7de",
                tags=(*tag, f"maze-cell:{index}:{position}"),
            )
        # Paint walls after the tiles so no adjacent tile obscures an edge.
        for position, steps in enumerate(board.steps):
            r, c = divmod(position, board.width)
            x, y = left + c * CELL, top + r * CELL
            if r and steps[UP] == position:
                self.canvas.create_line(x, y, x + CELL, y, fill=WALL, width=3, tags=tag)
            if c and steps[LEFT] == position:
                self.canvas.create_line(x, y, x, y + CELL, fill=WALL, width=3, tags=tag)
        self.canvas.create_rectangle(left, top, left + board.width * CELL, top + board.height * CELL,
                                     outline=WALL, width=3, tags=tag)
        goal = self.maze_game.goals[index]
        x, y = self.maze_cell_center(index, goal)
        fill, border = ("#ddf1dc", "#27644c") if self.maze_game.variant == MINOTAUR else DUAL_PALETTES[index][::-1]
        self.canvas.create_rectangle(x - 16, y - 16, x + 16, y + 16, fill=fill, outline=border, width=2,
                                     tags=(*tag, f"maze-goal:{index}"))
        self.canvas.create_text(x, y, fill=border, text="Z" if self.maze_game.variant == MINOTAUR else str(index+1),
                                font=("Helvetica", 11, "bold"), tags=tag)

    def maze_cell_center(self, board_index, position):
        left, top = self.maze_origins[board_index]
        board = self.maze_game.boards[board_index]
        r, c = divmod(position, board.width)
        return left + (c + .5) * CELL, top + (r + .5) * CELL

    def paint_maze_pieces(self):
        self.canvas.delete("maze-piece")
        pursuit = self.maze_game.variant == MINOTAUR
        faces = (("Du", "#245d50"), ("M", "#a43e30")) if pursuit else (
            ("1", DUAL_PALETTES[0][0]), ("2", DUAL_PALETTES[1][0]))
        for index, (position, (name, color)) in enumerate(zip(self.maze_state, faces)):
            x, y = self.maze_cell_center(0 if pursuit else index, position)
            tag = ("maze-piece", f"maze-piece:{index}")
            self.canvas.create_oval(x - 12, y - 12, x + 12, y + 12, fill=color, outline="#fffef9", width=1.5, tags=tag)
            if pursuit and index == 1:
                self.canvas.create_line(x-10, y-6, x-14, y-11, x-14, y-16, fill=color, width=3, tags=tag)
                self.canvas.create_line(x+10, y-6, x+14, y-11, x+14, y-16, fill=color, width=3, tags=tag)
            self.canvas.create_text(x, y, text=name, fill="#fffef9", font=("Helvetica", 9, "bold"), tags=tag)

    def maze_key(self, action):
        self.move_maze(action)
        return "break"

    def move_maze(self, action):
        if self.busy or self.maze_frames or self.maze_game.result(self.maze_state):
            return
        frames = self.maze_game.trace(self.maze_state, action)
        if not frames:
            self.update_maze_status("Die Mauer blockiert den Zug." if action != WAIT else "Der Minotaurus bleibt stehen.")
            return
        self.clear_hint()
        self.maze_history.append(frames[-1])
        self.maze_frames = list(frames)
        self.advance_maze_turn()

    def advance_maze_turn(self):
        if self.busy:
            self.maze_job = self.root.after(160, self.advance_maze_turn)
            return
        self.maze_job = None
        self.maze_state = self.maze_frames.pop(0)
        self.paint_maze_pieces()
        if self.maze_frames:
            self.update_maze_status("Minotaurus zieht …")
            self.maze_job = self.root.after(160, self.advance_maze_turn)
        else:
            self.update_maze_status()

    def cancel_maze_turn(self):
        if getattr(self, "maze_job", None) is not None:
            self.root.after_cancel(self.maze_job)
            self.maze_job = None

    def undo_maze(self):
        if self.busy or self.maze_frames or len(self.maze_history) == 1:
            return
        self.maze_history.pop()
        self.restore_maze()

    def restart_maze(self):
        if self.busy or self.maze_frames:
            return
        self.maze_history = [self.maze_game.start]
        self.restore_maze()

    def restore_maze(self):
        self.clear_hint()
        self.maze_state = self.maze_history[-1]
        self.paint_maze_pieces()
        self.update_maze_status()

    def update_maze_status(self, message=""):
        result = None if self.maze_frames else self.maze_game.result(self.maze_state)
        moves = len(self.maze_history) - 1
        count = "1 Zug" if moves == 1 else f"{moves} Züge"
        color = INK
        if result == "caught":
            message, color = "Vom Minotaurus gefangen.", "#a43e30"
        elif result == "won":
            message, color = "Ausgang erreicht!" if self.maze_game.variant == MINOTAUR else "Beide Ziele erreicht!", "#27644c"
        status = f"{count} · {message}" if message else count
        self.canvas.itemconfigure(self.maze_caption, text=status, fill=color)
        self.status.configure(text=status, foreground=color)
        for button in self.maze_action_buttons.values():
            button.configure(state="disabled" if result or self.busy else "normal")
        history = moves and not self.maze_frames and not self.busy
        for button in (self.maze_undo_button, self.maze_restart_button):
            button.configure(state="normal" if history else "disabled")

    def maze_hint(self):
        if self.maze_frames:
            return "Warte, bis der Minotaurus seinen Zug beendet hat."
        route = shortest_moves(self.maze_game, self.maze_state)
        if route is None:
            return "Von hier aus führt kein sicherer Weg zum Ziel. Nimm einen Zug zurück oder starte neu."
        if not route:
            return "Das Ziel ist erreicht."
        action = route[0]
        self.outline_assist(self.canvas.bbox(f"maze-control:{action}"), hint=True)
        return "Warte einen Zug." if action == WAIT else f"Ziehe nach {MOVE_NAMES[action].lower()}."

"""Keyboard and touch controls for the atelier's two-piece mazes."""
from .maze_art import draw_maze_token
from .paired_maze import DOWN, LEFT, MINOTAUR, MOVE_NAMES, RIGHT, UP, WAIT, shortest_moves

CELL = 42
MARGIN = 14
TOP = 151
INK = "#233a32"
PANEL = "#faf8ef"
WALL = "#456657"
DUAL_PALETTES = (("#285c83", "#dcecf7"), ("#764692", "#eee1f4"))
KEYS = {"<Up>": UP, "<Right>": RIGHT, "<Down>": DOWN, "<Left>": LEFT}
ACTION_TEXT = ("▲", "▶", "▼", "◀", "Warten")
ARROW_OFFSETS = {UP: (-69, 49), LEFT: (-125, 105), DOWN: (-69, 105), RIGHT: (-13, 105)}


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
                ACTION_TEXT[action], lambda a=action: self.move_maze(a), 0, 0, 110 if action == WAIT else 52,
                tags=(f"maze-control:{action}",), height=34 if action == WAIT else 48,
                style="TButton" if action == WAIT else "MazeDirection.TButton",
            )
            self.maze_action_buttons[action] = button
        self.maze_undo_button = self.activity_button(
            "Zug zurück", self.undo_maze, 0, 0, 110, tags=("maze-undo",), height=34, style="TButton")
        self.maze_restart_button = self.activity_button(
            "Neu starten", self.restart_maze, 0, 0, 110, tags=("maze-restart",), height=34, style="TButton")
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
        for action, (x, y) in ARROW_OFFSETS.items():
            self.canvas.coords(f"maze-control:{action}", center + x, y)
        pursuit = self.maze_game.variant == MINOTAUR
        if pursuit:
            self.canvas.coords(f"maze-control:{WAIT}", center + 86, 37)
        self.canvas.coords("maze-undo", center + 86, 76 if pursuit else 53)
        self.canvas.coords("maze-restart", center + 86, 115 if pursuit else 102)
        self.canvas.delete("maze-board")
        # The backing groups the four controls into a directional pad.
        self.canvas.create_rectangle(center - 156, 23, center + 16, 134,
                                     fill="#e9efe7", outline="#b7c9bc", width=1, tags=("maze-board",))
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
                x, y, x + CELL, y + CELL, fill=PANEL if (r + c) % 2 else "#f3f0e4", outline="#e3e7de",
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
        for index, position in enumerate(self.maze_state):
            x, y = self.maze_cell_center(0 if pursuit else index, position)
            piece = ("hero" if index == 0 else "mino") if pursuit else "gem"
            draw_maze_token(self.canvas, x, y, piece, index)

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

"""Radial grid and board controls for the geometry and placement puzzles."""
from math import cos, pi, sin

from .placement_puzzles import PIECE_NAMES, adjacency, water_options

PLACEMENT_MODES = {"h2o", "schachaufstellung"}
INK, ACCENT, MUTED = "#233a32", "#27644c", "#63736a"
MARGIN = 20
PIECE_SYMBOLS = {"K": "♔", "D": "♕", "T": "♖", "L": "♗", "S": "♘"}
SPRITES = dict(zip("KDTLS", "KQRBN"))


class PlacementUI:
    def render_harakiri(self):
        center = 207
        radii = (53, 96, 139, 182)

        def xy(radius, position):
            angle = position*pi/4
            return center+radius*sin(angle), center-radius*cos(angle)

        self.canvas.create_rectangle(7, 7, 407, 407, fill="#f5f9f3", outline="#a7bba7", width=1)
        self.canvas.create_oval(center-3, center-3, center+3, center+3, fill=INK, outline="")
        for position in range(4):
            self.canvas.create_line(*xy(radii[-1], position), *xy(radii[-1], position+4),
                                    fill="#8aa1a2", width=2, tags=("harakiri-axis",))
        for ring, radius in enumerate(radii):
            self.canvas.create_oval(center-radius, center-radius, center+radius, center+radius,
                                    outline="#66947e", width=2, tags=("harakiri-ring",))
            for position in range(8):
                key = f"{ring},{position}"
                x, y = xy(radius, position)
                bg = "#e3eee2" if key in self.puzzle.givens else "#fffef9"
                self.cell_bgs[key] = bg
                self.canvas.create_oval(x-18, y-18, x+18, y+18, fill=bg, outline="#759d8b", width=2,
                                        tags=(f"cell:{key}",))
                if key in self.puzzle.givens:
                    self.canvas.create_text(x, y, text=str(self.puzzle.givens[key]), fill=INK,
                                            font=("Helvetica", 16, "bold"))
                else:
                    self.add_entry(key, x, y, 25, borderless=True, font_size=16)
        self.canvas.configure(scrollregion=(0, 0, 414, 414))

    def paint_fillomino(self, values):
        self.canvas.delete("fillomino-border")
        size, step = self.puzzle.view["size"], self.puzzle.view["cell_size"]
        values = self.puzzle.givens | values
        for r in range(size):
            for c in range(size):
                value = values.get(f"{r},{c}")
                if not value:
                    continue
                x, y = 28+c*step, 28+r*step
                if c and values.get(f"{r},{c-1}") not in (None, value):
                    self.canvas.create_line(x, y, x, y+step, fill=ACCENT, width=3, tags=("fillomino-border",))
                if r and values.get(f"{r-1},{c}") not in (None, value):
                    self.canvas.create_line(x, y, x+step, y, fill=ACCENT, width=3, tags=("fillomino-border",))

    def render_placement(self):
        self.placement_step = 60 if self.puzzle.view["size"] == 6 else 72
        if self.puzzle.view["mode"] == "schachaufstellung":
            self.ensure_chess_images()
            self.placement_buttons = {}
            for x, piece in enumerate(("K", "D", "T", "L", "S")):
                self.placement_buttons[piece] = self.activity_button(
                    f"{PIECE_SYMBOLS[piece]} {piece}", lambda p=piece: self.select_placement_piece(p),
                    MARGIN+(x+.5)*72, 409, 66, height=43, style="TButton")
        self.canvas.bind("<Button-1>", self.click_placement)
        self.paint_activity()

    def select_placement_piece(self, piece):
        if self.busy or self.showing_solution:
            return
        self.activity_selected = piece if self.activity_selected != piece else None
        self.paint_activity()
        self.refresh_assist_review()
        if self.activity_selected:
            self.status.configure(text=f"{PIECE_NAMES[piece]} ausgewählt · tippe auf ein Feld.", foreground=INK)

    def placement_center(self, cell):
        r, c = divmod(int(cell), self.puzzle.view["size"])
        step = self.placement_step
        return MARGIN+(c+.5)*step, MARGIN+(r+.5)*step

    def click_placement(self, event):
        if self.busy or self.showing_solution:
            return
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        step, size = self.placement_step, self.puzzle.view["size"]
        r, c = int((y-MARGIN)//step), int((x-MARGIN)//step)
        if not (0 <= r < size and 0 <= c < size):
            return
        cell = r*size+c
        if self.puzzle.view["mode"] == "h2o":
            self.click_water_atom(cell)
        else:
            self.click_placement_square(cell)

    def click_water_atom(self, cell):
        view = self.puzzle.view
        placed = self.activity_state["placed"]
        selected = self.activity_selected
        if cell not in view["hydrogen"]:
            if str(cell) in placed:
                del placed[str(cell)]
                self.activity_selected = None
                self.on_change()
                return
            if selected and selected[0] == cell:
                self.activity_selected = None
            else:
                self.activity_selected = (cell, None)
        elif selected:
            center, first = selected
            used = {atom for pair in placed.values() for atom in pair}
            if cell in used or cell not in adjacency(view["size"])[center]:
                self.status.configure(text="Wähle ein freies H direkt neben dem ausgewählten O.", foreground=MUTED)
                return
            if first is not None and first != cell:
                placed[str(center)] = tuple(sorted((first, cell)))
                self.activity_selected = None
                self.on_change()
                return
            self.activity_selected = (center, None if first == cell else cell)
        else:
            self.status.configure(text="Wähle zuerst ein leeres Feld als O.", foreground=MUTED)
            return
        self.on_placement_change()
        self.refresh_assist_review()

    def click_placement_square(self, cell):
        if cell in self.puzzle.view["clues"]:
            return
        placed = self.activity_state["placed"]
        occupant = next((name for name, where in placed.items() if cell == where), None)
        if occupant and occupant == self.activity_selected:
            del placed[occupant]
            self.on_change()
        elif occupant:
            self.select_placement_piece(occupant)
        elif self.activity_selected:
            placed[self.activity_selected] = cell
            self.activity_selected = None
            self.on_change()

    def on_placement_change(self):
        self.paint_activity()
        placed = self.activity_state["placed"]
        puzzle = self.puzzle
        if placed == puzzle.solution:
            self.show_success()
            return
        self.hide_success(reset=True)
        self.dismiss_error(reset=True)
        if puzzle.view["mode"] == "h2o":
            progress = f"{len(placed)} von {len(puzzle.view['hydrogen'])//2} Molekülen verbunden."
            if self.activity_selected:
                progress = "Wähle " + ("das erste" if self.activity_selected[1] is None else "das zweite") + " benachbarte H."
        else:
            progress = f"{len(placed)} von 5 Figuren platziert."
            if self.activity_selected:
                progress = f"{PIECE_NAMES[self.activity_selected]} ausgewählt · tippe auf ein Feld."
        if len(placed) == len(puzzle.solution):
            self.show_error_count(sum(puzzle.solution.get(key) != value for key, value in placed.items()))
        self.status.configure(text=progress, foreground=INK)

    def placement_hint(self):
        view = self.puzzle.view
        if view["mode"] == "schachaufstellung":
            return ("Eine Null schließt alle Positionen aus, von denen aus eine Figur dieses Feld angreifen würde. "
                    "Prüfe dann, welche übrigen Felder für Dame oder Turm infrage kommen.")
        placed = self.activity_state["placed"]
        remaining = set(view["hydrogen"]) - {atom for pair in placed.values() for atom in pair}
        if not remaining:
            return "Alle H sind verbunden. Prüfe, ob sie jeweils genau einmal vorkommen."
        candidates = [triple for triple in water_options(view["size"], remaining)
                      if triple[0] not in view["hydrogen"] and str(triple[0]) not in placed]
        atom = min(remaining, key=lambda cell: (sum(cell in (a, b) for _, a, b in candidates), cell))
        self.outline_assist(self.canvas.bbox(f"placement-cell:{atom}"), hint=True)
        return "Prüfe beim markierten H, welches leere Nachbarfeld es zusammen mit einem zweiten freien H verbinden kann."

    def paint_placement(self):
        view = self.puzzle.view
        size, step = view["size"], self.placement_step
        is_water = view["mode"] == "h2o"
        tag = ("activity-board",)
        for cell in range(size*size):
            r, c = divmod(cell, size)
            x, y = MARGIN+c*step, MARGIN+r*step
            base = "#f7fbf9" if is_water else "#dee7d6" if (r+c) % 2 == 0 else "#99b68e"
            self.canvas.create_rectangle(x, y, x+step, y+step, fill=base, outline="#98ae9d",
                                         tags=(*tag, f"placement-cell:{cell}"))
        placed = self.activity_state["placed"]
        if is_water:
            drawn = [(int(o), pair) for o, pair in placed.items()]
            if self.activity_selected:
                o, a = self.activity_selected
                drawn.append((o, () if a is None else (a,)))
            for o, pair in drawn:
                x, y = self.placement_center(o)
                for cell in pair:
                    self.canvas.create_line(x, y, *self.placement_center(cell), fill="#2c8d97",
                                            width=5, capstyle="round", tags=tag)
            for cell, letter in [*((h, "H") for h in view["hydrogen"]), *((o, "O") for o, _ in drawn)]:
                x, y = self.placement_center(cell)
                selected = self.activity_selected and cell in self.activity_selected
                fill = "#b7ddeb" if selected else "#d7ebf1" if letter == "O" else "#eff9f9"
                self.canvas.create_oval(x-17, y-17, x+17, y+17, fill=fill, outline="#488b93", width=2, tags=tag)
                self.canvas.create_text(x, y, text=letter, fill=INK, font=("Helvetica", 16, "bold"), tags=tag)
        else:
            for cell, clue in view["clues"].items():
                x, y = self.placement_center(cell)
                self.canvas.create_oval(x-16, y-16, x+16, y+16, fill="#f8f9ee", outline="#628670", tags=tag)
                self.canvas.create_text(x, y, text=str(clue), fill=INK, font=("Helvetica", 15, "bold"), tags=tag)
            for piece, cell in placed.items():
                x, y = self.placement_center(cell)
                if piece == self.activity_selected:
                    radius = step/2-4
                    self.canvas.create_rectangle(x-radius, y-radius, x+radius, y+radius, outline="#f5c961", width=4, tags=tag)
                self.canvas.create_scaled_image(x, y, size=step*.85, factory=lambda px, piece=piece: self.chess_piece_image(SPRITES[piece], px), tags=tag)
            for piece, button in self.placement_buttons.items():
                button.configure(state="disabled" if self.showing_solution or self.busy else "normal",
                                 style="Accent.TButton" if piece == self.activity_selected else "TButton")
        height = 400 if is_water else 450
        self.canvas.configure(scrollregion=(0, 0, 400, height), cursor="hand2")

"""Touch and keyboard controls for 4 gewinnt – PopOut."""
from .popout import HEIGHT, WIDTH, STRIDE, PopOutGame, engine_move, legal_moves, winning_cells
from .puzzle import Puzzle
from .solver import Model

INK = "#233a32"
LEFT, TOP, STEP = 18, 64, 58
DISC_COLORS = ("#ed882b", "#54bdd2")


class PopOutUI:
    def start_popout(self, seed):
        from secrets import randbits

        level = self.popout_level.get().lower()
        rules = ("Verbinde vier deiner Kugeln waagerecht, senkrecht oder diagonal. "
                 "Tippe oben auf eine Spalte oder auf ein freies Feld, um eine Kugel einzuwerfen. "
                 "Tippe auf eine eigene Kugel in der untersten Reihe, um sie zu entfernen. "
                 "Die Kugeln darüber rutschen nach. Entstehen gleichzeitig zwei Viererreihen, gewinnt die Seite am Zug. "
                 "Bei dreimal derselben Stellung mit demselben Zugrecht oder ohne legalen Zug endet die Partie remis. "
                 "Mit der Tastatur wählst du die Spalte mit ← und →, wirfst mit ↓ ein und nimmst mit ↑ heraus.")
        puzzle = Puzzle("vier-gewinnt", "4 gewinnt", rules, Model({}, []), {}, {},
                        {"kind": "popout"}, randbits(48) if seed is None else seed, level)
        self.load_puzzle(puzzle)

    def render_popout(self):
        self.popout_game = PopOutGame(self.puzzle.seed, self.puzzle.difficulty)
        self.popout_column = 3
        self.canvas.configure(cursor="hand2")
        self.canvas.bind("<Button-1>", self.click_popout)
        self.canvas.bind("<Left>", lambda event: self.focus_popout_column(-1))
        self.canvas.bind("<Right>", lambda event: self.focus_popout_column(1))
        self.canvas.bind("<Down>", lambda event: self.play_popout(self.popout_column) or "break")
        self.canvas.bind("<Up>", lambda event: self.play_popout(self.popout_column + WIDTH) or "break")
        self.paint_popout()

    def focus_popout_column(self, direction):
        self.popout_column = (self.popout_column + direction) % WIDTH
        self.paint_popout()
        return "break"

    def click_popout(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        column = int((x-LEFT)//STEP)
        if not 0 <= column < WIDTH or not TOP-39 <= y < TOP+HEIGHT*STEP:
            return
        if y < TOP:
            self.play_popout(column)
            return
        row = HEIGHT-1-int((y-TOP)//STEP)
        first, second = self.popout_game.board
        bit = 1 << (column*STRIDE+row)
        if not (first | second) & bit:
            self.play_popout(column)
        elif row == 0 and first & bit:
            self.play_popout(column+WIDTH)

    def cancel_popout(self):
        if getattr(self, "popout_job", None) is not None:
            self.root.after_cancel(self.popout_job)
        self.popout_job = None

    def play_popout(self, move):
        game = self.popout_game
        if self.busy or game.turn != 0 or not game.play(move):
            return
        self.popout_column = move % WIDTH
        self.paint_popout()
        if game.result is None:
            self.popout_job = self.root.after(180, lambda: self.advance_popout(game))

    def advance_popout(self, game):
        if self.puzzle is None or self.puzzle.view["kind"] != "popout" or game is not self.popout_game:
            return
        self.popout_job = None
        if self.busy:
            self.popout_job = self.root.after(180, lambda: self.advance_popout(game))
            return
        if game.turn == 1 and game.result is None:
            game.play(engine_move(game))
            self.paint_popout()

    def paint_popout(self):
        game = self.popout_game
        tag = ("popout-board",)
        self.canvas.delete("popout-board")
        self.canvas.create_rectangle(LEFT, TOP, LEFT+WIDTH*STEP, TOP+HEIGHT*STEP, fill="#173e54",
                                     outline="#103448", width=3, tags=tag)
        winning = winning_cells(game.board[game.result]) if isinstance(game.result, int) else set()
        moves = legal_moves(game.board, 0) if game.turn == 0 and game.result is None and not self.busy else ()
        for column in range(WIDTH):
            x = LEFT+(column+.5)*STEP
            outline = "#1d6b79" if column == self.popout_column else "#a0b9b9"
            self.canvas.create_rectangle(x-25, TOP-35, x+25, TOP-6, fill="#e4f2f2" if column in moves else "#f1f1e9",
                                         outline=outline, width=2 if column == self.popout_column else 1,
                                         tags=(*tag, f"popout-entry:{column}"))
            self.canvas.create_text(x, TOP-21, text="▾" if column in moves else "–", fill=outline,
                                    font=("Helvetica", 13, "bold"), tags=tag)
            for row in range(HEIGHT):
                y = TOP+(HEIGHT-row-.5)*STEP
                bit = 1 << (column*STRIDE+row)
                color = next((p for p in (0, 1) if game.board[p] & bit), None)
                fill = DISC_COLORS[color] if color is not None else "#ebf0ed"
                is_win = (column, row) in winning
                can_pop = row == 0 and column+WIDTH in moves
                self.canvas.create_oval(x-22, y-22, x+22, y+22, fill=fill,
                                         outline="#ffef9c" if is_win else "#fffdf3" if can_pop else "#224b63",
                                         width=4 if is_win else 2 if can_pop else 1,
                                         tags=(*tag, f"popout-cell:{column},{row}"))
                if color is not None:
                    mark = "×" if color else "●"
                    self.canvas.create_text(x, y, text=mark, fill="#15384b", font=("Helvetica", 16, "bold"), tags=tag)
        text = {0: "Du gewinnst!", 1: "Die Engine gewinnt.", "draw": "Remis."}.get(
            game.result, "Du bist am Zug." if game.turn == 0 else "Die Engine denkt …")
        self.canvas.create_text(LEFT, 430, anchor="nw", text="●  Du (Orange)     ×  Engine (Blau)",
                                fill=INK, font=("Helvetica", 12, "bold"), tags=tag)
        self.canvas.configure(scrollregion=(0, 0, LEFT*2+WIDTH*STEP, 466))
        self.status.configure(text=text, foreground=INK)

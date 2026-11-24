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
                 "Mit + wirfst du oben eine Kugel ein. Mit − entfernst du unten eine eigene Kugel. "
                 "Die Kugeln darüber rutschen nach. Entstehen gleichzeitig zwei Viererreihen, gewinnt die Seite am Zug. "
                 "Bei dreimal derselben Stellung mit demselben Zugrecht oder ohne legalen Zug endet die Partie remis.")
        puzzle = Puzzle("vier-gewinnt", "4 gewinnt", rules, Model({}, []), {}, {},
                        {"kind": "popout"}, randbits(48) if seed is None else seed, level)
        self.load_puzzle(puzzle)

    def render_popout(self):
        self.popout_game = PopOutGame(self.puzzle.seed, self.puzzle.difficulty)
        self.activity_controls = []
        self.popout_buttons = {}
        for dropping in (True, False):
            for column in range(WIDTH):
                move = column if dropping else WIDTH+column
                x = LEFT+(column+.5)*STEP
                y = 35 if dropping else TOP+HEIGHT*STEP+30
                visible = f"{'+' if dropping else '−'} {column+1}"
                self.popout_buttons[move] = self.activity_button(
                    visible, lambda move=move: self.play_popout(move), x, y, STEP-6,
                    height=41, style="TButton")
        self.paint_popout()

    def cancel_popout(self):
        if getattr(self, "popout_job", None) is not None:
            self.root.after_cancel(self.popout_job)
        self.popout_job = None

    def play_popout(self, move):
        game = self.popout_game
        if self.busy or game.turn != 0 or not game.play(move):
            return
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
        for column in range(WIDTH):
            x = LEFT+(column+.5)*STEP
            for row in range(HEIGHT):
                y = TOP+(HEIGHT-row-.5)*STEP
                bit = 1 << (column*STRIDE+row)
                color = next((p for p in (0, 1) if game.board[p] & bit), None)
                fill = DISC_COLORS[color] if color is not None else "#ebf0ed"
                is_win = (column, row) in winning
                self.canvas.create_oval(x-22, y-22, x+22, y+22, fill=fill,
                                         outline="#ffef9c" if is_win else "#224b63", width=4 if is_win else 1,
                                         tags=(*tag, f"popout-cell:{column},{row}"))
                if color is not None:
                    mark = "×" if color else "●"
                    self.canvas.create_text(x, y, text=mark, fill="#15384b", font=("Helvetica", 16, "bold"), tags=tag)
        moves = legal_moves(game.board, 0) if game.turn == 0 and game.result is None and not self.busy else ()
        for move, button in self.popout_buttons.items():
            button.configure(state="normal" if move in moves else "disabled")
        text = {0: "Du gewinnst!", 1: "Die Engine gewinnt.", "draw": "Remis."}.get(
            game.result, "Du bist am Zug." if game.turn == 0 else "Die Engine denkt …")
        self.canvas.create_text(LEFT, 478, anchor="nw", text="●  Du (Orange)     ×  Engine (Blau)",
                                fill=INK, font=("Helvetica", 12, "bold"), tags=tag)
        self.canvas.configure(scrollregion=(0, 0, LEFT*2+WIDTH*STEP, 515))
        self.status.configure(text=text, foreground=INK)

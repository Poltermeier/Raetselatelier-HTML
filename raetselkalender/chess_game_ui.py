"""Play a Stockfish match and review each half-move after the result."""
from .puzzle import Puzzle
from .solver import Model

CHESS_ELOS = (1320, 1500, 1750, 2000, 2250, 2500, 2750, 3000)
INK, MUTED = "#233a32", "#63736a"
MATCH_NAV = (("Anfang", "first"), ("Zurück", "previous"), ("Weiter", "next"), ("Ende", "last"))


class ChessGameUI:
    def start_chess_match(self):
        if self.busy or not self.chess_available():
            return
        elo = int(self.chess_elo.get())
        white = self.chess_color.get() == "Weiß"
        puzzle = Puzzle("schach", "Schach", "", Model({}, []), {}, {},
                        {"kind": "chess-match", "elo": elo, "white": white}, 0, "mittel")
        self.load_puzzle(puzzle)

    def render_chess_match(self):
        from .chess_game import ChessGame

        view = self.puzzle.view
        self.chess_match = ChessGame(view["elo"], view["white"])
        self.chess_geometry = 24, 24, 49
        self.chess_white_bottom = view["white"]
        self.chess_selected = None
        self.chess_review_index = None
        self.chess_reviews = {}
        self.chess_match_error = ""
        self.ensure_chess_images()
        self.activity_controls = []
        self.chess_match_buttons = {
            "resign": self.match_button("resign", "Aufgeben", self.resign_chess_match, 83, 461, 119, style="TButton"),
            "draw": self.match_button("draw", "Remis beanspruchen", self.claim_chess_match_draw, 250, 461, 188, style="TButton"),
            "review": self.match_button("review", "Partie analysieren", self.start_chess_review, 111, 461, 174),
            "retry": self.match_button("retry", "Erneut versuchen", self.request_current_chess, 232, 520, 174),
        }
        for index, (text, action) in enumerate(MATCH_NAV):
            self.chess_match_buttons[action] = self.match_button(
                action, text, lambda action=action: self.navigate_chess_review(action), 69+index*99, 461, 89, style="TButton")
        self.canvas.configure(cursor="hand2")
        self.canvas.bind("<Button-1>", self.click_chess_match)
        self.request_current_chess()

    def match_button(self, action, *args, **options):
        return self.activity_button(*args, tags=(f"chess-match-{action}",), **options)

    def cancel_chess_match_request(self):
        job = getattr(self, "chess_match_job", None)
        if job is not None:
            self.root.after_cancel(job)
        self.chess_match_job = None
        future = getattr(self, "chess_match_future", None)
        if future is not None:
            future.cancel()
        self.chess_match_future = None

    def submit_chess_request(self, kind, board, argument):
        from .chess_game import native_chess_request

        return self.pool.submit(native_chess_request, kind, board, argument)

    def request_current_chess(self):
        if self.busy or self.chess_match_future is not None:
            return
        game = self.chess_match
        self.chess_match_error = ""
        index = self.chess_review_index
        if index is not None and index not in self.chess_reviews:
            kind, board, argument = "review", game.position_before(index), game.board.move_stack[index]
        elif not game.result and game.board.turn != game.player:
            kind, board, argument = "play", game.board.copy(), game.elo
        else:
            self.paint_chess_match()
            return
        future = self.submit_chess_request(kind, board, argument)
        self.chess_match_future = future
        self.chess_match_job = self.root.after(50, lambda: self.poll_chess_match(future, index))
        self.paint_chess_match()

    def poll_chess_match(self, future, index):
        import chess

        if future is not self.chess_match_future:
            return
        if self.busy or not future.done():
            self.chess_match_job = self.root.after(50, lambda: self.poll_chess_match(future, index))
            return
        self.chess_match_job = self.chess_match_future = None
        try:
            result = future.result()
            if index is None:
                if not self.chess_match.play(chess.Move.from_uci(result)):
                    raise ValueError("Ungültiger Engine-Zug")
            else:
                self.chess_reviews[index] = result
        except Exception:
            self.chess_match_error = "Stockfish hat keinen Zug oder keine Bewertung geliefert."
        self.paint_chess_match()

    def click_chess_match(self, event):
        game = self.chess_match
        if self.busy or game.result or game.board.turn != game.player:
            return
        square = self.chess_square_at(event)
        if square is not None and self.choose_chess_square(game.board, square, self.play_chess_match_move, event):
            self.paint_chess_match()

    def play_chess_match_move(self, uci):
        import chess

        game = self.chess_match
        if not self.busy and game.board.turn == game.player and game.play(chess.Move.from_uci(uci)):
            self.chess_selected = None
            self.request_current_chess()

    def confirm_chess_resignation(self, callback):
        from tkinter import messagebox

        if messagebox.askyesno("Aufgeben", "Möchtest du diese Partie aufgeben?", parent=self.root):
            callback()

    def resign_chess_match(self):
        if self.busy or self.chess_match.result:
            return
        game = self.chess_match

        def resign():
            if (self.puzzle is not None and self.puzzle.view["kind"] == "chess-match"
                    and self.chess_match is game and not game.result):
                self.cancel_chess_match_request()
                game.resign()
                self.chess_selected = None
                self.chess_match_error = ""
                self.close_chess_menu()
                self.paint_chess_match()

        self.confirm_chess_resignation(resign)

    def claim_chess_match_draw(self):
        self.chess_match.claim_draw()
        self.chess_selected = None
        self.paint_chess_match()

    def start_chess_review(self):
        if self.chess_match.result and self.chess_match.board.move_stack:
            self.navigate_chess_review("first")

    def navigate_chess_review(self, action):
        if self.busy:
            return
        current = self.chess_review_index or 0
        last = len(self.chess_match.board.move_stack) - 1
        self.chess_review_index = {"first": 0, "previous": max(0, current-1),
                                   "next": min(last, current+1), "last": last}[action]
        self.cancel_chess_match_request()
        self.request_current_chess()

    def paint_chess_match(self):
        import chess
        from .chess_explanations import san
        from .chess_game import color_name, review_text

        game = self.chess_match
        index = self.chess_review_index
        board = game.board
        played = board.peek() if board.move_stack else None
        group = "chess-board"
        self.canvas.delete(group)
        if index is not None:
            board = game.position_before(index)
            played = game.board.move_stack[index]
            review = self.chess_reviews.get(index)
            suggested = chess.Move.from_uci(review.best_move) if review else None
            self.draw_chess_position(board, played=played, suggested=suggested)
            move_number = f"{board.fullmove_number}{'.' if board.turn else '…'}"
            title = f"{index+1} / {len(game.board.move_stack)} · Gespielt {move_number} {san(board, played)}"
            text = self.chess_match_error or (review_text(board, played, review) if review else "Stockfish analysiert diese Stellung …")
        else:
            self.draw_chess_position(board, self.chess_selected, played)
            title = game.result or f"{color_name(board.turn)} am Zug"
            if game.result:
                text = game.result
            else:
                text = ("Du bist am Zug." if board.turn == game.player else "Stockfish denkt …")
                if board.is_check():
                    text = f"{color_name(board.turn)} steht im Schach. " + text
                if self.chess_match_error:
                    text = self.chess_match_error
        self.canvas.create_text(23, 486, text=title, anchor="nw", fill=INK, width=392,
                                font=("Helvetica", 13, "bold"), tags=(group,))
        if text != title and not self.chess_match_error:
            self.canvas.create_text(23, 518, text=text, anchor="nw", justify="left", fill=MUTED, width=392,
                                    font=("Helvetica", 12), tags=(group, "chess-match-detail"))
        visible = set()
        if index is not None:
            visible.update(action for _, action in MATCH_NAV)
        elif game.result:
            if game.board.move_stack:
                visible.add("review")
        else:
            visible.add("resign")
            if board.turn == game.player and board.can_claim_draw():
                visible.add("draw")
        if self.chess_match_error:
            visible.add("retry")
        for action, button in self.chess_match_buttons.items():
            self.canvas.itemconfigure(f"chess-match-{action}", state="normal" if action in visible else "hidden")
            enabled = action in visible and (index is None or action == "retry" or (
                index > 0 if action in {"first", "previous"} else index < len(game.board.move_stack)-1))
            button.configure(state="normal" if enabled else "disabled")
        detail = self.canvas.bbox("chess-match-detail")
        self.canvas.configure(scrollregion=(0, 0, 440, max(585, detail[3]+18 if detail else 0)))
        self.status.configure(text=text, foreground=INK)

"""Hearts table, simultaneous passing, and paced opponent turns."""
from .hearts import HeartsMatch, penalty
from .hearts_ai import choose_card, choose_pass
from .playing_cards import card_text, red

SEATS = ("Du", "West", "Nord", "Ost")
DIRECTIONS = {1: "links an West", -1: "rechts an Ost", 2: "gegenüber an Nord"}
INK, ACCENT, MUTED = "#233a32", "#27644c", "#63736a"


class HeartsUI:
    def cancel_hearts_timer(self):
        timer = getattr(self, "hearts_timer", None)
        if timer is not None:
            self.root.after_cancel(timer)
        self.hearts_timer = None

    def reset_hearts_match(self):
        self.cancel_hearts_timer()
        self.hearts_game = HeartsMatch(self.puzzle.seed, self.puzzle.difficulty)
        self.hearts_selection = []
        self.hearts_pause = False
        self.hearts_received = ()
        return {}

    def render_hearts(self):
        self.hearts_cards = [
            self.activity_button("", lambda index=index: self.select_hearts_card(index),
                                 47 + index % 7 * 57, 339 + index // 7 * 57,
                                 50, height=48, style="Card.TButton", tags=(f"hearts-card:{index}",))
            for index in range(13)
        ]
        self.hearts_pass = self.activity_button("Karten weitergeben", self.pass_hearts_cards,
                                               220, 461, 210, height=46, tags=("hearts-pass",))
        self.hearts_round = self.activity_button("Nächste Runde", self.next_hearts_round,
                                                220, 461, 210, height=46, tags=("hearts-round",))
        self.paint_activity()

    def select_hearts_card(self, index):
        game = self.hearts_game
        if self.busy or self.hearts_pause or index >= len(game.hands[0]):
            return
        card = game.hands[0][index]
        if game.stage == "pass":
            if card in self.hearts_selection:
                self.hearts_selection.remove(card)
            elif len(self.hearts_selection) < 3:
                self.hearts_selection.append(card)
            self.on_hearts_change()
        elif game.stage == "play" and game.turn == 0 and card in game.observation(0).legal():
            self.play_hearts_card(card)

    def pass_hearts_cards(self):
        game = self.hearts_game
        if self.busy or game.stage != "pass" or len(self.hearts_selection) != 3:
            return
        outgoing = [tuple(self.hearts_selection)]
        outgoing.extend(choose_pass(game.observation(player), game.difficulty, game.bot_rngs[player])
                        for player in range(1, 4))
        self.hearts_received = tuple(sorted(outgoing[-game.offset % 4]))
        game.exchange(outgoing)
        self.hearts_selection.clear()
        self.on_hearts_change()

    def next_hearts_round(self):
        if self.busy or self.hearts_game.stage != "between":
            return
        self.hearts_game.start_round()
        self.hearts_received = ()
        self.hearts_pause = False
        self.on_hearts_change()

    def play_hearts_card(self, card):
        self.hearts_pause = self.hearts_game.play(card)
        self.on_hearts_change()

    def schedule_hearts_turn(self):
        game = self.hearts_game
        if (self.hearts_timer is None and (self.hearts_pause or
                (game.stage == "play" and game.turn != 0))):
            delay = 950 if self.hearts_pause else 310
            self.hearts_timer = self.root.after(delay, lambda: self.advance_hearts(game))

    def advance_hearts(self, game):
        self.hearts_timer = None
        if self.puzzle.type_id != "hearts" or game is not self.hearts_game:
            return
        if self.busy:
            self.schedule_hearts_turn()
            return
        if self.hearts_pause:
            self.hearts_pause = False
            self.on_hearts_change()
        elif game.stage == "play" and game.turn != 0:
            player = game.turn
            card = choose_card(game.observation(player), game.difficulty, game.bot_rngs[player])
            self.play_hearts_card(card)

    def on_hearts_change(self):
        self.paint_activity()
        self.schedule_hearts_turn()

    def paint_hearts(self):
        game = self.hearts_game
        finished_round = game.stage in ("between", "over")
        self.word_text(17, 16, f"Runde {game.round_number}", size=15, bold=True)
        self.word_text(300, 19, "Ziel · wenige Punkte", size=10, color=MUTED)
        for player, name in enumerate(SEATS):
            x = 16 + player * 105
            current = game.stage == "play" and game.turn == player and not self.hearts_pause
            self.canvas.create_rectangle(x, 52, x + 96, 117, fill="#dceee0" if current else "#edf3ec",
                                         outline="#88a995" if current else "#c1d0c6", tags=("activity-board",))
            self.word_text(x + 9, 59, name, size=12, bold=True)
            self.word_text(x + 9, 88, f"{game.scores[player]} gesamt", size=10)
            if not finished_round:
                self.word_text(x + 61, 62, f"+{game.points[player]}", size=10, color=MUTED)

        shown = game.last_trick if self.hearts_pause or finished_round else game.trick
        subtitle = "Kartenweitergabe" if game.stage == "pass" else "Letzter Stich" if self.hearts_pause or finished_round else "Aktueller Stich"
        self.word_text(17, 137, subtitle, size=13, bold=True)
        cards = dict(shown)
        for player in range(4):
            active = shown and game.last_winner == player and (self.hearts_pause or finished_round)
            self.draw_playing_card(24 + player * 105, 167, 75, 77, cards.get(player),
                                   label="–", active=active, tags=(f"hearts-played:{player}",))
        if (self.hearts_pause or finished_round) and game.last_winner is not None:
            taken = sum(penalty(card) for _, card in game.last_trick)
            winner = "Dein Stich" if game.last_winner == 0 else f"Stich an {SEATS[game.last_winner]}"
            self.word_text(17, 257, f"{winner} · {taken} Punkt{'e' if taken != 1 else ''}", size=11, color=MUTED)
        elif self.hearts_received and not game.history and game.stage == "play":
            self.word_text(17, 257, "Erhalten · " + "   ".join(map(card_text, self.hearts_received)),
                           size=11, color=MUTED)

        if not finished_round:
            self.word_text(17, 288, "Deine Hand", size=13, bold=True)
        self.show_hearts_hand(game)
        passing = game.stage == "pass"
        next_round = game.stage == "between" and not self.hearts_pause
        self.canvas.itemconfigure("hearts-pass", state="normal" if passing else "hidden")
        self.hearts_pass.configure(state="normal" if passing and len(self.hearts_selection) == 3 and not self.busy else "disabled")
        self.canvas.itemconfigure("hearts-round", state="normal" if next_round else "hidden")
        self.hearts_round.configure(state="normal" if next_round and not self.busy else "disabled")
        text = self.hearts_status(game)
        self.word_text(17, 395 if finished_round else 422, text, size=11 if finished_round else 10,
                       width=402, bold=finished_round)
        self.status.configure(text=text, foreground=ACCENT if game.stage == "over" and 0 in game.winners() else INK)
        self.canvas.configure(scrollregion=(0, 0, 440, 510))

    def show_hearts_hand(self, game):
        hand = game.hands[0]
        legal = (game.observation(0).legal() if game.stage == "play" and game.turn == 0
                 and not self.hearts_pause else ())
        for index, button in enumerate(self.hearts_cards):
            visible = index < len(hand)
            self.canvas.itemconfigure(f"hearts-card:{index}", state="normal" if visible else "hidden")
            if not visible:
                continue
            card = hand[index]
            chosen = card in self.hearts_selection
            enabled = game.stage == "pass" and (chosen or len(self.hearts_selection) < 3) or card in legal
            style = "CardSelected.TButton" if chosen else "CardRed.TButton" if red(card) else "Card.TButton"
            button.configure(text=card_text(card), style=style, state="normal" if enabled and not self.busy else "disabled")

    def hearts_status(self, game):
        if game.stage == "pass":
            return f"{len(self.hearts_selection)} von 3 Karten gewählt · weiter {DIRECTIONS[game.offset]}."
        if game.stage == "over":
            winners = game.winners()
            if winners == (0,):
                return "Partie gewonnen."
            prefix = "Geteilter Sieg" if len(winners) > 1 else "Sieger"
            return prefix + " · " + ", ".join(SEATS[player] for player in winners) + "."
        moon = next((player for player, total in enumerate(game.points) if total == 26), None)
        if game.stage == "between":
            if moon is not None:
                return ("Du holst alle 26 Punkte." if moon == 0 else f"{SEATS[moon]} holt alle 26 Punkte.") + " Die anderen erhalten je 26."
            return "Runde beendet · die Punkte wurden addiert."
        if self.hearts_pause:
            return "Stich ausgewertet."
        return "Du bist am Zug." if game.turn == 0 else f"{SEATS[game.turn]} ist am Zug."

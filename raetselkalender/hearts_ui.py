"""Hearts table, simultaneous passing, and paced opponent turns."""
from time import monotonic

from .hearts import HeartsMatch, hearts_hand_order, penalty
from .hearts_ai import choose_card, choose_pass
from .playing_cards import card_text, red

SEATS = ("Du", "Mara", "Nils", "Lea")
DIRECTIONS = {1: "links", -1: "rechts", 2: "gegenüber"}
INK, ACCENT, MUTED = "#233a32", "#27644c", "#63736a"
LEAD_COLOR = "#185b86"
CARD_WIDTH, CARD_HEIGHT = 54, 78
HAND_TOP, HAND_ROW_GAP = 337, 90
BOT_DELAY_MS, TRICK_PAUSE_MS = 1000, 950
FLIGHT_SECONDS = .28
TRICK_TOP, TRICK_WIDTH, TRICK_HEIGHT = 153, 75, 48


def hand_spacing(count):
    return min(59, (404 - CARD_WIDTH) / max(count - 1, 1))


def hand_rows(count, zoom):
    if count > 9 or (count > 7 and hand_spacing(count) * zoom < 30):
        first = (count + 1) // 2
        return first, count - first
    return (count,) if count else ()


class HeartsUI:
    animate_hearts_cards = True

    def cancel_hearts_timer(self):
        for timer in (getattr(self, "hearts_timer", None), getattr(self, "hearts_flight_timer", None)):
            if timer is not None:
                self.root.after_cancel(timer)
        self.hearts_timer = self.hearts_flight_timer = None
        self.hearts_flight = None

    def reset_hearts_match(self):
        self.cancel_hearts_timer()
        self.hearts_game = HeartsMatch(self.puzzle.seed, self.puzzle.difficulty)
        self.hearts_selection = []
        self.hearts_pause = False
        self.hearts_last_trick, self.hearts_last_winner = (), None
        self.hearts_received = ()
        return {}

    def render_hearts(self):
        self.hearts_cards = [
            self.activity_button("", lambda index=index: self.select_hearts_card(index),
                                 0, 0, CARD_WIDTH, height=CARD_HEIGHT,
                                 style="Card.TButton", tags=(f"hearts-card:{index}",))
            for index in range(13)
        ]
        self.hearts_pass = self.activity_button("Karten weitergeben", self.pass_hearts_cards,
                                               220, 461, 210, height=46, tags=("hearts-pass",))
        self.hearts_round = self.activity_button("Nächste Runde", self.next_hearts_round,
                                                220, 461, 210, height=46, tags=("hearts-round",))
        self.paint_activity()

    def select_hearts_card(self, index):
        game = self.hearts_game
        if self.busy or self.hearts_pause or self.hearts_flight or index >= len(game.hands[0]):
            return
        card = sorted(game.hands[0], key=hearts_hand_order)[index]
        if game.stage == "pass":
            if card in self.hearts_selection:
                self.hearts_selection.remove(card)
            elif len(self.hearts_selection) < 3:
                self.hearts_selection.append(card)
            self.on_hearts_change()
        elif game.stage == "play" and game.turn == 0 and card in game.observation(0).legal():
            self.play_hearts_card(card, hand_index=index)

    def pass_hearts_cards(self):
        game = self.hearts_game
        if self.busy or game.stage != "pass" or len(self.hearts_selection) != 3:
            return
        outgoing = [tuple(self.hearts_selection)]
        outgoing.extend(choose_pass(game.observation(player), game.difficulty, game.bot_rngs[player])
                        for player in range(1, 4))
        self.hearts_received = tuple(sorted(outgoing[-game.offset % 4], key=hearts_hand_order))
        game.exchange(outgoing)
        self.hearts_selection.clear()
        self.on_hearts_change()

    def next_hearts_round(self):
        if self.busy or self.hearts_game.stage != "between":
            return
        self.hearts_game.start_round()
        self.hearts_received = ()
        self.hearts_pause = False
        self.hearts_last_trick, self.hearts_last_winner = (), None
        self.on_hearts_change()

    def play_hearts_card(self, card, *, hand_index=None):
        game = self.hearts_game
        if not self.animate_hearts_cards:
            self.hearts_pause = game.play(card)
            self.on_hearts_change()
            return
        source = (self.canvas.coords(f"hearts-card:{hand_index}") if hand_index is not None
                  else (64 + game.turn * 105, 84))
        self.hearts_flight = game.turn, card, source, hand_index, monotonic()
        self.on_hearts_change()
        self.hearts_flight_timer = self.root.after(25, lambda: self.advance_hearts_flight(game))

    def advance_hearts_flight(self, game):
        if self.puzzle is None or self.puzzle.type_id != "hearts" or game is not self.hearts_game:
            return
        self.hearts_flight_timer = None
        if not self.hearts_flight:
            return
        _, card, _, _, started = self.hearts_flight
        if not self.busy and monotonic() - started >= FLIGHT_SECONDS:
            self.hearts_flight = None
            self.hearts_pause = game.play(card)
            self.on_hearts_change()
            return
        if not self.busy:
            self.paint_hearts_flight()
        self.hearts_flight_timer = self.root.after(100 if self.busy else 25, lambda: self.advance_hearts_flight(game))

    def paint_hearts_flight(self):
        self.canvas.delete("hearts-flight")
        player, card, (source_x, source_y), hand_index, started = self.hearts_flight
        elapsed = min(1, (monotonic() - started) / FLIGHT_SECONDS)
        progress = 1 - (1 - elapsed) ** 2
        width = CARD_WIDTH + (TRICK_WIDTH - CARD_WIDTH) * progress
        initial_height = CARD_HEIGHT if hand_index is not None else TRICK_HEIGHT
        height = initial_height + (TRICK_HEIGHT - initial_height) * progress
        target_x = 24 + player * 105 + TRICK_WIDTH / 2
        target_y = TRICK_TOP + TRICK_HEIGHT / 2
        x = source_x + (target_x - source_x) * progress - width / 2
        y = source_y + (target_y - source_y) * progress - height / 2 - 56 * elapsed * (1 - elapsed)
        self.canvas.create_rectangle(x+3, y+5, x+width+3, y+height+5, fill="#a1afa3", outline="",
                                     tags=("activity-board", "hearts-flight"))
        self.draw_playing_card(x, y, width, height, card, marked=True, tags=("hearts-flight",), text_tags=("hearts-flight",))

    def schedule_hearts_turn(self):
        game = self.hearts_game
        if (self.hearts_timer is None and not self.hearts_flight and (self.hearts_pause or
                (game.stage == "play" and game.turn != 0))):
            delay = TRICK_PAUSE_MS if self.hearts_pause else BOT_DELAY_MS
            self.hearts_timer = self.root.after(delay, lambda: self.advance_hearts(game))

    def advance_hearts(self, game):
        if self.puzzle is None or self.puzzle.type_id != "hearts" or game is not self.hearts_game:
            return
        self.hearts_timer = None
        if self.busy:
            self.schedule_hearts_turn()
            return
        if self.hearts_pause:
            self.hearts_last_trick, self.hearts_last_winner = game.last_trick, game.last_winner
            self.hearts_pause = False
            self.on_hearts_change()
        elif game.stage == "play" and game.turn != 0:
            player = game.turn
            card = choose_card(game.observation(player), game.difficulty, game.bot_rngs[player])
            self.play_hearts_card(card)

    def on_hearts_change(self):
        self.paint_activity()
        self.schedule_hearts_turn()

    def fit_hearts_hand(self):
        if self.puzzle.type_id == "hearts":
            rows = hand_rows(len(self.hearts_game.hands[0]), self.canvas.zoom)
            if rows != self.hearts_hand_rows:
                self.paint_activity()

    def paint_hearts(self):
        game = self.hearts_game
        finished_round = game.stage in ("between", "over") and not self.hearts_pause
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

        self.word_text(17, 130, "Aktueller Stich", size=13, bold=True)
        current_trick = game.last_trick if self.hearts_pause else game.trick
        if current_trick:
            leader, card = current_trick[0]
            self.word_text(184, 132, f"Ausspiel · {SEATS[leader]} {card_text(card)}", size=10, color=LEAD_COLOR, bold=True)
        latest = current_trick[-1][0] if current_trick else None
        self.draw_hearts_trick(current_trick, TRICK_TOP, "current", latest=latest)
        if self.hearts_received and not game.history and game.stage == "play":
            self.word_text(17, 207, "Erhalten · " + "   ".join(map(card_text, self.hearts_received)),
                           size=10, color=MUTED)

        if self.hearts_last_trick:
            taken = sum(penalty(card) for _, card in self.hearts_last_trick)
            winner = ("Dein Stich" if self.hearts_last_winner == 0
                      else f"Stich an {SEATS[self.hearts_last_winner]}")
            last_result = f"{winner} · {taken} Punkt{'e' if taken != 1 else ''}"
        else:
            last_result = "Noch keiner gespielt"
        self.word_text(17, 230, "Letzter Stich", size=13, bold=True)
        self.word_text(184, 232, last_result, size=10, color=MUTED)
        self.draw_hearts_trick(self.hearts_last_trick, 252, "last", winner=self.hearts_last_winner)

        if game.hands[0]:
            self.word_text(17, 314, "Deine Hand", size=13, bold=True)
        hand_bottom = self.show_hearts_hand(game)
        footer = 327 if finished_round else hand_bottom + 12
        self.canvas.coords("hearts-pass", 220, footer + 57)
        self.canvas.coords("hearts-round", 220, footer + 57)
        passing = game.stage == "pass"
        next_round = game.stage == "between" and not self.hearts_pause
        self.canvas.itemconfigure("hearts-pass", state="normal" if passing else "hidden")
        self.hearts_pass.configure(state="normal" if passing and len(self.hearts_selection) == 3 and not self.busy else "disabled")
        self.canvas.itemconfigure("hearts-round", state="normal" if next_round else "hidden")
        self.hearts_round.configure(state="normal" if next_round and not self.busy else "disabled")
        text = self.hearts_status(game, current_trick)
        self.word_text(17, footer, text, size=11 if finished_round else 10,
                       width=402, bold=finished_round)
        self.status.configure(text=text, foreground=ACCENT if game.stage == "over" and 0 in game.winners() else INK)
        self.canvas.configure(scrollregion=(0, 0, 440, 620))
        if self.hearts_flight:
            self.paint_hearts_flight()

    def draw_hearts_trick(self, trick, y, slot, *, winner=None, latest=None):
        cards = dict(trick)
        leader = trick[0][0] if trick else None
        for player, name in enumerate(SEATS):
            x = 24 + player * 105
            self.draw_playing_card(x, y, TRICK_WIDTH, TRICK_HEIGHT, cards.get(player),
                                   active=player == winner, marked=player == latest,
                                   tags=(f"hearts-{slot}:{player}",))
            self.canvas.create_text(x+5, y+26, text=name, anchor="nw",
                                    fill=INK if player in cards else MUTED,
                                    font=("Helvetica", 11, "bold"),
                                    tags=("activity-board", f"hearts-{slot}-name:{player}"))
            if player == leader:
                self.canvas.create_text(x+69, y+5, text="1.", anchor="ne", fill=LEAD_COLOR,
                                        font=("Helvetica", 11, "bold"),
                                        tags=("activity-board", f"hearts-{slot}-lead:{player}"))

    def show_hearts_hand(self, game):
        hand = sorted(game.hands[0], key=hearts_hand_order)
        moving = self.hearts_flight[3] if self.hearts_flight else None
        legal = (game.observation(0).legal() if game.stage == "play" and game.turn == 0
                 and not self.hearts_pause and not self.hearts_flight else ())
        rows = hand_rows(len(hand), self.canvas.zoom)
        self.hearts_hand_rows = rows
        positions = []
        for row, count in enumerate(rows):
            step = hand_spacing(count)
            for index in range(count):
                offset = index - (count - 1) / 2
                bend = 10 * (offset / max((count - 1) / 2, 1)) ** 2
                positions.append((220 + offset * step, HAND_TOP + row * HAND_ROW_GAP + CARD_HEIGHT / 2 + bend))
        for index, button in enumerate(self.hearts_cards):
            visible = index < len(hand) and index != moving
            self.canvas.itemconfigure(f"hearts-card:{index}", state="normal" if visible else "hidden")
            if not visible:
                continue
            card = hand[index]
            chosen = card in self.hearts_selection
            x, y = positions[index]
            self.canvas.coords(f"hearts-card:{index}", x, y - (9 if chosen else 0))
            enabled = game.stage == "pass" and (chosen or len(self.hearts_selection) < 3) or card in legal
            style = "CardSelected.TButton" if chosen else "CardRed.TButton" if red(card) else "Card.TButton"
            button.configure(text=card_text(card), style=style, state="normal" if enabled and not self.busy else "disabled")
        return HAND_TOP + max(0, len(rows) - 1) * HAND_ROW_GAP + CARD_HEIGHT + 10

    def hearts_status(self, game, current_trick):
        if game.stage == "pass":
            recipient = SEATS[game.offset % 4]
            return f"{len(self.hearts_selection)} von 3 Karten gewählt · weiter an {recipient} ({DIRECTIONS[game.offset]})."
        if current_trick:
            player, card = current_trick[-1]
            if len(current_trick) == 1:
                played = (f"Du spielst {card_text(card)} aus." if player == 0
                          else f"{SEATS[player]} spielt {card_text(card)} aus.")
            else:
                played = f"Du spielst {card_text(card)}." if player == 0 else f"{SEATS[player]} spielt {card_text(card)}."
            if self.hearts_pause:
                result = "Du gewinnst den Stich." if game.last_winner == 0 else f"Der Stich geht an {SEATS[game.last_winner]}."
                return f"{played} {result}"
        else:
            played = ""
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
        turn = "Du bist am Zug." if game.turn == 0 else f"{SEATS[game.turn]} ist am Zug."
        return f"{played} {turn}".strip()

"""Present two open symbol cards in the atelier's game area."""
from secrets import randbits

from .puzzle import Puzzle
from .solver import Model
from .symbol_duel import SYMBOLS_PER_CARD, SymbolDuel
from .symbol_icons import ICONS

CARD_WIDTH = 392
CARD_HEIGHT = 230
MARGIN = 8
GAP = 12
TILE_WIDTH = 88
TILE_HEIGHT = 83
INK = "#233a32"
SURFACES = (
    ("#e9f3ee", "#9dbeb0", "#28634f"),
    ("#edf0f8", "#aebbd1", "#405c88"),
)


class SymbolDuelUI:
    symbol_faces_in_buttons = False

    def start_symbol_duel(self, seed):
        rules = ("Auf den beiden offenen Karten kommt genau ein Symbol doppelt vor. "
                 "Tippe es auf einer der beiden Karten an. Bei jedem Treffer wechselt abwechselnd eine Karte. "
                 "Finde auch das gemeinsame Symbol auf dem letzten Kartenpaar.")
        puzzle = Puzzle("symbol-duel", "Symbolduell", rules, Model({}, []), {}, {},
                        {"kind": "symbol-duel"}, randbits(48) if seed is None else seed, "")
        self.load_puzzle(puzzle)

    def render_symbol_duel(self):
        self.symbol_duel = SymbolDuel(self.puzzle.seed)
        self.symbol_wide = None
        self.symbol_frames = []
        self.activity_controls = []
        self.symbol_buttons = [[], []]
        for side, (background, border, ink) in enumerate(SURFACES):
            panel = self.canvas.create_rectangle(0, 0, 1, 1, fill=background, outline=border, width=1.5)
            heading = self.canvas.create_text(0, 0, anchor="nw", fill=ink, font=("Helvetica", 11, "bold"))
            self.symbol_frames.append((panel, heading))
            for index in range(SYMBOLS_PER_CARD):
                button = self.activity_button(
                    "", lambda s=side, i=index: self.pick_symbol(s, i), 0, 0, TILE_WIDTH,
                    height=TILE_HEIGHT if self.symbol_faces_in_buttons else 26, style="Symbol.TButton",
                    tags=(f"symbol-tile:{side}:{index}",),
                )
                self.symbol_buttons[side].append(button)
        self.symbol_count_text = self.canvas.create_text(0, 0, anchor="w", fill=INK, font=("Helvetica", 11, "bold"))
        self.symbol_feedback = ""
        if not self.symbol_faces_in_buttons:
            self.canvas.bind("<Button-1>", self.click_symbol_duel)
        self.layout_symbol_duel()
        for side in range(2):
            self.paint_symbol_card(side)
        self.update_symbol_status()

    def symbol_card_origin(self, side):
        return (MARGIN + side * (CARD_WIDTH + GAP), 32) if self.symbol_wide else (
            MARGIN, 32 + side * (CARD_HEIGHT + GAP))

    def symbol_tile_origin(self, side, index):
        x, y = self.symbol_card_origin(side)
        row, column = divmod(index, 4)
        return x + 12 + column * (TILE_WIDTH + 5), y + 41 + row * (TILE_HEIGHT + 6)

    def layout_symbol_duel(self):
        if self.puzzle is None or self.puzzle.view["kind"] != "symbol-duel":
            return
        wide = self.canvas.winfo_width() >= 740
        if self.symbol_wide == wide:
            return
        self.symbol_wide = wide
        self.canvas.coords(self.symbol_count_text, MARGIN + 1, 16)
        for side, (panel, heading) in enumerate(self.symbol_frames):
            x, y = self.symbol_card_origin(side)
            self.canvas.coords(panel, x, y, x + CARD_WIDTH, y + CARD_HEIGHT)
            self.canvas.coords(heading, x + 12, y + 10)
            for index in range(SYMBOLS_PER_CARD):
                x, y = self.symbol_tile_origin(side, index)
                self.canvas.coords(f"symbol-tile:{side}:{index}",
                                   x + TILE_WIDTH / 2, y + (TILE_HEIGHT / 2 if self.symbol_faces_in_buttons else 68))
            if not self.symbol_faces_in_buttons:
                self.paint_native_symbol_card(side)
        width = 2 * MARGIN + (2 * CARD_WIDTH + GAP if wide else CARD_WIDTH)
        height = 32 + MARGIN + (CARD_HEIGHT if wide else 2 * CARD_HEIGHT + GAP)
        self.canvas.configure(scrollregion=(0, 0, width, height))

    def set_symbol_face(self, button, icon, card_position):
        button.configure(text=icon[0])

    def paint_native_symbol_card(self, side):
        tag = f"symbol-drawing:{side}"
        self.canvas.delete(tag)
        for index, symbol in enumerate(self.symbol_duel.open_cards[side]):
            x, y = self.symbol_tile_origin(side, index)
            _, color, primitives = ICONS[symbol]
            self.canvas.create_rectangle(x, y, x + TILE_WIDTH, y + 53, fill="#fffef9", outline="", tags=(tag,))
            x += (TILE_WIDTH - 45) / 2
            y += 4
            for kind, points in primitives:
                coords = tuple((x if i % 2 == 0 else y) + point * 45 / 24 for i, point in enumerate(points))
                if kind == "line":
                    self.canvas.create_line(*coords, fill=color, width=2.8, capstyle="round", joinstyle="round", tags=(tag,))
                elif kind in ("oval", "dot"):
                    self.canvas.create_oval(*coords, outline=color, width=2.6 if kind == "oval" else 0,
                                            fill=color if kind == "dot" else "#f7f5ef", tags=(tag,))
                else:
                    self.canvas.create_polygon(*coords, fill="#f7f5ef", outline=color, width=2.6,
                                               joinstyle="round", tags=(tag,))

    def paint_symbol_card(self, side):
        number = self.symbol_duel.open_indices[side] + 1
        label = f"Karte {number}"
        self.canvas.itemconfigure(self.symbol_frames[side][1], text=label)
        for index, symbol in enumerate(self.symbol_duel.open_cards[side]):
            self.set_symbol_face(self.symbol_buttons[side][index], ICONS[symbol], label)
        if not self.symbol_faces_in_buttons:
            self.paint_native_symbol_card(side)

    def click_symbol_duel(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        for side in range(2):
            for index in range(SYMBOLS_PER_CARD):
                left, top = self.symbol_tile_origin(side, index)
                if left <= x <= left + TILE_WIDTH and top <= y < top + TILE_HEIGHT:
                    self.pick_symbol(side, index)
                    return

    def pick_symbol(self, side, index):
        game = self.symbol_duel
        if self.busy or game.finished:
            return
        prior = game.open_indices
        if game.choose(game.open_cards[side][index]):
            self.symbol_feedback = "Partie geschafft!" if game.finished else "Treffer!"
            for position, before in enumerate(prior):
                if game.open_indices[position] != before:
                    self.paint_symbol_card(position)
            if game.finished:
                for button in self.activity_controls:
                    button.configure(state="disabled")
        else:
            self.symbol_feedback = "Kein Treffer."
        self.update_symbol_status()

    def update_symbol_status(self):
        game = self.symbol_duel
        score = f"{game.hits} von {len(game.deck) - 1} Treffern"
        message = f"{score} · {self.symbol_feedback}" if self.symbol_feedback else score
        color = "#943b34" if self.symbol_feedback == "Kein Treffer." else INK
        self.canvas.itemconfigure(self.symbol_count_text, text=message, fill=color)
        self.status.configure(text=message, foreground=color)

"""Present two open symbol cards in the atelier's game area."""
from math import ceil, cos, floor, hypot, radians, sin, sqrt, tau
from random import Random
from secrets import randbits
from typing import NamedTuple

from .puzzle import Puzzle
from .solver import Model
from .symbol_duel import SYMBOLS_PER_CARD, SymbolDuel
from .symbol_icons import ICONS

CARD_RADIUS = 172
INNER_RADIUS = CARD_RADIUS - 4
MIN_TOUCH_RADIUS = 35
SYMBOL_GAP = 3
SYMBOL_STROKE = 1.55
DRAWING_MARGIN = .4
SYMBOL_SIZES = (36, 54, 60, 65, 70, 75, 80, 86)
SYMBOL_ANGLES = (-162, -108, -57, -24, 0, 39, 85, 143)
MARGIN = 8
GAP = 18
HEADING_HEIGHT = 26
SCORE_HEIGHT = 32
CARD_DIAMETER = 2 * CARD_RADIUS
INK = "#233a32"
SURFACES = (
    ("#eaf4ef", "#9dbeb0", "#28634f"),
    ("#f1eff9", "#b9afd0", "#5b467f"),
)


class SymbolPlacement(NamedTuple):
    x: float
    y: float
    radius: int
    size: int
    angle: int


def motif_extent(primitives):
    """Conservative radius, in fractions of the drawing width, at any rotation."""
    radii = []
    for kind, coords, _ in primitives:
        if kind in ("oval", "dot"):
            left, top, right, bottom = coords
            cx, cy = (left + right) / 2, (top + bottom) / 2
            radius = hypot(cx - 12, cy - 12) + max(right - left, bottom - top) / 2
            corner = max(hypot(x - 12, y - 12) for x in (left, right) for y in (top, bottom))
            radius = min(radius, corner)
        else:
            radius = max(hypot(x - 12, y - 12) for x, y in zip(coords[::2], coords[1::2]))
        radii.append(radius + (0 if kind == "dot" else SYMBOL_STROKE / 2))
    return max(radii) / 24


MOTIF_EXTENTS = tuple(motif_extent(primitives) for _, _, primitives in ICONS)


def symbol_touch_radius(size, extent):
    return max(MIN_TOUCH_RADIUS, ceil(size * extent + DRAWING_MARGIN))


def symbol_offsets(rng, radii):
    # Place the largest targets first and keep the two largest close together.
    order = sorted(range(len(radii)), key=radii.__getitem__, reverse=True)
    first, second = order[:2]
    for _ in range(36):
        placed = {}
        for index in order:
            radius = radii[index]
            limit = INNER_RADIUS - radius
            for _ in range(64):
                angle = rng.uniform(0, tau)
                if index == second:
                    cx, cy = placed[first]
                    distance = radius + radii[first] + rng.uniform(SYMBOL_GAP, SYMBOL_GAP + 4)
                else:
                    cx, cy = 0, 0
                    distance = limit * sqrt(rng.random())
                x, y = cx + distance * cos(angle), cy + distance * sin(angle)
                if hypot(x, y) <= limit and all(
                    hypot(x - px, y - py) >= radius + radii[other] + SYMBOL_GAP
                    for other, (px, py) in placed.items()
                ):
                    placed[index] = x, y
                    break
            else:
                break
        else:
            return tuple(placed[index] for index in range(len(radii)))

    # A rotated arrangement is available even if the random attempts run out.
    start = rng.uniform(0, tau)
    ring = len(radii) - 1
    angles = (start + tau * i / ring for i in range(ring))
    orbit = INNER_RADIUS - radii[first]
    offsets = [(orbit * cos(angle), orbit * sin(angle)) for angle in angles]
    offsets.append((0, 0))
    # Spread the larger targets around the rim in the fallback as well.
    positions = dict(zip(order, (offsets[i] for i in (0, 3, 1, 5, 2, 6, 4, 7))))
    return tuple(positions[index] for index in range(len(radii)))


def available_radius(x, y, slots, index):
    room = INNER_RADIUS - hypot(x, y)
    for i, other in enumerate(slots):
        if i != index:
            room = min(room, hypot(x - other.x, y - other.y) - other.radius - SYMBOL_GAP)
    return room


def enlarge_symbols(rng, slots, extents, starting_sizes):
    """Move each motif wherever nearby space allows it to grow."""
    indices = list(range(len(slots)))
    for distance in (33, 18, 8):
        rng.shuffle(indices)
        for index in indices:
            slot = slots[index]
            extent = extents[index]
            limit = round(starting_sizes[index] * 1.42)
            best = slot
            candidates = [(slot.x, slot.y)]
            candidates += [(slot.x + rng.uniform(-distance, distance), slot.y + rng.uniform(-distance, distance))
                           for _ in range(12)]
            for x, y in candidates:
                room = floor(available_radius(x, y, slots, index))
                if room < best.radius:
                    continue
                size = min(limit, floor((room - DRAWING_MARGIN) / extent))
                if size > best.size:
                    best = SymbolPlacement(x, y, symbol_touch_radius(size, extent), size, slot.angle)
            slots[index] = best
    return tuple(slots)


def symbol_placements(seed, card_index, symbols):
    rng = Random(f"{seed}:{card_index}")
    sizes = rng.sample(SYMBOL_SIZES, SYMBOLS_PER_CARD)
    angles = rng.sample(SYMBOL_ANGLES, SYMBOLS_PER_CARD)
    extents = tuple(MOTIF_EXTENTS[symbol] for symbol in symbols)
    radii = tuple(symbol_touch_radius(size, extent) for size, extent in zip(sizes, extents))
    arrangements = []
    for _ in range(5):
        slots = [SymbolPlacement(x, y, radius, size, angle)
                 for (x, y), radius, size, angle in zip(symbol_offsets(rng, radii), radii, sizes, angles)]
        arrangements.append(enlarge_symbols(rng, slots, extents, sizes))
    return max(arrangements, key=lambda slots: sum((slot.size * extent)**2 for slot, extent in zip(slots, extents)))


def native_symbol_points(kind, coords):
    if kind in ("oval", "dot"):
        left, top, right, bottom = coords
        cx, cy = (left + right) / 2, (top + bottom) / 2
        rx, ry = (right - left) / 2, (bottom - top) / 2
        for i in range(24):
            angle = tau * i / 24
            yield cx + rx * cos(angle), cy + ry * sin(angle)
    else:
        yield from zip(coords[::2], coords[1::2])


class SymbolDuelUI:
    symbol_faces_in_buttons = False

    def start_symbol_duel(self, seed):
        rules = ("Auf den beiden offenen Karten kommt genau ein Symbol doppelt vor. "
                 "Tippe es auf einer der beiden Karten an. Bei jedem Treffer wechselt abwechselnd eine Karte. "
                 "Finde auch das gemeinsame Symbol auf dem letzten Kartenpaar.")
        if not self.symbol_faces_in_buttons:
            rules += (" Mit den Pfeiltasten wählst du auf dem Spielfeld ein Symbol aus. "
                      "Mit der Eingabetaste oder der Leertaste bestätigst du.")
        puzzle = Puzzle("symbol-duel", "Symbolduell", rules, Model({}, []), {}, {},
                        {"kind": "symbol-duel"}, randbits(48) if seed is None else seed, "")
        self.load_puzzle(puzzle)

    def render_symbol_duel(self):
        self.symbol_duel = SymbolDuel(self.puzzle.seed)
        self.symbol_wide = None
        self.symbol_frames = []
        self.symbol_slots = [(), ()]
        self.activity_controls = []
        self.symbol_buttons = [[], []]
        for side, (background, border, ink) in enumerate(SURFACES):
            card = self.canvas.create_oval(0, 0, 1, 1, fill=background, outline=border, width=2)
            rim = self.canvas.create_oval(0, 0, 1, 1, outline=border, width=1)
            heading = self.canvas.create_text(0, 0, anchor="n", fill=ink, font=("Helvetica", 12, "bold"))
            self.symbol_frames.append((card, rim, heading))
            if self.symbol_faces_in_buttons:
                for index in range(SYMBOLS_PER_CARD):
                    button = self.activity_button(
                        "", lambda s=side, i=index: self.pick_symbol(s, i), 0, 0,
                        2 * MIN_TOUCH_RADIUS, height=2 * MIN_TOUCH_RADIUS, style="TButton",
                        tags=(f"symbol-tile:{side}:{index}",),
                    )
                    self.symbol_buttons[side].append(button)
        self.symbol_count_text = self.canvas.create_text(0, 0, anchor="w", fill=INK, font=("Helvetica", 11, "bold"))
        self.symbol_feedback = ""
        if not self.symbol_faces_in_buttons:
            self.install_native_symbol_controls()
        self.layout_symbol_duel()
        for side in range(2):
            self.paint_symbol_card(side)
        self.update_symbol_status()

    def symbol_card_center(self, side):
        x, y = MARGIN + CARD_RADIUS, SCORE_HEIGHT + HEADING_HEIGHT + CARD_RADIUS
        if self.symbol_wide:
            return x + side * (CARD_DIAMETER + GAP), y
        return x, y + side * (CARD_DIAMETER + HEADING_HEIGHT + GAP)

    def symbol_tile_center(self, side, slot):
        x, y = self.symbol_card_center(side)
        return x + slot.x, y + slot.y

    def position_symbol_buttons(self, side):
        for index, slot in enumerate(self.symbol_slots[side]):
            tag = f"symbol-tile:{side}:{index}"
            self.canvas.coords(tag, *self.symbol_tile_center(side, slot))
            self.canvas.itemconfigure(tag, width=2 * slot.radius, height=2 * slot.radius)

    def layout_symbol_duel(self):
        if self.puzzle is None or self.puzzle.view["kind"] != "symbol-duel":
            return
        wide = self.canvas.winfo_width() >= 680
        if self.symbol_wide == wide:
            return
        resize = self.symbol_wide is not None
        self.symbol_wide = wide
        self.canvas.coords(self.symbol_count_text, MARGIN + 1, 16)
        for side, (card, rim, heading) in enumerate(self.symbol_frames):
            x, y = self.symbol_card_center(side)
            for item, radius in ((card, CARD_RADIUS), (rim, INNER_RADIUS)):
                self.canvas.coords(item, x - radius, y - radius, x + radius, y + radius)
            self.canvas.coords(heading, x, y - CARD_RADIUS - HEADING_HEIGHT)
            if self.symbol_faces_in_buttons:
                self.position_symbol_buttons(side)
            elif resize:
                self.paint_native_symbol_card(side)
        width = 2 * MARGIN + CARD_DIAMETER + (CARD_DIAMETER + GAP if wide else 0)
        card_with_heading = CARD_DIAMETER + HEADING_HEIGHT
        height = SCORE_HEIGHT + MARGIN + card_with_heading + (card_with_heading + GAP if not wide else 0)
        self.canvas.configure(scrollregion=(0, 0, width, height))

    def paint_native_symbol_card(self, side):
        tag = f"symbol-drawing:{side}"
        self.canvas.delete(tag)
        for symbol, slot in zip(self.symbol_duel.open_cards[side], self.symbol_slots[side]):
            x, y = self.symbol_tile_center(side, slot)
            _, palette, primitives = ICONS[symbol]
            scale = slot.size / 24
            a, b = scale * cos(radians(slot.angle)), scale * sin(radians(slot.angle))
            for kind, points, accent in primitives:
                ink, fill = accent or palette
                coords = tuple(
                    coordinate
                    for px, py in native_symbol_points(kind, points)
                    for coordinate in (x + a * (px-12) - b * (py-12), y + b * (px-12) + a * (py-12))
                )
                if kind == "line":
                    self.canvas.create_line(*coords, fill=ink, width=SYMBOL_STROKE*scale,
                                            capstyle="round", joinstyle="round", tags=tag)
                else:
                    self.canvas.create_polygon(*coords, fill=ink if kind == "dot" else fill,
                                               outline="" if kind == "dot" else ink, width=SYMBOL_STROKE*scale,
                                               joinstyle="round", tags=tag)
        self.paint_symbol_focus()

    def paint_symbol_card(self, side):
        card_index = self.symbol_duel.open_indices[side]
        label = f"Karte {card_index + 1}"
        self.canvas.itemconfigure(self.symbol_frames[side][-1], text=label)
        symbols = self.symbol_duel.open_cards[side]
        slots = self.symbol_slots[side] = symbol_placements(self.puzzle.seed, card_index, symbols)
        if self.symbol_faces_in_buttons:
            self.position_symbol_buttons(side)
            for button, symbol, slot in zip(self.symbol_buttons[side], symbols, slots):
                self.set_symbol_face(button, ICONS[symbol], label, slot.size / (2 * slot.radius), slot.angle)
        else:
            self.paint_native_symbol_card(side)

    def install_native_symbol_controls(self):
        self.symbol_focus = (0, 0)
        self.original_symbol_takefocus = self.canvas.cget("takefocus")
        self.canvas.configure(takefocus=True)
        self.canvas.bind("<Button-1>", self.click_symbol_duel)
        self.canvas.bind("<KeyPress>", self.key_symbol_duel)
        self.canvas.bind("<FocusIn>", self.paint_symbol_focus)
        self.canvas.bind("<FocusOut>", lambda event: self.canvas.delete("symbol-focus"))

    def clear_symbol_controls(self):
        if hasattr(self, "original_symbol_takefocus"):
            for sequence in ("<KeyPress>", "<FocusIn>", "<FocusOut>"):
                self.canvas.unbind(sequence)
            self.canvas.configure(takefocus=self.original_symbol_takefocus)
            del self.original_symbol_takefocus

    def paint_symbol_focus(self, event=None):
        self.canvas.delete("symbol-focus")
        if self.canvas.focus_get() == self.canvas and not self.symbol_duel.finished:
            side, index = self.symbol_focus
            slot = self.symbol_slots[side][index]
            x, y = self.symbol_tile_center(side, slot)
            r = slot.radius
            self.canvas.create_oval(x-r, y-r, x+r, y+r, outline="#2471a6", width=2, tags="symbol-focus")

    def key_symbol_duel(self, event):
        side, index = self.symbol_focus
        if event.keysym in ("Left", "Right"):
            step = -1 if event.keysym == "Left" else 1
            self.symbol_focus = side, (index + step) % SYMBOLS_PER_CARD
        elif event.keysym in ("Up", "Down"):
            self.symbol_focus = 1 - side, index
        elif event.keysym in ("Return", "space"):
            self.pick_symbol(side, index)
        else:
            return
        self.paint_symbol_focus()
        return "break"

    def click_symbol_duel(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        for side in range(2):
            for index, slot in enumerate(self.symbol_slots[side]):
                cx, cy = self.symbol_tile_center(side, slot)
                if (cx - x)**2 + (cy - y)**2 <= slot.radius**2:
                    self.symbol_focus = side, index
                    self.canvas.focus_set()
                    self.pick_symbol(side, index)
                    self.paint_symbol_focus()
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

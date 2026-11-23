"""Boards and solution replay for Mahjong and FreeCell."""
from .freecell import EMPTY, free_move, initial_state, ordered
from .mahjong import blockers, group, mahjong_move, open_tiles
from .playing_cards import SUIT_SIGNS, card_text, red

TABLETOP_MODES = ("mahjong", "freecell")
WIDTH = 440
INK, ACCENT, PAPER, MUTED = "#233a32", "#27644c", "#fffef9", "#63736a"
TABLE, LINE, RED = "#edf3ec", "#a8bbaf", "#a02d37"
WINDS = ("O", "S", "W", "N")
DRAGONS = ("R", "G", "W")


class TabletopUI:
    def initial_tabletop_state(self):
        view = self.puzzle.view
        if view["mode"] == "mahjong":
            return dict(board=(1 << len(view["tiles"])) - 1)
        return dict(board=initial_state(view["columns"]))

    def render_tabletop(self):
        self.tabletop_preview = ()
        self.tabletop_step = 0
        if self.puzzle.type_id == "mahjong":
            self.mahjong_geometry = blockers(self.puzzle.view["tiles"])
        labels = (("Anfang", 0), ("Zurück", -1), ("Weiter", 1), ("Ziel", 2))
        self.tabletop_navigation = [
            self.activity_button(label, lambda op=op: self.navigate_tabletop(op),
                                 62 + index * 105, 56, 94, height=42, tags=("tabletop-replay",))
            for index, (label, op) in enumerate(labels)
        ]
        self.canvas.bind("<Button-1>", self.click_tabletop)
        self.paint_activity()

    def tabletop_move(self, board, move):
        if self.puzzle.type_id == "mahjong":
            return mahjong_move(board, move, self.puzzle.view["faces"], self.mahjong_geometry)
        return free_move(board, move)

    def prepare_tabletop_replay(self):
        board = self.initial_tabletop_state()["board"]
        states = [board]
        for move in self.puzzle.solution.values():
            board = self.tabletop_move(board, move)
            states.append(board)
        self.tabletop_preview = tuple(states)
        self.tabletop_step = 0

    def navigate_tabletop(self, operation):
        if self.busy or not self.showing_solution:
            return
        last = len(self.tabletop_preview) - 1
        next_step = {0: 0, -1: self.tabletop_step - 1, 1: self.tabletop_step + 1, 2: last}[operation]
        self.tabletop_step = max(0, min(last, next_step))
        self.paint_activity()

    def paint_tabletop(self):
        if self.showing_solution:
            board = self.tabletop_preview[self.tabletop_step]
            index = self.tabletop_step
            total = len(self.tabletop_preview) - 1
            self.word_text(16, 12, f"Lösungsweg · {index} / {total}", size=13, bold=True)
            suggested = self.puzzle.solution.get(index)
            top = 89
        else:
            board = self.activity_state["board"]
            suggested = None
            top = 52
        if self.puzzle.type_id == "mahjong":
            self.paint_mahjong(board, top, suggested)
        else:
            self.paint_freecell(board, top, suggested)
        self.update_activity_solution_navigation(
            "tabletop-replay", self.tabletop_navigation, self.tabletop_step, len(self.tabletop_preview) - 1
        )

    def paint_mahjong(self, board, top, suggested):
        tiles, faces = self.puzzle.view["tiles"], self.puzzle.view["faces"]
        available = set(open_tiles(board, self.mahjong_geometry))
        self.tabletop_hits = []
        left = min(x for x, _, _ in tiles)
        columns = 1 + (max(x for x, _, _ in tiles) - left) / 2
        pitch = min(34, 416 / columns)
        origin = (WIDTH - columns * pitch) / 2
        width, height = pitch - 5, 33
        depth_x, depth_y = 4, 6
        self.word_text(16, top - 29 if not self.showing_solution else top,
                       f"{board.bit_count()} Steine · {len(available)} frei", size=12, bold=True)
        legend_y = top - 29 if not self.showing_solution else top
        self.canvas.create_rectangle(261, legend_y+3, 271, legend_y+13, fill="#fffdf4",
                                     outline="#246a54", width=2, tags=("activity-board",))
        self.word_text(277, legend_y, "Grüner Rand · frei", size=10, color=MUTED)
        if self.showing_solution:
            top += 30
        bottom = top + 27
        for index in sorted(range(len(tiles)), key=lambda i: (tiles[i][2], tiles[i][1], tiles[i][0])):
            if not board & (1 << index):
                continue
            x, y, layer = tiles[index]
            x = origin + (x - left) * pitch / 2 + layer * 5
            y = top + y * 20 - layer * 9
            hint = suggested and index in suggested
            selected = index == self.activity_selected
            open_face = index in available
            right, base = x + width, y + height
            body = ("activity-board", f"mahjong-body:{index}")
            if layer:
                self.canvas.create_rectangle(x+2, y+2, right+depth_x+2, base+depth_y+2,
                                             fill="#75887b", outline="", tags=body)
            side, front = ("#477562", "#80a28c") if open_face else ("#7b8f81", "#a3b1a2")
            self.canvas.create_polygon(right, y, right+depth_x, y+depth_y, right+depth_x, base+depth_y,
                                       right, base, fill=side, outline=side, tags=body)
            self.canvas.create_polygon(x, base, right, base, right+depth_x, base+depth_y,
                                       x+depth_x, base+depth_y, fill=front, outline=side, tags=body)
            fill = "#deeffa" if hint else "#f8e4b6" if selected else "#fffdf4" if open_face else "#e1e6df"
            edge = "#225a92" if hint else "#9a6419" if selected else "#246a54" if open_face else "#a2ada2"
            self.canvas.create_rectangle(x, y, right, base, fill=fill, outline=edge,
                                         width=2 if open_face else 1,
                                         tags=("activity-board", f"mahjong-tile:{index}"))
            self.draw_mahjong_face(x + width / 2, y, faces[index], open_face)
            self.tabletop_hits.append((x, y, right+depth_x, base+depth_y, index))
            bottom = max(bottom, base + depth_y)
        self.canvas.configure(scrollregion=(0, 0, WIDTH, max(bottom + 22, top + 405)))

    def draw_mahjong_face(self, center, y, face, available):
        dimmed = "#68716c"
        if face < 27:
            family, value = divmod(face, 9)
            label, color = (("●", "#8d3b42"), ("║", "#2b6a4e"), ("◇", "#364d78"))[family]
            symbol, size = label, 11
            self.canvas.create_text(center, y + 10, text=str(value + 1), fill=color if available else dimmed,
                                    font=("Helvetica", 12, "bold"), tags=("activity-board",))
        else:
            if face < 31:
                symbol, color = WINDS[face - 27], "#364d78"
            elif face < 34:
                symbol, color = DRAGONS[face - 31], ("#a02d37", "#2b6a4e", "#526b70")[face - 31]
            elif face < 38:
                symbol, color = str(face - 33), "#6e3c77"
            else:
                symbol, color = str(face - 37), "#72551d"
            size = 11
            emblem = "◈" if face >= 38 else "✿" if face >= 34 else "◆"
            self.canvas.create_text(center, y + 9, text=emblem, fill=color if available else dimmed,
                                    font=("Helvetica", 8, "bold"), tags=("activity-board",))
        self.canvas.create_text(center, y + 23, text=symbol, fill=color if available else dimmed,
                                font=("Helvetica", size, "bold"), tags=("activity-board",))

    def draw_playing_card(self, x, y, width, height, card, *, label="", active=False, marked=False,
                          tags=(), text_tags=(), font_size=13):
        border = "#27644c" if active else "#a76d19" if marked else LINE
        fill = "#dceee0" if active else "#fff0ce" if marked else PAPER if card is not None else TABLE
        self.canvas.create_rectangle(x, y, x + width, y + height, fill=fill, outline=border,
                                     width=2 if active or marked else 1, tags=("activity-board", *tags))
        if card is None:
            if label:
                self.canvas.create_text(x + width / 2, y + height / 2, text=label, fill=MUTED,
                                        font=("Helvetica", 14, "bold"), tags=("activity-board",))
        else:
            ink = RED if red(card) else "#203c40"
            self.canvas.create_text(x + 5, y + 4, text=card_text(card), fill=ink, anchor="nw",
                                    font=("Helvetica", font_size, "bold"), tags=("activity-board", *text_tags))

    def paint_freecell(self, board, top, suggested):
        self.tabletop_hits = []
        self.word_text(16, top - 31 if not self.showing_solution else top,
                       f"Zielstapel · {sum(board.foundations)} / 52 Karten", size=12, bold=True)
        if self.showing_solution:
            top += 29
        origin, step, w, h = 15, 52, 45, 64
        self.word_text(origin, top, "Freie Zellen", size=11, bold=True)
        self.word_text(origin + step * 4, top, "Zielstapel", size=11, bold=True)
        for index in range(8):
            location = 8 + index
            x, y = origin + index * step, top + 24
            value = board.cells[index] if index < 4 else (
                13 * (index - 4) + board.foundations[index - 4] - 1 if board.foundations[index - 4] else EMPTY)
            self.draw_playing_card(x, y, w, h, value if value != EMPTY else None,
                                   label=SUIT_SIGNS[index - 4] if index >= 4 else "",
                                   active=self.activity_selected == (location, 1),
                                   marked=suggested and location in suggested[:2], tags=(f"freecell-slot:{location}",))
            self.tabletop_hits.append((x, y, x + w, y + h, (location, 1)))
        bottom = top + 130
        row_top = top + 108
        for index, column in enumerate(board.columns):
            x = origin + index * step
            if not column:
                self.draw_playing_card(x, row_top, w, h, None,
                                       marked=suggested and suggested[1] == index, tags=(f"freecell-slot:{index}",))
                self.tabletop_hits.append((x, row_top, x + w, row_top + h, (index, 0)))
            for offset, card in enumerate(column):
                y = row_top + offset * 24
                length = len(column) - offset
                selected = self.activity_selected
                active = selected and selected[0] == index and length <= selected[1]
                marked = suggested and (index == suggested[0] and length <= suggested[2]
                                        or index == suggested[1] and length == 1)
                self.draw_playing_card(x, y, w, h, card, active=active, marked=marked,
                                       tags=(f"freecell-card:{index}:{card}",))
                self.tabletop_hits.append((x, y, x + w, y + h, (index, length)))
                bottom = max(bottom, y + h)
        self.canvas.configure(scrollregion=(0, 0, WIDTH, max(470, bottom + 25)))

    def click_tabletop(self, event):
        if self.busy or self.showing_solution:
            return
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        hit = next((value for a, b, c, d, value in reversed(self.tabletop_hits)
                    if a <= x <= c and b <= y <= d), None)
        if hit is None:
            self.activity_selected = None
            self.paint_activity()
            return
        board = self.activity_state["board"]
        old = self.activity_selected
        if self.puzzle.type_id == "mahjong":
            if hit not in open_tiles(board, self.mahjong_geometry):
                self.status.configure(text="Dieser Stein ist blockiert.", foreground=MUTED)
                return
            if old is not None and old != hit and self.apply_tabletop_move((old, hit)):
                return
            self.activity_selected = hit if old != hit else None
            message = "Wähle einen freien Stein aus derselben Gruppe." if self.activity_selected is not None else ""
        else:
            location, count = hit
            moving = old is not None and old[0] != location
            if moving and self.apply_tabletop_move((old[0], location, old[1])):
                return
            valid = ((location < 8 and count > 0 and ordered(board.columns[location][-count:]))
                     or (8 <= location < 12 and board.cells[location - 8] != EMPTY))
            if moving and not valid:
                self.status.configure(text="Der Zug passt hier nicht. Die gewählte Karte oder Folge bleibt markiert.", foreground=MUTED)
                return
            self.activity_selected = hit if old != hit and valid else None
            message = "Wähle einen Zielplatz." if self.activity_selected else "Wähle eine freie Karte oder eine geordnete Folge."
        self.paint_activity()
        if message:
            self.status.configure(text=message, foreground=INK)

    def apply_tabletop_move(self, move):
        state = self.activity_state
        following = self.tabletop_move(state["board"], move)
        if following is None:
            return False
        state["board"] = following
        self.activity_selected = None
        self.on_change()
        return True

    def on_tabletop_change(self):
        self.paint_activity()
        board = self.activity_state["board"]
        if self.puzzle.type_id == "mahjong":
            finished = board == 0
            available = open_tiles(board, self.mahjong_geometry)
            groups = {group(self.puzzle.view["faces"][tile]) for tile in available}
            status = (f"{board.bit_count()} Steine verbleiben." if len(groups) != len(available)
                      else "Kein freies Paar. Du kannst einen Zug zurücknehmen.")
        else:
            finished = sum(board.foundations) == 52
            status = f"{sum(board.foundations)} von 52 Karten auf den Zielstapeln."
        if finished:
            self.show_success()
        else:
            self.hide_success(reset=True)
            self.status.configure(text=status, foreground=INK)

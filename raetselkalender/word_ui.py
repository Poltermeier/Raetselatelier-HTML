"""Interactive panels for the German word puzzles."""
import math
import tkinter as tk

from .board_canvas import BoardEntry
from .word_games import ALPHABET, display_word, normalize_word, word_feedback

INK, ACCENT, PAPER = "#233a32", "#27644c", "#fffef9"
MUTED, LINE = "#63736a", "#c5d0c7"
WORD_WIDTH = 460
MARKS = {
    "exact": ("✓", "#d9eee0", "#27644c"),
    "present": ("↔", "#f6e8c7", "#694900"),
    "absent": ("–", "#eef0eb", "#536159"),
}


class WordGamesUI:
    def render_word_game(self):
        ring = self.puzzle.view["mode"] == "wortring"
        y = 334 if ring else 134
        self.word_variable = tk.StringVar()
        self.word_entry = BoardEntry(self.canvas, textvariable=self.word_variable, font=("Helvetica", 17),
                                     bg=PAPER, fg=INK, justify="left", highlightthickness=1,
                                     highlightbackground=LINE)
        validator = self.root.register(lambda value: len(value) <= 24 and
                                       all(letter in ALPHABET for letter in normalize_word(value)))
        self.word_entry.configure(validate="key", validatecommand=(validator, "%P"))
        self.word_variable.trace_add("write", self.edit_word_draft)
        self.word_entry.bind("<Return>", self.submit_word)
        self.extra_widgets.append(self.word_entry)
        self.activity_controls.append(self.word_entry)
        self.canvas.create_window(138, y, window=self.word_entry, width=222, height=42,
                                  tags=("word-game-controls",))
        self.activity_button("Wort prüfen", self.submit_word, 348, y, 150, tags=("word-game-controls",))
        if ring:
            self.activity_button("Auswahl leeren", self.clear_word_draft, 230, 383, 164, tags=("word-game-controls",))
            self.canvas.bind("<Button-1>", self.click_word_ring)
        self.paint_activity()

    def word_game_finished(self):
        words = self.activity_state["words"]
        return self.puzzle.is_solved(words) or len(words) >= self.puzzle.view.get("attempts", math.inf)

    def edit_word_draft(self, *_):
        if self.updating or self.busy or self.showing_solution:
            return
        self.activity_state["draft"] = self.word_variable.get()
        if self.activity_state["path"]:
            self.activity_state["path"] = []
            self.paint_activity()

    def clear_word_draft(self):
        if self.busy or self.showing_solution or self.word_game_finished():
            return
        self.activity_state.update(draft="", path=[])
        self.paint_activity()

    def submit_word(self, event=None):
        if self.busy or self.showing_solution or self.word_game_finished():
            return "break"
        word = normalize_word(self.word_variable.get())
        state = self.activity_state
        message = self.puzzle.word_error(word)
        if word in state["words"]:
            message = "Dieses Wort hast du schon eingetragen."
        if message:
            self.status.configure(text=message, foreground="#94412d")
        else:
            state["words"].append(word)
            state.update(draft="", path=[])
            self.on_change()
        return "break"

    def on_word_game_change(self):
        self.paint_activity()
        puzzle = self.puzzle
        words = self.activity_state["words"]
        if puzzle.is_solved(words):
            self.show_success()
            return
        self.hide_success(reset=True)
        self.dismiss_error(reset=True)
        if self.word_game_finished():
            text = "Die Versuche sind aufgebraucht. Du kannst die Lösung ansehen oder einen Versuch zurücknehmen."
        elif puzzle.view["mode"] == "wortspur" and words:
            marks = word_feedback(words[-1], puzzle.answer_words[0])
            text = f"Letzter Versuch: {marks.count('exact')} richtig platziert, {marks.count('present')} an anderer Stelle."
        elif puzzle.view["mode"] == "buchstabenwerkstatt":
            text = f'{len(words)} von {puzzle.view["goal"]} Wörtern gefunden.'
        else:
            text = "Wort eingeben und prüfen."
        self.status.configure(text=text, foreground=INK)

    def paint_word_game(self):
        state = self.activity_state
        if self.word_variable.get() != state["draft"]:
            previous = self.updating
            self.updating = True
            try:
                self.word_variable.set(state["draft"])
            finally:
                self.updating = previous
        self.canvas.itemconfigure("word-game-controls", state="hidden" if self.showing_solution else "normal")
        mode = self.puzzle.view["mode"]
        if mode == "wortspur":
            height = self.paint_word_trail()
        elif mode == "buchstabenwerkstatt":
            height = self.paint_letter_workshop()
        else:
            height = self.paint_word_ring()
        self.canvas.configure(scrollregion=(0, 0, WORD_WIDTH, height),
                              cursor="hand2" if mode == "wortring" and not self.showing_solution else "")

    def word_text(self, x, y, text, *, size=12, color=INK, bold=False, width=0):
        font = ("Helvetica", size, "bold") if bold else ("Helvetica", size)
        self.canvas.create_text(x, y, text=text, fill=color, font=font, width=width,
                                anchor="nw", justify="left", tags=("activity-board",))

    def paint_word_trail(self):
        view = self.puzzle.view
        words = self.activity_state["words"]
        target = self.puzzle.answer_words[0]
        if self.showing_solution:
            self.word_text(26, 25, "Lösung", size=13, bold=True)
            self.word_text(26, 58, display_word(target), size=24, color=ACCENT, bold=True)
            return 130
        self.word_text(26, 24, f'{view["length"]} Buchstaben · {len(words)} von {view["attempts"]} Versuchen', size=14, bold=True)
        if view["theme"]:
            self.word_text(26, 54, f'Thema: {view["theme"]}')
        self.word_text(26, 171, "✓ Richtig     ↔ Andere Position     – Fehlt", size=11, color=MUTED)
        for row, word in enumerate(reversed(words)):
            y = 206 + row * 44
            self.word_text(26, y + 6, f"{len(words) - row}.", size=11, color=MUTED)
            self.word_text(57, y + 3, display_word(word), size=14, bold=True)
            for i, rating in enumerate(word_feedback(word, target)):
                symbol, background, color = MARKS[rating]
                x = 199 + i * 36
                self.canvas.create_oval(x, y, x + 29, y + 29, fill=background, outline="",
                                        tags=("activity-board", f"word-feedback:{rating}"))
                self.canvas.create_text(x + 14.5, y + 14.5, text=symbol, fill=color,
                                        font=("Helvetica", 12, "bold"), tags=("activity-board",))
        return max(250, 220 + len(words) * 44)

    def paint_letter_workshop(self):
        view = self.puzzle.view
        found = self.activity_state["words"]
        self.word_text(26, 24, f'Pflichtbuchstabe: {display_word(view["required"])}', size=14, bold=True)
        for i, letter in enumerate(view["letters"]):
            x = 26 + i * 50
            required = letter == view["required"]
            self.canvas.create_rectangle(x, 61, x + 43, 104, fill="#d9eee0" if required else PAPER,
                                          outline=ACCENT if required else LINE, width=2 if required else 1,
                                          tags=("activity-board", "workshop-letter"))
            self.canvas.create_text(x + 21.5, 82.5, text=display_word(letter), fill=ACCENT if required else INK,
                                    font=("Helvetica", 17, "bold"), tags=("activity-board",))
        words = self.puzzle.answer_words if self.showing_solution else reversed(found)
        heading = "Mögliche Wörter" if self.showing_solution else f'{len(found)} von {view["goal"]} Wörtern gefunden'
        self.word_text(26, 121 if self.showing_solution else 177, heading, size=13, bold=True)
        start = 158 if self.showing_solution else 216
        words = tuple(words)
        for i, word in enumerate(words):
            self.word_text(26 + (i % 2) * 210, start + (i // 2) * 27, display_word(word))
        return max(250, start + ((len(words) + 1) // 2) * 27 + 20)

    def paint_word_ring(self):
        puzzle = self.puzzle
        view = puzzle.view
        letters = view["letters"]
        count = len(letters)
        center_x, center_y, radius = 230, 181, 103
        state = self.activity_state
        self.word_text(26, 20, f'Thema: {view["theme"]}', size=14, bold=True, width=410)
        self.canvas.create_oval(center_x - radius, center_y - radius, center_x + radius, center_y + radius,
                                outline=LINE, width=2, tags=("activity-board",))
        direction = puzzle.ring_direction
        path = [(puzzle.ring_start + direction*i) % count for i in range(count)] if self.showing_solution else state["path"]
        self.ring_centers = []
        for i, letter in enumerate(letters):
            angle = 2 * math.pi * i / count - math.pi / 2
            x, y = center_x + radius * math.cos(angle), center_y + radius * math.sin(angle)
            picked = i in path
            self.ring_centers.append((x, y))
            self.canvas.create_oval(x - 23, y - 23, x + 23, y + 23, fill="#d9eee0" if picked else PAPER,
                                   outline=ACCENT if picked else LINE, width=2, tags=("activity-board", f"ring-letter:{i}"))
            self.canvas.create_text(x, y, text=display_word(letter), fill=INK,
                                    font=("Helvetica", 17, "bold"), tags=("activity-board",))
            if picked:
                badge_x = center_x + (radius - 34) * math.cos(angle)
                badge_y = center_y + (radius - 34) * math.sin(angle)
                self.canvas.create_text(badge_x, badge_y, text=str(path.index(i) + 1), fill=ACCENT,
                                        font=("Helvetica", 9, "bold"), tags=("activity-board",))
        if self.showing_solution:
            word = display_word(puzzle.answer_words[0])
            sense = "im Uhrzeigersinn" if direction == 1 else "gegen den Uhrzeigersinn"
            self.word_text(26, 324, word, size=21, color=ACCENT, bold=True)
            self.word_text(26, 363, f'Bei Feld 1 beginnen und {sense} lesen.', width=408)
        return 425

    def click_word_ring(self, event):
        if self.busy or self.showing_solution or self.word_game_finished():
            return
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        index = next((i for i, (a, b) in enumerate(self.ring_centers) if math.hypot(x-a, y-b) <= 23), None)
        if index is None:
            return
        state = self.activity_state
        letters = self.puzzle.view["letters"]
        count = len(letters)
        path = state["path"]
        if path and index == path[-1]:
            path.pop()
        elif index in path:
            return
        else:
            if path:
                step = (index - path[-1]) % count
                allowed = (1, count - 1) if len(path) == 1 else ((path[1] - path[0]) % count,)
                if step not in allowed:
                    self.status.configure(text="Wähle das nächste Feld in derselben Leserichtung.", foreground="#94412d")
                    return
            path.append(index)
        state["draft"] = display_word("".join(letters[i] for i in path))
        self.status.configure(text="Wort prüfen oder den Ring weiterlesen.", foreground=INK)
        self.paint_activity()

"""Run the original atelier UI and generators in a browser worker."""
import asyncio
from concurrent.futures import Future
import json
import random
import secrets

from js import atelierSound, atelierSave, atelierPreferences
import tkinter as tk

from raetselkalender import catalog, gui, settings_ui
from raetselkalender.preferences import normalize_preferences

# The browser has a bundled UCI engine accessed by the chess adapter.
catalog.stockfish_path = lambda: "browser-stockfish"
gui.load_preferences = lambda path=None: normalize_preferences(json.loads(atelierPreferences()))
settings_ui.save_preferences = lambda values, path=None: atelierSave(json.dumps(normalize_preferences(values)))


class BrowserVictorySound:
    def play(self, volume):
        if volume:
            atelierSound(volume)


gui.VictorySound = BrowserVictorySound


async def generate_in_browser(type_id, seed, difficulty, **options):
    if seed is None:
        seed = secrets.randbits(48)
    if type_id == "random":
        type_id = random.Random(seed).choice([p.id for p in catalog.CATALOG if p.available])
    if type_id != "schachraetsel":
        return catalog.generate(type_id, seed, difficulty, **options)
    from chess_adapter import browser_chess_puzzle
    puzzle = await browser_chess_puzzle(seed, difficulty)
    puzzle.analysis.update(generation_attempts=1, generation_seed=seed)
    return puzzle


class BrowserExecutor:
    def submit(self, function, *args, **options):
        future = Future()

        async def run():
            try:
                future.set_result(await generate_in_browser(*args, **options))
            except Exception as error:
                future.set_exception(error)
        # Give the browser the disabled controls and progress state before generation.
        tk._root.after(16, lambda: asyncio.ensure_future(run()))
        return future

    def shutdown(self, **options):
        pass


gui.ThreadPoolExecutor = lambda **options: BrowserExecutor()


class BrowserApp(gui.App):
    sudoku_diagonal_color = "#367db859"  # 35% opacity.

    def reset(self):
        if self.puzzle is None or self.busy or self.showing_solution:
            return
        puzzle = self.puzzle
        original_reset = super().reset

        def reset_current():
            if self.puzzle is puzzle:
                original_reset()

        tk.confirm(self.root, "Eingaben zurücksetzen",
                   "Alle eigenen Eingaben und Notizen dieses Rätsels leeren?", reset_current)

    def export(self):
        if self.puzzle is None:
            return
        tk.send("download", f"{self.puzzle.type_id}-{self.puzzle.seed}.json",
                json.dumps(self.puzzle.export(), ensure_ascii=False, indent=2))

    def add_entry(self, key, *args, **options):
        super().add_entry(key, *args, **options)
        coordinates = key.split(",")
        label = (f"Zeile {int(coordinates[0]) + 1}, Spalte {int(coordinates[1]) + 1}"
                 if len(coordinates) == 2 and all(part.isdecimal() for part in coordinates) else f"Rätselfeld {key}")
        tk.send("label", self.entries[key].id, label)

    def render_word_game(self):
        super().render_word_game()
        tk.send("label", self.word_entry.id, "Wort eingeben")

    def register_diagonal_entry(self, key):
        # Transparent inputs keep the board's diagonal visible through the cell.
        tk.send("role", self.entries[key].id, "diagonal-entry")

    def fit_board(self):
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        if self.puzzle is None or self.fixed_board_scale is not None or min(width, height) < 100:
            super().fit_board()
            return
        self.fit_job = None
        x1, y1, x2, y2 = self.canvas.logical_region
        zoom = max(.65, min(1.7, (width - 8) / max(1, x2 - x1), (height - 8) / max(1, y2 - y1)))
        if self.canvas.set_zoom(int(zoom * 100) / 100) and not self.is_click_board():
            self.refresh_note_previews()

    def poll_generation(self):
        previous = self.puzzle
        super().poll_generation()
        if self.puzzle is not previous:
            tk.send("reveal", self.main.id)

    def open_settings(self):
        super().open_settings()
        # Persist on close, including Escape, as in the desktop dialog.
        if self.settings_window:
            tk.send("role", self.settings_window.id, "settings")


def start():
    root = tk.Tk()
    app = BrowserApp(root)
    sidebar = app.choice.master
    roles = {
        root: "app", sidebar.master.master: "shell", app.settings_button.master: "header",
        sidebar.master: "body", sidebar: "sidebar", app.main: "main",
        app.title: "title", app.meta: "metadata", app.rules: "rules",
        app.board_holder: "board-holder", app.canvas: "board", app.status: "status",
        app.progress: "progress", app.success_panel: "success",
        app.error_panel: "error", app.confetti_canvas: "confetti",
    }
    for widget, role in roles.items():
        tk.send("role", widget.id, role)
    for widget, label in ((app.choice, "Rätseltyp"), (app.seed, "Seed (optional)"),
                          (app.cat_size_choice, "Feldgröße Katzensuche"),
                          (app.pipe_size_choice, "Feldgröße Pipes")):
        tk.send("label", widget.id, label)
    tk.flush()
    return app

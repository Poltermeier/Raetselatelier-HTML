"""Local Tk interface. Worker threads never access Tk widgets."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import unicodedata
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .catalog import BY_ID, CATALOG, generate
from .rectangle_ui import RectangleUI
from .diagram_geometry import circle_link
from .lock_ui import LockUI
from .notes_ui import NotesUI
from .nonogram_ui import NonogramUI
from .arithmetic_ui import ArithmeticUI
from .hashi_ui import HashiUI
from .click_boards import ClickBoardUI
from .history_ui import HistoryUI
from .hearts import HEARTS_LEVELS
from .chess_game_ui import ChessGameUI, CHESS_ELOS
from .popout import LEVELS as POPOUT_LEVELS
from .popout_ui import FOUR_TITLES, PopOutUI
from .paired_maze import MAZE_FORMS, MAZE_TITLES, RANDOM_FORM, generate_maze
from .paired_maze_ui import PairedMazeUI
from .sequence_ui import SEQUENCE_TITLES, SequenceUI
from .symbol_duel import CARD_COUNT, SYMBOLS_PER_CARD
from .symbol_duel_ui import SymbolDuelUI
from .camping_ui import CampingUI
from .board_canvas import BoardCanvas, BoardEntry
from .feedback_ui import FeedbackUI
from .calendar_ui import CalendarUI
from .pouring_ui import PouringUI
from .matrix_ui import MatrixUI
from .route_ui import RouteUI
from .strategy_ui import StrategyUI
from .spring_ui import SpringUI
from .activity_ui import ActivityUI
from .assistance_ui import AssistanceUI
from .diagonal_ui import DiagonalUI,DIAGONAL_COLOR,WINDOW_COLOR
from .preferences import load_preferences,VictorySound,save_preferences
from .settings_ui import SettingsUI
from .workshop_ui import WorkshopUI
from .pipes import PIPE_SIZES

BG = "#f6f3eb"
PAPER = "#fffef9"
INK = "#233a32"
ACCENT = "#27644c"
MUTED = "#63736a"
LINE = "#d1d8cf"


class App(RectangleUI, LockUI, NotesUI, NonogramUI, ArithmeticUI, HashiUI, ClickBoardUI, HistoryUI, CampingUI, FeedbackUI, CalendarUI, PouringUI, MatrixUI, RouteUI, StrategyUI, ChessGameUI, PopOutUI, PairedMazeUI, SequenceUI, SymbolDuelUI, SpringUI, ActivityUI, AssistanceUI, DiagonalUI, SettingsUI, WorkshopUI):
    sudoku_diagonal_color = DIAGONAL_COLOR

    def __init__(self, root, type_id="random", seed=None, difficulty="schwer", *, board_scale=None, cat_size=6, pipe_size=5, settings_path=None):
        if type_id in BY_ID:
            type_id = BY_ID[type_id].id
        self.root = root
        self.preferences_file=settings_path
        self.preferences=load_preferences(settings_path)
        self.victory_sound=VictorySound()
        self.settings_window=None
        self.fixed_board_scale = board_scale
        self.fit_job = None
        self.last_canvas_size = None
        self.idle_diagnostics = None
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.future = None
        self.puzzle = None
        self.nonogram_lives = None
        self.vars = {}
        self.entries = {}
        self.diagonal_overlays={}
        self.diagonal_segments=[]
        self.pour_widgets = []
        self.pour_rows = []
        self.showing_solution = False
        self.updating = False
        self.busy = False
        self.init_notes()
        self.init_history()
        self.root.bind("<Control-z>", self.undo_last)
        self.root.bind("<Escape>", self.escape)
        self.root.bind('<KeyPress-n>',self.notes_hotkey,add='+')
        self.root.bind('<KeyPress-N>',self.notes_hotkey,add='+')
        self.root.title("Simon's Rätselatelier")
        self.root.geometry("1140x880")
        self.root.minsize(860, 640)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=INK, font=("Helvetica", 10))
        style.configure("TButton", font=("Helvetica", 10), padding=(12, 8))
        style.configure("MazeDirection.TButton", background="#28584c", foreground="#fff9ea",
                        padding=(4, 4), font=("Helvetica", 16, "bold"))
        style.map("MazeDirection.TButton", background=[("active", "#377462"), ("disabled", "#cbd8ce")],
                  foreground=[("disabled", "#5b7369")])
        self.configure_sequence_styles(style)
        for name, background, foreground in (
            ("Deduction", "#f7f6ee", INK),
            ("DeductionSelected", ACCENT, "white"),
            ("DeductionLinked", "#fbebc9", INK),
            ("DeductionResolved", "#e4eee4", INK),
        ):
            style.configure(f"{name}.TButton", font=("Helvetica", 9, "bold"), padding=(3, 2),
                            background=background, foreground=foreground, justify="center")
        style.configure("Accent.TButton", background=ACCENT, foreground="white")
        style.map("Accent.TButton", background=[("active", "#34775d")])
        style.configure("NotesOn.TButton", background=ACCENT, foreground="white")
        style.map("NotesOn.TButton", background=[("disabled", "#d1d8cf"), ("active", "#34775d")],
                  foreground=[("disabled", MUTED), ("active", "white")])
        style.configure("DifficultyOn.TButton",background=ACCENT,foreground="white")
        style.map("DifficultyOn.TButton",background=[("disabled","#d1d8cf"),("active","#34775d")],
                  foreground=[("disabled",MUTED),("active","white")])
        style.configure("TCombobox", padding=5)
        for name, color, background in (
            ("Card", INK, PAPER), ("CardRed", "#a02d37", PAPER), ("CardSelected", "#ffffff", ACCENT)
        ):
            style.configure(f"{name}.TButton", font=("Helvetica", 10, "bold"), padding=(3, 4),
                            anchor="nw", foreground=color, background=background)

        shell = ttk.Frame(root, padding=16)
        shell.pack(fill="both", expand=True)
        header=ttk.Frame(shell);header.pack(fill='x')
        ttk.Label(header, text="Simon's Rätselatelier", foreground=ACCENT,
                  font=("Helvetica", 11, "bold")).pack(side='left')
        self.settings_icon=tk.PhotoImage(master=root,width=19,height=19)
        for y,handle in ((4,5),(9,13),(14,8)):
            self.settings_icon.put(ACCENT,to=(1,y,18,y+1))
            self.settings_icon.put(ACCENT,to=(handle-2,y-2,handle+3,y+3))
            self.settings_icon.put(BG,to=(handle-1,y-1,handle+2,y+2))
        self.settings_button=ttk.Button(header,text='Einstellungen',image=self.settings_icon,compound='left',command=self.open_settings,padding=(8,2))
        self.settings_button.pack(side='right')
        body = ttk.Frame(shell)
        body.pack(fill="both", expand=True, pady=(8,0))
        sidebar = ttk.Frame(body, width=230)
        sidebar.pack(side="left", fill="y", padx=(0, 18))
        sidebar.pack_propagate(False)
        ttk.Label(sidebar, text="DEIN NÄCHSTES RÄTSEL", font=("Helvetica", 10, "bold")).pack(anchor="w")
        ordered_types = sorted((p for p in CATALOG if p.id != "hearts"),key=lambda p:"".join(c for c in unicodedata.normalize("NFKD",p.title.casefold()) if not unicodedata.combining(c)))
        self.labels = ["Zufälliger Rätseltyp"] + [p.title + (" · "+p.availability_label if not p.available else "") for p in ordered_types]
        self.type_ids = ["random"] + [p.id for p in ordered_types]
        self.choice = ttk.Combobox(sidebar, values=self.labels, state="readonly", width=24)
        self.choice.current(self.type_ids.index("random" if type_id == "hearts" else type_id))
        self.choice.pack(fill="x", pady=(10, 14))
        self.choice.bind("<<ComboboxSelected>>", self.selection_changed)
        ttk.Label(sidebar, text="Längere Denkspiele").pack(anchor="w")
        games = {None: "Spiel auswählen", "hearts": "Hearts", "schach": "Schach", **FOUR_TITLES,
                 "symbol-duel": "Symbolduell", **SEQUENCE_TITLES, **MAZE_TITLES}
        self.long_ids = tuple(games)
        self.long_choice = ttk.Combobox(sidebar, values=tuple(games.values()), state="readonly")
        self.long_choice.current(1 if type_id == "hearts" else 0)
        self.long_choice.pack(fill="x", pady=(5,12))
        self.long_choice.bind("<<ComboboxSelected>>", self.selection_changed)
        self.level_label = ttk.Label(sidebar, text="Schwierigkeitsgrad")
        self.level_label.pack(anchor="w")
        self.level = tk.StringVar(value=difficulty if difficulty in ("mittel", "schwer") else "schwer")
        self.level_frame = ttk.Frame(sidebar)
        self.level_frame.pack(fill="x",pady=(5,12))
        self.level_buttons = {}
        for value in ("mittel","schwer"):
            button = ttk.Button(self.level_frame,text=value.capitalize(),command=lambda v=value:self.level.set(v))
            button.pack(side="left",fill="x",expand=True,padx=(0,4) if value=="mittel" else (4,0))
            self.level_buttons[value] = button
        self.level.trace_add("write",lambda *args:self.refresh_difficulty_buttons())
        self.refresh_difficulty_buttons()
        hearts_default = difficulty.capitalize() if type_id == "hearts" and difficulty in HEARTS_LEVELS else "Mittel"
        self.hearts_level = tk.StringVar(value=hearts_default)
        self.hearts_level_choice = ttk.Combobox(sidebar, textvariable=self.hearts_level,
            values=[value.capitalize() for value in HEARTS_LEVELS], state="readonly")
        self.popout_level = tk.StringVar(value="Mittel")
        self.popout_level_choice = ttk.Combobox(sidebar, textvariable=self.popout_level,
            values=[value.capitalize() for value in POPOUT_LEVELS], state="readonly")
        self.chess_settings = ttk.Frame(sidebar)
        ttk.Label(self.chess_settings, text="Stockfish-Elo").pack(anchor="w")
        self.chess_elo = tk.StringVar(value="1500")
        self.chess_elo_choice = ttk.Combobox(self.chess_settings, textvariable=self.chess_elo, values=CHESS_ELOS, state="readonly")
        self.chess_elo_choice.pack(fill="x", pady=(4,9))
        ttk.Label(self.chess_settings, text="Deine Farbe").pack(anchor="w")
        self.chess_color = tk.StringVar(value="Weiß")
        self.chess_color_choice = ttk.Combobox(self.chess_settings, textvariable=self.chess_color, values=("Weiß", "Schwarz"), state="readonly")
        self.chess_color_choice.pack(fill="x", pady=(4,0))
        self.cat_size=tk.IntVar(value=cat_size)
        self.cat_size_frame=ttk.Frame(sidebar)
        ttk.Label(self.cat_size_frame,text='Feldgröße Katzensuche').pack(anchor='w')
        self.cat_size_choice=ttk.Combobox(self.cat_size_frame,textvariable=self.cat_size,
            values=list(range(4,11)),state='readonly',width=8)
        self.cat_size_choice.pack(fill='x',pady=(4,0))
        self.pipe_size=tk.IntVar(value=pipe_size)
        self.pipe_size_frame=ttk.Frame(sidebar)
        ttk.Label(self.pipe_size_frame,text='Feldgröße Pipes').pack(anchor='w')
        self.pipe_size_choice=ttk.Combobox(self.pipe_size_frame,textvariable=self.pipe_size,values=PIPE_SIZES,state='readonly',width=8)
        self.pipe_size_choice.pack(fill='x',pady=(4,0))
        self.maze_form = tk.StringVar(value=RANDOM_FORM)
        self.maze_form_frame = ttk.Frame(sidebar)
        ttk.Label(self.maze_form_frame, text="Bauform").pack(anchor="w")
        self.maze_form_choice = ttk.Combobox(self.maze_form_frame, textvariable=self.maze_form,
                                            values=(RANDOM_FORM, *MAZE_FORMS), state="readonly")
        self.maze_form_choice.pack(fill="x", pady=(4, 0))
        self.seed_label=ttk.Label(sidebar, text="Seed (optional)")
        self.seed_label.pack(anchor="w")
        self.seed = ttk.Entry(sidebar)
        if seed is not None:
            self.seed.insert(0, str(seed))
        self.seed.pack(fill="x", pady=(5, 12))
        self.new_button = ttk.Button(sidebar, text="Neues Rätsel", style="Accent.TButton", command=self.new_puzzle)
        self.new_button.pack(fill="x")
        self.random_button = ttk.Button(sidebar, text="Zufällig überraschen", command=self.random_puzzle)
        self.random_button.pack(fill="x", pady=(8, 12))
        self.note = ttk.Label(sidebar, text="", wraplength=235, foreground=MUTED)
        ttk.Separator(sidebar).pack(fill="x", pady=8)
        self.notes_button = ttk.Button(sidebar, text="Notizen (N)", command=self.toggle_notes, state="disabled")
        self.notes_button.pack(fill="x", pady=(8, 0))
        self.undo_button = ttk.Button(sidebar, text="Letzten Schritt zurücknehmen", command=self.undo_last, state="disabled")
        self.undo_button.pack(fill="x", pady=(8, 0))
        self.solution_button = ttk.Button(sidebar, text="Lösung ansehen", command=self.toggle_solution, state="disabled")
        self.solution_button.pack(fill="x", pady=(10, 8))
        self.reset_button = ttk.Button(sidebar, text="Eingaben zurücksetzen", command=self.reset, state="disabled")
        self.reset_button.pack(fill="x", pady=(0, 8))
        self.export_button = ttk.Button(sidebar, text="Rätsel als JSON speichern", command=self.export, state="disabled")
        self.export_button.pack(fill="x")
        self.main = ttk.Frame(body)
        self.main.pack(side="left", fill="both", expand=True)
        self.title = ttk.Label(self.main, text="Simon's Rätselatelier", font=("Times", 23))
        self.title.pack(anchor="w")
        self.meta = ttk.Label(self.main, text="Wähle einen Rätseltyp oder lass dich überraschen.", foreground=MUTED)
        self.meta.pack(anchor="w", pady=(4, 8))
        self.rules = ttk.Label(self.main, text="", wraplength=730, justify="left", font=("Helvetica",12))
        self.rules.pack(anchor="w", pady=(0, 12))
        self.setup_assistance()
        self.setup_picture_nonogram_toolbar()
        self.board_holder = ttk.Frame(self.main)
        self.board_holder.pack(fill="both", expand=True)
        self.canvas = BoardCanvas(self.board_holder, bg=PAPER, highlightthickness=1,
                                highlightbackground=LINE)
        ybar = ttk.Scrollbar(self.board_holder, orient="vertical", command=self.canvas.yview)
        xbar = ttk.Scrollbar(self.board_holder, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)
        ybar.pack(side="right", fill="y")
        xbar.pack(side="bottom", fill="x")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self.request_board_fit)
        self.main.bind("<Configure>", self.resize_rules)
        self.status = ttk.Label(self.main, text="Noch kein Rätsel geladen.", wraplength=700,
                                font=("Helvetica", 11, "bold"))
        self.status.pack(anchor="w", pady=(14, 3))
        self.progress = ttk.Progressbar(self.main, mode="indeterminate")
        self.progress.pack(fill="x", pady=(4, 0))
        self.setup_feedback()
        self.selection_changed()
        if type_id != "random" and BY_ID[type_id].available:
            root.after(100, self.new_puzzle)

    def selected_long_game(self):
        return self.long_ids[max(0, self.long_choice.current())]

    def chess_available(self):
        return BY_ID["schachraetsel"].available

    def selection_changed(self, event=None):
        if event and event.widget is self.choice:
            self.long_choice.current(0)
        if event and event.widget is self.long_choice and self.selected_long_game():
            self.choice.current(0)
        long_game = self.selected_long_game()
        item = BY_ID.get(long_game or self.type_ids[max(0, self.choice.current())])
        choices = {"hearts": self.hearts_level_choice, **dict.fromkeys(FOUR_TITLES, self.popout_level_choice)}
        for widget in (self.level_label, self.level_frame, self.chess_settings, self.hearts_level_choice, self.popout_level_choice):
            widget.pack_forget()
        if long_game == "schach":
            self.seed_label.pack_forget()
            self.seed.pack_forget()
            self.chess_settings.pack(fill="x", pady=(0,12), before=self.new_button)
            for widget in (self.chess_elo_choice, self.chess_color_choice):
                widget.configure(state="disabled" if self.busy else "readonly")
        else:
            self.seed_label.pack(anchor="w", before=self.new_button)
            self.seed.pack(fill="x", pady=(5,12), before=self.new_button)
            if long_game != "symbol-duel" and long_game not in SEQUENCE_TITLES:
                self.level_label.pack(anchor="w", before=self.seed_label)
                difficulty_control = choices.get(long_game, self.level_frame)
                difficulty_control.pack(fill="x", pady=(5,12), before=self.seed_label)
                if long_game in choices:
                    difficulty_control.configure(state="disabled" if self.busy else "readonly")
        if long_game in MAZE_TITLES:
            self.maze_form_frame.pack(fill="x", pady=(0, 12), before=self.seed_label)
            self.maze_form_choice.configure(state="disabled" if self.busy else "readonly")
        else:
            self.maze_form_frame.pack_forget()
        if item is not None and item.id=='katzensuche':
            self.cat_size_frame.pack(fill='x',pady=(0,12),before=self.seed_label)
            self.cat_size_choice.configure(state='disabled' if self.busy else 'readonly')
        else:
            self.cat_size_frame.pack_forget()
        if item is not None and item.id=='pipes':
            self.pipe_size_frame.pack(fill='x',pady=(0,12),before=self.seed_label)
            self.pipe_size_choice.configure(state='disabled' if self.busy else 'readonly')
        else:self.pipe_size_frame.pack_forget()
        available = self.chess_available() if long_game == "schach" else item is None or item.available
        self.new_button.configure(text="Partie starten" if long_game else "Neues Rätsel",
                                  state="normal" if available and not self.busy else "disabled")
        if not available:
            self.note.configure(text=(item or BY_ID["schachraetsel"]).unavailable_reason)
            self.note.pack(anchor="w", pady=(0,8))
        else:
            self.note.pack_forget()


    def refresh_difficulty_buttons(self):
        for value,button in self.level_buttons.items():
            button.configure(style="DifficultyOn.TButton" if self.level.get()==value else "TButton",
                             state="disabled" if self.busy else "normal")

    def random_puzzle(self):
        if self.busy:
            return
        self.choice.current(0)
        self.long_choice.current(0)
        self.seed.delete(0, "end")
        self.selection_changed()
        self.new_puzzle()

    def set_busy(self, value):
        if value:
            self.cancel_pentomino_drag(paint=False);self.finish_route_drag()
        self.busy = value
        if value:
            self.disabled_board_controls=[(widget,widget.cget('state')) for widget in getattr(self,'extra_widgets',[])]
            for widget,state in self.disabled_board_controls:widget.configure(state='disabled')
        else:
            for widget,state in getattr(self,'disabled_board_controls',[]):
                if widget.winfo_exists():widget.configure(state=state)
            self.disabled_board_controls=[]
        self.choice.configure(state="disabled" if value else "readonly")
        self.long_choice.configure(state="disabled" if value else "readonly")
        self.refresh_difficulty_buttons()
        self.seed.configure(state="disabled" if value else "normal")
        self.random_button.configure(state="disabled" if value else "normal")
        for button in (self.solution_button, self.reset_button, self.export_button):
            button.configure(state="normal" if self.puzzle is not None and not value else "disabled")
        if self.puzzle is not None and self.puzzle.type_id == "hearts":
            self.solution_button.configure(state="disabled")
        if self.puzzle is not None and self.puzzle.view["kind"] in ("chess-match", "popout", "symbol-duel", "sequence", "maze-game"):
            for button in (self.solution_button, self.reset_button, self.export_button):
                button.configure(state="disabled")
        self.update_notes_button()
        self.update_undo_button()
        self.update_assist_buttons()
        self.selection_changed()
        self.refresh_nonogram_toolbar()
        if value:
            self.cancel_pour_animation()
            if self.idle_diagnostics is not None:
                self.idle_diagnostics.generation_started()
            self.cancel_nonogram_clicks()
            self.cancel_validation()
            self.hide_success()
            self.dismiss_error()
            self.progress.start(60)
        else:
            self.progress.stop()

    def new_puzzle(self):
        if self.busy:
            return
        long_game = self.selected_long_game()
        if long_game == "schach":
            self.start_chess_match()
            return
        try:
            seed = int(self.seed.get()) if self.seed.get().strip() else None
        except ValueError:
            messagebox.showerror("Ungültiger Seed", "Der Seed muss eine ganze Zahl sein.", parent=self.root)
            return
        if long_game in FOUR_TITLES:
            self.start_popout(seed, long_game)
            return
        if long_game == "symbol-duel":
            self.start_symbol_duel(seed)
            return
        if long_game in SEQUENCE_TITLES:
            self.start_sequence(seed, long_game)
            return
        type_id = long_game or self.type_ids[max(0, self.choice.current())]
        if type_id not in MAZE_TITLES and type_id != "random" and not BY_ID[type_id].available:
            return
        generator = generate_maze if type_id in MAZE_TITLES else generate
        self.set_busy(True)
        self.status.configure(text="Erzeuge Rätsel und prüfe die Lösbarkeit …", foreground=INK)
        options = {}
        if type_id in MAZE_TITLES:
            options["form"] = self.maze_form.get()
        elif type_id == "katzensuche":
            options["size"] = self.cat_size.get()
        elif type_id == "pipes":
            options["size"] = self.pipe_size.get()
        level = self.hearts_level.get().lower() if type_id == "hearts" else self.level.get()
        self.future = self.pool.submit(generator, type_id, seed, level, **options)
        self.root.after(80, self.poll_generation)

    def poll_generation(self):
        if not self.future.done():
            self.root.after(80, self.poll_generation)
            return
        try:
            puzzle = self.future.result()
        except Exception as exc:
            self.set_busy(False)
            self.status.configure(text="Generierung fehlgeschlagen. Bitte erneut versuchen.", foreground="#9a3c30")
            messagebox.showerror("Generierung fehlgeschlagen", str(exc), parent=self.root)
            return
        self.load_puzzle(puzzle)

    def load_puzzle(self, puzzle):
        self.puzzle = puzzle
        self.reset_nonogram_lives()
        self.showing_solution = False
        self.solution_button.configure(text="Lösung ansehen")
        self.set_busy(False)
        self.title.configure(text=puzzle.title)
        certificate = (('Matt & Stockfish geprüft' if puzzle.view['task']=='mate' else 'Stockfish geprüft') if puzzle.view['kind']=='chess' else
                       'Optimalität geprüft' if puzzle.view['kind'] in ('pouring','jump') else
                       'Spielregeln geprüft' if puzzle.view['kind'] in ('activity', 'popout') and not puzzle.analysis.get('logical_solvable') else
                       'Eindeutigkeit geprüft' if puzzle.analysis.get('unique') and not puzzle.analysis.get('logical_solvable') else 'Ohne Raten geprüft')
        if puzzle.view['kind'] == 'chess-match':
            color = 'Weiß' if puzzle.view['white'] else 'Schwarz'
            self.meta.configure(text=f"Du spielst {color} · Stockfish {puzzle.view['elo']} Elo")
        elif puzzle.view["kind"] == "maze-game":
            self.meta.configure(text=f"{puzzle.difficulty.capitalize()} · {puzzle.view['form']} · Seed {puzzle.seed} · Lösbarkeit geprüft")
        elif puzzle.view["kind"] == "picture-nonogram":
            cols, rows = puzzle.view["cols"], puzzle.view["rows"]
            self.meta.configure(text=f"{cols} × {rows} Felder · {puzzle.difficulty.capitalize()} · Seed {puzzle.seed} · {certificate}")
        elif puzzle.view["kind"] == "sequence":
            size = puzzle.view["size"]
            layout = "4 Felder im Kreis" if size == 2 else "3 × 3 Felder"
            self.meta.configure(text=f"{layout} · Seed {puzzle.seed}")
        elif puzzle.view["kind"] == "symbol-duel":
            self.meta.configure(text=f"{CARD_COUNT} Karten · {SYMBOLS_PER_CARD} Symbole pro Karte · Seed {puzzle.seed}")
        else:
            self.meta.configure(text=f"{puzzle.difficulty.capitalize()}   ·   Seed {puzzle.seed}   ·   {certificate}")
        self.rules.configure(text=puzzle.rules.replace("−", "-").replace("–", "-"))
        self.render()
        self.on_change()
        if self.idle_diagnostics is not None:
            self.idle_diagnostics.arm()

    def clear_board(self):
        self.nonogram_toolbar.pack_forget()
        self.clear_symbol_controls()
        self.close_assistance()
        self.cancel_hearts_timer()
        self.cancel_chess_match_request()
        self.cancel_popout()
        self.cancel_maze_turn()
        self.cancel_sequence_job()
        self.cancel_pentomino_drag(paint=False)
        self.close_chess_menu()
        self.route_drag_active=False
        self.cancel_pour_animation()
        self.cancel_nonogram_clicks()
        self.reset_feedback()
        self.updating = True
        for entry in self.entries.values():
            entry.destroy()
        for widget in self.pour_widgets:
            widget.destroy()
        for widget in getattr(self,'extra_widgets',[]):widget.destroy()
        self.extra_widgets=[]
        self.pour_widgets, self.pour_rows = [], []
        self.canvas.delete("all")
        self.canvas.unbind("<Button-1>")
        self.canvas.unbind("<Double-Button-1>")
        self.canvas.unbind("<Button-3>")
        for key in ("r","R","m","M"):self.canvas.unbind(f"<KeyPress-{key}>")
        self.canvas.unbind("<B1-Motion>")
        self.canvas.unbind("<ButtonRelease-1>")
        self.canvas.unbind("<Motion>")
        self.canvas.unbind("<Leave>")
        for sequence in ("<Left>", "<Right>", "<Up>", "<Down>", "<KeyPress-space>"):
            self.canvas.unbind(sequence)
        self.canvas.configure(cursor="")
        self.vars = {}
        self.entries = {}
        self.diagonal_overlays={}
        self.diagonal_segments=[]
        self.cell_bgs = {}
        self.init_notes()
        self.init_history()

    def add_entry(self, key, x, y, size=38, *, borderless=False, width=None, font_size=14, entry_options=None):
        var = tk.StringVar()
        validate = self.root.register(lambda s: s == "" or s == "-" or (len(s) <= 3 and s.lstrip("-").isdigit()))
        options = dict(justify="center", relief="flat",
                         bg=PAPER, fg=ACCENT, insertbackground=ACCENT,
                         font=("Helvetica", font_size, "bold"), width=3,
                         highlightthickness=0 if borderless else 1,
                         borderwidth=0 if borderless else 2, highlightbackground=LINE,
                         highlightcolor=ACCENT, validate="key", validatecommand=(validate, "%P"))
        options.update(entry_options or {})
        entry = BoardEntry(self.canvas, textvariable=var, **options)
        window = self.canvas.create_window(x, y, window=entry, width=size if width is None else width,
                                           height=size, tags=(f"assist-field:{key}",))
        self.vars[key] = var
        self.entries[key] = entry
        var.trace_add("write", lambda *args,k=key: self.on_change(k))
        entry.bind("<Up>", lambda e: self.move(key, -1, 0))
        entry.bind("<Down>", lambda e: self.move(key, 1, 0))
        entry.bind("<Left>", lambda e: self.move(key, 0, -1))
        entry.bind("<Right>", lambda e: self.move(key, 0, 1))
        self.register_notes(key, entry, window)
        self.register_input_commit(key,entry)

    def move(self, key, dr, dc):
        try:
            r, c = map(int, key.split(","))
        except ValueError:
            return
        view = self.puzzle.view
        rows, cols = view.get("rows", view.get("size", 0)), view.get("cols", view.get("size", 0))
        for _ in range(max(rows, cols)):
            r, c = r+dr, c+dc
            if not (0 <= r < rows and 0 <= c < cols):
                return "break"
            target = f"{r},{c}"
            if target in self.entries:
                self.entries[target].focus_set()
                self.entries[target].selection_range(0, "end")
                return "break"
        return "break"

    def render(self):
        self.clear_board()
        p, view = self.puzzle, self.puzzle.view
        if p.type_id == "camping":
            self.render_camping()
        elif p.type_id == "kistenguck":
            self.render_boxes()
        elif view['kind'] == 'cheese':
            self.render_cheese()
        elif view['kind'] == 'nest':
            self.render_nest()
        elif view['kind'] in ('cats','matrix'):
            self.render_matrix()
        elif view['kind']=='routes':
            self.render_routes()
        elif view['kind']=='mines':
            self.render_mines()
        elif view['kind']=='binary-symbols':
            self.render_symbol_grid()
        elif view['kind']=='treasure':
            self.render_treasure()
        elif view['kind']=='activity':
            self.render_activity()
        elif view['kind']=='jump':
            self.render_jump()
        elif view['kind']=='chess':
            self.render_chess()
        elif view['kind']=='chess-match':
            self.render_chess_match()
        elif view['kind'] == 'popout':
            self.render_popout()
        elif view['kind'] == 'maze-game':
            self.render_maze_game()
        elif view['kind'] == 'sequence':
            self.render_sequence()
        elif view['kind'] == 'symbol-duel':
            self.render_symbol_duel()
        elif view['kind'] == 'distance':
            self.render_distance()
        elif view['kind'] == 'harakiri':
            self.render_harakiri()
        elif view['kind'] == 'pouring':
            self.render_pouring()
        elif view["kind"] == "rectangles":
            self.render_rectangles()
        elif view["kind"] == "pearls":
            self.render_pearls()
        elif view["kind"] == "kakuro":
            self.render_kakuro()
        elif view["kind"] == "diagram":
            self.render_diagram()
        elif view["kind"] == "lock":
            self.render_lock()
        elif view["kind"] == "arithmetic":
            self.render_arithmetic()
        elif view["kind"] == "form":
            self.canvas.create_text(28, 24, text="DIE HINWEISE" if "lock_clues" in view else "DIE GLEICHUNGEN", anchor="nw", fill=MUTED,
                                    font=("Helvetica", 10, "bold"))
            y = 66
            for equation in view["equations"]:
                self.canvas.create_text(28, y, text=equation.replace("−", "-").replace("→", ":"), anchor="nw", width=640, fill=INK,
                    font=("Helvetica", 12 if "lock_clues" in view else 15))
                y += 60 if "lock_clues" in view else 37
            self.canvas.create_text(28, y+12, text=("Zusatzhinweise: " if "lock_clues" in view else "Schlussformel: ") + view["expression"].replace("−", "-"), anchor="nw",
                                    width=640, fill=INK, font=("Helvetica", 12))
            y += 86
            for key in p.editable:
                self.canvas.create_text(28, y, text=key, anchor="w", fill=INK, font=("Helvetica", 13))
                self.add_entry(key, 210, y, 40)
                y += 52
            self.canvas.configure(scrollregion=(0, 0, 700, y+25))
        elif view["kind"] == "hashi":
            self.render_hashi()
        else:
            self.render_grid()
        self.updating = False
        self.history_state = self.capture_history()
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)
        self.request_board_fit()
        self.update_undo_button()
        self.update_notes_button()
        self.paint_color_labels()
        if self.entries:
            next(iter(self.entries.values())).focus_set()
        else:
            self.canvas.bind('<Button-1>',lambda event:self.canvas.focus_set(),add='+')

    def resize_rules(self, event):
        width = max(250,event.width-12)
        if int(self.rules.cget('wraplength')) != width:
            self.rules.configure(wraplength=width)
        if int(self.status.cget('wraplength')) != width:
            self.status.configure(wraplength=width)
        for label in (self.hint_message, self.review_message):
            if int(label.cget("wraplength")) != width:
                label.configure(wraplength=width)

    def request_board_fit(self, event=None):
        if event is not None:
            size = event.width, event.height
            if size == self.last_canvas_size:
                return
            self.last_canvas_size = size
        if self.fit_job is not None:
            self.root.after_cancel(self.fit_job)
        self.fit_job = self.root.after_idle(self.fit_board)

    def fit_board(self):
        self.fit_job = None
        if self.puzzle is None:
            return
        self.layout_symbol_duel()
        self.layout_maze_game()
        if self.fixed_board_scale is not None:
            zoom = self.fixed_board_scale
        else:
            x1,y1,x2,y2 = self.canvas.logical_region
            width,height = self.canvas.winfo_width()-8,self.canvas.winfo_height()-8
            zoom = max(1.0,min(1.7,width/max(1,x2-x1),height/max(1,y2-y1)))
            zoom = int(zoom*100)/100
        if self.canvas.set_zoom(zoom) and not self.is_click_board():
            self.refresh_note_previews()
        self.fit_hearts_hand()

    def render_diagram(self):
        p, v = self.puzzle, self.puzzle.view
        positions = v["positions"]
        for a, b in v.get("links", []):
            self.canvas.create_line(*circle_link(positions[a], positions[b]), fill=MUTED, width=2,
                                    tags=("diagram-link", f"link:{a}:{b}"))
        for key, polygon in v.get("polygons", {}).items():
            self.canvas.create_polygon(*polygon, fill="#edf0e7" if key in p.givens else PAPER,
                                       outline=INK, width=1, tags=("hive-triangle",))
        if v.get("polygons"):
            for i, group in enumerate(v.get("groups", [])):
                boundary = [point for key in group for point in v["polygons"][key][2:4]]
                self.canvas.create_polygon(*boundary, fill="", outline=INK, width=4,
                                           tags=("hive-outline", f"hive:{i}"))
        for key, (x, y) in positions.items():
            if not v.get("polygons"):
                if v.get("tiles"):
                    self.canvas.create_rectangle(x-25, y-22, x+25, y+22, outline=INK, fill=PAPER)
                else:
                    self.canvas.create_oval(x-29, y-29, x+29, y+29, outline=INK, fill=PAPER, width=2)
            if v.get("labels") and (key != "Mitte" or v.get("center_label", True)):
                label_x, label_y = v.get("label_positions", {}).get(key, (x, y-42))
                self.canvas.create_text(label_x, label_y, text=key, fill=MUTED, font=("Helvetica", 11, "bold"))
            if key in p.givens:
                self.canvas.create_text(x, y, text=str(p.givens[key]), fill=INK, font=("Helvetica", 14, "bold"))
            else:
                self.add_entry(key, x, y, v.get("entry_size", 35))
        y = v["height"]
        equations = v.get("equations", [])
        columns = v.get("equation_columns", 1)
        count_rows = (len(equations)+columns-1)//columns
        column_width = (v["width"]-56)/columns
        for i, equation in enumerate(equations):
            column, row = divmod(i, count_rows)
            self.canvas.create_text(28+column*column_width, y+row*32,
                text=equation.replace("−", "-"), anchor="nw", width=column_width-12,
                fill=INK, font=("Helvetica", 13), tags=("diagram-equation", f"equation:{i}"))
        y += count_rows*32
        self.canvas.configure(scrollregion=(0, 0, v["width"], y+25))

    def render_pearls(self):
        p, view = self.puzzle, self.puzzle.view
        step, margin, radius = 54, 30, 21
        xy = lambda key: (margin+int(key.split(',')[1])*step,
                          margin+int(key.split(',')[0])*step)
        for i, path in enumerate(view["paths"]):
            for a, b in zip(path, path[1:]):
                self.canvas.create_line(*circle_link(xy(a), xy(b), radius), fill=INK, width=3,
                    tags=("pearl-link", f"string:{i}", f"pearl-link:{a}:{b}"))
        for key in p.model.domains:
            x, y = xy(key)
            r, c = map(int, key.split(","))
            main, other = r == c, r+c == view["size"]-1
            bg = "#e9e2f5" if main and other else "#e4edf9" if main else "#fff0cb" if other else PAPER
            self.cell_bgs[key] = bg
            tag = f"pearl:{key}"
            diagonal_tags = (("pearl-diagonal-main",) if main else ()) + (("pearl-diagonal-other",) if other else ())
            self.canvas.create_oval(x-radius, y-radius, x+radius, y+radius, fill=bg,
                outline=INK, width=1.5, tags=("pearl", tag)+diagonal_tags)
            if key in p.givens:
                self.canvas.create_text(x, y, text=str(p.givens[key]), fill=INK,
                    font=("Helvetica", 15, "bold"))
            else:
                self.add_entry(key, x, y, 28, borderless=True)
                self.entries[key].configure(bg=bg)
                self.entries[key].bind("<FocusIn>", lambda event, t=tag:
                    self.canvas.itemconfigure(t, outline=ACCENT, width=3))
                self.entries[key].bind("<FocusOut>", lambda event, t=tag:
                    self.canvas.itemconfigure(t, outline=INK, width=1.5),add="+")
                self.canvas.tag_bind(tag, "<Button-1>", lambda event, k=key: self.entries[k].focus_set())
        extent = 2*margin+(view["size"]-1)*step
        self.canvas.create_text(12, extent+2, text="Blau und Gelb markieren die Diagonalen; die Mitte gehört zu beiden.",
                                anchor="nw", fill=MUTED, font=("Helvetica", 9), width=extent-24)
        self.canvas.configure(scrollregion=(0, 0, extent, extent+34))

    def render_kakuro(self):
        p, v = self.puzzle, self.puzzle.view
        step, margin = 46, 20
        rows, cols = v["rows"], v["cols"]
        for r in range(-1, rows):
            for c in range(-1, cols):
                key = f"{r},{c}"
                x, y = margin+(c+1)*step, margin+(r+1)*step
                outside = r == -1 or c == -1
                tags = ("kakuro-external-clue",) if outside else ("kakuro-cell",)
                if key in p.model.domains:
                    bg = "#edf0e7" if key in p.givens else PAPER
                    self.canvas.create_rectangle(x, y, x+step, y+step, fill=bg, outline=LINE, tags=tags)
                    if key in p.givens:
                        self.canvas.create_text(x+step/2, y+step/2, text=str(p.givens[key]),
                                               fill=INK, font=("Helvetica", 15, "bold"))
                    else:
                        self.add_entry(key, x+step/2, y+step/2, step-10)
                else:
                    hint = v["hints"].get(key, {})
                    if not outside or hint:
                        self.canvas.create_rectangle(x, y, x+step, y+step, fill="#31576d", outline=LINE, tags=tags)
                    color = PAPER
                    if hint:
                        self.canvas.create_line(x, y, x+step, y+step, fill="#aebdb1")
                    if "right" in hint:
                        self.canvas.create_line(x+5, y+12, x+19, y+12, arrow="last", arrowshape=(4, 5, 2), fill=color)
                        self.canvas.create_text(x+step-4, y+12, text=str(hint['right']), anchor="e",
                            fill=color, font=("Helvetica", 11, "bold"), tags=("kakuro-sum",f"kakuro-sum:{key}:right"))
                    if "down" in hint:
                        self.canvas.create_line(x+9, y+step-23, x+9, y+step-5, arrow="last", arrowshape=(4, 5, 2), fill=color)
                        self.canvas.create_text(x+18, y+step-12, text=str(hint['down']), anchor="w",
                            fill=color, font=("Helvetica", 11, "bold"), tags=("kakuro-sum",f"kakuro-sum:{key}:down"))
        if v.get("blocks"):
            left,top = margin+step,margin+step
            for i in (0,3,6,9):
                self.canvas.create_line(left+i*step,top,left+i*step,top+rows*step,
                                        fill=INK,width=2.5,tags=("kakuro-block",))
                self.canvas.create_line(left,top+i*step,left+cols*step,top+i*step,
                                        fill=INK,width=2.5,tags=("kakuro-block",))
        if any(v["missing"].values()):
            self.canvas.create_text(margin+(cols+1)*step+12, margin+step/2, text="Fehlt in der Zeile",
                anchor="w", fill=MUTED, font=("Helvetica", 10, "bold"))
        for row, digits in v["missing"].items():
            if not digits:
                continue
            self.canvas.create_text(margin+(cols+1)*step+12, margin+(int(row)+1.5)*step,
                text=", ".join(map(str, digits)), anchor="w", fill=INK,
                font=("Helvetica", 11), tags=("kakuro-missing", f"kakuro-missing:{row}"))
        self.canvas.configure(scrollregion=(0, 0, margin+(cols+1)*step+170, margin+(rows+1)*step+28))

    def render_grid(self):
        p, v = self.puzzle, self.puzzle.view
        rows, cols = v.get("rows", v["size"]), v.get("cols", v["size"])
        step = v.get('cell_size', 51 if max(rows, cols) <= 9 else 44)
        bottom_right = v.get("hints_side") == "bottom-right"
        left = 90 if "row_hints" in v and not bottom_right else 28
        top = 68 if 'diagonal_sums' in v else 105 if "col_hints" in v and not bottom_right else 28
        picture = v["kind"] == "picture-nonogram"
        if picture:
            left = max(62, 14 + 8 * max(len(" ".join(map(str, h))) for h in v["row_hints"]))
            top = 20 + 16 * max(map(len, v["col_hints"]))
        xy = lambda key: (left+(int(key.split(',')[1])+.5)*step,
                          top+(int(key.split(',')[0])+.5)*step)
        trees = set(v.get("trees", []))
        for r in range(rows):
            for c in range(cols):
                key = f"{r},{c}"
                x, y = xy(key)
                bg = "#edf0e7" if key in p.givens else PAPER if key in p.model.domains else "#e6ebdf"
                if key in v.get('black_cells', {}):
                    bg = INK
                elif v.get('highlight_diagonals') and (r == c or r+c == rows-1):
                    bg = '#f7f3e7'
                if any(key in group for group in v.get('windows',[])):bg=WINDOW_COLOR
                if key in v.get("shaded", []):
                    bg = "#dce2dc"
                self.cell_bgs[key] = bg
                self.canvas.create_rectangle(x-step/2, y-step/2, x+step/2, y+step/2, fill=bg,
                    outline=LINE, tags=("grid-cell", f"cell:{key}"))
        if picture:
            for r in range(5, rows, 5):
                y = top + r * step
                self.canvas.create_line(left, y, left + cols * step, y, fill="#839b8e", width=2)
            for c in range(5, cols, 5):
                x = left + c * step
                self.canvas.create_line(x, top, x, top + rows * step, fill="#839b8e", width=2)
        if v.get('diagonals'):
            for a,b,c,d in ((0,0,cols,rows),(0,rows,cols,0)):
                segment=(left+a*step,top+b*step,left+c*step,top+d*step)
                self.diagonal_segments.append(segment)
                self.canvas.create_line(*segment,fill=self.sudoku_diagonal_color,width=4,tags=('sudoku-diagonal',))
        regions = {k: i for i, g in enumerate(v.get("regions", [])) for k in g}
        if regions:
            for r in range(rows):
                for c in range(cols):
                    x, y = left+c*step, top+r*step
                    key = f"{r},{c}"
                    if r == 0 or regions.get(key) != regions.get(f"{r-1},{c}"):
                        self.canvas.create_line(x, y, x+step, y, fill=INK, width=3)
                    if c == 0 or regions.get(key) != regions.get(f"{r},{c-1}"):
                        self.canvas.create_line(x, y, x, y+step, fill=INK, width=3)
            self.canvas.create_line(left+cols*step, top, left+cols*step, top+rows*step, fill=INK, width=3)
            self.canvas.create_line(left, top+rows*step, left+cols*step, top+rows*step, fill=INK, width=3)
        if v.get("blocks"):
            for i in range(0, cols+1, 3):
                self.canvas.create_line(left+i*step, top, left+i*step, top+rows*step, fill=INK, width=2)
            for i in range(0, rows+1, 3):
                self.canvas.create_line(left, top+i*step, left+cols*step, top+i*step, fill=INK, width=2)
        for key in p.model.domains:
            x, y = xy(key)
            if p.type_id == "nonogramm" or picture:
                self.register_click_value(key)
            elif key in p.givens:
                self.canvas.create_text(x, y, text=str(p.givens[key]),
                    fill='white' if key in v.get('black_cells', {}) else INK, font=("Helvetica", 15, "bold"))
            else:
                r,c=map(int,key.split(','))
                diagonal_cell=bool(v.get('windows') and (r==c or r+c==rows-1))
                self.add_entry(key, x, y+(6 if v.get("corner_labels") else 0),
                    v.get('entry_size', step-22 if v.get("corner_labels") else step-9),
                    borderless=diagonal_cell,
                    entry_options={'bg':self.cell_bgs[key]} if v.get('windows') else None)
                if diagonal_cell:
                    self.register_diagonal_entry(key)
        for key, label in v.get("corner_labels", {}).items():
            x, y = xy(key)
            self.canvas.create_text(x-step/2+4, y-step/2+3, text=label.replace("−", "-"), anchor="nw",
                                   fill=INK, font=("Helvetica", 9, "bold"))
        for key, label in v.get("labels", {}).items():
            self.canvas.create_text(*xy(key), text=str(label), fill=ACCENT, font=("Helvetica", 17, "bold"))
        for key in trees:
            self.canvas.create_text(*xy(key), text="♠", fill=ACCENT, font=("Helvetica", 24))
        for a, b, kind in v.get("dots", []):
            x1, y1 = xy(a)
            x2, y2 = xy(b)
            x, y = (x1+x2)/2, (y1+y2)/2
            self.canvas.create_oval(x-4, y-4, x+4, y+4, fill=INK if kind == "black" else PAPER, outline=INK)
        for r, hint in enumerate([] if v.get('sum_cells') else v.get("row_hints", [])):
            self.canvas.create_text(left+cols*step+16 if bottom_right else left-10, top+(r+.5)*step,
                text=" ".join(map(str, hint)) or "0", anchor="w" if bottom_right else "e",
                fill=INK, font=("Helvetica", 10, "bold"))
        for c, hint in enumerate([] if v.get('sum_cells') else v.get("col_hints", [])):
            self.canvas.create_text(left+(c+.5)*step, top+rows*step+16 if bottom_right else top-10,
                text="\n".join(map(str, hint)) or "0", anchor="n" if bottom_right else "s",
                fill=INK, font=("Helvetica", 10, "bold"))
        bottom = top+rows*step+(50 if bottom_right else 28)
        if v.get('sum_cells'):
            bottom = top+(rows+1)*step+28
        if 'diagonal_sums' in v:
            bottom = top+rows*step+80
        if v.get("footer"):
            self.canvas.create_text(left, bottom+4, text=v["footer"], anchor="nw", fill=INK, font=("Helvetica", 12, "bold"))
            bottom += 40
        if p.result is not None:
            self.canvas.create_text(left, bottom+4, text="", anchor="nw", fill=INK,
                font=("Helvetica", 15, "bold"), tags=("puzzle-result",))
            bottom += 35
        self.draw_calendar_marks(left, top, step, rows, cols)
        right = step+28 if v.get('sum_cells') else 90 if 'diagonal_sums' in v else 65 if bottom_right else 28
        self.canvas.configure(scrollregion=(0, 0, left+cols*step+right, bottom))
        if p.type_id == "nonogramm" or picture:
            self.nonogram_geometry = left, top, step, rows, cols
            self.nonogram_paints = {}
            self.canvas.bind('<Button-1>', self.click_nonogram)
            self.canvas.configure(cursor='hand2')
            if picture:
                self.nonogram_toolbar.pack(fill="x", pady=(0, 8), before=self.board_holder)
                self.canvas.bind("<Button-3>", lambda event: self.click_nonogram(event, cross=True))

    def on_change(self,edited_key=None):
        if self.updating or self.puzzle is None or self.showing_solution:
            return
        self.clear_hint()
        if self.assist_review:
            self.clear_assist_marks()
        self.apply_change(edited_key)
        if self.assist_review and not self.busy:
            self.dismiss_error()
            self.paint_assist_review()

    def apply_change(self, edited_key):
        if edited_key is not None:
            self.answer_edited(edited_key)
        self.record_history()
        if self.busy:
            return
        if self.puzzle.view['kind'] == 'pouring':
            self.on_pour_change()
            return
        if self.puzzle.view['kind'] in ('cats','matrix'):
            self.on_matrix_change()
            return
        if self.puzzle.view['kind']=='routes':
            self.on_routes_change()
            return
        if self.puzzle.view['kind']=='jump':
            self.on_jump_change()
            return
        if self.puzzle.view['kind']=='chess':
            self.on_chess_change()
            return
        if self.puzzle.view['kind'] in ('chess-match', 'popout', 'symbol-duel', 'sequence', 'maze-game'):
            return
        if self.puzzle.view['kind']=='binary-symbols':
            self.on_symbol_change()
            return
        if self.puzzle.view['kind']=='treasure':
            self.on_treasure_change()
            return
        if self.puzzle.view['kind']=='activity':
            self.on_activity_change()
            return
        if self.puzzle.view["kind"] == "picture-nonogram":
            self.update_picture_nonogram()
            return
        if self.is_click_board():
            self.on_click_board_change()
            return
        if self.note_mode:
            self.hide_success()
            self.dismiss_error()
            self.note_status()
            return
        if self.puzzle.view["kind"] == "rectangles":
            self.on_rectangle_change()
            return
        if self.puzzle.view["kind"] == "lock":
            self.on_lock_change()
            return
        values = {}
        invalid = []
        for key, var in self.vars.items():
            entry = self.entries[key]
            text = var.get()
            try:
                if text:
                    value = int(text)
                    if value not in self.puzzle.model.domains[key]:
                        invalid.append(key)
                    values[key] = value
            except ValueError:
                invalid.append(key)
            bg, fg = (ACCENT, "white") if (self.puzzle.view.get("binary_paint") and text == "1") else (self.cell_bgs.get(key, PAPER), ACCENT)
            entry.configure(bg=bg, fg=fg)
            if self.puzzle.view["kind"] == "pearls":
                self.canvas.itemconfigure(f"pearl:{key}", fill=bg)
        self.refresh_note_previews()
        if self.puzzle.type_id == "fillomino":
            self.paint_fillomino(values)
        complete = all(var.get() for var in self.vars.values())
        if invalid and not complete:
            self.hide_success(reset=True)
            self.dismiss_error(reset=True)
            self.status.configure(text="Ungültige Eingabe: Beachte den erlaubten Zahlenbereich.", foreground="#9a3c30")
            return
        state,wrong = self.puzzle.check(values)
        if complete and invalid:
            wrong = [k for k in self.vars if values.get(k) != self.puzzle.solution[k]]
            state = "wrong"
        pending = self.pending_answer(wrong) if complete else None
        if not complete:
            self.hide_success(reset=True)
            self.dismiss_error(reset=True)
            self.status.configure(text=f"{len(values)} von {len(self.vars)} Feldern ausgefüllt · vollständige Eingaben werden automatisch geprüft.", foreground=MUTED)
        elif pending is not None:
            self.hide_success()
            self.dismiss_error(reset=True)
            self.error_count = None
            self.status.configure(text="Letzte Eingabe vervollständigen …",foreground=MUTED)
        elif wrong:
            self.show_error_count(len(wrong))
        else:
            self.show_success()

    def toggle_solution(self):
        self.close_assistance()
        self.cancel_pentomino_drag(paint=False)
        self.finish_route_drag()
        self.cancel_pour_animation()
        self.cancel_nonogram_clicks()
        self.cancel_validation()
        self.hide_success()
        self.dismiss_error()
        self.finish_rectangle_drag()
        self._toggle_solution()
        self.update_assist_buttons()
        self.update_undo_button()

    def _toggle_solution(self):
        if self.puzzle is None:
            return
        if self.puzzle.view['kind']=='activity':
            self.toggle_activity_solution()
            return
        if self.puzzle.view['kind'] in ('jump','chess'):
            self.close_chess_menu()
            self.toggle_strategy_solution()
            return
        if self.puzzle.view['kind'] == 'pouring':
            self.toggle_pour_solution()
            return
        if self.is_click_board():
            self.toggle_click_solution()
            return
        if self.puzzle.view["kind"] == "rectangles":
            self.toggle_rectangle_solution()
            return
        if self.puzzle.view["kind"] == "lock":
            self.toggle_lock_solution()
            return
        if not self.showing_solution:
            self.pause_notes_for_solution()
        self.showing_solution = not self.showing_solution
        self.updating = True
        if self.showing_solution:
            self.saved_values = {k: v.get() for k, v in self.vars.items()}
            for k, var in self.vars.items():
                var.set(str(self.puzzle.solution[k]))
                bg = self.cell_bgs[k] if self.puzzle.view["kind"] == "pearls" or self.puzzle.view.get('windows') else "#e6eee5"
                self.entries[k].configure(state="readonly", readonlybackground=bg, fg=INK)
                if self.puzzle.view["kind"] == "pearls":
                    self.canvas.itemconfigure(f"pearl:{k}", fill=bg)
            self.solution_button.configure(text="Zurück zu meinen Eingaben")
            self.status.configure(text="Lösungsansicht · deine bisherigen Eingaben bleiben erhalten.", foreground=INK)
            self.reset_button.configure(state="disabled")
            if self.puzzle.type_id == "fillomino":
                self.paint_fillomino(self.puzzle.solution)
        else:
            for k, var in self.vars.items():
                self.entries[k].configure(state="normal")
                var.set(self.saved_values[k])
            self.solution_button.configure(text="Lösung ansehen")
            self.reset_button.configure(state="normal")
        self.updating = False
        self.refresh_diagonal_entries()
        if not self.showing_solution:
            self.resume_notes_after_solution()
        self.update_notes_button()
        self.refresh_note_previews()
        if not self.showing_solution:
            self.on_change()

    def reset(self):
        if self.puzzle is None or self.showing_solution:
            return
        if not messagebox.askyesno("Eingaben zurücksetzen", "Alle eigenen Eingaben und Notizen dieses Rätsels leeren?", parent=self.root):
            return
        self.cancel_pentomino_drag(paint=False)
        self.finish_route_drag()
        self.close_chess_menu()
        self.cancel_nonogram_clicks()
        self.cancel_validation()
        self.finish_rectangle_drag()
        if self.puzzle.view['kind']=='activity':
            self.cancel_pour_animation()
            self.activity_state=self.initial_activity_state();self.activity_selected=None
            self.on_change();return
        if self.puzzle.view['kind'] == 'pouring':
            self.set_pour_rows([('', '')])
            self.on_change()
            return
        if self.puzzle.view['kind']=='jump':
            self.jump_path=[self.puzzle.view['start']]
            self.on_change();return
        if self.puzzle.view['kind']=='chess':
            self.chess_move='';self.chess_selected=None
            self.on_change();return
        if self.puzzle.view["kind"] == "rectangles":
            self.borders.clear()
            self.refresh_borders()
            self.on_change()
            return
        if self.nonogram_lives is not None:
            self.reset_nonogram_lives()
            self.init_history()
            self.update_assist_buttons()
        self.updating = True
        for var in self.vars.values():
            var.set("")
        self.clear_notes()
        if self.puzzle.view["kind"] == "hashi":
            self.hashi_directions = {}
        self.updating = False
        if self.note_mode:
            self.set_note_mode(True)
        if self.nonogram_lives is not None:
            self.history_state = self.capture_history()
        self.on_change()

    def export(self):
        if self.puzzle is None:
            return
        path = filedialog.asksaveasfilename(parent=self.root, defaultextension=".json",
            initialfile=f"{self.puzzle.type_id}-{self.puzzle.seed}.json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        # Export is deliberately spoiler-free; CLI --show-solution is explicit.
        try:
            with open(path, "w", encoding="utf-8") as stream:
                json.dump(self.puzzle.export(), stream, ensure_ascii=False, indent=2)
        except OSError as exc:
            messagebox.showerror("Speichern fehlgeschlagen", str(exc), parent=self.root)

    def close(self):
        self.cancel_chess_match_request()
        self.cancel_popout()
        self.cancel_maze_turn()
        self.cancel_sequence_job()
        self.cancel_pentomino_drag(paint=False)
        if self.settings_window is not None:save_preferences(self.preferences,self.preferences_file)
        self.close_chess_menu()
        self.cancel_pour_animation()
        if self.idle_diagnostics is not None:
            self.idle_diagnostics.close()
        self.cancel_nonogram_clicks()
        self.cancel_validation()
        self.stop_confetti()
        if self.fit_job is not None:
            self.root.after_cancel(self.fit_job)
            self.fit_job = None
        self.pool.shutdown(wait=False, cancel_futures=True)
        self.root.destroy()


def run(type_id="random", seed=None, difficulty="schwer", *, diagnose_idle=None, cat_size=6, pipe_size=5):
    root = tk.Tk()
    app = App(root, type_id, seed, difficulty, cat_size=cat_size,pipe_size=pipe_size)
    if diagnose_idle is not None:
        from .idle_diagnostics import IdleDiagnostics
        app.idle_diagnostics = IdleDiagnostics(app, diagnose_idle)
    root.mainloop()

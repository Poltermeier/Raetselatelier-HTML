"""Original two-by-two and three-by-three color-sequence boards."""
from secrets import randbits

from .puzzle import Puzzle
from .sequence_game import ColorSequence
from .solver import Model

SEQUENCE_TITLES = {"farbfolge": "Farbfolge", "farbfolge-extrem": "Farbfolge Extrem"}
PADS = (
    ("Türkis", "#bef0e6", "#07695f", 261.63),
    ("Orange", "#ffe1b7", "#935208", 329.63),
    ("Violett", "#e6d9fa", "#69419c", 392.00),
    ("Pink", "#fbdae9", "#973260", 466.16),
    ("Blau", "#d1e7ff", "#225f9d", 523.25),
    ("Limette", "#e5efbd", "#566a19", 311.13),
    ("Rot", "#ffe0dc", "#a74036", 369.99),
    ("Gelb", "#fff1ae", "#806206", 440.00),
    ("Schiefer", "#dfe5f2", "#536182", 587.33),
)
INK = "#233a32"
ERROR = "#943b34"


class SequenceUI:
    def configure_sequence_styles(self, style):
        for index, (_, pale, strong, _) in enumerate(PADS):
            for lit, background, foreground in ((False, pale, strong), (True, strong, "#ffffff")):
                name = self.sequence_pad_style(index, lit)
                style.configure(name, background=background, foreground=foreground, font=("Helvetica", 22, "bold"))
                style.map(name, background=[("active", background), ("disabled", background)],
                          foreground=[("disabled", foreground)])

    @staticmethod
    def sequence_pad_style(index, lit):
        return f"Sequence{index}{'Lit' if lit else 'Idle'}.TButton"

    def start_sequence(self, seed, variant):
        size = 3 if variant == "farbfolge-extrem" else 2
        rules = ("Merke dir die Felder, die nacheinander aufleuchten, und tippe sie in derselben Reihenfolge an. "
                 "Nach jeder richtigen Folge wächst sie um ein Feld und du bekommst einen Punkt. "
                 "Beim ersten falschen Feld endet die Partie.")
        view = {"kind": "sequence", "size": size}
        puzzle = Puzzle(variant, SEQUENCE_TITLES[variant], rules, Model({}, []), {}, {},
                        view, randbits(48) if seed is None else seed, "")
        self.load_puzzle(puzzle)

    def render_sequence(self):
        size = self.puzzle.view["size"]
        self.sequence_game = ColorSequence(self.puzzle.seed, size * size)
        self.sequence_phase = "preview"
        self.sequence_lit = None
        self.activity_controls = []
        self.sequence_buttons = []
        self.sequence_score_text = self.canvas.create_text(16, 18, anchor="nw", fill=INK, font=("Helvetica", 17, "bold"))
        self.sequence_instruction = self.canvas.create_text(16, 53, anchor="nw", fill=INK, font=("Helvetica", 11))
        gap = 10
        width = (308 - gap * (size - 1)) / size
        for index in range(size * size):
            row, column = divmod(index, size)
            button = self.activity_button(
                str(index + 1), lambda i=index: self.choose_sequence_field(i),
                16 + width / 2 + column * (width + gap), 82 + width / 2 + row * (width + gap),
                width, height=width, style=self.sequence_pad_style(index, False),
            )
            self.sequence_buttons.append(button)
            self.set_sequence_pad(button, index, False)
        self.activity_button("Neue Partie", lambda: self.start_sequence(None, self.puzzle.type_id),
                             170, 421, tags=("sequence-restart",))
        self.canvas.itemconfigure("sequence-restart", state="hidden")
        self.canvas.configure(scrollregion=(0, 0, 340, 454))
        self.update_sequence_status("Schau zu · Runde 1")
        self.schedule_sequence(850, lambda: self.show_sequence_step(0))

    def set_sequence_pad(self, button, index, lit):
        button.configure(style=self.sequence_pad_style(index, lit))

    def light_sequence_pad(self, index=None):
        if self.sequence_lit is not None:
            old = self.sequence_lit
            self.set_sequence_pad(self.sequence_buttons[old], old, False)
        self.sequence_lit = index
        if index is not None:
            self.set_sequence_pad(self.sequence_buttons[index], index, True)
            self.victory_sound.play(self.preferences["volume"], frequency=PADS[index][3], duration=.19)

    def cancel_sequence_job(self):
        if getattr(self, "sequence_job", None) is not None:
            self.root.after_cancel(self.sequence_job)
        self.sequence_job = None

    def schedule_sequence(self, delay, callback):
        self.cancel_sequence_job()

        def advance():
            self.sequence_job = None
            if self.busy:
                self.schedule_sequence(100, callback)
            else:
                callback()

        self.sequence_job = self.root.after(delay, advance)

    def show_sequence_step(self, step):
        if step == len(self.sequence_game.pattern):
            self.sequence_phase = "answer"
            self.update_sequence_status(f"Du bist dran · 0 von {step} Feldern")
            return
        self.light_sequence_pad(self.sequence_game.pattern[step])
        self.schedule_sequence(310, lambda: self.pause_before_sequence_step(step + 1))

    def pause_before_sequence_step(self, step):
        self.light_sequence_pad()
        self.schedule_sequence(150, lambda: self.show_sequence_step(step))

    def choose_sequence_field(self, index):
        if self.busy or self.sequence_phase != "answer":
            return
        result = self.sequence_game.choose(index)
        self.light_sequence_pad(index)
        if result == "lost":
            self.sequence_phase = "finished"
            self.update_sequence_status("Partie beendet", finished=True)
            self.canvas.itemconfigure("sequence-restart", state="normal")
            self.schedule_sequence(180, self.light_sequence_pad)
        elif result == "round":
            self.sequence_phase = "preview"
            self.update_sequence_status(f"Richtig · Schau zu · Runde {self.sequence_game.score + 1}")
            self.schedule_sequence(175, lambda: self.pause_before_sequence_step(0))
        else:
            game = self.sequence_game
            self.update_sequence_status(f"Du bist dran · {game.entered} von {len(game.pattern)} Feldern")
            self.schedule_sequence(140, self.light_sequence_pad)

    def update_sequence_status(self, message, *, finished=False):
        prefix = "Erreichter Punktestand" if finished else "Punktestand"
        score = f"{prefix}: {self.sequence_game.score}"
        color = ERROR if finished else INK
        self.canvas.itemconfigure(self.sequence_score_text, text=score, fill=color)
        self.canvas.itemconfigure(self.sequence_instruction, text=message, fill=color)
        self.status.configure(text=f"{score} · {message}", foreground=color)

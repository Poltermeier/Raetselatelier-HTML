"""Circular and three-by-three color-sequence boards."""
from secrets import randbits
from typing import NamedTuple

from .puzzle import Puzzle
from .sequence_game import ColorSequence
from .solver import Model

SEQUENCE_TITLES = {"farbfolge": "Farbfolge", "farbfolge-extrem": "Farbfolge Extrem"}



class Pad(NamedTuple):
    name: str
    color: str
    ink: str
    frequency: float
    flash: str


PADS = (
    Pad("Türkis", "#18c5b4", "#083a37", 261.63, "#83ffeb"),
    Pad("Orange", "#fa832b", "#4b2108", 329.63, "#ffd394"),
    Pad("Violett", "#ae74fa", "#291548", 392.00, "#ead0ff"),
    Pad("Pink", "#f264ac", "#4b0d35", 466.16, "#ffc0e1"),
    Pad("Blau", "#53a9ff", "#102650", 523.25, "#b6e2ff"),
    Pad("Limette", "#afce28", "#293609", 311.13, "#e9ff82"),
    Pad("Rot", "#f46154", "#4e1511", 369.99, "#ffb5a7"),
    Pad("Gelb", "#ffd22e", "#483104", 440.00, "#fff59d"),
    Pad("Schieferblau", "#8f9ace", "#1e274c", 587.33, "#d5deff"),
)
DIAL_CENTER = (170, 236)
DIAL_RADIUS = 102
DIAL_PAD_LENGTH, DIAL_PAD_DEPTH = 150, 94
ROUND_PAUSE = 1200
INPUT_FLASH = 175
INK = "#233a32"
ERROR = "#943b34"


class SequenceUI:
    def configure_sequence_styles(self, style):
        for index, pad in enumerate(PADS):
            for lit, background in ((False, pad.color), (True, pad.flash)):
                name = self.sequence_pad_style(index, lit)
                style.configure(name, background=background, foreground=pad.ink, font=("Helvetica", 22, "bold"))
                style.map(name, background=[("active", background), ("disabled", background)],
                          foreground=[("disabled", pad.ink)])

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
        if size == 2:
            x, y = DIAL_CENTER
            radius = DIAL_RADIUS
            bezel = 155
            self.canvas.create_oval(x - bezel, y - bezel, x + bezel, y + bezel,
                                    fill="#284840", outline="#18352f", width=2, tags=("sequence-dial",))
            hub = 49
            self.canvas.create_oval(x - hub, y - hub, x + hub, y + hub, fill="#e9f3ed", outline="#b3cfc3", width=2)
            self.sequence_score_text = self.canvas.create_text(x, y - 11, fill=INK, font=("Helvetica", 28, "bold"))
            self.canvas.create_text(x, y + 20, text="Punkte", fill=INK, font=("Helvetica", 10, "bold"))
            self.sequence_instruction = self.canvas.create_text(170, 39, fill=INK, font=("Helvetica", 11))
            length, depth = DIAL_PAD_LENGTH, DIAL_PAD_DEPTH
            pads = ((x, y - radius, length, depth), (x + radius, y, depth, length),
                    (x, y + radius, length, depth), (x - radius, y, depth, length))
        else:
            self.sequence_score_text = self.canvas.create_text(16, 18, anchor="nw", fill=INK, font=("Helvetica", 17, "bold"))
            self.sequence_instruction = self.canvas.create_text(16, 53, anchor="nw", fill=INK, font=("Helvetica", 11))
            gap = 10
            width = (308 - gap * (size - 1)) / size
            pads = tuple((16 + width / 2 + col * (width + gap), 82 + width / 2 + row * (width + gap), width, width)
                         for row in range(size) for col in range(size))
        for index, (x, y, width, height) in enumerate(pads):
            button = self.activity_button(
                str(index + 1), lambda i=index: self.choose_sequence_field(i), x, y,
                width, height=height, style=self.sequence_pad_style(index, False),
            )
            self.sequence_buttons.append(button)
            self.set_sequence_pad(button, index, False)
        self.activity_button("Neue Partie", lambda: self.start_sequence(None, self.puzzle.type_id),
                             170, 421, tags=("sequence-restart",))
        self.canvas.itemconfigure("sequence-restart", state="hidden")
        self.canvas.configure(scrollregion=(0, 0, 340, 454))
        self.update_sequence_status("Bereit · Runde 1 startet gleich")
        self.schedule_sequence(ROUND_PAUSE, lambda: self.show_sequence_step(0))

    def set_sequence_pad(self, button, index, lit):
        button.configure(style=self.sequence_pad_style(index, lit))

    def light_sequence_pad(self, index=None):
        if self.sequence_lit is not None:
            old = self.sequence_lit
            self.set_sequence_pad(self.sequence_buttons[old], old, False)
        self.sequence_lit = index
        if index is not None:
            self.set_sequence_pad(self.sequence_buttons[index], index, True)
            self.victory_sound.play(self.preferences["volume"], frequency=PADS[index].frequency, duration=.19)

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
        if step == 0:
            self.update_sequence_status(f"Schau zu · Runde {self.sequence_game.score + 1}")
        self.light_sequence_pad(self.sequence_game.pattern[step])
        self.schedule_sequence(310, lambda: self.pause_before_sequence_step(step + 1))

    def pause_before_sequence_step(self, step, delay=150):
        self.light_sequence_pad()
        self.schedule_sequence(delay, lambda: self.show_sequence_step(step))

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
            self.update_sequence_status(f"Richtig · Runde {self.sequence_game.score + 1} startet gleich")
            self.schedule_sequence(INPUT_FLASH, lambda: self.pause_before_sequence_step(0, ROUND_PAUSE - INPUT_FLASH))
        else:
            game = self.sequence_game
            self.update_sequence_status(f"Du bist dran · {game.entered} von {len(game.pattern)} Feldern")
            self.schedule_sequence(140, self.light_sequence_pad)

    def update_sequence_status(self, message, *, finished=False):
        prefix = "Erreichter Punktestand" if finished else "Punktestand"
        score = f"{prefix}: {self.sequence_game.score}"
        color = ERROR if finished else INK
        board_score = str(self.sequence_game.score) if self.puzzle.view["size"] == 2 else score
        self.canvas.itemconfigure(self.sequence_score_text, text=board_score, fill=color)
        self.canvas.itemconfigure(self.sequence_instruction, text=message, fill=color)
        self.status.configure(text=f"{score} · {message}", foreground=color)

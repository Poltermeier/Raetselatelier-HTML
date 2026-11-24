from dataclasses import dataclass
from importlib.util import find_spec
import random
import secrets
import time

from . import generators as g
from . import calendar_generators as calendar
from . import new_calendar_generators as extra
from .pouring import pouring
from .nest_tens_generators import easter_nest, tens_grid
from . import route_generators as routes
from . import logic_generators as logic
from .cats import cats
from .jump_puzzle import jump_puzzle
from .shikaku import shikaku
from .spring_generators import window_sudoku,lanterns,hitori,treasure_logic
from .contact import contact
from .maze_puzzles import arrow_maze,chess_maze
from .card_code_matches import sets_puzzle,mastermind,matchsticks
from .moving_games import solitaire,water_sort
from .freecell import freecell
from .hearts import HEARTS_LEVELS, hearts
from .mahjong import mahjong
from .line_generators import abknicker,light_rays
from .workshop_games import cryptogram,target24,circuits,row_shift
from .pentomino import pentomino
from .word_games import wortspur, buchstabenwerkstatt, wortring
from .gruppen import gruppen
from .ermittlungsakte import ermittlungsakte
from .pipes import pipes,PIPE_SIZES
from .puzzle import LogicalProofMissing
from .chess_engine import stockfish_path,stockfish_missing_message
from .new_puzzles import distance, sum_product, twiddle
from .friedman import friedman


def chess_puzzle(seed, difficulty):
    # Loading the catalog must also work before source dependencies are installed.
    from .chess_puzzle import chess_puzzle as generate_chess
    return generate_chess(seed, difficulty)


@dataclass(frozen=True)
class PuzzleType:
    id: str
    title: str
    generator: object = None
    clarification: str = ""
    dependency: str = ""

    @property
    def unavailable_reason(self):
        if self.generator is None:
            return f"{self.title}: Regeln noch offen. {self.clarification}"
        if self.dependency and find_spec(self.dependency) is None:
            return (f"{self.title} benötigt das Python-Paket '{self.dependency}'. "
                    "Im Projektordner mit demselben Python installieren:\n"
                    "python -m pip install .\nDanach das Programm neu starten. "
                    "Die übrigen Rätsel bleiben spielbar.")
        if self.id=='schachraetsel' and stockfish_path() is None:return stockfish_missing_message()
        return ""

    @property
    def available(self):
        return not self.unavailable_reason

    @property
    def availability_label(self):
        if self.available:
            return "spielbar"
        if self.id=='schachraetsel' and find_spec(self.dependency) is not None:return "Engine fehlt"
        return "Paket fehlt" if self.generator is not None else "Regeln offen"


CATALOG = [
    PuzzleType("distance", "Distance", distance),
    PuzzleType("friedman-zahlen", "Friedman Zahlen", friedman),
    PuzzleType("summe-produkt", "Summe Produkt", sum_product),
    PuzzleType("twiddle", "Twiddle", twiddle),
    PuzzleType("rechenfreude", "Rechenfreude", g.arithmetic),
    PuzzleType("perlenschnursudoku", "Perlenschnursudoku", g.pearls),
    PuzzleType("kistenguck", "Kistenguck", calendar.kistenguck),
    PuzzleType("breite-plus-hoehe", "Breite Plus Höhe", calendar.rectangles),
    PuzzleType("mein-guter-nachbar", "Mein guter Nachbar", calendar.neighbors),
    PuzzleType("binaersystem", "Binärsystem", g.binary),
    PuzzleType("beziehungskiste", "Beziehungskiste", calendar.relationship),
    PuzzleType("denk-denk", "Denk Denk", calendar.kenken),
    PuzzleType("kakuro-sudoku", "Kakuro Sudoku", calendar.kakuro),
    PuzzleType("camping", "Camping", g.camping),
    PuzzleType("kropki-sudoku", "Kropki Sudoku", g.kropki),
    PuzzleType("windrose", "Windrose", calendar.windrose),
    PuzzleType("rinjin-sudoku", "Rinjin-Sudoku", calendar.rinjin),
    PuzzleType("nonogramm", "Nonogramm", g.nonogram),
    PuzzleType("bienensudoku", "Bienensudoku", calendar.bees),
    PuzzleType("pontifex-hashikake", "Pontifex Hashikake", g.hashi),
    PuzzleType("kombinationsschloss", "Kombinationsschloss", calendar.combination_lock),
    PuzzleType("denk-denk-pyramide", "Denk Denk Pyramide", calendar.pyramid),
    PuzzleType("crossie", "Crossie", calendar.crossie),
    PuzzleType("formen-sudoku", "Formen Sudoku", calendar.jigsaw),
    PuzzleType("hidato", "Hidato", g.hidato),
    PuzzleType("lauter-einser-und-zweier-5x5", "Lauter Einser und Zweier 5x5", calendar.ones_twos),
    PuzzleType("lauter-einser-und-zweier-6x6", "Lauter Einser und Zweier 6x6", calendar.ones_twos_6),
    PuzzleType('mini-sudoku', 'Mini-Sudoku', extra.mini_sudoku),
    PuzzleType('strassen', 'Straßen', extra.streets),
    PuzzleType('kaesekaestchen', 'Käsekästchen', extra.cheese),
    PuzzleType('tuer-an-tuer-sudoku', 'Tür an Tür – Sudoku X', extra.doors),
    PuzzleType('von-1-bis-9', 'Von 1 bis 9', extra.one_to_nine),
    PuzzleType('optimal-umgefuellt', 'Optimal umgefüllt', pouring),
    PuzzleType('osternest-sudoku', 'Osternest Sudoku', easter_nest),
    PuzzleType('zehnergitter', 'Zehnergitter', tens_grid),
    PuzzleType('slitherlink', 'Slitherlink', routes.slitherlink),
    PuzzleType('killer-sudoku', 'Killer-Sudoku', logic.killer_sudoku),
    PuzzleType('numberlink', 'Numberlink', routes.numberlink),
    PuzzleType('country-road', 'Country Road', routes.country_road),
    PuzzleType('minesweeper', 'Minesweeper', logic.minesweeper),
    PuzzleType('ripple-effect', 'Ripple Effect', logic.ripple_effect),
    PuzzleType('katzensuche', 'Katzensuche', cats),
    PuzzleType('logic-equations', 'Logic Equations', logic.logic_equations),
    PuzzleType('jump-puzzle', 'Jump Puzzle', jump_puzzle),
    PuzzleType('schachraetsel', 'Schachrätsel', chess_puzzle, dependency='chess'),
    PuzzleType('shikaku', 'Shikaku', shikaku),
    PuzzleType("suguru", "Suguru", g.suguru),
    PuzzleType("tatami", "Tatami", calendar.tatami),
    PuzzleType("kontakt", "Kontakt", contact),
    PuzzleType("fensterkreuz-sudoku", "Fensterkreuz Sudoku X", window_sudoku),
    PuzzleType("leo-laternenmann", "Leo Laternenmann", lanterns),
    PuzzleType("hitori", "Hitori", hitori),
    PuzzleType("schatzkisten-logik", "Schatzkisten-Logik", treasure_logic),
    PuzzleType("pfeil-labyrinth", "Pfeil-Labyrinth", arrow_maze),
    PuzzleType("schach-labyrinth", "Schach-Labyrinth", chess_maze),
    PuzzleType("sets", "Sets", sets_puzzle),
    PuzzleType("superhirn", "Superhirn", mastermind),
    PuzzleType("solitaer", "Solitär", solitaire),
    PuzzleType("freecell", "FreeCell", freecell),
    PuzzleType("hearts", "Hearts", hearts),
    PuzzleType("mahjong", "Mahjong", mahjong),
    PuzzleType("streichholzraetsel", "Streichholzrätsel", matchsticks),
    PuzzleType("water-sort", "Water Sort", water_sort),
    PuzzleType("abknicker", "Abknicker", abknicker),
    PuzzleType("lichtstrahl", "Lichtstrahl", light_rays),
    PuzzleType('kryptogramm','Kryptogramm',cryptogram),
    PuzzleType('vier-zahlen-ein-ziel','Vier Zahlen – ein Ziel',target24),
    PuzzleType('logikschaltungen','Logikschaltungen',circuits),
    PuzzleType('pentomino-puzzle','Pentomino Puzzle',pentomino),
    PuzzleType('row-shift','Row Shift',row_shift),
    PuzzleType('pipes','Pipes',pipes),
    PuzzleType('wortspur', 'Wordle', wortspur),
    PuzzleType('buchstabenwerkstatt', 'Spelling Bee', buchstabenwerkstatt),
    PuzzleType('wortring', 'Wortring', wortring),
    PuzzleType('gruppen', 'Gruppen', gruppen),
    PuzzleType('ermittlungsakte', 'Ermittlungsakte', ermittlungsakte),
]
BY_ID = {p.id: p for p in CATALOG}
BY_ID["wordle"] = BY_ID["wortspur"]
BY_ID["spelling-bee"] = BY_ID["buchstabenwerkstatt"]
# Keep older command lines and exported type IDs usable.
BY_ID["katzenraetsel"] = BY_ID["katzensuche"]
BY_ID["rechenfreunde"] = BY_ID["rechenfreude"]
BY_ID['lauter-einser-und-zweier'] = BY_ID['lauter-einser-und-zweier-5x5']


def generate(type_id="random", seed=None, difficulty="schwer", *, size=None):
    levels = HEARTS_LEVELS if type_id == "hearts" else ("mittel", "schwer")
    if difficulty not in levels:
        raise ValueError("Schwierigkeit muss eine der folgenden Stufen sein: " + ", ".join(levels))
    if seed is None:
        seed = secrets.randbits(48)
    if type(seed) is not int:
        raise ValueError("Seed muss eine ganze Zahl sein")
    if type_id == "random":
        # Only playable types; pending rules must never produce a different puzzle.
        type_id = random.Random(seed).choice([p.id for p in CATALOG if p.available and p.id != 'hearts'])
    if type_id not in BY_ID:
        raise ValueError(f"Unbekannter Rätseltyp: {type_id}")
    item = BY_ID[type_id]
    if size is not None:
        valid=type(size) is int and (item.id=='katzensuche' and 4<=size<=10 or item.id=='pipes' and size in PIPE_SIZES)
        if not valid:raise ValueError('Größenauswahl: Katzensuche 4–10; Pipes 4, 5, 7, 10, 12, 15 oder 20')
    if not item.available:
        raise ValueError(item.unavailable_reason)
    retries = random.Random(seed)
    deadline = time.monotonic()+20
    for attempt in range(32):
        candidate_seed = seed if attempt == 0 else retries.getrandbits(48)
        try:
            puzzle = item.generator(candidate_seed, difficulty, size=size) if size is not None else item.generator(candidate_seed, difficulty)
        except LogicalProofMissing:
            if time.monotonic() > deadline:
                break
            continue
        puzzle.seed = seed
        puzzle.analysis.update(generation_attempts=attempt+1, generation_seed=candidate_seed)
        return puzzle
    raise ValueError(f"{item.title}: Kein Rätsel mit vollständigem Lösungsweg ohne Raten im Versuchslimit gefunden")

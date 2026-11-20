"""Build four disjoint groups from German theme vocabularies."""
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from itertools import combinations
import json
import random

from .puzzle import LogicalProofMissing, Puzzle
from .solver import Model
from .word_games import lexicon

MODE = "gruppen"

# A board should not use overlapping broad domains such as Tiere and Vögel.
RELATED_THEMES = (
    frozenset(("Tiere", "Vögel", "Insekten", "Hunderassen", "Pferderassen", "Schmetterlinge", "Vogelarten am Wasser")),
    frozenset(("Bäume und Blumen", "Im Garten", "Obst und Gemüse", "Gewürze und Küchenkräuter", "Baumfrüchte", "Baumarten")),
    frozenset(("Backwaren und Gebäck", "Kuchen und Torten", "Entsteht in der Bäckerei", "Weihnachtsgebäck")),
    frozenset(("Getränke", "Heiße Getränke")),
    frozenset(("Küche und Tisch", "Geschirr und Besteck", "Küchengeräte")),
    frozenset(("Wetter und Himmel", "Naturgewalten")),
    frozenset(("Weltraum und Astronomie", "Im Weltall", "Planeten", "Raumfahrt")),
    frozenset(("Landschaften und Gewässer", "Küstenformen", "Deutsche Flüsse", "Große Seen im Alpenraum",
               "Ostseeinseln", "Inseln im Mittelmeer")),
    frozenset(("Werkzeug und Werkstatt", "Werkzeuge zum Schneiden", "Handarbeiten und Basteln", "Technik im Alltag")),
    frozenset(("Sport und Bewegung", "Wintersportarten", "Sommersportarten", "Disziplinen der Leichtathletik",
               "Kampfsportarten", "Mannschaftssport")),
)


@dataclass
class GruppenPuzzle(Puzzle):
    groups: tuple[tuple[str, tuple[str, ...]], ...] = ()

    def check_group(self, words):
        selected = frozenset(words)
        return next((i for i, (_, group) in enumerate(self.groups) if selected == frozenset(group)), None)

    def export(self, include_solution=False):
        data = super().export(include_solution)
        if include_solution:
            data["solution"] = [{"Thema": theme, "Wörter": list(words)} for theme, words in self.groups]
        return data


@lru_cache(maxsize=2)
def theme_bank(difficulty):
    filename = "gruppen.json" if difficulty == "schwer" else "gruppen_mittel.json"
    path = files("raetselkalender").joinpath("data", filename)
    themes = json.loads(path.read_text(encoding="utf-8"))
    if difficulty == "mittel":
        themes = lexicon().themes | themes
    return {theme: tuple(sorted({word.capitalize() for word in words if len(word) <= 13}))
            for theme, words in themes.items()}


@lru_cache(maxsize=1)
def overlapping_themes():
    bank = theme_bank("schwer")
    members = {theme: set(words) for theme, words in bank.items()}
    options = {}
    for first, words in members.items():
        partners = [(second, tuple(sorted(words & other))) for second, other in members.items()
                    if first != second and words & other and len(other - words) >= 3]
        if partners:
            options[first] = partners
    return options


@lru_cache(maxsize=1)
def partition_bank():
    return theme_bank("mittel") | theme_bank("schwer")


def partition_count(words, bank):
    """Count catalogued covers up to two, using at most one group for each theme."""
    bits = {word: 1 << i for i, word in enumerate(words)}
    choices = {bit: [] for bit in bits.values()}
    for index, members in enumerate(bank.values()):
        for group in combinations((bits[word] for word in members if word in bits), 4):
            entry = (sum(group), 1 << index)
            for bit in group:
                choices[bit].append(entry)

    partitions = set()

    def covers(remaining, used_themes, groups):
        if not remaining:
            partitions.add(frozenset(groups))
            return
        for group, theme in choices[remaining & -remaining]:
            if group & remaining == group and not used_themes & theme:
                covers(remaining ^ group, used_themes | theme, (*groups, group))
                if len(partitions) >= 2:
                    return

    covers((1 << len(words)) - 1, 0, ())
    return len(partitions)


def gruppen(seed, difficulty):
    rng = random.Random(seed)
    bank = theme_bank(difficulty)
    names = tuple(bank)
    for _ in range(128):
        shared = None
        if difficulty == "schwer":
            options = overlapping_themes()
            first = rng.choice(tuple(options))
            second, overlap = rng.choice(options[first])
            shared = rng.choice(overlap)
            chosen = [first, second, *rng.sample([name for name in names if name not in (first, second)], 2)]
        else:
            chosen = rng.sample(names, 4)
            if any(len(family.intersection(chosen)) > 1 for family in RELATED_THEMES):
                continue

        used = set()
        groups = []
        for index, theme in enumerate(chosen):
            fixed = (shared,) if index == 0 and shared else ()
            available = [word for word in bank[theme] if word not in used and word not in fixed]
            if len(available) < 4 - len(fixed):
                break
            members = tuple(sorted((*fixed, *rng.sample(available, 4 - len(fixed)))))
            used.update(members)
            groups.append((theme, members))
        if len(groups) != 4:
            continue
        words = sorted(used)
        if partition_count(words, partition_bank()) != 1:
            continue
        rng.shuffle(words)
        return GruppenPuzzle(MODE, "Gruppen",
            "Finde vier Gruppen aus je vier zusammengehörenden Wörtern. Wähle vier Felder und prüfe die Gruppe. "
            "Jedes Wort gehört genau zu einer Gruppe. Auf Schwer können Wörter zunächst zu mehreren Themen passen.",
            Model({}, []), {}, {}, dict(kind="activity", mode=MODE, words=words), seed, difficulty,
            analysis=dict(unique=True, uniqueness_scope="theme_catalog"), groups=tuple(groups))
    raise LogicalProofMissing("Keine eindeutige Zusammenstellung aus vier Gruppen gefunden.")

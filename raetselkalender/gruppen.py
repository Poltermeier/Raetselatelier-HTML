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
    frozenset(("Tiere", "Vögel", "Insekten")),
    frozenset(("Bäume und Blumen", "Im Garten", "Obst und Gemüse", "Gewürze und Küchenkräuter")),
    frozenset(("Backwaren und Gebäck", "Getränke", "Küche und Tisch")),
    frozenset(("Wetter und Himmel", "Weltraum und Astronomie")),
    frozenset(("Landschaften und Gewässer", "Gesteine und Mineralien")),
    frozenset(("Werkzeug und Werkstatt", "Handarbeiten und Basteln", "Technik im Alltag")),
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
    if difficulty == "schwer":
        path = files("raetselkalender").joinpath("data", "gruppen.json")
        themes = json.loads(path.read_text(encoding="utf-8"))
    else:
        themes = lexicon().themes
    return {theme: tuple(sorted(word.capitalize() for word in words if len(word) <= 13))
            for theme, words in themes.items()}


@lru_cache(maxsize=1)
def overlapping_themes():
    bank = theme_bank("schwer")
    return tuple((first, second, tuple(sorted(set(words).intersection(other))))
                 for first, words in bank.items() for second, other in bank.items()
                 if first != second and len(set(other).difference(words)) >= 3
                 and set(words).intersection(other))


def partition_count(words, bank):
    """Count catalogued covers up to two, using at most one group for each theme."""
    bits = {word: 1 << i for i, word in enumerate(words)}
    choices = {bit: [] for bit in bits.values()}
    for index, members in enumerate(bank.values()):
        for group in combinations((bits[word] for word in members if word in bits), 4):
            entry = (sum(group), 1 << index)
            for bit in group:
                choices[bit].append(entry)

    def covers(remaining, used_themes):
        if not remaining:
            return 1
        result = 0
        for group, theme in choices[remaining & -remaining]:
            if group & remaining == group and not used_themes & theme:
                result += covers(remaining ^ group, used_themes | theme)
                if result >= 2:
                    return 2
        return result

    return covers((1 << len(words)) - 1, 0)


def gruppen(seed, difficulty):
    rng = random.Random(seed)
    bank = theme_bank(difficulty)
    names = tuple(bank)
    for _ in range(128):
        shared = None
        if difficulty == "schwer":
            first, second, overlap = rng.choice(overlapping_themes())
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
        if partition_count(words, bank) != 1:
            continue
        rng.shuffle(words)
        return GruppenPuzzle(MODE, "Gruppen",
            "Finde vier Gruppen aus je vier zusammengehörenden Wörtern. Wähle vier Felder und prüfe die Gruppe. "
            "Jedes Wort gehört genau zu einer Gruppe. Auf Schwer können Wörter zunächst zu mehreren Themen passen.",
            Model({}, []), {}, {}, dict(kind="activity", mode=MODE, words=words), seed, difficulty,
            analysis=dict(unique=True, uniqueness_scope="theme_catalog"), groups=tuple(groups))
    raise LogicalProofMissing("Keine eindeutige Zusammenstellung aus vier Gruppen gefunden.")

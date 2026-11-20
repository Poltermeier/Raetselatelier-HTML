"""Seeded German word puzzles using the bundled open-licensed lexicon."""
from collections import Counter
from functools import lru_cache
from importlib.resources import files
import json
import random
import unicodedata

from .puzzle import Puzzle
from .solver import Model

WORD_MODES = ("wortspur", "buchstabenwerkstatt", "wortring")
ALPHABET = "abcdefghijklmnopqrstuvwxyzäöüß"
BITS = {letter: 1 << i for i, letter in enumerate(ALPHABET)}


def normalize_word(text):
    return unicodedata.normalize("NFC", text.strip()).lower()


def display_word(word):
    return word.replace("ß", "ẞ").upper()


@lru_cache(maxsize=1)
def lexicon():
    path = files("raetselkalender").joinpath("data", "german_words.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    return frozenset(data["words"]), tuple((theme, tuple(words)) for theme, words in data["themes"].items())


def letter_mask(word):
    return sum(BITS[letter] for letter in set(word))


@lru_cache(maxsize=1)
def workshop_lexicon():
    words, _ = lexicon()
    indexed = tuple((word, letter_mask(word)) for word in sorted(words)
                    if len(word) <= 9 and len(set(word)) == len(word))
    vowels = letter_mask("aeiouäöü")
    masks = tuple(sorted({mask for word, mask in indexed
                          if len(word) == 9 and (mask & vowels).bit_count() >= 2}))
    return indexed, masks


def word_feedback(guess, target):
    """Reserve exact matches before counting misplaced repeated letters."""
    remaining = Counter(answer for proposed, answer in zip(guess, target) if proposed != answer)
    result = []
    for proposed, answer in zip(guess, target):
        if proposed == answer:
            result.append("exact")
        elif remaining[proposed]:
            result.append("present")
            remaining[proposed] -= 1
        else:
            result.append("absent")
    return tuple(result)


def ring_readings(letters):
    count = len(letters)
    return {''.join(letters[(start + step * i) % count] for i in range(count))
            for start in range(count) for step in (-1, 1)}


@lru_cache(maxsize=2)
def ring_candidates(difficulty):
    _, themes = lexicon()
    lower, upper = (4, 10) if difficulty == "mittel" else (11, 16)
    return tuple((theme, word) for theme, words in themes for word in words
                 if lower <= len(word) <= upper and ring_readings(word).intersection(words) == {word})


class WordPuzzle(Puzzle):
    def word_error(self, word):
        view = self.view
        mode = view["mode"]
        if mode == "buchstabenwerkstatt":
            maximum = len(view["letters"])
            if not view["minimum"] <= len(word) <= maximum:
                return f"Das Wort braucht zwischen {view['minimum']} und {maximum} Buchstaben."
            if not set(word) <= set(view["letters"]):
                return "Verwende nur die angezeigten Buchstaben."
            if len(set(word)) != len(word):
                return "Verwende jeden Buchstaben im Wort höchstens einmal."
            if view["required"] not in word:
                return f"{display_word(view['required'])} muss im Wort vorkommen."
            if word not in self.answer_words:
                return "Dieses Wort steht nicht im deutschen Spielwortschatz."
        elif len(word) != view["length"]:
            return f"Das Wort braucht genau {view['length']} Buchstaben."
        elif mode == "wortspur":
            if word not in lexicon()[0]:
                return "Dieses Wort steht nicht im deutschen Spielwortschatz."
        elif word != self.answer_words[0]:
            if word not in ring_readings(view["letters"]):
                return "Lies den ganzen Ring in einer Richtung, ohne einen Buchstaben zu überspringen."
            return "Diese Lesart passt nicht zum Thema."
        return ""

    def is_solved(self, words):
        if self.view["mode"] == "buchstabenwerkstatt":
            return len(set(words)) >= self.view["goal"]
        return bool(words and words[-1] == self.answer_words[0])

    def export(self, include_solution=False):
        data = super().export(include_solution)
        if include_solution:
            data["solution"] = {"Wörter": list(self.answer_words)}
            if self.view["mode"] == "wortring":
                data["solution"].update(Startfeld=self.ring_start + 1, Richtung=self.ring_direction)
        return data


def make_word_puzzle(mode, title, rules, seed, difficulty, answers, **view):
    puzzle = WordPuzzle(mode, title, rules, Model({}, []), {}, {},
                        dict(kind="activity", mode=mode, **view), seed, difficulty,
                        analysis=dict(unique=mode != "buchstabenwerkstatt", logical_solvable=False, word_list_checked=True))
    puzzle.answer_words = tuple(answers)
    return puzzle


def wortspur(seed, difficulty):
    rng = random.Random(seed)
    length, attempts = (5, 6) if difficulty == "mittel" else (6, 5)
    _, themes = lexicon()
    word = rng.choice([word for _, words in themes for word in words if len(word) == length])
    return make_word_puzzle("wortspur", "Wordle",
        f"Errate das deutsche Wort mit {length} Buchstaben in {attempts} Versuchen. "
        "Zu jedem Buchstaben erfährst du, ob er richtig steht, an anderer Stelle vorkommt oder fehlt. "
        "Ä, Ö, Ü und ß zählen als eigene Buchstaben.",
        seed, difficulty, (word,), length=length, attempts=attempts)


def buchstabenwerkstatt(seed, difficulty):
    rng = random.Random(seed)
    minimum, goal = (4, 8) if difficulty == "mittel" else (5, 12)
    indexed, masks = workshop_lexicon()
    for mask in rng.sample(masks, len(masks)):
        answers = tuple(word for word, bits in indexed if len(word) >= minimum and bits & mask == bits)
        letters = [letter for letter in ALPHABET if BITS[letter] & mask]
        required = [letter for letter in letters if sum(letter in word for word in answers) >= goal + 8]
        if required:
            mandatory = rng.choice(required)
            rng.shuffle(letters)
            return make_word_puzzle("buchstabenwerkstatt", "Spelling Bee",
                f"Finde {goal} verschiedene deutsche Wörter mit mindestens {minimum} Buchstaben. "
                "Verwende die neun angezeigten Buchstaben. Der Pflichtbuchstabe in der Mitte gehört in jedes Wort. "
                "Jeder Buchstabe darf pro Wort höchstens einmal vorkommen.",
                seed, difficulty, (word for word in answers if mandatory in word),
                letters=letters, required=mandatory, minimum=minimum, goal=goal)
    raise ValueError("Für diesen Seed konnte keine ausreichend ergiebige Buchstabenauswahl erzeugt werden.")


def wortring(seed, difficulty):
    rng = random.Random(seed)
    theme, word = rng.choice(ring_candidates(difficulty))
    count = len(word)
    start = rng.randrange(count)
    direction = rng.choice((1, -1))
    letters = [""] * count
    for i, letter in enumerate(word):
        letters[(start + i * direction) % count] = letter
    puzzle = make_word_puzzle("wortring", "Wortring",
        "Der Hinweis nennt das Thema des gesuchten Wortes. Beginne bei einem beliebigen Buchstaben. "
        "Lies den Ring im oder gegen den Uhrzeigersinn und verwende jedes Feld genau einmal. "
        "Tippe das Wort ein oder wähle die Buchstaben nacheinander im Ring.",
        seed, difficulty, (word,), theme=theme, length=count, letters=letters)
    puzzle.ring_start = start
    puzzle.ring_direction = direction
    return puzzle

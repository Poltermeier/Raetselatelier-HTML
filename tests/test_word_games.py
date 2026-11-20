import unittest

from raetselkalender.catalog import generate
from raetselkalender.word_games import lexicon, normalize_word, ring_readings, word_feedback


class GermanWordGames(unittest.TestCase):
    def test_duplicate_feedback_reserves_correct_positions(self):
        self.assertEqual(
            word_feedback("tasse", "tanne"),
            ("exact", "exact", "absent", "absent", "exact"),
        )
        self.assertEqual(word_feedback("aab", "baa"), ("present", "exact", "present"))
        self.assertEqual(normalize_word("  GROẞE ÄHRE  "), "große ähre")

    def test_word_trail_has_valid_targets_in_both_lengths(self):
        words, _ = lexicon()
        for difficulty, length in (("mittel", 5), ("schwer", 6)):
            puzzle = generate("wortspur", 42, difficulty)
            answer = puzzle.answer_words[0]
            self.assertEqual(len(answer), length)
            self.assertIn(answer, words)
            self.assertEqual(puzzle.word_error(answer), "")
            self.assertTrue(puzzle.is_solved([answer]))
            self.assertNotIn("solution", puzzle.export())

    def test_workshop_requires_dictionary_letters_and_distinct_words(self):
        for difficulty in ("mittel", "schwer"):
            for seed in (0, 1, 42, 31415, 65535):
                puzzle = generate("buchstabenwerkstatt", seed, difficulty)
                view = puzzle.view
                self.assertEqual(len(set(view["letters"])), 8)
                self.assertGreaterEqual(len(puzzle.answer_words), view["goal"] + 12)
                self.assertTrue(all(not puzzle.word_error(word) for word in puzzle.answer_words))
                self.assertTrue(puzzle.word_error("zzz"))
                self.assertFalse(puzzle.is_solved([puzzle.answer_words[0]] * view["goal"]))
                self.assertTrue(puzzle.is_solved(list(puzzle.answer_words[:view["goal"]])))

    def test_ring_replays_every_position_in_either_direction(self):
        _, themes = lexicon()
        themes = dict(themes)
        seen = set()
        for seed in range(20):
            for difficulty in ("mittel", "schwer"):
                puzzle = generate("wortring", seed, difficulty)
                letters = puzzle.view["letters"]
                directions = puzzle.ring_direction
                indexes = [(puzzle.ring_start + directions * i) % len(letters) for i in range(len(letters))]
                expected = "".join(letters[i] for i in indexes)
                self.assertEqual(len(set(indexes)), len(letters))
                self.assertEqual(puzzle.answer_words, (expected,))
                self.assertEqual(ring_readings(letters).intersection(themes[puzzle.view["theme"]]), {expected})
                self.assertEqual(puzzle.word_error(expected), "")
                self.assertTrue(puzzle.word_error(expected + expected[0]))
                other = next(word for word in ring_readings(letters) if word != expected)
                self.assertTrue(puzzle.word_error(other))
                self.assertNotIn("Startfeld", puzzle.export())
                self.assertEqual(puzzle.export(True)["solution"]["Startfeld"], puzzle.ring_start + 1)
                seen.add(directions)
        self.assertEqual(seen, {-1, 1})

import unittest
from io import BytesIO
import struct
import wave

from raetselkalender.preferences import sound_wave
from raetselkalender.sequence_game import ColorSequence
from raetselkalender.sequence_ui import PADS


class SequenceGameTests(unittest.TestCase):
    def test_scoring_grows_only_for_completed_patterns_and_survives_loss(self):
        for count in (4, 9):
            game = ColorSequence(33, count)
            for round_number in range(1, 12):
                expected = tuple(game.pattern)
                self.assertEqual(len(expected), round_number)
                for field in expected[:-1]:
                    self.assertEqual(game.choose(field), "continue")
                    self.assertEqual(game.score, round_number - 1)
                self.assertEqual(game.choose(expected[-1]), "round")
                self.assertEqual(game.score, round_number)
                self.assertEqual(tuple(game.pattern[:-1]), expected)
                self.assertTrue(0 <= game.pattern[-1] < count)
            self.assertEqual(game.choose((game.pattern[0] + 1) % count), "lost")
            self.assertTrue(game.finished)
            self.assertEqual(game.score, 11)
            self.assertIsNone(game.choose(game.pattern[0]))
            self.assertEqual(game.score, 11)

    def test_each_pad_has_its_own_pitch_and_pcm_responds_to_volume(self):
        pitches = {pad.frequency for pad in PADS}
        self.assertEqual(len(pitches), 9)
        notes = ((PADS[0].frequency, .19),)

        def peak(volume):
            with wave.open(BytesIO(sound_wave(volume, notes)), "rb") as audio:
                return max(abs(value) for value, in struct.iter_unpack("<h", audio.readframes(audio.getnframes())))

        self.assertEqual(peak(0), 0)
        self.assertGreater(peak(20), 0)
        self.assertGreater(peak(80), 3 * peak(20))

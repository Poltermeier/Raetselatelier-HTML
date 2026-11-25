"""State for a growing sequence of color cues."""
from random import Random


class ColorSequence:
    def __init__(self, seed, field_count):
        self.random = Random(seed)
        self.field_count = field_count
        self.pattern = [self.random.randrange(field_count)]
        self.entered = 0
        self.score = 0
        self.finished = False

    def choose(self, field):
        if self.finished or type(field) is not int or not 0 <= field < self.field_count:
            return
        if self.pattern[self.entered] != field:
            self.finished = True
            return "lost"
        self.entered += 1
        if self.entered < len(self.pattern):
            return "continue"
        self.score += 1
        self.entered = 0
        self.pattern.append(self.random.randrange(self.field_count))
        return "round"

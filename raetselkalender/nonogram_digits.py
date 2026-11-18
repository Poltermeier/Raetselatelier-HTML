"""Five-pixel-high digits with an empty column between neighboring digits.

The 10-column calendar format needs at least one narrow glyph (1 or 7).
Only triplets which fit with both separators are used; glyphs are never squeezed
or joined together just to force an arbitrary code into the diagram.
"""

DIGITS = {
    "0": ("111", "101", "101", "101", "111"),
    "1": ("1", "1", "1", "1", "1"),
    "2": ("111", "001", "111", "100", "111"),
    "3": ("111", "001", "111", "001", "111"),
    "4": ("101", "101", "111", "001", "001"),
    "5": ("111", "100", "111", "001", "111"),
    "6": ("111", "100", "111", "101", "111"),
    "7": ("11", "01", "01", "01", "01"),
    "8": ("111", "101", "111", "101", "111"),
    "9": ("111", "101", "111", "001", "111"),
}


def digit_bitmap(code):
    if len(code) != 3 or any(char not in DIGITS for char in code):
        raise ValueError("Das Nonogramm-Ergebnis muss aus genau drei Ziffern bestehen")
    width = sum(len(DIGITS[digit][0]) for digit in code)+2
    if width > 10:
        raise ValueError("Diese Ziffernfolge passt mit Zwischenräumen nicht in zehn Spalten")
    left = (10-width)//2
    return [tuple(map(int, "0"*left+"0".join(DIGITS[digit][r] for digit in code)+"0"*(10-width-left)))
            for r in range(5)]

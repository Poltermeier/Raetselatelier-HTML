"""Derive verified expressions from OEIS A080035 (https://oeis.org/A080035).

Run with the A080035 b-file as the first argument.
"""
from functools import lru_cache
from fractions import Fraction
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from raetselkalender.friedman import bounded, evaluate_friedman, power


@lru_cache(maxsize=2048)
def expressions(digits):
    values = {}
    if len(digits) == 1 or digits[0] != "0":
        number = Fraction(digits)
        values[number] = digits
        values[-number] = "-" + digits if number else digits
    for split in range(1, len(digits)):
        for a, left in expressions(digits[:split]).items():
            for b, right in expressions(digits[split:]).items():
                candidates = [(a+b, "+"), (a-b, "-"), (a*b, "*")]
                if b:
                    candidates.append((a/b, "/"))
                try:
                    candidates.append((power(a, b), "^"))
                except (ValueError, ZeroDivisionError):
                    pass
                for value, op in candidates:
                    if value not in values and bounded(value):
                        expression = f"({left}){op}({right})"
                        values[value] = f"({expression})"
                        values.setdefault(-value, f"-({expression})")
    return values


def witness(number):
    digits = str(number)
    goal = Fraction(number)
    for split in range(1, len(digits)):
        left = expressions(digits[:split])
        right = expressions(digits[split:])
        for target, negate in ((goal, ""), (-goal, "-")):
            for a, a_text in left.items():
                needed = [(target-a, "+"), (a-target, "-")]
                if a:
                    needed.extend(((target/a, "*"), (a/target, "/")))
                for b, op in needed:
                    if b in right and (op != "/" or b):
                        return f"{negate}(({a_text}){op}({right[b]}))"
                for b, b_text in right.items():
                    if b.denominator != 1 or not 1 <= abs(b) <= 128:
                        continue
                    if a and power(a, b) == target:
                        return f"{negate}(({a_text})^({b_text}))"
    return None


def compact(expression):
    previous = None
    while previous != expression:
        previous = expression
        expression = re.sub(r"\(([0-9]+)\)", r"\1", expression)
        expression = re.sub(r"\(\(([^()]*)\)\)", r"(\1)", expression)
    return expression


if __name__ == "__main__":
    numbers = [int(row.split()[1]) for row in Path(sys.argv[1]).read_text().splitlines()
               if row.strip() and not row.startswith("#")]
    results = []
    for number in numbers:
        expression = witness(number)
        if expression:
            expression = compact(expression)
            assert evaluate_friedman(expression, number) == number
            results.append((number, expression))
    path = ROOT / "raetselkalender/data/friedman.json"
    path.write_text(json.dumps(results, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"{len(results)} / {len(numbers)} expressions verified.")

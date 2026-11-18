"""Calendar equations with repeated symbols and all four operations."""
from itertools import permutations

from .solver import Table


def expression_value(expression, values):
    """Evaluate generated tokens with precedence and exact division only.

    Tokens alternate symbol names and operators; there is no executable input.
    A nonintegral quotient makes an assignment inadmissible.
    """
    tokens = expression.split()
    total, sign, term = 0, 1, values[tokens[0]]
    for operator, key in zip(tokens[1::2], tokens[2::2]):
        value = values[key]
        if operator == "×":
            term *= value
        elif operator == ":":
            if term % value:
                return None
            term //= value
        elif operator in ("+", "-"):
            total += sign*term
            sign, term = (1 if operator == "+" else -1), value
        else:
            raise ValueError(f"Unbekannte Rechenoperation: {operator}")
    return total+sign*term


def expression_table(expression, total):
    keys = tuple(dict.fromkeys(expression.split()[::2]))
    rows = tuple(row for row in permutations(range(1, 10), len(keys))
                 if expression_value(expression, dict(zip(keys, row))) == total)
    return Table(keys, rows)


def result_table(expression, symbols):
    rows = []
    for row in permutations(range(1, 10), len(symbols)):
        result = expression_value(expression, dict(zip(symbols, row)))
        if result is not None and result > 0:
            rows.append(row+(result,))
    return Table(symbols+("Ergebnis",), tuple(rows))


def formula_signature(expression):
    """Normalize additive term order; reject cancelling or trivial terms."""
    tokens = expression.split()
    terms, sign, factors, divisors = [], 1, [tokens[0]], []
    for op, key in zip(tokens[1::2], tokens[2::2]):
        if op in ("+", "-"):
            terms.append((sign, tuple(sorted(factors)), tuple(sorted(divisors))))
            sign, factors, divisors = (1 if op == "+" else -1), [key], []
        elif op == "×":
            factors.append(key)
        else:
            divisors.append(key)
    terms.append((sign, tuple(sorted(factors)), tuple(sorted(divisors))))
    if any(set(a) & set(b) for sign, a, b in terms):
        return None
    if any((-sign, a, b) in terms for sign, a, b in terms):
        return None
    return tuple(sorted(terms))


def varied_equations(symbols, rng):
    """Select four independent, varied clues by enumerating all assignments.

    No fixed equation templates: operands, repetitions, operations and order
    are sampled afresh. Each clue must be necessary for a unique solution.
    """
    assignments = [dict(zip(symbols, row)) for row in permutations(range(1, 10), 4)]

    def draw(source, required=None, final=False):
        operands = rng.sample(symbols, 4) if final else rng.choices(symbols, k=rng.choice((3, 4)))
        if len(set(operands)) < 2:
            return None
        operators = rng.choices(("+", "-", "×", ":"), weights=(3, 2, 2, 1), k=len(operands)-1)
        if required and required not in operators:
            return None
        if final and len(set(operators)) < 2:
            return None
        if any(op == ":" and source[key] == 1 for op, key in zip(operators, operands[1:])):
            return None
        expression = operands[0]+"".join(f" {op} {key}" for op, key in zip(operators, operands[1:]))
        signature = formula_signature(expression)
        value = expression_value(expression, source)
        if signature is None or value is None or not 1 <= value <= 99:
            return None
        return expression, value, signature

    for _ in range(300):
        source = rng.choice(assignments)
        if not any(source[a] > source[b] > 1 and source[a] % source[b] == 0
                   for a in symbols for b in symbols):
            continue
        remaining = assignments
        required = rng.sample(("+", "-", "×", ":"), 4)
        clues, signatures, supports = [], set(), []
        for stage in range(4):
            for _ in range(600):
                candidate = draw(source, required[stage])
                if candidate is None:
                    continue
                expression, value, signature = candidate
                if signature in signatures:
                    continue
                survivors = [row for row in remaining if expression_value(expression, row) == value]
                minimum = (100, 16, 3, 1)[stage]
                if not minimum <= len(survivors) < len(remaining) or (stage == 3 and len(survivors) != 1):
                    continue
                allowed = {i for i, row in enumerate(assignments) if expression_value(expression, row) == value}
                # Keep a witness for every earlier clue. A later clue must not
                # make an earlier one redundant, even before the system is unique.
                if any(not (set.intersection(allowed, *(s for j, s in enumerate(supports) if j != i))-support)
                       for i, support in enumerate(supports)):
                    continue
                supports.append(allowed)
                clues.append((expression, value))
                signatures.add(signature)
                remaining = survivors
                break
            else:
                break
        if len(clues) != 4 or not any(len(set(expr.split()[::2])) < len(expr.split()[::2]) for expr, _ in clues):
            continue
        for _ in range(600):
            candidate = draw(source, final=True)
            if candidate is not None and candidate[2] not in signatures:
                return clues, source.copy(), candidate[0]
    raise ValueError("Keine abwechslungsreiche eindeutige Rechenfreude im Versuchslimit gefunden")

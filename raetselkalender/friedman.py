"""Ordered Friedman numbers checked with exact arithmetic and no code execution."""
import ast
from fractions import Fraction
from functools import lru_cache
from importlib.resources import files
import json
import random
import re

from .puzzle import Puzzle
from .solver import Model

INTERMEDIATE_LIMIT = 1 << 64


def bounded(value):
    return abs(value.numerator) <= INTERMEDIATE_LIMIT and value.denominator <= INTERMEDIATE_LIMIT


def power(base, exponent):
    if exponent.denominator != 1 or abs(exponent) > 128 or (not base and not exponent):
        raise ValueError("Verwende ganzzahlige Exponenten und lass 0⁰ weg.")
    return base ** int(exponent)


def evaluate_friedman(expression, number):
    text = expression.translate(str.maketrans("−×÷", "-*/")).replace("^", "**").strip()
    if len(text) > 128 or not re.fullmatch(r"[0-9()+*/\-\s]+", text):
        raise ValueError("Verwende Ziffern, +, −, ×, /, ^ und Klammern.")
    if "".join(re.findall(r"[0-9]", text)) != str(number):
        raise ValueError(f"Verwende die Ziffern von {number} genau einmal in dieser Reihenfolge.")
    if re.search(r"\b0[0-9]", text):
        raise ValueError("Zusammengefügte Ziffern dürfen nicht mit einer Null beginnen.")
    tree = ast.parse(text, mode="eval")
    if not any(isinstance(node, ast.BinOp) for node in ast.walk(tree)):
        raise ValueError("Baue eine Rechnung mit mindestens einer Rechenoperation.")

    def read(node):
        if isinstance(node, ast.Constant) and type(node.value) is int:
            value = Fraction(node.value)
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            operand = read(node.operand)
            value = -operand if isinstance(node.op, ast.USub) else operand
        elif isinstance(node, ast.BinOp):
            left, right = read(node.left), read(node.right)
            operations = {ast.Add: Fraction.__add__, ast.Sub: Fraction.__sub__,
                          ast.Mult: Fraction.__mul__, ast.Div: Fraction.__truediv__, ast.Pow: power}
            operation = operations.get(type(node.op))
            if operation is None:
                raise ValueError("Diese Rechenoperation ist hier nicht erlaubt.")
            value = operation(left, right)
        else:
            raise ValueError("Dieser Ausdruck ist hier nicht erlaubt.")
        if not bounded(value):
            raise ValueError("Ein Zwischenergebnis liegt außerhalb des Rechenbereichs.")
        return value

    return read(tree.body)


class FriedmanPuzzle(Puzzle):
    def check_expression(self, expression):
        if not expression.strip():
            return "incomplete", "Gib zuerst einen Ausdruck ein."
        try:
            value = evaluate_friedman(expression, self.view["number"])
        except SyntaxError:
            return "invalid", "Prüfe die Schreibweise und die Klammern."
        except ZeroDivisionError:
            return "invalid", "Teilen durch null ist nicht erlaubt."
        except ValueError as error:
            return "invalid", str(error)
        if value == self.view["number"]:
            return "correct", "Der Ausdruck stimmt."
        return "wrong", f"Der Ausdruck ergibt {value}. Gesucht ist {self.view['number']}."


@lru_cache(maxsize=1)
def friedman_numbers():
    return tuple((number, expression) for number, expression in json.loads(
        files("raetselkalender").joinpath("data/friedman.json").read_text(encoding="utf-8")))


def readable_expression(expression):
    tree = ast.parse(expression.replace("^", "**"), mode="eval")
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.right, ast.UnaryOp) and isinstance(node.right.op, ast.USub):
            if isinstance(node.op, (ast.Add, ast.Sub)):
                node.op = ast.Sub() if isinstance(node.op, ast.Add) else ast.Add()
                node.right = node.right.operand
    return ast.unparse(tree).replace("**", "^")


def friedman(seed, difficulty):
    hard = difficulty == "schwer"
    number, expression = random.Random(seed).choice(
        [(n, s) for n, s in friedman_numbers() if (n >= 10000) == hard])
    rules = ("Schreibe die Zielzahl als Rechnung mit ihren eigenen Ziffern in derselben Reihenfolge. "
             "Erlaubt sind +, −, ×, /, Klammern, Potenzen wie 2^3 und das Zusammenfassen benachbarter Ziffern. "
             "Exponenten sind ganzzahlig. Verwende mindestens eine Rechenoperation.")
    return FriedmanPuzzle("friedman-zahlen", "Friedman Zahlen", rules, Model({}, []), {}, {},
                          dict(kind="activity", mode="friedman", number=number), seed, difficulty,
                          analysis=dict(solution_verified=True), result=readable_expression(expression))

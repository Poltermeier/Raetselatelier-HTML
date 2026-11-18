from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .solver import Model, deduce, solve


class LogicalProofMissing(ValueError):
    """A candidate is not certified for completion without search."""


@dataclass
class Puzzle:
    type_id: str
    title: str
    rules: str
    model: Model
    solution: dict[str, int]
    givens: dict[str, int]
    view: dict[str, Any]
    seed: int
    difficulty: str
    analysis: dict[str, Any] = field(default_factory=dict)
    result: str | None = None
    logical_steps: list[dict] = field(default_factory=list, repr=False)

    @property
    def editable(self) -> list[str]:
        return [k for k in self.model.domains if k not in self.givens]

    def check(self, entries: dict[str, int]) -> tuple[str, list[str]]:
        """Never interpret an empty cell as zero or accept bool/float as a digit."""
        if any(k not in self.model.domains or type(v) is not int or v not in self.model.domains[k]
               for k, v in entries.items()):
            return "invalid", []
        if any(k in entries and entries[k] != v for k, v in self.givens.items()):
            return "invalid", []
        values = self.givens | entries
        if any(k not in values for k in self.model.domains):
            return "incomplete", []
        wrong = [k for k in self.editable if values[k] != self.solution[k]]
        return ("wrong" if wrong else "correct"), wrong

    def certify(self) -> None:
        self.logical_steps = []
        self.analysis.update(unique=False, logical_solvable=False)
        logical = deduce(self.model, self.givens)
        if logical.status == 'contradiction':
            raise ValueError("Die Regeln und Vorgaben widersprechen sich")
        if not logical.solved:
            raise LogicalProofMissing("Kein vollständiger Lösungsweg ohne Raten nachgewiesen")
        if {k: next(iter(v)) for k, v in logical.domains.items()} != self.solution:
            raise ValueError("Der hergeleitete Lösungsweg passt nicht zur gespeicherten Lösung")
        result = solve(self.model, self.givens, limit=2, seconds=12)
        if len(result.solutions) != 1 or result.solutions[0] != self.solution:
            raise ValueError("Das Rätsel besitzt keine nachgewiesene eindeutige Lösung")
        self.logical_steps = logical.steps
        self.analysis.update(unique=True, logical_solvable=True,
                             logical_method='constraint_propagation', logical_step_count=len(logical.steps),
                             search_nodes=result.nodes,
                             search_branches=result.branches,
                             difficulty_note="Heuristische Einstufung; noch keine menschliche Kalibrierung.")

    def export(self, include_solution: bool = False) -> dict[str, Any]:
        data = dict(type=self.type_id, title=self.title, rules=self.rules, seed=self.seed,
                    difficulty=self.difficulty, givens=self.givens, view=self.view,
                    domains={k: sorted(v) for k, v in self.model.domains.items()},
                    analysis=self.analysis)
        if include_solution:
            data["solution"] = self.solution
            data["logical_proof"] = self.logical_steps
            if self.result is not None:
                data["result"] = self.result
        return data

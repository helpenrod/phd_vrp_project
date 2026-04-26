from dataclasses import dataclass, field
from typing import FrozenSet


@dataclass(frozen=True)
class ConstraintSet:
    constraints: FrozenSet[str]

    def has(self, constraint: str) -> bool:
        return constraint in self.constraints

    def has_all(self, required: set[str]) -> bool:
        return required.issubset(self.constraints)

    def has_any(self, candidates: set[str]) -> bool:
        return bool(self.constraints.intersection(candidates))


@dataclass
class AlgorithmBlueprint:
    representation: str
    initialization: list[str] = field(default_factory=list)
    selection: list[str] = field(default_factory=list)
    crossover: list[str] = field(default_factory=list)
    mutation: list[str] = field(default_factory=list)
    repair: list[str] = field(default_factory=list)
    local_search: list[str] = field(default_factory=list)
    evaluation: list[str] = field(default_factory=list)
    replacement: list[str] = field(default_factory=list)
    termination: list[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "representation": self.representation,
            "initialization": self.initialization,
            "selection": self.selection,
            "crossover": self.crossover,
            "mutation": self.mutation,
            "repair": self.repair,
            "local_search": self.local_search,
            "evaluation": self.evaluation,
            "replacement": self.replacement,
            "termination": self.termination,
        }

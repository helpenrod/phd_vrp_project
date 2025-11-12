# Reusable selection operators
import random
from copy import deepcopy

def tournament_selection(population: list, k: int, inst) -> list:
    """
    Selects one individual from the population using k-tournament selection.
    The instance `inst` is needed to score the individuals.
    """
    candidates = random.sample(population, k)
    scored = [(inst.total_cost(c), c) for c in candidates]
    scored.sort(key=lambda x: x[0])
    return deepcopy(scored[0][1])
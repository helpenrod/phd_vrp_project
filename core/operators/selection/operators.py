# Reusable selection operators
import random
from copy import deepcopy

def tournament_selection(population: list, k: int, cost_function) -> list:
    """
    Selects one individual from the population using k-tournament selection.
    The `cost_function` is a function pointer used to score individuals.
    """
    candidates = random.sample(population, k)
    scored = [(cost_function(c), c) for c in candidates]
    scored.sort(key=lambda x: x[0])
    return deepcopy(scored[0][1])
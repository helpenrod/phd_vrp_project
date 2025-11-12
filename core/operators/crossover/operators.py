# Reusable crossover operators
import random
from copy import deepcopy

def route_based_crossover(p1: list, p2: list, inst) -> list:
    """
    Route-based crossover (as seen in alg1, alg2, alg3).
    1. Takes a random subset of routes from parent 1.
    2. Greedily inserts the remaining customers in the order of parent 2,
       using the instance's `cheapest_feasible_insertion` method.
    """
    r1 = inst.split_chromosome(p1)
    r2 = inst.split_chromosome(p2)

    keep_count = max(1, len(r1) // 2) if r1 else 0
    kept_idx = set(random.sample(range(len(r1)), keep_count)) if r1 else set()
    child_routes = [deepcopy(r1[i]) for i in sorted(kept_idx)]

    assigned = set(c for rt in child_routes for c in rt)
    p2_order = [c for rt in r2 for c in rt]

    for c in p2_order:
        if c in assigned:
            continue
        r_idx, pos, _ = inst.cheapest_feasible_insertion(child_routes, c)
        if r_idx is None:
            # If no feasible insertion, try to open a new route.
            # The feasibility of [c] depends on all constraints (cap, tw).
            if inst.is_feasible_routes([[c]]):
                child_routes.append([c])
            else:
                child_routes.append([c])  # Fallback: let repair handle it
        else:
            child_routes[r_idx].insert(pos, c)
        assigned.add(c)

    return inst.routes_to_chromosome(child_routes)
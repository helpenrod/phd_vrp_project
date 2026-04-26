# Reusable crossover operators
import random
from copy import deepcopy

def route_based_crossover(p1: list, p2: list, inst) -> list:
    """
    Standard Route-based crossover.
    1. Takes a random subset of routes from parent 1.
    2. Greedily inserts remaining customers in the order of parent 2.
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
            
        # inst.cheapest_feasible_insertion returns (r_idx, p_pos, d_pos, cost)
        r_idx, pos, _, _ = inst.cheapest_feasible_insertion(child_routes, c)
        if r_idx is None:
            child_routes.append([c])
        else:
            if r_idx == len(child_routes):
                child_routes.append([c])
            else:
                child_routes[r_idx].insert(pos, c)
        assigned.add(c)

    return inst.routes_to_chromosome(child_routes)

def pd_route_based_crossover(p1: list, p2: list, inst) -> list:
    """
    PD-Aware Route-based crossover.
    1. Takes a random subset of routes from parent 1.
    2. Greedily inserts remaining PD-pairs in the order of parent 2,
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
        
        # Skip deliveries; they are handled when their pickup is processed
        if hasattr(inst, 'delivery_to_pickup') and c in inst.delivery_to_pickup:
            continue
            
        r_idx, p_pos, d_pos, _ = inst.cheapest_feasible_insertion(child_routes, c)
        if r_idx is None:
            new_r = [c, inst.pd_pairs[c]] if c in inst.pd_pairs else [c]
            child_routes.append(new_r)
        else:
            if r_idx == len(child_routes):
                new_r = [c, inst.pd_pairs[c]] if c in inst.pd_pairs else [c]
                child_routes.append(new_r)
            else:
                child_routes[r_idx].insert(p_pos, c)
                if d_pos is not None:
                    child_routes[r_idx].insert(d_pos, inst.pd_pairs[c])
        
        assigned.add(c)
        if c in inst.pd_pairs:
            assigned.add(inst.pd_pairs[c])

    return inst.routes_to_chromosome(child_routes)

route_based_crossover.required_constraints = set()
route_based_crossover.forbidden_constraints = {'pickup_delivery'}
route_based_crossover.compatible_constraints = {'capacity', 'time_window'}
route_based_crossover.tags = route_based_crossover.compatible_constraints
route_based_crossover.stage = "crossover"
route_based_crossover.name = "route_based"
route_based_crossover.requires = route_based_crossover.required_constraints
route_based_crossover.forbids = route_based_crossover.forbidden_constraints
route_based_crossover.supports = route_based_crossover.compatible_constraints
route_based_crossover.representation = "direct_route"

pd_route_based_crossover.required_constraints = {'pickup_delivery'}
pd_route_based_crossover.forbidden_constraints = set()
pd_route_based_crossover.compatible_constraints = {'capacity', 'time_window', 'pickup_delivery'}
pd_route_based_crossover.tags = pd_route_based_crossover.compatible_constraints
pd_route_based_crossover.stage = "crossover"
pd_route_based_crossover.name = "pd_route_based"
pd_route_based_crossover.requires = pd_route_based_crossover.required_constraints
pd_route_based_crossover.forbids = pd_route_based_crossover.forbidden_constraints
pd_route_based_crossover.supports = pd_route_based_crossover.compatible_constraints
pd_route_based_crossover.representation = "direct_route"

# Reusable mutation operators
import random

def relocate_mutation(routes: list, inst) -> list:
    """
    Picks a random customer and relocates it to the cheapest feasible position.
    Relies on `inst.cheapest_feasible_insertion`.
    """
    if not routes:
        return routes
    
    src_idx = random.randrange(len(routes))
    while not routes[src_idx]:
        src_idx = (src_idx + 1) % len(routes)

    pos = random.randrange(len(routes[src_idx]))
    c = routes[src_idx].pop(pos)
    
    best = inst.cheapest_feasible_insertion(routes, c)
    if best[0] is None:
        if inst.is_feasible_routes([[c]]):
            routes.append([c])
        else:
            routes[src_idx].insert(pos, c)  # Revert
    else:
        r_idx, insert_pos, _ = best
        routes[r_idx].insert(insert_pos, c)
    return routes

def swap_mutation(routes: list, inst) -> list:
    """
    Swaps two random customers, checking for feasibility.
    Relies on `inst.is_feasible_routes` (or `schedule_route` for speed).
    """
    flat = [(ri, ci) for ri, r in enumerate(routes) for ci, _ in enumerate(r)]
    if len(flat) < 2:
        return routes

    (r1, i1), (r2, i2) = random.sample(flat, 2)
    routes[r1][i1], routes[r2][i2] = routes[r2][i2], routes[r1][i1]

    # Check if the modified routes are feasible.
    if not inst.is_feasible_routes([routes[r1]]) or (r1 != r2 and not inst.is_feasible_routes([routes[r2]])):
        routes[r1][i1], routes[r2][i2] = routes[r2][i2], routes[r1][i1] # Revert

    return routes
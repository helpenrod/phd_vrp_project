import random

def relocate_mutation(routes, inst):
    """Standard relocate: move one random node. Safe for all variants."""
    if not routes: return routes
    all_nodes = [n for r in routes for n in r]
    if not all_nodes: return routes
    target = random.choice(all_nodes)
    
    new_routes = []
    for r in routes:
        filtered = [n for n in r if n != target]
        if filtered: new_routes.append(filtered)
        
    # Use the new insertion signature: (r_idx, p_pos, d_pos, cost)
    res = inst.cheapest_feasible_insertion(new_routes, target)
    r_idx, pos = res[0], res[1]
    
    if r_idx is not None:
        if r_idx == len(new_routes): new_routes.append([target])
        else: new_routes[r_idx].insert(pos, target)
        return new_routes
    return routes

relocate_mutation.required_constraints = set()
relocate_mutation.forbidden_constraints = {'pickup_delivery'}
relocate_mutation.compatible_constraints = {'capacity', 'time_window'}
relocate_mutation.tags = relocate_mutation.compatible_constraints

def swap_mutation(routes, inst):
    """Standard swap: swap two random nodes if feasible."""
    if not routes: return routes
    all_pos = [(ri, ni) for ri, r in enumerate(routes) for ni in range(len(r))]
    if len(all_pos) < 2: return routes
    
    (r1, n1), (r2, n2) = random.sample(all_pos, 2)
    new_routes = [r[:] for r in routes]
    new_routes[r1][n1], new_routes[r2][n2] = new_routes[r2][n2], new_routes[r1][n1]
    
    if inst.is_feasible_routes(new_routes): return new_routes
    return routes

swap_mutation.required_constraints = set()
swap_mutation.forbidden_constraints = {'pickup_delivery'}
swap_mutation.compatible_constraints = {'capacity', 'time_window'}
swap_mutation.tags = swap_mutation.compatible_constraints

def pd_relocate_mutation(routes, inst):
    """Relocates a random PD-pair (or single node) to its cheapest feasible position."""
    if not routes: return routes
    
    all_nodes = [n for r in routes for n in r]
    if not all_nodes: return routes
    
    target = random.choice(all_nodes)
    # Identify the pair
    p = target if target in inst.pd_pairs else inst.delivery_to_pickup.get(target, target)
    d = inst.pd_pairs.get(p)
    
    # 1. Remove the pair
    new_routes = []
    for r in routes:
        filtered = [node for node in r if node != p and node != d]
        if filtered:
            new_routes.append(filtered)
            
    # 2. Re-insert optimally
    r_idx, p_pos, d_pos, _ = inst.cheapest_feasible_insertion(new_routes, p)
    
    if r_idx is not None:
        if r_idx == len(new_routes):
            new_routes.append([p, d] if d else [p])
        else:
            new_routes[r_idx].insert(p_pos, p)
            if d_pos is not None:
                new_routes[r_idx].insert(d_pos, d)
    else:
        # Fallback
        new_routes.append([p, d] if d else [p])
        
    return new_routes

pd_relocate_mutation.required_constraints = {'pickup_delivery'}
pd_relocate_mutation.forbidden_constraints = set()
pd_relocate_mutation.compatible_constraints = {'capacity', 'time_window', 'pickup_delivery'}
pd_relocate_mutation.tags = pd_relocate_mutation.compatible_constraints

def pd_swap_mutation(routes, inst):
    """PD-Aware swap: Re-inserts two PD-pairs greedily."""
    pickups = [n for r in routes for n in r if n in inst.pd_pairs]
    if len(pickups) < 2: return routes
    
    p_chosen = random.sample(pickups, 2)
    pairs = [(p, inst.pd_pairs[p]) for p in p_chosen]
    
    new_routes = []
    for r in routes:
        filtered = [n for n in r if n not in (p_chosen[0], pairs[0][1], p_chosen[1], pairs[1][1])]
        if filtered: new_routes.append(filtered)
        
    for p, d in pairs:
        r_idx, p_pos, d_pos, _ = inst.cheapest_feasible_insertion(new_routes, p)
        if r_idx is not None:
            if r_idx == len(new_routes): new_routes.append([p, d])
            else:
                new_routes[r_idx].insert(p_pos, p)
                new_routes[r_idx].insert(d_pos, d)
        else: new_routes.append([p, d])
    return new_routes

pd_swap_mutation.required_constraints = {'pickup_delivery'}
pd_swap_mutation.forbidden_constraints = set()
pd_swap_mutation.compatible_constraints = {'capacity', 'time_window', 'pickup_delivery'}
pd_swap_mutation.tags = pd_swap_mutation.compatible_constraints

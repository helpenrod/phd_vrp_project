# Primitive constraint checker for vehicle capacity.

def check_capacity(routes, instance):
    """Checks if any route exceeds vehicle capacity at any point."""
    if not hasattr(instance, 'capacity') or instance.capacity is None or instance.capacity == float('inf'):
        return True  # No capacity constraint to check

    for r in routes:
        load = 0.0
        for node in r:
            load += instance.demand.get(node, 0.0)
            if load > instance.capacity + 1e-9:
                return False
    return True

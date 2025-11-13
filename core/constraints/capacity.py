# Primitive constraint checker for vehicle capacity.

def check_capacity(routes, instance):
    """Checks if any route exceeds vehicle capacity."""
    if not hasattr(instance, 'capacity') or instance.capacity is None or instance.capacity == float('inf'):
        return True  # No capacity constraint to check

    for r in routes:
        if instance.route_load(r) > instance.capacity + 1e-9:
            return False
    return True
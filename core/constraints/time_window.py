# Primitive constraint checker for time windows.

def check_time_windows(routes, instance):
    """Checks if all routes are feasible according to their time windows."""
    if not hasattr(instance, 'due_time') or not instance.due_time:
        return True # No time window constraint to check

    for r in routes:
        if not instance.schedule_route(r)[0]:
            return False
    return True
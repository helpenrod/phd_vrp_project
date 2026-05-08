from core.data.route_history import RouteHistory


def validate_route_history(route_history: RouteHistory, constraints: list[str] | set[str]) -> None:
    """Validate historical data against explicitly configured constraints."""
    active_constraints = set(constraints)

    if not route_history.coordinates:
        raise ValueError("Historical data must include coordinates.")

    if route_history.depot not in route_history.coordinates:
        raise ValueError("Historical data depot must exist in coordinates.")

    if "capacity" in active_constraints and route_history.demands is None:
        raise ValueError("Capacity-constrained historical data must include demands.")

    if "time_window" in active_constraints and route_history.time_windows is None:
        raise ValueError("Time-window historical data must include time windows.")

    if "pickup_delivery" in active_constraints and route_history.pickup_delivery_pairs is None:
        raise ValueError(
            "Pickup-delivery historical data must include pickup-delivery pairs."
        )

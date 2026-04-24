def check_pickup_delivery(routes, instance):
    """
    Validates that pickup and delivery pairs are served by the same vehicle
    and that the pickup occurs before the delivery.
    """
    for route in routes:
        route_set = set(route)
        for i, node in enumerate(route):
            # If node is a pickup, its delivery must be in the same route later
            if node in instance.pd_pairs:
                delivery = instance.pd_pairs[node]
                if delivery not in route_set or route.index(delivery) <= i:
                    return False
            # If node is a delivery, its pickup must be in the same route (implicitly checked by above)
    return True
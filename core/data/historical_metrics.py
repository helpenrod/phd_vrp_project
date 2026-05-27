import statistics


class HistoricalMetrics:
    def __init__(self, instance, constraints: list[str]):
        self.instance = instance
        self.constraints = set(constraints)

    def compute_route_cost(self, route: list[int]) -> float:
        return float(self.instance.route_cost(self._clean_route(route)))

    def compute_total_cost(self, previous_routes: list[list[int]]) -> float:
        route_sets = self._as_route_sets(previous_routes)
        if not route_sets:
            return 0.0
        return float(self.compute_route_set_cost(route_sets[0]))

    def compute_route_set_cost(self, route_set: list[list[int]]) -> float:
        return float(sum(self.compute_route_cost(route) for route in route_set or []))

    def compute_route_set_costs(self, previous_routes_or_sets) -> list[float]:
        return [
            self.compute_route_set_cost(route_set)
            for route_set in self._as_route_sets(previous_routes_or_sets)
        ]

    def compute_average_total_cost(self, previous_routes_or_sets) -> float:
        return self._mean(self.compute_route_set_costs(previous_routes_or_sets))

    def compute_feasibility_summary(self, previous_routes: list[list[int]]) -> dict:
        route_sets = self._as_route_sets(previous_routes)
        routes = [
            self._clean_route(route)
            for route_set in route_sets
            for route in route_set
        ]
        feasible_routes = 0
        feasible_route_sets = 0
        capacity_violations = 0
        pickup_delivery_violations = 0
        time_window_violations = 0

        for route_set in route_sets:
            cleaned_set = [self._clean_route(route) for route in route_set]
            if self.instance.is_feasible_routes(cleaned_set, check_coverage=True):
                feasible_route_sets += 1

        for route in routes:
            if self.instance.is_feasible_routes([route]):
                feasible_routes += 1
            if "capacity" in self.constraints and self._has_capacity_violation(route):
                capacity_violations += 1
            if (
                "pickup_delivery" in self.constraints
                and self._has_pickup_delivery_violation(route)
            ):
                pickup_delivery_violations += 1
            if "time_window" in self.constraints and not self.instance.schedule_route(route)[0]:
                time_window_violations += 1

        total_routes = len(routes)
        total_route_sets = len(route_sets)
        return {
            "total_route_sets": total_route_sets,
            "feasible_route_sets": feasible_route_sets,
            "infeasible_route_sets": total_route_sets - feasible_route_sets,
            "total_routes": total_routes,
            "feasible_routes": feasible_routes,
            "infeasible_routes": total_routes - feasible_routes,
            "capacity_violations": capacity_violations,
            "pickup_delivery_violations": pickup_delivery_violations,
            "time_window_violations": time_window_violations,
        }

    @staticmethod
    def compute_improvement(historical_cost: float, generated_cost: float) -> dict:
        historical_cost = float(historical_cost)
        generated_cost = float(generated_cost)
        if historical_cost <= 0:
            return {
                "historical_cost": historical_cost,
                "generated_cost": generated_cost,
                "absolute_improvement": None,
                "percent_improvement": None,
            }

        absolute_improvement = historical_cost - generated_cost
        return {
            "historical_cost": historical_cost,
            "generated_cost": generated_cost,
            "absolute_improvement": absolute_improvement,
            "percent_improvement": 100.0 * absolute_improvement / historical_cost,
        }

    def extract_metrics(self, previous_routes: list[list[int]]) -> dict:
        route_sets = self._as_route_sets(previous_routes)
        routes = [
            self._clean_route(route)
            for route_set in route_sets
            for route in route_set
        ]
        route_set_costs = self.compute_route_set_costs(route_sets)
        route_lengths = [self.compute_route_cost(route) for route in routes]
        customers_per_route = [len(route) for route in routes]
        capacity_usages = [
            self._capacity_usage(route)
            for route in routes
            if self._capacity_usage(route) is not None
        ]
        feasibility = self.compute_feasibility_summary(routes)

        return {
            "avg_route_length": self._mean(route_lengths),
            "avg_customers_per_route": self._mean(customers_per_route),
            "avg_capacity_usage": self._mean(capacity_usages),
            "max_capacity_usage": max(capacity_usages) if capacity_usages else 0.0,
            "capacity_violation_rate": self._rate(
                feasibility["capacity_violations"], feasibility["total_routes"]
            ),
            "pickup_delivery_violation_rate": self._rate(
                feasibility["pickup_delivery_violations"],
                feasibility["total_routes"],
            ),
            "route_variability": self._coefficient_of_variation(customers_per_route),
            "historical_cost": self._mean(route_set_costs),
            "historical_costs": route_set_costs,
            "historical_route_sets": len(route_sets),
        }

    def _clean_route(self, route: list[int]) -> list[int]:
        return [int(node) for node in route if int(node) != 0]

    def _as_route_sets(self, previous_routes_or_sets) -> list[list[list[int]]]:
        if not previous_routes_or_sets:
            return []

        first = previous_routes_or_sets[0]
        if not first:
            return [previous_routes_or_sets]

        if isinstance(first[0], (list, tuple)):
            return [
                [[int(node) for node in route] for route in route_set]
                for route_set in previous_routes_or_sets
            ]

        return [
            [[int(node) for node in route] for route in previous_routes_or_sets]
        ]

    def _capacity_usage(self, route: list[int]) -> float | None:
        capacity = getattr(self.instance, "capacity", float("inf"))
        if capacity in {None, float("inf")} or capacity <= 0:
            return None
        return float(self.instance.route_load(route) / capacity)

    def _has_capacity_violation(self, route: list[int]) -> bool:
        capacity = getattr(self.instance, "capacity", float("inf"))
        if capacity in {None, float("inf")}:
            return False

        load = 0.0
        for node in route:
            load += self.instance.demand.get(node, 0.0)
            if load > capacity + 1e-9:
                return True
        return False

    def _has_pickup_delivery_violation(self, route: list[int]) -> bool:
        positions = {node: idx for idx, node in enumerate(route)}
        route_set = set(route)
        for pickup, delivery in getattr(self.instance, "pd_pairs", {}).items():
            if pickup in route_set or delivery in route_set:
                if pickup not in positions or delivery not in positions:
                    return True
                if positions[pickup] >= positions[delivery]:
                    return True
        return False

    @staticmethod
    def _mean(values) -> float:
        values = list(values)
        if not values:
            return 0.0
        return float(sum(values) / len(values))

    @staticmethod
    def _rate(count: int, total: int) -> float:
        if total <= 0:
            return 0.0
        return float(count / total)

    @staticmethod
    def _coefficient_of_variation(values) -> float:
        values = list(values)
        if len(values) < 2:
            return 0.0
        mean_value = sum(values) / len(values)
        if mean_value <= 0:
            return 0.0
        return float(statistics.pstdev(values) / mean_value)

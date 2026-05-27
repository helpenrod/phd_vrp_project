class HistoricalHeuristicModel:
    def __init__(self, historical_metrics: dict, constraints: list[str]):
        self.metrics = historical_metrics or {}
        self.constraints = set(constraints)

    def get_eta(self, decision: str, value) -> float:
        eta = 1.0

        if self.metrics.get("avg_capacity_usage", 0.0) > 0.85:
            if decision == "repair" and value == "greedy_repair":
                eta *= 1.3
            if decision == "mutation" and value in {"relocate", "pd_relocate"}:
                eta *= 1.25
            if decision == "penalty_weight" and self._numeric_at_least(value, 50):
                eta *= 1.2

        if self.metrics.get("capacity_violation_rate", 0.0) > 0.0:
            if decision == "repair" and value == "greedy_repair":
                eta *= 1.5
            if decision == "penalty_weight" and self._numeric_at_least(value, 100):
                eta *= 1.4

        if "pickup_delivery" in self.constraints:
            if decision == "mutation" and value in {"pd_relocate", "pd_swap"}:
                eta *= 1.4
            if decision == "crossover" and value == "pd_route_based":
                eta *= 1.4
            if decision == "repair" and value == "greedy_repair":
                eta *= 1.2

        if self.metrics.get("avg_customers_per_route", 0.0) > 10:
            if decision == "local_search" and value == "2opt":
                eta *= 1.4

        if self.metrics.get("route_variability", 0.0) > 0.5:
            if decision == "mutation_prob" and self._numeric_at_least(value, 0.15):
                eta *= 1.25
            if decision == "mutation" and value in {"swap", "pd_swap"}:
                eta *= 1.2

        return float(max(eta, 1e-9))

    def snapshot(self, configuration_space: dict) -> dict:
        return {
            decision: {
                value: self.get_eta(decision, value)
                for value in values
            }
            for decision, values in configuration_space.items()
        }

    @staticmethod
    def _numeric_at_least(value, threshold: float) -> bool:
        try:
            return float(value) >= threshold
        except (TypeError, ValueError):
            return False

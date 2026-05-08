import math


def summarize_results(results: list[dict]) -> dict:
    costs = [float(result["best_cost"]) for result in results]
    runtimes = [float(result.get("runtime", 0.0)) for result in results]
    feasibility_values = [1.0 if result.get("is_feasible") else 0.0 for result in results]

    mean_cost = _mean(costs)
    feasibility_rate = _mean(feasibility_values)

    return {
        "mean_cost": mean_cost,
        "std_cost": _std(costs, mean_cost),
        "best_cost": min(costs) if costs else float("inf"),
        "worst_cost": max(costs) if costs else float("inf"),
        "mean_feasibility_rate": feasibility_rate,
        "mean_runtime": _mean(runtimes),
    }


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _std(values: list[float], mean_value: float | None = None) -> float:
    if len(values) < 2:
        return 0.0
    if mean_value is None:
        mean_value = _mean(values)
    variance = sum((value - mean_value) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance)

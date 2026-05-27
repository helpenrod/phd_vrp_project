from core.ga_framework import GARunner
from core.hyperheuristic.statistics import summarize_results


class ConfigurationEvaluator:
    def __init__(
        self,
        instance,
        constraints: list[str],
        objective: str = "distance",
        n_repetitions: int = 5,
        base_seed: int = 42,
        historical_routes: list[list[int]] | None = None,
        historical_seed_fraction: float = 0.0,
        historical_variants_per_seed: int = 2,
    ):
        self.instance = instance
        self.constraints = list(constraints)
        self.objective = objective
        self.n_repetitions = int(n_repetitions)
        self.base_seed = int(base_seed)
        self.historical_routes = historical_routes
        self.historical_seed_fraction = float(historical_seed_fraction)
        self.historical_variants_per_seed = int(historical_variants_per_seed)

    def evaluate(self, ga_config: dict) -> dict:
        results = []

        for repetition in range(self.n_repetitions):
            seed = self.base_seed + repetition
            run_config = dict(ga_config)
            run_config["objective"] = self.objective
            if self.historical_routes:
                run_config["historical_routes"] = self.historical_routes
                run_config["historical_seed_fraction"] = self.historical_seed_fraction
                run_config["historical_variants_per_seed"] = self.historical_variants_per_seed
            runner = GARunner(
                self.instance,
                self.constraints,
                run_config,
                seed=seed,
            )
            results.append(runner.run())

        summary = summarize_results(results)
        penalty_weight = float(ga_config.get("penalty_weight", 50))
        infeasibility_penalty = (1.0 - summary["mean_feasibility_rate"]) * penalty_weight * 1000.0
        runtime_penalty = summary["mean_runtime"] * 0.01
        summary["score"] = summary["mean_cost"] + infeasibility_penalty + runtime_penalty
        summary["results"] = results
        summary["best_result"] = min(results, key=lambda result: result["best_cost"])
        return summary

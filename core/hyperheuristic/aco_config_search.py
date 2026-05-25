import math
import random

from core.hyperheuristic.pheromone_model import PheromoneModel


class ACOConfigSearch:
    def __init__(
        self,
        configuration_space: dict,
        evaluator,
        n_ants: int = 10,
        n_iterations: int = 20,
        evaporation_rate: float = 0.2,
        alpha: float = 1.0,
        beta: float = 1.0,
        seed: int | None = None,
    ):
        self.configuration_space = configuration_space
        self.evaluator = evaluator
        self.n_ants = int(n_ants)
        self.n_iterations = int(n_iterations)
        self.evaporation_rate = float(evaporation_rate)
        self.alpha = float(alpha)
        self.beta = float(beta)
        self.random = random.Random(seed)
        self.pheromones = PheromoneModel(configuration_space)

    def run(self) -> dict:
        best_configuration = None
        best_evaluation = None
        history = []

        for iteration in range(self.n_iterations):
            iteration_results = []
            print(self._iteration_separator(iteration))

            for ant_idx in range(self.n_ants):
                internal_config = self._construct_internal_configuration()
                ga_config = self._to_ga_config(internal_config)
                print(
                    f"ACO iteration {iteration + 1}/{self.n_iterations} | "
                    f"ant {ant_idx + 1}/{self.n_ants} | "
                    f"testing {self._format_configuration(ga_config)}"
                )
                evaluation = self.evaluator.evaluate(ga_config)
                iteration_results.append({
                    "configuration": ga_config,
                    "internal_configuration": internal_config,
                    "evaluation": evaluation,
                })
                print(
                    f"  result: score={evaluation['score']:.4f}, "
                    f"mean_cost={evaluation['mean_cost']:.4f}, "
                    f"best_cost={evaluation['best_cost']:.4f}, "
                    f"feasible_rate={evaluation['mean_feasibility_rate']:.2f}, "
                    f"mean_runtime={evaluation['mean_runtime']:.4f}s"
                )

                if best_evaluation is None or evaluation["score"] < best_evaluation["score"]:
                    best_configuration = ga_config
                    best_evaluation = evaluation
                    print("  new best configuration found")

            self.pheromones.evaporate(self.evaporation_rate)
            for result in iteration_results:
                reward = self._reward(result["evaluation"]["score"])
                self.pheromones.reinforce(result["internal_configuration"], reward)

            iteration_best = min(
                iteration_results,
                key=lambda result: result["evaluation"]["score"],
            )
            print(
                f"ACO iteration {iteration + 1} best: "
                f"score={iteration_best['evaluation']['score']:.4f} | "
                f"{self._format_configuration(iteration_best['configuration'])}"
            )

            history.append({
                "iteration": iteration,
                "best_score": best_evaluation["score"],
                "best_configuration": dict(best_configuration),
                "tested_configurations": [
                    {
                        "configuration": dict(result["configuration"]),
                        "score": result["evaluation"]["score"],
                        "mean_cost": result["evaluation"]["mean_cost"],
                        "best_cost": result["evaluation"]["best_cost"],
                        "mean_feasibility_rate": result["evaluation"]["mean_feasibility_rate"],
                        "mean_runtime": result["evaluation"]["mean_runtime"],
                    }
                    for result in iteration_results
                ],
            })

        return {
            "best_configuration": best_configuration,
            "best_evaluation": best_evaluation,
            "history": history,
            "pheromones": self.pheromones.snapshot(),
        }

    def _construct_internal_configuration(self) -> dict:
        return {
            decision: self._choose_value(decision, values)
            for decision, values in self.configuration_space.items()
        }

    def _choose_value(self, decision: str, values: list):
        weights = []
        for value in values:
            pheromone = self.pheromones.get(decision, value)
            heuristic = 1.0
            weights.append((pheromone ** self.alpha) * (heuristic ** self.beta))

        total = sum(weights)
        if total <= 0:
            return self.random.choice(values)

        threshold = self.random.random() * total
        cumulative = 0.0
        for value, weight in zip(values, weights):
            cumulative += weight
            if cumulative >= threshold:
                return value
        return values[-1]

    @staticmethod
    def _to_ga_config(internal_config: dict) -> dict:
        ga_config = dict(internal_config)
        repair = ga_config.get("repair")
        ga_config["repair"] = [] if repair == "none" else [repair]
        local_search = ga_config.get("local_search")
        ga_config["local_search"] = [] if local_search == "none" else [local_search]
        return ga_config

    @staticmethod
    def _reward(score: float) -> float:
        if not math.isfinite(score):
            return 0.0
        return 1.0 / (1.0 + max(score, 0.0))

    def _iteration_separator(self, iteration: int) -> str:
        return (
            "\n"
            + "=" * 80
            + "\n"
            + f"ACO ITERATION {iteration + 1}/{self.n_iterations}: comparing GA configurations"
            + "\n"
            + "=" * 80
        )

    @staticmethod
    def _format_configuration(configuration: dict) -> str:
        fields = [
            "selection",
            "crossover",
            "mutation",
            "repair",
            "local_search",
            "population_size",
            "generations",
            "crossover_prob",
            "mutation_prob",
            "tournament_size",
            "penalty_weight",
        ]
        return ", ".join(
            f"{field}={configuration[field]}"
            for field in fields
            if field in configuration
        )

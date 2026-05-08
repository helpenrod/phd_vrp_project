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

            for _ in range(self.n_ants):
                internal_config = self._construct_internal_configuration()
                ga_config = self._to_ga_config(internal_config)
                evaluation = self.evaluator.evaluate(ga_config)
                iteration_results.append({
                    "configuration": ga_config,
                    "internal_configuration": internal_config,
                    "evaluation": evaluation,
                })

                if best_evaluation is None or evaluation["score"] < best_evaluation["score"]:
                    best_configuration = ga_config
                    best_evaluation = evaluation

            self.pheromones.evaporate(self.evaporation_rate)
            for result in iteration_results:
                reward = self._reward(result["evaluation"]["score"])
                self.pheromones.reinforce(result["internal_configuration"], reward)

            history.append({
                "iteration": iteration,
                "best_score": best_evaluation["score"],
                "best_configuration": dict(best_configuration),
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

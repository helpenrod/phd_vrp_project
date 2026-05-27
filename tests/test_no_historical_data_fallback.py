import unittest

from core.constraints import capacity
from core.ga_framework import GAFramework
from core.hyperheuristic.aco_config_search import ACOConfigSearch
from core.hyperheuristic.dynamic_instance import DynamicInstance


class NoHistoricalDataFallbackTests(unittest.TestCase):
    def test_ga_initialization_without_history_keeps_population_size(self):
        config = {
            "instance": {
                "coordinates": {0: [0, 0], 1: [1, 0], 2: [2, 0]},
                "demand": {0: 0, 1: 1, 2: 1},
            },
            "fleet": {"capacity": 10},
            "constraints": {"problem_type": ["capacity"]},
        }
        instance = DynamicInstance(config, [capacity.check_capacity])
        ga = GAFramework(
            instance,
            params={
                "population_size": 4,
                "generations": 1,
                "crossover_prob": 0.8,
                "mutation_prob": 0.1,
                "tournament_size": 2,
                "seed": 7,
                "objective": "distance",
                "operators": {"mutation": ["relocate"]},
                "verbose": False,
            },
        )

        population = ga.initialize()

        self.assertEqual(len(population), 4)
        self.assertEqual(ga._historical_seed_population(), [])

    def test_aco_without_heuristic_uses_pheromone_only_path(self):
        search = ACOConfigSearch(
            {"mutation": ["relocate", "swap"]},
            evaluator=None,
            seed=1,
        )

        self.assertIsNone(search.heuristic_model)
        self.assertIn(
            search._choose_value("mutation", ["relocate", "swap"]),
            {"relocate", "swap"},
        )


if __name__ == "__main__":
    unittest.main()

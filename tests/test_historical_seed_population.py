import unittest

from core.constraints import capacity
from core.data.historical_solution_builder import HistoricalSolutionBuilder
from core.ga_framework import GAFramework
from core.hyperheuristic.dynamic_instance import DynamicInstance


class HistoricalSeedPopulationTests(unittest.TestCase):
    def setUp(self):
        config = {
            "instance": {
                "coordinates": {
                    0: [0, 0],
                    1: [1, 0],
                    2: [2, 0],
                    3: [3, 0],
                },
                "demand": {0: 0, 1: 1, 2: 1, 3: 1},
            },
            "fleet": {"capacity": 10},
            "constraints": {"problem_type": ["capacity"]},
        }
        self.instance = DynamicInstance(config, [capacity.check_capacity])
        self.previous_routes = [[1, 2], [3]]

    def test_builder_creates_feasible_historical_seed_population(self):
        builder = HistoricalSolutionBuilder(self.instance, ["capacity"])
        seeds = builder.build_seed_population(
            self.previous_routes,
            max_seeds=3,
            variants_per_seed=2,
            seed=7,
        )

        self.assertEqual(len(seeds), 3)
        for seed in seeds:
            self.assertTrue(self.instance.is_feasible(seed))

    def test_builder_uses_multiple_historical_route_sets(self):
        builder = HistoricalSolutionBuilder(self.instance, ["capacity"])
        route_sets = [
            [[1, 2], [3]],
            [[3, 2], [1]],
        ]

        seeds = builder.build_seed_population(
            route_sets,
            max_seeds=4,
            variants_per_seed=0,
            seed=7,
        )

        expected_first = builder.build_individual_from_routes(route_sets[0])
        expected_second = builder.build_individual_from_routes(route_sets[1])
        self.assertEqual(seeds, [expected_first, expected_second])

    def test_ga_initial_population_includes_historical_seed(self):
        params = {
            "population_size": 4,
            "generations": 1,
            "crossover_prob": 0.8,
            "mutation_prob": 0.1,
            "tournament_size": 2,
            "seed": 7,
            "objective": "distance",
            "operators": {"mutation": ["relocate"]},
            "constraints": ["capacity"],
            "historical_routes": self.previous_routes,
            "historical_seed_fraction": 0.5,
            "historical_variants_per_seed": 1,
            "verbose": False,
        }
        ga = GAFramework(self.instance, params=params)
        population = ga.initialize()
        expected = HistoricalSolutionBuilder(
            self.instance, ["capacity"]
        ).build_individual_from_routes(self.previous_routes)

        self.assertEqual(len(population), 4)
        self.assertEqual(population[0], expected)
        self.assertTrue(all(self.instance.is_feasible(chrom) for chrom in population))


if __name__ == "__main__":
    unittest.main()

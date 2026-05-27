import unittest

from core.constraints import capacity, time_window
from core.data import HistoricalDataLoader
from core.data.client_config_adapter import normalize_client_config
from core.hyperheuristic.aco_config_search import ACOConfigSearch
from core.hyperheuristic.configuration_evaluator import ConfigurationEvaluator
from core.hyperheuristic.configuration_space import build_compatible_configuration_space
from core.hyperheuristic.dynamic_instance import DynamicInstance


class DataDrivenComponentTests(unittest.TestCase):
    def base_config(self):
        return {
            "instance": {
                "coordinates": {0: [0, 0], 1: [1, 1], 2: [2, 2]},
                "demand": {0: 0, 1: 1, 2: 1},
                "ready_time": {0: 0, 1: 0, 2: 0},
                "due_time": {0: 100, 1: 100, 2: 100},
                "service_time": {0: 0, 1: 0, 2: 0},
            },
            "fleet": {"capacity": 10, "speed": 1.0},
            "constraints": {"problem_type": ["capacity", "time_window"]},
            "parameters": {
                "population_size": 4,
                "generations": 2,
                "crossover_prob": 0.8,
                "mutation_prob": 0.1,
                "tournament_size": 2,
                "seed": 7,
            },
            "data": {"previous_routes": [[1, 2]]},
            "objective": "distance",
        }

    def test_historical_loader_uses_instance_fields_without_inferring_variant(self):
        route_history = HistoricalDataLoader(self.base_config()).load()

        self.assertEqual(route_history.depot, 0)
        self.assertEqual(route_history.coordinates[1], (1.0, 1.0))
        self.assertEqual(route_history.previous_routes, [[1, 2]])
        self.assertEqual(route_history.previous_route_sets, [[[1, 2]]])

    def test_historical_loader_accepts_multiple_previous_route_sets(self):
        config = self.base_config()
        config["data"] = {
            "previous_route_sets": [
                [[1, 2]],
                [[2], [1]],
            ]
        }

        route_history = HistoricalDataLoader(config).load()

        self.assertIsNone(route_history.previous_routes)
        self.assertEqual(
            route_history.previous_route_sets,
            [
                [[1, 2]],
                [[2], [1]],
            ],
        )

    def test_client_records_file_gets_internal_solver_defaults(self):
        client_config = {
            "constraints": {"problem_type": ["capacity", "time_window"]},
            "fleet": {"capacity": 10, "speed": 1.0},
            "coordinates": {0: [0, 0], 1: [1, 1]},
            "demand": {0: 0, 1: 1},
            "ready_time": {0: 0, 1: 0},
            "due_time": {0: 100, 1: 100},
            "service_time": {0: 0, 1: 0},
            "previous_routes": [[1]],
            "previous_route_sets": [[[1]], [[1]]],
        }

        normalized, changed = normalize_client_config(client_config)

        self.assertTrue(changed)
        self.assertIn("parameters", normalized)
        self.assertIn("aco", normalized)
        self.assertEqual(normalized["instance"]["coordinates"][1], [1, 1])
        self.assertEqual(normalized["data"]["previous_routes"], [[1]])
        self.assertEqual(normalized["data"]["previous_route_sets"], [[[1]], [[1]]])
        self.assertEqual(normalized["parameters"]["crossover_prob"], 0.8)

    def test_configuration_space_filters_pd_operators_by_explicit_constraints(self):
        standard_space = build_compatible_configuration_space({"capacity", "time_window"})
        pd_space = build_compatible_configuration_space({"pickup_delivery"})

        self.assertEqual(standard_space["crossover"], ["route_based"])
        self.assertEqual(set(standard_space["mutation"]), {"relocate", "swap"})
        self.assertEqual(pd_space["crossover"], ["pd_route_based"])
        self.assertEqual(set(pd_space["mutation"]), {"pd_relocate", "pd_swap"})

    def test_aco_search_returns_feasible_lower_level_ga_result(self):
        config = self.base_config()
        constraints = {"capacity", "time_window"}
        instance = DynamicInstance(
            config,
            [capacity.check_capacity, time_window.check_time_windows],
        )
        space = build_compatible_configuration_space(constraints, config["parameters"])
        space["population_size"] = [4]
        space["generations"] = [2]
        space["tournament_size"] = [2]

        evaluator = ConfigurationEvaluator(
            instance,
            list(constraints),
            n_repetitions=1,
            base_seed=7,
        )
        result = ACOConfigSearch(
            space,
            evaluator,
            n_ants=1,
            n_iterations=1,
            seed=7,
        ).run()

        self.assertIn("best_configuration", result)
        self.assertTrue(result["best_evaluation"]["best_result"]["is_feasible"])


if __name__ == "__main__":
    unittest.main()

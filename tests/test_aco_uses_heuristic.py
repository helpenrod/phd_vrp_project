import unittest

from core.hyperheuristic.aco_config_search import ACOConfigSearch


class DummyEvaluator:
    def evaluate(self, ga_config):
        return {
            "score": 1.0,
            "mean_cost": 1.0,
            "best_cost": 1.0,
            "mean_feasibility_rate": 1.0,
            "mean_runtime": 0.0,
            "best_result": {
                "best_solution": [0],
                "best_cost": 1.0,
                "is_feasible": True,
                "runtime": 0.0,
            },
        }


class StrongHeuristic:
    def get_eta(self, decision, value):
        if decision == "mutation" and value == "relocate":
            return 100.0
        return 1.0


class ACOUsesHeuristicTests(unittest.TestCase):
    def test_heuristic_biases_value_selection_when_pheromones_are_equal(self):
        search = ACOConfigSearch(
            {"mutation": ["relocate", "swap"]},
            DummyEvaluator(),
            heuristic_model=StrongHeuristic(),
            beta=2.0,
            seed=3,
        )

        choices = [
            search._choose_value("mutation", ["relocate", "swap"])
            for _ in range(100)
        ]

        self.assertGreater(choices.count("relocate"), 95)

    def test_without_heuristic_model_selection_still_returns_valid_value(self):
        search = ACOConfigSearch(
            {"mutation": ["relocate", "swap"]},
            DummyEvaluator(),
            seed=3,
        )

        self.assertIn(
            search._choose_value("mutation", ["relocate", "swap"]),
            {"relocate", "swap"},
        )


if __name__ == "__main__":
    unittest.main()

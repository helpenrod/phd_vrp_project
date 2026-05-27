import unittest

from core.hyperheuristic.historical_heuristic_model import HistoricalHeuristicModel


class HistoricalHeuristicModelTests(unittest.TestCase):
    def test_high_capacity_usage_increases_capacity_sensitive_eta(self):
        model = HistoricalHeuristicModel(
            {"avg_capacity_usage": 0.9, "capacity_violation_rate": 0.0},
            ["capacity"],
        )

        self.assertGreater(model.get_eta("repair", "greedy_repair"), 1.0)
        self.assertGreater(model.get_eta("mutation", "relocate"), 1.0)
        self.assertEqual(model.get_eta("selection", "tournament"), 1.0)

    def test_pickup_delivery_constraints_favor_pd_operators(self):
        model = HistoricalHeuristicModel({}, ["pickup_delivery"])

        self.assertGreater(model.get_eta("mutation", "pd_relocate"), 1.0)
        self.assertGreater(model.get_eta("crossover", "pd_route_based"), 1.0)
        self.assertEqual(model.get_eta("mutation", "relocate"), 1.0)


if __name__ == "__main__":
    unittest.main()

import unittest

from core.constraints import capacity
from core.data.historical_metrics import HistoricalMetrics
from core.hyperheuristic.dynamic_instance import DynamicInstance


class HistoricalMetricsTests(unittest.TestCase):
    def setUp(self):
        config = {
            "instance": {
                "coordinates": {0: [0, 0], 1: [3, 4], 2: [6, 8]},
                "demand": {0: 0, 1: 4, 2: 7},
            },
            "fleet": {"capacity": 10},
            "constraints": {"problem_type": ["capacity"]},
        }
        self.instance = DynamicInstance(config, [capacity.check_capacity])
        self.metrics = HistoricalMetrics(self.instance, ["capacity"])

    def test_historical_cost_and_improvement_are_computed(self):
        historical_cost = self.metrics.compute_total_cost([[1], [2]])
        comparison = self.metrics.compute_improvement(historical_cost, 20.0)

        self.assertAlmostEqual(historical_cost, 30.0)
        self.assertEqual(comparison["absolute_improvement"], 10.0)
        self.assertAlmostEqual(comparison["percent_improvement"], 100.0 / 3.0)

    def test_feasibility_summary_counts_capacity_violations(self):
        summary = self.metrics.compute_feasibility_summary([[1, 2], [1]])

        self.assertEqual(summary["total_routes"], 2)
        self.assertEqual(summary["feasible_routes"], 1)
        self.assertEqual(summary["capacity_violations"], 1)

    def test_extract_metrics_contains_expected_keys(self):
        extracted = self.metrics.extract_metrics([[1], [2]])

        self.assertIn("avg_route_length", extracted)
        self.assertIn("avg_customers_per_route", extracted)
        self.assertIn("avg_capacity_usage", extracted)
        self.assertIn("historical_cost", extracted)

    def test_extract_metrics_averages_multiple_route_set_costs(self):
        extracted = self.metrics.extract_metrics([
            [[1], [2]],
            [[1, 2]],
        ])

        self.assertEqual(extracted["historical_route_sets"], 2)
        self.assertEqual(extracted["historical_costs"], [30.0, 20.0])
        self.assertEqual(extracted["historical_cost"], 25.0)


if __name__ == "__main__":
    unittest.main()

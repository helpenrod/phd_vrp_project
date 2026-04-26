import unittest

from core.hyperheuristic.hyperheuristic import HyperHeuristic
from core.hyperheuristic.blueprint import ConstraintSet


class OperatorSelectionTests(unittest.TestCase):
    def setUp(self):
        self.hh = HyperHeuristic()

    def assert_standard_operators(self, constraints):
        selected = self.hh._select_operators(constraints)

        self.assertEqual(selected["crossover"], "route_based")
        self.assertEqual(set(selected["mutation"]), {"relocate", "swap"})
        self.assert_no_pd_operators(selected)

    def assert_pd_aware_operators(self, constraints):
        selected = self.hh._select_operators(constraints)

        self.assertEqual(selected["crossover"], "pd_route_based")
        self.assertEqual(set(selected["mutation"]), {"pd_relocate", "pd_swap"})

    def assert_no_pd_operators(self, selected):
        selected_names = [selected["crossover"], *selected["mutation"]]
        pd_operators = [name for name in selected_names if name.startswith("pd_")]

        self.assertEqual(pd_operators, [])

    def test_capacity_only_selects_standard_operators(self):
        self.assert_standard_operators({"capacity"})

    def test_time_window_only_selects_standard_operators(self):
        self.assert_standard_operators({"time_window"})

    def test_pickup_delivery_variants_select_pd_aware_operators(self):
        pd_variants = [
            {"pickup_delivery"},
            {"capacity", "pickup_delivery"},
            {"time_window", "pickup_delivery"},
            {"capacity", "time_window", "pickup_delivery"},
        ]

        for constraints in pd_variants:
            with self.subTest(constraints=constraints):
                self.assert_pd_aware_operators(constraints)

    def test_non_pd_variants_never_select_pd_operators(self):
        non_pd_variants = [
            {"capacity"},
            {"time_window"},
            {"capacity", "time_window"},
        ]

        for constraints in non_pd_variants:
            with self.subTest(constraints=constraints):
                selected = self.hh._select_operators(constraints)
                self.assert_no_pd_operators(selected)

    def test_capacity_time_window_blueprint_uses_standard_components(self):
        blueprint = self.hh.generate_blueprint(
            ConstraintSet(frozenset({"capacity", "time_window"}))
        )

        self.assertEqual(blueprint.representation, "direct_route")
        self.assertEqual(blueprint.selection, ["tournament"])
        self.assertEqual(blueprint.crossover, ["route_based"])
        self.assertEqual(set(blueprint.mutation), {"relocate", "swap"})
        self.assertEqual(blueprint.repair, ["greedy_repair"])
        self.assertEqual(blueprint.local_search, ["2opt"])
        self.assertEqual(blueprint.evaluation, ["objective_cost"])
        self.assertEqual(blueprint.replacement, ["generational"])
        self.assertEqual(blueprint.termination, ["fixed_generations"])

    def test_pd_blueprint_uses_pd_aware_components(self):
        blueprint = self.hh.generate_blueprint(
            ConstraintSet(frozenset({"capacity", "time_window", "pickup_delivery"}))
        )

        self.assertEqual(blueprint.representation, "direct_route")
        self.assertEqual(blueprint.selection, ["tournament"])
        self.assertEqual(blueprint.crossover, ["pd_route_based"])
        self.assertEqual(set(blueprint.mutation), {"pd_relocate", "pd_swap"})
        self.assertEqual(blueprint.repair, ["greedy_repair"])
        self.assertEqual(blueprint.local_search, ["2opt"])
        self.assertEqual(blueprint.evaluation, ["objective_cost"])
        self.assertEqual(blueprint.replacement, ["generational"])
        self.assertEqual(blueprint.termination, ["fixed_generations"])


if __name__ == "__main__":
    unittest.main()

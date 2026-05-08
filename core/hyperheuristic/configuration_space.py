from copy import deepcopy


DEFAULT_PARAMETER_SPACE = {
    "crossover_prob": [0.7, 0.8, 0.9],
    "mutation_prob": [0.05, 0.1, 0.2],
    "population_size": [20, 50, 100],
    "generations": [50, 100, 200],
    "tournament_size": [2, 3, 5],
    "penalty_weight": [10, 50, 100],
}


def build_compatible_configuration_space(
    constraints: list[str] | set[str],
    base_parameters: dict | None = None,
) -> dict:
    """Build an ACO decision space using explicit VRP constraints only."""
    active_constraints = set(constraints)
    space = deepcopy(DEFAULT_PARAMETER_SPACE)

    space["selection"] = ["tournament"]

    if "pickup_delivery" in active_constraints:
        space["crossover"] = ["pd_route_based"]
        space["mutation"] = ["pd_relocate", "pd_swap"]
    else:
        space["crossover"] = ["route_based"]
        space["mutation"] = ["relocate", "swap"]

    space["repair"] = ["greedy_repair"]
    space["local_search"] = ["none", "2opt"]

    if base_parameters:
        for parameter_name in DEFAULT_PARAMETER_SPACE:
            if parameter_name in base_parameters:
                space[parameter_name] = _with_base_value(
                    DEFAULT_PARAMETER_SPACE[parameter_name],
                    base_parameters[parameter_name],
                )

    return space


def _with_base_value(values: list, base_value):
    normalized = [base_value]
    for value in values:
        if value not in normalized:
            normalized.append(value)
    return normalized

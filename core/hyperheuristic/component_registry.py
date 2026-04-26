from core.operators import crossover, mutation, repair, selection


COMPONENT_STAGES = [
    "initialization",
    "selection",
    "crossover",
    "mutation",
    "repair",
    "local_search",
    "evaluation",
    "replacement",
    "termination",
]


class ComponentRegistry:
    def __init__(self):
        self.components = {stage: [] for stage in COMPONENT_STAGES}

    def register(self, component):
        self.components[component.stage].append(component)

    def get_stage(self, stage: str):
        return self.components.get(stage, [])

    def resolve(self, stage: str, names: list[str]):
        components = {component.name: component for component in self.get_stage(stage)}
        return [components[name] for name in names if name in components]


def is_compatible(component, constraint_set, representation):
    required = getattr(component, "requires", set())
    forbidden = getattr(component, "forbids", set())
    supports = getattr(component, "supports", set())

    if getattr(component, "representation", None) != representation:
        return False
    if not constraint_set.has_all(required):
        return False
    if constraint_set.has_any(forbidden):
        return False
    if not constraint_set.constraints.issubset(supports):
        return False
    return True


def build_default_registry():
    registry = ComponentRegistry()

    for component in [
        selection.tournament_selection,
        crossover.route_based_crossover,
        crossover.pd_route_based_crossover,
        mutation.relocate_mutation,
        mutation.swap_mutation,
        mutation.pd_relocate_mutation,
        mutation.pd_swap_mutation,
        repair.greedy_repair,
    ]:
        registry.register(component)

    return registry

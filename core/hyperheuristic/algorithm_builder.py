from core.ga_framework import GAFramework


class AlgorithmBuilder:
    def __init__(self, registry):
        self.registry = registry

    def resolve(self, stage: str, names: list[str]):
        return self.registry.resolve(stage, names)

    def build(self, blueprint, instance, config):
        ga_config = dict(config["parameters"])
        ga_config["objective"] = config.get("objective", "distance")

        return GAFramework(
            instance=instance,
            config=ga_config,
            selection_ops=self.resolve("selection", blueprint.selection),
            crossover_ops=self.resolve("crossover", blueprint.crossover),
            mutation_ops=self.resolve("mutation", blueprint.mutation),
            repair_ops=self.resolve("repair", blueprint.repair),
            evaluation_ops=self.resolve("evaluation", blueprint.evaluation),
            replacement_ops=self.resolve("replacement", blueprint.replacement),
            termination_ops=self.resolve("termination", blueprint.termination),
            blueprint=blueprint,
        )

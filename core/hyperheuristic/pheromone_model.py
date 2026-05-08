class PheromoneModel:
    def __init__(self, configuration_space: dict, initial_pheromone: float = 1.0):
        self.pheromones = {
            decision: {value: float(initial_pheromone) for value in values}
            for decision, values in configuration_space.items()
        }

    def get(self, decision: str, value) -> float:
        return self.pheromones[decision][value]

    def evaporate(self, evaporation_rate: float) -> None:
        retention = 1.0 - evaporation_rate
        for values in self.pheromones.values():
            for value in values:
                values[value] = max(values[value] * retention, 1e-12)

    def reinforce(self, configuration: dict, reward: float) -> None:
        for decision, value in configuration.items():
            if decision in self.pheromones and value in self.pheromones[decision]:
                self.pheromones[decision][value] += reward

    def snapshot(self) -> dict:
        return {
            decision: dict(values)
            for decision, values in self.pheromones.items()
        }

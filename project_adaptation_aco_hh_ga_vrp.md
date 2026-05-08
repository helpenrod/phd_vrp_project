# Project Adaptation: Data-Driven ACO Hyper-Heuristic + GA Solver for VRP Variants

## Purpose

Adapt the current VRP hyper-heuristic project so it supports two working modes:

1. **Constraint-only mode**  
   If no client/historical data is provided, the system behaves as before:
   - The user explicitly provides the VRP variant/restrictions.
   - The framework selects compatible operators.
   - A generated/configured Genetic Algorithm solves the VRP.

2. **Data-driven ad-hoc mode**  
   If client/historical data is provided, the system uses the explicit variant/restrictions plus the data to tune the solver:
   - The user still explicitly provides the VRP variant/restrictions.
   - The system does **not** infer the variant from the data.
   - The upper level uses **Ant Colony Optimization (ACO)** to search for the best GA configuration.
   - The lower level uses a **Genetic Algorithm (GA)** to solve the VRP instance.
   - The best configuration is selected based on repeated runs and statistical/performance evaluation.

The final objective is:

> The lower-level GA searches in the space of routes.  
> The upper-level ACO searches in the space of GA configurations.

---

## Important Conceptual Decision

Do **not** infer the VRP variant from historical data.

The variant/restrictions must be explicit in the configuration file.

Example:

```yaml
constraints:
  - capacity
  - time_window
  - pickup_delivery
```

The historical data, if available, should only be used to adapt/tune the algorithm.

---

## Target Architecture

The adapted system should follow this structure:

```text
Explicit variants/restrictions
        +
Optional historical/client data
        ↓
Compatibility validation
        ↓
Operator and parameter search space
        ↓
Upper-level ACO hyper-heuristic
        ↓
Candidate GA configurations
        ↓
Lower-level GA execution
        ↓
Evaluation and statistical ranking
        ↓
Best ad-hoc solver configuration
```

---

## Required Project Behavior

### Case 1: No Historical Data Provided

When the config does not include a `data` or `historical_data` section, the system should use the existing behavior.

Expected pipeline:

```text
constraints → compatible operators → default/generated GA → solution
```

The current project behavior must remain valid.

This mode should be treated as the fallback mode.

---

### Case 2: Historical Data Provided

When the config includes historical/client data, activate the ACO upper-level search.

Expected pipeline:

```text
constraints + data → ACO upper level → tuned GA lower level → best configuration + solution
```

The data may include:
- coordinates
- demands
- time windows
- pickup-delivery pairs
- vehicle capacity
- depot
- previous routes
- service times
- route cost/distance/time if available
- feasibility information if available

However, the variant must still come from the explicit `constraints` section.

---

## Proposed Folder Structure

Add or adapt the following modules.

```text
core/
  hyperheuristic/
    __init__.py
    aco_config_search.py
    configuration_space.py
    configuration_evaluator.py
    pheromone_model.py
    statistics.py

  ga_framework/
    __init__.py
    ga_runner.py
    ga_config.py

  data/
    __init__.py
    historical_data_loader.py
    route_history.py
    data_validator.py

  utils/
    __init__.py
    random_control.py
    logging_utils.py
```

If some similar modules already exist, adapt them instead of duplicating functionality.

---

## Main New Components

## 1. Historical Data Loader

Create:

```text
core/data/historical_data_loader.py
```

Responsibilities:
- Load historical/client data from YAML, JSON, or CSV paths declared in config.
- Validate that required fields exist depending on explicit constraints.
- Return a normalized internal object.

Suggested class:

```python
class HistoricalDataLoader:
    def __init__(self, config: dict):
        self.config = config

    def has_historical_data(self) -> bool:
        ...

    def load(self) -> "RouteHistory":
        ...
```

---

## 2. Route History Object

Create:

```text
core/data/route_history.py
```

Suggested dataclass:

```python
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

@dataclass
class RouteHistory:
    coordinates: Dict[int, tuple]
    depot: int
    demands: Optional[Dict[int, float]] = None
    time_windows: Optional[Dict[int, tuple]] = None
    service_times: Optional[Dict[int, float]] = None
    pickup_delivery_pairs: Optional[List[tuple]] = None
    previous_routes: Optional[List[List[int]]] = None
    metadata: Optional[Dict[str, Any]] = None
```

This object should not decide the variant.  
It only stores data.

---

## 3. Configuration Space

Create:

```text
core/hyperheuristic/configuration_space.py
```

This module defines what the ACO can choose.

The ACO should construct GA configurations by choosing among:
- selection operators
- crossover operators
- mutation operators
- repair operators
- local search operators
- parameter values

Example search space:

```python
CONFIGURATION_SPACE = {
    "selection": ["tournament", "roulette", "rank"],
    "crossover": ["order_crossover", "route_exchange", "precedence_preserving"],
    "mutation": ["swap", "relocate", "inversion", "scramble"],
    "repair": ["capacity_repair", "time_window_repair", "pickup_delivery_repair"],
    "local_search": ["none", "two_opt", "relocate_ls"],
    "crossover_prob": [0.7, 0.8, 0.9],
    "mutation_prob": [0.05, 0.1, 0.15, 0.2],
    "population_size": [50, 100, 150],
    "generations": [100, 200, 300],
    "penalty_weight": [10, 50, 100]
}
```

The actual values must be adapted to the current project.

---

## 4. Compatibility Filtering

The configuration space must be filtered based on explicit constraints.

Examples:

If `capacity` is active:
- include capacity-aware repair
- include capacity penalty
- reject configurations that cannot handle capacity

If `time_window` is active:
- include time-window repair
- include time-window penalty
- reject configurations that ignore time feasibility

If `pickup_delivery` is active:
- include pickup-delivery repair
- use pickup-delivery-compatible crossover/mutation
- reject configurations that can break precedence without repair

Create a function like:

```python
def build_compatible_configuration_space(constraints: list[str]) -> dict:
    ...
```

---

## 5. ACO Upper-Level Search

Create:

```text
core/hyperheuristic/aco_config_search.py
```

The ACO searches for the best GA configuration.

Each ant constructs a candidate GA configuration by selecting one value from each decision component.

Example candidate:

```python
{
    "selection": "tournament",
    "crossover": "route_exchange",
    "mutation": "relocate",
    "repair": ["capacity_repair", "time_window_repair"],
    "local_search": "two_opt",
    "crossover_prob": 0.8,
    "mutation_prob": 0.1,
    "population_size": 100,
    "generations": 200,
    "penalty_weight": 50
}
```

ACO responsibilities:
- initialize pheromone values
- construct candidate configurations
- evaluate each candidate by running the lower-level GA
- update pheromones based on performance
- evaporate pheromones
- keep best configuration found

Suggested class:

```python
class ACOConfigSearch:
    def __init__(
        self,
        configuration_space: dict,
        evaluator,
        n_ants: int = 10,
        n_iterations: int = 20,
        evaporation_rate: float = 0.2,
        alpha: float = 1.0,
        beta: float = 1.0,
        seed: int | None = None,
    ):
        ...

    def run(self) -> dict:
        ...
```

---

## 6. Pheromone Model

Create:

```text
core/hyperheuristic/pheromone_model.py
```

Pheromones should be stored per decision/value pair.

Example:

```python
pheromones = {
    "selection": {
        "tournament": 1.0,
        "roulette": 1.0,
        "rank": 1.0
    },
    "mutation": {
        "swap": 1.0,
        "relocate": 1.0
    }
}
```

ACO should increase pheromone for components used in good configurations.

Basic update:

```python
pheromone = (1 - evaporation_rate) * pheromone + reward
```

Reward may be based on inverse cost:

```python
reward = 1 / (1 + score)
```

or normalized ranking.

---

## 7. Configuration Evaluator

Create:

```text
core/hyperheuristic/configuration_evaluator.py
```

This module evaluates a candidate GA configuration.

Responsibilities:
- receive a candidate configuration from ACO
- instantiate/run the lower-level GA using that configuration
- run multiple repetitions because GA is stochastic
- return performance metrics

Suggested class:

```python
class ConfigurationEvaluator:
    def __init__(
        self,
        instance,
        constraints: list[str],
        n_repetitions: int = 5,
        base_seed: int = 42,
    ):
        ...

    def evaluate(self, ga_config: dict) -> dict:
        ...
```

Returned metrics:

```python
{
    "mean_cost": ...,
    "std_cost": ...,
    "best_cost": ...,
    "mean_feasibility_rate": ...,
    "mean_runtime": ...,
    "score": ...
}
```

The `score` should be minimized by ACO.

Suggested score:

```python
score = mean_cost + infeasibility_penalty + runtime_penalty
```

Start simple.  
Do not implement complex statistical tests in the first version unless the rest is stable.

---

## 8. Lower-Level GA Runner

Create or adapt:

```text
core/ga_framework/ga_runner.py
```

The GA runner should accept a configuration dictionary generated by ACO.

Suggested interface:

```python
class GARunner:
    def __init__(self, instance, constraints: list[str], ga_config: dict, seed: int | None = None):
        ...

    def run(self) -> dict:
        ...
```

Returned result:

```python
{
    "best_solution": ...,
    "best_cost": ...,
    "is_feasible": ...,
    "runtime": ...,
    "history": ...
}
```

The GA runner should use the selected:
- selection operator
- crossover operator
- mutation operator
- repair operator
- local search
- parameter values

Do not hard-code one operator.

---

## 9. Statistics Module

Create:

```text
core/hyperheuristic/statistics.py
```

First version can include simple descriptive statistics:

```python
def summarize_results(results: list[dict]) -> dict:
    ...
```

Include:
- mean
- standard deviation
- best
- worst
- feasibility rate

Later, this can be extended with:
- Wilcoxon signed-rank test
- Friedman test
- Holm posthoc analysis

But do not overcomplicate the first implementation.

---

## Config Changes

Extend the experiment YAML config to support both modes.

Example:

```yaml
experiment:
  name: alg4_pdptw_aco_hh
  mode: auto

constraints:
  - capacity
  - time_window
  - pickup_delivery

instance:
  path: data/instances/example_pdptw.yaml

historical_data:
  enabled: true
  path: data/client/client_routes.yaml
  format: yaml

hyperheuristic:
  upper_level: aco
  lower_level: ga
  n_ants: 10
  n_iterations: 20
  evaporation_rate: 0.2
  alpha: 1.0
  beta: 1.0
  seed: 42

evaluation:
  n_repetitions: 5
  train_validation_split: 0.8
  objective: minimize_total_cost
  infeasibility_penalty: 100000
  runtime_weight: 0.0

ga_defaults:
  population_size: 100
  generations: 200
  crossover_prob: 0.8
  mutation_prob: 0.1
  elitism: 2
```

Behavior:
- If `historical_data.enabled: true`, use ACO upper level.
- If `historical_data.enabled: false` or section is missing, use previous constraint-only method.
- If `experiment.mode: constraint_only`, force previous behavior.
- If `experiment.mode: data_driven`, require historical data.
- If `experiment.mode: auto`, decide based on historical data availability.

---

## Main Execution Logic

Modify the main entry point, probably:

```text
core/main.py
```

Expected logic:

```python
def main():
    config = load_config()

    constraints = config["constraints"]

    historical_loader = HistoricalDataLoader(config)
    has_data = historical_loader.has_historical_data()

    mode = config.get("experiment", {}).get("mode", "auto")

    if mode == "constraint_only":
        run_constraint_only_pipeline(config, constraints)

    elif mode == "data_driven":
        if not has_data:
            raise ValueError("Data-driven mode requires historical_data.")
        run_data_driven_pipeline(config, constraints)

    elif mode == "auto":
        if has_data:
            run_data_driven_pipeline(config, constraints)
        else:
            run_constraint_only_pipeline(config, constraints)
```

---

## Data-Driven Pipeline

Suggested function:

```python
def run_data_driven_pipeline(config: dict, constraints: list[str]):
    instance = load_instance(config)
    route_history = HistoricalDataLoader(config).load()

    configuration_space = build_compatible_configuration_space(constraints)

    evaluator = ConfigurationEvaluator(
        instance=instance,
        constraints=constraints,
        n_repetitions=config["evaluation"].get("n_repetitions", 5),
        base_seed=config["hyperheuristic"].get("seed", 42),
    )

    search = ACOConfigSearch(
        configuration_space=configuration_space,
        evaluator=evaluator,
        n_ants=config["hyperheuristic"].get("n_ants", 10),
        n_iterations=config["hyperheuristic"].get("n_iterations", 20),
        evaporation_rate=config["hyperheuristic"].get("evaporation_rate", 0.2),
        alpha=config["hyperheuristic"].get("alpha", 1.0),
        beta=config["hyperheuristic"].get("beta", 1.0),
        seed=config["hyperheuristic"].get("seed", 42),
    )

    best_config = search.run()

    final_result = GARunner(
        instance=instance,
        constraints=constraints,
        ga_config=best_config,
        seed=config["hyperheuristic"].get("seed", 42),
    ).run()

    save_results(best_config, final_result)
```

---

## Results to Save

Create a results folder per experiment.

Example:

```text
results/
  alg4_pdptw_aco_hh/
    best_config.yaml
    final_solution.yaml
    aco_history.csv
    evaluation_summary.yaml
```

Save:
- best GA configuration found
- final best solution
- cost
- feasibility
- runtime
- ACO iteration history
- all tested configurations if possible

---

## Minimal First Implementation

Do not try to implement the full final research system at once.

First version should achieve:

1. Detect whether historical data exists.
2. If no data exists, run previous behavior.
3. If data exists, build compatible configuration space.
4. Run a simple ACO over GA configurations.
5. For each candidate configuration, run GA several times.
6. Rank candidate configurations by mean cost plus penalties.
7. Save best configuration.
8. Run final GA with best configuration.
9. Save results.

---

## Acceptance Tests

Create or adapt tests for the following.

### Test 1: Constraint-only fallback

Given a config with:

```yaml
historical_data:
  enabled: false
```

Expected:
- system does not run ACO
- system runs previous constraint-based GA pipeline
- no error

---

### Test 2: Auto mode without data

Given:

```yaml
experiment:
  mode: auto
```

and no `historical_data` section.

Expected:
- system runs constraint-only mode

---

### Test 3: Auto mode with data

Given:

```yaml
experiment:
  mode: auto

historical_data:
  enabled: true
  path: data/client/client_routes.yaml
```

Expected:
- system runs ACO upper-level search
- system returns best GA configuration
- system runs lower-level GA with best configuration

---

### Test 4: Explicit data-driven mode without data

Given:

```yaml
experiment:
  mode: data_driven
```

and no historical data.

Expected:
- system raises a clear error:
  `"Data-driven mode requires historical_data."`

---

### Test 5: Compatibility filtering

Given constraints:

```yaml
constraints:
  - capacity
  - time_window
  - pickup_delivery
```

Expected:
- compatible configuration space includes required repair/penalty components
- incompatible operators are removed or rejected

---

### Test 6: ACO output format

Expected best configuration must be a dictionary with keys like:

```python
{
    "selection": ...,
    "crossover": ...,
    "mutation": ...,
    "repair": ...,
    "local_search": ...,
    "crossover_prob": ...,
    "mutation_prob": ...,
    "population_size": ...,
    "generations": ...,
    "penalty_weight": ...
}
```

---

## Recommended Implementation Order

1. Add config mode detection.
2. Add `HistoricalDataLoader`.
3. Add `RouteHistory`.
4. Add `configuration_space.py`.
5. Add compatibility filtering.
6. Add `GARunner` interface that accepts dynamic GA configs.
7. Add `ConfigurationEvaluator`.
8. Add simple `ACOConfigSearch`.
9. Add saving of results.
10. Add tests.

---

## Scope Warning

Do not evolve Python code directly.

Evolve only GA configurations.

The ACO should not generate new source code.

It should generate dictionaries/configurations that define how the existing GA components are combined.

Correct:

```python
{
    "crossover": "route_exchange",
    "mutation": "relocate",
    "mutation_prob": 0.1
}
```

Avoid:

```python
def generated_algorithm(...):
    ...
```

The project can later move toward algorithm blueprint generation, but the first stable version should evolve configurations only.

---

## Final Research Interpretation

After this adaptation, the project can be described as:

> A data-driven hyper-heuristic framework for VRP variants where explicit constraints define the feasible operator space, an ACO upper level searches for high-performing GA configurations, and a GA lower level solves the resulting VRP instance. When historical data is unavailable, the system falls back to constraint-driven algorithm generation.

This keeps the project scientifically strong, modular, and implementable.

# Tagged Diagram Explanation: Modified VRP Hyper-Heuristic Process

This document explains the numbered connection tags in the updated Mermaid diagram for the modified VRP project.

The modified project has two modes:

1. **Constraint-only mode**: If no historical/client data is provided, the system behaves as before.
2. **Data-driven ad-hoc mode**: If historical/client data is provided, the system activates an ACO upper level to tune the GA configuration.

The central interpretation is:

> Historical data activates the ACO tuning layer.  
> Explicit restrictions define the variant.  
> The GA solves the routes.  
> The ACO searches for the best GA configuration.

---

## General startup and configuration reading

### 1 — Start the program

The process begins when you execute the project from the terminal, usually with something like:

```bash
python3 -m core.main variants/some_variant/config.yaml
```

This enters the project through `core/main.py`, specifically the `main()` function.

---

### 2 — Create the hyper-heuristic object and send it the problem file

`main()` does not solve the VRP directly. It creates a `HyperHeuristic` object and sends the config path to it using:

```python
hh.solve(problem_file)
```

From this point, the main logic moves into the hyper-heuristic layer.

---

### 3 — Load the experiment configuration

Inside `HyperHeuristic.solve()`, the system reads the YAML configuration file.

This file contains:

- explicit problem restrictions
- instance data
- fleet data
- GA parameters
- possibly historical/client data

---

### 4 — Normalize client-style configuration if needed

If the input config has a client-oriented format, the project converts it into the internal format expected by the solver.

This is important because future users may provide data in a more practical business format, not necessarily in the exact internal structure expected by the solver.

---

### 5 — Check whether historical data exists

The project checks if the config includes enabled historical/client data.

This is the decision point that separates the two modes:

- data-driven ACO mode
- previous constraint-only mode

---

## Historical data branch

### 6 — Historical data exists

If the config says that historical data is enabled, the project loads that data.

This does **not** mean the system will infer the VRP variant.

It only means the system has extra information to tune the algorithm.

---

### 7 — Normalize and validate historical data

The loaded data is converted into a standard `RouteHistory` structure.

This prevents the rest of the project from depending on many possible external data formats.

Validation checks that the data is coherent and usable.

---

### 8 — Merge historical data into the solver configuration

The normalized historical data is inserted into the internal solver configuration.

After this step, the GA and ACO components can access historical route information if needed.

---

## Constraint-only fallback branch

### 9 — No historical data exists

If no historical data is provided, the system does not use ACO.

It keeps the original config and continues with the previous project behavior:

```text
explicit restrictions → compatible operators → GA solver
```

---

## Explicit restriction handling

### 10 — Read restrictions after historical data was loaded

In the data-driven branch, after loading data, the system reads the explicit restrictions from the config.

These restrictions define the actual VRP variant:

- capacity
- time windows
- pickup-delivery
- or combinations of them

---

### 11 — Read restrictions in fallback mode

In the fallback branch, the system also reads the explicit restrictions from the config.

The important point is that both branches use the same source for the variant: the configuration file.

---

### 12 — Validate the problem definition

The system checks whether the explicit restrictions are consistent with the provided data.

Examples:

- If `capacity` is active, the instance should include demands and vehicle capacity.
- If `time_window` is active, customers should have time windows.
- If `pickup_delivery` is active, pickup-delivery pairs should be available.

---

### 13 — Stop if the problem is invalid

If the required fields are missing or inconsistent, the system raises a clear error instead of continuing with a wrong or incomplete problem definition.

---

### 14 — Continue if the problem is valid

If the configuration is valid, the system proceeds to create an algorithm blueprint.

This blueprint represents what kind of solver structure is needed for the selected restrictions.

---

## Blueprint and operator preparation

### 15 — Discover and select compatible operators

The project looks at the available operators in the repository and checks which ones are compatible with the active restrictions.

Example:

- pickup-delivery problems need operators or repairs that preserve pickup-before-delivery logic.
- time-window problems need operators, repairs, or penalties that can handle time feasibility.
- capacity problems need operators, repairs, or penalties that can handle vehicle capacity.

---

### 16 — Build primitive constraint checkers

The system prepares the functions that will later verify feasibility.

These are the checkers for:

- capacity
- time windows
- pickup-delivery
- any other active restriction

---

### 17 — Decide the solving branch

At this point, the system already knows the explicit restrictions and has prepared the constraint machinery.

Now it checks whether historical data was loaded.

- If yes, it enters the ACO upper-level branch.
- If not, it enters the previous GA-only branch.

---

# Data-driven branch: ACO upper level + GA lower level

### 18 — Enter the data-driven ACO pipeline

Since historical data exists, the project starts the new pipeline.

The goal here is not only to solve the VRP, but first to search for a good GA configuration for this specific problem/data context.

---

### 19 — Create the dynamic VRP instance

The project creates a `DynamicInstance`.

This object represents the VRP instance with:

- coordinates
- demands
- time windows
- pickup-delivery pairs
- constraint checkers

It is the object used by the GA to evaluate solutions.

---

### 20 — Build the compatible configuration space

The system creates the search space for the upper-level ACO.

This search space includes possible choices such as:

- crossover type
- mutation type
- repair method
- local search
- mutation probability
- crossover probability
- population size
- number of generations
- penalty weights

The search space is filtered by the explicit restrictions.

---

### 21 — Create the configuration evaluator

The evaluator is responsible for judging whether one GA configuration is good or bad.

It receives a candidate configuration from ACO, runs the lower-level GA several times, and summarizes the performance.

---

### 22 — Initialize the ACO search

The ACO search begins by creating pheromone values for each possible configuration choice.

For example, there may be pheromones for choosing:

- `relocate_mutation`
- `swap_mutation`
- `route_based_crossover`
- `two_opt`
- `capacity_repair`

---

### 23 — Run the ACO iterations

ACO starts its main loop.

In each iteration:

1. Several ants build candidate GA configurations.
2. Those configurations are evaluated.
3. The pheromone values are updated.

---

### 24 — Each ant constructs an internal configuration

Each ant chooses one option from each part of the configuration space.

Example:

```python
{
    "selection": "tournament",
    "crossover": "route_exchange",
    "mutation": "relocate",
    "repair": ["capacity_repair", "time_window_repair"],
    "local_search": "two_opt",
    "mutation_prob": 0.1
}
```

---

### 25 — Convert the internal ACO configuration into a GA configuration

The ant’s internal choices are transformed into the format expected by the GA runner.

This step is necessary because the ACO representation and the GA execution format may not be exactly the same.

---

### 26 — Evaluate the candidate configuration

The selected GA configuration is evaluated.

Because GA is stochastic, the same configuration should be tested multiple times with different seeds.

The evaluator computes:

- mean cost
- best cost
- feasibility rate
- runtime
- final score

---

### 27 — Lower-level GA solves the VRP routes

Now the lower-level GA actually solves the VRP instance using the candidate configuration selected by the ant.

This is where route chromosomes are evolved.

---

### 28 — GA performs its internal evolutionary cycle

Inside the lower-level GA, the usual genetic process happens:

1. Initialize population.
2. Select parents.
3. Apply crossover.
4. Apply mutation.
5. Repair if needed.
6. Evaluate individuals.
7. Keep or improve the best solution.

---

### 29 — Apply the selected operators

The GA does not use fixed operators.

It applies the operators selected by the current ACO candidate configuration.

For example:

- one candidate may use route-based crossover and relocate mutation
- another candidate may use a different crossover and swap mutation
- another may activate local search
- another may use a different mutation probability

---

### 30 — Summarize the candidate’s performance

After all repetitions of the lower-level GA are finished, the evaluator summarizes the results.

This gives the ACO a numerical way to compare one GA configuration against another.

---

### 31 — Update best configuration and pheromones

If a candidate configuration performs well, the ACO increases pheromone on the choices used by that configuration.

Poor configurations receive little or no reinforcement.

All pheromones are also partially evaporated to avoid premature convergence.

---

### 32 — Check ACO termination

The system checks whether the ACO has reached the maximum number of iterations or another stopping condition.

If not, the ACO continues searching.

---

### 33 — Continue ACO search

If the termination condition is not met, the system sends the process back to the ant construction step.

New ants build new candidate configurations using the updated pheromone information.

---

### 34 — Finish ACO search

If the termination condition is met, the ACO stops and returns the best GA configuration found during the search.

---

### 35 — Build a blueprint from the best GA configuration

The best ACO-generated configuration is converted back into an algorithm blueprint or selected-operator structure.

This makes it compatible with the rest of the project architecture.

---

### 36 — Save the data-driven experiment log

The project saves the result of the ACO search.

The saved information should include:

- best configuration
- performance history
- tested candidates
- final solution information
- final cost
- feasibility
- runtime

This is very important for thesis reproducibility.

---

# Constraint-only branch: previous behavior

### 37 — Assemble solver from blueprint

If no historical data was loaded, the project uses the existing hyper-heuristic pipeline.

It builds the solver from the blueprint and selected compatible operators.

---

### 38 — Initialize GA population

The GA creates the initial population of candidate routes.

This may include:

- random individuals
- greedy seeded routes
- any existing initialization logic in the project

---

### 39 — Evaluate individuals

Each individual solution is evaluated using cost and feasibility.

The dynamic instance checks:

- distance
- capacity
- time windows
- pickup-delivery precedence
- any other active restriction

---

### 40 — Check GA termination

The system checks whether the GA has reached the maximum number of generations or another stopping condition.

---

### 41 — Continue GA if not finished

If the GA is not done, it continues evolving the population.

---

### 42 — Generate the next population and return to evaluation

The GA selects parents, applies crossover, mutation, repair, and then evaluates the new individuals.

This loop continues until the GA termination condition is reached.

---

### 43 — Return the best individual

When the GA finishes, it returns the best solution found and saves the standard experiment log.

---

# Final output

### 44 — Return final result from the data-driven branch

After the ACO branch finishes, the system returns:

- the final instance
- the best solution
- the best cost

---

### 45 — Return final result from the constraint-only branch

After the fallback GA branch finishes, the system also returns:

- the final instance
- the best solution
- the best cost

---

### 46 — Print final solution

The main program receives the result and prints:

- final route structure
- total distance or cost
- feasibility information

---

### 47 — End the program

The execution finishes.

---

# Final interpretation

The most important interpretation is:

```text
Historical data does not define the variant.
Historical data activates the ACO tuning layer.

Explicit restrictions define the variant.
The GA solves the routes.
The ACO searches for the best GA configuration.
```

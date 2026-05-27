import json
import inspect
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import yaml
from core.operators import crossover, mutation

# NEW: Import the dynamic instance and primitive constraint checkers
from core.data import HistoricalDataLoader, HistoricalMetrics
from core.data.client_config_adapter import normalize_client_config
from core.hyperheuristic.aco_config_search import ACOConfigSearch
from core.hyperheuristic.algorithm_builder import AlgorithmBuilder
from core.hyperheuristic.blueprint import AlgorithmBlueprint, ConstraintSet
from core.hyperheuristic.component_registry import build_default_registry, is_compatible
from core.hyperheuristic.configuration_evaluator import ConfigurationEvaluator
from core.hyperheuristic.configuration_space import build_compatible_configuration_space
from core.hyperheuristic.dynamic_instance import DynamicInstance
from core.hyperheuristic.historical_heuristic_model import HistoricalHeuristicModel
from core.constraints import capacity, time_window, pickup_delivery

# NEW: Map constraint names to their primitive checker functions.
# This is the HH's knowledge base of primitive components.
CONSTRAINT_CHECKER_MAP = {
    'capacity': capacity.check_capacity,
    'time_window': time_window.check_time_windows,
    'pickup_delivery': pickup_delivery.check_pickup_delivery,
}

HISTORICAL_OPTION_DEFAULTS = {
    "use_as_seeds": True,
    "seed_fraction": 0.25,
    "variants_per_seed": 2,
    "compute_baseline": True,
    "use_heuristic_for_aco": True,
}

HISTORICAL_OPTION_KEYS = set(HISTORICAL_OPTION_DEFAULTS)

class HyperHeuristic:
    def __init__(self):
        self.available_operators = self._discover_operators()
        self.registry = build_default_registry()
        self.builder = AlgorithmBuilder(self.registry)
        self.last_selection_report = {}

    def _operator_metadata(self, func):
        """
        Reads explicit compatibility metadata from an operator.

        Legacy `tags` are treated as compatible constraints only, so older
        operators can still be discovered while newer operators can express
        required and forbidden constraints.
        """
        compatible_constraints = set(
            getattr(func, 'compatible_constraints', getattr(func, 'tags', set()))
        )
        return {
            'func': func,
            'required_constraints': set(getattr(func, 'required_constraints', set())),
            'forbidden_constraints': set(getattr(func, 'forbidden_constraints', set())),
            'compatible_constraints': compatible_constraints,
            'tags': set(getattr(func, 'tags', compatible_constraints)),
        }

    def _discover_operators(self):
        """
        Uses Python's inspection capabilities to find all functions in the
        operator packages and read their compatibility metadata.
        """
        discovered = {'crossover': [], 'mutation': []}
        
        for op_name, op_module in [('crossover', crossover), ('mutation', mutation)]:
            for name, func in inspect.getmembers(op_module, inspect.isfunction):
                if hasattr(func, 'compatible_constraints') or hasattr(func, 'tags'):
                    discovered[op_name].append(self._operator_metadata(func))
        
        return discovered

    @staticmethod
    def _format_constraints(constraints):
        if not constraints:
            return "none"
        return ", ".join(sorted(constraints))

    @staticmethod
    def _operator_name(func, operator_type):
        suffix = f"_{operator_type}"
        if func.__name__.endswith(suffix):
            return func.__name__[:-len(suffix)]
        return func.__name__

    def _load_config(self, problem_config_path):
        with open(problem_config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _detect_constraints(self, config):
        constraints_config = config.get('constraints', {})
        if isinstance(constraints_config, dict):
            constraints = constraints_config.get('problem_type', [])
        else:
            constraints = constraints_config or []
        problem_constraints = frozenset(constraints)
        if not problem_constraints:
            raise ValueError(
                "Problem file must specify a 'constraints.problem_type' list "
                "(e.g., ['capacity', 'time_window'])"
            )
        return problem_constraints

    def _build_constraint_set(self, config):
        return ConstraintSet(self._detect_constraints(config))

    def _validate_problem_definition(self, config, problem_constraints):
        unknown_constraints = problem_constraints.difference(CONSTRAINT_CHECKER_MAP)
        if unknown_constraints:
            raise NotImplementedError(
                "No constraint checker registered for: "
                f"{self._format_constraints(unknown_constraints)}"
            )

        if 'instance' not in config:
            raise ValueError("Problem file must define an 'instance' section.")
        if 'parameters' not in config:
            raise ValueError("Problem file must define a 'parameters' section.")

        instance_config = config['instance']
        fleet_config = config.get('fleet', {})

        if 'coordinates' not in instance_config:
            raise ValueError("Problem instance must define 'instance.coordinates'.")
        if 'capacity' in problem_constraints and 'capacity' not in fleet_config:
            raise ValueError("Capacity-constrained problems must define 'fleet.capacity'.")
        if 'time_window' in problem_constraints:
            missing_tw_fields = {
                field for field in ('ready_time', 'due_time')
                if field not in instance_config
            }
            if missing_tw_fields:
                raise ValueError(
                    "Time-window problems must define: "
                    f"{self._format_constraints(missing_tw_fields)}"
                )
        if 'pickup_delivery' in problem_constraints:
            has_pd_pairs = (
                'pickups' in instance_config
                or 'pickup_delivery_pairs' in instance_config
            )
            if not has_pd_pairs:
                raise ValueError(
                    "Pickup-delivery problems must define 'instance.pickups' "
                    "or 'instance.pickup_delivery_pairs'."
                )

    def _operator_compatibility(self, op, problem_constraints):
        required = op['required_constraints']
        forbidden = op['forbidden_constraints']
        compatible = op['compatible_constraints']

        missing_required = required.difference(problem_constraints)
        present_forbidden = forbidden.intersection(problem_constraints)
        incompatible_constraints = problem_constraints.difference(compatible)

        selected = (
            not missing_required
            and not present_forbidden
            and not incompatible_constraints
        )

        reasons = [
            f"detected constraints: {self._format_constraints(problem_constraints)}",
            f"required constraints satisfied: {self._format_constraints(required)}",
            f"forbidden constraints absent: {self._format_constraints(forbidden)}",
            f"compatible set covers detected constraints: {self._format_constraints(compatible)}",
        ]
        failures = []
        if missing_required:
            failures.append(
                f"missing required constraints: {self._format_constraints(missing_required)}"
            )
        if present_forbidden:
            failures.append(
                f"forbidden constraints present: {self._format_constraints(present_forbidden)}"
            )
        if incompatible_constraints:
            failures.append(
                f"unsupported constraints: {self._format_constraints(incompatible_constraints)}"
            )

        return selected, reasons, failures

    def _select_operators(self, problem_constraints):
        """
        Selects operators from the available pool that are compatible
        with the given problem constraints.
        """
        selected = {
            'selection': ['tournament'],
            'crossover': None,
            'mutation': [],
            'repair': ['greedy_repair'],
        }
        selection_report = {
            'selection': [{
                'name': 'tournament',
                'reasons': ['default parent selection for generated GA solvers'],
            }],
            'crossover': [],
            'mutation': [],
            'repair': [{
                'name': 'greedy_repair',
                'reasons': ['default insertion-based repair for generated GA solvers'],
            }],
        }
        problem_constraints = set(problem_constraints)

        # Select the first compatible crossover operator
        for op in self.available_operators['crossover']:
            is_compatible, reasons, _ = self._operator_compatibility(op, problem_constraints)
            if is_compatible:
                # Format the name to match what GAFramework expects (e.g., "route_based")
                op_name = self._operator_name(op['func'], 'crossover')
                selected['crossover'] = op_name
                selection_report['crossover'].append({
                    'name': op_name,
                    'reasons': reasons,
                })
                break
        
        # Select all compatible mutation operators
        for op in self.available_operators['mutation']:
            is_compatible, reasons, _ = self._operator_compatibility(op, problem_constraints)
            if is_compatible:
                op_name = self._operator_name(op['func'], 'mutation')
                selected['mutation'].append(op_name) # e.g., "relocate"
                selection_report['mutation'].append({
                    'name': op_name,
                    'reasons': reasons,
                })

        if not selected['crossover'] or not selected['mutation']:
            raise RuntimeError(f"Could not find compatible operators for constraints: {problem_constraints}")

        # For now, local search is hardcoded, but could be made dynamic later
        selected['local_search'] = ['2opt']
        selection_report['local_search'] = [{
            'name': '2opt',
            'reasons': ['default local search for generated GA solvers'],
        }]

        self.last_selection_report = selection_report
        return selected

    def generate_blueprint(self, constraint_set):
        representation = "direct_route"
        blueprint = AlgorithmBlueprint(representation=representation)

        for stage in blueprint.__dict__.keys():
            if stage == "representation":
                continue

            candidates = self.registry.get_stage(stage)
            compatible = [
                component for component in candidates
                if is_compatible(component, constraint_set, representation)
            ]

            if stage == "mutation":
                setattr(blueprint, stage, [component.name for component in compatible])
            elif compatible:
                setattr(blueprint, stage, [compatible[0].name])

        blueprint.initialization = ["greedy_seed"]
        blueprint.evaluation = ["objective_cost"]
        blueprint.replacement = ["generational"]
        blueprint.termination = ["fixed_generations"]
        blueprint.local_search = ["2opt"]
        return blueprint

    def generate_candidate_blueprints(self, constraint_set, limit=5):
        base = self.generate_blueprint(constraint_set)
        candidates = [base]

        for mutation_name in base.mutation:
            candidate = deepcopy(base)
            candidate.mutation = [mutation_name]
            candidates.append(candidate)

        no_local_search = deepcopy(base)
        no_local_search.local_search = []
        candidates.append(no_local_search)

        no_repair = deepcopy(base)
        no_repair.repair = []
        candidates.append(no_repair)

        unique_candidates = []
        seen = set()
        for candidate in candidates:
            fingerprint = json.dumps(candidate.to_dict(), sort_keys=True)
            if fingerprint not in seen:
                seen.add(fingerprint)
                unique_candidates.append(candidate)

        return unique_candidates[:limit]

    def _selected_ops_from_blueprint(self, blueprint):
        return {
            "selection": blueprint.selection,
            "crossover": blueprint.crossover[0] if blueprint.crossover else None,
            "mutation": blueprint.mutation,
            "repair": blueprint.repair,
            "local_search": blueprint.local_search,
        }

    def _build_constraint_checkers(self, problem_constraints):
        checkers_to_inject = []
        for constraint in problem_constraints:
            checker_func = CONSTRAINT_CHECKER_MAP[constraint]
            checkers_to_inject.append(checker_func)
        return checkers_to_inject

    def _assemble_solver(self, config, blueprint, checkers_to_inject):
        inst = DynamicInstance(config, checkers_to_inject)
        return inst, self.builder.build(blueprint, inst, config)

    def _save_generated_internal_config(self, problem_config_path, config):
        output_dir = Path("experiments/generated_configs")
        output_dir.mkdir(parents=True, exist_ok=True)

        config_stem = Path(problem_config_path).stem
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        output_path = output_dir / f"{timestamp}_{config_stem}_internal.yaml"

        with open(output_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config, f, sort_keys=False)

        return output_path

    def _merge_route_history_into_config(self, config, route_history):
        merged_config = deepcopy(config)
        instance_config = merged_config.setdefault('instance', {})
        fleet_config = merged_config.setdefault('fleet', {})

        instance_config.setdefault('coordinates', {
            node: list(coords) for node, coords in route_history.coordinates.items()
        })
        if route_history.demands is not None:
            instance_config.setdefault('demand', dict(route_history.demands))
        if route_history.time_windows is not None:
            instance_config.setdefault(
                'ready_time',
                {node: window[0] for node, window in route_history.time_windows.items()},
            )
            instance_config.setdefault(
                'due_time',
                {node: window[1] for node, window in route_history.time_windows.items()},
            )
        if route_history.service_times is not None:
            instance_config.setdefault('service_time', dict(route_history.service_times))
        if route_history.pickup_delivery_pairs is not None:
            instance_config.setdefault(
                'pickup_delivery_pairs',
                [
                    {'pickup': pickup, 'delivery': delivery}
                    for pickup, delivery in route_history.pickup_delivery_pairs
                ],
            )

        metadata = route_history.metadata or {}
        fleet_metadata = metadata.get('fleet', {})
        if isinstance(fleet_metadata, dict):
            for key, value in fleet_metadata.items():
                fleet_config.setdefault(key, value)
        if 'vehicle_capacity' in metadata:
            fleet_config.setdefault('capacity', metadata['vehicle_capacity'])
        if 'capacity' in metadata:
            fleet_config.setdefault('capacity', metadata['capacity'])

        return merged_config

    @staticmethod
    def _selected_ops_from_ga_config(ga_config):
        return {
            "selection": [ga_config.get("selection", "tournament")],
            "crossover": ga_config.get("crossover"),
            "mutation": [ga_config.get("mutation")]
            if isinstance(ga_config.get("mutation"), str)
            else ga_config.get("mutation", []),
            "repair": ga_config.get("repair", []),
            "local_search": ga_config.get("local_search", []),
        }

    @staticmethod
    def _blueprint_from_ga_config(ga_config):
        mutation = ga_config.get("mutation", [])
        if isinstance(mutation, str):
            mutation = [mutation]

        return AlgorithmBlueprint(
            representation="direct_route",
            initialization=["greedy_seed"],
            selection=[ga_config.get("selection", "tournament")],
            crossover=[ga_config.get("crossover")],
            mutation=mutation,
            repair=ga_config.get("repair", []),
            local_search=ga_config.get("local_search", []),
            evaluation=["objective_cost"],
            replacement=["generational"],
            termination=["fixed_generations"],
        )

    def _report_operator_selection(self, selected_ops, selection_report):
        print(f"HH: Selected operators: {selected_ops}")
        print("HH: Operator selection rationale:")

        for operator_type in ('selection', 'crossover', 'mutation', 'repair', 'local_search'):
            for entry in selection_report.get(operator_type, []):
                reason_text = "; ".join(entry['reasons'])
                print(f"  - {operator_type}.{entry['name']}: {reason_text}")

    def _log_experiment(
        self,
        problem_config_path,
        config,
        problem_constraints,
        selected_ops,
        blueprint,
        checkers_to_inject,
        inst,
        best_solution,
        best_cost,
        runtime_seconds,
        experiment_label=None,
        extra_log_data=None,
    ):
        log_dir = Path("experiments/logs")
        log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        config_stem = Path(problem_config_path).stem
        log_path = log_dir / f"{timestamp}_{config_stem}.json"

        routes = inst.split_chromosome(best_solution)
        route_strings = ["0-" + "-".join(map(str, r)) + "-0" for r in routes]
        feasible = inst.is_feasible(best_solution)

        log_data = {
            "timestamp_utc": timestamp,
            "config_path": str(problem_config_path),
            "problem_name": config.get("name"),
            "experiment_label": experiment_label,
            "constraints": sorted(problem_constraints),
            "selected_operators": selected_ops,
            "blueprint": blueprint.to_dict(),
            "algorithm_blueprint": blueprint.to_dict(),
            "operator_selection_report": self.last_selection_report,
            "constraint_checkers": [checker.__name__ for checker in checkers_to_inject],
            "seed": config.get("parameters", {}).get("seed"),
            "runtime_seconds": round(runtime_seconds, 6),
            "best_cost": float(best_cost),
            "best_solution_chromosome": best_solution,
            "best_routes": routes,
            "best_route_strings": route_strings,
            "feasible": feasible,
        }
        if extra_log_data:
            log_data.update(extra_log_data)

        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2)

        return log_path

    def _historical_options(self, config):
        options = dict(HISTORICAL_OPTION_DEFAULTS)

        for section_name in ("historical_data", "data", "historical_options"):
            section = config.get(section_name)
            if isinstance(section, dict):
                for key in HISTORICAL_OPTION_KEYS:
                    if key in section:
                        options[key] = section[key]

        options["use_as_seeds"] = bool(options["use_as_seeds"])
        options["compute_baseline"] = bool(options["compute_baseline"])
        options["use_heuristic_for_aco"] = bool(options["use_heuristic_for_aco"])
        options["seed_fraction"] = float(options["seed_fraction"])
        options["variants_per_seed"] = int(options["variants_per_seed"])
        return options

    def _save_historical_outputs(
        self,
        problem_config_path,
        comparison=None,
        metrics=None,
        heuristic_values=None,
    ):
        if comparison is None and metrics is None and heuristic_values is None:
            return None

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        config_stem = Path(problem_config_path).stem
        output_dir = Path("results") / f"{timestamp}_{config_stem}"
        output_dir.mkdir(parents=True, exist_ok=True)

        paths = {}
        payloads = {
            "historical_comparison": comparison,
            "historical_metrics": metrics,
            "aco_heuristic_values": heuristic_values,
        }
        for name, payload in payloads.items():
            if payload is None:
                continue
            path = output_dir / f"{name}.yaml"
            with open(path, "w", encoding="utf-8") as f:
                yaml.safe_dump(payload, f, sort_keys=False)
            paths[name] = str(path)

        return {
            "directory": str(output_dir),
            "files": paths,
        }

    def _solve_with_data_driven_aco(
        self,
        problem_config_path,
        config,
        problem_constraints,
        checkers_to_inject,
        start_time,
        route_history,
    ):
        print("HH: Historical data found; activating ACO configuration search.")
        inst = DynamicInstance(config, checkers_to_inject)
        parameters = config.get("parameters", {})
        aco_settings = config.get("aco", {})
        historical_options = self._historical_options(config)
        previous_routes = (
            route_history.previous_route_sets
            or ([route_history.previous_routes] if route_history.previous_routes else [])
        )
        use_historical_seeds = bool(
            previous_routes and historical_options["use_as_seeds"]
        )

        historical_metrics = None
        historical_comparison = None
        heuristic_model = None
        heuristic_values = None
        metrics_calculator = HistoricalMetrics(inst, list(problem_constraints))

        if previous_routes:
            historical_metrics = metrics_calculator.extract_metrics(previous_routes)

        if (
            previous_routes
            and historical_options["use_heuristic_for_aco"]
            and historical_metrics is not None
        ):
            heuristic_model = HistoricalHeuristicModel(
                historical_metrics=historical_metrics,
                constraints=list(problem_constraints),
            )

        configuration_space = build_compatible_configuration_space(
            problem_constraints,
            base_parameters=parameters,
        )
        if heuristic_model is not None:
            heuristic_values = heuristic_model.snapshot(configuration_space)

        print("Historical routes detected: yes")
        print(
            "Historical routes used as GA seeds: "
            f"{'yes' if use_historical_seeds else 'no'}"
        )
        print(
            "ACO heuristic model: "
            f"{'enabled' if heuristic_model is not None else 'disabled'}"
        )
        print(f"ACO beta: {float(aco_settings.get('beta', 1.0))}")

        evaluator = ConfigurationEvaluator(
            inst,
            list(problem_constraints),
            objective=config.get("objective", "distance"),
            n_repetitions=aco_settings.get("n_repetitions", 5),
            base_seed=parameters.get("seed", 42),
            historical_routes=previous_routes if use_historical_seeds else None,
            historical_seed_fraction=historical_options["seed_fraction"]
            if use_historical_seeds
            else 0.0,
            historical_variants_per_seed=historical_options["variants_per_seed"],
        )
        aco = ACOConfigSearch(
            configuration_space,
            evaluator,
            heuristic_model=heuristic_model,
            n_ants=aco_settings.get("n_ants", 10),
            n_iterations=aco_settings.get("n_iterations", 20),
            evaporation_rate=aco_settings.get("evaporation_rate", 0.2),
            alpha=aco_settings.get("alpha", 1.0),
            beta=aco_settings.get("beta", 1.0),
            seed=parameters.get("seed"),
        )

        search_result = aco.run()
        best_config = search_result["best_configuration"]
        best_evaluation = search_result["best_evaluation"]
        best_result = best_evaluation["best_result"]
        best_solution = best_result["best_solution"]
        best_cost = best_result["best_cost"]
        runtime_seconds = time.perf_counter() - start_time

        if previous_routes and historical_options["compute_baseline"]:
            historical_cost = (
                historical_metrics["historical_cost"]
                if historical_metrics is not None
                else metrics_calculator.compute_total_cost(previous_routes)
            )
            historical_comparison = metrics_calculator.compute_improvement(
                historical_cost,
                best_cost,
            )
            historical_comparison["historical_feasibility"] = (
                metrics_calculator.compute_feasibility_summary(previous_routes)
            )
            print(f"Historical route cost: {historical_cost:.2f}")
            print(f"Generated solution cost: {float(best_cost):.2f}")
            if historical_comparison["percent_improvement"] is not None:
                print(
                    "Improvement over historical routes: "
                    f"{historical_comparison['percent_improvement']:.2f}%"
                )

        historical_outputs = self._save_historical_outputs(
            problem_config_path,
            comparison=historical_comparison,
            metrics=historical_metrics,
            heuristic_values=heuristic_values,
        )

        blueprint = self._blueprint_from_ga_config(best_config)
        selected_ops = self._selected_ops_from_ga_config(best_config)
        aco_metrics = {
            key: value for key, value in best_evaluation.items()
            if key not in {"results", "best_result"}
        }

        log_path = self._log_experiment(
            problem_config_path,
            config,
            problem_constraints,
            selected_ops,
            blueprint,
            checkers_to_inject,
            inst,
            best_solution,
            best_cost,
            runtime_seconds,
            experiment_label="data_driven_aco",
            extra_log_data={
                "mode": "data_driven_aco",
                "aco_best_configuration": best_config,
                "aco_best_metrics": aco_metrics,
                "aco_history": search_result["history"],
                "historical_data_metadata": route_history.metadata or {},
                "historical_options": historical_options,
                "historical_metrics": historical_metrics,
                "historical_comparison": historical_comparison,
                "aco_heuristic_values": heuristic_values,
                "historical_output": historical_outputs,
            },
        )
        print(f"HH: Best ACO GA configuration: {best_config}")
        print(f"HH: Best ACO score: {best_evaluation['score']:.4f}")
        print(f"HH: Experiment log saved to {log_path}")

        return inst, best_solution, best_cost

    def solve(self, problem_config_path: str):
        """
        The main entry point for the HH. It reads a problem file, selects
        components, and runs the solver.
        """
        start_time = time.perf_counter()
        config = self._load_config(problem_config_path)
        config, generated_internal_config = normalize_client_config(config)
        if generated_internal_config:
            generated_path = self._save_generated_internal_config(problem_config_path, config)
            print(f"HH: Generated internal solver config saved to {generated_path}")

        data_loader = HistoricalDataLoader(config, base_path=Path(problem_config_path).parent)
        route_history = None
        if data_loader.has_historical_data():
            route_history = data_loader.load()
            config = self._merge_route_history_into_config(config, route_history)

        constraint_set = self._build_constraint_set(config)
        problem_constraints = constraint_set.constraints
        print(f"HH: Detected constraints: {list(problem_constraints)}")

        self._validate_problem_definition(config, problem_constraints)
        print("HH: Problem definition validated.")

        blueprint = self.generate_blueprint(constraint_set)
        print(f"HH: Generated algorithm blueprint: {blueprint.to_dict()}")

        selected_ops = self._selected_ops_from_blueprint(blueprint)
        self._select_operators(problem_constraints)
        self._report_operator_selection(selected_ops, self.last_selection_report)

        checkers_to_inject = self._build_constraint_checkers(problem_constraints)
        print(f"HH: Generating instance with checkers: {[c.__name__ for c in checkers_to_inject]}")

        if route_history is not None:
            return self._solve_with_data_driven_aco(
                problem_config_path,
                config,
                problem_constraints,
                checkers_to_inject,
                start_time,
                route_history,
            )

        inst, ga = self._assemble_solver(config, blueprint, checkers_to_inject)
        print("HH: Solver assembled.")
        best_solution, best_cost = ga.run()
        runtime_seconds = time.perf_counter() - start_time

        log_path = self._log_experiment(
            problem_config_path,
            config,
            problem_constraints,
            selected_ops,
            blueprint,
            checkers_to_inject,
            inst,
            best_solution,
            best_cost,
            runtime_seconds,
        )
        print(f"HH: Experiment log saved to {log_path}")

        return inst, best_solution, best_cost

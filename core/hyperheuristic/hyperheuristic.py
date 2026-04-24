import json
import inspect
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml
from core.ga_framework import GAFramework
from core.operators import crossover, mutation

# NEW: Import the dynamic instance and primitive constraint checkers
from core.hyperheuristic.dynamic_instance import DynamicInstance
from core.constraints import capacity, time_window, pickup_delivery

# NEW: Map constraint names to their primitive checker functions.
# This is the HH's knowledge base of primitive components.
CONSTRAINT_CHECKER_MAP = {
    'capacity': capacity.check_capacity,
    'time_window': time_window.check_time_windows,
    'pickup_delivery': pickup_delivery.check_pickup_delivery,
}

class HyperHeuristic:
    def __init__(self):
        self.available_operators = self._discover_operators()
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
        problem_constraints = frozenset(constraints_config.get('problem_type', []))
        if not problem_constraints:
            raise ValueError(
                "Problem file must specify a 'constraints.problem_type' list "
                "(e.g., ['capacity', 'time_window'])"
            )
        return problem_constraints

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
        selected = {'crossover': None, 'mutation': []}
        selection_report = {'crossover': [], 'mutation': []}
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

    def _build_constraint_checkers(self, problem_constraints):
        checkers_to_inject = []
        for constraint in problem_constraints:
            checker_func = CONSTRAINT_CHECKER_MAP[constraint]
            checkers_to_inject.append(checker_func)
        return checkers_to_inject

    def _assemble_solver(self, config, selected_ops, checkers_to_inject):
        inst = DynamicInstance(config, checkers_to_inject)

        ga_params = dict(config['parameters'])
        ga_params['operators'] = selected_ops
        ga_params['objective'] = config.get('objective', 'distance')

        return inst, GAFramework(inst, ga_params)

    def _report_operator_selection(self, selected_ops, selection_report):
        print(f"HH: Selected operators: {selected_ops}")
        print("HH: Operator selection rationale:")

        for operator_type in ('crossover', 'mutation', 'local_search'):
            for entry in selection_report.get(operator_type, []):
                reason_text = "; ".join(entry['reasons'])
                print(f"  - {operator_type}.{entry['name']}: {reason_text}")

    def _log_experiment(
        self,
        problem_config_path,
        config,
        problem_constraints,
        selected_ops,
        checkers_to_inject,
        inst,
        best_solution,
        best_cost,
        runtime_seconds,
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
            "constraints": sorted(problem_constraints),
            "selected_operators": selected_ops,
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

        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2)

        return log_path

    def solve(self, problem_config_path: str):
        """
        The main entry point for the HH. It reads a problem file, selects
        components, and runs the solver.
        """
        start_time = time.perf_counter()
        config = self._load_config(problem_config_path)

        problem_constraints = self._detect_constraints(config)
        print(f"HH: Detected constraints: {list(problem_constraints)}")

        self._validate_problem_definition(config, problem_constraints)
        print("HH: Problem definition validated.")

        selected_ops = self._select_operators(problem_constraints)
        self._report_operator_selection(selected_ops, self.last_selection_report)

        checkers_to_inject = self._build_constraint_checkers(problem_constraints)
        print(f"HH: Generating instance with checkers: {[c.__name__ for c in checkers_to_inject]}")

        inst, ga = self._assemble_solver(config, selected_ops, checkers_to_inject)
        print("HH: Solver assembled.")
        best_solution, best_cost = ga.run()
        runtime_seconds = time.perf_counter() - start_time

        log_path = self._log_experiment(
            problem_config_path,
            config,
            problem_constraints,
            selected_ops,
            checkers_to_inject,
            inst,
            best_solution,
            best_cost,
            runtime_seconds,
        )
        print(f"HH: Experiment log saved to {log_path}")

        return inst, best_solution, best_cost

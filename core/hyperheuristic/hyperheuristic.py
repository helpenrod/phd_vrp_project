import inspect
import yaml
from core.ga_framework import GAFramework
from core.operators import crossover, mutation, selection

# NEW: Import the dynamic instance and primitive constraint checkers
from core.hyperheuristic.dynamic_instance import DynamicInstance
from core.constraints import capacity, time_window

# NEW: Map constraint names to their primitive checker functions.
# This is the HH's knowledge base of primitive components.
CONSTRAINT_CHECKER_MAP = {
    'capacity': capacity.check_capacity,
    'time_window': time_window.check_time_windows,
}

class HyperHeuristic:
    def __init__(self):
        self.available_operators = self._discover_operators()

    def _discover_operators(self):
        """
        Uses Python's inspection capabilities to find all functions in the
        operator packages and read their associated 'tags'.
        """
        discovered = {'crossover': [], 'mutation': []}
        
        for op_name, op_module in [('crossover', crossover), ('mutation', mutation)]:
            for name, func in inspect.getmembers(op_module, inspect.isfunction):
                if hasattr(func, 'tags'):
                    discovered[op_name].append({'func': func, 'tags': func.tags})
        
        return discovered

    def _select_operators(self, problem_constraints):
        """
        Selects operators from the available pool that are compatible
        with the given problem constraints.
        """
        selected = {'crossover': None, 'mutation': []}
        problem_constraints = set(problem_constraints)

        # Select the first compatible crossover operator
        for op in self.available_operators['crossover']:
            if op['tags'].issuperset(problem_constraints):
                # Format the name to match what GAFramework expects (e.g., "route_based")
                op_name = op['func'].__name__.replace('_crossover', '')
                selected['crossover'] = op_name
                break
        
        # Select all compatible mutation operators
        for op in self.available_operators['mutation']:
            if op['tags'].issuperset(problem_constraints):
                selected['mutation'].append(op['func'].__name__.replace('_mutation', '')) # e.g., "relocate"

        if not selected['crossover'] or not selected['mutation']:
            raise RuntimeError(f"Could not find compatible operators for constraints: {problem_constraints}")

        # For now, local search is hardcoded, but could be made dynamic later
        selected['local_search'] = ['2opt']
        
        return selected

    def solve(self, problem_config_path: str):
        """
        The main entry point for the HH. It reads a problem file, selects
        components, and runs the solver.
        """
        # 1. Load the user's problem definition
        with open(problem_config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # 2. Detect Constraints from the problem file
        constraints_config = config.get('constraints', {})
        problem_constraints = frozenset(constraints_config.get('problem_type', []))
        if not problem_constraints:
            raise ValueError("Problem file must specify a 'constraints.problem_type' list (e.g., ['capacity', 'time_window'])")

        # 3. Select Operators based on constraints
        print(f"HH: Detected constraints: {list(problem_constraints)}")
        selected_ops = self._select_operators(problem_constraints)
        print(f"HH: Selected operators: {selected_ops}")

        # 4. GENERATE the list of constraint checkers
        checkers_to_inject = []
        for constraint in problem_constraints:
            checker_func = CONSTRAINT_CHECKER_MAP.get(constraint)
            if checker_func:
                checkers_to_inject.append(checker_func)
            else:
                raise NotImplementedError(f"No constraint checker registered for: {constraint}")
        print(f"HH: Generating instance with checkers: {[c.__name__ for c in checkers_to_inject]}")

        # 5. Instantiate the DynamicInstance with the generated checkers
        inst = DynamicInstance(config, checkers_to_inject)

        # 6. Configure and Run the GA Framework
        ga_params = config['parameters']
        ga_params['operators'] = selected_ops # Override operators with the HH's choice
        ga_params['objective'] = config.get('objective', 'distance') # Pass the objective to the framework

        ga = GAFramework(inst, ga_params)
        best_solution, best_cost = ga.run()

        return inst, best_solution, best_cost
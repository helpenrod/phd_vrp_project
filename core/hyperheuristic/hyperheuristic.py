# The core Hyper-Heuristic (HH) class.
# This class is responsible for the intelligent selection of components.
import yaml
import inspect

from core.ga_framework import GAFramework
from core.operators import crossover, mutation, selection

# --- Mapping constraints to the correct Instance class ---
# This is a simple knowledge base for the HH.
# It tells the HH which Instance class to use for a given set of constraints.
from variants.alg1_cvrp.cvrp_instance import CVRPInstance
from variants.alg2_vrptw.vrptw_twonly_instance import VRPTWInstance_TWOnly
from variants.alg3_vrptwc.vrptw_instance import VRPTWInstance

INSTANCE_MAP = {
    frozenset(['capacity']): CVRPInstance,
    frozenset(['time_window']): VRPTWInstance_TWOnly,
    frozenset(['capacity', 'time_window']): VRPTWInstance,
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

        # 4. Select and Instantiate the correct Instance class
        InstanceClass = INSTANCE_MAP.get(problem_constraints)
        if not InstanceClass:
            raise NotImplementedError(f"No instance class registered for constraint set: {problem_constraints}")
        
        # Create the instance object from the config data
        inst_data = config['instance']
        fleet_data = config.get('fleet', {})
        allow_split = constraints_config.get('split_delivery', False)
        inst = InstanceClass(
            coords=inst_data['coordinates'],
            demand=inst_data.get('demand'),
            capacity=fleet_data.get('capacity'),
            ready_time=inst_data.get('ready_time'),
            due_time=inst_data.get('due_time'),
            service_time=inst_data.get('service_time'),
            speed=fleet_data.get('speed', 1.0),
            allow_split_delivery=allow_split
        )

        # 5. Configure and Run the GA Framework
        ga_params = config['parameters']
        ga_params['operators'] = selected_ops # Override operators with the HH's choice
        ga_params['objective'] = config.get('objective', 'distance') # Pass the objective to the framework

        ga = GAFramework(inst, ga_params)
        best_solution, best_cost = ga.run()

        return inst, best_solution, best_cost
# Core Genetic Algorithm Framework
# This is a generic, configurable GA that can be applied to different VRP variants.
# It is configured by a `params` dictionary and uses an `instance` object for
# all problem-specific operations (cost, feasibility, etc.).
import random
from copy import deepcopy

# Import the operator packages. The __init__.py files make the functions available.
from core.operators import crossover
from core.operators import mutation
from core.operators import selection

DEPOT = 0

class GAFramework:
    def __init__(
        self,
        instance,
        params: dict = None,
        config: dict = None,
        initialization_ops=None,
        selection_ops=None,
        crossover_ops=None,
        mutation_ops=None,
        repair_ops=None,
        evaluation_ops=None,
        replacement_ops=None,
        termination_ops=None,
        blueprint=None,
    ):
        """
        instance: A problem instance object (e.g., CVRPInstance, VRPTWInstance)
                  that provides methods like `total_cost`, `is_feasible`, etc.
        params: A dictionary of GA parameters, including operator selection.
        """
        if params is None:
            params = config or {}

        self.inst = instance
        self.pop_size = int(params["population_size"])
        self.gens = int(params["generations"])
        self.pc = float(params["crossover_prob"])
        self.pm = float(params["mutation_prob"])
        self.tournament_k = int(params["tournament_size"])
        random.seed(int(params["seed"]))
        self.blueprint = blueprint
        self.initialization_ops = initialization_ops or []
        self.repair_ops = repair_ops or []
        self.evaluation_ops = evaluation_ops or []
        self.replacement_ops = replacement_ops or []
        self.termination_ops = termination_ops or []

        # --- DYNAMIC OBJECTIVE FUNCTION SELECTION ---
        objective = params.get("objective", "distance").lower()
        if objective == "distance":
            self.cost_function = self.inst.total_distance_cost
        elif objective == "time":
            self.cost_function = self.inst.total_time_cost
        else:
            raise ValueError(f"Unknown objective function: {objective}")
        # All future cost evaluations will use self.cost_function

        # --- HYPER-HEURISTIC OPERATOR SELECTION ---
        ops = params.get("operators", {})
        
        # Dynamic Crossover Selection (Allows HH to inject 'pd_route_based')
        if crossover_ops:
            self.crossover_op = crossover_ops[0]
        else:
            cx_name = str(ops.get("crossover", "route_based")).lower()
            self.crossover_op = getattr(crossover, f"{cx_name}_crossover", crossover.route_based_crossover)

        # Dynamic Mutation Selection
        self.mutation_ops = list(mutation_ops or [])
        if not self.mutation_ops:
            mutation_names = ops.get("mutation", ["relocate", "swap"])
            for m_name in mutation_names:
                op_func = getattr(mutation, f"{m_name}_mutation", None)
                if op_func:
                    self.mutation_ops.append(op_func)

        self.selection_op = selection_ops[0] if selection_ops else selection.tournament_selection

        # Local Search
        if blueprint is not None:
            self.use_2opt = "2opt" in blueprint.local_search
        else:
            self.use_2opt = "2opt" in ops.get("local_search", [])

    # ---------- population init ----------
    def _greedy_seed_routes(self, customers):
        """Greedy packing using the instance's cheapest feasible insertion."""
        routes = []
        # The instance's insertion method will respect its specific constraints
        for c in customers:
            res = self.inst.cheapest_feasible_insertion(routes, c)
            r_idx, p_pos, d_pos, _ = res
            
            if r_idx is not None:
                if r_idx == len(routes):
                    new_r = [c, self.inst.pd_pairs[c]] if c in self.inst.pd_pairs else [c]
                    routes.append(new_r)
                else:
                    routes[r_idx].insert(p_pos, c)
                    if d_pos is not None:
                        routes[r_idx].insert(d_pos, self.inst.pd_pairs[c])
            else:
                # If no insertion is possible, try to form a new route
                # The instance's feasibility check will handle this
                if self.inst.is_feasible_routes([[c]]):
                    routes.append([c])
                else:
                    # Fallback: let repair handle it
                    routes.append([c])
        return routes

    def initialize(self):
        # For PD problems, we only iterate over pickup nodes; 
        # the insertion logic handles the corresponding delivery.
        if hasattr(self.inst, 'pd_pairs') and self.inst.pd_pairs:
            customers = [k for k in self.inst.demand.keys() if k != DEPOT and k not in self.inst.delivery_to_pickup]
        else:
            customers = [k for k in self.inst.demand.keys() if k != DEPOT]
            
        pop = []
        for _ in range(self.pop_size):
            random.shuffle(customers)
            routes = self._greedy_seed_routes(customers)
            chrom = self.inst.routes_to_chromosome(routes)
            pop.append(chrom)
        return pop

    # ---------- evaluation ----------
    def evaluate(self, chrom):
        if not self.inst.is_feasible(chrom):
            if self.repair_ops:
                for repair_op in self.repair_ops:
                    chrom = repair_op(chrom, self)
            elif self.blueprint is None:
                chrom = self._repair(chrom)
        return self.cost_function(chrom), chrom

    # ---------- selection (delegated) ----------
    def tournament(self, pop):
        return self.selection_op(pop, self.tournament_k, self.cost_function)

    # ---------- crossover (delegated) ----------
    def crossover(self, p1, p2):
        return self.crossover_op(p1, p2, self.inst)

    # ---------- mutation (delegated) ----------
    def mutate(self, chrom):
        if random.random() > self.pm:
            return chrom
        
        routes = self.inst.split_chromosome(chrom)

        # Choose one of the available mutation operators to apply.
        if self.mutation_ops:
            op_to_apply = random.choice(self.mutation_ops)
            routes = op_to_apply(routes, self.inst)

        chrom = self.inst.routes_to_chromosome(routes)

        # Optional local search
        if self.use_2opt:
            routes = self.inst.split_chromosome(chrom)
            if routes:
                ri = random.randrange(len(routes))
                routes[ri] = self._two_opt_intra_guarded(routes[ri])
                chrom = self.inst.routes_to_chromosome(routes)

        return chrom

    # ---------- local search helper ----------
    def _two_opt_intra_guarded(self, route):
        """2-opt improvement for ONE route, guarded by instance feasibility."""
        best = route[:]
        best_cost = self.inst.route_cost(best)
        n = len(route)
        improved = True
        while improved:
            improved = False
            for i in range(n-1):
                for k in range(i+1, n):
                    cand = best[:i] + list(reversed(best[i:k+1])) + best[k+1:]
                    # The instance's feasibility check handles all constraints
                    if not self.inst.is_feasible_routes([cand]):
                        continue
                    c = self.inst.route_cost(cand)
                    if c + 1e-9 < best_cost:
                        best, best_cost = cand, c
                        improved = True
                        break
                if improved:
                    break
        return best

    # ---------- repair ----------
    def _repair(self, chrom):
        """A light repair mechanism using the instance's insertion heuristic."""
        routes = [r[:] for r in self.inst.split_chromosome(chrom)]
        unassigned = []
        
        # Find all customers in infeasible routes and add them to a pool
        feasible_routes = []
        for r in routes:
            if self.inst.is_feasible_routes([r]):
                feasible_routes.append(r)
            else:
                unassigned.extend(r)

        # Greedily re-insert unassigned customers
        for c in unassigned:
            # Avoid redundant insertion for deliveries (handled with pickups)
            if hasattr(self.inst, 'delivery_to_pickup') and c in self.inst.delivery_to_pickup:
                continue
                
            res = self.inst.cheapest_feasible_insertion(feasible_routes, c)
            r_idx, p_pos, d_pos, _ = res
            if r_idx is not None:
                feasible_routes[r_idx].insert(p_pos, c)
                if d_pos is not None:
                    feasible_routes[r_idx].insert(d_pos, self.inst.pd_pairs[c])
            elif self.inst.is_feasible_routes([[c]]):
                feasible_routes.append([c])
        
        return self.inst.routes_to_chromosome(feasible_routes)

    # ---------- GA loop ----------
    def run(self):
        pop = self.initialize()
        scores = [self.cost_function(ind) for ind in pop]

        best_idx = min(range(len(pop)), key=lambda i: scores[i])
        best, best_fit = deepcopy(pop[best_idx]), scores[best_idx]

        for g in range(self.gens):
            new_pop = []
            while len(new_pop) < self.pop_size:
                p1 = self.tournament(pop)
                p2 = self.tournament(pop)
                child = deepcopy(p1)
                if random.random() < self.pc:
                    child = self.crossover(p1, p2)
                child = self.mutate(child)
                f, child = self.evaluate(child)
                new_pop.append(child)

            pop = new_pop
            scores = [self.cost_function(ind) for ind in pop]
            cur_idx = min(range(len(pop)), key=lambda i: scores[i])
            if scores[cur_idx] + 1e-9 < best_fit:
                best_fit = scores[cur_idx]
                best = deepcopy(pop[cur_idx])

            if g % 20 == 0:
                print(f"Gen {g}: best cost = {best_fit:.2f}")

        return best, best_fit

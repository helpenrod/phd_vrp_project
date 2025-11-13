# A dynamic, composable VRP Instance class for the generative hyper-heuristic.
# This class is configured at runtime with a set of constraint-checking functions.
import math
import itertools

DEPOT = 0

class DynamicInstance:
    def __init__(self, config: dict, constraint_checkers: list):
        """
        Initializes a dynamic instance from a config dictionary and a list of
        constraint-checking functions provided by the hyper-heuristic.
        """
        inst_data = config['instance']
        fleet_data = config.get('fleet', {})
        constraints_config = config.get('constraints', {})

        # --- Data Loading ---
        coords = {int(k): tuple(v) for k, v in inst_data['coordinates'].items()}
        demand = {int(k): float(v) for k, v in inst_data.get('demand', {}).items()}
        ready_time = {int(k): float(v) for k, v in inst_data.get('ready_time', {}).items()}
        due_time = {int(k): float(v) for k, v in inst_data.get('due_time', {}).items()}
        service_time = {int(k): float(v) for k, v in inst_data.get('service_time', {}).items()}

        self.capacity = float(fleet_data.get('capacity', float('inf')))
        self.speed = float(fleet_data.get('speed', 1.0))
        self.allow_split_delivery = bool(constraints_config.get('split_delivery', False))

        self.original_map = {}

        # Preprocess data (e.g., split demands)
        self.coords, self.demand, self.ready_time, self.due_time, self.service_time = \
            self._maybe_split_demands(coords, demand, ready_time, due_time, service_time)

        # Ensure depot defaults exist
        if DEPOT not in self.ready_time: self.ready_time[DEPOT] = 0.0
        if DEPOT not in self.due_time: self.due_time[DEPOT] = float("inf")
        if DEPOT not in self.service_time: self.service_time[DEPOT] = 0.0

        self.n_customers = len({k for k in self.demand.keys() if k != DEPOT})
        self.dist = self._compute_distance_matrix()

        # --- Generative Part ---
        # Store the constraint checkers injected by the HH
        self.constraint_checkers = constraint_checkers

    # ---------- geometry & time ----------
    def _compute_distance_matrix(self):
        nodes = list(self.coords.keys())
        nmax = max(nodes) if nodes else 0
        dist = [[0.0]*(nmax+1) for _ in range(nmax+1)]
        for i, j in itertools.product(nodes, nodes):
            xi, yi = self.coords[i]
            xj, yj = self.coords[j]
            dist[i][j] = math.hypot(xi - xj, yi - yj)
        return dist

    def travel_time(self, i, j):
        return self.dist[i][j] / self.speed

    # ---------- split-delivery preprocessing ----------
    def _maybe_split_demands(self, coords: dict, demand: dict, rt: dict, dt: dict, st: dict):
        max_d = max(demand.values()) if demand else 0.0
        if max_d <= self.capacity + 1e-12:
            for nid in coords.keys(): self.original_map[nid] = nid
            return dict(coords), dict(demand), dict(rt), dict(dt), dict(st)

        if not self.allow_split_delivery:
            raise ValueError(
                f"Found customer demand > capacity ({max_d:.2f} > {self.capacity:.2f}). "
                f"Set constraints.split_delivery: true to enable."
            )

        new_coords, new_demand = dict(coords), {}
        out_rt, out_dt, out_st = dict(rt), dict(dt), dict(st)
        next_id = max(coords.keys()) + 1

        for cid, d in demand.items():
            if d <= self.capacity + 1e-12:
                new_demand[cid] = d
                self.original_map[cid] = cid
                continue

            remaining, first = d, True
            while remaining > 1e-12:
                take = min(self.capacity, remaining)
                remaining -= take
                if first:
                    new_demand[cid] = take
                    self.original_map[cid] = cid
                    first = False
                else:
                    clone_id = next_id
                    next_id += 1
                    new_coords[clone_id] = coords[cid]
                    new_demand[clone_id] = take
                    self.original_map[clone_id] = cid
                    # Clones inherit TWs and service times
                    if cid in rt: out_rt[clone_id] = rt[cid]
                    if cid in dt: out_dt[clone_id] = dt[cid]
                    if cid in st: out_st[clone_id] = st[cid]

        return new_coords, new_demand, out_rt, out_dt, out_st

    # ---------- routes & costs ----------
    @staticmethod
    def split_chromosome(chrom):
        routes, cur = [], []
        for g in chrom:
            if g == DEPOT:
                if cur: routes.append(cur); cur = []
            else:
                cur.append(g)
        if cur: routes.append(cur)
        return routes

    @staticmethod
    def routes_to_chromosome(routes):
        chrom = [DEPOT]
        for r in routes:
            if r: chrom.extend(r); chrom.append(DEPOT)
        if not chrom or chrom[-1] != DEPOT: chrom.append(DEPOT)
        return chrom

    def route_load(self, route):
        return sum(self.demand.get(c, 0) for c in route)

    def route_cost(self, route):
        if not route: return 0.0
        d = self.dist[DEPOT][route[0]]
        for i in range(len(route)-1): d += self.dist[route[i]][route[i+1]]
        d += self.dist[route[-1]][DEPOT]
        return d

    def total_distance_cost(self, chrom):
        return sum(self.route_cost(r) for r in self.split_chromosome(chrom))

    def total_time_cost(self, chrom):
        total_time = 0
        for r in self.split_chromosome(chrom):
            is_feasible, _, _, finish_time = self.schedule_route(r)
            if not is_feasible: return float('inf')
            total_time += finish_time
        return total_time

    # ---------- time window schedule ----------
    def schedule_route(self, route):
        time = 0.0
        cur = DEPOT
        arrival_times, start_times = [], []

        time = max(time, self.ready_time.get(DEPOT, 0.0))
        time += self.service_time.get(DEPOT, 0.0)

        for node in route:
            time += self.travel_time(cur, node)
            arrival = time
            start = max(arrival, self.ready_time.get(node, 0.0))
            if start - 1e-9 > self.due_time.get(node, float("inf")):
                return False, [], [], float("inf")
            finish = start + self.service_time.get(node, 0.0)
            arrival_times.append(arrival)
            start_times.append(start)
            time = finish
            cur = node

        time += self.travel_time(cur, DEPOT)
        if time - 1e-9 > self.due_time.get(DEPOT, float("inf")):
            return False, [], [], float("inf")
        
        time += self.service_time.get(DEPOT, 0.0)
        return True, arrival_times, start_times, time

    # ---------- DYNAMIC FEASIBILITY (GENERATED) ----------
    def is_feasible_routes(self, routes):
        """
        Checks for basic validity (coverage) and then applies all dynamically
        injected constraint checkers.
        """
        seen = set()
        all_customers = set(k for k in self.demand.keys() if k != DEPOT)

        # Basic checks: no empty routes, no duplicate customers
        for r in routes:
            if not r: return False
            for c in r:
                if c in seen: return False
                seen.add(c)
        
        # Coverage check: all customers must be served
        if seen != all_customers:
            return False

        # GENERATIVE STEP: Apply all injected constraint checkers
        for checker_func in self.constraint_checkers:
            if not checker_func(routes, self):
                return False
        
        return True

    def is_feasible(self, chrom):
        return self.is_feasible_routes(self.split_chromosome(chrom))

    # ---------- helper: cheapest feasible insertion ----------
    def cheapest_feasible_insertion(self, routes, customer):
        best_insertion = {'cost': float('inf'), 'route_idx': None, 'pos': None}
    
        # Case 1: Try inserting into existing routes
        for r_idx, r in enumerate(routes):
            base_cost = self.route_cost(r)
            for pos in range(len(r) + 1):
                trial_route = r[:pos] + [customer] + r[pos:]
                
                # Create a copy of the routes for feasibility checking
                trial_routes = list(routes)
                trial_routes[r_idx] = trial_route
    
                # The feasibility check here is now fully dynamic!
                if self.is_feasible_routes(trial_routes):
                    insertion_cost = self.route_cost(trial_route) - base_cost
                    if insertion_cost < best_insertion['cost']:
                        best_insertion.update({'cost': insertion_cost, 'route_idx': r_idx, 'pos': pos})
    
        # Case 2: Try creating a new route for the customer
        trial_routes = routes + [[customer]]
        if self.is_feasible_routes(trial_routes):
            new_route_cost = self.route_cost([customer])
            if new_route_cost < best_insertion['cost']:
                best_insertion.update({'cost': new_route_cost, 'route_idx': len(routes), 'pos': 0})
    
        if best_insertion['route_idx'] is None:
            return None, None, float('inf')
        return best_insertion['route_idx'], best_insertion['pos'], best_insertion['cost']

    # ---------- render helpers ----------
    def render_routes_original_ids(self, routes):
        return [[self.original_map.get(c, c) for c in r] for r in routes]

    def render_chromosome_original_ids(self, chrom):
        return [0 if g == 0 else self.original_map.get(g, g) for g in chrom]
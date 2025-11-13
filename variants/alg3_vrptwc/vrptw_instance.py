
# VRPTW instance utilities (direct coding with 0 as depot delimiter)
# Differences vs CVRPInstance:
# - Adds time windows per node: ready_time[i], due_time[i], service_time[i].
# - Travel time = distance / speed (speed can be set in config; default 1.0).
# - Feasibility requires both capacity and time-window feasibility for each route.
# - Insertion heuristic and 2-opt guard respect time windows.
import math
import itertools

DEPOT = 0

class VRPTWInstance:
    def __init__(self, coords: dict, demand: dict, capacity: float,
                 ready_time: dict = None, due_time: dict = None, service_time: dict = None,
                 speed: float = 1.0, allow_split_delivery: bool = False):
        """
        coords: {node_id: (x, y)} with node 0 as depot, 1..n customers
        demand: {customer_id: demand} for 1..n
        capacity: vehicle capacity (homogeneous)
        ready_time, due_time, service_time: dicts for 0..n (0 optional; defaults to 0, +inf, 0)
        speed: travel speed so that time = distance / speed
        allow_split_delivery: if True, customers with demand > capacity are split into clones
                              (clones inherit TWs and service times from original customer)
        """
        # normalize keys to int
        coords = {int(k): tuple(v) for k, v in coords.items()}
        demand = {int(k): float(v) for k, v in demand.items()}
        ready_time = {int(k): float(v) for k, v in (ready_time or {}).items()}
        due_time = {int(k): float(v) for k, v in (due_time or {}).items()}
        service_time = {int(k): float(v) for k, v in (service_time or {}).items()}

        self.capacity = float(capacity)
        self.speed = float(speed) if speed else 1.0
        self.allow_split_delivery = bool(allow_split_delivery)

        # NEW: map each (possibly cloned) ID -> original customer ID
        self.original_map = {}

        # validate or split heavy customers
        self.coords, self.demand, self.ready_time, self.due_time, self.service_time =             self._maybe_split_demands(coords, demand, ready_time, due_time, service_time)

        # ensure depot defaults exist
        if DEPOT not in self.ready_time:
            self.ready_time[DEPOT] = 0.0
        if DEPOT not in self.due_time:
            self.due_time[DEPOT] = float("inf")
        if DEPOT not in self.service_time:
            self.service_time[DEPOT] = 0.0

        self.n_customers = len({k for k in self.demand.keys() if k != DEPOT})
        self.dist = self._compute_distance_matrix()

    # ---------- geometry ----------
    def _compute_distance_matrix(self):
        nodes = list(self.coords.keys())
        nmax = max(nodes)
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
            # no splitting; record identity mapping and fill TW defaults
            out_rt, out_dt, out_st = {}, {}, {}
            for nid in coords.keys():
                self.original_map[nid] = nid
                out_rt[nid] = float(rt.get(nid, 0.0 if nid == DEPOT else 0.0))
                out_dt[nid] = float(dt.get(nid, float("inf")))
                out_st[nid] = float(st.get(nid, 0.0))
            return dict(coords), dict(demand), out_rt, out_dt, out_st

        if not self.allow_split_delivery:
            raise ValueError(
                f"Found customer demand > capacity ({max_d:.2f} > {self.capacity:.2f}). "
                f"Set constraints.split_delivery: true to enable split-delivery."
            )

        # Split any customer i with d_i > Q into clones with demands <= Q.
        new_coords = dict(coords)
        new_demand = {}
        out_rt, out_dt, out_st = {}, {}, {}
        next_id = max(coords.keys()) + 1

        # depot first
        self.original_map[DEPOT] = DEPOT
        out_rt[DEPOT] = float(rt.get(DEPOT, 0.0))
        out_dt[DEPOT] = float(dt.get(DEPOT, float("inf")))
        out_st[DEPOT] = float(st.get(DEPOT, 0.0))

        for cid, d in demand.items():
            if d <= self.capacity + 1e-12:
                new_demand[cid] = d
                self.original_map[cid] = cid
                out_rt[cid] = float(rt.get(cid, 0.0))
                out_dt[cid] = float(dt.get(cid, float("inf")))
                out_st[cid] = float(st.get(cid, 0.0))
                continue

            # split into chunks of size <= capacity
            remaining = d
            first = True
            while remaining > 1e-12:
                take = min(self.capacity, remaining)
                remaining -= take
                if first:
                    new_demand[cid] = take
                    self.original_map[cid] = cid
                    out_rt[cid] = float(rt.get(cid, 0.0))
                    out_dt[cid] = float(dt.get(cid, float("inf")))
                    out_st[cid] = float(st.get(cid, 0.0))
                    first = False
                else:
                    clone_id = next_id
                    next_id += 1
                    new_coords[clone_id] = coords[cid]
                    new_demand[clone_id] = take
                    self.original_map[clone_id] = cid
                    out_rt[clone_id] = float(rt.get(cid, 0.0))
                    out_dt[clone_id] = float(dt.get(cid, float("inf")))
                    out_st[clone_id] = float(st.get(cid, 0.0))

        return new_coords, new_demand, out_rt, out_dt, out_st

    # ---------- routes & costs ----------
    @staticmethod
    def split_chromosome(chrom):
        """Convert a direct-coded chromosome (0-delimited) into list of routes (no 0s inside)."""
        routes, cur = [], []
        for g in chrom:
            if g == DEPOT:
                if cur:
                    routes.append(cur)
                    cur = []
            else:
                cur.append(g)
        if cur:
            routes.append(cur)
        return routes

    @staticmethod
    def routes_to_chromosome(routes):
        """Convert list of routes (no 0s) into direct-coded chromosome with 0 delimiters, starting/ending with 0."""
        chrom = [DEPOT]
        for r in routes:
            if r:
                chrom.extend(r)
                chrom.append(DEPOT)
        if chrom[-1] != DEPOT:
            chrom.append(DEPOT)
        return chrom

    def route_load(self, route):
        return sum(self.demand[c] for c in route)

    def route_cost(self, route):
        """Depot-start/end route distance cost (objective)."""
        if not route:
            return 0.0
        d = self.dist[DEPOT][route[0]]
        for i in range(len(route)-1):
            d += self.dist[route[i]][route[i+1]]
        d += self.dist[route[-1]][DEPOT]
        return d

    def total_distance_cost(self, chrom):
        """Calculates the total distance traveled for all routes in a chromosome."""
        routes = self.split_chromosome(chrom)
        return sum(self.route_cost(r) for r in routes)

    def total_time_cost(self, chrom):
        """Calculates the sum of finish times for all routes (total operational time)."""
        routes = self.split_chromosome(chrom)
        total_time = 0
        for r in routes:
            total_time += self.schedule_route(r)[3] # schedule_route returns (feasible, ..., finish_time)
        return total_time

    # ---------- time window schedule ----------
    def schedule_route(self, route):
        """
        Simulate a route and check TW feasibility.
        Returns (feasible:bool, arrival_times:list, start_times:list, finish_time:float).
        * arrival_times: time of reaching node i
        * start_times: max(arrival, ready_time[i])
        * finish_time: time after finishing service at depot at the end
        """
        time = 0.0
        cur = DEPOT
        arrival_times = []
        start_times = []

        # depart depot earliest at its ready_time
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

        # return to depot
        time += self.travel_time(cur, DEPOT)
        # respect depot due time if given
        dep_due = self.due_time.get(DEPOT, float("inf"))
        if time - 1e-9 > dep_due:
            return False, [], [], float("inf")
        # service at depot end (usually 0)
        time += self.service_time.get(DEPOT, 0.0)
        return True, arrival_times, start_times, time

    # ---------- feasibility ----------
    def is_feasible_routes(self, routes):
        """Checks: capacity, coverage (each token exactly once), and time windows per route."""
        seen = set()
        for r in routes:
            if not r:
                return False
            if self.route_load(r) > self.capacity + 1e-9:
                return False
            ok, *_ = self.schedule_route(r)
            if not ok:
                return False
            for c in r:
                if c in seen:
                    return False
                seen.add(c)
        all_tokens = set(k for k in self.demand.keys() if k != DEPOT)
        return seen == all_tokens

    def is_feasible(self, chrom):
        return self.is_feasible_routes(self.split_chromosome(chrom))

    # ---------- helper: cheapest feasible insertion (capacity + TW) ----------
    def cheapest_feasible_insertion(self, routes, customer):
        """
        Returns (best_route_index, best_pos, best_delta) to insert 'customer' feasibly wrt capacity & TW.
        If none fits, return (None, None, None).
        """
        best = (None, None, None)
        dem = self.demand[customer]
        for r_idx, r in enumerate(routes):
            if self.route_load(r) + dem > self.capacity + 1e-9:
                continue
            base_cost = self.route_cost(r)
            for pos in range(len(r)+1):
                new_r = r[:pos] + [customer] + r[pos:]
                ok, *_ = self.schedule_route(new_r)
                if not ok:
                    continue
                delta = self.route_cost(new_r) - base_cost
                if best[2] is None or delta < best[2]:
                    best = (r_idx, pos, delta)
        return best

    # ---------- render helpers (map clones -> original IDs) ----------
    def render_routes_original_ids(self, routes):
        """Return the routes list with each node mapped to its original customer ID."""
        return [[self.original_map.get(c, c) for c in r] for r in routes]

    def render_chromosome_original_ids(self, chrom):
        """Return the chromosome list with nodes mapped to original IDs (0 stays 0)."""
        out = []
        for g in chrom:
            out.append(0 if g == 0 else self.original_map.get(g, g))
        return out

# Direct-coding CVRP instance utilities (explicit routes with 0 as depot delimiter)
import math
import itertools

DEPOT = 0

class CVRPInstance:
    def __init__(self, coords: dict, demand: dict, capacity: float, allow_split_delivery: bool = False):
        """
        coords: {node_id: (x, y)} with node 0 as depot, 1..n as customers
        demand: {customer_id: demand} for 1..n (0 not included or assumed 0)
        capacity: vehicle capacity (homogeneous)
        allow_split_delivery: if True, customers with demand > capacity are split into clones
        """
        # normalize keys to int
        coords = {int(k): tuple(v) for k, v in coords.items()}
        demand = {int(k): float(v) for k, v in demand.items()}

        self.capacity = float(capacity)
        self.allow_split_delivery = bool(allow_split_delivery)

        # NEW: map each (possibly cloned) ID -> original customer ID
        self.original_map = {}  # e.g., {2: 2, 7: 2, 8: 2, ...}

        # validate or split heavy customers
        self.coords, self.demand = self._maybe_split_demands(coords, demand)

        self.n_customers = len(self.demand)
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

    # ---------- split-delivery preprocessing ----------
    def _maybe_split_demands(self, coords: dict, demand: dict):
        max_d = max(demand.values()) if demand else 0.0
        if max_d <= self.capacity + 1e-12:
            # no splitting; record identity mapping
            for cid in demand.keys():
                self.original_map[cid] = cid
            return dict(coords), dict(demand)

        if not self.allow_split_delivery:
            raise ValueError(
                f"Found customer demand > capacity ({max_d:.2f} > {self.capacity:.2f}). "
                f"Set constraints.split_delivery: true to enable split-delivery."
            )

        # Split any customer i with d_i > Q into clones with demands <= Q
        new_coords = dict(coords)
        new_demand = {}
        next_id = max(coords.keys()) + 1

        for cid, d in demand.items():
            if d <= self.capacity + 1e-12:
                new_demand[cid] = d
                self.original_map[cid] = cid  # identity
                continue

            # split into chunks of size <= capacity
            k = int(math.ceil(d / self.capacity))
            remaining = d
            first = True
            while k > 0:
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
                    self.original_map[clone_id] = cid  # map clone -> original
                k -= 1

        return new_coords, new_demand

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
        """Depot-start/end route cost."""
        if not route:
            return 0.0
        d = self.dist[DEPOT][route[0]]
        for i in range(len(route)-1):
            d += self.dist[route[i]][route[i+1]]
        d += self.dist[route[-1]][DEPOT]
        return d

    def total_cost(self, chrom):
        routes = self.split_chromosome(chrom)
        return sum(self.route_cost(r) for r in routes)

    # ---------- feasibility ----------
    def is_feasible_routes(self, routes):
        """Checks: capacity and coverage (each token exactly once), no empties."""
        seen = set()
        for r in routes:
            if not r:
                return False
            if self.route_load(r) > self.capacity + 1e-9:
                return False
            for c in r:
                if c in seen:
                    return False
                seen.add(c)
        all_tokens = set(self.demand.keys())  # includes clones if any
        return seen == all_tokens

    def is_feasible(self, chrom):
        return self.is_feasible_routes(self.split_chromosome(chrom))

    # ---------- helper: cheapest feasible insertion ----------
    def cheapest_feasible_insertion(self, routes, customer):
        """
        Returns (best_route_index, best_pos, best_delta) to insert 'customer' into some route feasibly;
        If none fits by capacity, return (None, None, None).
        """
        best = (None, None, None)
        dem = self.demand[customer]
        for r_idx, r in enumerate(routes):
            if self.route_load(r) + dem > self.capacity + 1e-9:
                continue
            base_cost = self.route_cost(r)
            for pos in range(len(r)+1):
                new_r = r[:pos] + [customer] + r[pos:]
                delta = self.route_cost(new_r) - base_cost
                if best[2] is None or delta < best[2]:
                    best = (r_idx, pos, delta)
        return best

    # ---------- NEW: render helpers (map clones -> original IDs) ----------
    def render_routes_original_ids(self, routes):
        """Return the routes list with each node mapped to its original customer ID."""
        return [[self.original_map.get(c, c) for c in r] for r in routes]

    def render_chromosome_original_ids(self, chrom):
        """Return the chromosome list with nodes mapped to original IDs (0 stays 0)."""
        out = []
        for g in chrom:
            out.append(0 if g == 0 else self.original_map.get(g, g))
        return out


# VRPTW instance utilities (Time Windows only; NO capacity constraints)
# - Ignores demands and capacity entirely.
# - Keeps 0-delimited direct encoding.
# - Travel time = distance / speed.
import math
import itertools

DEPOT = 0

class VRPTWInstance_TWOnly:
    def __init__(self, coords: dict,
                 ready_time: dict = None, due_time: dict = None, service_time: dict = None,
                 speed: float = 1.0):
        """
        coords: {node_id: (x, y)} with node 0 as depot, 1..n customers
        *Demands/capacity are intentionally unsupported; TW feasibility only.*
        """
        coords = {int(k): tuple(v) for k, v in coords.items()}
        self.coords = coords
        self.speed = float(speed) if speed else 1.0

        self.ready_time = {int(k): float(v) for k, v in (ready_time or {}).items()}
        self.due_time = {int(k): float(v) for k, v in (due_time or {}).items()}
        self.service_time = {int(k): float(v) for k, v in (service_time or {}).items()}

        # defaults for depot
        if DEPOT not in self.ready_time:
            self.ready_time[DEPOT] = 0.0
        if DEPOT not in self.due_time:
            self.due_time[DEPOT] = float("inf")
        if DEPOT not in self.service_time:
            self.service_time[DEPOT] = 0.0

        self.n_customers = len([k for k in coords.keys() if k != DEPOT])
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

    # ---------- representation ----------
    @staticmethod
    def split_chromosome(chrom):
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
        chrom = [DEPOT]
        for r in routes:
            if r:
                chrom.extend(r)
                chrom.append(DEPOT)
        if chrom[-1] != DEPOT:
            chrom.append(DEPOT)
        return chrom

    # ---------- costs ----------
    def route_cost(self, route):
        if not route:
            return 0.0
        d = self.dist[DEPOT][route[0]]
        for i in range(len(route)-1):
            d += self.dist[route[i]][route[i+1]]
        d += self.dist[route[-1]][DEPOT]
        return d

    def total_cost(self, chrom):
        return sum(self.route_cost(r) for r in self.split_chromosome(chrom))

    # ---------- time window schedule ----------
    def schedule_route(self, route):
        time = 0.0
        cur = DEPOT
        arrival_times, start_times = [], []

        # depart depot not earlier than its ready_time
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
        dep_due = self.due_time.get(DEPOT, float("inf"))
        if time - 1e-9 > dep_due:
            return False, [], [], float("inf")
        time += self.service_time.get(DEPOT, 0.0)
        return True, arrival_times, start_times, time

    # ---------- feasibility ----------
    def is_feasible_routes(self, routes):
        """Checks: coverage (each customer exactly once) and time windows per route. NO capacity check."""
        seen = set()
        for r in routes:
            if not r:
                return False
            ok, *_ = self.schedule_route(r)
            if not ok:
                return False
            for c in r:
                if c == DEPOT:
                    return False
                if c in seen:
                    return False
                seen.add(c)
        all_customers = set(k for k in self.coords.keys() if k != DEPOT)
        return seen == all_customers

    def is_feasible(self, chrom):
        return self.is_feasible_routes(self.split_chromosome(chrom))

    # ---------- helper: cheapest feasible insertion (TW only) ----------
    def cheapest_feasible_insertion(self, routes, customer):
        """
        Returns (best_route_index, best_pos, best_delta) inserting 'customer' feasibly wrt time windows only.
        If none fits, return (None, None, None).
        """
        best = (None, None, None)
        for r_idx, r in enumerate(routes):
            base_cost = self.route_cost(r)
            for pos in range(len(r)+1):
                new_r = r[:pos] + [customer] + r[pos:]
                if not self.schedule_route(new_r)[0]:
                    continue
                delta = self.route_cost(new_r) - base_cost
                if best[2] is None or delta < best[2]:
                    best = (r_idx, pos, delta)
        return best

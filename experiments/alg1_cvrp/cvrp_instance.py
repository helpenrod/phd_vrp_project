# experiments/alg1_cvrp/cvrp_instance.py
import math
import itertools

class CVRPInstance:
    def __init__(self, coords: dict, demand: dict, capacity: float):
        self.coords = coords
        self.demand = demand
        self.capacity = capacity
        self.n_customers = len(demand)
        self.dist = self._compute_distance_matrix()

    def _compute_distance_matrix(self):
        nodes = list(self.coords.keys())
        n = len(nodes)
        dist = [[0]*n for _ in range(n)]
        for i, j in itertools.product(nodes, nodes):
            xi, yi = self.coords[i]
            xj, yj = self.coords[j]
            dist[i][j] = math.hypot(xi - xj, yi - yj)
        return dist

    def decode(self, chromosome):
        """Split chromosome into feasible routes by capacity."""
        routes, route, load = [], [], 0
        for c in chromosome:
            d = self.demand[c]
            if load + d > self.capacity:
                routes.append(route)
                route, load = [], 0
            route.append(c)
            load += d
        if route:
            routes.append(route)
        return routes

    def route_cost(self, route):
        """Compute cost of one route with depot (0)."""
        if not route:
            return 0
        cost = self.dist[0][route[0]]
        for i in range(len(route) - 1):
            cost += self.dist[route[i]][route[i + 1]]
        cost += self.dist[route[-1]][0]
        return cost

    def total_cost(self, chromosome):
        """Decode then compute total route distance."""
        routes = self.decode(chromosome)
        return sum(self.route_cost(r) for r in routes)

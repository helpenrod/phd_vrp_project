
# Minimal GA for VRPTW with DIRECT coding (0-delimited routes)
# This adapts the CVRP GA by making all feasibility checks and insertions respect time windows.
import random
from copy import deepcopy
from vrptw_instance import VRPTWInstance, DEPOT

class GAVRPTW_Direct:
    def __init__(self, instance: VRPTWInstance, params: dict):
        self.inst = instance
        self.pop_size = int(params["population_size"])
        self.gens = int(params["generations"])
        self.pc = float(params["crossover_prob"])
        self.pm = float(params["mutation_prob"])
        self.tournament_k = int(params["tournament_size"])
        self.use_2opt = bool(params.get("use_2opt", False))
        random.seed(int(params["seed"]))

        # Optional operator selection via YAML at parameters.operators
        ops = params.get("operators", None)
        if ops:
            self._crossover_kind = str(ops.get("crossover", "route_based")).lower()
            muts = ops.get("mutation", ["relocate", "swap"])
            self._mutation_choices = [m.lower() for m in muts] if muts else None
            ls = [x.lower() for x in ops.get("local_search", [])]
            if "2opt" in ls:
                self.use_2opt = True
        else:
            self._crossover_kind = "route_based"
            self._mutation_choices = None

    # ---------- population init ----------
    def _greedy_seed_routes(self, customers):
        """Greedy packing by capacity + TW feasibility -> list of routes."""
        routes = []
        rem = customers[:]
        for c in rem:
            placed = False
            # try to insert into existing routes at cheapest feasible position
            best = self.inst.cheapest_feasible_insertion(routes, c)
            if best[0] is not None:
                r_idx, pos, _ = best
                routes[r_idx].insert(pos, c)
                placed = True
            if not placed:
                # open a new route [c] only if feasible alone
                ok, *_ = self.inst.schedule_route([c])
                if ok:
                    routes.append([c])
                    placed = True
            if not placed:
                # If even alone is infeasible, keep as a singleton anyway to let repair handle (rare).
                routes.append([c])
        return routes

    def initialize(self):
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
        # Ensure feasibility; attempt light repairs if needed
        if not self.inst.is_feasible(chrom):
            chrom = self._repair(chrom)
        return self.inst.total_cost(chrom), chrom

    # ---------- selection ----------
    def tournament(self, pop):
        cand = random.sample(pop, self.tournament_k)
        scored = [(self.inst.total_cost(c), c) for c in cand]
        scored.sort(key=lambda x: x[0])  # sort by cost (fix in CVRP version)
        return deepcopy(scored[0][1])

    # ---------- crossover (Route-Based + greedy completion with TW) ----------
    def crossover(self, p1, p2):
        r1 = self.inst.split_chromosome(p1)
        r2 = self.inst.split_chromosome(p2)

        keep_count = max(1, len(r1)//2) if r1 else 0
        kept_idx = set(random.sample(range(len(r1)), keep_count)) if r1 else set()
        child_routes = [deepcopy(r1[i]) for i in sorted(kept_idx)]

        # purge duplicates tracking
        assigned = set(c for rt in child_routes for c in rt)

        # Greedily insert remaining customers following P2 order with TW constraints
        p2_order = [c for rt in r2 for c in rt]
        for c in p2_order:
            if c in assigned:
                continue
            r_idx, pos, _ = self.inst.cheapest_feasible_insertion(child_routes, c)
            if r_idx is None:
                # open new route if [c] is feasible
                if self.inst.schedule_route([c])[0]:
                    child_routes.append([c])
                else:
                    # fallback: place in the least time-violation spot (rare); skip here and let repair
                    child_routes.append([c])
            else:
                child_routes[r_idx].insert(pos, c)
            assigned.add(c)

        return self.inst.routes_to_chromosome(child_routes)

    # ---------- mutations ----------
    def mutate(self, chrom):
        if random.random() > self.pm:
            return chrom
        routes = self.inst.split_chromosome(chrom)

        if self._mutation_choices:
            choice = random.choice(self._mutation_choices)
            if choice == "relocate":
                chrom = self._mutate_relocate(routes)
            elif choice == "swap":
                chrom = self._mutate_swap(routes)
            else:
                chrom = self._mutate_original_mix(routes)
        else:
            chrom = self._mutate_original_mix(routes)

        # optional intra-route 2-opt guarded by TW feasibility
        if self.use_2opt:
            routes = self.inst.split_chromosome(chrom)
            if routes:
                ri = random.randrange(len(routes))
                routes[ri] = self._two_opt_intra_guarded(routes[ri])
                chrom = self.inst.routes_to_chromosome(routes)

        return chrom

    def _mutate_original_mix(self, routes):
        if len(routes) >= 2 and random.random() < 0.5:
            # Relocate with TW guard
            src_idx = random.randrange(len(routes))
            while len(routes[src_idx]) == 0:
                src_idx = random.randrange(len(routes))
            if not routes[src_idx]:
                return self.inst.routes_to_chromosome(routes)
            pos = random.randrange(len(routes[src_idx]))
            c = routes[src_idx].pop(pos)
            best = self.inst.cheapest_feasible_insertion(routes, c)
            if best[0] is None:
                if self.inst.schedule_route([c])[0]:
                    routes.append([c])
                else:
                    # revert if impossible
                    routes[src_idx].insert(pos, c)
            else:
                r_idx, insert_pos, _ = best
                routes[r_idx].insert(insert_pos, c)
        else:
            # Swap with TW guard
            flat = [(ri, ci) for ri, r in enumerate(routes) for ci, _ in enumerate(r)]
            if len(flat) >= 2:
                for _ in range(10):  # try a few times to find a TW-feasible swap
                    (r1, i1), (r2, i2) = random.sample(flat, 2)
                    a, b = routes[r1][i1], routes[r2][i2]
                    if r1 == r2 and i1 == i2:
                        continue
                    routes[r1][i1], routes[r2][i2] = b, a
                    if self.inst.schedule_route(routes[r1])[0] and self.inst.schedule_route(routes[r2])[0]:
                        break
                    # revert and try again
                    routes[r1][i1], routes[r2][i2] = a, b
        return self.inst.routes_to_chromosome(routes)

    def _mutate_relocate(self, routes):
        if not routes:
            return self.inst.routes_to_chromosome(routes)
        src_idx = random.randrange(len(routes))
        while not routes[src_idx]:
            src_idx = random.randrange(len(routes))
        pos = random.randrange(len(routes[src_idx]))
        c = routes[src_idx].pop(pos)
        best = self.inst.cheapest_feasible_insertion(routes, c)
        if best[0] is None:
            if self.inst.schedule_route([c])[0]:
                routes.append([c])
            else:
                routes[src_idx].insert(pos, c)  # revert
        else:
            r_idx, insert_pos, _ = best
            routes[r_idx].insert(insert_pos, c)
        return self.inst.routes_to_chromosome(routes)

    def _mutate_swap(self, routes):
        flat = [(ri, ci) for ri, r in enumerate(routes) for ci, _ in enumerate(r)]
        if len(flat) >= 2:
            for _ in range(10):
                (r1, i1), (r2, i2) = random.sample(flat, 2)
                a, b = routes[r1][i1], routes[r2][i2]
                if r1 == r2 and i1 == i2:
                    continue
                routes[r1][i1], routes[r2][i2] = b, a
                if self.inst.schedule_route(routes[r1])[0] and self.inst.schedule_route(routes[r2])[0]:
                    break
                routes[r1][i1], routes[r2][i2] = a, b
        return self.inst.routes_to_chromosome(routes)

    # ---------- local search helper ----------
    def _two_opt_intra_guarded(self, route):
        """2-opt improvement for ONE route with TW guard; keep best feasible."""
        best = route[:]
        best_cost = self.inst.route_cost(best)
        n = len(route)
        improved = True
        while improved:
            improved = False
            for i in range(n-1):
                for k in range(i+1, n):
                    cand = best[:i] + list(reversed(best[i:k+1])) + best[k+1:]
                    if not self.inst.schedule_route(cand)[0]:
                        continue
                    c = self.inst.route_cost(cand)
                    if c + 1e-9 < best_cost:
                        best, best_cost = cand, c
                        improved = True
                        break
                if improved:
                    break
        return best

    # ---------- light repair ----------
    def _repair(self, chrom):
        routes = [r[:] for r in self.inst.split_chromosome(chrom)]
        changed = True
        # Try relocating last customers from infeasible routes
        while changed:
            changed = False
            for idx, r in enumerate(list(routes)):
                # fix capacity first
                while self.inst.route_load(r) > self.inst.capacity + 1e-9 and r:
                    c = r.pop()  # remove last
                    ins = self.inst.cheapest_feasible_insertion(routes, c)
                    if ins[0] is None:
                        if self.inst.schedule_route([c])[0]:
                            routes.append([c])
                        else:
                            # revert if nothing works; put back (break loop)
                            r.append(c); break
                    else:
                        routes[ins[0]].insert(ins[1], c)
                    changed = True
                # fix time windows
                if r and not self.inst.schedule_route(r)[0]:
                    # try moving the last customer out
                    c = r.pop()
                    ins = self.inst.cheapest_feasible_insertion(routes, c)
                    if ins[0] is None:
                        if self.inst.schedule_route([c])[0]:
                            routes.append([c])
                        else:
                            r.append(c)  # revert
                    else:
                        routes[ins[0]].insert(ins[1], c)
                    changed = True
            # remove empties
            routes = [x for x in routes if x]
        return self.inst.routes_to_chromosome(routes)

    # ---------- GA loop ----------
    def run(self):
        pop = self.initialize()
        scores = []
        for ind in pop:
            f, ind = self.evaluate(ind)
            scores.append(f)

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
            scores = [self.inst.total_cost(ind) for ind in pop]
            cur_idx = min(range(len(pop)), key=lambda i: scores[i])
            if scores[cur_idx] + 1e-9 < best_fit:
                best_fit = scores[cur_idx]
                best = deepcopy(pop[cur_idx])

            if g % 20 == 0:
                print(f"Gen {g}: best cost = {best_fit:.2f}")

        return best, best_fit

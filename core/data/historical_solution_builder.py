import random


DEPOT = 0


class HistoricalSolutionBuilder:
    def __init__(self, instance, constraints: list[str]):
        self.instance = instance
        self.constraints = set(constraints)

    def build_individual_from_routes(self, previous_routes: list[list[int]]):
        routes = self._normalize_routes(previous_routes)
        if self.instance.is_feasible_routes(routes, check_coverage=True):
            return self.instance.routes_to_chromosome(routes)

        repaired_routes = self._repair_routes(routes)
        return self.instance.routes_to_chromosome(repaired_routes)

    def build_seed_population(
        self,
        previous_routes: list[list[int]],
        max_seeds: int,
        variants_per_seed: int = 2,
        seed: int | None = None,
    ) -> list:
        if not previous_routes or max_seeds <= 0:
            return []

        rng = random.Random(seed)
        population = []

        for route_set in self._as_route_sets(previous_routes):
            if len(population) >= max_seeds:
                break

            base_routes = self.instance.split_chromosome(
                self.build_individual_from_routes(route_set)
            )
            population.append(self.instance.routes_to_chromosome(base_routes))

            for _ in range(max(0, variants_per_seed)):
                if len(population) >= max_seeds:
                    break
                variant_routes = self._mutate_routes(base_routes, rng)
                if not self.instance.is_feasible_routes(variant_routes, check_coverage=True):
                    variant_routes = self._repair_routes(variant_routes)
                population.append(self.instance.routes_to_chromosome(variant_routes))

        return population[:max_seeds]

    def _as_route_sets(self, previous_routes_or_sets) -> list[list[list[int]]]:
        if not previous_routes_or_sets:
            return []

        first = previous_routes_or_sets[0]
        if not first:
            return [previous_routes_or_sets]

        if isinstance(first[0], (list, tuple)):
            return [
                [[int(node) for node in route] for route in route_set]
                for route_set in previous_routes_or_sets
            ]

        return [
            [[int(node) for node in route] for route in previous_routes_or_sets]
        ]

    def _normalize_routes(self, previous_routes: list[list[int]]) -> list[list[int]]:
        known_nodes = set(getattr(self.instance, "demand", {}).keys())
        seen = set()
        routes = []

        for route in previous_routes or []:
            cleaned = []
            for raw_node in route:
                node = int(raw_node)
                if node == DEPOT or node in seen:
                    continue
                if known_nodes and node not in known_nodes:
                    continue
                cleaned.append(node)
                seen.add(node)
            if cleaned:
                routes.append(cleaned)

        return self._normalize_pickup_delivery_order(routes)

    def _normalize_pickup_delivery_order(self, routes: list[list[int]]) -> list[list[int]]:
        if "pickup_delivery" not in self.constraints:
            return routes

        pd_pairs = getattr(self.instance, "pd_pairs", {})
        normalized = []
        for route in routes:
            route_set = set(route)
            output = []
            emitted = set()
            for node in route:
                if node in emitted:
                    continue
                if node in getattr(self.instance, "delivery_to_pickup", {}):
                    pickup = self.instance.delivery_to_pickup[node]
                    if pickup in route_set and pickup not in emitted:
                        output.append(pickup)
                        emitted.add(pickup)
                    output.append(node)
                    emitted.add(node)
                else:
                    output.append(node)
                    emitted.add(node)
                    delivery = pd_pairs.get(node)
                    if delivery in route_set and delivery not in emitted:
                        output.append(delivery)
                        emitted.add(delivery)
            if output:
                normalized.append(output)
        return normalized

    def _repair_routes(self, routes: list[list[int]]) -> list[list[int]]:
        service_order = self._historical_service_order(routes)
        repaired = []

        for node in service_order:
            if node in getattr(self.instance, "delivery_to_pickup", {}):
                continue

            r_idx, p_pos, d_pos, _ = self.instance.cheapest_feasible_insertion(
                repaired, node
            )
            delivery = getattr(self.instance, "pd_pairs", {}).get(node)
            if r_idx is None:
                candidate = [node, delivery] if delivery is not None else [node]
                repaired.append(candidate)
            elif r_idx == len(repaired):
                candidate = [node, delivery] if delivery is not None else [node]
                repaired.append(candidate)
            else:
                repaired[r_idx].insert(p_pos, node)
                if d_pos is not None:
                    repaired[r_idx].insert(d_pos, delivery)

        return repaired

    def _historical_service_order(self, routes: list[list[int]]) -> list[int]:
        customers = [node for node in self.instance.demand.keys() if node != DEPOT]
        seen = set()
        order = []

        for route in routes:
            for node in route:
                if node in seen:
                    continue
                order.append(node)
                seen.add(node)

        for node in customers:
            if node not in seen:
                order.append(node)
        return order

    def _mutate_routes(self, routes: list[list[int]], rng: random.Random) -> list[list[int]]:
        candidate = [route[:] for route in routes]
        if "pickup_delivery" in self.constraints:
            return self._mutate_pickup_delivery_routes(candidate, rng)
        return self._mutate_standard_routes(candidate, rng)

    def _mutate_standard_routes(self, routes: list[list[int]], rng: random.Random) -> list[list[int]]:
        positions = [
            (route_idx, node_idx)
            for route_idx, route in enumerate(routes)
            for node_idx in range(len(route))
        ]
        if len(positions) < 2:
            return routes

        first, second = rng.sample(positions, 2)
        r1, n1 = first
        r2, n2 = second
        routes[r1][n1], routes[r2][n2] = routes[r2][n2], routes[r1][n1]
        return routes

    def _mutate_pickup_delivery_routes(self, routes: list[list[int]], rng: random.Random) -> list[list[int]]:
        pickups = [node for route in routes for node in route if node in self.instance.pd_pairs]
        if not pickups:
            return routes

        pickup = rng.choice(pickups)
        delivery = self.instance.pd_pairs[pickup]
        reduced = []
        for route in routes:
            filtered = [node for node in route if node not in {pickup, delivery}]
            if filtered:
                reduced.append(filtered)

        r_idx, p_pos, d_pos, _ = self.instance.cheapest_feasible_insertion(
            reduced, pickup
        )
        if r_idx is None:
            reduced.append([pickup, delivery])
        elif r_idx == len(reduced):
            reduced.append([pickup, delivery])
        else:
            reduced[r_idx].insert(p_pos, pickup)
            if d_pos is not None:
                reduced[r_idx].insert(d_pos, delivery)
        return reduced

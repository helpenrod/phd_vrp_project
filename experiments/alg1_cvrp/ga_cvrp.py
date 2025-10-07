# experiments/alg1_cvrp/ga_cvrp.py
import random
from copy import deepcopy

class GACVRP:
    def __init__(self, instance, params):
        self.inst = instance
        self.pop_size = params["population_size"]
        self.gens = params["generations"]
        self.pc = params["crossover_prob"]
        self.pm = params["mutation_prob"]
        self.tournament_k = params["tournament_size"]
        random.seed(params["seed"])

    # ----- Core GA -----
    def initialize(self):
        customers = list(self.inst.demand.keys())
        return [random.sample(customers, len(customers)) for _ in range(self.pop_size)]

    def evaluate(self, chrom):
        return self.inst.total_cost(chrom)

    def tournament(self, pop, fitness):
        """Select one parent by tournament."""
        selected = random.sample(list(zip(pop, fitness)), self.tournament_k)
        selected.sort(key=lambda x: x[1])
        return deepcopy(selected[0][0])

    def crossover(self, p1, p2):
        """Simple route-based crossover."""
        n = len(p1)
        cut1, cut2 = sorted(random.sample(range(n), 2))
        child = [None]*n
        child[cut1:cut2] = p1[cut1:cut2]
        fill = [c for c in p2 if c not in child]
        j = 0
        for i in range(n):
            if child[i] is None:
                child[i] = fill[j]
                j += 1
        return child

    def mutate(self, chrom):
        """Swap two customers."""
        if random.random() < self.pm:
            i, j = random.sample(range(len(chrom)), 2)
            chrom[i], chrom[j] = chrom[j], chrom[i]
        return chrom

    def run(self):
        pop = self.initialize()
        fitness = [self.evaluate(ind) for ind in pop]
        best_idx = min(range(self.pop_size), key=lambda i: fitness[i])
        best, best_fit = pop[best_idx], fitness[best_idx]

        for g in range(self.gens):
            new_pop = []
            while len(new_pop) < self.pop_size:
                p1, p2 = self.tournament(pop, fitness), self.tournament(pop, fitness)
                if random.random() < self.pc:
                    child = self.crossover(p1, p2)
                else:
                    child = deepcopy(p1)
                child = self.mutate(child)
                new_pop.append(child)
            pop = new_pop
            fitness = [self.evaluate(ind) for ind in pop]
            current_best_idx = min(range(self.pop_size), key=lambda i: fitness[i])
            if fitness[current_best_idx] < best_fit:
                best_fit = fitness[current_best_idx]
                best = deepcopy(pop[current_best_idx])
            if g % 20 == 0:
                print(f"Gen {g}: best cost = {best_fit:.2f}")
        return best, best_fit

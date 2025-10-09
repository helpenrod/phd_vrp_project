import yaml
from cvrp_instance import CVRPInstance
from ga_cvrp import GACVRP_Direct

def load_config(path="experiments/alg1_cvrp/config.yaml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)

def pretty_routes(routes):
    return ["0-" + "-".join(map(str, r)) + "-0" for r in routes]

def main():
    cfg = load_config()
    coords = {int(k): v for k, v in cfg["instance"]["coordinates"].items()}
    demand = {int(k): v for k, v in cfg["instance"]["demand"].items()}
    allow_split = bool(cfg.get("constraints", {}).get("split_delivery", False))

    inst = CVRPInstance(coords, demand, cfg["fleet"]["capacity"], allow_split_delivery=allow_split)
    ga = GACVRP_Direct(inst, cfg["parameters"])

    best, cost = ga.run()

    # render to ORIGINAL IDs (so clones appear as repeated original IDs)
    routes_tokens = inst.split_chromosome(best)
    routes_orig = inst.render_routes_original_ids(routes_tokens)
    chrom_orig = inst.render_chromosome_original_ids(best)

    print("\n=== FINAL SOLUTION (DIRECT CODING; ORIGINAL IDs) ===")
    print("Chromosome:", chrom_orig)
    print("Routes:")
    for r in routes_orig:
        print("  " + "0-" + "-".join(map(str, r)) + "-0")
    print(f"Total cost: {cost:.2f}")
    print("Feasible:", inst.is_feasible(best))

if __name__ == "__main__":
    main()

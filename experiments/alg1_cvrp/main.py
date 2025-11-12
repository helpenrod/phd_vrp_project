import yaml
import sys
import os

# Add the project root to the Python path to allow imports from 'core'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from .cvrp_instance import CVRPInstance
from core.ga_framework import GAFramework

def load_config(path="experiments/alg1_cvrp/config.yaml"):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def pretty_routes(routes):
    return ["0-" + "-".join(map(str, r)) + "-0" for r in routes]

def main():
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else "experiments/alg1_cvrp/config.yaml"
    cfg = load_config(cfg_path)
    coords = {int(k): v for k, v in cfg["instance"]["coordinates"].items()}
    demand = {int(k): v for k, v in cfg["instance"]["demand"].items()}
    allow_split = bool(cfg.get("constraints", {}).get("split_delivery", False))

    inst = CVRPInstance(coords, demand, cfg["fleet"]["capacity"], allow_split_delivery=allow_split)
    ga = GAFramework(inst, cfg["parameters"])

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

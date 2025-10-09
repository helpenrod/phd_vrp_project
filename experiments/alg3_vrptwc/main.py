
# Entry point for VRPTW (compatible with the new YAML layout).
# If some TW fields are missing in the YAML, defaults are used.
import sys
import yaml
from vrptw_instance import VRPTWInstance
from ga_vrptw import GAVRPTW_Direct

def load_config(path="experiments/alg2_vrptw/config.yaml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)

def main():
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else "experiments/alg2_vrptw/config.yaml"
    cfg = load_config(cfg_path)

    inst_cfg = cfg["instance"]
    coords = {int(k): v for k, v in inst_cfg["coordinates"].items()}
    demand = {int(k): v for k, v in inst_cfg["demand"].items()}

    # Optional TW fields with safe defaults
    ready_time = {int(k): v for k, v in inst_cfg.get("ready_time", {}).items()}
    due_time = {int(k): v for k, v in inst_cfg.get("due_time", {}).items()}
    service_time = {int(k): v for k, v in inst_cfg.get("service_time", {}).items()}

    allow_split = bool(cfg.get("constraints", {}).get("split_delivery", False))
    speed = float(cfg.get("fleet", {}).get("speed", 1.0))
    capacity = float(cfg["fleet"]["capacity"])

    inst = VRPTWInstance(coords, demand, capacity,
                         ready_time=ready_time, due_time=due_time, service_time=service_time,
                         speed=speed, allow_split_delivery=allow_split)

    ga = GAVRPTW_Direct(inst, cfg["parameters"])
    best, cost = ga.run()

    routes_tokens = inst.split_chromosome(best)
    routes_orig = inst.render_routes_original_ids(routes_tokens)
    chrom_orig = inst.render_chromosome_original_ids(best)

    print("\n=== FINAL SOLUTION (VRPTW; DIRECT CODING; ORIGINAL IDs) ===")
    print("Chromosome:", chrom_orig)
    print("Routes:")
    for r in routes_orig:
        print("  " + "0-" + "-".join(map(str, r)) + "-0")
    print(f"Total distance: {cost:.2f}")
    print("Feasible:", inst.is_feasible(best))

if __name__ == "__main__":
    main()

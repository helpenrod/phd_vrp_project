
# Entry point for VRPTW TW-only (ignores capacity & demand). Uses same YAML but ignores demand/capacity.
import sys
import yaml
from vrptw_twonly_instance import VRPTWInstance_TWOnly
from ga_twonly_vrptw import GAVRPTW_TWOnly

def load_config(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)

def main():
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else "experiments/alg2_vrptw/config.yaml"
    cfg = load_config(cfg_path)

    inst_cfg = cfg["instance"]
    coords = {int(k): v for k, v in inst_cfg["coordinates"].items()}

    ready_time = {int(k): v for k, v in inst_cfg.get("ready_time", {}).items()}
    due_time = {int(k): v for k, v in inst_cfg.get("due_time", {}).items()}
    service_time = {int(k): v for k, v in inst_cfg.get("service_time", {}).items()}

    speed = float(cfg.get("fleet", {}).get("speed", 1.0))

    inst = VRPTWInstance_TWOnly(coords,
                                ready_time=ready_time, due_time=due_time, service_time=service_time,
                                speed=speed)

    ga = GAVRPTW_TWOnly(inst, cfg["parameters"])
    best, cost = ga.run()

    routes_tokens = inst.split_chromosome(best)

    print("\n=== FINAL SOLUTION (VRPTW TW-only; DIRECT CODING) ===")
    print("Chromosome:", best)
    print("Routes:")
    for r in routes_tokens:
        print("  " + "0-" + "-".join(map(str, r)) + "-0")
    print(f"Total distance: {cost:.2f}")
    print("Feasible:", inst.is_feasible(best))

if __name__ == "__main__":
    main()

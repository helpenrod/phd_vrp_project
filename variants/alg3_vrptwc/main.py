
# Entry point for VRPTWC (Capacity and Time Windows).
import sys
import yaml
import os

# Add the project root to the Python path to allow imports from 'core'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from .vrptw_instance import VRPTWInstance
from core.ga_framework import GAFramework

def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def main():
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else "variants/alg3_vrptwc/config.yaml"
    cfg = load_config(cfg_path)

    inst_cfg = cfg["instance"]
    coords = {int(k): v for k, v in inst_cfg["coordinates"].items()}
    demand = {int(k): v for k, v in inst_cfg["demand"].items()}

    # Optional TW fields with safe defaults
    ready_time = {int(k): v for k, v in inst_cfg.get("ready_time", {}).items()} if inst_cfg.get("ready_time") else {}
    due_time = {int(k): v for k, v in inst_cfg.get("due_time", {}).items()} if inst_cfg.get("due_time") else {}
    service_time = {int(k): v for k, v in inst_cfg.get("service_time", {}).items()} if inst_cfg.get("service_time") else {}
    
    fleet_cfg = cfg.get("fleet", {})
    capacity = float(fleet_cfg.get("capacity", float("inf")))
    speed = float(fleet_cfg.get("speed", 1.0))
    
    allow_split = bool(cfg.get("constraints", {}).get("split_delivery", False))

    inst = VRPTWInstance(coords, demand=demand, capacity=capacity,
                         ready_time=ready_time, due_time=due_time, service_time=service_time,
                         speed=speed, allow_split_delivery=allow_split)

    ga = GAFramework(inst, cfg["parameters"])
    best, cost = ga.run()

    routes_tokens = inst.split_chromosome(best)
    routes_orig = inst.render_routes_original_ids(routes_tokens)

    print("\n=== FINAL SOLUTION (VRPTWC; FRAMEWORK; ORIGINAL IDs) ===")
    print("Routes:")
    for r in routes_orig:
        print("  " + "0-" + "-".join(map(str, r)) + "-0")
    print(f"Total distance: {cost:.2f}")
    print("Feasible:", inst.is_feasible(best))

if __name__ == "__main__":
    main()

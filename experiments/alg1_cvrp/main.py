# experiments/alg1_cvrp/main.py
import yaml
from cvrp_instance import CVRPInstance
from ga_cvrp import GACVRP

def load_config(path="experiments/alg1_cvrp/config.yaml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)

def main():
    cfg = load_config()
    coords = {int(k): v for k, v in cfg["instance"]["coordinates"].items()}
    demand = {int(k): v for k, v in cfg["instance"]["demand"].items()}
    inst = CVRPInstance(coords, demand, cfg["fleet"]["capacity"])
    ga = GACVRP(inst, cfg["parameters"])

    best, cost = ga.run()
    print("\n=== FINAL SOLUTION ===")
    print("Best chromosome:", best)
    print("Best total cost:", cost)
    print("Decoded routes:", inst.decode(best))

if __name__ == "__main__":
    main()

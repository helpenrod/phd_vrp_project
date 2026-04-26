import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_logs(log_dir):
    for path in sorted(Path(log_dir).glob("*.json")):
        with open(path, "r", encoding="utf-8") as f:
            yield path, json.load(f)


def main():
    component_counts = Counter()
    performance_by_blueprint = defaultdict(list)

    for path, log in load_logs("experiments/logs"):
        blueprint = log.get("blueprint") or log.get("algorithm_blueprint")
        if not blueprint:
            continue

        for stage, components in blueprint.items():
            if stage == "representation":
                continue
            for component in components:
                component_counts[f"{stage}.{component}"] += 1

        fingerprint = json.dumps(blueprint, sort_keys=True)
        performance_by_blueprint[fingerprint].append({
            "log": str(path),
            "best_cost": log.get("best_cost"),
            "feasible": log.get("feasible"),
            "runtime_seconds": log.get("runtime_seconds"),
            "constraints": log.get("constraints"),
        })

    print("Frequently selected components:")
    for component, count in component_counts.most_common():
        print(f"  {component}: {count}")

    print("\nBlueprint performance groups:")
    for idx, (fingerprint, runs) in enumerate(performance_by_blueprint.items(), start=1):
        feasible_runs = [run for run in runs if run["feasible"]]
        best_costs = [run["best_cost"] for run in feasible_runs if run["best_cost"] is not None]
        best_cost = min(best_costs) if best_costs else None
        print(f"  blueprint_{idx}: runs={len(runs)}, feasible={len(feasible_runs)}, best_cost={best_cost}")


if __name__ == "__main__":
    main()

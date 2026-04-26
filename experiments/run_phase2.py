import json
import sys
import time
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.hyperheuristic.hyperheuristic import HyperHeuristic


VARIANT_CONFIGS = {
    "CVRP": "variants/alg1_cvrp/config.yaml",
    "VRPTW": "variants/alg3_vrptwc/config.yaml",
    "PDPTW": "variants/alg4_pdptw/config.yaml",
}


def run_blueprint(hh, config_path, blueprint, label):
    start_time = time.perf_counter()
    config = hh._load_config(config_path)
    constraint_set = hh._build_constraint_set(config)
    problem_constraints = constraint_set.constraints
    hh._validate_problem_definition(config, problem_constraints)

    selected_ops = hh._selected_ops_from_blueprint(blueprint)
    hh._select_operators(problem_constraints)
    checkers = hh._build_constraint_checkers(problem_constraints)
    instance, ga = hh._assemble_solver(config, blueprint, checkers)
    best_solution, best_cost = ga.run()
    runtime = time.perf_counter() - start_time

    log_path = hh._log_experiment(
        config_path,
        config,
        problem_constraints,
        selected_ops,
        blueprint,
        checkers,
        instance,
        best_solution,
        best_cost,
        runtime,
        experiment_label=label,
    )

    return {
        "label": label,
        "config_path": config_path,
        "constraints": sorted(problem_constraints),
        "blueprint": blueprint.to_dict(),
        "best_cost": best_cost,
        "feasible": instance.is_feasible(best_solution),
        "runtime_seconds": runtime,
        "log_path": str(log_path),
    }


def compare_generated_blueprints(hh):
    results = []
    for variant_name, config_path in VARIANT_CONFIGS.items():
        config = hh._load_config(config_path)
        constraint_set = hh._build_constraint_set(config)
        blueprint = hh.generate_blueprint(constraint_set)
        results.append(run_blueprint(hh, config_path, blueprint, f"compare_{variant_name}"))
    return results


def pdptw_ablations(hh):
    config_path = VARIANT_CONFIGS["PDPTW"]
    config = hh._load_config(config_path)
    constraint_set = hh._build_constraint_set(config)
    full = hh.generate_blueprint(constraint_set)

    ablations = [("pdptw_full", full)]

    without_repair = deepcopy(full)
    without_repair.repair = []
    ablations.append(("pdptw_without_repair", without_repair))

    incompatible_crossover = deepcopy(full)
    incompatible_crossover.crossover = ["route_based"]
    ablations.append(("pdptw_incompatible_crossover", incompatible_crossover))

    simplified_mutation = deepcopy(full)
    simplified_mutation.mutation = full.mutation[:1]
    ablations.append(("pdptw_simplified_mutation", simplified_mutation))

    return [
        run_blueprint(hh, config_path, blueprint, label)
        for label, blueprint in ablations
    ]


def candidate_blueprint_search(hh, limit=5):
    config_path = VARIANT_CONFIGS["PDPTW"]
    config = hh._load_config(config_path)
    constraint_set = hh._build_constraint_set(config)
    blueprints = hh.generate_candidate_blueprints(constraint_set, limit=limit)

    return [
        run_blueprint(hh, config_path, blueprint, f"pdptw_candidate_{idx}")
        for idx, blueprint in enumerate(blueprints, start=1)
    ]


def main():
    hh = HyperHeuristic()
    results = {
        "blueprint_comparison": compare_generated_blueprints(hh),
        "pdptw_ablations": pdptw_ablations(hh),
        "pdptw_candidate_search": candidate_blueprint_search(hh),
    }

    output_dir = Path("experiments/results")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "phase2_summary.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"Phase 2 summary saved to {output_path}")


if __name__ == "__main__":
    main()

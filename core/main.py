# Main entry point for the Hyper-Heuristic Framework
import sys
from core.hyperheuristic.hyperheuristic import HyperHeuristic

def main():
    """
    Usage: python3 -m core.main <path_to_problem_config.yaml>
    """
    if len(sys.argv) < 2:
        print("Error: Please provide the path to the problem configuration file.")
        print("Usage: python3 -m core.main path/to/your_problem.yaml")
        # As an example, use the PDPTW config if none is provided
        print("\nRunning with default PDPTW example...")
        problem_file = "variants/alg4_pdptw/config.yaml"
    else:
        problem_file = sys.argv[1]

    # 1. Instantiate the Hyper-Heuristic
    hh = HyperHeuristic()

    # 2. Solve the problem
    instance, best_solution, best_cost = hh.solve(problem_file)

    # 3. Print the results
    routes = instance.split_chromosome(best_solution)
    print("\n=== HYPER-HEURISTIC FINAL SOLUTION ===")
    print("Routes:", ["0-" + "-".join(map(str, r)) + "-0" for r in routes])
    print(f"Total distance: {best_cost:.2f}")
    print("Feasible:", instance.is_feasible(best_solution))

if __name__ == "__main__":
    main()

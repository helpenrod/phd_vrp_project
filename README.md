# PhD Research Project — Hyper-Heuristic Framework for VRP Variants

## Overview

This repository contains the implementation and experimental framework for my PhD research, focused on the **automatic generation of metaheuristics** through **hyper-heuristics** for solving **Vehicle Routing Problem (VRP)** variants.

The project aims to design a **modular system** capable of combining and adapting genetic algorithm (GA) operators to generate specialized solvers for new or hybrid VRP variants.

---

## Official Run Command

Run the current hyper-heuristic pipeline from the repository root with:

```bash
python3 -m core.main variants/alg4_pdptw/config.yaml
```

---

## Research Goals

1. **Develop a hyper-heuristic framework** that can intelligently select and combine GA operators.
2. **Model VRP variants declaratively** through YAML configuration files, specifying constraints and objectives.
3. **Automate the generation of algorithms** for new VRP variants by reusing and recombining previously implemented operators.
4. **Validate performance** on classical and extended VRP instances (CVRP, VRPTW, PDPTW, etc.).
5. **Contribute a reproducible methodology** adapted from the DIMMA (Design and Implementation Methodology for Metaheuristic Algorithms) approach.

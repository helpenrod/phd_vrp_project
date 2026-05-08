from copy import deepcopy


DEFAULT_GA_PARAMETERS = {
    "population_size": 20,
    "generations": 50,
    "crossover_prob": 0.8,
    "mutation_prob": 0.1,
    "tournament_size": 3,
    "seed": 42,
}

DEFAULT_ACO_PARAMETERS = {
    "n_ants": 4,
    "n_iterations": 5,
    "n_repetitions": 2,
    "evaporation_rate": 0.2,
    "alpha": 1.0,
    "beta": 1.0,
}

INSTANCE_FIELDS = {
    "coordinates",
    "demand",
    "demands",
    "ready_time",
    "due_time",
    "service_time",
    "service_times",
    "time_windows",
    "pickups",
    "pickup_delivery_pairs",
}

HISTORY_FIELDS = {
    "depot",
    "previous_routes",
    "route_costs",
    "route_times",
    "feasibility",
    *INSTANCE_FIELDS,
}


def normalize_client_config(config: dict) -> tuple[dict, bool]:
    """
    Convert a client-facing records file into the internal solver config.

    Returns the normalized config and whether defaults/client adaptation were applied.
    """
    normalized = deepcopy(config)
    changed = False

    if _looks_like_client_records(normalized):
        normalized = _move_top_level_records_into_sections(normalized)
        changed = True

    if "parameters" not in normalized:
        normalized["parameters"] = dict(DEFAULT_GA_PARAMETERS)
        changed = True
    else:
        for key, value in DEFAULT_GA_PARAMETERS.items():
            if key not in normalized["parameters"]:
                normalized["parameters"][key] = value
                changed = True

    if normalized.get("data") or normalized.get("historical_data"):
        if "aco" not in normalized:
            normalized["aco"] = dict(DEFAULT_ACO_PARAMETERS)
            changed = True
        else:
            for key, value in DEFAULT_ACO_PARAMETERS.items():
                if key not in normalized["aco"]:
                    normalized["aco"][key] = value
                    changed = True

    normalized.setdefault("objective", "distance")
    return normalized, changed


def _looks_like_client_records(config: dict) -> bool:
    return (
        "instance" not in config
        and "coordinates" in config
        and "constraints" in config
    )


def _move_top_level_records_into_sections(config: dict) -> dict:
    normalized = deepcopy(config)
    instance = {}
    data = {}

    for key in list(normalized):
        value = normalized[key]
        if key in INSTANCE_FIELDS:
            instance[_internal_instance_key(key)] = value
            data[key] = value
            del normalized[key]
        elif key in HISTORY_FIELDS:
            data[key] = value
            del normalized[key]

    depot = data.get("depot")
    if depot is not None:
        data["depot"] = depot

    capacity = normalized.pop("capacity", None)
    vehicle_capacity = normalized.pop("vehicle_capacity", None)
    if capacity is not None or vehicle_capacity is not None:
        fleet = normalized.setdefault("fleet", {})
        fleet.setdefault("capacity", capacity if capacity is not None else vehicle_capacity)
        data["capacity"] = fleet["capacity"]

    if "time_windows" in data and (
        "ready_time" not in instance or "due_time" not in instance
    ):
        ready_time = {}
        due_time = {}
        for node, window in data["time_windows"].items():
            ready_time[node] = window[0]
            due_time[node] = window[1]
        instance.setdefault("ready_time", ready_time)
        instance.setdefault("due_time", due_time)

    normalized["instance"] = instance
    normalized["data"] = data
    return normalized


def _internal_instance_key(key: str) -> str:
    aliases = {
        "demands": "demand",
        "service_times": "service_time",
    }
    return aliases.get(key, key)

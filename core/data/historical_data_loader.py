import csv
import json
from pathlib import Path
from typing import Any

import yaml

from core.data.data_validator import validate_route_history
from core.data.route_history import RouteHistory


class HistoricalDataLoader:
    def __init__(self, config: dict, base_path: str | Path | None = None):
        self.config = config
        self.base_path = Path(base_path or ".")

    def has_historical_data(self) -> bool:
        return bool(self.config.get("historical_data") or self.config.get("data"))

    def load(self) -> RouteHistory:
        if not self.has_historical_data():
            raise ValueError("No historical data section found in configuration.")

        raw_data = self._load_declared_data()
        merged_data = self._merge_with_problem_instance(raw_data)
        route_history = self._normalize(merged_data)
        validate_route_history(route_history, self._constraints())
        return route_history

    def _constraints(self) -> set[str]:
        constraints_config = self.config.get("constraints", {})
        if isinstance(constraints_config, dict):
            return set(constraints_config.get("problem_type", []))
        return set(constraints_config or [])

    def _load_declared_data(self) -> dict[str, Any]:
        data_config = self.config.get("historical_data") or self.config.get("data") or {}

        if isinstance(data_config, (str, Path)):
            return self._load_file(Path(data_config))

        if not isinstance(data_config, dict):
            raise ValueError("Historical data section must be a mapping or path.")

        path_value = data_config.get("path") or data_config.get("file")
        if not path_value:
            return dict(data_config)

        loaded = self._load_file(Path(path_value))
        inline_data = {k: v for k, v in data_config.items() if k not in {"path", "file"}}
        return self._deep_merge(loaded, inline_data)

    def _load_file(self, path: Path) -> dict[str, Any]:
        resolved_path = path if path.is_absolute() else self.base_path / path
        suffix = resolved_path.suffix.lower()

        with open(resolved_path, "r", encoding="utf-8") as f:
            if suffix in {".yaml", ".yml"}:
                return yaml.safe_load(f) or {}
            if suffix == ".json":
                return json.load(f)
            if suffix == ".csv":
                return self._load_csv(f)

        raise ValueError(f"Unsupported historical data format: {resolved_path}")

    def _load_csv(self, file_obj) -> dict[str, Any]:
        coordinates = {}
        demands = {}
        ready_time = {}
        due_time = {}
        service_time = {}
        depot = 0

        for row in csv.DictReader(file_obj):
            node = int(row.get("node") or row.get("id") or row.get("customer"))
            x = row.get("x")
            y = row.get("y")
            if x is not None and y is not None:
                coordinates[node] = [float(x), float(y)]
            if row.get("demand") not in {None, ""}:
                demands[node] = float(row["demand"])
            if row.get("ready_time") not in {None, ""}:
                ready_time[node] = float(row["ready_time"])
            if row.get("due_time") not in {None, ""}:
                due_time[node] = float(row["due_time"])
            if row.get("service_time") not in {None, ""}:
                service_time[node] = float(row["service_time"])
            if str(row.get("is_depot", "")).lower() in {"1", "true", "yes"}:
                depot = node

        data = {"coordinates": coordinates, "depot": depot}
        if demands:
            data["demand"] = demands
        if ready_time and due_time:
            data["ready_time"] = ready_time
            data["due_time"] = due_time
        if service_time:
            data["service_time"] = service_time
        return data

    def _merge_with_problem_instance(self, data: dict[str, Any]) -> dict[str, Any]:
        instance_data = dict(self.config.get("instance", {}))
        fleet_data = dict(self.config.get("fleet", {}))
        merged = self._deep_merge(instance_data, data)

        metadata = dict(merged.get("metadata") or {})
        if fleet_data:
            metadata.setdefault("fleet", fleet_data)
        if metadata:
            merged["metadata"] = metadata

        return merged

    def _normalize(self, data: dict[str, Any]) -> RouteHistory:
        coordinates = {
            int(node): (float(value[0]), float(value[1]))
            for node, value in (data.get("coordinates") or {}).items()
        }
        depot = int(data.get("depot", 0))

        demands = self._numeric_node_dict(data.get("demands") or data.get("demand"))
        service_times = self._numeric_node_dict(
            data.get("service_times") or data.get("service_time")
        )
        time_windows = self._time_windows(data)
        pickup_delivery_pairs = self._pickup_delivery_pairs(data)

        previous_routes = data.get("previous_routes")
        if previous_routes is not None:
            previous_routes = [[int(node) for node in route] for route in previous_routes]

        previous_route_sets = data.get("previous_route_sets")
        if previous_route_sets is not None:
            previous_route_sets = [
                [[int(node) for node in route] for route in route_set]
                for route_set in previous_route_sets
            ]
        elif previous_routes is not None:
            previous_route_sets = [previous_routes]

        metadata = dict(data.get("metadata") or {})
        for key in ("capacity", "vehicle_capacity", "fleet"):
            if key in data:
                metadata[key] = data[key]

        return RouteHistory(
            coordinates=coordinates,
            depot=depot,
            demands=demands,
            time_windows=time_windows,
            service_times=service_times,
            pickup_delivery_pairs=pickup_delivery_pairs,
            previous_routes=previous_routes,
            previous_route_sets=previous_route_sets,
            metadata=metadata,
        )

    @staticmethod
    def _numeric_node_dict(values) -> dict[int, float] | None:
        if not values:
            return None
        return {int(node): float(value) for node, value in values.items()}

    @staticmethod
    def _time_windows(data: dict[str, Any]) -> dict[int, tuple[float, float]] | None:
        if data.get("time_windows"):
            return {
                int(node): (float(value[0]), float(value[1]))
                for node, value in data["time_windows"].items()
            }

        ready_time = data.get("ready_time")
        due_time = data.get("due_time")
        if not ready_time or not due_time:
            return None

        nodes = set(ready_time).intersection(due_time)
        return {
            int(node): (float(ready_time[node]), float(due_time[node]))
            for node in nodes
        }

    @staticmethod
    def _pickup_delivery_pairs(data: dict[str, Any]) -> list[tuple[int, int]] | None:
        pairs = data.get("pickup_delivery_pairs")
        if pairs:
            normalized = []
            for pair in pairs:
                if isinstance(pair, dict):
                    normalized.append((int(pair["pickup"]), int(pair["delivery"])))
                else:
                    normalized.append((int(pair[0]), int(pair[1])))
            return normalized

        pickups = data.get("pickups")
        if pickups:
            return [(int(pickup), int(delivery)) for pickup, delivery in pickups.items()]

        return None

    @staticmethod
    def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        merged = dict(base)
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = HistoricalDataLoader._deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged

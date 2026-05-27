from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class RouteHistory:
    coordinates: Dict[int, Tuple[float, float]]
    depot: int
    demands: Optional[Dict[int, float]] = None
    time_windows: Optional[Dict[int, Tuple[float, float]]] = None
    service_times: Optional[Dict[int, float]] = None
    pickup_delivery_pairs: Optional[List[Tuple[int, int]]] = None
    previous_routes: Optional[List[List[int]]] = None
    previous_route_sets: Optional[List[List[List[int]]]] = None
    metadata: Optional[Dict[str, Any]] = None

# Large client_records-style test file

This file follows the same flat format as your uploaded `client_records.yaml`.

## File

`client_records_large_capacity_pickup_delivery.yaml`

## Restrictions

```yaml
constraints:
  problem_type: ["capacity", "pickup_delivery"]
```

## Size

- Depot: node 0
- Pickup-delivery pairs: 60
- Customer nodes: 120
- Total nodes including depot: 121
- Historical routes: 12
- Vehicle capacity: 30

## Format notes

The file uses the same style as your last configuration:

```yaml
constraints:
  problem_type: [...]
fleet:
  capacity: ...
  speed: ...
objective: "distance"
depot: 0
coordinates:
  ...
demand:
  ...
pickups:
  ...
previous_routes:
  ...
```

There is no nested `instance:` section in this file.

Your current `client_config_adapter.py` should identify it as client-style data because it has top-level `coordinates`, `constraints`, and no `instance` section.

## Pickup-delivery convention

Pickup nodes are odd:

```text
1, 3, 5, ...
```

Delivery nodes are the following even nodes:

```text
2, 4, 6, ...
```

Examples:

```yaml
pickups:
  1: 2
  3: 4
  5: 6
```

Pickup demands are positive. Delivery demands are negative.

## How to run

Example:

```bash
python3 -m core.main variants/client_example/client_records_large_capacity_pickup_delivery.yaml
```

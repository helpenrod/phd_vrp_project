import random


def set_seed(seed: int | None) -> None:
    if seed is not None:
        random.seed(int(seed))

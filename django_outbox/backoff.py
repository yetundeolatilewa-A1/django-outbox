import random


def compute_delay(attempt: int, base: float, cap: float, jitter: float = 0.0, rng=random.random) -> float:
    """Seconds to wait after the ``attempt``-th failed attempt (1-based).

    Exponential: base, 2*base, 4*base, ... capped at ``cap``, plus up to
    ``jitter`` (a fraction) of extra random delay.
    """
    if attempt < 1:
        raise ValueError("attempt starts at 1")
    delay = min(cap, base * (2 ** (attempt - 1)))
    return delay * (1 + jitter * rng())

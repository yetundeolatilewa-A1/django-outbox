import pytest

from django_outbox.backoff import compute_delay


def test_exponential_growth_and_cap():
    assert [compute_delay(n, 10, 100) for n in (1, 2, 3, 4, 5)] == [10, 20, 40, 80, 100]


def test_jitter_adds_up_to_fraction():
    assert compute_delay(1, 10, 100, jitter=0.5, rng=lambda: 1.0) == pytest.approx(15)
    assert compute_delay(1, 10, 100, jitter=0.5, rng=lambda: 0.0) == 10


def test_attempt_must_be_positive():
    with pytest.raises(ValueError):
        compute_delay(0, 10, 100)

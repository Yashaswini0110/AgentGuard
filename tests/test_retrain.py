"""F5.2 retrain guardrail: only swap when the challenger matches/beats the incumbent."""

from core.retrain import should_swap


def test_swaps_when_strictly_better():
    assert should_swap(0.90, 0.85) is True


def test_swaps_on_tie():
    assert should_swap(0.85, 0.85) is True


def test_keeps_incumbent_when_worse():
    assert should_swap(0.80, 0.85) is False


def test_swaps_when_no_incumbent():
    assert should_swap(0.50, None) is True

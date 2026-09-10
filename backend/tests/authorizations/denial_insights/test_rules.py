from __future__ import annotations

import pytest

from authstatus_api.authorizations.denial_insights.rules import (
    RuleThresholds,
    absolute_rate_difference,
    evaluate_denial_pattern,
    evaluate_groups_against_baseline,
    relative_rate_increase,
)


def _group(
    *,
    decision_count: int,
    denial_rate: float | None,
    payer: str = "Payer A",
) -> dict:
    return {
        "dimensions": {
            "insurance": payer,
        },
        "decision_count": decision_count,
        "observed_denial_rate": denial_rate,
    }


def test_relative_rate_increase():
    assert relative_rate_increase(
        0.30,
        0.20,
    ) == pytest.approx(0.5)


def test_relative_rate_increase_returns_none_for_zero_baseline():
    assert (
        relative_rate_increase(
            0.20,
            0.0,
        )
        is None
    )


def test_relative_rate_increase_zero_vs_zero_is_zero():
    assert (
        relative_rate_increase(
            0.0,
            0.0,
        )
        == 0.0
    )


def test_absolute_rate_difference():
    assert absolute_rate_difference(
        0.35,
        0.20,
    ) == pytest.approx(0.15)


def test_pattern_triggers_when_all_thresholds_are_met():
    result = evaluate_denial_pattern(
        _group(
            decision_count=20,
            denial_rate=0.40,
        ),
        _group(
            decision_count=100,
            denial_rate=0.20,
            payer="Baseline",
        ),
    )

    assert result["triggered"] is True
    assert result["decision_count"] == 20
    assert result["baseline_decision_count"] == 100
    assert result["observed_denial_rate"] == pytest.approx(0.40)
    assert result["baseline_denial_rate"] == pytest.approx(0.20)
    assert result["absolute_rate_difference"] == pytest.approx(0.20)
    assert result["relative_rate_increase"] == pytest.approx(1.0)


def test_pattern_does_not_trigger_for_small_group_sample():
    result = evaluate_denial_pattern(
        _group(
            decision_count=4,
            denial_rate=0.75,
        ),
        _group(
            decision_count=100,
            denial_rate=0.20,
            payer="Baseline",
        ),
    )

    assert result["triggered"] is False
    assert result["reason"] == "Group sample size is below the configured minimum."


def test_pattern_does_not_trigger_for_small_baseline_sample():
    result = evaluate_denial_pattern(
        _group(
            decision_count=20,
            denial_rate=0.60,
        ),
        _group(
            decision_count=4,
            denial_rate=0.20,
            payer="Baseline",
        ),
    )

    assert result["triggered"] is False
    assert result["reason"] == "Baseline sample size is below the configured minimum."


def test_pattern_does_not_trigger_below_denial_rate_threshold():
    result = evaluate_denial_pattern(
        _group(
            decision_count=20,
            denial_rate=0.10,
        ),
        _group(
            decision_count=100,
            denial_rate=0.05,
            payer="Baseline",
        ),
    )

    assert result["triggered"] is False


def test_pattern_does_not_trigger_without_required_relative_increase():
    result = evaluate_denial_pattern(
        _group(
            decision_count=20,
            denial_rate=0.22,
        ),
        _group(
            decision_count=100,
            denial_rate=0.20,
            payer="Baseline",
        ),
    )

    assert result["triggered"] is False


def test_pattern_can_trigger_against_zero_baseline():
    result = evaluate_denial_pattern(
        _group(
            decision_count=20,
            denial_rate=0.30,
        ),
        _group(
            decision_count=100,
            denial_rate=0.0,
            payer="Baseline",
        ),
    )

    assert result["triggered"] is True
    assert result["relative_rate_increase"] is None
    assert result["absolute_rate_difference"] == pytest.approx(0.30)


def test_custom_thresholds_are_applied():
    thresholds = RuleThresholds(
        minimum_sample_size=10,
        minimum_denial_rate=0.50,
        minimum_relative_increase=0.50,
    )

    result = evaluate_denial_pattern(
        _group(
            decision_count=15,
            denial_rate=0.60,
        ),
        _group(
            decision_count=50,
            denial_rate=0.30,
            payer="Baseline",
        ),
        thresholds=thresholds,
    )

    assert result["triggered"] is True
    assert result["minimum_sample_size"] == 10
    assert result["minimum_denial_rate"] == pytest.approx(0.50)
    assert result["minimum_relative_increase"] == pytest.approx(0.50)


def test_evaluate_groups_can_return_triggered_only():
    groups = [
        _group(
            decision_count=20,
            denial_rate=0.50,
            payer="Payer A",
        ),
        _group(
            decision_count=20,
            denial_rate=0.21,
            payer="Payer B",
        ),
    ]

    baseline = _group(
        decision_count=100,
        denial_rate=0.20,
        payer="Baseline",
    )

    results = evaluate_groups_against_baseline(
        groups,
        baseline,
        triggered_only=True,
    )

    assert len(results) == 1
    assert results[0]["dimensions"] == {
        "insurance": "Payer A",
    }


def test_invalid_threshold_sample_size_is_rejected():
    with pytest.raises(
        ValueError,
        match="minimum_sample_size must be at least 1",
    ):
        evaluate_denial_pattern(
            _group(
                decision_count=20,
                denial_rate=0.50,
            ),
            _group(
                decision_count=100,
                denial_rate=0.20,
            ),
            thresholds=RuleThresholds(
                minimum_sample_size=0,
            ),
        )


def test_invalid_rate_is_rejected():
    with pytest.raises(
        ValueError,
        match="observed_rate must be between 0 and 1",
    ):
        relative_rate_increase(
            1.2,
            0.20,
        )

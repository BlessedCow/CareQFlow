from __future__ import annotations

import pytest

from authstatus_api.authorizations.denial_insights.evidence import (
    calculate_evidence_strength,
    wilson_interval,
)


def _group(
    *,
    decisions: int,
    denied: int,
    insurance: str = "Payer A",
    unclassified: int = 0,
) -> dict:
    return {
        "dimensions": {
            "insurance": insurance,
        },
        "decision_count": decisions,
        "denied_count": denied,
        "unclassified_count": unclassified,
    }


def _evaluation(
    *,
    baseline_decisions: int,
    absolute_difference: float,
) -> dict:
    return {
        "baseline_decision_count": baseline_decisions,
        "absolute_rate_difference": absolute_difference,
    }


def test_wilson_interval_for_half_of_one_hundred():
    interval = wilson_interval(
        50,
        100,
    )

    assert interval is not None
    assert interval[0] == pytest.approx(
        0.4038,
        abs=0.0001,
    )
    assert interval[1] == pytest.approx(
        0.5962,
        abs=0.0001,
    )


def test_wilson_interval_is_wider_for_small_sample():
    small = wilson_interval(
        5,
        10,
    )
    large = wilson_interval(
        50,
        100,
    )

    assert small is not None
    assert large is not None

    assert small[1] - small[0] > large[1] - large[0]


def test_evidence_strength_returns_public_summary():
    result = calculate_evidence_strength(
        _group(
            decisions=100,
            denied=50,
        ),
        _evaluation(
            baseline_decisions=100,
            absolute_difference=0.25,
        ),
        dimensions=["insurance"],
    )

    assert 0 <= result["score"] <= 100
    assert result["level"] in {
        "Very weak",
        "Limited",
        "Moderate",
        "Strong",
        "Very strong",
    }

    assert result["sample_size"] == 100
    assert result["baseline_sample_size"] == 100
    assert result["wilson_95_interval"] == {
        "lower": pytest.approx(0.4038),
        "upper": pytest.approx(0.5962),
    }

    assert "calculation" not in result


def test_admin_calculation_can_include_component_math():
    result = calculate_evidence_strength(
        _group(
            decisions=100,
            denied=50,
        ),
        _evaluation(
            baseline_decisions=100,
            absolute_difference=0.25,
        ),
        dimensions=["insurance"],
        include_calculation=True,
    )

    calculation = result["calculation"]

    assert calculation["version"] == "1.0"

    assert calculation["sample_strength"]["maximum_points"] == 40.0
    assert calculation["baseline_separation"]["maximum_points"] == 30.0
    assert calculation["rate_stability"]["maximum_points"] == 20.0
    assert calculation["data_completeness"]["maximum_points"] == 10.0

    assert calculation["final_score"] == result["score"]


def test_insufficient_sample_cannot_exceed_very_weak():
    result = calculate_evidence_strength(
        _group(
            decisions=4,
            denied=4,
        ),
        _evaluation(
            baseline_decisions=100,
            absolute_difference=1.0,
        ),
        dimensions=["insurance"],
    )

    assert result["score"] <= 24
    assert result["level"] == "Very weak"


def test_preliminary_sample_cannot_exceed_limited():
    result = calculate_evidence_strength(
        _group(
            decisions=10,
            denied=10,
        ),
        _evaluation(
            baseline_decisions=100,
            absolute_difference=1.0,
        ),
        dimensions=["insurance"],
    )

    assert result["score"] <= 49
    assert result["level"] == "Limited"


def test_small_baseline_also_caps_strength():
    result = calculate_evidence_strength(
        _group(
            decisions=100,
            denied=80,
        ),
        _evaluation(
            baseline_decisions=4,
            absolute_difference=0.70,
        ),
        dimensions=["insurance"],
    )

    assert result["score"] <= 24
    assert result["level"] == "Very weak"


def test_unknown_dimension_reduces_completeness():
    complete = calculate_evidence_strength(
        _group(
            decisions=50,
            denied=25,
            insurance="Payer A",
        ),
        _evaluation(
            baseline_decisions=50,
            absolute_difference=0.10,
        ),
        dimensions=["insurance"],
        include_calculation=True,
    )

    incomplete = calculate_evidence_strength(
        _group(
            decisions=50,
            denied=25,
            insurance="Unknown",
        ),
        _evaluation(
            baseline_decisions=50,
            absolute_difference=0.10,
        ),
        dimensions=["insurance"],
        include_calculation=True,
    )

    assert (
        complete["calculation"]["data_completeness"]["points"]
        > incomplete["calculation"]["data_completeness"]["points"]
    )

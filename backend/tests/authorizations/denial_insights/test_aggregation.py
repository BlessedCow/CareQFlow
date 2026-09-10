from __future__ import annotations

import pytest

from authstatus_api.authorizations.denial_insights.aggregation import (
    add_sample_states,
    classify_decision,
    group_decisions,
    sample_state,
    summarize_decisions,
)


def _snapshot(
    *,
    outcome: str,
    insurance: str = "Example Health",
    insurance_plan: str = "Gold PPO",
    loc: str = "RTC",
    requested_days: int = 0,
    approved_days: int = 0,
    denied_days: int = 0,
    days_at_current_loc: int | None = None,
    total_treatment_days: int | None = None,
) -> dict:
    return {
        "facility": "Facility A",
        "insurance": insurance,
        "insurance_plan": insurance_plan,
        "loc": loc,
        "auth_type": "Concurrent",
        "outcome": outcome,
        "requested_days": requested_days,
        "approved_days": approved_days,
        "denied_days": denied_days,
        "denial_reason_category": None,
        "denial_source": None,
        "source": "manual",
        "days_at_current_loc": days_at_current_loc,
        "total_treatment_days": total_treatment_days,
    }


def test_classify_approved_decision():
    result = classify_decision(
        _snapshot(
            outcome="Approved",
            requested_days=5,
            approved_days=5,
        )
    )

    assert result.approved is True
    assert result.partial is False
    assert result.denied is False
    assert result.adverse is False


def test_classify_denied_decision():
    result = classify_decision(
        _snapshot(
            outcome="Denied",
            requested_days=5,
            denied_days=5,
        )
    )

    assert result.approved is False
    assert result.partial is False
    assert result.denied is True
    assert result.adverse is True


def test_classify_partial_from_day_counts():
    result = classify_decision(
        _snapshot(
            outcome="Decision",
            requested_days=7,
            approved_days=3,
            denied_days=4,
        )
    )

    assert result.approved is False
    assert result.partial is True
    assert result.denied is False
    assert result.adverse is True


def test_summarize_decisions_keeps_partial_separate_from_denial():
    summary = summarize_decisions(
        [
            _snapshot(
                outcome="Approved",
                requested_days=5,
                approved_days=5,
            ),
            _snapshot(
                outcome="Denied",
                requested_days=5,
                denied_days=5,
            ),
            _snapshot(
                outcome="Partial",
                requested_days=5,
                approved_days=2,
                denied_days=3,
            ),
        ]
    )

    assert summary["decision_count"] == 3
    assert summary["approved_count"] == 1
    assert summary["partial_count"] == 1
    assert summary["denied_count"] == 1
    assert summary["adverse_count"] == 2

    assert summary["observed_denial_rate"] == pytest.approx(0.3333)
    assert summary["observed_partial_rate"] == pytest.approx(0.3333)
    assert summary["observed_adverse_rate"] == pytest.approx(0.6667)

    assert summary["requested_days"] == 15
    assert summary["approved_days"] == 7
    assert summary["denied_days"] == 8


def test_group_decisions_by_payer_and_loc():
    groups = group_decisions(
        [
            _snapshot(
                outcome="Approved",
                insurance="Payer A",
                loc="RTC",
            ),
            _snapshot(
                outcome="Denied",
                insurance="Payer A",
                loc="RTC",
            ),
            _snapshot(
                outcome="Approved",
                insurance="Payer A",
                loc="PHP",
            ),
            _snapshot(
                outcome="Denied",
                insurance="Payer B",
                loc="RTC",
            ),
        ],
        [
            "insurance",
            "loc",
        ],
    )

    assert len(groups) == 3

    assert groups[0]["dimensions"] == {
        "insurance": "Payer A",
        "loc": "PHP",
    }
    assert groups[0]["decision_count"] == 1

    assert groups[1]["dimensions"] == {
        "insurance": "Payer A",
        "loc": "RTC",
    }
    assert groups[1]["decision_count"] == 2
    assert groups[1]["observed_denial_rate"] == 0.5

    assert groups[2]["dimensions"] == {
        "insurance": "Payer B",
        "loc": "RTC",
    }


def test_group_decisions_uses_unknown_for_missing_dimension():
    groups = group_decisions(
        [
            _snapshot(
                outcome="Denied",
                insurance="",
            ),
        ],
        ["insurance"],
    )

    assert groups[0]["dimensions"] == {
        "insurance": "Unknown",
    }


def test_group_decisions_rejects_unsupported_dimension():
    with pytest.raises(
        ValueError,
        match="Unsupported analytics dimensions",
    ):
        group_decisions(
            [],
            ["client_name"],
        )


@pytest.mark.parametrize(
    ("decision_count", "expected"),
    [
        (0, "insufficient"),
        (4, "insufficient"),
        (5, "preliminary"),
        (19, "preliminary"),
        (20, "standard"),
        (100, "standard"),
    ],
)
def test_sample_state(
    decision_count,
    expected,
):
    assert sample_state(decision_count) == expected


def test_add_sample_states():
    groups = add_sample_states(
        [
            {
                "decision_count": 3,
                "dimensions": {
                    "insurance": "Payer A",
                },
            },
            {
                "decision_count": 12,
                "dimensions": {
                    "insurance": "Payer B",
                },
            },
            {
                "decision_count": 27,
                "dimensions": {
                    "insurance": "Payer C",
                },
            },
        ]
    )

    assert [group["sample_state"] for group in groups] == [
        "insufficient",
        "preliminary",
        "standard",
    ]


def test_group_decisions_uses_exact_current_loc_day():
    groups = group_decisions(
        [
            _snapshot(
                outcome="Denied",
                days_at_current_loc=5,
            ),
            _snapshot(
                outcome="Approved",
                days_at_current_loc=6,
            ),
            _snapshot(
                outcome="Denied",
                days_at_current_loc=7,
            ),
        ],
        ["days_at_current_loc"],
    )

    assert {group["dimensions"]["days_at_current_loc"] for group in groups} == {
        "5",
        "6",
        "7",
    }


def test_group_decisions_uses_exact_total_treatment_day():
    groups = group_decisions(
        [
            _snapshot(
                outcome="Approved",
                total_treatment_days=13,
            ),
            _snapshot(
                outcome="Denied",
                total_treatment_days=14,
            ),
        ],
        ["total_treatment_days"],
    )

    assert {group["dimensions"]["total_treatment_days"] for group in groups} == {
        "13",
        "14",
    }


def test_daily_duration_dimension_uses_unknown_when_missing():
    groups = group_decisions(
        [
            _snapshot(
                outcome="Denied",
                days_at_current_loc=None,
            )
        ],
        ["days_at_current_loc"],
    )

    assert groups[0]["dimensions"] == {
        "days_at_current_loc": "Unknown",
    }


def test_exact_day_dimension_can_be_combined_with_payer():
    groups = group_decisions(
        [
            _snapshot(
                outcome="Denied",
                insurance="Payer A",
                days_at_current_loc=5,
            ),
            _snapshot(
                outcome="Approved",
                insurance="Payer A",
                days_at_current_loc=6,
            ),
            _snapshot(
                outcome="Denied",
                insurance="Payer B",
                days_at_current_loc=5,
            ),
        ],
        [
            "insurance",
            "days_at_current_loc",
        ],
    )

    assert {
        (
            group["dimensions"]["insurance"],
            group["dimensions"]["days_at_current_loc"],
        )
        for group in groups
    } == {
        ("Payer A", "5"),
        ("Payer A", "6"),
        ("Payer B", "5"),
    }


def test_clinical_dimensions_preserve_exact_score():
    snapshots = [
        _snapshot(
            outcome="Denied",
        ),
        _snapshot(
            outcome="Approved",
        ),
    ]

    snapshots[0]["clinical_instrument"] = "CIWA-Ar"
    snapshots[0]["clinical_latest_score"] = 23.0
    snapshots[0]["clinical_score_age_days"] = 0

    snapshots[1]["clinical_instrument"] = "CIWA-Ar"
    snapshots[1]["clinical_latest_score"] = 24.0
    snapshots[1]["clinical_score_age_days"] = 1

    groups = group_decisions(
        snapshots,
        [
            "clinical_instrument",
            "clinical_latest_score",
        ],
    )

    assert {
        (
            group["dimensions"]["clinical_instrument"],
            group["dimensions"]["clinical_latest_score"],
        )
        for group in groups
    } == {
        ("CIWA-Ar", "23.0"),
        ("CIWA-Ar", "24.0"),
    }

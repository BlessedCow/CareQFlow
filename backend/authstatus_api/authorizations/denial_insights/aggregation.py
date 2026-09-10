from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

DIMENSION_FIELDS = frozenset(
    {
        "facility",
        "insurance",
        "insurance_plan",
        "loc",
        "auth_type",
        "outcome",
        "denial_reason_category",
        "denial_source",
        "source",
        "days_at_current_loc",
        "total_treatment_days",
        "clinical_instrument",
        "clinical_latest_score",
        "clinical_score_age_days",
        "clinical_score_change",
        "clinical_score_trend",
        "clinical_assessment_count",
        "clinical_min_score",
        "clinical_max_score",
    }
)

APPROVED_OUTCOMES = frozenset(
    {
        "approved",
        "peer to peer overturned",
        "p2p overturned",
        "appeal overturned",
    }
)

PARTIAL_OUTCOMES = frozenset(
    {
        "partial",
        "partially approved",
        "partial approval",
        "modified loc",
    }
)

DENIED_OUTCOMES = frozenset(
    {
        "denied",
        "administrative denied",
        "administratively denied",
        "final upheld",
        "denial upheld",
        "appeal upheld",
    }
)


@dataclass(frozen=True)
class DecisionClassification:
    approved: bool
    partial: bool
    denied: bool
    adverse: bool


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""

    return " ".join(str(value).strip().lower().split())


def _display_dimension_value(value: Any) -> str:
    if value is None:
        return "Unknown"

    normalized = str(value).strip()

    if not normalized:
        return "Unknown"

    return normalized


def classify_decision(
    snapshot: dict[str, Any],
) -> DecisionClassification:
    outcome = _normalize_text(snapshot.get("outcome"))

    requested_days = int(snapshot.get("requested_days") or 0)
    approved_days = int(snapshot.get("approved_days") or 0)
    denied_days = int(snapshot.get("denied_days") or 0)

    explicitly_approved = outcome in APPROVED_OUTCOMES
    explicitly_partial = outcome in PARTIAL_OUTCOMES
    explicitly_denied = outcome in DENIED_OUTCOMES

    has_approved_days = approved_days > 0
    has_denied_days = denied_days > 0

    partial = (
        explicitly_partial
        or (has_approved_days and has_denied_days)
        or (requested_days > 0 and 0 < approved_days < requested_days)
    )

    denied = explicitly_denied or (
        has_denied_days and not partial and approved_days == 0
    )

    approved = explicitly_approved or (approved_days > 0 and not partial and not denied)

    adverse = denied or partial

    return DecisionClassification(
        approved=approved,
        partial=partial,
        denied=denied,
        adverse=adverse,
    )


def _percentage(
    numerator: int,
    denominator: int,
) -> float | None:
    if denominator == 0:
        return None

    return round(
        numerator / denominator,
        4,
    )


def summarize_decisions(
    snapshots: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    records = list(snapshots)

    approved_count = 0
    partial_count = 0
    denied_count = 0
    adverse_count = 0
    unclassified_count = 0

    requested_days = 0
    approved_days = 0
    denied_days = 0

    for snapshot in records:
        classification = classify_decision(snapshot)

        approved_count += int(classification.approved)
        partial_count += int(classification.partial)
        denied_count += int(classification.denied)
        adverse_count += int(classification.adverse)

        if not (
            classification.approved or classification.partial or classification.denied
        ):
            unclassified_count += 1

        requested_days += int(snapshot.get("requested_days") or 0)
        approved_days += int(snapshot.get("approved_days") or 0)
        denied_days += int(snapshot.get("denied_days") or 0)

    decision_count = len(records)

    return {
        "decision_count": decision_count,
        "approved_count": approved_count,
        "partial_count": partial_count,
        "denied_count": denied_count,
        "adverse_count": adverse_count,
        "unclassified_count": unclassified_count,
        "observed_denial_rate": _percentage(
            denied_count,
            decision_count,
        ),
        "observed_partial_rate": _percentage(
            partial_count,
            decision_count,
        ),
        "observed_adverse_rate": _percentage(
            adverse_count,
            decision_count,
        ),
        "requested_days": requested_days,
        "approved_days": approved_days,
        "denied_days": denied_days,
    }


def group_decisions(
    snapshots: Iterable[dict[str, Any]],
    dimensions: Sequence[str],
) -> list[dict[str, Any]]:
    invalid_dimensions = [
        dimension for dimension in dimensions if dimension not in DIMENSION_FIELDS
    ]

    if invalid_dimensions:
        names = ", ".join(sorted(invalid_dimensions))
        raise ValueError(f"Unsupported analytics dimensions: {names}")

    records = list(snapshots)

    if not dimensions:
        return [
            {
                "dimensions": {},
                **summarize_decisions(records),
            }
        ]

    groups: dict[
        tuple[str, ...],
        list[dict[str, Any]],
    ] = {}

    for snapshot in records:
        key = tuple(
            _display_dimension_value(snapshot.get(dimension))
            for dimension in dimensions
        )

        groups.setdefault(
            key,
            [],
        ).append(snapshot)

    result: list[dict[str, Any]] = []

    for key, group_records in groups.items():
        dimension_values = {
            dimension: key[index] for index, dimension in enumerate(dimensions)
        }

        result.append(
            {
                "dimensions": dimension_values,
                **summarize_decisions(group_records),
            }
        )

    return sorted(
        result,
        key=lambda item: tuple(
            str(
                item["dimensions"].get(
                    dimension,
                    "",
                )
            ).casefold()
            for dimension in dimensions
        ),
    )


def sample_state(
    decision_count: int,
    *,
    preliminary_minimum: int = 5,
    standard_minimum: int = 20,
) -> str:
    if preliminary_minimum < 1:
        raise ValueError("preliminary_minimum must be at least 1.")

    if standard_minimum < preliminary_minimum:
        raise ValueError("standard_minimum cannot be lower than preliminary_minimum.")

    if decision_count < preliminary_minimum:
        return "insufficient"

    if decision_count < standard_minimum:
        return "preliminary"

    return "standard"


def add_sample_states(
    groups: Iterable[dict[str, Any]],
    *,
    preliminary_minimum: int = 5,
    standard_minimum: int = 20,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []

    for group in groups:
        enriched = dict(group)
        enriched["sample_state"] = sample_state(
            int(group["decision_count"]),
            preliminary_minimum=preliminary_minimum,
            standard_minimum=standard_minimum,
        )
        result.append(enriched)

    return result

from __future__ import annotations

from datetime import datetime
from typing import Any

from authstatus_api.authorizations.denial_insights.aggregation import (
    add_sample_states,
    group_decisions,
    summarize_decisions,
)
from authstatus_api.authorizations.denial_insights.rules import (
    RuleThresholds,
    evaluate_groups_against_baseline,
)
from authstatus_api.persistence.connections import get_conn
from authstatus_api.persistence.schema import init_db


class DenialInsightsError(ValueError):
    pass


class InvalidDenialInsightsFilterError(DenialInsightsError):
    pass


SUPPORTED_FILTER_FIELDS = frozenset(
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
    }
)


def _parse_timestamp(
    value: str,
    field_name: str,
) -> str:
    normalized = value.strip()

    if not normalized:
        raise InvalidDenialInsightsFilterError(f"{field_name} cannot be blank.")

    try:
        datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise InvalidDenialInsightsFilterError(
            f"{field_name} must be a valid ISO 8601 timestamp."
        ) from exc

    return normalized


def _row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "auth_id": int(row["auth_id"]),
        "auth_event_id": (
            int(row["auth_event_id"]) if row["auth_event_id"] is not None else None
        ),
        "facility": str(row["facility"]),
        "insurance": (str(row["insurance"]) if row["insurance"] is not None else None),
        "insurance_plan": (
            str(row["insurance_plan"]) if row["insurance_plan"] is not None else None
        ),
        "loc": str(row["loc"]),
        "auth_type": str(row["auth_type"]),
        "outcome": str(row["outcome"]),
        "requested_days": int(row["requested_days"]),
        "approved_days": int(row["approved_days"]),
        "denied_days": int(row["denied_days"]),
        "decision_at": str(row["decision_at"]),
        "denial_reason_category": (
            str(row["denial_reason_category"])
            if row["denial_reason_category"] is not None
            else None
        ),
        "denial_source": (
            str(row["denial_source"]) if row["denial_source"] is not None else None
        ),
        "days_at_current_loc": (
            int(row["days_at_current_loc"])
            if row["days_at_current_loc"] is not None
            else None
        ),
        "total_treatment_days": (
            int(row["total_treatment_days"])
            if row["total_treatment_days"] is not None
            else None
        ),
        "source": str(row["source"]),
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }


def list_decision_snapshots(
    *,
    start_at: str | None = None,
    end_at: str | None = None,
    filters: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    init_db()

    clauses: list[str] = []
    params: list[Any] = []

    if start_at is not None:
        normalized_start = _parse_timestamp(
            start_at,
            "start_at",
        )
        clauses.append("decision_at >= ?")
        params.append(normalized_start)

    if end_at is not None:
        normalized_end = _parse_timestamp(
            end_at,
            "end_at",
        )
        clauses.append("decision_at <= ?")
        params.append(normalized_end)

    if (
        start_at is not None
        and end_at is not None
        and datetime.fromisoformat(normalized_end)
        < datetime.fromisoformat(normalized_start)
    ):
        raise InvalidDenialInsightsFilterError(
            "end_at cannot be earlier than start_at."
        )

    for field_name, value in (filters or {}).items():
        if field_name not in SUPPORTED_FILTER_FIELDS:
            raise InvalidDenialInsightsFilterError(
                f"Unsupported analytics filter: {field_name}"
            )

        normalized_value = value.strip()

        if not normalized_value:
            continue

        clauses.append(f"LOWER(TRIM({field_name})) = LOWER(TRIM(?))")
        params.append(normalized_value)

    query = """
        SELECT *
        FROM auth_decision_snapshots
    """

    if clauses:
        query += " WHERE " + " AND ".join(clauses)

    query += " ORDER BY decision_at, id"

    with get_conn() as conn:
        rows = conn.execute(
            query,
            params,
        ).fetchall()

    return [_row_to_dict(row) for row in rows]


def build_denial_insights(
    *,
    dimensions: list[str],
    start_at: str | None = None,
    end_at: str | None = None,
    filters: dict[str, str] | None = None,
    baseline_filters: dict[str, str] | None = None,
    preliminary_minimum: int = 5,
    standard_minimum: int = 20,
    rule_thresholds: RuleThresholds | None = None,
) -> dict[str, Any]:
    records = list_decision_snapshots(
        start_at=start_at,
        end_at=end_at,
        filters=filters,
    )

    baseline_records = list_decision_snapshots(
        start_at=start_at,
        end_at=end_at,
        filters=baseline_filters,
    )

    groups = add_sample_states(
        group_decisions(
            records,
            dimensions,
        ),
        preliminary_minimum=preliminary_minimum,
        standard_minimum=standard_minimum,
    )

    baseline = {
        "dimensions": {},
        **summarize_decisions(baseline_records),
    }

    baseline["sample_state"] = add_sample_states(
        [baseline],
        preliminary_minimum=preliminary_minimum,
        standard_minimum=standard_minimum,
    )[0]["sample_state"]

    evaluations = evaluate_groups_against_baseline(
        groups,
        baseline,
        thresholds=rule_thresholds,
    )

    return {
        "dimensions": list(dimensions),
        "filters": dict(filters or {}),
        "baseline_filters": dict(baseline_filters or {}),
        "start_at": start_at,
        "end_at": end_at,
        "summary": summarize_decisions(records),
        "baseline": baseline,
        "groups": groups,
        "evaluations": evaluations,
    }

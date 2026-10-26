from __future__ import annotations

from datetime import datetime
from typing import Any

from authstatus_api.authorizations.denial_insights.aggregation import (
    add_sample_states,
    classify_decision,
    group_decisions,
    summarize_decisions,
    summarize_follow_up_cases,
)
from authstatus_api.authorizations.denial_insights.clinical_context import (
    enrich_snapshots_with_clinical_context,
)
from authstatus_api.authorizations.denial_insights.evidence import (
    calculate_evidence_strength,
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
        "snapshot_role": str(row["snapshot_role"]),
        "review_type": str(row["review_type"]),
        "parent_snapshot_id": (
            int(row["parent_snapshot_id"])
            if row["parent_snapshot_id"] is not None
            else None
        ),
        "root_snapshot_id": (
            int(row["root_snapshot_id"])
            if row["root_snapshot_id"] is not None
            else None
        ),
        "follow_up_decision_at": (
            str(row["follow_up_decision_at"])
            if row["follow_up_decision_at"] is not None
            else None
        ),
    }


def _list_snapshot_population(
    *,
    population_clause: str,
    start_at: str | None = None,
    end_at: str | None = None,
    filters: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    init_db()

    clauses: list[str] = [
        population_clause,
        "auth_id IN (SELECT id FROM auths WHERE is_voided = 0)",
    ]
    params: list[Any] = []

    normalized_start: str | None = None
    normalized_end: str | None = None

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
        normalized_start is not None
        and normalized_end is not None
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

    query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY decision_at, id"

    with get_conn() as conn:
        rows = conn.execute(
            query,
            params,
        ).fetchall()

    return [_row_to_dict(row) for row in rows]


def list_decision_snapshots(
    *,
    start_at: str | None = None,
    end_at: str | None = None,
    filters: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    return _list_snapshot_population(
        population_clause="""
            (
                snapshot_role = 'legacy'
                OR (
                    snapshot_role = 'root'
                    AND LOWER(TRIM(review_type)) != 'retro'
                )
            )
        """,
        start_at=start_at,
        end_at=end_at,
        filters=filters,
    )


def list_retro_root_snapshots(
    *,
    start_at: str | None = None,
    end_at: str | None = None,
    filters: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    return _list_snapshot_population(
        population_clause="""
            snapshot_role = 'root'
            AND LOWER(TRIM(review_type)) = 'retro'
        """,
        start_at=start_at,
        end_at=end_at,
        filters=filters,
    )


def _list_follow_up_snapshots(
    root_snapshot_ids: list[int],
) -> list[dict[str, Any]]:
    if not root_snapshot_ids:
        return []

    placeholders = ", ".join("?" for _ in root_snapshot_ids)

    query = f"""
        SELECT *
        FROM auth_decision_snapshots
        WHERE
            snapshot_role = 'follow_up'
            AND root_snapshot_id IN ({placeholders})
            AND auth_id IN (
                SELECT id FROM auths WHERE is_voided = 0
            )
        ORDER BY
            COALESCE(follow_up_decision_at, decision_at),
            id
    """  # nosec B608

    with get_conn() as conn:
        rows = conn.execute(
            query,
            root_snapshot_ids,
        ).fetchall()

    return [_row_to_dict(row) for row in rows]


def _list_follow_up_auth_states(
    auth_ids: list[int],
) -> dict[int, dict[str, Any]]:
    if not auth_ids:
        return {}

    placeholders = ", ".join("?" for _ in auth_ids)

    query = f"""
        SELECT
            id,
            p2p_requested,
            p2p_decided_at,
            p2p_outcome,
            appeal_submitted,
            appeal_decided_at,
            appeal_outcome,
            retro_requested,
            retro_decided_at,
            retro_outcome
        FROM auths
        WHERE id IN ({placeholders})
          AND is_voided = 0
    """  # nosec B608

    with get_conn() as conn:
        rows = conn.execute(
            query,
            auth_ids,
        ).fetchall()

    return {
        int(row["id"]): {
            "p2p_requested": bool(row["p2p_requested"]),
            "p2p_decided_at": str(row["p2p_decided_at"] or "").strip(),
            "p2p_outcome": str(row["p2p_outcome"] or "").strip(),
            "appeal_submitted": bool(row["appeal_submitted"]),
            "appeal_decided_at": str(row["appeal_decided_at"] or "").strip(),
            "appeal_outcome": str(row["appeal_outcome"] or "").strip(),
            "retro_requested": bool(row["retro_requested"]),
            "retro_decided_at": str(row["retro_decided_at"] or "").strip(),
            "retro_outcome": str(row["retro_outcome"] or "").strip(),
        }
        for row in rows
    }


def _resolved_follow_up_by_root(
    snapshots: list[dict[str, Any]],
) -> dict[tuple[int, str], dict[str, Any]]:
    resolved: dict[
        tuple[int, str],
        dict[str, Any],
    ] = {}

    for snapshot in snapshots:
        root_snapshot_id = snapshot.get("root_snapshot_id")
        review_type = str(snapshot.get("review_type") or "").strip().lower()

        if root_snapshot_id is None or not review_type:
            continue

        resolved[
            (
                int(root_snapshot_id),
                review_type,
            )
        ] = snapshot

    return resolved


def _follow_up_is_successful(
    snapshot: dict[str, Any] | None,
) -> bool:
    if snapshot is None:
        return False

    outcome = str(snapshot.get("outcome") or "").strip().lower()

    return outcome.endswith(
        (
            " approved",
            " overturned",
        )
    )


def _build_follow_up_metrics(
    records: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    roots = [
        record
        for record in records
        if record.get("snapshot_role") == "root"
        and record.get("review_type") != "retro"
        and classify_decision(record).adverse
    ]

    root_snapshot_ids = [int(record["id"]) for record in roots]
    auth_ids = sorted({int(record["auth_id"]) for record in roots})

    follow_up_snapshots = _list_follow_up_snapshots(root_snapshot_ids)
    auth_states = _list_follow_up_auth_states(auth_ids)
    resolved_by_root = _resolved_follow_up_by_root(follow_up_snapshots)

    cases: dict[str, list[dict[str, Any]]] = {
        "p2p": [],
        "appeal": [],
        "retro": [],
    }

    for root in roots:
        root_snapshot_id = int(root["id"])
        auth_id = int(root["auth_id"])

        auth_state = auth_states.get(
            auth_id,
            {},
        )

        p2p_snapshot = resolved_by_root.get(
            (
                root_snapshot_id,
                "p2p",
            )
        )
        appeal_snapshot = resolved_by_root.get(
            (
                root_snapshot_id,
                "appeal",
            )
        )
        retro_snapshot = resolved_by_root.get(
            (
                root_snapshot_id,
                "retro",
            )
        )

        p2p_resolved = p2p_snapshot is not None
        p2p_pending = (
            not p2p_resolved
            and bool(auth_state.get("p2p_requested"))
            and not bool(auth_state.get("p2p_decided_at"))
        )
        p2p_initiated = (
            p2p_resolved or p2p_pending or bool(auth_state.get("p2p_requested"))
        )

        cases["p2p"].append(
            {
                "eligible": True,
                "initiated": p2p_initiated,
                "pending": p2p_pending,
                "resolved": p2p_resolved,
                "outcome": (
                    p2p_snapshot["outcome"] if p2p_snapshot is not None else None
                ),
            }
        )

        appeal_eligible = not p2p_pending and not _follow_up_is_successful(p2p_snapshot)

        appeal_resolved = appeal_snapshot is not None
        appeal_pending = (
            appeal_eligible
            and not appeal_resolved
            and bool(auth_state.get("appeal_submitted"))
            and not bool(auth_state.get("appeal_decided_at"))
        )
        appeal_initiated = (
            appeal_resolved
            or appeal_pending
            or (appeal_eligible and bool(auth_state.get("appeal_submitted")))
        )

        cases["appeal"].append(
            {
                "eligible": appeal_eligible,
                "initiated": appeal_initiated,
                "pending": appeal_pending,
                "resolved": appeal_resolved,
                "outcome": (
                    appeal_snapshot["outcome"] if appeal_snapshot is not None else None
                ),
            }
        )

        retro_eligible = (
            appeal_eligible
            and not appeal_pending
            and not _follow_up_is_successful(appeal_snapshot)
        )

        retro_resolved = retro_snapshot is not None
        retro_pending = (
            retro_eligible
            and not retro_resolved
            and bool(auth_state.get("retro_requested"))
            and not bool(auth_state.get("retro_decided_at"))
        )
        retro_initiated = (
            retro_resolved
            or retro_pending
            or (retro_eligible and bool(auth_state.get("retro_requested")))
        )

        cases["retro"].append(
            {
                "eligible": retro_eligible,
                "initiated": retro_initiated,
                "pending": retro_pending,
                "resolved": retro_resolved,
                "outcome": (
                    retro_snapshot["outcome"] if retro_snapshot is not None else None
                ),
            }
        )

    return {
        review_type: summarize_follow_up_cases(
            review_cases,
            review_type=review_type,
        )
        for review_type, review_cases in cases.items()
    }


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
    include_evidence_calculation: bool = False,
) -> dict[str, Any]:
    records = enrich_snapshots_with_clinical_context(
        list_decision_snapshots(
            start_at=start_at,
            end_at=end_at,
            filters=filters,
        )
    )

    baseline_records = enrich_snapshots_with_clinical_context(
        list_decision_snapshots(
            start_at=start_at,
            end_at=end_at,
            filters=baseline_filters,
        )
    )
    follow_up_metrics = _build_follow_up_metrics(records)

    retro_root_records = list_retro_root_snapshots(
        start_at=start_at,
        end_at=end_at,
        filters=filters,
    )
    retro_root_metrics = summarize_decisions(retro_root_records)

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

    for group, evaluation in zip(
        groups,
        evaluations,
        strict=True,
    ):
        evaluation["evidence_strength"] = calculate_evidence_strength(
            group,
            evaluation,
            dimensions=dimensions,
            preliminary_minimum=preliminary_minimum,
            standard_minimum=standard_minimum,
            include_calculation=(include_evidence_calculation),
        )

    return {
        "dimensions": list(dimensions),
        "filters": dict(filters or {}),
        "baseline_filters": dict(baseline_filters or {}),
        "start_at": start_at,
        "end_at": end_at,
        "summary": summarize_decisions(records),
        "follow_up_metrics": follow_up_metrics,
        "retro_root_metrics": retro_root_metrics,
        "baseline": baseline,
        "groups": groups,
        "evaluations": evaluations,
    }

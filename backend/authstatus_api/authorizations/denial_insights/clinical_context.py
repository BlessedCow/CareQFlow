from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from authstatus_api.persistence.connections import get_conn
from authstatus_api.persistence.schema import init_db


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.strip())

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)

    return parsed.astimezone(UTC)


def _assessment_row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "auth_id": int(row["auth_id"]),
        "auth_event_id": (
            int(row["auth_event_id"]) if row["auth_event_id"] is not None else None
        ),
        "instrument": str(row["instrument"]),
        "score": float(row["score"]),
        "assessed_at": str(row["assessed_at"]),
    }


def _select_latest_assessment(
    snapshot: dict[str, Any],
    assessments: list[dict[str, Any]],
) -> tuple[
    dict[str, Any] | None,
    list[dict[str, Any]],
]:
    decision_at = _parse_timestamp(str(snapshot["decision_at"]))

    eligible = [
        assessment
        for assessment in assessments
        if _parse_timestamp(str(assessment["assessed_at"])) <= decision_at
    ]

    if not eligible:
        return None, []

    auth_event_id = snapshot.get("auth_event_id")

    if auth_event_id is not None:
        event_assessments = [
            assessment
            for assessment in eligible
            if assessment["auth_event_id"] == auth_event_id
        ]

        if event_assessments:
            eligible = event_assessments

    latest = max(
        eligible,
        key=lambda assessment: (
            _parse_timestamp(str(assessment["assessed_at"])),
            int(assessment["id"]),
        ),
    )

    same_instrument = [
        assessment
        for assessment in eligible
        if assessment["instrument"] == latest["instrument"]
    ]

    same_instrument.sort(
        key=lambda assessment: (
            _parse_timestamp(str(assessment["assessed_at"])),
            int(assessment["id"]),
        )
    )

    return latest, same_instrument


def _clinical_history_features(
    assessments: list[dict[str, Any]],
) -> dict[str, Any]:
    if not assessments:
        return {
            "clinical_score_change": None,
            "clinical_score_trend": None,
            "clinical_assessment_count": 0,
            "clinical_min_score": None,
            "clinical_max_score": None,
        }

    scores = [float(assessment["score"]) for assessment in assessments]

    score_change: float | None = None
    trend: str | None = None

    if len(scores) >= 2:
        score_change = scores[-1] - scores[-2]

        if score_change > 0:
            trend = "increasing"
        elif score_change < 0:
            trend = "decreasing"
        else:
            trend = "stable"

    return {
        "clinical_score_change": score_change,
        "clinical_score_trend": trend,
        "clinical_assessment_count": len(scores),
        "clinical_min_score": min(scores),
        "clinical_max_score": max(scores),
    }


def enrich_snapshots_with_clinical_context(
    snapshots: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not snapshots:
        return []

    init_db()

    auth_ids = sorted({int(snapshot["auth_id"]) for snapshot in snapshots})

    placeholders = ", ".join("?" for _ in auth_ids)

    query = f"""
        SELECT
            id,
            auth_id,
            auth_event_id,
            instrument,
            score,
            assessed_at
        FROM clinical_assessments
        WHERE auth_id IN ({placeholders})
        ORDER BY auth_id, assessed_at, id
        """  # nosec B608

    with get_conn() as conn:
        rows = conn.execute(
            query,
            auth_ids,
        ).fetchall()

    assessments_by_auth: dict[
        int,
        list[dict[str, Any]],
    ] = defaultdict(list)

    for row in rows:
        assessment = _assessment_row_to_dict(row)
        assessments_by_auth[assessment["auth_id"]].append(assessment)

    enriched_snapshots: list[dict[str, Any]] = []

    for snapshot in snapshots:
        enriched = dict(snapshot)

        assessment, same_instrument = _select_latest_assessment(
            snapshot,
            assessments_by_auth.get(
                int(snapshot["auth_id"]),
                [],
            ),
        )

        if assessment is None:
            enriched["clinical_instrument"] = None
            enriched["clinical_latest_score"] = None
            enriched["clinical_score_age_days"] = None
            enriched["clinical_score_change"] = None
            enriched["clinical_score_trend"] = None
            enriched["clinical_assessment_count"] = 0
            enriched["clinical_min_score"] = None
            enriched["clinical_max_score"] = None

            enriched_snapshots.append(enriched)
            continue

        decision_at = _parse_timestamp(str(snapshot["decision_at"]))
        assessed_at = _parse_timestamp(str(assessment["assessed_at"]))

        age_days = int((decision_at - assessed_at).total_seconds() // 86400)

        enriched["clinical_instrument"] = assessment["instrument"]
        enriched["clinical_latest_score"] = assessment["score"]
        enriched["clinical_score_age_days"] = age_days
        enriched.update(_clinical_history_features(same_instrument))

        enriched_snapshots.append(enriched)

    return enriched_snapshots

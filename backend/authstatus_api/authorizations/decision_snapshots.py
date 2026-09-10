from __future__ import annotations

from datetime import datetime
from typing import Any

from authstatus_api.authorizations.state import current_timestamp
from authstatus_api.persistence.connections import get_conn
from authstatus_api.persistence.schema import init_db


class AuthDecisionSnapshotError(ValueError):
    pass


class InvalidAuthDecisionSnapshotError(AuthDecisionSnapshotError):
    pass


def _parse_timestamp(value: str, field_name: str) -> datetime:
    normalized = value.strip()

    if not normalized:
        raise InvalidAuthDecisionSnapshotError(f"{field_name} is required.")

    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise InvalidAuthDecisionSnapshotError(
            f"{field_name} must be a valid ISO 8601 timestamp."
        ) from exc


def _auth_exists(conn: Any, auth_id: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM auths WHERE id = ?",
        (auth_id,),
    ).fetchone()

    return row is not None


def _auth_event_belongs_to_auth(
    conn: Any,
    auth_id: int,
    auth_event_id: int,
) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM auth_events
        WHERE id = ? AND auth_id = ?
        """,
        (
            auth_event_id,
            auth_id,
        ),
    ).fetchone()

    return row is not None


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


def _duration_days(
    started_at: str,
    ended_at: str,
) -> int:
    start = _parse_timestamp(started_at, "started_at")
    end = _parse_timestamp(ended_at, "ended_at")

    if end < start:
        return 0

    return (end - start).days


def _calculate_loc_context(
    conn: Any,
    auth_id: int,
    decision_at: str,
    current_loc: str,
) -> tuple[int | None, int | None]:
    decision_dt = _parse_timestamp(
        decision_at,
        "decision_at",
    )

    rows = conn.execute(
        """
        SELECT
            loc,
            started_at,
            ended_at
        FROM auth_loc_episodes
        WHERE auth_id = ?
        ORDER BY started_at, id
        """,
        (auth_id,),
    ).fetchall()

    if not rows:
        return None, None

    total_days = 0
    days_at_current_loc: int | None = None

    for row in rows:
        started_at = str(row["started_at"])
        start_dt = _parse_timestamp(
            started_at,
            "started_at",
        )

        if start_dt > decision_dt:
            continue

        if row["ended_at"] is None:
            effective_end = decision_dt
        else:
            episode_end = _parse_timestamp(
                str(row["ended_at"]),
                "ended_at",
            )
            effective_end = min(
                episode_end,
                decision_dt,
            )

        if effective_end < start_dt:
            continue

        episode_days = _duration_days(
            started_at,
            effective_end.isoformat(),
        )
        total_days += episode_days

        if (
            str(row["loc"]) == current_loc
            and start_dt <= decision_dt
            and (
                row["ended_at"] is None
                or _parse_timestamp(
                    str(row["ended_at"]),
                    "ended_at",
                )
                >= decision_dt
            )
        ):
            days_at_current_loc = episode_days

    return days_at_current_loc, total_days


def create_auth_decision_snapshot(
    auth_id: int,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    init_db()

    decision_at = str(payload["decision_at"]).strip()
    _parse_timestamp(
        decision_at,
        "decision_at",
    )

    outcome = str(payload["outcome"]).strip()

    if not outcome:
        raise InvalidAuthDecisionSnapshotError("outcome is required.")

    source = str(payload.get("source") or "manual").strip()

    if not source:
        raise InvalidAuthDecisionSnapshotError("source is required.")

    now = current_timestamp()

    with get_conn() as conn:
        auth_row = conn.execute(
            """
            SELECT
                facility,
                insurance,
                insurance_plan,
                loc,
                auth_type,
                requested_days,
                approved_days,
                denied_days,
                denial_reason_category,
                denial_source
            FROM auths
            WHERE id = ?
            """,
            (auth_id,),
        ).fetchone()

        if auth_row is None:
            return None

        auth_event_id = payload.get("auth_event_id")

        if auth_event_id is not None and not _auth_event_belongs_to_auth(
            conn,
            auth_id,
            int(auth_event_id),
        ):
            raise InvalidAuthDecisionSnapshotError(
                "auth_event_id must reference an event for this authorization."
            )

        facility = str(
            payload.get(
                "facility",
                auth_row["facility"],
            )
        ).strip()

        loc = str(
            payload.get(
                "loc",
                auth_row["loc"],
            )
        ).strip()

        auth_type = str(
            payload.get(
                "auth_type",
                auth_row["auth_type"],
            )
        ).strip()

        if not facility:
            raise InvalidAuthDecisionSnapshotError("facility is required.")

        if not loc:
            raise InvalidAuthDecisionSnapshotError("loc is required.")

        if not auth_type:
            raise InvalidAuthDecisionSnapshotError("auth_type is required.")

        insurance = payload.get(
            "insurance",
            auth_row["insurance"],
        )
        insurance_plan = payload.get(
            "insurance_plan",
            auth_row["insurance_plan"],
        )

        requested_days = int(
            payload.get(
                "requested_days",
                auth_row["requested_days"],
            )
            or 0
        )
        approved_days = int(
            payload.get(
                "approved_days",
                auth_row["approved_days"],
            )
            or 0
        )
        denied_days = int(
            payload.get(
                "denied_days",
                auth_row["denied_days"],
            )
            or 0
        )

        denial_reason_category = payload.get(
            "denial_reason_category",
            auth_row["denial_reason_category"],
        )
        denial_source = payload.get(
            "denial_source",
            auth_row["denial_source"],
        )

        days_at_current_loc, total_treatment_days = _calculate_loc_context(
            conn,
            auth_id,
            decision_at,
            loc,
        )

        cursor = conn.execute(
            """
            INSERT INTO auth_decision_snapshots (
                auth_id,
                auth_event_id,
                facility,
                insurance,
                insurance_plan,
                loc,
                auth_type,
                outcome,
                requested_days,
                approved_days,
                denied_days,
                decision_at,
                denial_reason_category,
                denial_source,
                days_at_current_loc,
                total_treatment_days,
                source,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                auth_id,
                auth_event_id,
                facility,
                insurance,
                insurance_plan,
                loc,
                auth_type,
                outcome,
                requested_days,
                approved_days,
                denied_days,
                decision_at,
                denial_reason_category,
                denial_source,
                days_at_current_loc,
                total_treatment_days,
                source,
                now,
                now,
            ),
        )

        snapshot_id = int(cursor.lastrowid)

    return get_auth_decision_snapshot(
        auth_id,
        snapshot_id,
    )


def list_auth_decision_snapshots(
    auth_id: int,
) -> list[dict[str, Any]] | None:
    init_db()

    with get_conn() as conn:
        if not _auth_exists(
            conn,
            auth_id,
        ):
            return None

        rows = conn.execute(
            """
            SELECT *
            FROM auth_decision_snapshots
            WHERE auth_id = ?
            ORDER BY decision_at, id
            """,
            (auth_id,),
        ).fetchall()

    return [_row_to_dict(row) for row in rows]


def get_auth_decision_snapshot(
    auth_id: int,
    snapshot_id: int,
) -> dict[str, Any] | None:
    init_db()

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM auth_decision_snapshots
            WHERE auth_id = ? AND id = ?
            """,
            (
                auth_id,
                snapshot_id,
            ),
        ).fetchone()

    if row is None:
        return None

    return _row_to_dict(row)

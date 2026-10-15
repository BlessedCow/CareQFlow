from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
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
        "reviewed_from": (
            str(row["reviewed_from"]) if row["reviewed_from"] is not None else None
        ),
        "reviewed_to": (
            str(row["reviewed_to"]) if row["reviewed_to"] is not None else None
        ),
        "reviewed_loc": (
            str(row["reviewed_loc"]) if row["reviewed_loc"] is not None else None
        ),
        "retro_reason": (
            str(row["retro_reason"]) if row["retro_reason"] is not None else None
        ),
        "context_derivation_version": int(row["context_derivation_version"]),
        "context_provenance": str(row["context_provenance"]),
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }


def _duration_days(
    started_at: str,
    ended_at: str,
) -> int:
    start = _normalized_timestamp(started_at, "started_at")
    end = _normalized_timestamp(ended_at, "ended_at")

    if end < start:
        return 0

    return (end - start).days


def _derive_loc_context(
    conn: Any,
    auth_id: int,
    decision_at: str,
    fallback_loc: str,
) -> tuple[str, int | None, int | None, str]:
    decision_dt = _normalized_timestamp(
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
        return fallback_loc, None, None, "auth_loc_fallback"

    total_days = 0
    active_loc: str | None = None
    days_at_current_loc: int | None = None

    for row in rows:
        started_at = str(row["started_at"])
        start_dt = _normalized_timestamp(
            started_at,
            "started_at",
        )

        if start_dt > decision_dt:
            continue

        ended_at = row["ended_at"]

        if ended_at is None:
            episode_end = None
            effective_end = decision_dt
        else:
            episode_end = _normalized_timestamp(
                str(ended_at),
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

        if start_dt <= decision_dt and (
            episode_end is None or episode_end >= decision_dt
        ):
            active_loc = str(row["loc"]).strip()
            days_at_current_loc = episode_days

    if active_loc is None:
        raise InvalidAuthDecisionSnapshotError(
            "No LOC episode is active at decision_at."
        )

    return (
        active_loc,
        days_at_current_loc,
        total_days,
        "loc_episode",
    )


def _automatic_outcome(auth_record: dict[str, Any]) -> str | None:
    status = str(auth_record.get("status") or "").strip()

    requested_days = int(auth_record.get("requested_days") or 0)
    approved_days = int(auth_record.get("approved_days") or 0)
    denied_days = int(auth_record.get("denied_days") or 0)

    if approved_days > 0 and denied_days > 0:
        return "Partial"

    if requested_days > 0 and 0 < approved_days < requested_days:
        return "Partial"

    if denied_days > 0 and approved_days == 0:
        return "Denied"

    if status == "Approved":
        return "Approved"

    if status == "Denied":
        return "Denied"

    return None


def _follow_up_snapshot_outcome(
    prefix: str,
    outcome: Any,
) -> str | None:
    normalized = str(outcome or "").strip()

    if not normalized:
        return None

    allowed_outcomes = {
        "P2P": {
            "Approved",
            "Denied",
            "Upheld",
            "Overturned",
        },
        "Appeal": {
            "Approved",
            "Denied",
            "Upheld",
            "Overturned",
        },
        "Retro": {
            "Approved",
            "Denied",
            "Partially Approved",
        },
    }

    if normalized not in allowed_outcomes[prefix]:
        return None

    return f"{prefix} {normalized}"


def _review_type_from_auth_type(auth_type: str) -> str:
    normalized = auth_type.strip().lower()

    mappings = {
        "initial": "initial",
        "concurrent": "concurrent",
        "loc change": "loc_change",
        "retro": "retro",
    }

    return mappings.get(normalized, "unknown")


def _normalized_timestamp(value: str, field_name: str) -> datetime:
    parsed = _parse_timestamp(
        value,
        field_name,
    )

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)

    return parsed.astimezone(UTC)


def _effective_snapshot_decision_at(row: Any) -> str:
    follow_up_decision_at = str(row["follow_up_decision_at"] or "").strip()

    if follow_up_decision_at:
        return follow_up_decision_at

    return str(row["decision_at"]).strip()


def _find_follow_up_parent_snapshot(
    conn: Any,
    auth_id: int,
    review_type: str,
    follow_up_decision_at: str,
) -> Any | None:
    follow_up_dt = _normalized_timestamp(
        follow_up_decision_at,
        "follow_up_decision_at",
    )

    rows = conn.execute(
        """
        SELECT *
        FROM auth_decision_snapshots
        WHERE
            auth_id = ?
            AND snapshot_role IN ('root', 'follow_up')
        ORDER BY id
        """,
        (auth_id,),
    ).fetchall()

    candidates: list[tuple[datetime, int, Any]] = []

    for row in rows:
        snapshot_role = str(row["snapshot_role"])
        snapshot_review_type = str(row["review_type"])
        outcome = str(row["outcome"])

        eligible = False

        if review_type == "p2p":
            eligible = snapshot_role == "root" and outcome in {"Denied", "Partial"}
        elif review_type == "appeal":
            eligible = (
                snapshot_role == "root" and outcome in {"Denied", "Partial"}
            ) or (
                snapshot_role == "follow_up"
                and snapshot_review_type == "p2p"
                and outcome in {"P2P Denied", "P2P Upheld"}
            )
        elif review_type == "retro":
            eligible = (
                (snapshot_role == "root" and outcome in {"Denied", "Partial"})
                or (
                    snapshot_role == "follow_up"
                    and snapshot_review_type == "p2p"
                    and outcome in {"P2P Denied", "P2P Upheld"}
                )
                or (
                    snapshot_role == "follow_up"
                    and snapshot_review_type == "appeal"
                    and outcome in {"Appeal Denied", "Appeal Upheld"}
                )
            )
        if not eligible:
            continue

        effective_decision_at = _effective_snapshot_decision_at(row)
        effective_dt = _normalized_timestamp(
            effective_decision_at,
            "decision_at",
        )

        if effective_dt > follow_up_dt:
            continue

        candidates.append(
            (
                effective_dt,
                int(row["id"]),
                row,
            )
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: (
            item[0],
            item[1],
        )
    )

    return candidates[-1][2]


def _create_automatic_follow_up_snapshot(
    auth_id: int,
    *,
    review_type: str,
    outcome: str,
    follow_up_decision_at: str,
    auth_event_id: int | None,
) -> dict[str, Any] | None:
    init_db()

    with get_conn() as conn:
        parent = _find_follow_up_parent_snapshot(
            conn,
            auth_id,
            review_type,
            follow_up_decision_at,
        )

        if parent is None:
            return None

        parent_effective_dt = _normalized_timestamp(
            _effective_snapshot_decision_at(parent),
            "parent_decision_at",
        )
        follow_up_dt = _normalized_timestamp(
            follow_up_decision_at,
            "follow_up_decision_at",
        )

        if follow_up_dt < parent_effective_dt:
            raise InvalidAuthDecisionSnapshotError(
                "follow_up_decision_at cannot be earlier than its parent decision."
            )

        if str(parent["snapshot_role"]) == "root":
            root_snapshot_id = int(parent["id"])
        else:
            if parent["root_snapshot_id"] is None:
                raise InvalidAuthDecisionSnapshotError(
                    "Follow-up parent is missing root_snapshot_id."
                )

            root_snapshot_id = int(parent["root_snapshot_id"])

        root = conn.execute(
            """
            SELECT *
            FROM auth_decision_snapshots
            WHERE auth_id = ? AND id = ?
            """,
            (
                auth_id,
                root_snapshot_id,
            ),
        ).fetchone()

        if root is None:
            raise InvalidAuthDecisionSnapshotError(
                "Root decision snapshot could not be found."
            )

        existing = conn.execute(
            """
            SELECT id
            FROM auth_decision_snapshots
            WHERE
                auth_id = ?
                AND snapshot_role = 'follow_up'
                AND review_type = ?
                AND root_snapshot_id = ?
                AND outcome = ?
                AND follow_up_decision_at = ?
                AND source = 'automatic'
            LIMIT 1
            """,
            (
                auth_id,
                review_type,
                root_snapshot_id,
                outcome,
                follow_up_decision_at,
            ),
        ).fetchone()

        if existing is not None:
            snapshot_id = int(existing["id"])
        else:
            now = current_timestamp()

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
                    snapshot_role,
                    review_type,
                    parent_snapshot_id,
                    root_snapshot_id,
                    follow_up_decision_at,
                    reviewed_from,
                    reviewed_to,
                    reviewed_loc,
                    retro_reason,
                    context_derivation_version,
                    context_provenance,
                    created_at,
                    updated_at
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    auth_id,
                    auth_event_id,
                    root["facility"],
                    root["insurance"],
                    root["insurance_plan"],
                    root["loc"],
                    root["auth_type"],
                    outcome,
                    root["requested_days"],
                    root["approved_days"],
                    root["denied_days"],
                    root["decision_at"],
                    root["denial_reason_category"],
                    root["denial_source"],
                    root["days_at_current_loc"],
                    root["total_treatment_days"],
                    "automatic",
                    "follow_up",
                    review_type,
                    int(parent["id"]),
                    root_snapshot_id,
                    follow_up_decision_at,
                    root["reviewed_from"],
                    root["reviewed_to"],
                    root["reviewed_loc"],
                    root["retro_reason"],
                    int(root["context_derivation_version"]),
                    "inherited_root",
                    now,
                    now,
                ),
            )

            snapshot_id = int(cursor.lastrowid)

    return get_auth_decision_snapshot(
        auth_id,
        snapshot_id,
    )


def _create_automatic_retro_root_snapshot(
    auth_record: dict[str, Any],
    *,
    outcome: str,
    auth_event_id: int | None,
) -> dict[str, Any] | None:
    auth_id = int(auth_record["id"])

    retro_decided_at = str(auth_record.get("retro_decided_at") or "").strip()
    reviewed_from = str(auth_record.get("retro_reviewed_from") or "").strip()
    reviewed_to = str(auth_record.get("retro_reviewed_to") or "").strip()
    reviewed_loc = str(auth_record.get("retro_reviewed_loc") or "").strip()
    retro_reason = str(auth_record.get("retro_reason") or "").strip()

    if not retro_decided_at:
        return None

    missing_fields = [
        field_name
        for field_name, value in (
            ("retro_reviewed_from", reviewed_from),
            ("retro_reviewed_to", reviewed_to),
            ("retro_reviewed_loc", reviewed_loc),
            ("retro_reason", retro_reason),
        )
        if not value
    ]

    if missing_fields:
        raise InvalidAuthDecisionSnapshotError(
            "Retro root snapshots require " + ", ".join(missing_fields) + "."
        )

    reviewed_from_dt = _normalized_timestamp(
        reviewed_from,
        "retro_reviewed_from",
    )
    reviewed_to_dt = _normalized_timestamp(
        reviewed_to,
        "retro_reviewed_to",
    )

    if reviewed_to_dt < reviewed_from_dt:
        raise InvalidAuthDecisionSnapshotError(
            "retro_reviewed_to cannot be earlier than retro_reviewed_from."
        )

    init_db()

    with get_conn() as conn:
        existing = conn.execute(
            """
            SELECT id
            FROM auth_decision_snapshots
            WHERE
                auth_id = ?
                AND snapshot_role = 'root'
                AND review_type = 'retro'
                AND outcome = ?
                AND decision_at = ?
                AND source = 'automatic'
            LIMIT 1
            """,
            (
                auth_id,
                outcome,
                retro_decided_at,
            ),
        ).fetchone()

    if existing is not None:
        return get_auth_decision_snapshot(
            auth_id,
            int(existing["id"]),
        )

    payload: dict[str, Any] = {
        "outcome": outcome,
        "decision_at": retro_decided_at,
        "source": "automatic",
        "snapshot_role": "root",
        "review_type": "retro",
        "loc": reviewed_loc,
        "reviewed_from": reviewed_from,
        "reviewed_to": reviewed_to,
        "reviewed_loc": reviewed_loc,
        "retro_reason": retro_reason,
    }

    if auth_event_id is not None:
        payload["auth_event_id"] = auth_event_id

    return create_auth_decision_snapshot(
        auth_id,
        payload,
    )


def create_automatic_follow_up_decision_snapshots(
    auth_record: dict[str, Any],
) -> list[dict[str, Any]]:
    auth_id = int(auth_record["id"])

    follow_up_decisions = (
        (
            "P2P",
            "p2p",
            "Peer Review",
            auth_record.get("p2p_outcome"),
            auth_record.get("p2p_decided_at"),
        ),
        (
            "Appeal",
            "appeal",
            "Appeal",
            auth_record.get("appeal_outcome"),
            auth_record.get("appeal_decided_at"),
        ),
    )

    created: list[dict[str, Any]] = []

    for (
        prefix,
        review_type,
        event_type,
        raw_outcome,
        raw_decision_at,
    ) in follow_up_decisions:
        outcome = _follow_up_snapshot_outcome(
            prefix,
            raw_outcome,
        )

        if outcome is None:
            continue

        follow_up_decision_at = str(raw_decision_at or "").strip()

        if not follow_up_decision_at:
            continue

        init_db()

        with get_conn() as conn:
            event_row = conn.execute(
                """
                SELECT id
                FROM auth_events
                WHERE
                    auth_id = ?
                    AND event_type = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (
                    auth_id,
                    event_type,
                ),
            ).fetchone()

            auth_event_id = int(event_row["id"]) if event_row is not None else None

        snapshot = _create_automatic_follow_up_snapshot(
            auth_id,
            review_type=review_type,
            outcome=outcome,
            follow_up_decision_at=follow_up_decision_at,
            auth_event_id=auth_event_id,
        )

        if snapshot is not None:
            created.append(snapshot)

    retro_outcome = _follow_up_snapshot_outcome(
        "Retro",
        auth_record.get("retro_outcome"),
    )
    retro_decided_at = str(auth_record.get("retro_decided_at") or "").strip()

    if retro_outcome is None or not retro_decided_at:
        return created

    init_db()

    with get_conn() as conn:
        event_row = conn.execute(
            """
            SELECT id
            FROM auth_events
            WHERE
                auth_id = ?
                AND event_type = 'Retro Auth'
            ORDER BY id DESC
            LIMIT 1
            """,
            (auth_id,),
        ).fetchone()

        auth_event_id = int(event_row["id"]) if event_row is not None else None

        existing_root = conn.execute(
            """
            SELECT id
            FROM auth_decision_snapshots
            WHERE
                auth_id = ?
                AND snapshot_role = 'root'
            ORDER BY id
            LIMIT 1
            """,
            (auth_id,),
        ).fetchone()

    if existing_root is not None:
        retro_snapshot = _create_automatic_follow_up_snapshot(
            auth_id,
            review_type="retro",
            outcome=retro_outcome,
            follow_up_decision_at=retro_decided_at,
            auth_event_id=auth_event_id,
        )
    else:
        retro_snapshot = _create_automatic_retro_root_snapshot(
            auth_record,
            outcome=retro_outcome,
            auth_event_id=auth_event_id,
        )

    if retro_snapshot is not None:
        created.append(retro_snapshot)

    return created


def create_automatic_auth_decision_snapshot(
    auth_record: dict[str, Any],
) -> dict[str, Any] | None:
    auth_id = int(auth_record["id"])

    auth_type = str(auth_record.get("auth_type") or "").strip().lower()

    if auth_type == "retro":
        return None

    outcome = _automatic_outcome(auth_record)

    if outcome is None:
        return None

    decision_at = str(auth_record.get("decision_at") or "").strip()

    if not decision_at:
        return None

    init_db()

    with get_conn() as conn:
        existing = conn.execute(
            """
            SELECT id
            FROM auth_decision_snapshots
            WHERE
                auth_id = ?
                AND outcome = ?
                AND decision_at = ?
                AND source = 'automatic'
            LIMIT 1
            """,
            (
                auth_id,
                outcome,
                decision_at,
            ),
        ).fetchone()

    if existing is not None:
        return get_auth_decision_snapshot(
            auth_id,
            int(existing["id"]),
        )

    return create_auth_decision_snapshot(
        auth_id,
        {
            "outcome": outcome,
            "decision_at": decision_at,
            "source": "automatic",
        },
    )


def create_auth_decision_snapshot(
    auth_id: int,
    payload: dict[str, Any],
    *,
    before_commit: Callable[[Any, dict[str, Any]], None] | None = None,
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

    snapshot_role = str(payload.get("snapshot_role") or "root").strip()

    if snapshot_role not in {"root", "legacy"}:
        raise InvalidAuthDecisionSnapshotError(
            "snapshot_role must be 'root' or 'legacy'."
        )

    reviewed_from = str(payload.get("reviewed_from") or "").strip()
    reviewed_to = str(payload.get("reviewed_to") or "").strip()
    reviewed_loc = str(payload.get("reviewed_loc") or "").strip()
    retro_reason = str(payload.get("retro_reason") or "").strip()

    has_reviewed_context = any(
        (
            reviewed_from,
            reviewed_to,
            reviewed_loc,
            retro_reason,
        )
    )

    if has_reviewed_context:
        if not all(
            (
                reviewed_from,
                reviewed_to,
                reviewed_loc,
                retro_reason,
            )
        ):
            raise InvalidAuthDecisionSnapshotError(
                "reviewed_from, reviewed_to, reviewed_loc, and "
                "retro_reason must be provided together."
            )

        reviewed_from_dt = _normalized_timestamp(
            reviewed_from,
            "reviewed_from",
        )
        reviewed_to_dt = _normalized_timestamp(
            reviewed_to,
            "reviewed_to",
        )

        if reviewed_to_dt < reviewed_from_dt:
            raise InvalidAuthDecisionSnapshotError(
                "reviewed_to cannot be earlier than reviewed_from."
            )

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

        fallback_loc = str(
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

        review_type = str(
            payload.get("review_type") or _review_type_from_auth_type(auth_type)
        ).strip()

        if not facility:
            raise InvalidAuthDecisionSnapshotError("facility is required.")

        if not fallback_loc:
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

        if has_reviewed_context:
            loc = reviewed_loc
            days_at_current_loc = None
            total_treatment_days = None
            context_provenance = "retro_review_context"
        else:
            (
                loc,
                days_at_current_loc,
                total_treatment_days,
                context_provenance,
            ) = _derive_loc_context(
                conn,
                auth_id,
                decision_at,
                fallback_loc,
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
                snapshot_role,
                review_type,
                parent_snapshot_id,
                root_snapshot_id,
                follow_up_decision_at,
                reviewed_from,
                reviewed_to,
                reviewed_loc,
                retro_reason,
                context_derivation_version,
                context_provenance,
                created_at,
                updated_at
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
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
                snapshot_role,
                review_type,
                None,
                None,
                None,
                reviewed_from or None,
                reviewed_to or None,
                reviewed_loc or None,
                retro_reason or None,
                2,
                context_provenance,
                now,
                now,
            ),
        )

        snapshot_id = int(cursor.lastrowid)

        if snapshot_role == "root":
            conn.execute(
                """
                UPDATE auth_decision_snapshots
                SET root_snapshot_id = ?
                WHERE id = ?
                """,
                (
                    snapshot_id,
                    snapshot_id,
                ),
            )

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
            raise RuntimeError(
                "Created authorization decision snapshot could not be reloaded."
            )

        snapshot = _row_to_dict(row)

        if before_commit is not None:
            before_commit(conn, snapshot)

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
            ORDER BY COALESCE(follow_up_decision_at, decision_at), id
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

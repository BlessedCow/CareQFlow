from __future__ import annotations

from datetime import datetime
from typing import Any

from authstatus_api.authorizations.state import current_timestamp
from authstatus_api.persistence.connections import get_conn
from authstatus_api.persistence.schema import init_db


class ClinicalAssessmentError(ValueError):
    pass


class InvalidClinicalAssessmentError(ClinicalAssessmentError):
    pass


def _parse_timestamp(value: str) -> str:
    normalized = value.strip()

    if not normalized:
        raise InvalidClinicalAssessmentError("assessed_at is required.")

    try:
        datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise InvalidClinicalAssessmentError(
            "assessed_at must be a valid ISO 8601 timestamp."
        ) from exc

    return normalized


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
        "instrument": str(row["instrument"]),
        "score": float(row["score"]),
        "assessed_at": str(row["assessed_at"]),
        "loc": (str(row["loc"]) if row["loc"] is not None else None),
        "source": str(row["source"]),
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }


def _prepare_assessment_values(
    payload: dict[str, Any],
    *,
    existing: Any | None = None,
) -> dict[str, Any]:
    instrument_value = payload.get(
        "instrument",
        existing["instrument"] if existing is not None else "",
    )
    instrument = str(instrument_value).strip()

    if not instrument:
        raise InvalidClinicalAssessmentError("instrument is required.")

    score_value = payload.get(
        "score",
        existing["score"] if existing is not None else None,
    )

    if score_value is None:
        raise InvalidClinicalAssessmentError("score is required.")

    try:
        score = float(score_value)
    except (TypeError, ValueError) as exc:
        raise InvalidClinicalAssessmentError("score must be numeric.") from exc

    assessed_at_value = payload.get(
        "assessed_at",
        existing["assessed_at"] if existing is not None else "",
    )
    assessed_at = _parse_timestamp(str(assessed_at_value))

    if "auth_event_id" in payload:
        auth_event_id = payload["auth_event_id"]
    elif existing is not None:
        auth_event_id = existing["auth_event_id"]
    else:
        auth_event_id = None

    if "loc" in payload:
        loc_value = payload["loc"]
        loc = str(loc_value).strip() if loc_value is not None else None
    elif existing is not None:
        loc = str(existing["loc"]) if existing["loc"] is not None else None
    else:
        loc = None

    if loc == "":
        loc = None

    source_value = payload.get(
        "source",
        existing["source"] if existing is not None else "manual",
    )
    source = str(source_value or "").strip()

    if not source:
        raise InvalidClinicalAssessmentError("source is required.")

    return {
        "instrument": instrument,
        "score": score,
        "assessed_at": assessed_at,
        "auth_event_id": auth_event_id,
        "loc": loc,
        "source": source,
    }


def create_clinical_assessment(
    auth_id: int,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    init_db()

    prepared = _prepare_assessment_values(payload)
    now = current_timestamp()

    with get_conn() as conn:
        if not _auth_exists(conn, auth_id):
            return None

        auth_event_id = prepared["auth_event_id"]

        if auth_event_id is not None and not _auth_event_belongs_to_auth(
            conn,
            auth_id,
            int(auth_event_id),
        ):
            raise InvalidClinicalAssessmentError(
                "auth_event_id must reference an event for this authorization."
            )

        cursor = conn.execute(
            """
            INSERT INTO clinical_assessments (
                auth_id,
                auth_event_id,
                instrument,
                score,
                assessed_at,
                loc,
                source,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                auth_id,
                auth_event_id,
                prepared["instrument"],
                prepared["score"],
                prepared["assessed_at"],
                prepared["loc"],
                prepared["source"],
                now,
                now,
            ),
        )

        assessment_id = int(cursor.lastrowid)

    return get_clinical_assessment(
        auth_id,
        assessment_id,
    )


def list_clinical_assessments(
    auth_id: int,
) -> list[dict[str, Any]] | None:
    init_db()

    with get_conn() as conn:
        if not _auth_exists(conn, auth_id):
            return None

        rows = conn.execute(
            """
            SELECT *
            FROM clinical_assessments
            WHERE auth_id = ?
            ORDER BY assessed_at, id
            """,
            (auth_id,),
        ).fetchall()

    return [_row_to_dict(row) for row in rows]


def get_clinical_assessment(
    auth_id: int,
    assessment_id: int,
) -> dict[str, Any] | None:
    init_db()

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM clinical_assessments
            WHERE auth_id = ? AND id = ?
            """,
            (
                auth_id,
                assessment_id,
            ),
        ).fetchone()

    if row is None:
        return None

    return _row_to_dict(row)


def update_clinical_assessment(
    auth_id: int,
    assessment_id: int,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    init_db()

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM clinical_assessments
            WHERE auth_id = ? AND id = ?
            """,
            (
                auth_id,
                assessment_id,
            ),
        ).fetchone()

        if row is None:
            return None

        prepared = _prepare_assessment_values(
            payload,
            existing=row,
        )

        auth_event_id = prepared["auth_event_id"]

        if auth_event_id is not None and not _auth_event_belongs_to_auth(
            conn,
            auth_id,
            int(auth_event_id),
        ):
            raise InvalidClinicalAssessmentError(
                "auth_event_id must reference an event for this authorization."
            )

        conn.execute(
            """
            UPDATE clinical_assessments
            SET
                auth_event_id = ?,
                instrument = ?,
                score = ?,
                assessed_at = ?,
                loc = ?,
                source = ?,
                updated_at = ?
            WHERE auth_id = ? AND id = ?
            """,
            (
                auth_event_id,
                prepared["instrument"],
                prepared["score"],
                prepared["assessed_at"],
                prepared["loc"],
                prepared["source"],
                current_timestamp(),
                auth_id,
                assessment_id,
            ),
        )

    return get_clinical_assessment(
        auth_id,
        assessment_id,
    )


def delete_clinical_assessment(
    auth_id: int,
    assessment_id: int,
) -> bool:
    init_db()

    with get_conn() as conn:
        cursor = conn.execute(
            """
            DELETE FROM clinical_assessments
            WHERE auth_id = ? AND id = ?
            """,
            (
                auth_id,
                assessment_id,
            ),
        )

        return cursor.rowcount > 0

from __future__ import annotations

from datetime import datetime
from typing import Any

from authstatus_api.authorizations.state import current_timestamp
from authstatus_api.persistence.connections import get_conn
from authstatus_api.persistence.schema import init_db


class AuthLocEpisodeError(ValueError):
    pass


class InvalidAuthLocEpisodeError(AuthLocEpisodeError):
    pass


class OverlappingAuthLocEpisodeError(AuthLocEpisodeError):
    pass


def _parse_timestamp(value: str, field_name: str) -> datetime:
    normalized = value.strip()

    if not normalized:
        raise InvalidAuthLocEpisodeError(f"{field_name} is required.")

    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise InvalidAuthLocEpisodeError(
            f"{field_name} must be a valid ISO 8601 timestamp."
        ) from exc


def _validate_episode_window(
    started_at: str,
    ended_at: str | None,
) -> None:
    start = _parse_timestamp(started_at, "started_at")

    if ended_at is None:
        return

    end = _parse_timestamp(ended_at, "ended_at")

    if end < start:
        raise InvalidAuthLocEpisodeError("ended_at cannot be earlier than started_at.")


def _auth_exists(conn: Any, auth_id: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM auths WHERE id = ?",
        (auth_id,),
    ).fetchone()

    return row is not None


def _row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "auth_id": int(row["auth_id"]),
        "loc": str(row["loc"]),
        "started_at": str(row["started_at"]),
        "ended_at": (str(row["ended_at"]) if row["ended_at"] is not None else None),
        "source": str(row["source"]),
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }


def _episode_overlaps(
    conn: Any,
    auth_id: int,
    started_at: str,
    ended_at: str | None,
    *,
    exclude_episode_id: int | None = None,
) -> bool:
    query = """
        SELECT 1
        FROM auth_loc_episodes
        WHERE auth_id = ?
          AND (
                ended_at IS NULL
                OR ended_at > ?
              )
          AND (
                ? IS NULL
                OR started_at < ?
              )
    """
    params: list[Any] = [
        auth_id,
        started_at,
        ended_at,
        ended_at,
    ]

    if exclude_episode_id is not None:
        query += " AND id != ?"
        params.append(exclude_episode_id)

    query += " LIMIT 1"

    return conn.execute(query, params).fetchone() is not None


def create_auth_loc_episode(
    auth_id: int,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    init_db()

    loc = str(payload["loc"]).strip()
    started_at = str(payload["started_at"]).strip()
    ended_at_value = payload.get("ended_at")
    ended_at = str(ended_at_value).strip() if ended_at_value is not None else None
    source = str(payload.get("source") or "manual").strip() or "manual"

    if not loc:
        raise InvalidAuthLocEpisodeError("loc is required.")

    _validate_episode_window(started_at, ended_at)

    now = current_timestamp()

    with get_conn() as conn:
        if not _auth_exists(conn, auth_id):
            return None

        if _episode_overlaps(
            conn,
            auth_id,
            started_at,
            ended_at,
        ):
            raise OverlappingAuthLocEpisodeError(
                "The LOC episode overlaps an existing episode."
            )

        cursor = conn.execute(
            """
            INSERT INTO auth_loc_episodes (
                auth_id,
                loc,
                started_at,
                ended_at,
                source,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                auth_id,
                loc,
                started_at,
                ended_at,
                source,
                now,
                now,
            ),
        )
        episode_id = int(cursor.lastrowid)

    return get_auth_loc_episode(auth_id, episode_id)


def list_auth_loc_episodes(
    auth_id: int,
) -> list[dict[str, Any]] | None:
    init_db()

    with get_conn() as conn:
        if not _auth_exists(conn, auth_id):
            return None

        rows = conn.execute(
            """
            SELECT *
            FROM auth_loc_episodes
            WHERE auth_id = ?
            ORDER BY started_at, id
            """,
            (auth_id,),
        ).fetchall()

    return [_row_to_dict(row) for row in rows]


def get_auth_loc_episode(
    auth_id: int,
    episode_id: int,
) -> dict[str, Any] | None:
    init_db()

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM auth_loc_episodes
            WHERE auth_id = ? AND id = ?
            """,
            (auth_id, episode_id),
        ).fetchone()

    if row is None:
        return None

    return _row_to_dict(row)


def update_auth_loc_episode(
    auth_id: int,
    episode_id: int,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    init_db()

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM auth_loc_episodes
            WHERE auth_id = ? AND id = ?
            """,
            (auth_id, episode_id),
        ).fetchone()

        if row is None:
            return None

        loc = str(payload.get("loc", row["loc"])).strip()
        started_at = str(payload.get("started_at", row["started_at"])).strip()

        if "ended_at" in payload:
            ended_at_value = payload["ended_at"]
            ended_at = (
                str(ended_at_value).strip() if ended_at_value is not None else None
            )
        else:
            ended_at = str(row["ended_at"]) if row["ended_at"] is not None else None

        source = str(payload.get("source", row["source"])).strip()

        if not loc:
            raise InvalidAuthLocEpisodeError("loc is required.")

        if not source:
            raise InvalidAuthLocEpisodeError("source is required.")

        _validate_episode_window(started_at, ended_at)

        if _episode_overlaps(
            conn,
            auth_id,
            started_at,
            ended_at,
            exclude_episode_id=episode_id,
        ):
            raise OverlappingAuthLocEpisodeError(
                "The LOC episode overlaps an existing episode."
            )

        conn.execute(
            """
            UPDATE auth_loc_episodes
            SET
                loc = ?,
                started_at = ?,
                ended_at = ?,
                source = ?,
                updated_at = ?
            WHERE auth_id = ? AND id = ?
            """,
            (
                loc,
                started_at,
                ended_at,
                source,
                current_timestamp(),
                auth_id,
                episode_id,
            ),
        )

    return get_auth_loc_episode(auth_id, episode_id)


def close_auth_loc_episode(
    auth_id: int,
    episode_id: int,
    ended_at: str,
) -> dict[str, Any] | None:
    return update_auth_loc_episode(
        auth_id,
        episode_id,
        {"ended_at": ended_at},
    )


def delete_auth_loc_episode(
    auth_id: int,
    episode_id: int,
) -> bool:
    init_db()

    with get_conn() as conn:
        cursor = conn.execute(
            """
            DELETE FROM auth_loc_episodes
            WHERE auth_id = ? AND id = ?
            """,
            (auth_id, episode_id),
        )

        return cursor.rowcount > 0

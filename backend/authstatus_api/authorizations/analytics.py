from __future__ import annotations

from typing import Any

from authstatus_api.authorizations.mappings import auth_row_to_dict
from authstatus_api.persistence.connections import get_conn
from authstatus_api.persistence.schema import init_db


def summarize_authorizations(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    by_status: dict[str, int] = {}
    by_loc: dict[str, int] = {}
    by_auth_type: dict[str, int] = {}

    no_pa_required = 0
    waiting_on_clinicals = 0

    for record in records:
        status = record.get("status") or "Unknown"
        loc = record.get("loc") or "Unknown"
        auth_type = record.get("auth_type") or "Unknown"

        by_status[status] = by_status.get(status, 0) + 1
        by_loc[loc] = by_loc.get(loc, 0) + 1
        by_auth_type[auth_type] = by_auth_type.get(auth_type, 0) + 1

        if record.get("no_pa_required"):
            no_pa_required += 1

        if record.get("waiting_on_clinicals"):
            waiting_on_clinicals += 1

    return {
        "total_auths": len(records),
        "by_status": by_status,
        "by_loc": by_loc,
        "by_auth_type": by_auth_type,
        "no_pa_required": no_pa_required,
        "waiting_on_clinicals": waiting_on_clinicals,
    }


def get_analytics_summary() -> dict[str, Any]:
    init_db()

    with get_conn() as conn:
        rows = conn.execute("""
            SELECT *
            FROM auths
            WHERE is_voided = 0
            ORDER BY auth_start_date, client_name
            """).fetchall()

    records = [auth_row_to_dict(row) for row in rows]

    return summarize_authorizations(records)

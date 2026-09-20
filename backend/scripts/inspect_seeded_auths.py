"""Inspect installed authorization values without modifying rows or running migrations."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backend-root", type=Path, default=Path(r"C:\Program Files\CareQueue\backend")
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(r"C:\ProgramData\CareQueue\Config\carequeue.env"),
    )
    parser.add_argument(
        "--auth-id",
        type=int,
        action="append",
        help="Limit output to these IDs; repeat as needed.",
    )
    args = parser.parse_args()
    if (
        not (args.backend_root / "authstatus_api").is_dir()
        or not args.env_file.is_file()
    ):
        parser.error("Supply an existing backend directory and environment file.")
    sys.path.insert(0, str(args.backend_root.resolve()))
    from dotenv import load_dotenv

    for name in tuple(os.environ):
        if name.startswith("AUTHSTATUS_"):
            os.environ.pop(name)
    load_dotenv(args.env_file, override=True)

    from pydantic import ValidationError

    from authstatus_api.authorizations.mappings import (
        auth_event_row_to_dict,
        auth_row_to_dict,
    )
    from authstatus_api.authorizations.timeline import current_auth_snapshot
    from authstatus_api.persistence.connections import get_conn
    from authstatus_api.persistence.paths import get_database_path
    from authstatus_api.schemas import AuthRecord
    from authstatus_api.settings import get_settings

    get_settings.cache_clear()
    if not get_database_path().is_file():
        parser.error("The configured database does not exist; no database was opened.")
    fields = (
        "id",
        "status",
        "requested_days",
        "approved_days",
        "denied_days",
        "auth_start_date",
        "auth_end_date",
        "review_due_date",
        "submitted_at",
        "decision_at",
        "p2p_outcome",
        "p2p_deadline",
        "appeal_outcome",
        "appeal_deadline",
        "retro_outcome",
        "retro_deadline",
    )
    event_fields = (
        "id",
        "event_type",
        "event_date",
        "outcome",
        "requested_days",
        "approved_days",
        "auth_start_date",
        "auth_end_date",
        "review_due_date",
    )
    conn = get_conn()
    try:
        conn.execute("PRAGMA query_only = ON")
        rows = conn.execute("SELECT * FROM auths ORDER BY id").fetchall()
        report = []
        for row in rows:
            if args.auth_id and row["id"] not in args.auth_id:
                continue
            auth = auth_row_to_dict(row)
            try:
                AuthRecord.model_validate(auth)
                errors = []
            except ValidationError as exc:
                # Report field names and error types, never patient values or secrets.
                errors = [
                    {"field": list(e["loc"]), "type": e["type"]} for e in exc.errors()
                ]
            events = [
                auth_event_row_to_dict(event)
                for event in conn.execute(
                    "SELECT * FROM auth_events WHERE auth_id = ? ORDER BY event_date, event_time, id",
                    (row["id"],),
                ).fetchall()
            ]
            snapshots = conn.execute(
                "SELECT id, outcome, requested_days, approved_days, denied_days, decision_at "
                "FROM auth_decision_snapshots WHERE auth_id = ? ORDER BY id",
                (row["id"],),
            ).fetchall()
            report.append(
                {
                    "stored_authorization": {
                        field: auth.get(field) for field in fields
                    },
                    "response_validation_errors": errors,
                    "events": [
                        {field: event.get(field) for field in event_fields}
                        for event in events
                    ],
                    "computed_timeline": current_auth_snapshot(events),
                    "decision_snapshots": [dict(snapshot) for snapshot in snapshots],
                }
            )
        print(
            json.dumps({"total_authorizations": len(rows), "records": report}, indent=2)
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()

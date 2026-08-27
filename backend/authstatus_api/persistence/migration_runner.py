from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from authstatus_api.persistence.migration_steps.audit import (
    add_audit_event_columns,
)
from authstatus_api.persistence.migration_steps.authorizations import (
    add_core_authorization_columns,
    add_denial_follow_up_columns,
)
from authstatus_api.persistence.migration_steps.governance import (
    enforce_append_only_governance_attestations,
)
from authstatus_api.persistence.migration_steps.security import (
    add_authentication_and_session_columns,
    add_walkthrough_columns,
)
from authstatus_api.persistence.migration_steps.governance_revision import (
    add_governance_document_revision,
)


class MigrationError(RuntimeError):
    pass


@dataclass(frozen=True)
class Migration:
    migration_id: str
    apply: Callable[[Any], None]


def _validate_migrations(migrations: list[Migration]) -> None:
    migration_ids = [migration.migration_id for migration in migrations]

    if any(not migration_id.strip() for migration_id in migration_ids):
        raise MigrationError("Migration IDs must not be empty.")

    duplicates = sorted(
        migration_id
        for migration_id in set(migration_ids)
        if migration_ids.count(migration_id) > 1
    )

    if duplicates:
        raise MigrationError(
            "Duplicate migration IDs are not allowed: " + ", ".join(duplicates)
        )


def _initialize_migration_table(conn: Any) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            migration_id TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
        """)


def get_applied_migration_ids(conn: Any) -> set[str]:
    _initialize_migration_table(conn)

    rows = conn.execute("""
        SELECT migration_id
        FROM schema_migrations
        """).fetchall()

    return {str(row["migration_id"]) for row in rows}


def run_migrations(
    conn: Any,
    migrations: Iterable[Migration],
) -> list[str]:
    migration_list = list(migrations)
    _validate_migrations(migration_list)

    ordered_migrations = sorted(
        migration_list,
        key=lambda migration: migration.migration_id,
    )

    _initialize_migration_table(conn)
    applied_migration_ids = get_applied_migration_ids(conn)
    newly_applied: list[str] = []

    for index, migration in enumerate(ordered_migrations):
        if migration.migration_id in applied_migration_ids:
            continue

        savepoint_name = f"carequeue_migration_{index}"
        conn.execute(f"SAVEPOINT {savepoint_name}")

        try:
            migration.apply(conn)

            conn.execute(
                """
                INSERT INTO schema_migrations (
                    migration_id,
                    applied_at
                )
                VALUES (?, ?)
                """,
                (
                    migration.migration_id,
                    datetime.now(UTC).isoformat(timespec="seconds"),
                ),
            )

            conn.execute(f"RELEASE SAVEPOINT {savepoint_name}")
        except Exception as exc:
            conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
            conn.execute(f"RELEASE SAVEPOINT {savepoint_name}")

            raise MigrationError(
                f"Database migration failed: {migration.migration_id}"
            ) from exc

        applied_migration_ids.add(migration.migration_id)
        newly_applied.append(migration.migration_id)

    return newly_applied


MIGRATIONS: tuple[Migration, ...] = (
    Migration(
        migration_id="0001_security_walkthrough_columns",
        apply=add_walkthrough_columns,
    ),
    Migration(
        migration_id="0002_security_authentication_and_session_columns",
        apply=add_authentication_and_session_columns,
    ),
    Migration(
        migration_id="0003_authorization_core_columns",
        apply=add_core_authorization_columns,
    ),
    Migration(
        migration_id="0004_authorization_denial_follow_up_columns",
        apply=add_denial_follow_up_columns,
    ),
    Migration(
        migration_id="0005_governance_append_only_history",
        apply=enforce_append_only_governance_attestations,
    ),
    Migration(
        migration_id="0006_audit_event_columns",
        apply=add_audit_event_columns,
    ),
    Migration(
        migration_id="0007_governance_document_revision",
        apply=add_governance_document_revision,
    ),
)


def run_registered_migrations(conn: Any) -> list[str]:
    return run_migrations(conn, MIGRATIONS)

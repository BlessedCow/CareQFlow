from __future__ import annotations

import sqlite3
from datetime import datetime

import pytest

from authstatus_api.persistence.migration_runner import (
    Migration,
    MigrationError,
    get_applied_migration_ids,
    run_migrations,
)
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
from authstatus_api.persistence.migration_steps.governance_revision import (
    add_governance_document_revision,
)
from authstatus_api.persistence.migration_steps.security import (
    add_authentication_and_session_columns,
    add_walkthrough_columns,
)


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row

    yield connection

    connection.close()


def test_run_migrations_creates_migration_history_table(conn):
    assert run_migrations(conn, []) == []

    row = conn.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'schema_migrations'
        """).fetchone()

    assert row is not None
    assert row["name"] == "schema_migrations"


def test_run_migrations_applies_migrations_in_id_order(conn):
    execution_order: list[str] = []

    migrations = [
        Migration(
            migration_id="0003_third",
            apply=lambda _conn: execution_order.append("third"),
        ),
        Migration(
            migration_id="0001_first",
            apply=lambda _conn: execution_order.append("first"),
        ),
        Migration(
            migration_id="0002_second",
            apply=lambda _conn: execution_order.append("second"),
        ),
    ]

    applied = run_migrations(conn, migrations)

    assert execution_order == [
        "first",
        "second",
        "third",
    ]
    assert applied == [
        "0001_first",
        "0002_second",
        "0003_third",
    ]


def test_run_migrations_applies_each_migration_only_once(conn):
    execution_count = 0

    def apply_migration(_conn):
        nonlocal execution_count
        execution_count += 1

    migrations = [
        Migration(
            migration_id="0001_once",
            apply=apply_migration,
        )
    ]

    first_run = run_migrations(conn, migrations)
    second_run = run_migrations(conn, migrations)

    assert first_run == ["0001_once"]
    assert second_run == []
    assert execution_count == 1
    assert get_applied_migration_ids(conn) == {"0001_once"}


def test_run_migrations_rejects_duplicate_migration_ids(conn):
    migrations = [
        Migration(
            migration_id="0001_duplicate",
            apply=lambda _conn: None,
        ),
        Migration(
            migration_id="0001_duplicate",
            apply=lambda _conn: None,
        ),
    ]

    with pytest.raises(
        MigrationError,
        match="Duplicate migration IDs are not allowed",
    ):
        run_migrations(conn, migrations)

    row = conn.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'schema_migrations'
        """).fetchone()

    assert row is None


def test_failed_migration_rolls_back_its_database_changes(conn):
    def fail_migration(connection):
        connection.execute("""
            CREATE TABLE should_not_survive (
                id INTEGER PRIMARY KEY
            )
            """)
        raise RuntimeError("forced migration failure")

    migrations = [
        Migration(
            migration_id="0001_failure",
            apply=fail_migration,
        )
    ]

    with pytest.raises(
        MigrationError,
        match="Database migration failed: 0001_failure",
    ):
        run_migrations(conn, migrations)

    table_row = conn.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'should_not_survive'
        """).fetchone()

    migration_row = conn.execute(
        """
        SELECT migration_id
        FROM schema_migrations
        WHERE migration_id = ?
        """,
        ("0001_failure",),
    ).fetchone()

    assert table_row is None
    assert migration_row is None


def test_successful_migration_records_applied_timestamp(conn):
    run_migrations(
        conn,
        [
            Migration(
                migration_id="0001_timestamp",
                apply=lambda _conn: None,
            )
        ],
    )

    row = conn.execute(
        """
        SELECT migration_id, applied_at
        FROM schema_migrations
        WHERE migration_id = ?
        """,
        ("0001_timestamp",),
    ).fetchone()

    assert row is not None
    assert row["migration_id"] == "0001_timestamp"

    applied_at = datetime.fromisoformat(row["applied_at"])

    assert applied_at.tzinfo is not None


def test_registered_migrations_apply_registered_registry(conn):
    from authstatus_api.persistence.migration_runner import (
        run_registered_migrations,
    )

    conn.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL
        )
        """)

    conn.execute("""
        CREATE TABLE sessions (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            token_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            revoked_at TEXT
        )
        """)

    conn.execute("""
        CREATE TABLE auths (
            id INTEGER PRIMARY KEY,
            facility TEXT NOT NULL,
            client_name TEXT NOT NULL,
            loc TEXT NOT NULL,
            submission_methods TEXT NOT NULL,
            auth_type TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)

    conn.execute("""
        CREATE TABLE auth_events (
            id INTEGER PRIMARY KEY,
            auth_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            event_date TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)

    conn.execute("""
        CREATE TABLE governance_attestations (
            id INTEGER PRIMARY KEY,
            attestation_version INTEGER NOT NULL,
            organization_name TEXT NOT NULL
        )
        """)

    conn.execute("""
        CREATE TABLE audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            resource_id INTEGER,
            created_at TEXT NOT NULL
        )
        """)

    applied = run_registered_migrations(conn)

    assert applied == [
        "0001_security_walkthrough_columns",
        "0002_security_authentication_and_session_columns",
        "0003_authorization_core_columns",
        "0004_authorization_denial_follow_up_columns",
        "0005_governance_append_only_history",
        "0006_audit_event_columns",
        "0007_governance_document_revision",
    ]
    assert get_applied_migration_ids(conn) == {
        "0001_security_walkthrough_columns",
        "0002_security_authentication_and_session_columns",
        "0003_authorization_core_columns",
        "0004_authorization_denial_follow_up_columns",
        "0005_governance_append_only_history",
        "0006_audit_event_columns",
        "0007_governance_document_revision",
    }

    governance_triggers = {row["name"] for row in conn.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'trigger'
              AND tbl_name = 'governance_attestations'
            """).fetchall()}

    assert governance_triggers == {
        "governance_attestations_prevent_delete",
        "governance_attestations_prevent_update",
    }

    governance_columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(governance_attestations)").fetchall()
    }

    assert "document_revision" in governance_columns

    columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()
    }

    session_columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(sessions)").fetchall()
    }

    assert "ip_address" in session_columns
    assert "user_agent" in session_columns

    assert "walkthrough_status" in columns
    assert "walkthrough_step" in columns

    auth_columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(auths)").fetchall()
    }

    event_columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(auth_events)").fetchall()
    }

    assert "member_id" in auth_columns
    assert "requested_days" in auth_columns
    assert "review_due_date" in auth_columns

    assert "requested_days" in event_columns
    assert "auth_start_date" in event_columns
    assert "review_due_date" in event_columns

    audit_columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(audit_events)").fetchall()
    }

    assert {
        "user_id",
        "username",
        "metadata",
        "ip_address",
        "user_agent",
        "previous_hash",
        "event_hash",
    }.issubset(audit_columns)


def test_schema_migrations_table_is_created_during_init_db(
    tmp_path,
    monkeypatch,
):
    from authstatus_api.persistence.schema import init_db
    from authstatus_api.settings import get_settings

    database_path = tmp_path / "auth_tracker.db"

    monkeypatch.setenv(
        "AUTHSTATUS_DATABASE_PATH",
        str(database_path),
    )
    get_settings.cache_clear()

    init_db()

    with sqlite3.connect(database_path) as connection:
        row = connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'schema_migrations'
            """).fetchone()

    assert row is not None
    assert row[0] == "schema_migrations"


def test_init_db_upgrades_legacy_users_table_and_preserves_existing_user(
    tmp_path,
    monkeypatch,
):
    from authstatus_api.persistence.schema import init_db
    from authstatus_api.settings import get_settings

    database_path = tmp_path / "auth_tracker.db"

    with sqlite3.connect(database_path) as connection:
        connection.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'UR',
                is_active INTEGER NOT NULL DEFAULT 1,
                failed_login_count INTEGER NOT NULL DEFAULT 0,
                locked_until TEXT,
                last_login_at TEXT,
                password_changed_at TEXT NOT NULL,
                must_change_password INTEGER NOT NULL DEFAULT 0,
                mfa_enabled INTEGER NOT NULL DEFAULT 0,
                mfa_secret TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """)

        connection.execute(
            """
            INSERT INTO users (
                username,
                password_hash,
                role,
                is_active,
                failed_login_count,
                password_changed_at,
                must_change_password,
                mfa_enabled,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "legacy-admin",
                "legacy-password-hash",
                "Admin",
                1,
                0,
                "2026-01-01T00:00:00+00:00",
                0,
                0,
                "2026-01-01T00:00:00+00:00",
                "2026-01-01T00:00:00+00:00",
            ),
        )

        connection.commit()

    monkeypatch.setenv(
        "AUTHSTATUS_DATABASE_PATH",
        str(database_path),
    )
    get_settings.cache_clear()

    init_db()

    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row

        user_row = connection.execute(
            """
            SELECT
                username,
                role,
                walkthrough_status,
                walkthrough_step
            FROM users
            WHERE username = ?
            """,
            ("legacy-admin",),
        ).fetchone()

        migration_row = connection.execute(
            """
            SELECT migration_id
            FROM schema_migrations
            WHERE migration_id = ?
            """,
            ("0001_security_walkthrough_columns",),
        ).fetchone()

        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(users)").fetchall()
        }

    assert user_row is not None
    assert user_row["username"] == "legacy-admin"
    assert user_row["role"] == "Admin"
    assert user_row["walkthrough_status"] == "pending"
    assert user_row["walkthrough_step"] is None

    assert "walkthrough_status" in columns
    assert "walkthrough_step" in columns

    assert migration_row is not None
    assert migration_row["migration_id"] == "0001_security_walkthrough_columns"


def test_init_db_applies_registered_migrations_in_order(
    tmp_path,
    monkeypatch,
):
    from authstatus_api.persistence.schema import init_db
    from authstatus_api.settings import get_settings

    database_path = tmp_path / "auth_tracker.db"

    with sqlite3.connect(database_path) as connection:
        connection.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'UR',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """)

        connection.execute("""
            CREATE TABLE sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                revoked_at TEXT
            )
            """)

        connection.execute(
            """
            INSERT INTO users (
                username,
                password_hash,
                role,
                is_active,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "legacy-admin",
                "legacy-password-hash",
                "Admin",
                1,
                "2026-01-01T00:00:00+00:00",
                "2026-01-01T00:00:00+00:00",
            ),
        )

        connection.execute(
            """
            INSERT INTO sessions (
                user_id,
                token_hash,
                created_at,
                last_seen_at,
                expires_at,
                revoked_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                "legacy-token",
                "2026-01-01T00:00:00+00:00",
                "2026-01-01T00:00:00+00:00",
                "2026-01-02T00:00:00+00:00",
                None,
            ),
        )

        connection.commit()

    monkeypatch.setenv(
        "AUTHSTATUS_DATABASE_PATH",
        str(database_path),
    )
    get_settings.cache_clear()

    init_db()

    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row

        migration_rows = connection.execute("""
            SELECT migration_id
            FROM schema_migrations
            ORDER BY migration_id
            """).fetchall()

        user_row = connection.execute(
            """
            SELECT
                username,
                failed_login_count,
                locked_until,
                last_login_at,
                password_changed_at,
                must_change_password,
                mfa_enabled,
                mfa_secret,
                walkthrough_status,
                walkthrough_step
            FROM users
            WHERE username = ?
            """,
            ("legacy-admin",),
        ).fetchone()

        session_row = connection.execute(
            """
            SELECT
                token_hash,
                ip_address,
                user_agent
            FROM sessions
            WHERE token_hash = ?
            """,
            ("legacy-token",),
        ).fetchone()

    assert [row["migration_id"] for row in migration_rows] == [
        "0001_security_walkthrough_columns",
        "0002_security_authentication_and_session_columns",
        "0003_authorization_core_columns",
        "0004_authorization_denial_follow_up_columns",
        "0005_governance_append_only_history",
        "0006_audit_event_columns",
        "0007_governance_document_revision",
    ]

    assert user_row is not None
    assert user_row["username"] == "legacy-admin"
    assert user_row["failed_login_count"] == 0
    assert user_row["locked_until"] is None
    assert user_row["last_login_at"] is None
    assert user_row["password_changed_at"] is None
    assert user_row["must_change_password"] == 0
    assert user_row["mfa_enabled"] == 0
    assert user_row["mfa_secret"] is None
    assert user_row["walkthrough_status"] == "pending"
    assert user_row["walkthrough_step"] is None

    assert session_row is not None
    assert session_row["token_hash"] == "legacy-token"
    assert session_row["ip_address"] is None
    assert session_row["user_agent"] is None


def test_init_db_upgrades_legacy_database_through_all_registered_migrations(
    tmp_path,
    monkeypatch,
):
    from authstatus_api.persistence.schema import init_db
    from authstatus_api.settings import get_settings

    database_path = tmp_path / "auth_tracker.db"

    with sqlite3.connect(database_path) as connection:
        connection.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'UR',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """)

        connection.execute("""
            CREATE TABLE sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                revoked_at TEXT
            )
            """)

        connection.execute("""
            CREATE TABLE auths (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                facility TEXT NOT NULL,
                client_name TEXT NOT NULL,
                loc TEXT NOT NULL,
                submission_methods TEXT NOT NULL,
                auth_type TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """)

        connection.execute("""
            CREATE TABLE auth_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                auth_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                event_date TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """)

        connection.execute(
            """
            INSERT INTO users (
                username,
                password_hash,
                role,
                is_active,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "legacy-admin",
                "legacy-password-hash",
                "Admin",
                1,
                "2026-01-01T00:00:00+00:00",
                "2026-01-01T00:00:00+00:00",
            ),
        )

        connection.execute(
            """
            INSERT INTO sessions (
                user_id,
                token_hash,
                created_at,
                last_seen_at,
                expires_at,
                revoked_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                "legacy-token",
                "2026-01-01T00:00:00+00:00",
                "2026-01-01T00:00:00+00:00",
                "2026-01-02T00:00:00+00:00",
                None,
            ),
        )

        connection.execute(
            """
            INSERT INTO auths (
                facility,
                client_name,
                loc,
                submission_methods,
                auth_type,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "Legacy Facility",
                "Legacy Client",
                "RTC",
                "Fax",
                "Initial",
                "Pending",
                "2026-01-01T00:00:00+00:00",
                "2026-01-01T00:00:00+00:00",
            ),
        )

        connection.execute(
            """
            INSERT INTO auth_events (
                auth_id,
                event_type,
                event_date,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                1,
                "Submitted",
                "2026-01-01",
                "2026-01-01T00:00:00+00:00",
                "2026-01-01T00:00:00+00:00",
            ),
        )

        connection.commit()

    monkeypatch.setenv(
        "AUTHSTATUS_DATABASE_PATH",
        str(database_path),
    )
    get_settings.cache_clear()

    init_db()

    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row

        migration_rows = connection.execute("""
            SELECT migration_id
            FROM schema_migrations
            ORDER BY migration_id
            """).fetchall()

        user_row = connection.execute(
            """
            SELECT
                username,
                failed_login_count,
                must_change_password,
                mfa_enabled,
                walkthrough_status,
                walkthrough_step
            FROM users
            WHERE username = ?
            """,
            ("legacy-admin",),
        ).fetchone()

        session_row = connection.execute(
            """
            SELECT
                token_hash,
                ip_address,
                user_agent
            FROM sessions
            WHERE token_hash = ?
            """,
            ("legacy-token",),
        ).fetchone()

        auth_row = connection.execute(
            """
            SELECT
                facility,
                client_name,
                insurance,
                requested_days,
                approved_days,
                denial_reason_category,
                denied_days,
                p2p_requested,
                appeal_submitted,
                retro_requested
            FROM auths
            WHERE id = ?
            """,
            (1,),
        ).fetchone()

        event_row = connection.execute(
            """
            SELECT
                event_type,
                requested_days,
                approved_days,
                auth_start_date,
                auth_end_date,
                review_due_date
            FROM auth_events
            WHERE id = ?
            """,
            (1,),
        ).fetchone()

    assert [row["migration_id"] for row in migration_rows] == [
        "0001_security_walkthrough_columns",
        "0002_security_authentication_and_session_columns",
        "0003_authorization_core_columns",
        "0004_authorization_denial_follow_up_columns",
        "0005_governance_append_only_history",
        "0006_audit_event_columns",
        "0007_governance_document_revision",
    ]

    assert user_row is not None
    assert user_row["username"] == "legacy-admin"
    assert user_row["failed_login_count"] == 0
    assert user_row["must_change_password"] == 0
    assert user_row["mfa_enabled"] == 0
    assert user_row["walkthrough_status"] == "pending"
    assert user_row["walkthrough_step"] is None

    assert session_row is not None
    assert session_row["token_hash"] == "legacy-token"
    assert session_row["ip_address"] is None
    assert session_row["user_agent"] is None

    assert auth_row is not None
    assert auth_row["facility"] == "Legacy Facility"
    assert auth_row["client_name"] == "Legacy Client"
    assert auth_row["insurance"] is None
    assert auth_row["requested_days"] == 0
    assert auth_row["approved_days"] == 0
    assert auth_row["denial_reason_category"] is None
    assert auth_row["denied_days"] == 0
    assert auth_row["p2p_requested"] == 0
    assert auth_row["appeal_submitted"] == 0
    assert auth_row["retro_requested"] == 0

    assert event_row is not None
    assert event_row["event_type"] == "Submitted"
    assert event_row["requested_days"] == 0
    assert event_row["approved_days"] == 0
    assert event_row["auth_start_date"] is None
    assert event_row["auth_end_date"] is None
    assert event_row["review_due_date"] is None


def test_walkthrough_migration_adds_columns_to_legacy_users_table(conn):
    conn.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL
        )
        """)

    applied = run_migrations(
        conn,
        [
            Migration(
                migration_id="0001_security_walkthrough_columns",
                apply=(
                    __import__(
                        "authstatus_api.persistence.migration_steps.security",
                        fromlist=["add_walkthrough_columns"],
                    ).add_walkthrough_columns
                ),
            )
        ],
    )

    columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()
    }

    assert applied == ["0001_security_walkthrough_columns"]
    assert "walkthrough_status" in columns
    assert "walkthrough_step" in columns


def test_walkthrough_migration_preserves_existing_user_rows(conn):
    conn.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL
        )
        """)

    conn.execute(
        """
        INSERT INTO users (
            id,
            username
        )
        VALUES (?, ?)
        """,
        (
            1,
            "legacy-admin",
        ),
    )

    run_migrations(
        conn,
        [
            Migration(
                migration_id="0001_security_walkthrough_columns",
                apply=add_walkthrough_columns,
            )
        ],
    )

    row = conn.execute(
        """
        SELECT
            username,
            walkthrough_status,
            walkthrough_step
        FROM users
        WHERE id = ?
        """,
        (1,),
    ).fetchone()

    assert row is not None
    assert row["username"] == "legacy-admin"
    assert row["walkthrough_status"] == "pending"
    assert row["walkthrough_step"] is None


def test_walkthrough_migration_accepts_database_with_existing_columns(conn):
    conn.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            walkthrough_status TEXT NOT NULL DEFAULT 'pending',
            walkthrough_step TEXT
        )
        """)

    run_migrations(
        conn,
        [
            Migration(
                migration_id="0001_security_walkthrough_columns",
                apply=add_walkthrough_columns,
            )
        ],
    )

    columns = [
        row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()
    ]

    assert columns.count("walkthrough_status") == 1
    assert columns.count("walkthrough_step") == 1


def test_authentication_migration_upgrades_legacy_security_schema(conn):
    conn.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)

    conn.execute("""
        CREATE TABLE sessions (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            token_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            revoked_at TEXT
        )
        """)

    applied = run_migrations(
        conn,
        [
            Migration(
                migration_id=("0002_security_authentication_and_session_columns"),
                apply=add_authentication_and_session_columns,
            )
        ],
    )

    user_columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()
    }

    session_columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(sessions)").fetchall()
    }

    assert applied == ["0002_security_authentication_and_session_columns"]

    assert {
        "failed_login_count",
        "locked_until",
        "last_login_at",
        "password_changed_at",
        "must_change_password",
        "mfa_enabled",
        "mfa_secret",
    }.issubset(user_columns)

    assert {
        "ip_address",
        "user_agent",
    }.issubset(session_columns)


def test_authentication_migration_preserves_existing_security_rows(conn):
    conn.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)

    conn.execute("""
        CREATE TABLE sessions (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            token_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            revoked_at TEXT
        )
        """)

    conn.execute(
        """
        INSERT INTO users (
            id,
            username,
            password_hash,
            role,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            1,
            "legacy-admin",
            "legacy-hash",
            "Admin",
            "2026-01-01T00:00:00+00:00",
            "2026-01-01T00:00:00+00:00",
        ),
    )

    conn.execute(
        """
        INSERT INTO sessions (
            id,
            user_id,
            token_hash,
            created_at,
            last_seen_at,
            expires_at,
            revoked_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            1,
            1,
            "legacy-token",
            "2026-01-01T00:00:00+00:00",
            "2026-01-01T00:00:00+00:00",
            "2026-01-02T00:00:00+00:00",
            None,
        ),
    )

    run_migrations(
        conn,
        [
            Migration(
                migration_id=("0002_security_authentication_and_session_columns"),
                apply=add_authentication_and_session_columns,
            )
        ],
    )

    user_row = conn.execute(
        """
        SELECT
            username,
            role,
            failed_login_count,
            locked_until,
            must_change_password,
            mfa_enabled
        FROM users
        WHERE id = ?
        """,
        (1,),
    ).fetchone()

    session_row = conn.execute(
        """
        SELECT
            token_hash,
            ip_address,
            user_agent
        FROM sessions
        WHERE id = ?
        """,
        (1,),
    ).fetchone()

    assert user_row is not None
    assert user_row["username"] == "legacy-admin"
    assert user_row["role"] == "Admin"
    assert user_row["failed_login_count"] == 0
    assert user_row["locked_until"] is None
    assert user_row["must_change_password"] == 0
    assert user_row["mfa_enabled"] == 0

    assert session_row is not None
    assert session_row["token_hash"] == "legacy-token"
    assert session_row["ip_address"] is None
    assert session_row["user_agent"] is None


def test_authentication_migration_accepts_current_security_schema(conn):
    conn.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            failed_login_count INTEGER NOT NULL DEFAULT 0,
            locked_until TEXT,
            last_login_at TEXT,
            password_changed_at TEXT,
            must_change_password INTEGER NOT NULL DEFAULT 0,
            mfa_enabled INTEGER NOT NULL DEFAULT 0,
            mfa_secret TEXT
        )
        """)

    conn.execute("""
        CREATE TABLE sessions (
            id INTEGER PRIMARY KEY,
            ip_address TEXT,
            user_agent TEXT
        )
        """)

    run_migrations(
        conn,
        [
            Migration(
                migration_id=("0002_security_authentication_and_session_columns"),
                apply=add_authentication_and_session_columns,
            )
        ],
    )

    user_columns = [
        row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()
    ]

    session_columns = [
        row["name"] for row in conn.execute("PRAGMA table_info(sessions)").fetchall()
    ]

    assert user_columns.count("failed_login_count") == 1
    assert user_columns.count("mfa_secret") == 1
    assert session_columns.count("ip_address") == 1
    assert session_columns.count("user_agent") == 1


def test_core_authorization_migration_upgrades_legacy_tables(conn):
    conn.execute("""
        CREATE TABLE auths (
            id INTEGER PRIMARY KEY,
            facility TEXT NOT NULL,
            client_name TEXT NOT NULL,
            loc TEXT NOT NULL,
            submission_methods TEXT NOT NULL,
            auth_type TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)

    conn.execute("""
        CREATE TABLE auth_events (
            id INTEGER PRIMARY KEY,
            auth_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            event_date TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)

    applied = run_migrations(
        conn,
        [
            Migration(
                migration_id="0003_authorization_core_columns",
                apply=add_core_authorization_columns,
            )
        ],
    )

    auth_columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(auths)").fetchall()
    }

    event_columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(auth_events)").fetchall()
    }

    assert applied == ["0003_authorization_core_columns"]

    assert {
        "member_id",
        "auth_number",
        "group_number",
        "date_of_birth",
        "insurance",
        "insurance_fax",
        "requested_days",
        "approved_days",
        "review_due_date",
        "programming_days",
        "submitted_at",
        "decision_at",
    }.issubset(auth_columns)

    assert {
        "requested_days",
        "approved_days",
        "auth_start_date",
        "auth_end_date",
        "review_due_date",
    }.issubset(event_columns)


def test_core_authorization_migration_preserves_existing_rows(conn):
    conn.execute("""
        CREATE TABLE auths (
            id INTEGER PRIMARY KEY,
            facility TEXT NOT NULL,
            client_name TEXT NOT NULL,
            loc TEXT NOT NULL,
            submission_methods TEXT NOT NULL,
            auth_type TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)

    conn.execute("""
        CREATE TABLE auth_events (
            id INTEGER PRIMARY KEY,
            auth_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            event_date TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)

    conn.execute(
        """
        INSERT INTO auths (
            id,
            facility,
            client_name,
            loc,
            submission_methods,
            auth_type,
            status,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            1,
            "Legacy Facility",
            "Legacy Client",
            "RTC",
            "Fax",
            "Initial",
            "Pending",
            "2026-01-01T00:00:00+00:00",
            "2026-01-01T00:00:00+00:00",
        ),
    )

    conn.execute(
        """
        INSERT INTO auth_events (
            id,
            auth_id,
            event_type,
            event_date,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            1,
            1,
            "Submitted",
            "2026-01-01",
            "2026-01-01T00:00:00+00:00",
            "2026-01-01T00:00:00+00:00",
        ),
    )

    run_migrations(
        conn,
        [
            Migration(
                migration_id="0003_authorization_core_columns",
                apply=add_core_authorization_columns,
            )
        ],
    )

    auth_row = conn.execute(
        """
        SELECT
            facility,
            client_name,
            requested_days,
            approved_days,
            insurance
        FROM auths
        WHERE id = ?
        """,
        (1,),
    ).fetchone()

    event_row = conn.execute(
        """
        SELECT
            event_type,
            requested_days,
            approved_days,
            review_due_date
        FROM auth_events
        WHERE id = ?
        """,
        (1,),
    ).fetchone()

    assert auth_row is not None
    assert auth_row["facility"] == "Legacy Facility"
    assert auth_row["client_name"] == "Legacy Client"
    assert auth_row["requested_days"] == 0
    assert auth_row["approved_days"] == 0
    assert auth_row["insurance"] is None

    assert event_row is not None
    assert event_row["event_type"] == "Submitted"
    assert event_row["requested_days"] == 0
    assert event_row["approved_days"] == 0
    assert event_row["review_due_date"] is None


def test_core_authorization_migration_accepts_current_schema(conn):
    conn.execute("""
        CREATE TABLE auths (
            id INTEGER PRIMARY KEY,
            member_id TEXT,
            auth_number TEXT,
            group_number TEXT,
            date_of_birth TEXT,
            insurance TEXT,
            insurance_fax TEXT,
            requested_days INTEGER NOT NULL DEFAULT 0,
            approved_days INTEGER NOT NULL DEFAULT 0,
            review_due_date TEXT,
            programming_days TEXT,
            submitted_at TEXT,
            decision_at TEXT
        )
        """)

    conn.execute("""
        CREATE TABLE auth_events (
            id INTEGER PRIMARY KEY,
            requested_days INTEGER NOT NULL DEFAULT 0,
            approved_days INTEGER NOT NULL DEFAULT 0,
            auth_start_date TEXT,
            auth_end_date TEXT,
            review_due_date TEXT
        )
        """)

    run_migrations(
        conn,
        [
            Migration(
                migration_id="0003_authorization_core_columns",
                apply=add_core_authorization_columns,
            )
        ],
    )

    auth_columns = [
        row["name"] for row in conn.execute("PRAGMA table_info(auths)").fetchall()
    ]

    event_columns = [
        row["name"] for row in conn.execute("PRAGMA table_info(auth_events)").fetchall()
    ]

    assert auth_columns.count("member_id") == 1
    assert auth_columns.count("review_due_date") == 1
    assert event_columns.count("requested_days") == 1
    assert event_columns.count("review_due_date") == 1


def test_denial_follow_up_migration_adds_workflow_columns(conn):
    conn.execute("""
        CREATE TABLE auths (
            id INTEGER PRIMARY KEY,
            facility TEXT NOT NULL,
            client_name TEXT NOT NULL,
            loc TEXT NOT NULL,
            submission_methods TEXT NOT NULL,
            auth_type TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)

    applied = run_migrations(
        conn,
        [
            Migration(
                migration_id="0004_authorization_denial_follow_up_columns",
                apply=add_denial_follow_up_columns,
            )
        ],
    )

    columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(auths)").fetchall()
    }

    assert applied == ["0004_authorization_denial_follow_up_columns"]

    assert {
        "denial_reason_category",
        "denial_reason_notes",
        "denial_prevention_notes",
        "denied_days",
        "denial_date",
        "denial_through_date",
        "denial_level_of_care",
        "denial_source",
        "p2p_requested",
        "p2p_scheduled_at",
        "p2p_deadline",
        "p2p_outcome",
        "p2p_reviewer",
        "p2p_notes",
        "appeal_submitted",
        "appeal_deadline",
        "appeal_outcome",
        "appeal_notes",
        "retro_requested",
        "retro_deadline",
        "retro_outcome",
        "retro_notes",
    }.issubset(columns)


def test_denial_follow_up_migration_preserves_existing_authorization(conn):
    conn.execute("""
        CREATE TABLE auths (
            id INTEGER PRIMARY KEY,
            facility TEXT NOT NULL,
            client_name TEXT NOT NULL,
            loc TEXT NOT NULL,
            submission_methods TEXT NOT NULL,
            auth_type TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)

    conn.execute(
        """
        INSERT INTO auths (
            id,
            facility,
            client_name,
            loc,
            submission_methods,
            auth_type,
            status,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            1,
            "Legacy Facility",
            "Legacy Client",
            "RTC",
            "Fax",
            "Initial",
            "Pending",
            "2026-01-01T00:00:00+00:00",
            "2026-01-01T00:00:00+00:00",
        ),
    )

    run_migrations(
        conn,
        [
            Migration(
                migration_id="0004_authorization_denial_follow_up_columns",
                apply=add_denial_follow_up_columns,
            )
        ],
    )

    row = conn.execute(
        """
        SELECT
            facility,
            client_name,
            denied_days,
            p2p_requested,
            appeal_submitted,
            retro_requested
        FROM auths
        WHERE id = ?
        """,
        (1,),
    ).fetchone()

    assert row is not None
    assert row["facility"] == "Legacy Facility"
    assert row["client_name"] == "Legacy Client"
    assert row["denied_days"] == 0
    assert row["p2p_requested"] == 0
    assert row["appeal_submitted"] == 0
    assert row["retro_requested"] == 0


def test_denial_follow_up_migration_accepts_current_schema(conn):
    conn.execute("""
        CREATE TABLE auths (
            id INTEGER PRIMARY KEY,
            denial_reason_category TEXT,
            denial_reason_notes TEXT,
            denial_prevention_notes TEXT,
            denied_days INTEGER NOT NULL DEFAULT 0,
            denial_date TEXT,
            denial_through_date TEXT,
            denial_level_of_care TEXT,
            denial_source TEXT,
            p2p_requested INTEGER NOT NULL DEFAULT 0,
            p2p_scheduled_at TEXT,
            p2p_deadline TEXT,
            p2p_outcome TEXT,
            p2p_reviewer TEXT,
            p2p_notes TEXT,
            appeal_submitted INTEGER NOT NULL DEFAULT 0,
            appeal_deadline TEXT,
            appeal_outcome TEXT,
            appeal_notes TEXT,
            retro_requested INTEGER NOT NULL DEFAULT 0,
            retro_deadline TEXT,
            retro_outcome TEXT,
            retro_notes TEXT
        )
        """)

    run_migrations(
        conn,
        [
            Migration(
                migration_id="0004_authorization_denial_follow_up_columns",
                apply=add_denial_follow_up_columns,
            )
        ],
    )

    columns = [
        row["name"] for row in conn.execute("PRAGMA table_info(auths)").fetchall()
    ]

    assert columns.count("denial_reason_category") == 1
    assert columns.count("denied_days") == 1
    assert columns.count("p2p_requested") == 1
    assert columns.count("appeal_submitted") == 1
    assert columns.count("retro_requested") == 1


def test_governance_append_only_migration_creates_protection_triggers(conn):
    conn.execute("""
        CREATE TABLE governance_attestations (
            id INTEGER PRIMARY KEY,
            attestation_version INTEGER NOT NULL,
            organization_name TEXT NOT NULL
        )
        """)

    applied = run_migrations(
        conn,
        [
            Migration(
                migration_id="0005_governance_append_only_history",
                apply=enforce_append_only_governance_attestations,
            )
        ],
    )

    trigger_rows = conn.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'trigger'
          AND tbl_name = 'governance_attestations'
        ORDER BY name
        """).fetchall()

    assert applied == ["0005_governance_append_only_history"]
    assert [row["name"] for row in trigger_rows] == [
        "governance_attestations_prevent_delete",
        "governance_attestations_prevent_update",
    ]


def test_governance_append_only_migration_blocks_attestation_update(conn):
    conn.execute("""
        CREATE TABLE governance_attestations (
            id INTEGER PRIMARY KEY,
            attestation_version INTEGER NOT NULL,
            organization_name TEXT NOT NULL
        )
        """)

    conn.execute("""
        INSERT INTO governance_attestations (
            id,
            attestation_version,
            organization_name
        )
        VALUES (1, 1, 'Original Facility')
        """)

    run_migrations(
        conn,
        [
            Migration(
                migration_id="0005_governance_append_only_history",
                apply=enforce_append_only_governance_attestations,
            )
        ],
    )

    with pytest.raises(
        sqlite3.IntegrityError,
        match="governance attestations are append-only",
    ):
        conn.execute("""
            UPDATE governance_attestations
            SET organization_name = 'Changed Facility'
            WHERE id = 1
            """)

    row = conn.execute("""
        SELECT organization_name
        FROM governance_attestations
        WHERE id = 1
        """).fetchone()

    assert row is not None
    assert row["organization_name"] == "Original Facility"


def test_governance_append_only_migration_blocks_attestation_delete(conn):
    conn.execute("""
        CREATE TABLE governance_attestations (
            id INTEGER PRIMARY KEY,
            attestation_version INTEGER NOT NULL,
            organization_name TEXT NOT NULL
        )
        """)

    conn.execute("""
        INSERT INTO governance_attestations (
            id,
            attestation_version,
            organization_name
        )
        VALUES (1, 1, 'Original Facility')
        """)

    run_migrations(
        conn,
        [
            Migration(
                migration_id="0005_governance_append_only_history",
                apply=enforce_append_only_governance_attestations,
            )
        ],
    )

    with pytest.raises(
        sqlite3.IntegrityError,
        match="governance attestations are append-only",
    ):
        conn.execute("""
            DELETE FROM governance_attestations
            WHERE id = 1
            """)

    row = conn.execute("""
        SELECT id
        FROM governance_attestations
        WHERE id = 1
        """).fetchone()

    assert row is not None
    assert row["id"] == 1


def test_governance_append_only_migration_is_idempotent(conn):
    conn.execute("""
        CREATE TABLE governance_attestations (
            id INTEGER PRIMARY KEY,
            attestation_version INTEGER NOT NULL,
            organization_name TEXT NOT NULL
        )
        """)

    migration = Migration(
        migration_id="0005_governance_append_only_history",
        apply=enforce_append_only_governance_attestations,
    )

    assert run_migrations(conn, [migration]) == ["0005_governance_append_only_history"]
    assert run_migrations(conn, [migration]) == []

    trigger_count = conn.execute("""
        SELECT COUNT(*) AS trigger_count
        FROM sqlite_master
        WHERE type = 'trigger'
          AND tbl_name = 'governance_attestations'
        """).fetchone()

    assert trigger_count is not None
    assert trigger_count["trigger_count"] == 2


def test_audit_event_columns_migration_upgrades_legacy_table(conn):
    conn.execute("""
        CREATE TABLE audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            resource_id INTEGER,
            created_at TEXT NOT NULL
        )
        """)

    applied = run_migrations(
        conn,
        [
            Migration(
                migration_id="0006_audit_event_columns",
                apply=add_audit_event_columns,
            )
        ],
    )

    columns = {
        row["name"]: row
        for row in conn.execute("PRAGMA table_info(audit_events)").fetchall()
    }

    assert applied == ["0006_audit_event_columns"]

    assert {
        "user_id",
        "username",
        "metadata",
        "ip_address",
        "user_agent",
        "previous_hash",
        "event_hash",
    }.issubset(columns)

    assert columns["metadata"]["notnull"] == 1
    assert columns["metadata"]["dflt_value"] == "'{}'"


def test_audit_event_columns_migration_preserves_existing_data(conn):
    conn.execute("""
        CREATE TABLE audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            resource_id INTEGER,
            created_at TEXT NOT NULL
        )
        """)

    conn.execute(
        """
        INSERT INTO audit_events (
            action,
            resource_type,
            resource_id,
            created_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            "legacy.action",
            "legacy_resource",
            42,
            "2026-01-01T00:00:00+00:00",
        ),
    )

    run_migrations(
        conn,
        [
            Migration(
                migration_id="0006_audit_event_columns",
                apply=add_audit_event_columns,
            )
        ],
    )

    row = conn.execute("""
        SELECT
            action,
            resource_type,
            resource_id,
            created_at,
            metadata,
            user_id,
            username,
            ip_address,
            user_agent,
            previous_hash,
            event_hash
        FROM audit_events
        WHERE id = 1
        """).fetchone()

    assert row is not None
    assert row["action"] == "legacy.action"
    assert row["resource_type"] == "legacy_resource"
    assert row["resource_id"] == 42
    assert row["created_at"] == "2026-01-01T00:00:00+00:00"

    assert row["metadata"] == "{}"
    assert row["user_id"] is None
    assert row["username"] is None
    assert row["ip_address"] is None
    assert row["user_agent"] is None
    assert row["previous_hash"] is None
    assert row["event_hash"] is None


def test_audit_event_columns_migration_preserves_current_schema(conn):
    conn.execute("""
        CREATE TABLE audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            action TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            resource_id INTEGER,
            metadata TEXT NOT NULL DEFAULT '{}',
            ip_address TEXT,
            user_agent TEXT,
            created_at TEXT NOT NULL,
            previous_hash TEXT,
            event_hash TEXT
        )
        """)

    applied = run_migrations(
        conn,
        [
            Migration(
                migration_id="0006_audit_event_columns",
                apply=add_audit_event_columns,
            )
        ],
    )

    assert applied == ["0006_audit_event_columns"]

    columns = [
        row["name"]
        for row in conn.execute("PRAGMA table_info(audit_events)").fetchall()
    ]

    assert columns == [
        "id",
        "user_id",
        "username",
        "action",
        "resource_type",
        "resource_id",
        "metadata",
        "ip_address",
        "user_agent",
        "created_at",
        "previous_hash",
        "event_hash",
    ]


def test_audit_event_columns_migration_is_idempotent(conn):
    conn.execute("""
        CREATE TABLE audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            resource_id INTEGER,
            created_at TEXT NOT NULL
        )
        """)

    migration = Migration(
        migration_id="0006_audit_event_columns",
        apply=add_audit_event_columns,
    )

    assert run_migrations(conn, [migration]) == ["0006_audit_event_columns"]
    assert run_migrations(conn, [migration]) == []


def test_governance_document_revision_migration_adds_column(conn):
    conn.execute("""
        CREATE TABLE governance_attestations (
            id INTEGER PRIMARY KEY,
            attestation_version INTEGER NOT NULL,
            organization_name TEXT NOT NULL
        )
        """)

    applied = run_migrations(
        conn,
        [
            Migration(
                migration_id="0007_governance_document_revision",
                apply=add_governance_document_revision,
            )
        ],
    )

    columns = {
        row["name"]: row
        for row in conn.execute("PRAGMA table_info(governance_attestations)").fetchall()
    }

    assert applied == ["0007_governance_document_revision"]
    assert "document_revision" in columns
    assert columns["document_revision"]["notnull"] == 0


def test_governance_document_revision_migration_preserves_history(conn):
    conn.execute("""
        CREATE TABLE governance_attestations (
            id INTEGER PRIMARY KEY,
            attestation_version INTEGER NOT NULL,
            organization_name TEXT NOT NULL
        )
        """)

    conn.execute("""
        INSERT INTO governance_attestations (
            id,
            attestation_version,
            organization_name
        )
        VALUES (1, 1, 'Legacy Facility')
        """)

    run_migrations(
        conn,
        [
            Migration(
                migration_id="0007_governance_document_revision",
                apply=add_governance_document_revision,
            )
        ],
    )

    row = conn.execute("""
        SELECT
            id,
            attestation_version,
            organization_name,
            document_revision
        FROM governance_attestations
        WHERE id = 1
        """).fetchone()

    assert row is not None
    assert row["id"] == 1
    assert row["attestation_version"] == 1
    assert row["organization_name"] == "Legacy Facility"
    assert row["document_revision"] is None


def test_governance_document_revision_migration_accepts_current_schema(conn):
    conn.execute("""
        CREATE TABLE governance_attestations (
            id INTEGER PRIMARY KEY,
            attestation_version INTEGER NOT NULL,
            organization_name TEXT NOT NULL,
            document_revision TEXT
        )
        """)

    applied = run_migrations(
        conn,
        [
            Migration(
                migration_id="0007_governance_document_revision",
                apply=add_governance_document_revision,
            )
        ],
    )

    columns = [
        row["name"]
        for row in conn.execute("PRAGMA table_info(governance_attestations)").fetchall()
    ]

    assert applied == ["0007_governance_document_revision"]
    assert columns.count("document_revision") == 1


def test_governance_document_revision_migration_is_idempotent(conn):
    conn.execute("""
        CREATE TABLE governance_attestations (
            id INTEGER PRIMARY KEY,
            attestation_version INTEGER NOT NULL,
            organization_name TEXT NOT NULL
        )
        """)

    migration = Migration(
        migration_id="0007_governance_document_revision",
        apply=add_governance_document_revision,
    )

    assert run_migrations(conn, [migration]) == ["0007_governance_document_revision"]
    assert run_migrations(conn, [migration]) == []

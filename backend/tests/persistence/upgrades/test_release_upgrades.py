from __future__ import annotations

import sqlite3
from contextlib import closing

import pytest

from authstatus_api.persistence.migration_runner import MIGRATIONS

V0_2_0_SCHEMA = """
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
    updated_at TEXT NOT NULL,
    CHECK (role IN ('Admin', 'UR', 'Read Only')),
    CHECK (is_active IN (0, 1)),
    CHECK (must_change_password IN (0, 1)),
    CHECK (failed_login_count >= 0)
);

CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT,
    ip_address TEXT,
    user_agent TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE mfa_login_challenges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    consumed_at TEXT,
    ip_address TEXT,
    user_agent TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE trusted_devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    last_used_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT,
    ip_address TEXT,
    user_agent TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE auths (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    facility TEXT NOT NULL,
    client_name TEXT NOT NULL,
    member_id TEXT,
    auth_number TEXT,
    group_number TEXT,
    date_of_birth TEXT,
    loc TEXT NOT NULL,
    insurance TEXT,
    insurance_phone TEXT,
    insurance_fax TEXT,
    submission_methods TEXT NOT NULL,
    portal_name TEXT,
    fax_numbers TEXT,
    live_call_type TEXT,
    scheduled_call_at TEXT,
    care_manager_enabled INTEGER NOT NULL DEFAULT 0,
    care_manager_details TEXT,
    notes_links TEXT,
    auth_type TEXT NOT NULL,
    status TEXT NOT NULL,
    discharge_clinical_needed INTEGER NOT NULL DEFAULT 0,
    no_pa_required INTEGER NOT NULL DEFAULT 0,
    progress_made INTEGER NOT NULL DEFAULT 0,
    facility_informed INTEGER NOT NULL DEFAULT 0,
    waiting_on_clinicals INTEGER NOT NULL DEFAULT 0,
    los_requested TEXT,
    days_approved TEXT,
    requested_days INTEGER NOT NULL DEFAULT 0,
    approved_days INTEGER NOT NULL DEFAULT 0,
    auth_start_date TEXT,
    auth_end_date TEXT,
    programming_days TEXT,
    submitted_at TEXT,
    review_due_date TEXT,
    decision_at TEXT,
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
    retro_notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE auth_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    auth_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    event_date TEXT NOT NULL,
    event_time TEXT,
    outcome TEXT,
    notes TEXT,
    requested_days INTEGER NOT NULL DEFAULT 0,
    approved_days INTEGER NOT NULL DEFAULT 0,
    auth_start_date TEXT,
    auth_end_date TEXT,
    review_due_date TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (auth_id) REFERENCES auths (id) ON DELETE CASCADE
);

CREATE TABLE auth_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    auth_id INTEGER NOT NULL,
    document_type TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    content_type TEXT NOT NULL,
    encrypted_pdf BLOB NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (auth_id) REFERENCES auths (id) ON DELETE CASCADE
);

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
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE registered_options (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    is_protected INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (
        category IN (
            'facility',
            'insurance',
            'web_portal'
        )
    ),
    CHECK (is_protected IN (0, 1)),
    UNIQUE (category, normalized_name)
);
"""


def _create_v0_2_0_database(database_path) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.executescript(V0_2_0_SCHEMA)

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
                "release-admin",
                "release-password-hash",
                "Admin",
                1,
                0,
                "2026-08-18T00:00:00+00:00",
                0,
                0,
                "2026-08-18T00:00:00+00:00",
                "2026-08-18T00:00:00+00:00",
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
                revoked_at,
                ip_address,
                user_agent
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                "release-session-token",
                "2026-08-18T00:00:00+00:00",
                "2026-08-18T00:05:00+00:00",
                "2026-08-19T00:00:00+00:00",
                None,
                "127.0.0.1",
                "CareQueue v0.2.0 test client",
            ),
        )

        connection.execute(
            """
            INSERT INTO auths (
                facility,
                client_name,
                member_id,
                auth_number,
                loc,
                insurance,
                submission_methods,
                auth_type,
                status,
                requested_days,
                approved_days,
                review_due_date,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "Release Facility",
                "Release Client",
                "MEMBER-020",
                "AUTH-020",
                "RTC",
                "Release Insurance",
                "Fax",
                "Initial",
                "Pending",
                7,
                3,
                "2026-08-25",
                "2026-08-18T00:00:00+00:00",
                "2026-08-18T00:00:00+00:00",
            ),
        )

        connection.execute(
            """
            INSERT INTO auth_events (
                auth_id,
                event_type,
                event_date,
                outcome,
                notes,
                requested_days,
                approved_days,
                review_due_date,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                "Submitted",
                "2026-08-18",
                "Pending",
                "Release event",
                7,
                3,
                "2026-08-25",
                "2026-08-18T00:00:00+00:00",
                "2026-08-18T00:00:00+00:00",
            ),
        )

        connection.execute(
            """
            INSERT INTO audit_events (
                user_id,
                username,
                action,
                resource_type,
                resource_id,
                metadata,
                ip_address,
                user_agent,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                "release-admin",
                "auth.created",
                "authorization",
                1,
                '{"release":"0.2.0"}',
                "127.0.0.1",
                "CareQueue v0.2.0 test client",
                "2026-08-18T00:00:00+00:00",
            ),
        )

        connection.execute(
            """
            INSERT INTO registered_options (
                category,
                name,
                normalized_name,
                is_protected,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "facility",
                "Release Facility",
                "release facility",
                0,
                "2026-08-18T00:00:00+00:00",
                "2026-08-18T00:00:00+00:00",
            ),
        )

        connection.commit()


def _create_v0_3_0_database(database_path) -> None:
    _create_v0_2_0_database(database_path)

    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute("""
            CREATE TABLE governance_attestations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attestation_version INTEGER NOT NULL,
                organization_name TEXT NOT NULL,
                deployment_mode TEXT NOT NULL,
                accepted_by_user_id INTEGER NOT NULL,
                accepted_at TEXT NOT NULL,
                app_version TEXT NOT NULL,
                FOREIGN KEY (accepted_by_user_id)
                    REFERENCES users (id)
                    ON DELETE RESTRICT,
                CHECK (attestation_version >= 1),
                CHECK (
                    deployment_mode IN (
                        'self_hosted',
                        'managed'
                    )
                )
            )
            """)

        connection.execute(
            """
            INSERT INTO governance_attestations (
                attestation_version,
                organization_name,
                deployment_mode,
                accepted_by_user_id,
                accepted_at,
                app_version
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                "Release Organization",
                "self_hosted",
                1,
                "2026-08-23T12:00:00+00:00",
                "0.3.0",
            ),
        )

        connection.execute("""
            CREATE TABLE audit_chain_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                head_event_id INTEGER,
                head_event_hash TEXT,
                state_hash TEXT
            )
            """)

        connection.commit()


def test_current_init_db_upgrades_released_v0_2_0_database(
    tmp_path,
    monkeypatch,
):
    from authstatus_api.persistence.schema import init_db
    from authstatus_api.settings import get_settings

    database_path = tmp_path / "auth_tracker.db"
    _create_v0_2_0_database(database_path)

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
                role,
                walkthrough_status,
                walkthrough_step
            FROM users
            WHERE id = ?
            """,
            (1,),
        ).fetchone()

        session_row = connection.execute(
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

        auth_row = connection.execute(
            """
            SELECT
                facility,
                client_name,
                member_id,
                auth_number,
                requested_days,
                approved_days,
                review_due_date
            FROM auths
            WHERE id = ?
            """,
            (1,),
        ).fetchone()

        event_row = connection.execute(
            """
            SELECT
                event_type,
                outcome,
                notes,
                requested_days,
                approved_days,
                review_due_date
            FROM auth_events
            WHERE id = ?
            """,
            (1,),
        ).fetchone()

        audit_row = connection.execute(
            """
            SELECT
                username,
                action,
                resource_type,
                resource_id,
                metadata,
                previous_hash,
                event_hash
            FROM audit_events
            WHERE id = ?
            """,
            (1,),
        ).fetchone()

        registered_option_row = connection.execute(
            """
            SELECT
                category,
                name,
                normalized_name
            FROM registered_options
            WHERE normalized_name = ?
            """,
            ("release facility",),
        ).fetchone()

        governance_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(governance_attestations)"
            ).fetchall()
        }

        governance_triggers = {row["name"] for row in connection.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'trigger'
                  AND tbl_name = 'governance_attestations'
                """).fetchall()}

        audit_chain_state_table = connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'audit_chain_state'
            """).fetchone()

    assert [row["migration_id"] for row in migration_rows] == [
        migration.migration_id for migration in MIGRATIONS
    ]

    assert user_row is not None
    assert user_row["username"] == "release-admin"
    assert user_row["role"] == "Admin"
    assert user_row["walkthrough_status"] == "pending"
    assert user_row["walkthrough_step"] is None

    assert session_row is not None
    assert session_row["token_hash"] == "release-session-token"
    assert session_row["ip_address"] == "127.0.0.1"
    assert session_row["user_agent"] == "CareQueue v0.2.0 test client"

    assert auth_row is not None
    assert auth_row["facility"] == "Release Facility"
    assert auth_row["client_name"] == "Release Client"
    assert auth_row["member_id"] == "MEMBER-020"
    assert auth_row["auth_number"] == "AUTH-020"
    assert auth_row["requested_days"] == 7
    assert auth_row["approved_days"] == 3
    assert auth_row["review_due_date"] == "2026-08-25"

    assert event_row is not None
    assert event_row["event_type"] == "Submitted"
    assert event_row["outcome"] == "Pending"
    assert event_row["notes"] == "Release event"
    assert event_row["requested_days"] == 7
    assert event_row["approved_days"] == 3
    assert event_row["review_due_date"] == "2026-08-25"

    assert audit_row is not None
    assert audit_row["username"] == "release-admin"
    assert audit_row["action"] == "auth.created"
    assert audit_row["resource_type"] == "authorization"
    assert audit_row["resource_id"] == 1
    assert audit_row["metadata"] == '{"release":"0.2.0"}'
    assert audit_row["previous_hash"] is None
    assert audit_row["event_hash"] is None

    assert registered_option_row is not None
    assert registered_option_row["category"] == "facility"
    assert registered_option_row["name"] == "Release Facility"
    assert registered_option_row["normalized_name"] == "release facility"

    assert "document_revision" in governance_columns
    assert governance_triggers == {
        "governance_attestations_prevent_delete",
        "governance_attestations_prevent_update",
    }
    assert audit_chain_state_table is not None


def test_current_recovery_activates_and_upgrades_v0_2_0_backup(
    tmp_path,
    monkeypatch,
):
    from cryptography.fernet import Fernet

    from authstatus_api.backups.recovery_activation import (
        RECOVERY_CONFIRMATION_PHRASE,
        activate_staged_database_recovery,
    )
    from authstatus_api.backups.service import (
        create_encrypted_database_backup,
        stage_encrypted_database_recovery,
        verify_encrypted_database_backup,
    )
    from authstatus_api.crypto import generate_encryption_key
    from authstatus_api.persistence.schema import init_db
    from authstatus_api.settings import get_settings

    active_database = tmp_path / "auth_tracker.db"
    released_database = tmp_path / "v0_2_0.db"
    backup_directory = tmp_path / "backups"
    restore_directory = tmp_path / "restores"

    backup_key = generate_encryption_key()
    monkeypatch.setenv("AUTHSTATUS_DATABASE_PATH", str(active_database))
    monkeypatch.setenv("AUTHSTATUS_BACKUP_DIRECTORY", str(backup_directory))
    monkeypatch.setenv("AUTHSTATUS_RESTORE_DIRECTORY", str(restore_directory))
    monkeypatch.setenv("AUTHSTATUS_BACKUP_ENCRYPTION_KEY", backup_key)
    monkeypatch.setenv("AUTHSTATUS_DATABASE_ENCRYPTION", "plaintext")
    get_settings.cache_clear()

    init_db()
    _create_v0_2_0_database(released_database)

    backup_directory.mkdir(exist_ok=True)
    released_backup = backup_directory / "auth_tracker_20260818_000000_000000.db.enc"
    released_backup.write_bytes(
        Fernet(backup_key.encode("utf-8")).encrypt(released_database.read_bytes())
    )

    verify_encrypted_database_backup(backup_path=released_backup)

    recovery_info = stage_encrypted_database_recovery(
        filename=released_backup.name,
        backup_directory=backup_directory,
        restore_directory=restore_directory,
    )

    staged_database = restore_directory / recovery_info["staged_filename"]
    rollback_database = tmp_path / "auth_tracker.pre_recovery.db"
    safety_backup = create_encrypted_database_backup(
        database_path=active_database,
        backup_directory=backup_directory,
    )
    verify_encrypted_database_backup(backup_path=safety_backup)

    plan = {
        "active_database": active_database.resolve(),
        "staged_database": staged_database.resolve(),
        "rollback_database": rollback_database.resolve(),
        "safety_backup": safety_backup.resolve(),
        "sidecars": [],
        "service_name": None,
        "api_host": "127.0.0.1",
        "api_port": 8000,
    }

    monkeypatch.setattr(
        "authstatus_api.backups.recovery_activation.verify_managed_service_stopped",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        "authstatus_api.backups.recovery_activation.verify_api_port_available",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        "authstatus_api.backups.recovery_activation.verify_exclusive_database_access",
        lambda: None,
    )

    result = activate_staged_database_recovery(
        plan=plan,
        confirmation=RECOVERY_CONFIRMATION_PHRASE,
    )

    assert result["active_database"] == active_database.resolve()
    assert result["rollback_database"] == rollback_database.resolve()
    assert result["safety_backup"] == safety_backup.resolve()
    assert rollback_database.exists()
    assert active_database.exists()
    assert not staged_database.exists()
    assert not (restore_directory / "pending_recovery.json").exists()

    with sqlite3.connect(active_database) as connection:
        recovered_user = connection.execute(
            "SELECT username, role FROM users WHERE id = ?",
            (1,),
        ).fetchone()
        recovered_auth = connection.execute(
            "SELECT client_name, auth_number FROM auths WHERE id = ?",
            (1,),
        ).fetchone()

    assert recovered_user == ("release-admin", "Admin")
    assert recovered_auth == ("Release Client", "AUTH-020")

    init_db()

    with sqlite3.connect(active_database) as connection:
        connection.row_factory = sqlite3.Row

        migration_rows = connection.execute("""
            SELECT migration_id
            FROM schema_migrations
            ORDER BY migration_id
            """).fetchall()

        user_row = connection.execute(
            """
            SELECT username, role, walkthrough_status, walkthrough_step
            FROM users
            WHERE id = ?
            """,
            (1,),
        ).fetchone()

        auth_row = connection.execute(
            """
            SELECT client_name, auth_number, requested_days, approved_days
            FROM auths
            WHERE id = ?
            """,
            (1,),
        ).fetchone()

    assert [row["migration_id"] for row in migration_rows] == [
        migration.migration_id for migration in MIGRATIONS
    ]

    assert user_row is not None
    assert user_row["username"] == "release-admin"
    assert user_row["role"] == "Admin"
    assert user_row["walkthrough_status"] == "pending"
    assert user_row["walkthrough_step"] is None

    assert auth_row is not None
    assert auth_row["client_name"] == "Release Client"
    assert auth_row["auth_number"] == "AUTH-020"
    assert auth_row["requested_days"] == 7
    assert auth_row["approved_days"] == 3


def test_failed_post_recovery_migration_preserves_recovery_paths(
    tmp_path,
    monkeypatch,
):
    from cryptography.fernet import Fernet

    from authstatus_api.backups.recovery_activation import (
        RECOVERY_CONFIRMATION_PHRASE,
        activate_staged_database_recovery,
    )
    from authstatus_api.backups.service import (
        create_encrypted_database_backup,
        stage_encrypted_database_recovery,
        verify_encrypted_database_backup,
    )
    from authstatus_api.crypto import generate_encryption_key
    from authstatus_api.persistence.migration_runner import MigrationError
    from authstatus_api.persistence.schema import init_db
    from authstatus_api.settings import get_settings

    active_database = tmp_path / "auth_tracker.db"
    released_database = tmp_path / "v0_2_0.db"
    backup_directory = tmp_path / "backups"
    restore_directory = tmp_path / "restores"

    backup_key = generate_encryption_key()

    monkeypatch.setenv(
        "AUTHSTATUS_DATABASE_PATH",
        str(active_database),
    )
    monkeypatch.setenv(
        "AUTHSTATUS_BACKUP_DIRECTORY",
        str(backup_directory),
    )
    monkeypatch.setenv(
        "AUTHSTATUS_RESTORE_DIRECTORY",
        str(restore_directory),
    )
    monkeypatch.setenv(
        "AUTHSTATUS_BACKUP_ENCRYPTION_KEY",
        backup_key,
    )
    monkeypatch.setenv(
        "AUTHSTATUS_DATABASE_ENCRYPTION",
        "plaintext",
    )
    get_settings.cache_clear()

    init_db()

    with closing(sqlite3.connect(active_database)) as connection:
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
                updated_at,
                walkthrough_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "pre-recovery-admin",
                "pre-recovery-password-hash",
                "Admin",
                1,
                0,
                "2026-08-27T00:00:00+00:00",
                0,
                0,
                "2026-08-27T00:00:00+00:00",
                "2026-08-27T00:00:00+00:00",
                "completed",
            ),
        )
        connection.commit()

    _create_v0_2_0_database(released_database)

    backup_directory.mkdir(exist_ok=True)

    released_backup = backup_directory / "auth_tracker_20260818_000000_000000.db.enc"
    released_backup.write_bytes(
        Fernet(backup_key.encode("utf-8")).encrypt(released_database.read_bytes())
    )

    verify_encrypted_database_backup(
        backup_path=released_backup,
    )

    recovery_info = stage_encrypted_database_recovery(
        filename=released_backup.name,
        backup_directory=backup_directory,
        restore_directory=restore_directory,
    )

    staged_database = restore_directory / recovery_info["staged_filename"]
    rollback_database = tmp_path / "auth_tracker.pre_recovery.db"

    safety_backup = create_encrypted_database_backup(
        database_path=active_database,
        backup_directory=backup_directory,
    )

    verify_encrypted_database_backup(
        backup_path=safety_backup,
    )

    plan = {
        "active_database": active_database.resolve(),
        "staged_database": staged_database.resolve(),
        "rollback_database": rollback_database.resolve(),
        "safety_backup": safety_backup.resolve(),
        "sidecars": [],
        "service_name": None,
        "api_host": "127.0.0.1",
        "api_port": 8000,
    }

    monkeypatch.setattr(
        "authstatus_api.backups.recovery_activation." "verify_managed_service_stopped",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        "authstatus_api.backups.recovery_activation." "verify_api_port_available",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        "authstatus_api.backups.recovery_activation."
        "verify_exclusive_database_access",
        lambda: None,
    )

    activate_staged_database_recovery(
        plan=plan,
        confirmation=RECOVERY_CONFIRMATION_PHRASE,
    )

    assert active_database.exists()
    assert rollback_database.exists()
    assert safety_backup.exists()

    def fail_registered_migrations(_conn):
        raise MigrationError("Simulated post-recovery migration failure.")

    monkeypatch.setattr(
        "authstatus_api.persistence.schema.run_registered_migrations",
        fail_registered_migrations,
    )

    with pytest.raises(
        MigrationError,
        match="Simulated post-recovery migration failure",
    ):
        init_db()

    assert active_database.exists()
    assert rollback_database.exists()
    assert safety_backup.exists()

    with closing(sqlite3.connect(active_database)) as connection:
        recovered_user = connection.execute(
            """
            SELECT username
            FROM users
            WHERE id = ?
            """,
            (1,),
        ).fetchone()

        migration_table = connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'schema_migrations'
            """).fetchone()

    assert recovered_user == ("release-admin",)
    assert migration_table is None

    with closing(sqlite3.connect(rollback_database)) as connection:
        original_user = connection.execute(
            """
            SELECT username
            FROM users
            WHERE username = ?
            """,
            ("pre-recovery-admin",),
        ).fetchone()

    assert original_user == ("pre-recovery-admin",)

    verify_encrypted_database_backup(
        backup_path=safety_backup,
    )


def test_current_init_db_upgrades_released_v0_3_0_database(
    tmp_path,
    monkeypatch,
):
    from authstatus_api.persistence.schema import init_db
    from authstatus_api.settings import get_settings

    database_path = tmp_path / "auth_tracker.db"
    _create_v0_3_0_database(database_path)

    monkeypatch.setenv(
        "AUTHSTATUS_DATABASE_PATH",
        str(database_path),
    )
    get_settings.cache_clear()

    init_db()

    with closing(sqlite3.connect(database_path)) as connection:
        connection.row_factory = sqlite3.Row

        migration_rows = connection.execute("""
            SELECT migration_id
            FROM schema_migrations
            ORDER BY migration_id
            """).fetchall()

        governance_row = connection.execute(
            """
            SELECT
                attestation_version,
                organization_name,
                deployment_mode,
                accepted_by_user_id,
                accepted_at,
                app_version,
                document_revision
            FROM governance_attestations
            WHERE id = ?
            """,
            (1,),
        ).fetchone()

        governance_triggers = {row["name"] for row in connection.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'trigger'
                  AND tbl_name = 'governance_attestations'
                """).fetchall()}

        user_row = connection.execute(
            """
            SELECT
                username,
                role,
                walkthrough_status,
                walkthrough_step
            FROM users
            WHERE id = ?
            """,
            (1,),
        ).fetchone()

        auth_row = connection.execute(
            """
            SELECT
                facility,
                client_name,
                auth_number,
                requested_days,
                approved_days
            FROM auths
            WHERE id = ?
            """,
            (1,),
        ).fetchone()

    assert [row["migration_id"] for row in migration_rows] == [
        migration.migration_id for migration in MIGRATIONS
    ]

    assert governance_row is not None
    assert governance_row["attestation_version"] == 1
    assert governance_row["organization_name"] == "Release Organization"
    assert governance_row["deployment_mode"] == "self_hosted"
    assert governance_row["accepted_by_user_id"] == 1
    assert governance_row["accepted_at"] == "2026-08-23T12:00:00+00:00"
    assert governance_row["app_version"] == "0.3.0"
    assert governance_row["document_revision"] is None

    assert governance_triggers == {
        "governance_attestations_prevent_delete",
        "governance_attestations_prevent_update",
    }

    assert user_row is not None
    assert user_row["username"] == "release-admin"
    assert user_row["role"] == "Admin"
    assert user_row["walkthrough_status"] == "pending"
    assert user_row["walkthrough_step"] is None

    assert auth_row is not None
    assert auth_row["facility"] == "Release Facility"
    assert auth_row["client_name"] == "Release Client"
    assert auth_row["auth_number"] == "AUTH-020"
    assert auth_row["requested_days"] == 7
    assert auth_row["approved_days"] == 3


def test_current_recovery_activates_and_upgrades_v0_3_0_backup(
    tmp_path,
    monkeypatch,
):
    from cryptography.fernet import Fernet

    from authstatus_api.backups.recovery_activation import (
        RECOVERY_CONFIRMATION_PHRASE,
        activate_staged_database_recovery,
    )
    from authstatus_api.backups.service import (
        create_encrypted_database_backup,
        stage_encrypted_database_recovery,
        verify_encrypted_database_backup,
    )
    from authstatus_api.crypto import generate_encryption_key
    from authstatus_api.persistence.schema import init_db
    from authstatus_api.settings import get_settings

    active_database = tmp_path / "auth_tracker.db"
    released_database = tmp_path / "v0_3_0.db"
    backup_directory = tmp_path / "backups"
    restore_directory = tmp_path / "restores"

    backup_key = generate_encryption_key()

    monkeypatch.setenv(
        "AUTHSTATUS_DATABASE_PATH",
        str(active_database),
    )
    monkeypatch.setenv(
        "AUTHSTATUS_BACKUP_DIRECTORY",
        str(backup_directory),
    )
    monkeypatch.setenv(
        "AUTHSTATUS_RESTORE_DIRECTORY",
        str(restore_directory),
    )
    monkeypatch.setenv(
        "AUTHSTATUS_BACKUP_ENCRYPTION_KEY",
        backup_key,
    )
    monkeypatch.setenv(
        "AUTHSTATUS_DATABASE_ENCRYPTION",
        "plaintext",
    )
    get_settings.cache_clear()

    init_db()
    _create_v0_3_0_database(released_database)

    backup_directory.mkdir(exist_ok=True)

    released_backup = backup_directory / "auth_tracker_20260823_120000_000000.db.enc"
    released_backup.write_bytes(
        Fernet(backup_key.encode("utf-8")).encrypt(released_database.read_bytes())
    )

    verify_encrypted_database_backup(
        backup_path=released_backup,
    )

    recovery_info = stage_encrypted_database_recovery(
        filename=released_backup.name,
        backup_directory=backup_directory,
        restore_directory=restore_directory,
    )

    staged_database = restore_directory / recovery_info["staged_filename"]
    rollback_database = tmp_path / "auth_tracker.pre_recovery.db"

    safety_backup = create_encrypted_database_backup(
        database_path=active_database,
        backup_directory=backup_directory,
    )

    verify_encrypted_database_backup(
        backup_path=safety_backup,
    )

    plan = {
        "active_database": active_database.resolve(),
        "staged_database": staged_database.resolve(),
        "rollback_database": rollback_database.resolve(),
        "safety_backup": safety_backup.resolve(),
        "sidecars": [],
        "service_name": None,
        "api_host": "127.0.0.1",
        "api_port": 8000,
    }

    monkeypatch.setattr(
        "authstatus_api.backups.recovery_activation." "verify_managed_service_stopped",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        "authstatus_api.backups.recovery_activation." "verify_api_port_available",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        "authstatus_api.backups.recovery_activation."
        "verify_exclusive_database_access",
        lambda: None,
    )

    result = activate_staged_database_recovery(
        plan=plan,
        confirmation=RECOVERY_CONFIRMATION_PHRASE,
    )

    assert result["active_database"] == active_database.resolve()
    assert result["rollback_database"] == rollback_database.resolve()
    assert result["safety_backup"] == safety_backup.resolve()

    assert active_database.exists()
    assert rollback_database.exists()
    assert safety_backup.exists()
    assert not staged_database.exists()
    assert not (restore_directory / "pending_recovery.json").exists()

    with closing(sqlite3.connect(active_database)) as connection:
        governance_before_migration = connection.execute(
            """
            SELECT
                attestation_version,
                organization_name,
                deployment_mode,
                accepted_by_user_id,
                accepted_at,
                app_version
            FROM governance_attestations
            WHERE id = ?
            """,
            (1,),
        ).fetchone()

    assert governance_before_migration == (
        1,
        "Release Organization",
        "self_hosted",
        1,
        "2026-08-23T12:00:00+00:00",
        "0.3.0",
    )

    init_db()

    with closing(sqlite3.connect(active_database)) as connection:
        connection.row_factory = sqlite3.Row

        migration_rows = connection.execute("""
            SELECT migration_id
            FROM schema_migrations
            ORDER BY migration_id
            """).fetchall()

        governance_row = connection.execute(
            """
            SELECT
                attestation_version,
                organization_name,
                deployment_mode,
                accepted_by_user_id,
                accepted_at,
                app_version,
                document_revision
            FROM governance_attestations
            WHERE id = ?
            """,
            (1,),
        ).fetchone()

        governance_triggers = {row["name"] for row in connection.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'trigger'
                  AND tbl_name = 'governance_attestations'
                """).fetchall()}

        user_row = connection.execute(
            """
            SELECT
                username,
                role,
                walkthrough_status,
                walkthrough_step
            FROM users
            WHERE id = ?
            """,
            (1,),
        ).fetchone()

        auth_row = connection.execute(
            """
            SELECT
                client_name,
                auth_number,
                requested_days,
                approved_days
            FROM auths
            WHERE id = ?
            """,
            (1,),
        ).fetchone()

    assert [row["migration_id"] for row in migration_rows] == [
        migration.migration_id for migration in MIGRATIONS
    ]

    assert governance_row is not None
    assert governance_row["attestation_version"] == 1
    assert governance_row["organization_name"] == "Release Organization"
    assert governance_row["deployment_mode"] == "self_hosted"
    assert governance_row["accepted_by_user_id"] == 1
    assert governance_row["accepted_at"] == "2026-08-23T12:00:00+00:00"
    assert governance_row["app_version"] == "0.3.0"
    assert governance_row["document_revision"] is None

    assert governance_triggers == {
        "governance_attestations_prevent_delete",
        "governance_attestations_prevent_update",
    }

    assert user_row is not None
    assert user_row["username"] == "release-admin"
    assert user_row["role"] == "Admin"
    assert user_row["walkthrough_status"] == "pending"
    assert user_row["walkthrough_step"] is None

    assert auth_row is not None
    assert auth_row["client_name"] == "Release Client"
    assert auth_row["auth_number"] == "AUTH-020"
    assert auth_row["requested_days"] == 7
    assert auth_row["approved_days"] == 3

    verify_encrypted_database_backup(
        backup_path=safety_backup,
    )

from __future__ import annotations

import sqlite3
from contextlib import closing

import pytest

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


def test_current_init_db_rejects_released_v0_2_0_plaintext_database(
    tmp_path,
    monkeypatch,
):
    from authstatus_api.persistence.connections import DatabaseEncryptionError
    from authstatus_api.persistence.schema import init_db
    from authstatus_api.settings import get_settings

    database_path = tmp_path / "auth_tracker.db"
    _create_v0_2_0_database(database_path)

    monkeypatch.setenv(
        "AUTHSTATUS_DATABASE_PATH",
        str(database_path),
    )
    get_settings.cache_clear()

    with pytest.raises(
        DatabaseEncryptionError,
        match="Unable to open the encrypted database",
    ):
        init_db()


def test_current_recovery_rejects_v0_2_0_plaintext_backup(
    tmp_path,
    monkeypatch,
):
    from cryptography.fernet import Fernet

    from authstatus_api.backups.service import (
        BackupError,
        verify_encrypted_database_backup,
    )
    from authstatus_api.crypto import generate_encryption_key
    from authstatus_api.settings import get_settings

    released_database = tmp_path / "v0_2_0.db"
    backup_directory = tmp_path / "backups"
    backup_key = generate_encryption_key()

    monkeypatch.setenv(
        "AUTHSTATUS_BACKUP_DIRECTORY",
        str(backup_directory),
    )
    monkeypatch.setenv(
        "AUTHSTATUS_BACKUP_ENCRYPTION_KEY",
        backup_key,
    )
    get_settings.cache_clear()

    _create_v0_2_0_database(released_database)

    backup_directory.mkdir(exist_ok=True)
    released_backup = backup_directory / "auth_tracker_20260818_000000_000000.db.enc"
    released_backup.write_bytes(
        Fernet(backup_key.encode("utf-8")).encrypt(released_database.read_bytes())
    )

    with pytest.raises(
        BackupError,
        match="not a valid SQLCipher database for the configured key",
    ):
        verify_encrypted_database_backup(
            backup_path=released_backup,
        )


def test_current_init_db_rejects_released_v0_3_0_plaintext_database(
    tmp_path,
    monkeypatch,
):
    from authstatus_api.persistence.connections import DatabaseEncryptionError
    from authstatus_api.persistence.schema import init_db
    from authstatus_api.settings import get_settings

    database_path = tmp_path / "auth_tracker.db"
    _create_v0_3_0_database(database_path)

    monkeypatch.setenv(
        "AUTHSTATUS_DATABASE_PATH",
        str(database_path),
    )
    get_settings.cache_clear()

    with pytest.raises(
        DatabaseEncryptionError,
        match="Unable to open the encrypted database",
    ):
        init_db()


def test_current_recovery_rejects_v0_3_0_plaintext_backup(
    tmp_path,
    monkeypatch,
):
    from cryptography.fernet import Fernet

    from authstatus_api.backups.service import (
        BackupError,
        verify_encrypted_database_backup,
    )
    from authstatus_api.crypto import generate_encryption_key
    from authstatus_api.settings import get_settings

    released_database = tmp_path / "v0_3_0.db"
    backup_directory = tmp_path / "backups"
    backup_key = generate_encryption_key()

    monkeypatch.setenv(
        "AUTHSTATUS_BACKUP_DIRECTORY",
        str(backup_directory),
    )
    monkeypatch.setenv(
        "AUTHSTATUS_BACKUP_ENCRYPTION_KEY",
        backup_key,
    )
    get_settings.cache_clear()

    _create_v0_3_0_database(released_database)

    backup_directory.mkdir(exist_ok=True)
    released_backup = backup_directory / "auth_tracker_20260823_120000_000000.db.enc"
    released_backup.write_bytes(
        Fernet(backup_key.encode("utf-8")).encrypt(released_database.read_bytes())
    )

    with pytest.raises(
        BackupError,
        match="not a valid SQLCipher database for the configured key",
    ):
        verify_encrypted_database_backup(
            backup_path=released_backup,
        )

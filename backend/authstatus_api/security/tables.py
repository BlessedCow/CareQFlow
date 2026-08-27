from __future__ import annotations

from typing import Any


def initialize_security_tables(conn: Any) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
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
            walkthrough_status TEXT NOT NULL DEFAULT 'pending',
            walkthrough_step TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CHECK (role IN ('Admin', 'UR', 'Read Only')),
            CHECK (is_active IN (0, 1)),
            CHECK (must_change_password IN (0, 1)),
            CHECK (failed_login_count >= 0),
            CHECK (walkthrough_status IN ('pending', 'completed', 'skipped'))
        )
        """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
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
        )
        """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS mfa_login_challenges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            consumed_at TEXT,
            ip_address TEXT,
            user_agent TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS trusted_devices (
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
        )
        """)

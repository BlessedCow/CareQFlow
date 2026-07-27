from pathlib import Path

import pytest

from authstatus_api.database_encryption.sqlcipher_probe import (
    plaintext_sqlite_can_read_database,
)
from authstatus_api.persistence.connections import (
    DatabaseEncryptionError,
    get_conn,
)
from authstatus_api.persistence.paths import (
    EXPECTED_DATABASE_DIRECTORY,
    DatabasePathError,
    get_database_path,
    resolve_database_path,
)
from authstatus_api.persistence.schema import init_db
from authstatus_api.settings import PROJECT_ROOT, get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()

    yield

    get_settings.cache_clear()


def test_default_relative_database_path_resolves_under_backend_data(monkeypatch):
    monkeypatch.delenv("AUTHSTATUS_DATABASE_PATH", raising=False)
    monkeypatch.delenv("AUTHSTATUS_ALLOW_UNSAFE_DATABASE_PATH", raising=False)
    get_settings.cache_clear()

    database_path = get_database_path()

    assert database_path == EXPECTED_DATABASE_DIRECTORY / "auth_tracker.db"


def test_absolute_database_path_is_allowed(tmp_path, monkeypatch):
    expected_path = tmp_path / "auth_tracker.db"
    monkeypatch.setenv("AUTHSTATUS_DATABASE_PATH", str(expected_path))
    get_settings.cache_clear()

    assert get_database_path() == expected_path.resolve()


def test_relative_database_path_outside_backend_data_is_rejected():
    with pytest.raises(DatabasePathError):
        resolve_database_path(Path("auth_tracker.db"))


def test_relative_database_path_outside_backend_data_can_be_explicitly_allowed():
    database_path = resolve_database_path(
        Path("auth_tracker.db"),
        allow_unsafe_database_path=True,
    )

    assert database_path == (PROJECT_ROOT / "auth_tracker.db").resolve()


def test_database_path_rejects_backup_directory():
    with pytest.raises(DatabasePathError):
        resolve_database_path(Path("../backups/auth_tracker.db"))


def test_database_path_rejects_restore_directory():
    with pytest.raises(DatabasePathError):
        resolve_database_path(Path("../restores/auth_tracker.db"))


def test_database_path_rejects_non_database_suffix(tmp_path):
    with pytest.raises(DatabasePathError):
        resolve_database_path(tmp_path / "auth_tracker.txt")


def test_get_conn_uses_plaintext_database_by_default(tmp_path, monkeypatch):
    database_path = tmp_path / "auth_tracker.db"

    monkeypatch.setenv("AUTHSTATUS_DATABASE_PATH", str(database_path))
    monkeypatch.delenv("AUTHSTATUS_DATABASE_ENCRYPTION", raising=False)
    get_settings.cache_clear()

    init_db()

    assert database_path.exists()
    assert plaintext_sqlite_can_read_database(database_path) is True


def test_get_conn_uses_sqlcipher_database_when_enabled(tmp_path, monkeypatch):
    database_path = tmp_path / "auth_tracker.sqlcipher.db"

    monkeypatch.setenv("AUTHSTATUS_DATABASE_PATH", str(database_path))
    monkeypatch.setenv("AUTHSTATUS_DATABASE_ENCRYPTION", "sqlcipher")
    monkeypatch.setenv("AUTHSTATUS_SQLCIPHER_KEY", "correct horse battery staple")
    get_settings.cache_clear()

    init_db()

    assert database_path.exists()
    assert plaintext_sqlite_can_read_database(database_path) is False

    with get_conn() as conn:
        row = conn.execute("""
            SELECT COUNT(*) AS table_count
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'auths'
            """).fetchone()

    assert row["table_count"] == 1


def test_sqlcipher_mode_requires_key(tmp_path, monkeypatch):
    database_path = tmp_path / "auth_tracker.sqlcipher.db"

    monkeypatch.setenv("AUTHSTATUS_DATABASE_PATH", str(database_path))
    monkeypatch.setenv("AUTHSTATUS_DATABASE_ENCRYPTION", "sqlcipher")
    monkeypatch.setenv("AUTHSTATUS_SQLCIPHER_KEY", "")
    get_settings.cache_clear()

    with pytest.raises(DatabaseEncryptionError):
        init_db()

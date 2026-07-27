from __future__ import annotations

import secrets
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError

from authstatus_api.settings import PROJECT_ROOT, Settings


def encryption_key() -> str:
    return Fernet.generate_key().decode("utf-8")


def valid_production_settings(**overrides):
    values = {
        "AUTHSTATUS_APP_ENVIRONMENT": "production",
        "AUTHSTATUS_DATABASE_ENCRYPTION": "sqlcipher",
        "AUTHSTATUS_SQLCIPHER_KEY": secrets.token_urlsafe(32),
        "AUTHSTATUS_ENCRYPTION_KEY": encryption_key(),
        "AUTHSTATUS_BACKUP_ENCRYPTION_KEY": encryption_key(),
        "AUTHSTATUS_SESSION_COOKIE_SECURE": True,
        "AUTHSTATUS_CORS_ORIGINS": "https://carequeue.example",
    }
    values.update(overrides)

    return Settings(
        _env_file=None,
        **values,
    )


def test_default_environment_is_development(monkeypatch):
    monkeypatch.delenv(
        "AUTHSTATUS_APP_ENVIRONMENT",
        raising=False,
    )

    settings = Settings(_env_file=None)

    assert settings.app_environment == "development"


@pytest.mark.parametrize(
    "value",
    [
        "development",
        "DEVELOPMENT",
        " test ",
    ],
)
def test_supported_environment_values_are_normalized(value):
    settings = Settings(
        _env_file=None,
        AUTHSTATUS_APP_ENVIRONMENT=value,
    )

    assert settings.app_environment == value.strip().lower()


def test_production_environment_is_normalized_with_secure_configuration():
    settings = valid_production_settings(
        AUTHSTATUS_APP_ENVIRONMENT=" PRODUCTION ",
    )

    assert settings.app_environment == "production"


def test_unsupported_environment_is_rejected():
    with pytest.raises(
        ValidationError,
        match="app_environment must be",
    ):
        Settings(
            _env_file=None,
            AUTHSTATUS_APP_ENVIRONMENT="staging",
        )


@pytest.mark.parametrize(
    "origin",
    [
        "ftp://carequeue.example",
        "carequeue.example",
        "https://user:password@carequeue.example",
        "https://carequeue.example/application",
        "https://carequeue.example?source=test",
        "https://carequeue.example#section",
    ],
)
def test_cors_origins_reject_non_origin_urls(origin):
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            AUTHSTATUS_CORS_ORIGINS=origin,
        )


def test_cors_origins_accept_json_environment_list():
    settings = Settings(
        _env_file=None,
        AUTHSTATUS_CORS_ORIGINS=(
            '["http://localhost:5173",' '"https://carequeue.example"]'
        ),
    )

    assert settings.cors_origins == [
        "http://localhost:5173",
        "https://carequeue.example",
    ]


@pytest.mark.parametrize(
    "value",
    [
        "[invalid-json",
        '{"origin": "https://carequeue.example"}',
        '["https://carequeue.example", 123]',
    ],
)
def test_cors_origins_reject_invalid_json_values(value):
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            AUTHSTATUS_CORS_ORIGINS=value,
        )


def test_cors_origins_are_normalized():
    settings = Settings(
        _env_file=None,
        AUTHSTATUS_CORS_ORIGINS=(
            "HTTP://LOCALHOST:5173/," "HTTPS://CAREQUEUE.EXAMPLE/"
        ),
    )

    assert settings.cors_origins == [
        "http://localhost:5173",
        "https://carequeue.example",
    ]


def test_cors_origins_reject_normalized_duplicates():
    with pytest.raises(
        ValidationError,
        match="CORS origins cannot contain duplicates",
    ):
        Settings(
            _env_file=None,
            AUTHSTATUS_CORS_ORIGINS=(
                "https://carequeue.example," "HTTPS://CAREQUEUE.EXAMPLE/"
            ),
        )


def test_production_allows_hostname_containing_localhost_text():
    settings = valid_production_settings(
        AUTHSTATUS_CORS_ORIGINS=("https://localhost-support.example"),
    )

    assert settings.cors_origins == [
        "https://localhost-support.example",
    ]


def test_production_requires_secure_session_cookie():
    with pytest.raises(
        ValidationError,
        match="Production requires secure session cookies",
    ):
        valid_production_settings(
            AUTHSTATUS_SESSION_COOKIE_SECURE=False,
        )


@pytest.mark.parametrize(
    "origin",
    [
        "*",
        "http://carequeue.example",
        "https://localhost:5173",
        "https://127.0.0.1:5173",
        "https://[::1]:5173",
    ],
)
def test_production_rejects_unsafe_cors_origins(origin):
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            AUTHSTATUS_APP_ENVIRONMENT="production",
            AUTHSTATUS_SESSION_COOKIE_SECURE=True,
            AUTHSTATUS_CORS_ORIGINS=origin,
        )


def test_production_accepts_secure_configuration():
    settings = valid_production_settings(
        AUTHSTATUS_CORS_ORIGINS=(
            "https://carequeue.example," "https://admin.carequeue.example"
        ),
    )

    assert settings.app_environment == "production"
    assert settings.database_encryption == "sqlcipher"
    assert settings.session_cookie_secure is True
    assert settings.cors_origins == [
        "https://carequeue.example",
        "https://admin.carequeue.example",
    ]


def test_production_rejects_plaintext_database_mode():
    with pytest.raises(
        ValidationError,
        match="Production requires SQLCipher",
    ):
        valid_production_settings(
            AUTHSTATUS_DATABASE_ENCRYPTION="plaintext",
        )


def test_production_requires_sqlcipher_key():
    with pytest.raises(
        ValidationError,
        match="AUTHSTATUS_SQLCIPHER_KEY",
    ):
        valid_production_settings(
            AUTHSTATUS_SQLCIPHER_KEY="",
        )


def test_production_rejects_short_sqlcipher_key():
    with pytest.raises(
        ValidationError,
        match="must be at least 32 characters",
    ):
        valid_production_settings(
            AUTHSTATUS_SQLCIPHER_KEY="a" * 31,
        )


@pytest.mark.parametrize(
    "value",
    [
        "change-me-change-me-change-me-value",
        "CHANGE_ME_CHANGE_ME_CHANGE_ME_VALUE",
        "password-password-password-password",
        "replace-this-replace-this-value-value",
        "your-key-here-your-key-here-value",
    ],
)
def test_production_rejects_placeholder_sqlcipher_key(value):
    with pytest.raises(
        ValidationError,
        match="cannot use a placeholder value",
    ):
        valid_production_settings(
            AUTHSTATUS_SQLCIPHER_KEY=value,
        )


def test_production_accepts_minimum_length_sqlcipher_key():
    sqlcipher_key = "a" * 32

    settings = valid_production_settings(
        AUTHSTATUS_SQLCIPHER_KEY=sqlcipher_key,
    )

    assert settings.sqlcipher_key == sqlcipher_key


def test_production_requires_field_encryption_key():
    with pytest.raises(
        ValidationError,
        match="AUTHSTATUS_ENCRYPTION_KEY",
    ):
        valid_production_settings(
            AUTHSTATUS_ENCRYPTION_KEY="",
        )


def test_production_rejects_invalid_field_encryption_key():
    with pytest.raises(
        ValidationError,
        match="valid AUTHSTATUS_ENCRYPTION_KEY",
    ):
        valid_production_settings(
            AUTHSTATUS_ENCRYPTION_KEY="invalid-key",
        )


def test_production_requires_backup_encryption_key():
    with pytest.raises(
        ValidationError,
        match="AUTHSTATUS_BACKUP_ENCRYPTION_KEY",
    ):
        valid_production_settings(
            AUTHSTATUS_BACKUP_ENCRYPTION_KEY="",
        )


def test_production_rejects_invalid_backup_encryption_key():
    with pytest.raises(
        ValidationError,
        match="valid AUTHSTATUS_BACKUP_ENCRYPTION_KEY",
    ):
        valid_production_settings(
            AUTHSTATUS_BACKUP_ENCRYPTION_KEY="invalid-key",
        )


def test_production_requires_separate_encryption_keys():
    shared_key = encryption_key()

    with pytest.raises(
        ValidationError,
        match="encryption keys must be different",
    ):
        valid_production_settings(
            AUTHSTATUS_ENCRYPTION_KEY=shared_key,
            AUTHSTATUS_BACKUP_ENCRYPTION_KEY=shared_key,
        )


def test_production_rejects_database_path_outside_data_directory():
    with pytest.raises(
        ValidationError,
        match="database paths must resolve under backend/data",
    ):
        valid_production_settings(
            AUTHSTATUS_DATABASE_PATH=Path("production/auth_tracker.sqlcipher.db"),
        )


def test_production_allows_explicit_external_database_path():
    database_path = PROJECT_ROOT / "production" / "auth_tracker.sqlcipher.db"

    settings = valid_production_settings(
        AUTHSTATUS_DATABASE_PATH=database_path,
        AUTHSTATUS_ALLOW_UNSAFE_DATABASE_PATH=True,
    )

    assert settings.database_path == database_path


def test_production_rejects_external_backup_directory():
    with pytest.raises(
        ValidationError,
        match="backup directories must resolve under backend/backups",
    ):
        valid_production_settings(
            AUTHSTATUS_BACKUP_DIRECTORY=Path("production/backups"),
        )


def test_production_rejects_external_restore_directory():
    with pytest.raises(
        ValidationError,
        match="restore directories must resolve under backend/restores",
    ):
        valid_production_settings(
            AUTHSTATUS_RESTORE_DIRECTORY=Path("production/restores"),
        )


def test_production_allows_explicit_external_storage_directories():
    backup_directory = PROJECT_ROOT / "production" / "backups"
    restore_directory = PROJECT_ROOT / "production" / "restores"

    settings = valid_production_settings(
        AUTHSTATUS_BACKUP_DIRECTORY=backup_directory,
        AUTHSTATUS_RESTORE_DIRECTORY=restore_directory,
        AUTHSTATUS_ALLOW_UNSAFE_STORAGE_PATHS=True,
    )

    assert settings.backup_directory == backup_directory
    assert settings.restore_directory == restore_directory


def test_production_rejects_shared_backup_and_restore_directory():
    with pytest.raises(
        ValidationError,
        match="backup and restore directories must be different",
    ):
        valid_production_settings(
            AUTHSTATUS_RESTORE_DIRECTORY=Path("backend/backups"),
            AUTHSTATUS_ALLOW_UNSAFE_STORAGE_PATHS=True,
        )


def test_production_rejects_overlapping_storage_directories():
    with pytest.raises(
        ValidationError,
        match="backup and restore directories cannot overlap",
    ):
        valid_production_settings(
            AUTHSTATUS_BACKUP_DIRECTORY=Path("backend/backups"),
            AUTHSTATUS_RESTORE_DIRECTORY=Path("backend/backups/restores"),
            AUTHSTATUS_ALLOW_UNSAFE_STORAGE_PATHS=True,
        )


def test_production_rejects_database_inside_backup_directory():
    with pytest.raises(
        ValidationError,
        match="database files cannot be stored inside",
    ):
        valid_production_settings(
            AUTHSTATUS_DATABASE_PATH=Path("backend/backups/auth_tracker.sqlcipher.db"),
            AUTHSTATUS_ALLOW_UNSAFE_DATABASE_PATH=True,
            AUTHSTATUS_ALLOW_UNSAFE_STORAGE_PATHS=True,
        )

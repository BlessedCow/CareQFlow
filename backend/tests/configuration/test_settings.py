from __future__ import annotations

import secrets
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError

from authstatus_api.settings import Settings


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


def test_backup_retention_defaults_are_safe():
    settings = Settings(_env_file=None)

    assert settings.backup_retention_days == 90
    assert settings.backup_minimum_count == 5


def test_backup_retention_settings_accept_environment_values():
    settings = Settings(
        _env_file=None,
        AUTHSTATUS_BACKUP_RETENTION_DAYS="60",
        AUTHSTATUS_BACKUP_MINIMUM_COUNT="10",
    )

    assert settings.backup_retention_days == 60
    assert settings.backup_minimum_count == 10


@pytest.mark.parametrize(
    ("setting_name", "value"),
    [
        ("AUTHSTATUS_BACKUP_RETENTION_DAYS", 0),
        ("AUTHSTATUS_BACKUP_RETENTION_DAYS", -1),
        ("AUTHSTATUS_BACKUP_MINIMUM_COUNT", 0),
        ("AUTHSTATUS_BACKUP_MINIMUM_COUNT", -1),
    ],
)
def test_backup_retention_settings_reject_values_below_one(
    setting_name,
    value,
):
    with pytest.raises(
        ValidationError,
        match="greater than or equal to 1",
    ):
        Settings(
            _env_file=None,
            **{
                setting_name: value,
            },
        )


@pytest.mark.parametrize(
    "setting_name",
    [
        "AUTHSTATUS_BACKUP_RETENTION_DAYS",
        "AUTHSTATUS_BACKUP_MINIMUM_COUNT",
    ],
)
def test_backup_retention_settings_reject_non_integer_values(
    setting_name,
):
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            **{
                setting_name: "invalid",
            },
        )


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


def test_session_inactivity_defaults_to_twenty_minutes():
    settings = Settings()

    assert settings.session_inactivity_minutes == 20


@pytest.mark.parametrize(
    "minutes",
    [
        "0",
        "4",
        "481",
    ],
)
def test_session_inactivity_rejects_out_of_range_values(
    minutes,
):
    with pytest.raises(ValidationError):
        Settings(
            AUTHSTATUS_SESSION_INACTIVITY_MINUTES=minutes,
        )


@pytest.mark.parametrize(
    "minutes",
    [
        "5",
        "20",
        "60",
        "480",
    ],
)
def test_session_inactivity_accepts_supported_values(
    minutes,
):
    settings = Settings(
        AUTHSTATUS_SESSION_INACTIVITY_MINUTES=minutes,
    )

    assert settings.session_inactivity_minutes == int(minutes)


def test_production_requires_secure_session_cookie():
    with pytest.raises(
        ValidationError,
        match="Production requires secure session cookies",
    ):
        valid_production_settings(
            AUTHSTATUS_SESSION_COOKIE_SECURE=False,
        )


@pytest.mark.parametrize(
    "setting_name",
    [
        "AUTHSTATUS_SESSION_COOKIE_NAME",
        "AUTHSTATUS_CSRF_COOKIE_NAME",
        "AUTHSTATUS_TRUSTED_DEVICE_COOKIE_NAME",
    ],
)
def test_production_rejects_empty_cookie_names(setting_name):
    with pytest.raises(
        ValidationError,
        match="Production cookie names cannot be empty",
    ):
        valid_production_settings(
            **{
                setting_name: "   ",
            },
        )


@pytest.mark.parametrize(
    "overrides",
    [
        {
            "AUTHSTATUS_SESSION_COOKIE_NAME": "carequeue_cookie",
            "AUTHSTATUS_CSRF_COOKIE_NAME": "carequeue_cookie",
        },
        {
            "AUTHSTATUS_SESSION_COOKIE_NAME": "carequeue_cookie",
            "AUTHSTATUS_TRUSTED_DEVICE_COOKIE_NAME": "carequeue_cookie",
        },
        {
            "AUTHSTATUS_CSRF_COOKIE_NAME": "carequeue_cookie",
            "AUTHSTATUS_TRUSTED_DEVICE_COOKIE_NAME": "carequeue_cookie",
        },
    ],
)
def test_production_rejects_duplicate_cookie_names(overrides):
    with pytest.raises(
        ValidationError,
        match="cookie names must be different",
    ):
        valid_production_settings(**overrides)


@pytest.mark.parametrize(
    "setting_name",
    [
        "AUTHSTATUS_SESSION_COOKIE_NAME",
        "AUTHSTATUS_CSRF_COOKIE_NAME",
        "AUTHSTATUS_TRUSTED_DEVICE_COOKIE_NAME",
    ],
)
@pytest.mark.parametrize(
    "cookie_name",
    [
        "carequeue cookie",
        "carequeue;cookie",
        "carequeue,cookie",
        "carequeue/cookie",
        "carequeue(cookie)",
    ],
)
def test_production_rejects_invalid_cookie_names(
    setting_name,
    cookie_name,
):
    with pytest.raises(
        ValidationError,
        match="valid HTTP cookie token characters",
    ):
        valid_production_settings(
            **{
                setting_name: cookie_name,
            },
        )


def test_production_rejects_empty_csrf_header_name():
    with pytest.raises(
        ValidationError,
        match="CSRF header name cannot be empty",
    ):
        valid_production_settings(
            AUTHSTATUS_CSRF_HEADER_NAME="   ",
        )


@pytest.mark.parametrize(
    "header_name",
    [
        "X CSRF Token",
        "X-CSRF-Token:",
        "X-CSRF-Token\r\nInjected",
    ],
)
def test_production_rejects_invalid_csrf_header_name(
    header_name,
):
    with pytest.raises(
        ValidationError,
        match="CSRF header name must use valid HTTP header token",
    ):
        valid_production_settings(
            AUTHSTATUS_CSRF_HEADER_NAME=header_name,
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


def test_production_rejects_database_path_outside_data_root():
    with pytest.raises(
        ValidationError,
        match="database paths must resolve under AUTHSTATUS_PRODUCTION_DATA_ROOT",
    ):
        valid_production_settings(
            AUTHSTATUS_DATABASE_PATH=Path("production/auth_tracker.sqlcipher.db"),
        )


def test_production_rejects_unsafe_database_path_override():
    with pytest.raises(
        ValidationError,
        match="Production cannot enable AUTHSTATUS_ALLOW_UNSAFE_DATABASE_PATH",
    ):
        valid_production_settings(
            AUTHSTATUS_ALLOW_UNSAFE_DATABASE_PATH=True,
        )


def test_production_rejects_backup_directory_outside_data_root():
    with pytest.raises(
        ValidationError,
        match="backup directories must resolve under AUTHSTATUS_PRODUCTION_DATA_ROOT",
    ):
        valid_production_settings(
            AUTHSTATUS_BACKUP_DIRECTORY=Path("production/backups"),
        )


def test_production_rejects_restore_directory_outside_data_root():
    with pytest.raises(
        ValidationError,
        match="restore directories must resolve under AUTHSTATUS_PRODUCTION_DATA_ROOT",
    ):
        valid_production_settings(
            AUTHSTATUS_RESTORE_DIRECTORY=Path("production/restores"),
        )


def test_production_accepts_paths_under_custom_data_root():
    settings = valid_production_settings(
        AUTHSTATUS_PRODUCTION_DATA_ROOT=Path("production/carequeue"),
        AUTHSTATUS_DATABASE_PATH=Path(
            "production/carequeue/data/auth_tracker.sqlcipher.db"
        ),
        AUTHSTATUS_BACKUP_DIRECTORY=Path("production/carequeue/backups"),
        AUTHSTATUS_RESTORE_DIRECTORY=Path("production/carequeue/restores"),
    )

    assert settings.production_data_root == Path("production/carequeue")


def test_production_custom_data_root_rejects_path_escape():
    with pytest.raises(
        ValidationError,
        match="database paths must resolve under AUTHSTATUS_PRODUCTION_DATA_ROOT",
    ):
        valid_production_settings(
            AUTHSTATUS_PRODUCTION_DATA_ROOT=Path("production/carequeue"),
            AUTHSTATUS_DATABASE_PATH=Path(
                "production/outside/auth_tracker.sqlcipher.db"
            ),
            AUTHSTATUS_BACKUP_DIRECTORY=Path("production/carequeue/backups"),
            AUTHSTATUS_RESTORE_DIRECTORY=Path("production/carequeue/restores"),
        )


def test_production_rejects_unsafe_storage_path_override():
    with pytest.raises(
        ValidationError,
        match="Production cannot enable AUTHSTATUS_ALLOW_UNSAFE_STORAGE_PATHS",
    ):
        valid_production_settings(
            AUTHSTATUS_ALLOW_UNSAFE_STORAGE_PATHS=True,
        )


def test_production_rejects_debug_mode():
    with pytest.raises(
        ValidationError,
        match="Production cannot enable AUTHSTATUS_APP_DEBUG",
    ):
        valid_production_settings(
            AUTHSTATUS_APP_DEBUG=True,
        )


def test_development_allows_debug_mode():
    settings = Settings(
        _env_file=None,
        AUTHSTATUS_APP_ENVIRONMENT="development",
        AUTHSTATUS_APP_DEBUG=True,
    )

    assert settings.app_debug is True

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Annotated
from urllib.parse import urlsplit

from cryptography.fernet import Fernet
from pydantic import Field, field_validator, model_validator
from pydantic_settings import (
    BaseSettings,
    NoDecode,
    SettingsConfigDict,
)

PACKAGE_ROOT = Path(__file__).resolve().parents[0]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ROOT_ENV_FILE = PROJECT_ROOT / ".env"
EXPECTED_DATABASE_DIRECTORY = (PROJECT_ROOT / "backend" / "data").resolve()
EXPECTED_BACKUP_DIRECTORY = (PROJECT_ROOT / "backend" / "backups").resolve()
EXPECTED_RESTORE_DIRECTORY = (PROJECT_ROOT / "backend" / "restores").resolve()
_HTTP_TOKEN_PATTERN = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")

MINIMUM_SQLCIPHER_KEY_LENGTH = 32

PRODUCTION_SECRET_PLACEHOLDERS = {
    "change-me",
    "changeme",
    "example",
    "password",
    "replace-me",
    "replace-this",
    "secret",
    "test",
    "your-key-here",
}


def resolve_project_path(path: Path) -> Path:
    if path.is_absolute():
        return path.resolve()

    return (PROJECT_ROOT / path).resolve()


def path_is_relative_to(
    path: Path,
    parent: Path,
) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False

    return True


def is_placeholder_secret(value: str) -> bool:
    normalized_value = value.strip().lower().replace("_", "-")

    if normalized_value in PRODUCTION_SECRET_PLACEHOLDERS:
        return True

    words = {part for part in normalized_value.split("-") if part}

    placeholder_words = {
        "change",
        "example",
        "here",
        "key",
        "me",
        "password",
        "replace",
        "secret",
        "test",
        "this",
        "value",
        "your",
    }

    return bool(words) and words.issubset(placeholder_words)


class Settings(BaseSettings):
    app_name: str = "AuthStatus API"
    app_version: str = "0.2.0"
    app_environment: str = Field(
        default="development",
        validation_alias="AUTHSTATUS_APP_ENVIRONMENT",
    )
    app_debug: bool = Field(
        default=False,
        validation_alias="AUTHSTATUS_APP_DEBUG",
    )
    database_path: Path = Field(
        default=Path("backend/data/auth_tracker.db"),
        validation_alias="AUTHSTATUS_DATABASE_PATH",
    )
    database_encryption: str = Field(
        default="plaintext",
        validation_alias="AUTHSTATUS_DATABASE_ENCRYPTION",
    )
    production_data_root: Path = Field(
        default=Path("backend"),
        validation_alias="AUTHSTATUS_PRODUCTION_DATA_ROOT",
    )
    allow_unsafe_database_path: bool = Field(
        default=False,
        validation_alias="AUTHSTATUS_ALLOW_UNSAFE_DATABASE_PATH",
    )
    allow_unsafe_storage_paths: bool = Field(
        default=False,
        validation_alias="AUTHSTATUS_ALLOW_UNSAFE_STORAGE_PATHS",
    )
    encryption_key: str = Field(
        default="", validation_alias="AUTHSTATUS_ENCRYPTION_KEY"
    )
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        validation_alias="AUTHSTATUS_CORS_ORIGINS",
    )
    session_cookie_name: str = Field(
        default="carequeue_session",
        validation_alias="AUTHSTATUS_SESSION_COOKIE_NAME",
    )
    session_cookie_secure: bool = Field(
        default=False,
        validation_alias="AUTHSTATUS_SESSION_COOKIE_SECURE",
    )
    session_inactivity_minutes: int = Field(
        default=20,
        ge=5,
        le=480,
        validation_alias="AUTHSTATUS_SESSION_INACTIVITY_MINUTES",
    )
    csrf_cookie_name: str = Field(
        default="carequeue_csrf",
        validation_alias="AUTHSTATUS_CSRF_COOKIE_NAME",
    )
    trusted_device_cookie_name: str = Field(
        default="carequeue_trusted_device",
        validation_alias="AUTHSTATUS_TRUSTED_DEVICE_COOKIE_NAME",
    )
    csrf_header_name: str = Field(
        default="X-CSRF-Token",
        validation_alias="AUTHSTATUS_CSRF_HEADER_NAME",
    )
    sqlcipher_key: str = Field(
        default="",
        validation_alias="AUTHSTATUS_SQLCIPHER_KEY",
    )

    backup_encryption_key: str = Field(
        default="",
        validation_alias="AUTHSTATUS_BACKUP_ENCRYPTION_KEY",
    )
    backup_directory: Path = Field(
        default=Path("backend/backups"),
        validation_alias="AUTHSTATUS_BACKUP_DIRECTORY",
    )

    backup_retention_days: int = Field(
        default=90,
        ge=1,
        validation_alias="AUTHSTATUS_BACKUP_RETENTION_DAYS",
    )
    backup_minimum_count: int = Field(
        default=5,
        ge=1,
        validation_alias="AUTHSTATUS_BACKUP_MINIMUM_COUNT",
    )

    restore_directory: Path = Field(
        default=Path("backend/restores"),
        validation_alias="AUTHSTATUS_RESTORE_DIRECTORY",
    )

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("app_environment")
    @classmethod
    def validate_app_environment(cls, value: str) -> str:
        normalized_value = value.strip().lower()

        if normalized_value not in {
            "development",
            "test",
            "production",
        }:
            raise ValueError(
                "app_environment must be development, test, or production."
            )

        return normalized_value

    @field_validator("database_encryption")
    @classmethod
    def validate_database_encryption(cls, value: str) -> str:
        normalized_value = value.strip().lower()

        if normalized_value not in {"plaintext", "sqlcipher"}:
            raise ValueError("database_encryption must be plaintext or sqlcipher.")

        return normalized_value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_and_validate_cors_origins(
        cls,
        value: str | list[str],
    ) -> list[str]:
        if isinstance(value, str):
            stripped_value = value.strip()

            if stripped_value.startswith("["):
                try:
                    parsed_value = json.loads(stripped_value)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        "CORS origins must be a valid JSON list or "
                        "comma-separated origins."
                    ) from exc

                if not isinstance(parsed_value, list) or not all(
                    isinstance(origin, str) for origin in parsed_value
                ):
                    raise ValueError(
                        "CORS origins JSON value must be a list of strings."
                    )

                values = parsed_value
            else:
                values = [
                    origin.strip()
                    for origin in stripped_value.split(",")
                    if origin.strip()
                ]
        else:
            values = value

        normalized_origins: list[str] = []
        seen_origins: set[str] = set()

        for raw_origin in values:
            origin = raw_origin.strip()
            parsed_origin = urlsplit(origin)

            if parsed_origin.scheme.lower() not in {
                "http",
                "https",
            }:
                raise ValueError("CORS origins must use HTTP or HTTPS.")

            if not parsed_origin.netloc:
                raise ValueError("CORS origins must include a hostname.")

            if parsed_origin.username is not None or parsed_origin.password is not None:
                raise ValueError("CORS origins cannot contain credentials.")

            if parsed_origin.path not in {"", "/"}:
                raise ValueError("CORS origins cannot contain a path.")

            if parsed_origin.query:
                raise ValueError("CORS origins cannot contain a query string.")

            if parsed_origin.fragment:
                raise ValueError("CORS origins cannot contain a fragment.")

            normalized_origin = (
                f"{parsed_origin.scheme.lower()}://" f"{parsed_origin.netloc.lower()}"
            )

            if normalized_origin in seen_origins:
                raise ValueError("CORS origins cannot contain duplicates.")

            seen_origins.add(normalized_origin)
            normalized_origins.append(normalized_origin)

        return normalized_origins

    @model_validator(mode="after")
    def validate_production_security(self) -> Settings:
        if self.app_environment != "production":
            return self

        if self.app_debug:
            raise ValueError("Production cannot enable AUTHSTATUS_APP_DEBUG.")

        if self.allow_unsafe_database_path:
            raise ValueError(
                "Production cannot enable AUTHSTATUS_ALLOW_UNSAFE_DATABASE_PATH."
            )

        if self.allow_unsafe_storage_paths:
            raise ValueError(
                "Production cannot enable AUTHSTATUS_ALLOW_UNSAFE_STORAGE_PATHS."
            )

        production_data_root = resolve_project_path(self.production_data_root)

        if production_data_root == production_data_root.parent:
            raise ValueError("Production data root cannot be a filesystem root.")

        database_path = resolve_project_path(self.database_path)
        backup_directory = resolve_project_path(self.backup_directory)
        restore_directory = resolve_project_path(self.restore_directory)

        if not path_is_relative_to(
            database_path,
            production_data_root,
        ):
            raise ValueError(
                "Production database paths must resolve under "
                "AUTHSTATUS_PRODUCTION_DATA_ROOT."
            )

        if not path_is_relative_to(
            backup_directory,
            production_data_root,
        ):
            raise ValueError(
                "Production backup directories must resolve under "
                "AUTHSTATUS_PRODUCTION_DATA_ROOT."
            )

        if not path_is_relative_to(
            restore_directory,
            production_data_root,
        ):
            raise ValueError(
                "Production restore directories must resolve under "
                "AUTHSTATUS_PRODUCTION_DATA_ROOT."
            )

        if backup_directory == restore_directory:
            raise ValueError(
                "Production backup and restore directories must be different."
            )

        if path_is_relative_to(
            backup_directory, restore_directory
        ) or path_is_relative_to(restore_directory, backup_directory):
            raise ValueError(
                "Production backup and restore directories cannot overlap."
            )

        if path_is_relative_to(database_path, backup_directory) or path_is_relative_to(
            database_path, restore_directory
        ):
            raise ValueError(
                "Production database files cannot be stored inside "
                "backup or restore directories."
            )

        if self.database_encryption != "sqlcipher":
            raise ValueError("Production requires SQLCipher database encryption.")

        sqlcipher_key = self.sqlcipher_key.strip()

        if not sqlcipher_key:
            raise ValueError("Production requires AUTHSTATUS_SQLCIPHER_KEY.")

        if len(sqlcipher_key) < MINIMUM_SQLCIPHER_KEY_LENGTH:
            raise ValueError(
                "Production AUTHSTATUS_SQLCIPHER_KEY must be at least "
                f"{MINIMUM_SQLCIPHER_KEY_LENGTH} characters."
            )

        if is_placeholder_secret(sqlcipher_key):
            raise ValueError(
                "Production AUTHSTATUS_SQLCIPHER_KEY cannot use a " "placeholder value."
            )

        encryption_key = self.encryption_key.strip()

        if not encryption_key:
            raise ValueError("Production requires AUTHSTATUS_ENCRYPTION_KEY.")

        try:
            Fernet(encryption_key.encode("utf-8"))
        except ValueError as exc:
            raise ValueError(
                "Production requires a valid AUTHSTATUS_ENCRYPTION_KEY."
            ) from exc

        backup_encryption_key = self.backup_encryption_key.strip()

        if not backup_encryption_key:
            raise ValueError("Production requires AUTHSTATUS_BACKUP_ENCRYPTION_KEY.")

        try:
            Fernet(backup_encryption_key.encode("utf-8"))
        except ValueError as exc:
            raise ValueError(
                "Production requires a valid " "AUTHSTATUS_BACKUP_ENCRYPTION_KEY."
            ) from exc

        if encryption_key == backup_encryption_key:
            raise ValueError(
                "Production field and backup encryption keys must be different."
            )

        if not self.session_cookie_secure:
            raise ValueError("Production requires secure session cookies.")

        cookie_names = {
            self.session_cookie_name.strip(),
            self.csrf_cookie_name.strip(),
            self.trusted_device_cookie_name.strip(),
        }

        if any(not cookie_name for cookie_name in cookie_names):
            raise ValueError("Production cookie names cannot be empty.")

        if len(cookie_names) != 3:
            raise ValueError(
                "Production session, CSRF, and trusted-device cookie names "
                "must be different."
            )

        for cookie_name in cookie_names:
            if not _HTTP_TOKEN_PATTERN.fullmatch(cookie_name):
                raise ValueError(
                    "Production cookie names must use valid HTTP cookie token characters."
                )

        csrf_header_name = self.csrf_header_name.strip()

        if not csrf_header_name:
            raise ValueError("Production CSRF header name cannot be empty.")

        if not _HTTP_TOKEN_PATTERN.fullmatch(csrf_header_name):
            raise ValueError(
                "Production CSRF header name must use valid HTTP "
                "header token characters."
            )

        if not self.cors_origins:
            raise ValueError("Production requires at least one trusted CORS origin.")

        for origin in self.cors_origins:
            normalized_origin = origin.strip().lower()

            if normalized_origin == "*":
                raise ValueError("Production CORS origins cannot contain a wildcard.")

            if not normalized_origin.startswith("https://"):
                raise ValueError("Production CORS origins must use HTTPS.")

            hostname = urlsplit(normalized_origin).hostname

            if hostname in {
                "localhost",
                "127.0.0.1",
                "::1",
            }:
                raise ValueError(
                    "Production CORS origins cannot use local development hosts."
                )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings(_env_file=ROOT_ENV_FILE)

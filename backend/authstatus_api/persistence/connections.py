from __future__ import annotations

from typing import Any

from authstatus_api.database_encryption.sqlcipher_probe import (
    SQLCipherProbeError,
    apply_sqlcipher_key,
    import_sqlcipher,
)
from authstatus_api.persistence.paths import get_database_path
from authstatus_api.settings import get_settings


class DatabaseEncryptionError(RuntimeError):
    pass


def _get_sqlcipher_conn(database_path, passphrase: str):
    try:
        sqlcipher = import_sqlcipher()
        conn = sqlcipher.connect(database_path)
        conn.row_factory = sqlcipher.Row
        apply_sqlcipher_key(conn, passphrase)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("SELECT count(*) FROM sqlite_master").fetchone()
    except SQLCipherProbeError as exc:
        raise DatabaseEncryptionError(str(exc)) from exc
    except Exception as exc:
        raise DatabaseEncryptionError("Unable to open the encrypted database.") from exc

    return conn


def get_conn() -> Any:
    settings = get_settings()
    database_path = get_database_path()

    database_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    passphrase = settings.sqlcipher_key.strip()

    if not passphrase:
        raise DatabaseEncryptionError("Missing AUTHSTATUS_DATABASE_PASSPHRASE.")

    return _get_sqlcipher_conn(
        database_path,
        passphrase,
    )

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parents[1]
load_dotenv(PROJECT_ROOT / ".env")

sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault(
    "AUTHSTATUS_DATABASE_PATH",
    str(PROJECT_ROOT / "backend" / "data" / "auth_tracker.db"),
)

from authstatus_api.database_encryption.sqlcipher_probe import (  # noqa: E402
    SQLCipherProbeError,
    migrate_plaintext_sqlite_to_sqlcipher,
)
from authstatus_api.persistence.paths import get_database_path  # noqa: E402
from authstatus_api.settings import get_settings  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a SQLCipher encrypted copy of the CareQFlow SQLite database."
    )
    parser.add_argument(
        "--source-path",
        type=Path,
        default=None,
        help="Optional plaintext source database. Defaults to AUTHSTATUS_DATABASE_PATH.",
    )
    parser.add_argument(
        "--destination-path",
        type=Path,
        default=None,
        help="Optional encrypted output path. Defaults to backend/data/auth_tracker.sqlcipher.db.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = get_settings()
    sqlcipher_key = settings.sqlcipher_key.strip()

    if not sqlcipher_key:
        print("Missing AUTHSTATUS_SQLCIPHER_KEY.", file=sys.stderr)
        return 1

    source_path = args.source_path or get_database_path()
    destination_path = args.destination_path or (
        source_path.with_name(f"{source_path.stem}.sqlcipher{source_path.suffix}")
    )

    try:
        migrated_path = migrate_plaintext_sqlite_to_sqlcipher(
            source_path=source_path,
            destination_path=destination_path,
            passphrase=sqlcipher_key,
        )
    except SQLCipherProbeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Created SQLCipher encrypted database copy: {migrated_path}")
    print("This did not replace the active plaintext database.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

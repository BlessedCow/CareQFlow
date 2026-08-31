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
    verify_sqlcipher_database,
)
from authstatus_api.persistence.paths import get_database_path  # noqa: E402
from authstatus_api.settings import get_settings  # noqa: E402

CAREQUEUE_REQUIRED_TABLES = {
    "auth_events",
    "auths",
    "audit_events",
    "sessions",
    "users",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify a SQLCipher encrypted CareQFlow database copy."
    )
    parser.add_argument(
        "--database-path",
        type=Path,
        default=None,
        help=(
            "Optional SQLCipher database path. Defaults to "
            "backend/data/auth_tracker.sqlcipher.db."
        ),
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = get_settings()
    sqlcipher_key = settings.sqlcipher_key.strip()

    if not sqlcipher_key:
        print("Missing AUTHSTATUS_SQLCIPHER_KEY.", file=sys.stderr)
        return 1

    plaintext_path = get_database_path()
    encrypted_path = args.database_path or plaintext_path.with_name(
        f"{plaintext_path.stem}.sqlcipher{plaintext_path.suffix}"
    )

    try:
        result = verify_sqlcipher_database(
            database_path=encrypted_path,
            passphrase=sqlcipher_key,
            required_tables=CAREQUEUE_REQUIRED_TABLES,
        )
    except SQLCipherProbeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Verified SQLCipher database: {result['database_path']}")
    print("Required tables found:")
    for table_name in result["required_tables"]:
        print(f"- {table_name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

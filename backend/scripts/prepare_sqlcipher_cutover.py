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
os.environ.setdefault(
    "AUTHSTATUS_BACKUP_DIRECTORY", str(PROJECT_ROOT / "backend" / "backups")
)

from authstatus_api.database_encryption.cutover import (  # noqa: E402
    SQLCipherCutoverError,
    prepare_sqlcipher_cutover,
)
from authstatus_api.settings import get_settings  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare a safe SQLCipher cutover for CareQFlow."
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
        help="Optional SQLCipher output path. Defaults to auth_tracker.sqlcipher.db.",
    )
    parser.add_argument(
        "--backup-directory",
        type=Path,
        default=None,
        help="Optional encrypted backup output directory.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recreate the SQLCipher output file if it already exists.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = get_settings()

    source_path = args.source_path or (
        PROJECT_ROOT / "backend" / "data" / "auth_tracker.db"
    )

    try:
        result = prepare_sqlcipher_cutover(
            source_path=source_path,
            destination_path=args.destination_path,
            sqlcipher_key=settings.sqlcipher_key,
            backend_root=PROJECT_ROOT,
            backup_directory=args.backup_directory,
            force=args.force,
        )
    except SQLCipherCutoverError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print("SQLCipher cutover preparation complete.")
    print()
    print(f"Encrypted backup created: {result['backup_path']}")
    print(f"SQLCipher database created: {result['sqlcipher_path']}")
    print()
    print("Required tables verified:")
    for table_name in result["verification"]["required_tables"]:
        print(f"- {table_name}")

    print()
    print("To switch the backend to SQLCipher mode, update the repository-root .env:")
    print(
        f"AUTHSTATUS_DATABASE_PATH={result['env_values']['AUTHSTATUS_DATABASE_PATH']}"
    )
    print(
        "AUTHSTATUS_DATABASE_ENCRYPTION="
        f"{result['env_values']['AUTHSTATUS_DATABASE_ENCRYPTION']}"
    )
    print("AUTHSTATUS_SQLCIPHER_KEY=<keep your existing local SQLCipher key>")
    print()
    print("Do not delete the plaintext database yet.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

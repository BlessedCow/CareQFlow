from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
load_dotenv(PROJECT_ROOT / ".env")

sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault(
    "AUTHSTATUS_DATABASE_PATH",
    str(PROJECT_ROOT / "backend" / "data" / "auth_tracker.db"),
)
os.environ.setdefault(
    "AUTHSTATUS_BACKUP_DIRECTORY", str(PROJECT_ROOT / "backend" / "backups")
)

from authstatus_api.backups.service import (  # noqa: E402
    BackupConfigError,
    BackupError,
    create_encrypted_database_backup,
    verify_encrypted_database_backup,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create an encrypted CareQueue database backup."
    )
    parser.add_argument(
        "--database-path",
        type=Path,
        default=None,
        help="Optional database path. Defaults to AUTHSTATUS_DATABASE_PATH.",
    )
    parser.add_argument(
        "--backup-directory",
        type=Path,
        default=None,
        help="Optional backup output directory. Defaults to AUTHSTATUS_BACKUP_DIRECTORY.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        backup_path = create_encrypted_database_backup(
            database_path=args.database_path,
            backup_directory=args.backup_directory,
        )
        verify_encrypted_database_backup(
            backup_path=backup_path,
        )
    except (BackupConfigError, BackupError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Created and verified encrypted backup: {backup_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

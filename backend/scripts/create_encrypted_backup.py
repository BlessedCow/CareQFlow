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

from authstatus_api.backups.retention import (  # noqa: E402
    BackupRetentionError,
    prune_encrypted_database_backups,
)
from authstatus_api.backups.service import (  # noqa: E402
    BackupConfigError,
    BackupError,
    create_encrypted_database_backup,
    verify_encrypted_database_backup,
)
from authstatus_api.settings import get_settings  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create an encrypted CareQFlow database backup."
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
    settings = get_settings()

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

    try:
        prune_result = prune_encrypted_database_backups(
            retention_days=settings.backup_retention_days,
            minimum_count=settings.backup_minimum_count,
            backup_directory=args.backup_directory,
        )
    except BackupRetentionError as exc:
        print(
            f"Backup retention cleanup failed: {exc}",
            file=sys.stderr,
        )
        return 2

    if prune_result["deleted"]:
        print("Pruned encrypted backups: " + ", ".join(prune_result["deleted"]))
    else:
        print("No encrypted backups were eligible for pruning.")

    if prune_result["protected"]:
        print("Protected by pending recovery: " + ", ".join(prune_result["protected"]))

    if prune_result["failed"]:
        for failure in prune_result["failed"]:
            print(
                "Unable to prune " f"{failure['filename']}: {failure['reason']}",
                file=sys.stderr,
            )

        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

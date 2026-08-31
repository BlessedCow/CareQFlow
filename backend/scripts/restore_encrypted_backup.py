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
    "AUTHSTATUS_RESTORE_DIRECTORY", str(PROJECT_ROOT / "backend" / "restores")
)

from authstatus_api.backups.service import (  # noqa: E402
    BackupConfigError,
    BackupError,
    restore_encrypted_database_backup,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Restore an encrypted CareQFlow database backup to a safe restore file."
    )
    parser.add_argument(
        "backup_path",
        type=Path,
        help="Path to the encrypted .db.enc backup file.",
    )
    parser.add_argument(
        "--restore-directory",
        type=Path,
        default=None,
        help="Optional restore output directory. Defaults to AUTHSTATUS_RESTORE_DIRECTORY.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        restored_path = restore_encrypted_database_backup(
            backup_path=args.backup_path,
            restore_directory=args.restore_directory,
        )
    except (BackupConfigError, BackupError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Restored backup to: {restored_path}")
    print("This did not overwrite the active database.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

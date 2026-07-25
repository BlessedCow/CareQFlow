from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent

sys.path.insert(0, str(BACKEND_ROOT))

from authstatus_api.authorizations.encryption import (  # noqa: E402
    back_up_and_encrypt_plaintext_authorization_fields,
)
from authstatus_api.backups.service import (  # noqa: E402
    BackupConfigError,
    BackupError,
)


def configure_environment() -> None:
    load_dotenv(PROJECT_ROOT / ".env")

    os.environ.setdefault(
        "AUTHSTATUS_DATABASE_PATH",
        str(BACKEND_ROOT / "data" / "auth_tracker.db"),
    )
    os.environ.setdefault(
        "AUTHSTATUS_BACKUP_DIRECTORY",
        str(BACKEND_ROOT / "backups"),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create an encrypted CareQueue database backup, then encrypt "
            "legacy plaintext authorization fields."
        )
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm that the configured database should be modified.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.confirm:
        print(
            "Migration not run. Pass --confirm to modify the configured database.",
            file=sys.stderr,
        )
        return 1

    configure_environment()

    try:
        backup_path, updated_rows = back_up_and_encrypt_plaintext_authorization_fields()
    except (BackupConfigError, BackupError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Created encrypted backup: {backup_path}")
    print(f"Encrypted authorization records: {updated_rows}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

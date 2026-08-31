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
    FieldEncryptionRotationAuditError,
    back_up_and_rotate_field_encryption_data,
)
from authstatus_api.backups.service import (  # noqa: E402
    BackupConfigError,
    BackupError,
)
from authstatus_api.crypto import (  # noqa: E402
    DecryptionError,
    EncryptionConfigError,
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
            "Create and verify an encrypted CareQFlow database backup, "
            "then rotate field-encrypted data from the configured previous "
            "encryption key to the current encryption key."
        )
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm that the configured database should be modified.",
    )
    parser.add_argument(
        "--username",
        default=None,
        help=("Optional operator username recorded in the security audit event."),
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.confirm:
        print(
            "Rotation not run. Pass --confirm to modify the configured database.",
            file=sys.stderr,
        )
        return 1

    configure_environment()

    try:
        backup_path, counts = back_up_and_rotate_field_encryption_data(
            username=args.username,
        )
    except FieldEncryptionRotationAuditError as exc:
        print(
            "Field encryption key rotation completed successfully, "
            "but the security audit event could not be recorded.",
            file=sys.stderr,
        )
        print(
            f"Verified pre-rotation backup: {exc.backup_path}",
            file=sys.stderr,
        )
        print(
            "Do not restore the previous field encryption key as the " "current key.",
            file=sys.stderr,
        )
        return 2
    except (
        BackupConfigError,
        BackupError,
        DecryptionError,
        EncryptionConfigError,
        RuntimeError,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Created and verified encrypted backup: {backup_path}")
    print("Rotated authorization fields: " f"{counts['authorization_fields']}")
    print(f"Rotated authorization event notes: {counts['event_notes']}")
    print(f"Rotated MFA secrets: {counts['mfa_secrets']}")
    print(f"Rotated authorization documents: {counts['documents']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

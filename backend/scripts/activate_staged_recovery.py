from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent

sys.path.insert(0, str(BACKEND_ROOT))


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
    os.environ.setdefault(
        "AUTHSTATUS_RESTORE_DIRECTORY",
        str(BACKEND_ROOT / "restores"),
    )


from authstatus_api.backups.recovery_activation import (  # noqa: E402
    RECOVERY_CONFIRMATION_PHRASE,
    RecoveryActivationError,
    activate_staged_database_recovery,
    format_recovery_activation_plan,
    prepare_recovery_activation,
)

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_CANCELED = 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Activate a staged CareQFlow database recovery while "
            "the application service is stopped."
        )
    )
    parser.add_argument(
        "--database-path",
        type=Path,
        default=None,
        help=(
            "Optional active database path. Defaults to " "AUTHSTATUS_DATABASE_PATH."
        ),
    )
    parser.add_argument(
        "--backup-directory",
        type=Path,
        default=None,
        help=(
            "Optional encrypted safety-backup directory. Defaults "
            "to AUTHSTATUS_BACKUP_DIRECTORY."
        ),
    )
    parser.add_argument(
        "--restore-directory",
        type=Path,
        default=None,
        help=(
            "Optional staged-recovery directory. Defaults to "
            "AUTHSTATUS_RESTORE_DIRECTORY."
        ),
    )
    parser.add_argument(
        "--service-name",
        default=None,
        help=(
            "Optional Windows service or systemd unit name. When "
            "provided, activation requires the service to be stopped."
        ),
    )
    parser.add_argument(
        "--api-host",
        default="127.0.0.1",
        help="CareQFlow API host used for the offline socket check.",
    )
    parser.add_argument(
        "--api-port",
        type=int,
        default=8000,
        help="CareQFlow API port that must not be accepting connections.",
    )

    return parser.parse_args()


def read_confirmation() -> str | None:
    print()
    print("Type the following phrase exactly to activate the staged recovery:")
    print()
    print(f"    {RECOVERY_CONFIRMATION_PHRASE}")
    print()

    try:
        return input("Confirmation: ")
    except (EOFError, KeyboardInterrupt):
        print()
        return None


def main() -> int:
    args = parse_args()
    configure_environment()

    try:
        plan = prepare_recovery_activation(
            database_path=args.database_path,
            backup_directory=args.backup_directory,
            restore_directory=args.restore_directory,
            service_name=args.service_name,
            api_host=args.api_host,
            api_port=args.api_port,
        )
    except RecoveryActivationError as exc:
        print(
            f"Recovery preflight failed: {exc}",
            file=sys.stderr,
        )
        return EXIT_FAILURE

    print(format_recovery_activation_plan(plan))

    confirmation = read_confirmation()

    if confirmation is None:
        print(
            "Recovery activation canceled before database cutover.",
            file=sys.stderr,
        )
        return EXIT_CANCELED

    try:
        result = activate_staged_database_recovery(
            plan=plan,
            confirmation=confirmation,
        )
    except RecoveryActivationError as exc:
        if confirmation != RECOVERY_CONFIRMATION_PHRASE:
            print(
                "Recovery activation canceled because the "
                "confirmation phrase did not match exactly.",
                file=sys.stderr,
            )
            return EXIT_CANCELED

        print(
            f"Recovery activation failed: {exc}",
            file=sys.stderr,
        )
        return EXIT_FAILURE

    print()
    print("Database recovery activated successfully.")
    print(f"Active database:   {result['active_database']}")
    print(f"Rollback database: {result['rollback_database']}")
    print(f"Safety backup:     {result['safety_backup']}")
    print()
    print(
        "CareQFlow remains stopped. Start the service only after "
        "reviewing the activation result."
    )

    return EXIT_SUCCESS


if __name__ == "__main__":
    raise SystemExit(main())

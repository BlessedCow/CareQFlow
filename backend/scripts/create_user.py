from __future__ import annotations

import argparse
import getpass
import os
import sqlite3
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

from authstatus_api.security.password_policy import (  # noqa: E402
    PasswordPolicyError,
    validate_password_policy,
)
from authstatus_api.security.users import create_user  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a CareQueue user.")
    parser.add_argument("--username", required=True)
    parser.add_argument(
        "--role",
        choices=["Admin", "UR", "Read Only"],
        default="UR",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    password = getpass.getpass("Password: ")
    confirm_password = getpass.getpass("Confirm password: ")

    if password != confirm_password:
        print("Passwords do not match.", file=sys.stderr)
        return 1

    try:
        validate_password_policy(password)
    except PasswordPolicyError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    try:
        user = create_user(args.username, password, role=args.role)
    except sqlite3.IntegrityError:
        print("A user with that username already exists.", file=sys.stderr)
        return 1

    print(f"Created user {user['username']} with role {user['role']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

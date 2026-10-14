from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from faker import Faker

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent

sys.path.insert(0, str(BACKEND_ROOT))

from authstatus_api.authorizations.decision_snapshots import (  # noqa: E402
    create_auth_decision_snapshot,
)
from authstatus_api.authorizations.loc_episodes import (  # noqa: E402
    create_auth_loc_episode,
)
from authstatus_api.authorizations.records import create_auth  # noqa: E402
from authstatus_api.settings import get_settings  # noqa: E402

EXPECTED_CONTEXT = {
    "loc": "RTC",
    "days_at_current_loc": 20,
    "total_treatment_days": 20,
    "context_derivation_version": 2,
    "context_provenance": "loc_episode",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Seed one synthetic historical LOC decision case and verify that "
            "the snapshot preserves the LOC active at decision time."
        )
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=PROJECT_ROOT / ".env",
        help="Environment file whose database/settings should be used.",
    )
    parser.add_argument(
        "--allow-production",
        action="store_true",
        help=(
            "Explicitly allow seeding when AUTHSTATUS_APP_ENVIRONMENT is not "
            "development. Use only with a database intended for synthetic data."
        ),
    )
    return parser.parse_args()


def load_environment(env_file: Path) -> None:
    if not env_file.is_file():
        raise SystemExit(f"Environment file does not exist: {env_file}")

    for name in tuple(os.environ):
        if name.startswith("AUTHSTATUS_"):
            os.environ.pop(name)

    load_dotenv(env_file, override=True)
    get_settings.cache_clear()


def validate_environment(
    app_environment: str,
    allow_production: bool,
) -> None:
    if app_environment.strip().lower() == "development":
        return

    if not allow_production:
        raise SystemExit(
            "Configured environment is not development. "
            "Re-run with --allow-production only if this database contains "
            "synthetic/test data and you intend to modify it."
        )


def create_manual_loc_context_case() -> tuple[dict[str, Any], dict[str, Any]]:
    fake = Faker()
    fake.seed_instance(20261014)

    auth = create_auth(
        {
            "facility": "Serenoa Healing Center",
            "client_name": f"LOC Snapshot Test - {fake.first_name()} {fake.last_name()}",
            "loc": "PHP",
            "submission_methods": "Fax",
            "auth_type": "Concurrent",
            "status": "In Progress",
            "insurance": "Example Health",
            "insurance_plan": "Gold PPO",
            "requested_days": 5,
            "approved_days": 0,
            "denied_days": 0,
        }
    )

    create_auth_loc_episode(
        auth["id"],
        {
            "loc": "RTC",
            "started_at": "2026-06-01T00:00:00+00:00",
            "ended_at": "2026-06-27T00:00:00+00:00",
        },
    )

    create_auth_loc_episode(
        auth["id"],
        {
            "loc": "PHP",
            "started_at": "2026-06-27T00:00:00+00:00",
        },
    )

    snapshot = create_auth_decision_snapshot(
        auth["id"],
        {
            "outcome": "Denied",
            "decision_at": "2026-06-21T00:00:00+00:00",
            "denial_reason_category": "Medical Necessity",
            "denial_source": "Payer Review",
            "source": "manual",
        },
    )

    if snapshot is None:
        raise RuntimeError("Decision snapshot creation returned no record.")

    return auth, snapshot


def verify_snapshot(snapshot: dict[str, Any]) -> None:
    mismatches = {
        field: {
            "expected": expected,
            "actual": snapshot.get(field),
        }
        for field, expected in EXPECTED_CONTEXT.items()
        if snapshot.get(field) != expected
    }

    if mismatches:
        raise RuntimeError(
            "Historical LOC snapshot verification failed: " f"{mismatches}"
        )


def main() -> None:
    args = parse_args()
    load_environment(args.env_file)

    settings = get_settings()
    validate_environment(
        settings.app_environment,
        args.allow_production,
    )

    print(f"Environment: {settings.app_environment}")
    print(f"Database: {settings.database_path}")
    print(f"Environment file: {args.env_file}")

    auth, snapshot = create_manual_loc_context_case()
    verify_snapshot(snapshot)

    print()
    print("Created historical LOC snapshot smoke-test data.")
    print(f"Authorization ID: {auth['id']}")
    print(f"Client: {auth['client_name']}")
    print(f"Current authorization LOC: {auth['loc']}")
    print(f"Snapshot ID: {snapshot['id']}")
    print(f"Snapshot decision_at: {snapshot['decision_at']}")
    print(f"Snapshot LOC: {snapshot['loc']}")
    print(f"Days at snapshot LOC: {snapshot['days_at_current_loc']}")
    print(f"Total treatment days: {snapshot['total_treatment_days']}")
    print(f"Context provenance: {snapshot['context_provenance']}")
    print("Context derivation version: " f"{snapshot['context_derivation_version']}")
    print()
    print(
        "PASS: June 21 decision correctly retained RTC context "
        "while the authorization LOC is PHP."
    )


if __name__ == "__main__":
    main()

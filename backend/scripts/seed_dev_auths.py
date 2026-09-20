from __future__ import annotations

import argparse
import os
import random
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from faker import Faker

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
INSTALLED_ENV_PATH = Path(r"C:\ProgramData\CareQueue\Config\carequeue.env")
load_dotenv(PROJECT_ROOT / ".env")
sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault(
    "AUTHSTATUS_DATABASE_PATH",
    str(PROJECT_ROOT / "backend" / "data" / "auth_tracker.db"),
)

from authstatus_api.authorizations.records import create_auth, update_auth  # noqa: E402
from authstatus_api.settings import get_settings  # noqa: E402


def load_installed_environment() -> None:
    if not INSTALLED_ENV_PATH.is_file():
        raise SystemExit(
            f"Installed CareQFlow environment file not found: " f"{INSTALLED_ENV_PATH}"
        )

    for key in tuple(os.environ):
        if key.startswith("AUTHSTATUS_"):
            os.environ.pop(key)

    load_dotenv(
        INSTALLED_ENV_PATH,
        override=True,
    )

    get_settings.cache_clear()


SEED_START_DATE = date(2026, 8, 1)
SEED_END_DATE = date(2026, 9, 19)

FACILITY_LOCS = {
    "Aura Horizon Recovery Center": ("DTX", "RTC"),
    "Clearpath Recovery Institute": ("DTX", "RTC"),
    "Pinecrest Behavioral Health": ("PHP", "IOP"),
    "Serenoa Healing Center": ("DTX", "RTC", "PHP", "IOP"),
    "Verdant Oaks Wellness Hub": ("PHP", "IOP"),
}

INSURERS = (
    "Aetna Behavioral Health",
    "Anthem Blue Cross of CA",
    "Blue Shield of CA",
    "Carefirst Blue Cross Blue Shield",
    "Carelon Behavioral Health",
    "Empire Blue Cross Blue Shield",
    "Evernorth Health Services",
    "Highmark Blue Cross Blue Shield",
    "Horizon Blue Cross Blue Shield of NJ",
    "Humana Behavioral Health",
    "Independence Blue Cross",
    "Kaiser Permanente",
    "Magellan Health",
    "Molina Healthcare",
    "Optum Behavioral Health",
)

WEB_PORTALS = (
    "Availity",
    "Carelon Provider Portal",
    "ConnectiCare",
    "Lucet",
)

SUBMISSION_METHODS = (
    "Fax",
    "Live Call",
    "Voicemail",
    "Web Portal",
)

DENIAL_REASONS = (
    "Medical Necessity",
    "Level of Care",
    "Documentation",
    "Benefit Limitation",
)

DENIAL_SOURCES = (
    "Payer Review",
    "Medical Director",
    "Administrative Review",
)

PROGRAMMING_DAYS = {
    ("Pinecrest Behavioral Health", "PHP"): "Wed-Fri, 6 hours/day",
    ("Pinecrest Behavioral Health", "IOP"): "Mon/Wed/Fri, 3 hours/day",
    ("Verdant Oaks Wellness Hub", "PHP"): "Mon-Sat, 6 hours/day",
    ("Verdant Oaks Wellness Hub", "IOP"): "Mon/Wed/Fri, 3 hours/day",
    ("Serenoa Healing Center", "PHP"): "Mon-Fri, 6 hours/day",
    ("Serenoa Healing Center", "IOP"): "Mon/Wed/Fri, 3 hours/day",
}

PROGRAMMING_WEEKDAYS = {
    ("Pinecrest Behavioral Health", "PHP"): {2, 3, 4},
    ("Pinecrest Behavioral Health", "IOP"): {0, 2, 4},
    ("Verdant Oaks Wellness Hub", "PHP"): {0, 1, 2, 3, 4, 5},
    ("Verdant Oaks Wellness Hub", "IOP"): {0, 2, 4},
    ("Serenoa Healing Center", "PHP"): {0, 1, 2, 3, 4},
    ("Serenoa Healing Center", "IOP"): {0, 2, 4},
}

LOC_START_WEIGHTS = {
    "DTX": 32,
    "RTC": 28,
    "PHP": 24,
    "IOP": 16,
}


def _iso_datetime(day: date, hour: int) -> str:
    return datetime.combine(day, time(hour=hour)).isoformat(timespec="seconds")


def _programming_weekdays(
    facility: str,
    loc: str,
) -> set[int]:
    if loc in {"DTX", "RTC"}:
        return set(range(7))

    return PROGRAMMING_WEEKDAYS[(facility, loc)]


def _count_programming_days(
    start_day: date,
    calendar_days: int,
    facility: str,
    loc: str,
) -> int:
    weekdays = _programming_weekdays(
        facility,
        loc,
    )

    return sum(
        1
        for offset in range(calendar_days)
        if (start_day + timedelta(days=offset)).weekday() in weekdays
    )


def _end_date_for_programming_days(
    start_day: date,
    programming_days: int,
    facility: str,
    loc: str,
) -> date:
    if programming_days <= 0:
        return start_day

    weekdays = _programming_weekdays(
        facility,
        loc,
    )

    current_day = start_day
    completed_days = 0

    while True:
        if current_day.weekday() in weekdays:
            completed_days += 1

            if completed_days >= programming_days:
                return current_day

        current_day += timedelta(days=1)


def _weighted_choice(rng: random.Random, weights: dict[str, int]) -> str:
    values = list(weights)
    return rng.choices(
        values,
        weights=[weights[value] for value in values],
        k=1,
    )[0]


def _facilities_for_loc(loc: str) -> list[str]:
    return [
        facility
        for facility, supported_locs in FACILITY_LOCS.items()
        if loc in supported_locs
    ]


def _choose_facility(
    rng: random.Random,
    loc: str,
    previous_facility: str | None = None,
) -> str:
    candidates = _facilities_for_loc(loc)

    if previous_facility in candidates and rng.random() < 0.70:
        return previous_facility

    return rng.choice(candidates)


def _build_loc_path(rng: random.Random) -> list[str]:
    start_loc = _weighted_choice(rng, LOC_START_WEIGHTS)

    if start_loc == "DTX":
        if rng.random() < 0.82:
            return ["DTX", "RTC", "PHP", "IOP"]
        return ["DTX", "PHP", "IOP"]

    if start_loc == "RTC":
        return ["RTC", "PHP", "IOP"]

    if start_loc == "PHP":
        return ["PHP", "IOP"]

    return ["IOP"]


def _episode_calendar_durations(
    rng: random.Random,
    loc_path: list[str],
    insurance: str,
) -> dict[str, int]:
    durations: dict[str, int] = {}

    if "DTX" in loc_path:
        durations["DTX"] = rng.randint(7, 14)

    if "RTC" in loc_path:
        if "DTX" in durations:
            minimum_total = max(28, durations["DTX"] + 14)
            maximum_total = min(42, durations["DTX"] + 28)
            combined_days = rng.randint(minimum_total, maximum_total)
            durations["RTC"] = combined_days - durations["DTX"]
        else:
            durations["RTC"] = rng.randint(14, 28)

    if "PHP" in loc_path:
        if insurance == "Evernorth Health Services":
            durations["PHP"] = rng.randint(42, 70)
        else:
            durations["PHP"] = rng.randint(28, 56)

    if "IOP" in loc_path:
        if insurance == "Evernorth Health Services":
            durations["IOP"] = rng.randint(70, 112)
        else:
            durations["IOP"] = rng.randint(56, 84)

    return durations


def _review_chunk_days(
    rng: random.Random,
    insurance: str,
    loc: str,
    remaining_days: int,
) -> int:
    if loc == "DTX":
        minimum, maximum = 3, 5

        if insurance in {"Kaiser Permanente", "Molina Healthcare"}:
            minimum, maximum = 2, 4
    elif loc == "RTC":
        minimum, maximum = 5, 7

        if insurance == "Kaiser Permanente":
            minimum, maximum = 3, 5
        elif insurance == "Empire Blue Cross Blue Shield":
            minimum, maximum = 4, 6
    elif loc == "PHP":
        minimum, maximum = 5, 10

        if insurance == "Evernorth Health Services":
            minimum, maximum = 10, 15
        elif insurance == "Molina Healthcare":
            minimum, maximum = 4, 6
        elif insurance == "Empire Blue Cross Blue Shield":
            minimum, maximum = 4, 7
    else:
        minimum, maximum = 6, 12

        if insurance == "Evernorth Health Services":
            minimum, maximum = 12, 18
        elif insurance == "Empire Blue Cross Blue Shield":
            minimum, maximum = 5, 8

    return min(
        remaining_days,
        rng.randint(minimum, maximum),
    )


def _denial_probability(insurance: str, loc: str) -> float:
    probability = 0.18

    if insurance == "Empire Blue Cross Blue Shield":
        probability += 0.22

    if insurance == "Kaiser Permanente" and loc in {"DTX", "RTC"}:
        probability += 0.15

    if insurance == "Molina Healthcare" and loc in {"DTX", "PHP"}:
        probability += 0.14

    return min(probability, 0.65)


def _partial_probability(insurance: str, loc: str) -> float:
    probability = 0.22

    if insurance == "Kaiser Permanente" and loc in {"DTX", "RTC"}:
        probability += 0.20

    if insurance == "Molina Healthcare" and loc in {"DTX", "PHP"}:
        probability += 0.18

    if insurance == "Evernorth Health Services" and loc in {"PHP", "IOP"}:
        probability -= 0.10

    return max(min(probability, 0.60), 0.05)


def _decision_days(
    rng: random.Random,
    insurance: str,
    loc: str,
    requested_days: int,
) -> tuple[str, int, int]:
    roll = rng.random()
    denial_probability = _denial_probability(insurance, loc)
    partial_probability = _partial_probability(insurance, loc)

    if roll < denial_probability:
        return "Denied", 0, requested_days

    if roll < denial_probability + partial_probability:
        if requested_days <= 1:
            return "Approved", requested_days, 0

        minimum_ratio = 0.45
        maximum_ratio = 0.80

        if insurance == "Kaiser Permanente" and loc in {"DTX", "RTC"}:
            maximum_ratio = 0.70

        if insurance == "Molina Healthcare" and loc in {"DTX", "PHP"}:
            maximum_ratio = 0.68

        approved_days = max(
            1,
            min(
                requested_days - 1,
                round(requested_days * rng.uniform(minimum_ratio, maximum_ratio)),
            ),
        )
        return "Approved", approved_days, requested_days - approved_days

    return "Approved", requested_days, 0


def _follow_up_overturn_probability(
    insurance: str,
    stage: str,
) -> float:
    probability = 0.45 if stage == "P2P" else 0.35

    if insurance in {
        "Empire Blue Cross Blue Shield",
        "Kaiser Permanente",
        "Molina Healthcare",
    }:
        probability -= 0.12

    return max(probability, 0.10)


def _build_follow_up(
    rng: random.Random,
    insurance: str,
    decision_day: date,
) -> tuple[dict[str, Any] | None, bool]:
    follow_up: dict[str, Any] = {}
    overturned = False

    p2p_attempted = rng.random() < 0.40

    if p2p_attempted:
        p2p_day = min(
            decision_day + timedelta(days=rng.randint(1, 3)),
            SEED_END_DATE,
        )
        p2p_overturned = rng.random() < _follow_up_overturn_probability(
            insurance, "P2P"
        )

        follow_up.update(
            {
                "p2p_requested": True,
                "p2p_scheduled_at": _iso_datetime(p2p_day, rng.randint(9, 16)),
                "p2p_deadline": p2p_day.isoformat(),
                "p2p_outcome": "Overturned" if p2p_overturned else "Upheld",
                "p2p_notes": "Synthetic P2P outcome for development analytics.",
            }
        )
        overturned = p2p_overturned

    appeal_probability = 0.30 if p2p_attempted and not overturned else 0.18

    if not overturned and rng.random() < appeal_probability:
        appeal_day = min(
            decision_day + timedelta(days=rng.randint(3, 7)),
            SEED_END_DATE,
        )
        appeal_overturned = rng.random() < _follow_up_overturn_probability(
            insurance, "Appeal"
        )

        follow_up.update(
            {
                "appeal_submitted": True,
                "appeal_deadline": appeal_day.isoformat(),
                "appeal_outcome": "Overturned" if appeal_overturned else "Upheld",
                "appeal_notes": "Synthetic appeal outcome for development analytics.",
            }
        )
        overturned = appeal_overturned

    return (follow_up or None), overturned


def _build_record(
    *,
    rng: random.Random,
    client_name: str,
    date_of_birth: str,
    member_id: str,
    facility: str,
    insurance: str,
    loc: str,
    requested_days: int,
    auth_start: date,
    auth_type: str,
) -> tuple[dict[str, Any], str, bool]:
    status, approved_days, denied_days = _decision_days(
        rng,
        insurance,
        loc,
        requested_days,
    )

    decision_day = auth_start + timedelta(days=rng.randint(0, 2))

    if decision_day > SEED_END_DATE:
        decision_day = SEED_END_DATE

    submission_method = rng.choice(SUBMISSION_METHODS)
    portal_name = rng.choice(WEB_PORTALS) if submission_method == "Web Portal" else ""

    record: dict[str, Any] = {
        "client_name": client_name,
        "date_of_birth": date_of_birth,
        "member_id": member_id,
        "facility": facility,
        "loc": loc,
        "status": status,
        "insurance": insurance,
        "auth_type": auth_type,
        "submission_methods": submission_method,
        "portal_name": portal_name,
        "requested_days": requested_days,
        "approved_days": approved_days,
        "denied_days": denied_days,
        "auth_start_date": auth_start.isoformat(),
        "submitted_at": _iso_datetime(auth_start, rng.randint(8, 15)),
        "decision_at": _iso_datetime(decision_day, rng.randint(9, 17)),
        "programming_days": PROGRAMMING_DAYS.get((facility, loc), ""),
        "progress_made": rng.random() < 0.75,
        "facility_informed": True,
        "waiting_on_clinicals": False,
        "notes_links": "Synthetic development authorization.",
    }

    if approved_days > 0:
        auth_end_day = _end_date_for_programming_days(
            auth_start,
            approved_days,
            facility,
            loc,
        )
        record["auth_end_date"] = auth_end_day.isoformat()
        record["review_due_date"] = auth_end_day.isoformat()
        record["days_approved"] = str(approved_days)

    if denied_days > 0:
        record.update(
            {
                "denial_reason_category": rng.choice(DENIAL_REASONS),
                "denial_reason_notes": (
                    "Synthetic denial generated for development analytics."
                ),
                "denial_prevention_notes": (
                    "Synthetic record. Review documentation and payer criteria."
                ),
                "denial_date": decision_day.isoformat(),
                "denial_level_of_care": loc,
                "denial_source": rng.choice(DENIAL_SOURCES),
            }
        )

    outcome = (
        "Denied"
        if status == "Denied"
        else "Partial" if approved_days > 0 and denied_days > 0 else "Approved"
    )

    follow_up_overturned = False

    if outcome == "Denied":
        follow_up, follow_up_overturned = _build_follow_up(
            rng,
            insurance,
            decision_day,
        )

        if follow_up is not None:
            record["_synthetic_follow_up"] = follow_up

    return record, outcome, follow_up_overturned


def build_records(
    count: int,
    *,
    seed: int | None = None,
) -> list[dict[str, Any]]:
    rng = random.Random(seed)  # nosec B311
    fake = Faker()

    if seed is not None:
        fake.seed_instance(seed)

    records: list[dict[str, Any]] = []

    while len(records) < count:
        insurance = rng.choice(INSURERS)
        client_name = fake.name()
        date_of_birth = fake.date_of_birth(
            minimum_age=18,
            maximum_age=74,
        ).isoformat()
        member_id = f"SYN-{rng.randint(100000, 999999)}"

        loc_path = _build_loc_path(rng)
        calendar_durations = _episode_calendar_durations(
            rng,
            loc_path,
            insurance,
        )

        episode_start = SEED_START_DATE + timedelta(
            days=rng.randint(
                0,
                (SEED_END_DATE - SEED_START_DATE).days,
            )
        )

        previous_facility: str | None = None
        current_start = episode_start

        for loc in loc_path:
            if len(records) >= count or current_start > SEED_END_DATE:
                break

            loc_auth_sequence = 0
            facility = _choose_facility(
                rng,
                loc,
                previous_facility,
            )
            previous_facility = facility

            total_programming_days = _count_programming_days(
                current_start,
                calendar_durations[loc],
                facility,
                loc,
            )
            remaining_days = total_programming_days
            step_down_early = False

            while (
                remaining_days > 0
                and len(records) < count
                and current_start <= SEED_END_DATE
            ):
                requested_days = _review_chunk_days(
                    rng,
                    insurance,
                    loc,
                    remaining_days,
                )
                auth_type = "Initial" if loc_auth_sequence == 0 else "Concurrent"

                record, outcome, follow_up_overturned = _build_record(
                    rng=rng,
                    client_name=client_name,
                    date_of_birth=date_of_birth,
                    member_id=member_id,
                    facility=facility,
                    insurance=insurance,
                    loc=loc,
                    requested_days=requested_days,
                    auth_start=current_start,
                    auth_type=auth_type,
                )
                records.append(record)
                loc_auth_sequence += 1

                if follow_up_overturned:
                    effective_approved_days = requested_days
                else:
                    effective_approved_days = int(record["approved_days"] or 0)

                if effective_approved_days > 0:
                    approved_end = _end_date_for_programming_days(
                        current_start,
                        effective_approved_days,
                        facility,
                        loc,
                    )
                    current_start = approved_end + timedelta(days=1)

                if outcome == "Approved" and int(record["denied_days"] or 0) == 0:
                    remaining_days -= requested_days
                    continue

                if follow_up_overturned:
                    remaining_days -= requested_days
                    continue

                if outcome == "Partial":
                    step_down_early = True
                    break

                current_start += timedelta(days=rng.randint(1, 3))
                step_down_early = True
                break

            if current_start > SEED_END_DATE:
                break

            if step_down_early and loc == "IOP":
                break

    return records


def create_record(record: dict[str, Any]) -> dict[str, Any]:
    payload = dict(record)
    follow_up = payload.pop("_synthetic_follow_up", None)

    created = create_auth(payload)

    if created is None:
        raise RuntimeError("Authorization creation returned no record.")

    if follow_up:
        update_payload = {
            key: value
            for key, value in created.items()
            if key not in {"id", "created_at", "updated_at"}
        }
        update_payload.update(follow_up)

        updated = update_auth(
            created["id"],
            update_payload,
        )

        if updated is not None:
            return updated

    return created


def seed_records(
    count: int,
    *,
    seed: int | None = None,
) -> None:
    created = 0

    for record in build_records(
        count,
        seed=seed,
    ):
        create_record(record)
        created += 1
        print(
            "Created: "
            f"{record['client_name']} | "
            f"{record['facility']} | "
            f"{record['loc']} | "
            f"{record['auth_type']} | "
            f"{record['status']} | "
            f"{record['insurance']}"
        )

    print(f"Seeded {created} authorization records.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Seed realistic synthetic authorization episodes into the "
            "configured CareQFlow database."
        )
    )
    parser.add_argument(
        "--count",
        type=int,
        default=100,
        help="Maximum number of synthetic authorization records to create.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for reproducible synthetic data.",
    )
    parser.add_argument(
        "--installed",
        action="store_true",
        help=(
            "Seed the installed CareQFlow database using the "
            "ProgramData service environment."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.count < 1:
        raise SystemExit("Count must be at least 1.")

    if args.installed:
        load_installed_environment()

    settings = get_settings()

    print(f"Database: {settings.database_path}")

    seed_records(
        args.count,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()

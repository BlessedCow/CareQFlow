import argparse
import json
import secrets
import urllib.error
import urllib.parse
import urllib.request

from faker import Faker

API_URL = "http://127.0.0.1:8000/api/auths"

fake = Faker()

FACILITIES = [
    "Verdant Ridge",
    "Aura Wellness Collective",
    "Meridian Pathway Recovery",
    "New Dawn Treatment Center",
    "Harbor View Behavioral Health",
    "Summit Pathways",
    "Canyon Ridge Treatment",
]

INSURERS = [
    "Aetna",
    "Anthem",
    "Carelon Behavioral Health",
    "Cigna",
    "Evernorth Behavioral Health",
    "Kaiser",
    "Optum",
    "UnitedHealthcare",
]

LOCS = [
    "DTX",
    "RTC",
    "PHP",
    "IOP",
]

STATUSES = [
    "Approved",
    "Pending",
    "Denied",
    "Needs Review",
]

AUTH_TYPES = [
    "Initial",
    "Concurrent",
    "Retro",
]

SUBMISSION_METHODS = [
    "Fax",
    "Live Call",
    "Voicemail",
    "Web Portal",
]


def build_record() -> dict[str, str]:
    facility = secrets.choice(FACILITIES)
    loc = secrets.choice(LOCS)
    auth_type = secrets.choice(AUTH_TYPES)

    return {
        "client_name": fake.name(),
        "facility": facility,
        "loc": loc,
        "status": secrets.choice(STATUSES),
        "insurance": secrets.choice(INSURERS),
        "auth_type": auth_type,
        "submission_methods": secrets.choice(SUBMISSION_METHODS),
    }


def validate_api_url(api_url: str) -> None:
    parsed_url = urllib.parse.urlparse(api_url)

    if parsed_url.scheme != "http":
        raise SystemExit("The development seed API URL must use HTTP.")

    if parsed_url.hostname not in {"127.0.0.1", "localhost"}:
        raise SystemExit("The development seed API URL must target localhost.")

    if parsed_url.path != "/api/auths":
        raise SystemExit("The development seed API URL must target /api/auths.")


def create_record(record: dict[str, str]) -> dict:
    validate_api_url(API_URL)

    payload = json.dumps(record).encode("utf-8")

    request = urllib.request.Request(
        API_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(  # nosec B310
        request,
        timeout=10,
    ) as response:
        return json.loads(response.read().decode("utf-8"))


def seed_records(count: int) -> None:
    created = 0

    for _ in range(count):
        record = build_record()

        try:
            create_record(record)
            created += 1
            print(
                f"Created: {record['client_name']} | {record['facility']} | {record['loc']}"
            )
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8")
            raise SystemExit(f"API rejected record: {error_body}") from exc
        except urllib.error.URLError as exc:
            raise SystemExit(
                f"Could not connect to the API at {API_URL}: {exc}"
            ) from exc

    print(f"Seeded {created} development authorization records.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed local development authorization records."
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of development records to create.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.count < 1:
        raise SystemExit("Count must be at least 1.")

    seed_records(args.count)


if __name__ == "__main__":
    main()

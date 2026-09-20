from __future__ import annotations

import importlib.util
from collections import defaultdict
from datetime import date
from pathlib import Path

import pytest

from authstatus_api.authorizations.decision_snapshots import (
    list_auth_decision_snapshots,
)
from authstatus_api.crypto import generate_encryption_key

SEED_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "seed_dev_auths.py"

spec = importlib.util.spec_from_file_location("seed_dev_auths", SEED_SCRIPT)

if spec is None or spec.loader is None:
    raise RuntimeError("Could not load seed_dev_auths.py for testing.")

seed_dev_auths = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seed_dev_auths)


def test_build_records_respects_count_and_facility_loc_rules():
    records = seed_dev_auths.build_records(
        250,
        seed=12345,
    )

    assert len(records) == 250

    for record in records:
        assert record["loc"] in seed_dev_auths.FACILITY_LOCS[record["facility"]]


def test_build_records_stays_within_seed_window():
    records = seed_dev_auths.build_records(
        500,
        seed=24680,
    )

    for record in records:
        auth_start = date.fromisoformat(record["auth_start_date"])

        assert (
            seed_dev_auths.SEED_START_DATE <= auth_start <= seed_dev_auths.SEED_END_DATE
        )


@pytest.mark.parametrize(
    ("facility", "loc", "expected"),
    [
        (
            "Pinecrest Behavioral Health",
            "PHP",
            "Wed-Fri, 6 hours/day",
        ),
        (
            "Pinecrest Behavioral Health",
            "IOP",
            "Mon/Wed/Fri, 3 hours/day",
        ),
        (
            "Verdant Oaks Wellness Hub",
            "PHP",
            "Mon-Sat, 6 hours/day",
        ),
        (
            "Verdant Oaks Wellness Hub",
            "IOP",
            "Mon/Wed/Fri, 3 hours/day",
        ),
    ],
)
def test_programming_days_match_facility_schedule(
    facility,
    loc,
    expected,
):
    assert seed_dev_auths.PROGRAMMING_DAYS[(facility, loc)] == expected


def test_web_portal_records_only_populate_portal_for_web_submission():
    records = seed_dev_auths.build_records(
        250,
        seed=13579,
    )

    for record in records:
        if record["submission_methods"] == "Web Portal":
            assert record["portal_name"] in seed_dev_auths.WEB_PORTALS
        else:
            assert record["portal_name"] == ""


def test_episode_calendar_duration_ranges():
    rng = seed_dev_auths.random.Random(86420)

    for _ in range(500):
        loc_path = seed_dev_auths._build_loc_path(rng)
        insurance = rng.choice(seed_dev_auths.INSURERS)
        durations = seed_dev_auths._episode_calendar_durations(
            rng,
            loc_path,
            insurance,
        )

        if "DTX" in durations:
            assert 7 <= durations["DTX"] <= 14

        if "RTC" in durations and "DTX" not in durations:
            assert 14 <= durations["RTC"] <= 28

        if "DTX" in durations and "RTC" in durations:
            assert 28 <= durations["DTX"] + durations["RTC"] <= 42

        if "PHP" in durations:
            if insurance == "Evernorth Health Services":
                assert 42 <= durations["PHP"] <= 70
            else:
                assert 28 <= durations["PHP"] <= 56

        if "IOP" in durations:
            if insurance == "Evernorth Health Services":
                assert 70 <= durations["IOP"] <= 112
            else:
                assert 56 <= durations["IOP"] <= 84


def test_review_chunks_follow_payer_and_loc_ranges():
    rng = seed_dev_auths.random.Random(97531)

    assert (
        2
        <= seed_dev_auths._review_chunk_days(
            rng,
            "Kaiser Permanente",
            "DTX",
            20,
        )
        <= 4
    )

    assert (
        3
        <= seed_dev_auths._review_chunk_days(
            rng,
            "Kaiser Permanente",
            "RTC",
            20,
        )
        <= 5
    )

    assert (
        4
        <= seed_dev_auths._review_chunk_days(
            rng,
            "Molina Healthcare",
            "PHP",
            20,
        )
        <= 6
    )

    assert (
        10
        <= seed_dev_auths._review_chunk_days(
            rng,
            "Evernorth Health Services",
            "PHP",
            20,
        )
        <= 15
    )

    assert (
        12
        <= seed_dev_auths._review_chunk_days(
            rng,
            "Evernorth Health Services",
            "IOP",
            20,
        )
        <= 18
    )


def test_loc_paths_follow_supported_step_down_patterns():
    rng = seed_dev_auths.random.Random(112233)

    allowed_paths = {
        ("DTX", "RTC", "PHP", "IOP"),
        ("DTX", "PHP", "IOP"),
        ("RTC", "PHP", "IOP"),
        ("PHP", "IOP"),
        ("IOP",),
    }

    generated_paths = {tuple(seed_dev_auths._build_loc_path(rng)) for _ in range(250)}

    assert generated_paths <= allowed_paths
    assert generated_paths == allowed_paths


def test_payer_tendencies_adjust_denial_and_partial_probabilities():
    base_dtx_denial = seed_dev_auths._denial_probability(
        "Aetna Behavioral Health",
        "DTX",
    )
    base_php_denial = seed_dev_auths._denial_probability(
        "Aetna Behavioral Health",
        "PHP",
    )
    base_php_partial = seed_dev_auths._partial_probability(
        "Aetna Behavioral Health",
        "PHP",
    )

    assert (
        seed_dev_auths._denial_probability(
            "Kaiser Permanente",
            "DTX",
        )
        > base_dtx_denial
    )
    assert (
        seed_dev_auths._denial_probability(
            "Empire Blue Cross Blue Shield",
            "PHP",
        )
        > base_php_denial
    )
    assert (
        seed_dev_auths._denial_probability(
            "Molina Healthcare",
            "PHP",
        )
        > base_php_denial
    )
    assert (
        seed_dev_auths._partial_probability(
            "Evernorth Health Services",
            "PHP",
        )
        < base_php_partial
    )


def test_build_records_creates_initial_and_concurrent_review_cycles():
    records = seed_dev_auths.build_records(
        500,
        seed=20260919,
    )

    by_member_and_loc: dict[tuple[str, str], list[dict]] = defaultdict(list)

    for record in records:
        by_member_and_loc[
            (
                record["member_id"],
                record["loc"],
            )
        ].append(record)

    repeated_loc_groups = [
        group for group in by_member_and_loc.values() if len(group) > 1
    ]

    assert repeated_loc_groups

    assert any(
        any(record["auth_type"] == "Concurrent" for record in group)
        for group in repeated_loc_groups
    )


def test_first_auth_at_each_loc_is_initial_then_concurrent():
    records = seed_dev_auths.build_records(
        500,
        seed=20260920,
    )

    by_member_and_loc: dict[tuple[str, str], list[dict]] = defaultdict(list)

    for record in records:
        by_member_and_loc[
            (
                record["member_id"],
                record["loc"],
            )
        ].append(record)

    for loc_records in by_member_and_loc.values():
        ordered = sorted(
            loc_records,
            key=lambda item: (
                item["auth_start_date"],
                item["decision_at"],
            ),
        )

        assert ordered[0]["auth_type"] == "Initial"

        for record in ordered[1:]:
            assert record["auth_type"] == "Concurrent"


def test_programmed_auth_end_date_uses_service_days():
    start_day = date(2026, 8, 3)

    end_day = seed_dev_auths._end_date_for_programming_days(
        start_day,
        6,
        "Pinecrest Behavioral Health",
        "IOP",
    )

    assert end_day == date(2026, 8, 14)


def test_follow_up_payloads_only_use_supported_outcomes():
    records = seed_dev_auths.build_records(
        1000,
        seed=314159,
    )

    follow_ups = [
        record["_synthetic_follow_up"]
        for record in records
        if "_synthetic_follow_up" in record
    ]

    assert follow_ups

    for follow_up in follow_ups:
        if "p2p_outcome" in follow_up:
            assert follow_up["p2p_outcome"] in {"Overturned", "Upheld"}

        if "appeal_outcome" in follow_up:
            assert follow_up["appeal_outcome"] in {"Overturned", "Upheld"}


def test_create_record_persists_auth_and_automatic_snapshot(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv(
        "AUTHSTATUS_DATABASE_PATH",
        str(tmp_path / "seed_dev_auths.db"),
    )
    monkeypatch.setenv(
        "AUTHSTATUS_ENCRYPTION_KEY",
        generate_encryption_key(),
    )

    seed_dev_auths.get_settings.cache_clear()

    try:
        created = seed_dev_auths.create_record(
            {
                "facility": "Aura Horizon Recovery Center",
                "client_name": "Synthetic Test Client",
                "date_of_birth": "1990-01-01",
                "member_id": "SYN-TEST-001",
                "loc": "DTX",
                "submission_methods": "Web Portal",
                "portal_name": "Availity",
                "auth_type": "Initial",
                "status": "Denied",
                "insurance": "Kaiser Permanente",
                "requested_days": 4,
                "approved_days": 0,
                "denied_days": 4,
                "auth_start_date": "2026-09-01",
                "submitted_at": "2026-09-01T09:00:00",
                "decision_at": "2026-09-02T10:00:00",
                "denial_reason_category": "Medical Necessity",
                "denial_date": "2026-09-02",
                "denial_level_of_care": "DTX",
                "denial_source": "Payer Review",
            }
        )

        assert created["id"] > 0
        assert created["client_name"] == "Synthetic Test Client"
        assert created["status"] == "Denied"

        snapshots = list_auth_decision_snapshots(created["id"])

        assert snapshots is not None
        assert len(snapshots) == 1
        assert snapshots[0]["outcome"] == "Denied"
        assert snapshots[0]["source"] == "automatic"
        assert snapshots[0]["requested_days"] == 4
        assert snapshots[0]["denied_days"] == 4
    finally:
        seed_dev_auths.get_settings.cache_clear()


def test_create_record_follow_up_preserves_authorization_fields(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv(
        "AUTHSTATUS_DATABASE_PATH",
        str(tmp_path / "seed_follow_up.db"),
    )
    monkeypatch.setenv(
        "AUTHSTATUS_ENCRYPTION_KEY",
        generate_encryption_key(),
    )
    monkeypatch.setenv(
        "AUTHSTATUS_SQLCIPHER_KEY",
        "careqflow-test-sqlcipher-key-1234567890",
    )

    seed_dev_auths.get_settings.cache_clear()

    try:
        created = seed_dev_auths.create_record(
            {
                "facility": "Serenoa Healing Center",
                "client_name": "Synthetic Follow Up Client",
                "date_of_birth": "1990-01-01",
                "member_id": "SYN-FOLLOW-UP-001",
                "loc": "RTC",
                "submission_methods": "Web Portal",
                "portal_name": "Availity",
                "auth_type": "Initial",
                "status": "Denied",
                "insurance": "Molina Healthcare",
                "requested_days": 5,
                "approved_days": 0,
                "denied_days": 5,
                "auth_start_date": "2026-09-01",
                "submitted_at": "2026-09-01T09:00:00",
                "decision_at": "2026-09-02T10:00:00",
                "denial_reason_category": "Medical Necessity",
                "denial_date": "2026-09-02",
                "denial_level_of_care": "RTC",
                "denial_source": "Payer Review",
                "_synthetic_follow_up": {
                    "p2p_requested": True,
                    "p2p_scheduled_at": "2026-09-03T10:00:00",
                    "p2p_deadline": "2026-09-03",
                    "p2p_outcome": "Overturned",
                    "p2p_notes": "Synthetic P2P outcome.",
                },
            }
        )

        assert created["requested_days"] == 5
        assert created["approved_days"] == 0
        assert created["denied_days"] == 5
        assert created["auth_start_date"] == "2026-09-01"
        assert created["status"] == "Approved"
        assert created["p2p_requested"] is True
        assert created["p2p_outcome"] == "Overturned"
    finally:
        seed_dev_auths.get_settings.cache_clear()


def test_load_installed_environment_replaces_repo_authstatus_values(
    tmp_path,
    monkeypatch,
):
    installed_env = tmp_path / "carequeue.env"
    installed_database = tmp_path / "installed.sqlcipher.db"

    installed_env.write_text(
        "\n".join(
            [
                "AUTHSTATUS_APP_ENVIRONMENT=production",
                f"AUTHSTATUS_DATABASE_PATH={installed_database}",
                "AUTHSTATUS_DATABASE_ENCRYPTION=sqlcipher",
                "AUTHSTATUS_SQLCIPHER_KEY=installed-test-sqlcipher-key-1234567890",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        seed_dev_auths,
        "INSTALLED_ENV_PATH",
        installed_env,
    )

    monkeypatch.setenv(
        "AUTHSTATUS_APP_ENVIRONMENT",
        "development",
    )
    monkeypatch.setenv(
        "AUTHSTATUS_DATABASE_PATH",
        str(tmp_path / "repo.db"),
    )
    monkeypatch.setenv(
        "AUTHSTATUS_DATABASE_ENCRYPTION",
        "plaintext",
    )
    monkeypatch.setenv(
        "AUTHSTATUS_SQLCIPHER_KEY",
        "repo-test-key",
    )

    seed_dev_auths.get_settings.cache_clear()

    try:
        seed_dev_auths.load_installed_environment()

        assert seed_dev_auths.os.environ["AUTHSTATUS_APP_ENVIRONMENT"] == "production"
        assert seed_dev_auths.os.environ["AUTHSTATUS_DATABASE_PATH"] == str(
            installed_database
        )
        assert (
            seed_dev_auths.os.environ["AUTHSTATUS_DATABASE_ENCRYPTION"] == "sqlcipher"
        )
        assert (
            seed_dev_auths.os.environ["AUTHSTATUS_SQLCIPHER_KEY"]
            == "installed-test-sqlcipher-key-1234567890"
        )
    finally:
        seed_dev_auths.get_settings.cache_clear()


def test_load_installed_environment_rejects_missing_config(
    tmp_path,
    monkeypatch,
):
    missing_env = tmp_path / "missing-carequeue.env"

    monkeypatch.setattr(
        seed_dev_auths,
        "INSTALLED_ENV_PATH",
        missing_env,
    )

    with pytest.raises(
        SystemExit,
        match="Installed CareQFlow environment file not found",
    ):
        seed_dev_auths.load_installed_environment()

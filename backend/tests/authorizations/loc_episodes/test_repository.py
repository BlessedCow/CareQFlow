from __future__ import annotations

import pytest

from authstatus_api.authorizations.loc_episodes import (
    InvalidAuthLocEpisodeError,
    OverlappingAuthLocEpisodeError,
    close_auth_loc_episode,
    create_auth_loc_episode,
    delete_auth_loc_episode,
    get_auth_loc_episode,
    list_auth_loc_episodes,
    update_auth_loc_episode,
)
from authstatus_api.authorizations.records import create_auth
from authstatus_api.crypto import generate_encryption_key
from authstatus_api.settings import get_settings


@pytest.fixture(autouse=True)
def configure_test_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTHSTATUS_ENCRYPTION_KEY", generate_encryption_key())
    monkeypatch.setenv(
        "AUTHSTATUS_DATABASE_PATH",
        str(tmp_path / "auth_tracker.db"),
    )
    get_settings.cache_clear()

    yield

    get_settings.cache_clear()


def _create_auth() -> dict:
    record = create_auth(
        {
            "facility": "Facility A",
            "client_name": "Test Client",
            "loc": "RTC",
            "submission_methods": "Fax",
            "auth_type": "Concurrent",
            "status": "Pending",
        }
    )

    assert record is not None
    return record


def test_create_auth_loc_episode():
    auth = _create_auth()

    episode = create_auth_loc_episode(
        auth["id"],
        {
            "loc": "RTC",
            "started_at": "2026-09-01T08:00:00+00:00",
        },
    )

    assert episode is not None
    assert episode["auth_id"] == auth["id"]
    assert episode["loc"] == "RTC"
    assert episode["started_at"] == "2026-09-01T08:00:00+00:00"
    assert episode["ended_at"] is None
    assert episode["source"] == "manual"
    assert episode["created_at"]
    assert episode["updated_at"]


def test_create_auth_loc_episode_returns_none_for_missing_auth():
    episode = create_auth_loc_episode(
        999,
        {
            "loc": "RTC",
            "started_at": "2026-09-01T08:00:00+00:00",
        },
    )

    assert episode is None


def test_list_auth_loc_episodes_returns_chronological_history():
    auth = _create_auth()

    create_auth_loc_episode(
        auth["id"],
        {
            "loc": "PHP",
            "started_at": "2026-09-05T10:00:00+00:00",
        },
    )

    create_auth_loc_episode(
        auth["id"],
        {
            "loc": "RTC",
            "started_at": "2026-09-01T08:00:00+00:00",
            "ended_at": "2026-09-05T10:00:00+00:00",
        },
    )

    episodes = list_auth_loc_episodes(auth["id"])

    assert episodes is not None
    assert [episode["loc"] for episode in episodes] == [
        "RTC",
        "PHP",
    ]


def test_list_auth_loc_episodes_returns_none_for_missing_auth():
    assert list_auth_loc_episodes(999) is None


def test_get_auth_loc_episode():
    auth = _create_auth()

    created = create_auth_loc_episode(
        auth["id"],
        {
            "loc": "RTC",
            "started_at": "2026-09-01T08:00:00+00:00",
        },
    )

    assert created is not None

    episode = get_auth_loc_episode(
        auth["id"],
        created["id"],
    )

    assert episode == created


def test_update_auth_loc_episode():
    auth = _create_auth()

    created = create_auth_loc_episode(
        auth["id"],
        {
            "loc": "RTC",
            "started_at": "2026-09-01T08:00:00+00:00",
        },
    )

    assert created is not None

    updated = update_auth_loc_episode(
        auth["id"],
        created["id"],
        {
            "loc": "PHP",
            "source": "timeline",
        },
    )

    assert updated is not None
    assert updated["loc"] == "PHP"
    assert updated["source"] == "timeline"
    assert updated["started_at"] == created["started_at"]


def test_close_auth_loc_episode():
    auth = _create_auth()

    created = create_auth_loc_episode(
        auth["id"],
        {
            "loc": "RTC",
            "started_at": "2026-09-01T08:00:00+00:00",
        },
    )

    assert created is not None

    closed = close_auth_loc_episode(
        auth["id"],
        created["id"],
        "2026-09-05T10:00:00+00:00",
    )

    assert closed is not None
    assert closed["ended_at"] == "2026-09-05T10:00:00+00:00"


def test_delete_auth_loc_episode():
    auth = _create_auth()

    created = create_auth_loc_episode(
        auth["id"],
        {
            "loc": "RTC",
            "started_at": "2026-09-01T08:00:00+00:00",
        },
    )

    assert created is not None

    assert delete_auth_loc_episode(
        auth["id"],
        created["id"],
    )

    assert (
        get_auth_loc_episode(
            auth["id"],
            created["id"],
        )
        is None
    )


def test_rejects_episode_with_end_before_start():
    auth = _create_auth()

    with pytest.raises(
        InvalidAuthLocEpisodeError,
        match="ended_at cannot be earlier than started_at",
    ):
        create_auth_loc_episode(
            auth["id"],
            {
                "loc": "RTC",
                "started_at": "2026-09-05T10:00:00+00:00",
                "ended_at": "2026-09-01T08:00:00+00:00",
            },
        )


def test_rejects_invalid_episode_timestamp():
    auth = _create_auth()

    with pytest.raises(
        InvalidAuthLocEpisodeError,
        match="started_at must be a valid ISO 8601 timestamp",
    ):
        create_auth_loc_episode(
            auth["id"],
            {
                "loc": "RTC",
                "started_at": "not-a-timestamp",
            },
        )


def test_rejects_overlapping_auth_loc_episode():
    auth = _create_auth()

    create_auth_loc_episode(
        auth["id"],
        {
            "loc": "RTC",
            "started_at": "2026-09-01T08:00:00+00:00",
            "ended_at": "2026-09-05T10:00:00+00:00",
        },
    )

    with pytest.raises(
        OverlappingAuthLocEpisodeError,
        match="overlaps an existing episode",
    ):
        create_auth_loc_episode(
            auth["id"],
            {
                "loc": "PHP",
                "started_at": "2026-09-04T08:00:00+00:00",
                "ended_at": "2026-09-06T08:00:00+00:00",
            },
        )


def test_allows_adjacent_auth_loc_episodes():
    auth = _create_auth()

    first = create_auth_loc_episode(
        auth["id"],
        {
            "loc": "RTC",
            "started_at": "2026-09-01T08:00:00+00:00",
            "ended_at": "2026-09-05T10:00:00+00:00",
        },
    )

    second = create_auth_loc_episode(
        auth["id"],
        {
            "loc": "PHP",
            "started_at": "2026-09-05T10:00:00+00:00",
        },
    )

    assert first is not None
    assert second is not None


def test_update_rejects_overlap_with_another_episode():
    auth = _create_auth()

    first = create_auth_loc_episode(
        auth["id"],
        {
            "loc": "RTC",
            "started_at": "2026-09-01T08:00:00+00:00",
            "ended_at": "2026-09-05T10:00:00+00:00",
        },
    )

    second = create_auth_loc_episode(
        auth["id"],
        {
            "loc": "PHP",
            "started_at": "2026-09-05T10:00:00+00:00",
        },
    )

    assert first is not None
    assert second is not None

    with pytest.raises(
        OverlappingAuthLocEpisodeError,
        match="overlaps an existing episode",
    ):
        update_auth_loc_episode(
            auth["id"],
            second["id"],
            {
                "started_at": "2026-09-04T10:00:00+00:00",
            },
        )

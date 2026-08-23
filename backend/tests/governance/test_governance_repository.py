from __future__ import annotations

import pytest

from authstatus_api.governance.repository import (
    CURRENT_GOVERNANCE_ATTESTATION_VERSION,
    create_governance_attestation,
    get_current_governance_attestation,
    get_governance_attestation_history,
    get_latest_governance_attestation,
    is_governance_attestation_current,
)
from authstatus_api.security.users import create_user
from authstatus_api.settings import get_settings


@pytest.fixture(autouse=True)
def configure_test_settings(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "AUTHSTATUS_DATABASE_PATH",
        str(tmp_path / "auth_tracker.db"),
    )
    get_settings.cache_clear()

    yield

    get_settings.cache_clear()


def test_governance_attestation_is_incomplete_without_acceptance():
    assert get_latest_governance_attestation() is None
    assert get_current_governance_attestation() is None
    assert is_governance_attestation_current() is False


def test_create_governance_attestation_records_current_version():
    admin = create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    attestation = create_governance_attestation(
        organization_name="Example Facility",
        deployment_mode="self_hosted",
        accepted_by_user_id=admin["id"],
        app_version="0.2.0",
    )

    assert attestation["attestation_version"] == (
        CURRENT_GOVERNANCE_ATTESTATION_VERSION
    )
    assert attestation["organization_name"] == "Example Facility"
    assert attestation["deployment_mode"] == "self_hosted"
    assert attestation["accepted_by_user_id"] == admin["id"]
    assert attestation["accepted_by_username"] == admin["username"]
    assert attestation["accepted_at"]
    assert attestation["app_version"] == "0.2.0"

    assert is_governance_attestation_current() is True

    current = get_current_governance_attestation()

    assert current is not None
    assert current["accepted_by_username"] == admin["username"]


def test_governance_attestation_normalizes_organization_whitespace():
    admin = create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    attestation = create_governance_attestation(
        organization_name="  Example   Treatment   Center  ",
        deployment_mode="managed",
        accepted_by_user_id=admin["id"],
        app_version="0.2.0",
    )

    assert attestation["organization_name"] == "Example Treatment Center"


@pytest.mark.parametrize(
    "organization_name",
    [
        "",
        "   ",
        "\t\n",
    ],
)
def test_create_governance_attestation_requires_organization_name(
    organization_name,
):
    admin = create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    with pytest.raises(
        ValueError,
        match="Organization name is required.",
    ):
        create_governance_attestation(
            organization_name=organization_name,
            deployment_mode="self_hosted",
            accepted_by_user_id=admin["id"],
            app_version="0.2.0",
        )


def test_create_governance_attestation_rejects_unknown_deployment_mode():
    admin = create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    with pytest.raises(
        ValueError,
        match="Invalid deployment mode.",
    ):
        create_governance_attestation(
            organization_name="Example Facility",
            deployment_mode="unknown",
            accepted_by_user_id=admin["id"],
            app_version="0.2.0",
        )


def test_governance_attestations_are_append_only_history():
    admin = create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    first = create_governance_attestation(
        organization_name="Example Facility",
        deployment_mode="self_hosted",
        accepted_by_user_id=admin["id"],
        app_version="0.2.0",
    )

    second = create_governance_attestation(
        organization_name="Example Facility",
        deployment_mode="self_hosted",
        accepted_by_user_id=admin["id"],
        app_version="0.2.1",
    )

    latest = get_latest_governance_attestation()

    assert latest is not None
    assert latest["id"] == second["id"]
    assert first["id"] != second["id"]


def test_governance_attestation_history_returns_all_records_newest_first(
    monkeypatch,
):
    import authstatus_api.governance.repository as governance_repository

    admin = create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    first = create_governance_attestation(
        organization_name="Example Facility",
        deployment_mode="self_hosted",
        accepted_by_user_id=admin["id"],
        app_version="0.2.0",
    )

    monkeypatch.setattr(
        governance_repository,
        "CURRENT_GOVERNANCE_ATTESTATION_VERSION",
        2,
    )

    second = create_governance_attestation(
        organization_name="Example Facility",
        deployment_mode="managed",
        accepted_by_user_id=admin["id"],
        app_version="0.3.0",
    )

    history = get_governance_attestation_history()

    assert [item["id"] for item in history] == [
        second["id"],
        first["id"],
    ]

    assert [item["attestation_version"] for item in history] == [
        2,
        1,
    ]

    assert history[0]["accepted_by_username"] == admin["username"]
    assert history[1]["accepted_by_username"] == admin["username"]

    assert history[0]["deployment_mode"] == "managed"
    assert history[1]["deployment_mode"] == "self_hosted"


def test_governance_attestation_history_is_empty_without_acceptance():
    assert get_governance_attestation_history() == []

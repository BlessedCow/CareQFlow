from __future__ import annotations

import json

import pytest

import authstatus_api.governance.repository as governance_repository
import authstatus_api.governance.service as governance_service
from authstatus_api.governance.repository import (
    CURRENT_GOVERNANCE_ATTESTATION_VERSION,
)
from authstatus_api.governance.service import (
    GovernanceAttestationAlreadyCurrentError,
    GovernanceAttestationPermissionError,
    accept_governance_attestation,
    get_governance_status,
)
from authstatus_api.persistence.connections import get_conn
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


def test_governance_status_reports_incomplete_before_acceptance():
    status = get_governance_status()

    assert status == {
        "required_version": CURRENT_GOVERNANCE_ATTESTATION_VERSION,
        "current": False,
        "attestation": None,
    }


def test_admin_can_accept_governance_attestation():
    admin = create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    attestation = accept_governance_attestation(
        organization_name="Example Facility",
        deployment_mode="self_hosted",
        user=admin,
    )

    assert attestation["organization_name"] == "Example Facility"
    assert attestation["deployment_mode"] == "self_hosted"
    assert attestation["accepted_by_user_id"] == admin["id"]
    assert attestation["attestation_version"] == (
        CURRENT_GOVERNANCE_ATTESTATION_VERSION
    )
    assert attestation["app_version"] == get_settings().app_version

    status = get_governance_status()

    assert status["current"] is True
    assert status["attestation"]["id"] == attestation["id"]


@pytest.mark.parametrize(
    "role",
    [
        "UR",
        "Read Only",
    ],
)
def test_non_admin_cannot_accept_governance_attestation(role):
    user = create_user(
        "user@example.com",
        "correct horse battery staple",
        role=role,
    )

    with pytest.raises(
        GovernanceAttestationPermissionError,
        match="Only an administrator",
    ):
        accept_governance_attestation(
            organization_name="Example Facility",
            deployment_mode="self_hosted",
            user=user,
        )


def test_current_governance_attestation_cannot_be_accepted_twice():
    admin = create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    accept_governance_attestation(
        organization_name="Example Facility",
        deployment_mode="self_hosted",
        user=admin,
    )

    with pytest.raises(
        GovernanceAttestationAlreadyCurrentError,
        match="already been accepted",
    ):
        accept_governance_attestation(
            organization_name="Example Facility",
            deployment_mode="self_hosted",
            user=admin,
        )


def test_governance_acceptance_writes_safe_audit_event():
    admin = create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    attestation = accept_governance_attestation(
        organization_name="Sensitive Facility Name",
        deployment_mode="managed",
        user=admin,
    )

    with get_conn() as conn:
        row = conn.execute("""
            SELECT
                action,
                resource_type,
                resource_id,
                user_id,
                username,
                metadata,
                event_hash
            FROM audit_events
            WHERE action = 'governance.attestation_accepted'
            """).fetchone()

    assert row is not None
    assert row["resource_type"] == "governance_attestation"
    assert row["resource_id"] == attestation["id"]
    assert row["user_id"] == admin["id"]
    assert row["username"] == admin["username"]
    assert row["event_hash"]

    metadata = json.loads(row["metadata"])

    assert metadata == {
        "app_version": get_settings().app_version,
        "attestation_version": (CURRENT_GOVERNANCE_ATTESTATION_VERSION),
        "deployment_mode": "managed",
    }

    assert "Sensitive Facility Name" not in row["metadata"]


def test_new_attestation_version_requires_reacceptance(
    monkeypatch,
):
    admin = create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    first_attestation = accept_governance_attestation(
        organization_name="Example Facility",
        deployment_mode="self_hosted",
        user=admin,
    )

    assert first_attestation["attestation_version"] == 1
    assert get_governance_status()["current"] is True

    monkeypatch.setattr(
        governance_repository,
        "CURRENT_GOVERNANCE_ATTESTATION_VERSION",
        2,
    )
    monkeypatch.setattr(
        governance_service,
        "CURRENT_GOVERNANCE_ATTESTATION_VERSION",
        2,
    )

    outdated_status = get_governance_status()

    assert outdated_status == {
        "required_version": 2,
        "current": False,
        "attestation": None,
    }

    second_attestation = accept_governance_attestation(
        organization_name="Example Facility",
        deployment_mode="self_hosted",
        user=admin,
    )

    assert second_attestation["attestation_version"] == 2
    assert second_attestation["id"] != first_attestation["id"]

    current_status = get_governance_status()

    assert current_status["required_version"] == 2
    assert current_status["current"] is True
    assert current_status["attestation"]["id"] == second_attestation["id"]


def test_reacceptance_preserves_previous_attestation_history(
    monkeypatch,
):
    admin = create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    first_attestation = accept_governance_attestation(
        organization_name="Example Facility",
        deployment_mode="self_hosted",
        user=admin,
    )

    monkeypatch.setattr(
        governance_repository,
        "CURRENT_GOVERNANCE_ATTESTATION_VERSION",
        2,
    )
    monkeypatch.setattr(
        governance_service,
        "CURRENT_GOVERNANCE_ATTESTATION_VERSION",
        2,
    )

    second_attestation = accept_governance_attestation(
        organization_name="Example Facility",
        deployment_mode="self_hosted",
        user=admin,
    )

    with get_conn() as conn:
        rows = conn.execute("""
            SELECT
                id,
                attestation_version
            FROM governance_attestations
            ORDER BY id
            """).fetchall()

    assert [(row["id"], row["attestation_version"]) for row in rows] == [
        (first_attestation["id"], 1),
        (second_attestation["id"], 2),
    ]

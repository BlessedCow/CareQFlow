from __future__ import annotations

from typing import Any

from fastapi import Request

from authstatus_api.audit.service import record_audit_event
from authstatus_api.governance.repository import (
    CURRENT_GOVERNANCE_ATTESTATION_VERSION,
    CURRENT_GOVERNANCE_DOCUMENT_REVISION,
    create_governance_attestation,
    get_current_governance_attestation,
    is_governance_attestation_current,
)
from authstatus_api.persistence.connections import get_conn
from authstatus_api.settings import get_settings


class GovernanceAttestationAlreadyCurrentError(ValueError):
    pass


class GovernanceAttestationPermissionError(PermissionError):
    pass


def get_governance_status() -> dict[str, Any]:
    attestation = get_current_governance_attestation()

    return {
        "required_version": CURRENT_GOVERNANCE_ATTESTATION_VERSION,
        "required_document_revision": CURRENT_GOVERNANCE_DOCUMENT_REVISION,
        "current": attestation is not None,
        "attestation": attestation,
    }


def accept_governance_attestation(
    *,
    organization_name: str,
    deployment_mode: str,
    user: dict[str, Any],
    request: Request | None = None,
) -> dict[str, Any]:
    if user["role"] != "Admin":
        raise GovernanceAttestationPermissionError(
            "Only an administrator can accept governance terms."
        )

    if is_governance_attestation_current():
        raise GovernanceAttestationAlreadyCurrentError(
            "The current governance attestation has already been accepted."
        )

    settings = get_settings()

    with get_conn() as conn:
        conn.execute("BEGIN IMMEDIATE")

        attestation = create_governance_attestation(
            organization_name=organization_name,
            deployment_mode=deployment_mode,
            accepted_by_user_id=user["id"],
            app_version=settings.app_version,
            conn=conn,
        )

        record_audit_event(
            action="governance.attestation_accepted",
            resource_type="governance_attestation",
            resource_id=attestation["id"],
            user=user,
            metadata={
                "attestation_version": attestation["attestation_version"],
                "document_revision": attestation["document_revision"],
                "deployment_mode": attestation["deployment_mode"],
                "app_version": attestation["app_version"],
            },
            request=request,
            conn=conn,
        )

    return attestation

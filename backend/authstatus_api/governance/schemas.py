from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DeploymentMode = Literal[
    "self_hosted",
    "managed",
]


class GovernanceAttestationResponse(BaseModel):
    id: int
    attestation_version: int
    organization_name: str
    deployment_mode: DeploymentMode
    accepted_by_user_id: int
    accepted_by_username: str
    accepted_at: str
    app_version: str
    document_revision: str | None = None


class GovernanceStatusResponse(BaseModel):
    required_version: int
    required_document_revision: str
    current: bool
    attestation: GovernanceAttestationResponse | None = None


class GovernanceAcceptanceRequest(BaseModel):
    organization_name: str = Field(
        min_length=1,
        max_length=200,
    )
    deployment_mode: DeploymentMode

    acknowledge_privacy_security_responsibility: Literal[True]
    acknowledge_required_agreements: Literal[True]
    acknowledge_authorized_access: Literal[True]
    acknowledge_device_and_export_safeguards: Literal[True]
    acknowledge_test_data_requirements: Literal[True]

    model_config = ConfigDict(extra="forbid")

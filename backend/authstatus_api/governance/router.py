from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from authstatus_api.governance.repository import (
    get_governance_attestation_history,
)
from authstatus_api.governance.schemas import (
    GovernanceAcceptanceRequest,
    GovernanceAttestationResponse,
    GovernanceStatusResponse,
)
from authstatus_api.governance.service import (
    GovernanceAttestationAlreadyCurrentError,
    accept_governance_attestation,
    get_governance_status,
)
from authstatus_api.security.dependencies import (
    AuthenticatedUserDependency,
    require_role,
)

router = APIRouter(
    prefix="/api/governance",
    tags=["governance"],
)


def require_governance_admin(
    current_user: dict = AuthenticatedUserDependency,
) -> dict:
    if current_user["role"] != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted for this role.",
        )

    return current_user


GovernanceAdminDependency = Depends(require_governance_admin)

AdminUserDependency = Depends(require_role("Admin"))


@router.get(
    "/status",
    response_model=GovernanceStatusResponse,
)
def governance_status(
    current_user: dict = AuthenticatedUserDependency,
) -> GovernanceStatusResponse:
    del current_user

    return GovernanceStatusResponse(
        **get_governance_status(),
    )


@router.get(
    "/attestations",
    response_model=list[GovernanceAttestationResponse],
)
def governance_attestation_history(
    current_user: dict = AdminUserDependency,
) -> list[GovernanceAttestationResponse]:
    del current_user

    return [
        GovernanceAttestationResponse(**attestation)
        for attestation in get_governance_attestation_history()
    ]


@router.post(
    "/attestations",
    response_model=GovernanceAttestationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_governance_acceptance(
    payload: GovernanceAcceptanceRequest,
    request: Request,
    current_user: dict = GovernanceAdminDependency,
) -> GovernanceAttestationResponse:
    try:
        attestation = accept_governance_attestation(
            organization_name=payload.organization_name,
            deployment_mode=payload.deployment_mode,
            user=current_user,
            request=request,
        )
    except GovernanceAttestationAlreadyCurrentError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return GovernanceAttestationResponse(
        **attestation,
    )

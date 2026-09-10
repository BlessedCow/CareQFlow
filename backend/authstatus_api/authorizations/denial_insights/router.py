from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from authstatus_api.authorizations.denial_insights.repository import (
    InvalidDenialInsightsFilterError,
    build_denial_insights,
)
from authstatus_api.authorizations.denial_insights.rules import (
    RuleThresholds,
)
from authstatus_api.security.dependencies import require_role

router = APIRouter(
    prefix="/api/denial-insights",
    tags=["denial-insights"],
)

DenialInsightsUser = Depends(
    require_role(
        "Admin",
        "UR",
    )
)


class DenialInsightsThresholdsRequest(BaseModel):
    minimum_sample_size: int = Field(default=5, ge=1)
    minimum_denial_rate: float = Field(
        default=0.20,
        ge=0,
        le=1,
    )
    minimum_relative_increase: float = Field(
        default=0.25,
        ge=0,
    )

    model_config = ConfigDict(extra="forbid")


class DenialInsightsQueryRequest(BaseModel):
    dimensions: list[str] = Field(default_factory=list)
    filters: dict[str, str] = Field(default_factory=dict)
    baseline_filters: dict[str, str] = Field(default_factory=dict)
    start_at: str | None = None
    end_at: str | None = None
    preliminary_minimum: int = Field(default=5, ge=1)
    standard_minimum: int = Field(default=20, ge=1)
    rule_thresholds: DenialInsightsThresholdsRequest = Field(
        default_factory=DenialInsightsThresholdsRequest
    )
    include_evidence_calculation: bool = False

    model_config = ConfigDict(extra="forbid")


class DenialInsightsResponse(BaseModel):
    dimensions: list[str]
    filters: dict[str, str]
    baseline_filters: dict[str, str]
    start_at: str | None
    end_at: str | None
    summary: dict[str, Any]
    baseline: dict[str, Any]
    groups: list[dict[str, Any]]
    evaluations: list[dict[str, Any]]


@router.post(
    "/query",
    response_model=DenialInsightsResponse,
)
def query_denial_insights(
    payload: DenialInsightsQueryRequest,
    current_user: dict = DenialInsightsUser,
) -> DenialInsightsResponse:
    if payload.standard_minimum < payload.preliminary_minimum:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=("standard_minimum cannot be lower than " "preliminary_minimum."),
        )

    thresholds = RuleThresholds(
        minimum_sample_size=(payload.rule_thresholds.minimum_sample_size),
        minimum_denial_rate=(payload.rule_thresholds.minimum_denial_rate),
        minimum_relative_increase=(payload.rule_thresholds.minimum_relative_increase),
    )

    if payload.include_evidence_calculation and current_user["role"] != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=("Evidence calculation details are restricted " "to Admin users."),
        )

    try:
        result = build_denial_insights(
            dimensions=payload.dimensions,
            start_at=payload.start_at,
            end_at=payload.end_at,
            filters=payload.filters,
            baseline_filters=payload.baseline_filters,
            preliminary_minimum=payload.preliminary_minimum,
            standard_minimum=payload.standard_minimum,
            rule_thresholds=thresholds,
            include_evidence_calculation=(payload.include_evidence_calculation),
        )
    except (
        InvalidDenialInsightsFilterError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return DenialInsightsResponse(**result)

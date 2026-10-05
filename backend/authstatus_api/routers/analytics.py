from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from authstatus_api.audit.service import record_audit_event
from authstatus_api.authorizations.analytics import get_analytics_summary
from authstatus_api.schemas import AnalyticsSummaryResponse
from authstatus_api.security.dependencies import get_current_user

router = APIRouter(prefix="/api/analytics", tags=["analytics"])
AnalyticsUser = Depends(get_current_user)


@router.get("/summary", response_model=AnalyticsSummaryResponse)
def read_analytics_summary(
    request: Request,
    current_user: dict = AnalyticsUser,
) -> AnalyticsSummaryResponse:
    summary = get_analytics_summary()

    record_audit_event(
        action="analytics.summary.read",
        resource_type="analytics",
        user=current_user,
        metadata={
            "result_count": summary["total_auths"],
        },
        request=request,
    )

    return AnalyticsSummaryResponse(**summary)

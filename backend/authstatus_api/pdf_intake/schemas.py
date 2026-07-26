from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

PdfCandidateSource = Literal["form_field", "embedded_text"]


class PdfIntakeCandidate(BaseModel):
    value: str
    source: PdfCandidateSource
    confidence: Literal["high", "medium", "low"]
    needs_review: bool

    model_config = ConfigDict(extra="forbid")


class PdfIntakePreviewResponse(BaseModel):
    template_id: str | None
    template_matched: bool
    facility: PdfIntakeCandidate | None = None
    client_name: PdfIntakeCandidate | None = None
    admit_date_range: PdfIntakeCandidate | None = None
    date_of_birth: PdfIntakeCandidate | None = None
    insurance: PdfIntakeCandidate | None = None
    insurance_phone: PdfIntakeCandidate | None = None
    authorization_phone: PdfIntakeCandidate | None = None
    medical_member_id: PdfIntakeCandidate | None = None
    medical_group_number: PdfIntakeCandidate | None = None
    behavioral_health_member_id: PdfIntakeCandidate | None = None
    behavioral_health_group_number: PdfIntakeCandidate | None = None
    has_usable_text: bool

    model_config = ConfigDict(extra="forbid")

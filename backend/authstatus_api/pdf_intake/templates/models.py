from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ExtractionSource(StrEnum):
    FORM_FIELD = "form_field"
    EMBEDDED_TEXT = "embedded_text"


class ExtractionConfidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class ExtractedValue:
    value: str
    source: ExtractionSource
    confidence: ExtractionConfidence
    needs_review: bool


@dataclass(frozen=True)
class PdfTemplateExtraction:
    template_id: str | None
    is_match: bool
    admit_date_range: ExtractedValue | None
    facility: ExtractedValue | None
    patient_name: ExtractedValue | None
    patient_dob: ExtractedValue | None
    insurance_company: ExtractedValue | None
    insurance_phone: ExtractedValue | None
    medical_member_id: ExtractedValue | None
    medical_group_number: ExtractedValue | None
    behavioral_health_member_id: ExtractedValue | None
    behavioral_health_group_number: ExtractedValue | None
    authorization_phone: ExtractedValue | None


def empty_pdf_template_extraction() -> PdfTemplateExtraction:
    return PdfTemplateExtraction(
        template_id=None,
        is_match=False,
        admit_date_range=None,
        facility=None,
        patient_name=None,
        patient_dob=None,
        insurance_company=None,
        insurance_phone=None,
        medical_member_id=None,
        medical_group_number=None,
        behavioral_health_member_id=None,
        behavioral_health_group_number=None,
        authorization_phone=None,
    )

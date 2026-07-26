from __future__ import annotations

import re

from authstatus_api.pdf_intake.extractor import (
    PdfTextExtractionResult,
)
from authstatus_api.pdf_intake.templates.models import (
    ExtractedValue,
    ExtractionConfidence,
    ExtractionSource,
    PdfTemplateExtraction,
    empty_pdf_template_extraction,
)

STANDARD_VOB_TEMPLATE_ID = "standard_vob_v1"

STANDARD_VOB_REQUIRED_LABELS = (
    "ADMIT DATE RANGE:",
    "FACILITY:",
    "PATIENT INFORMATION",
    "INSURANCE COMPANY:",
    "MEDICAL ID#:",
    "PHONE NUMBER FOR AUTHORIZATION:",
)

STANDARD_VOB_FORM_FIELD_NAMES = {
    "admit_date_range": "text_1tgth",
    "facility": "text_2mfsh",
    "patient_name": "text_4cvll",
    "patient_dob": "text_5vani",
    "insurance_company": "text_18cnrm",
    "insurance_phone": "text_19jkwv",
    "medical_member_id": "text_27yesv",
    "medical_group_number": "text_26rjsk",
    "behavioral_health_member_id": "text_25attw",
    "behavioral_health_group_number": "text_23ikpt",
    "authorization_phone": "text_47lxxj",
}

STANDARD_VOB_EMPTY_VALUES = {
    "-",
    "N/A",
    "N A",
    "NA",
    "NONE",
    "NOT APPLICABLE",
}

STANDARD_VOB_TEXT_PATTERNS = {
    "admit_date_range": re.compile(
        r"^ADMIT DATE RANGE:[ \t]*(.*?)" r"(?=[ \t]*NUMBER OF ADMIT:|$)",
        re.IGNORECASE | re.MULTILINE,
    ),
    "facility": re.compile(
        r"^FACILITY:[ \t]*(.*?)" r"(?=[ \t]*CALLER:|$)",
        re.IGNORECASE | re.MULTILINE,
    ),
    "patient_name": re.compile(
        r"^PATIENT:[ \t]*(.*?)$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "patient_dob": re.compile(
        r"^DOB:[ \t]*(.*?)" r"(?=[ \t]*GENDER:|$)",
        re.IGNORECASE | re.MULTILINE,
    ),
    "insurance_company": re.compile(
        r"^INSURANCE COMPANY:[ \t]*(.*?)" r"(?=[ \t]*PHONE NUMBER:|$)",
        re.IGNORECASE | re.MULTILINE,
    ),
    "insurance_phone": re.compile(
        r"^INSURANCE COMPANY:[^\r\n]*?" r"\bPHONE NUMBER:[ \t]*(.*?)$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "medical_member_id": re.compile(
        r"^MEDICAL ID#:[ \t]*(.*?)" r"(?=[ \t]*MEDICAL GROUP#:|$)",
        re.IGNORECASE | re.MULTILINE,
    ),
    "medical_group_number": re.compile(
        r"^MEDICAL ID#:[^\r\n]*?"
        r"\bMEDICAL GROUP#:[ \t]*(.*?)"
        r"(?=[ \t]*BH ID#:|$)",
        re.IGNORECASE | re.MULTILINE,
    ),
    "behavioral_health_member_id": re.compile(
        r"^MEDICAL ID#:[^\r\n]*?" r"\bBH ID#:[ \t]*(.*?)" r"(?=[ \t]*BH GROUP#:|$)",
        re.IGNORECASE | re.MULTILINE,
    ),
    "behavioral_health_group_number": re.compile(
        r"^MEDICAL ID#:[^\r\n]*?" r"\bBH GROUP#:[ \t]*(.*?)$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "authorization_phone": re.compile(
        r"^PHONE NUMBER FOR AUTHORIZATION:[ \t]*(.*?)" r"(?=[ \t]*NO AUTH PENALTY:|$)",
        re.IGNORECASE | re.MULTILINE,
    ),
}


def is_standard_vob(
    result: PdfTextExtractionResult,
) -> bool:
    normalized_text = result.combined_text.upper()

    return all(label in normalized_text for label in STANDARD_VOB_REQUIRED_LABELS)


def _normalize_extracted_value(value: str) -> str:
    return " ".join(value.split()).strip()


def _meaningful_extracted_value(value: str) -> str | None:
    normalized_value = _normalize_extracted_value(value)

    if normalized_value.upper() in STANDARD_VOB_EMPTY_VALUES:
        return None

    return normalized_value or None


def _form_values(
    result: PdfTextExtractionResult,
) -> dict[str, str]:
    values_by_field_name: dict[str, str] = {}

    for field in result.form_fields:
        value = _meaningful_extracted_value(field.value)

        if value is not None:
            values_by_field_name[field.name] = value

    return {
        target_name: values_by_field_name[field_name]
        for target_name, field_name in (STANDARD_VOB_FORM_FIELD_NAMES.items())
        if values_by_field_name.get(field_name)
    }


def _embedded_text_values(
    combined_text: str,
) -> dict[str, str]:
    extracted: dict[str, str] = {}

    for field_name, pattern in STANDARD_VOB_TEXT_PATTERNS.items():
        match = pattern.search(combined_text)

        if match is None:
            continue

        value = _meaningful_extracted_value(match.group(1))

        if value is not None:
            extracted[field_name] = value

    return extracted


def _candidate(
    field_name: str,
    *,
    form_values: dict[str, str],
    text_values: dict[str, str],
) -> ExtractedValue | None:
    form_value = form_values.get(field_name)

    if form_value:
        return ExtractedValue(
            value=form_value,
            source=ExtractionSource.FORM_FIELD,
            confidence=ExtractionConfidence.HIGH,
            needs_review=False,
        )

    text_value = text_values.get(field_name)

    if text_value:
        return ExtractedValue(
            value=text_value,
            source=ExtractionSource.EMBEDDED_TEXT,
            confidence=ExtractionConfidence.MEDIUM,
            needs_review=True,
        )

    return None


def _resolve_same_identifier(
    candidate: ExtractedValue | None,
    fallback: ExtractedValue | None,
) -> ExtractedValue | None:
    if candidate is None:
        return None

    if candidate.value.strip().upper() != "SAME":
        return candidate

    if fallback is None:
        return None

    return ExtractedValue(
        value=fallback.value,
        source=candidate.source,
        confidence=candidate.confidence,
        needs_review=candidate.needs_review,
    )


def parse_standard_vob(
    result: PdfTextExtractionResult,
) -> PdfTemplateExtraction:
    if not is_standard_vob(result):
        return empty_pdf_template_extraction()

    form_values = _form_values(result)
    text_values = _embedded_text_values(result.combined_text)

    medical_member_id = _candidate(
        "medical_member_id",
        form_values=form_values,
        text_values=text_values,
    )
    medical_group_number = _candidate(
        "medical_group_number",
        form_values=form_values,
        text_values=text_values,
    )

    behavioral_health_member_id = _resolve_same_identifier(
        _candidate(
            "behavioral_health_member_id",
            form_values=form_values,
            text_values=text_values,
        ),
        medical_member_id,
    )
    behavioral_health_group_number = _resolve_same_identifier(
        _candidate(
            "behavioral_health_group_number",
            form_values=form_values,
            text_values=text_values,
        ),
        medical_group_number,
    )

    return PdfTemplateExtraction(
        template_id=STANDARD_VOB_TEMPLATE_ID,
        is_match=True,
        admit_date_range=_candidate(
            "admit_date_range",
            form_values=form_values,
            text_values=text_values,
        ),
        facility=_candidate(
            "facility",
            form_values=form_values,
            text_values=text_values,
        ),
        patient_name=_candidate(
            "patient_name",
            form_values=form_values,
            text_values=text_values,
        ),
        patient_dob=_candidate(
            "patient_dob",
            form_values=form_values,
            text_values=text_values,
        ),
        insurance_company=_candidate(
            "insurance_company",
            form_values=form_values,
            text_values=text_values,
        ),
        insurance_phone=_candidate(
            "insurance_phone",
            form_values=form_values,
            text_values=text_values,
        ),
        medical_member_id=medical_member_id,
        medical_group_number=medical_group_number,
        behavioral_health_member_id=behavioral_health_member_id,
        behavioral_health_group_number=behavioral_health_group_number,
        authorization_phone=_candidate(
            "authorization_phone",
            form_values=form_values,
            text_values=text_values,
        ),
    )

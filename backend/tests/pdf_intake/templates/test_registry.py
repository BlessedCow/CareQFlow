from __future__ import annotations

from authstatus_api.pdf_intake.extractor import (
    PdfTextExtractionResult,
)
from authstatus_api.pdf_intake.templates.registry import parse_pdf_intake
from authstatus_api.pdf_intake.templates.standard_vob import (
    STANDARD_VOB_TEMPLATE_ID,
)


def extraction_result(text: str) -> PdfTextExtractionResult:
    return PdfTextExtractionResult(
        page_count=1,
        page_texts=(text,),
        combined_text=text,
        has_usable_text=bool(text.strip()),
        form_fields=(),
    )


def test_registry_returns_matching_template():
    result = extraction_result("""
        ADMIT DATE RANGE:
        FACILITY:
        PATIENT INFORMATION
        INSURANCE COMPANY:
        MEDICAL ID#:
        PHONE NUMBER FOR AUTHORIZATION:
        """)

    extraction = parse_pdf_intake(result)

    assert extraction.is_match is True
    assert extraction.template_id == STANDARD_VOB_TEMPLATE_ID


def test_registry_returns_empty_result_for_unknown_layout():
    extraction = parse_pdf_intake(extraction_result("Unrecognized document layout"))

    assert extraction.is_match is False
    assert extraction.template_id is None
    assert extraction.facility is None

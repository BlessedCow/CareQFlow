from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from authstatus_api.audit.service import record_audit_event
from authstatus_api.pdf_intake.extractor import (
    EncryptedPdfError,
    InvalidPdfError,
    OversizedPdfError,
    PdfExtractionError,
)
from authstatus_api.pdf_intake.request_body import (
    PdfRequestBodyTooLargeError,
    read_pdf_request_body,
)
from authstatus_api.pdf_intake.schemas import (
    PdfIntakeCandidate,
    PdfIntakePreviewResponse,
)
from authstatus_api.pdf_intake.templates.models import ExtractedValue
from authstatus_api.pdf_intake.templates.registry import parse_pdf_intake
from authstatus_api.pdf_intake.worker import (
    PdfExtractionTimeoutError,
    extract_pdf_text_isolated,
)
from authstatus_api.security.dependencies import require_role

router = APIRouter(
    prefix="/api/pdf-intake",
    tags=["pdf-intake"],
)

PdfIntakeUser = Depends(require_role("Admin", "UR"))

NO_STORE_HEADERS = {
    "Cache-Control": "no-store, private",
    "Pragma": "no-cache",
    "Expires": "0",
}


def _raise_pdf_error(
    *,
    status_code: int,
    detail: str,
) -> None:
    raise HTTPException(
        status_code=status_code,
        detail=detail,
        headers=NO_STORE_HEADERS,
    )


def _candidate(
    extracted_value: ExtractedValue | None,
) -> PdfIntakeCandidate | None:
    if extracted_value is None:
        return None

    return PdfIntakeCandidate(
        value=extracted_value.value,
        source=extracted_value.source.value,
        confidence=extracted_value.confidence.value,
        needs_review=extracted_value.needs_review,
    )


def _candidate_count(
    preview: PdfIntakePreviewResponse,
) -> int:
    candidate_fields = (
        preview.facility,
        preview.client_name,
        preview.admit_date_range,
        preview.date_of_birth,
        preview.insurance,
        preview.insurance_phone,
        preview.authorization_phone,
        preview.medical_member_id,
        preview.medical_group_number,
        preview.behavioral_health_member_id,
        preview.behavioral_health_group_number,
    )

    return sum(candidate is not None for candidate in candidate_fields)


@router.post(
    "/preview",
    response_model=PdfIntakePreviewResponse,
)
async def preview_pdf_intake(
    request: Request,
    response: Response,
    current_user: dict = PdfIntakeUser,
) -> PdfIntakePreviewResponse:
    content_type = (
        request.headers.get("content-type", "").partition(";")[0].strip().lower()
    )

    if content_type != "application/pdf":
        _raise_pdf_error(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="The request must contain a PDF.",
        )

    try:
        pdf_bytes = await read_pdf_request_body(request)
        extraction_result = extract_pdf_text_isolated(pdf_bytes)
    except (
        PdfRequestBodyTooLargeError,
        OversizedPdfError,
    ):
        _raise_pdf_error(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="The uploaded PDF exceeds the allowed file size.",
        )
    except EncryptedPdfError:
        _raise_pdf_error(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Encrypted PDFs are not supported.",
        )
    except InvalidPdfError:
        _raise_pdf_error(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The uploaded PDF could not be read.",
        )
    except PdfExtractionTimeoutError:
        _raise_pdf_error(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The uploaded PDF could not be processed in time.",
        )
    except PdfExtractionError:
        _raise_pdf_error(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The uploaded PDF could not be processed.",
        )

    parsed = parse_pdf_intake(extraction_result)

    preview = PdfIntakePreviewResponse(
        template_id=parsed.template_id,
        template_matched=parsed.is_match,
        facility=_candidate(parsed.facility),
        client_name=_candidate(parsed.patient_name),
        admit_date_range=_candidate(parsed.admit_date_range),
        date_of_birth=_candidate(parsed.patient_dob),
        insurance=_candidate(parsed.insurance_company),
        insurance_phone=_candidate(parsed.insurance_phone),
        authorization_phone=_candidate(parsed.authorization_phone),
        medical_member_id=_candidate(parsed.medical_member_id),
        medical_group_number=_candidate(parsed.medical_group_number),
        behavioral_health_member_id=_candidate(parsed.behavioral_health_member_id),
        behavioral_health_group_number=_candidate(
            parsed.behavioral_health_group_number
        ),
        has_usable_text=extraction_result.has_usable_text,
    )

    response.headers.update(NO_STORE_HEADERS)

    record_audit_event(
        action="pdf_intake.preview",
        resource_type="pdf_intake",
        user=current_user,
        metadata={
            "template_matched": preview.template_matched,
            "candidate_count": _candidate_count(preview),
            "has_usable_text": preview.has_usable_text,
        },
        request=request,
    )

    return preview

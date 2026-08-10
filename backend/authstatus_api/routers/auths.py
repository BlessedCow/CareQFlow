from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from authstatus_api.audit.service import audit_field_names, record_audit_event
from authstatus_api.authorizations.documents import (
    AuthDocumentLimitError,
    InvalidAuthDocumentError,
    InvalidAuthDocumentTypeError,
    create_auth_document,
    delete_auth_document,
    get_auth_document_pdf,
    list_auth_documents,
)
from authstatus_api.authorizations.events import (
    create_auth_event,
    delete_auth_event,
    list_auth_events,
    update_auth_event,
)
from authstatus_api.authorizations.records import (
    create_auth,
    delete_auth,
    get_auth,
    list_auths,
    update_auth,
)
from authstatus_api.pdf_intake.request_body import (
    PdfRequestBodyTooLargeError,
    read_pdf_request_body,
)
from authstatus_api.schemas import (
    AuthCreate,
    AuthDocumentListResponse,
    AuthDocumentRecord,
    AuthEventCreate,
    AuthEventListResponse,
    AuthEventRecord,
    AuthEventUpdate,
    AuthListResponse,
    AuthRecord,
    AuthUpdate,
    DeleteResponse,
)
from authstatus_api.security.dependencies import get_current_user, require_role

router = APIRouter(prefix="/api/auths", tags=["auths"])
ReadAuthUser = Depends(get_current_user)
WriteAuthUser = Depends(require_role("Admin", "UR"))


NO_STORE_HEADERS = {
    "Cache-Control": "no-store, private",
    "Pragma": "no-cache",
    "Expires": "0",
}


def _raise_document_error(
    *,
    status_code: int,
    detail: str,
) -> None:
    raise HTTPException(
        status_code=status_code,
        detail=detail,
        headers=NO_STORE_HEADERS,
    )


def _validate_pdf_content_type(request: Request) -> None:
    content_type = (
        request.headers.get("content-type", "").partition(";")[0].strip().lower()
    )

    if content_type != "application/pdf":
        _raise_document_error(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="The request must contain a PDF.",
        )


def _download_headers(filename: str) -> dict[str, str]:
    safe_filename = (
        filename.replace("\\", "_")
        .replace("/", "_")
        .replace('"', "")
        .replace("\r", "")
        .replace("\n", "")
        .strip()
    )

    if not safe_filename:
        safe_filename = "authorization-document.pdf"

    return {
        **NO_STORE_HEADERS,
        "Content-Disposition": (
            "attachment; " f"filename*=UTF-8''{quote(safe_filename)}"
        ),
    }


@router.get("", response_model=AuthListResponse)
def read_auths(current_user: dict = ReadAuthUser) -> AuthListResponse:
    return AuthListResponse(auths=list_auths())


@router.post("", response_model=AuthRecord, status_code=status.HTTP_201_CREATED)
def create_auth_record(
    payload: AuthCreate,
    request: Request,
    current_user: dict = WriteAuthUser,
) -> AuthRecord:
    payload_data = payload.model_dump()
    record = create_auth(payload_data)

    record_audit_event(
        action="auth.create",
        resource_type="auth",
        resource_id=record["id"],
        user=current_user,
        metadata=audit_field_names(payload_data),
        request=request,
    )

    return AuthRecord(**record)


@router.get("/{auth_id}", response_model=AuthRecord)
def read_auth(auth_id: int, current_user: dict = ReadAuthUser) -> AuthRecord:
    record = get_auth(auth_id)

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Auth record not found."
        )

    return AuthRecord(**record)


@router.get("/{auth_id}/documents", response_model=AuthDocumentListResponse)
def read_auth_document_records(
    auth_id: int,
    current_user: dict = ReadAuthUser,
) -> AuthDocumentListResponse:
    documents = list_auth_documents(auth_id)

    if documents is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Auth record not found.",
        )

    return AuthDocumentListResponse(
        documents=[AuthDocumentRecord(**document) for document in documents]
    )


@router.post(
    "/{auth_id}/documents",
    response_model=AuthDocumentRecord,
    status_code=status.HTTP_201_CREATED,
)
async def create_auth_document_record(
    auth_id: int,
    document_type: str,
    request: Request,
    filename: str = "",
    current_user: dict = WriteAuthUser,
) -> AuthDocumentRecord:
    _validate_pdf_content_type(request)

    try:
        pdf_bytes = await read_pdf_request_body(request)
        document = create_auth_document(
            auth_id,
            document_type=document_type,
            original_filename=filename,
            pdf_bytes=pdf_bytes,
        )
    except PdfRequestBodyTooLargeError:
        _raise_document_error(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="The uploaded PDF exceeds the allowed file size.",
        )
    except AuthDocumentLimitError:
        _raise_document_error(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Authorization document storage limit exceeded.",
        )
    except InvalidAuthDocumentTypeError:
        _raise_document_error(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid authorization document type.",
        )
    except InvalidAuthDocumentError:
        _raise_document_error(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The uploaded document must be a PDF.",
        )

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Auth record not found.",
        )

    record_audit_event(
        action="auth_document.create",
        resource_type="auth_document",
        resource_id=document["id"],
        user=current_user,
        metadata={
            "auth_id": auth_id,
            "document_type": document["document_type"],
            "file_size_bytes": document["file_size_bytes"],
        },
        request=request,
    )

    return AuthDocumentRecord(**document)


@router.get("/{auth_id}/documents/{document_id}/pdf")
def download_auth_document_pdf(
    auth_id: int,
    document_id: int,
    request: Request,
    current_user: dict = ReadAuthUser,
) -> Response:
    result = get_auth_document_pdf(auth_id, document_id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authorization document not found.",
        )

    document, pdf_bytes = result

    record_audit_event(
        action="auth_document.download",
        resource_type="auth_document",
        resource_id=document_id,
        user=current_user,
        metadata={
            "auth_id": auth_id,
            "document_type": document["document_type"],
        },
        request=request,
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers=_download_headers(document["original_filename"]),
    )


@router.delete("/{auth_id}/documents/{document_id}", response_model=DeleteResponse)
def delete_auth_document_record(
    auth_id: int,
    document_id: int,
    request: Request,
    current_user: dict = WriteAuthUser,
) -> DeleteResponse:
    deleted = delete_auth_document(auth_id, document_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authorization document not found.",
        )

    record_audit_event(
        action="auth_document.delete",
        resource_type="auth_document",
        resource_id=document_id,
        user=current_user,
        metadata={"auth_id": auth_id},
        request=request,
    )

    return DeleteResponse(deleted=True, id=document_id)


@router.patch("/{auth_id}", response_model=AuthRecord)
def update_auth_record(
    auth_id: int,
    payload: AuthUpdate,
    request: Request,
    current_user: dict = WriteAuthUser,
) -> AuthRecord:
    payload_data = payload.model_dump(exclude_unset=True)
    record = update_auth(auth_id, payload_data)

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Auth record not found."
        )

    record_audit_event(
        action="auth.update",
        resource_type="auth",
        resource_id=auth_id,
        user=current_user,
        metadata=audit_field_names(payload_data),
        request=request,
    )

    return AuthRecord(**record)


@router.get("/{auth_id}/events", response_model=AuthEventListResponse)
def read_auth_events(
    auth_id: int,
    current_user: dict = ReadAuthUser,
) -> AuthEventListResponse:
    events = list_auth_events(auth_id)

    if events is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Auth record not found."
        )

    return AuthEventListResponse(events=[AuthEventRecord(**event) for event in events])


@router.post(
    "/{auth_id}/events",
    response_model=AuthEventRecord,
    status_code=status.HTTP_201_CREATED,
)
def create_auth_event_record(
    auth_id: int,
    payload: AuthEventCreate,
    request: Request,
    current_user: dict = WriteAuthUser,
) -> AuthEventRecord:
    payload_data = payload.model_dump()
    event = create_auth_event(auth_id, payload_data)

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Auth record not found."
        )

    record_audit_event(
        action="auth_event.create",
        resource_type="auth_event",
        resource_id=event["id"],
        user=current_user,
        metadata={"auth_id": auth_id, **audit_field_names(payload_data)},
        request=request,
    )

    return AuthEventRecord(**event)


@router.patch("/{auth_id}/events/{event_id}", response_model=AuthEventRecord)
def update_auth_event_record(
    auth_id: int,
    event_id: int,
    payload: AuthEventUpdate,
    request: Request,
    current_user: dict = WriteAuthUser,
) -> AuthEventRecord:
    payload_data = payload.model_dump(exclude_unset=True)
    event = update_auth_event(auth_id, event_id, payload_data)

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Auth event not found."
        )

    record_audit_event(
        action="auth_event.update",
        resource_type="auth_event",
        resource_id=event_id,
        user=current_user,
        metadata={"auth_id": auth_id, **audit_field_names(payload_data)},
        request=request,
    )

    return AuthEventRecord(**event)


@router.delete("/{auth_id}/events/{event_id}", response_model=DeleteResponse)
def delete_auth_event_record(
    auth_id: int,
    event_id: int,
    request: Request,
    current_user: dict = WriteAuthUser,
) -> DeleteResponse:
    deleted = delete_auth_event(auth_id, event_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Auth event not found."
        )

    record_audit_event(
        action="auth_event.delete",
        resource_type="auth_event",
        resource_id=event_id,
        user=current_user,
        metadata={"auth_id": auth_id},
        request=request,
    )

    return DeleteResponse(deleted=True, id=event_id)


@router.delete("/{auth_id}", response_model=DeleteResponse)
def delete_auth_record(
    auth_id: int,
    request: Request,
    current_user: dict = WriteAuthUser,
) -> DeleteResponse:
    deleted = delete_auth(auth_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Auth record not found."
        )

    record_audit_event(
        action="auth.delete",
        resource_type="auth",
        resource_id=auth_id,
        user=current_user,
        request=request,
    )

    return DeleteResponse(deleted=True, id=auth_id)

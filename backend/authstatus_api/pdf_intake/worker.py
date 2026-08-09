from __future__ import annotations

from multiprocessing import Pipe, Process
from multiprocessing.connection import Connection
from typing import Literal

from authstatus_api.pdf_intake.extractor import (
    EncryptedPdfError,
    InvalidPdfError,
    OversizedPdfError,
    PdfExtractionError,
    PdfTextExtractionResult,
    extract_pdf_text,
)

DEFAULT_PDF_EXTRACTION_TIMEOUT_SECONDS = 10.0

PdfWorkerStatus = Literal[
    "ok",
    "encrypted",
    "invalid",
    "oversized",
    "extraction_error",
]


class PdfExtractionTimeoutError(PdfExtractionError):
    pass


def _send_worker_result(
    connection: Connection,
    status: PdfWorkerStatus,
    result: PdfTextExtractionResult | None = None,
) -> None:
    try:
        connection.send((status, result))
    finally:
        connection.close()


def _extract_pdf_text_worker(
    pdf_bytes: bytes,
    connection: Connection,
) -> None:
    try:
        result = extract_pdf_text(pdf_bytes)
    except EncryptedPdfError:
        _send_worker_result(connection, "encrypted")
    except InvalidPdfError:
        _send_worker_result(connection, "invalid")
    except OversizedPdfError:
        _send_worker_result(connection, "oversized")
    except PdfExtractionError:
        _send_worker_result(connection, "extraction_error")
    else:
        _send_worker_result(connection, "ok", result)


def extract_pdf_text_isolated(
    pdf_bytes: bytes,
    *,
    timeout_seconds: float = DEFAULT_PDF_EXTRACTION_TIMEOUT_SECONDS,
) -> PdfTextExtractionResult:
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than zero.")

    parent_connection, child_connection = Pipe(duplex=False)
    process = Process(
        target=_extract_pdf_text_worker,
        args=(pdf_bytes, child_connection),
    )

    process.start()
    child_connection.close()

    try:
        if not parent_connection.poll(timeout_seconds):
            process.terminate()
            process.join(timeout=1)

            if process.is_alive():
                process.kill()
                process.join(timeout=1)

            raise PdfExtractionTimeoutError("PDF extraction timed out.")

        status, result = parent_connection.recv()
    finally:
        parent_connection.close()

        if process.is_alive():
            process.join(timeout=1)

    if status == "ok" and result is not None:
        return result

    if status == "encrypted":
        raise EncryptedPdfError("Encrypted PDFs are not supported.")

    if status == "invalid":
        raise InvalidPdfError("The uploaded PDF could not be read.")

    if status == "oversized":
        raise OversizedPdfError("The uploaded PDF exceeds the allowed file size.")

    raise PdfExtractionError("The uploaded PDF could not be processed.")

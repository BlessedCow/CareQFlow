from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

PDF_FILE_SIGNATURE = b"%PDF-"
DEFAULT_MAX_PDF_SIZE_BYTES = 10 * 1024 * 1024
MINIMUM_USABLE_TEXT_CHARACTERS = 20


class PdfExtractionError(ValueError):
    pass


class InvalidPdfError(PdfExtractionError):
    pass


class EncryptedPdfError(PdfExtractionError):
    pass


class OversizedPdfError(PdfExtractionError):
    pass


@dataclass(frozen=True)
class PdfFormField:
    name: str
    value: str
    field_type: str
    page_number: int
    rectangle: tuple[float, float, float, float] | None


@dataclass(frozen=True)
class PdfTextExtractionResult:
    page_count: int
    page_texts: tuple[str, ...]
    combined_text: str
    has_usable_text: bool
    form_fields: tuple[PdfFormField, ...]


def _normalize_page_text(text: str | None) -> str:
    if not text:
        return ""

    normalized_lines = [" ".join(line.split()) for line in text.splitlines()]

    return "\n".join(line for line in normalized_lines if line)


def _resolve_pdf_object(value: object) -> object:
    get_object = getattr(value, "get_object", None)

    if callable(get_object):
        return get_object()

    return value


def _pdf_value_to_text(value: object) -> str:
    if value is None:
        return ""

    resolved_value = _resolve_pdf_object(value)

    if isinstance(resolved_value, bytes):
        return resolved_value.decode(
            "utf-8",
            errors="replace",
        ).strip()

    if isinstance(resolved_value, list | tuple):
        values = [_pdf_value_to_text(item) for item in resolved_value]

        return ", ".join(item for item in values if item)

    text = str(resolved_value).strip()

    if text.startswith("/"):
        return text[1:]

    return text


def _field_property(
    widget: object,
    property_name: str,
) -> object | None:
    current_object: object | None = widget
    visited_object_ids: set[int] = set()

    for _ in range(20):
        if current_object is None:
            return None

        resolved_object = _resolve_pdf_object(current_object)
        object_id = id(resolved_object)

        if object_id in visited_object_ids:
            return None

        visited_object_ids.add(object_id)

        get_value = getattr(resolved_object, "get", None)

        if not callable(get_value):
            return None

        value = get_value(property_name)

        if value is not None:
            return value

        current_object = get_value("/Parent")

    return None


def _rectangle_from_widget(
    widget: object,
) -> tuple[float, float, float, float] | None:
    resolved_widget = _resolve_pdf_object(widget)
    get_value = getattr(resolved_widget, "get", None)

    if not callable(get_value):
        return None

    rectangle = get_value("/Rect")

    if rectangle is None:
        return None

    resolved_rectangle = _resolve_pdf_object(rectangle)

    try:
        values = tuple(
            float(_resolve_pdf_object(value)) for value in resolved_rectangle
        )
    except (TypeError, ValueError):
        return None

    if len(values) != 4:
        return None

    return values


def _extract_form_fields(reader: PdfReader) -> tuple[PdfFormField, ...]:
    extracted_fields: list[PdfFormField] = []
    seen_fields: set[
        tuple[
            str,
            int,
            tuple[float, float, float, float] | None,
        ]
    ] = set()

    for page_number, page in enumerate(reader.pages, start=1):
        try:
            annotations = page.get("/Annots", [])
            resolved_annotations = _resolve_pdf_object(annotations)
        except (AttributeError, KeyError, TypeError, ValueError):
            continue

        try:
            annotation_items = list(resolved_annotations)
        except TypeError:
            continue

        for annotation_reference in annotation_items:
            try:
                widget = _resolve_pdf_object(annotation_reference)
                get_value = getattr(widget, "get", None)

                if not callable(get_value):
                    continue

                subtype = _pdf_value_to_text(get_value("/Subtype"))

                if subtype != "Widget":
                    continue

                name = _pdf_value_to_text(_field_property(widget, "/T"))

                if not name:
                    continue

                value = _pdf_value_to_text(_field_property(widget, "/V"))
                field_type = _pdf_value_to_text(_field_property(widget, "/FT"))
                rectangle = _rectangle_from_widget(widget)
                field_identity = (
                    name,
                    page_number,
                    rectangle,
                )

                if field_identity in seen_fields:
                    continue

                seen_fields.add(field_identity)
                extracted_fields.append(
                    PdfFormField(
                        name=name,
                        value=value,
                        field_type=field_type,
                        page_number=page_number,
                        rectangle=rectangle,
                    )
                )
            except (
                AttributeError,
                KeyError,
                TypeError,
                ValueError,
            ):
                continue

    return tuple(extracted_fields)


def _validate_pdf_bytes(
    pdf_bytes: bytes,
    *,
    max_size_bytes: int,
) -> None:
    if not pdf_bytes:
        raise InvalidPdfError("The uploaded PDF is empty.")

    if len(pdf_bytes) > max_size_bytes:
        raise OversizedPdfError("The uploaded PDF exceeds the allowed file size.")

    if not pdf_bytes.lstrip().startswith(PDF_FILE_SIGNATURE):
        raise InvalidPdfError("The uploaded file is not a valid PDF.")


def extract_pdf_text(
    pdf_bytes: bytes,
    *,
    max_size_bytes: int = DEFAULT_MAX_PDF_SIZE_BYTES,
) -> PdfTextExtractionResult:
    _validate_pdf_bytes(
        pdf_bytes,
        max_size_bytes=max_size_bytes,
    )

    try:
        reader = PdfReader(BytesIO(pdf_bytes))
    except (PdfReadError, OSError, ValueError) as error:
        raise InvalidPdfError("The uploaded PDF could not be read.") from error

    if reader.is_encrypted:
        raise EncryptedPdfError("Encrypted PDFs are not supported.")
    form_fields = _extract_form_fields(reader)

    page_texts: list[str] = []

    try:
        for page in reader.pages:
            page_texts.append(_normalize_page_text(page.extract_text()))
    except (PdfReadError, OSError, ValueError, KeyError) as error:
        raise InvalidPdfError(
            "Text could not be extracted from the uploaded PDF."
        ) from error

    combined_text = "\n\n".join(page_text for page_text in page_texts if page_text)

    usable_character_count = sum(
        1 for character in combined_text if character.isalnum()
    )

    return PdfTextExtractionResult(
        page_count=len(reader.pages),
        page_texts=tuple(page_texts),
        combined_text=combined_text,
        has_usable_text=(usable_character_count >= MINIMUM_USABLE_TEXT_CHARACTERS),
        form_fields=form_fields,
    )

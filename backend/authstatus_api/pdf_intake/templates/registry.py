from __future__ import annotations

from collections.abc import Callable

from authstatus_api.pdf_intake.extractor import (
    PdfTextExtractionResult,
)
from authstatus_api.pdf_intake.templates.models import (
    PdfTemplateExtraction,
    empty_pdf_template_extraction,
)
from authstatus_api.pdf_intake.templates.standard_vob import (
    parse_standard_vob,
)

PdfTemplateParser = Callable[
    [PdfTextExtractionResult],
    PdfTemplateExtraction,
]

PDF_TEMPLATE_PARSERS: tuple[PdfTemplateParser, ...] = (parse_standard_vob,)


def parse_pdf_intake(
    result: PdfTextExtractionResult,
) -> PdfTemplateExtraction:
    for parser in PDF_TEMPLATE_PARSERS:
        extraction = parser(result)

        if extraction.is_match:
            return extraction

    return empty_pdf_template_extraction()

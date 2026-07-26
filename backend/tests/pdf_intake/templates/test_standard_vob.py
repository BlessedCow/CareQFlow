from authstatus_api.pdf_intake.extractor import (
    PdfFormField,
    PdfTextExtractionResult,
)
from authstatus_api.pdf_intake.templates.models import (
    ExtractionConfidence,
    ExtractionSource,
)
from authstatus_api.pdf_intake.templates.standard_vob import (
    STANDARD_VOB_TEMPLATE_ID,
    is_standard_vob,
    parse_standard_vob,
)

BLANK_STANDARD_VOB_TEXT = """
ADMIT DATE RANGE: NUMBER OF ADMIT:
FACILITY: CALLER:
PATIENT INFORMATION
PATIENT:
DOB: GENDER:
INSURANCE INFORMATION
INSURANCE COMPANY: PHONE NUMBER:
MEDICAL ID#: MEDICAL GROUP#: BH ID#: BH GROUP#:
PHONE NUMBER FOR AUTHORIZATION: NO AUTH PENALTY:
"""


def make_result(
    *,
    text: str = BLANK_STANDARD_VOB_TEXT,
    form_fields: tuple[PdfFormField, ...] = (),
) -> PdfTextExtractionResult:
    return PdfTextExtractionResult(
        page_count=1,
        page_texts=(text,),
        combined_text=text,
        has_usable_text=True,
        form_fields=form_fields,
    )


def form_field(
    name: str,
    value: str,
) -> PdfFormField:
    return PdfFormField(
        name=name,
        value=value,
        field_type="Tx",
        page_number=1,
        rectangle=None,
    )


def test_detects_standard_vob_from_embedded_labels():
    assert is_standard_vob(make_result()) is True


def test_rejects_unrecognized_pdf():
    result = make_result(
        text="Unrelated insurance document",
    )

    extraction = parse_standard_vob(result)

    assert extraction.is_match is False
    assert extraction.template_id is None
    assert extraction.facility is None


def test_extracts_known_fillable_form_fields():
    result = make_result(
        form_fields=(
            form_field(
                "text_1tgth",
                "01/15/2030 - 01/15/2030",
            ),
            form_field("text_2mfsh", "Example Facility"),
            form_field("text_4cvll", "Test Patient"),
            form_field("text_5vani", "01/02/1990"),
            form_field(
                "text_18cnrm",
                "Example Health Plan",
            ),
            form_field("text_19jkwv", "844-555-0101"),
            form_field(
                "text_27yesv",
                "TEST-MED-12345",
            ),
            form_field(
                "text_26rjsk",
                "TEST-GROUP-100",
            ),
            form_field(
                "text_25attw",
                "TEST-BH-67890",
            ),
            form_field(
                "text_23ikpt",
                "TEST-BH-GROUP-200",
            ),
            form_field("text_47lxxj", "800-555-0100"),
        ),
    )

    extraction = parse_standard_vob(result)

    assert extraction.is_match is True
    assert extraction.template_id == STANDARD_VOB_TEMPLATE_ID

    assert extraction.facility is not None
    assert extraction.facility.value == "Example Facility"
    assert extraction.facility.source == ExtractionSource.FORM_FIELD

    assert extraction.medical_member_id is not None
    assert extraction.medical_member_id.value == "TEST-MED-12345"

    assert extraction.authorization_phone is not None
    assert extraction.authorization_phone.value == "800-555-0100"

    assert extraction.facility.confidence == ExtractionConfidence.HIGH
    assert extraction.facility.needs_review is False

    assert extraction.patient_dob is not None
    assert extraction.patient_dob.confidence == ExtractionConfidence.HIGH
    assert extraction.patient_dob.needs_review is False


def test_resolves_same_behavioral_health_identifiers():
    result = make_result(
        form_fields=(
            form_field("text_27yesv", "TEST-MED-12345"),
            form_field("text_26rjsk", "TEST-GROUP-100"),
            form_field("text_25attw", "SAME"),
            form_field("text_23ikpt", "SAME"),
        ),
    )

    extraction = parse_standard_vob(result)

    assert extraction.medical_member_id is not None
    assert extraction.behavioral_health_member_id is not None
    assert extraction.behavioral_health_member_id.value == "TEST-MED-12345"

    assert extraction.medical_group_number is not None
    assert extraction.behavioral_health_group_number is not None
    assert extraction.behavioral_health_group_number.value == "TEST-GROUP-100"


def test_ignores_placeholder_values():
    result = make_result(
        form_fields=(
            form_field("text_2mfsh", "N/A"),
            form_field("text_19jkwv", "-"),
            form_field("text_27yesv", "NONE"),
            form_field("text_26rjsk", "N A"),
        ),
    )

    extraction = parse_standard_vob(result)

    assert extraction.facility is None
    assert extraction.insurance_phone is None
    assert extraction.medical_member_id is None
    assert extraction.medical_group_number is None


def test_same_identifier_without_medical_fallback_is_not_extracted():
    result = make_result(
        form_fields=(
            form_field("text_25attw", "SAME"),
            form_field("text_23ikpt", "SAME"),
        ),
    )

    extraction = parse_standard_vob(result)

    assert extraction.behavioral_health_member_id is None
    assert extraction.behavioral_health_group_number is None


def test_uses_embedded_text_without_form_fields():
    text = """
ADMIT DATE RANGE: 01/15/2030 - 01/15/2030 NUMBER OF ADMIT: 1
FACILITY: Example Recovery Center CALLER: Test Caller
PATIENT INFORMATION
PATIENT: Test Patient
DOB: 01/02/1990 GENDER: Male
INSURANCE INFORMATION
INSURANCE COMPANY: Example Health Plan PHONE NUMBER: 844-555-0101
MEDICAL ID#: TEST-MED-12345 MEDICAL GROUP#: TEST-GROUP-100
BH ID#: TEST-BH-67890 BH GROUP#: TEST-BH-GROUP-200
PHONE NUMBER FOR AUTHORIZATION: 800-555-0100 NO AUTH PENALTY: No
"""

    extraction = parse_standard_vob(
        make_result(text=text),
    )

    assert extraction.is_match is True

    assert extraction.facility is not None
    assert extraction.facility.value == "Example Recovery Center"
    assert extraction.facility.source == ExtractionSource.EMBEDDED_TEXT

    assert extraction.patient_dob is not None
    assert extraction.patient_dob.value == "01/02/1990"
    assert extraction.patient_dob.confidence == ExtractionConfidence.MEDIUM
    assert extraction.patient_dob.needs_review is True

    assert extraction.medical_member_id is not None
    assert extraction.medical_member_id.value == "TEST-MED-12345"

    assert extraction.authorization_phone is not None
    assert extraction.authorization_phone.value == "800-555-0100"


def test_form_field_takes_priority_over_text():
    text = BLANK_STANDARD_VOB_TEXT.replace(
        "FACILITY: CALLER:",
        "FACILITY: Text Facility CALLER:",
    )
    result = make_result(
        text=text,
        form_fields=(
            form_field(
                "text_2mfsh",
                "Form Facility",
            ),
        ),
    )

    extraction = parse_standard_vob(result)

    assert extraction.facility is not None
    assert extraction.facility.value == "Form Facility"
    assert extraction.facility.source == ExtractionSource.FORM_FIELD


def test_text_fills_blank_form_value():
    text = BLANK_STANDARD_VOB_TEXT.replace(
        "DOB: GENDER:",
        "DOB: 01/02/1990 GENDER:",
    )
    result = make_result(
        text=text,
        form_fields=(form_field("text_5vani", ""),),
    )

    extraction = parse_standard_vob(result)

    assert extraction.patient_dob is not None
    assert extraction.patient_dob.value == "01/02/1990"
    assert extraction.patient_dob.source == ExtractionSource.EMBEDDED_TEXT


def test_text_fills_missing_fields_while_form_values_remain():
    text = BLANK_STANDARD_VOB_TEXT.replace(
        "DOB: GENDER:",
        "DOB: 01/02/1990 GENDER:",
    )
    result = make_result(
        text=text,
        form_fields=(
            form_field(
                "text_2mfsh",
                "Form Facility",
            ),
        ),
    )

    extraction = parse_standard_vob(result)

    assert extraction.facility is not None
    assert extraction.facility.value == "Form Facility"
    assert extraction.facility.source == ExtractionSource.FORM_FIELD

    assert extraction.patient_dob is not None
    assert extraction.patient_dob.value == "01/02/1990"
    assert extraction.patient_dob.source == ExtractionSource.EMBEDDED_TEXT


def test_blank_template_does_not_invent_values():
    extraction = parse_standard_vob(make_result())

    assert extraction.is_match is True
    assert extraction.template_id == STANDARD_VOB_TEMPLATE_ID
    assert extraction.admit_date_range is None
    assert extraction.facility is None
    assert extraction.patient_name is None
    assert extraction.patient_dob is None
    assert extraction.insurance_company is None
    assert extraction.insurance_phone is None
    assert extraction.medical_member_id is None
    assert extraction.medical_group_number is None
    assert extraction.behavioral_health_member_id is None
    assert extraction.behavioral_health_group_number is None
    assert extraction.authorization_phone is None


def test_normalizes_form_field_whitespace():
    result = make_result(
        form_fields=(
            form_field(
                "text_2mfsh",
                "  Example    Facility  ",
            ),
        ),
    )

    extraction = parse_standard_vob(result)

    assert extraction.facility is not None
    assert extraction.facility.value == "Example Facility"

# PDF Intake

CareQueue includes a local PDF-assisted intake workflow for supported verification-of-benefits documents.

The workflow reduces repetitive entry, but it does not treat the PDF as authoritative. CareQueue extracts candidate values, identifies the source of each candidate, assigns confidence, and requires user review before values are copied into the authorization form.

Current supported template family:

```text
standard_vob_v1
```

Other layouts may upload successfully but produce no mapped values.

## Scope

PDF intake is a preview-and-review workflow.

It can:

- Accept a PDF from the add-authorization form
- Read fillable PDF fields
- Read embedded page text
- Match supported templates
- Extract supported candidate values
- Report each candidate source
- Assign candidate confidence
- Mark uncertain values for review
- Let the user edit extracted values before applying them
- Let the user choose medical or behavioral-health identifiers
- Warn when extracted facility or insurance values are not registered options
- Record a limited audit event for successful previews

It does not:

- Create an authorization automatically
- Guarantee extracted values are correct
- Store the uploaded PDF with the authorization
- Store extracted page text
- Perform OCR
- Support encrypted PDFs
- Support every document layout
- Add unknown facilities or insurers automatically
- Choose the correct identifier pair without user review
- Replace payer, portal, or source-document verification

## Access

Preview endpoint:

```text
POST /api/pdf-intake/preview
```

Allowed roles:

```text
Admin
UR
```

Read Only users cannot preview PDFs.

PDF intake is a protected application workflow. The user must have an active authenticated session, satisfy the current governance requirement, and have a role permitted to use the preview endpoint.

Because preview is a state-changing authenticated request, the browser client also supplies the required CSRF protection.

## Request Format

The frontend sends the PDF as the raw request body.

Required content type:

```text
application/pdf
```

The endpoint does not use multipart form upload.

The request and response use no-store caching behavior.

## File Size Limit

Maximum size:

```text
10 MiB
```

The backend checks both declared length and streamed bytes.

Oversized requests return:

```text
413 Request Entity Too Large
```

## Processing and Persistence

The current preview workflow processes the PDF in memory through an isolated extraction worker.

The worker has timeout handling so a stalled parser can be terminated without blocking the API process indefinitely.

It does not write the uploaded document to the CareQueue database or a permanent upload directory.

Operators must still account for browser behavior, proxy limits, crash dumps, endpoint security, operating-system protections, and infrastructure logging.

Do not add request-body logging around the PDF endpoint, and do not log extracted page text or candidate values.

## Validation

CareQueue checks that:

1. The request is not empty.
2. The file is within the size limit.
3. The bytes begin with `%PDF-`.
4. The PDF can be parsed.
5. The document is not encrypted.

Common responses:

```text
415 The request must contain a PDF.
422 The uploaded PDF could not be read.
422 Encrypted PDFs are not supported.
422 The uploaded PDF could not be processed.
422 The uploaded PDF could not be processed in time.
```

Internal parser details should not be returned to the client.

## Extraction Sources

Candidate source values:

```text
form_field
embedded_text
```

### Fillable fields

Recognized fillable fields are currently assigned:

```text
Confidence: high
Needs review: false
```

High confidence still requires the user to verify the value before applying it.

### Embedded text

Recognized embedded-text values are currently assigned:

```text
Confidence: medium
Needs review: true
```

Embedded text is more sensitive to layout order, line breaks, and PDF-generation differences.

## Usable Text

CareQueue considers embedded text usable when it contains at least:

```text
20 alphanumeric characters
```

When the threshold is not met:

```text
has_usable_text: false
```

A PDF may still contain usable fillable fields even when embedded text is limited.

## Scanned PDFs

The current pipeline does not perform OCR.

Image-only scanned documents may produce:

- No template match
- No usable text
- Few or no candidates
- A requirement for manual entry

An empty preview means the current extraction method found no mapped values. It does not mean the document contains no information.

## Supported Template

Current template ID:

```text
standard_vob_v1
```

The parser expects stable labels such as:

```text
ADMIT DATE RANGE:
FACILITY:
PATIENT INFORMATION
INSURANCE COMPANY:
MEDICAL ID#:
PHONE NUMBER FOR AUTHORIZATION:
```

All required match signals must be present. A similar document with different labels may not match.

## Candidate Fields

The preview may return:

```text
facility
client_name
admit_date_range
date_of_birth
insurance
insurance_phone
authorization_phone
medical_member_id
medical_group_number
behavioral_health_member_id
behavioral_health_group_number
```

The review panel applies these reviewed values to the authorization form when available:

```text
clientName
memberId
groupNumber
dateOfBirth
facility
startDate
insurance
phoneNumber
```

`insurance_phone` may be returned for review, but the review panel applies `authorization_phone` to the authorization phone field.

## Candidate Structure

Example:

```json
{
  "value": "Example value",
  "source": "form_field",
  "confidence": "high",
  "needs_review": false
}
```

Allowed confidence values:

```text
high
medium
low
```

## Empty Values

The parser ignores values that normalize to:

```text
-
N/A
N A
NA
NONE
NOT APPLICABLE
```

Whitespace-only values are also ignored.

Missing values appear in the review panel as:

```text
Not extracted. Review required.
```

## Identifier Handling

The preview can surface separate medical and behavioral-health identifiers.

The user chooses one of:

```text
Behavioral health identifiers
Medical identifiers
Do not apply a member ID or group number
```

Initial selection order:

1. Behavioral-health pair when either behavioral-health candidate exists
2. Medical pair when either medical candidate exists
3. No pair when neither pair exists

Only the selected pair is copied into the authorization form.

### `SAME` rule

When a document uses:

```text
SAME
```

for behavioral-health identifiers, the parser copies the corresponding medical identifier when available.

Example:

```text
Medical ID: MED-123
BH ID: SAME
```

Result:

```text
Behavioral-health member ID: MED-123
```

The user must still choose which identifier pair to apply.

## Review Panel

The review panel allows editing of:

- Client name
- Date of birth
- Facility
- Initial admit date
- Insurance
- Authorization phone
- Medical member ID
- Medical group number
- Behavioral-health member ID
- Behavioral-health group number

The panel instructs the user to verify every value before applying it.

## Review-Required Confirmation

When any candidate has:

```text
needs_review: true
```

the panel requires the user to confirm:

```text
I reviewed the fields marked as needing review and confirmed or corrected their values.
```

Until checked, `Apply to authorization` remains disabled.

## Date Handling

The review panel accepts:

```text
YYYY-MM-DD
M/D/YYYY
MM/DD/YYYY
```

For admit-date ranges, it applies the first recognized date as the initial admit date.

The user must confirm that this is the actual original admit date.

## Registered Facility and Insurance Matching

CareQueue attempts to match extracted facility and insurance values against registered options.

When no match exists, the value is not added automatically. The user must select an existing value, correct the extracted value, or ask an Admin to add the approved option.

See [Registered Options](../administration/registered-options.md).

## Authorization Phone

The review panel applies `authorization_phone`, not `insurance_phone`.

Confirm that the number is the correct authorization contact and not merely the general insurance line.

## Cancel and Clear

Before preview, `Clear` removes the selected file or upload error.

During review, `Cancel PDF intake` discards the preview.

Canceling does not remove values already entered manually in the authorization form.

After applying values, the preview state and file input are cleared.

## Applying Values

`Apply to authorization` copies reviewed values into the ordinary add-authorization form.

It does not submit the authorization.

Only nonempty reviewed values are applied.

The ordinary form remains editable and runs final validation on submission.

## Audit Event

Successful preview records:

```text
pdf_intake.preview
```

Current metadata includes:

```text
template_matched
candidate_count
has_usable_text
```

It does not include PDF bytes, extracted text, candidate values, patient identifiers, or authorization data.

The audit event participates in CareQueue's normal application audit pipeline. See [Audit Log](../administration/audit-log.md) for audit-chain and integrity-verification behavior.

## Local Inspection Tool

Development utility:

```text
backend/scripts/inspect_pdf_intake.py
```

From `backend`:

```powershell
python scripts\inspect_pdf_intake.py `
    "..\local_vobs\example.pdf"
```

Include normalized embedded text only when necessary:

```powershell
python scripts\inspect_pdf_intake.py `
    "..\local_vobs\example.pdf" `
    --show-text
```

The tool prints document-derived information to the terminal.

Use synthetic or approved stripped PDFs. Do not place real output in public issues, repository files, screenshots, or recorded terminals.

## Adding a Template

Template modules belong under:

```text
backend/authstatus_api/pdf_intake/templates/
```

Tests belong under:

```text
backend/tests/pdf_intake/templates/
```

A new parser should define:

- Stable template ID
- Reliable match criteria
- Fillable-field mappings when available
- Embedded-text fallbacks
- Empty-value handling
- Candidate confidence
- Review requirements
- Identifier fallback behavior
- Positive and false-match tests

Keep unrelated layouts in separate modules.

False-positive matches are more dangerous than requiring manual entry.

## Confidence Guidance

### High

Use for stable, recognized fillable-field mappings.

### Medium

Use for labeled embedded-text extraction from a matched template.

Set:

```text
needs_review: true
```

### Low

Use for weak or heuristic matches.

When uncertainty is too high, return no candidate.

## Conflict Priority

The current parser prefers:

```text
1. Meaningful recognized form-field value
2. Embedded-text value
3. No candidate
```

Future conflict handling should surface competing values rather than silently choosing between equally strong candidates.

## Testing Expectations

PDF intake tests should cover:

- File signature
- Empty request
- Wrong content type
- Oversized request
- Invalid PDF
- Encrypted PDF
- Extraction timeout
- Text normalization
- Form-field extraction
- Template matching
- Embedded-text fallback
- Placeholder values
- Identifier fallback
- False-positive prevention
- Role access
- Governance enforcement
- CSRF protection
- No-store headers
- Safe error messages
- Safe audit metadata
- Review behavior
- Registered-option matching

Use synthetic fixtures only.

Do not create fixtures by partially redacting a real document.

## Common Problems

### No values appear

Possible causes:

- Template did not match
- Document is scanned
- Embedded text is missing
- Fillable fields use unknown names
- Labels changed
- Document is a different layout

An empty preview should be treated as a request for manual review, not as evidence that the source document contains no relevant information.

### Dates do not appear

The current review panel recognizes:

```text
YYYY-MM-DD
M/D/YYYY
MM/DD/YYYY
```

Other formats require manual correction.

### Facility or insurance is not applied

The value did not match a registered option.

Correct it, select an existing option, or add the approved value in Settings.

### Wrong identifier pair is selected

Choose the medical pair, behavioral-health pair, or no pair after comparing both with the source document.

### 403 response

A `403` can indicate that:

- The current role is not allowed to use PDF intake.
- CSRF validation failed for the authenticated request.
- A required password-change state is still active.

Confirm the signed-in role, session state, and browser request path before retrying.

### 428 Governance attestation required

The user is authenticated, but the current organization governance attestation has not been completed.

An Admin must complete the current governance requirement before PDF intake and other normal protected workflows become available.

### 413 response

The PDF exceeds 10 MiB.

### 415 response

The request was not sent as `application/pdf`.

### 422 encrypted PDF

Use an approved unencrypted source only when policy permits.

## Future OCR

Local OCR may be considered for image-only documents.

Before adding OCR, evaluate:

- Telemetry
- Network requests
- Automatic model downloads
- Temporary file handling
- Logging
- Crash-report content
- Licensing
- Platform support
- Resource use
- Accuracy
- Review behavior

OCR output must remain review-first and must not be treated as automatically correct.

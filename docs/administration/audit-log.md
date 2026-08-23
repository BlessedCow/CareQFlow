# Audit Log

CareQueue records selected security, governance, authorization, document, timeline, user-management, registered-option, PDF-intake, backup, and recovery activity in an application audit log.

The audit log supports accountability, operational review, and investigation. It is application-managed evidence and should be used alongside operating-system logs, deployment records, organizational access records, and any external monitoring required by the deployment.

CareQueue also maintains a tamper-evident cryptographic hash chain for current audit events and provides an Admin-only integrity verification action.

## Access

The Audit Log is available only to:

```text
Admin
```

The backend endpoints are also Admin-protected.

Frontend navigation is not the security boundary. Backend authorization remains authoritative.

## Audit Event Endpoint

```text
GET /api/security/audit-events
```

Supported query parameters:

```text
page
page_size
action
username
```

Defaults:

```text
page: 1
page_size: 50
```

Limits:

```text
page >= 1
1 <= page_size <= 200
```

The current frontend requests 25 events per page.

## Integrity Verification Endpoint

```text
POST /api/security/audit-events/verify-integrity
```

This endpoint verifies the current cryptographic audit chain and returns:

```text
valid
status
checked_events
legacy_events
failed_event_id
reason
```

Possible status values are:

```text
valid
invalid
not_initialized
```

Integrity verification is itself audited when CareQueue is able to append the verification event safely.

## Event Structure

Each audit event returned through the API includes:

```text
id
user_id
username
action
resource_type
resource_id
metadata
ip_address
user_agent
created_at
```

Example:

```json
{
  "id": 42,
  "user_id": 3,
  "username": "ur.user@example.invalid",
  "action": "auth.update",
  "resource_type": "authorization",
  "resource_id": 18,
  "metadata": "{\"fields\":[\"status\"]}",
  "ip_address": "127.0.0.1",
  "user_agent": "Mozilla/5.0 ...",
  "created_at": "2030-01-15T18:20:14+00:00"
}
```

`metadata` is stored and returned as a JSON string. The frontend attempts to parse and display it as formatted JSON.

The API does not expose internal audit-chain hash fields as part of the normal Audit Log event response.

## Storage

Audit events are stored in:

```text
audit_events
```

Current columns include:

```text
id
user_id
username
action
resource_type
resource_id
metadata
ip_address
user_agent
created_at
previous_hash
event_hash
```

Audit-chain head state is stored separately in:

```text
audit_chain_state
```

The `user_id` foreign key uses:

```text
ON DELETE SET NULL
```

The recorded username remains available even when the user reference is no longer present.

## Tamper-Evident Audit Chain

Current audit events are linked through cryptographic hashes.

For each chained event, CareQueue:

1. Reads and validates the current audit-chain head state.
2. Uses the prior event hash as the new event's `previous_hash`.
3. Inserts the event.
4. Computes the event hash from the event's stored fields and prior hash.
5. Stores the resulting `event_hash`.
6. Updates the protected chain-head state.

The first chained event uses the defined audit-chain genesis value as its previous hash.

Before appending a new event, CareQueue checks that the stored chain-head state matches the current head event. If the chain state or head is inconsistent, the audit writer refuses to append the new event.

The integrity verifier checks:

- The chain-state integrity value.
- Every `previous_hash` link.
- Every event hash.
- The relationship between the final event and the recorded chain head.

A failed verification identifies the first failed event when one can be determined.

### Legacy Events

Databases upgraded from an earlier CareQueue version may contain audit events created before cryptographic chaining was introduced.

Those records can have:

```text
event_hash = NULL
```

Integrity verification reports the count of these records as:

```text
legacy_events
```

Legacy events are not retroactively rewritten into the current cryptographic chain.

## What Tamper-Evident Means

The audit hash chain is designed to detect changes to chained audit records and chain state when CareQueue later verifies or appends to the chain.

It does not make the database write-once or immune to a fully privileged attacker who can modify the application, database, secrets, backups, and host state together.

Deployments requiring independent or immutable evidence should export or forward approved security records to an external system designed for that purpose.

## Ordering and Pagination

Events are returned newest first.

The frontend shows:

```text
Page <current> of <total>
```

with:

```text
Previous
Next
```

The table displays:

```text
Time
User
Action
Resource
Metadata
IP address
```

The event model also contains `user_agent`, but the current table does not display it as a separate column.

## Time Display

Audit timestamps are stored as UTC ISO values.

The frontend renders them using the reviewing browser's local date, time, locale, and time zone.

For investigations, preserve the original stored timestamp and record the reviewer's local time zone.

## Filters

The Audit Log supports:

```text
Action
Username
```

Both use case-insensitive substring matching.

For example:

```text
auth
```

can match actions such as:

```text
auth.create
auth.update
auth.delete
auth_event.create
auth_document.create
```

CareQueue escapes SQL wildcard characters before constructing the search pattern.

## Current Action Names

The following action names are produced by the current implementation.

### Security, login, MFA, and sessions

```text
security.initial_admin_setup
security.login
security.login_failed
security.login_locked
security.login_trusted_device
security.login_mfa_required
security.login_mfa_challenge_invalid
security.login_mfa_failed
security.login_mfa_verified
security.logout
security.password_change
security.mfa_enrollment_password_failed
security.mfa_enrollment_started
security.mfa_enrollment_verification_failed
security.mfa_enabled
security.trusted_device_created
security.trusted_devices_revoked
security.audit_integrity_verified
```

### Governance

```text
governance.attestation_accepted
```

### User administration

```text
user.create
user.update
user.password_reset
user.mfa_reset
```

### Authorizations

```text
auth.create
auth.update
auth.delete
```

### Authorization documents

```text
auth_document.create
auth_document.download
auth_document.delete
```

### Timeline events

```text
auth_event.create
auth_event.update
auth_event.delete
```

### Registered options

```text
registered_option.create
registered_option.delete
```

### PDF intake

```text
pdf_intake.preview
```

### Backups

```text
backup.create
backup.verify
backup.verify_failed
```

### Recovery

```text
recovery.stage
recovery.stage_failed
recovery.cancel
```

This list reflects the current application implementation.

## Metadata Rules

Audit metadata is serialized as JSON with sorted keys.

When no metadata is supplied, CareQueue stores:

```json
{}
```

Update-style workflows generally record field names or bounded operational information rather than sensitive field values.

Example:

```json
{
  "fields": [
    "status"
  ]
}
```

This identifies what part of a record changed without copying the old or new value into the audit record.

## Event Details by Workflow

### Initial Admin Setup

Initial Admin setup records:

```text
security.initial_admin_setup
```

The event is written when the one-time bootstrap endpoint creates the first Admin user.

The supplied password and password hash are not included.

### Successful and Failed Login

Successful authenticated login records:

```text
security.login
```

The current event metadata includes the number of prior active sessions revoked as part of single-session enforcement.

Failed password login records:

```text
security.login_failed
```

Temporary account lockout attempts record:

```text
security.login_locked
```

Failed-login and lockout events retain the normalized username associated with the attempt when available.

The client still receives a generic authentication error for an invalid username or password.

### MFA Login

When a password is correct but TOTP MFA is still required:

```text
security.login_mfa_required
```

Successful MFA verification records:

```text
security.login_mfa_verified
```

Invalid TOTP verification records:

```text
security.login_mfa_failed
```

An invalid or expired MFA challenge records:

```text
security.login_mfa_challenge_invalid
```

MFA codes, MFA secrets, and raw challenge tokens are not stored in audit metadata.

### Remembered-Device Login

When a valid remembered-device token satisfies the MFA step:

```text
security.login_trusted_device
```

Creating a remembered device after successful MFA verification records:

```text
security.trusted_device_created
```

Revoking remembered devices records:

```text
security.trusted_devices_revoked
```

Current trusted-device metadata may include safe operational information such as the trusted-device expiration time or the number of records revoked.

Raw remembered-device tokens are not included.

### MFA Enrollment

Enrollment started:

```text
security.mfa_enrollment_started
```

Current-password failure during enrollment:

```text
security.mfa_enrollment_password_failed
```

Invalid TOTP confirmation during enrollment:

```text
security.mfa_enrollment_verification_failed
```

Successful MFA enablement:

```text
security.mfa_enabled
```

The MFA secret and TOTP codes are not included in audit metadata.

### Password Activity

Password change:

```text
security.password_change
```

Current metadata includes bounded counts such as:

```text
sessions_revoked
trusted_devices_revoked
```

Administrative password reset:

```text
user.password_reset
```

Current metadata includes:

```text
sessions_revoked
trusted_devices_revoked
must_change_password
```

Passwords, temporary passwords, and password hashes are not included.

### User Management

Create user:

```text
user.create
```

Current metadata includes safe account-management information such as:

```text
role
must_change_password
```

Update user:

```text
user.update
```

Metadata identifies changed field names and may include bounded revocation counts produced by security-sensitive changes.

Administrative MFA reset:

```text
user.mfa_reset
```

Current metadata includes:

```text
sessions_revoked
trusted_devices_revoked
```

### Governance Attestation

Accepted organization governance attestation:

```text
governance.attestation_accepted
```

The event uses:

```text
resource_type: governance_attestation
resource_id: <accepted attestation record>
```

Current safe metadata includes:

```text
attestation_version
deployment_mode
app_version
```

The organization name is intentionally not copied into audit metadata.

The full governance attestation record, including organization and accepting user information, is maintained in the governance attestation history rather than duplicated in the audit metadata.

### Authorization Records

Create:

```text
auth.create
```

Update:

```text
auth.update
```

Delete:

```text
auth.delete
```

Create and update events identify submitted field names rather than copying sensitive field values.

### Authorization Documents

Document upload:

```text
auth_document.create
```

Document download:

```text
auth_document.download
```

Document deletion:

```text
auth_document.delete
```

These events identify the relevant authorization/document resources without placing document bytes or document contents into audit metadata.

### Timeline Events

```text
auth_event.create
auth_event.update
auth_event.delete
```

Metadata may include:

```text
auth_id
fields
```

Timeline notes and other sensitive values should not be copied into audit metadata.

### Registered Options

```text
registered_option.create
registered_option.delete
```

Current metadata includes bounded category information rather than arbitrary record contents.

### PDF Intake

```text
pdf_intake.preview
```

Current metadata includes:

```text
template_matched
candidate_count
has_usable_text
```

It does not include:

- Uploaded PDF bytes
- Extracted PDF text
- Extracted patient values
- Candidate field contents

### Backup and Recovery

Backup actions:

```text
backup.create
backup.verify
backup.verify_failed
```

Recovery actions:

```text
recovery.stage
recovery.stage_failed
recovery.cancel
```

Recovery activation is performed through the separate recovery process. Application audit events cover the application-side staging, verification, and cancellation workflows implemented by CareQueue.

### Audit Integrity Verification

An Admin integrity check records:

```text
security.audit_integrity_verified
```

when the result can be appended safely.

Current metadata includes:

```text
valid
status
checked_events
legacy_events
failed_event_id
```

If the audit chain is already damaged in a way that prevents the writer from safely appending a new event, CareQueue returns the verification result without forcing an additional audit write.

## Prohibited Audit Content

Audit metadata must not contain:

- Passwords
- Temporary passwords
- Password hashes
- MFA secrets
- TOTP codes
- Raw MFA challenge tokens
- Raw remembered-device tokens
- Session tokens
- CSRF tokens
- Authentication cookies
- Encryption keys
- Environment-file secrets
- Full request or response bodies
- Patient names
- Dates of birth
- Member IDs
- Group numbers
- Authorization numbers
- Clinical notes
- Extracted PDF text
- PDF bytes
- Portal credentials
- Decrypted database values

Prefer resource IDs, field names, bounded counts, status values, and other non-sensitive operational metadata.

## IP Address and User Agent

The audit service records the request client address and user-agent header when available.

These values provide context but are not definitive proof of identity.

IP accuracy depends on:

- Reverse-proxy behavior
- Trusted proxy configuration
- Network topology
- Shared networks
- VPN use

User-agent values are supplied by the client and may be incomplete or spoofed.

## Audit Log Versus Service Logs

Audit records describe selected user and application actions.

Examples:

```text
A user logged in
An MFA verification failed
A governance attestation was accepted
An authorization was updated
A document was downloaded
A backup was verified
```

Operational logs describe service behavior and failures.

Examples:

```text
Service startup
Dependency failure
Database connection error
Caddy configuration error
Installer failure
```

Not every operational failure appears in the application audit log.

## Review Workflow

A practical audit review:

1. Define the review period and purpose.
2. Review newest events first.
3. Filter by action for a workflow investigation.
4. Filter by username for a user review.
5. Review safe metadata and resource references.
6. Compare events with approved access, administrative, or deployment changes.
7. Verify audit integrity when appropriate.
8. Review operational logs when needed.
9. Preserve findings through the organization's approved review process.
10. Escalate unexplained or suspicious activity.

## Useful Filters

Initial Admin setup:

```text
security.initial_admin_setup
```

Successful logins:

```text
security.login
```

Failed and locked logins:

```text
security.login_
```

MFA activity:

```text
mfa
```

Remembered-device activity:

```text
trusted_device
```

Password activity:

```text
password
```

Governance:

```text
governance
```

User administration:

```text
user.
```

Authorization activity:

```text
auth
```

Authorization documents:

```text
auth_document
```

PDF intake:

```text
pdf_intake
```

Backups:

```text
backup
```

Recovery:

```text
recovery
```

Audit integrity:

```text
audit_integrity
```

## Retention

Audit events are stored in the CareQueue database.

They therefore follow the database's:

- Backup lifecycle
- Restore lifecycle
- Recovery lifecycle
- Access controls
- Retention policy

The current implementation does not define automatic audit-event deletion through the application.

A database restore returns the audit log and audit-chain state to the state contained in the selected backup.

Events created after that backup may remain only in rollback files, safety backups, external logs, or other retained evidence.

Organizations should define audit retention requirements based on applicable contractual, legal, regulatory, and operational needs.

## Integrity Scope and Limitations

CareQueue provides cryptographic chaining and an integrity-verification workflow for current chained audit events.

The audit system is not currently:

- Write-once storage
- Stored in an independent immutable external system
- Automatically forwarded to a SIEM
- Independently digitally signed by an external trust service
- Protected from a fully privileged host administrator who can alter the application, database, secrets, and surrounding system state together

The hash chain increases the ability to detect unauthorized modification within the protected application data set. It does not replace host security, backups, access control, centralized monitoring, or external immutable logging where those controls are required.

## Current Interface Limitations

The current Audit Log interface does not provide:

- Date-range filtering
- Resource-type filtering
- Resource-ID filtering
- IP-address filtering
- User-agent filtering
- CSV export
- Saved searches
- Alert rules
- Automatic archival

It supports action filtering, username filtering, pagination, refresh, and Admin-triggered integrity verification through the System/security administration workflow.

## Common Problems

### Audit Log is not visible

Confirm the current user has the Admin role and that current governance setup is complete.

### Events will not load

Check:

- The session is active.
- The user remains an Admin.
- Current governance requirements are satisfied.
- API readiness succeeds.
- The expected environment is open.
- The database is available.

### Filter returns no results

Try:

- Clearing filters.
- Using a shorter action substring.
- Checking username spelling.
- Reviewing adjacent pages.
- Confirming the workflow is currently audited.

### Expected event is missing

Possible reasons include:

- The operation is not audited.
- The request failed before the audit call.
- The event occurred on another installation or database.
- The database was restored.
- Current filters exclude it.

### Integrity status is `not_initialized`

No current cryptographically chained audit events exist yet.

This can occur on a database that contains no audit events or only legacy pre-chain events.

### Integrity verification reports legacy events

The database contains older audit records created before audit chaining was introduced.

The verifier reports those separately and verifies the current chained portion.

### Integrity verification reports `invalid`

Treat an invalid result as a security and integrity issue requiring investigation.

Preserve the current database and relevant backups before attempting corrective action.

Review:

- The reported failed event ID and reason.
- Recent application and operating-system changes.
- Database access.
- Restore or recovery activity.
- Service logs.
- Backup history.
- Administrative activity.

Do not delete or rewrite audit records merely to make an integrity check pass.

## Development Guidance

When adding an audited workflow:

1. Choose a stable action name.
2. Choose a clear resource type.
3. Include a resource ID when appropriate.
4. Use bounded, non-sensitive metadata.
5. Prefer field names over field values.
6. Pass the current user and request when available.
7. Add tests for event creation.
8. Add tests proving sensitive values are absent.
9. Confirm the action participates correctly in audit-chain creation.
10. Update this reference.

Recommended naming:

```text
domain.operation
```

Examples:

```text
auth.update
user.create
security.login_mfa_failed
governance.attestation_accepted
backup.verify
```

# Audit Log

CareQueue records selected security, authorization, timeline, user-management, registered-option, PDF-intake, backup, and recovery activity in an application audit log.

The audit log supports accountability and later review. It is not a complete SIEM, immutable evidence store, or organizational compliance record.

## Access

The Audit Log is available only to:

```text
Admin
```

The backend endpoint is also Admin-protected.

Frontend navigation is not the security boundary. The backend role check is authoritative.

## Endpoint

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

## Event Structure

Each event includes:

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

## Storage

Audit events are stored in:

```text
audit_events
```

Current columns:

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

The `user_id` foreign key uses:

```text
ON DELETE SET NULL
```

The recorded username remains available even when the user reference is unavailable.

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

The frontend renders them using the reviewing browser’s local date, time, locale, and time zone.

For investigations, preserve the original stored timestamp and record the reviewer’s local time zone.

## Filters

The Audit Log supports:

```text
Action
Username
```

Both use case-insensitive substring matching.

Examples:

```text
auth
```

may match:

```text
auth.create
auth.update
auth.delete
auth_event.create
auth_event.update
auth_event.delete
```

The service escapes SQL wildcard characters before constructing the search pattern.

## Current Action Names

### Security and sessions

```text
security.initial_admin_setup
security.login
security.login_failed
security.logout
security.password_change
```

### User administration

```text
user.create
user.update
user.password_reset
```

### Authorizations

```text
auth.create
auth.update
auth.delete
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

This list reflects the current implementation.

## Metadata Rules

Audit metadata is serialized as JSON with sorted keys.

When no metadata is supplied, CareQueue stores:

```json
{}
```

Update-style workflows generally record field names rather than field values.

Example:

```json
{
  "fields": [
    "status"
  ]
}
```

This shows what part of a record changed without copying the old or new value.

## Event Details by Workflow

### Initial Admin setup

Initial Admin setup:

```text
security.initial_admin_setup
```

Current metadata includes:

```text
role
```

The event is recorded when the one-time initial Admin setup endpoint creates the first Admin user.

It does not include the supplied password or password hash.

### Login

Successful login:

```text
security.login
```

Failed login:

```text
security.login_failed
```

Failed login records the normalized username supplied during the attempt when available.

The client still receives:

```text
Invalid username or password.
```

### Password activity

Password change:

```text
security.password_change
```

Current metadata includes:

```text
sessions_revoked
```

Administrative reset:

```text
user.password_reset
```

Current metadata includes:

```text
sessions_revoked
must_change_password
```

Passwords, temporary passwords, and password hashes are not included.

### User management

Create user:

```text
user.create
```

Current metadata includes:

```text
role
must_change_password
```

Update user:

```text
user.update
```

Metadata identifies changed field names such as:

```text
role
is_active
```

### Authorization records

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

### Timeline events

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

### Registered options

```text
registered_option.create
registered_option.delete
```

Current metadata includes safe category information.

### PDF intake

```text
pdf_intake.preview
```

Current metadata includes:

```text
template_matched
candidate_count
has_usable_text
```

It does not include extracted values, PDF bytes, or extracted text.

### Backup and recovery

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

Recovery activation is performed through a separate offline process. Application audit events cover staging and cancellation activity.

## Prohibited Audit Content

Audit metadata must not contain:

- Passwords
- Temporary passwords
- Password hashes
- Session tokens
- CSRF tokens
- Authentication cookies
- Encryption keys
- Environment variables
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

Prefer resource IDs and changed field names.

## IP Address and User Agent

The audit service records the request client address and user-agent header when available.

These values provide context but are not definitive identity proof.

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
An authorization was updated
A backup was verified
```

Operational logs describe service behavior and failures.

Examples:

```text
Service startup
Dependency failure
Database connection error
Caddy configuration error
```

Not every operational failure appears in the audit log.

## Review Workflow

A practical review:

1. Confirm the review period.
2. Review newest events first.
3. Filter by action for a workflow investigation.
4. Filter by username for a user review.
5. Review safe metadata.
6. Compare events with approved changes or access records.
7. Review operational logs when needed.
8. Record findings outside CareQueue.
9. Escalate unexplained or suspicious activity.

## Useful Filters

Initial Admin setup:

```text
security.initial_admin_setup
```

Successful logins:

```text
security.login
```

Failed logins:

```text
security.login_failed
```

Password activity:

```text
password
```

User administration:

```text
user.
```

Authorization activity:

```text
auth
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

## Retention

Audit events are stored in the CareQueue database.

They therefore follow the database’s:

- Backup lifecycle
- Restore lifecycle
- Recovery lifecycle
- Access controls
- Retention policy

The current implementation does not define automatic audit-event deletion.

A database restore returns the Audit Log to the state contained in the selected backup.

Events created after that backup may remain only in rollback files, safety backups, or external records.

## Integrity Limitations

The current audit log is application-managed and stored in the same database as application data.

It is not currently:

- Cryptographically chained
- Digitally signed
- Write-once
- Stored in an immutable external system
- Automatically forwarded to a SIEM
- Protected from a fully privileged host or database administrator

Higher-assurance deployments may require approved external immutable logging.

## Current Interface Limitations

The current Audit Log does not provide:

- Date-range filtering
- Resource-type filtering
- Resource-ID filtering
- IP-address filtering
- User-agent filtering
- CSV export
- Saved searches
- Alert rules
- Automatic archival

It supports action, username, pagination, and refresh.

## Common Problems

### Audit Log is not visible

Confirm the current user has the Admin role.

### Events will not load

Check:

- Session is active
- User remains an Admin
- API readiness succeeds
- Correct environment is open
- Database is available

### Filter returns no results

Try:

- Clearing filters
- Using a shorter action substring
- Checking username spelling
- Reviewing adjacent pages
- Confirming the workflow is currently audited

### Expected event is missing

Possible reasons:

- The operation is not audited
- The request failed before the audit call
- The event occurred on another instance
- The database was restored
- Current filters exclude it

## Development Guidance

When adding an audited workflow:

1. Choose a stable action name.
2. Choose a clear resource type.
3. Include a resource ID when appropriate.
4. Use safe metadata.
5. Prefer field names over values.
6. Pass the current user and request when available.
7. Add tests for event creation.
8. Add tests proving sensitive values are absent.
9. Update this reference.

Recommended naming:

```text
domain.operation
```

Examples:

```text
auth.update
user.create
backup.verify
```

## Related Documentation

```text
docs/administration/users-and-security.md
docs/operations/health-checks.md
docs/troubleshooting/index.md
docs/workflows/backup-and-recovery.md
SECURITY.md
```

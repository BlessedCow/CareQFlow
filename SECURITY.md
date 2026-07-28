# Security Policy

## Supported Use

CareQueue is a local-first healthcare workflow and authorization management project intended for private development, testing, and controlled deployment evaluation.

CareQueue includes technical safeguards intended to reduce risk, including authenticated access, role-based authorization, session expiration, CSRF protection, encrypted storage options, encrypted backups, audit logging, sanitized application logging, and operational backup scheduling helpers.

These controls do not make CareQueue HIPAA compliant by themselves.

Production or organizational use requires additional administrative, physical, technical, contractual, legal, and operational safeguards.

## Security Scope

This document describes:

- Sensitive-data handling rules
- Authentication and authorization controls
- Session and CSRF protections
- Encryption and key management
- Database and backup safety
- PDF intake handling
- Audit and operational logging
- Deployment and scheduler security
- Vulnerability reporting
- Known limitations

Detailed backup and recovery procedures are documented in:

```text
docs/workflows/backup-and-recovery.md
```

## Sensitive Data Rules

Do not commit, upload, publish, or share:

- `.env` files
- Encryption keys
- API keys
- Passwords or temporary passwords
- Session tokens
- CSRF tokens
- Authentication cookies
- Service-account credentials
- SQLite database files
- SQLCipher database files
- Encrypted backup files
- Restored database files
- Export files containing sensitive information
- Log files containing sensitive information
- Real intake PDFs
- Screenshots containing sensitive information
- Real client or patient names
- Real member IDs
- Real group numbers
- Real dates of birth
- Real clinical notes
- Real payer authorization records tied to identifiable people
- Any protected health information or personally identifiable information

Use fictional or clearly synthetic data for:

- Tests
- Development databases
- Screenshots
- Documentation
- Issues
- Pull requests
- Examples
- Demonstrations
- PDF intake fixtures

Do not rely on blurring or partial redaction when a clean synthetic example can be created instead.

## Local Secrets

Local secrets should be stored in environment files that are ignored by Git.

Examples include:

```text
.env
frontend/.env
C:\ProgramData\CareQueue\Config\carequeue.env
/etc/carequeue/carequeue.env
```

Commit only example configuration files:

```text
.env.example
frontend/.env.example
```

Before committing, inspect staged and unstaged files:

```bash
git status --short
```

Do not commit:

```text
.env
backend/data/
backend/backups/
backend/restores/
local_backups/
local_config/
local_vobs/
*.db
*.sqlite
*.sqlite3
*.db.enc
*.restored.db
frontend/node_modules/
backend/.venv/
__pycache__/
```

Environment files must not be pasted into issues, logs, screenshots, documentation, or chat messages.

## Current Security Controls

CareQueue currently includes:

- Argon2id password hashing
- Local user authentication
- Role-based access control
- Server-side sessions
- Hashed session-token persistence
- Secure browser-managed session cookies
- CSRF protection for authenticated state-changing requests
- Twenty-minute authenticated sessions
- Mandatory expiration warning during the final five minutes
- Active-session renewal
- Automatic frontend state clearing after expiration or logout
- Field-level encryption for selected sensitive authorization fields
- Optional SQLCipher database encryption
- Separately encrypted database backups
- Safe database, backup, and restore path validation
- Audit logging for selected authentication, administration, authorization, and timeline actions
- Centralized production log sanitization
- In-memory PDF intake processing
- Confidence and review indicators for extracted intake fields
- Windows Task Scheduler helpers for automated encrypted backups
- Linux systemd service and timer definitions for automated encrypted backups

These controls reduce specific risks but do not replace:

- Secure host configuration
- Network security
- HTTPS and TLS termination
- Secret management
- Workforce access policies
- Device security
- Incident response procedures
- Backup retention policies
- Restore exercises
- Risk analysis
- Legal review
- Compliance review
- Business associate agreements
- Organizational approval

## Authentication

CareQueue uses local application authentication.

Passwords are hashed using Argon2id.

Plaintext passwords must never be stored or logged.

Public self-registration is not provided.

Administrators create users through approved administrative workflows or maintenance scripts.

Temporary-password workflows require the user to change the password before normal application use.

Authentication failures should return generic messages that do not reveal whether a username exists.

## Roles and Authorization

CareQueue currently supports:

```text
Admin
UR
Read Only
```

Role behavior:

```text
Admin:
Can manage users, review audit events, and manage authorization workflows.

UR:
Can view, create, edit, and delete authorization records and timeline events.

Read Only:
Can view authorization records but cannot create, edit, or delete them.
```

Backend permission checks are authoritative.

Frontend visibility and disabled controls are usability features, not security boundaries.

New routes that read or modify protected data must use the appropriate backend authentication and role dependencies.

## Session Security

CareQueue uses server-side session records.

The browser receives the raw session token through an HttpOnly cookie.

The backend stores only a hash of the session token.

Session records include:

```text
user reference
creation time
last-seen time
expiration time
revocation time
hashed token
```

The default authenticated session duration is 20 minutes.

A mandatory warning appears during the final 5 minutes.

An authenticated user may renew an active session through:

```text
POST /api/security/session/renew
```

Renewal:

- Requires an active authenticated session
- Requires valid CSRF protection
- Extends the server-side expiration
- Refreshes relevant cookie lifetimes
- Returns the new expiration timestamp
- Does not expose the raw session token to frontend application state

The optional bottom-right countdown is informational only.

It is off by default and stores only a non-sensitive display preference.

Hiding the countdown does not disable the mandatory expiration warning.

When a session expires or logout occurs, CareQueue clears authenticated frontend state, including loaded authorization and timeline data.

## Cookie Security

Production deployments should use secure cookies over HTTPS.

Session cookies should remain:

- HttpOnly
- Secure in production
- Restricted to the intended path
- Configured with an appropriate SameSite policy

CSRF cookies must remain accessible to frontend request code but must not contain authentication credentials.

Cookie behavior must be tested behind the actual production reverse proxy or TLS termination layer.

## CSRF Protection

Authenticated state-changing requests require CSRF validation.

The frontend sends a CSRF header that must match the expected browser cookie value.

Missing or mismatched CSRF values are rejected.

CSRF validation must remain enabled for authenticated create, update, delete, logout, password-change, and session-renewal requests.

Authentication cookies alone must not be treated as sufficient protection for state-changing requests.

## Encryption Key Handling

CareQueue uses separate keys for separate protection layers:

```env
AUTHSTATUS_ENCRYPTION_KEY=field-level encryption key
AUTHSTATUS_SQLCIPHER_KEY=SQLCipher database key
AUTHSTATUS_BACKUP_ENCRYPTION_KEY=encrypted backup file key
```

These keys should be generated independently.

Do not reuse one key for multiple protection layers.

Important requirements:

- Do not commit encryption keys.
- Do not place keys in service files or scheduled-task arguments.
- Do not paste keys into issues, pull requests, screenshots, logs, chat messages, or documentation.
- Store keys securely outside the repository.
- Restrict key access to authorized application processes and administrators.
- Back up keys separately if encrypted data must remain recoverable.
- Document key ownership and recovery responsibility.
- Rotate keys only through a tested migration process.
- Test recovery before retiring an old key.

Key loss consequences:

- Losing `AUTHSTATUS_ENCRYPTION_KEY` may make encrypted field values unreadable.
- Losing `AUTHSTATUS_SQLCIPHER_KEY` may make the active SQLCipher database unreadable.
- Losing `AUTHSTATUS_BACKUP_ENCRYPTION_KEY` may make encrypted backup files unreadable.

Anyone who possesses both a protected file and its matching key may be able to decrypt the data.

## Field-Level Encryption

Selected sensitive authorization fields are encrypted before persistence.

Field-level encryption supplements database encryption. It does not replace it.

When adding a sensitive field:

1. Determine whether the value requires application-level encryption.
2. Add it to the controlled sensitive-field mapping.
3. Add encryption and decryption tests.
4. Confirm the plaintext value does not appear in the database.
5. Confirm the value is returned only to authorized users.
6. Confirm logs and audit metadata do not contain the value.

Do not add sensitive fields to audit metadata or exception messages.

## SQLCipher Database Encryption

CareQueue supports SQLCipher database encryption.

Production environments containing sensitive data should not use plaintext SQLite mode.

Configuration includes:

```env
AUTHSTATUS_DATABASE_ENCRYPTION=sqlcipher
AUTHSTATUS_SQLCIPHER_KEY=
```

The SQLCipher key must be available before the application opens the encrypted database.

Changing or losing the SQLCipher key without a tested migration process may make the database inaccessible.

Migration and verification scripts must be run against backups or approved copies before production cutover.

A successful application startup is not a substitute for verifying that the database file is actually encrypted.

## Database and Storage Paths

CareQueue validates database, backup, and restore paths to reduce accidental writes to unsafe locations.

External deployment paths require explicit configuration.

Examples include:

```env
AUTHSTATUS_ALLOW_UNSAFE_DATABASE_PATH=true
AUTHSTATUS_ALLOW_UNSAFE_STORAGE_PATHS=true
```

These settings do not make an external path safe by themselves.

Administrators must separately enforce:

- Restricted filesystem permissions
- Correct ownership
- Service-account access
- Backup isolation
- Host encryption where applicable
- Secure deletion and retention procedures

The active database, backup destination, and restore destination should remain separate.

## Backup Security

CareQueue creates separately encrypted backup files.

Encrypted backups remain sensitive and must be protected as though they contain readable PHI or PII.

Backup requirements include:

- Write backups outside the active database directory
- Restrict access to authorized service accounts and administrators
- Keep backup encryption keys separate from backup files
- Do not commit generated backups
- Confirm each backup is nonempty
- Review failed scheduled runs
- Define a retention policy
- Test restoration periodically
- Store at least one approved recovery copy separately from the active host when production requirements demand it
- Document recovery responsibilities

Restore scripts should write into an isolated restore location.

Restore operations must not automatically overwrite the active database.

Replacement of the active database should require a deliberate, documented administrative procedure.

## Automated Backup Scheduling

CareQueue includes platform-specific scheduling helpers.

Windows:

```text
deployment/windows/
├── install-backup-task.ps1
├── remove-backup-task.ps1
└── run-backup.ps1
```

Linux:

```text
deployment/linux/systemd/
├── carequeue-backup.service
└── carequeue-backup.timer
```

Scheduler files must not contain encryption keys or passwords.

### Windows

The Windows scheduled task runs as `SYSTEM` by default and may be configured for a dedicated service account.

Task registration and removal require elevated PowerShell.

The scheduled account must have only the access required to:

- Read the application files
- Execute the backend Python environment
- Read the protected environment file
- Read the active database
- Write to the backup directory

The environment file should be kept outside the application installation directory in production.

The task should report:

```text
LastTaskResult : 0
```

after a successful run.

A zero result must still be followed by confirmation that a recent, nonempty encrypted backup exists.

### Linux

The Linux systemd service should run under a dedicated CareQueue service account.

The supplied service restricts writable access to the configured backup directory and uses a restrictive file-creation mask.

The service account must be able to:

- Read the application files
- Execute the backend virtual environment
- Read the protected environment file
- Read the active database
- Write to the isolated backup directory

Administrators should review failures through `systemctl` and `journalctl`.

A successful timer invocation does not replace restoration testing.

Detailed setup and troubleshooting instructions are available in:

```text
docs/workflows/backup-and-recovery.md
```

## PDF Intake Security

PDF intake is designed to process uploaded files in memory.

The intake workflow should not:

- Persist the uploaded PDF
- Save extracted PDF text
- Include extracted values in production logs
- Include extracted values in audit metadata
- Send the PDF to an external service without explicit review and approval
- Accept uncertain extracted values without human review

Uploaded PDFs may contain PHI, PII, payer identifiers, member identifiers, dates of birth, clinical information, and facility details.

The current text extraction workflow is local and does not require an external OCR service.

Scanned PDFs without an embedded text layer may require a separately evaluated local OCR implementation.

Any future OCR dependency must be reviewed for:

- Telemetry
- Network communication
- Temporary-file behavior
- Model downloads
- Logging
- Update behavior
- Licensing
- Data retention

Fields marked as needing review must be confirmed or corrected before intake values are accepted.

Test fixtures and screenshots must use synthetic PDF content only.

## Audit Logging

CareQueue records selected authentication, administration, authorization, and timeline actions.

Audit metadata should identify what happened without storing sensitive before-and-after values.

Preferred metadata includes:

```text
record IDs
user IDs
action names
event types
changed field names
success or failure state
```

Audit metadata must not contain:

- Patient or client names
- Member IDs
- Group numbers
- Dates of birth
- Authorization numbers tied to identifiable people
- Clinical notes
- Free-text notes containing PHI or PII
- Extracted PDF text
- Uploaded filenames containing sensitive information
- Passwords
- Temporary passwords
- Session tokens
- CSRF tokens
- Encryption keys
- Authentication cookies

Audit access should be restricted to authorized administrators.

Audit retention and review frequency must be defined by the deploying organization.

## Operational Logging

CareQueue applies centralized production log sanitization.

Logging controls are intended to remove or mask:

- Authorization headers
- Cookie values
- Session values
- CSRF tokens
- Password fields
- Known sensitive data fields
- Raw exception messages
- Traceback details that may contain request data

Production logs may retain safe operational context such as:

- Timestamp
- Log level
- Logger name
- Event category
- Exception class name
- Non-sensitive request status

Developers must not bypass the centralized logging configuration with ad hoc file writes, `print()` statements, or custom handlers that expose sensitive values.

Do not log complete request bodies, response bodies, uploaded PDF text, database rows, decrypted records, or environment variables.

Log files require:

- Restricted access
- Defined retention
- Secure storage
- Review procedures
- Safe disposal

Sanitization reduces risk but does not guarantee that arbitrary developer-written log content is safe.

## Error Handling

Client-facing errors should be generic when detailed information could expose:

- Credentials
- Account existence
- Database paths
- Encryption configuration
- Internal SQL
- Filesystem layout
- PHI or PII
- Session state
- Stack traces

Detailed debugging should be performed in controlled development environments using synthetic data.

Production exception messages and tracebacks should not be returned to clients.

## Screenshots and Demonstrations

All public screenshots must use a dedicated synthetic dataset.

Screenshots must not expose:

- Real names
- Real facilities
- Real payer identifiers
- Real member or group numbers
- Real dates of birth
- Real authorization identifiers
- Clinical notes
- Browser autofill data
- Local usernames
- Machine names
- Sensitive file paths
- Environment values
- Terminal history
- Keys or credentials

Store approved screenshots in:

```text
docs/assets/screenshots/
```

Review each screenshot at full resolution before committing it.

## Dependency and Code Review

Security-related changes should receive focused review.

Examples include:

- Authentication
- Password handling
- Session logic
- CSRF behavior
- Authorization dependencies
- SQL construction
- Encryption
- Key handling
- Logging
- Audit metadata
- PDF processing
- Backup and restore code
- Scheduler scripts
- Deployment configuration

Backend checks include:

```bash
pytest tests -n auto -q
python -m ruff check . --fix
bandit -r authstatus_api
```

Frontend checks include:

```bash
npm run build
```

PowerShell and systemd files require manual review and platform-specific validation.

## Reporting Security Issues

Do not open a public issue for concerns involving:

- Exposed secrets
- Exposed PHI or PII
- Authentication bypass
- Authorization bypass
- Session or CSRF vulnerabilities
- Encryption failures
- Backup exposure
- Path traversal
- SQL injection
- Sensitive logging
- Unsafe PDF handling
- Service-account exposure
- Deployment misconfiguration

Report security concerns privately to the repository owner when possible.

A security report should include:

- A concise description
- Affected component
- Reproduction steps using synthetic data
- Expected behavior
- Actual behavior
- Potential impact
- Suggested mitigation, when known

Do not include real sensitive data, credentials, keys, production databases, or private backups in a report.

## Production Readiness Warning

CareQueue is not independently production-ready or HIPAA compliant.

Before production or organizational use, complete and document at least:

- Deployment architecture review
- HTTPS and TLS enforcement
- Host hardening
- Firewall and network restrictions
- Production secret management
- Service-account configuration
- Access approval and termination procedures
- Periodic access review
- Password and authentication policy
- Device and workstation security
- Logging and monitoring procedures
- Audit review procedures
- Backup retention policy
- Off-host backup strategy where required
- Restore testing
- Disaster recovery procedures
- Incident response procedures
- Vulnerability management
- Dependency update procedures
- Secure software release procedures
- Risk analysis
- Compliance review
- Privacy review
- Legal review
- Business associate agreements where required
- Workforce training
- Organizational approval
- Independent security assessment

Technical features in this repository are only one part of a secure and compliant operating environment.
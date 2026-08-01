# Security Policy

CareQueue is a local-first healthcare workflow application intended for private development, testing, and controlled deployment.

It includes authentication, role-based authorization, session controls, CSRF protection, encrypted storage options, encrypted backups, audit logging, log sanitization, private HTTPS deployment, and backup scheduling support.

Those controls do not make CareQueue HIPAA compliant by themselves. Any organization using CareQueue with protected health information remains responsible for its own administrative, physical, technical, contractual, legal, and operational safeguards.

## Supported Versions

CareQueue is under active development. Security fixes are applied to the current development line.

Older releases, copied deployments, and unmaintained forks should not be assumed to receive security updates.

Production operators should:

- Track the current repository state
- Review release and dependency changes before upgrading
- Test upgrades against a backup or non-production instance
- Keep operating systems, browsers, Python, Node.js, Caddy, and service wrappers supported and patched
- Re-run security and functional checks after deployment changes

## Reporting a Security Issue

Do not open a public issue for a suspected vulnerability involving:

- Exposed credentials or encryption keys
- Exposed PHI or PII
- Authentication or authorization bypass
- Session or CSRF weaknesses
- SQL injection
- Path traversal
- Sensitive logging
- Backup exposure
- Encryption failure
- Unsafe PDF handling
- Service-account exposure
- Deployment or certificate misconfiguration

Report security concerns privately to the repository owner when possible.

A useful report includes:

- A concise description
- The affected component
- Reproduction steps using synthetic data
- Expected behavior
- Actual behavior
- Potential impact
- A suggested mitigation, when known

Do not include real patient information, credentials, production databases, encryption keys, or private backup files in a report.

## Sensitive Data Rules

Do not commit, publish, upload, or share:

- `.env` files
- Encryption keys
- Passwords or temporary passwords
- Session or CSRF tokens
- Authentication cookies
- Service-account credentials
- SQLite or SQLCipher database files
- Encrypted backup files
- Restored database files
- Real intake PDFs
- Logs containing sensitive information
- Screenshots containing real data
- Real names, member IDs, group numbers, dates of birth, authorization numbers, or clinical notes
- Any other PHI or PII

Use fictional or clearly synthetic data for:

- Tests
- Development databases
- Screenshots
- Documentation
- Issues
- Pull requests
- Demonstrations
- PDF intake fixtures

A clean synthetic example is safer than blurring or partially redacting a real record.

Before committing:

```powershell
git status --short
```

Common local-only files and directories include:

```text
.env
backend/.venv/
backend/data/
backend/backups/
backend/restores/
frontend/node_modules/
local_backups/
local_config/
local_vobs/
*.db
*.sqlite
*.sqlite3
*.db.enc
*.restored.db
```

## Local Secrets

Secrets belong in environment files or another approved secret store outside the repository.

Examples include:

```text
.env
frontend/.env.development.local
C:\ProgramData\CareQueue\Config\carequeue.env
/etc/carequeue/carequeue.env
```

Only example configuration files should be committed:

```text
.env.example
frontend/.env.example
```

Environment files must not be pasted into issues, screenshots, terminal transcripts, documentation, or chat messages.

## Current Security Controls

CareQueue currently includes:

- Argon2id password hashing
- Local user authentication
- Role-based access control
- Server-side sessions
- Hashed session-token persistence
- Secure browser-managed session cookies
- CSRF protection for authenticated state-changing requests
- Session expiration, warning, renewal, and token rotation
- Frontend state clearing after logout or expiration
- Field-level encryption for selected sensitive values
- Optional SQLCipher database encryption
- Separately encrypted database backups
- Backup verification and retention controls
- Safe database, backup, restore, and recovery path validation
- Audit logging for selected security and workflow actions
- Centralized production log sanitization
- Local PDF text extraction with confidence and review flags
- Windows and Linux backup scheduling helpers
- Private Windows HTTPS through Caddy
- Loopback-only API binding in the Windows production deployment
- Restricted production runtime directories
- Service-aware production upgrades

These controls reduce specific risks. They do not replace secure host configuration, network controls, secret management, access policies, endpoint protection, monitoring, incident response, legal review, or compliance review.

## Authentication

CareQueue uses local application authentication.

Passwords are hashed with Argon2id. Plaintext passwords must never be stored or logged.

Public self-registration is not provided. Administrators create users through approved administrative workflows or maintenance scripts.

Temporary-password workflows require a password change before normal use.

Authentication failures should use generic responses that do not reveal whether a username exists.

## Roles and Authorization

CareQueue currently supports:

```text
Admin
UR
Read Only
```

Role behavior:

```text
Admin
Full authorization workflow access plus user and administrative controls.

UR
Create, view, edit, and manage authorization records and timeline events.

Read Only
View authorization records without create, edit, or delete controls.
```

Backend permission checks are authoritative.

Frontend visibility and disabled controls are usability features only. They are not security boundaries.

New routes that read or modify protected data must use the appropriate backend authentication and role dependencies.

## Session Security

CareQueue uses server-side session records.

The browser receives a raw session token through an HttpOnly cookie. The backend stores only a hash of that token.

Session records include:

```text
user reference
creation time
last-seen time
expiration time
revocation time
hashed token
```

The configured session flow includes:

- A fixed authenticated session duration
- A mandatory expiration warning
- Active-session renewal
- Session and CSRF token rotation during renewal
- Cookie lifetime refresh
- Frontend state clearing after logout or expiration

The renewal endpoint requires both an active authenticated session and valid CSRF protection.

The frontend may display an optional countdown, but the backend remains authoritative for session validity and expiration.

## Cookie Security

Production session cookies should remain:

- HttpOnly
- Secure
- Restricted to the intended path
- Configured with an appropriate SameSite policy

The CSRF cookie must remain readable by frontend request code but must not contain authentication credentials.

Cookie behavior should be tested through the actual production HTTPS origin, not only against the development API.

## CSRF Protection

Authenticated state-changing requests require CSRF validation.

The frontend sends a CSRF header whose value must match the expected browser cookie value.

Missing or mismatched values are rejected.

CSRF protection must remain enabled for authenticated operations such as:

- Create
- Update
- Delete
- Logout
- Password change
- Session renewal
- Administrative changes

Authentication cookies alone are not sufficient protection for state-changing requests.

## Encryption Model

CareQueue uses separate keys for separate protection layers:

```env
AUTHSTATUS_ENCRYPTION_KEY=field-level encryption key
AUTHSTATUS_SQLCIPHER_KEY=database encryption key
AUTHSTATUS_BACKUP_ENCRYPTION_KEY=backup encryption key
```

These keys should be generated independently.

Do not reuse one key for multiple layers.

### Key handling requirements

- Do not commit keys.
- Do not place keys in service definitions or scheduled-task arguments.
- Do not paste keys into issues, screenshots, logs, documentation, or chat messages.
- Restrict key access to the application process and authorized administrators.
- Keep recoverable copies separate from protected data.
- Document key ownership and recovery responsibility.
- Rotate keys only through a tested migration process.
- Verify recovery before retiring an old key.

Key loss can make protected data unreadable:

- Losing the field-level key may make encrypted field values unreadable.
- Losing the SQLCipher key may make the active database unreadable.
- Losing the backup key may make encrypted backups unreadable.

Anyone with both a protected file and its matching key may be able to decrypt the data.

## Field-Level Encryption

Selected sensitive authorization values are encrypted before persistence.

Field-level encryption supplements database encryption. It does not replace it.

When adding a sensitive field:

1. Decide whether the value requires application-level encryption.
2. Add it to the controlled sensitive-field mapping.
3. Add encryption and decryption tests.
4. Confirm plaintext does not appear in the database.
5. Confirm the value is returned only to authorized users.
6. Confirm logs and audit metadata do not contain the value.

Sensitive values should not appear in exception messages, audit metadata, or debug output.

## SQLCipher Database Encryption

CareQueue supports either SQLite or SQLCipher-backed storage.

A production environment containing sensitive data should not use plaintext SQLite mode.

Typical SQLCipher settings include:

```env
AUTHSTATUS_DATABASE_ENCRYPTION=sqlcipher
AUTHSTATUS_SQLCIPHER_KEY=
```

The SQLCipher key must be available before the application opens the database.

Changing or losing the key without a tested migration process may make the database inaccessible.

A successful application startup is not, by itself, proof that the database file is encrypted. Encryption should be verified through an approved database check or migration procedure.

## Database and Storage Paths

CareQueue validates active database, backup, restore, and recovery paths to reduce accidental writes to unsafe locations.

External production paths may require explicit configuration such as:

```env
AUTHSTATUS_ALLOW_UNSAFE_DATABASE_PATH=true
AUTHSTATUS_ALLOW_UNSAFE_STORAGE_PATHS=true
```

These settings only allow the path. They do not make it secure.

Administrators must still enforce:

- Restricted filesystem permissions
- Correct ownership
- Service-account access
- Host and volume protection where required
- Backup isolation
- Retention and deletion procedures

The active database, backup destination, restore destination, and recovery staging area should remain separate.

## Backup Security

CareQueue creates separately encrypted backup files.

Encrypted backups must still be treated as sensitive.

Backup requirements include:

- Store backups outside the active database directory.
- Restrict access to the service account and authorized administrators.
- Keep backup keys separate from backup files.
- Verify backups are nonempty and readable by the restore workflow.
- Review failed scheduled runs.
- Define and enforce retention.
- Keep an approved off-host recovery copy when required.
- Test restoration periodically.
- Document who is responsible for recovery.

Restore operations write to an isolated location first. They should not overwrite the active database automatically.

Activation of a restored database should be deliberate, documented, and tested.

Detailed procedures are in:

```text
docs/workflows/backup-and-recovery.md
```

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

Scheduler files must not contain passwords or encryption keys.

The scheduled account should have only the access required to:

- Read application files
- Execute the backend environment
- Read the protected environment file
- Read the active database
- Write to the backup directory

A successful scheduler result does not replace checking that a recent, nonempty encrypted backup exists.

It also does not replace restoration testing.

## PDF Intake Security

PDF intake is designed to process supported documents locally and in memory.

The intake workflow should not:

- Persist the uploaded PDF unnecessarily
- Save extracted text
- Include extracted values in production logs
- Include extracted values in audit metadata
- Send documents to an external service without explicit review and approval
- Accept uncertain extracted values without human review

Uploaded documents may contain PHI, PII, payer identifiers, member identifiers, dates of birth, clinical information, and facility details.

The current extraction workflow reads embedded PDF text and does not depend on an external OCR service.

Scanned PDFs without a usable text layer may require a separately reviewed local OCR implementation.

Any future OCR dependency should be evaluated for:

- Telemetry
- Network communication
- Temporary-file behavior
- Model downloads
- Logging
- Update behavior
- Licensing
- Data retention

Fields marked as needing review must be confirmed or corrected before intake values are accepted.

Tests and screenshots must use synthetic PDF content only.

## Audit Logging

CareQueue records selected authentication, administration, authorization, and timeline actions.

Audit metadata should explain what happened without storing sensitive before-and-after values.

Appropriate metadata may include:

```text
record IDs
user IDs
action names
event types
changed field names
success or failure state
```

Audit metadata must not contain:

- Names
- Member IDs
- Group numbers
- Dates of birth
- Clinical notes
- Extracted PDF text
- Uploaded filenames containing sensitive information
- Passwords
- Session or CSRF tokens
- Encryption keys
- Authentication cookies

Audit access should be limited to authorized administrators.

Retention and review frequency must be defined by the deploying organization.

## Operational Logging

CareQueue applies centralized production log sanitization.

Logging controls are intended to remove or mask:

- Authorization headers
- Cookies
- Session values
- CSRF tokens
- Password fields
- Known sensitive fields
- Raw exception messages
- Traceback details that may contain request data

Production logs may retain safe operational context such as:

- Timestamp
- Log level
- Logger name
- Event category
- Exception class
- Non-sensitive status information

Developers should not bypass the logging configuration with ad hoc file writes, `print()` statements, or custom handlers that expose data.

Do not log:

- Complete request or response bodies
- Uploaded PDF text
- Database rows
- Decrypted records
- Environment variables
- Credentials or keys

Log files require restricted access, retention rules, review procedures, and secure disposal.

Sanitization reduces risk but cannot make arbitrary developer-written log content safe.

## Error Handling

Client-facing errors should remain generic when detailed output could expose:

- Credentials
- Account existence
- Database paths
- Encryption configuration
- SQL details
- Filesystem layout
- PHI or PII
- Session state
- Stack traces

Detailed debugging belongs in controlled development environments using synthetic data.

Production tracebacks and internal exception details should not be returned to clients.

## Private Windows HTTPS Deployment

The Windows production deployment uses:

```text
CareQueueApi
CareQueueCaddy
```

`CareQueueApi` runs FastAPI on:

```text
127.0.0.1:8000
```

`CareQueueCaddy` serves the frontend and proxies `/api` through private HTTPS.

A local installation may use a private hostname such as:

```text
https://carequeue.local
```

Security assumptions for this deployment include:

- The API remains bound to loopback.
- Users access the application through the HTTPS origin.
- The local hostname resolves only where intended.
- The Caddy local root certificate is trusted only on approved systems.
- Runtime files under `C:\ProgramData\CareQueue` have restricted permissions.
- The production environment file is not readable by ordinary users.
- Windows services run under an approved account.
- Firewall and network policy prevent unintended exposure.

The built-in Windows configuration is for private or restricted-network use. It is not a public internet deployment template.

A public deployment would require additional review of DNS, certificates, firewall rules, service accounts, remote access, monitoring, patching, and incident response.

## Service Accounts and Permissions

Service accounts should receive only the permissions they need.

The API service requires access to:

- Installed backend files
- The production environment file
- The active database
- Approved backup, restore, recovery, and log directories

The Caddy service requires access to:

- The built frontend
- The installed Caddy configuration
- Caddy certificate and runtime storage
- Caddy log storage
- Network ports used by the private HTTPS deployment

Interactive user accounts should not receive production data access unless they are approved administrators.

Permission changes should be tested after upgrades because inherited Windows ACLs can behave differently from explicit service-account grants.

## Upgrade Security

The Windows production installer preserves the production environment file and encryption keys during forced upgrades.

When running services are detected, the installer:

- Stops Caddy first
- Stops the API second
- Replaces application files
- Rebuilds the production backend environment
- Validates the installed backend
- Reapplies runtime permissions
- Restarts the API
- Restarts Caddy

Only services that were previously running are restored.

Before an upgrade:

- Confirm a recent encrypted backup exists.
- Confirm the backup key is available.
- Review dependency changes.
- Test the upgrade in a non-production copy when possible.
- Keep rollback and recovery instructions available.

An application upgrade is not a substitute for a database migration or recovery plan.

## Screenshots and Demonstrations

Public screenshots must use a dedicated synthetic dataset.

Screenshots must not expose:

- Real names or facilities
- Real payer, member, group, or authorization identifiers
- Real dates of birth
- Clinical notes
- Browser autofill data
- Local usernames or machine names
- Sensitive file paths
- Environment values
- Terminal history
- Keys or credentials

Review each screenshot at full resolution before committing it.

A public demo should be a separate deployment with synthetic data, independent keys, separate storage, and no connection to a private CareQueue instance.

## Dependency and Code Review

Security-sensitive changes require focused review.

Examples include:

- Authentication
- Password handling
- Session logic
- CSRF behavior
- Role dependencies
- SQL construction
- Encryption
- Key handling
- Logging
- Audit metadata
- PDF processing
- Backup and recovery
- Deployment scripts
- Service definitions
- Certificate handling

Backend checks include:

```powershell
pytest tests -n auto -q
python -m ruff check . --fix
bandit -r authstatus_api
pip-audit
```

Frontend checks include:

```powershell
npm test
npm run build
npm audit
```

PowerShell, Caddy, WinSW, systemd, and certificate changes also require platform-specific manual validation.

## Production Readiness

CareQueue is not independently production-ready or HIPAA compliant.

Before organizational use, complete and document at least:

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
- Backup retention
- Off-host recovery where required
- Restore testing
- Disaster recovery
- Incident response
- Vulnerability management
- Dependency updates
- Secure release procedures
- Risk analysis
- Privacy, legal, and compliance review
- Business associate agreements where required
- Workforce training
- Organizational approval
- Independent security assessment

Technical safeguards in this repository are only one part of operating a secure healthcare system.

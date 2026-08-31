# Security Policy

CareQueue is a local-first healthcare workflow application intended for private development, testing, and controlled deployment.

It includes authentication, role-based authorization, TOTP multi-factor authentication, remembered-device MFA, single-session enforcement, inactivity-based session controls, CSRF protection, versioned governance attestation, encrypted storage options, encrypted backups, audit logging, log sanitization, isolated PDF extraction, private HTTPS deployment, browser security headers, dependency checks, and backup scheduling support.

Those controls do not make CareQueue HIPAA compliant by themselves. Any organization using CareQueue with protected health information remains responsible for its own administrative, physical, technical, contractual, legal, and operational safeguards.

## Supported Versions

CareQueue is under active development. Security fixes are applied to the current development line.

Older releases, copied deployments, and unmaintained forks should not be assumed to receive security updates.

Licensing status and security-support status are separate concerns. Historical or source-available code should not be assumed to receive security fixes merely because its source remains available. See `LICENSE` and `docs/licensing.md` for licensing terms.

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
- Shared server-side password policy enforcement
- Failed-login tracking and temporary account lockout
- Local user authentication
- Role-based access control
- TOTP multi-factor authentication
- Short-lived server-side MFA login challenges
- Optional time-limited remembered devices for MFA
- Trusted-device revocation during security-sensitive account changes
- Single active authenticated session per account
- Server-side sessions
- Hashed session-token persistence
- Secure browser-managed session cookies
- CSRF protection for authenticated state-changing requests
- Configurable inactivity timeout with a 20-minute default
- Sliding authenticated-session expiration
- Session expiration warning and explicit renewal
- Session and CSRF token rotation during renewal
- Cross-tab session expiration and logout synchronization
- Frontend state clearing after logout or expiration
- Versioned organization governance attestation before protected application access
- Admin-only governance acceptance
- Append-only governance attestation history
- Audit logging for governance acceptance
- Field-level encryption for selected sensitive values
- Optional SQLCipher database encryption
- Separately encrypted database backups
- Backup verification and retention controls
- Safe database, backup, restore, and recovery path validation
- Audit logging for selected security and workflow actions
- Centralized production log sanitization
- Local PDF text extraction with confidence and review flags
- Isolated PDF extraction worker with timeout handling
- Bounded backend production dependency requirements
- Backend dependency audit checks with `pip-audit`
- Frontend dependency audit checks with `npm audit`
- Static security scanning with Bandit
- Windows and Linux backup scheduling
- Private HTTPS through Caddy for packaged Windows and Linux deployments
- Content Security Policy and related browser security headers
- Loopback-only first-time Admin setup
- Loopback-only API binding in packaged production deployments
- Restricted production runtime directories
- Service-aware production upgrades
- Verified pre-upgrade database and application recovery assets
- Failed-upgrade recovery records and assisted rollback on packaged Windows and Linux deployments
- Post-rollback service and application-health validation

These controls reduce specific risks. They do not replace secure host configuration, network controls, secret management, access policies, endpoint protection, monitoring, incident response, legal review, or compliance review.

## Authentication

CareQueue uses local application authentication.

Passwords are hashed with Argon2id. Plaintext passwords must never be stored or logged.

Public self-registration is not provided. Administrators create users through approved administrative workflows or maintenance scripts.

Temporary-password workflows require a password change before normal use.

Authentication failures should use generic responses that do not reveal whether a username exists.

A failed login records:

```text
security.login_failed
```

Repeated failed logins increment the account's failed-login count. After the configured threshold is reached, the account is temporarily locked and later login attempts receive a generic locked-account response.

A locked login attempt records:

```text
security.login_locked
```

Successful authentication clears the failed-login state.

### Multi-Factor Authentication

CareQueue supports TOTP multi-factor authentication.

When MFA is enabled for a user, a successful username/password check does not immediately create an authenticated application session unless a valid remembered-device token is accepted. Otherwise, CareQueue creates a short-lived server-side MFA challenge and requires a valid TOTP code before creating the authenticated session.

MFA secrets are encrypted before persistence and must never be logged, returned after enrollment is complete, or included in audit metadata.

MFA login challenge tokens are generated from cryptographically secure random values. The backend persists a keyed digest rather than the raw challenge token.

Administrators may reset MFA for another user through the approved user-management workflow. Security-sensitive account changes that invalidate authentication state must also revoke affected sessions and remembered devices where implemented.

### Remembered Devices

After successful MFA verification, a user may choose to remember the current device.

The remembered-device control:

- Is optional.
- Is separate from the authenticated session.
- Uses an HttpOnly, Secure browser cookie in production.
- Stores only a keyed digest of the raw trusted-device token.
- Has a limited lifetime.
- Does not extend the authenticated session lifetime.
- Does not bypass password authentication.
- Can be revoked.
- Is invalidated during supported security-sensitive account changes.

The current trusted-device lifetime is 30 days.

A remembered device suppresses the TOTP step only while its trusted-device record and cookie remain valid. It does not create a persistent authenticated session.

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

CareQueue enforces one active authenticated session per account. Creating a new authenticated session revokes any previous non-revoked sessions for that user.

Authenticated sessions use an inactivity timeout rather than a long-lived browser login. The default inactivity window is 20 minutes and is configurable through:

```env
AUTHSTATUS_SESSION_INACTIVITY_MINUTES=20
```

The configured session flow includes:

- Server-authoritative inactivity expiration
- Sliding expiration while authenticated activity continues
- Atomic activity updates that do not revive an already expired session
- A mandatory frontend expiration warning
- Explicit active-session renewal
- Session and CSRF token rotation during renewal
- Browser-session cookies for the authenticated session and CSRF state
- Cross-tab synchronization of logout and expiration state
- Frontend state clearing after logout or expiration

The frontend sends throttled activity updates for supported user interaction rather than renewing continuously on every browser event.

The activity and renewal endpoints require an active authenticated session and valid CSRF protection. An expired session cannot be renewed or revived by later browser activity.

The backend remains authoritative for session validity and expiration. Frontend timers and cross-tab synchronization are usability and coordination controls, not the security boundary.

Remembered-device MFA is intentionally separate from authenticated session lifetime. A remembered device may suppress the TOTP step at a later login, but it does not keep an authenticated CareQueue session alive.

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
- Session activity updates
- Governance attestation acceptance
- Administrative changes

Authentication cookies alone are not sufficient protection for state-changing requests.

## Governance Attestation

CareQueue requires the current organization governance attestation before normal protected application functionality becomes available.

After initial Admin setup and login, an Admin must complete the current attestation version. Non-Admin users cannot accept organization-level governance terms.

The attestation records:

```text
attestation version
organization name
deployment mode
accepting user
acceptance time
CareQueue application version
```

Governance history is append-only through the application. Previous accepted records remain available to authorized administrators when a later governance version requires re-attestation.

Acceptance records an audit event:

```text
governance.attestation_accepted
```

The governance audit event identifies the governance record and safe version/deployment metadata without placing the organization name into audit metadata.

The governance attestation version is independent from the CareQueue application version. Updating CareQueue does not by itself require re-attestation. Re-attestation occurs when the required governance attestation version changes.

The governance workflow is an application control intended to support organizational accountability. It does not itself execute a Business Associate Agreement, establish HIPAA compliance, replace legal review, or replace required administrative, physical, and technical safeguards.

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

For the full CareQueue key custody, rotation, compromise response, recovery, and retirement procedure, see [Encryption Key Lifecycle](docs/security/encryption-key-lifecycle.md).

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

The current extraction workflow reads embedded PDF text and does not depend on an external OCR service. PDF parsing runs in an isolated worker process with timeout handling so a stalled parser can be terminated without blocking the API process indefinitely.

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

## Private HTTPS Deployment

Packaged Windows and Linux production deployments place Caddy in front of a loopback-only CareQueue API.

The API listens on:

```text
127.0.0.1:8000
```

Caddy serves the built frontend and proxies `/api` through HTTPS.

The Caddy configuration also applies browser security headers, including Content Security Policy, frame denial, content-type sniffing protection, referrer policy, permissions policy, and HSTS.

The packaged private deployment uses:

```text
https://carequeue.local
```

with Caddy's internal certificate authority.

Security assumptions for this deployment include:

- The API remains bound to loopback.
- Users access the application through the approved HTTPS origin.
- The private hostname resolves only where intended.
- The Caddy local root certificate is trusted only on approved systems.
- Production configuration, database, backup, recovery, and log locations have restricted permissions.
- The production environment file is not readable by ordinary users.
- Services run under approved restricted accounts.
- Firewall and network policy prevent unintended exposure.

On Windows, runtime data is stored under `C:\ProgramData\CareQueue`.

On Linux, packaged deployment uses the dedicated `carequeue` service account and stores production configuration, data, and logs under restricted system paths documented in `docs/deployment/linux.md`.

The built-in configurations are for private or restricted-network use. They are not public internet deployment templates.

A public deployment would require separate review of DNS, publicly trusted certificates, firewall rules, service accounts, remote access, monitoring, patching, incident response, and the Caddy/hostname configuration.

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

Permission changes should be tested after upgrades. Windows ACL inheritance and Linux ownership/mode changes can both produce permissions that differ from the intended service-account grants.

## Upgrade and Rollback Security

Packaged Windows and Linux upgrade workflows preserve the existing production environment configuration and encryption keys rather than generating replacement keys during an ordinary upgrade.

Supported Upgrade workflows also preserve verified recovery assets before replacing the installed application. Depending on platform, these include:

- A verified encrypted pre-upgrade database backup
- A preserved archive of the previously installed application
- A SHA256 checksum for the preserved application archive
- Previous and incoming application versions
- Installer log information
- A durable upgrade recovery record

The deployment workflows replace application and runtime files, rebuild or refresh the production backend environment, validate the installed backend, reapply deployment configuration and permissions, and restart the required services.

CareQueue database schema changes are applied through an ordered versioned migration framework during database initialization.

Applied migrations are recorded in the `schema_migrations` ledger. Previously completed migrations are skipped on later startups. Each new migration runs within a database savepoint and is recorded only after successful application.

A failed required migration prevents that migration from being recorded as complete and should be investigated rather than bypassed by manually editing the migration ledger or production schema.

Before an upgrade:

- Confirm a recent verified encrypted backup exists.
- Confirm the backup key and required database encryption keys are available.
- Review dependency, schema, migration, deployment, and recovery changes.
- Test the upgrade in a non-production copy when possible.
- Keep recovery instructions and the previously trusted release artifact available.
- Confirm the current installation is healthy before beginning the upgrade.
- Confirm sufficient disk space is available for application files, databases, logs, backups, application archives, and recovery data.
- Preserve upgrade recovery assets until the operation and post-upgrade validation are complete.

After an upgrade:

- Confirm required services are running.
- Confirm liveness and readiness checks pass.
- Confirm login succeeds.
- Confirm governance status shows the expected attestation version and document revision.
- Confirm representative application workflows operate correctly.
- Confirm audit integrity remains valid.
- Confirm backup scheduling and recovery functionality remain available.
- Confirm the application is reachable only through the intended HTTPS origin.
- Confirm the expected application version is active.

### Failed-Upgrade Rollback

CareQueue provides assisted rollback for supported packaged Windows and Linux upgrades when a valid failed-upgrade recovery record and required recovery assets exist.

Rollback is not a general downgrade mechanism.

The supported workflow restores the preserved previous application together with the verified pre-upgrade database backup. This avoids treating application-file replacement alone as sufficient after a migration-bearing upgrade.

Rollback recovery records may use durable states such as:

```text
failed
rollback_staged
rollback_activated
rollback_completed
```

Linux may also record an application-restoration state when an application swap fails and the failed incoming application is restored.

Do not manually alter recovery records, application archive checksums, migration records, or encrypted database files to force rollback to continue.

Before rollback:

- Preserve the failed-upgrade recovery record and referenced assets.
- Confirm the preserved pre-upgrade database backup exists and is nonempty.
- Confirm the preserved previous-application archive exists and passes its recorded SHA256 check.
- Confirm required encryption keys remain available.
- Review the installer log and determine the current service state.

After rollback:

- Confirm required services are running.
- Confirm liveness and readiness checks pass.
- Confirm the expected previous application version is active.
- Confirm representative application data is available.
- Confirm governance state remains available.
- Confirm audit integrity remains valid.
- Confirm backup scheduling remains available.
- Confirm the recovery record reached `rollback_completed`.

A recovery record that reached `rollback_activated` but not `rollback_completed` indicates an incomplete recovery state. The pre-upgrade database may already be active even though service startup or health validation failed.

Treat that state as a recovery incident. Preserve logs and recovery assets, confirm service and database state, and avoid additional state-changing operations until the failure is understood.

Windows rollback attempts to stop CareQueue services again when a post-database-activation failure occurs. Linux rollback also keeps or returns the API to a stopped state in safety-sensitive database activation failures.

Temporary rollback staging is not the authoritative recovery evidence. Durable recovery records, verified backups, application archives, checksums, and logs should be retained according to operational policy.

Database migrations, application rollback, database recovery, and disaster recovery remain related but distinct operational concerns. See `docs/operations/upgrades.md` and `docs/workflows/backup-and-recovery.md` for the corresponding procedures.

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
- MFA and trusted-device handling
- Session logic
- Governance enforcement
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
pytest backend\tests -n auto -q
ruff check . --fix
bandit -r backend\authstatus_api backend\scripts -c backend\pyproject.toml
python -m pip_audit -r backend\requirements.txt
```

Frontend checks include:

```powershell
npm audit
npm test
npm run build
```

PowerShell, Caddy, WinSW, systemd, and certificate changes also require platform-specific manual validation.

## Threat Model and Risk Register

CareQueue maintains a formal threat model and risk register covering application, deployment, operational, and supply-chain risks.

See:

```text
docs/security/threat-model-and-risk-register.md
```

The threat model documents:

- Protected assets and security objectives
- Threat actors and attacker capabilities
- Application and deployment trust boundaries
- Representative abuse cases
- Existing security controls
- Residual risks
- Risk likelihood and impact
- Planned mitigations and remediation priorities
- Security review triggers

The risk register should be reviewed when security boundaries, authentication behavior, encryption, deployment architecture, privileged workflows, external dependencies, or release processes materially change.

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
- Password, MFA, and authentication policy
- Governance attestation ownership and review
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

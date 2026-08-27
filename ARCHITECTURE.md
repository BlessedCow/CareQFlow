# Architecture

CareQueue is a local-first utilization review and authorization tracking application. It uses a React and TypeScript frontend, a FastAPI backend, and SQLite or SQLCipher-backed persistence.

The application is organized around several separate concerns:

- Authorization records and timeline events
- Dashboard analytics and due-date workflows
- Authentication, MFA, sessions, roles, and CSRF protection
- Versioned organization governance attestation
- Registered facilities, insurers, and portal details
- PDF-assisted intake
- Encrypted storage, backups, and staged recovery
- Tamper-evident audit records and operational logging
- Packaged private Windows and Linux deployment through Caddy and operating-system services

CareQueue is intended for private or controlled deployment. Its technical controls are only one part of operating a system that may handle sensitive healthcare information.

## System Overview

In private production use, requests follow this path:

```text
Browser
  |
  | HTTPS
  v
Caddy
  |\
  | \__ Serves the built React frontend
  |
  \____ Proxies /api requests
          |
          v
      FastAPI on 127.0.0.1:8000
          |
          v
      Application services and repositories
          |
          v
      SQLite or SQLCipher database
```

The browser communicates only with the HTTPS application origin. The FastAPI server remains bound to the loopback interface and is not intended to be exposed directly.

For local development, the frontend and backend normally run separately:

```text
React development server
http://localhost:5173
        |
        | API requests
        v
FastAPI development server
http://127.0.0.1:8000
```

The frontend uses a configured API base URL during development. Production builds use same-origin `/api` requests through Caddy.

## Repository Layout

The main areas of the repository are:

```text
CareQueue/
├── backend/
│   ├── authstatus_api/     # API, domains, persistence, security, and operations
│   ├── scripts/            # Administrative and recovery utilities
│   └── tests/              # Backend tests organized by domain
├── frontend/
│   └── src/                # React application
├── deployment/
│   ├── windows/            # Installer, services, Caddy, and scheduled backups
│   └── linux/              # Release packaging, installer, Caddy, and systemd services
├── docs/                   # Longer workflow and operating documentation
├── README.md
├── ARCHITECTURE.md
├── SECURITY.md
└── ROADMAP.md
```

The repository avoids placing all backend behavior in one module. Most persistence and workflow logic lives in domain-specific packages.

## Frontend Architecture

The frontend is located under:

```text
frontend/src/
```

Its main areas are:

```text
src/
├── api/
├── components/
├── hooks/
├── pages/
├── types/
├── utils/
├── App.tsx
└── main.tsx
```

### Application shell and routing

`App.tsx` coordinates the top-level application state. It is responsible for:

- Restoring the current authenticated session
- Tracking the signed-in user and role
- Loading and resolving governance status
- Preventing normal protected workflows until required governance setup is complete
- Clearing protected data after logout or session expiration
- Loading authorization records after authentication and governance prerequisites are satisfied
- Coordinating page navigation
- Passing user permissions into page and component workflows
- Managing session expiration and cross-tab session behavior

The application shell provides primary navigation, user context, theme controls, and logout access.

### API layer

The frontend API layer is under:

```text
frontend/src/api/
```

It contains clients for:

- Authentication, MFA, remembered-device, and session operations
- Governance status, acceptance, and history
- Authorization records
- Authorization timeline events
- Registered options
- PDF intake
- Backup and system operations where exposed to the frontend

The shared client:

- Sends browser credentials with authenticated requests
- Adds the CSRF token header to state-changing requests
- Uses a configurable development API base URL
- Uses same-origin requests when no override is present

The raw session token is not stored in frontend state or local storage. Authentication is handled through browser cookies.

### Pages and components

Top-level screens are under:

```text
frontend/src/pages/
```

These pages compose the main workflows, including:

- Dashboard
- Authorization queue
- Calendar
- Settings
- User administration
- Audit review

Reusable interface and workflow components are under:

```text
frontend/src/components/
```

These include forms, filters, data tables, charts, authorization detail views, timeline controls, PDF intake review, login and MFA screens, password-change screens, governance setup, and session timeout controls.

### Hooks and local preferences

Reusable state and workflow logic lives under:

```text
frontend/src/hooks/
```

Hooks manage areas such as:

- Authorization form state
- Authorization filtering
- Record selection
- Timeline events
- Mutations
- Registered options
- PDF intake previews
- Dashboard presentation
- Session activity and timeout behavior

Only non-sensitive interface preferences should be stored in browser persistence.

## Backend Architecture

The backend is located under:

```text
backend/authstatus_api/
```

The main package layout is:

```text
authstatus_api/
├── audit/
├── authorizations/
├── backups/
├── database_encryption/
├── governance/
├── observability/
├── pdf_intake/
├── persistence/
├── registered_options/
├── routers/
├── security/
├── system/
├── crypto.py
├── errors.py
├── main.py
├── schemas.py
└── settings.py
```

### Application startup

`main.py` creates the FastAPI application.

At startup it:

- Loads validated settings
- Configures application logging
- Registers CORS behavior
- Registers centralized exception handlers
- Initializes the database schema
- Registers API routers
- Exposes health and readiness endpoints

The application exposes:

```text
/api/health
/api/health/live
/api/health/ready
```

The liveness endpoint reports that the process is running. The readiness endpoint also checks that the configured database can be queried.

### Configuration

`settings.py` centralizes environment-based configuration.

It validates areas such as:

- Application environment
- Database path
- Database encryption mode
- Field-level encryption key
- SQLCipher key
- Backup encryption key
- Backup and restore locations
- CORS origins
- Session cookie settings
- Storage path safety

Production validation is intentionally stricter than development validation. Placeholder secrets, unsafe origins, and unexpected storage paths are rejected unless an explicit deployment setting permits them.

Secrets are supplied through environment variables or the production environment file. They are not intended to be committed to the repository.

## API Organization

Some domains expose routers directly from their package, while general application routers remain under:

```text
backend/authstatus_api/routers/
```

The API is divided into the following main areas:

- Security, MFA, trusted devices, and session management
- Governance status, acceptance, and history
- Authorization records and timeline events
- Dashboard analytics
- Registered facilities, insurers, and portal details
- PDF intake
- Backups
- System and recovery operations

Routers are kept relatively thin. Validation, persistence, encryption, and workflow behavior are handled by domain modules where practical.

## Authorization Domain

Authorization logic is under:

```text
backend/authstatus_api/authorizations/
```

Important responsibilities include:

- Creating, reading, updating, and deleting authorization records
- Managing authorization timeline events
- Calculating dashboard and workload summaries
- Mapping database rows into API responses
- Deriving workflow state
- Encrypting selected sensitive fields before persistence
- Decrypting selected fields for authorized responses
- Keeping SQL definitions separate from request handling

The authorization domain contains fixed SQL and controlled query construction rather than accepting arbitrary table or column input from requests.

## Persistence Layer

Shared persistence code is under:

```text
backend/authstatus_api/persistence/
```

It is responsible for:

- Opening SQLite or SQLCipher connections
- Applying the configured database mode
- Resolving approved data paths
- Initializing tables and indexes
- Coordinating schema migrations

Domain packages define their own tables where practical. This keeps authorization, security, governance, audit, registered-option, and backup concerns separate while still using the same database connection layer.

## Database and Encryption Boundaries

CareQueue uses more than one encryption layer.

### Database encryption

The database can run in either:

```text
sqlite
sqlcipher
```

SQLCipher mode encrypts the database file at rest using the configured SQLCipher key.

### Field-level encryption

Selected sensitive authorization fields are encrypted before they are written to the database. This uses a separate field-level encryption key.

Field-level encryption is independent of SQLCipher. A deployment may use both:

```text
Sensitive field
  |
  | Field-level encryption
  v
Encrypted value
  |
  | Stored inside SQLCipher database
  v
Encrypted database file
```

This separation limits the impact of a single exposed key and keeps sensitive-field handling explicit in the authorization domain.

### Backup encryption

Backups use a separate backup encryption key. The active database key and the backup key serve different purposes and should be stored and managed separately.

## Authentication, MFA, Sessions, and Governance

Authentication behavior is under:

```text
backend/authstatus_api/security/
```

Governance behavior is under:

```text
backend/authstatus_api/governance/
```

### Password authentication

The initial authentication path is:

```text
User submits username and password
  |
  v
Backend normalizes the username
  |
  v
Backend verifies the Argon2id password hash
  |
  +--> Invalid credentials update failed-login state
  |
  +--> Valid credentials continue to MFA or session creation
```

Repeated failed password attempts can temporarily lock the account.

### TOTP MFA

When MFA is enabled and no valid remembered-device token is accepted, password verification does not immediately create an authenticated session.

The flow becomes:

```text
Username and password accepted
  |
  v
Backend creates a short-lived MFA challenge
  |
  v
User submits current TOTP code
  |
  v
Backend verifies the challenge and code
  |
  v
Authenticated session is created
```

MFA secrets are encrypted before persistence.

Raw MFA challenge tokens are returned only to the client participating in the login flow. The backend stores a keyed digest rather than the raw challenge token.

### Remembered devices

After successful MFA verification, the user can optionally remember the device.

The trusted-device model is separate from the authenticated session:

```text
Password verification
  |
  v
Valid remembered-device token?
  |                    |
 yes                   no
  |                    |
  v                    v
Skip TOTP         Require MFA challenge
  |                    |
  +----------+---------+
             |
             v
      Create session
```

Remembered-device records have their own expiration and revocation state. The raw trusted-device token is kept in a protected browser cookie while the backend stores a keyed digest.

A remembered device does not bypass password verification and does not create a persistent authenticated session.

### Single active session

CareQueue allows one active authenticated session per account.

When a new authenticated session is created, previous active sessions for that user are revoked.

This rule applies whether the login completed through password-only authentication, MFA verification, or a valid remembered-device path.

### Server-side session validation

The browser receives the raw session token through an HttpOnly cookie. The backend stores only a hash of that token.

For authenticated requests:

```text
Browser sends session cookie
  |
  v
Backend hashes and verifies the session token
  |
  v
Session, user, expiration, revocation, and account state are checked
  |
  v
Required password-change state is checked
  |
  v
Governance state is checked for protected application routes
  |
  v
Role requirements are enforced
```

For state-changing requests, the frontend reads the CSRF cookie and sends its value in the configured CSRF header. The backend verifies that the cookie and header values match.

### Inactivity timeout

Authenticated sessions use a configurable server-side inactivity timeout. The default is 20 minutes.

Authenticated application activity can extend the expiration of a session that is still valid. The update is designed not to revive an already expired session.

The backend communicates the current expiration time to the frontend. The frontend uses that value to:

- Display the required expiration warning
- Offer explicit session renewal
- Keep expiration state aligned across open CareQueue tabs
- Clear protected state after logout or expiration

Session and CSRF tokens are rotated during explicit renewal.

Browser activity updates are throttled so ordinary interaction can extend the inactivity window without generating a request for every individual browser event.

The backend remains authoritative for session validity.

### Initial Admin setup

CareQueue does not provide public registration.

Packaged Windows and Linux installations include local first-time Admin setup workflows. These workflows submit the initial Admin credentials only to the loopback CareQueue API.

The bootstrap endpoint is available only while no users exist. After the first account is created, user management proceeds through authenticated Admin workflows or approved maintenance tooling.

### Governance prerequisite

After authentication and any required password change, CareQueue evaluates the current organization governance attestation.

The application flow is:

```text
Authenticated user
  |
  v
Required password change?
  | yes
  v
Password-change workflow
  |
  no
  v
Current governance attestation accepted?
  |                         |
 yes                        no
  |                         |
  v                         v
Normal application    Governance setup state
                            |
                            +--> Admin may accept
                            |
                            +--> Non-Admin waits for Admin completion
```

Normal protected application routes are rejected until the current governance attestation has been accepted.

The governance status endpoint remains available during setup so the frontend can determine which state to display. The Admin acceptance route also remains available before governance is current.

Each accepted attestation records:

```text
Attestation version
Document revision
Organization name
Deployment mode
Accepting user
Acceptance time
CareQueue application version
```

Attestation history is append-only and is also protected against direct update or deletion by database triggers. A future governance version or required document revision can require re-attestation without deleting prior records.

The governance attestation version, governance document revision, and CareQueue application version are separate values.

The attestation version identifies the required governance acceptance generation. The document revision identifies the exact governance text revision that was accepted. The CareQueue application version records which application release was running when the attestation was accepted.

A normal CareQueue application-version change does not by itself require re-attestation. A change to the required governance attestation version or required governance document revision does require a new acceptance.

Older governance records created before document-revision tracking was introduced may have no stored document revision. Those records are preserved as historical records rather than having a revision reconstructed or invented.

### Roles

CareQueue currently uses three roles:

- `Admin`
- `UR`
- `Read Only`

Backend dependencies enforce role requirements. Frontend role checks improve the interface but are not treated as the security boundary.

## Audit and Logging

Audit behavior is under:

```text
backend/authstatus_api/audit/
```

Audit records capture security, governance, authorization, document, backup, recovery, and administrative activity where supported by the workflow.

Current audit events are linked through a cryptographic hash chain. CareQueue stores the current chain head separately and provides an Admin integrity-verification workflow. Older pre-chain events may remain as legacy records and are reported separately during verification.

Operational logging is under:

```text
backend/authstatus_api/observability/
```

Application logging is configured according to the environment. Production logging is designed to avoid including credentials, session tokens, encryption keys, and protected field values.

Audit records and operational logs serve different purposes:

- **Audit records** describe user or application actions that may need later review.
- **Operational logs** help diagnose service behavior and failures.

Neither should be treated as a complete organizational compliance record by itself.

## Registered Options

Registered facilities, insurers, and related portal details are handled under:

```text
backend/authstatus_api/registered_options/
```

This domain supports reusable values that appear across authorization workflows.

Keeping these values separate from authorization records allows the application to:

- Reuse facility and payer details
- Keep portal metadata consistent
- Reduce repetitive data entry
- Manage options through settings rather than free text alone

## PDF Intake

PDF intake is under:

```text
backend/authstatus_api/pdf_intake/
```

The flow is:

```text
User selects a PDF
  |
  v
Frontend uploads it for preview
  |
  v
Backend reads embedded text in memory
  |
  v
Template and extraction rules identify candidate values
  |
  v
Confidence and review flags are returned
  |
  v
User confirms or corrects values
  |
  v
Accepted values enter the authorization form
```

The PDF is not treated as authoritative. Extracted values are only suggestions until reviewed.

The intake pipeline is designed to:

- Process supported documents locally
- Avoid external OCR services
- Identify malformed or unsupported PDFs
- Mark uncertain fields for review
- Require explicit confirmation for flagged values

Scanned PDFs without usable embedded text may not be extractable through the current pipeline.

## Backup and Recovery

Backup logic is under:

```text
backend/authstatus_api/backups/
```

The backup flow is:

```text
Active database
  |
  v
Consistent database copy
  |
  v
Backup encryption
  |
  v
Encrypted backup file
  |
  v
Verification and retention handling
```

Backups are never restored directly over the active database as the first step.

The restore flow is:

```text
Encrypted backup
  |
  v
Decrypt into approved restore area
  |
  v
Validate restored database
  |
  v
Stage recovery candidate
  |
  v
Activate through controlled recovery workflow
```

This separation reduces the chance of replacing the active database with an invalid or incomplete restore.

CareQueue also supports:

- Backup verification
- Retention periods
- A protected minimum backup count
- Windows scheduled backup tasks
- Linux systemd backup scheduling

## System and Recovery Operations

System-level operations are under:

```text
backend/authstatus_api/system/
```

This area coordinates operational actions that do not belong to the authorization domain, including recovery-related behavior exposed through the application.

Recovery paths are kept separate from the active database path. Production settings also restrict unsafe storage locations unless they are explicitly approved.

## Private Windows Deployment

Windows deployment files are under:

```text
deployment/windows/
```

Important files include:

```text
Caddyfile
CareQueue-AdminSetup.ps1
CareQueueApi.xml
CareQueueCaddy.xml
install-production.ps1
install-api-service.ps1
install-caddy-service.ps1
remove-api-service.ps1
remove-caddy-service.ps1
install-backup-task.ps1
remove-backup-task.ps1
run-api.ps1
installer/CareQueue.iss
installer/build-payload.ps1
installer/invoke-install.ps1
```

The packaged Windows installer is the normal private Windows installation path. The lower-level PowerShell scripts remain available for development, troubleshooting, and direct validation of install modes.

### Installed layout

The production installer uses:

```text
C:\Program Files\CareQueue
```

for installed application files, and:

```text
C:\ProgramData\CareQueue
```

for runtime data.

The runtime area contains locations for:

- Configuration
- Active data
- Backups
- Restore staging
- Recovery staging
- API logs
- Caddy data and logs

The installer generates independent production keys during the first installation and preserves the existing environment file during upgrades, repairs, and uninstall/reinstall flows that retain ProgramData.

### Windows services

The production deployment uses two Windows services:

```text
CareQueueApi
CareQueueCaddy
```

`CareQueueApi` runs FastAPI through Uvicorn on:

```text
127.0.0.1:8000
```

`CareQueueCaddy`:

- Serves the built frontend
- Terminates HTTPS
- Proxies `/api` requests to the API service
- Depends on the API service
- Stores its local certificate authority data under ProgramData

WinSW is used as the Windows service wrapper.

### Installer operation modes

When CareQueue is not installed, the packaged installer presents the normal install flow. When an existing installation is detected, it offers these operation modes:

- Upgrade existing installation
- Repair existing installation
- Uninstall CareQueue

Install, upgrade, and repair validate the service state and local API health after installation work completes. Uninstall removes Windows services and installed application files while preserving runtime data under ProgramData.

### Private HTTPS

A private Windows installation can use a local hostname such as:

```text
https://carequeue.local
```

The hostname resolves locally, and Caddy issues a certificate through its local certificate authority.

The Caddy root certificate must be trusted by the operating system or managed through an appropriate organizational certificate process.

This setup is private to the configured machine or network. It is not a public internet deployment.

## Linux Deployment

Linux deployment files are under:

```text
deployment/linux/
```

The packaged Linux deployment includes:

```text
Caddyfile
CareQueue-AdminSetup.sh
install-production.sh
uninstall-production.sh
installer/build-payload.ps1
installer/invoke-install.sh
systemd/carequeue-api.service
systemd/carequeue-backup.service
systemd/carequeue-backup.timer
systemd/carequeue-caddy.service
```

The Linux release is distributed as a versioned tar archive:

```text
CareQueue-Linux-Setup-<version>.tar.gz
```

The installer supports:

- Install
- Upgrade
- Repair
- Uninstall

The production layout separates application files from configuration, data, and logs.

The installer creates a dedicated `carequeue` service identity, installs the backend runtime and prebuilt frontend, preserves existing production configuration during upgrade or repair, installs systemd units, configures Caddy, enables encrypted backup scheduling, establishes private HTTPS trust, starts the services, and performs post-install health checks.

The packaged services keep FastAPI bound to:

```text
127.0.0.1:8000
```

and place Caddy in front of the application.

The default packaged private origin is:

```text
https://carequeue.local
```

The Linux deployment is intended for administrators comfortable with Linux, systemd, package installation, certificate trust, and operating-system permissions.

Automated rollback to a previous application release is not currently implemented.

## Testing Structure

Backend tests are under:

```text
backend/tests/
```

They are organized by domain, including authorization, security, governance, audit, backup, PDF intake, configuration, database encryption, observability, deployment, and system behavior.

Frontend tests are colocated under `__tests__` directories and use Vitest and Testing Library.

The primary checks are:

```powershell
pytest tests -n auto -q
ruff check . --fix
```

and:

```powershell
npm test
npm run build
```

Security-focused development checks also include Bandit, dependency auditing, npm audit, and code scanning.

## Design Principles

CareQueue follows several practical design rules.

### Local-first operation

The application is designed to operate without sending authorization data to a hosted CareQueue service.

### Explicit security boundaries

Password authentication, MFA, remembered-device handling, sessions, authorization, governance enforcement, CSRF handling, encryption, backup encryption, and audit behavior are separate concerns rather than one shared mechanism.

### Domain ownership

Authorization, security, governance, backup, audit, registered-option, PDF intake, and system behavior are grouped into their own backend packages.

### Backend-enforced access

The frontend may hide controls based on role, but the backend decides whether an action is allowed.

### Review before acceptance

PDF extraction and recovery operations require review or staging rather than silently changing active data.

### Separate development and production behavior

Development may use separate frontend and backend origins. Production uses same-origin HTTPS and stricter configuration validation.

### Controlled installation lifecycle

Packaged Windows and Linux install, upgrade, repair, and uninstall flows preserve runtime data and keys where appropriate, validate service health after installation work, and keep service orchestration inside the deployment layer.

## Current Limitations

The current architecture has several known boundaries:

- The built-in private HTTPS configurations are not public internet deployment templates.
- PDF intake depends on embedded PDF text and does not provide a general OCR pipeline.
- Technical controls and governance attestation do not establish HIPAA compliance by themselves.
- Operational monitoring, endpoint protection, periodic access review, incident response, secure key custody, and organizational policy remain deployment responsibilities.
- Automated rollback to a previous application release is not implemented across all packaged deployment paths.
- Linux deployment currently targets supported Debian-based systems and should be validated on the exact target operating-system version.
- Public DNS and publicly trusted certificate deployment require separate design and security review.
- A public demonstration environment must use synthetic data and independent credentials, keys, storage, and backups.

See [SECURITY.md](SECURITY.md) for security assumptions and reporting, and [ROADMAP.md](ROADMAP.md) for planned work.

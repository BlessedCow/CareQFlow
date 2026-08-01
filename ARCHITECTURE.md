# Architecture

CareQueue is a local-first utilization review and authorization tracking application. It uses a React and TypeScript frontend, a FastAPI backend, and SQLite or SQLCipher-backed persistence.

The application is organized around several separate concerns:

- Authorization records and timeline events
- Dashboard analytics and due-date workflows
- Authentication, sessions, roles, and CSRF protection
- Registered facilities, insurers, and portal details
- PDF-assisted intake
- Encrypted storage, backups, and staged recovery
- Audit and operational logging
- Private Windows deployment through Caddy and Windows services

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
│   └── linux/              # Linux Caddy and systemd files
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
- Clearing protected data after logout or session expiration
- Loading authorization records
- Coordinating page navigation
- Passing user permissions into page and component workflows
- Managing session expiration behavior

The application shell provides primary navigation, user context, theme controls, and logout access.

### API layer

The frontend API layer is under:

```text
frontend/src/api/
```

It contains clients for:

- Authentication and session operations
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

These include forms, filters, data tables, charts, authorization detail views, timeline controls, PDF intake review, login screens, password-change screens, and session timeout controls.

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
- Session timer preferences

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

- Security and session management
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

Domain packages define their own tables where practical. This keeps authorization, security, audit, registered-option, and backup concerns separate while still using the same database connection layer.

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

## Authentication and Session Flow

Authentication behavior is under:

```text
backend/authstatus_api/security/
```

The session flow is:

```text
User submits username and password
  |
  v
Backend verifies Argon2id password hash
  |
  v
Backend creates a server-side session
  |
  +--> Hashed session token stored in database
  |
  +--> Secure session cookie returned to browser
  |
  +--> CSRF cookie returned to browser
```

For authenticated requests:

```text
Browser sends session cookie
  |
  v
Backend hashes and verifies the session token
  |
  v
Session, user, role, expiration, and revocation are checked
```

For state-changing requests, the frontend reads the CSRF cookie and sends its value in the configured CSRF header. The backend verifies that the cookie and header values match.

Session tokens and CSRF tokens are rotated during renewal. Expired, revoked, or otherwise invalid sessions are rejected.

### Roles

CareQueue currently uses three roles:

- `Admin`
- `UR`
- `Read Only`

Backend dependencies enforce role requirements. Frontend role checks improve the interface but are not treated as the security boundary.

### Session expiration

The backend returns the current session expiration time to the frontend. The frontend uses that value to:

- Display the mandatory expiration warning
- Offer session renewal
- Optionally show a countdown
- Clear protected state after expiration

The backend remains authoritative for whether a session is valid.

## Audit and Logging

Audit behavior is under:

```text
backend/authstatus_api/audit/
```

Audit records capture security and authorization activity where supported by the workflow.

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
CareQueueApi.xml
CareQueueCaddy.xml
install-production.ps1
install-api-service.ps1
install-caddy-service.ps1
remove-api-service.ps1
remove-caddy-service.ps1
run-api.ps1
install-backup-task.ps1
remove-backup-task.ps1
run-backup.ps1
```

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

The installer generates independent production keys during the first installation and preserves the existing environment file during upgrades.

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

### Upgrade behavior

During a forced production upgrade, the installer:

```text
Detects running services
  |
  v
Stops Caddy
  |
  v
Stops the API
  |
  v
Replaces application files
  |
  v
Creates the production virtual environment
  |
  v
Installs dependencies
  |
  v
Validates the installed backend
  |
  v
Restores runtime permissions
  |
  v
Starts the API
  |
  v
Starts Caddy
```

Only services that were running before the upgrade are restarted. The installer also attempts to restore the original service state after a failure.

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

The repository currently includes:

- A Caddy configuration
- A systemd service for backups
- A systemd timer for scheduled backups

The Linux deployment path is less complete than the Windows path and still requires operating-system-specific setup and validation.

## Testing Structure

Backend tests are under:

```text
backend/tests/
```

They are organized by domain, including authorization, security, audit, backup, PDF intake, configuration, database encryption, observability, and system behavior.

Frontend tests are colocated under `__tests__` directories and use Vitest and Testing Library.

The primary checks are:

```powershell
pytest tests -n auto -q
python -m ruff check . --fix
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

Authentication, authorization, CSRF handling, encryption, backup encryption, and audit behavior are separate concerns rather than one shared mechanism.

### Domain ownership

Authorization, security, backup, audit, registered-option, PDF intake, and system behavior are grouped into their own backend packages.

### Backend-enforced access

The frontend may hide controls based on role, but the backend decides whether an action is allowed.

### Review before acceptance

PDF extraction and recovery operations require review or staging rather than silently changing active data.

### Separate development and production behavior

Development may use separate frontend and backend origins. Production uses same-origin HTTPS and stricter configuration validation.

### Controlled upgrades

Production upgrades preserve runtime data and keys, stop services in dependency order, validate the installed backend, and restore service state.

## Current Limitations

The current architecture has several known boundaries:

- It is primarily developed and validated on Windows.
- Linux deployment support is not yet equivalent to Windows deployment.
- The built-in private HTTPS configuration is not a public internet deployment template.
- PDF intake depends on embedded PDF text and does not provide a general OCR pipeline.
- Technical controls do not establish HIPAA compliance by themselves.
- Operational monitoring, endpoint protection, access reviews, incident response, and secure key custody remain deployment responsibilities.
- Migration and rollback workflows still need additional formalization.
- A public demo must use a separate instance with synthetic data and independent keys, storage, and backups.

See [SECURITY.md](SECURITY.md) for security assumptions and reporting, and [ROADMAP.md](ROADMAP.md) for planned work.

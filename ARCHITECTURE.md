# Architecture

CareQueue is a local-first utilization review workflow and authorization management application built with a React and TypeScript frontend and a FastAPI backend.

The application is organized around authorization tracking, timeline events, review due dates, payer and facility workflows, PDF-assisted intake, authentication, role-based access control, audit logging, encrypted storage, encrypted backups, and operational deployment support.

CareQueue is designed for private workflow development, testing, and controlled deployment evaluation. Its technical controls do not independently establish HIPAA compliance or production readiness.

## High-Level Overview

```text
Browser
  ↓
React, TypeScript, Vite, and Tailwind frontend
  ↓
Secure cookie authentication and CSRF-protected requests
  ↓
FastAPI backend
  ↓
Domain routers, services, and persistence modules
  ↓
SQLite or SQLCipher database
```

CareQueue currently supports local development and platform-specific deployment preparation.

```text
Development frontend:
http://localhost:5173

Development backend:
http://127.0.0.1:8000
```

Production exposure requires HTTPS, restricted network access, protected configuration, appropriate service accounts, operational monitoring, and additional organizational safeguards.

## Repository Layout

```text
CareQueue/
├── backend/
│   ├── authstatus_api/
│   │   ├── audit/
│   │   ├── authorizations/
│   │   ├── backups/
│   │   ├── database_encryption/
│   │   ├── observability/
│   │   ├── pdf_intake/
│   │   ├── persistence/
│   │   ├── registered_options/
│   │   ├── routers/
│   │   ├── security/
│   │   ├── crypto.py
│   │   ├── errors.py
│   │   ├── main.py
│   │   ├── schemas.py
│   │   └── settings.py
│   ├── scripts/
│   ├── tests/
│   │   ├── audit/
│   │   ├── authorizations/
│   │   ├── backups/
│   │   ├── configuration/
│   │   ├── database_encryption/
│   │   ├── observability/
│   │   ├── pdf_intake/
│   │   ├── registered_options/
│   │   ├── schemas/
│   │   ├── security/
│   │   └── conftest.py
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── pyproject.toml
│
├── deployment/
│   ├── linux/
│   │   └── systemd/
│   │       ├── carequeue-backup.service
│   │       └── carequeue-backup.timer
│   └── windows/
│       ├── install-backup-task.ps1
│       ├── remove-backup-task.ps1
│       └── run-backup.ps1
│
├── docs/
│   ├── README.md
│   ├── assets/
│   │   └── screenshots/
│   └── workflows/
│       └── backup-and-recovery.md
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── pages/
│   │   ├── types/
│   │   ├── utils/
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── .env.example
├── ARCHITECTURE.md
├── CONTRIBUTING.md
├── DISCLAIMER.md
├── README.md
├── ROADMAP.md
├── SECURITY.md
├── LICENSE
└── .gitignore
```

The application backend lives in:

```text
backend/authstatus_api/
```

The backend directory also contains operational scripts, dependency definitions, tooling configuration, and the domain-organized test suite.

## Frontend Architecture

The frontend is a React, TypeScript, Vite, and Tailwind application.

```text
frontend/src/
├── api/
├── components/
│   └── layout/
├── hooks/
├── pages/
├── types/
├── utils/
├── App.tsx
└── main.tsx
```

### `App.tsx`

`App.tsx` coordinates application-wide state and top-level workflows.

Responsibilities include:

- Restore an authenticated session
- Track the current user
- Track the server-provided session expiration
- Clear authenticated data after logout or expiration
- Coordinate page navigation
- Load authorization records
- Coordinate authorization filters, forms, selection, and timeline state
- Pass settings and permissions into page components
- Render the session timeout manager

Sensitive authorization data is cleared from frontend state when authentication ends.

### `api/`

The `api/` folder contains frontend clients for the FastAPI backend.

Current files include:

```text
authEvents.ts
authStatus.ts
client.ts
pdfIntake.ts
registeredOptions.ts
security.ts
```

Responsibilities include:

- Send authenticated requests with browser-managed cookies
- Attach CSRF headers to state-changing authenticated requests
- Call login, logout, current-user, and session-renewal endpoints
- Call authorization and timeline endpoints
- Call registered-option endpoints
- Submit in-memory PDF intake requests
- Convert API failures into frontend-safe errors

The frontend does not store the raw session token in application state.

### `pages/`

The `pages/` folder contains top-level application screens.

Current pages include:

```text
AdminAuditPage
AdminUsersPage
AuthorizationsPage
CalendarRoutePage
DashboardPage
SettingsPage
```

Responsibilities include:

- Compose page-level workflows
- Display dashboard and authorization data
- Coordinate page-specific filters and actions
- Expose administrative user and audit interfaces
- Render workflow and display settings

### `components/`

The `components/` folder contains reusable interface and workflow components.

Current examples include:

```text
AddAuthorizationForm
AuthTimelineSection
AuthorizationReadOnlyView
CalendarPage
Charts
DataTable
Filters
KPICards
LoginPage
PdfIntakeReviewPanel
RequiredPasswordChangePage
SessionTimeoutManager
UpcomingWorkflowCard
```

Responsibilities include:

- Render forms, tables, filters, charts, cards, and timeline events
- Provide create, edit, and read-only authorization workflows
- Display PDF intake extraction results
- Mark low-confidence fields that require review
- Require explicit confirmation before accepting flagged PDF values
- Display the mandatory session-expiration warning
- Optionally display the session countdown
- Support role-aware interface behavior

### `components/layout/`

The layout folder contains the application shell.

```text
AppShell
```

Responsibilities include:

- Render primary navigation
- Display current-user context
- Provide dark-mode controls
- Provide logout access
- Wrap authenticated page content

### `hooks/`

The `hooks/` folder contains reusable frontend state and workflow logic.

Current hooks include:

```text
useAuthorizationEvents
useAuthorizationFilters
useAuthorizationForm
useAuthorizationMutations
useAuthorizationSelection
useDashboardCardSettings
usePdfIntakePreview
useRegisteredOptions
useSessionTimerPreference
useWorkflowViewMode
```

Responsibilities include:

- Manage authorization form state and validation flow
- Load and modify timeline events
- Apply authorization filters
- Manage authorization selection and detail views
- Submit authorization mutations
- Manage registered facilities, insurers, and portals
- Process PDF intake previews
- Store non-sensitive display preferences
- Store the optional session-timer visibility preference
- Manage dashboard and workflow presentation settings

Only non-sensitive interface preferences should be stored in browser persistence.

### `types/`

The `types/` folder contains shared frontend TypeScript types.

Current files include:

```text
auth.ts
navigation.ts
```

### `utils/`

The `utils/` folder contains frontend helper logic.

Current files include:

```text
authEvents.ts
authSchedule.ts
authorizationFormValidation.ts
cn.ts
```

Responsibilities include:

- Format authorization events
- Calculate authorization schedule behavior
- Validate authorization form values
- Compose conditional CSS class names

## Frontend Session Management

The backend supplies an expiration timestamp during login and current-session restoration.

```text
Login or GET /api/security/me
  ↓
Frontend receives user and session expiration
  ↓
SessionTimeoutManager calculates remaining time
  ↓
Mandatory warning appears with five minutes remaining
  ↓
User renews the active session or logs out
```

The default authenticated session length is 20 minutes.

The warning threshold is five minutes.

The visible bottom-right countdown is:

- Optional
- Off by default
- Controlled from Settings
- Informational only
- Derived from the backend expiration timestamp

The warning modal remains mandatory even when the visible timer is hidden.

When a session expires, CareQueue clears authenticated frontend state and returns the user to the login screen.

## Backend Architecture

The FastAPI backend is located at:

```text
backend/authstatus_api/
```

The backend is divided into domain packages instead of relying on one large repository module.

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
├── crypto.py
├── errors.py
├── main.py
├── schemas.py
└── settings.py
```

### `main.py`

Creates and configures the FastAPI application.

Responsibilities include:

- Build the FastAPI application
- Configure centralized logging
- Register middleware
- Register routers
- Configure CORS
- Expose health behavior
- Initialize required persistence structures

### `settings.py`

Centralizes backend configuration.

Responsibilities include:

- Read environment settings
- Configure application environment
- Configure database path and encryption mode
- Configure field-level encryption
- Configure SQLCipher
- Configure encrypted backup and restore paths
- Configure CORS origins
- Enforce safe path behavior
- Provide production-sensitive defaults and validation

Important environment values include:

```env
AUTHSTATUS_APP_ENVIRONMENT=
AUTHSTATUS_ENCRYPTION_KEY=
AUTHSTATUS_SQLCIPHER_KEY=
AUTHSTATUS_BACKUP_ENCRYPTION_KEY=
AUTHSTATUS_DATABASE_PATH=
AUTHSTATUS_DATABASE_ENCRYPTION=
AUTHSTATUS_BACKUP_DIRECTORY=
AUTHSTATUS_RESTORE_DIRECTORY=
AUTHSTATUS_CORS_ORIGINS=
AUTHSTATUS_ALLOW_UNSAFE_DATABASE_PATH=
AUTHSTATUS_ALLOW_UNSAFE_STORAGE_PATHS=
```

Secrets must not be committed to the repository.

## Persistence Architecture

Persistence-related code is located at:

```text
backend/authstatus_api/persistence/
```

```text
persistence/
├── connections.py
├── migrations.py
├── paths.py
└── schema.py
```

### `connections.py`

Responsibilities include:

- Open SQLite or SQLCipher connections
- Apply configured database behavior
- Provide shared connection access to domain repositories
- Keep connection setup separate from domain logic

### `paths.py`

Responsibilities include:

- Resolve database and storage paths
- Enforce project-safe paths by default
- Permit intentional external deployment paths only when explicitly configured
- Prevent accidental writes to unexpected locations

### `schema.py`

Responsibilities include:

- Coordinate table creation
- Initialize domain-owned tables
- Keep schema setup separate from request handling

### `migrations.py`

Responsibilities include:

- Coordinate schema changes
- Preserve compatibility with existing local databases
- Apply controlled migration behavior

Individual domains own their table definitions where practical.

Examples include:

```text
audit/tables.py
authorizations/tables.py
registered_options/tables.py
security/tables.py
```

## Authorization Domain

Authorization behavior is located at:

```text
backend/authstatus_api/authorizations/
```

```text
authorizations/
├── analytics.py
├── encryption.py
├── events.py
├── mappings.py
├── records.py
├── sql.py
├── state.py
├── tables.py
└── timeline.py
```

### `records.py`

Responsibilities include:

- Create authorization records
- Read authorization records
- Update authorization records
- Delete authorization records
- Convert stored values into API-safe response data

### `events.py`

Responsibilities include:

- Create authorization timeline events
- Update timeline events
- Delete timeline events
- Apply fixed, parameterized update operations

### `timeline.py`

Responsibilities include:

- Build authorization timeline representations
- Coordinate event ordering and workflow state

### `analytics.py`

Responsibilities include:

- Calculate authorization dashboard summaries
- Support level-of-care and work-queue metrics
- Provide analytics data to router-level responses

### `encryption.py`

Responsibilities include:

- Identify sensitive authorization fields
- Encrypt selected values before persistence
- Decrypt selected values for authorized responses
- Keep encryption mapping separate from general persistence logic

### `mappings.py`

Responsibilities include:

- Convert database rows and stored representations
- Normalize authorization and event values
- Keep mapping logic out of routers

### `sql.py`

Responsibilities include:

- Store fixed SQL statements and controlled query construction
- Validate identifiers where dynamic selection is unavoidable
- Reduce SQL injection risk
- Keep SQL definitions separate from business logic

### `state.py`

Responsibilities include:

- Represent authorization workflow state
- Coordinate derived status behavior

### `tables.py`

Defines authorization-domain tables and indexes.

## Backend Routers

Primary API routers are located at:

```text
backend/authstatus_api/routers/
```

### `auths.py`

Authorization and timeline routes.

Responsibilities include:

- List authorization records
- Create authorization records
- Read one authorization record
- Update authorization records
- Delete authorization records
- List timeline events
- Create timeline events
- Update timeline events
- Delete timeline events
- Enforce authorization dependencies and role requirements

### `analytics.py`

Dashboard analytics routes.

Responsibilities include:

- Provide dashboard summary metrics
- Support frontend KPI and workload views

### `security.py`

Authentication and session routes.

Responsibilities include:

- Authenticate users
- Create secure browser sessions
- Return current-user and session-expiration information
- Renew active sessions
- Revoke sessions during logout
- Enforce CSRF validation for state-changing requests

Current session endpoints include:

```text
POST /api/security/login
GET  /api/security/me
POST /api/security/session/renew
POST /api/security/logout
```

## Security Architecture

Security-related backend code is located at:

```text
backend/authstatus_api/security/
```

```text
security/
├── csrf.py
├── dependencies.py
├── mappings.py
├── password_hashing.py
├── schemas.py
├── sessions.py
├── tables.py
├── temporary_passwords.py
└── users.py
```

### `users.py`

Responsibilities include:

- Create local users
- Find users
- Authenticate credentials
- Update supported user attributes
- Manage user state

### `password_hashing.py`

Passwords are hashed using Argon2id.

Plaintext passwords must never be stored.

### `sessions.py`

Responsibilities include:

- Generate session tokens
- Hash session tokens before persistence
- Create server-side session records
- Find active sessions
- Touch active sessions
- Renew active sessions
- Revoke individual sessions
- Revoke all sessions for a user
- Enforce expiration behavior

The default session duration is 20 minutes.

### `csrf.py`

Responsibilities include:

- Create CSRF tokens
- Extract expected CSRF values
- Validate state-changing authenticated requests
- Reject missing or mismatched tokens

### `dependencies.py`

Responsibilities include:

- Resolve the authenticated user
- Enforce active-session requirements
- Enforce role-based permissions
- Coordinate authentication and CSRF dependencies

### `temporary_passwords.py`

Responsibilities include:

- Support required password-change workflows
- Validate temporary-password state
- Keep first-login password handling separate from normal authentication

### `mappings.py`

Responsibilities include:

- Convert user and session records into safe response forms
- Keep response mapping separate from persistence logic

### `schemas.py`

Defines security request and response contracts.

### `tables.py`

Defines user and session tables.

## Authentication and Session Flow

Typical login flow:

```text
User submits credentials
  ↓
Frontend calls POST /api/security/login
  ↓
Backend verifies the Argon2id password hash
  ↓
Backend creates a server-side session
  ↓
Raw session token is placed in an HttpOnly cookie
  ↓
CSRF token is placed in a separate browser cookie
  ↓
Frontend receives user data and session expiration
```

Typical authenticated request flow:

```text
Browser sends secure session cookie
  ↓
Backend hashes the token
  ↓
Backend finds a matching active session
  ↓
Backend resolves the current user
  ↓
Backend enforces role requirements
  ↓
Request is processed
```

Typical state-changing request flow:

```text
Browser sends session cookie
  ↓
Frontend sends matching CSRF header
  ↓
Backend validates authentication and CSRF
  ↓
Backend performs the requested write
```

Typical renewal flow:

```text
Five-minute warning appears
  ↓
User selects Continue session
  ↓
Frontend calls POST /api/security/session/renew
  ↓
Backend validates the current session and CSRF token
  ↓
Backend extends session expiration
  ↓
Browser cookie lifetimes are refreshed
  ↓
Frontend receives the new expiration timestamp
```

Typical expiration flow:

```text
Server expiration is reached
  ↓
Frontend clears authenticated state
  ↓
Authorization and timeline data are removed from memory
  ↓
User returns to the login screen
```

## Role-Based Access Control

CareQueue supports:

```text
Admin
UR
Read Only
```

Role behavior:

```text
Admin:
Can manage users, review audit records, and manage authorization workflows.

UR:
Can view, create, edit, and delete authorization records and timeline events.

Read Only:
Can view records but cannot create, edit, or delete authorization data.
```

Backend authorization checks are authoritative.

The frontend also hides or disables unavailable controls, but frontend visibility is not treated as a security boundary.

## Registered Options Domain

Registered facilities, insurers, and portals are handled under:

```text
backend/authstatus_api/registered_options/
```

```text
registered_options/
├── repository.py
├── router.py
├── schemas.py
└── tables.py
```

Responsibilities include:

- List registered options
- Add supported options
- Remove supported options
- Protect required default values
- Validate request and response shapes
- Persist values separately from authorization records

## PDF Intake Architecture

PDF intake code is located at:

```text
backend/authstatus_api/pdf_intake/
```

```text
pdf_intake/
├── extractor.py
├── parsers/
├── request_body.py
├── router.py
└── schemas.py
```

Responsibilities include:

- Accept an uploaded PDF in memory
- Enforce expected content type and request limits
- Extract text locally
- Select a supported parser
- Return structured intake fields
- Attach confidence values
- Mark uncertain or missing fields as needing review
- Avoid persisting the uploaded PDF
- Avoid placing extracted PHI or PII into logs or audit metadata

The frontend displays extracted values in a review panel.

Fields marked for review must be confirmed or corrected before the values are accepted into the authorization workflow.

External OCR services are not required for the current text-based extraction path.

Scanned PDFs without an embedded text layer may require a separately evaluated local OCR workflow in the future.

## Data Protection Architecture

CareQueue uses layered data protection.

```text
Field-level encryption
  ↓
SQLCipher database encryption
  ↓
Separately encrypted backups
  ↓
Restricted scheduler and storage permissions
```

Each layer protects a different part of the data lifecycle and uses separately managed keys.

### Field-Level Encryption

Implemented through:

```text
backend/authstatus_api/crypto.py
backend/authstatus_api/authorizations/encryption.py
```

Configured with:

```env
AUTHSTATUS_ENCRYPTION_KEY=
```

Selected sensitive fields are encrypted before they are stored.

The same key is required to decrypt existing field values.

Loss of the field-encryption key may make protected values unrecoverable.

### SQLCipher Database Encryption

Implemented through:

```text
backend/authstatus_api/database_encryption/
backend/authstatus_api/persistence/connections.py
```

Configured with:

```env
AUTHSTATUS_DATABASE_ENCRYPTION=sqlcipher
AUTHSTATUS_SQLCIPHER_KEY=
```

SQLCipher protects the database file at rest.

A plaintext development mode remains available:

```env
AUTHSTATUS_DATABASE_ENCRYPTION=plaintext
```

Plaintext mode should not be used for production PHI or PII.

### Encrypted Backups

Implemented in:

```text
backend/authstatus_api/backups/service.py
```

Configured with:

```env
AUTHSTATUS_BACKUP_ENCRYPTION_KEY=
AUTHSTATUS_BACKUP_DIRECTORY=
AUTHSTATUS_RESTORE_DIRECTORY=
```

Encrypted backup files use:

```text
*.db.enc
```

Backup encryption is separate from SQLCipher database encryption.

Restore operations write to a safe restore directory and do not automatically overwrite the active database.

## Backup Scheduling Architecture

CareQueue includes platform-specific backup scheduling helpers.

```text
deployment/
├── linux/
│   └── systemd/
└── windows/
```

### Windows

Windows files include:

```text
deployment/windows/run-backup.ps1
deployment/windows/install-backup-task.ps1
deployment/windows/remove-backup-task.ps1
```

The Windows workflow:

```text
Task Scheduler
  ↓
run-backup.ps1
  ↓
Protected environment file is loaded into process scope
  ↓
create_encrypted_backup.py
  ↓
Encrypted backup is written to an isolated directory
```

The installer defaults to:

```text
Installation:
C:\Program Files\CareQueue

Operational data:
C:\ProgramData\CareQueue

Backups:
C:\ProgramData\CareQueue\Backups

Configuration:
C:\ProgramData\CareQueue\Config\carequeue.env
```

The task runs as `SYSTEM` by default and may be configured to use a dedicated service account.

Task registration requires elevated PowerShell.

### Linux

Linux files include:

```text
deployment/linux/systemd/carequeue-backup.service
deployment/linux/systemd/carequeue-backup.timer
```

The Linux workflow:

```text
systemd timer
  ↓
carequeue-backup.service
  ↓
Protected environment file is loaded
  ↓
create_encrypted_backup.py
  ↓
Encrypted backup is written to isolated storage
```

The supplied service expects:

```text
Application:
 /opt/carequeue

Environment file:
 /etc/carequeue/carequeue.env

Backup directory:
 /var/lib/carequeue/backups
```

The systemd service applies filesystem and process restrictions, including a restrictive file-creation mask and a limited writable path.

Scheduled execution does not replace periodic restoration testing.

## Observability Architecture

Production logging code is located at:

```text
backend/authstatus_api/observability/
```

```text
observability/
├── filters.py
├── logging.py
└── sanitization.py
```

### `sanitization.py`

Responsibilities include:

- Mask known sensitive fields
- Sanitize structured values
- Remove authorization headers, cookies, session values, and tokens
- Avoid rendering raw exception messages

### `filters.py`

Responsibilities include:

- Apply sanitization to log records
- Prevent sensitive values from reaching configured handlers

### `logging.py`

Responsibilities include:

- Configure application logging centrally
- Apply sanitization consistently
- Preserve useful operational context without exposing PHI, PII, credentials, or session material

Production logs may retain exception class names while removing traceback details and raw exception messages.

Logging controls reduce risk but must still be supported by restricted log access, retention rules, and operational review.

## Audit Logging

Audit logging is implemented in:

```text
backend/authstatus_api/audit/service.py
```

Audit tables are defined in:

```text
backend/authstatus_api/audit/tables.py
```

Audit logging covers selected actions such as:

```text
security.login
security.login_failed
security.logout
auth.create
auth.update
auth.delete
auth_event.create
auth_event.update
auth_event.delete
```

Audit metadata should contain only the minimum information needed to identify the action.

Preferred metadata includes:

```text
record IDs
action names
changed field names
event types
user IDs
```

Audit metadata should not contain:

```text
patient or client names
member IDs
group numbers
dates of birth
authorization numbers tied to identifiable people
clinical notes
uploaded PDF text
free-text PHI or PII
credentials
session tokens
CSRF tokens
```

## Database Architecture

CareQueue uses local SQLite-compatible storage.

Core tables include:

```text
auths
auth_events
registered_options
users
sessions
audit_events
```

### `auths`

Stores authorization records and workflow fields.

Examples include:

```text
facility
payer
level of care
authorization type
status
start date
end date
review due date
member details
submission details
decision details
notes
```

Selected sensitive values are encrypted before persistence.

### `auth_events`

Stores authorization timeline events.

Examples include:

```text
event type
status
start date
end date
review due date
decision date
notes
```

### `registered_options`

Stores configurable facilities, insurers, and portal options.

### `users`

Stores local application users.

Passwords are stored as Argon2id hashes.

### `sessions`

Stores server-side session records.

Stored session values include:

```text
hashed token
user reference
creation time
last-seen time
expiration time
revocation time
```

Raw session tokens are not stored in the database.

### `audit_events`

Stores selected authentication, administration, and authorization actions.

Audit metadata must not contain sensitive field values.

## Authorization API Flow

Typical authorization list flow:

```text
Frontend calls GET /api/auths
  ↓
Browser sends session cookie
  ↓
Backend verifies the active session
  ↓
Backend checks the user role
  ↓
Authorization records are loaded
  ↓
Sensitive fields are decrypted
  ↓
Safe response data is returned
```

Typical create or update flow:

```text
Frontend submits authorization data
  ↓
Backend validates the request schema
  ↓
Backend verifies authentication, CSRF, and write permission
  ↓
Sensitive values are encrypted
  ↓
Authorization domain writes the change
  ↓
Audit metadata is recorded
  ↓
Updated response data is returned
```

Typical timeline-event flow:

```text
Frontend submits an event
  ↓
Backend validates permissions and payload
  ↓
Authorization event module writes the event
  ↓
Authorization state and timeline are refreshed
  ↓
Audit event is recorded
```

## Scripts

Maintenance and operational scripts live in:

```text
backend/scripts/
```

Current script categories include:

```text
user creation
development data seeding
PDF intake inspection
encrypted backup creation
encrypted backup restoration
SQLCipher migration
SQLCipher verification
SQLCipher cutover preparation
```

Examples include:

```text
create_user.py
seed_dev_auths.py
inspect_pdf_intake.py
create_encrypted_backup.py
restore_encrypted_backup.py
migrate_to_sqlcipher.py
verify_sqlcipher_database.py
prepare_sqlcipher_cutover.py
```

### User Creation

`create_user.py` creates local users because CareQueue does not provide public self-registration.

### Development Data

`seed_dev_auths.py` creates development authorization records.

Development data must be fictional or clearly synthetic.

### PDF Inspection

`inspect_pdf_intake.py` supports local inspection of PDF extraction behavior without sending files to an external service.

### Backup and Restore

```text
create_encrypted_backup.py
restore_encrypted_backup.py
```

These scripts create separately encrypted database backups and restore them into a safe destination.

### SQLCipher

```text
migrate_to_sqlcipher.py
verify_sqlcipher_database.py
prepare_sqlcipher_cutover.py
```

These scripts support migration, verification, and controlled preparation for SQLCipher database use.

## Runtime Data

Runtime files and sensitive operational data should not be committed.

Examples include:

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
```

Environment files, encryption keys, production databases, real intake PDFs, generated backups, and restore outputs must remain outside version control.

## Testing Architecture

Backend tests are organized by application domain.

```text
backend/tests/
├── audit/
├── authorizations/
├── backups/
├── configuration/
├── database_encryption/
├── observability/
├── pdf_intake/
├── registered_options/
├── schemas/
├── security/
└── conftest.py
```

Shared fixtures remain in:

```text
backend/tests/conftest.py
```

Run backend tests from `backend`:

```bash
pytest tests -n auto -q
```

Run Ruff from `backend`:

```bash
python -m ruff check . --fix
```

Run Bandit from `backend`:

```bash
bandit -r authstatus_api
```

Run the frontend build check from `frontend`:

```bash
npm run build
```

Test modules should use unique basenames because pytest may import test files as top-level modules depending on the active configuration.

## Current Limitations

CareQueue is not independently production-ready or HIPAA compliant.

Current limitations include:

- No complete hosted deployment reference architecture
- No integrated HTTPS or reverse-proxy deployment package
- No production secret-manager integration
- No external identity provider or single sign-on integration
- No multi-tenant data isolation
- No automated backup retention policy
- No automated backup-health notification
- No continuous restore verification
- No formal disaster-recovery exercise record
- Limited frontend automated testing
- Text-based PDF extraction does not process all scanned documents
- No independent security assessment
- No formal compliance review
- No executed business associate agreements
- No organizational policies or workforce training supplied by the application
- No guarantee that a local machine or deployment host is appropriately secured

## Design Principles

CareQueue should prioritize:

- Local-first development safety
- Explicit authentication and authorization
- Server-enforced session expiration
- PHI and PII minimization
- Backend-enforced permissions
- Secure defaults
- Layered encryption
- Separate key responsibilities
- Safe database and storage paths
- Audit metadata without sensitive values
- Sanitized operational logging
- In-memory PDF processing where practical
- Explicit human review of uncertain extracted data
- Isolated encrypted backups
- Periodic restore testing
- Domain-focused modules
- Domain-organized tests
- Small, reviewable changes
- Straightforward architecture over unnecessary abstraction
- Honest documentation of limitations
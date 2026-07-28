# CareQueue

CareQueue is a local-first utilization review workflow and authorization management application for tracking prior authorization work, review dates, payer decisions, timeline events, documentation intake, and follow-up queues.

It combines a FastAPI backend with a React, TypeScript, Vite, and Tailwind frontend. CareQueue includes application-level security controls, encrypted storage options, encrypted backup and recovery utilities, role-based access, audit logging, and operational deployment helpers.

CareQueue is intended for private workflow development, testing, and controlled deployment evaluation. It is not HIPAA compliant by itself, and deploying it does not replace an organization’s required administrative, physical, technical, legal, contractual, and operational safeguards.

## Important Disclaimer

CareQueue may handle sensitive operational or health-adjacent information during local testing. Do not use real patient data unless you understand and accept the privacy, security, compliance, legal, and organizational responsibilities involved.

Security features in this project reduce risk, but they do not create HIPAA compliance on their own. See `DISCLAIMER.md` and `SECURITY.md`.

## Features

### Authorization workflow

- Track initial, continued stay, and level-of-care authorization work
- Store facility, payer, level of care, member details, authorization dates, review dates, and outcomes
- Track pending, approved, denied, appealed, P2P, no-PA-required, discharged, and completed workflows
- Maintain authorization timeline events
- Support continued stay / LOC workflow transitions
- View authorization records in dashboard, calendar, table, and detail views

### Frontend

### Frontend

- React, TypeScript, Vite, and Tailwind interface
- Login screen and authenticated session restoration
- Twenty-minute server-enforced sessions
- Mandatory warning during the final five minutes of a session
- Session renewal without exposing the session token to application code
- Optional bottom-right session countdown that is off by default
- Role-aware UI controls
- Dashboard KPI cards and workload summaries
- Level-of-care and work-queue filtering
- Calendar view for review dates, start dates, end dates, and closed authorization events
- Authorization work queue with filters, sorting, and pagination
- Read-only authorization detail view
- Timeline event management
- PDF intake review workflow with confidence and needs-review indicators
- Explicit confirmation before accepting fields marked for review
- Settings for registered facilities, insurances, portals, workflow views, dashboard cards, and session-timer visibility
- Dark mode
- Local browser persistence for non-sensitive UI preferences

### Backend

### Backend

- FastAPI API
- SQLite storage with SQLCipher database-encryption support
- Field-level encryption for selected sensitive authorization fields
- Argon2id password hashing
- Server-side sessions with hashed session tokens
- CSRF protection for authenticated state-changing requests
- Configurable session renewal and expiration
- Role-based access control
- Audit logging for authentication, user administration, and authorization changes
- PHI-conscious production logging with centralized sanitization
- Structured authorization, security, persistence, audit, backup, and PDF-intake modules
- Local PDF text extraction without requiring an external OCR service
- Confidence and review metadata for extracted intake fields
- Encrypted database backup and safe restore utilities
- Windows Task Scheduler deployment scripts for automated encrypted backups
- Linux systemd service and timer definitions for automated encrypted backups
- SQLCipher migration, verification, and cutover preparation scripts
- Domain-organized backend tests covering API, persistence, security, audit, backups, logging, PDF intake, and SQLCipher behavior

## Current Security Model

CareQueue currently uses layered local security controls:

```text
Field-level encryption:
Sensitive fields are encrypted before being stored.

SQLCipher mode:
The SQLite database file can be encrypted at rest.

Encrypted backups:
Backup copies are encrypted separately and may be scheduled through Windows Task Scheduler or a Linux systemd timer.

Authentication:
Users log in with hashed passwords.

Sessions:
Raw session tokens remain in secure browser cookies. The backend stores token hashes.

Session expiration:
Authenticated sessions expire after 20 minutes. A mandatory warning appears during the final 5 minutes, and authorized users may renew an active session.

CSRF protection:
Authenticated state-changing requests require a matching CSRF token.

Logging:
Production logging applies centralized sanitization intended to prevent credentials, session values, sensitive fields, and exception details from being written to logs.

Roles:
Admin and UR users can manage records. Read Only users can view records.

Audit logging:
Security and authorization actions are recorded without storing PHI values in audit metadata.
```

The three key types are separate and should not be mixed:

```env
AUTHSTATUS_ENCRYPTION_KEY=field-level Fernet encryption key
AUTHSTATUS_SQLCIPHER_KEY=SQLCipher database key
AUTHSTATUS_BACKUP_ENCRYPTION_KEY=encrypted backup file key
```

## Project Structure

```text
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
│   │   │   ├── layout/
│   │   │   └── security/
│   │   ├── hooks/
│   │   ├── pages/
│   │   ├── types/
│   │   └── utils/
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

## Backend Setup

From the repository root:

```bash
cd backend
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

Create a root runtime environment file:

```text
.env
```

Use `.env.example` as the template.

Generate keys:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Run that command separately for:

```env
AUTHSTATUS_ENCRYPTION_KEY=
AUTHSTATUS_BACKUP_ENCRYPTION_KEY=
```

For `AUTHSTATUS_SQLCIPHER_KEY`, use a long local passphrase or another securely generated value.

Recommended SQLCipher `.env` configuration:

```env
AUTHSTATUS_ENCRYPTION_KEY=your-field-encryption-key
AUTHSTATUS_SQLCIPHER_KEY=your-sqlcipher-key
AUTHSTATUS_BACKUP_ENCRYPTION_KEY=your-backup-encryption-key

AUTHSTATUS_DATABASE_PATH=backend/data/auth_tracker.sqlcipher.db
AUTHSTATUS_DATABASE_ENCRYPTION=sqlcipher
AUTHSTATUS_ALLOW_UNSAFE_DATABASE_PATH=false

AUTHSTATUS_BACKUP_DIRECTORY=backend/backups
AUTHSTATUS_RESTORE_DIRECTORY=backend/restores
AUTHSTATUS_CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]
```

Plaintext SQLite fallback configuration:

```env
AUTHSTATUS_ENCRYPTION_KEY=your-field-encryption-key
AUTHSTATUS_SQLCIPHER_KEY=your-sqlcipher-key
AUTHSTATUS_BACKUP_ENCRYPTION_KEY=your-backup-encryption-key

AUTHSTATUS_DATABASE_PATH=backend/data/auth_tracker.db
AUTHSTATUS_DATABASE_ENCRYPTION=plaintext
AUTHSTATUS_ALLOW_UNSAFE_DATABASE_PATH=false

AUTHSTATUS_BACKUP_DIRECTORY=backend/backups
AUTHSTATUS_RESTORE_DIRECTORY=backend/restores
AUTHSTATUS_CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]
```

Only one database mode should be active at a time.

Start the backend:

```bash
uvicorn authstatus_api.main:create_app --factory --host 127.0.0.1 --port 8000
```

Health check:

```text
http://127.0.0.1:8000/api/health
```

## Frontend Setup

From the repository root:

```bash
cd frontend
npm install
npm run dev
```

The frontend uses this default backend API URL if no Vite environment override is provided:

```text
http://127.0.0.1:8000
```

The frontend usually runs at:

```text
http://localhost:5173
```

## Creating the First User

There is no public signup screen. Create users locally from the backend script.

From the repository root:

```bash
python backend/scripts/create_user.py --username admin@example.com --role Admin
```

Available roles:

```text
Admin
UR
Read Only
```

Role behavior:

```text
Admin:
Can view, create, edit, and delete authorization records and timeline events.

UR:
Can view, create, edit, and delete authorization records and timeline events.

Read Only:
Can view records but does not see create, edit, or delete controls.
```

## Documentation

Additional project documentation is available in the repository root and under `docs/`.

- `ARCHITECTURE.md` explains the frontend, backend, persistence, security, audit, backup, logging, and PDF-intake structure.
- `ROADMAP.md` tracks completed milestones, near-term priorities, and longer-term development direction.
- `SECURITY.md` describes security controls, key handling, sessions, CSRF protection, logging, encrypted storage, backups, and reporting guidance.
- `DISCLAIMER.md` explains project limitations, PHI and PII warnings, and compliance boundaries.
- `CONTRIBUTING.md` explains contribution expectations, testing, privacy rules, repository organization, and pull request guidance.
- `docs/workflows/backup-and-recovery.md` documents manual and scheduled encrypted backups, restoration, verification, Windows Task Scheduler, and Linux systemd operation.
- `deployment/windows/` contains Windows backup runner, installer, and removal scripts.
- `deployment/linux/systemd/` contains the Linux backup service and timer definitions.
- `docs/assets/screenshots/` is reserved for sanitized screenshots created with entirely synthetic data.

## API Endpoints

```text
GET    /api/health

POST   /api/security/login
POST   /api/security/logout
GET    /api/security/me
POST   /api/security/session/renew

GET    /api/auths
POST   /api/auths
GET    /api/auths/{auth_id}
PATCH  /api/auths/{auth_id}
DELETE /api/auths/{auth_id}

GET    /api/auths/{auth_id}/events
POST   /api/auths/{auth_id}/events
PATCH  /api/auths/{auth_id}/events/{event_id}
DELETE /api/auths/{auth_id}/events/{event_id}

GET    /api/analytics/summary
```

Most API routes require an authenticated secure cookie. State-changing authenticated requests also require CSRF validation.

## Encrypted Backups

Create an encrypted backup of the active database:

```bash
python backend/scripts/create_encrypted_backup.py
```

Backups are written to:

```text
backend/backups/
```

Backup files end in:

```text
.db.enc
```

Restore an encrypted backup to a safe restore location:

```bash
python backend/scripts/restore_encrypted_backup.py backend/backups/<backup-file>.db.enc
```

Restores are written to:

```text
backend/restores/
```

The restore script does not overwrite the active database.

### Automated backup scheduling

CareQueue includes platform-specific scheduling files:

```text
deployment/windows/
deployment/linux/systemd/
```
Windows deployments may register the encrypted backup utility through Task Scheduler. Linux deployments may use the supplied systemd service and timer.

Detailed setup, verification, removal, recovery, and troubleshooting instructions are available in:
`docs/workflows/backup-and-recovery.md`

Scheduled backups should write to an isolated storage path outside the active application installation and database directory. Backup files, environment files, and encryption keys must remain restricted to authorized service accounts and administrators.

## SQLCipher Workflow

CareQueue supports optional SQLCipher database-file encryption.

Prepare a safe SQLCipher cutover:

```bash
python backend/scripts/prepare_sqlcipher_cutover.py --force
```

This will:

```text
1. Create an encrypted backup of the plaintext database
2. Create a SQLCipher encrypted database copy
3. Verify required CareQueue tables
4. Print the .env values needed to switch to SQLCipher mode
5. Avoid deleting the plaintext database
```

The SQLCipher database is usually created at:

```text
backend/data/auth_tracker.sqlcipher.db
```

Verify a SQLCipher database manually:

```bash
python backend/scripts/verify_sqlcipher_database.py
```

Create only the SQLCipher copy manually:

```bash
python backend/scripts/migrate_to_sqlcipher.py
```

Recommended local switch to SQLCipher mode:

```env
AUTHSTATUS_DATABASE_PATH=../data/auth_tracker.sqlcipher.db
AUTHSTATUS_DATABASE_ENCRYPTION=sqlcipher
AUTHSTATUS_SQLCIPHER_KEY=your-sqlcipher-key
```

Keep the plaintext database until SQLCipher mode has been tested through normal app use.

## Testing

Backend tests:

```bash
cd backend
pytest tests -n auto -q
```

Ruff:

```bash
python -m ruff check . --fix
```

Security scan:
```bash
bandit -r authstatus_api
```

Frontend build check:

```bash
cd frontend
npm run build
```

## Files That Should Not Be Committed

The following files and directories are local runtime data, generated artifacts, or sensitive configuration and should remain ignored:

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

Before committing, check the staged and unstaged files:

```bash
git status --short
```

Do not commit databases, encrypted backups, restored databases, environment files, encryption keys, real intake PDFs, screenshots containing sensitive information, virtual environments, caches, or `node_modules`.


## Development Notes

- The FastAPI backend lives in `backend/authstatus_api`.
- Backend tests are organized by application domain under `backend/tests`.
- The frontend lives in `frontend/src`.
- The application uses a local-first architecture and should not be exposed publicly without a documented deployment model and additional production hardening.
- Session expiration is enforced by the backend. The frontend countdown is informational only.
- The visible session countdown is optional and off by default. The five-minute expiration warning remains mandatory.
- Uploaded PDFs are processed for intake extraction and should not be persisted or logged by the intake workflow.
- Screenshots and examples must use synthetic data only.
- Scheduled backup success does not replace periodic restore testing.
- Security controls reduce risk but do not independently establish regulatory compliance.

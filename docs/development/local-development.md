# Local Development

This guide covers setting up and running CareQueue locally for development and testing.

Development is separate from packaged Windows and Linux deployment. Use this guide when working on source code, running tests, or testing the application with the backend and frontend development servers.

For packaged deployment, see:

- [Windows Deployment](../deployment/windows.md)
- [Linux Deployment](../deployment/linux.md)

For health validation, see [Health Checks](../operations/health-checks.md).

For backup and restore procedures, see [Backup and Recovery](../workflows/backup-and-recovery.md).

## Development Stack

CareQueue development uses:

- Python and FastAPI for the backend
- React, TypeScript, Vite, and Tailwind for the frontend
- SQLite or SQLCipher for local data storage
- Separate backend and frontend development servers
- Local application accounts stored in the active development database
- TOTP MFA and remembered-device authentication
- Versioned governance attestation

## Development Architecture

```text
Browser
  |
  | http://localhost:5173
  v
Vite development server
  |
  | API requests
  v
FastAPI
  |
  | http://127.0.0.1:8000
  v
SQLite or SQLCipher database
```

Packaged production deployment uses a different shape: operating-system services, packaged runtime dependencies, Caddy, and `https://carequeue.local`. Do not use the development server setup as proof that a packaged Windows or Linux release works.

## Prerequisites

Install:

- Git
- Python 3.11 or newer
- Node.js
- npm
- PowerShell on Windows
- A code editor

PowerShell examples in this guide assume Windows development. Equivalent tooling may be used on other supported development systems when the repository dependencies are available.

## Clone the Repository

```powershell
git clone https://github.com/BlessedCow/CareQueue.git
Set-Location CareQueue
```

Review the checkout:

```powershell
git status --short
```

A clean checkout should not contain environment files, local databases, backups, or real PDFs.

## Repository Layout

```text
CareQueue/
├── backend/
│   ├── authstatus_api/
│   ├── scripts/
│   ├── tests/
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
├── deployment/
├── docs/
├── .env.example
└── README.md
```

## Backend Setup

From the repository root:

```powershell
Set-Location backend
```

Create the virtual environment:

```powershell
py -3.14 -m venv .venv
```

When that launcher version is unavailable:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Confirm the interpreter:

```powershell
python --version
python -c "import sys; print(sys.executable)"
```

The executable should come from:

```text
backend\.venv\Scripts\python.exe
```

Do not select a packaged runtime under `build\windows\components\python-runtime` or `build\windows\payload\runtime\python` as the project interpreter. Those paths are build artifacts for installer packaging, not development environments.

### PowerShell Activation Policy

When activation is blocked:

```powershell
Set-ExecutionPolicy `
    -Scope Process `
    -ExecutionPolicy Bypass
```

Then activate again.

Do not weaken the machine-wide policy merely to activate the virtual environment.

## Install Backend Dependencies

With the virtual environment active:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

## Development Environment File

Copy the example file from the repository root:

```powershell
Copy-Item `
    ".env.example" `
    ".env"
```

The development `.env` belongs at:

```text
CareQueue\.env
```

It must remain uncommitted.

Do not use production keys or real patient data in development.

## Required Development Keys

CareQueue uses three separate keys:

```text
AUTHSTATUS_ENCRYPTION_KEY
AUTHSTATUS_SQLCIPHER_KEY
AUTHSTATUS_BACKUP_ENCRYPTION_KEY
```

Generate a Fernet key:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Run it separately for:

```text
AUTHSTATUS_ENCRYPTION_KEY
AUTHSTATUS_BACKUP_ENCRYPTION_KEY
```

Use another independent long random value for:

```text
AUTHSTATUS_SQLCIPHER_KEY
```

Do not reuse one key across protection layers.

## Recommended Development Configuration

A SQLCipher development configuration resembles:

```env
AUTHSTATUS_APP_ENVIRONMENT=development

AUTHSTATUS_ENCRYPTION_KEY=<field-level Fernet key>
AUTHSTATUS_SQLCIPHER_KEY=<independent SQLCipher key>
AUTHSTATUS_BACKUP_ENCRYPTION_KEY=<backup Fernet key>

AUTHSTATUS_DATABASE_PATH=backend/data/auth_tracker.sqlcipher.db
AUTHSTATUS_DATABASE_ENCRYPTION=sqlcipher
AUTHSTATUS_ALLOW_UNSAFE_DATABASE_PATH=false
AUTHSTATUS_ALLOW_UNSAFE_STORAGE_PATHS=false

AUTHSTATUS_BACKUP_DIRECTORY=backend/backups
AUTHSTATUS_BACKUP_RETENTION_DAYS=90
AUTHSTATUS_BACKUP_MINIMUM_COUNT=5
AUTHSTATUS_RESTORE_DIRECTORY=backend/restores

AUTHSTATUS_CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]

AUTHSTATUS_SESSION_COOKIE_SECURE=false
AUTHSTATUS_SESSION_COOKIE_NAME=carequeue_session
AUTHSTATUS_SESSION_INACTIVITY_MINUTES=20
AUTHSTATUS_CSRF_COOKIE_NAME=carequeue_csrf
AUTHSTATUS_TRUSTED_DEVICE_COOKIE_NAME=carequeue_trusted_device
AUTHSTATUS_CSRF_HEADER_NAME=X-CSRF-Token

VITE_AUTHSTATUS_API_BASE_URL=http://localhost:8000
```

Replace placeholders with local values.

Do not commit the completed file.

## Plaintext SQLite Mode

For limited local development:

```env
AUTHSTATUS_DATABASE_PATH=backend/data/auth_tracker.db
AUTHSTATUS_DATABASE_ENCRYPTION=plaintext
```

Only one database mode should be active at a time.

Plaintext mode does not provide database-file encryption and must not be used for production data.

## Frontend Environment

Prefer:

```text
frontend/.env.development.local
```

with:

```env
VITE_AUTHSTATUS_API_BASE_URL=http://localhost:8000
```

Do not place the localhost override in production frontend environment files.

The production frontend should use same-origin `/api` requests.

## Start the Backend

From `backend` with the virtual environment active:

```powershell
uvicorn `
    authstatus_api.main:create_app `
    --factory `
    --host 127.0.0.1 `
    --port 8000
```

Backend origin:

```text
http://127.0.0.1:8000
```

Use [Health Checks](../operations/health-checks.md#local-development) to verify liveness and readiness.

## Start the Frontend

Open a second terminal.

From `frontend`:

```powershell
npm ci
npm run dev
```

Frontend origin:

```text
http://localhost:5173
```

Use `npm install` instead of `npm ci` only when intentionally changing frontend dependencies.

Do not commit `node_modules`.

## Create the First Development User

CareQueue has no public registration.

From the repository root with the backend environment active:

```powershell
python backend\scripts\create_user.py `
    --username "admin@example.invalid" `
    --role "Admin"
```

Available roles:

```text
Admin
UR
Read Only
```

The password must be at least 12 characters.

After the first Admin exists, create ordinary users through the Admin interface.

When the current governance attestation has not yet been accepted, the first Admin is directed to the governance setup workflow after login. Normal protected application functionality remains unavailable until an Admin completes the current organization attestation.

Packaged Windows and Linux releases also include first-time Admin setup workflows. Those bootstrap tools are part of packaged deployment and are separate from the normal development-server workflow.

## Development Database Initialization

The backend initializes required tables during startup.

Development databases normally appear under:

```text
backend/data/
```

Users are stored in the active database.

Deleting or changing the local database may remove development accounts.

## Seed Synthetic Data

CareQueue includes:

```text
backend/scripts/seed_dev_auths.py
```

Run only against a confirmed development database:

```powershell
python backend\scripts\seed_dev_auths.py
```

Review the script before running it.

Do not seed production.

## PDF Intake Development

Use synthetic or approved stripped files under:

```text
local_vobs/
```

Inspect from `backend`:

```powershell
python scripts\inspect_pdf_intake.py `
    "..\local_vobs\example.pdf"
```

Include normalized text only when necessary:

```powershell
python scripts\inspect_pdf_intake.py `
    "..\local_vobs\example.pdf" `
    --show-text
```

Do not place real output in public issues, documentation, or screenshots.

See [PDF Intake](../workflows/pdf-intake.md).

## Backend Tests

From `backend`:

```powershell
pytest tests -n auto -q
```

## Ruff

From `backend`:

```powershell
ruff check . --fix
```

Ruff configuration is in:

```text
backend/pyproject.toml
```

## Targeted Backend Tests

Run the smallest relevant suite while developing.

Examples:

```powershell
pytest tests\security -q
pytest tests\governance -q
pytest tests\pdf_intake -q
pytest tests\backups -q
pytest tests\authorizations -q
```

After targeted checks pass, run the full backend suite.

## Frontend Tests

From `frontend`:

```powershell
npm test
```

Watch mode:

```powershell
npm run test:watch
```

## Frontend Build

From `frontend`:

```powershell
npm run build
```

Build output:

```text
frontend/dist/
```

Do not commit generated output unless the release process explicitly requires it.

## Full Development Check

Backend:

```powershell
pytest tests -n auto -q
ruff check . --fix
```

Frontend:

```powershell
npm test
npm run build
```

Then manually test the workflow affected by the change.

## Packaged Deployment Development Checks

Use these commands when changing installer packaging, service configuration, production startup behavior, or release tooling.

### Windows

Build a fresh Windows payload:

```powershell
.\deployment\windows\installer\build-payload.ps1 `
    -EmbeddedPythonArchive ".\local_installer_assets\python-3.14.6-embed-amd64.zip"
```

Compile the installer:

```powershell
& "C:\Program Files\Inno Setup 7\ISCC.exe" `
    ".\deployment\windows\installer\CareQueue.iss"
```

For CareQueue `0.3.0`, run:

```powershell
.\build\windows\installer\CareQueue-Setup-0.3.0.exe
```

Validate the package:

```powershell
.\deployment\windows\installer\validate-release-package.ps1
```

### Linux

Build the production frontend first:

```powershell
npm --prefix frontend run build
```

Build the Linux release archive:

```powershell
.\deployment\linux\installer\build-payload.ps1 -Version 0.3.0
```

For CareQueue `0.3.0`, the resulting archive is:

```text
build\linux\installer\CareQueue-Linux-Setup-0.3.0.tar.gz
```

Local package creation is not sufficient release validation. Test the exact release artifact on clean supported virtual machines before publishing it.

## Optional Security Checks

Backend:

```powershell
bandit -r authstatus_api scripts -c pyproject.toml
python -m pip_audit -r requirements.txt
```

Frontend:

```powershell
npm audit
```

Review findings before changing dependencies.

## Release Version During Development

When preparing a new release, use the repository version helper:

```powershell
.\deployment\bump-version.ps1 -Version 0.3.0
```

Replace `0.3.0` with the intended application release version.

The helper updates controlled backend and deployment version declarations without blindly replacing matching strings in tests, dependency versions, documentation examples, or historical governance fixtures.

The governance attestation version is independent of the CareQueue application version. Do not change the governance version only because the application release number changes.

Review all changes after a version bump:

```powershell
git status --short
git diff
```

## API Documentation

While the backend is running:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/openapi.json
```

Most routes require authentication.

State-changing authenticated routes also require CSRF protection.

Use the browser application for normal protected workflows.

## Development CORS

Recommended local origins:

```json
[
  "http://localhost:5173",
  "http://127.0.0.1:5173"
]
```

When Vite uses another port, either free port 5173 or add the actual local origin.

Do not use a wildcard origin with credentialed requests.

## Development Cookies and Sessions

Local development uses:

```env
AUTHSTATUS_SESSION_COOKIE_SECURE=false
```

because the development frontend and backend use HTTP.

Production must use secure HTTPS cookies.

Authenticated sessions use a server-enforced inactivity timeout. The default is:

```env
AUTHSTATUS_SESSION_INACTIVITY_MINUTES=20
```

Supported values range from 5 to 480 minutes.

CareQueue also uses a separate remembered-device cookie for optional MFA trust:

```env
AUTHSTATUS_TRUSTED_DEVICE_COOKIE_NAME=carequeue_trusted_device
```

Remembered-device state is separate from the authenticated session and does not keep the user signed in.

Do not copy development-only cookie security settings into production.

## Switching Database Modes

Do not point SQLCipher mode at a plaintext database or plaintext mode at a SQLCipher database and expect automatic conversion.

Relevant scripts:

```text
backend/scripts/prepare_sqlcipher_cutover.py
backend/scripts/migrate_to_sqlcipher.py
backend/scripts/verify_sqlcipher_database.py
```

Review the current scripts before running them.

Database migration and backup procedures belong in [Backup and Recovery](../workflows/backup-and-recovery.md).

## Stop Development Servers

Use:

```text
Ctrl+C
```

in each terminal.

When needed, confirm ports are free:

```powershell
Get-NetTCPConnection `
    -LocalPort 8000 `
    -State Listen `
    -ErrorAction SilentlyContinue
```

```powershell
Get-NetTCPConnection `
    -LocalPort 5173 `
    -State Listen `
    -ErrorAction SilentlyContinue
```

## Reset Local Development Data

Stop the backend first.

Confirm the active path in `.env`.

Remove only the intended local file.

SQLCipher example:

```powershell
Remove-Item `
    "backend\data\auth_tracker.sqlcipher.db"
```

Plaintext example:

```powershell
Remove-Item `
    "backend\data\auth_tracker.db"
```

Restart the backend to create a new empty database.

This also removes local users stored in that database.

Never run these commands against production paths.

## Recreate the Backend Environment

From `backend`:

```powershell
Deactivate
Remove-Item ".venv" -Recurse -Force
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

Do not delete `backend/data` while recreating the virtual environment.

## Recreate Frontend Dependencies

From `frontend`:

```powershell
Remove-Item "node_modules" -Recurse -Force
npm ci
```

Do not delete `package-lock.json` as a first troubleshooting step.

## Common Problems

### Backend cannot find `.env`

Confirm:

```text
CareQueue\.env
```

exists at the repository root.

### Missing encryption key

Confirm all three development keys are present.

Do not paste their values into shared troubleshooting output.

### Database path is rejected

Use the standard local paths:

```text
backend/data
backend/backups
backend/restores
```

Do not enable unsafe paths merely to bypass a typo.

### Frontend cannot reach the backend

Check:

- Backend liveness
- `frontend/.env.development.local`
- API base URL
- CORS origins
- Vite port

### CORS error

Confirm the actual Vite origin appears in `AUTHSTATUS_CORS_ORIGINS`, then restart the backend.

### Login fails after database reset

Create the first Admin again.

A newly initialized database also has no governance attestation history, so the first Admin must complete the current governance setup after login before normal protected application pages become available.

### Login works in development but not production

The environments use separate databases, keys, cookies, origins, governance state, sessions, MFA enrollment, and remembered-device records.

Manage the account and authentication state in the correct environment.

### Backend import fails

From `backend`:

```powershell
python -c "import authstatus_api.main"
```

Check the virtual environment, installed requirements, root `.env`, Python version, and current source errors.

### Frontend dependency or build failure

Run:

```powershell
npm ci
npm test
npm run build
```

Review `package.json` and `package-lock.json` together.

### Ruff changes files

Review the changes, then rerun Ruff and tests.

### Build artifact runtime is locked

If a packaged runtime file under `build\windows` is locked, close any terminal or editor session using it.

In VS Code, select the backend virtual environment interpreter:

```text
backend\.venv\Scripts\python.exe
```

Do not use the packaged runtime as the workspace interpreter.

## Files That Must Remain Local

Do not commit:

```text
.env
frontend/.env.development.local
backend/.venv/
backend/data/
backend/backups/
backend/restores/
frontend/node_modules/
build/
local_backups/
local_config/
local_installer_assets/
local_vobs/
*.db
*.sqlite
*.sqlite3
*.db.enc
*.restored.db
__pycache__/
```

Encrypted backups remain sensitive.

## Before Committing

Review:

```powershell
git status --short
git diff
```

Confirm:

- No environment file is staged
- No database or backup is staged
- No real PDF is staged
- No sensitive screenshot is staged
- No key, credential, MFA secret, or authentication token appears in the changes
- Backend tests passed
- Ruff passed
- Frontend tests passed when relevant
- Frontend build passed when relevant
- Packaged deployment validation passed when deployment files changed

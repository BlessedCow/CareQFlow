# CareQueue

CareQueue is a local-first application for managing utilization review and prior authorization work.

It brings authorization records, review dates, payer decisions, timeline events, follow-up work, and PDF-assisted intake into one place. The goal is to make day-to-day authorization tracking easier to follow without relying on scattered spreadsheets, notes, and reminders.

CareQueue is built for private use and controlled deployment. It is not a hosted service, and it is not HIPAA compliant simply because it includes security controls. Any organization using it with protected health information remains responsible for its own legal, administrative, physical, and technical safeguards.

## What CareQueue Does

CareQueue supports the main parts of an authorization workflow:

- Track initial and continued-stay authorizations
- Record facilities, payers, levels of care, member details, and review dates
- Follow pending, approved, denied, appealed, peer-to-peer, discharged, and completed work
- Keep a timeline of authorization events
- View work through dashboard, calendar, queue, and detail screens
- Filter records by facility, payer, level of care, status, and due date
- Review information extracted from intake PDFs before saving it
- Manage users, roles, registered facilities, insurers, and portal details
- Create encrypted backups and stage safe recoveries

## Screens and Workflow

The frontend includes:

- A dashboard with workload summaries and due-date information
- A searchable and filterable authorization queue
- Calendar views for review dates and authorization milestones
- Read-only detail views for reviewing a record without opening an edit form
- Timeline event management
- PDF intake review with confidence and needs-review indicators
- Administrative pages for users and audit activity
- Settings for facilities, insurers, portals, dashboard cards, and workflow preferences
- Dark mode and local display preferences

## Security at a Glance

CareQueue includes several layers of application security:

- Argon2id password hashing
- Role-based access for Admin, UR, and Read Only users
- Server-side sessions with hashed session tokens
- Secure browser cookies
- CSRF protection for authenticated changes
- Session expiration and renewal controls
- Field-level encryption for selected sensitive values
- SQLCipher support for encrypted database storage
- Separately encrypted database backups
- Audit logging for security and authorization activity
- Production log sanitization intended to keep credentials, tokens, and sensitive field values out of logs

These controls reduce risk, but they do not replace a complete security or compliance program. See [SECURITY.md](SECURITY.md) and [DISCLAIMER.md](DISCLAIMER.md) before using CareQueue with sensitive information.

## Technology

CareQueue uses:

- **Backend:** Python, FastAPI, Pydantic, SQLite, and SQLCipher
- **Frontend:** React, TypeScript, Vite, and Tailwind CSS
- **Authentication:** Secure cookie sessions, CSRF protection, and Argon2id
- **Testing:** Pytest, Vitest, Testing Library, and Ruff
- **Windows deployment:** WinSW services and Caddy for private HTTPS

## Project Layout

Only the main areas are shown here.

```text
CareQueue/
├── backend/
│   ├── authstatus_api/     # API, business logic, storage, security, and backups
│   ├── scripts/            # User, backup, recovery, PDF, and database utilities
│   └── tests/              # Backend tests organized by application area
├── frontend/
│   └── src/                # React application
├── deployment/
│   ├── windows/            # Production installer, services, Caddy, and backup tasks
│   └── linux/              # Linux service and scheduling files
├── docs/                   # Longer workflow and operating documentation
├── ARCHITECTURE.md
├── SECURITY.md
├── ROADMAP.md
└── DISCLAIMER.md
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for a technical description of how these pieces work together.

## Local Development

### Requirements

- Python 3.11 or newer
- Node.js and npm
- A SQLCipher-compatible Python package when using SQLCipher mode

The project is currently developed and tested on Windows. Other platforms may require small command or deployment changes.

### Backend

Create and activate a virtual environment:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

Copy the root environment example:

```powershell
cd ..
Copy-Item .env.example .env
```

Fill in the required keys and local paths in `.env`. Do not commit that file.

Start the API from `backend`:

```powershell
uvicorn authstatus_api.main:create_app --factory --host 127.0.0.1 --port 8000
```

The development API is available at:

```text
http://127.0.0.1:8000
```

### Frontend

In a second terminal:

```powershell
cd frontend
npm install
Copy-Item .env.example .env.development.local
npm run dev
```

The development frontend normally opens at:

```text
http://localhost:5173
```

The development environment file points the frontend directly to the local FastAPI server. Production builds use same-origin `/api` requests through the reverse proxy.

## Create the First Admin

CareQueue does not include public account registration.

For a packaged Windows installation, the installer can launch the first-time Admin setup window after installation completes. The setup window creates the first Admin through the local CareQueue API without passing the password through command-line arguments.

The first-time setup flow is available only while no users exist. After any user exists, the backend disables the initial Admin setup endpoint and the setup window will report that setup is already complete.

For development or maintenance workflows, an Admin can also be created from the backend script.

With the backend environment active and the root `.env` configured:

```powershell
python backend/scripts/create_user.py --username carequeue.admin --role Admin
```

The script prompts for a password without printing it to the terminal.

Available roles:

- **Admin:** Full record access plus user and administrative controls
- **UR:** Create, view, edit, and manage authorization work
- **Read Only:** View records without create, edit, or delete controls

## Private Windows Deployment

CareQueue includes a Windows production installer and service definitions under:

```text
deployment/windows/
```

The current Windows deployment can:

- Build and package the production frontend
- Bundle a private Python runtime for the backend
- Bundle pinned Caddy and WinSW service binaries
- Install application files into `C:\Program Files\CareQueue`
- Store runtime data under `C:\ProgramData\CareQueue`
- Generate and preserve independent production encryption keys
- Run the FastAPI backend as a Windows service
- Serve the frontend and proxy `/api` through Caddy
- Provide private HTTPS through a local hostname such as `carequeue.local`
- Offer installer modes for Install, Upgrade, Repair, and Uninstall
- Preserve runtime data during uninstall
- Launch the first-time Admin setup GUI after installation
- Run post-installation validation for services and loopback health
- Install scheduled encrypted backups

The packaged Windows installer is intended to be the normal private Windows installation path. The lower-level PowerShell scripts remain useful for development, troubleshooting, and direct validation of installer modes.

The production installer is intended for private or restricted-network use. It should not be treated as a public internet deployment template without additional review and hardening.

Technical deployment details belong in the deployment scripts and [ARCHITECTURE.md](ARCHITECTURE.md). Security responsibilities and limitations are covered in [SECURITY.md](SECURITY.md).

## Backups and Recovery

CareQueue can create encrypted backups of the active database:

```powershell
python backend/scripts/create_encrypted_backup.py
```

A backup can be decrypted and staged in a safe restore location without overwriting the active database:

```powershell
python backend/scripts/restore_encrypted_backup.py path\to\backup.db.enc
```

CareQueue also includes:

- Backup verification
- Retention rules
- A minimum protected backup count
- Windows Task Scheduler integration
- Linux systemd scheduling files
- Staged recovery activation

Detailed instructions are in [docs/workflows/backup-and-recovery.md](docs/workflows/backup-and-recovery.md).

Backups are useful only when restoration is tested. Keep backup keys separate from backup files and restrict both to authorized administrators or service accounts.

## PDF Intake

CareQueue can read text from supported PDFs locally and present likely intake values for review.

The intake workflow is designed to:

- Keep processing local
- Avoid sending documents to an external OCR service
- Mark uncertain fields for review
- Require confirmation before accepting flagged values
- Avoid treating extracted data as automatically correct

Scanned or malformed documents may not contain usable embedded text. Extracted values must be reviewed before they are saved.

## Testing

### Backend

From `backend`, with the project virtual environment active:

```powershell
pytest tests -n auto -q
python -m ruff check . --fix
```

Additional security checks used during development include:

```powershell
bandit -r authstatus_api
pip-audit
```

### Frontend

From `frontend`:

```powershell
npm test
npm run build
```

## Sensitive Files

Do not commit local configuration, databases, backups, restored databases, intake documents, or screenshots containing real information.

Common local-only paths include:

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
```

Before committing:

```powershell
git status --short
```

Use synthetic data in tests, screenshots, examples, and public documentation.

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) explains the technical structure and request flow.
- [SECURITY.md](SECURITY.md) documents security controls, reporting, deployment assumptions, and limitations.
- [ROADMAP.md](ROADMAP.md) tracks completed work and planned priorities.
- [DISCLAIMER.md](DISCLAIMER.md) explains privacy, compliance, and use limitations.
- [CONTRIBUTING.md](CONTRIBUTING.md) covers contribution and testing expectations.
- [docs/workflows/backup-and-recovery.md](docs/workflows/backup-and-recovery.md) covers backup scheduling, restoration, and recovery.

## Status

CareQueue is under active development. The core authorization workflow, authentication, encrypted storage options, encrypted backups, PDF-assisted intake, frontend testing, and private Windows deployment are implemented.

The roadmap still includes additional deployment documentation, upgrade and rollback improvements, broader browser-level testing, accessibility work, Linux deployment work, and a separate synthetic-data demo environment.

## License

See [LICENSE](LICENSE).

# CareQueue Command Reference

This reference lists the commands used most often while developing, testing, packaging, and starting CareQueue.

Use these commands from the repository root unless a section says otherwise.

```text
G:\CareQueue
```

Do not use this document as a production compliance checklist. It is a command reference for local development and Windows packaging work.

## Quick Start: Local Development

Use local development when changing source code or testing the app with separate backend and frontend development servers.

Local development uses:

```text
Backend:  http://127.0.0.1:8000
Frontend: http://localhost:5173
```

The backend and frontend must run at the same time.

## Start the Backend Development Server

Open the first terminal.

From the repository root:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn authstatus_api.main:create_app --factory --host 127.0.0.1 --port 8000
```

Leave this terminal open while using the development app.

The backend is running at:

```text
http://127.0.0.1:8000
```

Health check:

```powershell
Invoke-RestMethod `
    -Method Get `
    -Uri "http://127.0.0.1:8000/api/health" `
    -TimeoutSec 5
```

API docs while the backend is running:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/openapi.json
```

## Start the Frontend Development Server

Open a second terminal.

From the repository root:

```powershell
cd frontend
npm run dev
```

Leave this terminal open while using the development app.

The frontend is running at:

```text
http://localhost:5173
```

Open that URL in the browser for local development.

## Start Backend and Frontend Together

Use this when you want to launch both development servers from one PowerShell window.

From the repository root:

```powershell
Start-Process powershell.exe `
    -ArgumentList '-NoExit', '-Command', 'cd "G:\CareQueue\backend"; .\.venv\Scripts\Activate.ps1; uvicorn authstatus_api.main:create_app --factory --host 127.0.0.1 --port 8000'

Start-Process powershell.exe `
    -ArgumentList '-NoExit', '-Command', 'cd "G:\CareQueue\frontend"; npm run dev'
```

Then open:

```text
http://localhost:5173
```

If your repository is not located at `G:\CareQueue`, change the paths in the two `cd` commands.

## Stop Local Development Servers

In each development server terminal, press:

```text
Ctrl+C
```

Check whether the backend port is still in use:

```powershell
Get-NetTCPConnection `
    -LocalPort 8000 `
    -State Listen `
    -ErrorAction SilentlyContinue
```

Check whether the frontend port is still in use:

```powershell
Get-NetTCPConnection `
    -LocalPort 5173 `
    -State Listen `
    -ErrorAction SilentlyContinue
```

## Concurrent Run Rules

CareQueue can run the development backend and development frontend at the same time. That is the normal development setup.

Avoid running two API servers on the same port at the same time.

Do not run these together on port `8000`:

```text
- Development backend through uvicorn on 127.0.0.1:8000
- Installed CareQueueApi Windows service on 127.0.0.1:8000
```

If the packaged Windows services are running and you want to start the development backend on port `8000`, stop the installed services first:

```powershell
Stop-Service CareQueueCaddy
Stop-Service CareQueueApi
```

Start them again when finished:

```powershell
Start-Service CareQueueApi
Start-Service CareQueueCaddy
```

If you need the installed app and a development backend at the same time, run the development backend on another port and update the frontend development API URL accordingly.

Example alternate backend port:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn authstatus_api.main:create_app --factory --host 127.0.0.1 --port 8001
```

Then set the frontend development API base URL to match:

```env
VITE_AUTHSTATUS_API_BASE_URL=http://localhost:8001
```

The recommended local development default remains port `8000`.

## First Development Admin User

CareQueue does not have public registration.

From the repository root, with the backend virtual environment active:

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

## Backend Checks

Run the full backend test suite from the repository root:

```powershell
pytest backend\tests -n auto -q
```

Run Ruff from the repository root:

```powershell
ruff check . --fix
```

Run backend security checks:

```powershell
bandit -r backend\authstatus_api backend\scripts -c backend\pyproject.toml
python -m pip_audit -r backend\requirements.txt
```

Targeted backend test examples:

```powershell
pytest backend\tests\security -q
pytest backend\tests\pdf_intake -q
pytest backend\tests\backups -q
pytest backend\tests\authorizations -q
```

## Frontend Checks

From `frontend`:

```powershell
npm audit
npm test
npm run build
```

Watch tests while developing:

```powershell
npm run test:watch
```

Return to the repository root:

```powershell
cd ..
```

## Full Local Check Before Commit

From the repository root:

```powershell
pytest backend\tests -n auto -q
ruff check . --fix
```

From `frontend`:

```powershell
npm audit
npm test
npm run build
```

Then review changed files:

```powershell
git status --short
git diff
```

## Build the Windows Installer Payload

Use this when installer, deployment, production startup, frontend build output, dependency packaging, Caddy configuration, or Windows service behavior changed.

From the repository root:

```powershell
.\deployment\windows\installer\build-payload.ps1 `
    -EmbeddedPythonArchive "G:\CareQueue\local_installer_assets\python-3.14.6-embed-amd64.zip"
```

The default payload output is:

```text
build\windows\payload
```

## Compile the Windows Installer

From the repository root:

```powershell
& "C:\Program Files\Inno Setup 7\ISCC.exe" ".\deployment\windows\installer\CareQueue.iss"
```

The installer output is:

```text
build\windows\installer\CareQueue-Setup-0.1.0.exe
```

## Run the Windows Installer

From the repository root:

```powershell
.\build\windows\installer\CareQueue-Setup-0.1.0.exe
```

If PowerShell requires an explicit invocation path:

```powershell
& "G:\CareQueue\build\windows\installer\CareQueue-Setup-0.1.0.exe"
```

The installer requires administrator elevation because it installs Windows services and writes under protected directories.

When CareQueue is not installed, the installer shows the first-time Install flow.

When CareQueue is already installed, the installer offers:

```text
Upgrade existing installation
Repair existing installation
Uninstall CareQueue
```

## Start the Installed Windows App

The packaged Windows app runs through Windows services.

Check services:

```powershell
Get-Service CareQueueApi, CareQueueCaddy |
    Select-Object Name, Status, StartType
```

Start services:

```powershell
Start-Service CareQueueApi
Start-Service CareQueueCaddy
```

Open the installed app:

```text
https://carequeue.local
```

Health checks:

```powershell
Invoke-RestMethod `
    -Method Get `
    -Uri "https://carequeue.local/api/health/live" `
    -TimeoutSec 5
```

```powershell
Invoke-RestMethod `
    -Method Get `
    -Uri "https://carequeue.local/api/health/ready" `
    -TimeoutSec 5
```

If `carequeue.local` does not resolve, confirm the hosts file entry exists:

```powershell
ping carequeue.local
```

## Stop the Installed Windows App

Stop the proxy first, then the API:

```powershell
Stop-Service CareQueueCaddy
Stop-Service CareQueueApi
```

Confirm both stopped:

```powershell
Get-Service CareQueueApi, CareQueueCaddy |
    Select-Object Name, Status, StartType
```

## First-Time Admin Setup for Installed Windows App

After a packaged Windows installation, the installer can launch the first-time Admin setup window.

The setup window is installed at:

```text
C:\Program Files\CareQueue\deployment\windows\CareQueue-AdminSetup.ps1
```

Run it manually if needed:

```powershell
powershell.exe `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File "C:\Program Files\CareQueue\deployment\windows\CareQueue-AdminSetup.ps1"
```

The setup window checks:

```text
http://127.0.0.1:8000/api/security/setup-initial-admin/status
```

The first-time Admin setup endpoint is loopback-only and is available only while no users exist.

## Installer Logs

Find the newest installer log:

```powershell
$latestLog = Get-ChildItem `
    -Path "$env:ProgramData\CareQueue\Logs\Installer" `
    -Filter "CareQueue-*.log" `
    -ErrorAction SilentlyContinue |
Sort-Object LastWriteTime -Descending |
Select-Object -First 1

$latestLog.FullName
```

Read the newest installer log:

```powershell
Get-Content `
    -LiteralPath $latestLog.FullName `
    -Tail 240
```

## Verify Packaged Caddy Security Headers

After installing or repairing the packaged Windows app:

```powershell
Invoke-WebRequest `
    -Uri "https://carequeue.local" `
    -UseBasicParsing |
Select-Object -ExpandProperty Headers
```

Expected headers include:

```text
Content-Security-Policy
Strict-Transport-Security
X-Content-Type-Options
X-Frame-Options
Referrer-Policy
Permissions-Policy
```

## Generate Installer Checksum

From the repository root:

```powershell
Get-FileHash `
    -Algorithm SHA256 `
    ".\build\windows\installer\CareQueue-Setup-0.1.0.exe" |
ForEach-Object {
    "$($_.Hash)  CareQueue-Setup-0.1.0.exe"
} |
Set-Content `
    -Encoding ASCII `
    ".\build\windows\installer\CareQueue-Setup-0.1.0.exe.sha256"
```

Verify the checksum file:

```powershell
$expectedHash = (
    Get-Content ".\build\windows\installer\CareQueue-Setup-0.1.0.exe.sha256"
).Split(" ")[0]

$actualHash = (
    Get-FileHash `
        -Algorithm SHA256 `
        ".\build\windows\installer\CareQueue-Setup-0.1.0.exe"
).Hash

$actualHash -eq $expectedHash
```

Expected result:

```text
True
```

## Direct Installer Engine Validation

Use this only for lower-level installer troubleshooting.

From the repository root, run the packaged installer engine directly:

```powershell
powershell.exe `
    -NoProfile `
    -NonInteractive `
    -ExecutionPolicy Bypass `
    -File ".\build\windows\payload\deployment\windows\installer\invoke-install.ps1" `
    -Mode Repair `
    -ApplicationOrigin "https://carequeue.local" `
    -PayloadDirectory ".\build\windows\payload" `
    -InstallDirectory "C:\Program Files\CareQueue" `
    -DataDirectory "C:\ProgramData\CareQueue"
```

Supported modes:

```text
Install
Upgrade
Repair
Uninstall
```

Use the installer GUI for ordinary validation. Use direct engine validation only when debugging the installer scripts.

## Backup Runner

Run the installed backup task helper from the installed app directory:

```powershell
& "C:\Program Files\CareQueue\deployment\windows\install-backup-task.ps1"
```

Run the installed backup command manually:

```powershell
& "C:\Program Files\CareQueue\deployment\windows\run-backup.ps1"
```

Backup files remain sensitive even when encrypted.

## Common Start Points

Use these start points most often:

```text
Local development app:
http://localhost:5173

Local development API:
http://127.0.0.1:8000

Local development API docs:
http://127.0.0.1:8000/docs

Installed Windows app:
https://carequeue.local

Installed Admin setup GUI:
C:\Program Files\CareQueue\deployment\windows\CareQueue-AdminSetup.ps1

Installed runtime data:
C:\ProgramData\CareQueue

Installed application files:
C:\Program Files\CareQueue
```

## Do Not Commit Local Artifacts

Before committing, check:

```powershell
git status --short
```

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

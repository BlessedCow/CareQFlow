# CareQueue Command Reference

This reference collects commonly used commands for CareQueue development, testing, packaging, release preparation, and installed-service validation.

Run commands from the repository root unless a section says otherwise.

Examples use PowerShell for Windows development and packaging tasks. Linux installation commands use Bash.

## Local Development

Local development normally uses separate backend and frontend development servers:

```text
Backend:  http://127.0.0.1:8000
Frontend: http://localhost:5173
```

Both processes must be running to use the development application.

## Start the Backend Development Server

From the repository root:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn authstatus_api.main:create_app --factory --host 127.0.0.1 --port 8000
```

The backend is available at:

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

Development API documentation:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/openapi.json
```

Production deployments do not expose the interactive API documentation by default.

## Start the Frontend Development Server

Open a second terminal.

From the repository root:

```powershell
cd frontend
npm run dev
```

The frontend is available at:

```text
http://localhost:5173
```

## Stop Local Development Servers

In each development-server terminal, press:

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

## Running Development and Installed Services

Do not run two API servers on the same port.

The normal development backend and packaged production API both use:

```text
127.0.0.1:8000
```

If the installed Windows services are running and the development backend needs port `8000`, stop the installed services first:

```powershell
Stop-Service CareQueueCaddy
Stop-Service CareQueueApi
```

Restart them when finished:

```powershell
Start-Service CareQueueApi
Start-Service CareQueueCaddy
```

To use a different development backend port:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn authstatus_api.main:create_app --factory --host 127.0.0.1 --port 8001
```

Then configure the frontend development API URL accordingly:

```env
VITE_AUTHSTATUS_API_BASE_URL=http://localhost:8001
```

## Create a Development Admin User

CareQueue does not provide public registration.

From the repository root, with the backend environment available:

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

The script prompts for the password without placing it on the command line.

The minimum password length is 12 characters.

A user created against a development database does not automatically exist in a packaged production installation.

## Backend Tests

From the repository root:

```powershell
pytest backend\tests -n auto -q
```

From the `backend` directory:

```powershell
pytest tests -n auto -q
```

Run a targeted test module:

```powershell
pytest tests\security\test_security_routes.py -q
```

Run a targeted test:

```powershell
pytest tests\security\test_security_routes.py::test_me_returns_current_user -q
```

Common targeted suites:

```powershell
pytest tests\security -q
pytest tests\governance -q
pytest tests\pdf_intake -q
pytest tests\backups -q
pytest tests\authorizations -q
```

## Ruff

From the repository root:

```powershell
ruff check backend\authstatus_api backend\tests --fix
```

From the `backend` directory:

```powershell
ruff check authstatus_api tests --fix
```

## Backend Security Checks

From the repository root:

```powershell
bandit -r backend\authstatus_api backend\scripts -c backend\pyproject.toml
```

Dependency audit:

```powershell
python -m pip_audit -r backend\requirements.txt
```

## Frontend Tests and Build

From the repository root:

```powershell
npm --prefix frontend test
```

Run the frontend production build:

```powershell
npm --prefix frontend run build
```

Run the frontend dependency audit:

```powershell
npm --prefix frontend audit
```

From the `frontend` directory, the equivalent commands are:

```powershell
npm test
npm run build
npm audit
```

Watch tests during frontend development:

```powershell
npm run test:watch
```

## Full Local Validation

A typical source validation run is:

```powershell
pytest backend\tests -n auto -q
ruff check backend\authstatus_api backend\tests --fix
npm --prefix frontend test
npm --prefix frontend run build
```

For release work, also run the project's dependency and security checks as required by the release process.

Review the working tree afterward:

```powershell
git status --short
git diff
```

## Release Version

CareQueue keeps the application release version in several backend and deployment files.

Use the repository release-version helper rather than editing those locations individually:

```powershell
.\deployment\bump-version.ps1 -Version 0.3.0
```

Replace `0.3.0` with the intended release version.

The script updates the controlled release-version declarations used by:

- Backend application metadata
- Windows installer metadata
- Windows release validation
- Windows packaged payload metadata
- Linux release-package defaults

It intentionally does not replace arbitrary matching version strings in tests, documentation, dependency versions, or historical governance fixtures.

The governance attestation version and governance document revision are independent of the CareQueue application version and should not be changed merely because the application release number changes.

Change the required governance metadata deliberately when governance text or required acknowledgments change. A change to either the required attestation version or required document revision causes existing acceptance records that do not match both values to no longer be current.

After a version bump, review:

```powershell
git status --short
git diff
```

## Build the Frontend for Packaging

The packaged Windows and Linux release workflows use the production frontend build.

From the repository root:

```powershell
npm --prefix frontend run build
```

The build output is:

```text
frontend/dist
```

## Build the Windows Installer Payload

From the repository root:

```powershell
.\deployment\windows\installer\build-payload.ps1 `
    -EmbeddedPythonArchive ".\local_installer_assets\python-3.14.6-embed-amd64.zip"
```

The default payload output is:

```text
build\windows\payload
```

The embedded Python archive is a local installer asset and should not be committed to source control.

## Compile the Windows Installer

After the Windows payload has been built:

```powershell
& "C:\Program Files\Inno Setup 7\ISCC.exe" `
    ".\deployment\windows\installer\CareQueue.iss"
```

For CareQueue `0.3.0`, the resulting installer is:

```text
build\windows\installer\CareQueue-Setup-0.3.0.exe
```

Future releases use the version configured by the release-version tooling.

## Validate the Windows Release Package

The Windows release validator checks the packaged payload and installer.

From the repository root:

```powershell
.\deployment\windows\installer\validate-release-package.ps1
```

The script uses the versioned installer path configured in the release tooling unless another path is explicitly supplied.

Use this validation before publishing the Windows release artifact.

## Run the Windows Installer

For CareQueue `0.3.0`:

```powershell
.\build\windows\installer\CareQueue-Setup-0.3.0.exe
```

An explicit invocation path can also be used:

```powershell
& ".\build\windows\installer\CareQueue-Setup-0.3.0.exe"
```

The installer requires administrator elevation because it installs Windows services and writes to protected locations.

When CareQueue is not installed, the installer uses the fresh-install flow.

When an existing installation is detected, the installer offers:

```text
Upgrade existing installation
Repair existing installation
Uninstall CareQueue
```

## Installed Windows Services

Check the service state:

```powershell
Get-Service CareQueueApi, CareQueueCaddy |
    Select-Object Name, Status, StartType
```

Start CareQueue:

```powershell
Start-Service CareQueueApi
Start-Service CareQueueCaddy
```

Stop CareQueue:

```powershell
Stop-Service CareQueueCaddy
Stop-Service CareQueueApi
```

The proxy is stopped before the API.

## Installed Windows Application

The packaged private application is available at:

```text
https://carequeue.local
```

Liveness:

```powershell
Invoke-RestMethod `
    -Method Get `
    -Uri "https://carequeue.local/api/health/live" `
    -TimeoutSec 5
```

Readiness:

```powershell
Invoke-RestMethod `
    -Method Get `
    -Uri "https://carequeue.local/api/health/ready" `
    -TimeoutSec 5
```

If the hostname does not resolve:

```powershell
ping carequeue.local
```

Then review the local hosts entry and packaged Caddy configuration.

## First-Time Admin Setup on Windows

The packaged setup utility is installed at:

```text
C:\Program Files\CareQueue\deployment\windows\CareQueue-AdminSetup.ps1
```

Run it manually if necessary:

```powershell
powershell.exe `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File "C:\Program Files\CareQueue\deployment\windows\CareQueue-AdminSetup.ps1"
```

The setup utility communicates with the loopback-only initial Admin endpoint.

Initial Admin setup is available only while no users exist.

After the first Admin signs in through the browser, the current organization governance attestation must also be completed before normal protected application functionality becomes available.

## Windows Installer Logs

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

## Verify Packaged Browser Security Headers

After installing or repairing the packaged Windows application:

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

## Generate a Windows Installer Checksum

For CareQueue `0.3.0`:

```powershell
Get-FileHash `
    -Algorithm SHA256 `
    ".\build\windows\installer\CareQueue-Setup-0.3.0.exe" |
ForEach-Object {
    "$($_.Hash)  CareQueue-Setup-0.3.0.exe"
} |
Set-Content `
    -Encoding ASCII `
    ".\build\windows\installer\CareQueue-Setup-0.3.0.exe.sha256"
```

Verify it:

```powershell
$expectedHash = (
    Get-Content ".\build\windows\installer\CareQueue-Setup-0.3.0.exe.sha256"
).Split(" ")[0]

$actualHash = (
    Get-FileHash `
        -Algorithm SHA256 `
        ".\build\windows\installer\CareQueue-Setup-0.3.0.exe"
).Hash

$actualHash -eq $expectedHash
```

Expected result:

```text
True
```

## Direct Windows Installer Engine Validation

Use the packaged installer engine directly only for lower-level installer troubleshooting.

From the repository root:

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

Use the compiled installer for ordinary release validation. Direct engine invocation is primarily a troubleshooting tool.

## Windows Backup Commands

Install or refresh the scheduled backup task from an installed deployment:

```powershell
& "C:\Program Files\CareQueue\deployment\windows\install-backup-task.ps1"
```

Run the installed backup helper manually:

```powershell
& "C:\Program Files\CareQueue\deployment\windows\run-backup.ps1"
```

Backup files remain sensitive even when encrypted.

## Build the Linux Release Package

The Linux package requires the production frontend build.

From the repository root:

```powershell
npm --prefix frontend run build
```

Then build the Linux archive:

```powershell
.\deployment\linux\installer\build-payload.ps1 -Version 0.3.0
```

Because the release script also has a version default, after the repository has been bumped to the intended version this can be shortened to:

```powershell
.\deployment\linux\installer\build-payload.ps1
```

For CareQueue `0.3.0`, the artifact is:

```text
build\linux\installer\CareQueue-Linux-Setup-0.3.0.tar.gz
```

The build script reports the resulting package path, size, and SHA256 value.

## Extract a Linux Release Package

On the Linux target:

```bash
mkdir carequeue-installer
tar -xzf CareQueue-Linux-Setup-0.3.0.tar.gz \
  -C carequeue-installer
cd carequeue-installer
```

## Install CareQueue on Linux

From the extracted release package:

```bash
sudo bash deployment/linux/installer/invoke-install.sh install
```

The packaged private origin is:

```text
https://carequeue.local
```

The Linux installer requires root privileges because it installs system packages, writes to protected system directories, creates a service account, installs systemd units, and configures certificate trust.

## Upgrade CareQueue on Linux

From a newly extracted reviewed release package:

```bash
sudo bash deployment/linux/installer/invoke-install.sh upgrade
```

Before upgrading, confirm that a recent verified encrypted backup is available.

## Repair CareQueue on Linux

From the extracted release package:

```bash
sudo bash deployment/linux/installer/invoke-install.sh repair
```

Repair preserves the existing production configuration and data.

## Uninstall CareQueue on Linux

From the extracted release package:

```bash
sudo bash deployment/linux/installer/invoke-install.sh uninstall
```

Review the Linux deployment documentation before uninstalling. The packaged uninstall workflow preserves documented CareQueue configuration, data, and logs rather than treating uninstall as secure data destruction.

## Linux Service Status

Check the API service:

```bash
sudo systemctl status carequeue-api.service
```

Check the HTTPS service:

```bash
sudo systemctl status carequeue-caddy.service
```

Check the backup timer:

```bash
sudo systemctl status carequeue-backup.timer
```

List the backup timer schedule:

```bash
sudo systemctl list-timers carequeue-backup.timer
```

## Linux Logs

API logs:

```bash
sudo journalctl \
  -u carequeue-api.service \
  --since today
```

HTTPS/Caddy logs:

```bash
sudo journalctl \
  -u carequeue-caddy.service \
  --since today
```

Backup service logs:

```bash
sudo journalctl \
  -u carequeue-backup.service \
  --since today
```

Installer logs are stored under:

```text
/var/log/carequeue/installer/
```

## Linux Health Checks

From the installed Linux host:

```bash
curl --fail --silent --show-error \
  https://carequeue.local/api/health/live
```

Readiness:

```bash
curl --fail --silent --show-error \
  https://carequeue.local/api/health/ready
```

If the local Caddy root has not yet been trusted by the invoking environment, resolve certificate trust rather than permanently disabling TLS verification.

## Linux First-Time Admin Setup

The packaged Linux utility is installed at:

```text
/opt/carequeue/deployment/linux/CareQueue-AdminSetup.sh
```

Run it manually when initial setup is still available:

```bash
sudo bash /opt/carequeue/deployment/linux/CareQueue-AdminSetup.sh
```

The utility submits the initial Admin credentials only to the loopback CareQueue API.

After the first Admin signs in through the browser, the current organization governance attestation must also be completed before normal protected application functionality becomes available.

## Common Development and Production URLs

```text
Development frontend:
http://localhost:5173

Development API:
http://127.0.0.1:8000

Development API documentation:
http://127.0.0.1:8000/docs

Packaged private application:
https://carequeue.local

Packaged API liveness:
https://carequeue.local/api/health/live

Packaged API readiness:
https://carequeue.local/api/health/ready
```

## Common Windows Paths

```text
Installed application:
C:\Program Files\CareQueue

Runtime data:
C:\ProgramData\CareQueue

Installer logs:
C:\ProgramData\CareQueue\Logs\Installer

Admin setup utility:
C:\Program Files\CareQueue\deployment\windows\CareQueue-AdminSetup.ps1
```

## Common Linux Paths

```text
Installed application:
/opt/carequeue

Production configuration:
/etc/carequeue

Production data:
/var/lib/carequeue

Logs:
/var/log/carequeue

Admin setup utility:
/opt/carequeue/deployment/linux/CareQueue-AdminSetup.sh
```

## Git Review Commands

Review changed files:

```powershell
git status --short
```

Review unstaged changes:

```powershell
git diff
```

Review staged changes:

```powershell
git diff --cached
```

## Do Not Commit Local Artifacts

Before committing, inspect:

```powershell
git status --short
```

Do not commit local runtime, secret, dependency, or build artifacts such as:

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

Also do not commit:

- Real patient data
- Production credentials
- Encryption keys
- Authenticator secrets
- MFA codes
- Session tokens
- Remembered-device tokens
- Production environment files
- Private certificates or private keys

# Windows Deployment

This guide covers a private Windows installation of CareQueue using the packaged Windows installer.

The packaged installer is built from:

```text
deployment/windows/installer/CareQueue.iss
```

The installer uses the packaged payload created by:

```text
deployment/windows/installer/build-payload.ps1
```

A completed installation uses:

- A bundled private Python runtime for the backend
- Bundled Caddy and WinSW service binaries
- The CareQueue API Windows service
- The CareQueue Caddy Windows service
- A local HTTPS hostname such as `carequeue.local`
- SQLCipher-backed production storage
- Runtime data under `C:\ProgramData\CareQueue`
- Application files under `C:\Program Files\CareQueue`

The built-in Windows deployment is intended for a private workstation or restricted private network. It is not a public internet deployment template.

CareQueue's security controls do not establish HIPAA compliance by themselves. Before using real protected health information, review [SECURITY.md](../../SECURITY.md), [DISCLAIMER.md](../../DISCLAIMER.md), and the organization's legal, operational, and compliance requirements.

## Deployment Overview

A completed Windows installation uses this request path:

```text
Browser
  |
  | https://carequeue.local
  v
CareQueueCaddy Windows service
  |
  | Serves frontend files
  |
  \__ Proxies /api
          |
          v
CareQueueApi Windows service
          |
          | http://127.0.0.1:8000
          v
FastAPI
  |
  v
SQLCipher database under C:\ProgramData\CareQueue
```

The browser should use the HTTPS application origin. The API remains bound to the loopback interface and should not be opened directly to the network.

## Installed Locations

The Windows installer separates application files from runtime data.

### Application files

```text
C:\Program Files\CareQueue
```

This includes installed application code and packaged runtime files such as:

```text
backend/
frontend/
deployment/
runtime/
Service/
vendor/
```

The packaged backend uses the bundled runtime at:

```text
C:\Program Files\CareQueue\runtime\python\python.exe
```

The packaged Caddy executable is installed at:

```text
C:\Program Files\CareQueue\vendor\caddy\caddy.exe
```

### Runtime data

```text
C:\ProgramData\CareQueue
```

The installer creates or uses directories for runtime state, configuration, data, logs, backups, restores, recovery staging, and Caddy runtime files.

The production environment file is:

```text
C:\ProgramData\CareQueue\Config\carequeue.env
```

Do not commit, copy into documentation, paste into an issue, or share the contents of this file. It contains production encryption keys and other sensitive configuration.

## Windows Services

A complete packaged installation uses two Windows services:

```text
CareQueueApi
CareQueueCaddy
```

### CareQueueApi

The API service:

- Runs the FastAPI backend through Uvicorn
- Loads configuration from the production environment file
- Forces the application environment to `production`
- Binds to `127.0.0.1:8000`
- Trusts proxy headers only from `127.0.0.1`
- Disables Uvicorn access logging
- Starts automatically with Windows
- Restarts after unexpected failures

### CareQueueCaddy

The HTTPS service:

- Serves the production frontend
- Proxies `/api` to `127.0.0.1:8000`
- Depends on `CareQueueApi`
- Starts automatically with Windows
- Restarts after unexpected failures
- Stores its local certificate authority and runtime data under ProgramData
- Writes service logs under ProgramData

## Installer Modes

The packaged installer supports four operation modes:

```text
Install
Upgrade
Repair
Uninstall
```

When CareQueue is not installed, the installer presents the normal first-time Install flow.

When CareQueue is already installed, the installer presents operation choices:

```text
Upgrade existing installation
Repair existing installation
Uninstall CareQueue
```

### Install

Install is used when CareQueue is not already installed.

Install creates application files, runtime directories, services, production configuration, and production encryption keys when no existing runtime configuration is present.

### Upgrade

Upgrade is used when CareQueue is already installed.

Upgrade replaces application files and packaged runtime files while preserving runtime data and production configuration under:

```text
C:\ProgramData\CareQueue
```

### Repair

Repair is used when CareQueue is already installed.

Repair restores application files, packaged runtime files, service files, and expected installation structure while preserving runtime data and production configuration.

### Uninstall

Uninstall removes CareQueue application files and Windows services.

Uninstall deliberately preserves runtime data under:

```text
C:\ProgramData\CareQueue
```

This preserves configuration, database files, backups, Caddy runtime files, logs, restore staging, and recovery staging unless they are removed manually after review.

## Build Prerequisites

These prerequisites are needed to build the installer package from source.

They are not intended to be required on an ordinary target machine running the packaged installer.

### 1. Windows and administrator access

Use a supported Windows system. Build and installer validation commands that install services or write under protected locations should be run from:

```text
PowerShell as Administrator
```

The deployment scripts use Windows-specific commands such as:

- `icacls`
- `Get-Service`
- `Start-Service`
- `Stop-Service`
- Scheduled Tasks cmdlets
- The Local Machine certificate store

### 2. Repository checkout

Have a clean local copy of the CareQueue repository.

Example:

```text
G:\CareQueue
```

Review the working tree before building a release package:

```powershell
git status --short
```

Do not build a release package from a working tree containing unknown changes, real data, local secrets, private PDFs, or temporary restored databases.

### 3. Build Python

The payload builder needs a build-time Python executable on PATH, or an explicit path supplied through `-BuildPythonExecutable`.

Confirm Python works:

```powershell
python --version
```

### 4. Embedded Python archive

The payload builder needs a Windows embedded Python ZIP archive.

Example:

```text
G:\CareQueue\local_installer_assets\python-3.14.6-embed-amd64.zip
```

This archive is used to create the private packaged runtime under:

```text
build\windows\components\python-runtime
```

and then in the installer payload under:

```text
build\windows\payload\runtime\python
```

### 5. Node.js and npm

Install Node.js and npm on the build machine.

Confirm both are available:

```powershell
node --version
npm --version
```

The payload builder uses npm to install frontend dependencies and build the production frontend.

### 6. Inno Setup

Install Inno Setup on the build machine.

The expected compiler path used in this guide is:

```text
C:\Program Files\Inno Setup 7\ISCC.exe
```

### 7. Network access for vendor assets

The payload build process can download pinned Caddy and WinSW assets using:

```text
deployment/windows/installer/vendor-assets.json
```

The downloaded assets are validated by SHA256 before use.

If the assets are already cached and valid, the builder can reuse the cached files.

## Build the Installer Payload

From the repository root:

```powershell
.\deployment\windows\installer\build-payload.ps1 `
    -EmbeddedPythonArchive "G:\CareQueue\local_installer_assets\python-3.14.6-embed-amd64.zip"
```

The default output directory is:

```text
build\windows\payload
```

The payload contains the files that Inno Setup packages into the installer EXE.

If a previous payload exists and should be replaced, run without `-KeepExisting`. The script removes and rebuilds the payload by default.

To force vendor downloads again:

```powershell
.\deployment\windows\installer\build-payload.ps1 `
    -EmbeddedPythonArchive "G:\CareQueue\local_installer_assets\python-3.14.6-embed-amd64.zip" `
    -ForceVendorDownload
```

## Compile the Installer EXE

After building the payload, compile the Inno Setup script:

```powershell
& "C:\Program Files\Inno Setup 7\ISCC.exe" ".\deployment\windows\installer\CareQueue.iss"
```

The default output is:

```text
build\windows\installer\CareQueue-Setup-0.1.0.exe
```

The exact filename follows the version configured in `CareQueue.iss`.

## Run the Packaged Installer

Run the compiled installer:

```powershell
.\build\windows\installer\CareQueue-Setup-0.1.0.exe
```

If PowerShell requires an explicit invocation path:

```powershell
& "G:\CareQueue\build\windows\installer\CareQueue-Setup-0.1.0.exe"
```

The installer requires administrator elevation because it installs services and writes to protected directories.

## First-Time Admin Setup

CareQueue does not provide public account registration.

After a packaged Windows installation completes, the installer can launch the first-time Admin setup window:

```text
CareQueue-AdminSetup.ps1
```

The setup window calls the local CareQueue API over loopback:

```text
http://127.0.0.1:8000/api/security/setup-initial-admin/status
http://127.0.0.1:8000/api/security/setup-initial-admin
```

The setup window creates the first Admin without passing the password through command-line arguments.

The first-time setup endpoint is available only while no users exist. After any user exists, the backend disables the initial Admin setup endpoint and the setup window reports that setup is already complete.

The first Admin password must be at least 12 characters.

## Choose a Private Application Origin

The packaged installer currently uses:

```text
https://carequeue.local
```

The production origin must be an HTTPS origin. For the current private single-machine installation, use:

```text
https://carequeue.local
```

The origin must contain only:

- `https`
- A hostname
- An optional port

It must not contain:

- A path
- Credentials
- A query string
- A fragment

Valid example:

```text
https://carequeue.local
```

Invalid examples:

```text
http://carequeue.local
https://carequeue.local/app
https://user@carequeue.local
https://carequeue.local?mode=prod
```

Do not use `https://localhost` for the current production configuration. Production CORS validation rejects local development hosts.

## Add the Private Hostname

For a private single-machine installation, map the chosen hostname to the loopback address.

Open PowerShell as Administrator:

```powershell
$hostsFile = "$env:SystemRoot\System32\drivers\etc\hosts"

if (
    -not (
        Select-String `
            -Path $hostsFile `
            -SimpleMatch "carequeue.local" `
            -Quiet
    )
) {
    Add-Content `
        -Path $hostsFile `
        -Value "`r`n127.0.0.1 carequeue.local"
}
```

Confirm name resolution:

```powershell
ping carequeue.local
```

The hostname should resolve to:

```text
127.0.0.1
```

This hosts-file entry does not publish CareQueue to the internet. It only maps the hostname on the configured machine.

For a restricted-network deployment, use an approved internal DNS record instead of manually editing every hosts file.

## Development Environment Files

Vite environment files can change the API URL baked into the production frontend.

A development file may contain:

```env
VITE_AUTHSTATUS_API_BASE_URL=http://localhost:8000
```

For local development, prefer:

```text
frontend\.env.development.local
```

Do not leave a development override in a general `.env` file and assume it will be safe for production.

The payload builder and production installer include safeguards for production frontend builds, but the source tree should still be reviewed before packaging.

The production frontend should make same-origin requests such as:

```text
https://carequeue.local/api/security/me
```

It should not call:

```text
http://localhost:8000/api/security/me
```

## Validate an Installation

After installing, verify both services:

```powershell
Get-Service CareQueueApi, CareQueueCaddy |
Select-Object Name, Status, StartType
```

Expected service status after a normal install:

```text
Running
```

Check the loopback API health endpoint:

```powershell
Invoke-RestMethod `
    -Method Get `
    -Uri "http://127.0.0.1:8000/api/health" `
    -TimeoutSec 5
```

Check first-time setup status:

```powershell
Invoke-RestMethod `
    -Method Get `
    -Uri "http://127.0.0.1:8000/api/security/setup-initial-admin/status" `
    -TimeoutSec 5
```

Open the application through the approved HTTPS origin:

```text
https://carequeue.local
```

Confirm:

- The login page loads over HTTPS.
- First-time Admin setup works when no users exist.
- Existing Admin setup is blocked after a user exists.
- Login succeeds.
- Dashboard loads.
- Authorization queue loads.
- Logout succeeds.

Service status alone does not prove the full application is healthy. Verify the HTTPS endpoint and login workflow.

## Installer Logs

The packaged installer engine writes logs under:

```text
C:\ProgramData\CareQueue\Logs\Installer
```

View the newest installer log:

```powershell
$latestLog = Get-ChildItem `
    -Path "$env:ProgramData\CareQueue\Logs\Installer" `
    -Filter "CareQueue-*.log" `
    -ErrorAction SilentlyContinue |
Sort-Object LastWriteTime -Descending |
Select-Object -First 1

$latestLog.FullName

Get-Content `
    -LiteralPath $latestLog.FullName `
    -Tail 240
```

Review logs before sharing them. Do not post production logs publicly without checking for sensitive values, machine names, paths, usernames, operational details, or protected information.

## Service Logs

### API logs

```text
C:\ProgramData\CareQueue\Logs\Api
```

WinSW wrapper log:

```text
C:\ProgramData\CareQueue\Logs\Api\CareQueueApi.wrapper.log
```

Review recent API wrapper entries:

```powershell
Get-Content `
    "C:\ProgramData\CareQueue\Logs\Api\CareQueueApi.wrapper.log" `
    -Tail 100
```

### Caddy logs

```text
C:\ProgramData\CareQueue\Logs\Caddy
```

WinSW wrapper log:

```text
C:\ProgramData\CareQueue\Logs\Caddy\CareQueueCaddy.wrapper.log
```

Review all recent Caddy service logs:

```powershell
Get-ChildItem `
    "C:\ProgramData\CareQueue\Logs\Caddy" `
    -File |
ForEach-Object {
    Write-Host "`n=== $($_.Name) ==="
    Get-Content $_.FullName -Tail 100
}
```

## Service Management

Check status:

```powershell
Get-Service -Name "CareQueueApi", "CareQueueCaddy"
```

Stop in dependency order:

```powershell
Stop-Service -Name "CareQueueCaddy"
Stop-Service -Name "CareQueueApi"
```

Start in dependency order:

```powershell
Start-Service -Name "CareQueueApi"
Start-Service -Name "CareQueueCaddy"
```

Restart both:

```powershell
Stop-Service -Name "CareQueueCaddy"
Restart-Service -Name "CareQueueApi"
Start-Service -Name "CareQueueCaddy"
```

Wait before checking health:

```powershell
Start-Sleep -Seconds 3
```

## Uninstall Behavior

The packaged Uninstall operation removes:

- `CareQueueCaddy` service
- `CareQueueApi` service
- Application files under `C:\Program Files\CareQueue`

The packaged Uninstall operation preserves:

```text
C:\ProgramData\CareQueue
```

After uninstall, verify:

```powershell
Get-Service CareQueueApi, CareQueueCaddy -ErrorAction SilentlyContinue

Test-Path "C:\Program Files\CareQueue"
Test-Path "C:\ProgramData\CareQueue"
Test-Path "C:\ProgramData\CareQueue\Config\carequeue.env"
Test-Path "C:\ProgramData\CareQueue\Data\auth_tracker.sqlcipher.db"
```

Expected after a normal uninstall with existing runtime data:

```text
No service output
False
True
True
True
```

Do not delete `C:\ProgramData\CareQueue` unless the data-retention and backup requirements have been reviewed.

## Fresh Install After Uninstall

Because uninstall preserves ProgramData, a later Install can reuse the preserved production configuration and database.

After reinstalling, verify:

- Services are running.
- The health endpoint responds.
- Existing Admin setup is not offered if users already exist.
- Existing login credentials still work.
- Existing authorization data is still present.

## Lower-Level PowerShell Scripts

The packaged installer is the normal private Windows installation path.

The lower-level PowerShell scripts remain useful for development, troubleshooting, and direct validation of installer modes.

The lower-level installer engine is:

```text
deployment/windows/installer/invoke-install.ps1
```

Direct mode example:

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

For direct Uninstall, `-ApplicationOrigin` is not required.

The older production script remains available:

```text
deployment/windows/install-production.ps1
```

Prefer the packaged installer for normal release validation because it exercises the same path an end user will run.

## Backup Task

CareQueue includes scripts for encrypted backup operation and scheduled backup task management:

```text
deployment/windows/run-backup.ps1
deployment/windows/install-backup-task.ps1
deployment/windows/remove-backup-task.ps1
```

Install the scheduled backup task only after confirming the production installation, runtime paths, retention policy, and recovery responsibilities.

Existing backup files should be protected and recovery-tested according to the backup and recovery guide.

## Clean-Machine Validation

Before treating a Windows installer build as stable, validate it on a clean machine or clean VM that has not previously hosted CareQueue.

At minimum, test:

- Fresh install on a clean Windows 11 VM
- First-time Admin setup with no existing users
- Browser access to `https://carequeue.local`
- Login
- Reboot and service auto-start
- Repair
- Upgrade over an existing install
- Uninstall with ProgramData preserved
- Fresh install after uninstall using preserved data

Ideally, repeat the same matrix on a clean supported Windows 10 VM.

Local developer-machine success is useful, but it does not replace clean-machine testing.

## Troubleshooting

### Installer shows only Install

This is expected when CareQueue is not currently installed.

The Upgrade, Repair, and Uninstall options appear only when the installer detects an existing installation under:

```text
C:\Program Files\CareQueue
```

The detection checks for required installed files such as:

```text
backend\authstatus_api
frontend\dist\index.html
runtime\python\python.exe
vendor\caddy\caddy.exe
```

### Installer says CareQueue is already installed

Use the operation page to choose:

```text
Upgrade existing installation
Repair existing installation
Uninstall CareQueue
```

Install mode is only for a machine where CareQueue is not already installed.

### First-time Admin setup says setup is already complete

This means at least one user already exists in the production database.

Use the existing Admin account to sign in and manage users.

If the Admin password is lost, use the approved password reset or recovery procedure. Do not delete production data to reopen first-time setup unless the deployment is disposable and has no retained data requirements.

### Production frontend calls `localhost:8000`

Symptom:

Browser requests use:

```text
http://localhost:8000/api/...
```

instead of:

```text
https://carequeue.local/api/...
```

Cause:

A Vite development API override was included in the production build.

Check frontend environment files:

```powershell
Get-ChildItem `
    ".\frontend" `
    -Force `
    -File `
    -Filter ".env*"
```

Inspect only API URL lines:

```powershell
Get-ChildItem `
    ".\frontend" `
    -Force `
    -File `
    -Filter ".env*" |
ForEach-Object {
    Write-Host "`n=== $($_.Name) ==="

    Select-String `
        -Path $_.FullName `
        -Pattern "VITE_AUTHSTATUS_API_BASE_URL|VITE_API_BASE_URL"
}
```

Keep development configuration in:

```text
frontend\.env.development.local
```

Then rebuild the payload and installer.

### `/api/security/me` returns 401 before login

This is expected when no active session exists.

The frontend uses that request to check whether the browser is already authenticated.

After successful login, authenticated session checks should succeed.

### API service remains `StartPending`

Wait briefly:

```powershell
Start-Sleep -Seconds 3

Get-Service -Name "CareQueueApi"
```

If it stops, inspect:

```text
C:\ProgramData\CareQueue\Logs\Api
```

### Caddy service starts and then stops

Inspect:

```text
C:\ProgramData\CareQueue\Logs\Caddy
```

Common causes include:

- Port 443 is already in use.
- The installed Caddyfile is invalid.
- Caddy cannot access its runtime directory.
- Another service is holding a required port.
- The service XML does not match the installed path.

Validate the installed Caddyfile with the packaged Caddy executable:

```powershell
& "C:\Program Files\CareQueue\vendor\caddy\caddy.exe" `
    validate `
    --config "C:\Program Files\CareQueue\deployment\windows\Caddyfile" `
    --adapter caddyfile
```

Expected final line:

```text
Valid configuration
```

### Caddy cannot bind port 80

The current Caddyfile disables automatic HTTP redirects:

```caddyfile
auto_https disable_redirects
```

Confirm the installed Caddyfile contains the global options block.

### Browser reports an untrusted certificate

Confirm the Caddy root certificate exists:

```powershell
Test-Path `
    "C:\ProgramData\CareQueue\Caddy\Data\caddy\pki\authorities\local\root.crt"
```

Import it into:

```text
Cert:\LocalMachine\Root
```

Close and reopen the browser after importing when necessary.

### CareQueue hostname does not resolve

Check:

```powershell
ping carequeue.local
```

Confirm the hosts file contains:

```text
127.0.0.1 carequeue.local
```

For network deployments, confirm internal DNS.

### Production CORS validation rejects the origin

The current production configuration rejects local development hosts such as `localhost`.

Use an approved private hostname and ensure the environment file contains a matching origin:

```env
AUTHSTATUS_CORS_ORIGINS=["https://carequeue.local"]
```

Do not paste other environment values while checking this line.

### Access denied reading `carequeue.env`

Run the installer from PowerShell as Administrator.

Inspect permissions without printing file contents:

```powershell
icacls.exe `
    "C:\ProgramData\CareQueue\Config\carequeue.env"
```

Do not weaken permissions broadly to make troubleshooting easier.

The production environment should be readable only by the approved service context and authorized administrators.

### Health endpoint works but login fails

Check:

- The browser is using `https://carequeue.local`.
- The production frontend uses same-origin `/api` requests.
- The user was created against the production database.
- The password is correct.
- The account role is valid.
- Cookies are enabled.
- The system clock is correct.
- The browser is not blocking the private certificate.
- API and Caddy logs do not show a startup or session error.

A user created against the development `.env` and development database will not automatically exist in the production database.

## Production Database Is a Separate Instance

The production installation uses the database configured in:

```text
C:\ProgramData\CareQueue\Config\carequeue.env
```

The default installed database lives under:

```text
C:\ProgramData\CareQueue\Data
```

It is separate from a development database under the repository.

Creating the first production Admin writes that user to the production database.

Development data is not copied automatically.

Do not copy a development database into production without a reviewed migration and encryption procedure.

## Security Checklist

Before using CareQueue with sensitive information, confirm:

- The application is accessed only through approved HTTPS.
- The API remains bound to loopback.
- The hostname resolves only where intended.
- The Caddy root certificate is trusted only on approved systems.
- The production environment file is restricted.
- Runtime directories are restricted.
- SQLCipher mode is enabled.
- Production encryption keys are backed up securely.
- Backup keys are stored separately from backups.
- Encrypted backup procedures are configured and tested.
- Restoration has been tested.
- Service logs are protected and reviewed.
- Windows and dependencies are patched.
- Access is limited to approved users.
- User removal and password-reset procedures exist.
- Real data is not used in public screenshots, issues, or tests.
- Incident response and recovery responsibilities are documented.
- Legal and compliance review is complete.

## Files Used by This Deployment

The main Windows deployment files are:

```text
deployment/windows/
├── Caddyfile
├── CareQueue-AdminSetup.ps1
├── CareQueueApi.xml
├── CareQueueCaddy.xml
├── install-production.ps1
├── install-api-service.ps1
├── install-caddy-service.ps1
├── remove-api-service.ps1
├── remove-caddy-service.ps1
├── run-api.ps1
├── install-backup-task.ps1
├── remove-backup-task.ps1
├── run-backup.ps1
├── uninstall-production.ps1
└── installer/
    ├── CareQueue.iss
    ├── build-payload.ps1
    ├── build-python-runtime.ps1
    ├── build-vendor-assets.ps1
    ├── build-wheelhouse.ps1
    ├── invoke-install.ps1
    └── vendor-assets.json
```

The exact source files in the current repository remain authoritative. Review them before modifying paths, service accounts, ports, certificate behavior, installer modes, or release packaging.

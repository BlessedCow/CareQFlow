# Windows Deployment

This guide covers a private Windows installation of CareQueue using:

- The production installer in `deployment/windows/install-production.ps1`
- WinSW for the CareQueue API and Caddy Windows services
- Caddy for private HTTPS
- A local hostname such as `carequeue.local`
- SQLCipher-backed production storage
- Encrypted scheduled backups

The built-in Windows deployment is intended for a private workstation or a restricted network. It is not a public internet deployment template.

CareQueue’s security controls do not establish HIPAA compliance by themselves. Before using real protected health information, review [SECURITY.md](../../SECURITY.md), [DISCLAIMER.md](../../DISCLAIMER.md), and the organization’s legal, operational, and compliance requirements.

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

The production installer separates application files from runtime data.

### Application files

```text
C:\Program Files\CareQueue
```

This includes:

```text
backend/
frontend/
deployment/
Service/
```

The installed backend has its own virtual environment:

```text
C:\Program Files\CareQueue\backend\.venv
```

### Runtime data

```text
C:\ProgramData\CareQueue
```

The installer creates or uses directories for:

```text
Backups/
Caddy/
Config/
Data/
Logs/
Recovery/
Restores/
```

The production environment file is:

```text
C:\ProgramData\CareQueue\Config\carequeue.env
```

Do not commit, copy into documentation, paste into an issue, or share the contents of this file. It contains production encryption keys and other sensitive configuration.

## Windows Services

A complete installation uses two Windows services:

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

## Prerequisites

Complete these steps before running the production installer.

### 1. Supported Windows environment

Use an administrator account on a supported Windows system.

The installation and service scripts must be run from:

```text
PowerShell as Administrator
```

The current deployment scripts use Windows PowerShell-compatible syntax and Windows-specific commands such as:

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

The production installer builds from the current repository contents, so review the working tree before installation:

```powershell
git status --short
```

Do not build production from a working tree containing unknown changes, real data, or local secrets.

### 3. Python

Install a supported Python version and know the full path to `python.exe`.

Example:

```text
C:\Python314\python.exe
```

Confirm it works:

```powershell
& "C:\Python314\python.exe" --version
```

The production installer creates a separate virtual environment inside the installed application directory and installs the backend requirements there.

### 4. Node.js and npm

Install Node.js and npm.

Confirm both are available:

```powershell
node --version
npm --version
```

The production installer runs:

```text
npm ci
npm run build
```

against the repository frontend.

### 5. Caddy

Install the Caddy executable at:

```text
C:\Program Files (x86)\Caddy\caddy.exe
```

Confirm the file exists:

```powershell
Test-Path `
    "C:\Program Files (x86)\Caddy\caddy.exe" `
    -PathType Leaf
```

Expected:

```text
True
```

Confirm Caddy starts:

```powershell
& "C:\Program Files (x86)\Caddy\caddy.exe" version
```

The current service definition uses this exact path. A different path requires updating both the service XML and the installation command parameters consistently.

### 6. WinSW

CareQueue uses WinSW as the Windows service wrapper.

Before installing the API service, place a WinSW executable at:

```text
C:\Program Files\CareQueue\Service\CareQueueApi.exe
```

The executable name matters. WinSW uses the matching XML file beside the executable:

```text
CareQueueApi.exe
CareQueueApi.xml
```

The Caddy service installer copies the API WinSW executable to:

```text
CareQueueCaddy.exe
```

and pairs it with:

```text
CareQueueCaddy.xml
```

Use a trusted WinSW release and verify the downloaded file according to the release publisher’s instructions.

Do not commit the WinSW executable into the repository unless the project later adopts a reviewed binary-distribution policy.

## Choose a Private Application Origin

The production installer requires an absolute HTTPS origin.

For a single-machine private installation, this guide uses:

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

The production installer temporarily moves these files out of the frontend directory during the build and restores them afterward:

```text
.env
.env.local
.env.production
.env.production.local
```

The production frontend should make same-origin requests such as:

```text
https://carequeue.local/api/security/me
```

It should not call:

```text
http://localhost:8000/api/security/me
```

## First Production Installation

Run the installer from the repository root in PowerShell as Administrator.

Example:

```powershell
Set-Location "G:\CareQueue"

.\deployment\windows\install-production.ps1 `
    -ApplicationOrigin "https://carequeue.local" `
    -PythonExecutable "C:\Python314\python.exe"
```

Do not use `-Force` for a clean first installation unless an incomplete application directory already exists and has been reviewed.

### What the installer does

The installer:

1. Validates the HTTPS application origin.
2. Verifies required source files.
3. Creates a temporary staging area.
4. Builds the production frontend.
5. Copies backend and deployment files into staging.
6. Replaces the Caddy hostname placeholder.
7. Creates production runtime directories.
8. Generates independent production encryption keys on the first installation.
9. Writes the production environment file.
10. Installs the staged application files.
11. Creates the production backend virtual environment.
12. Installs backend dependencies.
13. Loads the production environment.
14. Imports the installed backend to validate it.
15. Applies restricted runtime permissions.
16. Restores previously running services during an upgrade.

The installer does not automatically install the API or Caddy services during the first installation.

### Generated production settings

The first installation generates independent values for:

```text
AUTHSTATUS_ENCRYPTION_KEY
AUTHSTATUS_SQLCIPHER_KEY
AUTHSTATUS_BACKUP_ENCRYPTION_KEY
```

It also configures production behavior including:

```text
AUTHSTATUS_APP_ENVIRONMENT=production
AUTHSTATUS_DATABASE_ENCRYPTION=sqlcipher
AUTHSTATUS_SESSION_COOKIE_SECURE=true
```

The default runtime paths point to `C:\ProgramData\CareQueue`.

The default backup policy created by the installer is:

```text
Retention: 90 days
Minimum retained backups: 5
```

Review the organization’s requirements before changing those values.

### Successful result

A successful installation ends with output similar to:

```text
CareQueue production files installed successfully.
Application directory: C:\Program Files\CareQueue
Runtime data directory: C:\ProgramData\CareQueue
Environment file: C:\ProgramData\CareQueue\Config\carequeue.env
Application origin: https://carequeue.local
```

For a first installation with no running CareQueue services, the installer reports that no running services required restoration.

## Validate the Installed Backend

The installer performs an import check automatically.

You may also verify that the expected files exist:

```powershell
Test-Path `
    "C:\Program Files\CareQueue\backend\.venv\Scripts\python.exe"

Test-Path `
    "C:\ProgramData\CareQueue\Config\carequeue.env"

Test-Path `
    "C:\Program Files\CareQueue\deployment\windows\Caddyfile"
```

All three should return:

```text
True
```

Do not print the production environment file to a shared terminal transcript.

## Install the API Service

The API service installer expects:

```text
C:\Program Files\CareQueue\Service\CareQueueApi.exe
```

to already contain the WinSW executable.

Install and start the service:

```powershell
& "C:\Program Files\CareQueue\deployment\windows\install-api-service.ps1" `
    -StartService
```

The script:

- Requires administrator access
- Validates the installed service XML
- Copies `CareQueueApi.xml` beside the WinSW executable
- Refuses to overwrite an existing Windows service
- Installs `CareQueueApi`
- Optionally starts it

The immediate status may briefly show:

```text
StartPending
```

Wait and check again:

```powershell
Start-Sleep -Seconds 3

Get-Service -Name "CareQueueApi"
```

Expected:

```text
Running
```

Test the API directly on loopback:

```powershell
Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/api/health/live"
```

Expected response:

```text
status  app             version
------  ---             -------
ok      AuthStatus API  0.1.0
```

The exact version may change over time.

## Install the Caddy Service

Install and start Caddy after the API service is installed:

```powershell
& "C:\Program Files\CareQueue\deployment\windows\install-caddy-service.ps1" `
    -StartService
```

The script:

- Requires administrator access
- Validates the installed Caddy service XML
- Validates the installed Caddyfile
- Confirms the API service exists
- Creates Caddy data, configuration, and log directories
- Copies WinSW to `CareQueueCaddy.exe`
- Copies `CareQueueCaddy.xml` beside it
- Installs `CareQueueCaddy`
- Optionally starts it

Wait and verify both services:

```powershell
Start-Sleep -Seconds 3

Get-Service -Name "CareQueueApi", "CareQueueCaddy"
```

Expected:

```text
Running  CareQueueApi
Running  CareQueueCaddy
```

## Why HTTP Redirects Are Disabled

The Windows Caddyfile contains:

```caddyfile
{
	auto_https disable_redirects
	skip_install_trust
}
```

`disable_redirects` prevents Caddy from creating the automatic HTTP listener used only to redirect port 80 traffic to HTTPS.

CareQueue’s private deployment accesses the application directly over HTTPS, so an HTTP listener is unnecessary.

`skip_install_trust` prevents the Windows service from trying to modify the machine certificate store while running in the service context. The root certificate is imported deliberately by an administrator instead.

## Trust the Caddy Root Certificate

Caddy creates a local certificate authority for the private hostname.

The root certificate is stored at:

```text
C:\ProgramData\CareQueue\Caddy\Data\caddy\pki\authorities\local\root.crt
```

Confirm the certificate exists:

```powershell
$rootCertificate = (
    "C:\ProgramData\CareQueue\Caddy\Data\caddy\" +
    "pki\authorities\local\root.crt"
)

Test-Path `
    -LiteralPath $rootCertificate `
    -PathType Leaf
```

Expected:

```text
True
```

Import it into the Local Machine trusted root store:

```powershell
Import-Certificate `
    -FilePath $rootCertificate `
    -CertStoreLocation "Cert:\LocalMachine\Root"
```

The command displays the imported certificate thumbprint and subject.

Only trust the root certificate generated by the intended CareQueue Caddy instance.

For a managed network, certificate distribution should follow the organization’s approved certificate and endpoint-management process.

## Verify Private HTTPS

Test the HTTPS health endpoint:

```powershell
Invoke-RestMethod `
    -Uri "https://carequeue.local/api/health/live"
```

Expected:

```text
status  app             version
------  ---             -------
ok      AuthStatus API  0.1.0
```

Test readiness:

```powershell
Invoke-RestMethod `
    -Uri "https://carequeue.local/api/health/ready"
```

Readiness should report success only when the application can also query the configured database.

Open the frontend:

```text
https://carequeue.local
```

The browser should display the CareQueue login page without a certificate warning.

## Create the First Production User

CareQueue does not provide public registration.

Create the first user from the installed backend using the production environment.

Open PowerShell as Administrator:

```powershell
Set-Location "C:\Program Files\CareQueue\backend"

$environmentFile = (
    "C:\ProgramData\CareQueue\Config\carequeue.env"
)

Get-Content -LiteralPath $environmentFile |
ForEach-Object {
    $line = $_.Trim()

    if (
        $line `
        -and -not $line.StartsWith("#") `
        -and $line.Contains("=")
    ) {
        $name, $value = $line.Split("=", 2)

        [Environment]::SetEnvironmentVariable(
            $name.Trim(),
            $value.Trim(),
            "Process"
        )
    }
}

& ".\.venv\Scripts\python.exe" `
    ".\scripts\create_user.py" `
    --username "carequeue.admin" `
    --role "Admin"
```

The script prompts for a password and confirmation.

Password requirements enforced by the script include:

```text
Minimum length: 12 characters
```

The password is not displayed while typing.

Available roles are:

```text
Admin
UR
Read Only
```

Use a role-based or organizational username rather than a personal name when that fits the deployment’s account-management policy.

After creation, sign in at:

```text
https://carequeue.local
```

## Expected 401 Responses

Before login, the frontend checks whether a session already exists.

A request such as:

```text
GET https://carequeue.local/api/security/me
```

may return:

```text
401 Unauthorized
```

when the browser is logged out. That is expected.

Protected endpoints may also return 401 until authentication succeeds.

After a successful login, session-aware requests should return normally.

The important production check is the request origin. Requests should use:

```text
https://carequeue.local/api/...
```

They should not use:

```text
http://localhost:8000/api/...
```

A localhost API URL in the production browser normally means a development Vite environment override was included in the frontend build.

## Install the Scheduled Backup Task

CareQueue includes a daily encrypted backup task.

Install the default task:

```powershell
& "C:\Program Files\CareQueue\deployment\windows\install-backup-task.ps1"
```

Defaults:

```text
Task name: CareQueue Encrypted Backup
Run time: 02:00
Account: SYSTEM
Backup directory: C:\ProgramData\CareQueue\Backups
```

Use a different daily time:

```powershell
& "C:\Program Files\CareQueue\deployment\windows\install-backup-task.ps1" `
    -RunAt "03:30"
```

`RunAt` uses 24-hour `HH:mm` format.

Use a dedicated service account:

```powershell
& "C:\Program Files\CareQueue\deployment\windows\install-backup-task.ps1" `
    -ServiceAccount "DOMAIN\CareQueueBackup"
```

The script prompts for that account’s password.

The account must have permission to:

- Read installed application files
- Execute the installed Python environment
- Read the production environment file
- Read the active database
- Write to the backup directory

Do not place encryption keys or passwords in scheduled-task arguments.

### Verify the task

```powershell
Get-ScheduledTask `
    -TaskName "CareQueue Encrypted Backup"
```

Start a manual test run:

```powershell
Start-ScheduledTask `
    -TaskName "CareQueue Encrypted Backup"
```

Wait briefly, then review task information:

```powershell
Get-ScheduledTaskInfo `
    -TaskName "CareQueue Encrypted Backup"
```

Confirm that a recent encrypted backup exists:

```powershell
Get-ChildItem `
    "C:\ProgramData\CareQueue\Backups" `
    -File |
Sort-Object LastWriteTime -Descending |
Select-Object -First 5 `
    Name,
    Length,
    LastWriteTime
```

A successful task result is not enough by itself. Confirm that the backup exists, is nonempty, and can be restored through the approved staging workflow.

See [Backup and Recovery](../workflows/backup-and-recovery.md) for backup verification and restoration procedures.

## Manual Backup

Run the installed backup runner:

```powershell
& "C:\Program Files\CareQueue\deployment\windows\run-backup.ps1"
```

The runner:

- Loads the production environment
- Uses the installed Python virtual environment
- Writes to the production backup directory
- Invokes the encrypted backup script

Review the output and confirm the resulting file exists.

## Production Upgrade

Use the production installer with `-Force` for an existing installation.

From the updated repository root:

```powershell
.\deployment\windows\install-production.ps1 `
    -ApplicationOrigin "https://carequeue.local" `
    -PythonExecutable "C:\Python314\python.exe" `
    -Force
```

### Upgrade behavior

When the services are running, the installer:

1. Builds and stages the updated application.
2. Preserves the existing production environment file.
3. Stops `CareQueueCaddy`.
4. Stops `CareQueueApi`.
5. Replaces installed application files.
6. Recreates the installed backend virtual environment.
7. Installs dependencies.
8. Validates the installed backend.
9. Reapplies runtime permissions.
10. Starts `CareQueueApi`.
11. Starts `CareQueueCaddy`.

The service order matters:

```text
Stop:
CareQueueCaddy
CareQueueApi

Start:
CareQueueApi
CareQueueCaddy
```

Only services that were running before the upgrade are restarted.

If installation fails after the services were stopped, the installer attempts to restore their previous running state.

### Before upgrading

Before every production upgrade:

- Confirm the source tree is trusted.
- Run backend and frontend tests.
- Confirm a recent encrypted backup exists.
- Confirm the backup key is recoverable.
- Review dependency and configuration changes.
- Keep recovery instructions available.
- Avoid making unrelated configuration changes during the upgrade.

Recommended repository checks:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest tests -n auto -q
python -m ruff check . --fix
```

Then:

```powershell
cd ..\frontend
npm test
npm run build
```

### After upgrading

Check the services:

```powershell
Get-Service -Name "CareQueueApi", "CareQueueCaddy"
```

Check liveness:

```powershell
Invoke-RestMethod `
    -Uri "https://carequeue.local/api/health/live"
```

Check readiness:

```powershell
Invoke-RestMethod `
    -Uri "https://carequeue.local/api/health/ready"
```

Then sign in and verify a basic workflow using approved test or synthetic data.

## Verify Service Startup After Reboot

Both services use automatic startup.

After a planned restart:

```powershell
Get-Service -Name "CareQueueApi", "CareQueueCaddy"
```

Then:

```powershell
Invoke-RestMethod `
    -Uri "https://carequeue.local/api/health/live"
```

Do not assume service status alone proves the full application is healthy. Verify the HTTPS endpoint and login workflow.

## Service Logs

### API logs

```text
C:\ProgramData\CareQueue\Logs\Api
```

WinSW wrapper log:

```text
C:\ProgramData\CareQueue\Logs\Api\CareQueueApi.wrapper.log
```

Review the latest API wrapper entries:

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

Do not post full production logs publicly without reviewing them for sensitive values, machine names, paths, and operational details.

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

## Remove the Caddy Service

Run:

```powershell
& "C:\Program Files\CareQueue\deployment\windows\remove-caddy-service.ps1"
```

The removal script:

- Stops the service when needed
- Uninstalls `CareQueueCaddy`
- Waits for the service to disappear
- Removes the Caddy WinSW executable and installed XML

It deliberately preserves:

```text
C:\ProgramData\CareQueue\Caddy
C:\ProgramData\CareQueue\Logs\Caddy
```

This preserves the local certificate authority and logs during a service reinstall.

## Remove the API Service

Remove Caddy first because it depends on the API.

Then run:

```powershell
& "C:\Program Files\CareQueue\deployment\windows\remove-api-service.ps1"
```

The API removal script removes the Windows service. Review its output before deleting any application or runtime files.

## Remove the Scheduled Backup Task

Run:

```powershell
& "C:\Program Files\CareQueue\deployment\windows\remove-backup-task.ps1"
```

This removes the scheduled task named:

```text
CareQueue Encrypted Backup
```

It does not delete existing backup files.

## Reinstall a Service

A service installer refuses to overwrite an existing Windows service.

For Caddy:

```powershell
& "C:\Program Files\CareQueue\deployment\windows\remove-caddy-service.ps1"

& "C:\Program Files\CareQueue\deployment\windows\install-caddy-service.ps1" `
    -StartService
```

For the API, remove Caddy first, then remove and reinstall the API:

```powershell
& "C:\Program Files\CareQueue\deployment\windows\remove-caddy-service.ps1"

& "C:\Program Files\CareQueue\deployment\windows\remove-api-service.ps1"

& "C:\Program Files\CareQueue\deployment\windows\install-api-service.ps1" `
    -StartService

& "C:\Program Files\CareQueue\deployment\windows\install-caddy-service.ps1" `
    -StartService
```

## Troubleshooting

### Installer cannot remove `_rust.pyd`

Example:

```text
Access to the path '_rust.pyd' is denied.
```

Cause:

The running API service has loaded a compiled Python dependency from the installed virtual environment.

Current installer behavior should stop the running services automatically during a forced upgrade.

If working with an older installer, stop Caddy and the API before rerunning:

```powershell
Stop-Service -Name "CareQueueCaddy"
Stop-Service -Name "CareQueueApi"
```

Then run the installer with `-Force`.

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

Inspect only the API URL lines:

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

Then rebuild and reinstall.

The current installer temporarily removes production-relevant Vite environment files during the build as an additional safeguard.

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
- The Caddy executable path is wrong.
- The installed Caddyfile is invalid.
- Caddy cannot access its runtime directory.
- Another service is holding a required port.
- The service XML does not match the installed path.

Validate the installed Caddyfile:

```powershell
& "C:\Program Files (x86)\Caddy\caddy.exe" `
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

Creating the first production user writes that user to the production database.

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
- Scheduled encrypted backups are running.
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
└── run-backup.ps1
```

The exact source files in the current repository remain authoritative. Review them before modifying paths, service accounts, ports, or certificate behavior.

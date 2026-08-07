# Windows Upgrades

This guide covers upgrading, repairing, and uninstalling an existing private Windows installation of CareQueue.

The normal private Windows path is the packaged installer:

```text
CareQueue-Setup-0.1.0.exe
```

The lower-level installer engine remains available for development, troubleshooting, and direct validation:

```text
deployment/windows/installer/invoke-install.ps1
```

The production services are:

```text
CareQueueApi
CareQueueCaddy
```

The upgrade process replaces installed application files while preserving production configuration and runtime data.

For first-time installation, see [Windows Deployment](../deployment/windows.md).

For backup and recovery, see [Backup and Recovery](../workflows/backup-and-recovery.md).

For service validation and smoke tests, see [Health Checks](health-checks.md).

## Installer Operation Modes

When CareQueue is not installed, the packaged installer shows the normal Install flow.

When CareQueue is already installed, the packaged installer offers these operation modes:

- **Upgrade existing installation**
- **Repair existing installation**
- **Uninstall CareQueue**

The installer detects an existing installation by checking for the installed backend, frontend, Python runtime, and Caddy files under:

```text
C:\Program Files\CareQueue
```

## Operation Summary

| Operation | Purpose | Preserves runtime data? | Starts services afterward? |
| --- | --- | --- | --- |
| Install | Install CareQueue on a machine without an existing installation | Creates new runtime data | Yes |
| Upgrade | Replace application files and packaged runtime files | Yes | Yes |
| Repair | Restore application files, packaged runtime files, and services | Yes | Yes |
| Uninstall | Remove application files and Windows services | Yes | No |

Runtime data is stored under:

```text
C:\ProgramData\CareQueue
```

## What an Upgrade Replaces

An upgrade may replace application files under:

```text
C:\Program Files\CareQueue
```

This includes:

```text
backend/
frontend/
deployment/
runtime/
vendor/
```

The packaged installer uses the private Python runtime and offline wheelhouse included in the installer payload.

The installed backend environment is recreated from the packaged runtime and bundled dependencies.

## What Repair Replaces

Repair is intended to restore a damaged or incomplete installation while preserving runtime data.

Repair may replace or restore:

- Installed backend files
- Installed frontend files
- Deployment scripts
- Private Python runtime files
- Packaged vendor binaries
- Windows service definitions
- Runtime directory structure
- Filesystem permissions

Repair does not reset Admin users, encryption keys, runtime data, active databases, or encrypted backups.

## What Uninstall Removes

Uninstall removes:

- CareQueue application files under `C:\Program Files\CareQueue`
- The `CareQueueApi` Windows service
- The `CareQueueCaddy` Windows service

Uninstall preserves:

- Runtime configuration
- Encryption keys
- Active database
- Encrypted backups
- Restore staging
- Recovery staging
- Logs
- Caddy runtime data
- Local certificate data

Preserved runtime data remains under:

```text
C:\ProgramData\CareQueue
```

## What an Upgrade Preserves

The installer preserves the production environment file:

```text
C:\ProgramData\CareQueue\Config\carequeue.env
```

This preserves settings and keys such as:

```text
AUTHSTATUS_ENCRYPTION_KEY
AUTHSTATUS_SQLCIPHER_KEY
AUTHSTATUS_BACKUP_ENCRYPTION_KEY
```

The installer also preserves runtime data under:

```text
C:\ProgramData\CareQueue
```

This includes:

- Active database
- Encrypted backups
- Restore staging
- Recovery staging
- Logs
- Caddy runtime data
- Local certificate data

## What the Installer Does Not Do

The installer does not automatically:

- Prove that the latest backup is recoverable
- Require a fresh pre-upgrade backup
- Rotate encryption keys
- Migrate to another database engine
- Roll back source code after a failed smoke test
- Restore an older database schema
- Validate every browser workflow
- Complete clean-machine VM certification
- Code sign the release package

These responsibilities remain part of the deployment, validation, and release process.

## Required Access

Run the installer with administrative privileges.

The installer needs elevated rights to:

- Write under `C:\Program Files`
- Write and secure `C:\ProgramData\CareQueue`
- Install, remove, stop, and start Windows services
- Replace installed files
- Recreate the installed backend runtime
- Reapply filesystem permissions

## Pre-Upgrade Checklist

Before upgrading:

- Review the source being packaged.
- Confirm the working tree contains only intended changes.
- Record the source commit.
- Run backend tests.
- Run Ruff.
- Run frontend tests.
- Run the frontend build.
- Build a fresh installer payload.
- Compile a fresh installer EXE.
- Confirm current production health.
- Create or confirm a recent encrypted backup.
- Confirm required recovery keys are available.
- Review dependency and configuration changes.
- Schedule a maintenance window.
- Keep rollback and recovery instructions available.

Do not begin while the current database or service state is uncertain.

## Review the Source

From the repository root:

```powershell
git status --short
git rev-parse HEAD
git log -1 --oneline
```

Do not deploy from a working tree containing:

- Unknown changes
- Real databases
- Real PDFs
- Environment files
- Backup files
- Temporary restored databases
- Unreviewed generated files
- Sensitive screenshots

## Run Backend Checks

From `backend`:

```powershell
pytest tests -n auto -q
ruff check . --fix
```

Optional release checks:

```powershell
bandit -r authstatus_api
pip-audit
```

## Run Frontend Checks

From `frontend`:

```powershell
npm test
npm run build
```

Optional dependency review:

```powershell
npm audit
```

## Confirm Current Production Health

Use the procedures in [Health Checks](health-checks.md).

At minimum, confirm:

- `CareQueueApi` is running
- `CareQueueCaddy` is running
- HTTPS liveness passes
- HTTPS readiness passes
- Login works
- The authorization queue loads

Do not use an upgrade to conceal an existing production failure.

## Create a Fresh Pre-Upgrade Backup

Run:

```powershell
& "C:\Program Files\CareQueue\deployment\windows\run-backup.ps1"
```

Confirm the new file exists:

```powershell
Get-ChildItem `
    "C:\ProgramData\CareQueue\Backups" `
    -Filter "*.db.enc" |
Sort-Object LastWriteTime -Descending |
Select-Object -First 3 `
    Name,
    Length,
    LastWriteTime
```

Record the selected backup filename in the change record.

A file listing does not prove recoverability. For higher-risk upgrades, verify or restore the selected backup into the approved restore area before proceeding.

## Review Frontend Environment Files

Development may use:

```env
VITE_AUTHSTATUS_API_BASE_URL=http://localhost:8000
```

Keep that setting in:

```text
frontend\.env.development.local
```

The production frontend should use same-origin API requests.

Review frontend environment files:

```powershell
Get-ChildItem `
    ".\frontend" `
    -Force `
    -File `
    -Filter ".env*"
```

Inspect API URL settings:

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

Do not store production secrets in frontend environment files.

## Build the Installer Payload

Build the Windows payload from the repository root:

```powershell
.\deployment\windows\installer\build-payload.ps1 `
    -EmbeddedPythonArchive "G:\CareQueue\local_installer_assets\python-3.14.6-embed-amd64.zip"
```

Use the approved local path for the embedded Python archive.

The payload build should create or update:

```text
build\windows\payload
```

## Compile the Packaged Installer

Compile the Inno Setup installer:

```powershell
& "C:\Program Files\Inno Setup 7\ISCC.exe" ".\deployment\windows\installer\CareQueue.iss"
```

The compiled installer should be created under:

```text
build\windows\installer
```

For version `0.1.0`, the expected installer filename is:

```text
CareQueue-Setup-0.1.0.exe
```

## Run the Upgrade Through the GUI Installer

Run the compiled installer:

```powershell
.\build\windows\installer\CareQueue-Setup-0.1.0.exe
```

If CareQueue is already installed, choose:

```text
Upgrade existing installation
```

Confirm the ready page describes the upgrade operation before continuing.

## Run Repair Through the GUI Installer

Run:

```powershell
.\build\windows\installer\CareQueue-Setup-0.1.0.exe
```

Choose:

```text
Repair existing installation
```

Repair should preserve runtime data and restore the installed application, services, and packaged runtime files.

## Run Uninstall Through the GUI Installer

Run:

```powershell
.\build\windows\installer\CareQueue-Setup-0.1.0.exe
```

Choose:

```text
Uninstall CareQueue
```

Confirm the ready page describes the uninstall operation before continuing.

After uninstall, confirm application files and services were removed while runtime data was preserved.

```powershell
Get-Service CareQueueApi, CareQueueCaddy -ErrorAction SilentlyContinue

Test-Path "C:\Program Files\CareQueue"
Test-Path "C:\ProgramData\CareQueue"
Test-Path "C:\ProgramData\CareQueue\Config\carequeue.env"
Test-Path "C:\ProgramData\CareQueue\Data\auth_tracker.sqlcipher.db"
```

Expected result after uninstall:

```text
No service output
False
True
True
True
```

## Direct Installer Engine Validation

The packaged installer calls the direct installer engine internally.

For development or troubleshooting, the engine can be run directly against the packaged payload.

Upgrade example:

```powershell
powershell.exe `
    -NoProfile `
    -NonInteractive `
    -ExecutionPolicy Bypass `
    -File ".\build\windows\payload\deployment\windows\installer\invoke-install.ps1" `
    -Mode Upgrade `
    -ApplicationOrigin "https://carequeue.local" `
    -PayloadDirectory ".\build\windows\payload" `
    -InstallDirectory "C:\Program Files\CareQueue" `
    -DataDirectory "C:\ProgramData\CareQueue"
```

Repair example:

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

Uninstall example:

```powershell
powershell.exe `
    -NoProfile `
    -NonInteractive `
    -ExecutionPolicy Bypass `
    -File ".\build\windows\payload\deployment\windows\installer\invoke-install.ps1" `
    -Mode Uninstall `
    -PayloadDirectory ".\build\windows\payload" `
    -InstallDirectory "C:\Program Files\CareQueue" `
    -DataDirectory "C:\ProgramData\CareQueue"
```

Use the GUI installer for normal operator validation. Use direct mode only when lower-level diagnostics are needed.

## Upgrade Sequence

The installer engine performs the upgrade in this general order:

1. Validate the application origin.
2. Verify required packaged payload files.
3. Create required runtime directories.
4. Read or create the production environment.
5. Stop Caddy.
6. Stop the API.
7. Replace installed application files.
8. Restore packaged Python runtime and vendor assets.
9. Recreate the installed backend environment.
10. Install backend dependencies from the packaged wheelhouse.
11. Validate the installed backend.
12. Reapply runtime permissions.
13. Start the API.
14. Start Caddy.
15. Run post-installation validation.

## Service Stop Order

The installer stops services in this order:

```text
1. CareQueueCaddy
2. CareQueueApi
```

Caddy is stopped first because it depends on the API.

## Service Start Order

The installer starts services in this order:

```text
1. CareQueueApi
2. CareQueueCaddy
```

The API starts first because Caddy proxies to it.

## Installed Backend Validation

After dependency installation, the installer loads the production environment and imports:

```text
authstatus_api.main
uvicorn
```

Successful output includes:

```text
CareQueue production backend validated.
```

This confirms the installed backend can load under production configuration.

It does not replace the post-upgrade smoke test.

## Post-Installation Validation

The installer engine validates that the expected services reach a running state and that the local API health check responds.

Successful logs may include:

```text
Post-installation validation completed successfully.
```

A successful installer validation does not replace browser smoke testing.

## Permission Hardening

The installer reapplies restricted permissions to:

```text
C:\ProgramData\CareQueue
```

The intended access includes:

- `SYSTEM`
- Built-in Administrators
- The administrator performing the installation

Do not broadly grant access to resolve unrelated failures.

## Installer Logs

Installer logs are stored under:

```text
C:\ProgramData\CareQueue\Logs\Installer
```

To inspect the newest installer log:

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

Review logs before sharing them.

## Successful Upgrade Output

Important successful lines include:

```text
Mode: Upgrade
CareQueue Upgrade operation completed successfully.
Post-installation validation completed successfully.
```

Review the full installer result. Dependency installation output alone does not prove success.

## Successful Repair Output

Important successful lines include:

```text
Mode: Repair
CareQueue Repair operation completed successfully.
Post-installation validation completed successfully.
```

## Successful Uninstall Output

Important successful lines include:

```text
Mode: Uninstall
CareQueue application files and Windows services were removed.
CareQueue data was preserved at: C:\ProgramData\CareQueue
Uninstall operation completed successfully.
```

## Post-Upgrade Validation

Run the post-upgrade procedure in [Health Checks](health-checks.md#post-upgrade-smoke-test).

At minimum, confirm:

- Both services are running
- HTTPS liveness passes
- HTTPS readiness passes
- The login page loads over HTTPS
- Login succeeds
- Dashboard loads
- Authorization queue loads
- Registered options load
- Logout succeeds
- A post-upgrade encrypted backup succeeds

Do not declare the upgrade complete based only on service status.

## Verify Backup Operation

Run:

```powershell
& "C:\Program Files\CareQueue\deployment\windows\run-backup.ps1"
```

Confirm a new encrypted backup appears.

This checks:

- Environment loading
- Database access
- Backup path handling
- Permissions
- Backup encryption

## Review Logs

API wrapper log:

```powershell
Get-Content `
    "C:\ProgramData\CareQueue\Logs\Api\CareQueueApi.wrapper.log" `
    -Tail 100
```

Caddy logs:

```powershell
Get-ChildItem `
    "C:\ProgramData\CareQueue\Logs\Caddy" `
    -File |
ForEach-Object {
    Write-Host "`n=== $($_.Name) ==="
    Get-Content $_.FullName -Tail 100
}
```

Review logs before sharing them.

## Record the Upgrade

Record:

- Upgrade date and time
- Administrator
- Source commit
- Previous version
- New version
- Installer filename
- Installer checksum
- Pre-upgrade backup filename
- Test results
- Installer result
- Service status
- Health-check results
- Login result
- Post-upgrade backup result
- Problems encountered
- Corrective actions
- Final approval

Do not include passwords, keys, tokens, cookies, PHI, or decrypted database content.

## Rollback Strategy

CareQueue does not currently provide a one-command code rollback.

A rollback plan requires:

- Previous trusted source
- Preserved production environment
- Recent encrypted backup
- Required encryption keys
- Installer access
- A reviewed database compatibility decision

Do not assume older code is compatible with a newer database schema.

## Code Rollback

When schema compatibility is confirmed:

1. Check out the previous trusted source.
2. Run tests.
3. Confirm database compatibility.
4. Build the payload and packaged installer for the approved source.
5. Run the installer against the target machine.
6. Run health checks.
7. Verify login and representative workflows.

Example:

```powershell
git checkout <approved-previous-commit>
```

Then build and run the approved installer package for that source.

## Database Rollback

Database rollback is a recovery operation.

Use:

```text
docs/workflows/backup-and-recovery.md
```

Do not manually overwrite the active database.

## Failed Upgrade Scenarios

### Python runtime files are locked

Cause:

A running process is using files from the packaged Python runtime or installed backend environment.

Check:

```powershell
Get-Service -Name "CareQueueApi", "CareQueueCaddy"
```

Also check whether developer tools are using the packaged runtime as an interpreter.

Use the project virtual environment for development instead of:

```text
build\windows\components\python-runtime\python.exe
```

### Frontend build fails during payload build

Because this happens before the packaged installer is compiled, the installed application is untouched.

Run:

```powershell
npm test
npm run build
```

Review frontend environment files and correct the source problem.

### Payload build fails

Review:

- Missing embedded Python archive
- Missing vendor asset
- Failed frontend build
- Failed wheelhouse build
- Locked build output files
- Unexpected source tree contents

Do not compile or release an installer from a failed or partial payload.

### Dependency installation fails

The installer may already have replaced files and stopped services.

Preserve:

```text
C:\ProgramData\CareQueue\Config\carequeue.env
C:\ProgramData\CareQueue\Data
C:\ProgramData\CareQueue\Backups
```

Review:

- Full package error
- Python compatibility
- Requirements changes
- Service status
- Whether post-installation validation ran

Do not repeatedly rerun the installer without understanding the current state.

### Backend validation fails

Possible causes:

- Invalid production configuration
- Missing dependency
- Incompatible Python version
- Invalid CORS origin
- Unsafe path rejection
- Database configuration error
- Source import error

Keep services stopped when the installed state is uncertain.

Do not paste production environment contents into troubleshooting output.

### Permission hardening fails

Inspect ACLs:

```powershell
icacls.exe `
    "C:\ProgramData\CareQueue"
```

Confirm the installer is elevated.

Do not grant `Everyone` broad access.

### API starts but Caddy does not

Check services and Caddy logs.

Validate the installed Caddyfile with the packaged Caddy binary:

```powershell
& "C:\Program Files\CareQueue\vendor\caddy\caddy.exe" `
    validate `
    --config "C:\Program Files\CareQueue\deployment\windows\Caddyfile" `
    --adapter caddyfile
```

### Health succeeds but login fails

Use [Health Checks](health-checks.md) to isolate the issue, then verify:

- The production user exists
- Cookies are enabled
- The certificate is trusted
- The production frontend uses same-origin API requests
- The system clock is correct

## Emergency Stop

To stop access quickly:

```powershell
Stop-Service -Name "CareQueueCaddy"
Stop-Service -Name "CareQueueApi"
```

Confirm:

```powershell
Get-Service -Name "CareQueueApi", "CareQueueCaddy"
```

Do not delete application or database files during an emergency stop.

## Upgrade Acceptance Checklist

Before declaring the upgrade complete:

- Repository checks passed.
- A recent encrypted backup exists.
- Required keys are recoverable.
- Installer payload built successfully.
- Packaged installer compiled successfully.
- Installer completed successfully.
- Installed backend validation passed.
- Permission hardening passed.
- Post-installation validation passed.
- Services are running.
- HTTPS liveness passed.
- HTTPS readiness passed.
- Login succeeded.
- Dashboard loaded.
- Authorization queue loaded.
- Registered options loaded.
- Logout and login were tested.
- A post-upgrade backup succeeded.
- Logs were reviewed.
- Upgrade details were recorded.
- The change owner accepted the result.

## Repair Acceptance Checklist

Before declaring repair complete:

- Installer completed in Repair mode.
- Runtime data was preserved.
- Services are running.
- HTTPS liveness passed.
- HTTPS readiness passed.
- Login succeeded.
- Dashboard loaded.
- Representative workflows loaded.
- Logs were reviewed.

## Uninstall Acceptance Checklist

Before declaring uninstall complete:

- Installer completed in Uninstall mode.
- `CareQueueApi` service was removed.
- `CareQueueCaddy` service was removed.
- `C:\Program Files\CareQueue` was removed.
- `C:\ProgramData\CareQueue` was preserved.
- Runtime configuration was preserved.
- Active database was preserved.
- Encrypted backups were preserved.
- Installer log was reviewed.

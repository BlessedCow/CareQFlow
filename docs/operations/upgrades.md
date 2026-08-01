# Windows Upgrades

This guide covers upgrading an existing private Windows installation of CareQueue created with:

```text
deployment/windows/install-production.ps1
```

The production services are:

```text
CareQueueApi
CareQueueCaddy
```

The upgrade process replaces installed application code while preserving production configuration and runtime data.

For first-time installation, see [Windows Deployment](../deployment/windows.md).

For backup and recovery, see [Backup and Recovery](../workflows/backup-and-recovery.md).

For service validation and smoke tests, see [Health Checks](health-checks.md).

## What an Upgrade Replaces

A forced upgrade may replace application files under:

```text
C:\Program Files\CareQueue
```

This includes:

```text
backend/
frontend/
deployment/
```

The installed backend virtual environment is recreated:

```text
C:\Program Files\CareQueue\backend\.venv
```

Dependencies are then installed from the current repository requirements.

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

The service wrapper directory is preserved where required so existing WinSW service executables remain available.

## What an Upgrade Does Not Do

The current installer does not automatically:

- Prove that the latest backup is recoverable
- Require a fresh pre-upgrade backup
- Rotate encryption keys
- Migrate to another database engine
- Roll back source code after a failed smoke test
- Restore an older database schema
- Validate every browser workflow
- Update the separately installed Caddy executable
- Update the separately supplied WinSW executable

These responsibilities remain part of the deployment and recovery process.

## Required Access

Run the upgrade from:

```text
PowerShell as Administrator
```

The installer needs elevated rights to:

- Write under `C:\Program Files`
- Write and secure `C:\ProgramData\CareQueue`
- Stop and start Windows services
- Replace installed files
- Recreate the installed virtual environment
- Reapply filesystem permissions

## Pre-Upgrade Checklist

Before upgrading:

- Review the source being installed.
- Confirm the working tree contains only intended changes.
- Record the source commit.
- Run backend tests.
- Run Ruff.
- Run frontend tests.
- Run the frontend build.
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
python -m ruff check . --fix
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

The installer temporarily moves frontend `.env` files that could affect the production build, then restores them afterward.

Do not store production secrets in frontend environment files.

## Run the Upgrade

From the repository root in elevated PowerShell:

```powershell
.\deployment\windows\install-production.ps1 `
    -ApplicationOrigin "https://carequeue.local" `
    -PythonExecutable "C:\Python314\python.exe" `
    -Force
```

Use the approved origin and Python path for the installation.

Do not use `-SkipPermissionHardening` during a normal production upgrade.

## Why `-Force` Is Required

Without `-Force`, the installer refuses to replace an existing installation.

Use it only after confirming:

- The target installation is correct
- A recent backup exists
- The source is trusted
- The maintenance window is approved
- The preserved environment belongs to this installation

## Upgrade Sequence

The installer performs the upgrade in this order:

1. Validate the application origin.
2. Verify required source files.
3. Create a staging directory.
4. Build the frontend.
5. Copy backend and deployment files into staging.
6. Create required runtime directories.
7. Read or create the production environment.
8. Stop Caddy.
9. Stop the API.
10. Replace installed application files.
11. Recreate the installed Python environment.
12. Install backend dependencies.
13. Validate the installed backend.
14. Reapply runtime permissions.
15. Start the API.
16. Start Caddy.
17. Restore the original service-running states.

Building before stopping services reduces downtime.

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

## Service State Preservation

The installer records whether each service was running before the upgrade.

A service that was stopped before the upgrade remains stopped afterward.

Examples:

```text
Before: API running, Caddy running
After:  API running, Caddy running
```

```text
Before: API stopped, Caddy stopped
After:  API stopped, Caddy stopped
```

```text
Before: API running, Caddy stopped
After:  API running, Caddy stopped
```

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

## Successful Installer Output

Important successful lines include:

```text
Stopping CareQueue HTTPS service...
Stopping CareQueue API service...
Installing staged application files...
Creating the production Python environment...
Installing production backend dependencies...
Validating the installed backend...
CareQueue production backend validated.
Restricting runtime directory permissions...
Starting CareQueue API service...
Starting CareQueue HTTPS service...
CareQueue production files installed successfully.
The original API and Caddy service running states were restored.
```

Review the full installer result. Dependency installation output alone does not prove success.

## Post-Upgrade Validation

Run the post-upgrade procedure in [Health Checks](health-checks.md#post-upgrade-smoke-test).

At minimum, confirm:

- Both services are in the expected state
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
4. Run the production installer with `-Force`.
5. Run health checks.
6. Verify login and representative workflows.

Example:

```powershell
git checkout <approved-previous-commit>
```

Then:

```powershell
.\deployment\windows\install-production.ps1 `
    -ApplicationOrigin "https://carequeue.local" `
    -PythonExecutable "C:\Python314\python.exe" `
    -Force
```

## Database Rollback

Database rollback is a recovery operation.

Use:

```text
docs/workflows/backup-and-recovery.md
```

Do not manually overwrite the active database.

## Failed Upgrade Scenarios

### `_rust.pyd` access denied

Cause:

The API process still has a compiled dependency loaded from the installed virtual environment.

Check:

```powershell
Get-Service -Name "CareQueueApi", "CareQueueCaddy"
```

For older installer behavior, stop:

```powershell
Stop-Service -Name "CareQueueCaddy"
Stop-Service -Name "CareQueueApi"
```

Then rerun the installer.

### Frontend build fails

Because the build occurs before service shutdown, the installed application may still be untouched.

Run:

```powershell
npm test
npm run build
```

Review frontend environment files and correct the source problem.

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
- Whether the installer restored prior service state

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

Validate the installed Caddyfile:

```powershell
& "C:\Program Files (x86)\Caddy\caddy.exe" `
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
- Installer completed successfully.
- Installed backend validation passed.
- Permission hardening passed.
- Service states were restored correctly.
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

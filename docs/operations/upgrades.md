# Upgrades, Repair, and Uninstall

This guide covers upgrading, repairing, and uninstalling packaged CareQFlow installations on Windows and Linux.

CareQFlow separates installed application files from production configuration and runtime data so packaged upgrades and repairs can replace application components without intentionally replacing the active database, encryption keys, backups, or other persistent data.

For first-time installation, see:

```text
docs/deployment/windows.md
docs/deployment/linux.md
```

For backup and recovery procedures, see:

```text
docs/workflows/backup-and-recovery.md
```

For service validation and smoke tests, see:

```text
docs/operations/health-checks.md
```

## Supported Operations

The packaged deployment workflows support:

```text
Install
Upgrade
Repair
Rollback
Uninstall
```

### Install

Use Install when CareQFlow is not already installed.

A new installation creates the required application, configuration, data, service, and logging structure.

### Upgrade

Use Upgrade when replacing an existing installation with a newer reviewed CareQFlow release.

Upgrade preserves production configuration and runtime data while replacing application and packaged runtime components.

### Repair

Use Repair when the installed release is damaged, incomplete, or needs its packaged application files and service definitions restored.

Repair preserves production configuration and runtime data.

### Rollback

Use Rollback after a failed supported upgrade when CareQFlow has preserved the required pre-upgrade recovery assets.

Rollback restores the previous packaged application, stages and activates the verified pre-upgrade encrypted database backup, restores the previous installed version metadata, restores the packaged service definitions, validates required services and application health, and retains recovery evidence for review.

Rollback is a recovery operation and should be performed only by an administrator who understands the failed upgrade state and has reviewed the preserved recovery record.

### Uninstall

Use Uninstall to remove the installed CareQFlow application and its operating-system services while intentionally preserving production configuration, data, and logs.

A normal uninstall is not secure data destruction.

## Application Version and Governance Revision

CareQFlow tracks three separate version values:

```text
CareQFlow application version: 0.3.0
Governance attestation version: 1
Governance document revision: governance-attestation-v1
```

The CareQFlow application version identifies the installed software release.

The governance attestation version identifies the required governance acceptance generation.

The governance document revision identifies the exact revision of the governance text that was accepted.

A governance attestation is current only when both its attestation version and document revision match the values required by the installed application.

Installing a new CareQFlow application version does not by itself require a new governance attestation. Re-attestation is required when the required governance attestation version changes, when the required governance document revision changes, or when no current attestation exists for the installation.

Historical attestations created before document-revision tracking was introduced may not contain a document revision. These records are preserved as historical evidence but do not satisfy a current requirement that includes a document revision.

After an upgrade, verify that the expected governance status, required attestation version, and required document revision are shown before returning the installation to normal use.

## General Upgrade Safety

Before upgrading any CareQFlow installation:

- Identify the exact release artifact being installed.
- Record the current application version and source release information when available.
- Confirm the current installation is healthy before changing it.
- Create or confirm a recent encrypted backup.
- Verify the selected backup for higher-risk upgrades.
- Confirm required encryption and recovery keys are available.
- Review release notes for configuration, migration, or security changes.
- Schedule an appropriate maintenance window.
- Keep the previously trusted release artifact and recovery documentation available.
- Ensure that only approved administrators can access the host during the upgrade.
- Do not begin an upgrade while the database, services, or storage state is uncertain.

An application upgrade is not a substitute for backup, restore, migration, or disaster-recovery planning.

## Database Migration Safety

CareQFlow uses ordered, versioned database migrations for schema changes that must be applied to an existing installation.

Applied migrations are recorded in the database table:

```text
schema_migrations
```

Each migration has a unique migration identifier and an application timestamp. Registered migrations are applied in migration-ID order, and migrations already recorded in the ledger are skipped on later startups. This makes normal startup and repair operations idempotent with respect to previously completed migrations.

Current migration identifiers include:

```text
0001_security_walkthrough_columns
0002_security_authentication_and_session_columns
0003_authorization_core_columns
0004_authorization_denial_follow_up_columns
0005_governance_append_only_history
0006_audit_event_columns
0007_governance_document_revision
```

Each individual migration runs inside a database savepoint. If a migration step raises an error, CareQFlow rolls that step back to its savepoint, does not record that migration as applied, and raises a migration error instead of continuing silently.

Database initialization commits only after schema initialization and registered migrations complete successfully. If initialization raises an exception, the normal initialization path does not commit the failed startup attempt.

Operators should not manually insert, delete, or alter rows in `schema_migrations` to bypass a failed upgrade. The migration ledger is part of the database's upgrade state.

Before an upgrade that includes database migrations:

- Create or confirm a recent encrypted backup.
- Prefer a verified backup for higher-risk changes.
- Preserve the required database and backup encryption keys.
- Confirm sufficient free disk space for the application, database, logs, and recovery files.
- Confirm the current installation is healthy before beginning the upgrade.
- Review release notes for schema or migration changes.

After the upgrade:

- Confirm CareQFlow starts normally.
- Confirm readiness and health checks pass.
- Confirm expected application workflows operate correctly.
- Confirm governance status is correct.
- Confirm backup and recovery functions remain available.

A successful migration is not a downgrade guarantee. Reverting application files to an older release does not automatically make a database that has been migrated by a newer release compatible with that older application. Treat application rollback and database recovery as separate operations and use a verified pre-upgrade backup when recovery to an older database state is required.

## Release Validation Before Deployment

Before a release artifact is used for an upgrade, the source revision and release build should already have passed the project's release validation.

Typical source checks include:

```powershell
pytest backend\tests -n auto -q
ruff check backend\authstatus_api backend\tests --fix
npm --prefix frontend test
npm --prefix frontend run build
```

Additional release security checks may include:

```powershell
bandit -r backend\authstatus_api backend\scripts -c backend\pyproject.toml
python -m pip_audit -r backend\requirements.txt
npm --prefix frontend audit
```

Review the repository state before building release artifacts:

```powershell
git status --short
git rev-parse HEAD
git log -1 --oneline
```

Do not package or deploy:

- Real patient data
- Production databases
- Production environment files
- Encryption keys
- Backup files
- Restored databases
- Real PDFs containing PHI
- Unreviewed generated files
- Sensitive screenshots

## Release Version Preparation

Use the repository release-version helper to update controlled application and installer version declarations:

```powershell
.\deployment\bump-version.ps1 -Version 0.3.0
```

Replace `0.3.0` with the intended release version.

The version helper intentionally does not rewrite arbitrary matching version strings in tests, dependency versions, documentation examples, or historical governance fixtures.

Review the resulting changes:

```powershell
git status --short
git diff
```

## Windows Upgrade Workflow

The packaged Windows installer is the normal Windows upgrade path.

A versioned release has a filename such as:

```text
CareQueue-Setup-0.3.0.exe
```

The lower-level installer engine is:

```text
deployment/windows/installer/invoke-install.ps1
```

Direct engine invocation is intended for development, validation, and troubleshooting rather than normal operator use.

### Windows Production Services

The packaged Windows services are:

```text
CareQueueApi
CareQueueCaddy
```

The API remains bound to loopback and Caddy provides the private HTTPS application endpoint.

### Windows Persistent Data

Installed application files are stored under:

```text
C:\Program Files\CareQueue
```

Persistent production data is stored under:

```text
C:\ProgramData\CareQueue
```

The production environment file is:

```text
C:\ProgramData\CareQueue\Config\carequeue.env
```

An upgrade or repair preserves the existing environment file and runtime data.

This includes settings and keys such as:

```text
AUTHSTATUS_ENCRYPTION_KEY
AUTHSTATUS_SQLCIPHER_KEY
AUTHSTATUS_BACKUP_ENCRYPTION_KEY
```

Persistent data can include:

- Active database
- Encrypted backups
- Restore staging
- Recovery staging
- Logs
- Caddy runtime data
- Local certificate data

### What a Windows Upgrade Replaces

A Windows upgrade may replace application files under:

```text
C:\Program Files\CareQueue
```

including:

```text
backend/
frontend/
deployment/
runtime/
vendor/
```

The packaged installer recreates the installed backend environment from the packaged private Python runtime and bundled dependency wheelhouse.

### What Windows Repair Replaces

Repair may restore:

- Installed backend files
- Installed frontend files
- Deployment scripts
- Private Python runtime files
- Packaged vendor binaries
- Windows service definitions
- Runtime directory structure
- Filesystem permissions

Repair does not intentionally reset:

- Admin users
- Production encryption keys
- Active database data
- Encrypted backups
- Governance attestation history

### Windows Pre-Upgrade Health Check

Before starting the installer, confirm:

```powershell
Get-Service CareQueueApi, CareQueueCaddy |
    Select-Object Name, Status, StartType
```

Both services should normally be running.

Check liveness:

```powershell
Invoke-RestMethod `
    -Method Get `
    -Uri "https://careqflow.local/api/health/live" `
    -TimeoutSec 5
```

Check readiness:

```powershell
Invoke-RestMethod `
    -Method Get `
    -Uri "https://careqflow.local/api/health/ready" `
    -TimeoutSec 5
```

Also verify normal browser login and a basic authorization workflow before changing the installation.

Do not use an upgrade to hide an existing production failure.

### Create a Windows Pre-Upgrade Backup

Run the installed backup helper:

```powershell
& "C:\Program Files\CareQueue\deployment\windows\run-backup.ps1"
```

Review the newest backups:

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

A file listing confirms only that a backup file exists. It does not prove recoverability.

For higher-risk upgrades, verify the selected encrypted backup through the supported backup verification workflow before proceeding.

### Build the Windows Release

Build the production frontend first:

```powershell
npm --prefix frontend run build
```

Build the Windows payload:

```powershell
.\deployment\windows\installer\build-payload.ps1 `
    -EmbeddedPythonArchive ".\local_installer_assets\python-3.14.6-embed-amd64.zip"
```

Compile the Inno Setup installer:

```powershell
& "C:\Program Files\Inno Setup 7\ISCC.exe" `
    ".\deployment\windows\installer\CareQueue.iss"
```

For CareQueue `0.3.0`, the resulting artifact is:

```text
build\windows\installer\CareQueue-Setup-0.3.0.exe
```

Validate the release package:

```powershell
.\deployment\windows\installer\validate-release-package.ps1
```

### Run the Windows Upgrade

Launch the versioned installer:

```powershell
.\build\windows\installer\CareQueue-Setup-0.3.0.exe
```

When an existing installation is detected, select:

```text
Upgrade existing installation
```

Review the installer summary before continuing.

### Run Windows Repair

Launch the same versioned installer and select:

```text
Repair existing installation
```

Repair should preserve production configuration and runtime data while restoring packaged application and service components.

### Run Windows Uninstall

Launch the installer and select:

```text
Uninstall CareQFlow
```

The uninstall workflow removes the installed application and CareQFlow Windows services while preserving persistent runtime data.

After uninstall, verify:

```powershell
Get-Service CareQueueApi, CareQueueCaddy -ErrorAction SilentlyContinue

Test-Path "C:\Program Files\CareQueue"
Test-Path "C:\ProgramData\CareQueue"
Test-Path "C:\ProgramData\CareQueue\Config\carequeue.env"
Test-Path "C:\ProgramData\CareQueue\Data\auth_tracker.sqlcipher.db"
```

For a normal populated installation, the expected pattern is:

```text
No CareQFlow service output
False
True
True
True
```

The final database-path result depends on whether that installation already contains an active database.

### Windows Installer Sequence

The Windows installer performs the upgrade in a controlled sequence that includes:

1. Validate installer state and application origin.
2. Validate required packaged payload files.
3. Verify the packaged payload hash manifest.
4. Prepare required runtime directories and logging.
5. Preserve or migrate the production environment configuration.
6. Stop the HTTPS proxy.
7. Stop the API service.
8. Replace installed application and packaged runtime files.
9. Recreate the installed backend environment.
10. Install backend dependencies from the packaged wheelhouse.
11. Validate the installed backend.
12. Reinstall or refresh service configuration.
13. Reapply runtime permission hardening.
14. Start the API.
15. Start Caddy.
16. Validate the installed services and application health.

The exact implementation may evolve, so release validation should always use the installer included with the release being tested.

### Windows Service Order

The normal stop order is:

```text
1. CareQueueCaddy
2. CareQueueApi
```

The normal start order is:

```text
1. CareQueueApi
2. CareQueueCaddy
```

This keeps the reverse proxy from serving requests while the API is unavailable during planned replacement work.

### Windows Installer Logs

Installer logs are stored under:

```text
C:\ProgramData\CareQueue\Logs\Installer
```

Find the newest log:

```powershell
$latestLog = Get-ChildItem `
    -Path "$env:ProgramData\CareQueue\Logs\Installer" `
    -Filter "CareQueue-*.log" `
    -ErrorAction SilentlyContinue |
Sort-Object LastWriteTime -Descending |
Select-Object -First 1

$latestLog.FullName
```

Read the newest log:

```powershell
Get-Content `
    -LiteralPath $latestLog.FullName `
    -Tail 240
```

Review logs before sharing them because deployment logs can reveal environment and host information.

## Linux Upgrade Workflow

CareQFlow includes a packaged Linux release workflow for supported Debian-based systems.

The release archive has a filename such as:

```text
CareQueue-Linux-Setup-0.3.0.tar.gz
```

The packaged entry point is:

```text
deployment/linux/installer/invoke-install.sh
```

Supported Linux modes are:

```text
install
upgrade
repair
rollback
uninstall
```

### Linux Production Services

The packaged Linux services are:

```text
carequeue-api.service
carequeue-caddy.service
carequeue-backup.service
carequeue-backup.timer
```

### Linux Persistent Paths

Installed application files:

```text
/opt/carequeue
```

Production configuration:

```text
/etc/carequeue
```

Runtime data:

```text
/var/lib/carequeue
```

Logs:

```text
/var/log/carequeue
```

Upgrade and repair replace application/runtime files under `/opt/carequeue` while preserving production configuration and runtime data.

### What a Linux Upgrade Replaces

The Linux installer refreshes:

- Backend application files
- Frontend production build
- Deployment files
- Python virtual environment
- Backend dependencies
- systemd unit files
- Caddy configuration
- Installed application metadata

Existing production configuration is preserved and required deployment settings may be migrated.

### What Linux Repair Replaces

Repair uses the same production installation engine to restore the packaged application state while preserving:

- `/etc/carequeue`
- `/var/lib/carequeue`
- `/var/log/carequeue`

Repair is appropriate when application files, Python dependencies, service definitions, or other packaged installation components need to be restored.

### Linux Pre-Upgrade Health Check

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

Check liveness:

```bash
curl --fail --silent --show-error \
  https://careqflow.local/api/health/live
```

Check readiness:

```bash
curl --fail --silent --show-error \
  https://careqflow.local/api/health/ready
```

Also verify normal browser login and a basic authorization workflow.

Do not proceed until unexplained service or readiness failures have been resolved.

### Create or Verify a Linux Pre-Upgrade Backup

Confirm that the scheduled backup timer is active:

```bash
sudo systemctl is-enabled carequeue-backup.timer
sudo systemctl is-active carequeue-backup.timer
```

Review the most recent encrypted backup files in the configured CareQFlow backup directory.

Use the supported backup verification workflow for higher-risk upgrades.

Do not assume that the presence of a backup file proves it can be restored.

### Build the Linux Release

Build the production frontend:

```powershell
npm --prefix frontend run build
```

Build the Linux release archive:

```powershell
.\deployment\linux\installer\build-payload.ps1 -Version 0.3.0
```

After the repository version has already been bumped, the default version can be used:

```powershell
.\deployment\linux\installer\build-payload.ps1
```

For CareQueue `0.3.0`, the resulting artifact is:

```text
build\linux\installer\CareQueue-Linux-Setup-0.3.0.tar.gz
```

The build script reports the package path, size, and SHA256 value.

### Extract the Linux Release

On the target Linux system:

```bash
mkdir carequeue-installer
tar -xzf CareQueue-Linux-Setup-0.3.0.tar.gz \
  -C carequeue-installer
cd carequeue-installer
```

Use a newly extracted, reviewed release package for upgrade and repair operations.

### Run the Linux Upgrade

From the extracted release package:

```bash
sudo bash deployment/linux/installer/invoke-install.sh upgrade
```

Upgrade preserves the existing production configuration and data.

### Run Linux Repair

From the extracted release package:

```bash
sudo bash deployment/linux/installer/invoke-install.sh repair
```

Repair also preserves production configuration and data.

### Run Linux Rollback

Linux upgrade rollback is available after a failed upgrade that created a valid CareQFlow upgrade recovery record and preserved the required database and application recovery assets.

From the extracted release package associated with the failed upgrade:

```bash
sudo bash deployment/linux/installer/invoke-install.sh rollback
```

The rollback workflow:

- Selects the newest failed upgrade recovery record.
- Verifies the preserved pre-upgrade application archive and SHA256 checksum.
- Extracts and validates the previous application in an isolated staging directory.
- Preserves the failed incoming application and records its archive metadata.
- Stops CareQFlow services before application replacement.
- Restores the previous backend, frontend, and deployment payload.
- Recreates and validates the previous Python environment.
- Restores the previous packaged systemd service definitions.
- Stages the verified pre-upgrade encrypted database backup.
- Requires administrator confirmation before activating staged database recovery.
- Restores the previous installed application version metadata.
- Restarts the API and HTTPS services.
- Restores the scheduled backup timer.
- Verifies required service state, application health, and readiness.
- Marks the recovery record as completed only after successful validation.
- Removes temporary application staging while retaining durable recovery assets.

Database recovery activation requires the administrator to enter the confirmation phrase displayed by the recovery tool. Do not automate or bypass that confirmation.

If application replacement fails during rollback, CareQFlow attempts to restore the failed incoming application files and leaves services stopped for administrator review.

A successful rollback retains the encrypted recovery backup, previous application archive, failed incoming application archive, checksums, recovery record, and installer logs.

### Run Linux Uninstall

From the extracted release package:

```bash
sudo bash deployment/linux/installer/invoke-install.sh uninstall
```

The uninstall workflow:

- Stops and disables the CareQFlow backup timer.
- Stops and disables the CareQFlow Caddy service.
- Stops and disables the CareQFlow API service.
- Removes CareQFlow systemd unit files.
- Removes `/opt/carequeue`.
- Removes the CareQFlow-managed local hosts-file entry.
- Preserves configuration, runtime data, and logs.

The following paths are intentionally preserved:

```text
/etc/carequeue
/var/lib/carequeue
/var/log/carequeue
```

A normal uninstall does not delete the database or encryption keys.

### Linux Upgrade Sequence

The Linux production installer performs the installation or refresh in this general order:

1. Require root privileges.
2. Validate the HTTPS application origin.
3. Validate the Linux distribution.
4. Validate required release-package contents.
5. Install required system dependencies.
6. Ensure the dedicated CareQFlow service account exists.
7. Create or validate production directories.
8. Replace installed application files under `/opt/carequeue`.
9. Recreate the CareQFlow Python virtual environment.
10. Install backend dependencies.
11. Validate the backend import.
12. Preserve or create the production environment file.
13. Write installation state.
14. Install or refresh systemd units.
15. Install Caddy when required.
16. Disable the distribution's default Caddy service where necessary.
17. Install and validate the CareQFlow Caddy configuration.
18. Ensure the packaged local hostname configuration exists.
19. Start or restart CareQFlow services.
20. Ensure the Caddy internal root certificate is trusted.
21. Validate the API service, Caddy service, and backup timer.
22. Validate the HTTPS frontend, liveness endpoint, and readiness endpoint.

Upgrade and repair use the same production installation engine and therefore refresh the packaged application state while preserving existing production configuration and data.

### Linux Installer Logs

Installer logs are stored under:

```text
/var/log/carequeue/installer/
```

Review the relevant log after upgrade, repair, or uninstall.

API logs:

```bash
sudo journalctl \
  -u carequeue-api.service \
  --since today
```

Caddy logs:

```bash
sudo journalctl \
  -u carequeue-caddy.service \
  --since today
```

Backup logs:

```bash
sudo journalctl \
  -u carequeue-backup.service \
  --since today
```

## Post-Upgrade Validation

After any upgrade or repair, validate the installation before returning it to routine use.

### Service Health

Confirm that required services are running.

Windows:

```powershell
Get-Service CareQueueApi, CareQueueCaddy |
    Select-Object Name, Status, StartType
```

Linux:

```bash
sudo systemctl is-active carequeue-api.service
sudo systemctl is-active carequeue-caddy.service
sudo systemctl is-enabled carequeue-backup.timer
```

### HTTPS Application Health

Confirm:

```text
https://careqflow.local/
https://careqflow.local/api/health/live
https://careqflow.local/api/health/ready
```

The packaged installer performs automated health checks, but operator validation should still include the browser workflow.

### Browser Smoke Test

At minimum:

1. Open CareQFlow through the approved HTTPS origin.
2. Sign in with an approved test or administrative account.
3. Confirm any required governance attestation state is correct.
4. Confirm the authorization queue loads.
5. Open an existing authorization.
6. Confirm expected role restrictions.
7. Confirm logout works.
8. Sign in again.
9. Confirm the Admin System page reports the expected application version.
10. Confirm backup scheduling remains enabled.

Use only synthetic or approved non-production data during release validation environments.

### Security-Sensitive Checks

For releases that modify authentication, session, governance, encryption, or deployment behavior, perform targeted checks appropriate to the change.

Examples include:

- MFA enrollment and login
- Remembered-device behavior
- Single-session invalidation
- Inactivity timeout warning and expiration
- Session renewal
- Cross-tab logout behavior
- Governance enforcement and history
- Audit integrity verification
- Backup creation and verification
- Certificate trust
- Production same-origin API behavior

## Failure Handling

If an upgrade or repair fails:

1. Preserve the installer log and relevant service logs.
2. Do not delete the production database or encryption keys.
3. Confirm the current state of the installed services.
4. Confirm whether the application files were partially replaced.
5. Confirm the production environment file is still present.
6. Confirm the most recent verified encrypted backup is available.
7. Avoid repeated repair attempts until the failure is understood.
8. Use the documented recovery workflow when database recovery is required.

Do not edit encrypted database or backup files manually.

## Rollback

CareQFlow currently provides an assisted rollback workflow for supported packaged Linux upgrades.

A Linux upgrade preserves recovery information before replacing the installed application. When version metadata is available, this includes:

- A verified encrypted pre-upgrade database backup.
- A preserved archive of the previous application.
- A SHA256 checksum for the previous application archive.
- Previous and incoming application versions.
- Installer log location.
- Upgrade recovery status.

If the upgrade fails, the recovery record is marked as failed and can be used by the Linux rollback mode.

During rollback, CareQFlow also preserves the failed incoming application before restoring the previous release. This allows the failed application state to remain available for troubleshooting after recovery.

The recovery lifecycle may include:

```text
failed
rollback_staged
rollback_activated
rollback_completed
```

If application replacement fails and the failed incoming application is restored successfully, the record may instead enter:

```text
rollback_application_restored
```

In that state, CareQFlow services remain stopped pending administrator review.

A rollback is marked complete only after:

- The previous application has been restored and validated.
- The pre-upgrade database has been activated successfully.
- The previous installed version metadata has been restored.
- The CareQFlow API service is active.
- The CareQFlow HTTPS service is active.
- The scheduled backup timer is active.
- Application health and readiness checks pass.

Temporary rollback application staging is removed after successful completion. Durable recovery evidence is retained.

The current assisted rollback workflow is Linux-specific. Windows packaged rollback behavior is documented separately when supported.

Rollback should not be treated as a substitute for normal backup and recovery planning. Preserve encryption keys and recovery assets independently of the application installation.

## What the Installers Do Not Prove

A successful installer result does not prove that:

- The newest backup is recoverable.
- Every browser workflow works.
- Every role-specific workflow works.
- External network policy is correct.
- Endpoint protection is healthy.
- Organizational access reviews are current.
- Required agreements have been executed.
- The deployment is HIPAA compliant.
- The release is appropriate for public internet exposure.
- Disaster recovery has been tested.

Those remain part of release validation and organizational operations.

## Permission Review

After upgrade or repair, confirm that persistent production directories still have the intended restricted permissions.

Windows deployments should review access under:

```text
C:\ProgramData\CareQueue
```

Linux deployments should review ownership and modes under:

```text
/etc/carequeue
/var/lib/carequeue
/var/log/carequeue
```

Do not broaden permissions simply to bypass an unrelated installation or service failure.

## Common Problems

### Upgrade is unavailable

Confirm CareQFlow is already installed.

Windows detects the installed backend, frontend, private Python runtime, and Caddy files under the installation directory.

Linux upgrade should be run against an existing packaged installation using a newly extracted release package.

### Install is rejected because CareQFlow already exists

Use Upgrade or Repair rather than Install.

### Application does not start after upgrade

Review:

- Installer logs
- API service logs
- Caddy service logs
- Production environment-file presence
- Database path
- Encryption-key availability
- Service-account permissions
- Backend dependency installation
- Health and readiness results

### Readiness fails after upgrade

Readiness can fail even when the process is running.

Review:

- Database accessibility
- SQLCipher configuration
- Production path validation
- Encryption configuration
- Service logs
- Application environment
- Installed application version

Do not treat liveness alone as proof that the application is ready.

### Login succeeds but protected pages require governance setup

The current organization governance attestation has not been completed.

An Admin must complete the current attestation before normal protected application functionality becomes available.

A CareQFlow application-version change does not automatically require re-attestation. Re-attestation is required when the required governance attestation version changes, when the required governance document revision changes, or when no current attestation exists.

### Certificate warning appears after upgrade

Confirm that the packaged Caddy service is running and the CareQFlow internal root certificate is trusted on the approved client system.

Do not permanently disable TLS certificate validation to work around a trust problem.

### Backup timer is missing after Linux upgrade

Check:

```bash
sudo systemctl status carequeue-backup.timer
sudo systemctl list-timers carequeue-backup.timer
```

Review the installer log and reinstall or repair only after the cause is understood.

### Windows services are missing after repair

Check:

```powershell
Get-Service CareQueueApi, CareQueueCaddy -ErrorAction SilentlyContinue
```

Review the newest installer log before retrying the operation.

## Recommended Change Record

For production upgrades, retain an organizational change record containing at least:

```text
Date and time
Operator
Previous CareQFlow version
New CareQFlow version
Release artifact filename
Release artifact SHA256
Source commit or tag
Pre-upgrade health result
Backup filename
Backup verification result
Upgrade or repair result
Post-upgrade health result
Browser smoke-test result
Governance status
Unexpected findings
Recovery or rollback actions, if any
```

Do not include passwords, MFA secrets, encryption keys, session tokens, PHI, or other sensitive values in the change record.

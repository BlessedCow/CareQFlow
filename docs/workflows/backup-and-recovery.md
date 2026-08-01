# Backup and Recovery

CareQueue creates encrypted database backups and uses a staged recovery process designed to protect the active database.

The central rule is:

> Never replace the active database until the selected backup has been decrypted, validated, staged, and reviewed.

Backup creation, restore staging, recovery staging, and recovery activation are separate operations.

## Protection Layers

CareQueue uses separate keys:

```env
AUTHSTATUS_ENCRYPTION_KEY=
AUTHSTATUS_SQLCIPHER_KEY=
AUTHSTATUS_BACKUP_ENCRYPTION_KEY=
```

Purpose:

- `AUTHSTATUS_ENCRYPTION_KEY` protects selected sensitive field values
- `AUTHSTATUS_SQLCIPHER_KEY` opens the encrypted database file
- `AUTHSTATUS_BACKUP_ENCRYPTION_KEY` encrypts and decrypts `.db.enc` backups

Generate and store them independently.

A backup may decrypt successfully and still be unusable when the SQLCipher or field-level encryption key is wrong.

## Key Custody

Keep recoverable copies of all required keys in an approved secret-management process.

Do not store keys:

- In source control
- Beside backups
- In screenshots
- In scheduled-task arguments
- In service XML
- In ordinary email or chat
- Only on the database host

Document ownership, approved retrieval, rotation, and recovery testing.

## Standard Paths

### Windows production

```text
Database:
C:\ProgramData\CareQueue\Data

Backups:
C:\ProgramData\CareQueue\Backups

Restores:
C:\ProgramData\CareQueue\Restores

Recovery:
C:\ProgramData\CareQueue\Recovery

Environment:
C:\ProgramData\CareQueue\Config\carequeue.env
```

### Development

```text
backend/data/
backend/backups/
backend/restores/
```

These local directories must remain uncommitted.

## Backup Format

Encrypted backups end with:

```text
.db.enc
```

CareQueue creates a consistent database snapshot, encrypts it, writes the output atomically, and verifies the result.

It does not simply copy the live database file while it may be changing.

## Create a Development Backup

From the repository root:

```powershell
backend\.venv\Scripts\python.exe `
    backend\scripts\create_encrypted_backup.py
```

A successful result includes:

```text
Created and verified encrypted backup: <path>
```

Retention is applied after successful creation.

## Create a Windows Production Backup

Use the installed runner:

```powershell
& "C:\Program Files\CareQueue\deployment\windows\run-backup.ps1"
```

Default destination:

```text
C:\ProgramData\CareQueue\Backups
```

The runner loads the protected production environment and returns a nonzero exit code when creation or retention fails.

## Custom Backup Directory

Development:

```powershell
backend\.venv\Scripts\python.exe `
    backend\scripts\create_encrypted_backup.py `
    --backup-directory "G:\CareQueue\local_backups"
```

Windows production:

```powershell
& "C:\Program Files\CareQueue\deployment\windows\run-backup.ps1" `
    -BackupDirectory "D:\CareQueueBackups"
```

External storage may require:

```env
AUTHSTATUS_ALLOW_UNSAFE_STORAGE_PATHS=true
```

That setting permits the path. It does not secure it.

The destination still requires appropriate permissions, volume protection, retention, and off-host policy.

## Inspect Recent Backups

Production example:

```powershell
Get-ChildItem `
    "C:\ProgramData\CareQueue\Backups" `
    -Filter "*.db.enc" |
Sort-Object LastWriteTime -Descending |
Select-Object -First 10 `
    Name,
    Length,
    LastWriteTime
```

Confirm:

- A recent file exists
- File size is greater than zero
- Timestamp matches the expected run
- Correct directory is being inspected

A file listing does not prove recoverability.

## Verification

Backup verification confirms that CareQueue can:

1. Read the encrypted file.
2. Decrypt it with the backup key.
3. Open the decrypted database in the configured mode.
4. Run an integrity check.
5. Confirm required CareQueue tables exist.

Verification is stronger than checking for a file, but it is not a full recovery drill.

## Admin Backup Interface

Admin-only backup operations are available under:

```text
/api/admin/system/backups
```

Current workflow supports:

- Listing backups
- Creating a restore point
- Verifying a restore point
- Viewing pending recovery status
- Staging a backup
- Canceling staged recovery

Backup and recovery events are recorded in the Audit Log.

## Retention

Retention settings:

```env
AUTHSTATUS_BACKUP_RETENTION_DAYS=
AUTHSTATUS_BACKUP_MINIMUM_COUNT=
```

Default Windows values are equivalent to:

```text
Retention period: 90 days
Minimum retained backups: 5
```

Rules:

- Old backups may become eligible for deletion
- The minimum count remains protected
- A backup tied to pending recovery remains protected

A pruning failure does not necessarily mean the newly created backup is invalid.

## Windows Scheduled Backups

Deployment scripts:

```text
deployment/windows/install-backup-task.ps1
deployment/windows/remove-backup-task.ps1
deployment/windows/run-backup.ps1
```

Default task:

```text
Name: CareQueue Encrypted Backup
Schedule: Daily at 02:00
Account: SYSTEM
```

Install:

```powershell
& "C:\Program Files\CareQueue\deployment\windows\install-backup-task.ps1"
```

Custom time:

```powershell
& "C:\Program Files\CareQueue\deployment\windows\install-backup-task.ps1" `
    -RunAt "03:30"
```

Validate:

```powershell
Get-ScheduledTask `
    -TaskName "CareQueue Encrypted Backup"

Start-ScheduledTask `
    -TaskName "CareQueue Encrypted Backup"

Get-ScheduledTaskInfo `
    -TaskName "CareQueue Encrypted Backup"
```

Then confirm a new nonempty backup exists.

Remove the task:

```powershell
& "C:\Program Files\CareQueue\deployment\windows\remove-backup-task.ps1"
```

Removing the task does not delete existing backups.

## Linux Scheduled Backups

Systemd files:

```text
deployment/linux/systemd/carequeue-backup.service
deployment/linux/systemd/carequeue-backup.timer
```

Expected paths:

```text
Install: /opt/carequeue
Environment: /etc/carequeue/carequeue.env
Backups: /var/lib/carequeue/backups
```

Validate:

```bash
systemd-analyze verify \
  deployment/linux/systemd/carequeue-backup.service \
  deployment/linux/systemd/carequeue-backup.timer
```

Install and test the service before enabling the timer.

```bash
sudo systemctl start carequeue-backup.service
sudo systemctl status carequeue-backup.service
sudo journalctl -u carequeue-backup.service --since today
```

Enable the timer only after a successful manual run:

```bash
sudo systemctl enable --now carequeue-backup.timer
```

## Restore to a Safe File

Restoring does not activate a backup.

Development example:

```powershell
backend\.venv\Scripts\python.exe `
    backend\scripts\restore_encrypted_backup.py `
    "G:\CareQueue\backend\backups\<backup-file>.db.enc"
```

Successful output includes:

```text
Restored backup to: <path>
This did not overwrite the active database.
```

Restored files normally end with:

```text
.restored.db
```

## Restore Validation

Restore processing:

1. Resolves the backup through approved storage.
2. Rejects unsafe paths.
3. Decrypts into a temporary file.
4. Opens the database in the configured mode.
5. Runs an integrity check.
6. Confirms required tables.
7. Moves the validated file into the restore directory.
8. Cleans temporary files after failure.

A restored file is still not active.

## Stage a Recovery

Staging prepares a verified backup for later activation.

It creates:

- A validated staged database
- A pending-recovery manifest
- Metadata identifying the source backup and staged filename

Only one pending recovery should exist at a time.

Staging does not stop services or replace the active database.

## Cancel a Staged Recovery

Canceling removes the pending state and records an audit event.

It does not delete the original encrypted backup.

Cancel when:

- Wrong backup was selected
- A newer restore point is needed
- Review raised concerns
- Recovery was postponed
- A drill is complete

## Activation Requirements

Recovery activation is offline and interactive.

Before activation:

- API service is stopped
- API port is free
- Database is not locked
- Staged and active databases are on the same filesystem
- No SQLite sidecar files remain
- A verified encrypted safety backup is created
- Exact confirmation phrase is entered

Confirmation phrase:

```text
ACTIVATE RECOVERY
```

The application remains stopped after activation for review.

## Activate on Windows

Stop services:

```powershell
Stop-Service -Name "CareQueueCaddy"
Stop-Service -Name "CareQueueApi"
```

Load the production environment into the current PowerShell process, then run:

```powershell
Set-Location "C:\Program Files\CareQueue\backend"

& ".\.venv\Scripts\python.exe" `
    ".\scripts\activate_staged_recovery.py" `
    --service-name "CareQueueApi" `
    --api-host "127.0.0.1" `
    --api-port 8000
```

Review the printed plan:

- Active database path
- Staged database path
- Rollback path
- Safety backup path
- Managed service
- API socket
- Detected sidecars

Then enter:

```text
ACTIVATE RECOVERY
```

exactly.

## Recovery Preflight

Before cutover, the script:

1. Resolves active, staged, and rollback paths.
2. Confirms the service is stopped.
3. Confirms the API socket is free.
4. Requests exclusive database access.
5. Detects sidecar files.
6. Creates and verifies a safety backup.
7. Confirms files are on the same filesystem.
8. Prints the activation plan.
9. Waits for confirmation.

No active database file is replaced during preflight.

## Atomic Cutover

After confirmation:

1. Service and socket checks run again.
2. Exclusive access is rechecked.
3. Sidecar files cause refusal.
4. Active database moves to rollback path.
5. Staged database moves to active path.
6. New active database is validated.
7. Pending manifest is removed after success.

## Failed Final Validation

When final validation fails, the script attempts to:

1. Move the failed activated database back to staging.
2. Restore the rollback database.
3. Preserve the encrypted safety backup.

Keep CareQueue stopped until the final state is understood.

## Post-Activation Validation

Before restarting:

- Confirm active database exists
- Confirm rollback database exists
- Confirm safety backup exists
- Confirm pending manifest is gone
- Confirm no unexpected sidecars exist
- Review activation output

Start the API:

```powershell
Start-Service -Name "CareQueueApi"
```

Check direct readiness:

```powershell
Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/api/health/ready"
```

Start Caddy:

```powershell
Start-Service -Name "CareQueueCaddy"
```

Check HTTPS readiness:

```powershell
Invoke-RestMethod `
    -Uri "https://carequeue.local/api/health/ready"
```

Then verify:

- Login
- Representative authorization records
- Timeline events
- Registered options
- Audit continuity
- Dashboard summaries

See [Health Checks](../operations/health-checks.md#post-recovery-smoke-test).

## Rollback and Safety Backup

The previous active database remains as a rollback database.

Recovery activation also creates a fresh encrypted safety backup before cutover.

Keep both until:

- Services start successfully
- Readiness passes
- Login succeeds
- Critical records are verified
- Recovery is accepted
- Retention requirements permit removal

## Sidecar Files

Common sidecars:

```text
-wal
-shm
-journal
```

Their presence may indicate the database is in use or did not shut down cleanly.

Do not delete them blindly.

Confirm all services and maintenance processes are stopped, then retry preflight.

## Recovery Drills

A backup is not fully proven until restored and validated.

A drill should include:

1. Select a recent backup.
2. Confirm all required keys are available.
3. Restore to an isolated directory.
4. Verify integrity and required tables.
5. Confirm SQLCipher protection.
6. Start an isolated test instance.
7. Verify login and representative records.
8. Record elapsed time and issues.
9. Remove drill data securely.

Do not wait for an emergency to perform the first drill.

## Off-Host Backups

Local backups do not protect against:

- Device theft
- Disk failure
- Ransomware
- Fire
- Whole-machine administrative error
- Loss of both data and keys

Use an approved off-host process when required.

CareQueue does not currently upload backups externally by itself.

## Monitoring

Monitor:

- Last successful backup
- File size
- Scheduled-task result
- Retention failures
- Available storage
- Last restore test
- Last key-recovery test

## Common Failures

### Backup key missing or wrong

A new key cannot decrypt old backups.

Restore the correct key from approved custody.

### SQLCipher key wrong

The backup may decrypt but database validation will fail.

Confirm the key belongs to that database.

### Field-level key wrong

The database may open while selected values fail to decrypt.

Do not accept the recovery until representative encrypted fields are verified.

### Backup corrupted or truncated

Do not stage it.

Select another verified backup and investigate storage integrity.

### Backup directory full

Free space through approved retention or archival procedures.

Do not delete the only recent verified backup.

### Scheduled task fails

Run the installed backup runner manually and check permissions, environment loading, script paths, and task history.

### Unsafe restore path

Use configured backup and restore directories.

Do not bypass path validation merely to make the command succeed.

### Service or port still active during recovery

Stop Caddy, stop the API, confirm port 8000 is free, and retry.

### Database locked

Close all services, development servers, backup scripts, restore scripts, and database tools.

### Activation fails after cutover

Keep CareQueue stopped.

Confirm which file is active, locate rollback and safety backup files, and do not make manual moves until the state is understood.

## Files That Must Not Be Committed

```text
backend/data/
backend/backups/
backend/restores/
local_backups/
*.db
*.sqlite
*.sqlite3
*.db.enc
*.restored.db
*.rollback.db
.env
```

Encrypted backups remain sensitive.

## Recovery Record

For a real recovery, record:

- Incident or change reference
- Recovery owner
- Approval
- Start time
- Selected backup
- Backup timestamp
- Verification result
- Safety backup path
- Rollback path
- Activation time
- Validation results
- Service restart time
- Final acceptance
- Follow-up actions

Do not include PHI, credentials, or keys.

## Minimum Recovery Checklist

Before declaring success:

- Selected backup was verified
- Required keys were available
- Services were stopped
- Preflight passed
- Safety backup was created
- Exact confirmation phrase was entered
- Final database validation passed
- Rollback database was preserved
- Direct readiness passed
- HTTPS readiness passed
- Login succeeded
- Representative records were reviewed
- Audit continuity was reviewed
- Recovery owner accepted the result
- Recovery record was completed

## Related Documentation

```text
docs/operations/health-checks.md
docs/operations/upgrades.md
docs/deployment/windows.md
docs/deployment/linux.md
docs/administration/audit-log.md
docs/troubleshooting/index.md
```

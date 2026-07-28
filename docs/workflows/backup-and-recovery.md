# Backup and Recovery Guide

This guide describes how to create, restore, and verify encrypted CareQueue database backups.

CareQueue backups are intended to protect the active local database without directly modifying or overwriting it during recovery.

## Important Key Requirements

CareQueue uses separate keys for separate protection layers:

```env
AUTHSTATUS_ENCRYPTION_KEY=
AUTHSTATUS_SQLCIPHER_KEY=
AUTHSTATUS_BACKUP_ENCRYPTION_KEY=
```

Each key has a different purpose:

- `AUTHSTATUS_ENCRYPTION_KEY` decrypts selected sensitive fields stored inside the database.
- `AUTHSTATUS_SQLCIPHER_KEY` unlocks the SQLCipher database file.
- `AUTHSTATUS_BACKUP_ENCRYPTION_KEY` decrypts encrypted `.db.enc` backup files.

A restored database may be unusable if any required key is missing or incorrect.

Store the keys securely outside the repository. Do not commit them, include them in screenshots, or paste them into issues or documentation.

## Before Creating a Backup

Confirm that the root `.env` points to the intended active database:

```env
AUTHSTATUS_DATABASE_PATH=backend/data/auth_tracker.sqlcipher.db
AUTHSTATUS_DATABASE_ENCRYPTION=sqlcipher
```

Also confirm that the SQLCipher and backup encryption keys are configured.

From the repository root:

```powershell
backend\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'backend'); from authstatus_api.settings import get_settings; s=get_settings(); print(s.database_path); print(s.database_encryption); print(bool(s.sqlcipher_key)); print(bool(s.backup_encryption_key))"
```

Expected output:

```text
backend\data\auth_tracker.sqlcipher.db
sqlcipher
True
True
```

Do not proceed if either key prints `False`.

## Create an Encrypted Backup

Run from the repository root:

```powershell
backend\.venv\Scripts\python.exe backend\scripts\create_encrypted_backup.py
```

The encrypted backup is written to:

```text
backend/backups/
```

Backup filenames end in:

```text
.db.enc
```

CareQueue creates a consistent database snapshot before encrypting the backup. It does not simply copy the active database file while it may be changing.

## Find the Newest Backup

From the repository root:

```powershell
Get-ChildItem backend\backups -Filter *.db.enc |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1 |
    Format-List FullName, Length, LastWriteTime
```

Confirm that the file exists and its size is greater than zero.

## Restore an Encrypted Backup

Restoring a backup creates a separate database under `backend/restores/`. It does not overwrite the active CareQueue database.

Run:

```powershell
backend\.venv\Scripts\python.exe backend\scripts\restore_encrypted_backup.py "G:\CareQueue\backend\backups\<backup-file>.db.enc"
```

Replace `<backup-file>` with the exact backup filename.

The restored database is written to:

```text
backend/restores/
```

Restored filenames normally end in:

```text
.restored.db
```

The restore process:

1. Decrypts the backup.
2. Writes it to a temporary file.
3. Runs a database integrity check.
4. Verifies that required CareQueue tables exist.
5. Moves the validated database into the restore directory.
6. Removes temporary files if validation fails.

## Find the Newest Restored Database

```powershell
Get-ChildItem backend\restores -Filter *.db |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1 |
    Format-List FullName, Length, LastWriteTime
```

## Verify a Restored SQLCipher Database

Run:

```powershell
backend\.venv\Scripts\python.exe backend\scripts\verify_sqlcipher_database.py --database-path "G:\CareQueue\backend\restores\<restored-file>.db"
```

Replace `<restored-file>` with the exact restored filename.

Expected output includes:

```text
Verified SQLCipher database
Required tables found:
- audit_events
- auth_events
- auths
- sessions
- users
```

## Confirm Plain SQLite Cannot Read the Restored File

A SQLCipher database should not be readable through ordinary SQLite.

Run this from an activated backend virtual environment:

```powershell
python -c "import sqlite3; p=r'G:\CareQueue\backend\restores\<restored-file>.db'; c=sqlite3.connect(p); ok=False;
try:
 c.execute('SELECT name FROM sqlite_master LIMIT 1').fetchone()
except sqlite3.DatabaseError:
 ok=True
finally:
 c.close()
print('PASS: plaintext SQLite cannot read the restored SQLCipher database' if ok else 'FAIL: plaintext SQLite read the restored database')"
```

Expected:

```text
PASS: plaintext SQLite cannot read the restored SQLCipher database
```

## Recovery Checklist

Before considering a restored database usable:

1. Confirm the backup decrypted successfully.
2. Confirm restore validation completed.
3. Run the independent SQLCipher verification script.
4. Confirm ordinary SQLite cannot read the restored file.
5. Keep the active database unchanged during verification.
6. Confirm all required encryption keys are available.
7. Preserve the original active database as a rollback copy.
8. Test the restored database through CareQueue before replacing anything.

## Replacing the Active Database

CareQueue does not automatically replace the active database during restore.

Do not overwrite the active database until the restored copy has been independently verified.

Before any manual replacement:

1. Stop the CareQueue backend.
2. Create another encrypted backup of the current active database.
3. Preserve the current active database as a rollback copy.
4. Confirm the restored database uses the expected SQLCipher key.
5. Confirm the root `.env` points to the intended database path.
6. Restart CareQueue and verify login, authorization records, users, and audit events.

Manual replacement should be treated as a recovery operation, not a routine restore step.

## Files That Must Not Be Committed

Do not commit:

```text
backend/backups/
backend/restores/
backend/data/
*.db
*.db.enc
*.restored.db
.env
```

Before committing documentation or source changes:

```powershell
git status --short
```

Encrypted backup files should still be treated as sensitive even though their contents are encrypted.

## Automated Backup Scheduling

CareQueue includes deployment files for scheduled encrypted backups on Windows and Linux.

The scheduling files invoke the same encrypted backup utility used for manual backups. They do not contain database keys or backup-encryption keys.

### Windows Task Scheduler

Windows deployment files are located under:

```text
deployment/windows/
├── install-backup-task.ps1
├── remove-backup-task.ps1
└── run-backup.ps1
```
The scheduled task defaults to:

- Task name: `CareQueue Encrypted Backup`
- Run time: `02:00`
- Service account: `SYSTEM`
- Production installation directory: `C:\Program Files\CareQueue`
- Backup directory: `C:\ProgramData\CareQueue\Backups`
- Environment file: `C:\ProgramData\CareQueue\Config\carequeue.env`

Run PowerShell as Administrator before installing or removing the scheduled task.

### Install the Windows Scheduled Task

For a production installation:

`.\deployment\windows\install-backup-task.ps1`

For a custom installation path:

```ps1
.\deployment\windows\install-backup-task.ps1 `
  -InstallDirectory "G:\CareQueue" `
  -BackupDirectory "G:\CareQueue\local_backups" `
  -EnvironmentFile "G:\CareQueue\.env"
```

The root `.env` example above is appropriate only for local testing. Production deployments should keep configuration and secrets outside the application installation directory.

### Confirm the Windows Task
```ps1
Get-ScheduledTask -TaskName "CareQueue Encrypted Backup"
```

A correctly installed task should normally show:
`State : Ready`

#### Run the Windows Task Manually
```ps1
Start-ScheduledTask -TaskName "CareQueue Encrypted Backup"
```
Wait for the task to finish, then inspect its result:
```ps1
Get-ScheduledTaskInfo -TaskName "CareQueue Encrypted Backup"
```
A successful run reports:
`LastTaskResult : 0`

Confirm that a nonempty encrypted backup was created:
```ps1
Get-ChildItem "G:\CareQueue\local_backups" |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 5 Name, Length, LastWriteTime
```
Production deployments should replace the example path with the configured backup directory.

#### Remove the Windows Scheduled Task
Run PowerShell as Administrator:
```ps1
.\deployment\windows\remove-backup-task.ps1
```
Confirm that it no longer exists:
```ps1
Get-ScheduledTask `
  -TaskName "CareQueue Encrypted Backup" `
  -ErrorAction SilentlyContinue
```
The removal script deletes only the scheduled task. It does not delete backups, configuration files, databases, or encryption keys.

#### Windows Troubleshooting
`Access is denied`

- Open PowerShell as Administrator.
- Re-run the installer.
- Confirm that the account can register scheduled tasks.

`Backup runner was not found`

- Confirm that `-InstallDirectory` points to the CareQueue repository or installation root.
- Confirm that `deployment\windows\run-backup.ps1` exists underneath that directory.

`Environment file was not found`
- Pass the correct path using `-EnvironmentFile`.
- Do not use `.env.example` as a production configuration file.
- Do not paste environment-file contents into logs, issues, or screenshots.

`LastTaskResult is not 0`
- Run `run-backup.ps1` manually with the same arguments.
- Confirm that the configured Python executable exists.
- Confirm that the database and backup encryption keys are available.
- Confirm that the service account can read the database and environment file.
- Confirm that the service account can write to the backup directory.

### Linux systemd Timer
Linux deployment files are located under:
```bash
deployment/linux/systemd/
├── carequeue-backup.service
└── carequeue-backup.timer
```
The supplied timer runs once daily around 2:00 AM and uses:
```bash
/var/lib/carequeue/backups
```
as the isolated backup destination.

The service expects CareQueue to be installed at:
```bash
/opt/carequeue
```
and expects its environment file at:
```bash
/etc/carequeue/carequeue.env
```
The service account must be able to:
- Read the CareQueue installation and active database.
- Read the protected environment file.
- Write to the isolated backup directory.
- Execute the backend virtual environment’s Python interpreter.

The environment file must include the required database and encryption settings. For an external backup directory, it should also include:
```env
AUTHSTATUS_BACKUP_DIRECTORY=/var/lib/carequeue/backups
AUTHSTATUS_ALLOW_UNSAFE_STORAGE_PATHS=true
```
The external path is intentional for deployment isolation. Filesystem ownership and permissions must restrict access to the CareQueue service account and authorized administrators.

#### Verify the Unit Files
On the Linux deployment host:
```bash
systemd-analyze verify \
  deployment/linux/systemd/carequeue-backup.service \
  deployment/linux/systemd/carequeue-backup.timer
```
#### Install the Unit Files
```bash
sudo cp deployment/linux/systemd/carequeue-backup.service \
  /etc/systemd/system/

sudo cp deployment/linux/systemd/carequeue-backup.timer \
  /etc/systemd/system/

sudo systemctl daemon-reload
```
#### Run the Linux Backup Manually
Before enabling the timer:
```bash
sudo systemctl start carequeue-backup.service
```
Check the result:
```bash
sudo systemctl status carequeue-backup.service
```
Review the service logs:
```bash
sudo journalctl \
  -u carequeue-backup.service \
  --since today
```
Confirm that a nonempty `.db.enc` file exists:
```bash
sudo find /var/lib/carequeue/backups \
  -maxdepth 1 \
  -type f \
  -name "*.db.enc" \
  -printf "%TY-%Tm-%Td %TH:%TM:%TS %s %f\n"
```
#### Enable the Linux Timer
Enable the timer only after the manual service run succeeds:
```bash
sudo systemctl enable --now carequeue-backup.timer
```
Confirm the next scheduled run:
```bash
systemctl list-timers carequeue-backup.timer
```
#### Disable the Linux Timer
```bash
sudo systemctl disable --now carequeue-backup.timer
```
Disabling the timer does not delete existing backups.

### Scheduled Backup Validation
A scheduler reporting success is not enough by itself.

Administrators should periodically confirm that:

1. A recent encrypted backup exists.
2. The backup file is greater than zero bytes.
3. Backup timestamps match the expected schedule.
4. Failed runs are investigated.
5. At least one backup can be restored and verified.
6. Backup files remain inaccessible to unauthorized accounts.
7. Encryption keys are backed up separately and securely.

## Recommended Backup Routine

For local personal workflow use:

- Create an encrypted backup before database migrations or major upgrades.
- Create an encrypted backup before changing encryption settings or keys.
- Create periodic backups during regular use.
- Keep more than one recent backup.
- Periodically perform a restore-and-verification drill.
- Store at least one protected backup separately from the active computer.
- Verify that the required keys are also backed up securely.

A backup should not be considered reliable until it has been successfully restored and verified.
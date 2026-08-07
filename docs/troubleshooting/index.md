# Troubleshooting

This page is a symptom-based index for common CareQueue problems.

Detailed procedures live in the documents that own each workflow. Use this page to identify the correct guide without repeating the same commands in several places.

## Start Here

First identify the environment:

```text
Development
Windows production
Linux deployment
```

Then identify the failure area:

```text
Installer or Windows services
Application startup
HTTPS or certificate
First-time Admin setup
Login or session
Database
Backup or recovery
Upgrade, repair, or uninstall
PDF intake
Registered options
Audit log
Local development
```

Development and production use separate databases, environment files, keys, users, cookies, origins, and runtime directories.

Do not replace a production database with a development database to resolve a login or workflow issue.

## Installer Does Not Show Upgrade, Repair, or Uninstall

Symptoms:

- The Windows installer shows only the normal Install flow
- The operation selection page is missing
- Upgrade, Repair, and Uninstall choices do not appear

Use:

```text
docs/deployment/windows.md
docs/operations/upgrades.md
```

The operation selection page appears only when CareQueue is already installed and the installer can detect the installed application files.

A clean machine or a machine after uninstall should show only the normal Install flow. After a successful install, running the installer again should show Upgrade, Repair, and Uninstall options.

Do not treat the missing operation page as a bug until you confirm whether the installed application directory still exists.

## Installer Fails During Install, Upgrade, Repair, or Uninstall

Symptoms:

- Installer reports that the operation failed
- Install succeeds locally but fails on another machine
- Service validation fails near the end of setup
- API or Caddy does not start after installation
- The newest installer log reports a failed mode

Use:

```text
docs/deployment/windows.md
docs/operations/upgrades.md
docs/operations/health-checks.md
```

Check the newest installer log first:

```text
C:\ProgramData\CareQueue\Logs\Installer
```

The installer mode matters. Confirm whether the log says:

```text
Mode: Install
Mode: Upgrade
Mode: Repair
Mode: Uninstall
```

Do not repeatedly rerun the installer without identifying which step failed.

## First-Time Admin Setup Problems

Symptoms:

- The first-time Admin setup window does not open
- The setup window says setup is already complete
- Admin creation fails
- Password is rejected
- The setup status endpoint says setup is unavailable
- The created Admin cannot sign in

Use:

```text
docs/administration/users-and-security.md
docs/deployment/windows.md
```

The first-time Admin setup flow is available only while no users exist in the active production database. After any user exists, the setup endpoint is disabled and the setup window should report that setup is already complete.

The packaged setup window posts credentials to the local API over loopback and does not pass the password through command-line arguments.

If setup is reported as complete unexpectedly, confirm that the installer is using the intended production database under the Windows data directory.

## Application Will Not Start

Symptoms:

- CareQueue page does not load
- API service is stopped
- Caddy service is stopped
- Port 8000 is not listening
- Port 443 is not listening
- Liveness fails
- Readiness fails

Use:

```text
docs/operations/health-checks.md
docs/deployment/windows.md
```

The health-check guide owns the troubleshooting order:

```text
1. Service status
2. Direct API liveness
3. Direct API readiness
4. Hostname resolution
5. Certificate trust
6. HTTPS liveness
7. HTTPS readiness
8. Frontend loading
9. Login
10. Representative workflow
```

## HTTPS, Caddy, or Certificate Problems

Symptoms:

- `carequeue.local` does not resolve
- Browser shows a certificate warning
- Direct API health works but HTTPS fails
- Caddy stops immediately
- Port 443 is already in use
- Reverse proxy cannot reach the API

Use:

```text
docs/operations/health-checks.md
docs/deployment/windows.md
```

The health-check guide owns the diagnostic commands for hostname resolution, certificate trust, port checks, direct API checks, and HTTPS checks.

## Login, Password, or Session Problems

Symptoms:

- Invalid username or password
- User exists in development but not production
- Required password-change screen appears
- Temporary password was lost
- Password change signs the user out
- Session warning does not appear
- Session renewal fails
- `401` from `/api/security/me`
- `403` on a state-changing request

Use:

```text
docs/administration/users-and-security.md
```

A `401` from `/api/security/me` before login is expected.

A successful password change revokes active sessions and requires login again.

## Production Frontend Calls `localhost:8000`

Symptom:

```text
Production browser requests use http://localhost:8000/api/...
```

Use:

```text
docs/development/local-development.md
docs/operations/upgrades.md
```

The production frontend should use same-origin requests:

```text
https://carequeue.local/api/...
```

Development API overrides should remain in frontend development environment files and should not be baked into production builds.

## Database Problems

Symptoms:

- Readiness fails while liveness passes
- SQLCipher database will not open
- Field-level decryption fails
- Database path is rejected
- Database is locked
- Plaintext and SQLCipher modes are confused
- Application starts against the wrong database

Use:

```text
SECURITY.md
docs/development/local-development.md
docs/workflows/backup-and-recovery.md
docs/operations/health-checks.md
```

Do not:

- Generate a new key for an existing encrypted database
- Open a plaintext database as SQLCipher
- Open a SQLCipher database as plaintext
- Delete sidecar files while a process may still be using the database
- Enable unsafe paths merely to bypass a typo
- Rewrite encrypted values with a guessed key

## Backup Problems

Symptoms:

- Scheduled backup did not run
- Task reports success but no backup appears
- Backup key is missing
- Retention cleanup fails
- Backup verification fails
- Restore reports an unsafe path

Use:

```text
docs/workflows/backup-and-recovery.md
```

A file appearing in the backup directory does not prove recoverability. Use the backup guide for verification and restore procedures.

## Recovery Problems

Symptoms:

- Recovery will not stage
- Recovery activation says services are running
- Port 8000 remains in use
- Database sidecar files remain
- Cutover fails
- Active database state is uncertain
- Rollback or safety-backup state is unclear

Use:

```text
docs/workflows/backup-and-recovery.md
```

Stop normal troubleshooting and preserve the current state when the active database is uncertain, cutover failed, rollback may have failed, or a safety backup cannot be verified.

## Upgrade, Repair, or Uninstall Problems

Symptoms:

- Upgrade does not preserve runtime data
- Repair does not restore files or services
- Uninstall removes application files but data expectations are unclear
- Services are left in an uncertain state
- Post-install validation fails
- Rollback may be required

Use:

```text
docs/operations/upgrades.md
docs/deployment/windows.md
docs/operations/health-checks.md
```

For packaged Windows installs, uninstall should remove application files and services while preserving runtime data under:

```text
C:\ProgramData\CareQueue
```

Confirm the actual behavior from the installer log instead of relying only on the final installer screen.

## PDF Intake Problems

Symptoms:

- No values extracted
- Unsupported template warning
- PDF contains no usable embedded text
- File is too large
- Password-protected PDF is rejected
- Extracted value is incorrect
- Facility or insurance does not match
- Inspection output contains sensitive text

Use:

```text
docs/workflows/pdf-intake.md
```

PDF intake does not automatically create an authorization. The user must review and correct extracted values before applying them to the authorization form.

Use synthetic or approved stripped PDFs for testing.

## Registered Option Problems

Symptoms:

- Registered options do not load
- Add button is disabled
- Duplicate option error
- Protected `Other` cannot be deleted
- Deleted option still appears in filters
- PDF intake reports an unregistered facility or insurance

Use:

```text
docs/administration/registered-options.md
```

Deleting a registered facility or insurance does not rewrite existing authorization records.

Historical values may remain available in filters.

## Audit Log Problems

Symptoms:

- Audit Log page is missing
- Audit events will not load
- Filters return no results
- Username is blank
- Expected event is missing
- IP address appears as loopback

Use:

```text
docs/administration/audit-log.md
```

The Audit Log is Admin-only.

A missing event does not always prove that an action did not occur. The action may not be audited, the request may have failed before auditing, or the active database may have been restored from an earlier backup.

## Local Development Problems

Symptoms:

- Backend cannot find `.env`
- Virtual environment will not activate
- Backend import fails
- CORS error
- Vite uses another port
- `npm ci` fails
- Frontend build fails
- Backend tests fail
- Ruff changes files
- Local database reset removes users

Use:

```text
docs/development/local-development.md
```

Standard backend checks:

```powershell
pytest tests -n auto -q
ruff check . --fix
```

Standard frontend checks:

```powershell
npm test
npm run build
```

## Authorization Workflow Problems

Symptoms:

- Add Authorization button is missing
- Form will not submit
- Record does not appear after creation
- Edit or delete fails
- Queue appears empty
- Dashboard count does not match the queue
- Calendar date appears wrong

Use:

```text
docs/workflows/authorization-workflow.md
```

Clear active filters before concluding that a record is missing.

Confirm the current user role before troubleshooting missing create, edit, or delete controls.

## Where to Find Logs

### Windows Installer

```text
C:\ProgramData\CareQueue\Logs\Installer
```

### Windows API

```text
C:\ProgramData\CareQueue\Logs\Api
```

### Windows Caddy

```text
C:\ProgramData\CareQueue\Logs\Caddy
```

### Linux

Caddy:

```bash
sudo journalctl -u caddy --since today
```

Backup service:

```bash
sudo journalctl -u carequeue-backup.service --since today
```

API log location depends on the process manager used by the Linux deployment.

Review logs before sharing them.

## Safe Troubleshooting Rules

Do not share:

- `.env` contents
- Encryption keys
- Passwords
- Temporary passwords
- Session tokens
- CSRF tokens
- Cookies
- Production databases
- Encrypted backups
- Real PDFs
- Real patient information
- Full unreviewed production logs

Do not:

- Disable security checks without understanding the effect
- Delete database sidecar files blindly
- Overwrite the active database manually
- Put sensitive values into temporary debug output
- Use real patient data to reproduce a bug

Use synthetic data whenever possible.

## What to Include in a Bug Report

Include:

- CareQueue commit or release
- Operating system
- Development or production environment
- Installer mode when relevant
- Exact command run
- Exact sanitized error
- Expected behavior
- Actual behavior
- Relevant service state
- Relevant health-check result
- Minimal sanitized log excerpt
- Synthetic reproduction steps

Do not include secrets or real record content.

## Escalation Conditions

Stop normal troubleshooting and preserve the current state when:

- An encryption key may be exposed
- A production database may be corrupted
- A backup cannot be decrypted
- A recovery cutover failed
- Audit records may have been altered
- Unauthorized access is suspected
- PHI or PII may have been exposed
- Multiple services fail after an upgrade or repair

In those cases, preserve logs, stop making state-changing fixes, and work from verified backups or a clean test reproduction.

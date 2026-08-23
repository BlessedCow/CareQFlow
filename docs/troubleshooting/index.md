# Troubleshooting

This page is a symptom-based index for common CareQueue problems.

Detailed procedures live in the documents that own each workflow. Use this page to identify the correct guide without duplicating complete recovery procedures in several places.

## Start Here

First identify the environment:

```text
Local development
Windows packaged deployment
Linux packaged deployment
```

Then identify the failure area:

```text
Installer or package
Application startup
HTTPS or certificate
First-time Admin setup
Governance attestation
Login, MFA, or session
Database
Backup or recovery
Upgrade, repair, or uninstall
PDF intake
Registered options
Audit log
Local development
```

Development and production environments use separate databases, environment files, keys, users, cookies, governance state, MFA enrollment, remembered-device records, origins, and runtime directories.

Do not replace a production database with a development database to resolve a login or workflow issue.

## Windows Installer Does Not Show Upgrade, Repair, or Uninstall

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

Do not treat the missing operation page as a failure until the installed application state has been confirmed.

## Windows Installer Fails During Install, Upgrade, Repair, or Uninstall

Symptoms:

- Installer reports that the operation failed
- Installation succeeds on one machine but fails on another
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

Do not repeatedly rerun the installer without first identifying the failed step.

## Linux Package or Installer Problems

Symptoms:

- The release archive will not extract
- The installer rejects the Linux distribution
- Required system packages cannot be installed
- The `carequeue` service account cannot be created
- API, Caddy, or backup systemd units fail to install
- Certificate trust setup fails
- Post-install HTTPS or readiness validation fails

Use:

```text
docs/deployment/linux.md
docs/operations/upgrades.md
docs/operations/health-checks.md
```

Linux installer logs are stored under:

```text
/var/log/carequeue/installer/
```

Check the installed service state:

```bash
sudo systemctl status carequeue-api.service
sudo systemctl status carequeue-caddy.service
sudo systemctl status carequeue-backup.timer
```

Review service logs before repeating the installation:

```bash
sudo journalctl -u carequeue-api.service --since today
sudo journalctl -u carequeue-caddy.service --since today
```

The Linux deployment is intended for supported Debian-based systems. Confirm that the target operating-system version is supported and that the release package is the intended artifact.

## First-Time Admin Setup Problems

Symptoms:

- The first-time Admin setup window or script does not run
- Setup reports that initial setup is already complete
- Admin creation fails
- Password is rejected
- The setup status endpoint says setup is unavailable
- The created Admin cannot sign in

Use:

```text
docs/administration/users-and-security.md
docs/deployment/windows.md
docs/deployment/linux.md
```

Initial Admin setup is available only while no users exist in the active production database.

After any user exists, the bootstrap endpoint is disabled and the setup utility should report that setup is already complete.

Packaged first-time setup sends credentials only to the loopback CareQueue API.

If setup is unexpectedly reported as complete, confirm that CareQueue is using the intended production database before changing any database or encryption configuration.

## Governance Attestation Problems

Symptoms:

- Login succeeds but normal application pages do not load
- The governance attestation page appears after login
- A non-Admin user cannot continue
- Protected API requests return HTTP `428`
- An Admin accepted governance previously but the application requires it again
- Governance history is missing or unexpected

Use:

```text
docs/administration/users-and-security.md
docs/administration/audit-log.md
```

A protected request returning:

```text
428 Governance attestation required.
```

means the user is authenticated but the current organization governance attestation has not been completed.

Only an Admin can accept the organization-level attestation.

A non-Admin user should remain blocked from normal protected application functionality until an Admin completes the requirement.

If governance was accepted previously but is required again, check whether:

- The application is using the expected database.
- The required governance attestation version changed.
- The installation was restored from an older backup.
- The previous attestation belongs to another environment or database.

The CareQueue application version and governance attestation version are independent. An ordinary application-version increase does not by itself require re-attestation.

Do not manually edit governance history to bypass the requirement.

## Application Will Not Start

Symptoms:

- CareQueue page does not load
- API service is stopped
- Caddy service is stopped
- Port `8000` is not listening
- Port `443` is not listening
- Liveness fails
- Readiness fails

Use:

```text
docs/operations/health-checks.md
docs/deployment/windows.md
docs/deployment/linux.md
```

Use this general troubleshooting order:

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
10. Governance state
11. Representative protected workflow
```

If direct API health works but HTTPS does not, focus on Caddy, hostname resolution, certificate trust, or port conflicts before changing backend configuration.

## HTTPS, Caddy, or Certificate Problems

Symptoms:

- `carequeue.local` does not resolve
- Browser shows a certificate warning
- Direct API health works but HTTPS fails
- Caddy stops immediately
- Port `443` is already in use
- Reverse proxy cannot reach the API

Use:

```text
docs/operations/health-checks.md
docs/deployment/windows.md
docs/deployment/linux.md
```

The health-check guide contains diagnostic commands for:

- Hostname resolution
- Certificate trust
- Port ownership
- Direct API checks
- HTTPS checks
- Windows service state
- Linux systemd state

Do not permanently disable TLS verification to work around a certificate problem.

## Login or Password Problems

Symptoms:

- Invalid username or password
- User exists in development but not production
- Required password-change screen appears
- Temporary password was lost
- Password change signs the user out
- Account is temporarily locked
- `401` from `/api/security/me`

Use:

```text
docs/administration/users-and-security.md
docs/administration/audit-log.md
```

A `401` from `/api/security/me` before login or after session expiration/revocation is expected.

A successful password change revokes active sessions and requires login again.

If a user exists in one environment but not another, confirm that the expected database and environment are active.

Do not recreate users or replace a database until the active environment has been confirmed.

## MFA Problems

Symptoms:

- Login asks for an authenticator code
- MFA enrollment will not complete
- A valid-looking TOTP code is rejected
- MFA setup shows as pending
- Admin MFA reset is unavailable
- User cannot log in after MFA reset

Use:

```text
docs/administration/users-and-security.md
docs/administration/audit-log.md
```

Check:

- The account is active.
- The authenticator is using the current CareQueue enrollment.
- The submitted code is the current 6-digit TOTP value.
- The authenticator device clock is accurate.
- The MFA challenge has not expired.
- The user is not trying to reuse an obsolete enrollment secret.

An Admin can reset MFA for another user through user management.

Admins cannot reset their own MFA using the administrative user-management reset action.

MFA secrets and codes must not be copied into screenshots, tickets, logs, or bug reports.

## Remembered Device Problems

Symptoms:

- A remembered device asks for MFA again
- A user expected MFA to be skipped but it was required
- Remembered-device revocation does not end the current login session

Use:

```text
docs/administration/users-and-security.md
```

A remembered device is separate from the authenticated session.

It may stop being trusted because:

- The 30-day trust period expired.
- Browser cookies were cleared.
- The remembered-device record was revoked.
- A security-sensitive account change invalidated remembered-device state.
- The login is occurring from another browser profile or device.

Revoking remembered devices does not necessarily end the currently authenticated session. It requires MFA again on a later login that would otherwise have used the trusted-device state.

A remembered device never bypasses password verification.

## Session Timeout, Renewal, or Cross-Tab Problems

Symptoms:

- Session warning appears unexpectedly
- Session expires while the user is inactive
- Session renewal fails
- One browser tab logs out after another tab logs out
- A previous session stops working after login from another browser or device
- Session activity does not revive an expired session
- `403` appears on a state-changing session request

Use:

```text
docs/administration/users-and-security.md
docs/operations/health-checks.md
```

CareQueue uses a server-enforced inactivity timeout with a 20-minute default.

Authenticated activity can extend a valid session, but an expired session cannot be revived.

CareQueue permits one active authenticated session per account. A new authenticated login revokes the previous active session.

Logout and expiration information is synchronized across open CareQueue tabs when supported by the browser.

Session renewal and session-activity requests require valid CSRF protection.

Do not increase the inactivity timeout solely to hide a session problem. Confirm the actual server expiration and browser behavior first.

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

Development API overrides should remain in development-only frontend configuration and must not be included in a production build.

## Database Problems

Symptoms:

- Readiness fails while liveness passes
- SQLCipher database will not open
- Field-level decryption fails
- Database path is rejected
- Database is locked
- Plaintext and SQLCipher modes are confused
- Application starts against the wrong database
- A restore produces unexpected application state

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
- Enable unsafe paths merely to bypass a path error
- Rewrite encrypted values with a guessed key
- Replace the active database with an unverified backup

If the active database state is uncertain, preserve the current state before making additional changes.

## Backup Problems

Symptoms:

- Windows scheduled backup did not run
- Linux backup timer did not run
- Backup service reports failure
- A backup file is not created
- Backup key is missing
- Retention cleanup fails
- Backup verification fails
- Restore reports an unsafe path

Use:

```text
docs/workflows/backup-and-recovery.md
```

A file appearing in the backup directory does not prove recoverability.

Use the supported verification workflow and periodically test recovery.

On Linux, check:

```bash
sudo systemctl status carequeue-backup.service
sudo systemctl status carequeue-backup.timer
sudo journalctl -u carequeue-backup.service --since today
```

On Windows, review the installed backup task and run the installed backup helper manually when appropriate.

## Recovery Problems

Symptoms:

- Recovery will not stage
- Recovery activation says services are running
- Port `8000` remains in use
- Database sidecar files remain
- Cutover fails
- Active database state is uncertain
- Rollback or safety-backup state is unclear

Use:

```text
docs/workflows/backup-and-recovery.md
```

Recovery activation is an offline administrative operation.

Stop the CareQueue HTTPS service first, then stop the API service before activation.

Windows services:

```text
CareQueueCaddy
CareQueueApi
```

Linux services:

```text
carequeue-caddy.service
carequeue-api.service
```

Stop normal troubleshooting and preserve the current state when:

- The active database is uncertain.
- Cutover failed.
- Rollback may have failed.
- A safety backup cannot be verified.
- Required encryption keys may be unavailable.

## Upgrade, Repair, or Uninstall Problems

Symptoms:

- Upgrade does not preserve runtime data
- Repair does not restore files or services
- Uninstall behavior is unclear
- Services are left in an uncertain state
- Post-install validation fails
- Rollback may be required

Use:

```text
docs/operations/upgrades.md
docs/deployment/windows.md
docs/deployment/linux.md
docs/operations/health-checks.md
```

### Windows

A normal packaged uninstall removes application files and CareQueue services while preserving runtime data under:

```text
C:\ProgramData\CareQueue
```

### Linux

A normal packaged uninstall removes `/opt/carequeue` and CareQueue systemd units while preserving:

```text
/etc/carequeue
/var/lib/carequeue
/var/log/carequeue
```

A normal uninstall is not secure data destruction.

Confirm actual behavior from installer logs and filesystem/service state rather than relying only on the final installer message.

## Release Version or Artifact Problems

Symptoms:

- Windows and Linux artifacts show different application versions
- The backend reports an unexpected application version
- The Windows release validator expects the wrong installer filename
- A release package still uses the previous version

Use:

```text
docs/development/command-reference.md
docs/operations/upgrades.md
```

Use the controlled release-version helper:

```powershell
.\deployment\bump-version.ps1 -Version 0.3.0
```

Replace `0.3.0` with the intended version.

Review the resulting changes:

```powershell
git status --short
git diff
```

Do not perform an unrestricted repository-wide text replacement for version numbers. Historical tests, governance fixtures, dependency versions, and documentation examples may intentionally contain older version values.

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

PDF intake does not automatically create an authorization.

The user must review and correct extracted values before applying them to the authorization form.

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

Deleting a registered facility or insurance does not rewrite historical authorization records.

Historical values may remain available in filters.

## Audit Log or Integrity Problems

Symptoms:

- Audit Log page is missing
- Audit events will not load
- Filters return no results
- Username is blank
- Expected event is missing
- IP address appears as loopback
- Audit integrity verification reports `invalid`
- Audit integrity verification reports legacy events

Use:

```text
docs/administration/audit-log.md
```

The Audit Log and integrity-verification controls are Admin-only.

A missing event does not always prove that an action did not occur. The action may not be audited, the request may have failed before the audit write, or the active database may have been restored from an earlier backup.

Legacy audit events can exist when a database contains records created before cryptographic audit chaining was introduced.

An `invalid` integrity result should be treated as a security and data-integrity issue. Preserve the current database, backups, and relevant logs before attempting corrective changes.

Do not edit or delete audit records merely to make an integrity check pass.

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
- Local database reset causes governance setup to appear again

Use:

```text
docs/development/local-development.md
```

Standard backend checks from the `backend` directory:

```powershell
pytest tests -n auto -q
ruff check authstatus_api tests --fix
```

Standard frontend checks from the repository root:

```powershell
npm --prefix frontend test
npm --prefix frontend run build
```

A newly initialized development database has no users, MFA enrollment, remembered devices, sessions, or governance history from the previous database.

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

Before troubleshooting a missing record:

- Clear active filters.
- Confirm the current user role.
- Confirm the current governance requirement has been completed.
- Confirm the expected database/environment is active.

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

### Linux Installer

```text
/var/log/carequeue/installer/
```

### Linux API

```bash
sudo journalctl -u carequeue-api.service --since today
```

### Linux Caddy

```bash
sudo journalctl -u carequeue-caddy.service --since today
```

### Linux Backup Service

```bash
sudo journalctl -u carequeue-backup.service --since today
```

Review logs before sharing them. Sanitize host, environment, user, and other sensitive information as appropriate.

## Safe Troubleshooting Rules

Do not share:

- `.env` contents
- Encryption keys
- Passwords
- Temporary passwords
- Password hashes
- MFA secrets
- MFA codes
- MFA challenge tokens
- Session tokens
- Remembered-device tokens
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
- Generate replacement production keys to bypass decryption failures
- Put sensitive values into temporary debug output
- Manually edit governance or audit history to bypass application controls
- Use real patient data to reproduce a bug
- Permanently disable TLS certificate validation
- Broaden filesystem permissions without understanding why access failed

Use synthetic data whenever possible.

## What to Include in a Bug Report

Include:

- CareQueue release version
- Source commit or tag when known
- Operating system and version
- Development or packaged environment
- Windows installer or Linux installer mode when relevant
- Release artifact filename when relevant
- Exact command run
- Exact sanitized error
- Expected behavior
- Actual behavior
- Relevant service state
- Relevant liveness/readiness result
- Minimal sanitized log excerpt
- Synthetic reproduction steps

For authentication or governance issues, include only non-sensitive state such as:

```text
Role
MFA enabled: yes/no
Governance current: yes/no
HTTP status code
```

Do not include credentials, TOTP values, secrets, tokens, patient data, or full record contents.

## Escalation Conditions

Stop normal troubleshooting and preserve the current state when:

- An encryption key may be exposed
- An authentication secret or session token may be exposed
- A production database may be corrupted
- A backup cannot be decrypted
- A recovery cutover failed
- Audit integrity verification fails unexpectedly
- Audit records may have been altered
- Unauthorized access is suspected
- PHI or PII may have been exposed
- Multiple services fail after an upgrade or repair
- The active database or encryption-key state is uncertain

In those situations:

1. Avoid additional state-changing fixes.
2. Preserve relevant logs and installation metadata.
3. Preserve the current database and verified backups.
4. Record recent deployment or administrative changes.
5. Follow the organization's incident-response or recovery process.
6. Reproduce the issue with synthetic data on a separate test system when possible.

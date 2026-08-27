# Health Checks

CareQueue exposes public health endpoints for operational validation.

Use health checks to confirm that the API process is responding and that the configured database is reachable. Health checks are intentionally narrow. They do not replace login testing, browser testing, governance validation, MFA testing, backup verification, or representative workflow testing.

## Health Endpoints

CareQueue exposes:

```text
GET /api/health
GET /api/health/live
GET /api/health/ready
```

The general and liveness endpoints currently return:

```json
{
  "status": "ok"
}
```

A successful readiness response returns:

```json
{
  "status": "ok"
}
```

If the readiness database check fails, CareQueue returns HTTP `503` with:

```json
{
  "status": "unavailable"
}
```

Use `/api/health/live` and `/api/health/ready` for operational checks because their meanings are explicit.

## Liveness

Endpoint:

```text
GET /api/health/live
```

Liveness answers:

```text
Is the API process running and able to respond?
```

A successful liveness response does not prove:

- Database access
- Authentication
- MFA
- Governance completion
- Caddy operation
- Certificate trust
- Frontend availability
- Backup operation
- Authorization workflow correctness

Liveness is useful when distinguishing an API process failure from a database or reverse-proxy problem.

## Readiness

Endpoint:

```text
GET /api/health/ready
```

Readiness answers:

```text
Can the API open the configured database and execute a basic query?
```

Use readiness for:

- Post-install validation
- Post-upgrade validation
- Post-repair validation
- Post-recovery validation
- Service monitoring
- Database accessibility checks

Readiness does not validate every table, application workflow, account, backup, or browser behavior.

Readiness also does not prove that every post-upgrade validation requirement has been completed.

Database initialization, including required registered schema migrations, occurs before normal API readiness can succeed. A readiness failure after an upgrade may therefore indicate a database configuration, encryption, schema initialization, or migration problem.

Do not treat a successful readiness response as proof that governance, audit integrity, backup operation, recovery compatibility, or representative protected workflows have been validated.

## General Health Endpoint

Endpoint:

```text
GET /api/health
```

The general health endpoint currently behaves like the liveness endpoint.

Prefer the explicit `/api/health/live` and `/api/health/ready` endpoints in operational procedures.

## Authentication and Information Exposure

Health endpoints are public and do not require an authenticated CareQueue session.

Their responses are intentionally minimal.

Health responses must not expose:

- Database paths
- Encryption keys
- Environment values
- User information
- Session state
- Governance records
- Internal SQL errors
- Stack traces
- Backup filenames
- Host credentials
- Authentication secrets

## Production Request Path

Packaged CareQueue deployments keep the API on loopback:

```text
127.0.0.1:8000
```

Caddy serves the frontend over HTTPS and proxies `/api` requests to the loopback API.

The packaged private application origin is:

```text
https://carequeue.local
```

Two types of health checks are useful:

### Direct API check

A direct loopback check bypasses Caddy:

```text
http://127.0.0.1:8000/api/health/...
```

Use this to isolate API and database behavior.

### HTTPS application-path check

An HTTPS check uses the same request path as the browser:

```text
https://carequeue.local/api/health/...
```

Use this to validate:

- Hostname resolution
- Port 443
- Caddy
- Certificate trust
- Reverse proxy
- API response
- Database readiness when using `/ready`

A deployment can pass a direct API check while failing the HTTPS check.

## Windows Service Checks

Packaged Windows installations use:

```text
CareQueueApi
CareQueueCaddy
```

Run PowerShell as Administrator:

```powershell
Get-Service CareQueueApi, CareQueueCaddy |
    Select-Object Name, Status, StartType
```

Both services should normally report:

```text
Status: Running
StartType: Automatic
```

A running service does not by itself prove that CareQueue is healthy. Continue with endpoint checks.

## Windows Direct API Liveness

```powershell
Invoke-RestMethod `
    -Method Get `
    -Uri "http://127.0.0.1:8000/api/health/live" `
    -TimeoutSec 10
```

Expected response:

```text
status
------
ok
```

This bypasses Caddy.

## Windows Direct API Readiness

```powershell
Invoke-RestMethod `
    -Method Get `
    -Uri "http://127.0.0.1:8000/api/health/ready" `
    -TimeoutSec 10
```

Expected response:

```text
status
------
ok
```

If direct liveness succeeds but direct readiness fails, focus troubleshooting on the backend database/configuration path rather than Caddy.

## Windows HTTPS Liveness

```powershell
Invoke-RestMethod `
    -Method Get `
    -Uri "https://carequeue.local/api/health/live" `
    -TimeoutSec 10
```

This checks the complete HTTPS request path without requiring authentication.

## Windows HTTPS Readiness

```powershell
Invoke-RestMethod `
    -Method Get `
    -Uri "https://carequeue.local/api/health/ready" `
    -TimeoutSec 10
```

This is the preferred Windows production readiness check because it validates both the HTTPS request path and database accessibility.

## Windows Frontend Check

Open:

```text
https://carequeue.local
```

Confirm:

- The certificate is trusted.
- The login page loads.
- Static assets load correctly.
- Browser developer tools do not show failed production asset requests.
- Production API requests use same-origin `/api` URLs.
- The browser is not attempting to call a development address such as `localhost:8000`.

A successful frontend load does not prove that authentication or protected application workflows are working.

## Windows First-Time Admin Setup Check

For a fresh installation, initial Admin setup uses:

```text
GET /api/security/setup-initial-admin/status
```

The packaged setup utility calls the loopback API.

Expected response while no users exist:

```json
{
  "setup_available": true
}
```

Expected response after at least one user exists:

```json
{
  "setup_available": false
}
```

The bootstrap status endpoint only indicates whether first-time Admin creation remains available.

After the first Admin is created:

1. Sign in through the browser.
2. Complete the current governance attestation when required.
3. Confirm protected application pages become available.

## Linux Service Checks

Packaged Linux installations use:

```text
carequeue-api.service
carequeue-caddy.service
carequeue-backup.service
carequeue-backup.timer
```

Check the API service:

```bash
sudo systemctl status carequeue-api.service
```

Check Caddy:

```bash
sudo systemctl status carequeue-caddy.service
```

Check whether the backup timer is enabled:

```bash
sudo systemctl is-enabled carequeue-backup.timer
```

Check whether the backup timer is active:

```bash
sudo systemctl is-active carequeue-backup.timer
```

List the scheduled timer:

```bash
sudo systemctl list-timers carequeue-backup.timer
```

The backup service itself may be inactive between scheduled runs. The timer is the persistent scheduling unit.

## Linux Direct API Liveness

```bash
curl \
  --fail \
  --silent \
  --show-error \
  http://127.0.0.1:8000/api/health/live
```

Expected JSON:

```json
{"status":"ok"}
```

## Linux Direct API Readiness

```bash
curl \
  --fail \
  --silent \
  --show-error \
  http://127.0.0.1:8000/api/health/ready
```

Expected JSON:

```json
{"status":"ok"}
```

## Linux HTTPS Liveness

```bash
curl \
  --fail \
  --silent \
  --show-error \
  https://carequeue.local/api/health/live
```

## Linux HTTPS Readiness

```bash
curl \
  --fail \
  --silent \
  --show-error \
  https://carequeue.local/api/health/ready
```

Do not permanently disable TLS verification to make a health check pass.

If the certificate is not trusted, resolve the Caddy internal certificate-authority trust problem.

## Linux Frontend Check

From a browser on an approved client system, open:

```text
https://carequeue.local
```

Confirm:

- The certificate is trusted.
- The login page loads.
- Static assets load.
- Requests to `/api` succeed through the same HTTPS origin.

The packaged Linux deployment is designed around the private `carequeue.local` origin. A different hostname or broader network deployment requires separate Caddy, DNS, and certificate planning.

## Local Development

The normal development endpoints are:

```text
Backend:  http://127.0.0.1:8000
Frontend: http://localhost:5173
```

Development liveness:

```powershell
Invoke-RestMethod `
    -Method Get `
    -Uri "http://127.0.0.1:8000/api/health/live" `
    -TimeoutSec 10
```

Development readiness:

```powershell
Invoke-RestMethod `
    -Method Get `
    -Uri "http://127.0.0.1:8000/api/health/ready" `
    -TimeoutSec 10
```

When using an alternate development backend port, change the URL accordingly.

## Interpreting Results

### Direct liveness succeeds, HTTPS fails

Likely areas to investigate:

- Caddy service stopped
- Invalid Caddy configuration
- Certificate trust failure
- Hostname resolution failure
- Port 443 conflict
- Local firewall or endpoint-security interference

Because the direct API responds, begin with the HTTPS/proxy layer.

### Direct liveness fails

Likely areas to investigate:

- API service stopped
- Backend startup failure
- Port 8000 conflict
- Invalid production configuration
- Missing backend dependency
- Service-account permission failure
- Invalid installed application files

Review the API service logs before changing configuration.

### Liveness succeeds, readiness fails

Likely areas to investigate:

- Incorrect database path
- Incorrect SQLCipher key
- Incorrect database-encryption mode
- Database lock
- Runtime permission failure
- Database corruption
- Schema initialization or migration failure
- Production configuration mismatch
- Recovery state requiring investigation

If this occurs immediately after an upgrade, review the API and installer logs before retrying the upgrade or modifying the database.

Do not manually edit `schema_migrations` or production table definitions to make readiness pass. Investigate the migration failure or use the documented backup and recovery procedure when recovery is required.

Do not generate a new key for an existing encrypted database.

### HTTPS readiness succeeds, login fails

The application and database are reachable, so investigate the authentication path.

Possible causes include:

- User does not exist in this database
- Account is inactive
- Password is incorrect
- Account is temporarily locked
- MFA cannot be completed
- Browser cookies are blocked
- Session or CSRF behavior is failing
- Client and server clocks are incorrect
- Browser is using the wrong CareQueue installation
- Frontend build or origin configuration is incorrect

Review authentication audit events when appropriate.

### Login succeeds, protected application shows governance setup

This is expected when the current organization governance attestation is incomplete.

An Admin must complete the current attestation before normal protected application functionality becomes available.

Non-Admin users cannot accept the organization-level governance attestation.

This state is not a health-check failure.

### HTTPS readiness succeeds, frontend is blank

Likely areas to investigate:

- Missing or invalid frontend build
- Static asset failure
- Caddy static-root configuration
- Browser-side JavaScript error
- Browser cache containing obsolete assets

Review browser developer tools and Caddy logs.

### Setup status says setup is complete

If the initial Admin setup utility reports that setup is already complete, at least one user exists in the active production database.

Confirm that the installation is using the expected database.

Do not delete runtime data or generate replacement encryption keys merely to reopen first-time setup.

## Connection Refused on Windows

### Port 8000

Check whether anything is listening:

```powershell
Get-NetTCPConnection `
    -LocalPort 8000 `
    -State Listen `
    -ErrorAction SilentlyContinue
```

Identify the process:

```powershell
$connection = Get-NetTCPConnection `
    -LocalPort 8000 `
    -State Listen `
    -ErrorAction SilentlyContinue |
Select-Object -First 1

if ($connection) {
    Get-Process -Id $connection.OwningProcess
}
```

The packaged API should listen only on loopback.

### Port 443

Check:

```powershell
Get-NetTCPConnection `
    -LocalPort 443 `
    -State Listen `
    -ErrorAction SilentlyContinue
```

Possible conflicts include:

- IIS
- Apache
- Nginx
- Another Caddy instance
- Other local HTTPS software

Do not stop unrelated production software without confirming ownership of the port.

## Connection Refused on Linux

Check listeners:

```bash
sudo ss -lntp
```

The expected CareQueue API listener is:

```text
127.0.0.1:8000
```

The HTTPS listener should be provided by the CareQueue Caddy service.

Check service state before changing firewall or Caddy configuration.

## Windows Certificate Error

Check whether the packaged Caddy root certificate exists:

```powershell
Test-Path `
    "C:\ProgramData\CareQueue\Caddy\Data\caddy\pki\authorities\local\root.crt"
```

If the certificate exists but is not trusted, review the installer log and certificate store.

For approved administrative recovery, the local root certificate can be imported with:

```powershell
Import-Certificate `
    -FilePath (
        "C:\ProgramData\CareQueue\Caddy\Data\caddy\" +
        "pki\authorities\local\root.crt"
    ) `
    -CertStoreLocation "Cert:\LocalMachine\Root"
```

Confirm the certificate path and deployment state before importing it.

Do not bypass certificate validation as a normal operating method.

## Linux Certificate Error

The Linux installer establishes trust for the Caddy internal root certificate as part of the packaged installation workflow.

If HTTPS certificate validation fails:

1. Confirm `carequeue-caddy.service` is running.
2. Review the Linux installer log.
3. Confirm the Caddy internal root certificate exists.
4. Confirm it has been installed into the system trust store.
5. Refresh the trust store using the distribution's approved process if necessary.
6. Retest HTTPS without disabling certificate validation.

A browser on another client computer also needs appropriate trust for the private certificate authority.

## Hostname Resolution

Check Windows:

```powershell
ping carequeue.local
```

Check Linux:

```bash
getent hosts carequeue.local
```

For the default packaged private installation, the hostname should resolve to the intended private CareQueue host.

On a single-machine installation this is normally the local system.

Windows local-hostname configuration is stored in:

```text
C:\Windows\System32\drivers\etc\hosts
```

Linux local-hostname configuration uses:

```text
/etc/hosts
```

Do not add duplicate or conflicting hostname entries.

A broader restricted-network deployment should use an approved DNS design rather than ad hoc hosts-file changes on multiple systems.

## Reverse Proxy Failure

When direct API checks work but HTTPS checks do not:

- Confirm the Caddy service is running.
- Test direct liveness and readiness.
- Review Caddy logs.
- Confirm the packaged proxy target remains `127.0.0.1:8000`.
- Confirm no unexpected process owns the required port.
- Confirm hostname resolution.
- Confirm certificate trust.
- Confirm the installed Caddy configuration matches the intended release.

## Database Readiness Failure

When readiness fails:

1. Review API logs.
2. Confirm the configured database file exists.
3. Confirm the SQLCipher key belongs to that database.
4. Confirm the configured database-encryption mode is correct.
5. Confirm the service identity can access the required directories and database.
6. Confirm the database is not locked by an unexpected process.
7. Confirm no incomplete recovery or migration requires investigation.
8. Confirm the production environment file contains the expected trusted paths.
9. Compare the failure with recent upgrade, restore, or configuration changes.

Do not:

- Generate new production encryption keys for an existing database.
- Replace the database with an unverified backup.
- Broaden filesystem permissions without understanding the cause.
- Disable SQLCipher to make readiness pass.

## Windows Logs

API service and wrapper logs are stored under the configured CareQueue logging paths in:

```text
C:\ProgramData\CareQueue
```

Installer logs are stored under:

```text
C:\ProgramData\CareQueue\Logs\Installer
```

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

Review the log:

```powershell
Get-Content `
    -LiteralPath $latestLog.FullName `
    -Tail 240
```

Review logs for sensitive environment or host details before sharing them.

## Linux Logs

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

Installer logs:

```text
/var/log/carequeue/installer/
```

## Active Ports Summary

Windows:

```powershell
Get-NetTCPConnection `
    -State Listen |
Where-Object {
    $_.LocalPort -in 443, 8000
} |
Select-Object `
    LocalAddress,
    LocalPort,
    OwningProcess
```

Linux:

```bash
sudo ss -lntp
```

For the packaged deployment, FastAPI should not be exposed as a general network listener.

## Post-Installation Smoke Test

After a fresh packaged installation:

1. Confirm the API and Caddy services are running.
2. Confirm backup scheduling is enabled.
3. Check direct liveness.
4. Check direct readiness.
5. Check HTTPS liveness.
6. Check HTTPS readiness.
7. Complete first-time Admin setup if no users exist.
8. Open `https://carequeue.local`.
9. Sign in as the first Admin.
10. Complete the current governance attestation.
11. Confirm the dashboard loads.
12. Confirm the authorization queue loads.
13. Create or review a synthetic authorization record.
14. Confirm logout succeeds.
15. Sign in again.
16. Confirm governance is not requested again for the same current attestation version.
17. Create or run a manual encrypted backup.
18. Verify the backup through the supported verification workflow.

For release validation, also test MFA, remembered-device behavior, session inactivity, and reboot persistence when those controls are part of the release scope.

## Post-Upgrade Smoke Test

After an upgrade:

1. Confirm required services are running.
2. Confirm backup scheduling remains enabled.
3. Check HTTPS liveness.
4. Check HTTPS readiness.
5. Open the frontend.
6. Sign in with an approved account.
7. Confirm governance status is appropriate for the installed governance version.
8. Confirm the Admin System page reports the expected CareQueue application version.
9. Verify representative protected pages.
10. Confirm existing authorization data remains available.
11. Confirm governance history remains available to an Admin.
12. Confirm logout and subsequent login work.
13. Review installer and service logs for unexpected errors.

A new CareQueue application version does not automatically require a new governance attestation version or governance document revision. Governance acceptance remains current only while both required governance values match the accepted record.

## Post-Repair Smoke Test

After repair:

1. Confirm required services are running.
2. Confirm backup scheduling remains enabled.
3. Check HTTPS liveness.
4. Check HTTPS readiness.
5. Open the frontend.
6. Sign in.
7. Verify representative protected pages.
8. Confirm existing data remains present.
9. Confirm governance history remains present.
10. Sign out.

Repair should restore packaged application and service components without replacing production data or encryption keys.

## Post-Reboot Smoke Test

After validating a new packaged installation on a clean system, reboot the host.

After reboot:

1. Confirm API service auto-start.
2. Confirm Caddy service auto-start.
3. Confirm the backup schedule remains enabled.
4. Check HTTPS readiness.
5. Open the frontend.
6. Sign in.
7. Confirm protected application access.
8. Confirm the expected application version.

Reboot validation is particularly important for release testing because installation success does not prove service persistence across restart.

## Security-Sensitive Functional Checks

Health endpoints are not sufficient for security-sensitive releases.

When a release changes authentication, sessions, governance, encryption, or deployment behavior, add targeted manual checks such as:

- Initial Admin bootstrap
- Governance enforcement
- Governance history
- Password change
- TOTP MFA enrollment
- TOTP login
- Remembered-device login
- Remembered-device revocation
- Single-session invalidation
- Inactivity timeout
- Session renewal
- Cross-tab logout
- Admin role restrictions
- Audit integrity verification
- Backup creation
- Backup verification
- Certificate trust
- Same-origin production requests

Use only synthetic or approved non-production data in release-validation environments.

## What Health Checks Do Not Prove

A successful liveness or readiness response does not prove:

- The user interface renders correctly.
- Login works.
- MFA works.
- Session expiration works.
- Governance has been accepted.
- Role enforcement is correct.
- PDF intake works.
- Authorization writes work.
- Audit events are complete.
- Audit integrity verification passes.
- Backups are recent.
- Backups can be restored.
- Certificate trust works from every approved client.
- Firewall policy is correct.
- The host is patched.
- Endpoint protection is healthy.
- Required agreements are executed.
- Organizational access reviews are current.
- The deployment is HIPAA compliant.

Health checks are one layer of operational validation.

## Suggested Monitoring Use

For automated service monitoring:

- Use `/api/health/live` to determine whether the API process responds.
- Use `/api/health/ready` to determine whether the API can access the configured database.
- Use the HTTPS endpoint when the monitoring goal includes Caddy, certificate trust, and the user-facing request path.
- Use direct loopback checks only when isolating backend behavior or when the monitor runs locally by design.

Do not build automated monitoring that records response bodies containing sensitive application data.

The current health responses contain only bounded status information.

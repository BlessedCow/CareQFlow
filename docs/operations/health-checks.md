# Health Checks

CareQueue exposes liveness and readiness endpoints for operational validation.

Use them for:

- Manual administrator checks
- Windows service validation
- Reverse-proxy validation
- Deployment smoke tests
- Upgrade verification
- Recovery verification
- Monitoring integrations

Health checks do not replace login testing or representative workflow testing.

## Endpoints

CareQueue exposes:

```text
/api/health
/api/health/live
/api/health/ready
```

The primary operational endpoints are:

```text
/api/health/live
/api/health/ready
```

## Liveness

Endpoint:

```text
GET /api/health/live
```

Liveness answers:

```text
Is the API process running and able to respond?
```

A successful response includes:

```json
{
  "status": "ok",
  "app": "AuthStatus API",
  "version": "0.1.0"
}
```

The version may change.

Liveness does not prove:

- Database access
- Login
- Caddy operation
- Certificate trust
- Backup operation
- Browser workflow correctness

## Readiness

Endpoint:

```text
GET /api/health/ready
```

Readiness answers:

```text
Can the API query the configured database?
```

Use readiness for:

- Post-installation validation
- Post-upgrade validation
- Post-recovery validation
- Monitoring application availability
- Confirming database access

A successful readiness response still does not prove that every application workflow is functioning.

## General Health Endpoint

Endpoint:

```text
GET /api/health
```

Use the explicit liveness and readiness endpoints for operational checks because their meanings are clearer.

## Authentication and Safety

Health endpoints are intended to be callable without an authenticated session.

Their responses must not expose:

- Database paths
- Encryption keys
- Environment values
- User information
- Session state
- Internal SQL errors
- Stack traces
- Backup filenames
- Host credentials

## Windows Production

A private Windows deployment normally uses:

```text
https://carequeue.local
```

The API listens on:

```text
127.0.0.1:8000
```

Caddy terminates HTTPS and proxies `/api`.

## Check Services

Run PowerShell as Administrator:

```powershell
Get-Service -Name "CareQueueApi", "CareQueueCaddy"
```

A service can report `Running` while the application is not ready, so always continue with endpoint checks.

## Direct API Liveness

```powershell
Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/api/health/live"
```

This bypasses Caddy.

Use it to separate API failures from HTTPS, certificate, or proxy failures.

## Direct API Readiness

```powershell
Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/api/health/ready"
```

When liveness succeeds but readiness fails, investigate the database and production configuration.

## HTTPS Liveness

```powershell
Invoke-RestMethod `
    -Uri "https://carequeue.local/api/health/live"
```

This validates:

- Hostname resolution
- Port 443
- Caddy
- Certificate trust
- Reverse proxy
- API response

## HTTPS Readiness

```powershell
Invoke-RestMethod `
    -Uri "https://carequeue.local/api/health/ready"
```

This is the preferred Windows production smoke test because it validates the full request path and database readiness.

## Frontend Check

Open:

```text
https://carequeue.local
```

Confirm:

- The certificate is trusted
- The login page loads
- Static assets load
- The browser does not call `localhost:8000`

Production API requests should use:

```text
https://carequeue.local/api/...
```

## Local Development

Backend:

```text
http://127.0.0.1:8000
```

Frontend:

```text
http://localhost:5173
```

Development liveness:

```powershell
Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/api/health/live"
```

Development readiness:

```powershell
Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/api/health/ready"
```

## Linux

Direct API liveness:

```bash
curl \
  --fail \
  --silent \
  --show-error \
  http://127.0.0.1:8000/api/health/live
```

Direct API readiness:

```bash
curl \
  --fail \
  --silent \
  --show-error \
  http://127.0.0.1:8000/api/health/ready
```

HTTPS readiness:

```bash
curl \
  --fail \
  --silent \
  --show-error \
  https://carequeue.example.com/api/health/ready
```

Replace the hostname with the actual deployment origin.

## Interpreting Results

### Direct liveness succeeds, HTTPS fails

Likely causes:

- Caddy stopped
- Invalid Caddy configuration
- Certificate trust failure
- Hostname resolution failure
- Port 443 conflict

### Direct liveness fails

Likely causes:

- API service stopped
- Uvicorn startup failure
- Port 8000 conflict
- Installed backend failure
- Production configuration failure

### Liveness succeeds, readiness fails

Likely causes:

- Wrong database path
- Wrong SQLCipher key
- Wrong database mode
- Database lock
- Runtime permission failure
- Database corruption
- Schema initialization failure

### HTTPS readiness succeeds, login fails

Likely causes:

- User does not exist in this database
- Account is inactive
- Password is wrong
- Cookies are blocked
- Frontend build uses the wrong API origin
- Session behavior is failing

### Health succeeds, frontend is blank

Likely causes:

- Missing or invalid frontend build
- Browser-side JavaScript error
- Static asset failure
- Caddy static-root problem

## Connection Refused

### Port 8000

Check:

```powershell
Get-NetTCPConnection `
    -LocalPort 8000 `
    -State Listen `
    -ErrorAction SilentlyContinue
```

Identify the process:

```powershell
Get-Process `
    -Id (
        Get-NetTCPConnection `
            -LocalPort 8000 `
            -State Listen
    ).OwningProcess
```

### Port 443

Check:

```powershell
Get-NetTCPConnection `
    -LocalPort 443 `
    -State Listen `
    -ErrorAction SilentlyContinue
```

Possible conflicts include IIS, Apache, Nginx, another Caddy instance, or endpoint-security software.

## Certificate Error

Check for the local Caddy root certificate:

```powershell
Test-Path `
    "C:\ProgramData\CareQueue\Caddy\Data\caddy\pki\authorities\local\root.crt"
```

Import it when needed:

```powershell
Import-Certificate `
    -FilePath (
        "C:\ProgramData\CareQueue\Caddy\Data\caddy\" +
        "pki\authorities\local\root.crt"
    ) `
    -CertStoreLocation "Cert:\LocalMachine\Root"
```

Do not bypass certificate validation as a normal operating method.

## Hostname Resolution

Check:

```powershell
ping carequeue.local
```

For a single-machine private deployment, it should resolve to:

```text
127.0.0.1
```

Review:

```text
C:\Windows\System32\drivers\etc\hosts
```

Expected entry:

```text
127.0.0.1 carequeue.local
```

For a restricted-network deployment, verify internal DNS instead.

## Reverse Proxy Failure

When Caddy responds but cannot reach the API:

- Check `CareQueueApi`
- Test direct liveness
- Review Caddy logs
- Confirm the proxy target is `127.0.0.1:8000`
- Confirm no other process owns port 8000

## Database Readiness Failure

When readiness fails:

1. Review API logs.
2. Confirm the database file exists.
3. Confirm the SQLCipher key belongs to that database.
4. Confirm the configured database mode is correct.
5. Confirm the service identity can access the runtime directory.
6. Confirm the database is not locked.
7. Confirm no incomplete recovery is pending.

Do not generate new keys for an existing database.

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
sudo ss \
  -lntp
```

## Post-Installation Smoke Test

After first installation:

1. Confirm both services are running.
2. Check direct liveness.
3. Check direct readiness.
4. Check HTTPS liveness.
5. Check HTTPS readiness.
6. Open the frontend.
7. Create the first production user.
8. Sign in.
9. Verify the dashboard loads.
10. Sign out.
11. Run a manual encrypted backup.

## Post-Upgrade Smoke Test

After an upgrade:

1. Confirm the services returned to their expected states.
2. Check HTTPS liveness.
3. Check HTTPS readiness.
4. Open the frontend.
5. Sign in.
6. Load the dashboard.
7. Load the authorization queue.
8. Load registered options.
9. Review the Audit Log as Admin.
10. Sign out and sign in again.
11. Run a post-upgrade encrypted backup.

Do not accept the upgrade based only on service status.

## Post-Recovery Smoke Test

After recovery activation:

1. Confirm the active database exists.
2. Confirm the rollback database exists.
3. Confirm the safety backup exists.
4. Start the API.
5. Check direct readiness.
6. Start Caddy.
7. Check HTTPS readiness.
8. Sign in.
9. Review representative records.
10. Review timeline events.
11. Review registered options.
12. Review audit continuity.
13. Keep rollback and safety backups until acceptance.

## Monitoring

Use:

```text
/api/health/ready
```

for application availability monitoring.

Use liveness separately to distinguish:

```text
Process down
```

from:

```text
Process running but database unavailable
```

Monitoring should:

- Use HTTPS for the user-facing endpoint
- Avoid sending credentials
- Avoid logging sensitive response content
- Alert on repeated failure
- Record timestamps and target origin
- Distinguish liveness from readiness

CareQueue does not currently ship with an external monitoring service.

## PowerShell Smoke-Test Block

```powershell
$checks = @(
    @{
        Name = "Direct API liveness"
        Uri = "http://127.0.0.1:8000/api/health/live"
    },
    @{
        Name = "Direct API readiness"
        Uri = "http://127.0.0.1:8000/api/health/ready"
    },
    @{
        Name = "HTTPS liveness"
        Uri = "https://carequeue.local/api/health/live"
    },
    @{
        Name = "HTTPS readiness"
        Uri = "https://carequeue.local/api/health/ready"
    }
)

foreach ($check in $checks) {
    try {
        $response = Invoke-RestMethod `
            -Uri $check.Uri `
            -TimeoutSec 10

        [PSCustomObject]@{
            Check = $check.Name
            Result = "PASS"
            Status = $response.status
        }
    }
    catch {
        [PSCustomObject]@{
            Check = $check.Name
            Result = "FAIL"
            Status = $_.Exception.Message
        }
    }
}
```

This checks only health endpoints. It does not authenticate or validate protected workflows.

## Safe Health Logging

Health monitoring may record:

- Timestamp
- Target endpoint
- Success or failure
- HTTP status
- Response time
- Safe application status

Do not log:

- Cookies
- Authorization headers
- Session tokens
- CSRF tokens
- Environment values
- Encryption keys
- Sensitive stack traces

## Manual Browser Validation

After health checks pass, confirm:

- Login page renders
- Login works
- Role-appropriate navigation appears
- Dashboard loads
- Authorization queue loads
- Settings loads
- Logout works

Health endpoints are intentionally narrow.

## Troubleshooting Order

Use this order:

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

This isolates the failure from the backend outward.

## Healthy Windows Production Checklist

A healthy private Windows instance should have:

- `CareQueueApi` in the expected state
- `CareQueueCaddy` in the expected state
- Port 8000 bound to loopback
- Port 443 listening through Caddy
- `carequeue.local` resolving correctly
- Trusted local certificate
- Direct liveness passing
- Direct readiness passing
- HTTPS liveness passing
- HTTPS readiness passing
- Frontend loading
- Login succeeding
- Protected workflows loading
- Encrypted backup succeeding

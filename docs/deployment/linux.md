# Linux Deployment

CareQueue includes an initial Linux deployment foundation, but the Linux path is not yet as complete as the Windows deployment.

The repository currently provides:

```text
deployment/linux/
├── Caddyfile
└── systemd/
    ├── carequeue-backup.service
    └── carequeue-backup.timer
```

These files cover:

- Serving the built frontend through Caddy
- Proxying `/api` requests to FastAPI on `127.0.0.1:8000`
- Running encrypted backups through a hardened systemd service
- Scheduling daily backups through a systemd timer

The repository does not yet include a complete Linux production installer or a systemd unit for the CareQueue API. Those pieces must be created and tested before the Linux deployment can be considered equivalent to the Windows deployment.

This guide documents the intended layout, the files that already exist, and the remaining manual work.

CareQueue is intended for private or controlled deployment. The configuration in this guide is not a complete public internet or compliance program.

## Current Linux Status

Implemented in the repository:

- Production Caddyfile
- Same-origin `/api` reverse proxy
- Static frontend serving with SPA fallback
- Security response headers
- Encrypted backup systemd service
- Daily backup systemd timer
- Basic systemd sandboxing for the backup process

Not yet included as a complete repository workflow:

- Linux production installer
- CareQueue API systemd service
- Runtime directory creation script
- Service-account creation script
- Environment-file installation script
- API service hardening policy
- Automated application upgrades
- Automated rollback workflow
- Caddy installation automation
- Certificate trust workflow for private local certificates
- Full Linux production smoke-test tooling
- Distribution-specific validation

Treat this document as an operator guide for the current foundation, not as proof that Linux deployment is fully complete.

## Intended Architecture

The intended request flow is:

```text
Browser
  |
  | HTTPS
  v
Caddy
  |\
  | \__ Serves /opt/carequeue/frontend/dist
  |
  \____ Proxies /api to 127.0.0.1:8000
           |
           v
       CareQueue API
           |
           v
       SQLCipher database
```

The API should bind only to:

```text
127.0.0.1:8000
```

Caddy should be the only process exposed to users.

## Recommended Filesystem Layout

The existing Linux files assume this application layout:

```text
/opt/carequeue
```

Recommended contents:

```text
/opt/carequeue/
├── backend/
│   ├── authstatus_api/
│   ├── scripts/
│   ├── requirements.txt
│   └── .venv/
├── frontend/
│   └── dist/
├── deployment/
│   └── linux/
└── docs/
```

Recommended runtime layout:

```text
/var/lib/carequeue/
├── backups/
├── data/
├── recovery/
└── restores/
```

Recommended configuration location:

```text
/etc/carequeue/carequeue.env
```

Recommended log location:

```text
/var/log/carequeue/
```

Caddy may use its distribution default storage and logging locations unless the deployment chooses explicit paths.

## Recommended Service Account

Use a dedicated system account:

```text
carequeue
```

The account should:

- Have no interactive login shell
- Own the CareQueue runtime directories
- Read the production environment file
- Read and write the active database
- Write backups
- Execute the installed Python environment
- Avoid unnecessary access outside CareQueue paths

Example account creation:

```bash
sudo useradd \
  --system \
  --home /var/lib/carequeue \
  --create-home \
  --shell /usr/sbin/nologin \
  carequeue
```

Some distributions use a different path for `nologin`.

Check before running:

```bash
command -v nologin
```

Do not reuse an ordinary administrator account as the long-running application identity.

## Create Runtime Directories

Create the recommended directories:

```bash
sudo install \
  -d \
  -o carequeue \
  -g carequeue \
  -m 0750 \
  /var/lib/carequeue
```

```bash
sudo install \
  -d \
  -o carequeue \
  -g carequeue \
  -m 0750 \
  /var/lib/carequeue/data
```

```bash
sudo install \
  -d \
  -o carequeue \
  -g carequeue \
  -m 0750 \
  /var/lib/carequeue/backups
```

```bash
sudo install \
  -d \
  -o carequeue \
  -g carequeue \
  -m 0750 \
  /var/lib/carequeue/restores
```

```bash
sudo install \
  -d \
  -o carequeue \
  -g carequeue \
  -m 0750 \
  /var/lib/carequeue/recovery
```

Create the configuration directory:

```bash
sudo install \
  -d \
  -o root \
  -g carequeue \
  -m 0750 \
  /etc/carequeue
```

Create the application directory:

```bash
sudo install \
  -d \
  -o root \
  -g carequeue \
  -m 0750 \
  /opt/carequeue
```

## Install Application Files

Copy a reviewed CareQueue source tree into:

```text
/opt/carequeue
```

The exact copy mechanism depends on the release process.

Examples include:

- A versioned release archive
- A deployment package
- A reviewed repository checkout
- A configuration-management system

Do not copy:

- Development databases
- Local `.env` files
- Real intake PDFs
- Local backup directories
- Test artifacts
- Development screenshots
- `node_modules`
- Development virtual environments

After copying, review:

```bash
sudo find /opt/carequeue \
  -maxdepth 2 \
  -type f \
  | sort
```

## Python Environment

Create the production virtual environment:

```bash
sudo -u carequeue \
  python3 \
  -m venv \
  /opt/carequeue/backend/.venv
```

Upgrade pip:

```bash
sudo -u carequeue \
  /opt/carequeue/backend/.venv/bin/python \
  -m pip install \
  --upgrade pip
```

Install backend requirements:

```bash
sudo -u carequeue \
  /opt/carequeue/backend/.venv/bin/python \
  -m pip install \
  -r /opt/carequeue/backend/requirements.txt
```

Confirm the installed interpreter:

```bash
sudo -u carequeue \
  /opt/carequeue/backend/.venv/bin/python \
  --version
```

Confirm the application imports:

```bash
sudo -u carequeue \
  /opt/carequeue/backend/.venv/bin/python \
  -c "import authstatus_api.main; import uvicorn; print('CareQueue backend import succeeded.')"
```

This import check requires valid production environment variables.

## Build the Frontend

Build from the frontend source:

```bash
cd /opt/carequeue/frontend
sudo -u carequeue npm ci
sudo -u carequeue npm run build
```

The built frontend should exist at:

```text
/opt/carequeue/frontend/dist
```

Confirm:

```bash
test -f /opt/carequeue/frontend/dist/index.html
```

The Linux Caddyfile expects that exact path.

Production builds should use same-origin API requests.

Do not build the frontend with:

```env
VITE_AUTHSTATUS_API_BASE_URL=http://localhost:8000
```

A production browser should call:

```text
https://<carequeue-hostname>/api/...
```

not the API port directly.

## Production Environment File

Create:

```text
/etc/carequeue/carequeue.env
```

Use the root `.env.example` only as a starting reference.

The production environment should include independent keys for:

```text
AUTHSTATUS_ENCRYPTION_KEY
AUTHSTATUS_SQLCIPHER_KEY
AUTHSTATUS_BACKUP_ENCRYPTION_KEY
```

Recommended production behavior includes:

```env
AUTHSTATUS_APP_ENVIRONMENT=production
AUTHSTATUS_DATABASE_ENCRYPTION=sqlcipher
AUTHSTATUS_SESSION_COOKIE_SECURE=true
```

Recommended paths:

```env
AUTHSTATUS_DATABASE_PATH=/var/lib/carequeue/data/carequeue.db
AUTHSTATUS_BACKUP_DIRECTORY=/var/lib/carequeue/backups
AUTHSTATUS_RESTORE_DIRECTORY=/var/lib/carequeue/restores
AUTHSTATUS_RECOVERY_DIRECTORY=/var/lib/carequeue/recovery
```

Set CORS to the exact HTTPS application origin:

```env
AUTHSTATUS_CORS_ORIGINS=["https://carequeue.example.com"]
```

For an approved private internal hostname:

```env
AUTHSTATUS_CORS_ORIGINS=["https://carequeue.internal.example"]
```

Do not use development origins in production.

## Environment File Permissions

Set ownership:

```bash
sudo chown root:carequeue \
  /etc/carequeue/carequeue.env
```

Set permissions:

```bash
sudo chmod 0640 \
  /etc/carequeue/carequeue.env
```

Confirm:

```bash
sudo stat \
  /etc/carequeue/carequeue.env
```

Do not print the file contents into logs, tickets, screenshots, or documentation.

## Generate Production Keys

Generate independent keys through an approved local process.

The exact commands may vary by the project utilities available in the current source tree.

Requirements:

- Each key must be independently generated.
- Keys must have sufficient entropy.
- Keys must be stored outside the repository.
- Recoverable copies must exist through an approved key-custody process.
- Backup keys must remain separate from backup files.

Do not reuse development keys in production.

## Database Mode

A production deployment containing sensitive data should use:

```env
AUTHSTATUS_DATABASE_ENCRYPTION=sqlcipher
```

The installed Python environment must include a working SQLCipher-compatible package.

Validate SQLCipher behavior before using real data.

A successful application import is not proof that the resulting database file is encrypted.

Use the project verification tooling and confirm plaintext SQLite cannot read the database.

## Current Caddyfile

The repository file is:

```text
deployment/linux/Caddyfile
```

It currently expects:

```text
carequeue.example.com
```

Replace that placeholder with the approved production hostname.

The current file:

- Enables `zstd` and `gzip`
- Adds security response headers
- Removes the `Server` header
- Proxies `/api` and `/api/*` to `127.0.0.1:8000`
- Serves the frontend from `/opt/carequeue/frontend/dist`
- Uses `/index.html` as the SPA fallback

## Install the Linux Caddyfile

Copy the file to the Caddy configuration location used by the distribution.

A common location is:

```text
/etc/caddy/Caddyfile
```

Example:

```bash
sudo cp \
  /opt/carequeue/deployment/linux/Caddyfile \
  /etc/caddy/Caddyfile
```

Edit the hostname:

```bash
sudo editor /etc/caddy/Caddyfile
```

Do not leave:

```text
carequeue.example.com
```

in a real deployment.

## Validate Caddy

Format the file:

```bash
sudo caddy fmt \
  --overwrite \
  /etc/caddy/Caddyfile
```

Validate it:

```bash
sudo caddy validate \
  --config /etc/caddy/Caddyfile \
  --adapter caddyfile
```

Expected final output includes:

```text
Valid configuration
```

Do not restart Caddy until validation succeeds.

## Start or Reload Caddy

The exact service name depends on the distribution package.

Common commands:

```bash
sudo systemctl enable --now caddy
```

After configuration changes:

```bash
sudo systemctl reload caddy
```

Check status:

```bash
sudo systemctl status caddy
```

Review logs:

```bash
sudo journalctl \
  -u caddy \
  --since today
```

## Public Certificate Mode

For a public DNS hostname, Caddy can normally request and renew a publicly trusted certificate when:

- DNS points to the server
- Required ports are reachable
- The hostname is valid
- Firewall rules allow Caddy
- No other service owns the required ports

The current repository Caddyfile assumes normal automatic HTTPS behavior.

A public deployment requires additional review and is outside the fully validated CareQueue deployment path.

## Private Certificate Mode

For a private hostname that cannot receive a public certificate, use an approved internal certificate strategy.

Options may include:

- Caddy’s internal certificate authority
- An organization-managed internal CA
- A certificate issued by an approved private PKI

Do not simply disable certificate validation in browsers or clients.

When using a private CA:

- Distribute the root certificate through an approved process.
- Trust it only on approved systems.
- Document renewal and replacement.
- Restrict private key access.
- Remove trust when the deployment is retired.

The current Linux Caddyfile does not include a private-CA directive. Add one only after reviewing the intended hostname and trust model.

## CareQueue API Service

The current repository does not include a Linux systemd unit for the API.

Until one is added and tested, create a reviewed unit outside the repository or run the API through an approved process manager.

A suitable future service should:

- Use `User=carequeue`
- Use `Group=carequeue`
- Set `WorkingDirectory=/opt/carequeue/backend`
- Load `/etc/carequeue/carequeue.env`
- Run the installed virtual environment
- Bind Uvicorn to `127.0.0.1:8000`
- Trust proxy headers only from loopback
- Restart after unexpected failure
- Use systemd sandboxing
- Allow writes only to required runtime paths
- Start before Caddy serves traffic
- Stop cleanly before upgrades or recovery

Do not expose Uvicorn directly on:

```text
0.0.0.0
```

without a separately reviewed network architecture.

## Temporary Manual API Start

For controlled validation only:

```bash
cd /opt/carequeue/backend
```

Load the environment:

```bash
set -a
source /etc/carequeue/carequeue.env
set +a
```

Start Uvicorn:

```bash
sudo -u carequeue \
  /opt/carequeue/backend/.venv/bin/uvicorn \
  authstatus_api.main:create_app \
  --factory \
  --host 127.0.0.1 \
  --port 8000 \
  --proxy-headers \
  --forwarded-allow-ips 127.0.0.1 \
  --no-access-log
```

This terminal process is not a durable production service.

Use it only to validate the application before a proper service unit is installed.

## Test the API Directly

From the server:

```bash
curl \
  --fail \
  --silent \
  --show-error \
  http://127.0.0.1:8000/api/health/live
```

Check readiness:

```bash
curl \
  --fail \
  --silent \
  --show-error \
  http://127.0.0.1:8000/api/health/ready
```

The API should not be reachable from unapproved remote systems.

## Test Through HTTPS

After Caddy and the API are running:

```bash
curl \
  --fail \
  --silent \
  --show-error \
  https://carequeue.example.com/api/health/live
```

Replace the hostname with the actual deployment origin.

Check readiness:

```bash
curl \
  --fail \
  --silent \
  --show-error \
  https://carequeue.example.com/api/health/ready
```

Open the frontend in a browser and confirm:

- The certificate is trusted
- The login page loads
- API calls use the HTTPS origin
- No browser request goes directly to `127.0.0.1:8000`
- No browser request uses the development frontend server

## Create the First User

Load the production environment in a controlled administrator shell:

```bash
set -a
source /etc/carequeue/carequeue.env
set +a
```

Run:

```bash
sudo -u carequeue \
  /opt/carequeue/backend/.venv/bin/python \
  /opt/carequeue/backend/scripts/create_user.py \
  --username carequeue.admin \
  --role Admin
```

The script prompts for the password.

Do not pass passwords on the command line.

Available roles:

```text
Admin
UR
Read Only
```

## Encrypted Backup Service

The repository includes:

```text
deployment/linux/systemd/carequeue-backup.service
```

The service is a one-shot task.

It runs:

```text
/opt/carequeue/backend/.venv/bin/python
/opt/carequeue/backend/scripts/create_encrypted_backup.py
```

with:

```text
--backup-directory /var/lib/carequeue/backups
```

It loads:

```text
/etc/carequeue/carequeue.env
```

## Backup Service Hardening

The current backup service includes:

```ini
PrivateTmp=true
NoNewPrivileges=true
ProtectHome=true
ProtectSystem=strict
ReadWritePaths=/var/lib/carequeue/backups
UMask=0077
```

These settings:

- Create a private temporary directory
- Prevent privilege escalation
- Restrict home-directory visibility
- Make most of the filesystem read-only
- Permit writes only to the backup directory
- Create files with restrictive default permissions

The service still needs read access to:

- `/opt/carequeue`
- `/etc/carequeue/carequeue.env`
- The configured active database
- Required shared libraries

Validate the unit against the actual database path and distribution.

## Backup Service Limitation

The current service allows writes only to:

```text
/var/lib/carequeue/backups
```

This is appropriate when:

- Temporary backup work uses permitted temporary storage
- The active database is read-only to the backup process
- No other restore or recovery directory is needed

If the backup implementation requires another writable path, update `ReadWritePaths` narrowly.

Do not remove `ProtectSystem=strict` merely to make the service work.

## Install the Backup Units

Copy the service:

```bash
sudo cp \
  /opt/carequeue/deployment/linux/systemd/carequeue-backup.service \
  /etc/systemd/system/
```

Copy the timer:

```bash
sudo cp \
  /opt/carequeue/deployment/linux/systemd/carequeue-backup.timer \
  /etc/systemd/system/
```

Reload systemd:

```bash
sudo systemctl daemon-reload
```

## Validate the Backup Units

Run:

```bash
systemd-analyze verify \
  /etc/systemd/system/carequeue-backup.service \
  /etc/systemd/system/carequeue-backup.timer
```

Resolve errors before enabling the timer.

## Run a Manual Backup

Start the service:

```bash
sudo systemctl start carequeue-backup.service
```

Check status:

```bash
sudo systemctl status carequeue-backup.service
```

A successful one-shot service may show:

```text
inactive (dead)
```

after completion.

That is normal when the result is successful.

Review logs:

```bash
sudo journalctl \
  -u carequeue-backup.service \
  --since today
```

Confirm a backup exists:

```bash
sudo find \
  /var/lib/carequeue/backups \
  -maxdepth 1 \
  -type f \
  -name "*.db.enc" \
  -printf "%TY-%Tm-%Td %TH:%TM:%TS %s %f\n"
```

Confirm the latest backup is nonempty.

## Enable the Backup Timer

Enable and start:

```bash
sudo systemctl enable --now carequeue-backup.timer
```

Check status:

```bash
sudo systemctl status carequeue-backup.timer
```

List the next run:

```bash
systemctl list-timers carequeue-backup.timer
```

The current timer uses:

```ini
OnCalendar=*-*-* 02:00:00
RandomizedDelaySec=15m
Persistent=true
```

This means:

- The timer runs daily around 2:00 AM.
- systemd may delay it by up to 15 minutes.
- A missed run may execute after the system returns.

## Disable the Backup Timer

Run:

```bash
sudo systemctl disable --now carequeue-backup.timer
```

Disabling the timer does not delete existing backups.

## Backup Verification

A successful systemd result is not enough.

Confirm:

- A recent `.db.enc` file exists
- The file is nonempty
- The backup creation output reported verification
- Retention completed or reported a reviewed warning
- A staged restore test has been performed on schedule

See [Backup and Recovery](../workflows/backup-and-recovery.md).

## File Permissions

Review runtime ownership:

```bash
sudo find \
  /var/lib/carequeue \
  -maxdepth 2 \
  -printf "%M %u %g %p\n"
```

Recommended general pattern:

```text
Directories: 0750
Environment file: 0640
Backup files: 0600
Database files: 0600 or similarly restricted
```

Exact permissions depend on the service and administrator access model.

Do not make runtime storage world-readable or world-writable.

## Firewall

A private reverse-proxy deployment normally exposes only the approved HTTPS port.

The API port should remain loopback-only.

Review listening sockets:

```bash
sudo ss \
  -lntp
```

Expected pattern:

```text
127.0.0.1:8000
0.0.0.0:443 or approved interface:443
```

Port 80 may be used by Caddy for redirects or certificate challenges depending on the certificate strategy.

Apply firewall rules through the distribution’s approved firewall tool.

Do not expose SSH, database files, backup storage, or the Uvicorn port more broadly than required.

## Logs

### Caddy

Review:

```bash
sudo journalctl \
  -u caddy \
  --since today
```

### API

The API log location depends on the service unit or process manager used.

A future CareQueue API systemd unit should write to the journal or to a restricted CareQueue log directory.

### Backups

Review:

```bash
sudo journalctl \
  -u carequeue-backup.service \
  --since today
```

Do not share production logs publicly without reviewing them for:

- Hostnames
- Usernames
- Internal paths
- Tokens
- Credentials
- Database errors
- Sensitive values

## Upgrade Procedure

Linux upgrade automation is not yet included.

A manual upgrade should follow this order:

```text
1. Confirm recent verified encrypted backup
2. Run repository tests
3. Build and stage updated frontend
4. Stop Caddy or place the application in maintenance mode
5. Stop the API
6. Preserve the current installed release
7. Install updated application files
8. Recreate or update the production Python environment
9. Validate the installed backend
10. Review database migration requirements
11. Start the API
12. Check readiness
13. Reload or start Caddy
14. Check HTTPS
15. Test login and representative workflows
16. Run a post-upgrade backup
```

Do not overwrite the only known-good installed release without keeping a rollback copy.

## Recommended Release Layout

A future safer Linux layout may use versioned releases:

```text
/opt/carequeue/
├── releases/
│   ├── 2026.07.31/
│   └── 2026.08.15/
├── current -> /opt/carequeue/releases/2026.08.15
└── shared/
```

This is not currently implemented by the repository.

Do not adopt it without updating:

- Caddy paths
- systemd paths
- backup service paths
- environment references
- upgrade documentation
- rollback testing

## Rollback

The current repository does not include a Linux rollback script.

A rollback requires:

- The previous trusted release
- The existing production environment file
- Database compatibility
- A recent verified encrypted backup
- Recovery instructions
- A maintenance window

Do not run older application code against a newer database schema without reviewing compatibility.

Database rollback must use the staged recovery process.

Do not manually overwrite the active database.

## Health Checks

Direct liveness:

```bash
curl \
  --fail \
  http://127.0.0.1:8000/api/health/live
```

Direct readiness:

```bash
curl \
  --fail \
  http://127.0.0.1:8000/api/health/ready
```

HTTPS liveness:

```bash
curl \
  --fail \
  https://carequeue.example.com/api/health/live
```

HTTPS readiness:

```bash
curl \
  --fail \
  https://carequeue.example.com/api/health/ready
```

Use the actual hostname.

## Troubleshooting

### Caddy reports an invalid configuration

Run:

```bash
sudo caddy fmt \
  --overwrite \
  /etc/caddy/Caddyfile
```

Then:

```bash
sudo caddy validate \
  --config /etc/caddy/Caddyfile \
  --adapter caddyfile
```

Review the exact line reported.

### Caddy cannot connect to the API

Confirm the API listens on loopback:

```bash
sudo ss \
  -lntp \
  | grep 8000
```

Test directly:

```bash
curl \
  --fail \
  http://127.0.0.1:8000/api/health/live
```

If direct health works but Caddy fails, inspect Caddy logs and reverse-proxy configuration.

### Frontend loads but routes return 404

Confirm the Caddyfile includes:

```caddyfile
try_files {path} /index.html
```

Confirm:

```text
/opt/carequeue/frontend/dist/index.html
```

exists.

### Browser requests `localhost:8000`

The production frontend was built with a development Vite API override.

Remove the production-relevant override, rebuild the frontend, and redeploy `dist`.

### API imports fail

Load the environment and test:

```bash
set -a
source /etc/carequeue/carequeue.env
set +a
```

```bash
sudo -u carequeue \
  /opt/carequeue/backend/.venv/bin/python \
  -c "import authstatus_api.main"
```

Review configuration validation errors without printing secrets.

### Backup service cannot write

Review:

```bash
sudo systemctl status carequeue-backup.service
```

```bash
sudo journalctl \
  -u carequeue-backup.service \
  --since today
```

Check:

```bash
sudo ls -ld \
  /var/lib/carequeue/backups
```

Confirm the directory is writable by `carequeue`.

### Backup service cannot read the database

Confirm:

- The environment file points to the intended database.
- The service account can traverse parent directories.
- The database is readable by `carequeue`.
- `ProtectSystem=strict` does not block the configured path.
- The SQLCipher key is present.
- The database path is not outside approved storage without explicit configuration.

### Environment file is rejected

Production configuration validation may reject:

- Placeholder keys
- Development origins
- Unsafe paths
- Missing required encryption settings
- Invalid JSON values

Fix the exact setting. Do not weaken validation without understanding the risk.

## Security Checklist

Before using real sensitive data:

- The API binds only to loopback.
- Caddy is the only user-facing service.
- HTTPS is valid and trusted.
- The production hostname is correct.
- The environment file is `0640` or more restrictive.
- Runtime directories are not world-readable.
- SQLCipher mode is enabled.
- Independent encryption keys are recoverable.
- Backups run automatically.
- Backup files are encrypted and nonempty.
- Restore testing has been completed.
- Off-host backup policy is documented.
- Firewall rules are reviewed.
- Service accounts are restricted.
- Logs are protected.
- Operating system updates are managed.
- Caddy and dependencies are patched.
- Access review procedures exist.
- Incident response is documented.
- Legal and compliance review is complete.

## Remaining Repository Work

The following Linux work remains a project priority:

- Add a hardened `carequeue-api.service`
- Add a Linux production installer
- Add environment generation and permission handling
- Add versioned release installation
- Add upgrade and rollback scripts
- Add production smoke tests
- Add private certificate guidance
- Add distribution-specific validation
- Add uninstall procedures
- Add complete Linux recovery activation instructions
- Test reboot and failure behavior

Until those pieces are implemented and tested, Linux deployment requires more operator judgment than Windows deployment.

## Screenshots

Screenshots should be added after the Linux workflow is implemented and validated.

Useful screenshots may include:

- `systemctl status` for the API
- `systemctl status` for Caddy
- `systemctl status` for the backup timer
- Successful HTTPS health response
- Successful backup service result
- CareQueue login page over HTTPS

Use synthetic data only.

Before committing:

- Remove personal usernames and hostnames where practical.
- Do not show environment-file contents.
- Do not show keys or credentials.
- Do not show real records.
- Review terminal history visible in the screenshot.

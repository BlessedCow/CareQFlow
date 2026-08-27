# Linux Deployment

CareQueue includes a packaged Linux installation workflow for supported Debian-based systems.

The Linux release is distributed as a versioned tar archive containing the production backend, prebuilt frontend, Linux installer scripts, Caddy configuration, and systemd service definitions.

CareQueue is intended for private or controlled deployment. This guide does not describe a general public internet hosting architecture, managed hosting service, or complete compliance program. Organizations remain responsible for their own security, privacy, legal, operational, and compliance requirements.

## Current Status

The repository currently includes:

```text
deployment/linux/
├── Caddyfile
├── CareQueue-AdminSetup.sh
├── install-production.sh
├── uninstall-production.sh
├── installer/
│   ├── build-payload.ps1
│   └── invoke-install.sh
└── systemd/
    ├── carequeue-api.service
    ├── carequeue-backup.service
    ├── carequeue-backup.timer
    └── carequeue-caddy.service
```

Implemented Linux deployment capabilities include:

- Versioned `CareQueue-Linux-Setup-<version>.tar.gz` release packages
- Install, upgrade, repair, and uninstall modes
- Ubuntu and Debian distribution validation
- Dedicated `carequeue` system account and group
- Production application, configuration, runtime, and log directories
- Prebuilt frontend installation
- Isolated production Python virtual environment creation
- Backend dependency installation and import validation
- Production environment-file creation
- Independent field-encryption, SQLCipher, and backup-encryption keys
- Preservation of existing production configuration during upgrade and repair
- Trusted production data-root migration for existing configuration
- SQLCipher production database configuration
- Hardened CareQueue API systemd service
- Hardened CareQueue Caddy systemd service
- Encrypted backup service and daily backup timer
- Automatic Caddy installation when it is not already available
- Same-origin HTTPS through Caddy
- Local `carequeue.local` hostname configuration
- Caddy internal certificate-authority trust setup on the Linux host
- Automatic service enablement and startup
- HTTPS frontend, liveness, and readiness validation after installation
- Interactive first-Admin setup on new installations
- Uninstall support while preserving production configuration, runtime data, and logs

The Linux installer is intended for an administrator comfortable with Linux, systemd, package installation, filesystem permissions, and certificate trust.

Current limitations include:

- Automated rollback to a previous application release is not implemented.
- Linux support is currently limited to Ubuntu and Debian.
- The packaged Caddy configuration is designed around the private `carequeue.local` deployment model.
- Trusting the Caddy internal CA on the server does not automatically distribute trust to other client devices.
- Public DNS and publicly trusted certificate deployment require separate planning and configuration.
- Production disaster-recovery activation still requires operator review and validation.
- The exact target distribution and operating-system version should be validated before introducing sensitive production data.

## Architecture

The packaged Linux request flow is:

```text
Browser
  |
  | HTTPS
  v
CareQueue Caddy service
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

The API binds only to:

```text
127.0.0.1:8000
```

Caddy is the user-facing HTTP service. Do not expose Uvicorn directly to the network unless a separately reviewed deployment architecture explicitly requires it.

## Default Filesystem Layout

Application files:

```text
/opt/carequeue/
├── backend/
│   ├── authstatus_api/
│   ├── scripts/
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── .venv/
├── frontend/
│   └── dist/
└── deployment/
    └── linux/
```

Runtime data:

```text
/var/lib/carequeue/
├── backups/
├── caddy/
│   ├── config/
│   └── data/
├── data/
├── recovery/
└── restores/
```

Configuration:

```text
/etc/carequeue/
├── carequeue.env
├── Caddyfile
└── install-state.env
```

Logs:

```text
/var/log/carequeue/
└── installer/
```

The installer supports environment overrides for the application, data, configuration, and log roots, but the packaged systemd units are designed for the default paths above. Treat path changes as an advanced deployment change that requires service-unit review and validation.

## Service Account

The installer creates or reuses the dedicated system account and group:

```text
carequeue
```

The service account is created without an interactive login shell and is used by the CareQueue API, Caddy, and backup services.

Do not run the long-lived application services under an ordinary administrator account.

## Build the Linux Release Archive

From the repository root, build the production frontend first:

```powershell
npm --prefix frontend run build
```

Then build the Linux release archive:

```powershell
.\deployment\linux\installer\build-payload.ps1
```

A specific version may also be supplied:

```powershell
.\deployment\linux\installer\build-payload.ps1 -Version 0.3.0
```

The package is written under:

```text
build/linux/installer/
```

For CareQueue v0.3.0, the expected release filename is:

```text
CareQueue-Linux-Setup-0.3.0.tar.gz
```

The build script validates required payload sources, requires an existing production frontend build, stages the production files, normalizes Linux deployment text files to LF line endings, and creates the compressed tar archive.

## Install the Release Package

Transfer the reviewed release archive to the target Linux system and extract it into a temporary installation directory.

For example:

```bash
mkdir carequeue-installer

tar -xzf CareQueue-Linux-Setup-0.3.0.tar.gz \
  -C carequeue-installer

cd carequeue-installer
```

Run the installer as root:

```bash
sudo bash deployment/linux/installer/invoke-install.sh install
```

The installer rejects `install` mode if an existing CareQueue installation is already detected. Use `upgrade` or `repair` for an existing installation.

Installer logs are written under:

```text
/var/log/carequeue/installer/
```

Keep the release archive and installer log until installation validation is complete.

## Supported Linux Distributions

The current production installer validates `/etc/os-release` and supports:

```text
Ubuntu
Debian
```

Other distributions are rejected by the installer.

The installer uses `apt` and installs required packages including Python, Python virtual-environment support, build tools, SQLCipher development libraries, certificates, and `curl`.

## What the Installer Does

A new installation performs the following high-level sequence:

1. Requires root privileges.
2. Validates the requested installer mode.
3. Creates an installer log.
4. Validates the application origin.
5. Validates the Linux distribution.
6. Installs required operating-system packages.
7. Creates or reuses the `carequeue` service account and group.
8. Creates the application, data, configuration, and log directories.
9. Installs the CareQueue backend, prebuilt frontend, and Linux deployment files.
10. Recreates the production Python virtual environment.
11. Installs backend Python requirements.
12. Validates that the backend imports successfully.
13. Creates the production environment file on a new installation or preserves and migrates it on upgrade or repair.
14. Installs CareQueue systemd units.
15. Installs Caddy if needed.
16. Disables the distribution's default Caddy service so CareQueue can use its dedicated Caddy unit.
17. Installs and validates the CareQueue Caddy configuration.
18. Ensures the local `carequeue.local` hosts entry exists.
19. Enables and starts the CareQueue API, Caddy, and backup timer.
20. Trusts the CareQueue Caddy internal root certificate on the Linux host.
21. Validates the HTTPS frontend, liveness endpoint, and readiness endpoint.
22. On a new installation, launches the interactive first-Admin setup utility.

If a required step fails, the installer stops with an error rather than continuing as though installation succeeded.

## Application Origin

The installer defaults to:

```text
https://carequeue.local
```

The installer validates that `APPLICATION_ORIGIN` is an absolute HTTPS origin containing only a hostname and optional port.

The packaged `deployment/linux/Caddyfile` is currently configured specifically for:

```text
carequeue.local
```

and uses Caddy's internal certificate authority.

Because the packaged Caddyfile and local hosts-entry management are currently centered on `carequeue.local`, use of a different application origin requires a reviewed Caddy and hostname configuration change. Do not assume that setting `APPLICATION_ORIGIN` alone completely reconfigures the packaged HTTPS deployment.

## Production Environment File

The installer creates the production environment file at:

```text
/etc/carequeue/carequeue.env
```

On a new installation, it generates independent secrets for:

```text
AUTHSTATUS_ENCRYPTION_KEY
AUTHSTATUS_SQLCIPHER_KEY
AUTHSTATUS_BACKUP_ENCRYPTION_KEY
```

The generated configuration includes production settings such as:

```env
AUTHSTATUS_APP_ENVIRONMENT=production
AUTHSTATUS_DATABASE_ENCRYPTION=sqlcipher
AUTHSTATUS_SESSION_COOKIE_SECURE=true
```

Default trusted storage paths include:

```env
AUTHSTATUS_PRODUCTION_DATA_ROOT=/var/lib/carequeue
AUTHSTATUS_DATABASE_PATH=/var/lib/carequeue/data/auth_tracker.sqlcipher.db
AUTHSTATUS_BACKUP_DIRECTORY=/var/lib/carequeue/backups
AUTHSTATUS_RESTORE_DIRECTORY=/var/lib/carequeue/restores
```

The installer also configures the exact application origin as the allowed CORS origin.

For a new production installation, do not replace the generated keys with development keys or placeholder values.

## Environment File Permissions

The installer sets:

```text
Owner: root
Group: carequeue
Mode: 0640
```

for:

```text
/etc/carequeue/carequeue.env
```

Do not print the environment file contents into logs, tickets, screenshots, chat messages, or public documentation.

## Upgrade and Repair Configuration Preservation

When `/etc/carequeue/carequeue.env` already exists, the installer preserves it rather than generating new encryption keys.

During the current migration path, legacy unsafe-path override settings are removed and the trusted production data root is written as:

```text
AUTHSTATUS_PRODUCTION_DATA_ROOT=/var/lib/carequeue
```

The existing database and encryption keys must remain available across upgrades and repairs. Replacing them can make existing encrypted data unreadable.

## Database Encryption

Production configuration uses:

```env
AUTHSTATUS_DATABASE_ENCRYPTION=sqlcipher
```

with the default database path:

```text
/var/lib/carequeue/data/auth_tracker.sqlcipher.db
```

The installer installs SQLCipher development libraries and the application's Python requirements.

Before using real sensitive data, validate that the deployed database is actually encrypted and cannot be read as ordinary plaintext SQLite.

## CareQueue API Service

The repository includes:

```text
deployment/linux/systemd/carequeue-api.service
```

The installer installs it as:

```text
/etc/systemd/system/carequeue-api.service
```

The service:

- Runs as `carequeue:carequeue`
- Uses `/opt/carequeue/backend` as its working directory
- Loads `/etc/carequeue/carequeue.env`
- Forces production application mode
- Runs the installed Python virtual environment
- Starts Uvicorn with one worker
- Binds to `127.0.0.1:8000`
- Trusts forwarded proxy information only from loopback
- Disables Uvicorn access logging
- Restarts after unexpected failure
- Uses a restrictive `UMask`
- Prevents privilege escalation
- Uses a private temporary directory
- Restricts home-directory visibility
- Makes the general filesystem read-only
- Allows writes only under the CareQueue runtime and log roots

Check status:

```bash
sudo systemctl status carequeue-api.service
```

Review logs:

```bash
sudo journalctl \
  -u carequeue-api.service \
  --since today
```

## CareQueue Caddy Service

The repository includes:

```text
deployment/linux/systemd/carequeue-caddy.service
```

The installer installs it as:

```text
/etc/systemd/system/carequeue-caddy.service
```

CareQueue uses this dedicated unit instead of the distribution's default `caddy.service`.

The service:

- Runs as `carequeue:carequeue`
- Requires the CareQueue API service
- Uses Caddy data under `/var/lib/carequeue/caddy`
- Loads `/etc/carequeue/Caddyfile`
- Uses only the capability needed to bind low-numbered network ports
- Prevents privilege escalation
- Uses a private temporary directory
- Restricts home-directory visibility
- Makes the general filesystem read-only
- Allows writes to the CareQueue Caddy data directory

Check status:

```bash
sudo systemctl status carequeue-caddy.service
```

Review logs:

```bash
sudo journalctl \
  -u carequeue-caddy.service \
  --since today
```

## Caddy Configuration

The packaged Caddyfile is:

```text
deployment/linux/Caddyfile
```

The installer copies it to:

```text
/etc/carequeue/Caddyfile
```

The current configuration:

- Serves `https://carequeue.local`
- Uses `tls internal`
- Enables `zstd` and `gzip`
- Adds security response headers
- Removes the `Server` response header
- Proxies `/api` and `/api/*` to `127.0.0.1:8000`
- Serves the frontend from `/opt/carequeue/frontend/dist`
- Uses `/index.html` as the SPA fallback

The installer validates the Caddyfile before starting CareQueue services.

## Local Hostname

For the default private deployment, the installer ensures `/etc/hosts` contains:

```text
127.0.0.1 carequeue.local # CareQueue
```

This makes `carequeue.local` resolvable on the Linux server itself.

This hosts entry does not automatically make `carequeue.local` resolvable from other computers. Client devices need an approved DNS, hosts-file, or other name-resolution strategy if users will access CareQueue from another machine.

## Certificate Trust

The packaged Caddy configuration uses Caddy's internal CA.

After starting the CareQueue Caddy service, the installer runs Caddy's trust operation using the CareQueue Caddy data and configuration directories. This establishes trust on the Linux installation host.

For other client devices, the internal CA root certificate must be distributed and trusted through an approved process before browsers on those devices will trust the CareQueue certificate.

Do not bypass browser certificate warnings or disable certificate validation.

For a deployment using public DNS or an organization-managed PKI, review and replace the packaged private certificate model rather than weakening TLS validation.

## Health Checks

The installer performs post-installation checks against the configured application origin for:

```text
/
/api/health/live
/api/health/ready
```

It accepts successful 2xx and 3xx responses and retries transient failures before declaring installation unsuccessful.

You can also check the API directly on the Linux server:

```bash
curl \
  --fail \
  --silent \
  --show-error \
  http://127.0.0.1:8000/api/health/live
```

```bash
curl \
  --fail \
  --silent \
  --show-error \
  http://127.0.0.1:8000/api/health/ready
```

Check the HTTPS deployment:

```bash
curl \
  --fail \
  --silent \
  --show-error \
  https://carequeue.local/api/health/live
```

```bash
curl \
  --fail \
  --silent \
  --show-error \
  https://carequeue.local/api/health/ready
```

## First-Time Admin Setup

On a new installation, `invoke-install.sh install` launches the installed Admin setup utility:

```text
/opt/carequeue/deployment/linux/CareQueue-AdminSetup.sh
```

The setup utility checks whether initial Admin setup is still available and, when required, prompts interactively for the first Admin account.

Do not place the Admin password on the command line or in shell history.

If initial setup has already been completed, the first-Admin endpoint is no longer available for creating another account.

## Governance Attestation

After the first Admin signs in through the browser, CareQueue requires the current organization governance attestation before normal protected application functionality becomes available.

The attestation records information including:

- Organization name
- Deployment mode
- Accepting Admin
- Acceptance timestamp
- CareQueue application version
- Governance attestation version

Governance history is append-only and is visible to Admin users on the System page.

The in-application governance workflow supports organizational security and compliance processes. Accepting the attestation does not itself execute a Business Associate Agreement or establish HIPAA compliance.

## Browser Smoke Test

After installation, open CareQueue in a supported browser and confirm:

- The CareQueue HTTPS certificate is trusted on the client device.
- The login page loads over HTTPS.
- Browser API calls use the same HTTPS origin.
- No browser request goes directly to `127.0.0.1:8000`.
- Initial Admin login works.
- The governance attestation appears when required.
- After governance acceptance, the normal application loads.
- A representative protected workflow loads successfully.
- Logout works and returns the browser to the login state.

Use synthetic data for deployment validation.

## Encrypted Backup Service

The repository includes:

```text
deployment/linux/systemd/carequeue-backup.service
```

The installer installs the service and its timer automatically.

The backup service runs the project's encrypted backup script from the installed Python environment and writes backups under:

```text
/var/lib/carequeue/backups
```

It loads the production environment from:

```text
/etc/carequeue/carequeue.env
```

The service uses systemd hardening including:

```ini
PrivateTmp=true
NoNewPrivileges=true
ProtectHome=true
ProtectSystem=strict
UMask=0077
```

The backup directory is explicitly writable while the general filesystem remains protected.

## Backup Timer

The installer enables:

```text
carequeue-backup.timer
```

The current schedule uses:

```ini
OnCalendar=*-*-* 02:00:00
RandomizedDelaySec=15m
Persistent=true
```

This means the backup runs daily around 2:00 AM, may be delayed by up to 15 minutes, and may run after startup if a scheduled run was missed while the system was unavailable.

Check the timer:

```bash
sudo systemctl status carequeue-backup.timer
```

List its next run:

```bash
systemctl list-timers carequeue-backup.timer
```

## Run a Manual Backup

Start the one-shot service:

```bash
sudo systemctl start carequeue-backup.service
```

Check the result:

```bash
sudo systemctl status carequeue-backup.service
```

A successful one-shot service may return to:

```text
inactive (dead)
```

after the task completes. Review the result and logs rather than treating that state alone as failure.

Review logs:

```bash
sudo journalctl \
  -u carequeue-backup.service \
  --since today
```

Confirm encrypted backups exist:

```bash
sudo find \
  /var/lib/carequeue/backups \
  -maxdepth 1 \
  -type f \
  -name "*.db.enc" \
  -printf "%TY-%Tm-%Td %TH:%TM:%TS %s %f\n"
```

A successful service result is not sufficient by itself. Confirm that the backup file is present, nonempty, encrypted, and recoverable through a staged restore test.

See [Backup and Recovery](../workflows/backup-and-recovery.md).

## File Permissions

Review runtime ownership and permissions:

```bash
sudo find \
  /var/lib/carequeue \
  -maxdepth 2 \
  -printf "%M %u %g %p\n"
```

The installer uses restrictive ownership and permissions for production configuration and runtime storage. Do not make the database, encryption keys, backups, recovery files, or logs world-readable or world-writable.

## Firewall and Network Exposure

The API should remain loopback-only:

```text
127.0.0.1:8000
```

Review listening sockets:

```bash
sudo ss -lntp
```

Only the approved HTTPS service should be exposed to CareQueue users.

Do not expose:

- The Uvicorn API port directly
- Database files
- Backup storage
- Recovery storage
- Administrative services beyond what the environment requires

Apply firewall rules through the operating system's approved firewall tooling.

## Logs

Installer logs:

```text
/var/log/carequeue/installer/
```

API logs:

```bash
sudo journalctl \
  -u carequeue-api.service \
  --since today
```

CareQueue Caddy logs:

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

Before sharing logs, review them for hostnames, usernames, internal paths, credentials, tokens, database errors, and other sensitive information.

## Upgrade

Before upgrading:

1. Confirm a recent verified encrypted backup exists.
2. Preserve the current release package until validation is complete.
3. Preserve a verified pre-upgrade backup until the upgraded installation has been fully validated.
4. Review the release notes and [upgrade documentation](../operations/upgrades.md).
5. Confirm the production environment file and all required encryption keys are accounted for.
6. Confirm the current installation is healthy.
7. Confirm sufficient disk space is available for application files, the database, logs, backups, and recovery data.
8. Extract the new release package into a temporary installer directory.

Run:

```bash
sudo bash deployment/linux/installer/invoke-install.sh upgrade
```

Upgrade mode requires an existing installation. It preserves the existing production configuration and runtime data while reinstalling application files, recreating the Python environment, reinstalling service definitions, validating Caddy, restarting services, and rerunning health checks.

When the upgraded CareQueue API starts, database initialization may apply registered versioned schema migrations that have not yet been recorded in the database's `schema_migrations` ledger.

Already applied migrations are skipped. Each new migration is applied through the migration framework and is recorded only after successful application.

Do not manually edit the migration ledger to bypass a failed upgrade.

A database migrated by a newer CareQueue release is not automatically guaranteed to be compatible with an older CareQueue application release. Keep the verified pre-upgrade backup available until rollback is no longer required.

After the installer completes, verify:

1. `carequeue-api.service` is active.
2. `carequeue-caddy.service` is active.
3. The encrypted backup timer remains enabled.
4. HTTPS frontend access succeeds.
5. Liveness and readiness checks pass.
6. Login succeeds.
7. Governance status shows the expected attestation version and document revision.
8. A representative authorization workflow works correctly.
9. Backup and recovery functionality remains available.

If the API fails to start after an upgrade, review the API journal and installer log before retrying the upgrade or modifying production data:

```bash
sudo journalctl \
  -u carequeue-api.service \
  --since today
```

```text
/var/log/carequeue/installer/
```

A migration failure should be investigated rather than worked around by deleting migration records or manually altering the production schema.

The current workflow does not provide automatic rollback to the previous application release.

## Repair

Use repair mode when an existing installation needs the packaged application and deployment components reapplied without intentionally replacing production data or secrets.

Run:

```bash
sudo bash deployment/linux/installer/invoke-install.sh repair
```

Repair mode requires an existing installation and preserves the existing production configuration and runtime data.

After repair, confirm service health, HTTPS access, login, governance state, and a representative application workflow.

## Uninstall

Run uninstall from an extracted CareQueue release package:

```bash
sudo bash deployment/linux/installer/invoke-install.sh uninstall
```

The uninstall workflow:

- Disables and stops the CareQueue backup timer
- Disables and stops the CareQueue Caddy service
- Disables and stops the CareQueue API service
- Removes the CareQueue systemd unit files
- Removes `/opt/carequeue`
- Removes the installer-managed `carequeue.local` hosts entry

A normal uninstall intentionally preserves:

```text
/etc/carequeue
/var/lib/carequeue
/var/log/carequeue
```

This means the database, encryption keys, backups, recovery data, and logs are not automatically deleted.

Do not manually remove preserved production data unless retention, recovery, and destruction requirements have been reviewed and the required backups and keys are accounted for.

## Rollback

The current repository does not include an automated Linux rollback command.

A safe rollback requires review of:

- The previous trusted application release
- Existing production configuration and encryption keys
- Database schema compatibility
- A recent verified encrypted backup
- Recovery procedures
- A maintenance window

Do not run older application code against a newer database schema without confirming compatibility.

Do not manually overwrite the active production database as an application rollback mechanism.

Database recovery should use the project's staged recovery workflow.

See [Upgrades](../operations/upgrades.md) and [Backup and Recovery](../workflows/backup-and-recovery.md).

## Troubleshooting

### The installer says CareQueue is already installed

Use:

```bash
sudo bash deployment/linux/installer/invoke-install.sh upgrade
```

or:

```bash
sudo bash deployment/linux/installer/invoke-install.sh repair
```

`install` mode intentionally refuses to overwrite an existing detected installation.

### Upgrade or repair says CareQueue is not installed

The installer considers CareQueue installed when both of these exist:

```text
/opt/carequeue/backend
/etc/carequeue/carequeue.env
```

Review whether the installation is incomplete or whether nondefault paths were used.

### CareQueue API service is not running

Check status:

```bash
sudo systemctl status carequeue-api.service
```

Review logs:

```bash
sudo journalctl \
  -u carequeue-api.service \
  --since today
```

Confirm the environment file exists and the database and runtime paths are accessible to the `carequeue` service account.

### CareQueue Caddy service is not running

Check status:

```bash
sudo systemctl status carequeue-caddy.service
```

Review logs:

```bash
sudo journalctl \
  -u carequeue-caddy.service \
  --since today
```

Validate the installed Caddyfile:

```bash
sudo caddy validate \
  --config /etc/carequeue/Caddyfile \
  --adapter caddyfile
```

### Caddy cannot connect to the API

Confirm Uvicorn is listening on loopback:

```bash
sudo ss -lntp | grep 8000
```

Test the API directly:

```bash
curl \
  --fail \
  http://127.0.0.1:8000/api/health/live
```

If direct health succeeds but HTTPS fails, inspect the CareQueue Caddy service and Caddy configuration.

### Browser does not trust the certificate

The installer trusts the Caddy internal root CA on the Linux server, not automatically on every client device.

Confirm that the CareQueue internal root certificate has been distributed and trusted on the browser's device through an approved process.

Do not bypass the certificate warning.

### `carequeue.local` does not resolve from another computer

The installer adds `carequeue.local` only to the Linux server's `/etc/hosts` file.

Configure approved name resolution for each client or through your private DNS environment.

### Frontend loads but routes return 404

Confirm the installed Caddyfile contains SPA fallback behavior using:

```caddyfile
try_files {path} /index.html
```

Confirm the frontend build exists:

```text
/opt/carequeue/frontend/dist/index.html
```

### Browser requests `localhost:8000`

The production frontend was built with an inappropriate development API override.

Rebuild the frontend for same-origin production API requests and recreate the release package.

### Backend import or startup fails

Check the API service logs first.

You can also validate the installed backend from the server:

```bash
cd /opt/carequeue/backend

sudo -u carequeue \
  /opt/carequeue/backend/.venv/bin/python \
  -c "import authstatus_api.main"
```

Review configuration errors without printing secrets.

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

Check the backup directory:

```bash
sudo ls -ld /var/lib/carequeue/backups
```

Confirm it is writable by the `carequeue` service account.

### Environment file is rejected

Production validation may reject placeholder secrets, unsafe paths, development origins, invalid encryption settings, or malformed configuration values.

Fix the specific rejected setting. Do not weaken production validation merely to make startup succeed.

## Security Checklist

Before using real sensitive data, confirm:

- The target operating system and version have been validated.
- The API binds only to loopback.
- The CareQueue Caddy service is the intended user-facing HTTP service.
- HTTPS is valid and trusted on every approved client device.
- The deployment hostname resolves only where intended.
- The production environment file remains restricted.
- Production encryption keys are independent and recoverable through an approved key-custody process.
- SQLCipher mode is enabled and the deployed database has been verified as encrypted.
- Runtime, backup, recovery, and log directories are not broadly readable.
- Automatic encrypted backups are enabled.
- Recent backup files exist and are nonempty.
- Backup restore testing has been performed.
- Off-host backup policy is documented when required.
- Firewall and network exposure have been reviewed.
- The `carequeue` service account has only the access it requires.
- Operating-system security updates are managed.
- Caddy and application dependencies are maintained.
- First-Admin setup is complete.
- Governance attestation is complete for the current required version.
- User roles and MFA requirements have been reviewed.
- Access review procedures exist.
- Incident-response procedures exist.
- Legal and compliance review is complete.

## Remaining Linux Work

The primary remaining Linux deployment work includes:

- Automated rollback to a previous trusted application release
- Broader tested distribution and operating-system coverage
- Additional automated release-package smoke testing
- Expanded disaster-recovery activation testing and documentation
- Validation of reboot, interrupted-upgrade, and service-failure scenarios across supported systems
- Continued hardening and documentation of private certificate distribution and lifecycle management
- Better support for deployments that use an application hostname other than the packaged `carequeue.local` model

The packaged Linux installation path should still be validated on the exact target environment before introducing sensitive production data.

## Screenshots

Documentation screenshots should use synthetic data only.

Useful Linux deployment screenshots may include:

- `systemctl status carequeue-api.service`
- `systemctl status carequeue-caddy.service`
- `systemctl status carequeue-backup.timer`
- Successful HTTPS health response
- Successful backup result
- CareQueue login page over trusted HTTPS
- Governance attestation screen using synthetic organization information

Before committing screenshots:

- Remove personal usernames and hostnames where practical.
- Do not show environment-file contents.
- Do not show keys, tokens, or credentials.
- Do not show real patient or authorization records.
- Review terminal history visible in the screenshot.

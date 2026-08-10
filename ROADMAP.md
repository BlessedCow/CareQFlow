# Roadmap

CareQueue is under active development. The main authorization workflow is in place, and the current focus is deployment validation, operations, maintainability, and release hardening.

This roadmap is intended to show the direction of the project without becoming a complete changelog.

## Current State

CareQueue currently includes:

- Authorization record management
- Authorization timeline events
- Dashboard and calendar workflows
- Search and filtering
- Role-based access for Admin, UR, and Read Only users
- Local user management
- Server-side sessions and CSRF protection
- Session expiration warnings and renewal
- Field-level encryption for selected sensitive values
- SQLCipher database support
- Encrypted backups
- Backup verification and retention controls
- Staged restore and recovery workflows
- Local PDF-assisted intake
- Confidence and needs-review flags for extracted values
- Audit logging
- Production log sanitization
- Backend and frontend automated tests
- Packaged Windows installation
- Windows services for the API and HTTPS frontend
- Private HTTPS through Caddy
- Installer modes for Install, Upgrade, Repair, and Uninstall
- First-time Admin setup through a local setup GUI
- Windows scheduled backup support
- Initial Linux deployment files

The current Windows deployment runs the API on the loopback interface and uses Caddy to serve the frontend and proxy `/api` requests over private HTTPS.

## Recently Completed

### Packaged Windows installer

The Windows installer now supports:

- Fresh installation on a local Windows development machine
- Upgrade over an existing installation
- Repair of an existing installation
- Uninstall while preserving runtime data
- Fresh installation after uninstall using preserved data
- Post-installation service and health validation
- First-time Admin setup from the installer finish page
- Existing-admin detection that disables repeat initial setup

The installer packages application files, backend runtime files, frontend build output, Caddy, WinSW service wrappers, and the private Python runtime needed by the backend.

### First-time Admin setup

CareQueue now includes a one-time initial Admin setup path for packaged Windows installations.

The setup flow is available only while no users exist. After a user exists, the backend disables initial Admin setup and the setup GUI reports that setup is already complete.

### Backup and recovery

Recent backup work includes:

- Separately encrypted backups
- Backup verification
- Retention periods
- Minimum protected backup counts
- Windows Task Scheduler integration
- Linux systemd scheduling files
- Safe restore staging
- Controlled recovery activation

### Security hardening

Recent security work includes:

- Session and CSRF token rotation
- Shared server-side password policy enforcement
- Failed-login tracking and temporary account lockout
- Loopback-only first-time Admin setup
- Trusted storage path checks
- Safer directory enumeration
- Symlink rejection in sensitive file workflows
- Centralized validated file reads
- Production log sanitization
- Bounded backend dependency requirements
- Backend and frontend dependency audit checks
- Static security scanning with Bandit
- Content Security Policy through Caddy
- Isolated PDF extraction with timeout handling
- Private same-origin production API requests
- Restricted production runtime directories
- Service-aware production upgrades

## Next Priorities

### 1. Clean-machine VM testing matrix

The next major validation step is to test the packaged Windows installer on clean virtual machines that do not contain the development environment.

The first target should be a clean Windows 11 VM.

Validation should include:

- Fresh install
- First-time Admin setup
- Browser access to `https://carequeue.local`
- Login with the first Admin account
- Basic authorization workflow smoke test
- Reboot and service auto-start check
- Repair from the installer mode page
- Upgrade from the installer mode page
- Uninstall from the installer mode page
- Confirmation that runtime data is preserved after uninstall
- Fresh install after uninstall using preserved data

A clean Windows 10 VM should be tested after the Windows 11 path is stable.

### 2. Code signing and release packaging

After clean-machine validation passes, the release path should focus on packaging and trust.

Remaining work includes:

- Decide whether the first public build is unsigned or signed
- Add code-signing guidance for the installer executable
- Document release asset naming
- Document GitHub pre-release versus stable release expectations
- Include checksums for release artifacts
- Confirm the source tag matches the attached installer artifact
- Keep release notes concise and tied to validated behavior

The first release candidate should remain marked as a pre-release until clean-machine validation and release packaging checks are complete.

### 3. Production smoke-test tooling

A small production validation script should check the installed application without exposing secrets.

It should verify:

- API service status
- Caddy service status
- Direct loopback API health
- HTTPS health through Caddy
- Readiness endpoint
- Frontend availability
- Same-origin API behavior
- Production database access
- Backup directory access
- Recent backup presence when scheduled backups are enabled
- Certificate trust

The script should report clear pass or fail results and point operators to the correct log locations.

### 4. Improve upgrade and rollback handling

The current installer can upgrade and repair the installed application, but rollback guidance should continue to improve.

Remaining work includes:

- Pre-upgrade backup verification
- Clear rollback instructions
- Versioned installation metadata
- Better failure summaries
- Database migration safeguards
- Validation before replacing the active installation
- Recovery steps when a packaged dependency fails to install

### 5. Formalize database migrations

The project currently initializes and evolves the schema through application migration logic.

A more formal migration strategy should provide:

- Explicit migration identifiers
- Ordered migration history
- Clear upgrade paths
- Validation of the current schema version
- Safer downgrade or rollback planning
- Migration tests using representative older schemas

### 6. Expand browser-level testing

Frontend unit and component tests are in place.

The next testing layer should cover full browser workflows such as:

- Login and logout
- Session expiration and renewal
- Creating an authorization
- Editing an authorization
- Adding timeline events
- Filtering and dashboard interactions
- PDF intake review
- Role-based access
- Backup and recovery administration
- Production same-origin behavior

Tests must use synthetic data.

### 7. Continue accessibility work

Accessibility review should include:

- Keyboard navigation
- Focus management
- Form labels and descriptions
- Error announcements
- Dialog behavior
- Table navigation
- Color contrast
- Reduced-motion preferences
- Screen-reader behavior
- Session warning accessibility

Accessibility should be reviewed alongside each major frontend workflow rather than postponed until the end.

## Later Work

### Linux deployment

The repository includes initial Linux deployment files, but the Linux path is not yet equivalent to Windows.

Remaining Linux work includes:

- API systemd service
- Caddy installation and validation
- Environment-file permissions
- Service-account setup
- Runtime directory creation
- Backup scheduling validation
- Upgrade procedures
- Log locations and rotation
- Private HTTPS validation
- Distribution-specific testing

### Backup operations

Future backup improvements include:

- Clear backup status view
- Improved failed-backup visibility
- Restore test guidance
- Off-host backup options
- Optional backup age warnings
- Retention review against operational needs
- Recovery testing from older backup versions

### PDF intake

Future PDF intake improvements include:

- Additional payer and facility templates
- Improved confidence scoring
- Better detection of conflicting values
- More malformed-PDF tests
- Clearer review messages
- Optional local OCR evaluation without telemetry
- Synthetic fixtures for more document layouts

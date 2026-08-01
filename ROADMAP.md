# Roadmap

CareQueue is under active development. The main authorization workflow is in place, and the current focus is shifting from core feature work toward deployment, operations, maintainability, and production validation.

This roadmap is intended to show the direction of the project without turning into a list of every completed change.

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
- Windows production installation
- Windows services for the API and HTTPS frontend
- Private HTTPS through Caddy
- Safe service handling during production upgrades
- Windows scheduled backup support
- Initial Linux deployment files

The current Windows deployment has been tested with:

```text
CareQueueApi
CareQueueCaddy
https://carequeue.local
```

The API runs on the loopback interface, and Caddy serves the frontend and proxies `/api` requests over private HTTPS.

## Recently Completed

### Private Windows deployment

The Windows deployment now supports:

- Building the production frontend
- Installing application files under `C:\Program Files\CareQueue`
- Storing runtime data under `C:\ProgramData\CareQueue`
- Generating independent production encryption keys
- Preserving production settings and keys during upgrades
- Running FastAPI as a Windows service
- Running Caddy as a Windows service
- Private HTTPS through a local hostname
- Installing the Caddy local root certificate
- Stopping and restoring services during upgrades
- Preventing local Vite environment files from affecting production builds
- Clean service installation and removal scripts

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

### Frontend testing

Frontend testing now covers important application behavior using Vitest and Testing Library.

The production frontend build is also checked through:

```powershell
npm test
npm run build
```

### Security hardening

Recent security work includes:

- Session and CSRF token rotation
- Trusted storage path checks
- Safer directory enumeration
- Symlink rejection in sensitive file workflows
- Centralized validated file reads
- Production log sanitization
- Dependency and static analysis review
- Private same-origin production API requests
- Restricted production runtime permissions

## Next Priorities

### 1. Finish deployment documentation

The current deployment scripts work, but operators still need concise documentation for:

- First-time Windows installation
- Creating the first production user
- Installing the API and Caddy services
- Trusting the local Caddy certificate
- Installing scheduled backups
- Performing upgrades
- Removing services
- Recovering from a failed upgrade
- Verifying service health
- Finding logs
- Restoring from backup

This should live under:

```text
docs/deployment/
docs/operations/
```

The goal is to make the deployment repeatable without requiring knowledge of the development history.

### 2. Add production smoke tests

A small production validation script should check:

- API service status
- Caddy service status
- HTTPS health endpoint
- Readiness endpoint
- Frontend availability
- Same-origin API behavior
- Production database access
- Backup directory access
- Recent backup presence
- Certificate trust

The script should report clear pass or fail results without exposing secrets.

### 3. Improve upgrade and rollback handling

The current Windows installer safely stops and restores services during upgrades.

Remaining work includes:

- Pre-upgrade backup verification
- Clear rollback instructions
- Versioned installation metadata
- Better failure summaries
- Optional upgrade logs
- Database migration safeguards
- Validation before replacing the active installation
- Recovery when dependency installation fails

### 4. Formalize database migrations

The project currently initializes and evolves the schema through application migration logic.

A more formal migration strategy should provide:

- Explicit migration identifiers
- Ordered migration history
- Clear upgrade paths
- Validation of the current schema version
- Safer downgrade or rollback planning
- Migration tests using representative older schemas

### 5. Expand browser-level testing

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

### 6. Continue accessibility work

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

## Near-Term Work

### Windows operations

- Complete operator documentation
- Add production health-check tooling
- Add safer upgrade logging
- Test service removal and reinstallation
- Test service behavior after restart and reboot
- Review service-account permissions
- Review Windows Firewall expectations
- Document certificate renewal and replacement behavior

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

- Add a clear backup status view
- Improve failed-backup visibility
- Add restore test guidance
- Document off-host backup options
- Add optional backup age warnings
- Review backup retention behavior against operational needs
- Test recovery from older backup versions

### PDF intake

- Expand supported payer and facility templates
- Improve field confidence scoring
- Improve detection of conflicting values
- Add more malformed-PDF tests
- Improve review messages
- Evaluate local OCR options without telemetry
- Keep OCR optional and separately reviewed
- Add synthetic fixtures for more document layouts

### Authorization workflow

- Continue refining payer and facility workflows
- Improve bulk review and queue management
- Add clearer stale-work indicators
- Improve denial, appeal, and peer-to-peer workflows
- Review how discharged and completed records are archived
- Improve reporting without exposing sensitive values

## Later Work

### Public synthetic demo

A public demo may be created later, but it must be completely separate from private CareQueue use.

The demo should have:

- Synthetic data only
- Independent encryption keys
- A separate database
- Separate backups
- Separate deployment files
- No connection to a private instance
- No copied production screenshots
- No real payer, facility, member, or clinical information

The public demo should be treated as its own deployment, not a mode switch inside a private installation.

### Reporting and exports

Potential reporting work includes:

- Workload summaries
- Due-date reports
- Authorization outcome summaries
- Facility and payer trend views
- Export controls
- Privacy-aware printable reports

Exports should be reviewed carefully because they create new copies of sensitive data.

### Notification support

Potential notification work includes:

- Local due-date reminders
- Backup failure notices
- Service health notices
- Optional email or system notifications

Notification systems must avoid placing PHI or credentials in message bodies, subject lines, URLs, or third-party services.

### Multi-user deployment

CareQueue currently supports multiple local application users, but broader shared deployment needs additional planning.

Areas to review include:

- Central identity integration
- Stronger account lifecycle controls
- Concurrent-use testing
- Shared-network deployment
- Remote access
- Session visibility and revocation
- Administrative access review
- Organizational audit requirements

### Packaging and releases

Future release work may include:

- Versioned release artifacts
- Checksums
- Signed packages
- Upgrade notes
- Release automation
- Installation verification
- Dependency lock review
- Supported-version documentation

## Ongoing Work

Some areas do not have a single completion point.

### Security

Security work remains continuous:

- Dependency updates
- Static analysis
- Authentication review
- Session review
- CSRF review
- SQL review
- Path and file handling review
- Logging review
- Backup and recovery testing
- Deployment review
- Secret handling
- Access-control review

### Testing

Tests should be added alongside behavior changes.

The project should continue using:

```powershell
pytest tests -n auto -q
python -m ruff check . --fix
```

and:

```powershell
npm test
npm run build
```

Additional manual validation remains necessary for:

- Windows services
- Caddy
- Certificates
- Scheduled tasks
- Filesystem permissions
- Production upgrades
- Backup restoration

### Documentation

Documentation should be updated when behavior changes.

Priority documents include:

```text
README.md
ARCHITECTURE.md
SECURITY.md
ROADMAP.md
docs/deployment/
docs/operations/
docs/workflows/
```

The root documents should remain readable. Detailed commands and operating procedures should move into `docs/`.

## Out of Scope or Not Guaranteed

CareQueue does not currently guarantee:

- HIPAA compliance
- Certification for clinical use
- Public internet deployment readiness
- Hosted multi-tenant operation
- Integration with every payer portal
- General OCR support for all scanned documents
- Automatic correctness of extracted PDF values
- Protection against a compromised host
- Recovery without valid encryption keys
- Complete legal or regulatory recordkeeping
- Automatic incident response
- Automatic off-site backup storage

These areas require separate technical, legal, operational, or organizational review.

## Guiding Principles

Future work should continue to follow these rules:

- Keep sensitive processing local where practical.
- Use synthetic data in tests, screenshots, and demos.
- Keep development and production configuration separate.
- Treat the backend as the authorization boundary.
- Preserve independent encryption keys for independent protection layers.
- Stage restores before activation.
- Review extracted data before accepting it.
- Prefer clear operational behavior over hidden automation.
- Keep public demo infrastructure separate from private production infrastructure.
- Do not describe the application as HIPAA compliant without a complete organizational compliance program and appropriate review.

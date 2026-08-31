# Roadmap

CareQFlow is under active development. The core authorization workflow, local authentication, MFA, session hardening, governance controls, encrypted storage and backups, PDF-assisted intake, packaged Windows and Linux deployment workflows, controlled upgrades, and failed-upgrade rollback workflows are in place.

The current focus is release hardening, deployment validation, upgrade safety, maintainability, broader testing, and operational maturity.

This roadmap summarizes current direction rather than serving as a complete changelog.

## Current State

CareQFlow currently includes:

- Authorization record management
- Authorization timeline events
- Dashboard and calendar workflows
- Search and filtering
- Role-based access for Admin, UR, and Read Only users
- Local user management
- Argon2id password hashing
- TOTP multi-factor authentication
- Optional 30-day remembered-device MFA
- Admin MFA reset
- Single active authenticated session per account
- Server-side sessions and CSRF protection
- Configurable inactivity timeout with a 20-minute default
- Sliding session expiration
- Session expiration warnings and explicit renewal
- Cross-tab logout and expiration synchronization
- Versioned organization governance attestation
- Admin-only governance acceptance
- Append-only governance attestation history
- Field-level encryption for selected sensitive values
- SQLCipher database support
- Encrypted backups
- Backup verification and retention controls
- Staged restore and recovery workflows
- Local PDF-assisted intake
- Confidence and needs-review flags for extracted values
- Audit logging
- Tamper-evident audit chaining and integrity verification
- Production log sanitization
- Backend and frontend automated tests
- Packaged Windows installation
- Packaged Linux release archives
- Windows services for the API and HTTPS frontend
- Linux systemd services for the API, HTTPS frontend, and scheduled backups
- Private HTTPS through Caddy
- Installer modes for Install, Upgrade, Repair, Rollback, and Uninstall
- First-time Admin setup for packaged Windows and Linux deployments
- Windows scheduled backup support
- Linux systemd backup scheduling
- Versioned release tooling for Windows and Linux artifacts
- Failed-upgrade recovery records and verified pre-upgrade recovery assets
- Assisted Windows and Linux rollback workflows with post-rollback validation
- Version-based licensing with historical MIT releases and Business Source License 1.1 beginning with CareQFlow 0.5.0

Packaged production deployments keep the CareQFlow API bound to the loopback interface and use Caddy to serve the frontend and proxy `/api` requests through private HTTPS.

## Recently Completed

### Session security and MFA

Recent authentication and session work includes:

- TOTP MFA enrollment and verification
- Short-lived server-side MFA login challenges
- Optional remembered-device MFA
- Server-side trusted-device token protection
- Trusted-device revocation
- Single active authenticated session per account
- Configurable inactivity timeout
- Sliding session expiration
- Throttled browser activity reporting
- Session and CSRF token rotation during renewal
- Cross-tab session expiration synchronization
- Cross-tab logout synchronization
- Frontend session warnings backed by server-authoritative expiration

Remembered devices remain separate from authenticated session lifetime and do not create persistent signed-in sessions.

### Governance attestation

CareQFlow now includes a versioned organization governance workflow.

The current implementation includes:

- Admin-only organization attestation acceptance
- Required governance completion before normal protected application access
- Explicit acknowledgments covering organizational security and privacy responsibilities
- Separate acknowledgment that applicable BAAs and other agreements must be executed independently
- Organization and deployment-mode recording
- Accepting Admin identity
- Acceptance timestamp
- CareQFlow application version recording
- Governance attestation version and document revision recording
- Append-only attestation history
- Re-attestation support when the required governance attestation version or document revision changes
- Audit logging for governance acceptance
- Admin System visibility for current and historical attestations

The governance attestation version and governance document revision are independent from the CareQFlow application version. A normal application-version change does not by itself require re-attestation.

The workflow supports organizational accountability but does not itself execute a Business Associate Agreement, establish HIPAA compliance, or replace required administrative, physical, technical, contractual, or legal safeguards.

### Packaged Windows installer

The Windows installer supports:

- Fresh installation
- Upgrade over an existing installation
- Repair of an existing installation
- Rollback after an eligible failed upgrade
- Uninstall while preserving runtime data
- Fresh installation after uninstall using preserved data
- Production configuration and encryption-key preservation
- Post-installation service and health validation
- First-time Admin setup
- Existing-admin detection that disables repeat initial setup
- Private HTTPS through Caddy
- Windows service installation
- Scheduled encrypted backups
- Verified pre-upgrade database backups and previous-application archives
- Durable upgrade recovery records
- Rollback activation of the previous application and pre-upgrade database
- Post-rollback service and health validation

The installer packages application files, backend runtime files, frontend build output, Caddy, WinSW service wrappers, and the private Python runtime required by the backend.

### Packaged Linux deployment

CareQFlow now includes a versioned Linux release package for supported Debian-based systems.

The Linux deployment workflow includes:

- Versioned `CareQFlow-Linux-Setup-<version>.tar.gz` release archives
- Install, Upgrade, Repair, Rollback, and Uninstall modes
- Ubuntu and Debian validation
- Dedicated `carequeue` service account
- Production application and runtime directory creation
- Production Python environment creation
- Prebuilt frontend installation
- Production configuration and encryption-key creation
- Existing configuration preservation during upgrade and repair
- CareQFlow API systemd service
- CareQFlow Caddy systemd service
- Encrypted backup service and timer
- Private `careqflow.local` HTTPS deployment
- Caddy internal certificate trust setup
- Post-install frontend and API health validation
- First-time Admin setup
- Verified pre-upgrade database and application recovery assets
- Durable failed-upgrade recovery records
- Rollback of the previous application, database, systemd definitions, and installed-version metadata
- Post-rollback service, liveness, and readiness validation

Linux deployment remains more administrator-oriented than the Windows installer and should be validated on the exact target operating-system version before sensitive production use.

### Licensing transition

CareQFlow `0.5.0` begins a new source-available licensing phase.

The repository now distinguishes:

- CareQueue `0.4.x` and earlier releases under the MIT License
- CareQFlow `0.5.0` and later versions expressly released under Business Source License 1.1
- Non-production use under the applicable BSL terms
- Separate commercial licensing for production use while a release remains under the BSL
- Per-version Change Dates
- GNU GPL version 3 or later as the current Change License
- Historical MIT license preservation under `LICENSES/MIT.txt`
- Public licensing guidance under `docs/licensing.md`

Licensing documentation must remain consistent with the authoritative root `LICENSE` and applicable license texts.

### Backup and recovery

Current backup and recovery capabilities include:

- Separately encrypted backups
- Backup verification
- Retention periods
- Minimum protected backup counts
- Windows Task Scheduler integration
- Linux systemd scheduling
- Safe restore staging
- Controlled recovery activation
- Backup and recovery audit events
- Path validation for backup and recovery operations

### Security hardening

Recent security work includes:

- Shared server-side password policy enforcement
- Failed-login tracking and temporary account lockout
- TOTP MFA
- Remembered-device controls
- Single-session enforcement
- Inactivity-based session expiration
- Loopback-only first-time Admin setup
- Governance enforcement before protected application access
- Trusted storage path checks
- Safer directory enumeration
- Symlink rejection in sensitive file workflows
- Centralized validated file reads
- Field-level encryption
- SQLCipher support
- Separately encrypted backups
- Production log sanitization
- Tamper-evident audit chaining
- Audit integrity verification
- Bounded backend dependency requirements
- Backend and frontend dependency audit checks
- Static security scanning with Bandit
- Content Security Policy through Caddy
- Isolated PDF extraction with timeout handling
- Private same-origin production API requests
- Restricted production runtime directories
- Service-aware production upgrades
- Trusted production origin and host validation

## Next Priorities

### 1. Clean-machine release validation

Packaged releases should continue to be validated on clean virtual machines that do not contain the development environment.

The validation matrix should include supported Windows and Linux targets.

Windows validation should include:

- Fresh install
- First-time Admin setup
- Governance attestation
- Browser access through the packaged HTTPS origin
- MFA enrollment and login
- Remembered-device behavior
- Session inactivity timeout
- Basic authorization workflow smoke test
- Reboot and service auto-start
- Scheduled backup validation
- Repair
- Upgrade
- Failed-upgrade rollback
- Uninstall
- Confirmation that runtime data is preserved where documented
- Fresh install after uninstall using preserved data

Linux validation should include:

- Fresh install on each supported distribution/version
- First-time Admin setup
- Governance attestation
- Browser access through private HTTPS
- API and Caddy systemd service startup
- Reboot persistence
- Backup timer behavior
- Upgrade
- Repair
- Failed-upgrade rollback
- Uninstall
- File ownership and permission review
- Certificate trust behavior
- Health and readiness validation

Release artifacts should be tested from the exact package intended for publication.

### 2. Release signing and artifact trust

The release process should continue to improve artifact provenance and operator trust.

Remaining work includes:

- Define installer signing expectations
- Add code-signing guidance for Windows release artifacts
- Define release asset naming conventions
- Document pre-release versus stable release expectations
- Publish checksums for release artifacts
- Confirm the source tag matches each published artifact
- Preserve release-build logs where appropriate
- Document how release artifacts should be verified before installation

### 3. Production smoke-test tooling

A small production validation tool should check an installed CareQFlow deployment without exposing secrets.

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
- Expected application version
- Expected governance status availability

The tool should report clear pass/fail results and point operators to the relevant log locations.

### 4. Harden upgrade and rollback recovery

Assisted rollback is now implemented for packaged Windows and Linux upgrades.

Current recovery behavior includes:

- Verified pre-upgrade encrypted database backups
- Preserved previous-application archives
- Application archive SHA256 verification
- Versioned upgrade recovery records
- Durable rollback states
- Failed-application preservation
- Database staging and activation
- Service restart and post-rollback health validation
- Installed-version metadata restoration

Remaining work focuses on failure injection and operational resilience:

- Interrupted-upgrade testing at multiple cutover points
- Interrupted-rollback testing at multiple recovery states
- Recovery validation when service restart fails
- Recovery validation when health checks fail after database activation
- Clear operator guidance for incomplete durable rollback states
- Cross-release recovery drills using previously published artifacts
- Retention guidance for failed-application and recovery evidence
- Automated production smoke testing after upgrade and rollback

### 5. Validate cross-release migrations and recovery

CareQFlow now uses an ordered versioned database migration framework with explicit migration identifiers, a persistent migration ledger, per-migration savepoint rollback, and automated coverage for legacy-schema upgrades, current schemas, idempotency, and migration failure behavior.

Remaining work focuses on release-to-release compatibility rather than creating the migration framework itself.

Planned work includes:

- Representative upgrades from previously released CareQueue versions
- Upgrade validation using older production-style databases
- Cross-version backup and recovery testing
- Compatibility validation before and after migration-bearing upgrades
- Recovery testing after interrupted or failed upgrades
- Clear supported-version upgrade paths
- Supported-path validation for rollback to previously released application/database pairs
- Preservation and validation of verified pre-upgrade backups and application archives

### 6. Expand end-to-end browser testing

Frontend unit and component tests are in place.

The next testing layer should cover full browser workflows such as:

- Initial Admin setup
- Governance attestation
- Login and logout
- MFA enrollment
- MFA login
- Remembered-device login
- Single-session invalidation
- Session inactivity warning and expiration
- Cross-tab logout behavior
- Creating an authorization
- Editing an authorization
- Adding timeline events
- Filtering and dashboard interactions
- PDF intake review
- Role-based access
- User administration
- Audit integrity verification
- Backup and recovery administration
- Production same-origin behavior

All browser tests must use synthetic data.

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
- MFA workflows
- Governance attestation
- Session warning accessibility
- Administrative tables and history views

Accessibility should be reviewed alongside each major frontend workflow.

## Later Work

### Operational monitoring

Future operations work should include:

- Better service-health summaries
- Clearer failed-backup visibility
- Backup age warnings
- Service restart and failure alerts
- Disk-space monitoring
- Certificate-expiration awareness where applicable
- Centralized log-forwarding guidance
- Optional integration guidance for external monitoring or SIEM systems
- Operational runbooks for common incidents

### Backup operations

Future backup improvements include:

- Clear backup status view
- Improved failed-backup visibility
- Restore test guidance
- Off-host backup options
- Optional backup age warnings
- Retention review against operational needs
- Recovery testing from older backup versions
- Disaster-recovery exercises
- Stronger guidance for backup-key custody

### Audit and security monitoring

Future audit and monitoring improvements may include:

- Date-range audit filtering
- Resource-type filtering
- Resource-ID filtering
- IP-address filtering
- User-agent filtering
- Export workflows designed to avoid sensitive-data leakage
- External immutable audit-log forwarding
- SIEM integration guidance
- Security alert thresholds
- Administrative review workflows

Any external logging feature must be designed to avoid exporting PHI, credentials, authentication tokens, encryption keys, or other sensitive values unintentionally.

### Identity and account lifecycle

Future identity-management work may include:

- Single sign-on
- LDAP or Active Directory integration
- More granular remembered-device management
- Account expiration
- Stronger organization-level MFA policy controls
- Additional account-recovery workflows
- Administrative review of active sessions and trusted devices

These features should preserve the current backend-enforced authorization and audit boundaries.

### PDF intake

Future PDF intake improvements include:

- Additional payer and facility templates
- Improved confidence scoring
- Better detection of conflicting values
- More malformed-PDF tests
- Clearer review messages
- Optional local OCR evaluation without telemetry
- Synthetic fixtures for more document layouts

Any OCR or extraction expansion should remain local by default and must preserve the current requirement for human review before extracted values are committed.

### Linux deployment

The packaged Linux workflow is now implemented, but additional Linux maturity work remains:

- Broader supported-distribution testing
- Reboot, interrupted-upgrade, and interrupted-rollback testing
- More detailed package smoke testing
- Log rotation review
- Certificate lifecycle guidance
- Disaster-recovery activation testing
- More explicit hardening verification
- Additional installation troubleshooting documentation

## Release Philosophy

CareQFlow releases should be based on validated behavior rather than version number alone.

Before a release is considered stable:

- Automated backend and frontend tests should pass.
- Static and dependency security checks should pass according to the project's release process.
- Release artifacts should be built from the intended source revision.
- Clean-machine installation should be validated for supported deployment targets.
- Upgrade behavior should be tested when the release changes installed application behavior.
- Rollback behavior should be tested when release or migration changes affect recovery compatibility.
- Security-sensitive workflows should receive targeted manual checks.
- Documentation should describe the behavior of the release being published.
- Release packaging should carry the applicable licensing material for that release.
- Version-specific licensing statements should match the authoritative repository license.
- Release notes should distinguish implemented controls from remaining deployment and organizational responsibilities.

A new CareQFlow application version does not automatically imply a new governance attestation version or document revision. Governance requirements should be versioned independently when the attestation content or required acknowledgments change. A change to either the required attestation version or required document revision causes the existing acceptance to no longer be current.

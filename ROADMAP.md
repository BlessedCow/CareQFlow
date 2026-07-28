# Roadmap

CareQueue is an actively developed local-first utilization review workflow and authorization management application.

This roadmap describes the current direction of the project. It is not a guarantee that every item will be implemented, and priorities may change as security, usability, testing, deployment, and operational needs become clearer.

## Project Direction

CareQueue is focused on becoming a secure, maintainable, and well-documented healthcare workflow application that supports:

- Authorization tracking
- Review-date and follow-up workflows
- Timeline events
- Facility, payer, and portal management
- Role-based access
- Auditability
- Local PDF-assisted intake
- Encrypted storage
- Encrypted backups
- Controlled deployment
- Recovery planning
- Operational monitoring

CareQueue is not independently HIPAA compliant or production-ready.

Production use requires organizational safeguards, secure infrastructure, legal and compliance review, access policies, workforce training, incident response procedures, and operational oversight outside the application itself.

## Recently Completed

### Core application

- FastAPI backend API
- React, TypeScript, Vite, and Tailwind frontend
- Authorization dashboard
- Authorization work queue
- Filtering, sorting, and pagination
- Calendar workflow view
- Read-only authorization detail view
- Authorization create and edit workflows
- Authorization timeline events
- Continued-stay workflow support
- Level-of-care workflow support
- Work-queue filtering
- Registered facilities, insurers, and portal management
- Dashboard card preferences
- Workflow-view preferences
- Dark mode

### Authorization data

- Patient identity fields
- Member ID
- Group number
- Date of birth
- Review dates
- Start and end dates
- Authorization status
- Timeline events
- Decision and follow-up tracking
- Level-of-care normalization
- Legacy level-of-care handling
- Sensitive field mapping

### Authentication and authorization

- Argon2id password hashing
- Login and logout
- Current-session restoration
- Server-side session records
- Hashed session-token persistence
- Secure browser-managed session cookies
- CSRF protection
- Role-based access control
- Admin, UR, and Read Only roles
- Required password-change workflow
- Twenty-minute authenticated sessions
- Mandatory warning during the final five minutes
- Active-session renewal
- Optional bottom-right session countdown
- Session countdown preference that is off by default
- Automatic frontend data clearing after logout or expiration

### Audit and logging

- Audit logging for selected authentication actions
- Audit logging for authorization changes
- Audit logging for timeline-event changes
- Admin audit review page
- Centralized application logging
- PHI-conscious log sanitization
- Credential, cookie, token, and sensitive-field masking
- Exception-message and traceback reduction for production logging
- Logging integration tests

### Encryption and persistence

- Field-level encryption for selected sensitive authorization fields
- Optional SQLCipher database encryption
- SQLCipher migration scripts
- SQLCipher verification scripts
- SQLCipher cutover preparation
- Safe database-path validation
- Safe backup and restore path validation
- Domain-organized persistence modules
- Domain-owned table definitions
- Fixed parameterized SQL for controlled update operations
- SQL identifier validation where required

### PDF intake

- Local PDF text extraction
- Parser registry
- Structured extraction models
- Confidence indicators
- Needs-review flags
- Placeholder-value filtering
- Same-identifier fallback handling
- Review confirmation before accepting uncertain values
- Local inspection script
- In-memory processing
- No intentional PDF persistence
- PHI-conscious logging and audit boundaries

### Backup and recovery

- Separately encrypted database backups
- Safe restore utility
- Restore output isolation
- Backup and recovery documentation
- Windows backup runner
- Windows Task Scheduler installer
- Windows Task Scheduler removal script
- Manual Windows scheduled-task validation
- Linux systemd backup service
- Linux systemd backup timer
- Isolated backup destination guidance
- Service-account and environment-file guidance

### Testing and maintenance

- Domain-organized backend tests
- Security tests
- Authorization tests
- Audit tests
- Backup tests
- Configuration tests
- Database-encryption tests
- Observability tests
- PDF-intake tests
- Registered-option tests
- Schema tests
- Full backend pytest coverage across current modules
- Ruff checks
- Bandit security scans
- Frontend production build checks
- Updated project documentation

## Current Priorities

## 1. Frontend Automated Testing

The frontend currently relies primarily on TypeScript compilation, production builds, and manual verification.

The next major quality milestone is a structured frontend test suite.

### Planned coverage

- Login behavior
- Logout behavior
- Session restoration
- Session countdown formatting
- Session warning visibility
- Session renewal
- Automatic expiration
- Countdown preference persistence
- Mandatory warning when the countdown is hidden
- Role-based interface behavior
- Authorization filters
- Authorization form validation
- Timeline event workflows
- PDF intake review
- Needs-review confirmation
- Registered-option management
- Dashboard-card preferences
- Workflow-view preferences
- Loading states
- Empty states
- Error states
- Accessibility behavior

### Likely tooling

The final test framework should match the existing Vite and React structure.

Potential tooling may include:

- Vitest
- React Testing Library
- User Event
- Mock Service Worker
- Playwright for selected browser-level workflows

The project should avoid adding multiple overlapping test frameworks without a clear need.

### Testing structure

Frontend tests should be organized by feature or domain rather than placed in one large flat folder.

A possible structure:

```text
frontend/src/
├── api/
│   └── __tests__/
├── components/
│   ├── security/
│   │   └── __tests__/
│   └── pdf_intake/
│       └── __tests__/
├── hooks/
│   └── __tests__/
└── pages/
    └── __tests__/
```

The exact structure should follow the actual frontend modules when testing begins.

## 2. Deployment Readiness

CareQueue needs a documented and repeatable deployment model for both Windows and Linux.

### Windows deployment

Planned work includes:

- Document installation under `C:\Program Files\CareQueue`
- Store operational data under `C:\ProgramData\CareQueue`
- Document protected environment-file placement
- Document database directory permissions
- Document backup directory permissions
- Document dedicated service-account setup
- Add application startup automation
- Add frontend and backend service management
- Add reverse-proxy or local TLS guidance
- Add production log location guidance
- Add upgrade and rollback procedures
- Add uninstall procedures that preserve operational data
- Add deployment validation checklist

### Linux deployment

Planned work includes:

- Document installation under `/opt/carequeue`
- Document operational data under `/var/lib/carequeue`
- Document protected configuration under `/etc/carequeue`
- Add backend systemd service
- Add frontend serving guidance
- Add reverse-proxy guidance
- Add HTTPS and TLS configuration guidance
- Add service-account setup
- Add filesystem ownership and permissions
- Add log-review procedures
- Add deployment validation checklist
- Add upgrade and rollback procedures
- Add uninstall procedures that preserve operational data

### Deployment boundaries

Deployment documentation should clearly distinguish:

- Development configuration
- Local evaluation
- Controlled internal deployment
- Production deployment requirements

No deployment guide should imply that installation alone establishes HIPAA compliance.

## 3. Backup Verification Automation

A scheduled task reporting success does not prove that a usable backup exists.

CareQueue should automate verification of each newly created backup.

### Planned checks

- Confirm a new backup file was created
- Confirm the file is greater than zero bytes
- Confirm the filename matches the expected format
- Confirm the backup destination is outside the active database directory
- Confirm the file can be decrypted with the configured backup key
- Confirm the decrypted output has a valid database header
- Confirm the database can be opened
- Confirm expected tables exist
- Confirm the active database is not modified
- Remove temporary verification output securely
- Return a nonzero exit code on failure
- Record only PHI-safe operational results

### Planned verification script

A future script may be added under:

```text
backend/scripts/verify_encrypted_backup.py
```

It should verify a backup without replacing the active database.

### Scheduler integration

Windows and Linux backup jobs should eventually run:

```text
Create backup
  ↓
Verify backup
  ↓
Record safe success or failure result
```

Verification failures should cause the scheduled job to report failure.

## 4. Automated Backup Health Monitoring

CareQueue should make failed or missing backups visible to administrators.

### Planned monitoring behavior

- Track the most recent successful backup time
- Track the most recent failed backup time
- Track the most recent successful verification time
- Detect when no recent backup exists
- Detect repeated scheduler failures
- Detect zero-byte backup files
- Detect verification failures
- Detect backup-directory access failures
- Detect configuration or key failures
- Avoid logging keys, paths containing sensitive data, or decrypted values

### Possible outputs

- Windows Event Log entry
- systemd journal entry
- Restricted local health-status file
- Admin dashboard backup-health indicator
- Health-check endpoint restricted to administrators
- Optional email or webhook alerting after security review

External notifications should not include PHI, PII, encryption keys, database content, or sensitive filenames.

## 5. Backup Retention Policy Enforcement

CareQueue currently creates encrypted backups but does not automatically enforce retention.

A retention system should be deliberate, configurable, and tested before it deletes files.

### Planned retention options

- Keep the most recent number of backups
- Keep daily backups for a defined period
- Keep weekly backups for a defined period
- Keep monthly backups for a defined period
- Preserve manually protected recovery points
- Avoid deleting the only known valid backup
- Delete only files that match the expected CareQueue backup format
- Refuse to operate on the active database directory
- Support dry-run output
- Record safe deletion summaries
- Return failure when retention cannot be applied safely

### Example future configuration

```env
AUTHSTATUS_BACKUP_RETENTION_ENABLED=false
AUTHSTATUS_BACKUP_RETENTION_DAILY=14
AUTHSTATUS_BACKUP_RETENTION_WEEKLY=8
AUTHSTATUS_BACKUP_RETENTION_MONTHLY=12
```

Retention should remain disabled by default until thoroughly tested.

### Safety requirements

Retention logic must:

- Never delete the active database
- Never delete restore outputs outside the configured backup directory
- Never follow unexpected symbolic links
- Never delete unknown files
- Never delete protected recovery points
- Require explicit administrator configuration
- Support a preview or dry-run mode

## 6. Disaster Recovery Procedures

CareQueue needs a formal recovery runbook for database loss, corruption, host failure, key loss, and failed deployment.

### Planned documentation

- Recovery roles and responsibilities
- Recovery authorization procedure
- Recovery point objective
- Recovery time objective
- Backup selection procedure
- Backup decryption procedure
- Database verification procedure
- Application shutdown procedure
- Active database replacement procedure
- File ownership and permission restoration
- Application restart procedure
- Post-recovery verification
- Audit and incident documentation
- User notification responsibilities
- Failed-recovery rollback procedure
- Recovery test schedule

### Recovery scenarios

The runbook should address:

- Active database corruption
- Accidental database deletion
- Failed SQLCipher migration
- Failed application upgrade
- Lost deployment host
- Lost backup directory
- Lost field-encryption key
- Lost SQLCipher key
- Lost backup-encryption key
- Incorrect environment configuration
- Unauthorized access incident
- Ransomware or destructive malware
- Backup verification failure

### Recovery exercises

CareQueue should support documented restore drills using synthetic or approved test data.

A recovery exercise should verify:

- The backup can be located
- The backup can be decrypted
- The database can be opened
- Expected tables exist
- Application startup succeeds
- Authentication works
- Authorization records can be read
- Encrypted fields can be decrypted
- Audit records remain accessible
- The active production database was not modified during the test

## 7. Administrative and Operational Documentation

CareQueue needs a complete operational documentation set.

### Planned documents

```text
docs/
├── deployment/
│   ├── linux-systemd.md
│   └── windows.md
├── operations/
│   ├── administrative-access.md
│   ├── backup-health-monitoring.md
│   ├── backup-retention.md
│   ├── disaster-recovery.md
│   ├── incident-response.md
│   ├── key-management.md
│   └── recovery-runbook.md
├── security/
│   ├── production-readiness.md
│   └── secure-deployment-checklist.md
└── workflows/
    └── backup-and-recovery.md
```

### Administrative access policy

Planned topics:

- Who may create users
- Who may assign roles
- Who may access audit logs
- Who may access backups
- Who may access encryption keys
- Who may restore a database
- User approval process
- User termination process
- Periodic access review
- Temporary access
- Emergency administrative access
- Shared-account prohibition
- Service-account ownership

## 8. Secure Deployment and HTTPS

CareQueue currently does not include a complete production HTTPS deployment package.

### Planned work

- Reverse-proxy reference configuration
- TLS certificate configuration
- HTTP-to-HTTPS redirect
- Secure cookie validation behind the proxy
- Trusted proxy configuration
- HSTS guidance
- CORS production configuration
- Allowed-host validation
- Request-size limits
- Upload-size limits
- Rate limiting research
- Security-header configuration
- Firewall guidance
- Local-network-only deployment option
- Production environment validation

Potential supported reverse proxies may include:

- Nginx
- Caddy
- IIS
- Apache

A single supported reference deployment should be completed before documenting many alternatives.

## 9. Secret Management

Current deployments rely on protected environment files.

Longer-term work should evaluate secure secret storage.

### Possible integrations

- Windows Credential Manager
- Windows DPAPI
- systemd credentials
- Linux secret files with restricted permissions
- HashiCorp Vault
- AWS Secrets Manager
- Azure Key Vault
- Google Secret Manager

Any secret-manager integration must avoid:

- Logging secret values
- Passing keys in command-line arguments
- Persisting decrypted keys unnecessarily
- Exposing keys to frontend code
- Reusing keys between encryption layers

## 10. Key Rotation Procedures

CareQueue uses separate keys for:

- Field-level encryption
- SQLCipher database encryption
- Backup encryption

Each key requires a documented rotation process.

### Planned work

- Field-encryption key rotation utility
- SQLCipher rekey procedure
- Backup-key rotation procedure
- Transitional support for old and new backup keys
- Verification before key retirement
- Recovery test after rotation
- Audit record for approved rotations
- Rollback procedure
- Key ownership documentation

No key should be rotated without a verified backup and recovery plan.

## 11. Incident Response

CareQueue needs an operational incident-response guide.

### Planned incident categories

- Suspected credential exposure
- Suspected encryption-key exposure
- Unauthorized login
- Authorization bypass
- PHI or PII exposure
- Sensitive log exposure
- Database theft
- Backup theft
- Malicious PDF upload
- Ransomware
- Host compromise
- Failed backup schedule
- Failed restore
- Lost device
- Misconfigured deployment

### Planned response stages

- Detect
- Contain
- Preserve evidence
- Revoke access
- Rotate affected secrets
- Assess data exposure
- Restore service
- Notify responsible parties
- Document the incident
- Review safeguards
- Prevent recurrence

Legal notification requirements are outside the application and must be handled by the deploying organization.

## 12. Admin Access Review Tools

CareQueue should improve administrative oversight.

### Planned features

- Active-user list
- Disabled-user list
- Role review
- Last login time
- Last session time
- Active-session list
- Revoke one session
- Revoke all sessions for a user
- Require password reset
- Disable account
- Re-enable account
- Access-review export using non-sensitive metadata
- Administrative action audit trail

Any export must avoid unnecessary PHI or PII.

## 13. Audit Review Improvements

Audit records are available, but review workflows can improve.

### Planned features

- Date filtering
- User filtering
- Action filtering
- Resource filtering
- Success and failure filtering
- Pagination
- Safe export
- Retention configuration
- Integrity review
- Suspicious authentication pattern review
- Repeated failure detection
- Administrator review notes

Audit exports must not contain sensitive field values.

## 14. PDF Intake Expansion

The current PDF intake workflow supports text-based extraction and review.

### Planned work

- Additional payer templates
- Additional facility templates
- Better phone-number extraction
- Better authorization-contact extraction
- Better initial-admit-date extraction
- Better member and group identifier extraction
- More parser confidence tests
- Better malformed-PDF handling
- Better unsupported-template feedback
- Local OCR evaluation for scanned documents
- OCR telemetry review
- Temporary-file review
- Model-download review
- Performance limits
- File-size limits
- Page-count limits
- Parser-version reporting

Local OCR should not be added until privacy, telemetry, storage, and dependency behavior are reviewed.

## 15. Frontend Accessibility

CareQueue should receive a structured accessibility review.

### Planned work

- Keyboard-only navigation
- Visible focus states
- Modal focus trapping
- Modal focus restoration
- Screen-reader labels
- Table accessibility
- Form-error announcements
- Countdown announcement behavior
- Color-contrast review
- Dark-mode contrast review
- Reduced-motion support
- Accessible chart summaries
- Accessible loading and empty states

The session warning must remain usable without a mouse.

## 16. API and Application Hardening

Additional backend hardening should be evaluated.

### Planned work

- Allowed-host validation
- Request-size limits
- Upload-size limits
- Rate limiting
- Login throttling
- Account lockout research
- Security headers
- Dependency vulnerability scanning
- Structured error codes
- Safer production startup validation
- Configuration self-check command
- Database health check
- Backup health check
- Readiness endpoint
- Liveness endpoint
- Protected administrative diagnostics

Health endpoints must not expose sensitive configuration or internal paths.

## 17. Release and Upgrade Process

CareQueue needs a repeatable release process.

### Planned work

- Versioning policy
- Release notes
- Database migration checklist
- Pre-upgrade backup
- Backup verification
- Upgrade procedure
- Rollback procedure
- Frontend build procedure
- Backend dependency lock strategy
- Deployment artifact strategy
- Configuration migration notes
- Post-upgrade verification
- Release signing research

## 18. Data Export and Reporting Safety

Future reporting features should minimize sensitive-data exposure.

### Possible work

- Authorization summary reports
- Facility workload reports
- Payer workload reports
- Level-of-care reports
- Review-due reports
- Denial and appeal reports
- Operational metrics
- Safe CSV export
- Export authorization checks
- Export audit events
- Export expiration
- Watermarking research
- Restricted export directories

Exports containing PHI or PII must be treated as sensitive records and protected accordingly.

## 19. Documentation and Screenshots

The public repository should become easier to understand without exposing sensitive data.

### Planned work

- Sanitized dashboard screenshot
- Sanitized authorization table screenshot
- Sanitized timeline screenshot
- Sanitized PDF review screenshot
- Sanitized session-warning screenshot
- Sanitized settings screenshot
- Windows deployment walkthrough
- Linux deployment walkthrough
- Backup verification walkthrough
- Recovery exercise walkthrough
- Admin-access policy
- Security checklist
- Documentation index

Screenshots must use entirely synthetic data.

Store approved screenshots under:

```text
docs/assets/screenshots/
```

## Near-Term Milestones

The recommended implementation order is:

### Milestone 1: Frontend testing foundation

- Select frontend test framework
- Configure test environment
- Add session timeout tests
- Add login and logout tests
- Add timer-preference tests
- Add PDF intake review tests
- Add CI-ready frontend test command

### Milestone 2: Backup verification automation

- Add encrypted-backup verification script
- Add tests
- Integrate verification with Windows runner
- Integrate verification with Linux service
- Return scheduler failure when verification fails

### Milestone 3: Backup health monitoring

- Record safe backup-health status
- Detect missing recent backups
- Detect verification failures
- Add administrator-visible status
- Document operational review

### Milestone 4: Retention policy

- Define configuration
- Add dry-run behavior
- Add safe file-selection logic
- Add retention tests
- Add scheduler integration
- Document retention and recovery-point protection

### Milestone 5: Disaster recovery

- Create recovery runbook
- Add restore-drill procedure
- Document active database replacement
- Document rollback
- Record recovery exercise results

### Milestone 6: Deployment guides

- Complete Windows deployment guide
- Complete Linux deployment guide
- Add HTTPS reference deployment
- Add permissions and service-account setup
- Add upgrade and rollback guidance

### Milestone 7: Operational security

- Administrative access policy
- Incident-response guide
- Key-management guide
- Access-review procedures
- Audit-review procedures
- Production-readiness checklist

## Longer-Term Ideas

These items may be considered after the near-term operational and testing milestones.

### Workflow improvements

- Better payer contact tracking
- Better authorization phone-number tracking
- Better portal tracking
- Better follow-up queues
- Denial tracking
- Appeal tracking
- Peer-to-peer review tracking
- Discharge workflow
- Completed authorization workflow
- More detailed facility reporting
- More detailed payer reporting
- More detailed level-of-care reporting
- Workload forecasting

### Identity and access

- External identity provider
- Single sign-on
- Multi-factor authentication
- Directory integration
- Centralized access review
- Conditional access
- Device-aware access
- Administrative approval workflows

### Deployment and infrastructure

- Container deployment research
- Managed database research
- Cloud backup integration
- Off-host encrypted backup replication
- Infrastructure-as-code
- Centralized monitoring
- Centralized logging
- High-availability research
- Multi-site recovery research

### Product maturity

- Formal versioning
- Release automation
- Migration compatibility policy
- Security review
- Penetration testing
- Threat modeling
- Privacy-impact assessment
- Formal compliance review
- User documentation
- Administrator training materials

## Out of Scope for Now

The following are not current priorities:

- Public multi-tenant SaaS hosting
- Replacing payer portals
- Automatically making medical necessity determinations
- Providing clinical recommendations
- Providing legal advice
- Providing billing advice
- Claiming HIPAA compliance based only on software features
- Processing real PHI or PII without appropriate approval and safeguards
- Sending sensitive PDFs to external AI or OCR services without formal review
- Automatic deletion of backups before retention safeguards are implemented
- Automatic active-database replacement during restore
- Multi-tenant data isolation
- Consumer self-registration

## Roadmap Principles

CareQueue roadmap decisions should follow these principles:

- Protect sensitive data
- Prefer server-enforced security controls
- Keep PHI and PII out of logs and audit metadata
- Use separate encryption keys for separate protection layers
- Verify backups instead of assuming success
- Test restoration instead of assuming recoverability
- Require explicit review before deleting backups
- Keep deployment configuration documented
- Keep administrative access limited
- Keep changes small and reviewable
- Organize code and tests by domain
- Use synthetic data in tests and documentation
- Avoid unnecessary dependencies
- Avoid external telemetry for sensitive workflows
- Document limitations honestly
- Do not represent technical safeguards as complete regulatory compliance
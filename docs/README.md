# CareQFlow Documentation

This directory contains CareQFlow’s detailed deployment, operations, administration, workflow, development, security, licensing, and troubleshooting documentation.

The root-level documents provide the project overview:

```text
README.md
ARCHITECTURE.md
SECURITY.md
ROADMAP.md
LICENSE
```

The files under `docs/` provide task-specific guidance.

## Start Here

### Project Overview

See:

```text
../README.md
```

Use it for:

- Project purpose
- Main workflows
- Technology stack
- Local development overview
- Production overview
- Testing summary
- Security summary
- Licensing summary

### Architecture

See:

```text
../ARCHITECTURE.md
```

Use it for:

- Frontend and backend structure
- Authentication, MFA, session, and governance flow
- Database and encryption boundaries
- Backup and recovery architecture
- PDF intake architecture
- Windows and Linux production services
- Current architectural limitations

### Security

See:

```text
../SECURITY.md
```

Use it for:

- Security reporting
- Sensitive-data rules
- Authentication, MFA, and roles
- Single-session, inactivity-timeout, and CSRF controls
- Remembered-device MFA behavior
- Governance attestation boundaries
- Encryption and key handling
- Backup security
- PDF security
- Logging and audit boundaries
- Production responsibilities

### Threat Model and Risk Register

See:

```text
security/threat-model-and-risk-register.md
```

Use it for:

- Protected assets and security objectives
- Threat actors and attacker capabilities
- Application and deployment trust boundaries
- Representative abuse cases
- Existing security controls
- Residual security risks
- Risk likelihood and impact assessment
- Planned mitigations and remediation priorities
- Security review triggers
- Security roadmap risk mapping

### Roadmap

See:

```text
../ROADMAP.md
```

Use it for:

- Current state
- Completed work
- Near-term priorities
- Longer-term plans
- Known limitations

### Licensing

See:

```text
licensing.md
```

Use it for:

- Historical MIT releases
- Business Source License 1.1 releases
- Non-production use
- Production-use requirements
- Commercial licensing
- Source availability and auditing
- Change Dates
- Contribution licensing

The authoritative licensing notice is:

```text
../LICENSE
```

The applicable license texts are stored under:

```text
../LICENSES/
```

## Deployment

### Windows

See:

```text
deployment/windows.md
```

Use it for:

- Packaged Windows installer flow
- Install, Upgrade, Repair, Rollback, and Uninstall modes
- First-time Admin setup GUI
- Runtime and application paths
- Private hostname setup
- API and Caddy services
- HTTPS and certificate trust
- Scheduled backups
- Service management
- Runtime data preservation
- Failed-upgrade recovery records
- Pre-upgrade application and database recovery assets
- Rollback validation and recovery completion
- Removal and reinstallation

This is the primary production deployment guide.

The packaged Windows installer is intended to be the normal private Windows installation path. The lower-level PowerShell scripts remain useful for development, troubleshooting, and direct validation of installer modes.

Rollback is offered by the Windows installer only when an eligible failed-upgrade recovery record is available. The rollback workflow validates required recovery assets before restoring the previous application and database state.

### Linux

See:

```text
deployment/linux.md
```

Use it for:

- Versioned Linux release packages
- Install, Upgrade, Repair, Rollback, and Uninstall modes
- Dedicated service account
- Application, configuration, data, and log paths
- Production environment and encryption-key setup
- CareQFlow API and Caddy systemd services
- Private HTTPS and certificate trust
- Encrypted backup service and timer
- First-time Admin setup
- Governance setup after first login
- Failed-upgrade recovery and rollback workflow
- Current Linux limitations

CareQFlow includes a packaged Linux installation workflow for supported Debian-based systems. Linux deployment remains more administrator-oriented than the Windows installer and should be validated on the exact target operating-system version before sensitive production use.

## Operations

### Upgrades

See:

```text
operations/upgrades.md
```

Use it for:

- Pre-upgrade checks
- Required tests
- Backup confirmation
- Packaged installer upgrade mode
- Direct PowerShell upgrade validation
- Service stop and start order
- Installed file replacement
- Environment preservation
- Backend validation
- Permission hardening
- Failure handling
- Pre-upgrade recovery asset creation
- Failed-upgrade recovery records
- Rollback activation
- Post-rollback health validation

### Health Checks

See:

```text
operations/health-checks.md
```

Use it for:

- Liveness
- Readiness
- Service status
- Direct API checks
- HTTPS checks
- Certificate and hostname checks
- Post-installation smoke tests
- Post-upgrade smoke tests
- Post-recovery smoke tests
- Monitoring guidance

## Administration

### Users and Security

See:

```text
administration/users-and-security.md
```

Use it for:

- First-time Admin setup
- Governance attestation after first Admin login
- User creation
- Roles
- Temporary passwords
- Password resets
- Required password changes
- TOTP MFA enrollment and reset
- Remembered-device MFA behavior
- Single active sessions
- Inactivity timeout and session renewal
- Cross-tab logout and expiration behavior
- CSRF behavior
- Deactivation
- Offboarding

### Audit Log

See:

```text
administration/audit-log.md
```

Use it for:

- Audit-event structure
- Action names
- Filters
- Metadata rules
- Review workflow
- Retention
- Integrity limitations
- Current interface limitations

### Registered Options

See:

```text
administration/registered-options.md
```

Use it for:

- Facilities
- Insurances
- Web portals
- Protected `Other` values
- Normalization
- Duplicate handling
- PDF intake matching
- Filter behavior
- Maintenance

## Workflows

### Authorization Workflow

See:

```text
workflows/authorization-workflow.md
```

Use it for:

- Authorization fields
- Record creation
- Editing
- Deletion
- Queue behavior
- Filters
- Dashboard and calendar interaction
- Timeline events
- Current-state versus history

### PDF Intake

See:

```text
workflows/pdf-intake.md
```

Use it for:

- Supported PDF behavior
- Template matching
- Fillable fields
- Embedded text
- Confidence levels
- Needs-review flags
- Member and group identifier selection
- Registered-option matching
- Local inspection tooling
- Synthetic fixtures
- Future OCR considerations

### Backup and Recovery

See:

```text
workflows/backup-and-recovery.md
```

Use it for:

- Manual encrypted backups
- Backup verification
- Retention
- Windows scheduled backups
- Linux scheduled backups
- Restore staging
- Recovery preflight
- Recovery activation
- Rollback databases
- Safety backups
- Pre-upgrade backups
- Upgrade recovery assets
- Failed-upgrade rollback
- Recovery drills
- Key-loss risks

## Development

### Local Development

See:

```text
development/local-development.md
```

Use it for:

- Backend setup
- Frontend setup
- Development environment
- Local keys
- Database mode
- First local user
- Synthetic seed data
- Tests
- Ruff
- Frontend build
- Local reset and dependency recreation

### Command Reference

See:

```text
development/command-reference.md
```

Use it for:

- Local backend start commands
- Local frontend start commands
- Concurrent backend and frontend runs
- Installed Windows app start and stop commands
- Health checks
- Windows installer build and repair commands
- Linux release-package build commands
- Release-version bump commands
- Checksum commands
- Security and test commands
- Common URLs and runtime paths

## Troubleshooting

See:

```text
troubleshooting/index.md
```

Use it to locate the authoritative guide for:

- Startup problems
- HTTPS or certificate problems
- Login and session problems
- Database problems
- Backup and recovery problems
- Installer failures
- Upgrade failures
- Rollback failures
- Repair failures
- Uninstall or reinstall issues
- PDF intake issues
- Registered-option issues
- Audit issues
- Local development failures

The troubleshooting page is a symptom-based index. It intentionally links to the documents that own each procedure rather than duplicating them.

## Documentation Structure

```text
docs/
├── README.md
├── licensing.md
├── administration/
│   ├── audit-log.md
│   ├── registered-options.md
│   └── users-and-security.md
├── deployment/
│   ├── linux.md
│   └── windows.md
├── development/
│   ├── command-reference.md
│   └── local-development.md
├── operations/
│   ├── health-checks.md
│   └── upgrades.md
├── security/
│   └── threat-model-and-risk-register.md
├── troubleshooting/
│   └── index.md
└── workflows/
    ├── authorization-workflow.md
    ├── backup-and-recovery.md
    └── pdf-intake.md
```

## Documentation Conventions

### Commands

State the working directory when it changes.

Windows commands use PowerShell unless otherwise noted.

Linux commands use a POSIX-compatible shell unless otherwise noted.

### Paths

Repository-relative paths:

```text
backend/authstatus_api/
frontend/src/
deployment/windows/
deployment/linux/
```

Installed Windows paths:

```text
C:\Program Files\CareQueue
C:\ProgramData\CareQueue
```

Installed Linux paths:

```text
/opt/carequeue
/var/lib/carequeue
/etc/carequeue
```

### Sensitive Values

Documentation must not contain:

- Real patient information
- Real member IDs
- Real group numbers
- Real dates of birth
- Real authorization numbers
- Credentials
- Passwords
- Session tokens
- CSRF tokens
- Encryption keys
- Authentication cookies
- Production environment contents
- Real database contents
- Real intake documents
- Commercial-license credentials or private contract information

Use clearly synthetic examples.

### Screenshots

Screenshots must use synthetic data only.

Screenshots are stored under:

```text
docs/images/
```

## Licensing Documentation

Licensing statements in public documentation must remain consistent with:

```text
LICENSE
LICENSES/
docs/licensing.md
```

CareQueue versions `0.4.x` and earlier were released under the MIT License.

CareQFlow version `0.5.0` and later versions expressly released under the current terms use the Business Source License 1.1 until the applicable Change Date.

Current BSL releases are source-available and should not be described as Open Source before the applicable Change Date.

Do not imply that public source availability grants unrestricted production use.

Commercial licensing terms should not be invented or inferred in documentation. Only rights actually granted by the applicable public license or a separate commercial agreement should be described as granted.

## Updating Documentation

Update documentation when a change affects:

- Installation
- Configuration
- Runtime paths
- Service names
- Environment variables
- Security behavior
- Roles or permissions
- Authorization workflows
- Backup behavior
- Recovery behavior
- Upgrade or rollback behavior
- PDF intake behavior
- Installer behavior
- Release packaging
- Licensing or distribution terms
- Testing commands
- Known limitations
- Operator responsibilities

Do not leave obsolete commands, filenames, paths, screenshots, licensing statements, or deployment procedures in the repository.

## Review Checklist

Before merging documentation changes:

- Paths match the current repository
- Service names match deployment files
- Commands use current script names
- Environment-variable names are correct
- Internal links resolve
- Licensing statements match the authoritative repository license
- Version-specific license boundaries are stated accurately
- Current BSL releases are not incorrectly described as Open Source
- Security claims are limited and accurate
- No HIPAA compliance claim is made
- No real PHI or PII is present
- No key or credential is present
- Headings are clear
- Repeated content is intentional
- Screenshots use synthetic data
- Current limitations are stated where needed
- Examples match current behavior

## Testing Documentation Changes

Markdown-only changes do not require pytest by themselves.

When documentation accompanies code changes, run the relevant checks.

Backend:

```powershell
pytest backend\tests -n auto -q
ruff check . --fix
```

Frontend:

```powershell
npm audit
npm test
npm run build
```

Deployment documentation should also be validated against the relevant manual workflow.

Licensing documentation changes should be reviewed against:

```text
LICENSE
LICENSES/BUSL-1.1.txt
LICENSES/MIT.txt
docs/licensing.md
```

## Reference Point

The current repository files remain authoritative.

When documentation and code disagree:

1. Review the current source.
2. Confirm whether behavior changed.
3. Update the documentation or implementation.
4. Add tests when the mismatch reflects missing coverage.

When licensing documentation and the applicable license terms disagree, the applicable license terms control.

Do not rely on old screenshots, copied commands, previous release notes, or historical licensing summaries without checking the current repository.

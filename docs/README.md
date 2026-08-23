# CareQueue Documentation

This directory contains CareQueue’s detailed deployment, operations, administration, workflow, development, and troubleshooting documentation.

The root-level documents provide the project overview:

```text
README.md
ARCHITECTURE.md
SECURITY.md
ROADMAP.md
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

## Deployment

### Windows

See:

```text
deployment/windows.md
```

Use it for:

- Packaged Windows installer flow
- Install, Upgrade, Repair, and Uninstall modes
- First-time Admin setup GUI
- Runtime and application paths
- Private hostname setup
- API and Caddy services
- HTTPS and certificate trust
- Scheduled backups
- Service management
- Runtime data preservation
- Removal and reinstallation

This is the primary production deployment guide.

The packaged Windows installer is intended to be the normal private Windows installation path. The lower-level PowerShell scripts remain useful for development, troubleshooting, and direct validation of installer modes.

### Linux

See:

```text
deployment/linux.md
```

Use it for:

- Versioned Linux release packages
- Install, Upgrade, Repair, and Uninstall modes
- Dedicated service account
- Application, configuration, data, and log paths
- Production environment and encryption-key setup
- CareQueue API and Caddy systemd services
- Private HTTPS and certificate trust
- Encrypted backup service and timer
- First-time Admin setup
- Governance setup after first login
- Current Linux limitations

CareQueue includes a packaged Linux installation workflow for supported Debian-based systems. Linux deployment remains more administrator-oriented than the Windows installer and should be validated on the exact target operating-system version before sensitive production use.

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
- Rollback planning

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

Use clearly synthetic examples.

### Screenshots

Screenshots must use synthetic data only.

Screenshots are stored under:

```text
docs/images/
```

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
- PDF intake behavior
- Installer behavior
- Release packaging
- Testing commands
- Known limitations
- Operator responsibilities

Do not leave obsolete commands, filenames, paths, or screenshots in the repository.

## Review Checklist

Before merging documentation changes:

- Paths match the current repository
- Service names match deployment files
- Commands use current script names
- Environment-variable names are correct
- Internal links resolve
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

## Reference point

The current repository files remain authoritative.

When documentation and code disagree:

1. Review the current source.
2. Confirm whether behavior changed.
3. Update the documentation or implementation.
4. Add tests when the mismatch reflects missing coverage.

Do not rely on old screenshots, copied commands, or previous release notes without checking the current repository.

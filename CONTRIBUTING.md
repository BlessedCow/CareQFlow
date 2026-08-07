# Contributing to CareQueue

Thank you for your interest in contributing to CareQueue.

CareQueue is a local-first utilization review workflow and authorization management application focused on authorization tracking, payer and facility workflows, timeline events, documentation intake, encrypted storage, audit logging, session security, and operational backup support.

The project is actively evolving. Contributions should remain focused, reviewable, privacy-conscious, and consistent with the existing repository structure.

## Project Status

CareQueue is under active development.

Application structure, deployment guidance, security controls, release packaging, and workflow behavior may continue to change as the project matures.

Contributions are welcome, but new work should:

- Solve a clear problem
- Match the existing architecture
- Avoid unnecessary abstraction
- Preserve privacy and security controls
- Include appropriate tests
- Update documentation when behavior changes
- Remain easy to review and maintain

## Ways to Contribute

Contributions may include:

- Reporting bugs
- Suggesting workflow improvements
- Improving documentation
- Adding or improving tests
- Refactoring existing code for clarity
- Improving frontend accessibility or usability
- Improving backend validation
- Improving API behavior
- Improving database or persistence behavior
- Improving PDF intake parsing
- Improving audit and logging safety
- Improving deployment or backup tooling
- Improving security controls
- Improving synthetic development data and examples

## Before Contributing

Before opening a pull request:

1. Review the existing issues and pull requests.
2. Confirm that the change is not already being worked on.
3. Keep the change focused on one logical improvement.
4. Review the surrounding code before adding new modules or abstractions.
5. Avoid unrelated formatting or naming changes.
6. Add or update tests when behavior changes.
7. Update documentation when setup, behavior, security, or deployment changes.
8. Confirm that no secrets or sensitive data are included.
9. Run the relevant test and static-analysis commands.
10. Review the final staged files before committing.

Use:

```bash
git status --short
```

and:

```bash
git diff --cached
```

to inspect the pending commit.

## Privacy and Data Safety

CareQueue is designed for healthcare-related workflows, so privacy requirements apply to all contributions.

Do not submit:

- Protected health information
- Personally identifiable information
- Real patient or client names
- Real dates of birth
- Real member IDs
- Real group numbers
- Real payer authorization identifiers tied to identifiable people
- Real clinical notes
- Real treatment details
- Real facility information that is not public
- Real employer records
- Internal payer documents
- Login credentials
- Passwords
- Temporary passwords
- API keys
- Encryption keys
- Session tokens
- CSRF tokens
- Authentication cookies
- SQLCipher databases
- Plaintext SQLite databases containing sensitive information
- Encrypted backup files
- Restored database files
- Production logs
- Real intake PDFs
- Screenshots containing sensitive information
- Environment files containing secrets

Use fictional or clearly synthetic data for:

- Tests
- Screenshots
- Documentation
- Demonstrations
- Bug reports
- Pull requests
- PDF fixtures
- Example databases
- Development seed data

Do not rely on blur effects or partial redaction when a clean synthetic example can be created.

## Screenshots

Screenshots for documentation or pull requests must use synthetic data only.

Before committing a screenshot, inspect it at full resolution for:

- Real names
- Member IDs
- Group numbers
- Dates of birth
- Authorization identifiers
- Facility names
- Payer data
- Clinical notes
- Browser autofill
- Local usernames
- Machine names
- File paths
- Environment values
- Terminal history
- Credentials
- Encryption keys

Approved repository screenshots should be placed under:

```text
docs/assets/screenshots/
```

Use descriptive filenames such as:

```text
dashboard-overview.png
authorization-timeline.png
pdf-intake-review.png
session-timeout-warning.png
settings-session-timer.png
```

## Local Files and Generated Artifacts

Do not commit local runtime files, generated files, caches, or sensitive configuration.

Examples include:

```text
.env
backend/data/
backend/backups/
backend/restores/
local_backups/
local_config/
local_vobs/
*.db
*.sqlite
*.sqlite3
*.db.enc
*.restored.db
frontend/node_modules/
backend/.venv/
__pycache__/
.pytest_cache/
.ruff_cache/
```

Do not commit:

- Production databases
- Development databases containing real data
- Generated backups
- Restored databases
- Real intake PDFs
- Exported reports
- Environment files
- Local service-account credentials
- Scheduler-generated logs
- Temporary debug files

Build outputs should normally remain uncommitted unless a release process specifically requires an artifact outside the repository source tree.

## Repository Organization

CareQueue is organized by application domain.

Backend source:

```text
backend/authstatus_api/
├── audit/
├── authorizations/
├── backups/
├── database_encryption/
├── observability/
├── pdf_intake/
├── persistence/
├── registered_options/
├── routers/
└── security/
```

Backend tests:

```text
backend/tests/
├── audit/
├── authorizations/
├── backups/
├── configuration/
├── database_encryption/
├── observability/
├── pdf_intake/
├── registered_options/
├── schemas/
├── security/
└── conftest.py
```

Frontend source:

```text
frontend/src/
├── api/
├── components/
├── hooks/
├── pages/
├── types/
└── utils/
```

Deployment helpers:

```text
deployment/
├── linux/
│   └── systemd/
└── windows/
```

Documentation:

```text
docs/
├── administration/
├── assets/
│   └── screenshots/
├── deployment/
├── development/
├── operations/
├── troubleshooting/
└── workflows/
```

New files should be placed with the domain they support.

Avoid adding many flat files with repeated prefixes when a shared package or folder would make the structure clearer.

Do not create a new folder for every small helper. Prefer practical grouping over excessive nesting.

## Development Setup

Clone the repository:

```bash
git clone https://github.com/BlessedCow/CareQueue.git
cd CareQueue
```

Use the root README and the local development guide for current setup instructions.

The developer environment and the packaged Windows installer are separate workflows:

- Developer setup runs the backend and frontend directly from source.
- The packaged Windows installer installs service-managed runtime files under the Windows installation directory and stores operational data under `C:\ProgramData\CareQueue`.
- Installer build and validation details belong in the Windows deployment guide.

### Backend

Create and activate a virtual environment, then install dependencies according to the root README.

Run backend checks from the `backend` directory unless a specific command says otherwise.

### Frontend

Install dependencies:

```bash
cd frontend
npm install
```

Start the development server:

```bash
npm run dev
```

## Code Style

Keep code readable, typed where practical, and consistent with the surrounding modules.

General expectations:

- Use clear names.
- Keep functions focused.
- Keep changes small and reviewable.
- Avoid unrelated formatting churn.
- Avoid unnecessary dependencies.
- Prefer straightforward solutions over clever abstractions.
- Reuse existing helpers and domain modules where appropriate.
- Keep routers thin.
- Keep persistence logic out of frontend code.
- Keep security decisions enforced by the backend.
- Avoid duplicating logic across modules.
- Add tests when changing behavior.
- Update documentation when behavior or setup changes.
- Avoid comments that speculate about future work.
- Avoid personal names or private details in source code, comments, examples, and test data.

## Backend Guidelines

Backend code lives under:

```text
backend/authstatus_api/
```

When adding backend behavior:

- Use the existing domain package when one exists.
- Keep request handling in routers.
- Keep persistence behavior in the relevant repository or domain module.
- Use parameterized SQL.
- Do not construct SQL from unvalidated user input.
- Use existing security dependencies.
- Preserve CSRF checks for authenticated state-changing requests.
- Do not expose internal exception details to clients.
- Do not log request bodies containing sensitive data.
- Keep audit metadata minimal and free of PHI or PII.
- Add schema validation for new request and response fields.
- Preserve SQLCipher and plaintext test compatibility where applicable.
- Use safe path validation for database, backup, restore, and intake paths.

## Frontend Guidelines

Frontend code lives under:

```text
frontend/src/
```

When adding frontend behavior:

- Use existing API clients under `frontend/src/api`.
- Keep application-wide state in the existing top-level flow when appropriate.
- Move reusable stateful logic into hooks.
- Keep page components focused on composition.
- Keep reusable visual behavior in components.
- Use TypeScript types for API contracts.
- Do not store session tokens in application state.
- Do not store PHI or PII in browser persistence.
- Store only non-sensitive display preferences locally.
- Treat frontend permission checks as interface behavior, not security enforcement.
- Preserve keyboard navigation and accessible labels.
- Preserve dark-mode behavior.
- Confirm loading, empty, error, and disabled states.

## Session and Authentication Changes

Changes to authentication or session behavior require focused review.

Confirm that:

- Raw session tokens remain in HttpOnly cookies.
- Session hashes remain server-side.
- CSRF validation still applies to state-changing requests.
- Session expiration remains backend-enforced.
- Frontend countdowns remain informational.
- Renewal requires an active session.
- Renewal refreshes backend expiration and cookie lifetimes.
- Logout clears frontend authorization data.
- Expiration clears frontend authorization data.
- Generic authentication errors do not reveal whether an account exists.

The first-time Admin setup endpoint is only for bootstrap. It must remain unavailable after any user exists and must not replace normal authenticated Admin user management.

## PDF Intake Changes

PDF intake changes must preserve privacy boundaries.

Do not:

- Persist uploaded PDFs
- Persist extracted PDF text
- Log uploaded PDF contents
- Add extracted values to audit metadata
- Send files to an external OCR service without explicit security review
- Accept uncertain extracted values without human review

When adding or changing a parser:

- Use synthetic PDF fixtures.
- Add parser-specific tests.
- Add confidence and needs-review behavior where applicable.
- Test missing fields.
- Test placeholder values such as `N/A`, `NONE`, and dashes.
- Test malformed input.
- Test unsupported templates.
- Confirm no extracted sensitive values reach logs.

## Database and Encryption Changes

Changes involving encryption or persistence require extra care.

Confirm that:

- Field-level encryption mappings remain controlled.
- Plaintext values do not appear in persisted sensitive fields.
- SQLCipher behavior remains tested.
- Encryption keys are not logged.
- Keys are not placed in command-line arguments.
- Backup encryption remains separate from database encryption.
- Restore operations do not overwrite the active database automatically.
- Database and storage paths remain validated.
- Migration behavior is tested against copies or fixtures.
- Failure messages do not expose keys or decrypted data.

## Audit and Logging Changes

Audit events should describe actions without storing sensitive values.

Preferred audit metadata includes:

```text
record IDs
user IDs
action names
event types
changed field names
success or failure state
```

Do not include:

```text
patient names
member IDs
group numbers
dates of birth
clinical notes
uploaded PDF text
authorization headers
cookies
passwords
session tokens
CSRF tokens
encryption keys
environment variables
```

Production logs should use the centralized observability configuration.

Do not add:

- Ad hoc file logging
- Debug `print()` calls containing request data
- Full request or response logging
- Raw exception messages containing sensitive data
- Database-row dumps
- Environment-variable dumps

## Deployment Changes

Deployment files live under:

```text
deployment/linux/
deployment/windows/
```

Deployment contributions must:

- Avoid embedded secrets
- Avoid embedded passwords
- Avoid embedded encryption keys
- Use protected environment files
- Use restricted service accounts
- Use isolated operational directories
- Document required permissions
- Document installation and removal
- Document manual verification
- Document failure diagnosis
- Avoid deleting databases or backups automatically
- Preserve safe defaults

Windows installer changes should be tested through the packaged installer when the change affects user-facing installation, upgrade, repair, uninstall, service startup, post-install health checks, first-time Admin setup, or ProgramData preservation.

### Windows PowerShell

PowerShell scripts should:

- Use `$ErrorActionPreference = "Stop"`
- Validate required files and directories
- Fail clearly when required inputs are missing
- Avoid printing environment values
- Use `-ErrorAction Stop` for operations that must abort on failure
- Support custom installation and backup paths
- Require elevation when registering or removing scheduled tasks
- Avoid storing secrets in scheduled-task arguments

PowerShell scripts are not checked by Ruff and require manual review on Windows.

### Linux systemd

systemd files should:

- Run as a restricted service account
- Load configuration from a protected environment file
- Use explicit working directories
- Restrict writable paths
- Use a restrictive file-creation mask
- Avoid embedding secrets
- Be verified with `systemd-analyze verify`
- Be tested manually before enabling timers

## Testing

Run the relevant checks before opening a pull request.

### Backend

From the `backend` directory:

```bash
pytest tests -n auto -q
```

Run Ruff:

```bash
ruff check . --fix
```

Run Bandit when security-sensitive backend code changes:

```bash
bandit -r authstatus_api
```

### Frontend

From the `frontend` directory:

```bash
npm run build
```

If frontend tests are added in the future, run the relevant test command as well.

### Focused Tests

Run focused tests while developing.

Examples:

```bash
pytest tests/security -n auto -q
pytest tests/authorizations -n auto -q
pytest tests/pdf_intake -n auto -q
pytest tests/database_encryption -n auto -q
```

Then run the complete suite before opening the pull request.

### Installer Validation

Installer validation is required when deployment behavior changes.

At minimum, confirm the relevant installer mode on Windows:

- Install
- Upgrade
- Repair
- Uninstall

Also confirm health checks, service status, and data preservation when those areas are affected.

Clean-machine VM testing is required before treating a Windows installer build as release-ready.

### Test Organization

Tests should be placed beside their domain under `backend/tests`.

Examples:

```text
backend/tests/security/
backend/tests/authorizations/
backend/tests/pdf_intake/
```

Keep shared fixtures in:

```text
backend/tests/conftest.py
```

Test modules should use unique basenames because pytest may import files as top-level modules depending on configuration.

Avoid duplicate names such as:

```text
tests/audit/test_service.py
tests/backups/test_service.py
```

Prefer unique names such as:

```text
tests/audit/test_audit_service.py
tests/backups/test_backup_service.py
```

## Manual Testing

Document relevant manual checks in the pull request.

Examples include:

- Login and logout
- Session restoration
- Session warning behavior
- Session renewal
- Automatic expiration
- Role-based UI behavior
- Authorization creation and editing
- Timeline updates
- PDF intake review
- Settings persistence
- Scheduled backup execution
- Backup-file creation
- Restore verification
- Windows service status
- Windows installer mode behavior
- Linux systemd service status

Manual checks must use synthetic data.

## Documentation Changes

Update documentation whenever a change affects:

- Setup
- Environment variables
- Security controls
- User workflows
- API endpoints
- Database structure
- Deployment paths
- Backup scheduling
- Restore procedures
- Testing commands
- Project limitations
- Repository layout

Documentation commands must match the actual repository structure.

Do not copy local usernames, machine-specific paths, or private working notes into public documentation.

Generic example paths are acceptable when clearly identified as examples.

Avoid duplicating long procedures across multiple documents. Prefer one owning document for each topic and link or reference that document from related pages.

## Pull Request Guidelines

A pull request should:

1. Describe what changed.
2. Explain why the change was made.
3. Identify affected modules.
4. Mention tests run.
5. Mention manual checks performed.
6. Link related issues when applicable.
7. Include screenshots for UI changes when useful.
8. Confirm that screenshots use synthetic data.
9. Confirm that no secrets or sensitive files are included.
10. Note any migration or deployment impact.

Keep unrelated changes in separate pull requests.

Avoid combining:

- Refactoring
- New features
- Large formatting changes
- Dependency upgrades
- Documentation rewrites

unless they are directly connected and safe to review together.

## Commit Messages

Use clear commit messages that describe the completed change.

Examples:

```text
Add session timeout warning and renewal
Organize backend tests by domain
Add Windows encrypted backup scheduling
Document backup and recovery workflow
Improve PDF intake review validation
```

Avoid vague messages such as:

```text
Update files
Fix stuff
Changes
Work in progress
```

## Issues

When reporting a bug, include:

- What happened
- What you expected
- Steps to reproduce
- Relevant error messages
- Operating system
- Python version
- Node.js version, when relevant
- Browser version, when relevant
- Affected module
- Whether the issue occurs with synthetic data
- Screenshots only when they contain no sensitive information

Do not paste:

- Environment files
- Encryption keys
- Database files
- Backup files
- Real PDFs
- Real patient data
- Authentication cookies
- Session tokens
- Full production logs

When suggesting a feature, include:

- The workflow problem
- Expected behavior
- Security or privacy impact
- Role impact
- Data-storage impact
- Testing considerations
- Important edge cases

## Security Concerns

Do not open a public issue for:

- Exposed secrets
- Exposed PHI or PII
- Authentication bypass
- Authorization bypass
- Session vulnerabilities
- CSRF vulnerabilities
- Encryption failures
- Backup exposure
- SQL injection
- Sensitive logging
- Unsafe PDF handling
- Service-account exposure
- Deployment misconfiguration

Report security concerns privately to the repository owner when possible.

See:

```text
SECURITY.md
```

for additional reporting guidance.

## License

By contributing to CareQueue, you agree that your contributions will be licensed under the license included in this repository.

# Threat Model and Risk Register

This document describes the current CareQueue security threat model and records known residual risks that should be considered during development, deployment, review, and release planning.

It is a technical risk-management document. It does not establish HIPAA compliance, replace an organizational HIPAA Security Rule risk analysis, provide legal advice, or replace deployment-specific security assessment.

## Scope

This threat model covers the CareQueue application and the packaged private deployment model represented in this repository, including:

- React/Vite browser frontend
- FastAPI backend
- Local user authentication and role-based authorization
- TOTP MFA and remembered-device MFA state
- Server-side sessions and CSRF protection
- Governance attestation workflow
- SQLite or SQLCipher persistence
- Field-level encryption
- Encrypted backups and restore/recovery workflows
- PDF-assisted intake
- Audit and operational logging
- Caddy HTTPS termination and reverse proxying
- Windows services and scheduled backups
- Linux systemd services and backup timers
- Installer, upgrade, repair, and uninstall workflows
- Release artifacts and dependency acquisition used to build or deploy CareQueue

The model focuses on the repository-supported private deployment architecture. A materially different deployment, such as public internet exposure, multi-host application/database separation, shared hosting, or third-party managed hosting, requires a separate threat assessment.

## Security Objectives

CareQueue security controls are intended to support the following objectives:

1. Prevent unauthorized access to authorization and workflow data.
2. Prevent users from performing actions outside their assigned role.
3. Protect sensitive stored data and backups from disclosure if storage media or files are copied.
4. Protect authenticated sessions from theft, replay, CSRF, and unintended persistence.
5. Preserve the integrity and availability of authorization records, audit records, backups, and governance records.
6. Fail closed when required authentication, authorization, governance, encryption, storage, or recovery prerequisites are not satisfied.
7. Prevent sensitive values from being written to logs, documentation, release assets, or other unintended locations.
8. Keep production application traffic within the documented private HTTPS deployment boundary unless an organization intentionally designs and assesses a broader deployment.
9. Provide sufficient auditability for security-sensitive and workflow-sensitive actions.
10. Make release and deployment behavior reproducible and reviewable.

## Assets

### Sensitive application data

CareQueue may store information associated with utilization review and prior authorization workflows. Depending on deployment and use, this may include protected health information, personally identifiable information, payer information, authorization status, clinical or administrative notes, documents, and workflow history.

### Authentication material

Security-sensitive authentication assets include:

- Password hashes
- TOTP secrets
- MFA challenge state
- Session tokens and persisted session-token digests
- CSRF tokens
- Remembered-device tokens and persisted keyed digests
- Temporary-password state
- Account lockout state

### Cryptographic material

Production cryptographic assets include:

- Field-level encryption key
- SQLCipher database key
- Backup encryption key
- Keyed-digest material used by security-sensitive token and audit mechanisms where applicable
- Caddy private certificate authority material and issued certificates

Loss, disclosure, replacement, or corruption of these values can affect confidentiality, integrity, authentication, or recoverability.

### Persistent data stores

Important persistent assets include:

- Primary CareQueue database
- Encrypted backup archives
- Restore staging data
- Recovery state
- Audit records and audit-chain data
- Governance attestation history
- Production configuration

### Application and deployment integrity

Integrity-sensitive assets include:

- Backend source and packaged runtime
- Frontend build output
- Installer scripts
- Windows service definitions
- Linux systemd unit files
- Caddy configuration
- Release archives and installer executables
- Dependency manifests and lockfiles
- GitHub Actions workflows

### Operational availability

CareQueue availability depends on:

- Database readability and writability
- Encryption keys
- Filesystem permissions and free space
- API service availability
- Caddy service availability
- Certificate trust
- Backup and restore availability
- Supported runtime dependencies

## Threat Actors

### Unauthenticated local or network user

A person who can reach the CareQueue HTTPS origin or backend endpoint but does not possess a valid application session.

Potential goals include credential guessing, endpoint discovery, session abuse, unauthorized initial setup, malformed-input attacks, and denial of service.

### Authenticated low-privilege user

A legitimate user with a UR or Read Only account who attempts to access data or operations outside the assigned role.

Potential goals include unauthorized modification, administrative actions, privilege escalation, bulk access, or bypass of governance and password-change requirements.

### Compromised authenticated account

An attacker using valid credentials, an active session, or a trusted-device token belonging to another user.

Potential goals include accessing workflow data, modifying authorizations, maintaining persistence, suppressing auditability, or escalating privileges.

### Malicious or careless administrator

An administrator has intentionally broad application privileges and may also have host-level access in a local deployment.

Potential risks include excessive access, unsafe user or key handling, disabling host protections, mishandling backups, or modifying application/runtime files outside normal workflows.

Application controls cannot fully protect against a hostile host administrator.

### Host-level attacker or malware

Malware or a person with local operating-system access may attempt to read application files, configuration, memory, databases, backups, certificates, or keys, or may alter binaries and scripts.

Encryption-at-rest controls reduce some storage disclosure risks but do not protect secrets that must be available to a running application on a fully compromised host.

### Supply-chain attacker

An attacker may attempt to compromise a dependency, package registry artifact, GitHub Action, vendored installer dependency, build environment, or release artifact.

Potential goals include introducing malicious code, stealing secrets during build or deployment, or distributing altered installers.

### Accidental operator error

An authorized operator may unintentionally delete files, use the wrong key, misconfigure storage paths, install an incorrect release, break permissions, restore an invalid backup, or expose sensitive logs or screenshots.

### Malicious or malformed document source

A PDF supplied to the intake workflow may be malformed, adversarial, unexpectedly large, unsupported, or constructed to exploit parser behavior or consume excessive resources.

## Trust Boundaries

### Browser to Caddy HTTPS boundary

The browser communicates with the packaged application through private HTTPS. Caddy serves the frontend and proxies API requests.

Security assumptions:

- The client trusts the intended Caddy certificate authority.
- DNS or local hostname resolution points to the intended CareQueue deployment.
- The deployment is not unintentionally exposed beyond its intended private network boundary.

### Caddy to FastAPI boundary

Packaged production deployments bind the CareQueue API to the loopback interface and use Caddy as the externally reached application endpoint.

Security assumptions:

- Host firewall and service configuration preserve loopback-only backend exposure.
- Caddy routing and security headers are not weakened outside the packaged configuration without review.

### Frontend to authenticated backend boundary

The frontend is not a security authority. Authentication, session validation, CSRF validation, governance prerequisites, and role authorization are enforced by the backend.

Security assumptions:

- Client-supplied state, role labels, identifiers, and form values are untrusted.
- Protected operations remain guarded by backend dependencies and explicit authorization checks.

### FastAPI to database boundary

The backend reads and writes persistent application state through SQLite or SQLCipher connections.

Production security assumptions:

- Production uses SQLCipher as required by application settings validation.
- The configured database path remains inside the trusted production data root.
- Database file ownership and permissions are restricted to intended service and administrative identities.

### Application to encryption-key boundary

The application requires cryptographic keys to decrypt protected values and backups and to open an encrypted production database.

Security assumptions:

- Keys are provisioned through protected production configuration.
- Key files and environment configuration are protected by operating-system ACLs or permissions.
- Field and backup encryption keys remain distinct, as enforced by production settings validation.

### Application to filesystem boundary

Backup, restore, database, logs, configuration, PDF handling, and deployment workflows interact with local filesystem paths.

Security assumptions:

- Production storage paths remain beneath the configured production data root.
- Backup and restore locations do not overlap.
- Sensitive path workflows continue to reject unsafe path traversal, symlink, and untrusted-storage behavior where implemented.
- Service account permissions remain restricted.

### PDF intake worker boundary

PDF extraction executes through an isolated worker with timeout handling rather than treating document parsing as trusted application logic.

Security assumptions:

- Uploaded or supplied documents remain untrusted.
- Extraction output is treated as candidate data that requires review rather than authoritative clinical or payer information.

### Backup and recovery boundary

Backup creation, verification, restore staging, and recovery activation move high-value persistent data between protected locations.

Security assumptions:

- Backup encryption keys are available only to authorized processes and operators.
- Restores are verified and staged before activation.
- Operators do not substitute unverified database files into production storage.

### Installer and service-management boundary

Windows and Linux installers perform privileged operations including directory creation, configuration, service installation, certificate trust changes, upgrade actions, and permission changes.

Security assumptions:

- Installation is performed by an authorized host administrator.
- Release artifacts are obtained from an authentic source.
- Installer scripts and bundled dependencies have not been altered.

### Source, CI, dependency, and release boundary

Source control, GitHub Actions, package registries, dependency resolution, build tooling, and release publication form a separate trust boundary from the installed application.

Security assumptions:

- Repository access controls are appropriate.
- CI actions and build dependencies are reviewed and pinned appropriately.
- Release artifacts can be tied to reviewed source and verified before installation.

## Representative Abuse Cases

### Credential guessing and account discovery

An attacker repeatedly attempts usernames and passwords or uses response differences to discover valid accounts.

Existing controls include Argon2id password hashing, generic authentication failures, failed-login tracking, and temporary account lockout.

Residual concerns include password reuse outside CareQueue, host compromise, phishing, and operational policies that permit weak account-management practices.

### MFA bypass or remembered-device theft

An attacker with a password attempts to bypass TOTP by forging, stealing, or replaying MFA challenge or remembered-device state.

Existing controls include short-lived server-side MFA challenges, keyed digests for MFA challenge and remembered-device tokens, time-limited remembered devices, and revocation during supported security-sensitive account changes.

Residual concerns include compromise of a browser profile or running host where valid cookies are accessible to the user's environment.

### Session replay or concurrent persistence

An attacker steals a valid authenticated session or attempts to maintain multiple active sessions.

Existing controls include server-side sessions, hashed session-token persistence, Secure cookies in production, inactivity expiration, sliding expiration, renewal-time rotation, logout/expiration synchronization, and one active authenticated session per account.

Residual concerns include malware or host compromise while a session is active.

### CSRF against authenticated state-changing operations

A malicious site attempts to cause an authenticated CareQueue browser to submit state-changing requests.

Existing controls include same-origin private deployment, CSRF validation, trusted production origins, and separate CSRF state.

Residual risk increases if production origin validation, cookie policy, or proxy configuration is modified without equivalent review.

### Role bypass through direct API calls

A Read Only or UR user bypasses frontend controls and directly calls administrative or modification endpoints.

Existing controls include backend-enforced authentication, governance prerequisites, password-change prerequisites, and role dependencies.

Residual risk remains if a new endpoint is added without the correct dependency or explicit resource-level authorization.

### Initial Admin setup abuse

An attacker attempts to claim the first administrative account on a newly installed system.

Existing controls restrict first-time Admin setup to the loopback deployment path.

Residual risk exists during unattended or poorly controlled host provisioning if an unauthorized person obtains local host access before intended setup is complete.

### Governance bypass

A user attempts to access protected application functions without the current required governance attestation.

Existing controls enforce current governance state in backend protected-user dependencies and record versioned acceptance history.

Residual risk includes organizational misuse of the attestation as a substitute for legal agreements, risk analysis, workforce procedures, or other required safeguards.

### Database theft

An attacker copies the production database from disk.

Existing controls require SQLCipher in production and also encrypt selected sensitive fields.

Residual risk includes key theft from the same host, memory compromise while the application is running, weak host ACLs, or unprotected copies created outside supported backup workflows.

### Backup theft or substitution

An attacker copies an encrypted backup, replaces a backup, or persuades an operator to restore a malicious or corrupted file.

Existing controls include separate backup encryption, backup verification, path validation, restore staging, and controlled recovery activation.

Residual concerns include compromise of both backup data and its key, operator use of unsupported manual restore procedures, and insufficient off-host or immutable backup strategy.

### Key loss

An operator loses or overwrites a field-encryption, SQLCipher, or backup-encryption key.

Existing controls validate required production keys but do not make key loss recoverable.

Residual risk is high because loss of the only valid key can make protected data permanently unreadable. Formal key custody, backup, rotation, and recovery procedures remain required.

### Key disclosure

An attacker obtains production encryption keys from configuration, filesystem access, process memory, logs, terminal history, screenshots, or backup material.

Existing controls include production secret validation, restricted runtime directories, separation of field and backup keys, and documentation prohibiting disclosure of secrets.

Residual risk remains significant on a compromised host because the running application must be able to access active keys.

### Malicious PDF processing

An attacker supplies a PDF intended to trigger parser vulnerabilities, excessive resource consumption, or misleading extracted data.

Existing controls include local processing, file signature/type validation, isolated extraction, timeout handling, confidence metadata, and needs-review behavior.

Residual risk includes vulnerabilities in PDF parsing dependencies and documents crafted to produce plausible but incorrect extracted content.

### Audit manipulation

An attacker attempts to alter or remove audit events to hide unauthorized activity.

Existing controls include audit logging, chained tamper-evident audit integrity data, and integrity verification.

Residual risk remains for a sufficiently privileged host administrator who can modify both application data and application code or keys. Current audit chaining is not an external immutable logging service or independent digital signature.

### Log or error disclosure

Sensitive application values are exposed through production logs, exception responses, debug output, screenshots, or support material.

Existing controls include production log sanitization, centralized exception handling, disabled production API documentation endpoints, and documented sensitive-data handling requirements.

Residual risk remains when new code logs unreviewed request or object data, operators collect raw diagnostics, or debug behavior is introduced outside the production settings controls.

### Path traversal, symlink, or unsafe storage use

An attacker attempts to redirect database, backup, restore, or other sensitive filesystem operations outside intended directories.

Existing controls include production-root validation, separation of backup and restore paths, path validation in sensitive storage workflows, safer directory enumeration, and symlink rejection where implemented.

Residual risk remains in future filesystem features that do not reuse the existing validation patterns.

### Dependency compromise

A malicious or compromised Python, npm, GitHub Action, or vendored deployment dependency enters the build or runtime supply chain.

Existing controls include bounded Python requirements, npm lockfile usage, `pip-audit`, `npm audit`, Bandit, automated backend/frontend security checks, and checksums for selected downloaded Windows deployment assets.

Residual risk remains because backend release dependencies are range-bounded rather than fully resolved in a reproducible lock, GitHub Actions are currently referenced by version tags rather than immutable commit SHAs, and a formal SBOM/provenance process is not yet complete.

### Release artifact tampering

An attacker replaces or modifies an installer or Linux release archive after build or publication.

Existing controls include versioned release tooling and SHA-256 generation/verification procedures for release artifacts.

Residual risk remains until release signing, artifact provenance, checksum publication policy, and source-tag-to-artifact verification are formalized.

### Upgrade or migration corruption

An upgrade changes database schema or runtime files in a way that causes corruption, incompatibility, or security control regression.

Existing controls include installer upgrade/repair modes, service-aware upgrades, configuration/key preservation, and the current incremental schema initialization mechanisms.

Residual risk remains because the repository does not yet have a complete versioned migration and rollback framework with tested upgrade paths across supported releases.

### Denial of service or resource exhaustion

An attacker, malformed input, disk-full condition, database corruption, repeated PDF processing, or service failure makes CareQueue unavailable.

Existing controls include PDF timeout handling, health/readiness endpoints, service management, and backup/recovery tooling.

Residual risk remains because comprehensive fault-injection testing for disk exhaustion, database corruption, permission failures, key failures, broken restores, and service restart failures is still required.

## Risk Rating Method

Each tracked risk uses qualitative likelihood and impact values:

- **Likelihood: Low**: requires unusual access, uncommon conditions, or multiple failed assumptions.
- **Likelihood: Medium**: plausible in a normal deployment if an expected control or operational practice fails.
- **Likelihood: High**: likely to occur without additional controls or is easy to trigger under realistic conditions.
- **Impact: Low**: limited operational effect with little or no sensitive-data exposure.
- **Impact: Medium**: meaningful availability, integrity, confidentiality, or recovery impact with bounded scope.
- **Impact: High**: potential sensitive-data disclosure, privilege compromise, unrecoverable data loss, broad integrity failure, or prolonged outage.

Priority is based on the combination of likelihood, impact, and the degree to which the risk remains unresolved.

## Risk Register

| ID | Risk | Likelihood | Impact | Existing controls | Residual risk / gap | Planned mitigation | Priority |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-001 | Production encryption key loss makes protected data unrecoverable | Medium | High | Production validates required keys; field, previous-field, backup, and SQLCipher key roles are independently validated; documented key custody, rotation, recovery, compromise-response, and retirement procedures; backup and recovery drills | Key loss remains unrecoverable if all valid recoverable copies are lost; SQLCipher and historical backup key rotation require controlled operator procedures | Maintain tested key-recovery drills, protected recoverable copies, and documented retirement evidence | High |
| R-002 | Production encryption keys are disclosed through host compromise or operator handling | Medium | High | Restricted production directories; secret validation; independent key-role validation; documented key custody, exposure response, rotation, and deployment review procedures | Active keys remain accessible to the running application and sufficiently privileged host administrators | Maintain ACL and permission review, protected key custody, exposure-response drills, and deployment security review | High |
| R-003 | Database or application state becomes corrupted during upgrade | Medium | High | Upgrade/repair modes; service-aware upgrade; configuration/key preservation; backup/recovery tooling | No complete versioned migration framework with cross-release upgrade tests and rollback strategy | Introduce versioned migrations, pre-upgrade validation, upgrade tests, and recovery/rollback procedures | High |
| R-004 | Release artifact is tampered with or cannot be tied confidently to reviewed source | Medium | High | Versioned artifacts; SHA-256 generation/verification procedures; selected vendor download checksums | Windows installer is not yet formally code-signed; provenance and checksum publication policy are incomplete | Add signing guidance/implementation, published checksums, source-tag verification, and release provenance procedure | High |
| R-005 | Compromised dependency or CI action introduces malicious code | Medium | High | Bounded Python requirements; npm lockfile; `pip-audit`; `npm audit`; Bandit; CI security workflow | Python production dependencies are not fully resolved; GitHub Actions use movable version tags; SBOM absent | Add dependency update automation, fully resolved release dependency set, SBOM, and immutable Action SHA pinning | High |
| R-006 | New endpoint omits required authentication, governance, CSRF, or role enforcement | Medium | High | Central backend dependencies; access-control tests; role-based routing patterns | Manual review is still required when new endpoints are introduced | Expand route-level security tests and browser E2E coverage for protected workflows | High |
| R-007 | Privileged host attacker alters application data and corresponding audit evidence | Low to Medium | High | Tamper-evident audit chain and verification; restricted deployment directories | Audit evidence is stored within the same administrative trust domain and is not externally immutable | Document limitation; evaluate off-host or externally protected audit export where required by deployment risk | High |
| R-008 | Broken, corrupt, or malicious backup is activated and causes data loss or compromise | Medium | High | Backup verification; encrypted backups; path validation; restore staging; controlled recovery activation; fault-injection coverage for corrupt backups, wrong keys, permission failures, disk-write failures, activation failures, rollback failures, and missing safety backups | Cross-version recovery validation remains incomplete | Add cross-version recovery validation alongside the versioned migration framework | Medium to High |
| R-009 | Disk-full, permission, missing-secret, corrupt-database, or service failure produces unsafe behavior | Medium | High | Production validation; health/readiness endpoints; exception handling; service management | Failure behavior has not been systematically fault-injection tested across all listed conditions | Implement fail-closed fault-injection test matrix | High |
| R-010 | Browser session or remembered-device state is stolen from a compromised workstation | Medium | High | Secure cookies in production; server-side sessions; inactivity timeout; rotation; single-session enforcement; remembered-device expiry/revocation | Application controls cannot fully defend an already compromised browser or OS account | Document workstation requirements; maintain short session lifetime and revocation controls; consider additional device/session review features if required | Medium to High |
| R-011 | First Admin account is claimed by an unauthorized local user during initial provisioning | Low | High | Initial Admin setup is restricted to loopback access | Physical/local host compromise during unattended provisioning remains possible | Require controlled installation procedure and immediate first-admin completion on trusted host | Medium |
| R-012 | Governance attestation is treated as proof of HIPAA compliance or as a substitute for a BAA | Medium | High | UI/docs explicitly state the attestation is not a BAA or compliance determination; versioned acknowledgments are recorded | Organizational misunderstanding or misuse remains possible | Keep disclaimers prominent; include governance review in release/deployment docs and organizational compliance procedures | Medium to High |
| R-013 | Malformed or adversarial PDF exploits parser dependency or causes excessive resource use | Medium | Medium to High | Signature validation; isolated extraction worker; timeout handling; local processing; review flags | Third-party parser vulnerabilities and intentionally misleading extraction remain possible | Continue dependency auditing; add parser failure/fuzz-style cases and explicit size/resource limits if needed | Medium |
| R-014 | Extracted PDF values are accepted as authoritative despite extraction error | Medium | Medium to High | Confidence and needs-review flags; workflow is review-oriented | Human reviewers may still accept plausible incorrect values | Preserve explicit review requirement; expand E2E tests for low-confidence and malformed extraction states | Medium |
| R-015 | Production logging or diagnostics disclose sensitive data | Medium | High | Central log sanitization; production debug disabled; production docs/OpenAPI disabled; sensitive-data rules | New code or operator diagnostics can bypass intended patterns | Maintain review tests for sanitization and add regression coverage when new logging fields are introduced | Medium to High |
| R-016 | Unsafe filesystem path or symlink redirects sensitive operations | Low to Medium | High | Production data-root validation; non-overlapping backup/restore paths; sensitive path checks; symlink rejection in supported workflows | Future file features may fail to reuse the same protections | Centralize/reuse storage validation and add path-abuse tests with each filesystem feature | Medium |
| R-017 | Misconfigured reverse proxy, origin, DNS, or certificate trust exposes or redirects application traffic | Low to Medium | High | Packaged private HTTPS; trusted-host middleware; HTTPS-only production origins; loopback API binding | Custom deployment changes can invalidate packaged assumptions | Require deployment architecture review for any network/topology change and validate certificate/host behavior during release tests | Medium to High |
| R-018 | Service or host outage prevents timely authorization workflow access | Medium | Medium to High | Windows services; Linux systemd services; health/readiness endpoints; backups | No high-availability design; CareQueue is local-first and can have a single-host failure domain | Document recovery objectives appropriate to deployment; test restart/reboot and recovery procedures | Medium |
| R-019 | Backup and primary data are lost together because they share the same host/failure domain | Medium | High | Encrypted scheduled backups and retention controls | Local backups do not inherently protect against host loss, ransomware, fire, theft, or catastrophic storage failure | Define off-host backup/custody requirements where organizational risk analysis requires them | High |
| R-020 | Unsupported manual changes to database schema or runtime configuration bypass expected controls | Medium | Medium to High | Packaged installer/configuration workflows; production settings validation | Administrators retain host-level ability to alter files directly | Document supported maintenance procedures and verify configuration during health/release checks | Medium |
| R-021 | Accessibility or UI-state defects cause users to misunderstand disabled/read-only/security-sensitive actions | Medium | Medium | Role-aware UI and frontend component tests | Formal accessibility and browser-level workflow coverage remain incomplete | Complete keyboard, screen-reader, focus, disabled/read-only, error-state, and responsive testing | Medium |
| R-022 | Security regression is missed because component/unit tests do not model the complete browser workflow | Medium | High | Extensive backend and frontend automated tests | Browser-level E2E coverage remains incomplete for login, MFA, session replacement, timeout, CSRF-sensitive flows, admin, and backups | Add browser E2E security suite before release-candidate validation | High |
| R-023 | Published documentation diverges from actual supported deployment or security behavior | Medium | Medium | Structured public documentation and command references | Rapid security/installer changes can make documentation stale | Make documentation review part of release checklist and final release-candidate validation | Medium |
| R-024 | An authenticated administrator intentionally misuses legitimate access | Low to Medium | High | Individual accounts, MFA, audit logging, single-session enforcement, role restrictions for non-admin users | Application cannot eliminate misuse by a fully authorized administrator, especially one with host access | Organizational least-privilege, access review, workforce controls, audit review, and separation of duties where appropriate | High |

## Residual Risk Themes

The current architecture has strong application-level controls for a local-first project, but several risks cannot be solved solely in application code.

### Host trust remains fundamental

A sufficiently privileged operating-system administrator or malware running with equivalent access can potentially read active secrets, replace application binaries, alter configuration, manipulate data, or interfere with logs. CareQueue therefore depends on host hardening, endpoint security, account management, physical security, patching, and administrative controls.

### Encryption depends on key custody

SQLCipher, field-level encryption, and encrypted backups protect data only while the required keys remain secret and available. Key disclosure weakens confidentiality; key loss can destroy availability. Key lifecycle work is therefore a release-critical security concern rather than a documentation-only task.

### Private deployment assumptions must be preserved

The packaged architecture assumes private HTTPS through Caddy and a loopback-only backend. Public internet exposure or a materially different proxy/network topology changes the threat model and requires additional controls and review.

### Audit integrity is not external immutability

The audit chain can reveal tampering under the assumptions of the current application trust domain, but it is not a substitute for an independent external logging system, write-once storage, or third-party digital signature where those controls are required.

### Organizational safeguards remain outside the application

CareQueue can support access control, authentication, auditing, governance acknowledgment, encryption, backup, and recovery. It does not implement an organization's complete risk-management program, workforce policies, incident-response program, BAA process, contingency plan, physical safeguards, device security, or legal/compliance review.

## Security Review Triggers

This threat model should be reviewed when any of the following occur:

- A new authentication or MFA mechanism is added.
- Session lifetime, cookie behavior, trusted-device behavior, or CSRF handling changes.
- A new user role or permission boundary is introduced.
- A new endpoint accesses protected data or performs administrative actions.
- Encryption algorithms, keys, key storage, or rotation behavior changes.
- Database migration behavior changes.
- Backup, restore, or recovery behavior changes.
- New file upload or document parsing functionality is introduced.
- Production filesystem locations or service accounts change.
- Caddy, TLS, hostname, network exposure, or deployment topology changes.
- Installer privilege or service-management behavior changes.
- Dependency-management, CI, build, signing, or release processes change.
- A security vulnerability or significant operational incident is discovered.
- A release candidate is prepared for broader testing or production evaluation.

## Relationship to Planned Hardening Work

The highest-priority residual risks in this register map directly to the remaining hardening milestones:

- **Supply-chain hardening:** R-004, R-005
- **Release signing and provenance:** R-004
- **Encryption key lifecycle:** R-001, R-002
- **Fault injection and fail-closed testing:** R-008, R-009, R-018
- **Formal migrations and rollback:** R-003
- **Browser E2E security tests:** R-006, R-022
- **Linux and deployment parity validation:** R-017, R-018, R-020
- **Accessibility and UX validation:** R-021
- **Final documentation and release review:** R-023

The register should be updated as mitigations are implemented. A risk should not be removed merely because a control exists; its residual likelihood and impact should be reassessed based on the implemented and tested control.

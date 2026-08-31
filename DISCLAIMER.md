# Disclaimer

CareQueue is a local-first workflow application for utilization review and authorization management. It supports authorization tracking, review dates, payer and facility workflows, timeline events, PDF-assisted intake, dashboards, user access controls, audit records, encrypted storage options, backups, and private packaged deployment.

This project is provided as software for administrative workflow support. It is not medical advice, legal advice, billing advice, clinical guidance, compliance guidance, or a substitute for verification with an authorized payer, provider, legal professional, compliance professional, or other responsible organization.

## Healthcare and Compliance Status

CareQueue includes technical and administrative-support features that may help an organization implement parts of its security and compliance program.

These include controls such as:

- Local user authentication
- Role-based access control
- TOTP multi-factor authentication
- Optional remembered-device MFA
- Single active authenticated sessions
- Server-enforced inactivity timeouts
- CSRF protection
- Versioned organization governance attestation
- Field-level encryption for selected sensitive values
- SQLCipher database encryption support
- Separately encrypted backups
- Audit logging and integrity verification
- Private HTTPS deployment through Caddy
- Restricted production runtime paths
- Backup and recovery workflows

These controls do not, by themselves, make CareQueue or a CareQueue deployment compliant with HIPAA or any other legal, regulatory, contractual, accreditation, security, or privacy framework.

Compliance depends on the complete environment in which the software is deployed and operated, including organizational policies, workforce practices, agreements, physical safeguards, technical safeguards, risk analysis, access management, incident response, backup practices, device security, network architecture, monitoring, and applicable legal requirements.

CareQueue is not represented as independently certified, formally audited, or approved by a government agency, payer, accreditation body, or standards organization unless a specific release or accompanying documentation explicitly states otherwise.

Organizations considering use with regulated or sensitive data should perform their own security, legal, compliance, and operational review before deployment.

## Governance Attestation

CareQueue includes a versioned organization governance attestation that must be completed by an Admin before normal protected application functionality becomes available.

The attestation is intended to:

- Record organizational acknowledgment of security and privacy responsibilities.
- Record the organization and deployment mode associated with the installation.
- Record the accepting Admin and acceptance time.
- Preserve versioned attestation history.
- Require re-attestation when the application's governance requirements are intentionally revised.

The governance workflow is an application accountability control.

Accepting the governance attestation:

- Does not execute a Business Associate Agreement.
- Does not replace a Business Associate Agreement where one is required.
- Does not establish HIPAA compliance.
- Does not replace legal or compliance review.
- Does not transfer responsibility for organizational safeguards to the software.
- Does not certify that a deployment has been configured or operated securely.

Required agreements must be executed separately by the appropriate parties.

## Administrative Workflow Only

CareQueue is intended to support administrative utilization review and authorization workflows.

It does not provide:

- Medical advice
- Diagnosis
- Treatment recommendations
- Clinical decision-making
- Medical necessity determinations
- Legal determinations
- Compliance determinations
- Billing advice
- Payer coverage guarantees
- Eligibility guarantees
- Authorization guarantees

CareQueue may display or organize information entered by users or extracted from documents, but it does not independently verify that the information is correct, current, complete, or authoritative.

Authorization statuses, payer decisions, review requirements, coverage details, dates, identifiers, and other operational information should be verified with the relevant payer, provider, facility, or other authorized source when accuracy matters.

## PDF Intake Limitations

CareQueue can assist with extracting information from supported PDF documents.

PDF-assisted intake is not an authoritative source of record.

Extracted values must be reviewed before they are applied to an authorization record.

CareQueue does not guarantee that:

- A PDF was parsed completely.
- Embedded text accurately represents the visible document.
- A payer or facility form is current.
- A supported template applies to every variation of a document.
- A field was labeled consistently.
- Extracted values are correct.
- Extracted authorization information matches the payer's final determination.
- Scanned documents can be processed successfully.

Fields marked as needing review should be confirmed or corrected by an authorized user before use.

CareQueue does not currently provide a general-purpose OCR pipeline for scanned documents.

## PHI and PII Warning

CareQueue can process information that may constitute protected health information, personally identifiable information, payer information, authorization information, or other sensitive operational data.

Do not commit, publish, upload, or otherwise expose real sensitive data through source control, public issue trackers, public demonstrations, screenshots, test fixtures, or documentation.

Sensitive information can include:

- Patient or client names
- Member IDs
- Group numbers
- Dates of birth
- Phone numbers
- Fax numbers
- Addresses
- Clinical notes
- Authorization numbers associated with identifiable individuals
- Facility-specific private information
- Payer communications associated with identifiable individuals
- Uploaded intake PDFs
- Extracted PDF text
- Extracted PDF JSON
- Database files
- SQLCipher database files
- Backup files
- Restored database files
- Environment files
- Encryption keys
- API credentials
- Passwords
- Temporary passwords
- MFA secrets
- MFA codes
- MFA challenge tokens
- Session tokens
- Remembered-device tokens
- CSRF tokens
- Authentication cookies
- Private certificates or private keys

Use synthetic or appropriately de-identified data for examples, automated tests, screenshots, demonstrations, bug reports, and documentation.

De-identification requirements depend on the applicable context and should be reviewed by qualified personnel when regulated data is involved.

## Authentication and Access-Control Limitations

CareQueue includes authentication, MFA, role-based authorization, session controls, and governance prerequisites.

These controls depend on correct deployment and operation.

For example:

- A compromised administrator account can still perform actions permitted to an Admin.
- A compromised host can undermine application-level controls.
- A remembered device reduces repeated MFA prompts and therefore must be used only on appropriately protected devices.
- Single-session enforcement does not prevent compromise of the currently active session.
- Session timeouts do not replace workstation locking or physical access controls.
- Role-based access does not replace periodic organizational access review.
- Account deactivation in CareQueue does not automatically remove operating-system, VPN, network, file-share, or other external access.

Organizations remain responsible for identity verification, account provisioning, role assignment, MFA policy, access review, offboarding, workstation security, and account recovery procedures.

## Encryption and Key-Management Limitations

CareQueue supports multiple encryption layers, including selected field-level encryption, SQLCipher-backed database encryption, and separately encrypted backups.

Encryption reduces certain risks but does not eliminate them.

Encryption protections depend on:

- Secure key generation
- Correct configuration
- Restricted access to environment files
- Secure key backup
- Appropriate service-account permissions
- Secure host administration
- Secure recovery procedures

If an encryption key is lost, related encrypted records or backups may become permanently unreadable.

If an encryption key is exposed together with the corresponding encrypted data, that data may become decryptable.

Do not generate replacement keys for an existing encrypted database merely to resolve a configuration or startup failure.

Encryption at rest also does not protect data after it has been legitimately decrypted for an authorized application process or displayed to an authorized user.

## Backup and Recovery Limitations

CareQueue supports encrypted backup creation, verification, retention controls, staged recovery, controlled recovery activation, and assisted failed-upgrade rollback for supported packaged deployment paths.

A successful backup operation does not prove that:

- The backup contains the expected data.
- The correct key is available.
- The backup can be restored on the required system.
- Recovery procedures will succeed during an actual incident.
- Off-host copies exist.
- Organizational retention requirements have been satisfied.

Organizations should perform periodic backup verification and recovery exercises.

Backup files, rollback databases, restored databases, recovery staging data, failed-upgrade recovery records, preserved application archives, and failed-application recovery assets remain sensitive or operationally significant and must be protected accordingly.

A successful rollback operation does not prove that every application workflow, external dependency, or operational process has been restored correctly. Post-rollback service, health, data, governance, audit, and backup validation remains required.

Do not manually alter recovery records, application archive checksums, migration records, or encrypted database files to force a failed recovery operation to continue.

## Audit Log Limitations

CareQueue records selected application, security, governance, administrative, backup, recovery, and workflow actions.

Current audit events participate in a tamper-evident cryptographic hash chain and can be checked through the application's integrity-verification workflow.

Tamper-evident does not mean tamper-proof.

A sufficiently privileged attacker who can modify the application, database, keys, backups, and host environment may be able to undermine application-level evidence.

CareQueue's audit log is not currently a substitute for:

- Independent immutable logging
- Centralized SIEM collection
- Host audit logging
- Network monitoring
- Administrative change records
- Organizational incident-response evidence

Deployments requiring independent or immutable evidence should use additional external controls.

## Private Deployment Model

Packaged CareQueue releases are designed primarily for private or controlled deployment.

The packaged Windows and Linux configurations place the CareQueue API on the loopback interface and use Caddy to provide HTTPS access.

The default packaged private origin is:

```text
https://carequeue.local
```

The included configuration should not be treated as a general-purpose public internet deployment template.

A public or broadly network-accessible deployment requires separate review of areas such as:

- DNS
- Public certificate management
- Reverse-proxy configuration
- Firewall policy
- Network segmentation
- Remote access
- Service identities
- Host hardening
- Monitoring
- Patch management
- Intrusion detection
- Incident response
- Availability requirements
- Backup location and key custody
- Denial-of-service exposure
- Administrative access paths

Do not expose the loopback CareQueue API directly to an untrusted network.

## Platform and Deployment Validation

CareQueue includes packaged deployment workflows for Windows and supported Debian-based Linux systems.

A successful build or installation on one system does not guarantee identical behavior on another system.

Before introducing sensitive production data, validate the exact release artifact on the intended operating-system version and deployment environment.

Validation should include appropriate checks for:

- Installation
- Service startup
- HTTPS access
- Certificate trust
- First-time Admin setup
- Governance attestation
- Login and logout
- MFA
- Session behavior
- Role enforcement
- Representative authorization workflows
- Backup creation
- Backup verification
- Upgrade
- Repair
- Failed-upgrade rollback
- Uninstall behavior
- Reboot persistence
- Recovery procedures

## Licensing and Distribution

CareQueue uses version-based licensing.

CareQueue versions `0.4.x` and earlier were released under the MIT License.

CareQueue version `0.5.0` and later versions expressly released under the current licensing terms use the Business Source License 1.1 until the applicable Change Date.

Current BSL-licensed releases are source-available. Public availability of the source code does not by itself grant unrestricted production-use, hosting, redistribution, or commercial rights.

Production use of a CareQueue version that remains under the Business Source License requires rights granted by the applicable license or a separate commercial license from the Licensor.

Each BSL-licensed version has its own Change Date. Under the current CareQueue licensing parameters, the Change Date is four years after the first publicly available distribution of that specific version, and the Change License is GNU General Public License version 3 or later.

Historical MIT releases retain the rights granted under the MIT License for those versions.

The authoritative licensing notice is:

```text
LICENSE
```

The applicable license texts are stored under:

```text
LICENSES/
```

A plain-language overview is available at:

```text
docs/licensing.md
```

This disclaimer does not modify, expand, or replace the rights and obligations in the applicable license or a separate commercial agreement.

## Release Status

Release artifacts and documentation should be interpreted according to their published release status.

A pre-release, beta, release candidate, development build, or locally built artifact may contain incomplete functionality or unresolved defects even when automated tests pass.

A stable release label does not remove the need for deployment-specific validation.

Release notes should be reviewed for:

- Security-sensitive changes
- Configuration changes
- Upgrade requirements
- Rollback and recovery requirements
- Known limitations
- Required manual validation
- Changes to deployment behavior
- Changes to governance requirements
- Changes to licensing or distribution terms

The CareQueue application version, governance attestation version, and governance document revision are separate values.

An application release does not automatically require a new governance attestation. Re-attestation is required when the required governance attestation version changes, when the required governance document revision changes, or when no current attestation exists.

## No Guarantee of Availability

CareQueue does not guarantee continuous availability.

Availability can be affected by:

- Host failure
- Database corruption
- Lost encryption keys
- Certificate problems
- Dependency failures
- Operating-system updates
- Storage exhaustion
- Backup failures
- Service failures
- Misconfiguration
- Network problems
- Software defects

Organizations using CareQueue for operational workflows should maintain appropriate downtime, backup, recovery, and business-continuity procedures.

## No Warranty

CareQueue is provided as-is, without warranty of any kind, to the extent permitted by applicable law.

No guarantee is made regarding:

- Accuracy
- Completeness
- Security
- Reliability
- Availability
- Compatibility
- Regulatory compliance
- Fitness for a particular purpose
- Suitability for healthcare operations
- Correctness of authorization or payer information
- Successful installation or recovery in every environment

Users and organizations are responsible for evaluating whether the software is appropriate for their intended use.

## Limitation of Liability

To the extent permitted by applicable law, use, modification, deployment, and distribution of CareQueue are at the user's or organization's own risk.

The project maintainers and contributors are not responsible for claims, damages, losses, privacy incidents, compliance failures, payer disputes, operational errors, data loss, service interruption, or other liabilities arising from use of the software except where liability cannot legally be excluded or limited.

Nothing in this disclaimer overrides rights or obligations that cannot be waived under applicable law.


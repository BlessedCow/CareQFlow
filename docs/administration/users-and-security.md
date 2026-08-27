# Users and Security

CareQueue uses local application accounts, role-based access control, Argon2id password hashing, TOTP multi-factor authentication (MFA), browser-managed cookies, server-side sessions, CSRF protection, and versioned governance attestation.

This guide covers the application account lifecycle and the security controls that affect users and administrators.

CareQueue's backend is authoritative for authentication, authorization, session validity, and governance enforcement. Frontend controls provide the user interface for those protections but do not replace backend enforcement.

## Roles

CareQueue supports three application roles:

```text
Admin
UR
Read Only
```

### Admin

Admins can use the authorization workflow and manage administrative functions, including:

- Creating users
- Changing another user's role
- Activating or deactivating another user
- Resetting another user's password
- Resetting another user's MFA
- Reviewing audit events
- Reviewing governance attestation status and history
- Managing registered options
- Accessing backup and recovery controls
- Reviewing system and security status

Admin access should be limited to users who need administrative authority.

### UR

UR users can work with authorization records and related workflows, including:

- Viewing, creating, and editing authorizations
- Managing timeline events
- Using PDF intake
- Using dashboard and calendar views

UR users do not receive Admin-only user-management, governance-history, audit, system, or backup controls.

### Read Only

Read Only users can view authorization information but cannot create, edit, or delete records.

Read Only access can still expose sensitive information and should be approved, reviewed, and removed when it is no longer needed.

Read Only users cannot use PDF intake preview.

## Least Privilege

Assign the lowest role that supports the user's work:

```text
Admin     Administrative access
UR        Authorization workflow access
Read Only View-only access
```

Do not grant Admin access solely to work around a configuration, interface, or troubleshooting issue.

## User Administration

The Users page is available only to Admins.

It supports:

```text
Create user
Review users
Change role
Activate or deactivate
Reset password
Reset MFA
```

The user table shows account information such as:

```text
Username
Role
Status
MFA status
Last login
Actions
```

The signed-in Admin is identified as the current user.

## Account Names

Usernames are normalized by:

- Trimming leading and trailing whitespace
- Converting text to lowercase

Usernames must be unique.

The web administration interface uses an email-style username. Example:

```text
ur.user@example.invalid
```

Do not include patient information, passwords, security answers, or other sensitive values in usernames.

## Create a User Through the Web Interface

Sign in as an Admin and open the Users page.

Enter:

```text
Username
Role
```

The default role is:

```text
UR
```

Select:

```text
Create
```

CareQueue then:

1. Creates the account as active.
2. Generates a temporary password.
3. Marks the account as requiring a password change.
4. Stores only the Argon2id password hash.
5. Displays the temporary password once.
6. Records a user-creation audit event.

## Temporary Passwords

Web-created and administrator-reset accounts receive a generated temporary password.

The generated password is 24 characters and contains at least:

- One lowercase letter
- One uppercase letter
- One number
- One symbol from the configured set

The plaintext temporary password is displayed once. Only the Argon2id hash is stored.

After the temporary-password panel is dismissed or the page is refreshed, the plaintext value cannot be retrieved.

Deliver temporary credentials using an approved secure method. Do not place them in:

- Screenshots
- Public issue trackers
- Ordinary email
- Unapproved chat systems
- Shared documents
- Browser notes
- Source control

If the temporary password is lost, reset the account again.

## Required Password Change

A new or administrator-reset account is marked as requiring a password change.

After login, the user must provide:

```text
Temporary password
New password
Confirm new password
```

A successful change:

1. Verifies the current password.
2. Confirms the new password differs from the current password.
3. Stores the new Argon2id hash.
4. Clears the required-password-change state.
5. Revokes active sessions for the account.
6. Invalidates supported authentication state associated with the prior credentials.
7. Records the password-change audit event.
8. Requires the user to sign in again.

## Password Policy

CareQueue enforces a shared server-side password policy for account creation, first-time Admin setup, password resets, and password changes.

The current minimum password length is:

```text
12 characters
```

The Admin web interface generates a 24-character temporary password for new users and password resets.

Authenticated password changes also verify the user's current password and require the new password to differ from it.

Organizations should define and communicate their own password-management policy in addition to the application minimums.

## First-Time Admin Setup

CareQueue does not provide public registration.

The first Admin account is the bootstrap account used to enter the normal Admin workflow. The bootstrap setup path is available only while no users exist.

### Windows Installation

The packaged Windows installer can launch the first-time Admin setup interface after installation.

The setup process:

1. Confirms that the local CareQueue API is ready.
2. Confirms that no users exist.
3. Sends the Admin credentials to the loopback-only setup endpoint.
4. Creates the first account with the `Admin` role.
5. Disables the bootstrap path after the account exists.

The setup endpoint accepts only local loopback requests.

The setup interface does not pass the password through command-line arguments.

### Linux Installation

The packaged Linux installer includes:

```text
/opt/carequeue/deployment/linux/CareQueue-AdminSetup.sh
```

For a new installation, the installer runs the setup utility after CareQueue services and HTTPS validation succeed.

The utility:

- Confirms that initial Admin setup is still available.
- Prompts interactively for the Admin username and password.
- Does not place the password on the command line.
- Sends the request only to the loopback CareQueue API.
- Exits without creating another account if bootstrap setup is already complete.

### Development and Maintenance Script

The command-line user creation script is also available for development and approved maintenance workflows.

From `backend` with the appropriate environment active:

```powershell
python scripts\create_user.py `
    --username "carequeue.admin" `
    --role "Admin"
```

The script prompts for the password without printing it to the terminal.

A user created against a development database does not automatically exist in a production database.

Use the Admin web interface for ordinary user onboarding after the first Admin exists.

## Governance Attestation

After the first Admin signs in, CareQueue requires the current organization governance attestation before normal protected application functionality becomes available.

The attestation includes acknowledgments covering organizational security and privacy responsibility, applicable agreements, individual user access, safeguards for devices and exported information, and handling of PHI in testing or demonstration environments.

The attestation records:

```text
Organization
Deployment mode
Accepting Admin
Acceptance time
CareQueue application version
Governance attestation version
```

Only an Admin can accept the organization-level governance attestation.

If the current governance version has not been accepted:

- The Admin can access the governance setup workflow.
- Non-Admin users cannot accept the attestation.
- Normal protected application functionality remains unavailable until an Admin completes the requirement.
- Login, required password change, session management, and other setup paths needed to complete the process remain available.

The Admin System page provides read-only access to the current attestation and append-only attestation history.

The governance attestation version and governance document revision are separate from the CareQueue application version.

Installing a newer CareQueue release does not by itself require re-attestation.

A governance attestation is current only when both its attestation version and document revision match the values required by the installed application. Re-attestation is therefore required when the required governance attestation version changes, when the required governance document revision changes, or when no current attestation exists.

Older historical attestations created before document-revision tracking was introduced may not contain a stored document revision. These records remain part of the append-only governance history but do not satisfy a current requirement that includes a document revision.

The governance workflow supports organizational accountability. It does not itself execute a Business Associate Agreement, establish HIPAA compliance, or replace required administrative, physical, technical, contractual, or legal safeguards.

## Password Storage

CareQueue stores password hashes, not plaintext passwords.

Passwords must not appear in:

- Logs
- Audit metadata
- Environment files
- Browser storage
- Documentation
- Screenshots
- Source control

If a password is forgotten, reset it rather than attempting to recover it.

## Multi-Factor Authentication

CareQueue supports TOTP MFA using a compatible authenticator application.

Users manage MFA from Settings.

### Enabling MFA

To begin enrollment, the user provides the current password.

CareQueue then displays:

- A QR code
- A manual secret
- A setup URI

The user adds CareQueue to an authenticator application and submits the current 6-digit authentication code to confirm enrollment.

MFA is not considered enabled until the confirmation code succeeds.

The MFA secret is sensitive authentication material. It should not be copied into tickets, messages, documentation, or screenshots.

### Signing In With MFA

When MFA is enabled and the device is not currently trusted, login occurs in two steps:

1. Username and password verification.
2. A current 6-digit authenticator code.

A valid MFA code is required before the authenticated application session is created.

Failed MFA attempts are included in security audit and monitoring data.

## Remembered Devices

During successful MFA verification, a user can choose:

```text
Remember this device for 30 days
```

A remembered device may skip the authenticator-code step on later logins after the password has been verified.

Remembered devices:

- Are optional.
- Are separate from the authenticated CareQueue session.
- Do not bypass password verification.
- Do not keep a user permanently signed in.
- Expire after 30 days.
- Can be revoked from Settings.
- Are invalidated during supported security-sensitive account changes.

The raw remembered-device token is stored only in the protected browser cookie. CareQueue stores a keyed digest of the token server-side.

### Revoke Remembered Devices

From Settings, a user can revoke all remembered devices associated with the account.

Revoking remembered devices does not end the current authenticated session. It requires MFA again on a later login from devices that had previously been remembered.

Use this control when a device is lost, replaced, shared unexpectedly, or no longer trusted.

## Admin MFA Reset

An Admin can reset MFA for another user from the Users page.

The reset:

1. Removes the user's authenticator enrollment.
2. Revokes active sessions for that user.
3. Revokes supported remembered-device authentication state.
4. Requires the user to enroll MFA again before MFA protection is restored.
5. Records the administrative MFA-reset action.

Admins cannot use the user-management MFA reset action on their own account.

An MFA reset should be treated as a security-sensitive account-recovery action and should follow the organization's identity-verification process.

## Login

The login page requests:

```text
Username
Password
```

The backend normalizes the username before authentication.

A failed login returns a generic error:

```text
Invalid username or password.
```

The same response is used for an unknown username and an incorrect password.

Before completing an authenticated login, CareQueue verifies:

1. The account exists.
2. The account is active.
3. The password is valid.
4. Required MFA is satisfied or an accepted remembered-device token is present.

After successful authentication, CareQueue:

- Creates a server-side session.
- Stores only a hash of the raw session token.
- Sets the session and CSRF cookies.
- Updates login information.
- Records the login audit event.

Repeated failed password attempts increment the failed-login state. After the configured threshold is reached, the account is temporarily locked.

Successful authentication clears the failed-login state.

## Single Active Session

CareQueue permits one active authenticated session per account.

When a new authenticated session is created, previous active sessions for the same user are revoked.

This applies after both password-only login and completed MFA login.

A user signing in from a second browser or device should therefore expect the previous authenticated CareQueue session to stop working.

A remembered device is not an authenticated session and does not change this rule.

## Server-Side Sessions

The session table stores:

```text
id
user_id
token_hash
created_at
last_seen_at
expires_at
revoked_at
ip_address
user_agent
```

The browser receives the raw session token through an HttpOnly cookie.

The database stores only a hash of that token.

For an authenticated request, CareQueue verifies that:

- The session exists.
- The session is not revoked.
- The session has not expired.
- The user still exists.
- The account remains active.
- Required account setup has been completed.
- Current governance requirements have been satisfied for protected application access.
- The user's role permits the requested action.

## Inactivity Timeout

Authenticated sessions use a server-enforced inactivity timeout.

The default inactivity period is:

```text
20 minutes
```

It is configurable through the deployment setting:

```env
AUTHSTATUS_SESSION_INACTIVITY_MINUTES=20
```

Supported values range from 5 to 480 minutes.

Authenticated activity extends the session expiration while the session is still valid.

An expired session cannot be revived by later activity.

The frontend receives the current server expiration time and uses it to provide warning and logout behavior, but the backend remains authoritative.

## Browser Activity and Session Extension

The CareQueue frontend sends throttled activity updates during supported user interaction.

This allows normal application use to extend the server-side inactivity window without sending a request for every individual browser event.

Activity reporting does not:

- Revive an expired session.
- Override account deactivation.
- Override session revocation.
- Bypass password-change requirements.
- Bypass governance requirements for protected functionality.

## Session Renewal

The session-warning interface allows an active user to explicitly renew the session.

Renewal requires:

- An active authenticated session
- Valid CSRF protection
- An active user account

A successful renewal:

- Rotates the session token.
- Rotates the CSRF token.
- Extends the server-side expiration.
- Returns the updated expiration time to the frontend.

The authenticated session and CSRF cookies remain browser-session cookies rather than becoming long-lived login cookies.

If renewal fails because the session is expired, revoked, or otherwise invalid, the user must sign in again.

## Cross-Tab Session Behavior

CareQueue synchronizes important session state across open tabs from the same browser profile.

When supported by the browser:

- Logout in one CareQueue tab is reflected in other open CareQueue tabs.
- Updated expiration information is shared across tabs.
- An expired or invalid session causes protected frontend state to be cleared.

This synchronization improves consistency between tabs. Server-side session validation remains the security boundary.

## Cookie and CSRF Security

Production session cookies are configured for secure browser handling.

The authenticated session cookie is HttpOnly so frontend JavaScript cannot read the raw session token.

The CSRF cookie is intentionally readable by the frontend so its value can be copied into the matching request header.

Authenticated state-changing requests require:

- The session cookie
- The CSRF cookie
- The matching CSRF header

This applies to actions including:

- Logout
- Session activity updates
- Session renewal
- Password changes
- MFA enrollment
- Remembered-device revocation
- User creation and updates
- Password and MFA resets
- Governance acceptance
- Authorization changes
- Registered-option changes
- Backup and recovery administration

Do not disable CSRF protection to simplify a client or integration.

## Production Origin

Production users should access CareQueue through the approved HTTPS origin.

The packaged private deployment uses:

```text
https://carequeue.local
```

Production browser requests should use the same HTTPS origin for `/api` requests.

Direct browser access to the loopback API is not the supported production user path.

A development API override should not be included in a production frontend build.

## Logout

A successful logout:

1. Revokes the current server-side session.
2. Clears authentication and CSRF cookies.
3. Records the logout audit event.
4. Clears protected frontend state.
5. Returns the browser to login.
6. Synchronizes the logout state to other open CareQueue tabs when supported.

Closing the browser is not a substitute for explicitly logging out on a shared workstation.

## Change Your Own Password

An authenticated user can change the password from Settings.

The current password is required.

A successful password change revokes active sessions for the account and invalidates supported authentication state associated with the prior credentials.

The user must sign in again.

## Reset Another User's Password

An Admin can reset another active user's password.

The reset:

1. Generates a new temporary password.
2. Replaces the stored password hash.
3. Marks the account as requiring a password change.
4. Revokes active sessions for the target user.
5. Invalidates supported remembered-device authentication state.
6. Displays the temporary password once.
7. Records the password-reset audit event.

The reset action is unavailable when:

- The target is the signed-in Admin.
- The target is inactive.
- Another reset is already in progress.
- The account is currently being updated.

An Admin must use Change Password for their own account.

## Change Another User's Role

An Admin can change another user to:

```text
Admin
UR
Read Only
```

A successful change is recorded in the audit log.

The signed-in Admin cannot remove their own Admin role.

Before changing Admin access, confirm that approved administrative access will remain available.

## Deactivate a User

An Admin can deactivate another account.

A deactivated account:

```text
is_active: false
```

remains in the database and appears as inactive in user administration.

The account cannot authenticate, and session validation rejects inactive users.

Supported authentication state associated with the account is invalidated as part of the security-sensitive account change.

The signed-in Admin cannot deactivate their own account.

Deactivation does not remove operating-system, network, VPN, browser-profile, or file access. Those controls must be managed separately.

## Reactivate a User

Reactivation restores the account's active state.

It does not automatically reset the password or restore previously revoked sessions or remembered-device state.

Before reactivation:

- Confirm access is approved.
- Confirm the assigned role remains appropriate.
- Reset credentials if exposure is possible.
- Review why the account was deactivated.

## User Offboarding

When CareQueue access ends:

1. Confirm the correct account.
2. Deactivate it.
3. Confirm the account shows as inactive.
4. Review the assigned role and recent audit activity.
5. Remove workstation, operating-system, network, VPN, and file access separately.
6. Follow the organization's access-removal documentation process.
7. Preserve the CareQueue account record for audit references.

CareQueue deactivates accounts rather than deleting them through the Admin interface.

## Periodic Access Review

Review CareQueue accounts on a defined organizational schedule.

For each user, confirm:

- Access is still required.
- The assigned role remains appropriate.
- The account should remain active.
- Last login activity is reasonable.
- Required-password-change status is understood.
- MFA status matches organizational policy.
- Admin access remains limited.
- No duplicate or unexplained accounts exist.

Governance attestation history should also be reviewed when the organization is validating deployment or compliance records.

## Shared and Service Accounts

Avoid shared application accounts for ordinary users.

Individual accounts improve accountability, access removal, role assignment, MFA enrollment, and audit review.

Windows and Linux service identities are operating-system accounts, not CareQueue application users.

Do not create CareQueue application accounts for service processes unless a supported integration explicitly requires one.

## Audit Events

Security and account activity recorded by CareQueue includes events related to:

```text
Login
Failed login
Temporary lockout
MFA enrollment and verification
Logout
Initial Admin setup
Password change
User creation and update
Password reset
MFA reset
Governance attestation acceptance
Remembered-device security actions
```

Audit metadata must not contain:

- Passwords
- Temporary passwords
- Password hashes
- MFA secrets
- MFA codes
- Raw MFA challenge tokens
- Raw remembered-device tokens
- Session tokens
- CSRF tokens
- Authentication cookies

See [Audit Log](audit-log.md) for the event reference and review guidance.

## Security Monitoring

The Admin System page includes a security monitoring summary for recent authentication activity.

The summary includes indicators such as:

- Failed password logins
- Locked login attempts
- Failed MFA activity
- Distinct source IP counts
- Distinct usernames associated with failures
- Overall severity

Security monitoring is a review aid. It does not replace centralized infrastructure monitoring, operating-system logs, incident response, or organizational security processes.

## Current Limitations

CareQueue does not currently provide:

- Public registration
- Email-based password recovery
- Self-service forgotten-password links
- Single sign-on
- LDAP or Active Directory integration
- Automatic account expiration
- Automatic account deletion
- Per-device remembered-device management in the user interface
- A replacement-password complexity policy beyond the shared minimum length and generated temporary-password controls

## Common Problems

### Duplicate username

Usernames are normalized to lowercase and must be unique.

Use the existing account when appropriate rather than creating a duplicate.

### Temporary password disappeared

Reset the account again. The previous plaintext temporary password cannot be recovered.

### User is stuck on required password change

Confirm:

- The temporary password is correct.
- New password and confirmation match.
- The new password differs from the temporary password.
- The account remains active.
- The session has not expired.

A successful change signs the user out.

### MFA enrollment does not complete

Confirm:

- The current password is correct.
- The authenticator app was configured using the current QR code or manual secret.
- The submitted code is the current 6-digit TOTP value.
- The device running the authenticator has accurate time.

If enrollment was started but not confirmed, the Settings page may show that MFA enrollment is pending.

### A remembered device asks for MFA again

This can occur when:

- The 30-day remembered-device period expired.
- Browser cookies were cleared.
- The remembered-device record was revoked.
- A security-sensitive account change invalidated trusted devices.
- The login is occurring from a different browser profile or device.

Password verification is still required even when the device is remembered.

### Reset MFA is unavailable

Admins cannot reset their own MFA through user management.

Another approved Admin must perform an administrative MFA reset when that workflow is required.

### Role or deactivate controls are unavailable

The signed-in Admin cannot remove their own Admin access or deactivate their own account.

Use another approved Admin for those account-management actions.

### User cannot log in

Check:

- Username spelling
- Password
- Active status
- Temporary lockout status
- MFA requirements
- Whether a remembered device is still valid
- Correct development or production database
- Application origin
- API readiness
- Authentication-related audit events

### Previous session stopped working after another login

This is expected. CareQueue allows one active authenticated session per account.

Signing in again revokes the previous active session.

### User is redirected to governance setup

The current governance attestation has not yet been completed.

An Admin must accept the current organization governance attestation before normal protected application functionality becomes available.

Non-Admin users cannot complete this organization-level requirement.

### 401 from `/api/security/me`

This is expected before login or after the authenticated session has expired or been revoked.

### 403 on a state-changing request

Check:

- Role permission
- Required password-change state
- CSRF cookie
- CSRF header
- Session status
- Account status

### 428 Governance attestation required

The user is authenticated, but the current organization governance attestation has not been completed.

An Admin must complete the governance workflow before protected application routes become available.

### Session renewal fails

The session may be expired, revoked, missing valid CSRF protection, or associated with an inactive account.

Sign in again after resolving the underlying issue.

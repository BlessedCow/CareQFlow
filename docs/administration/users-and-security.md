# Users and Security

CareQueue uses local application accounts, role-based access control, Argon2id password hashing, browser-managed cookies, server-side sessions, and CSRF protection.

This guide covers the full account lifecycle:

- Creating users
- Assigning roles
- Temporary passwords
- Required password changes
- Session behavior
- Password resets
- Deactivation and reactivation
- Access review and offboarding

The backend is authoritative for authentication and authorization. Frontend controls improve usability, but they are not the security boundary.

## Roles

CareQueue supports three roles:

```text
Admin
UR
Read Only
```

### Admin

Admins can use the authorization workflow and manage administrative functions, including:

- Creating users
- Changing another user’s role
- Activating or deactivating another user
- Resetting another user’s password
- Reviewing audit events
- Managing registered options
- Accessing backup and recovery controls

Admin access should be limited to users who need administrative authority.

### UR

UR users can work with authorization records and related workflows, including:

- Viewing, creating, and editing authorizations
- Managing timeline events
- Using PDF intake
- Using dashboard and calendar views

UR users do not receive Admin-only account or audit controls.

### Read Only

Read Only users can view authorization information but cannot create, edit, or delete records.

Read Only access still permits access to sensitive information and must be approved, reviewed, and removed when no longer needed.

Read Only users cannot use PDF intake preview.

## Least Privilege

Assign the lowest role that supports the user’s work:

```text
Admin     Administrative access
UR        Authorization workflow access
Read Only View-only access
```

Do not grant Admin access to work around a user-interface, configuration, or troubleshooting problem.

## User Administration

The Users page is available only to Admins.

It includes:

```text
Create user
Users
```

The user table shows:

```text
Username
Role
Status
Last login
Actions
```

The current Admin is labeled:

```text
Current user
```

## Account Names

Usernames are normalized by:

- Trimming leading and trailing whitespace
- Converting text to lowercase

Usernames must be unique.

The web administration form currently uses an email-style input. Examples:

```text
ur.user@example.invalid
read.only@example.invalid
```

The command-line script also accepts role-based names such as:

```text
carequeue.admin
```

Do not include patient information, credentials, or other sensitive values in usernames.

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
3. Sets `must_change_password` to true.
4. Stores the password using Argon2id.
5. Displays the temporary password once.
6. Records `user.create`.

## Temporary Passwords

Web-created and administrator-reset accounts receive a generated temporary password.

The current generator creates a 24-character password containing at least:

- One lowercase letter
- One uppercase letter
- One number
- One symbol from the configured set

The plaintext password is displayed once. Only the Argon2id hash is stored.

After the panel is dismissed or the page is refreshed, the password cannot be retrieved.

Deliver it through an approved secure method. Do not place it in:

- Screenshots
- Tickets
- Ordinary email
- Chat
- Shared documents
- Browser notes

When the temporary password is lost, reset the account again.

## Required Password Change

A new or reset account is marked:

```text
Password change required
```

After login, the user must enter:

```text
Temporary password
New password
Confirm new password
```

A successful change:

1. Verifies the current password.
2. Confirms the new password differs from it.
3. Stores a new Argon2id hash.
4. Clears `must_change_password`.
5. Revokes all active sessions for the account.
6. Records `security.password_change`.
7. Requires the user to sign in again.

## Password Policy Boundary

The command-line creation script requires at least 12 characters.

The web Admin flow generates a strong 24-character temporary password.

The current authenticated password-change endpoint verifies that the current password is correct and the new password is different. It does not currently enforce a separate centralized minimum length or complexity rule for the user-selected replacement password.

Until that is centralized, the deploying organization should define and communicate its password standard.

## Create the First Admin

CareQueue does not provide public registration.

The first Admin is normally created with:

```text
backend/scripts/create_user.py
```

### Development

From `backend` with the development virtual environment active:

```powershell
python scripts\create_user.py `
    --username "carequeue.admin" `
    --role "Admin"
```

### Windows production

From the installed backend:

```powershell
Set-Location "C:\Program Files\CareQueue\backend"
```

Load the production environment into the current PowerShell process:

```powershell
$environmentFile = (
    "C:\ProgramData\CareQueue\Config\carequeue.env"
)

Get-Content -LiteralPath $environmentFile |
ForEach-Object {
    $line = $_.Trim()

    if (
        $line `
        -and -not $line.StartsWith("#") `
        -and $line.Contains("=")
    ) {
        $name, $value = $line.Split("=", 2)

        [Environment]::SetEnvironmentVariable(
            $name.Trim(),
            $value.Trim(),
            "Process"
        )
    }
}
```

Create the Admin:

```powershell
& ".\.venv\Scripts\python.exe" `
    ".\scripts\create_user.py" `
    --username "carequeue.admin" `
    --role "Admin"
```

A user created against the development database does not automatically exist in production.

The command-line script creates the account with the password entered by the administrator and does not currently require a password change on first login.

Use the web Admin flow for ordinary onboarding.

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

When a password is forgotten, reset it rather than attempting to recover it.

## Login

The login page requests:

```text
Username
Password
```

The backend normalizes the username before authentication.

A failed login returns:

```text
Invalid username or password.
```

The same response is used for an unknown username and an incorrect password.

A successful login:

1. Verifies the account exists and is active.
2. Verifies the Argon2id password hash.
3. Creates a server-side session.
4. Stores only the hashed session token.
5. Sets the session and CSRF cookies.
6. Updates login information.
7. Records `security.login`.

A failed login records:

```text
security.login_failed
```

The user table contains `failed_login_count` and `locked_until`, but the current authentication flow does not implement a documented automatic account-lockout policy.

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

For each authenticated request, CareQueue confirms:

- The session exists
- The session is not revoked
- The session has not expired
- The user still exists
- The account remains active
- The role permits the requested action

## Cookie and CSRF Security

Production session cookies should remain:

```text
HttpOnly
Secure
SameSite restricted
Path restricted
```

The CSRF cookie is readable by frontend request code so its value can be copied into the CSRF header.

Authenticated state-changing requests require:

- The session cookie
- The CSRF cookie
- The matching CSRF header

This applies to actions such as:

- Logout
- Session renewal
- Password change
- User creation and updates
- Password resets
- Authorization changes
- Registered-option changes
- Backup and recovery administration

Do not disable CSRF protection to simplify a client or script.

## Production Origin

Production users should access CareQueue through the approved HTTPS origin, such as:

```text
https://carequeue.local
```

Production browser requests should use:

```text
https://carequeue.local/api/...
```

They should not use:

```text
http://localhost:8000/api/...
```

A localhost API URL in production indicates that a development frontend override was included in the build.

## Session Expiration

CareQueue uses server-side session expiration.

The backend returns the expiration time to the frontend.

The frontend uses it to:

- Display the required expiration warning
- Offer session renewal
- Optionally display a countdown
- Clear protected state after expiration

The backend remains authoritative.

The optional countdown does not extend the session.

## Session Renewal

Renewal requires:

- An active session
- A valid CSRF token
- An active user account

A successful renewal rotates:

- The session token
- The CSRF token

It also refreshes cookie lifetimes and returns the updated expiration time.

When renewal fails because the session is invalid, the frontend should clear protected state and return to login.

## Logout

A successful logout:

1. Revokes the current server-side session.
2. Clears authentication and CSRF cookies.
3. Records `security.logout`.
4. Clears protected frontend state.
5. Returns the browser to login.

Closing the browser is not a substitute for logging out on a shared workstation.

## Change Your Own Password

An authenticated user can change their password from Settings.

The current password is required.

A successful change revokes all active sessions for the account, including the current one.

The user must sign in again.

## Reset Another User’s Password

An Admin can reset another active user’s password.

The reset:

1. Generates a new temporary password.
2. Replaces the password hash.
3. Sets `must_change_password`.
4. Revokes all active sessions for the target user.
5. Displays the temporary password once.
6. Records `user.password_reset`.

The reset action is disabled when:

- The target is the current Admin
- The target is inactive
- Another reset is in progress
- The account is being updated

An Admin must use Change Password for their own account.

## Change Another User’s Role

An Admin can change another user to:

```text
Admin
UR
Read Only
```

A successful change records:

```text
user.update
```

The signed-in Admin cannot change their own role.

Before changing Admin access, confirm that another approved active Admin will remain.

The current implementation protects an Admin from removing their own access, but it does not separately enforce that at least one other Admin remains available.

## Deactivate a User

An Admin can deactivate another account.

A deactivated account:

```text
is_active: false
```

remains in the database and appears as:

```text
Inactive
```

The account cannot authenticate, and session validation rejects inactive users.

The signed-in Admin cannot deactivate their own account.

Deactivation does not remove operating-system, network, VPN, browser-profile, or file access. Those controls must be managed separately.

## Reactivate a User

Reactivation restores:

```text
is_active: true
```

It does not reset the password automatically.

Before reactivation:

- Confirm access is approved
- Confirm the role is still appropriate
- Reset the password when exposure is possible
- Review why the account was deactivated

## User Offboarding

When access ends:

1. Confirm the correct account.
2. Deactivate it.
3. Confirm the status is Inactive.
4. Review the assigned role and recent audit activity.
5. Remove workstation, network, VPN, and file access separately.
6. Record the access-removal time.
7. Preserve the CareQueue account for audit references.

CareQueue deactivates accounts rather than deleting them through the Admin interface.

## Periodic Access Review

Review accounts on a defined schedule.

For each user, confirm:

- Access is still needed
- The role remains appropriate
- The account should remain active
- Last login is reasonable
- Password-change-required status is understood
- Admin access remains limited
- No duplicate or unexplained accounts exist

## Shared and Service Accounts

Avoid shared accounts for ordinary users.

Individual accounts improve accountability, access removal, role assignment, and audit review.

Windows and Linux service identities are operating-system accounts, not CareQueue application users.

Do not create CareQueue application accounts for service processes unless a future integration explicitly requires one.

## Audit Events

Relevant actions include:

```text
security.login
security.login_failed
security.logout
security.password_change
user.create
user.update
user.password_reset
```

Audit metadata must not contain:

- Passwords
- Temporary passwords
- Password hashes
- Session tokens
- CSRF tokens
- Authentication cookies

See [Audit Log](audit-log.md) for the full event reference.

## Current Limitations

CareQueue does not currently provide:

- Public registration
- Email-based password recovery
- Self-service forgotten-password links
- Multi-factor authentication
- Single sign-on
- LDAP or Active Directory integration
- Automatic account expiration
- Automatic account deletion
- Individual Admin session revocation
- A documented failed-login lockout policy
- A centralized replacement-password complexity policy

## Common Problems

### Duplicate username

Usernames are normalized to lowercase and must be unique.

Use the existing account when appropriate rather than creating a duplicate.

### Temporary password disappeared

Reset the account again. The previous plaintext password cannot be recovered.

### User is stuck on password change

Confirm:

- The temporary password is correct
- New password and confirmation match
- The new password differs from the temporary password
- The account remains active
- The session has not expired

A successful change signs the user out.

### Reset password is disabled

The target may be:

- The current Admin
- Inactive
- Already being reset
- Currently being updated

### Role or deactivate controls are disabled

The current Admin cannot remove their own Admin access.

Use another approved Admin.

### User cannot log in

Check:

- Username spelling
- Password
- Active status
- Correct development or production database
- Application origin
- API readiness
- Failed-login audit events

### 401 from `/api/security/me`

This is expected before login when no active session exists.

### 403 on a state-changing request

Check:

- Role permission
- CSRF cookie
- CSRF header
- Session status
- Account status

### Session renewal fails

The session may be expired, revoked, missing valid CSRF protection, or associated with an inactive account.

Sign in again after resolving the underlying issue.

## Related Documentation

```text
docs/administration/audit-log.md
docs/operations/health-and-troubleshooting.md
docs/deployment/windows.md
SECURITY.md
```

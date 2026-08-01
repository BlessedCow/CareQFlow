# Registered Options

CareQueue uses registered options to keep frequently reused workflow values consistent.

Current categories:

```text
facility
insurance
web_portal
```

These values are used by authorization forms, filters, PDF intake review, and submission-method fields.

Registered options standardize selection lists. They do not prove that a facility, payer, or portal is operationally correct.

## Access

All authenticated users can read registered options.

Only Admins can create or delete them.

Backend authorization is authoritative.

## Settings Page

Registered options are managed under Settings.

Current sections:

```text
Registered Facilities
Registered Insurances
Web Portals
```

Admins see add and remove controls.

UR and Read Only users can view and use the values but cannot manage the lists.

## Categories

### Facilities

Category:

```text
facility
```

Used by:

- Add-authorization forms
- Authorization editing
- PDF intake matching
- Dashboard and queue filters
- Calendar and workflow views

### Insurances

Category:

```text
insurance
```

Used by:

- Add-authorization forms
- Authorization editing
- PDF intake matching
- Dashboard and queue filters

Parts of the authorization model may also refer to the selected insurance as a payer.

### Web portals

Category:

```text
web_portal
```

Used when the submission method is a web portal.

Store only a stable portal display name.

Do not store:

- Usernames
- Passwords
- MFA codes
- Security answers
- Tokens
- Credential-bearing URLs
- Patient information

## Built-In `Other`

CareQueue initializes one protected option in every category:

```text
Other
```

Protected entries are marked:

```text
Built in
```

They use:

```text
is_protected: true
```

and cannot be deleted through the repository or API.

## Storage

Registered options are stored in:

```text
registered_options
```

Current columns:

```text
id
category
name
normalized_name
is_protected
created_at
updated_at
```

The database restricts categories to:

```text
facility
insurance
web_portal
```

## Uniqueness and Normalization

Options are unique by:

```text
category
normalized_name
```

When an option is created, CareQueue:

- Trims leading and trailing whitespace
- Collapses repeated internal whitespace
- Uses case-insensitive normalization for duplicate checks

Example input:

```text
  Example   Health   Plan
```

Stored display name:

```text
Example Health Plan
```

These are duplicates within the same category:

```text
Example Health Plan
example health plan
EXAMPLE HEALTH PLAN
```

The same visible name may exist in different categories.

## Validation

Empty or whitespace-only names are rejected.

Safe error:

```text
Option name is required.
```

Duplicates within a category are rejected.

Safe error:

```text
A registered option with this name already exists.
```

Duplicate creation returns:

```text
409 Conflict
```

## API

Base path:

```text
/api/registered-options
```

### List options

```text
GET /api/registered-options
```

Access:

```text
Authenticated user
```

Optional category filter:

```text
GET /api/registered-options?category=facility
```

Allowed categories:

```text
facility
insurance
web_portal
```

### Create an option

```text
POST /api/registered-options
```

Access:

```text
Admin
```

Example:

```json
{
  "category": "facility",
  "name": "Example Recovery Center"
}
```

Successful status:

```text
201 Created
```

Unexpected request fields are rejected.

### Delete an option

```text
DELETE /api/registered-options/{option_id}
```

Access:

```text
Admin
```

Successful response:

```json
{
  "deleted": true
}
```

Protected options cannot be deleted.

Unknown IDs return:

```text
404 Not Found
```

## Add an Option

As an Admin:

1. Open Settings.
2. Choose the correct category.
3. Enter the option name.
4. Select Add.
5. Confirm the value appears in the list.

After success:

- The input clears
- The list updates
- `registered_option.create` is recorded

## Remove an Option

As an Admin:

1. Locate the option.
2. Select Remove.
3. Confirm the removal.

Protected options display:

```text
Built in
```

instead of a remove control.

A successful deletion records:

```text
registered_option.delete
```

## Deleting an Option Does Not Rewrite Records

Deleting a registered option removes it from the reusable selection list.

It does not modify existing authorization records containing that value.

Facility and insurance filters are built from both:

- Current registered options
- Values already present on authorization records

This preserves filtering for legacy values.

## Open Form Behavior

When an open authorization form contains a facility, insurance, or portal that is no longer registered, the frontend may reset the selection to:

- The first available option
- An empty value when no option exists

Because each category includes protected `Other`, there should normally be at least one available value.

Review open forms after changing registered options.

## Sorting

The backend orders options by category and normalized name.

When filtering to one category, it orders by normalized name.

The frontend also applies alphabetical display sorting.

Do not depend on insertion order.

## PDF Intake Matching

PDF intake compares extracted facility and insurance values with registered options.

When a match exists, CareQueue applies the registered value.

When no match exists, the review workflow warns that the value is not registered.

The PDF does not automatically create a new registered option.

The user must:

- Select an existing option
- Correct the extracted value
- Ask an Admin to add an approved option

## Matching Limitations

Matching is based on the displayed registered value.

Differences such as these may prevent a match:

```text
Example Health Plan
Example Healthplan
Example Health Plan, Inc.
EHP
```

CareQueue does not currently provide aliases.

Before adding another option, confirm whether the existing naming standard should be used instead.

## Filter Behavior

Facility and insurance filter lists combine:

- Registered values
- Values stored on existing authorization records

The first filter option is:

```text
All
```

Web portals are not included in this facility and insurance filter behavior.

## Audit Events

Create:

```text
registered_option.create
```

Delete:

```text
registered_option.delete
```

Resource type:

```text
registered_option
```

Current metadata includes:

```text
category
```

The option name is not intentionally included in audit metadata.

## Security Boundary

Registered options must not contain secrets or patient data.

Do not store:

- Portal credentials
- Authentication tokens
- Patient names
- Member IDs
- Group numbers
- Dates of birth
- Authorization numbers
- Clinical notes
- API keys
- Encryption keys

The `web_portal` category stores only the portal display name.

## Naming Guidance

### Facilities

Use the approved operational name.

Avoid unnecessary variants such as:

```text
Example Recovery Center
Example Recovery Ctr
ERC
Example Recovery Center LLC
```

unless each represents a real workflow distinction.

### Insurances

Use the payer name users need to recognize.

Distinguish the payer from a utilization-management vendor when required by the workflow.

### Web portals

Use a stable portal label.

Examples:

```text
Availity
Carelon Provider Portal
Lucet Portal
```

Do not include credentials.

## Maintenance

Before adding an option:

1. Confirm the request is approved.
2. Search the existing category.
3. Confirm the correct category.
4. Check naming consistency.
5. Add the option.
6. Verify it appears in the expected form.
7. Verify PDF intake matching when relevant.

Before deleting an option:

1. Confirm it is not protected.
2. Confirm it is no longer needed for new records.
3. Review active workflows.
4. Review PDF intake effects.
5. Understand that existing records will not be rewritten.

## Current Limitations

The current registered-option API supports:

```text
List
Create
Delete
```

It does not currently support:

- Rename
- Update
- Aliases
- Merge
- Active or inactive status
- Effective dates
- Usage counts
- Rename history

To correct a name:

1. Add the corrected option.
2. Confirm it appears in forms.
3. Review active workflow impact.
4. Remove the old option when appropriate.

Existing authorization records retain the old text.

## Common Problems

### Lists do not load

Check:

- User is authenticated
- API readiness succeeds
- Correct environment is open
- Registered-options endpoint succeeds
- Database is available

### Add button is disabled

The input may be empty, whitespace-only, or another save or delete operation may still be running.

### Duplicate error

Check for capitalization, spacing, punctuation, abbreviation, or naming variants.

### Remove control is missing

Possible reasons:

- Current user is not an Admin
- Option is protected
- List is still loading

### Protected `Other` cannot be deleted

This is expected.

### Deleted option still appears in filters

Existing authorization records still contain the value.

### PDF intake says a value is unregistered

Select an existing option, correct the extracted value, or add the approved option as Admin.

## Related Documentation

```text
docs/workflows/authorization-workflow.md
docs/workflows/pdf-intake.md
docs/administration/audit-log.md
docs/administration/users-and-security.md
```

# Authorization Workflow

CareQueue’s primary workflow is the creation, tracking, review, and completion of authorization records.

This guide covers the authorization record itself, the queue, filters, dashboard and calendar behavior, editing, deletion, and the relationship between the current record and its timeline.

For PDF-assisted data entry, see [PDF Intake](pdf-intake.md).

For registered facilities, insurers, portals, and option naming rules, see [Registered Options](../administration/registered-options.md).

## Roles

Current roles:

```text
Admin
UR
Read Only
```

Admin and UR users can create and manage authorization records.

Read Only users can view records but cannot create, edit, or delete them.

Backend permission checks are authoritative. Frontend controls should make the workflow clear, but the API remains the enforcement point.

## Authorization Record

An authorization record may include:

- Client name
- Member ID
- Group number
- Date of birth
- Facility
- Insurance
- Level of care
- Initial admit date
- Requested review date
- Authorization type
- Submission method
- Submission details
- Status
- Authorization phone
- Notes
- Timeline events
- Created and updated timestamps

The form and backend schema determine which fields are required.

## Create an Authorization

Open the authorization queue and select:

```text
Add Authorization
```

Complete the form and review every value before submitting.

After successful creation:

- The record appears in the queue
- Dashboard counts may change
- Calendar entries may change
- Filters may include the new values
- `auth.create` is recorded

## Core Fields

### Client name

Enter the approved client name format.

Do not add dates, diagnoses, room numbers, payer notes, or identifiers to the name field.

### Member ID and group number

Enter the identifiers used for the authorization workflow.

Confirm whether the payer expects:

- Medical identifiers
- Behavioral-health identifiers
- Another payer-specific identifier

Use the correct pair for the authorization being tracked.

### Date of birth

Enter the client’s date of birth.

Do not substitute:

- Admit date
- Review date
- Insurance effective date
- Document creation date

### Facility

Select a registered facility.

When the facility is missing:

- Check for an existing spelling variant
- Ask an Admin to add the approved value
- Use `Other` only when appropriate

### Insurance

Select the approved insurance or payer value.

Use the organization’s established naming convention, especially when distinguishing:

- Insurance company
- Behavioral-health administrator
- Utilization-management vendor

### Level of care

Select the current level of care.

Current workflows may include:

```text
DTX
RTC
PHP
IOP
```

Level of care affects filters, dashboard summaries, queue views, and reporting.

Legacy records may contain older values. Review them rather than silently rewriting them.

### Initial admit date

The initial admit date is the original admission date for the tracked episode or level of care.

It is not the same as:

- Requested review date
- Concurrent review date
- Last covered date
- Submission date

### Requested review date

The requested review date is the next authorization or review action date.

It drives due and overdue visibility in:

- Queue
- Dashboard
- Calendar

### Authorization type

Use the type that matches the workflow.

Examples:

```text
Initial
Concurrent
```

### Submission method

Select the actual submission method.

Current workflows may include:

- Fax
- Phone
- Web portal
- Another supported method

The selected method may reveal additional fields.

For web portals, store only the registered portal name. Do not place credentials in the authorization record.

### Status

Status should describe the current operational state.

Use the values provided by the form.

Use timeline events for dated details and workflow history.

### Notes

Use notes for concise operational context that belongs on the current record.

Do not place passwords, portal credentials, session tokens, encryption keys, copied documents, or unnecessary clinical detail in notes.

## Save the Record

A successful create operation:

1. Validates the request.
2. Encrypts selected sensitive fields.
3. Writes the authorization.
4. Updates frontend state.
5. Records `auth.create`.

Audit metadata identifies submitted field names rather than copying sensitive values.

## View and Edit

Open a record from the queue to review its details and timeline.

Admin and UR users may edit the record.

A successful update:

1. Validates the changes.
2. Encrypts selected sensitive fields.
3. Writes the update.
4. Refreshes frontend state.
5. Records `auth.update`.

Audit metadata identifies changed field names.

## Editing Dates

When editing:

- Keep the initial admit date as the original admission date
- Keep the requested review date aligned with the next action
- Do not overwrite history merely to make a record appear current
- Use timeline events to preserve review history

## Editing Level of Care

Use a currently accepted value.

When correcting a legacy record:

- Confirm the actual level of care
- Preserve important history through timeline events
- Recheck dashboard and filter behavior

## Delete an Authorization

Delete a record only when:

- It was created in error
- It is a duplicate
- Removal is approved
- Retention requirements allow deletion

Deletion records:

```text
auth.delete
```

Do not delete a valid completed authorization merely because the workflow is finished.

## Duplicate Records

Before creating a new record, search for the same:

- Client
- Facility
- Insurance
- Level of care
- Admit date
- Review date

When a duplicate exists, update the valid record when appropriate and remove only the mistaken duplicate.

## Authorization Queue

Use the queue to:

- Identify due items
- Identify overdue items
- Filter by facility
- Filter by insurance
- Filter by level of care
- Filter by status
- Search for a record
- Open details

## Filters

Filter values may come from:

- Registered options
- Existing authorization records

This preserves access to legacy facility and insurance values after a registered option is removed.

Clear filters before concluding that a record is missing.

A record may be hidden by:

- Facility filter
- Insurance filter
- Level-of-care filter
- Status filter
- Search text
- Dashboard-applied filter
- Calendar context

## Dashboard Interaction

Dashboard cards summarize authorization data.

Current behavior may allow a level-of-care item to filter the queue.

For example:

- Double-click to apply the level-of-care filter
- Double-click again to clear it

A filtered dashboard count is not the total database count.

## Calendar Interaction

The calendar presents authorization workflow dates.

Use it to review:

- Upcoming review dates
- Due items
- Overdue items
- Daily workload

The calendar is a view of authorization data, not a separate master record.

## Timeline Events

Use timeline events for dated workflow history, such as:

- Submission
- Follow-up
- Approval
- Denial
- Peer-to-peer
- Appeal
- Additional information sent
- Review-date change
- Coverage update

Use the main authorization record for the current state.

Use timeline events for what happened and when.

## Current Record Versus Timeline

Use the authorization record for:

- Current status
- Current requested review date
- Current submission method
- Current facility
- Current payer
- Current level of care
- Current member information

Use the timeline for:

- Follow-up attempts
- Responses
- Decisions
- Changes over time
- Historical context

## PDF-Assisted Intake

PDF intake previews supported documents and copies reviewed values into the ordinary authorization form.

It does not create the authorization automatically.

After applying PDF values:

- Review the full form
- Confirm dates
- Confirm identifiers
- Confirm facility and insurance
- Confirm authorization phone
- Correct fields marked as needing review
- Submit only after correction

See [PDF Intake](pdf-intake.md) for supported templates, confidence, review requirements, and file limits.

## Sensitive Fields

Selected authorization fields are encrypted before database storage.

Adding a new sensitive field requires review of:

- Field-level encryption
- SQLCipher storage
- Role restrictions
- Audit exclusion
- Log exclusion
- Backup and restore behavior

## Audit Events

Authorization actions:

```text
auth.create
auth.update
auth.delete
```

Timeline actions:

```text
auth_event.create
auth_event.update
auth_event.delete
```

Audit metadata should contain field names and resource identifiers, not sensitive values.

## Common Problems

### Add Authorization is missing

Check the user role and session.

Read Only users cannot create records.

### Form will not submit

Review:

- Required fields
- Date formats
- Level of care
- Registered facility
- Registered insurance
- Submission details
- Validation messages

### Record does not appear

Check:

- Create request succeeded
- Active filters
- Dashboard-applied filter
- Correct environment
- API readiness

### Edit or delete fails

Check:

- Current role
- Session status
- CSRF handling
- Record still exists
- Submitted values are valid
- API response

### Queue appears empty

Clear all filters and search text.

### Dashboard count does not match the queue

Check active filters, selected dashboard items, legacy values, and whether both views use the same loaded dataset.

### Calendar date appears wrong

Review the requested review date, time zone, edit history, and timeline events before changing the record.

## Related Documentation

```text
docs/workflows/pdf-intake.md
docs/administration/registered-options.md
docs/administration/audit-log.md
docs/administration/users-and-security.md
docs/troubleshooting/index.md
```

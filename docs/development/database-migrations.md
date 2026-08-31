# Database Migrations

This guide explains how CareQFlow database schema migrations are structured, registered, tested, and maintained.

Use this guide when changing an existing database schema in a way that must be applied safely to installations created by an earlier CareQFlow release.

For operator-facing upgrade procedures, see:

- [Upgrade and Migration Safety](../operations/upgrades.md)
- [Windows Deployment](../deployment/windows.md)
- [Linux Deployment](../deployment/linux.md)
- [Backup and Recovery](../workflows/backup-and-recovery.md)

## Migration Architecture

CareQFlow initializes its normal schema and then runs registered migrations from:

```text
backend/authstatus_api/persistence/migration_runner.py
```

Migration step implementations are stored under:

```text
backend/authstatus_api/persistence/migration_steps/
```

The current registered migration sequence is:

```text
0001_security_walkthrough_columns
0002_security_authentication_and_session_columns
0003_authorization_core_columns
0004_authorization_denial_follow_up_columns
0005_governance_append_only_history
0006_audit_event_columns
0007_governance_document_revision
```

Applied migrations are recorded in:

```text
schema_migrations
```

The ledger stores:

```text
migration_id
applied_at
```

The migration ID is the permanent identity of a migration. The applied timestamp records when that migration was successfully recorded for that database.

## How Migrations Run

`initialize_schema()` creates or initializes the current application tables and then calls:

```python
run_registered_migrations(conn)
```

Registered migrations are sorted by migration ID before execution.

For each migration that is not already present in `schema_migrations`, the runner:

1. Creates a database savepoint.
2. Calls the migration's `apply` function.
3. Inserts the migration ID and UTC application timestamp into `schema_migrations`.
4. Releases the savepoint.

If the migration raises an exception, the runner:

1. Rolls back to that migration's savepoint.
2. Releases the savepoint.
3. Does not record the migration as applied.
4. Raises `MigrationError`.

Previously applied migration IDs are skipped.

This makes repeated schema initialization safe with respect to migrations that have already completed.

## Migration IDs

Migration IDs must be:

- Non-empty.
- Unique.
- Ordered lexically in the sequence in which migrations must run.
- Permanent once released.

Use the existing four-digit numeric prefix followed by a concise descriptive name:

```text
0008_example_schema_change
```

When adding the next migration, use the next unused sequence number.

Do not:

- Rename a migration after it has shipped.
- Reuse an existing migration ID for different behavior.
- Change an old migration ID to improve wording.
- Insert a newly released migration before migrations that may already exist in deployed databases.

A released migration ID may already be stored in customer or test databases. Changing its meaning breaks the relationship between source code and the migration ledger.

## Adding a Migration

### 1. Add the migration step

Add the migration function to the most appropriate module under:

```text
backend/authstatus_api/persistence/migration_steps/
```

Use an existing domain module when the migration clearly belongs there, such as:

```text
security.py
authorizations.py
audit.py
governance.py
```

Create a new migration-step module only when the change belongs to a distinct domain that is not cleanly represented by the existing files.

Migration functions receive the active database connection:

```python
def add_example_column(conn: Any) -> None:
    ...
```

The migration function must not open a second application database connection.

### 2. Make the migration safe for existing data

A migration must account for databases that already contain production records.

Before altering an existing table, inspect the current schema when necessary. Existing migrations commonly use:

```sql
PRAGMA table_info(table_name)
```

to determine whether a column is already present.

For example:

```python
existing_columns = {
    row["name"]
    for row in conn.execute(
        "PRAGMA table_info(example_table)"
    ).fetchall()
}

if "example_column" not in existing_columns:
    conn.execute(
        "ALTER TABLE example_table "
        "ADD COLUMN example_column TEXT"
    )
```

Choose defaults and nullability based on what can truthfully be known about historical records.

Do not invent historical data merely to satisfy a new non-null field.

For example, governance document revision is nullable for legacy attestations because an exact document revision cannot be reconstructed reliably for records created before revision tracking existed.

### 3. Register the migration

Import the migration function in:

```text
backend/authstatus_api/persistence/migration_runner.py
```

Then append a new `Migration` entry to `MIGRATIONS`:

```python
Migration(
    migration_id="0008_example_schema_change",
    apply=add_example_schema_change,
),
```

Keep the registry readable and in migration-ID order even though the runner also sorts migrations before execution.

### 4. Update current-schema creation when appropriate

A migration upgrades older databases.

Fresh databases should normally be created directly in the current schema shape rather than depending on a chain of historical `ALTER TABLE` operations to become current.

When a schema change affects a table's current definition, update the appropriate table initializer as well as adding the migration for older databases.

The migration remains necessary because existing installations may already have the previous table shape.

## Migration Design Rules

### Preserve existing records

Schema changes must preserve existing application data unless the migration is explicitly designed and reviewed as a destructive operation.

Tests should prove preservation for representative legacy rows.

### Keep migrations deterministic

A migration should produce the same intended schema result whenever it is applied to a database at the expected preceding state.

Avoid behavior that depends on:

- Wall-clock business rules.
- External network services.
- User interaction.
- Unrelated application state outside the database.
- Non-deterministic values unless they are required migration metadata.

### Use the supplied connection

Migration functions must use the `conn` provided by the runner.

Do not call `get_conn()` from inside a migration step.

Using a second connection can break transaction and savepoint guarantees and can create locking problems.

### Do not commit inside a migration

The migration runner and schema initialization path control transaction boundaries.

A migration step must not call:

```python
conn.commit()
```

or otherwise independently finalize the transaction.

### Do not manually modify the migration ledger

Application code, maintenance scripts, and operator documentation must not use direct changes to `schema_migrations` as a workaround for a failed migration.

If a migration fails, fix the migration or recover the database through the supported backup and recovery process.

### Prefer additive changes

Additive schema changes are generally safer for upgrades than destructive rewrites.

When a destructive change is necessary, it requires dedicated migration logic, preservation tests, upgrade tests, and a recovery plan.

### Keep application startup failure visible

Migration errors must not be swallowed.

A failed required migration should prevent normal initialization from appearing successful.

## Idempotency

The migration runner guarantees that a successfully recorded migration ID is not applied again.

Migration-step functions should also be reasonably defensive when practical.

Examples include:

- Checking whether a column already exists before `ALTER TABLE`.
- Using `CREATE TRIGGER IF NOT EXISTS`.
- Using `CREATE TABLE IF NOT EXISTS` where appropriate.

This is useful for migration tests, partially prepared legacy fixtures, and recovery scenarios.

Do not use idempotency checks to hide an unexpected incompatible schema. A migration should still fail when the database state cannot be upgraded safely.

## Testing Requirements

Migration behavior is primarily tested in:

```text
backend/tests/persistence/test_migration_runner.py
```

When adding a migration, add or update tests that cover the behavior appropriate to the change.

At minimum, migration work should verify the following where applicable.

### Registry coverage

Confirm the new migration appears in the expected ordered registry results and in the applied migration ledger.

### Legacy schema upgrade

Create a database or table in the old shape, run the migration or `init_db()`, and verify:

- The new schema element exists.
- Existing rows are preserved.
- Existing values remain correct.
- New fields receive only safe and intentional defaults.

### Fresh current schema

Verify the migration does not break a database whose table initializer already creates the current schema.

### Idempotency

Run the relevant migration path more than once and verify the second run does not duplicate schema changes or corrupt data.

### Failure rollback

When the migration contains meaningful multi-step behavior, add a failure-path test when practical to confirm partial changes are not recorded as a completed migration.

The migration runner itself already has coverage proving that a failed migration is rolled back to its savepoint and is not added to `schema_migrations`.

### Cross-migration integration

Update the registered-migration integration expectations so the complete ordered list includes the new migration.

The current test suite also exercises legacy databases through the registered migration chain. Extend those fixtures when the new migration depends on a table or schema state not already represented.

## Example Workflow

For a hypothetical new authorization column:

1. Update the current authorization table definition.
2. Add an upgrade function under the authorization migration-step module.
3. Check the legacy table schema before adding the column.
4. Register `0008_...` in `migration_runner.py`.
5. Add a legacy database test containing an existing authorization row.
6. Run initialization.
7. Verify the existing authorization remains intact.
8. Verify the new column exists with the intended legacy value or nullability.
9. Verify the new migration ID is recorded.
10. Run initialization again and verify no additional migration is applied.

## Reviewing Migration Changes

Before merging a migration, confirm:

- The migration ID is new and correctly ordered.
- The migration ID will never need to be renamed.
- Fresh schema creation matches the intended final schema.
- Existing data is preserved.
- Historical values are not fabricated.
- The migration uses only the supplied connection.
- The migration does not commit independently.
- Failure remains visible as `MigrationError`.
- Legacy upgrade coverage exists.
- Current-schema coverage exists.
- Idempotency is covered.
- Registry expectations are updated.
- Operator upgrade and recovery documentation is updated when the change affects deployment behavior.

## Validation Commands

Run the migration-specific tests:

```powershell
pytest backend/tests/persistence/test_migration_runner.py -q
```

Run the broader persistence tests when the migration affects additional persistence behavior:

```powershell
pytest backend/tests/persistence -q
```

Run relevant domain tests for the schema being changed.

Then run Ruff:

```powershell
ruff check backend/authstatus_api/persistence backend/tests/persistence --fix
```

Before treating a migration-bearing release as ready, also run the repository's broader backend and release validation required for that milestone.

# Encryption Key Lifecycle

CareQueue uses multiple independent encryption keys because each key protects a different layer of data. Key custody, rotation, recovery, and retirement must be handled as operational security procedures rather than as one-time installation steps.

This document describes the expected lifecycle for CareQueue encryption keys and the safeguards that should be in place before a production deployment is considered recoverable.

## Scope

CareQueue currently uses these encryption settings:

```env
AUTHSTATUS_ENCRYPTION_KEY=
AUTHSTATUS_PREVIOUS_ENCRYPTION_KEY=
AUTHSTATUS_SQLCIPHER_KEY=
AUTHSTATUS_BACKUP_ENCRYPTION_KEY=
```

Their purposes are different:

- `AUTHSTATUS_ENCRYPTION_KEY` is the current field-level encryption key. It protects selected sensitive authorization fields, authorization event notes, stored MFA secrets, and encrypted authorization documents.
- `AUTHSTATUS_PREVIOUS_ENCRYPTION_KEY` is a temporary field-level key used only during a controlled field-key rotation window so data encrypted with the prior key can still be read and migrated to the new current key.
- `AUTHSTATUS_SQLCIPHER_KEY` opens the SQLCipher database when production database encryption is enabled.
- `AUTHSTATUS_BACKUP_ENCRYPTION_KEY` encrypts and decrypts CareQueue `.db.enc` backup files.

These keys are not interchangeable. Production validation requires configured encryption roles to use different key values.

## Core Rules

The following rules apply to every production deployment:

1. Generate each key independently.
2. Never reuse a key across field encryption, SQLCipher, or backup encryption.
3. Never commit keys to source control.
4. Never place keys in issue reports, screenshots, documentation, ordinary chat, email, audit metadata, logs, scheduled-task arguments, or service command lines.
5. Restrict key access to the CareQueue runtime identity and authorized administrators who require recovery access.
6. Keep recoverable key copies separate from the database and backup files they protect.
7. Maintain at least one approved recovery copy outside the CareQueue host when organizational policy requires recovery after complete host loss.
8. Test recovery before retiring a key.
9. Record key lifecycle actions without recording the secret value itself.
10. Treat suspected key disclosure as a security incident.

Encryption protects confidentiality only while the matching key remains secret. Recovery depends on the matching key remaining available.

## Key Generation

Fernet keys used for field-level and backup encryption can be generated with Python and `cryptography`:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Run the command separately for each Fernet key. Do not generate one value and copy it into multiple settings.

The SQLCipher key is a separate secret and must meet CareQueue's configured production requirements. It must not match any field or backup encryption key.

Generated values should be transferred directly into the approved secret-management process. Avoid leaving generated keys in shell history, clipboard history, notes, screenshots, or temporary files longer than necessary.

## Key Inventory and Ownership

Each production deployment should maintain a key inventory outside the application database. The inventory should identify the key by role and lifecycle metadata, but must not contain the raw secret unless the inventory itself is the approved secret store.

Recommended metadata includes:

```text
Key role
Deployment or environment
Created date
Activated date
Custodian or responsible role
Approved recovery location
Last recovery test date
Rotation or retirement date
Incident status, if applicable
```

Do not record patient information or unrelated application data in the key inventory.

## Storage and Access Control

Production keys are normally supplied to CareQueue through the protected environment configuration used by the deployment.

Typical production locations include:

```text
Windows:
C:\ProgramData\CareQueue\Config\carequeue.env

Linux:
/etc/carequeue/carequeue.env
```

The environment file must be restricted to the minimum required operating-system identities. The exact ACL or ownership model depends on the deployment, but the following principles apply:

- Ordinary users should not be able to read the production environment file.
- The CareQueue runtime account must have only the access required to run the application.
- Administrators should review permissions after installation, repair, upgrade, recovery, or service-account changes.
- Keys should not be duplicated into service definitions when the service can load the protected environment file instead.
- Backup copies of keys should not be stored beside the database or encrypted backups they protect.

A host administrator with access to both encrypted data and the matching key may be able to decrypt the data. Host security therefore remains part of the encryption threat model.

## Recovery Copies

A production key that exists only on the CareQueue host creates a single-host recovery dependency.

Organizations should maintain recoverable copies through an approved secret-management process appropriate to their environment. A recovery copy should be:

- Protected from unauthorized disclosure.
- Independent from the CareQueue application host when off-host recovery is required.
- Accessible to designated recovery personnel under documented procedures.
- Included in periodic recovery testing.
- Removed or archived according to policy after the associated encrypted data no longer requires it.

Do not assume that an encrypted backup is recoverable merely because the `.db.enc` file exists. Recovery may require the backup key, SQLCipher key, and field-level encryption key that correspond to the restored data.

## Field-Level Encryption Rotation

CareQueue provides a controlled field-key rotation workflow.

The rotation migrates supported encrypted data from the previous field key to the current field key. It covers:

- Selected encrypted authorization fields.
- Authorization event notes.
- Stored MFA secrets.
- Stored encrypted authorization documents.

The rotation workflow creates and verifies an encrypted pre-rotation database backup before modifying encrypted application data. The data migration runs transactionally, and post-rotation verification confirms that rotated values use the current key before the database transaction completes.

### Prepare the rotation

Before changing the production configuration:

1. Confirm that a current, verified encrypted backup can be created.
2. Confirm that the matching backup key is recoverable.
3. Confirm that the current SQLCipher key is recoverable when SQLCipher is enabled.
4. Confirm that the existing field key is recoverable.
5. Generate a new independent Fernet key for the new field key.
6. Schedule the change during an approved maintenance window.
7. Ensure the operator can review application and security audit results after rotation.

### Configure the rotation window

Before running the rotation:

- Set `AUTHSTATUS_PREVIOUS_ENCRYPTION_KEY` to the field key that is currently in use.
- Set `AUTHSTATUS_ENCRYPTION_KEY` to the newly generated field key.
- Leave the SQLCipher and backup keys unchanged unless a separate approved procedure explicitly requires changing them.

Conceptually:

```env
AUTHSTATUS_PREVIOUS_ENCRYPTION_KEY=<old field key>
AUTHSTATUS_ENCRYPTION_KEY=<new field key>
```

The current and previous field keys must be different. Production validation also prevents the previous field key from matching the backup or SQLCipher key.

### Run the rotation

The repository includes:

```text
backend/scripts/rotate_field_encryption_key.py
```

The script does not modify the configured database unless `--confirm` is supplied.

Example:

```powershell
python backend/scripts/rotate_field_encryption_key.py --confirm --username <operator-username>
```

The optional username is recorded with the security audit event and should identify the authorized operator account without including credentials or secrets.

A successful run reports:

- The verified pre-rotation backup path.
- Rotated authorization-field count.
- Rotated authorization event-note count.
- Rotated MFA-secret count.
- Rotated authorization-document count.

Successful audit recording creates:

```text
security.field_encryption_key_rotated
```

Audit metadata records rotation counts, not encryption key material.

### Verify the rotation

Do not remove `AUTHSTATUS_PREVIOUS_ENCRYPTION_KEY` immediately after the command returns without completing operational verification.

Verify at minimum:

1. The rotation command completed successfully.
2. The pre-rotation encrypted backup exists and was reported as verified.
3. CareQueue starts successfully with the new current field key.
4. Representative encrypted authorization records can be read through the application.
5. Stored authorization event notes remain readable.
6. MFA-backed accounts continue to operate as expected.
7. Stored authorization documents can be opened where applicable.
8. The expected security audit event exists, unless the command explicitly reported an audit-recording failure after a successful rotation.
9. Application health and readiness checks pass.

Use synthetic or approved test records for verification when practical. Do not copy sensitive values into tickets, logs, or validation notes.

### Retire the previous field key

After the rotation has been verified and the organization's recovery procedure confirms that the old key is no longer required for active data:

1. Preserve the verified pre-rotation backup and its required recovery keys for the retention period defined by policy.
2. Remove `AUTHSTATUS_PREVIOUS_ENCRYPTION_KEY` from the active CareQueue configuration.
3. Restart or reload CareQueue according to the deployment procedure so the retired previous key is no longer available to the running process.
4. Verify normal application startup and access to encrypted data.
5. Update the key inventory with the retirement date.

The old field key may still be required to recover historical data or a pre-rotation backup. Do not destroy it solely because active data has been rotated unless retention and recovery requirements have been reviewed.

## Field Rotation Failure Handling

### Backup creation or backup verification fails

If the pre-rotation backup cannot be created or verified, rotation must not proceed.

Actions:

1. Treat the rotation as not started.
2. Correct the backup configuration, storage, permissions, capacity, or key problem.
3. Do not remove or replace the existing field key.
4. Create and verify a new backup before retrying rotation.

### Rotation fails before completion

The rotation transaction is designed to roll back database changes when migration or post-rotation verification fails.

Actions:

1. Treat the rotation as failed.
2. Keep both the old and new field keys available while investigating.
3. Preserve the verified pre-rotation backup.
4. Do not attempt ad hoc ciphertext editing or bulk database updates.
5. Correct the cause and rerun only through the supported rotation workflow.
6. Confirm database health before returning the system to normal operation.

### Rotation succeeds but audit recording fails

CareQueue distinguishes a completed rotation from a failure to append the security audit event. The rotation script reports this condition separately.

If the script reports that field rotation completed successfully but audit recording failed:

1. Treat the encrypted data as already rotated to the new current key.
2. Do not restore the old field key as `AUTHSTATUS_ENCRYPTION_KEY` merely because the audit write failed.
3. Preserve the reported verified pre-rotation backup.
4. Record the operational incident through the organization's approved security or change-management process without including key material.
5. Investigate and restore audit logging before performing additional security-sensitive maintenance.
6. Complete the normal post-rotation verification before retiring the previous key.

## SQLCipher Key Lifecycle

`AUTHSTATUS_SQLCIPHER_KEY` protects the database file itself when CareQueue is configured for SQLCipher.

The SQLCipher key must be available before CareQueue opens the database. Losing the key can make the active database and any SQLCipher database snapshots unreadable even when other CareQueue keys are still available.

### Current rotation limitation

CareQueue does not currently provide an automated in-place SQLCipher key-rotation command equivalent to the field-key rotation workflow.

Do not change `AUTHSTATUS_SQLCIPHER_KEY` on an existing SQLCipher database and assume the database will automatically re-encrypt under the new key. Doing so may prevent CareQueue from opening the database.

SQLCipher key changes must use a separately tested migration/cutover procedure that:

1. Creates and verifies an encrypted CareQueue safety backup.
2. Preserves the existing SQLCipher key until the new database is validated.
3. Produces or rekeys a database using the new SQLCipher key through an approved migration mechanism.
4. Validates database integrity and required CareQueue tables.
5. Performs a deliberate cutover rather than overwriting the only known-good database.
6. Retains rollback material and the previous SQLCipher key until recovery is proven.

The existing plaintext-to-SQLCipher migration scripts are not a general promise of automatic SQLCipher key rotation. A key change should not be performed until the exact deployment-specific migration procedure has been tested.

## Backup Encryption Key Lifecycle

`AUTHSTATUS_BACKUP_ENCRYPTION_KEY` protects `.db.enc` files created by CareQueue.

Changing the configured backup key affects newly created backups. It does not automatically re-encrypt backups that were created with an older key.

Therefore:

- Old backups remain dependent on the backup key that encrypted them.
- Do not delete an old backup key while retained backups still require it.
- The key inventory should make it possible to determine which backup-key generation is required for retained recovery sets.
- Before retiring an old backup key, verify that every backup that still matters is either intentionally expired or recoverable through an approved replacement recovery set.

CareQueue does not currently provide an automated bulk re-encryption workflow for historical `.db.enc` backup files. Do not decrypt and re-encrypt production backups through ad hoc scripts without an approved, tested procedure that preserves integrity, provenance, and rollback capability.

A controlled backup-key change should normally include:

1. Create and verify a final backup using the old backup key if required by policy.
2. Preserve the old key with any retained backups that depend on it.
3. Generate a new independent backup key.
4. Update the protected CareQueue environment configuration.
5. Create a new backup using the new key.
6. Verify that the new backup can be decrypted and validated through the normal CareQueue verification workflow.
7. Update the key inventory to distinguish the old and new backup-key generations.
8. Retire the old key only after its dependent backups have expired or been replaced under an approved recovery plan.

## Suspected Key Disclosure

Treat suspected disclosure of any production encryption key as a security incident.

Immediate actions should include:

1. Preserve relevant logs and audit information without copying the secret into evidence notes.
2. Determine which key role was exposed.
3. Determine what encrypted data or backup files may have been accessible to the same party.
4. Restrict or revoke unauthorized host, administrator, service-account, or secret-store access.
5. Generate replacement keys through the approved process.
6. Perform the appropriate tested rotation or migration procedure.
7. Verify application and recovery behavior after the change.
8. Review whether backups or exported copies encrypted under the exposed key require additional containment.
9. Follow organizational incident-response, legal, contractual, and notification requirements.

Do not assume that rotating a key retroactively protects copies that were already obtained together with the exposed key.

### Field key exposure

Use the supported field-key rotation workflow after containment and recovery preparation. Preserve the previous key only as long as required to complete migration and recover retained data.

### SQLCipher key exposure

Treat the database file as potentially decryptable by anyone who obtained both the database and the key. Use an approved SQLCipher migration/key-change process rather than simply editing the environment value.

### Backup key exposure

Treat retained `.db.enc` files encrypted with that key as potentially decryptable by anyone who obtained both the backup and the key. A new key protects future backups but does not retroactively protect older backup files.

## Key Loss

Key loss is an availability incident.

### Field key loss

Loss of the current field key can make protected fields, MFA secrets, event notes, and stored documents unreadable. Do not generate a replacement key and expect existing ciphertext to become readable.

Recovery requires an approved copy of the matching field key or restoration of a recovery set for which the required keys are available.

### SQLCipher key loss

Loss of the SQLCipher key can make the database file unreadable. A field key or backup key cannot substitute for it.

Recovery requires the matching SQLCipher key for the database being opened, or a separately recoverable database copy whose required keys remain available.

### Backup key loss

Loss of the backup key can make matching `.db.enc` files unrecoverable. Creating a new backup key does not restore access to backups encrypted with the lost key.

If the active database remains healthy, establish a new backup recovery set immediately after configuring a new independent backup key and verifying the resulting backup.

## Recovery Drill

Key recovery should be tested periodically using an approved non-production or isolated recovery procedure.

A drill should demonstrate that designated personnel can retrieve the required secrets and successfully validate a representative recovery set without exposing the secret values in the drill record.

Record results such as:

```text
Drill date
Recovery set identifier
Key roles required
Whether each required key was retrievable
Backup verification result
Restore validation result
Application validation result
Problems found
Corrective actions
Reviewer
```

Do not record the raw encryption keys in the drill report.

A successful drill should verify more than file presence. The restored database should pass CareQueue validation, and representative encrypted application data should remain readable using the corresponding field and SQLCipher keys.

## Deployment and Upgrade Review

Review encryption-key handling whenever any of the following changes:

- CareQueue host or virtual machine.
- Windows service account or Linux service user.
- Environment-file location.
- Filesystem ownership or ACLs.
- Backup destination.
- Recovery destination.
- Secret-management system.
- Database encryption mode.
- Installer or service-wrapper behavior.
- Scheduled backup configuration.
- Disaster-recovery design.

After a deployment or upgrade that changes secret handling:

1. Verify the environment file still has restricted permissions.
2. Verify CareQueue can read only the intended production keys.
3. Verify key values were not copied into logs, command lines, service definitions, or installer output.
4. Create and verify an encrypted backup.
5. Confirm application health and readiness.
6. Review audit and service logs for unexpected secret or encryption errors.

## Key Retirement Checklist

A key should not be considered retired until all applicable conditions are satisfied:

- A replacement key is active where required.
- Migration or rotation completed successfully.
- Post-change application checks passed.
- Recovery was verified with the new key set.
- Retained databases and backups that still require the old key have been identified.
- Retention requirements have been reviewed.
- The old key has been removed from active CareQueue configuration when no longer required there.
- Authorized recovery storage for the old key has been retained or destroyed according to policy.
- The key inventory records the retirement date and disposition.
- No raw key material was written into audit logs or change records.

## Audit and Change Records

Operational records should identify what happened without storing secrets.

Appropriate records may include:

```text
Key role changed
Date and maintenance window
Authorized operator
Reason for rotation
Pre-change backup identifier
Rotation or migration result
Post-change verification result
Recovery test result
Audit event status
Old-key retirement status
```

Never include:

```text
Raw key values
Environment-file contents
Decrypted backup contents
Patient information
MFA secrets
Session tokens
```

## Related Documentation

See also:

```text
SECURITY.md
docs/workflows/backup-and-recovery.md
docs/security/threat-model-and-risk-register.md
docs/deployment/windows.md
docs/deployment/linux.md
docs/operations/upgrades.md
```

The threat model and risk register should be reviewed whenever key lifecycle controls materially change. Documentation reduces operational risk only when deployment permissions, recovery copies, rotation procedures, and recovery drills are actually maintained and tested.

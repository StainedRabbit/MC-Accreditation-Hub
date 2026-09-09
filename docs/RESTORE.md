# Backup and restore procedure

The database and evidence bytes are one recoverable set. A database-only backup cannot restore protected downloads, and an evidence-only copy cannot restore access control or review history.

## Nightly backup

Run the guarded script as the deployment operator after installing the environment file:

```bash
MC_ENV_FILE=/etc/mc-accreditation-hub.env /srv/mc-accreditation/app/deploy/scripts/backup.sh
```

It produces a timestamped archive containing a custom-format PostgreSQL dump, an evidence tarball, the protected deployment environment, a manifest, and SHA-256 checksums. The resulting archive is sensitive because it includes configuration and document bytes: restrict it, encrypt it at rest, and copy it to an approved separate failure domain. The school must approve the retention period, RPO, RTO, and off-host location; this repository does not invent those policies.

## Restore rehearsal (required before production acceptance)

Never restore over production. On an isolated host or database, copy a selected archive and run:

```bash
deploy/scripts/restore-verify.sh /absolute/path/mc-hub-YYYYMMDDTHHMMSSZ.tar.gz /absolute/path/empty-restore
```

The script verifies all checksums, the PostgreSQL archive structure, and the evidence archive without changing a database. Then, under the school DBA’s change control:

1. Create an empty non-production database and an empty private evidence directory.
2. Extract the bundle; run `pg_restore --clean --if-exists --no-owner --dbname=RESTORE_DATABASE database.dump` only against that named non-production database.
3. Extract `evidence.tar.gz` into the new private evidence directory. Set the same restrictive owner/mode as production.
4. Start Django pointed at the restored database and private directory on an isolated hostname.
5. Sign in with a permitted test account, open an approved evidence record, download the exact version, and confirm its review and certification history. Record the archive ID, date, operator, outcomes, and any defects in the release record.

Do not treat checksum/archive verification as a completed recovery rehearsal. As of this repository checkpoint, no school-server restoration has been performed.

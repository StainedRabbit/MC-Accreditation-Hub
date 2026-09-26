# Backup and restore procedure

The database and evidence bytes are one recoverable set. A database-only backup cannot restore protected downloads, and an evidence-only copy cannot restore access control or review history.

## Nightly backup

Run the guarded script as the deployment operator after installing the environment file:

```bash
MC_ENV_FILE=/etc/mc-accreditation-hub.env /srv/mc-accreditation/app/deploy/scripts/backup.sh
```

It takes an atomic run lock and gives each run a timestamp plus random suffix. A concurrent run fails without touching the first run; a stale lock after a hard crash must be reviewed by the operator before removal. The archive is assembled under a private temporary name and becomes visible only after its checksum sidecar has been completed. A failed/interrupted run removes its own unpublished work. The archive contains a custom-format PostgreSQL dump, a schema-only dump, an evidence tarball, the protected deployment environment, a manifest, and SHA-256 checksums. The manifest records the release commit and schema dump hash. Set `MC_RELEASE_COMMIT` to the exact 40-character commit when a deployment has no `.git` directory; otherwise the script reads the checked-out HEAD. The resulting archive is sensitive because it includes configuration and document bytes: restrict it, encrypt it at rest, and copy it to an approved separate failure domain. D19 still leaves the operator, backup role/platform, destination, encryption/key custody, retention, RPO/RTO, alerts, and rehearsal schedule to School IT.

New format-2 archives hash exactly four payload-relative files: `database.dump`, `schema.sql`, `evidence.tar.gz`, and `environment.env`. The verifier checks the extracted payload, the manifest's schema hash, the outer `.sha256` sidecar, and evidence archive member safety. The sidecar uses only the archive basename, so both files remain portable when copied away from the source host. Older format-1 archives retain their three-file verification path. Checksums detect corruption; they do not authenticate an archive whose contents and hashes an attacker can both replace. Obtain bundles through the school-approved trusted transfer/protection process.

## Restore rehearsal (required before production acceptance)

Never restore over production. On an isolated host or database, copy a selected archive and run:

```bash
deploy/scripts/restore-verify.sh /absolute/path/mc-hub-YYYYMMDDTHHMMSSZ-RANDOM.tar.gz /absolute/path/empty-restore
```

Copy both the archive and its `.sha256` sidecar. Use an absolute destination path that does **not yet exist**, beneath an existing private directory controlled by the restore operator. The verifier requires Bash, Python 3.13+ available as `python3`, and PostgreSQL's `pg_restore`. It validates the expected single payload directory and exact regular-file set before extraction; links, special entries, unexpected/duplicate paths, and missing files are rejected. It accepts one checksum per required relative filename, rejecting absolute paths, traversal, malformed or incomplete manifests. It hashes the extracted files, never source-host paths, and does not source `environment.env`. Format-2 verification also rejects missing/mismatched sidecars, invalid release/schema manifest fields, and unsafe evidence archive members.

On success, the verified payload remains beneath the destination for the DBA. On failure, the newly created destination is removed; pre-existing destinations are refused and left untouched. Legacy bundles with absolute checksum entries are deliberately rejected. Generate a new backup with the corrected script; do not strip prefixes or edit hashes to claim verification. If a legacy bundle is the only recovery source, school IT must handle it through a separately controlled recovery process.

The script checks the PostgreSQL dump with `pg_restore --list` and lists the evidence tarball without changing a database or extracting evidence into live storage. Then, under the school DBA’s change control:

1. Create an empty non-production database and an empty private evidence directory.
2. Use the verified extracted payload directory; run `pg_restore --clean --if-exists --no-owner --dbname=RESTORE_DATABASE database.dump` only against that named non-production database.
3. Extract `evidence.tar.gz` into the new private evidence directory. Set the same restrictive owner/mode as production.
4. Start Django pointed at the restored database and private directory on an isolated hostname.
5. Sign in with a permitted test account, open an approved evidence record, download the exact version, and confirm its review and certification history. Record the archive ID, date, operator, outcomes, and any defects in the release record.

Do not treat checksum/archive verification as a completed recovery rehearsal. As of this repository checkpoint, no school-server restoration has been performed.

## Read-only storage reconciliation

With the application pointed at the intended database and `PRIVATE_MEDIA_ROOT`, run `python backend/manage.py reconcile_storage`. It emits JSON lists/counts of version keys whose files are missing, whose size or SHA-256 differs, and disk entries with no version row. It makes no database or filesystem changes. Review every orphan before any separate, approved quarantine or retention action; never automatically delete referenced evidence or history. Run it before a backup and after an isolated restore, recording counts and investigation outcomes without exposing evidence bytes.

## Local synthetic database-and-evidence rehearsal

On 2026-09-26, `python -B deploy/tests/rehearse_synthetic_windows.py` completed on this Windows workspace using the ignored PostgreSQL 18 cluster bound to `127.0.0.1:55432`, Git Bash, and local trust authentication. The harness created two randomly named temporary synthetic databases, inserted a fictional history row, wrote one fictional evidence file, ran the real `backup.sh` and `restore-verify.sh`, restored the dump into the second database with `pg_restore`, read the restored row and evidence bytes, and compared the bytes/checksum. It reported success and removed the temporary databases, archive, sidecar, evidence and environment fixture in `finally`/temporary-directory cleanup. No production data, service, credential, or school host was used. This proves a local synthetic round trip only; School IT must still rehearse an approved version download with its review/certification history on the approved target environment and measure RPO/RTO.

## Isolated tooling regression verification

From the repository root, without deployment configuration or running services:

```bash
python3 -B -m unittest discover -s deploy/tests -v
```

These tests generate synthetic temporary files and stub `pg_dump`, `pg_restore`, deployment Python, npm, and HTTP calls. They copy a generated bundle/sidecar to another directory, delete the source backup directory, and verify the copied payload; check tampering of the legacy hashed files; reject unsafe/duplicate/missing/malformed checksum entries and unsafe archive layouts/links; check format-2 schema/sidecar/evidence validation, overlapping runs and interrupted dump cleanup; preserve existing destinations; and exercise direct invocation, release-gate failures, and Bash syntax. Git modes are checked for `100755` and shell files for LF. Temporary test data is automatically removed.

On 2026-09-26, the Windows/Python 3.13 tooling suite passed **19 tests** with `BACKUP_TEST_BASH` set to Git Bash. Those tests use stubs and temporary synthetic payloads; the separate real PostgreSQL local rehearsal above supplies the dump/restore check. Neither test represents a different-host or School IT target restore. A fresh Linux checkout must run the tooling suite and target release checklist, including operator permissions and approved-version download/history checks. Measured RPO/RTO and School IT acceptance remain outstanding.

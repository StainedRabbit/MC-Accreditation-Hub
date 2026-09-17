# Backup and restore procedure

The database and evidence bytes are one recoverable set. A database-only backup cannot restore protected downloads, and an evidence-only copy cannot restore access control or review history.

## Nightly backup

Run the guarded script as the deployment operator after installing the environment file:

```bash
MC_ENV_FILE=/etc/mc-accreditation-hub.env /srv/mc-accreditation/app/deploy/scripts/backup.sh
```

It produces a timestamped archive containing a custom-format PostgreSQL dump, an evidence tarball, the protected deployment environment, a manifest, and SHA-256 checksums. The resulting archive is sensitive because it includes configuration and document bytes: restrict it, encrypt it at rest, and copy it to an approved separate failure domain. The school must approve the retention period, RPO, RTO, and off-host location; this repository does not invent those policies.

The internal `SHA256SUMS` contains exactly three payload-relative filenames: `database.dump`, `evidence.tar.gz`, and `environment.env`. The archive's `.sha256` sidecar also uses only the archive basename, so both files remain portable when copied away from the source host. Checksums detect corruption; they do not authenticate an archive whose contents and hashes an attacker can both replace. Obtain bundles through the school-approved trusted transfer/protection process.

## Restore rehearsal (required before production acceptance)

Never restore over production. On an isolated host or database, copy a selected archive and run:

```bash
deploy/scripts/restore-verify.sh /absolute/path/mc-hub-YYYYMMDDTHHMMSSZ.tar.gz /absolute/path/empty-restore
```

Use an absolute destination path that does **not yet exist**, beneath an existing private directory controlled by the restore operator. The verifier requires Bash, Python 3.13+ available as `python3`, and PostgreSQL's `pg_restore`. It validates the expected single payload directory and five regular files before extraction; links, special entries, unexpected/duplicate paths, and missing files are rejected. It accepts only one checksum per required relative filename, rejecting absolute paths, traversal, malformed or incomplete manifests. It hashes the extracted files, never source-host paths, and does not source `environment.env`.

On success, the verified payload remains beneath the destination for the DBA. On failure, the newly created destination is removed; pre-existing destinations are refused and left untouched. Legacy bundles with absolute checksum entries are deliberately rejected. Generate a new backup with the corrected script; do not strip prefixes or edit hashes to claim verification. If a legacy bundle is the only recovery source, school IT must handle it through a separately controlled recovery process.

The script checks the PostgreSQL dump with `pg_restore --list` and lists the evidence tarball without changing a database or extracting evidence into live storage. Then, under the school DBA’s change control:

1. Create an empty non-production database and an empty private evidence directory.
2. Use the verified extracted payload directory; run `pg_restore --clean --if-exists --no-owner --dbname=RESTORE_DATABASE database.dump` only against that named non-production database.
3. Extract `evidence.tar.gz` into the new private evidence directory. Set the same restrictive owner/mode as production.
4. Start Django pointed at the restored database and private directory on an isolated hostname.
5. Sign in with a permitted test account, open an approved evidence record, download the exact version, and confirm its review and certification history. Record the archive ID, date, operator, outcomes, and any defects in the release record.

Do not treat checksum/archive verification as a completed recovery rehearsal. As of this repository checkpoint, no school-server restoration has been performed.

## Isolated tooling regression verification

From the repository root, without deployment configuration or running services:

```bash
python3 -B -m unittest discover -s deploy/tests -v
```

These tests generate synthetic temporary files and stub `pg_dump`, `pg_restore`, deployment Python, npm, and HTTP calls. They copy a generated bundle/sidecar to another directory, delete the source backup directory, and verify the copied payload; check tampering of all three hashed files; reject unsafe/duplicate/missing/malformed checksum entries and unsafe archive layouts/links; preserve existing destinations; check failure cleanup; and exercise direct invocation and Bash syntax for all three shell scripts. Git modes are checked for `100755` and shell files for LF. Temporary test data is automatically removed.

On 2026-09-17, `python -B -m unittest discover -s deploy/tests -v` passed **13 tests** on Windows/Python 3.13 with `BACKUP_TEST_BASH` set to Git Bash 5.2.37. This is a same-machine relocation test, not a different-host restore. PostgreSQL format probes were stubbed; no real dump/restore, production data/service, real secrets, or school infrastructure was used. Linux-only ownership/mode assertions await a Linux run. A fresh Linux checkout must run the command above and the target release checklist. The actual isolated database/evidence recovery rehearsal, approved-version download/history checks, and measured RPO/RTO remain mandatory and outstanding.

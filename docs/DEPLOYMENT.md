# Production deployment reference

This is a reference for a school-owned Linux host using Nginx, systemd, PostgreSQL, and a private evidence directory. It is not a claim that the school server has been provisioned or that it satisfies a particular private-cloud classification.

## Preconditions to confirm with school IT

- Approved hostname, DNS, TLS certificate ownership, firewall rules, and an IT service owner.
- Ubuntu/Debian-like host with Python 3.13+, Node 22.12+, PostgreSQL 17+, Nginx, and a restricted service account named `mc-hub`.
- A PostgreSQL application role with access only to the application database, and a separately controlled backup role.
- A private evidence mount with capacity, access controls, backup destination, retention, RPO/RTO, and an off-host failure domain approved by the school.
- D11 scanner approval and D12 [records schedule](RECORDS_SCHEDULE_INPUT.md) before accepting real institutional evidence. Keep synthetic-only until both are approved and verified. File-format validation is not malware scanning.

## Install layout

## Restricted on-premises test deployment (provisional D18)

Use this path only for synthetic test data and authorized school users. It is a preparation template, not a deployment to a school host or a production configuration. School IT must supply the internal test hostname, bind address, TLS certificate, client network CIDRs, sole Nginx peer address as seen by Gunicorn, management CIDRs, and an isolated PostgreSQL database. Do not publish DNS or firewall access to the public internet.

1. Start from [the test environment template](../deploy/env/mc-accreditation-hub.test.env.example) outside Git. Supply a unique test secret and isolated database credentials through the school's secret-management process. Keep `DJANGO_DEBUG=0`, set an explicit internal `DJANGO_ALLOWED_HOSTS` value and HTTPS `CSRF_TRUSTED_ORIGINS`, and leave `PASSWORD_RESET_ENABLED=0` unless separate test SMTP is deliberately configured and verified. Missing proxy trust denies all requests; missing management CIDRs keep admin inaccessible. A `/0` proxy or management allowlist is rejected.
2. Use [the test Nginx template](../deploy/nginx/mc-accreditation-hub-test.conf). Replace its internal bind address, hostname, and certificate placeholders. Create `/etc/nginx/mc-hub-test-client-allow.conf` with explicit `allow <approved-internal-CIDR>;` entries followed by `deny all;`. The absent include file or unreplaced placeholders prevent Nginx startup. Nginx replaces incoming forwarding headers with one client address; Django trusts only the configured proxy peer. Confirm any local firewall also limits the bound Nginx port to the internal test network.
3. Keep Gunicorn bound to `127.0.0.1:8001`, PostgreSQL private, and `PRIVATE_MEDIA_ROOT` outside the web root. Apply migrations, build the frontend, run `python backend/manage.py check --deploy`, and validate the filled Nginx file with `nginx -t` before starting services. Create only least-privilege test accounts and fictional requirements/evidence. Keep a recoverable backup copy outside the test host under school-approved access controls; do not use production backup material.
4. Assign the separate D15 permissions only through a School IT controlled change record; use the [launch administration runbook](LAUNCH_ADMINISTRATION.md) for reasoned user changes, grant commands, initial cycle provisioning, and credential recovery. Correlate CLI actor IDs with the target shell/operator log. From an approved test client, verify HTTPS, login, logout, CSRF and secure cookies, synthetic evidence access, and rate-limit responses. From a management source in `TEST_ADMIN_NETWORKS`, verify `/api/admin/login/` is reachable; from another internal source, verify it is unavailable. Send a forged forwarding header through Nginx and confirm Nginx replaces it; direct Gunicorn traffic and an unconfigured management list must be denied. Check that all Gunicorn workers share the PostgreSQL-backed throttle table and that logs contain no credentials or reset tokens. Record the real source addresses and results for School IT review without recording secrets.

The app limits login, recovery request/confirmation, and admin login using a single configurable per-minute count per client IP and route. PostgreSQL stores the counters across workers; no paid service is required. The repository's tests exercise this shared table through separate clients, while actual worker and Nginx behavior must be checked on the test host. School IT must confirm the proxy chain, internal exposure, permitted management networks, appropriate limits for shared school-network clients, TLS ownership, and any future production design. The general deployment reference below is not an approval of these values.

Use these paths consistently with the reference service and Nginx files:

```text
/srv/mc-accreditation/app              checked-out release
/srv/mc-accreditation/venv             Python virtual environment
/srv/mc-accreditation/private-media    protected document bytes (not web-served)
/srv/mc-accreditation/backups          local staging only; replicate off-host
/etc/mc-accreditation-hub.env          root-owned application environment
```

Do not put a real `.env` in Git, and do not serve `private-media` with Nginx. Copy [the deployment environment template](../deploy/env/mc-accreditation-hub.env.example) to `/etc/mc-accreditation-hub.env`, fill it through the school’s secret-management process, then set owner `root:mc-hub` and mode `0640`.

## Release procedure

1. Fetch the approved commit into `/srv/mc-accreditation/app`; record its commit ID in the change ticket.
2. Create/update the virtual environment and install `backend/requirements.txt`. Gunicorn is pinned in that file as the production WSGI server.
3. Set `DJANGO_DEBUG=0`, real `DJANGO_ALLOWED_HOSTS`, HTTPS `CSRF_TRUSTED_ORIGINS`, a unique secret, and a private absolute `PRIVATE_MEDIA_ROOT` in `/etc/mc-accreditation-hub.env`.
4. Run `python backend/manage.py migrate`, `python backend/manage.py collectstatic --noinput`, and `npm ci --prefix frontend && npm run build --prefix frontend` as the service/deployment operator.
5. Install [the systemd unit](../deploy/systemd/mc-accreditation-hub.service) and [Nginx configuration](../deploy/nginx/mc-accreditation-hub.conf), replacing the example hostname and certificate paths. Validate Nginx configuration before reload.
6. Start the service, then run `MC_ENV_FILE=/etc/mc-accreditation-hub.env deploy/scripts/release-check.sh /srv/mc-accreditation/app`. The gate checks all Django deployment errors/warnings and the database's applied migration graph before npm build and health probing. It fails on any warning unless its exact ID is named in `MC_ACCEPTED_DEPLOY_WARNINGS` with a recorded `MC_ACCEPTED_DEPLOY_WARNINGS_REASON`; accepted advisories remain visible in output. Do not place a blanket list in the environment template or treat a local synthetic acceptance reason as School IT approval. An unapplied migration or inaccessible database always fails.
7. Complete [the release checklist](RELEASE_CHECKLIST.md), including a controlled login, restricted download check, and backup verification, before admitting pilot users.

The environment enables HTTPS redirect and one-day HSTS only after a working HTTPS deployment is confirmed. Do not enable a longer HSTS duration or preload until the hostname and subdomain policy have formal approval.

The three `deploy/scripts/*.sh` entry points are tracked with executable Git mode `100755` and pinned LF line endings. Their documented direct invocations need no manual `chmod` after a normal Linux checkout. Keep `verify-backup-payload.py` alongside `restore-verify.sh`; the verifier invokes it through `python3` (Python 3.13+), not as an executable.

Before installing a fresh Linux checkout, run `python3 -B -m unittest discover -s deploy/tests -v` from its root. This runs synthetic/stubbed tooling tests only, not a backup of the deployment or the real release checker against services. The local Windows/Git Bash tooling suite and a separate real synthetic PostgreSQL round trip are recorded in [the recovery test scope](RESTORE.md#isolated-tooling-regression-verification). Linux filesystem permissions, installed operator access, PostgreSQL probes, Nginx/systemd, and the full release/recovery checklist still require school IT verification.

Configure `EVIDENCE_SCANNER_COMMAND` as a JSON argument array with exactly one `{file}` argument and `EVIDENCE_SCANNER_ID` only after School IT approves a local scanner. Exit code 0 releases exact matching bytes, 1 records an infected verdict, and any other exit, timeout, missing file, or checksum mismatch keeps the version quarantined. Unconfigured scanning leaves uploads pending. The upload request scans synchronously; use `python backend/manage.py scan_evidence` to retry pending/error versions and `--version-id ID` for a deliberate rescan. Do not use a public scanning service for institutional files. After migration, all historical versions are quarantined until scanned. Record target-environment scanner tests and operator ownership in the workshop tracker.

Before a scheduled backup, School IT must choose the D19 operator/platform, distinct backup role, protected destination and separate failure-domain copy, encryption/key custody, retention, RPO/RTO, alert owner, and rehearsal frequency. The repository's `backup.sh` serializes runs with a lock, stages unique archives privately and atomically publishes only completed archive files; it does not schedule, encrypt, replicate, or alert by itself. Point `MC_ENV_FILE` at a restricted backup-specific environment when IT provides a least-privilege role. Verify a copied bundle with `restore-verify.sh`, and run the read-only `python backend/manage.py reconcile_storage` against the intended database and evidence directory. Investigate missing/mismatched/orphaned files; the command never deletes them. Do not use the general Nginx/systemd examples as proof of target permissions, network boundaries, monitoring, or recovery.

## Operations

- Nginx serves the built React application and collected static files; it proxies only `/api/` to Gunicorn at `127.0.0.1:8001`.
- `/api/health/` is an unauthenticated readiness probe that performs `SELECT 1` and returns only `{"status":"ok"}` or a 503 status. It exposes no user, cycle, or evidence data.
- Use `journalctl -u mc-accreditation-hub` and the Nginx error log for incident investigation. Do not place credentials, evidence content, reset links, or request bodies in ticket comments or logs. The reference Nginx access-log format records `$uri` without query strings; keep request-body logging disabled, and review all school-managed proxy/application log formats before enabling recovery. New reset links use fragments, which browsers do not send in HTTP requests.
- Password reset remains disabled until School IT confirms authenticated encrypted SMTP delivery, the public HTTPS URL, and deployed log handling. Administrator-assisted recovery is the current pilot path; see the [account recovery procedure](../README.md#account-recovery). No delivery or production acceptance is claimed by the local tests.

See [backup and restore](RESTORE.md) for the paired data-recovery procedure.

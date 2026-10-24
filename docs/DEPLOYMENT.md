# Production deployment reference

This is a reference for a school-owned Linux host using Nginx, systemd, PostgreSQL, and a private evidence directory. It is not a claim that the school server has been provisioned or that it satisfies a particular private-cloud classification.

## GitHub Pages, Railway, Supabase PostgreSQL, and Cloudflare R2

The root `Dockerfile` and `railway.json` define the Django service for Railway. `.github/workflows/pages.yml` builds only the React frontend and deploys `frontend/dist` to GitHub Pages. The default Pages preview uses `/MC-Accreditation-Hub/`; set the non-secret Actions variable `VITE_BASE_PATH=/` when Pages is attached to a custom domain. Set `VITE_API_BASE_URL` to the Railway API origin. These frontend values are public configuration and must contain no credentials.

The repository's GitHub Pages setting must use **Settings → Pages → Build and deployment → Source → GitHub Actions**. Stage at `https://stainedrabbit.github.io/MC-Accreditation-Hub/` first. The Pages artifact and login are separate checks: the default `github.io` preview and a Railway hostname are cross-site, so browser privacy settings may block the Django session cookie. Use sibling HTTPS frontend/API hosts on the same school-owned registrable domain for the production login. Add a new, nonconflicting hostname only after the Pages artifact is verified; keep any current Cloudflare Worker routes and DNS records in place until the new login and upload flow passes.

Set the Railway variables from [the Railway environment template](../deploy/env/railway.env.example). Use the existing Supabase project's Session pooler host, port, database, username and password, with `PGSSLMODE=require`; Railway's default outbound network is IPv4, while a Supabase direct endpoint may require IPv6. `DJANGO_ALLOWED_HOSTS` must include the API hostname, and `CSRF_TRUSTED_ORIGINS` and `CORS_ALLOWED_ORIGINS` must list the exact frontend origin. Keep `DJANGO_DEBUG=0`, `DJANGO_TRUST_PROXY_SSL=1`, and secure cookies enabled. Add the Railway custom domain and verify `/api/health/` before a production frontend cutover.

The Railway image does not run migrations during build or startup. Before applying schema changes to the existing Supabase database, take the approved backup, inspect `python backend/manage.py showmigrations` and `python backend/manage.py migrate --plan`, then run `python backend/manage.py migrate` only after confirming the pending operations. This release adds one table for short-lived upload intents; it does not create a database or drop/alter existing application data. No migration has been applied to the user's Supabase project from this workspace.

Put `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, and `R2_BUCKET_NAME` in Railway variables using credentials scoped to the existing private bucket. The browser receives only a five-minute URL for `pending/<uuid>`; Django verifies the uploaded bytes and moves them to `evidence/<uuid>`. Configure an R2 lifecycle rule to delete abandoned objects under `pending/` after two days. Merge [the CORS example](../deploy/cloudflare/r2-cors.example.json) into the bucket's current CORS policy with the exact deployed frontend origin; allow `PUT`, `Content-Type`, and `x-amz-meta-sha256`, and expose `ETag`. Keep the bucket private. Django previews are framed only by the same origin and the configured CORS frontend origins.

Legacy local evidence remains readable if the matching R2 object is absent. To copy existing local evidence to R2 without deleting source files, configure the R2 variables and run `python backend/manage.py copy_evidence_to_r2` from the host that has both the existing database and `PRIVATE_MEDIA_ROOT`. `python backend/manage.py reconcile_storage` checks local and R2 evidence in the app-owned `evidence/` prefix without deleting objects. When R2 is configured, backups must set `MC_PYTHON` to the Django virtualenv Python; `backup.sh` then exports and verifies referenced R2 bytes into the evidence archive.

Deployment remains blocked until the exact custom frontend/API hostnames, Railway service URL, Supabase connection values, R2 bucket credentials, GitHub Actions variable, Pages source setting, and R2 CORS rule are available. No DNS or existing Worker route change is part of staging.

## Preconditions to confirm with school IT

- Approved hostname, DNS, TLS certificate ownership, firewall rules, and an IT service owner.
- Ubuntu/Debian-like host with Python 3.13+, Node 22.12+, PostgreSQL 17+, Nginx, and a restricted service account named `mc-hub`.
- A PostgreSQL application role with access only to the application database, and a separately controlled backup role.
- A private evidence mount with capacity, access controls, backup destination, retention, RPO/RTO, and an off-host failure domain approved by the school.
- D11 malware-handling policy and D12 [records schedule](RECORDS_SCHEDULE_INPUT.md) before accepting real institutional evidence. Keep synthetic-only until both are approved and verified. **This application currently does not malware-scan uploads; authorized versions are usable after format validation.** File-format validation and checksum integrity checks do not detect malware.

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

Scanning is currently disabled: uploads do not invoke a scanner, scan status is not exposed by the API, and the manual scan command is unavailable. Existing scan history remains stored but does not affect file access or evidence workflows. Do not describe uploads as malware-free. Before real institutional evidence is accepted, record the approved D11 malware-handling policy and any compensating controls in the workshop tracker.

Before a scheduled backup, School IT must choose the D19 operator/platform, distinct backup role, protected destination and separate failure-domain copy, encryption/key custody, retention, RPO/RTO, alert owner, and rehearsal frequency. The repository's `backup.sh` serializes runs with a lock, stages unique archives privately and atomically publishes only completed archive files; it does not schedule, encrypt, replicate, or alert by itself. Point `MC_ENV_FILE` at a restricted backup-specific environment when IT provides a least-privilege role. Verify a copied bundle with `restore-verify.sh`, and run the read-only `python backend/manage.py reconcile_storage` against the intended database and evidence directory. Investigate missing/mismatched/orphaned files; the command never deletes them. Do not use the general Nginx/systemd examples as proof of target permissions, network boundaries, monitoring, or recovery.

## Operations

- Nginx serves the built React application and collected static files; it proxies only `/api/` to Gunicorn at `127.0.0.1:8001`.
- `/api/health/` is an unauthenticated readiness probe that performs `SELECT 1` and returns only `{"status":"ok"}` or a 503 status. It exposes no user, cycle, or evidence data.
- Use `journalctl -u mc-accreditation-hub` and the Nginx error log for incident investigation. Do not place credentials, evidence content, reset links, or request bodies in ticket comments or logs. The reference Nginx access-log format records `$uri` without query strings; keep request-body logging disabled, and review all school-managed proxy/application log formats before enabling recovery. New reset links use fragments, which browsers do not send in HTTP requests.
- Password reset remains disabled until School IT confirms authenticated encrypted SMTP delivery, the public HTTPS URL, and deployed log handling. Administrator-assisted recovery is the current pilot path; see the [account recovery procedure](../README.md#account-recovery). No delivery or production acceptance is claimed by the local tests.

See [backup and restore](RESTORE.md) for the paired data-recovery procedure.

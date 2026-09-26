# Release verification checklist

Record the date, release commit, environment, operator, and result for every item. Stop and remediate a failed item before pilot use.

The F25 local synthetic tests use real Django cookie sessions and CSRF requests to verify password-change continuity, inactive-account denial, and immediate evidence-access loss after grant revocation. A backend test injects a database cursor failure and verifies `/api/health/` returns 503 without details. The separate `python -B scripts/run_isolated_browser.py` runner uses a disposable fictional database and loopback services to exercise the browser flows and healthy probe; it does not simulate a database outage. None of these local results checks a School IT target item below. Repeat session, access, and health checks through the approved HTTPS proxy on the target environment before acceptance.

- [ ] School IT approved hostname, TLS certificate, firewall, service account, database role, private evidence mount, backup target, retention, RPO/RTO, and incident owner.
- [ ] `DJANGO_DEBUG=0`; secret and database password are outside Git; allowed hosts and CSRF origins are the final HTTPS hostname.
- [ ] `deploy/scripts/release-check.sh` passed: no unapplied migrations, no deployment errors, and every deployment warning either resolved or explicitly accepted by ID with an approved reason. Attach the gate output; a printed migration plan alone is insufficient.
- [ ] Migrations and `collectstatic` completed; `npm ci` and `npm run build` produced the release frontend assets.
- [ ] A fresh Linux checkout passed `python3 -B -m unittest discover -s deploy/tests -v`; executable script modes, LF, and installed operator access match the documented commands. Local Windows/Git Bash results do not complete this target check.
- [ ] Nginx validates and serves HTTPS; HTTP redirects to HTTPS; `/api/health/` returns `{"status":"ok"}`.
- [ ] Login, refresh, logout, a scoped list, and a denied cross-scope URL behave as expected.
- [ ] An authorized protected evidence download succeeds as an attachment; a guessed unauthorized download URL fails; Nginx has no `private-media` alias.
- [ ] A closed cycle rejects ordinary writes; authorized reopen and its audit event are recorded.
- [ ] The named backup operator/platform, separate backup role, destination and failure-domain copy, encryption/key recovery, retention, RPO/RTO, alerts/incident owner and rehearsal frequency were approved under D19.
- [ ] A uniquely named backup completed without lock or partial-archive leftovers; its release commit and schema hash match the intended release, its copied sidecar and extracted payload verified, and protected off-host replication was confirmed.
- [ ] Read-only `reconcile_storage` results for the intended database/evidence directory were recorded; every missing, mismatched and orphaned object was investigated without automatic deletion.
- [ ] A separate-environment restoration rehearsal proved an approved evidence download and its history. Attach the recorded evidence; do not mark this complete from archive verification alone.
- [ ] Recovery email is either tested with school SMTP or remains disabled with administrator-assisted recovery documented.
- [ ] Known limitations and the evaluation protocol were given to pilot participants.

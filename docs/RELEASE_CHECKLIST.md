# Release verification checklist

Record the date, release commit, environment, operator, and result for every item. Stop and remediate a failed item before pilot use.

- [ ] School IT approved hostname, TLS certificate, firewall, service account, database role, private evidence mount, backup target, retention, RPO/RTO, and incident owner.
- [ ] `DJANGO_DEBUG=0`; secret and database password are outside Git; allowed hosts and CSRF origins are the final HTTPS hostname.
- [ ] `python backend/manage.py check --deploy` reports no deployment warnings that remain unaddressed.
- [ ] Migrations and `collectstatic` completed; `npm ci` and `npm run build` produced the release frontend assets.
- [ ] Nginx validates and serves HTTPS; HTTP redirects to HTTPS; `/api/health/` returns `{"status":"ok"}`.
- [ ] Login, refresh, logout, a scoped list, and a denied cross-scope URL behave as expected.
- [ ] An authorized protected evidence download succeeds as an attachment; a guessed unauthorized download URL fails; Nginx has no `private-media` alias.
- [ ] A closed cycle rejects ordinary writes; authorized reopen and its audit event are recorded.
- [ ] A backup archive completed, checksums passed, and its off-host replication was confirmed.
- [ ] A separate-environment restoration rehearsal proved an approved evidence download and its history. Attach the recorded evidence; do not mark this complete from archive verification alone.
- [ ] Recovery email is either tested with school SMTP or remains disabled with administrator-assisted recovery documented.
- [ ] Known limitations and the evaluation protocol were given to pilot participants.

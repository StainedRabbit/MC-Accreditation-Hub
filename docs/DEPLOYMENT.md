# Production deployment reference

This is a reference for a school-owned Linux host using Nginx, systemd, PostgreSQL, and a private evidence directory. It is not a claim that the school server has been provisioned or that it satisfies a particular private-cloud classification.

## Preconditions to confirm with school IT

- Approved hostname, DNS, TLS certificate ownership, firewall rules, and an IT service owner.
- Ubuntu/Debian-like host with Python 3.13+, Node 22.12+, PostgreSQL 17+, Nginx, and a restricted service account named `mc-hub`.
- A PostgreSQL application role with access only to the application database, and a separately controlled backup role.
- A private evidence mount with capacity, access controls, backup destination, retention, RPO/RTO, and an off-host failure domain approved by the school.
- Malware scanning/quarantine policy before accepting real institutional evidence. File-format validation in this application is not malware scanning.

## Install layout

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
6. Start the service, then run `MC_ENV_FILE=/etc/mc-accreditation-hub.env deploy/scripts/release-check.sh /srv/mc-accreditation/app`.
7. Complete [the release checklist](RELEASE_CHECKLIST.md), including a controlled login, restricted download check, and backup verification, before admitting pilot users.

The environment enables HTTPS redirect and one-day HSTS only after a working HTTPS deployment is confirmed. Do not enable a longer HSTS duration or preload until the hostname and subdomain policy have formal approval.

## Operations

- Nginx serves the built React application and collected static files; it proxies only `/api/` to Gunicorn at `127.0.0.1:8001`.
- `/api/health/` is an unauthenticated readiness probe that performs `SELECT 1` and returns only `{"status":"ok"}` or a 503 status. It exposes no user, cycle, or evidence data.
- Use `journalctl -u mc-accreditation-hub` and the Nginx error log for incident investigation. Do not place credentials, evidence content, or reset tokens in ticket comments or logs.
- Password reset remains disabled until school SMTP and the public HTTPS URL are configured and tested.

See [backup and restore](RESTORE.md) for the paired data-recovery procedure.

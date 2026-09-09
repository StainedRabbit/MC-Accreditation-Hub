#!/usr/bin/env bash
set -euo pipefail

app_root="${1:-/srv/mc-accreditation/app}"
venv="${VIRTUAL_ENV:-/srv/mc-accreditation/venv}"
: "${MC_ENV_FILE:=/etc/mc-accreditation-hub.env}"
test -r "$MC_ENV_FILE" || { echo "Cannot read MC_ENV_FILE." >&2; exit 1; }
set -a; source "$MC_ENV_FILE"; set +a
cd "$app_root"
"$venv/bin/python" backend/manage.py check --deploy
"$venv/bin/python" backend/manage.py migrate --plan
(cd frontend && npm ci && npm run build)
curl --fail --silent --show-error https://"${DJANGO_ALLOWED_HOSTS%%,*}"/api/health/ | grep -q '"status":"ok"'
echo "Release checks passed. Run the manual release checklist before enabling users."

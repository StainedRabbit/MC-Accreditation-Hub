#!/usr/bin/env bash
set -euo pipefail
umask 077

: "${MC_ENV_FILE:=/etc/mc-accreditation-hub.env}"
test -r "$MC_ENV_FILE" || { echo "Cannot read MC_ENV_FILE." >&2; exit 1; }
set -a; source "$MC_ENV_FILE"; set +a
: "${BACKUP_ROOT:?BACKUP_ROOT is required}"
: "${PRIVATE_MEDIA_ROOT:?PRIVATE_MEDIA_ROOT is required}"
: "${PGDATABASE:?PGDATABASE is required}"
test -d "$PRIVATE_MEDIA_ROOT" || { echo "PRIVATE_MEDIA_ROOT is not a directory." >&2; exit 1; }

mkdir -p "$BACKUP_ROOT"
run_id="mc-hub-$(date -u +%Y%m%dT%H%M%SZ)"
work_dir="$BACKUP_ROOT/.${run_id}.working"
bundle="$BACKUP_ROOT/${run_id}.tar.gz"
trap 'rm -rf "$work_dir"' EXIT
mkdir "$work_dir"

pg_dump --format=custom --no-owner --no-acl --file="$work_dir/database.dump" "$PGDATABASE"
tar -C "$PRIVATE_MEDIA_ROOT" -czf "$work_dir/evidence.tar.gz" .
cp "$MC_ENV_FILE" "$work_dir/environment.env"
chmod 600 "$work_dir/environment.env"
sha256sum "$work_dir/database.dump" "$work_dir/evidence.tar.gz" "$work_dir/environment.env" > "$work_dir/SHA256SUMS"
printf 'created_utc=%s\nsource_database=%s\n' "$(date -u +%FT%TZ)" "$PGDATABASE" > "$work_dir/manifest.txt"
tar -C "$BACKUP_ROOT" -czf "$bundle" ".${run_id}.working"
sha256sum "$bundle" > "${bundle}.sha256"
echo "Backup written: $bundle"

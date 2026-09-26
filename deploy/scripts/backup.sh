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

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
app_root="${MC_APP_ROOT:-$(cd -- "$script_dir/../.." && pwd -P)}"
release_commit="${MC_RELEASE_COMMIT:-$(git -C "$app_root" rev-parse --verify HEAD 2>/dev/null || true)}"
[[ "$release_commit" =~ ^[0-9a-f]{40}$ ]] || { echo "A 40-character release commit is required." >&2; exit 1; }

mkdir -p -- "$BACKUP_ROOT"
backup_root="$(cd -- "$BACKUP_ROOT" && pwd -P)"
lock_dir="$backup_root/.backup.lock"
mkdir -- "$lock_dir" 2>/dev/null || { echo "Another backup is running or its lock needs operator review." >&2; exit 1; }
work_dir=""
partial_bundle=""
partial_sidecar=""
final_sidecar=""
final_bundle=""
published=0
cleanup() {
    if [[ -n "$work_dir" && "$work_dir" == "$backup_root"/.mc-hub-* ]]; then rm -rf -- "$work_dir"; fi
    if [[ -n "$partial_bundle" ]]; then rm -f -- "$partial_bundle"; fi
    if [[ -n "$partial_sidecar" ]]; then rm -f -- "$partial_sidecar"; fi
    if [[ "$published" == 0 && -n "$final_sidecar" && ( -z "$final_bundle" || ! -f "$final_bundle" ) ]]; then rm -f -- "$final_sidecar"; fi
    rmdir -- "$lock_dir"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

work_dir="$(mktemp -d "$backup_root/.mc-hub-$(date -u +%Y%m%dT%H%M%SZ)-XXXXXXXX")"
run_id="${work_dir##*/}"
run_id="${run_id#.}"
bundle_name="${run_id}.tar.gz"
partial_bundle="$backup_root/.${bundle_name}.partial"
partial_sidecar="$backup_root/.${bundle_name}.sha256.partial"
final_bundle="$backup_root/$bundle_name"
final_sidecar="$final_bundle.sha256"

pg_dump --format=custom --no-owner --no-acl --file="$work_dir/database.dump" "$PGDATABASE"
pg_dump --schema-only --no-owner --no-acl --file="$work_dir/schema.sql" "$PGDATABASE"
tar -C "$PRIVATE_MEDIA_ROOT" -czf "$work_dir/evidence.tar.gz" .
cp -- "$MC_ENV_FILE" "$work_dir/environment.env"
chmod 600 "$work_dir/environment.env"
(cd "$work_dir" && sha256sum database.dump schema.sql evidence.tar.gz environment.env > SHA256SUMS)
schema_hash="$(sha256sum "$work_dir/schema.sql")"
schema_hash="${schema_hash%% *}"
printf 'format_version=2\ncreated_utc=%s\nsource_database=%s\nrelease_commit=%s\nschema_sha256=%s\n' \
    "$(date -u +%FT%TZ)" "$PGDATABASE" "$release_commit" "$schema_hash" > "$work_dir/manifest.txt"
tar -C "$backup_root" -czf "$partial_bundle" "${work_dir##*/}"
bundle_hash="$(sha256sum "$partial_bundle")"
printf '%s  %s\n' "${bundle_hash%% *}" "$bundle_name" > "$partial_sidecar"
# The archive becomes visible only after its sidecar is complete. Both renames
# stay on one filesystem; a failed run removes its unpublished sidecar.
mv -- "$partial_sidecar" "$final_sidecar"
partial_sidecar=""
mv -- "$partial_bundle" "$final_bundle"
partial_bundle=""
published=1
echo "Backup written: $final_bundle"

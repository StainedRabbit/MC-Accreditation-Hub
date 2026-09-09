#!/usr/bin/env bash
set -euo pipefail
umask 077

bundle="${1:?Usage: restore-verify.sh /absolute/path/to/backup.tar.gz /absolute/path/to/empty-restore-dir}"
restore_dir="${2:?Provide an empty restore directory.}"
case "$bundle" in /*) ;; *) echo "Backup path must be absolute." >&2; exit 1;; esac
case "$restore_dir" in /*) ;; *) echo "Restore directory must be absolute." >&2; exit 1;; esac
test -f "$bundle" || { echo "Backup bundle not found." >&2; exit 1; }
test ! -e "$restore_dir" || { echo "Restore directory must not already exist." >&2; exit 1; }

mkdir -p "$restore_dir"
trap 'rm -rf "$restore_dir"' ERR
tar -xzf "$bundle" -C "$restore_dir"
source_dir="$(find "$restore_dir" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
test -n "$source_dir" || { echo "Backup has no payload directory." >&2; exit 1; }
(cd "$source_dir" && sha256sum --check SHA256SUMS)
pg_restore --list "$source_dir/database.dump" >/dev/null
tar -tzf "$source_dir/evidence.tar.gz" >/dev/null
echo "Archive integrity verified. To perform a recovery, restore database.dump into a separately created non-production database and extract evidence.tar.gz into a new private directory before starting Django with matching environment settings."

"""Fail a release for pending migrations or deployment checks without explicit acceptance."""

import os
import re
import sys
from pathlib import Path


def evaluate_messages(messages, accepted, reason):
    failed = False
    for message in messages:
        identifier = message.id or "unidentified"
        if message.level >= 40:
            print(f"Deployment error {identifier}: {message.msg}", file=sys.stderr)
            failed = True
        elif message.level >= 30:
            if identifier in accepted and reason:
                print(f"Accepted deployment warning {identifier}: {message.msg} (reason: {reason})")
            else:
                print(f"Unaccepted deployment warning {identifier}: {message.msg}", file=sys.stderr)
                failed = True
    return not failed


def pending_labels(plan):
    return [migration.app_label + "." + migration.name for migration, _ in plan]


def main():
    if len(sys.argv) != 2:
        print("Usage: release-gate.py APP_ROOT", file=sys.stderr)
        return 1
    app_root = Path(sys.argv[1]).resolve()
    sys.path.insert(0, str(app_root / "backend"))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django
    from django.core.checks import run_checks
    from django.db import connection, DatabaseError
    from django.db.migrations.executor import MigrationExecutor

    django.setup()
    raw = os.getenv("MC_ACCEPTED_DEPLOY_WARNINGS", "")
    accepted = {part.strip() for part in raw.split(",") if part.strip()}
    reason = os.getenv("MC_ACCEPTED_DEPLOY_WARNINGS_REASON", "").strip()
    if (accepted and not reason) or any(not re.fullmatch(r"[A-Za-z0-9_.-]+\.W[0-9]+", item) for item in accepted):
        print("Accepted deployment warning IDs require a recorded reason and valid IDs.", file=sys.stderr)
        return 1
    if not evaluate_messages(run_checks(include_deployment_checks=True), accepted, reason):
        return 1
    try:
        executor = MigrationExecutor(connection)
        executor.loader.check_consistent_history(connection)
        pending = pending_labels(executor.migration_plan(executor.loader.graph.leaf_nodes()))
    except DatabaseError:
        print("Could not verify applied migrations against the configured database.", file=sys.stderr)
        return 1
    if pending:
        print("Unapplied migrations: " + ", ".join(pending), file=sys.stderr)
        return 1
    print("Deployment checks and applied migrations passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

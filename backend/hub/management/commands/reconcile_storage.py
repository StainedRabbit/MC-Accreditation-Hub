"""Read-only comparison of immutable version rows with private evidence bytes."""

import hashlib
import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from hub.models import DocumentVersion


class Command(BaseCommand):
    help = "Report missing, mismatched and orphaned private evidence files without modifying them."

    def handle(self, *args, **options):
        root = settings.PRIVATE_MEDIA_ROOT
        if root.is_symlink() or not root.is_dir():
            raise CommandError("PRIVATE_MEDIA_ROOT must be an existing private directory, not a link.")
        referenced = set()
        report = {"missing": [], "mismatched": [], "orphaned": []}
        for key, size, checksum in DocumentVersion.objects.values_list(
                'storage_key', 'size', 'checksum').iterator():
            name = str(key)
            referenced.add(name)
            path = root / name
            if not path.exists() and not path.is_symlink():
                report['missing'].append(name)
                continue
            if path.is_symlink() or not path.is_file():
                report['mismatched'].append(name)
                continue
            try:
                with path.open('rb') as source:
                    actual = hashlib.file_digest(source, 'sha256').hexdigest()
                if path.stat().st_size != size or actual != checksum:
                    report['mismatched'].append(name)
            except OSError:
                report['mismatched'].append(name)
        for path in root.iterdir():
            if path.name not in referenced:
                report['orphaned'].append(path.name)
        for values in report.values():
            values.sort()
        report['counts'] = {name: len(report[name]) for name in ('missing', 'mismatched', 'orphaned')}
        return json.dumps(report, sort_keys=True)

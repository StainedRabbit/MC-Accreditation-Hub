"""Read-only comparison of immutable version rows with private evidence bytes."""

import hashlib
import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from rest_framework.exceptions import ValidationError

from hub.models import DocumentVersion
from hub.storage import evidence_object_key, list_evidence_objects, read_r2_object


class Command(BaseCommand):
    help = "Report missing, mismatched and orphaned private evidence files without modifying them."

    def handle(self, *args, **options):
        root = settings.PRIVATE_MEDIA_ROOT
        if root.is_symlink() or (not root.is_dir() and not settings.R2_CONFIGURED):
            raise CommandError("PRIVATE_MEDIA_ROOT must be an existing private directory, not a link.")
        referenced = set()
        r2_referenced = set()
        report = {"missing": [], "mismatched": [], "orphaned": []}
        for key, size, checksum in DocumentVersion.objects.values_list(
                'storage_key', 'size', 'checksum').iterator():
            name = str(key)
            referenced.add(name)
            path = root / name
            local_exists = path.exists() or path.is_symlink()
            local_valid = False
            remote_exists = False
            remote_valid = False
            try:
                if local_exists and not path.is_symlink() and path.is_file():
                    with path.open('rb') as source:
                        actual = hashlib.file_digest(source, 'sha256').hexdigest()
                    local_valid = path.stat().st_size == size and actual == checksum
            except OSError:
                local_valid = False
            if settings.R2_CONFIGURED:
                r2_key = evidence_object_key(key)
                r2_referenced.add(r2_key)
                try:
                    remote = read_r2_object(r2_key)
                    remote_exists = remote is not None
                    remote_valid = remote_exists and len(remote) == size and hashlib.sha256(remote).hexdigest() == checksum
                except ValidationError:
                    remote_exists = True
                    remote_valid = False
            if local_exists and not local_valid:
                report['mismatched'].append(name)
            if remote_exists and not remote_valid:
                report['mismatched'].append('r2:' + name)
            if not local_valid and not remote_valid:
                report['missing'].append(name)
        if root.is_dir():
            for path in root.iterdir():
                if path.name not in referenced:
                    report['orphaned'].append(path.name)
        if settings.R2_CONFIGURED:
            try:
                for object_key in list_evidence_objects():
                    if object_key not in r2_referenced:
                        report['orphaned'].append('r2:' + object_key.removeprefix('evidence/'))
            except Exception as error:
                raise CommandError('Unable to list the private R2 evidence prefix.') from error
        for values in report.values():
            values.sort()
        report['counts'] = {name: len(report[name]) for name in ('missing', 'mismatched', 'orphaned')}
        return json.dumps(report, sort_keys=True)

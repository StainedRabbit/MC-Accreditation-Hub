"""Copy locally stored immutable versions to private R2 without deleting local files."""

import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from hub.models import DocumentVersion
from hub.storage import copy_local_version_to_r2


class Command(BaseCommand):
    help = 'Copy and verify every local evidence version in R2; preserve all source files.'

    def handle(self, *args, **options):
        if not settings.R2_CONFIGURED:
            raise CommandError('Configure the private R2 environment before copying evidence.')
        counts = {'copied': 0, 'already_present': 0}
        for version in DocumentVersion.objects.all().iterator():
            try:
                counts[copy_local_version_to_r2(version)] += 1
            except Exception:
                raise CommandError(f'Copy stopped at evidence version {version.pk}; inspect R2 connectivity and verify the source file.')
        return json.dumps(counts, sort_keys=True)

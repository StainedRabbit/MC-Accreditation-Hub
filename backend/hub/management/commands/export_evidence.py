"""Create a verified local backup set from private-media and referenced R2 evidence."""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from rest_framework.exceptions import ValidationError

from hub.models import DocumentVersion
from hub.storage import export_referenced_evidence


class Command(BaseCommand):
    help = 'Export and verify the evidence bytes referenced by the database into a private directory.'

    def add_arguments(self, parser):
        parser.add_argument('--output-dir', required=True)

    def handle(self, *args, **options):
        output_dir = Path(options['output_dir']).resolve()
        try:
            export_referenced_evidence(output_dir, DocumentVersion.objects.all().iterator())
        except (OSError, ValidationError) as error:
            raise CommandError(str(error)) from error
        return json.dumps({'exported_directory': str(output_dir), 'referenced_versions': DocumentVersion.objects.count()}, sort_keys=True)

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from hub.models import DocumentVersion
from hub.scanning import scan_status, scan_version


class Command(BaseCommand):
    help = 'Scan quarantined evidence with the locally configured School IT scanner.'

    def add_arguments(self, parser):
        parser.add_argument('--version-id', type=int, help='Rescan one version, including a previous threat verdict.')
        parser.add_argument('--limit', type=int, default=100)

    def handle(self, *args, **options):
        if not settings.EVIDENCE_SCANNER_COMMAND or not settings.EVIDENCE_SCANNER_ID:
            raise CommandError('An approved scanner command and identifier must be configured.')
        if options['limit'] < 1:
            raise CommandError('--limit must be positive.')
        if options['version_id']:
            ids = [options['version_id']]
            if not DocumentVersion.objects.filter(pk=ids[0]).exists():
                raise CommandError('Version not found.')
        else:
            pending, errors = [], []
            for version in DocumentVersion.objects.order_by('id'):
                status = scan_status(version)
                if status == 'pending':
                    pending.append(version.id)
                elif status == 'error':
                    errors.append(version.id)
            ids = (pending + errors)[:options['limit']]
        counts = {'clean': 0, 'infected': 0, 'error': 0}
        for version_id in ids:
            outcome = scan_version(version_id, force=bool(options['version_id']))
            counts[outcome] += 1
        self.stdout.write(f"Scanned {len(ids)} versions: {counts['clean']} clean, {counts['infected']} infected, {counts['error']} errors.")

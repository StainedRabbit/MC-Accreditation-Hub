"""Fail-closed malware scan gate for immutable evidence versions."""
import hashlib
import io
import subprocess

from django.conf import settings
from django.db import transaction
from rest_framework.exceptions import ValidationError

from .audit import write_audit
from .models import DocumentScan, DocumentVersion


def scan_status(version):
    latest = version.scans.order_by('-id').first()
    if latest is None:
        return 'pending'
    if latest.result == 'clean' and latest.checksum != version.checksum:
        return 'error'
    return latest.result


def clean_contents(version):
    if scan_status(version) != 'clean':
        raise ValidationError('This evidence version is quarantined until an approved malware scan passes.')
    source = settings.PRIVATE_MEDIA_ROOT / str(version.storage_key)
    try:
        contents = source.read_bytes()
    except OSError:
        raise ValidationError('Stored evidence is unavailable.')
    if hashlib.sha256(contents).hexdigest() != version.checksum:
        raise ValidationError('Stored evidence no longer matches the scanned checksum.')
    return contents


def require_clean(version):
    clean_contents(version)


def version_available(version):
    try:
        require_clean(version)
        return True
    except ValidationError:
        return False


def verified_file(version):
    """Return exactly the bytes that received a clean verdict."""
    return io.BytesIO(clean_contents(version))


def scan_version(version_id, *, force=False):
    """Run the locally configured School IT scanner. Exit 0=clean, 1=infected."""
    command = settings.EVIDENCE_SCANNER_COMMAND
    scanner_id = settings.EVIDENCE_SCANNER_ID
    if not command or not scanner_id:
        return 'pending'
    if command.count('{file}') != 1 or not all(isinstance(arg, str) for arg in command):
        raise ValueError('Scanner command must contain one {file} argument.')
    with transaction.atomic():
        version = DocumentVersion.objects.select_for_update().select_related('document__area').get(pk=version_id)
        if not force and scan_status(version) == 'clean':
            return 'clean'
        source = settings.PRIVATE_MEDIA_ROOT / str(version.storage_key)
        checksum = ''
        result = 'error'
        try:
            checksum = hashlib.sha256(source.read_bytes()).hexdigest()
            if checksum == version.checksum:
                args = [str(source) if arg == '{file}' else arg for arg in command]
                completed = subprocess.run(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                           stderr=subprocess.DEVNULL, timeout=settings.EVIDENCE_SCANNER_TIMEOUT,
                                           check=False)
                after = hashlib.sha256(source.read_bytes()).hexdigest()
                if after == checksum:
                    result = {0: 'clean', 1: 'infected'}.get(completed.returncode, 'error')
        except (OSError, subprocess.TimeoutExpired):
            pass
        verdict = DocumentScan.objects.create(version=version, result=result, checksum=checksum,
                                              scanner_id=scanner_id)
        write_audit(None, version.document.area, 'version_scan_' + result, f'version:{version.id}',
                    version=version.id, scan=verdict.id, scanner_id=scanner_id, checksum=checksum)
        return result

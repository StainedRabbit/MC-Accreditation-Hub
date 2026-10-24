"""Private evidence storage backed by legacy local files and Cloudflare R2."""

import hashlib
from pathlib import Path
from uuid import UUID

from django.conf import settings
from rest_framework.exceptions import ValidationError


MAX_EVIDENCE_SIZE = 25 * 1024 * 1024


def r2_client():
    if not settings.R2_CONFIGURED:
        raise RuntimeError('Cloudflare R2 storage is not configured.')
    import boto3
    from botocore.config import Config

    return boto3.client(
        's3', endpoint_url=settings.R2_ENDPOINT_URL, region_name='auto',
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        config=Config(signature_version='s3v4', s3={'addressing_style': 'path'}),
    )


def evidence_object_key(storage_key):
    return f'evidence/{UUID(str(storage_key))}'


def pending_object_key(storage_key):
    return f'pending/{UUID(str(storage_key))}'


def create_presigned_upload(storage_key, content_type, checksum):
    key = pending_object_key(storage_key)
    url = r2_client().generate_presigned_url(
        'put_object',
        Params={
            'Bucket': settings.R2_BUCKET_NAME,
            'Key': key,
            'ContentType': content_type,
            'Metadata': {'sha256': checksum},
        },
        ExpiresIn=settings.R2_UPLOAD_URL_TTL,
        HttpMethod='PUT',
    )
    return url, key


def _is_not_found(error):
    response = getattr(error, 'response', {}) or {}
    code = str(response.get('Error', {}).get('Code', ''))
    status = response.get('ResponseMetadata', {}).get('HTTPStatusCode')
    return code in {'NoSuchKey', 'NotFound', '404'} or status == 404


def read_r2_object(key, *, required=False):
    try:
        response = r2_client().get_object(Bucket=settings.R2_BUCKET_NAME, Key=key)
    except Exception as error:
        if _is_not_found(error) and not required:
            return None
        raise ValidationError('Stored evidence is unavailable.') from error
    body = response['Body']
    try:
        contents = body.read(MAX_EVIDENCE_SIZE + 1)
    finally:
        body.close()
    if len(contents) > MAX_EVIDENCE_SIZE or len(contents) != response.get('ContentLength'):
        raise ValidationError('Stored evidence has an invalid size.')
    return contents


def read_version_contents(version):
    """Read and verify an R2 object, falling back only when it is absent to legacy local media."""
    contents = None
    if settings.R2_CONFIGURED:
        contents = read_r2_object(evidence_object_key(version.storage_key))
    if contents is None:
        path = settings.PRIVATE_MEDIA_ROOT / str(version.storage_key)
        try:
            if path.is_symlink() or not path.is_file():
                raise OSError
            contents = path.read_bytes()
        except OSError as error:
            raise ValidationError('Stored evidence is unavailable.') from error
    if len(contents) != version.size or hashlib.sha256(contents).hexdigest() != version.checksum:
        raise ValidationError('Stored evidence does not match its recorded checksum.')
    return contents


def pending_upload_contents(intent):
    contents = read_r2_object(pending_object_key(intent.storage_key), required=True)
    if len(contents) != intent.size or hashlib.sha256(contents).hexdigest() != intent.checksum:
        raise ValidationError('Uploaded evidence does not match the prepared file.')
    return contents


def publish_pending_upload(intent):
    client = r2_client()
    source = pending_object_key(intent.storage_key)
    destination = evidence_object_key(intent.storage_key)
    client.copy_object(
        Bucket=settings.R2_BUCKET_NAME,
        Key=destination,
        CopySource={'Bucket': settings.R2_BUCKET_NAME, 'Key': source},
        MetadataDirective='COPY',
    )
    try:
        head = client.head_object(Bucket=settings.R2_BUCKET_NAME, Key=destination)
        metadata = {str(key).lower(): value for key, value in head.get('Metadata', {}).items()}
        if head.get('ContentLength') != intent.size or metadata.get('sha256') != intent.checksum:
            raise ValidationError('Uploaded evidence could not be safely finalized.')
    except Exception as error:
        try:
            client.delete_object(Bucket=settings.R2_BUCKET_NAME, Key=destination)
        except Exception:
            pass
        if isinstance(error, ValidationError):
            raise
        raise ValidationError('Uploaded evidence could not be safely finalized.') from error
    return destination


def delete_r2_object(key):
    r2_client().delete_object(Bucket=settings.R2_BUCKET_NAME, Key=key)


def copy_local_version_to_r2(version):
    """Copy a referenced legacy file without removing or changing its local source."""
    client = r2_client()
    destination = evidence_object_key(version.storage_key)
    try:
        head = client.head_object(Bucket=settings.R2_BUCKET_NAME, Key=destination)
    except Exception as error:
        if not _is_not_found(error):
            raise
    else:
        existing = read_r2_object(destination, required=True)
        if len(existing) != version.size or hashlib.sha256(existing).hexdigest() != version.checksum:
            raise ValidationError(f'Existing R2 object does not match version {version.pk}.')
        return 'already_present'

    source = settings.PRIVATE_MEDIA_ROOT / str(version.storage_key)
    if source.is_symlink() or not source.is_file():
        raise ValidationError(f'Legacy evidence file is missing or unsafe for version {version.pk}.')
    contents = source.read_bytes()
    if len(contents) != version.size or hashlib.sha256(contents).hexdigest() != version.checksum:
        raise ValidationError(f'Legacy evidence checksum does not match version {version.pk}.')
    client.put_object(
        Bucket=settings.R2_BUCKET_NAME,
        Key=destination,
        Body=contents,
        ContentLength=len(contents),
        ContentType=version.content_type,
        Metadata={'sha256': version.checksum},
    )
    return 'copied'


def list_evidence_objects():
    client = r2_client()
    paginator = client.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=settings.R2_BUCKET_NAME, Prefix='evidence/'):
        for item in page.get('Contents', []):
            yield item['Key']


def export_referenced_evidence(output_dir, versions):
    """Write a verified backup set containing local files and referenced R2 evidence."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    root = settings.PRIVATE_MEDIA_ROOT
    if root.is_symlink() or (not root.is_dir() and not settings.R2_CONFIGURED):
        raise ValidationError('PRIVATE_MEDIA_ROOT must be an existing private directory, not a link.')
    if root.is_dir():
        for path in root.iterdir():
            if path.is_symlink() or not path.is_file():
                raise ValidationError('PRIVATE_MEDIA_ROOT contains a non-regular entry.')
            (output_dir / path.name).write_bytes(path.read_bytes())
    for version in versions:
        local_path = output_dir / str(version.storage_key)
        local_valid = False
        if local_path.is_file():
            local_data = local_path.read_bytes()
            local_valid = len(local_data) == version.size and hashlib.sha256(local_data).hexdigest() == version.checksum
        if settings.R2_CONFIGURED:
            remote = read_r2_object(evidence_object_key(version.storage_key))
            if remote is not None:
                if len(remote) != version.size or hashlib.sha256(remote).hexdigest() != version.checksum:
                    raise ValidationError(f'R2 evidence checksum does not match version {version.pk}.')
                if local_valid and remote != local_data:
                    raise ValidationError(f'Local and R2 evidence differ for version {version.pk}.')
                if not local_valid:
                    local_path.write_bytes(remote)
                continue
        if not local_valid:
            raise ValidationError(f'No verified evidence bytes are available for version {version.pk}.')


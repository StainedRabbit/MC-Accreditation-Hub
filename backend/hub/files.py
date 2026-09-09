import hashlib
import io
import zipfile
from xml.etree import ElementTree
from pathlib import Path
from PIL import Image
from pypdf import PdfReader
from rest_framework.exceptions import ValidationError

TYPES = {'.pdf': 'application/pdf', '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
         '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg'}


def validate_upload(upload):
    if not upload or upload.size == 0 or upload.size > 25 * 1024 * 1024:
        raise ValidationError('Choose a nonempty file no larger than 25 MB.')
    name = Path(upload.name.replace('\\', '/')).name
    suffix = Path(name).suffix.lower()
    if suffix not in TYPES:
        raise ValidationError('Supported files: PDF, DOCX, XLSX, PNG, and JPEG.')
    data = upload.read()
    try:
        if suffix == '.pdf':
            if not data.startswith(b'%PDF-'):
                raise ValueError()
            pdf = PdfReader(io.BytesIO(data), strict=True)
            if pdf.is_encrypted or not len(pdf.pages):
                raise ValueError()
        elif suffix in ['.png', '.jpg', '.jpeg']:
            with Image.open(io.BytesIO(data)) as img:
                if img.format != ('PNG' if suffix == '.png' else 'JPEG') or img.width * img.height > 40_000_000:
                    raise ValueError()
                img.verify()
        else:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                entries = archive.infolist()
                names = {e.filename for e in entries}
                required = 'word/document.xml' if suffix == '.docx' else 'xl/workbook.xml'
                if required not in names or '[Content_Types].xml' not in names or len(entries) > 5000:
                    raise ValueError()
                if sum(e.file_size for e in entries) > 100 * 1024 * 1024:
                    raise ValueError()
                if any('vbaproject' in n.lower() or n.startswith('/') or '..' in n.split('/') for n in names):
                    raise ValueError()
                if archive.getinfo(required).file_size > 10 * 1024 * 1024:
                    raise ValueError()
                main = ElementTree.fromstring(archive.read(required))
                expected_root = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}document' if suffix == '.docx' else '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}workbook'
                content_types = ElementTree.fromstring(archive.read('[Content_Types].xml'))
                expected_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml' if suffix == '.docx' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml'
                if main.tag != expected_root or not any(e.attrib.get('PartName') == '/' + required and e.attrib.get('ContentType') == expected_type for e in content_types):
                    raise ValueError()
                if archive.testzip():
                    raise ValueError()
    except Exception:
        raise ValidationError('The file content is invalid, encrypted, or does not match its extension.')
    return name[:255], TYPES[suffix], data, hashlib.sha256(data).hexdigest()

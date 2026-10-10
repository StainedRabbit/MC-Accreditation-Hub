"""Simulated clean verdict for one known PDF in a disposable browser test only."""
import hashlib
import os
import re
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2 or os.environ.get('E2E_SCANNER_GUARD') != '1':
        return 2
    if not re.fullmatch(r'mc_browser_[0-9a-f]{12}', os.environ.get('PGDATABASE', '')):
        return 2
    root = Path(__file__).resolve().parent.parent
    local = (root / '.local').resolve()
    scratch = Path(os.environ.get('E2E_SCRATCH', '')).resolve()
    media = Path(os.environ.get('PRIVATE_MEDIA_ROOT', '')).resolve()
    source = Path(sys.argv[1]).resolve()
    if not scratch.is_relative_to(local) or not scratch.name.startswith('isolated-browser-'):
        return 2
    if media != scratch / 'media' or not source.is_file() or not source.is_relative_to(media):
        return 2
    expected = os.environ.get('E2E_SAMPLE_SHA256', '')
    if not re.fullmatch(r'[0-9a-f]{64}', expected):
        return 2
    return 0 if hashlib.sha256(source.read_bytes()).hexdigest() == expected else 2


if __name__ == '__main__':
    raise SystemExit(main())

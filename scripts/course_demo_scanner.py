"""Synthetic scan fixture for two known fictional PDFs in mc_course_demo only.

This deliberately does not detect malware and must never be used for real files.
"""
import hashlib
import os
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2 or os.environ.get('MC_COURSE_DEMO') != '1':
        return 2
    if os.environ.get('PGDATABASE') != 'mc_course_demo' or os.environ.get('DJANGO_DEBUG') != '1':
        return 2
    workspace = Path(__file__).resolve().parent.parent
    media = (workspace / '.local' / 'course-demo' / 'media').resolve()
    if media != workspace.resolve() / '.local' / 'course-demo' / 'media':
        return 2
    configured_media = Path(os.environ.get('PRIVATE_MEDIA_ROOT', '')).resolve()
    source = Path(sys.argv[1]).resolve()
    if configured_media != media or not source.is_file() or not source.is_relative_to(media):
        return 2
    permitted = set(os.environ.get('MC_COURSE_DEMO_SHA256', '').split(','))
    if not permitted or '' in permitted:
        return 2
    return 0 if hashlib.sha256(source.read_bytes()).hexdigest() in permitted else 2


if __name__ == '__main__':
    raise SystemExit(main())

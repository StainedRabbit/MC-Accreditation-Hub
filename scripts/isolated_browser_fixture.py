"""Guarded local fixture mutations for the isolated synthetic browser run."""
import os
import re
import sys
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parent.parent
LOCAL = (ROOT / '.local').resolve()
name = os.getenv('PGDATABASE', '')
scratch = Path(os.getenv('E2E_SCRATCH', '')).resolve()
if (not re.fullmatch(r'mc_browser_[0-9a-f]{12}', name) or
        os.getenv('E2E_ISOLATED_DB_NAME') != name or
        os.getenv('PGHOST') != '127.0.0.1' or os.getenv('PGPORT') != '55432' or
        not scratch.is_relative_to(LOCAL) or not scratch.name.startswith('isolated-browser-') or
        Path(os.getenv('PRIVATE_MEDIA_ROOT', '')).resolve() != scratch / 'media'):
    raise SystemExit('Isolated local browser fixture guard failed.')
with psycopg.connect(host='127.0.0.1', port=55432, user='mc_hub', dbname=name) as database:
    directory = Path(database.execute('SHOW data_directory').fetchone()[0]).resolve()
if directory != (LOCAL / 'postgres').resolve():
    raise SystemExit('The connected database is not the repository-local test cluster.')

sys.path.insert(0, str(ROOT / 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from hub.models import Area, Cycle, RoleAssignment, User

cycle = Cycle.objects.get(is_demo=True)
if Cycle.objects.count() != 1:
    raise SystemExit('Only the fictional demo cycle may exist in this fixture.')
if sys.argv[1:] == ['deactivate-viewer']:
    viewer = User.objects.get(username='demo.viewer')
    viewer.is_active = False
    viewer.save(update_fields=['is_active'])
elif sys.argv[1:] == ['revoke-faculty']:
    custodian = User.objects.get(username='demo.custodian')
    faculty = Area.objects.get(cycle=cycle, title='Faculty')
    removed, _ = RoleAssignment.objects.filter(user=custodian, cycle=cycle, area=faculty,
                                                role='custodian').delete()
    if removed != 1:
        raise SystemExit('Expected exactly one fictional Faculty grant.')
else:
    raise SystemExit('Unknown isolated browser fixture action.')

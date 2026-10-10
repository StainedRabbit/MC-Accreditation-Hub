"""Read-only checks for the disposable MIT 007 demo boundaries."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import course_demo


root = Path(__file__).resolve().parent.parent
state = json.loads((root / '.local/course-demo/state.json').read_text(encoding='utf-8'))
known = root / '.local/course-demo/media/guard-known.pdf'
unknown = root / '.local/course-demo/media/guard-unknown.pdf'
source = root / '.local/course-demo/source/fictional-faculty-plan.pdf'
scanner = root / 'scripts/course_demo_scanner.py'
base = course_demo._env(state)
postgres = course_demo._start_postgres()


def verdict(file, changes=None):
    env = base.copy()
    env.update(changes or {})
    return subprocess.run([sys.executable, '-B', str(scanner), str(file)],
                          cwd=root, env=env, capture_output=True, check=False).returncode


try:
    known.write_bytes(source.read_bytes())
    unknown.write_bytes(b'%PDF-1.4\nfictional but not approved by the fixture\n')
    assert hashlib.sha256(known.read_bytes()).hexdigest() in state['allowed_sha256']
    assert verdict(known) == 0, 'Known synthetic file should receive simulated clean verdict.'
    assert verdict(unknown) == 2, 'Unknown file should be refused.'
    assert verdict(source) == 2, 'A file outside private media should be refused.'
    assert verdict(known, {'PGDATABASE': 'mc_demo'}) == 2, 'Wrong database should be refused.'
    assert verdict(known, {'PRIVATE_MEDIA_ROOT': str(root / '.local')}) == 2, 'Wrong media path should be refused.'
    assert verdict(known, {'MC_COURSE_DEMO': '0'}) == 2, 'Missing demo guard should be refused.'
    original = course_demo.PGDATA
    try:
        course_demo.PGDATA = root / '.local/not-the-cluster'
        try:
            course_demo._database_connection()
        except RuntimeError:
            pass
        else:
            raise AssertionError('Wrong PostgreSQL data directory was accepted.')
    finally:
        course_demo.PGDATA = original
    original = course_demo.DEMO
    try:
        course_demo.DEMO = (root / 'docs').resolve()
        try:
            course_demo._safe_demo_path()
        except RuntimeError:
            pass
        else:
            raise AssertionError('Wrong demo path was accepted.')
    finally:
        course_demo.DEMO = original
    original = course_demo.MEDIA
    try:
        course_demo.MEDIA = (root / 'docs').resolve()
        try:
            course_demo._safe_demo_path()
        except RuntimeError:
            pass
        else:
            raise AssertionError('Wrong media directory was accepted.')
    finally:
        course_demo.MEDIA = original
    print('Demo guards passed: known file only, wrong DB/media rejected, wrong cluster/path rejected.')
finally:
    known.unlink(missing_ok=True)
    unknown.unlink(missing_ok=True)
    if postgres is not None:
        postgres.terminate()
        postgres.wait(timeout=10)

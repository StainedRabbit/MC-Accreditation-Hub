"""Run Playwright against a disposable fictional database and loopback services."""
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import psycopg
from psycopg import sql
from pypdf import PdfWriter


ROOT = Path(__file__).resolve().parent.parent
LOCAL = (ROOT / '.local').resolve()
DB_NAME = 'mc_browser_' + secrets.token_hex(6)


def free_port():
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        return listener.getsockname()[1]


def ready(url, process):
    for _ in range(100):
        if process.poll() is not None:
            raise RuntimeError('A temporary loopback service stopped during startup.')
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError('A temporary loopback service did not become ready.')


def run_quiet(stage, command, env):
    result = subprocess.run(command, cwd=ROOT, env=env, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, timeout=120)
    if result.returncode:
        raise RuntimeError(f'{stage} failed (exit {result.returncode}); no credentials were printed.')


def main():
    if os.name != 'nt' or not LOCAL.joinpath('postgres').is_dir():
        raise RuntimeError('This runner requires the ignored repository-local Windows PostgreSQL cluster.')
    node = shutil.which('node')
    if not node or not ROOT.joinpath('frontend/node_modules/@playwright/test/cli.js').is_file():
        raise RuntimeError('Install the existing frontend dependencies before this local run.')
    LOCAL.mkdir(exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix='isolated-browser-', dir=LOCAL)).resolve()
    if not scratch.is_relative_to(LOCAL) or scratch == LOCAL:
        raise RuntimeError('Temporary path escaped the intended local directory.')
    # The local trust-authenticated cluster does not need an ambient password file.
    os.environ.pop('PGPASSWORD', None)
    os.environ['PGPASSFILE'] = str(scratch / 'no-passfile')
    created = False
    processes = []
    try:
        admin = psycopg.connect(host='127.0.0.1', port=55432, user='mc_hub', dbname='postgres',
                                connect_timeout=3, autocommit=True)
        try:
            directory = Path(admin.execute('SHOW data_directory').fetchone()[0]).resolve()
            if directory != LOCAL.joinpath('postgres').resolve():
                raise RuntimeError('The connected database is not the repository-local test cluster.')
            admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(DB_NAME)))
            created = True
        finally:
            admin.close()
        backend_port, frontend_port = free_port(), free_port()
        if backend_port == frontend_port:
            frontend_port = free_port()
        media = scratch / 'media'
        media.mkdir()
        sample = scratch / 'synthetic-evidence.pdf'
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        with sample.open('wb') as output:
            writer.write(output)
        env = os.environ.copy()
        env.update({'PGHOST': '127.0.0.1', 'PGPORT': '55432', 'PGUSER': 'mc_hub',
                    'PGDATABASE': DB_NAME, 'PRIVATE_MEDIA_ROOT': str(media),
                    'DJANGO_SECRET_KEY': secrets.token_urlsafe(48), 'DJANGO_DEBUG': '1',
                    'DJANGO_ALLOWED_HOSTS': '127.0.0.1,localhost',
                    'CSRF_TRUSTED_ORIGINS': f'http://127.0.0.1:{frontend_port}',
                    'PASSWORD_RESET_ENABLED': '0', 'RESTRICTED_TEST_MODE': '0',
                    'DJANGO_EMAIL_BACKEND': 'django.core.mail.backends.dummy.EmailBackend',
                    'EMAIL_HOST_USER': '', 'EMAIL_HOST_PASSWORD': '', 'DEFAULT_FROM_EMAIL': '',
                    'MC_DEMO_PASSWORD': secrets.token_urlsafe(20),
                    'E2E_BACKEND_URL': f'http://127.0.0.1:{backend_port}',
                    'E2E_BASE_URL': f'http://127.0.0.1:{frontend_port}',
                    'E2E_OUTPUT_DIR': str(scratch / 'playwright-results'),
                    'E2E_SCRATCH': str(scratch), 'E2E_ISOLATED_DB_NAME': DB_NAME,
                    'E2E_SAMPLE_PDF': str(sample), 'E2E_PYTHON': sys.executable})
        env['E2E_SYNTHETIC_PASSWORD'] = env['MC_DEMO_PASSWORD']
        env['E2E_NEW_PASSWORD'] = secrets.token_urlsafe(20)
        run_quiet('Temporary schema migration', [sys.executable, '-B', 'backend/manage.py',
                                                   'migrate', '--noinput'], env)
        run_quiet('Fictional seed', [sys.executable, '-B', 'backend/manage.py', 'seed_demo'], env)
        if not sys.argv[1:] or 'legacy-review-context.spec.ts' in sys.argv[1:]:
            run_quiet('Legacy review browser fixture', [sys.executable, '-B', 'backend/manage.py',
                                                        'seed_legacy_review_e2e'], env)
        backend = subprocess.Popen([sys.executable, '-B', 'backend/manage.py', 'runserver',
                                    f'127.0.0.1:{backend_port}', '--noreload'], cwd=ROOT, env=env,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        processes.append(backend)
        ready(f'http://127.0.0.1:{backend_port}/api/health/', backend)
        frontend = subprocess.Popen([node, str(ROOT / 'frontend/node_modules/vite/bin/vite.js'),
                                     '--host', '127.0.0.1', '--port', str(frontend_port), '--strictPort'],
                                    cwd=ROOT / 'frontend', env=env,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        processes.append(frontend)
        ready(f'http://127.0.0.1:{frontend_port}/', frontend)
        print('Isolated fictional browser services ready on temporary loopback ports.', flush=True)
        suites = ([sys.argv[1:]] if sys.argv[1:] else [
            sorted(p.name for p in (ROOT / 'frontend/e2e').glob('*.spec.ts')
                   if p.name != 'isolated-session.spec.ts'),
            ['isolated-session.spec.ts'],
        ])
        for suite in suites:
            result = subprocess.run([node, str(ROOT / 'frontend/node_modules/@playwright/test/cli.js'),
                                     'test', *suite], cwd=ROOT / 'frontend', env=env, timeout=1200)
            if result.returncode:
                return result.returncode
        return 0
    finally:
        for process in reversed(processes):
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
        if created and re.fullmatch(r'mc_browser_[0-9a-f]{12}', DB_NAME):
            with psycopg.connect(host='127.0.0.1', port=55432, user='mc_hub', dbname='postgres',
                                 connect_timeout=3, autocommit=True) as admin:
                directory = Path(admin.execute('SHOW data_directory').fetchone()[0]).resolve()
                if directory != LOCAL.joinpath('postgres').resolve():
                    raise RuntimeError('Refusing cleanup against a different database cluster.')
                admin.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(DB_NAME)))
        if scratch.is_relative_to(LOCAL) and scratch.name.startswith('isolated-browser-'):
            shutil.rmtree(scratch)
        print('Temporary fictional database, evidence, and browser artifacts removed.', flush=True)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        raise SystemExit(f'Isolated browser run failed: {error}')

"""Start or reset an isolated, fictional MIT 007 demonstration on this Windows laptop."""
import argparse
import hashlib
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

import psycopg
from psycopg import sql


ROOT = Path(__file__).resolve().parent.parent
LOCAL = (ROOT / '.local').resolve()
DEMO = (LOCAL / 'course-demo').resolve()
MEDIA = DEMO / 'media'
STATE = DEMO / 'state.json'
STOP = DEMO / 'stop.request'
DB_NAME = 'mc_course_demo'
PGDATA = LOCAL / 'postgres'
POSTGRES = Path(r'C:\Program Files\PostgreSQL\18\bin\postgres.exe')


def _safe_demo_path():
    expected_local = ROOT.resolve() / '.local'
    if (LOCAL != expected_local or DEMO != LOCAL / 'course-demo' or
            MEDIA.resolve() != DEMO / 'media'):
        raise RuntimeError('Course demo path escaped the ignored project-local directory.')


def _database_connection():
    connection = psycopg.connect(host='127.0.0.1', port=55432, user='mc_hub', dbname='postgres',
                                 connect_timeout=3, autocommit=True)
    actual = Path(connection.execute('SHOW data_directory').fetchone()[0]).resolve()
    if actual != PGDATA.resolve():
        connection.close()
        raise RuntimeError('Connected PostgreSQL is not the repository-local test cluster.')
    return connection


def _postgres_ready():
    try:
        with _database_connection():
            return True
    except psycopg.OperationalError:
        return False


def _start_postgres():
    if not PGDATA.is_dir() or not POSTGRES.is_file():
        raise RuntimeError('The repository-local PostgreSQL 18 cluster is unavailable.')
    if _postgres_ready():
        return None
    _safe_demo_path()
    LOCAL.mkdir(exist_ok=True)
    log = (LOCAL / 'course-demo-postgres.log').open('a', encoding='utf-8')
    process = subprocess.Popen([str(POSTGRES), '-D', str(PGDATA), '-p', '55432', '-h', '127.0.0.1'],
                               cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    log.close()
    for _ in range(60):
        if process.poll() is not None:
            raise RuntimeError('Repository-local PostgreSQL stopped during startup.')
        if _postgres_ready():
            return process
        time.sleep(0.5)
    process.terminate()
    raise RuntimeError('Repository-local PostgreSQL did not become ready.')


def _pdf_bytes(lines):
    """Build a small readable PDF without external images or institutional content."""
    def escaped(value):
        return value.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
    commands = ['BT', '/F1 20 Tf', '60 760 Td']
    for index, line in enumerate(lines):
        if index:
            commands.append('0 -34 Td')
            commands.append('/F1 14 Tf')
        commands.append(f'({escaped(line)}) Tj')
    commands.append('ET')
    stream = '\n'.join(commands).encode('ascii')
    objects = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
        b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream',
    ]
    result = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for index, value in enumerate(objects, 1):
        offsets.append(len(result))
        result.extend(f'{index} 0 obj\n'.encode() + value + b'\nendobj\n')
    xref = len(result)
    result.extend(f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode())
    for offset in offsets[1:]:
        result.extend(f'{offset:010} 00000 n \n'.encode())
    result.extend(f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
    return bytes(result)


def _env(state):
    env = os.environ.copy()
    env.pop('PGPASSWORD', None)
    env.update({
        'PGHOST': '127.0.0.1', 'PGPORT': '55432', 'PGUSER': 'mc_hub', 'PGDATABASE': DB_NAME,
        'PGPASSFILE': str(DEMO / 'no-passfile'), 'PRIVATE_MEDIA_ROOT': str(MEDIA),
        'DJANGO_SECRET_KEY': state['secret_key'], 'DJANGO_DEBUG': '1',
        'DJANGO_ALLOWED_HOSTS': '127.0.0.1,localhost',
        'CSRF_TRUSTED_ORIGINS': 'http://127.0.0.1:5173',
        'PASSWORD_RESET_ENABLED': '0', 'MC_DEMO_PASSWORD': state['password'],
        'MC_COURSE_DEMO': '1', 'MC_COURSE_DEMO_SHA256': ','.join(state['allowed_sha256']),
        'EVIDENCE_SCANNER_ID': 'synthetic-course-demo-only',
        'EVIDENCE_SCANNER_COMMAND': json.dumps([sys.executable, str(ROOT / 'scripts' / 'course_demo_scanner.py'), '{file}']),
    })
    return env


def _run_checked(label, args, env):
    result = subprocess.run(args, cwd=ROOT, env=env, timeout=180)
    if result.returncode:
        raise RuntimeError(f'{label} failed with exit code {result.returncode}.')


def _database_exists(connection):
    return connection.execute('SELECT 1 FROM pg_database WHERE datname = %s', (DB_NAME,)).fetchone() is not None


def prepare():
    _safe_demo_path()
    with _database_connection() as connection:
        exists = _database_exists(connection)
        if STATE.is_file():
            state = json.loads(STATE.read_text(encoding='utf-8'))
            if state.get('database') != DB_NAME or not exists:
                raise RuntimeError('Course demo state/database mismatch; no records changed.')
            return state
        if exists:
            raise RuntimeError('Dedicated database exists without its state marker; refusing to reuse it.')
        DEMO.mkdir(parents=True, exist_ok=True)
        MEDIA.mkdir(exist_ok=True)
        source = DEMO / 'source'
        source.mkdir(exist_ok=True)
        a = source / 'fictional-faculty-plan.pdf'
        b = source / 'fictional-implementation-report.pdf'
        a.write_bytes(_pdf_bytes(['FICTIONAL COURSE DEMO', 'Faculty plan - sample evidence',
                                  'Mabini Colleges Graduate School example', 'No institutional data or approved criteria']))
        b.write_bytes(_pdf_bytes(['FICTIONAL COURSE DEMO', 'Implementation report - sample evidence',
                                  'Synthetic activities and outcomes', 'No institutional data or approved criteria']))
        state = {'database': DB_NAME, 'password': secrets.token_urlsafe(20),
                 'secret_key': secrets.token_urlsafe(48),
                 'allowed_sha256': [hashlib.sha256(a.read_bytes()).hexdigest(),
                                    hashlib.sha256(b.read_bytes()).hexdigest()]}
        connection.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(DB_NAME)))
    env = _env(state)
    try:
        _run_checked('Migrations', [sys.executable, '-B', 'backend/manage.py', 'migrate', '--noinput'], env)
        _run_checked('Fictional seed', [sys.executable, '-B', 'backend/manage.py', 'seed_demo'], env)
        _run_checked('Faculty assignment', [sys.executable, '-B', 'backend/manage.py', 'seed_course_demo'], env)
        STATE.write_text(json.dumps(state, indent=2), encoding='utf-8')
    except Exception:
        with _database_connection() as connection:
            connection.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(DB_NAME)))
        if DEMO.is_relative_to(LOCAL) and DEMO.name == 'course-demo':
            shutil.rmtree(DEMO)
        raise
    print('Course demo prepared with fictional data. Credentials remain in ignored .local/course-demo/state.json.')
    return state


def reset():
    _safe_demo_path()
    if not STATE.is_file():
        raise RuntimeError('No valid course demo marker; refusing to delete any database or directory.')
    state = json.loads(STATE.read_text(encoding='utf-8'))
    if state.get('database') != DB_NAME:
        raise RuntimeError('Unexpected course demo state; refusing reset.')
    with _database_connection() as connection:
        if _database_exists(connection):
            connection.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(DB_NAME)))
    if DEMO.is_relative_to(LOCAL) and DEMO.name == 'course-demo':
        shutil.rmtree(DEMO)
    print('Only the dedicated fictional course demo database and directory were removed.')


def _wait_for(url, process):
    for _ in range(100):
        if process.poll() is not None:
            raise RuntimeError('A course demo service stopped during startup.')
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f'Course demo service did not become ready: {url}')


def run():
    state = prepare()
    STOP.unlink(missing_ok=True)
    env = _env(state)
    processes = []
    try:
        for port in (8000, 5173):
            with socket.socket() as probe:
                if probe.connect_ex(('127.0.0.1', port)) == 0:
                    raise RuntimeError(f'Port {port} is already occupied; stop that service before the course demo.')
        for label, args in [
            ('backend', [sys.executable, '-B', 'backend/manage.py', 'runserver', '127.0.0.1:8000', '--noreload']),
            ('frontend', ['npm.cmd', 'run', 'dev', '--prefix', 'frontend', '--', '--host', '127.0.0.1']),
        ]:
            log = (DEMO / f'{label}.log').open('a', encoding='utf-8')
            process = subprocess.Popen(args, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
            log.close()
            processes.append(process)
            _wait_for('http://127.0.0.1:8000/api/health/' if label == 'backend' else
                      'http://127.0.0.1:5173/', process)
        print('Fictional course demo ready: http://127.0.0.1:5173/')
        print('Use usernames demo.coordinator, demo.custodian, demo.reviewer, and demo.viewer.')
        print('Read the generated password privately from .local/course-demo/state.json.')
        print('Run python -B scripts/course_demo.py stop in another terminal to stop the local services.')
        stop = threading.Event()
        def wait_for_enter():
            try:
                input()
                stop.set()
            except EOFError:
                pass
        threading.Thread(target=wait_for_enter, daemon=True).start()
        while not stop.is_set() and not STOP.is_file() and all(process.poll() is None for process in processes):
            time.sleep(0.5)
        if not stop.is_set() and not STOP.is_file():
            raise RuntimeError('A course demo service exited unexpectedly; inspect .local/course-demo/*.log.')
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
        STOP.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'run', 'reset', 'status', 'stop'])
    action = parser.parse_args().action
    if action == 'stop':
        _safe_demo_path()
        if not STATE.is_file() or json.loads(STATE.read_text(encoding='utf-8')).get('database') != DB_NAME:
            raise RuntimeError('No valid course demo state marker; stop request refused.')
        STOP.write_text('stop', encoding='ascii')
        print('Course demo stop requested; the launcher will stop both local services.')
        return
    postgres = _start_postgres()
    try:
        if action == 'prepare':
            prepare()
        elif action == 'run':
            run()
        elif action == 'reset':
            reset()
        else:
            with _database_connection() as connection:
                print(f'Local cluster verified; dedicated database exists: {_database_exists(connection)}; state marker exists: {STATE.is_file()}')
    finally:
        if postgres is not None:
            postgres.terminate()
            try:
                postgres.wait(timeout=10)
            except subprocess.TimeoutExpired:
                postgres.kill()


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, psycopg.Error, subprocess.TimeoutExpired) as error:
        raise SystemExit(f'Course demo stopped: {error}')

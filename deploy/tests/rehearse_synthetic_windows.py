"""One-off local synthetic rehearsal; never connect outside the ignored cluster."""
import hashlib
import os
import shlex
import subprocess
import sys
import tarfile
import tempfile
import uuid
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[2]
PG_BIN = Path('C:/Program Files/PostgreSQL/18/bin')
BASH = Path('C:/Program Files/Git/bin/bash.exe')
PORT = 55432
USER = 'mc_hub'


def shell_path(path):
    value = Path(path).resolve().as_posix()
    return '/' + value[0].lower() + value[2:]


def run_bash(script, env):
    result = subprocess.run([BASH], input=script, text=True, env=env,
                            capture_output=True, timeout=90)
    if result.returncode:
        raise RuntimeError('Synthetic Bash step failed: ' + result.stderr.strip())


def main():
    if not PG_BIN.joinpath('pg_dump.exe').is_file() or not BASH.is_file():
        raise RuntimeError('Local PostgreSQL 18 and Git Bash are required.')
    marker = uuid.uuid4().hex[:10]
    source_db = 'mc_synthetic_source_' + marker
    target_db = 'mc_synthetic_restored_' + marker
    admin = psycopg.connect(host='127.0.0.1', port=PORT, user=USER, dbname='postgres', autocommit=True)
    created = []
    try:
        for name in (source_db, target_db):
            admin.execute('CREATE DATABASE ' + name)
            created.append(name)
        with psycopg.connect(host='127.0.0.1', port=PORT, user=USER, dbname=source_db) as source:
            source.execute('CREATE TABLE synthetic_history (label text NOT NULL)')
            source.execute('INSERT INTO synthetic_history VALUES (%s)', ('fictional approved-version history',))
        with tempfile.TemporaryDirectory(prefix='rehearsal-', dir=ROOT / '.local') as scratch:
            base = Path(scratch)
            media = base / 'evidence'
            media.mkdir()
            sample = b'fictional immutable evidence bytes\n'
            (media / 'fictional.txt').write_bytes(sample)
            backups = base / 'backups'
            env_file = base / 'synthetic.env'
            env_file.write_text(
                'BACKUP_ROOT=' + shlex.quote(shell_path(backups)) + '\n'
                'PRIVATE_MEDIA_ROOT=' + shlex.quote(shell_path(media)) + '\n'
                'PGHOST=127.0.0.1\nPGPORT=55432\nPGUSER=mc_hub\n'
                'PGDATABASE=' + source_db + '\n', encoding='ascii')
            wrapper = base / 'python3'
            wrapper.write_text('#!/usr/bin/env bash\n'
                'output=$(' + '"' + shell_path(sys.executable) + '"' +
                ' "$(cygpath -w "$1")" "$(cygpath -w "$2")" "$(cygpath -w "$3")") || exit "$?"\n'
                'cygpath -u "$output"\n', encoding='ascii', newline='\n')
            wrapper.chmod(0o700)
            env = os.environ.copy()
            env.pop('PGPASSWORD', None)
            env['MC_ENV_FILE'] = shell_path(env_file)
            env['MC_RELEASE_COMMIT'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
            prefix = 'export PATH="' + shell_path(PG_BIN) + ':' + shell_path(base) + ':$PATH"\n'
            run_bash(prefix + '"' + shell_path(ROOT / 'deploy/scripts/backup.sh') + '"\n', env)
            bundle, = backups.glob('*.tar.gz')
            restore_dir = base / 'verified'
            run_bash(prefix + '"' + shell_path(ROOT / 'deploy/scripts/restore-verify.sh') +
                     '" "' + shell_path(bundle) + '" "' + shell_path(restore_dir) + '"\n', env)
            payload, = restore_dir.iterdir()
            subprocess.run([PG_BIN / 'pg_restore.exe', '--no-owner', '--dbname=' + target_db,
                            payload / 'database.dump'], check=True, capture_output=True,
                           env={**env, 'PGHOST': '127.0.0.1', 'PGPORT': str(PORT), 'PGUSER': USER})
            with psycopg.connect(host='127.0.0.1', port=PORT, user=USER, dbname=target_db) as target:
                restored = target.execute('SELECT label FROM synthetic_history').fetchone()[0]
            with tarfile.open(payload / 'evidence.tar.gz', 'r:gz') as evidence:
                recovered = evidence.extractfile('./fictional.txt').read()
            assert restored == 'fictional approved-version history'
            assert recovered == sample
            assert hashlib.sha256(recovered).digest() == hashlib.sha256(sample).digest()
            print('Synthetic backup, portable verification, database restore, evidence extraction and comparison passed.')
            print('Temporary archives and files removed by the rehearsal harness.')
    finally:
        for name in reversed(created):
            admin.execute('DROP DATABASE IF EXISTS ' + name)
        admin.close()
        print('Temporary synthetic databases removed.')


if __name__ == '__main__':
    main()

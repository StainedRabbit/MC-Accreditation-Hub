"""Generate local-only demo credentials and seed explicitly, without exposing passwords in logs."""
import os
from pathlib import Path
import secrets
import subprocess
import sys

root = Path(__file__).resolve().parent.parent
local = root / '.local'
local.mkdir(exist_ok=True)
credentials = local / 'demo-credentials.txt'
if credentials.exists():
    raise SystemExit('Demo credentials already exist. Use the existing credentials; no passwords changed.')
password = secrets.token_urlsafe(18)
result = subprocess.run([sys.executable, str(root / 'backend/manage.py'), 'seed_demo'],
                        env={**os.environ, 'MC_DEMO_PASSWORD': password})
if result.returncode:
    raise SystemExit(result.returncode)
credentials.write_text('LOCAL DEMO ONLY. Do not use real institutional evidence.\n\n' +
    '\n'.join(f'demo.{role}' for role in ['coordinator', 'reviewer', 'custodian', 'viewer', 'administrator']) +
    '\n\nPassword for these fictional accounts: ' + password + '\n', encoding='utf-8')
print('Demo credentials saved to .local/demo-credentials.txt (ignored by Git).')

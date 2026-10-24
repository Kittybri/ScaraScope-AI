#!/usr/bin/env bash
# Run on the Oracle VM, from a reviewed checkout. Keeps existing credentials/data.
set -euo pipefail
if [[ ${EUID} -ne 0 ]]; then
  echo 'Run with sudo: sudo bash deploy/oracle/deploy.sh [--discord]' >&2
  exit 1
fi
if [[ $# -gt 1 || ($# -eq 1 && $1 != --discord) ]]; then
  echo 'Usage: sudo bash deploy/oracle/deploy.sh [--discord]' >&2
  exit 1
fi
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
command -v python3 >/dev/null
docker compose version >/dev/null
umask 077
python3 - <<'PY'
import os
from pathlib import Path
import secrets

env = Path('.env')
if not env.exists():
    template = Path('.env.example').read_text()
    content = template.replace('SCARASCOPE_API_KEY=\n',
                               f'SCARASCOPE_API_KEY={secrets.token_hex(32)}\n', 1)
    fd = os.open(env, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as output:
        output.write(content)
elif env.is_symlink() or not env.is_file():
    raise SystemExit('Refusing an unsafe .env path.')
env.chmod(0o600)
PY
compose=(docker compose --env-file .env -f compose.yaml)
if [[ ${1:-} == --discord ]]; then
  compose+=(--profile discord)
  # Parse with Compose, never execute the secrets file as a shell script.
  "${compose[@]}" config --format json | python3 -c '
import json, sys
token = json.load(sys.stdin)["services"]["discord"]["environment"].get("DISCORD_BOT_TOKEN", "")
if not token.strip():
    raise SystemExit("Set DISCORD_BOT_TOKEN in deploy/oracle/.env before enabling Discord.")
'
fi
"${compose[@]}" config --quiet
"${compose[@]}" up --detach --build --wait --wait-timeout 180
python3 - <<'PY'
import json
import urllib.request

with urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=10) as response:
    health = json.load(response)
if health.get('status') != 'ok' or not health.get('auth_enabled') or not health.get('auth_required'):
    raise SystemExit('Health check failed or API authentication is disabled.')
print('ScaraScope API is healthy with authentication required.')
print('Web app: VM loopback port 8000. Connect using the SSH tunnel in deploy/oracle/README.md.')
print('Credentials remain in deploy/oracle/.env on the VM; they were not printed.')
PY

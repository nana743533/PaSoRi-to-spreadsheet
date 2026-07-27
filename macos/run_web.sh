#!/bin/bash
# Web UI（app.py）を起動 → http://127.0.0.1:5000
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

exec "$ROOT/venv/bin/python3" "$ROOT/app.py" "$@"

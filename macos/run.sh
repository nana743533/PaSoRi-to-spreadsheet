#!/bin/bash
# CLI 出席管理（attendance.py）を起動
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

exec "$ROOT/venv/bin/python3" "$ROOT/attendance.py" "$@"

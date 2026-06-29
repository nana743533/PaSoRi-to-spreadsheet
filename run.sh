#!/bin/bash
# 出席管理システム 実行スクリプト
cd "$(dirname "$0")"

# .env ファイルがあれば読み込む
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

exec ./venv/bin/python3 attendance.py "$@"

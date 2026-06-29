#!/bin/bash
# FeliCa 出席管理システム 実行スクリプト
cd "$(dirname "$0")"
export DYLD_LIBRARY_PATH=/opt/homebrew/opt/expat/lib
exec ./venv/bin/python3 attendance.py "$@"

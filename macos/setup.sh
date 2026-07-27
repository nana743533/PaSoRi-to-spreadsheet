#!/bin/bash
# macOS 一括セットアップ
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> 仮想環境を作成"
python3 -m venv venv

echo "==> 依存パッケージをインストール"
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

if [ ! -f .env ]; then
    cp .env.example .env
    echo "==> .env を作成しました（中身を編集してください）"
else
    echo "==> .env は既にあるためスキップ"
fi

mkdir -p credentials

echo ""
echo "セットアップ完了"
echo "  1. .env を編集"
echo "  2. credentials/ にサービスアカウント JSON を配置"
echo "  3. ./macos/run_web.sh  または  ./macos/run.sh"

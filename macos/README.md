# macOS セットアップ

macOS 13 以降では RC-S300 の追加ドライバは不要です（OS が PC/SC デバイスとして認識します）。

## 必要なもの

| 項目 | 備考 |
|------|------|
| macOS 13+ | ドライバ不要 |
| Python 3.12+ | Homebrew 推奨 |
| SONY PaSoRi RC-S300 | USB 接続 |
| NTAG215 カード | NFC Forum Type 2 Tag |

## セットアップ

リポジトリのルートで実行します。

```bash
# 1. 一括セットアップ（venv 作成・依存インストール・.env 作成）
./macos/setup.sh

# 2. .env を編集
#    SPREADSHEET_KEY / CREDENTIALS_FILE を記入

# 3. Google サービスアカウントの認証 JSON を credentials/ に配置
```

手動で行う場合:

```bash
cd "$(dirname "$0")/.."   # リポジトリルートへ
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## 使い方

```bash
# Web UI（http://127.0.0.1:5000）
./macos/run_web.sh

# CLI 出席モード
./macos/run.sh

# CLI カード登録
./macos/run.sh --register

# CLI 登録済み一覧
./macos/run.sh --list
```

## リーダー確認

```bash
source venv/bin/activate
python3 -c "from smartcard.System import readers; print(readers())"
```

`SONY FeliCa Port/PaSoRi 4.0` のような名前が出れば OK です。
